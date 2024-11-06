from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from stustapay.core.http.auth_user import CurrentAuthToken
from stustapay.core.http.context import ContextTerminalService
from stustapay.core.schema.terminal import NewTerminal, Terminal

router = APIRouter(
    prefix="/terminals",
    tags=["terminals"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[Terminal])
async def list_terminals(
    token: CurrentAuthToken, response: Response, terminal_service: ContextTerminalService, node_id: int
):
    resp = await terminal_service.list_terminals(token=token, node_id=node_id)
    response.headers["Content-Range"] = str(len(resp))
    return resp


@router.post("", response_model=Terminal)
async def create_terminal(
    terminal: NewTerminal,
    token: CurrentAuthToken,
    terminal_service: ContextTerminalService,
    node_id: int,
):
    return await terminal_service.create_terminal(token=token, terminal=terminal, node_id=node_id)


@router.get("/{terminal_id}", response_model=Terminal)
async def get_terminal(
    terminal_id: int, token: CurrentAuthToken, terminal_service: ContextTerminalService, node_id: int
):
    terminal = await terminal_service.get_terminal(token=token, terminal_id=terminal_id, node_id=node_id)
    if terminal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return terminal


@router.put("/{terminal_id}", response_model=Terminal)
async def update_terminal(
    terminal_id: int,
    terminal: NewTerminal,
    token: CurrentAuthToken,
    terminal_service: ContextTerminalService,
    node_id: int,
):
    return await terminal_service.update_terminal(
        token=token, terminal_id=terminal_id, terminal=terminal, node_id=node_id
    )


@router.delete("/{terminal_id}")
async def delete_terminal(
    terminal_id: int, token: CurrentAuthToken, terminal_service: ContextTerminalService, node_id: int
):
    deleted = await terminal_service.delete_terminal(token=token, terminal_id=terminal_id, node_id=node_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/{terminal_id}/logout")
async def logout_terminal(
    terminal_id: int, token: CurrentAuthToken, terminal_service: ContextTerminalService, node_id: int
):
    logged_out = await terminal_service.logout_terminal_id(token=token, terminal_id=terminal_id, node_id=node_id)
    if not logged_out:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


class SwitchTillPayload(BaseModel):
    new_till_id: int


@router.post("/{terminal_id}/switch-till", tags=["tills", "terminals"])
async def switch_till(
    terminal_id: int,
    token: CurrentAuthToken,
    terminal_service: ContextTerminalService,
    node_id: int,
    payload: SwitchTillPayload,
):
    await terminal_service.switch_till(
        token=token, terminal_id=terminal_id, node_id=node_id, new_till_id=payload.new_till_id
    )
