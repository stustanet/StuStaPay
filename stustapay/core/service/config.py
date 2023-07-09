import asyncpg

from stustapay.core.config import Config
from stustapay.core.schema.config import ConfigEntry, PublicConfig, SEPAConfig
from stustapay.core.schema.user import Privilege
from stustapay.core.service.auth import AuthService
from stustapay.core.service.common.dbservice import DBService
from stustapay.core.service.common.decorators import requires_user, with_db_transaction, DbContext, UserContext
from stustapay.core.service.common.error import NotFound


async def get_currency_identifier(*, conn: asyncpg.Connection) -> str:
    return await conn.fetchval("select value from config where key = 'currency.identifier' limit 1")


class ConfigService(DBService):
    def __init__(self, db_pool: asyncpg.Pool, config: Config, auth_service: AuthService):
        super().__init__(db_pool, config)
        self.auth_service = auth_service

    @with_db_transaction
    async def is_sumup_topup_enabled(self, ctx: DbContext) -> bool:
        db_config_entry = await ctx.conn.fetchval("select value from config where key = 'sumup_topup.enabled'")
        return self.cfg.customer_portal.sumup_config.enabled and db_config_entry == "true"

    @with_db_transaction
    async def get_public_config(self, ctx: DbContext) -> PublicConfig:
        row = await ctx.conn.fetchrow(
            "select "
            "   (select value from config where key = 'currency.symbol') as currency_symbol,"
            "   (select value from config where key = 'currency.identifier') as currency_identifier,"
            "   (select value from config where key = 'customer_portal.contact_email') as contact_email"
        )

        return PublicConfig(
            currency_symbol=row["currency_symbol"],
            currency_identifier=row["currency_identifier"],
            test_mode=self.cfg.core.test_mode,
            test_mode_message=self.cfg.core.test_mode_message,
            contact_email=row["contact_email"],
            sumup_topup_enabled=await self.is_sumup_topup_enabled(ctx),
        )

    @with_db_transaction
    async def get_sepa_config(self, ctx: DbContext) -> SEPAConfig:
        row = await ctx.conn.fetchrow(
            "select "
            "   (select value from config where key = 'customer_portal.sepa.sender_name') as sender_name,"
            "   (select value from config where key = 'customer_portal.sepa.sender_iban') as sender_iban,"
            "   (select value from config where key = 'customer_portal.sepa.description') as description,"
            "   (select value::json from config where key = 'customer_portal.sepa.allowed_country_codes') as allowed_country_codes"
        )

        return SEPAConfig(
            sender_name=row["sender_name"],
            sender_iban=row["sender_iban"],
            description=row["description"],
            allowed_country_codes=row["allowed_country_codes"],
        )

    @with_db_transaction
    @requires_user([Privilege.config_management])
    async def list_config_entries(self, ctx: UserContext) -> list[ConfigEntry]:
        cursor = ctx.conn.cursor("select * from config")
        result = []
        async for row in cursor:
            result.append(ConfigEntry.parse_obj(row))
        return result

    @with_db_transaction
    @requires_user([Privilege.config_management])
    async def set_config_entry(self, ctx: UserContext, *, entry: ConfigEntry) -> ConfigEntry:
        row = await ctx.conn.fetchrow(
            "update config set value = $2 where key = $1 returning key, value", entry.key, entry.value
        )
        if row is None:
            raise NotFound("config", entry.key)

        return ConfigEntry.parse_obj(row)
