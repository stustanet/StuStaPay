from typing import Optional

from pydantic import BaseModel

from stustapay.core.schema.till import Till
from stustapay.core.schema.user import Privilege


class Terminal(BaseModel):
    till: Till


class TerminalSecrets(BaseModel):
    sumup_affiliate_key: str


class TerminalButton(BaseModel):
    id: int
    name: str
    price: Optional[float]
    default_price: Optional[float] = None  # for variably priced products a default price might be interesting?
    price_in_vouchers: Optional[int] = None
    price_per_voucher: Optional[float] = None
    is_returnable: bool
    fixed_price: bool


class TerminalConfig(BaseModel):
    id: int
    name: str
    description: Optional[str]
    user_privileges: Optional[list[Privilege]]
    allow_top_up: bool
    allow_cash_out: bool
    buttons: Optional[list[TerminalButton]]
    secrets: Optional[TerminalSecrets]


class TerminalRegistrationSuccess(BaseModel):
    till: Till
    token: str
