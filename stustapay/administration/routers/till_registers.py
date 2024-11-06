from fastapi import APIRouter, Response
from pydantic import BaseModel

from stustapay.core.http.auth_user import CurrentAuthToken
from stustapay.core.http.context import ContextTillService
from stustapay.core.schema.till import CashRegister, NewCashRegister

router = APIRouter(
    prefix="/till_registers",
    tags=["till-registers"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[CashRegister])
async def list_cash_registers_admin(
    token: CurrentAuthToken, response: Response, till_service: ContextTillService, node_id: int
):
    resp = await till_service.register.list_cash_registers_admin(token=token, node_id=node_id)
    response.headers["Content-Range"] = str(len(resp))
    return resp


@router.post("", response_model=CashRegister)
async def create_register(
    register: NewCashRegister, token: CurrentAuthToken, till_service: ContextTillService, node_id: int
):
    return await till_service.register.create_cash_register(token=token, new_register=register, node_id=node_id)


class TransferRegisterPayload(BaseModel):
    source_cashier_id: int
    target_cashier_id: int


@router.post("/transfer-register")
async def transfer_register(
    token: CurrentAuthToken,
    payload: TransferRegisterPayload,
    till_service: ContextTillService,
    node_id: int,
):
    return await till_service.register.transfer_cash_register_admin(
        token=token,
        source_cashier_id=payload.source_cashier_id,
        target_cashier_id=payload.target_cashier_id,
        node_id=node_id,
    )


@router.put("/{register_id}")
async def update_register(
    register_id: int,
    register: NewCashRegister,
    token: CurrentAuthToken,
    till_service: ContextTillService,
    node_id: int,
):
    return await till_service.register.update_cash_register(
        token=token, register_id=register_id, register=register, node_id=node_id
    )


@router.delete("/{register_id}")
async def delete_register(register_id: int, token: CurrentAuthToken, till_service: ContextTillService, node_id: int):
    return await till_service.register.delete_cash_register(token=token, register_id=register_id, node_id=node_id)
