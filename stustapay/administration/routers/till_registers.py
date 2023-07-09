from fastapi import APIRouter

from stustapay.core.http.auth_user import CurrentAuthToken
from stustapay.core.http.context import ContextTillService
from stustapay.core.schema.till import NewCashRegister, CashRegister
from stustapay.core.service.common.decorators import OptionalUserContext
from stustapay.core.util import BaseModel

router = APIRouter(
    prefix="/till-registers",
    tags=["till-registers"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[CashRegister])
async def list_register_stockings(token: CurrentAuthToken, till_service: ContextTillService):
    return await till_service.register.list_cash_registers_admin(OptionalUserContext(token=token))


@router.post("", response_model=CashRegister)
async def create_register(
    register: NewCashRegister,
    token: CurrentAuthToken,
    till_service: ContextTillService,
):
    return await till_service.register.create_cash_register(OptionalUserContext(token=token), new_register=register)


class TransferRegisterPayload(BaseModel):
    source_cashier_id: int
    target_cashier_id: int


@router.post("/transfer-register")
async def transfer_register(
    token: CurrentAuthToken,
    payload: TransferRegisterPayload,
    till_service: ContextTillService,
):
    return await till_service.register.transfer_cash_register_admin(
        OptionalUserContext(token=token),
        source_cashier_id=payload.source_cashier_id,
        target_cashier_id=payload.target_cashier_id,
    )


@router.post("/{register_id}")
async def update_register(
    register_id: int,
    register: NewCashRegister,
    token: CurrentAuthToken,
    till_service: ContextTillService,
):
    return await till_service.register.update_cash_register(
        OptionalUserContext(token=token), register_id=register_id, register=register
    )


@router.delete("/{register_id}")
async def delete_register(
    register_id: int,
    token: CurrentAuthToken,
    till_service: ContextTillService,
):
    return await till_service.register.delete_cash_register(OptionalUserContext(token=token), register_id=register_id)
