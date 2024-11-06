from fastapi import APIRouter, HTTPException, Response, status

from stustapay.core.http.auth_user import CurrentAuthToken
from stustapay.core.http.context import ContextTillService
from stustapay.core.schema.till import CashRegisterStocking, NewCashRegisterStocking

router = APIRouter(
    prefix="/till_register_stockings",
    tags=["till-register-stockings"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[CashRegisterStocking])
async def list_register_stockings(
    token: CurrentAuthToken, response: Response, till_service: ContextTillService, node_id: int
):
    resp = await till_service.register.list_cash_register_stockings_admin(token=token, node_id=node_id)
    response.headers["Content-Range"] = str(len(resp))
    return resp


@router.post("", response_model=CashRegisterStocking)
async def create_register_stocking(
    stocking: NewCashRegisterStocking,
    token: CurrentAuthToken,
    till_service: ContextTillService,
    node_id: int,
):
    return await till_service.register.create_cash_register_stockings(token=token, stocking=stocking, node_id=node_id)


@router.post("/{stocking_id}", response_model=CashRegisterStocking)
async def update_register_stocking(
    stocking_id: int,
    stocking: NewCashRegisterStocking,
    token: CurrentAuthToken,
    till_service: ContextTillService,
    node_id: int,
):
    updated = await till_service.register.update_cash_register_stockings(
        token=token, stocking_id=stocking_id, stocking=stocking, node_id=node_id
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return updated


@router.delete("/{stocking_id}")
async def delete_register_stocking(
    stocking_id: int, token: CurrentAuthToken, till_service: ContextTillService, node_id: int
):
    deleted = await till_service.register.delete_cash_register_stockings(
        token=token, stocking_id=stocking_id, node_id=node_id
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
