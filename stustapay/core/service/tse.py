import asyncpg
from sftkit.database import Connection
from sftkit.error import NotFound
from sftkit.service import Service, with_db_transaction

from stustapay.core.config import Config
from stustapay.core.schema.tree import Node, ObjectType
from stustapay.core.schema.tse import NewTse, Tse, UpdateTse
from stustapay.core.schema.user import Privilege
from stustapay.core.service.auth import AuthService
from stustapay.core.service.common.decorators import requires_node, requires_user


async def list_tses(conn: Connection, node: Node) -> list[Tse]:
    return await conn.fetch_many(Tse, "select * from tse where node_id = any($1) order by name", node.ids_to_event_node)


async def fetch_tse(conn: Connection, node: Node, tse_id) -> Tse:
    return await conn.fetch_one(
        Tse, "select * from tse where node_id = any($1) and id = $2", node.ids_to_event_node, tse_id
    )


class TseService(Service[Config]):
    def __init__(self, db_pool: asyncpg.Pool, config: Config, auth_service: AuthService):
        super().__init__(db_pool, config)
        self.auth_service = auth_service

    @with_db_transaction
    @requires_node(object_types=[ObjectType.tse], event_only=False)
    @requires_user([Privilege.node_administration])
    async def create_tse(self, *, conn: Connection, node: Node, new_tse: NewTse) -> Tse:
        tse_id = await conn.fetchval(
            "insert into tse (node_id, name, serial, ws_url, ws_timeout, password, status) "
            "values ($1, $2, $3, $4, $5, $6, 'new') returning id",
            node.id,
            new_tse.name,
            new_tse.serial,
            new_tse.ws_url,
            new_tse.ws_timeout,
            new_tse.password,
        )
        return await conn.fetch_one(Tse, "select * from tse where id = $1", tse_id)

    @with_db_transaction
    @requires_node(object_types=[ObjectType.tse], event_only=False)
    @requires_user([Privilege.node_administration])
    async def update_tse(self, *, conn: Connection, node: Node, tse_id: int, updated_tse: UpdateTse) -> Tse:
        tse_id = await conn.fetchval(
            "update tse set name = $1, ws_timeout = $2, ws_url = $3, password = $4 "
            "where id = $5 and node_id = any($6) returning id",
            updated_tse.name,
            updated_tse.ws_timeout,
            updated_tse.ws_url,
            updated_tse.password,
            tse_id,
            node.ids_to_event_node,
        )
        if tse_id is None:
            raise NotFound(element_typ="tse", element_id=str(tse_id))
        return await conn.fetch_one(Tse, "select * from tse where id = $1", tse_id)

    @with_db_transaction(read_only=True)
    @requires_node(event_only=False)
    @requires_user([Privilege.node_administration])
    async def list_tses(self, *, conn: Connection, node: Node) -> list[Tse]:
        return await list_tses(conn=conn, node=node)

    @with_db_transaction(read_only=True)
    @requires_node(event_only=False)
    @requires_user([Privilege.node_administration])
    async def get_tse(self, *, conn: Connection, node: Node, tse_id: int) -> Tse:
        return await fetch_tse(conn=conn, node=node, tse_id=tse_id)
