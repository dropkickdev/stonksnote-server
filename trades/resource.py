from typing import Optional

from pydantic import BaseModel

from app.authentication.models.pydantic import UserDB


class CreateMark(BaseModel):
    symbol: str
    expires: Optional[str] = ''


class TradeData(BaseModel):
    user: UserDB
    p: int = 1                  # page
    t: str = 'all'              # tab
    i: int = 10                 # items
    s: str = 'created_at'       # sort
    d: str = 'desc'             # direction
    e: Optional[str] = None     # equity


async def trades_request(
    p: int = 1, t: str = 'all', i: int = 20,
    s: str = 'created_at', d: str = 'desc', e: Optional[str] = None
):
    return dict(page=p, tab=t, items=i, sort=s, dir=d, equity=e)