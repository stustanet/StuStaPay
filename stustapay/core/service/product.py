from typing import Optional

import asyncpg

from stustapay.core.config import Config
from stustapay.core.schema.product import (
    NewProduct,
    Product,
    DISCOUNT_PRODUCT_ID,
    TOP_UP_PRODUCT_ID,
    MONEY_TRANSFER_PRODUCT_ID,
    MONEY_DIFFERENCE_PRODUCT_ID,
    PAY_OUT_PRODUCT_ID,
)
from stustapay.core.schema.user import Privilege
from stustapay.core.service.auth import AuthService
from stustapay.core.service.common.dbservice import DBService
from stustapay.core.service.common.decorators import with_db_transaction, requires_user, UserContext
from stustapay.core.service.common.error import ServiceException


async def fetch_product(*, conn: asyncpg.Connection, product_id: int) -> Optional[Product]:
    result = await conn.fetchrow("select * from product_with_tax_and_restrictions where id = $1", product_id)
    if result is None:
        return None
    return Product.parse_obj(result)


async def fetch_constant_product(*, conn: asyncpg.Connection, product_id: int) -> Product:
    product = await fetch_product(conn=conn, product_id=product_id)
    if product is None:
        raise RuntimeError("no product found in database")
    return product


async def fetch_discount_product(*, conn: asyncpg.Connection) -> Product:
    return await fetch_constant_product(conn=conn, product_id=DISCOUNT_PRODUCT_ID)


async def fetch_top_up_product(*, conn: asyncpg.Connection) -> Product:
    return await fetch_constant_product(conn=conn, product_id=TOP_UP_PRODUCT_ID)


async def fetch_pay_out_product(*, conn: asyncpg.Connection) -> Product:
    return await fetch_constant_product(conn=conn, product_id=PAY_OUT_PRODUCT_ID)


async def fetch_money_transfer_product(*, conn: asyncpg.Connection) -> Product:
    return await fetch_constant_product(conn=conn, product_id=MONEY_TRANSFER_PRODUCT_ID)


async def fetch_money_difference_product(*, conn: asyncpg.Connection) -> Product:
    return await fetch_constant_product(conn=conn, product_id=MONEY_DIFFERENCE_PRODUCT_ID)


class ProductIsLockedException(ServiceException):
    id = "ProductNotEditable"
    description = "The product has been marked as not editable, its core metadata is therefore fixed"


class ProductService(DBService):
    def __init__(self, db_pool: asyncpg.Pool, config: Config, auth_service: AuthService):
        super().__init__(db_pool, config)
        self.auth_service = auth_service

    @with_db_transaction
    @requires_user([Privilege.product_management])
    async def create_product(self, ctx: UserContext, *, product: NewProduct) -> Product:
        product_id = await ctx.conn.fetchval(
            "insert into product "
            "(name, price, tax_name, target_account_id, fixed_price, price_in_vouchers, is_locked, is_returnable) "
            "values ($1, $2, $3, $4, $5, $6, $7, $8) "
            "returning id",
            product.name,
            product.price,
            product.tax_name,
            product.target_account_id,
            product.fixed_price,
            product.price_in_vouchers,
            product.is_locked,
            product.is_returnable,
        )

        for restriction in product.restrictions:
            await ctx.conn.execute(
                "insert into product_restriction (id, restriction) values ($1, $2)", product_id, restriction.name
            )

        if product_id is None:
            raise RuntimeError("product should have been created")
        created_product = await fetch_product(conn=ctx.conn, product_id=product_id)
        assert created_product is not None
        return created_product

    @with_db_transaction
    @requires_user()
    async def list_products(self, ctx: UserContext) -> list[Product]:
        cursor = ctx.conn.cursor("select * from product_with_tax_and_restrictions")
        result = []
        async for row in cursor:
            result.append(Product.parse_obj(row))
        return result

    @with_db_transaction
    @requires_user()
    async def get_product(self, ctx: UserContext, *, product_id: int) -> Optional[Product]:
        return await fetch_product(conn=ctx.conn, product_id=product_id)

    @with_db_transaction
    @requires_user([Privilege.product_management])
    async def update_product(self, ctx: UserContext, *, product_id: int, product: NewProduct) -> Optional[Product]:
        current_product = await fetch_product(conn=ctx.conn, product_id=product_id)
        if current_product is None:
            return None

        if current_product.is_locked:
            if any(
                [
                    current_product.price != product.price,
                    current_product.fixed_price != product.fixed_price,
                    current_product.price_in_vouchers != product.price_in_vouchers,
                    current_product.target_account_id != product.target_account_id,
                    current_product.tax_name != product.tax_name,
                    current_product.restrictions != product.restrictions,
                    current_product.is_locked != product.is_locked,
                    current_product.is_returnable != product.is_returnable,
                ]
            ):
                raise ProductIsLockedException()

        row = await ctx.conn.fetchrow(
            "update product set name = $2, price = $3, tax_name = $4, target_account_id = $5, fixed_price = $6, "
            "price_in_vouchers = $7, is_locked = $8, is_returnable = $9 "
            "where id = $1 "
            "returning id",
            product_id,
            product.name,
            product.price,
            product.tax_name,
            product.target_account_id,
            product.fixed_price,
            product.price_in_vouchers,
            product.is_locked,
            product.is_returnable,
        )
        if row is None:
            raise RuntimeError("product disappeared unexpecteldy within a transaction")

        await ctx.conn.execute("delete from product_restriction where id = $1", product_id)
        for restriction in product.restrictions:
            await ctx.conn.execute(
                "insert into product_restriction (id, restriction) values ($1, $2)", product_id, restriction.name
            )

        return await fetch_product(conn=ctx.conn, product_id=product_id)

    @with_db_transaction
    @requires_user([Privilege.product_management])
    async def delete_product(self, ctx: UserContext, *, product_id: int) -> bool:
        result = await ctx.conn.execute(
            "delete from product where id = $1",
            product_id,
        )
        return result != "DELETE 0"
