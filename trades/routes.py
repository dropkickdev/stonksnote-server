from fastapi import APIRouter, Response, Depends
from tortoise.exceptions import OperationalError
from redis.exceptions import RedisError

from app import ic, exceptions as x
from app.auth import current_user
from .resource import CreateMark, TradeData, trades_request
from .models import Mark, Trade



traderoutes = APIRouter()

@traderoutes.post('/marks/add')
async def add_mark(res: Response, mark: CreateMark, user=Depends(current_user)):
    if not await user.has_perm('mark.create'):
        raise x.PermissionDenied()
    try:
        if markmod := await Mark.create(**mark.dict(), author=user):
            res.status_code = 201
            return markmod.to_dict()
    except (OperationalError, RedisError):
        raise x.ServiceError()
    except Exception:
        raise x.AppError()

@traderoutes.get('')
async def get_trades(_: Response, spec: dict = Depends(trades_request), user=Depends(current_user)):
    if not await user.has_perm('trade.read'):
        raise x.PermissionDenied()
    try:
        spec = TradeData(**spec)
        trades = await Trade.get_trades(spec, user=user)
        if trades:
            # TODO: Do something with this
            pass
        return trades
    except (OperationalError, RedisError):
        raise x.ServiceError()
    except Exception:
        raise x.AppError()
    
    