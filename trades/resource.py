from typing import Optional

from pydantic import BaseModel, Field

from app.authentication.models.pydantic import UserDB


class CreateMark(BaseModel):
    symbol: str
    expires: Optional[str] = ''


class TradeData(BaseModel):
    page: int                  # page
    tab: str              # tab
    items: int                 # items
    sort: str       # sort
    direction: str             # direction
    equity: Optional[str] = None     # equity


# class CreateBrokerPy(BaseModel):
#     name: str = Field(..., le=191)
#     short: str = Field('', le=10)
#     brokerno: Optional[int] = None
#     rating: int = 0
#     email: str = Field('', le=191)
#     number: str = Field('', le=191)
#     url: str = Field('', le=191)
#     tel: str = Field('', le=191)
#     country: str = Field('', min_length=2, max_length=2)
#     logo: str = Field('', le=255)
#     buyfees: float = 0
#     sellfees: float = 0
#     is_active: bool = True


async def trades_request(
    p: int = 1, t: str = 'all', i: int = 20,
    s: str = 'transacted_at', d: str = 'desc', e: Optional[str] = None
):
    return dict(page=p, tab=t, items=i, sort=s, direction=d, equity=e)
