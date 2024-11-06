from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from stustapay.core.http.auth_user import CurrentAuthToken
from stustapay.core.http.context import ContextTillService
from stustapay.core.schema.till import NewTill, Till

router = APIRouter(
    prefix="/tills",
    tags=["tills"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[Till])
async def list_tills(token: CurrentAuthToken, response: Response, till_service: ContextTillService, node_id: int):
    resp = await till_service.list_tills(token=token, node_id=node_id)
    response.headers["Content-Range"] = str(len(resp))
    return resp


@router.post("", response_model=Till)
async def create_till(till: NewTill, token: CurrentAuthToken, till_service: ContextTillService, node_id: int):
    return await till_service.create_till(token=token, till=till, node_id=node_id)


@router.get("/{till_id}", response_model=Till)
async def get_till(till_id: int, token: CurrentAuthToken, till_service: ContextTillService, node_id: int):
    till = await till_service.get_till(token=token, till_id=till_id, node_id=node_id)
    if till is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return till


@router.put("/{till_id}", response_model=Till)
async def update_till(
    till_id: int,
    till: NewTill,
    token: CurrentAuthToken,
    till_service: ContextTillService,
    node_id: int,
):
    updated_till = await till_service.update_till(token=token, till_id=till_id, till=till, node_id=node_id)
    if updated_till is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return updated_till


@router.post("/{till_id}/force-logout-user")
async def force_logout_user(till_id: int, token: CurrentAuthToken, till_service: ContextTillService, node_id: int):
    await till_service.force_logout_user(token=token, till_id=till_id, node_id=node_id)


@router.post("/{till_id}/remove-from-terminal", tags=["tills", "terminals"])
async def remove_from_terminal(till_id: int, token: CurrentAuthToken, till_service: ContextTillService, node_id: int):
    await till_service.remove_from_terminal(token=token, till_id=till_id, node_id=node_id)


class SwitchTerminalPayload(BaseModel):
    new_terminal_id: int


@router.post("/{till_id}/switch-terminal", tags=["tills", "terminals"])
async def switch_terminal(
    till_id: int,
    token: CurrentAuthToken,
    till_service: ContextTillService,
    node_id: int,
    payload: SwitchTerminalPayload,
):
    await till_service.switch_terminal(
        token=token, till_id=till_id, node_id=node_id, new_terminal_id=payload.new_terminal_id
    )


@router.delete("/{till_id}")
async def delete_till(till_id: int, token: CurrentAuthToken, till_service: ContextTillService, node_id: int):
    deleted = await till_service.delete_till(token=token, till_id=till_id, node_id=node_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
