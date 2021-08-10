import pytz
from datetime import datetime
from typing import Optional, Tuple, Union, List
from tortoise.queryset import QuerySet, QuerySetSingle, Prefetch
from tortoise.transactions import in_transaction
from limeutils import listify

from .models import *
from .choices import *
from .resource import *
from app import ic, exceptions as x
from app.auth import UserMod



broker_fields = ('id', 'name', 'short', 'brokerno', 'rating', 'logo', 'currency', 'buyfees', 'sellfees')
userbroker_fields = ('id', 'user_id', 'broker_id', 'wallet', 'is_primary', 'status')
stash_fields = ('id', 'user_id', 'userbroker_id', 'shares', 'is_resolved')
mark_fields = ('id', 'equity_id', 'is_active')

class Trader:
    usermod: UserMod
    broker: Broker
    broker_list: list
    
    def __init__(self, usermod: UserMod):
        self.usermod = usermod
        self.currency = self.usermod.currency

    @staticmethod
    def cleanup_ublist(ublist: Union[UserBrokers, List[UserBrokers]]) -> List[UserBrokers]:
        """
        Cleans up the data for a UserBrokers instance
        :param ublist:  List of UserBrokers
        :return:        List[UserBrokers]
        """
        ublist = listify(ublist)
        for idx, i in enumerate(ublist):
            ublist[idx].name = i.broker.name                                       # noqa
            ublist[idx].short = i.broker.short                                     # noqa
            ublist[idx].brokerno = i.broker.brokerno                               # noqa
            ublist[idx].rating = i.broker.rating                                   # noqa
            ublist[idx].logo = i.broker.logo                                       # noqa
            ublist[idx].currency = i.broker.currency                               # noqa
            ublist[idx].buyfees = float(i.broker.buyfees)                          # noqa
            ublist[idx].sellfees = float(i.broker.sellfees)                        # noqa
            ublist[idx].wallet = float(i.wallet)                                   # noqa
        return ublist

    async def has_primary(self) -> bool:
        """
        Checks if the trader has a primary UserBroker
        :return:    bool
        """
        return await UserBrokers.exists(user=self.usermod, is_primary=True)

    async def has_userbrokers(self) -> bool:
        """
        Checks if the trader has any UserBrokers
        :return:    bool
        """
        return await UserBrokers.exists(user=self.usermod)

    async def get_primary(self, *, as_dict: bool = False) -> Union[UserBrokers, dict, None]:
        """
        Return an the primary UserBrokers
        :param as_dict: Return dict or instance
        :return:        Union[UserBrokers, dict, None]
        """
        if not await self.has_primary():
            return
        query = UserBrokers.get_or_none(user=self.usermod, is_primary=True)
        userbroker = (await self._query_userbroker(query, as_dict=as_dict))[0]
        return userbroker

    async def find_userbroker(self, broker_id: int, *, as_dict: bool = False) -> Union[UserBrokers, dict, None]:
        """
        Return an instance of UserBrokers based on a Broker id
        :param broker_id:   Broker id
        :param as_dict:     Return dict or instance
        :return:            Union[UserBrokers, dict, None]
        """
        if not await self.has_userbrokers():
            return
        query = UserBrokers.get_or_none(user=self.usermod, broker_id=broker_id)
        userbroker = (await self._query_userbroker(query, as_dict=as_dict))[0]
        return userbroker

    async def get_userbrokers(self, *, as_dict: bool = False) -> Union[list, List[Union[UserBrokers, dict]]]:
        """
        Get the brokers of a user
        :param as_dict: Return dict or instance
        :return:        Union[list, List[Union[UserBrokers, dict]]]
        """
        if not await self.has_userbrokers():
            return []
    
        query = UserBrokers.filter(user=self.usermod)
        return await self._query_userbroker(query, as_dict=as_dict)

    async def _query_userbroker(self, query: QuerySetSingle, *, as_dict: bool) -> List[Union[UserBrokers, dict]]:
        """
        Return a list of UserBrokers in instance or dict format
        :param query:       Starting query
        :param as_dict:     Return dict or instance
        :return:            List[Union[UserBrokers, dict]]
        """
        if as_dict:
            dict_fields = {i: f'broker__{i}' for i in broker_fields if i != 'id'}
            return await query.values(*userbroker_fields, **dict_fields)
    
        query = query.prefetch_related(
            Prefetch('broker', Broker.all().only(*broker_fields), to_attr='broker'),
        ).only(*userbroker_fields)
        ublist = await query
    
        # Cleanup and return
        return self.cleanup_ublist(ublist)

    async def get_userbroker(self, broker_id: Optional[int] = None) -> UserBrokers:
        """
        Get the assigned UserBroker based on a Broker id. If no Broker id is supplied then the
        primary UserBrokers is returned. If there is no assigned primary (but user has
        UserBrokers) the first UserBrokers wil be made into the primary and returned.
        :param broker_id:   Broker id
        :return:            UserBrokers instance
        """
        if broker_id:
            return await self.find_userbroker(broker_id)                                    # noqa
        if await self.has_primary():
            return await self.get_primary()                                                 # noqa
        if await self.has_userbrokers():
            userbroker = (await self.get_userbrokers())[0]
            await self.set_primary(userbroker.broker_id)                                    # noqa
            return userbroker
        raise x.MissingBrokersError()
    
    async def set_primary(self, broker_id: int) -> None:
        """
        Set a new primary broker for this user
        :param broker_id:   Broker id
        :return:            None
        """
        async with in_transaction():
            if ub := await UserBrokers.filter(user=self.usermod).only('id', 'broker_id', 'is_primary'):
                for i in ub:
                    if i.broker_id == broker_id:                                       # noqa
                        i.is_primary = True
                        await i.save(update_fields=['is_primary'])
                    elif i.is_primary:
                        i.is_primary = False
                        await i.save(update_fields=['is_primary'])

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
        if not broker:
            return
        
        broker_list = listify(broker)
        
        if isinstance(broker, Broker):
            if wallet or is_primary or meta:
                if not await UserBrokers.exists(user=self.usermod, broker=broker):
                    await UserBrokers.create(user=self.usermod, broker=broker, meta=meta,
                                             is_primary=is_primary, wallet=wallet)
                    return
        
        await self.usermod.brokers.add(*broker_list)
        
    
    # TESTME: Untested
    async def buy(self, equity_id: int, shares: int, price: float,
                  broker_id: Optional[int] = None, currency: Optional[str] = None):
        userbroker = await self.get_userbroker(broker_id)
        gross = price * shares
        fees = gross * userbroker.buyfees                                                   # noqa
        total = gross + fees
        currency = currency or userbroker.currency                                          # noqa

        async with in_transaction():
            stash = await self.get_stash(equity_id) or await self.add_stash(equity_id)
            if total <= await self.get_wallet(userbroker.broker_id):                        # noqa
                await userbroker.withdraw(total)
                await stash.deposit(shares)
                await Trade.create(
                    stash=stash, userbroker=userbroker, action=1, author=self.usermod,
                    price=price, shares=shares, gross=gross, fees=fees, total=total,
                    currency=currency
                )
                return gross, fees, total, currency
            raise x.NotEnoughFundsError()
        

    # TESTME: Untested
    async def sell(self, equity: Equity, shares: int, price: float,
                   broker: Optional[Broker] = None, currency: Optional[str] = None):
        # if not broker:
        #     if await self.has_primary():
        #         broker = await self.get_primary()
        #     else:
        #         if await self.has_userbrokers():
        #             ub = await UserBrokers.filter(user=self.usermod).first().values('id')
        #             broker = await self.find_userbroker(ub['id'])
        #             await self.set_primary(broker.id)
        #         else:
        #             raise x.MissingBrokersError()
        #
        # # ic(vars(broker))
        # gross = price * shares
        # fees = gross * broker.sellfees
        # total = gross - fees
        # currency = currency or broker.currency
        #
        # async with in_transaction():
        #     stash = await self.get_stash(equity)
        #     if not stash:
        #         stash = await Stash.create(user=self.usermod, equity=equity,
        #                                    author=self.usermod)
        #     # ic(type(stash), vars(stash))
        #
        #     await stash.withdraw(shares)
        #     await broker.ubs.incr_wallet(total)
        #     await Trade.create(stash=stash, broker=broker, action=2, author=self.usermod,
        #                        price=price, shares=shares, gross=gross, fees=fees, total=total,
        #                        currency=currency)
        #     return gross, fees, total, currency
        pass

    
    
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

    # TESTME: Untested
    async def add_stash(self, equity_id: int):
        if equity := await Equity.get_or_none(pk=equity_id).only('id'):
            return await Stash.create(user=self.usermod, equity=equity, author=self.usermod)
    
    # TESTME: Untested ready
    async def has_stash(self, equity_id: int):
        return await Stash.exists(user=self.usermod, equity_id=equity_id)
    
    # TESTME: Untested: ready
    async def get_stash(self, equity_id: int, *, as_dict: bool = False):
        query = Stash.get_or_none(user=self.usermod, equity_id=equity_id)
        if as_dict:
            return (await query.values(
                *stash_fields,
                equity='equity__ticker', category='equity__category',
                status='equity__status'
            ))[0]
        return await query.prefetch_related(
            Prefetch('equity', Equity.all().only('id', 'ticker', 'category', 'status'),
                     to_attr='equity')
        ).only(*stash_fields, 'equity_id')
    
    # TESTME: Untestedh
    @staticmethod
    async def deposit_shares(shares: int, stash: Stash):
        return await stash.deposit(shares)

    # TESTME: Untested
    @staticmethod
    async def withdraw_shares(shares: int, stash: Stash):
        return await stash.withdraw(shares)
    
    async def deposit_wallet(self, amount: float, broker_id: Optional[int] = None) -> float:
        """
        Add to your wallet
        :param amount:      The amount to add to the wallet
        :param broker_id:   The Broker to add to
        :return:            float New value of the wallet
        """
        userbroker = await self.get_userbroker(broker_id)
        return await userbroker.deposit(amount)

    async def withdraw_wallet(self, amount: float, broker_id: Optional[int] = None) -> float:
        """
        Deduct from your wallet
        :param amount:      The amount to deduct from the wallet
        :param broker_id:   The Broker to deduct from
        :return:            float New value of the wallet
        """
        userbroker = await self.get_userbroker(broker_id)
        return await userbroker.withdraw(amount)

    async def get_wallet(self, broker_id: Optional[int] = None) -> float:
        """
        Get the current value of a wallet
        :param broker_id:   Broker id
        :return:            float Wallet amount
        """
        userbroker = await self.get_userbroker(broker_id)
        return userbroker.wallet
    
    
    # TESTME: Untested
    async def _toggle_mark(self, *, equityid_list: Optional[List[int]] = None) -> None:
        """
        Adding new Marks or clearing all Marks
        :param equityid_list:   List of Equity ids
        :return:                None
        """
        # Adding
        if equityid_list:
            if equity_list := await Equity.filter(pk__in=equityid_list).only('id'):
                if existing := await Mark.filter(author=self.usermod, is_active=True) \
                                         .values_list('equity_id', flat=True):
                    equity_list = list(filter(lambda j: j.id not in existing, equity_list))
                ll = []
                for equity in equity_list:
                    ll.append(Mark(equity=equity, author=self.usermod, is_active=True))
                ll and await Mark.bulk_create(ll)
                return
            
        # Resetting
        await Mark.filter(author=self.usermod, is_active=True).update(is_active=False)

    # TESTME: Untested
    async def add_mark(self, equity_id: Union[int, List[int]]) -> None:
        """
        Add a new Mark to your list of Marks
        :param equity_id:   The Equity id you want to add
        :return:            None
        """
        return await self._toggle_mark(equityid_list=listify(equity_id))
    
    # TESTME: Untested
    async def reset_marks(self) -> None:
        """
        Deactivate all your currently active Marks
        :return:    None
        """
        return await self._toggle_mark()

    # TESTME: Untested
    async def remove_mark(self, mark_id: Union[int, List[int]]):
        """
        Hard-delete a mark
        :param mark_id: The Mark id you want to delete from your list.
        :return:        None
        """
        await Mark.filter(pk__in=listify(mark_id)).delete()

    
        
    # # TESTME: Untested
    # async def get_marks(self) -> list:
    #     """
    #     Get all of your active Marks
    #     :return:    list
    #     """
    #     return await Mark.filter(author=self.usermod, is_active=True).only(*mark_fields)
    #
    # # TESTME: Untested
    # async def disable_mark(self, equity_id: Union[int, List[int]]):
    #     now = datetime.now(tz=pytz.UTC)
    #     if equity_id:
    #         equityid_list = listify(equity_id)
    #         await Mark.filter(author=self.usermod, equity_id__in=equityid_list)\
    #                   .update(deleted_at=now, is_active=False)
    
    
    
    
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

