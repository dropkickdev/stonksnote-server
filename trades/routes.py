from fastapi import APIRouter, Response, Depends
from tortoise.exceptions import BaseORMException
from redis.exceptions import RedisError

from app import ic, exceptions as x
from app.auth import current_user
from .validation import CreateMark
from .models import Mark


traderoutes = APIRouter()


@traderoutes.post('/marks/add')
async def add_mark(res: Response, mark: CreateMark, user=Depends(current_user)):
    if not await user.has_perm('mark.create'):
        raise x.PermissionDenied()
    try:
        if markmod := await Mark.create(**mark.dict(), author=user):
            res.status_code = 201
            return markmod.to_dict()
    except (BaseORMException, RedisError):
        raise x.ServiceError()
    except Exception:
        raise x.AppError()
