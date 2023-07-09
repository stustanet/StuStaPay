from datetime import datetime
from typing import Optional

import asyncpg
from pydantic import BaseModel

from stustapay.core.config import Config
from stustapay.core.schema.account import ACCOUNT_IMBALANCE, ACCOUNT_CASH_VAULT
from stustapay.core.schema.cashier import Cashier, CashierShift, CashierShiftStats
from stustapay.core.schema.order import PaymentMethod, OrderType
from stustapay.core.schema.till import VIRTUAL_TILL_ID
from stustapay.core.schema.user import Privilege, User, CurrentUser
from stustapay.core.service.common.dbservice import DBService
from stustapay.core.service.common.decorators import with_db_transaction, requires_user, UserContext
from .common.error import ServiceException, NotFound
from .order.booking import book_order, BookingIdentifier, NewLineItem, book_money_transfer, OrderInfo
from .product import fetch_money_difference_product, fetch_product
from .user import AuthService


class InvalidCloseOutException(ServiceException):
    id = "InvalidCloseOut"
    description = "The cashier shift can't be closed out"


class CloseOut(BaseModel):
    comment: str
    actual_cash_drawer_balance: float
    closing_out_user_id: int


class CloseOutResult(BaseModel):
    cashier_id: int
    imbalance: float


