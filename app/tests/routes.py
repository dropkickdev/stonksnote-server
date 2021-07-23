from typing import Optional
from fastapi import Response, APIRouter, Depends, Cookie
from tortoise.query_utils import Prefetch
from tortoise.transactions import in_transaction

from app import exceptions as x, ic
from app.auth import current_user, UserMod, Taxonomy, Permission
from app.settings import settings as s
from trades.models import Equity, Owner, Broker, UserBrokers
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
    # the_owner = await b2.owner.only('id', 'name')     # Addt'l query
    # the_sql2 = b2.owner.only('id', 'name').sql()
    # ic(type(b2), vars(b2), type(the_owner), vars(the_owner), the_sql1, the_sql2)

    # # 2.3:  Using prefetch_related. There is a new 'owner' field which has the owner instance.
    # # The 'owner_id' field must be present.
    # b2 = await query.only('id', 'owner_id').prefetch_related('owner')           # All fields
    # the_sql1 = query.only('id', 'owner_id').prefetch_related('owner').sql()
    # the_owner = b2.owner                              # A query NOT needed
    # ic(type(b2), vars(b2), type(the_owner), vars(the_owner), the_sql1)
    
    # # 2.3a: Prefetch let's you select the fields you want. The 'owner_id' field must be present.
    # x = query.only('id', 'owner_id').prefetch_related(
    #     Prefetch('owner', queryset=Owner.all().only('id', 'name'))      # Select fields
    # )
    # b3a = await x
    # the_sql1 = x.sql()
    # the_owner = b3a.owner
    # ic(type(b3a), vars(b3a), type(the_owner), vars(the_owner), the_sql1)
    
    # # 2.3b: Variation of 2.3a with more FK fields
    # b3b = await query.only('id', 'owner_id', 'author_id', 'exchange_id').prefetch_related(
    #     Prefetch('owner', queryset=Owner.filter(deleted_at=None).only('id', 'name')),
    #     Prefetch('author', queryset=UserMod.filter(deleted_at=None).only('id', 'display')),
    #     'exchange',                                                         # All fields
    # )
    # the_sql1 = query.only('id', 'owner_id', 'author_id', 'exchange_id').prefetch_related(
    #     Prefetch('owner', queryset=Owner.filter(deleted_at=None).only('id', 'name')),
    #     Prefetch('author', queryset=UserMod.filter(deleted_at=None).only('id', 'display')),
    #     'exchange',
    # ).sql()
    # the_owner = b3b.owner           # Select fields
    # the_author = b3b.author         # Select fields
    # the_exchange = b3b.exchange     # All fields
    # ic(type(b3b), vars(b3b), vars(the_owner), vars(the_author), vars(the_exchange), the_sql1)

    # # 2.3c: Variation of 2.3a. Uses fetch_related to add a field (maybe you thought you didn't
    # # need it). The field_id of the related table must already be there to work.
    # x = query.only('id', 'owner_id', 'author_id').prefetch_related(
    #     Prefetch('owner', queryset=Owner.filter(deleted_at=None).only('id', 'name'), to_attr='xxx'),
    #     # Prefetch('author', queryset=UserMod.filter(deleted_at=None).only('id', 'display')),
    #     # 'exchange',  # All fields
    # )
    # b3c = await x
    # the_sql1 = x.sql()
    # the_owner = b3c.owner  # Select fields
    # ic(vars(b3c))
    # await b3c.fetch_related('author')       # Addt'l query
    # the_author = b3c.author  # Select fields
    # ic(vars(b3c), vars(the_owner), vars(the_author), the_sql1)
    
    
    # VERDICT: For FKs use 2.3 prefetch_related and Prefetch so you get the object. BUT if you only
    # want to display the data and not manipulate or call any methods then use 2.1 instead.
    # NOTE:
    #   - prefetch_related: For the INITIAL QUERY. Includes the object in the final result.
    #   - fetch_related: For the OBJECT from the initial query. Add the object to the final result.
    #     Using this will result in a +1 query because you're appending a field that was missing.
    #   - Both work for FKs and M2Ms
    #   - Either way, prefetch_related and fetch_related must have the field_id or it won't work.
    
    # -------------------------------------------------------------------------------------------

    # M2M Table
    # Get for only one entry
    query = UserMod.get(email=VERIFIED_EMAIL_DEMO)
    query_fiter = UserMod.filter(deleted_at=None)
    
    # # Wrong way: You need to bake a 2nd query to get the m2m
    # # Also prefetch_related is irrelevant here
    # c1 = await query.only('id', 'display').prefetch_related('brokers')      # 1q
    # broker_list = await c1.brokers                                          # +1q
    # ic(type(c1), vars(c1), broker_list)
    
    # # Right way: Using Prefetch with to_attr
    # # For a single item
    # x = query.only('id', 'display').prefetch_related(
    #     Prefetch('brokers', Broker.all(), to_attr='broker_list'),       # only() does nothing
    #     Prefetch('permissions', Permission.all(), to_attr='perm_list'), # only() does nothing
    # )
    # c2 = await x
    # the_sql = x.sql()
    # ic(type(c2), vars(c2), vars(c2.broker_list[0]), the_sql)

    # # Nested Prefetch doesn't work. You'll have to run it manuall after the first Prefetch.
    # x = query.only('id', 'display').prefetch_related(
    #     Prefetch('brokers', Broker.all().prefetch_related(
    #         Prefetch('author', UserMod.all(), to_attr='xxx')    # Does nothing
    #     ), to_attr='broker_list'),
    # )
    # c3a = await x
    # z = await c3a.broker_list[0].author.only('id', 'display')
    # the_sql = x.sql()
    # ic(type(c3a), vars(c3a), vars(c3a.broker_list[0]), type(c3a.broker_list[0].author), vars(z),
    #    the_sql)

    # # Alternative to c3a
    # x = query.only('id', 'display').prefetch_related(
    #     Prefetch('brokers', Broker.all(), to_attr='broker_list'),
    # )
    # c3b = await x
    # await c3b.broker_list[0].fetch_related('author')
    # broker1 = c3b.broker_list[0].author     # UserMod, bec you used fetch_related, +1q
    # broker2 = c3b.broker_list[1].author     # QuerySet
    # broker3 = c3b.broker_list[2].author     # QuerySet
    # the_sql = x.sql()
    # ic(type(c3b), vars(c3b), vars(c3b.broker_list[0]),
    #    type(broker1), type(broker2), type(broker3),
    #    vars(broker1),
    #    the_sql)

    # For multiple items + Relationship table + Nested Prefetch
    # Same thing except a list is returned instead of a single object
    # Remember, only() works if you're NOT using the M2M field instead traversing the tables
    # manuolly
    x = query_fiter.only('id', 'display').prefetch_related(
        # only() no use here (brokers is M2M)
        Prefetch('brokers', Broker.all().only('id', 'name'), to_attr='broker_list'),
        # only() works here as noted above
        Prefetch('userbrokers', UserBrokers.all().only('id', 'is_primary', 'user_id', 'broker_id')
             .prefetch_related(
                Prefetch('broker', Broker.all().only('id', 'name', 'author_id').prefetch_related(
                    Prefetch('author', UserMod.all().only('id', 'display'), to_attr='zzz')
                ), to_attr='yyy')
            ), to_attr='xxx'),
    )
    c3 = await x
    the_sql1 = x.sql()
    broker1 = c3[0].broker_list[0]
    userbrokers1 = c3[0].xxx[0]
    boo1 = userbrokers1.yyy
    auth1 = boo1.author
    broker2 = c3[0].broker_list[1]
    userbrokers2 = c3[0].xxx[1]
    boo2 = userbrokers2.yyy
    auth2 = boo2.author
    ic(type(c3), c3, vars(c3[0]), type(c3[0]),
       type(broker1), vars(broker1), type(userbrokers1), vars(userbrokers1),
       type(boo1), vars(boo1), type(auth1), vars(auth1),
       type(broker2), vars(broker2),
       type(userbrokers2), vars(userbrokers2),
       type(boo2), vars(boo2), type(auth2), vars(auth2),
       the_sql1,
    )
    
    # VERDICT:
    #   - Using the M2M fields do not allow the use of only()
    #   - Alternatively, traverse the tables intead of using the shortcut M2M fields and only()
    #   works
    #   - Nested Prefetch works when traversing tnhe tables manually. Won't work if you're using
    #   the M2M fields
    
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