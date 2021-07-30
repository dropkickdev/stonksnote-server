from typing import Optional
from fastapi import Response, APIRouter, Depends, Cookie
from tortoise.query_utils import Prefetch

from app import ic, exceptions as x, logger as log
from app.auth import current_user, UserMod
from app.settings import settings as s
from trades.models import Equity, Owner
from tests.app.data import VERIFIED_EMAIL_DEMO
from trades import Trader



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
async def dev_tortoise(_: Response, user=Depends(current_user)):
    log.warning('foo')
    log.error('error')
    log.critical('critical')
    log.info('info')
    
    # FK Relationships
    query = Equity.get(ticker='COL')
    
    """
    PATTERN 1: ForeignKeyField
    USES:
    - You only want to get the data and not edit in any way
    - Shows getting data for nested and non-nested tables
    - owner__author__display and name contain field data not an object
    TOTAL QUERIES: 1
    """
    # torun = query.values('id', 'ticker', 'owner__author__display', owner='owner__name')  # partial
    # # fields
    # pat1 = await torun
    # ic(type(pat1), pat1)
    
    """
    PATTERN 2a: ForeignKeyField
    USES:
    - The owner attr contains an object w/ partial fields
    - Queries to add the owner attr with owner object to the a2 instance
    - The owner_id field must exist
    TOTAL QUERIES: 2
    """
    # torun = query.only('id', 'owner_id')    # partial fields
    # pat2a = await torun
    # the_owner = await pat2a.owner.only('id', 'name')   # +1q, partial fields
    # ic(type(pat2a), vars(pat2a), type(the_owner), vars(the_owner))
    
    """
    PATTERN 2b: ForeignKeyField
    USES:
    - The owner attr contains an object w/ all fields
    - Variation of PATTERN 2a using fetch_related
    - fetch_related is called by the QuerySet OBJECT. The owner_id field must exist.
    - Better to use prefetch_related instead
    TOTAL QUERIES: 2
    """
    # torun = query.only('id', 'owner_id')    # partial fields
    # pat2b = await torun
    # await pat2b.fetch_related('owner')  # +1q, all fields
    # the_owner = pat2b.owner
    # ic(type(pat2b), vars(pat2b), type(the_owner), vars(the_owner))
    
    """
    PATTERN 2c: ForeignKeyField
    USES:
    - The owner attr contains an object w/ all fields
    - Variation of PATTERN 2b using prefetch_related
    - prefetch_related is called by the QuerySet CLASS. The owner_id field must exist.
    TIP: If you're only reading, use values() or values_list() to produce a more efficient query
    TOTAL QUERIES: 2
    """
    # query = query.only('id', 'owner_id')        # 1q, partial fields
    # torun = query.prefetch_related('owner')     # +1q, all fields
    # # torun = query.only('id', 'owner_id').prefetch_related('owner__anotherfield')  # 3q, all fields
    # pat2c = await torun
    # the_owner = pat2c.owner
    # ic(type(pat2c), vars(pat2c), type(the_owner), vars(the_owner))
    
    """
    PATTERN 2d (Recommended): ForeignKeyField
    USES:
    - The owner attr contains an object w/ partial fields
    - Variation of PATTERN 2c using prefetch_related + Prefetch
    - Allows for partial fields. The owner_id field must exist.
    - Using only() in Prefetch only works because it's a FK not M2M
    TIP: If you're only reading, use values() or values_list() to produce a more efficient query
    TOTAL QUERIES: 2
    """
    # query = query.only('id', 'owner_id')    # 1q, partial fields
    # torun = query.prefetch_related(
    #     Prefetch('owner', Owner.all().only('id', 'name'), to_attr='owner'),       # +1q,
    #     # partial fields
    #     # Prefetch('field1', SomeModel.all()),      # +1q, all fields
    #     # Prefetch('field2', SomeTable.filter(foo=True).all()), # +1q, all fields, list
    #     # 'field3'   # +1q, all fields, might be list
    # )
    # pat2d = await torun
    # the_owner = pat2d.owner
    # ic(type(pat2d), vars(pat2d), type(the_owner), vars(the_owner))
    
    """
    -------------------------------------------------------------------------------------------
    VERDICT FK: For FKs use prefetch_related + Prefetch for partial fields. BUT if you only want
    to get the data and not manipulate the object or call methods then use PATTERN 1 instead
    NOTE:
    - prefetch_related: Used on the QuerySet (recommended)
    - fetch_related: Used on the QuerySet instance
    - Both work for FKs and M2Ms and do the same thing
    - For both make sure you called the field_id in the main query or it won't work
    - Nested Prefetch will work
    -------------------------------------------------------------------------------------------
    """
    

    # M2M Relationships
    query = UserMod.get(email=VERIFIED_EMAIL_DEMO)

    """
    PATTERN 3a: ManyToManyField
    USES:
    - The brokers.related_objects attr contains a list of objects w/ all fields
    - only() will not work with broker_list as it's now M2M not FK. broker_id isn't required since
      there is no physical M2M field in both tables.
    TOTAL QUERIES: 2+?
    """
    # torun = query.only('id', 'display')
    # pat3a = await torun
    # await pat3a.fetch_related('brokers')
    # broker_list = pat3a.brokers.related_objects
    # ic(type(pat3a), vars(pat3a), type(broker_list[0]), vars(broker_list[0]))
    
    """
    PATTERN 3b: ManyToManyField (Recommended)
    USES:
    - The broker_list attr contains a list of objects w/ all fields
    - Variation of PATTERN 3a using prefetch_related + Prefetch
    - only() will not work with broker_list as it's now M2M not FK. broker_id isn't required since
      there is no physical M2M field in both tables.
    TIP: If you want partial fields for broker_list you'll have to go through the traversing of
    tables including the intermediary table manually. For this query that means going through the
    UserMod->UserBrokers->Brokers tables (3q total at least).
    TOTAL QUERIES: 2+?
    """
    # torun = query.only('id', 'display').prefetch_related(
    #     Prefetch('brokers', Broker.all(), to_attr='broker_list'),       # +1q, all fields
    # )
    # pat3b = await torun
    # broker_list = pat3b.broker_list
    # ic(type(pat3b), vars(pat3b), type(broker_list[0]), vars(broker_list[0]))
    
    """
    PATTERN 3c: ManyToManyField
    USES:
    - The broker_list attr contains a list of objects w/ all fields
    - Variation of PATTERN 3b but trying to get the author from broker as well
    - To get author of a broker you'll need to use fetch_related on each broker
    NOTE: There must be a better way
    TOTAL QUERIES: 3+?
    """
    # # WRONG WAY
    # torun = query.only('id', 'display').prefetch_related(
    #     # Fail 1: Nested Prefetch -> doesn't work
    #     Prefetch('brokers', Broker.all().prefetch_related(
    #         Prefetch('author', UserMod.all(), to_attr='xxx')    # does nothing
    #     ), to_attr='broker_list'),       # +1q, all fields
    #
    #     # Fail 2: Separate Prefetch -> doesn't work
    #     # Prefetch('brokers', Broker.all(), to_attr='broker_list'),
    #     # Prefetch('brokers__author', UserMod.all(), to_attr='xxx')  # does nothing
    # )
    
    # # RIGHT WAY
    # torun = query.only('id', 'display').prefetch_related(
    #     Prefetch('brokers', Broker.all(), to_attr='broker_list')    # same as 3b
    # )
    # pat3c = await torun
    # broker_list = pat3c.broker_list
    # await broker_list[0].fetch_related('author')    # +1q, all fields, single broker
    # ic(
    #     type(pat3c), vars(pat3c),
    #     type(broker_list[0]), vars(broker_list[0]),     # author is UserMod (bec of fetch_related)
    #     type(broker_list[1]), vars(broker_list[1]),     # no author
    # )
    
    """
    -------------------------------------------------------------------------------------------
    VERDICT M2M: For M2Ms use prefetch_related + Prefetch and only() will not work since it's now
    an M2M field not a FK field.
    NOTE:
    - field_id is not needed anymore since in M2M there is no physical field attached to the table
    - To get a sub-relation (e.g. author_id) you'll need to use fetch_related on each one manually
    -------------------------------------------------------------------------------------------
    """

    # Traversing Relationships Manually
    query = UserMod.filter(deleted_at=None)
    
    """
    PATTERN 4: Traversing tables manually (FK and M2M)
    USES:
    - Use only if you need data from the rel'p table
    - only() not work since you're basically making FK calls
    TOTAL QUERIES: 4+?
    """
    # torun = query.only('id', 'display').prefetch_related(
    #     # user_id, broker_id needed for userbrokers, broker, respectively since it's a rel'p table
    #     Prefetch('userbrokers', UserBrokers.all().only('id', 'is_primary', 'user_id', 'broker_id')
    #      .prefetch_related(
    #         # author_id needed for author
    #         Prefetch('broker', Broker.all().only('id', 'name', 'author_id').prefetch_related(
    #             Prefetch('author', UserMod.all().only('id', 'display'))   # +1q, partial fields
    #         ))  # +1q, partial fields
    #     ), to_attr='xuserbrokers_list'),    # +1q, partial fields
    # )
    # pat4 = await torun
    # user1 = pat4[0]
    # xuserbrokers1 = user1.xuserbrokers_list[0]
    # broker1 = xuserbrokers1.broker
    # auth1 = broker1.author
    # xuserbrokers2 = user1.xuserbrokers_list[1]
    # broker2 = xuserbrokers2.broker
    # auth2 = broker2.author
    # ic(type(pat4), pat4,
    #    type(user1), vars(user1),
    #    type(xuserbrokers1), vars(xuserbrokers1),
    #    type(broker1), vars(broker1),
    #    type(auth1), vars(auth1),
    #    type(xuserbrokers2), vars(xuserbrokers2),
    #    type(broker2), vars(broker2),
    #    type(auth2), vars(auth2),
    # )
    
    """
    -------------------------------------------------------------------------------------------
    VERDICT Manual: Use manual traversion of rel'p tables if you need data from the rel'p table
    NOTE:
    - Similar to FKs except the rel'p table has 2 kinds of field_id not 1
    - only() works here since you're basically traversing tables using FKs
    -------------------------------------------------------------------------------------------
    """
    
    
    
    # log.info('info here')
    # log.warning('warning here')
    # log.error('error here')
 
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




@testrouter.get('/query')
async def query_test(_: Response,):
    # usermod = await UserMod.get(pk=user.id)
    usermod_list = await UserMod.all()
    usermod = usermod_list[3]
    trader = Trader(usermod)
    
    # broker = await Broker.get(pk=1).only('id')
    # await trader.add_broker(broker, wallet=34, meta=dict(foo='bar', age=34))
    #
    # broker2 = await Broker.get(pk=2).only('id')
    # await trader.add_broker(broker2, wallet=12, meta=dict(foo='this', age=96))
    #
    # broker3 = await Broker.get(pk=3).only('id')
    # await trader.add_broker(broker3)
    #
    # x = await UserBrokers.filter(meta__isnull=False).all()
    # ic(type(x), x)

    # x = await trader.has_brokers()
    # ic(type(x), x)
    # x = await trader.has_primary()
    # ic(type(x), x)
    # x = await trader.get_primary(True)
    # ic(type(x), x)
    # x = await trader.get_brokers(True)
    # ic(type(x), x)
    
    return True