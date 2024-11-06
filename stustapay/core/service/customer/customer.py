# pylint: disable=unexpected-keyword-arg
# pylint: disable=unused-argument
import logging
import re
from typing import Optional

import asyncpg
from pydantic import BaseModel
from schwifty import IBAN
from sftkit.database import Connection
from sftkit.error import AccessDenied, InvalidArgument
from sftkit.service import Service, with_db_transaction

from stustapay.core.config import Config
from stustapay.core.schema.customer import (
    Customer,
    OrderWithBon,
    PayoutInfo,
    PayoutTransaction,
)
from stustapay.core.schema.tree import Language
from stustapay.core.service.auth import AuthService, CustomerTokenMetadata
from stustapay.core.service.common.decorators import requires_customer
from stustapay.core.service.config import ConfigService
from stustapay.core.service.customer.payout import PayoutService
from stustapay.core.service.customer.sumup import SumupService
from stustapay.core.service.mail import MailService
from stustapay.core.service.tree.common import (
    fetch_event_node_for_node,
    fetch_restricted_event_settings_for_node,
)


class CustomerPortalApiConfig(BaseModel):
    test_mode: bool
    test_mode_message: str
    data_privacy_url: str
    contact_email: str
    about_page_url: str
    payout_enabled: bool
    currency_identifier: str
    sumup_topup_enabled: bool
    allowed_country_codes: Optional[list[str]]
    translation_texts: dict[Language, dict[str, str]]


class CustomerLoginSuccess(BaseModel):
    customer: Customer
    token: str


class CustomerBank(BaseModel):
    iban: str
    account_name: str
    email: str
    donation: float = 0.0