class CashierService(DBService):
    def __init__(self, db_pool: asyncpg.Pool, config: Config, auth_service: AuthService):
        super().__init__(db_pool, config)
        self.auth_service = auth_service

    @with_db_transaction
    @requires_user([Privilege.cashier_management])
    async def list_cashiers(self, ctx: UserContext) -> list[Cashier]:
        cursor = ctx.conn.cursor("select * from cashier")
        result = []
        async for row in cursor:
            result.append(Cashier.parse_obj(row))
        return result

    @with_db_transaction
    @requires_user([Privilege.cashier_management])
    async def get_cashier(self, ctx: UserContext, *, cashier_id: int) -> Optional[Cashier]:
        row = await ctx.conn.fetchrow("select * from cashier where id = $1", cashier_id)
        if not row:
            return None
        return Cashier.parse_obj(row)

    @staticmethod
    async def _get_cashier_shift(conn: asyncpg.Connection, cashier_id: int, shift_id: int) -> Optional[CashierShift]:
        row = await conn.fetchrow("select * from cashier_shift where cashier_id = $1 and id = $2", cashier_id, shift_id)
        if row is None:
            return None
        return CashierShift.parse_obj(row)

    @with_db_transaction
    @requires_user([Privilege.cashier_management])
    async def get_cashier_shifts(self, ctx: UserContext, *, cashier_id: int) -> list[CashierShift]:
        cashier = await self.get_cashier(ctx, cashier_id=cashier_id)
        if not cashier:
            raise NotFound(element_typ="cashier", element_id=cashier_id)
        cursor = ctx.conn.cursor("select * from cashier_shift where cashier_id = $1", cashier_id)
        result = []
        async for row in cursor:
            result.append(CashierShift.parse_obj(row))
        return result

    @staticmethod
    async def _get_current_cashier_shift_start(*, conn: asyncpg.Connection, cashier_id: int) -> Optional[datetime]:
        return await conn.fetchval(
            "select ordr.booked_at from ordr "
            "where ordr.cashier_id = $1 and ordr.booked_at > coalesce(("
            "   select cs.ended_at from cashier_shift cs "
            "   where cs.cashier_id = $1 order by ended_at desc limit 1"
            "), '1970-01-01'::timestamptz) "
            "order by ordr.booked_at asc limit 1",
            cashier_id,
        )

    @with_db_transaction
    @requires_user([Privilege.cashier_management])
    async def get_cashier_shift_stats(
        self,
        ctx: UserContext,
        *,
        cashier_id: int,
        shift_id: Optional[int] = None,
    ) -> Optional[CashierShiftStats]:
        shift_end = None
        if shift_id is None:
            shift_start = await self._get_current_cashier_shift_start(conn=ctx.conn, cashier_id=cashier_id)
        else:
            shift = await self._get_cashier_shift(conn=ctx.conn, cashier_id=cashier_id, shift_id=shift_id)
            if shift is None:
                raise NotFound(element_typ="cashier_shift", element_id=str(shift_id))
            shift_start = shift.started_at
            shift_end = shift.ended_at

        if shift_end is None:
            rows = await ctx.conn.fetch(
                "select li.product_id, sum(li.quantity) as quantity "
                "from line_item li join ordr o on li.order_id = o.id "
                "where o.cashier_id = $1 and o.booked_at >= $2 "
                "group by li.product_id",
                cashier_id,
                shift_start,
            )
        else:
            rows = await ctx.conn.fetch(
                "select li.product_id, sum(li.quantity) as quantity "
                "from line_item li join ordr o on li.order_id = o.id "
                "where o.cashier_id = $1 and o.booked_at >= $2 and o.booked_at <= $3 "
                "group by li.product_id",
                cashier_id,
                shift_start,
                shift_end,
            )
        stats = CashierShiftStats(booked_products=[])
        for row in rows:
            product = await fetch_product(conn=ctx.conn, product_id=row["product_id"])
            if product is None:
                continue
            stats.booked_products.append(CashierShiftStats.ProductStats(product=product, quantity=row["quantity"]))
        return stats

    @staticmethod
    async def _book_imbalance_order(
        *,
        conn: asyncpg.Connection,
        current_user: CurrentUser,
        cashier_account_id: int,
        cash_register_id: int,
        imbalance: float,
    ) -> OrderInfo:
        difference_product = await fetch_money_difference_product(conn=conn)
        line_items = [
            NewLineItem(
                quantity=1,
                product_id=difference_product.id,
                product_price=imbalance,
                tax_name=difference_product.tax_name,
                tax_rate=difference_product.tax_rate,
            )
        ]

        bookings: dict[BookingIdentifier, float] = {
            BookingIdentifier(source_account_id=cashier_account_id, target_account_id=ACCOUNT_IMBALANCE): -imbalance,
        }

        return await book_order(
            conn=conn,
            payment_method=PaymentMethod.cash,
            order_type=OrderType.money_transfer_imbalance,
            till_id=VIRTUAL_TILL_ID,
            cashier_id=current_user.id,
            line_items=line_items,
            bookings=bookings,
            cash_register_id=cash_register_id,
        )

    @staticmethod
    async def _book_money_transfer_close_out_start(
        *, conn: asyncpg.Connection, current_user: CurrentUser, cash_register_id: int, amount: float
    ) -> OrderInfo:
        return await book_money_transfer(
            conn=conn,
            originating_user_id=current_user.id,
            cash_register_id=cash_register_id,
            amount=amount,
            till_id=VIRTUAL_TILL_ID,
            bookings={},
        )

    @staticmethod
    async def _book_money_transfer_cash_vault_order(
        *,
        conn: asyncpg.Connection,
        current_user: CurrentUser,
        cashier_account_id: int,
        cash_register_id: int,
        amount: float,
    ) -> OrderInfo:
        bookings: dict[BookingIdentifier, float] = {
            BookingIdentifier(source_account_id=cashier_account_id, target_account_id=ACCOUNT_CASH_VAULT): amount,
        }
        return await book_money_transfer(
            conn=conn,
            originating_user_id=current_user.id,
            cash_register_id=cash_register_id,
            amount=-amount,
            bookings=bookings,
            till_id=VIRTUAL_TILL_ID,
        )

    @with_db_transaction
    @requires_user([Privilege.cashier_management])
    async def close_out_cashier(self, ctx: UserContext, *, cashier_id: int, close_out: CloseOut) -> CloseOutResult:
        cashier = await self.get_cashier(ctx, cashier_id=cashier_id)
        if cashier.cash_register_id is None:
            raise InvalidCloseOutException("Cashier does not have a cash register")
        expected_balance = cashier.cash_drawer_balance

        is_logged_in = await ctx.conn.fetchval("select true from till where active_user_id = $1", cashier_id)
        if is_logged_in:
            raise InvalidCloseOutException("cannot close out a cashier who is logged in at a terminal")

        if cashier.cash_register_id is None:
            raise InvalidCloseOutException("cashier does not have a cash register assigned")

        # TODO: which way to compute this
        shift_start = await self._get_current_cashier_shift_start(conn=ctx.conn, cashier_id=cashier_id)
        if shift_start is None:
            raise InvalidCloseOutException("the cashier did not start a shift, no orders were booked")
        shift_end = datetime.now()
        imbalance = close_out.actual_cash_drawer_balance - expected_balance

        # first we transfer all money to the virtual till via a tse signed order
        await self._book_money_transfer_close_out_start(
            conn=ctx.conn,
            current_user=ctx.current_user,
            cash_register_id=cashier.cash_register_id,
            amount=expected_balance,
        )

        # then we book two orders, one to track the imbalance, on to transfer the money to the cash vault
        order_info = await self._book_money_transfer_cash_vault_order(
            conn=ctx.conn,
            current_user=ctx.current_user,
            cashier_account_id=cashier.cashier_account_id,
            cash_register_id=cashier.cash_register_id,
            amount=close_out.actual_cash_drawer_balance,
        )
        imbalance_order_info = await self._book_imbalance_order(
            conn=ctx.conn,
            current_user=ctx.current_user,
            cashier_account_id=cashier.cashier_account_id,
            cash_register_id=cashier.cash_register_id,
            imbalance=imbalance,
        )

        await ctx.conn.execute(
            "insert into cashier_shift ("
            "   cashier_id, started_at, ended_at, actual_cash_drawer_balance, expected_cash_drawer_balance, "
            "   comment, close_out_order_id, close_out_imbalance_order_id, closing_out_user_id) "
            "values ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            cashier.id,
            shift_start,
            shift_end,
            close_out.actual_cash_drawer_balance,
            expected_balance,
            close_out.comment,
            order_info.id,
            imbalance_order_info.id,
            close_out.closing_out_user_id,
        )

        await ctx.conn.execute("update usr set cash_register_id = null where id = $1", cashier.id)
        await ctx.conn.execute("update till set z_nr = z_nr + 1 where id = $1", VIRTUAL_TILL_ID)
        # correct the actual balance to rule out any floating point errors / representation errors
        await ctx.conn.execute("update account set balance = 0 where id = $1", cashier.cashier_account_id)

        return CloseOutResult(cashier_id=cashier.id, imbalance=imbalance)
