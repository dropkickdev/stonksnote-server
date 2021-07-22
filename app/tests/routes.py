from typing import Optional
from fastapi import Response, APIRouter, Depends, Cookie
from tortoise.query_utils import Prefetch

from app import exceptions as x, ic
from app.auth import current_user, UserMod
from app.settings import settings as s
from trades.models import Equity, Owner
from trades import get_foo


testrouter = APIRouter()

@testrouter.post('/dev_user_data')
async def dev_user_data(_: Response, user=Depends(current_user)):
    # x = await
    # try:
    #     usermod = await UserMod.get(id=user.id).only('id')
    #     ic(await usermod.brokers.all())
    # except Exception as e:
    #     ic(e)
    return user


@testrouter.get('/open')
async def random_route(_: Response):
    if s.DEBUG:
        raise x.NotFoundError('UserMod')


@testrouter.get('/readcookie')
def readcookie(refresh_token: Optional[str] = Cookie(None)):
    return refresh_token


# @authrouter.post('/username')
# async def check_username(inst: UniqueFieldsRegistration):
#     exists = await UserMod.filter(username=inst.username).exists()
#     return dict(exists=exists)
#
#
# @authrouter.post('/email')
# async def check_username(inst: UniqueFieldsRegistration):
#     exists = await UserMod.filter(email=inst.email).exists()
#     return dict(exists=exists)