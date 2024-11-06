from typing import Optional

import asyncpg
from sftkit.database import Connection
from sftkit.error import NotFound
from sftkit.service import Service, with_db_transaction

from stustapay.core.config import Config
from stustapay.core.schema.tax_rate import NewTaxRate, TaxRate
from stustapay.core.schema.tree import Node, ObjectType
from stustapay.core.schema.user import Privilege
from stustapay.core.service.auth import AuthService
from stustapay.core.service.common.decorators import requires_node, requires_user


async def fetch_tax_rate_none(*, conn: Connection, node: Node) -> TaxRate:
    return await conn.fetch_one(
        TaxRate, "select * from tax_rate where name = 'none' and node_id = any($1)", node.ids_to_event_node
    )


async def _fetch_tax_rate(*, conn: Connection, node: Node, tax_rate_id: int) -> TaxRate | None:
    return await conn.fetch_maybe_one(
        TaxRate, "select * from tax_rate where id = $1 and node_id = any($2)", tax_rate_id, node.ids_to_event_node
    )


class TaxRateService(Service[Config]):
    def __init__(self, db_pool: asyncpg.Pool, config: Config, auth_service: AuthService):
        super().__init__(db_pool, config)
        self.auth_service = auth_service

    @with_db_transaction
    @requires_node(object_types=[ObjectType.tax_rate], event_only=True)
    @requires_user([Privilege.node_administration])
    async def create_tax_rate(self, *, conn: Connection, node: Node, tax_rate: NewTaxRate) -> TaxRate:
        tax_rate_id = await conn.fetchval(
            "insert into tax_rate (node_id, name, rate, description) values ($1, $2, $3, $4) returning id",
            node.id,
            tax_rate.name,
            tax_rate.rate,
            tax_rate.description,
        )
        tax = await _fetch_tax_rate(conn=conn, node=node, tax_rate_id=tax_rate_id)
        assert tax is not None
        return tax

    @with_db_transaction(read_only=True)
    @requires_node(event_only=True)
    @requires_user()
    async def list_tax_rates(self, *, conn: Connection, node: Node) -> list[TaxRate]:
        return await conn.fetch_many(
            TaxRate, "select * from tax_rate where node_id = any($1) order by name", node.ids_to_event_node
        )

    @with_db_transaction(read_only=True)
    @requires_node(event_only=True)
    @requires_user()
    async def get_tax_rate(self, *, conn: Connection, node: Node, tax_rate_id: int) -> Optional[TaxRate]:
        return await _fetch_tax_rate(conn=conn, node=node, tax_rate_id=tax_rate_id)

    @with_db_transaction
    @requires_node(object_types=[ObjectType.tax_rate], event_only=True)
    @requires_user([Privilege.node_administration])
    async def update_tax_rate(self, *, conn: Connection, node: Node, tax_rate_id: int, tax_rate: NewTaxRate) -> TaxRate:
        tax_id = await conn.fetchval(
            "update tax_rate set name = $1, rate = $2, description = $3 "
            "where id = $4 and node_id = any($5) returning id",
            tax_rate.name,
            tax_rate.rate,
            tax_rate.description,
            tax_rate_id,
            node.ids_to_event_node,
        )
        if tax_id is None:
            raise NotFound(element_typ="tax_rate", element_id=tax_rate_id)
        updated_tax = await _fetch_tax_rate(conn=conn, node=node, tax_rate_id=tax_rate_id)
        assert updated_tax is not None
        return updated_tax

    @with_db_transaction
    @requires_node(object_types=[ObjectType.tax_rate], event_only=True)
    @requires_user([Privilege.node_administration])
    async def delete_tax_rate(self, *, conn: Connection, node: Node, tax_rate_id: int) -> bool:
        result = await conn.execute(
            "delete from tax_rate where id = $1 and node_id = any($2)", tax_rate_id, node.ids_to_event_node
        )
        return result != "DELETE 0"