class CustomerService(Service[Config]):
    def __init__(self, db_pool: asyncpg.Pool, config: Config, auth_service: AuthService, config_service: ConfigService):
        super().__init__(db_pool, config)
        self.auth_service = auth_service
        self.config_service = config_service
        self.logger = logging.getLogger("customer")

        self.sumup = SumupService(db_pool=db_pool, config=config, auth_service=auth_service)
        self.payout = PayoutService(
            db_pool=db_pool, config=config, auth_service=auth_service, config_service=config_service
        )

    @with_db_transaction
    async def login_customer(self, *, conn: Connection, pin: str) -> CustomerLoginSuccess:
        # Customer has hardware tag and pin
        customer = await conn.fetch_maybe_one(
            Customer,
            "select c.* from user_tag ut join customer c on ut.id = c.user_tag_id where ut.pin = $1 or ut.pin = $2",
            # TODO: restore case sensitivity
            pin.lower(),  # for simulator
            pin.upper(),  # for humans
        )
        if customer is None:
            raise AccessDenied("Invalid pin")

        session_id = await conn.fetchval(
            "insert into customer_session (customer) values ($1) returning id", customer.id
        )
        token = self.auth_service.create_customer_access_token(
            CustomerTokenMetadata(customer_id=customer.id, session_id=session_id)
        )
        return CustomerLoginSuccess(
            customer=customer,
            token=token,
        )

    @with_db_transaction
    @requires_customer
    async def logout_customer(self, *, conn: Connection, current_customer: Customer, token: str) -> bool:
        token_payload = self.auth_service.decode_customer_jwt_payload(token)
        assert token_payload is not None
        assert current_customer.id == token_payload.customer_id

        result = await conn.execute(
            "delete from customer_session where customer = $1 and id = $2",
            current_customer.id,
            token_payload.session_id,
        )
        return result != "DELETE 0"

    @with_db_transaction(read_only=True)
    @requires_customer
    async def get_customer(self, *, current_customer: Customer) -> Optional[Customer]:
        return current_customer

    @with_db_transaction(read_only=True)
    @requires_customer
    async def payout_info(self, *, conn: Connection, current_customer: Customer) -> PayoutInfo:
        # is customer registered for payout
        return await conn.fetch_one(
            PayoutInfo,
            "select "
            "   exists(select from payout where customer_account_id = $1) as in_payout_run, "
            "   ( "
            "       select pr.set_done_at "
            "       from payout_run pr left join payout p on pr.id = p.payout_run_id left join customer c on p.customer_account_id = c.id"
            "       where c.id = $1 "
            "    ) as payout_date",
            current_customer.id,
        )

    @with_db_transaction(read_only=True)
    @requires_customer
    async def get_orders_with_bon(self, *, conn: Connection, current_customer: Customer) -> list[OrderWithBon]:
        return await conn.fetch_many(
            OrderWithBon,
            "select o.*, b.generated as bon_generated from order_value_prefiltered("
            "   (select array_agg(o.id) from ordr o where customer_account_id = $1)"
            ") o left join bon b ON o.id = b.id order by o.booked_at desc",
            current_customer.id,
        )

    @with_db_transaction(read_only=True)
    @requires_customer
    async def get_payout_transactions(self, *, conn: Connection, current_customer: Customer) -> list[PayoutTransaction]:
        return await conn.fetch_many(
            PayoutTransaction,
            "select t.amount, t.booked_at, a.name as target_account_name, a.type as target_account_type, t.id as transaction_id "
            "from transaction t join account a on t.target_account = a.id "
            "where t.order_id is null and t.source_account = $1 and t.target_account in (select id from account where type = 'cash_exit' or type = 'donation_exit' or type = 'sepa_exit')",
            current_customer.id,
        )

    @with_db_transaction
    @requires_customer
    async def update_customer_info(
        self, *, conn: Connection, current_customer: Customer, customer_bank: CustomerBank, mail_service: MailService
    ) -> None:
        event_node = await fetch_event_node_for_node(conn=conn, node_id=current_customer.node_id)
        assert event_node is not None
        assert event_node.event is not None
        await self.check_payout_run(conn, current_customer)

        # check iban
        try:
            iban = IBAN(customer_bank.iban, validate_bban=True)
        except ValueError as exc:
            raise InvalidArgument("Provided IBAN is not valid") from exc

        # check country code
        if not event_node.event.sepa_enabled:
            raise InvalidArgument("SEPA payout is disabled")

        allowed_country_codes = event_node.event.sepa_allowed_country_codes
        if iban.country_code not in allowed_country_codes:
            raise InvalidArgument("Provided IBAN contains country code which is not supported")

        # check donation
        if customer_bank.donation < 0:
            raise InvalidArgument("Donation cannot be negative")
        if customer_bank.donation > current_customer.balance:
            raise InvalidArgument("Donation cannot be higher then your balance")

        # check email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", customer_bank.email):
            raise InvalidArgument("Provided email is not valid")

        # if customer_info does not exist create it, otherwise update it
        await conn.execute(
            "update customer_info set iban=$2, account_name=$3, email=$4, donation=$5, donate_all=false, has_entered_info=true "
            "where customer_account_id = $1",
            current_customer.id,
            iban.compact,
            customer_bank.account_name,
            customer_bank.email,
            round(customer_bank.donation, 2),
        )
        # get updated customer
        current_customer = await conn.fetch_one(
            Customer,
            "select * from customer where id = $1",
            current_customer.id,
        )
        if current_customer.email is not None:
            res_config = await fetch_restricted_event_settings_for_node(conn, current_customer.node_id)
            mail_service.send_mail(
                subject=res_config.payout_registered_subject,
                message=res_config.payout_registered_message.format(**current_customer.model_dump()),
                from_email=res_config.payout_sender,
                to_email=current_customer.email,
                node_id=current_customer.node_id,
            )

    async def check_payout_run(self, conn: Connection, current_customer: Customer) -> None:
        # if a payout is assigned, disallow updates.
        is_in_payout = await conn.fetchval(
            "select exists(select from payout where customer_account_id = $1)",
            current_customer.id,
        )
        if is_in_payout:
            raise InvalidArgument(
                "Your account is already scheduled for the next payout, so updates are no longer possible."
            )

    @with_db_transaction
    @requires_customer
    async def update_customer_info_donate_all(
        self, *, conn: Connection, current_customer: Customer, mail_service: MailService
    ) -> None:
        await self.check_payout_run(conn, current_customer)
        await conn.execute(
            "update customer_info set donation=null, donate_all=true, has_entered_info=true "
            "where customer_account_id = $1",
            current_customer.id,
        )

    @with_db_transaction(read_only=True)
    async def get_api_config(self, *, conn: Connection, base_url: str) -> CustomerPortalApiConfig:
        node_id = await conn.fetchval(
            "select n.id from node n join event e on n.event_id = e.id where e.customer_portal_url = $1", base_url
        )
        if node_id is None:
            raise InvalidArgument("Invalid customer portal configuration")
        node = await fetch_event_node_for_node(conn=conn, node_id=node_id)
        assert node is not None
        assert node.event is not None
        return CustomerPortalApiConfig(
            test_mode=self.config.core.test_mode,
            test_mode_message=self.config.core.test_mode_message,
            about_page_url=node.event.customer_portal_about_page_url,
            allowed_country_codes=node.event.sepa_allowed_country_codes,
            contact_email=node.event.customer_portal_contact_email,
            data_privacy_url=node.event.customer_portal_data_privacy_url,
            payout_enabled=node.event.sepa_enabled,
            sumup_topup_enabled=self.config.core.sumup_enabled and node.event.sumup_topup_enabled,
            translation_texts=node.event.translation_texts,
            currency_identifier=node.event.currency_identifier,
        )

    @with_db_transaction
    @requires_customer
    async def get_bon(self, *, conn: Connection, current_customer: Customer, bon_id: int) -> tuple[str, bytes]:
        blob = await conn.fetchrow(
            "select content, mime_type from bon b join ordr o on b.id = o.id "
            "where b.id = $1 and o.customer_account_id = $2",
            bon_id,
            current_customer.id,
        )
        if not blob:
            raise InvalidArgument("Bon not found")

        return blob["mime_type"], blob["content"]
