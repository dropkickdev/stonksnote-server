from typing import Optional

from pydantic import BaseModel

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


async def trades_request(
    p: int = 1, t: str = 'all', i: int = 20,
    s: str = 'created_at', d: str = 'desc', e: Optional[str] = None
):
    return dict(page=p, tab=t, items=i, sort=s, direction=d, equity=e)