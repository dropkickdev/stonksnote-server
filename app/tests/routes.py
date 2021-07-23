from typing import Optional
from fastapi import Response, APIRouter, Depends, Cookie
from tortoise.query_utils import Prefetch
from tortoise.transactions import in_transaction

from app import exceptions as x, ic
from app.auth import current_user, UserMod, Taxonomy
from app.settings import settings as s
from trades.models import Equity, Owner
from trades import get_foo
from app.fixtures.datastore import taxo_global
from app.tests.data import VERIFIED_EMAIL_DEMO


testrouter = APIRouter()

@testrouter.post('/dev_user_data')
async def dev_user_data(_: Response, user=Depends(current_user)):
    return user


@testrouter.get('/open')
async def random_route(_: Response):
    if s.DEBUG:
        raise x.NotFoundError('UserMod')


@testrouter.get('/readcookie')
def readcookie(refresh_token: Optional[str] = Cookie(None)):
    return refresh_token


@testrouter.get('/tortoise')
async def dev_user_data(_: Response, user=Depends(current_user)):
    
    # # 1: Same Table
    # a = await Equity.get(ticker='COL').only('id', 'ticker', 'status')                   # 1q
    # ic(type(a), a, vars(a))
    
    # -------------------------------------------------------------------------------------------
    
    # 2.1: FK Table
    query = Equity.get(ticker='COL')
    # b1 = await query.values('id', 'ticker', 'status', 'owner__author__display',
    #                         xyz='owner__name')    # 1q, only/values_list not allowed
    # the_sql = query.values('id', 'ticker', 'status', 'owner__author__display',
    #                        xyz='owner__name').sql()                                     # 1q
    # ic(type(b1), b1, the_sql)
    
    # # 2.2: 2q are run. See next for prefetch_related
    # b2 = await query.only('id', 'owner_id')
    # the_sql1 = query.only('id', 'owner_id').sql()
    # the_owner = await b2.owner.only('id', 'name')     # A query is needed
    # the_sql2 = b2.owner.only('id', 'name').sql()
    # ic(type(b2), vars(b2), type(the_owner), vars(the_owner), the_sql1, the_sql2)

    # # 2.3:  Using prefetch_related. There is a new 'owner' field which has the owner instance.
    # # The 'owner_id' field must be present.
    # b2 = await query.only('id', 'owner_id').prefetch_related('owner')           # All fields
    # the_sql1 = query.only('id', 'owner_id').prefetch_related('owner').sql()
    # the_owner = b2.owner                              # A query NOT needed
    # ic(type(b2), vars(b2), type(the_owner), vars(the_owner), the_sql1)
    
    # # 2.3a: Prefetch let's you select the fields you want. The 'owner_id' field must be present.
    # b3a = await query.only('id', 'owner_id').prefetch_related(
    #     Prefetch('owner', queryset=Owner.all().only('id', 'name'))      # Select fields
    # )
    # the_sql1 = query.only('id', 'owner_id').prefetch_related(
    #     Prefetch('owner', queryset=Owner.all().only('id', 'name'))
    # ).sql()
    # the_owner = b3a.owner
    # ic(type(b3a), vars(b3a), type(the_owner), vars(the_owner), the_sql1)
    
    # 2.3b: Variation of 2.3a with more FK fields
    b3b = await query.only('id', 'owner_id', 'author_id', 'exchange_id').prefetch_related(
        Prefetch('owner', queryset=Owner.filter(deleted_at=None).only('id', 'name')),
        Prefetch('author', queryset=UserMod.filter(deleted_at=None).only('id', 'display')),
        'exchange',                                                         # All fields
    )
    the_sql1 = query.only('id', 'owner_id', 'author_id', 'exchange_id').prefetch_related(
        Prefetch('owner', queryset=Owner.filter(deleted_at=None).only('id', 'name')),
        Prefetch('author', queryset=UserMod.filter(deleted_at=None).only('id', 'display')),
        'exchange',
    ).sql()
    the_owner = b3b.owner           # Select fields
    the_author = b3b.author         # Select fields
    the_exchange = b3b.exchange     # All fields
    ic(type(b3b), vars(b3b), vars(the_owner), vars(the_author), vars(the_exchange), the_sql1)
    
    
    # VERDICT: For FKs use 2.3 prefetch_related and Prefetch so you get the object. BUT if you only
    # want to display the data and not manipulate or call any methods then use 2.1 instead.
    
    # -------------------------------------------------------------------------------------------

    # M2M Table
    # b = await UserMod.get(email=VERIFIED_EMAIL_DEMO).only('id', 'email')
    
    # M2M Relationship Table
    
    # usermod_list = await UserMod.filter(is_verified=True)\
    #     .prefetch_related('brokers').only('id', 'email')
    # usermod_list = await UserMod.filter(is_verified=True).prefetch_related(
    #     Prefetch('brokers', queryset=Broker.all()),
    #     Prefetch('userbrokers', queryset=UserBrokers.all()),
    # ).only('id', 'email')
    # equity_list = await Equity.all().values_list('id', flat=True)

    # try:
    #     async with in_transaction():
    #         base = await Taxonomy.create(name='currency', is_global=True, author=usermod, tier='base')
    #         ll = []
    #         for i in taxo_global['currency']:
    #             ll.append(Taxonomy(name=i, is_global=True, author=usermod, tier='currency', parent=base))
    #         await Taxonomy.bulk_create(ll)
    #         return True
    # except Exception as e:
    #     ic(e)
    return True


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