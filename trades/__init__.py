from decimal import Decimal
from typing import Optional, Tuple, Union, List
from tortoise.query_utils import Prefetch, Q
from tortoise.queryset import QuerySet, QuerySetSingle
from tortoise.transactions import in_transaction
from pydantic import UUID4, BaseModel, validate_arguments
from limeutils import listify

from .models import *
from .choices import *
from .resource import *
from app import ic, exceptions as x
from app.settings import settings as s
from app.auth import UserMod




class Trader:
    usermod: UserMod
    broker: Broker
    broker_list: list
    
    def __init__(self, usermod: UserMod):
        self.usermod = usermod
        self.currency = self.usermod.currency
        
        # self.broker_list = brokers and listify(brokers) or []       # Not saved to db yet
        # self.broker = self.broker_list and self.broker_list[0] or None
        #
        # ll = []
        # for i in self.broker_list:
        #     is_primary = primary and primary.id == i.id or False        # noqa
        #     ll.append(UserBrokers(user=self.usermod, broker=i, is_primary=is_primary,
        #                           wallet=wallet))
        # UserBrokers.bulk_create(ll)

    async def has_primary(self):
        return await UserBrokers.exists(user=self.usermod, is_primary=True)

    async def has_brokers(self):
        return await UserBrokers.exists(user=self.usermod)

    # TESTME: Untested ready
    async def get_primary(self, *, as_instance: bool = False):
        if not await self.has_primary():
            return
        
        query = Broker.get_or_none(userbrokers__user=self.usermod, userbrokers__is_primary=True)
        return await self._query_userbroker(query, as_instance)

    # TESTME: Untested ready
    async def get_broker(self, id: int, *, as_instance: bool = False):
        if not await self.has_brokers():
            return
        
        query = Broker.get_or_none(userbrokers__user=self.usermod, userbrokers__broker_id=id)
        return await self._query_userbroker(query, as_instance)


    @staticmethod
    async def _query_userbroker(query: QuerySetSingle, as_instance: bool):
        fields = ['id', 'name', 'short', 'brokerno', 'rating', 'logo', 'currency', 'buyfees',
                  'sellfees']
        
        if not as_instance:
            query = query.values(*fields, is_primary='userbrokers__is_primary',
                                 wallet='userbrokers__wallet')
            # Returns a list even if you're using get() since userbrokers is M2M
            broker = await query
            return broker
    
        query = query.prefetch_related(
            Prefetch('userbrokers', UserBrokers.all() \
                     .only('id', 'broker_id', 'is_primary', 'wallet'), to_attr='ubs')
        )
        broker = await query.only(*fields)
    
        # Cleanup
        if broker:
            broker.is_primary = broker.ubs and broker.ubs[0].is_primary or None
            broker.wallet = broker.ubs and broker.ubs[0].wallet or None
            broker.ubs = broker.ubs and broker.ubs[0] or None
            broker.buyfees = float(broker.buyfees)
            broker.sellfees = float(broker.sellfees)
            broker.ubs.wallet = float(broker.ubs.wallet)
    
        return broker
        

    async def get_brokers(self, as_instance: bool = False) -> List[Union[UserBrokers, dict]]:
        """
        Get the brokers of a user
        :param as_instance: Return dict or objects
        :return:            list of UserBrokers/dict
        """
        fields = ('id', 'broker_id', 'is_primary', 'wallet', 'user_id')
        if not await self.has_brokers():
            return []
        
        if not as_instance:
            return await UserBrokers.filter(user=self.usermod) \
                .values(*fields,
                        name='broker__name',
                        short='broker__short',
                        brokerno='broker__brokerno',
                        rating='broker__rating',
                        logo='broker__logo',
                        currency='broker__currency')

        # When getting brokers always get UserBrokers not Broker
        query = UserBrokers.filter(user=self.usermod)
        query = query.prefetch_related(
            Prefetch('broker',
                     Broker.all().only('id', 'name', 'short', 'brokerno', 'rating', 'logo', 'currency'),
                     to_attr='broker'),
        ).only(*fields)
        broker_list = await query

        # Cleanup
        for idx, i in enumerate(broker_list):
            broker_list[idx].name = i.broker.name                                           # noqa
            broker_list[idx].short = i.broker.short                                         # noqa
            broker_list[idx].brokerno = i.broker.brokerno                                   # noqa
            broker_list[idx].rating = i.broker.rating                                       # noqa
            broker_list[idx].logo = i.broker.logo                                           # noqa
            broker_list[idx].currency = i.broker.currency                                   # noqa
            broker_list[idx].wallet = float(i.wallet)                                       # noqa
        return broker_list

    
    # TESTME: Untested: ready
    async def set_primary(self, id: int) -> None:
        """
        Set a new primary broker for this user
        :param id:  Broker id
        :return:    None
        """
        async with in_transaction():
            if ub := await UserBrokers.filter(user=self.usermod).only('id', 'broker_id', 'is_primary'):
                for i in ub:
                    if i.broker_id == id:                                       # noqa
                        i.is_primary = True
                        await i.save(update_fields=['is_primary'])
                    elif i.is_primary:
                        i.is_primary = False
                        await i.save(update_fields=['is_primary'])


    # TESTME: Untested: ready
    async def unset_primary(self) -> None:
        """
        Unset the primary broker
        :return:    None
        """
        if ub := await UserBrokers.get_or_none(user=self.usermod, is_primary=True).only('id', 'is_primary'):
            ub.is_primary = False
            await ub.save(update_fields=['is_primary'])
    
    
    async def add_broker(self, broker: Union[Broker, List[Broker]], *, wallet: float = 0,
                         is_primary: bool = False, meta: Optional[dict] = None) -> None:
        """
        Assign brokers to the user
        :param broker:      Broker to add
        :param wallet:      Starting wallet amount. Valid only if single Broker.
        :param is_primary:  Is this the primary? Valid only if single Broker.
        :param meta:        Meta data. Valid only if single Broker.
        :return:            None
        """
        broker_list = listify(broker)
        
        if isinstance(broker, Broker):
            if wallet or is_primary or meta:
                if not await UserBrokers.exists(user=self.usermod, broker=broker):
                    await UserBrokers.create(user=self.usermod, broker=broker, meta=meta,
                                             is_primary=is_primary, wallet=wallet)
                    return
        
        await self.usermod.brokers.add(*broker_list)
    
    
    async def remove_broker(self, broker: Union[Broker, List[Broker]]) -> None:
        """
        Unassign a Broker from the UserMod
        :param broker:     Broker
        :return:            None
        """
        if not broker:
            return
        broker = listify(broker)
        await self.usermod.brokers.remove(*broker)
    
    
    # TESTME: Untested ready
    async def has_stash(self, equity: Equity):
        return await Stash.exists(user=self.usermod, equity=equity)
    
    
    # TESTME: Untested: ready
    async def get_stash(self, equity: Equity, *, as_instance: bool = False):
        fields = ('id', 'shares', 'is_resolved', 'updated_at')
        query = Stash.get_or_none(user=self.usermod, equity=equity)
        if as_instance:
            return await query.prefetch_related(
                Prefetch('equity', Equity.all().only('id', 'ticker', 'category', 'status'),
                         to_attr='equity')
            ).only(*fields, 'equity_id')
        return (await query.values(*fields, equity='equity__ticker', equity_id='equity__id',
                                  category='equity__category', status='equity__status'))[0]
    
    
    # TESTME: Untested ready
    async def buy_stock(self, equity: Equity, shares: int, price: float,
                        broker: Optional[Broker] = None, currency: Optional[str] = None):
        if not broker:
            if await self.has_primary():
                broker = await self.get_primary(as_instance=True)
            else:
                if await self.has_brokers():
                    ub = await UserBrokers.filter(user=self.usermod).first().values('id')
                    broker = await self.get_broker(ub['id'], as_instance=True)
                    await self.set_primary(broker.id)
                else:
                    raise x.MissingBrokersError()

        # ic(vars(broker))
        gross = price * shares
        fees = gross * broker.buyfees
        total = gross + fees
        currency = currency or broker.currency

        async with in_transaction():
            stash = await self.get_stash(equity, as_instance=True)
            if not stash:
                stash = await Stash.create(user=self.usermod, equity=equity, author=self.usermod)
            
            await stash.incr_stash(shares)
            await broker.ubs.decr_wallet(total)
            await Trade.create(stash=stash, broker=broker, action=1, author=self.usermod,
                               price=price, shares=shares, gross=gross, fees=fees, total=total,
                               currency=currency)
            return gross, fees, total, currency

    # TESTME: Untested
    async def sell_stock(self, equity: Equity, shares: int, price: float,
                        broker: Optional[Broker] = None, currency: Optional[str] = None):
        if not broker:
            if await self.has_primary():
                broker = await self.get_primary(as_instance=True)
            else:
                if await self.has_brokers():
                    ub = await UserBrokers.filter(user=self.usermod).first().values('id')
                    broker = await self.get_broker(ub['id'], as_instance=True)
                    await self.set_primary(broker.id)
                else:
                    raise x.MissingBrokersError()

        # ic(vars(broker))
        gross = price * shares
        fees = gross * broker.sellfees
        total = gross - fees
        currency = currency or broker.currency

        async with in_transaction():
            stash = await self.get_stash(equity, as_instance=True)
            if not stash:
                stash = await Stash.create(user=self.usermod, equity=equity, author=self.usermod)
            # ic(type(stash), vars(stash))
            
            await stash.decr_stash(shares)
            await broker.ubs.incr_wallet(total)
            await Trade.create(stash=stash, broker=broker, action=2, author=self.usermod,
                               price=price, shares=shares, gross=gross, fees=fees, total=total,
                               currency=currency)
            return gross, fees, total, currency
    
    
    # # TODO: Update this since the Stash table was added
    # # TESTME: Untested
    # async def get_trades(self, spec: TradeData, start: Optional[datetime] = None,
    #                      end: Optional[datetime] = None) -> List[dict]:
    #     """
    #     Get list of trades for a specified user
    #     :param spec:    TradeData token from the route
    #     :param start:   Starting date
    #     :param end:     Ending date
    #     :return:        list
    #     """
    #     try:
    #         countquery = self.filter(author_id=user.id)
    #         tradequery = self.filter(author_id=user.id)
    #
    #         if spec.equity:
    #             tradequery = tradequery.filter(equity__ticker__icontains=spec.equity)
    #             countquery = countquery.filter(equity__ticker__icontains=spec.equity)
    #         if start:
    #             tradequery = tradequery.filter(created_at__gte=start)
    #             countquery = countquery.filter(created_at__gte=start)
    #         if end:
    #             tradequery = tradequery.filter(created_at__lte=end)
    #             countquery = countquery.filter(created_at__lte=end)
    #
    #         count = await countquery.count()
    #         orderby, offset, limit = setup_pagination(**spec.dict(), total=count)
    #         tradequery = tradequery.order_by(orderby).limit(limit).offset(offset)
    #         tradequery = tradequery.values(
    #             'id', 'shares', 'action', 'price', 'created_at', 'author_id',
    #             'currency', ticker='equity__ticker',
    #         )
    #         trades = await tradequery
    #
    #         clean_trades = self.trades_cleaner(trades)
    #         return clean_trades
    #     except Exception as e:
    #         ic(e)

    # # TODO: Update this since the Stash table was added
    # # TESTME: Untested
    # @classmethod
    # def trades_cleaner(self, trades: List[dict], buyfees: Optional[float] = None,
    #                    sellfees: Optional[float] = None) -> List[dict]:
    #     """
    #     Cleans data to be used by the react front-end
    #     :param trades:      Result of a DB query in dict format
    #     :param buyfees:     If there any any fees to include from broker
    #     :param sellfees:    If there any any fees to include from broker
    #     :return:            list
    #     """
    #     ll = []
    #     for i in trades:
    #         del i['author_id']
    #         i['minsell'] = 'n/a'
    #         i['gainloss'] = 'n/a'
    #
    #         i['total'] = i.get('shares') * i.get('price')
    #         if buyfees:
    #             i['total'] = i['total'] * buyfees
    #         elif sellfees:
    #             i['total'] = i['total'] * sellfees
    #
    #         # TODO: Convert to user's local time via offset
    #         created_at = i.get('created_at').strftime('%Y-%m-%d')
    #         i['bought'] = created_at if i.get('action') == 'buy' else ''
    #         i['sold'] = created_at if i.get('action') == 'sell' else ''
    #
    #         ll.append(i)
    #     return ll

    # async def preaction_setup(self):
    #     # Gather the brokers
    #     userbrokers = await self.usermod.brokers.all()

    
    async def get_ticketx(self, ticket: str):
        return
    


def get_foo():
    return Equity.get(pk=1).prefetch_related(
        Prefetch('owner', queryset=Owner.all().only('id', 'name'))
    ).only('id', 'ticker', 'owner_id')

