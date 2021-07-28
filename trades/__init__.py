from decimal import Decimal
from typing import Optional, Tuple, Union, List
from tortoise.query_utils import Prefetch, Q
from tortoise.transactions import in_transaction
from pydantic import UUID4, BaseModel
from limeutils import listify

from .models import *
# from .resource import CreateBrokerPy
from app.settings import settings as s
from app.auth import UserMod




class Trader:
    usermod: UserMod
    broker: Broker
    broker_list: list
    
    # unsaved_brokers: bool = False
    # unsaved = False
    
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

    # TESTME: Untested ready
    async def get_broker(self, as_instance: bool = False):
        fields = ['id', 'name', 'short', 'brokerno', 'rating', 'logo', 'currency']
        query = Broker.get_or_none(userbrokers__user=self.usermod, userbrokers__is_primary=True)
        
        if not as_instance:
            query = query.values(*fields, is_primary='userbrokers__is_primary',
                                 wallet='userbrokers__wallet')
            return (await query)[0]

        query = query.prefetch_related(
            Prefetch('userbrokers', UserBrokers.all()\
                     .only('id', 'broker_id', 'is_primary', 'wallet'), to_attr='ubs')
        )
        
        if broker := await query.only(*fields):
            broker.is_primary = broker.ubs[0].is_primary
            broker.wallet = broker.ubs[0].wallet
            return broker
                

    # TESTME: Untested: ready
    async def get_brokers(self, as_instance: bool = False) -> list:
        """
        Get the brokers of a user
        :param as_instance: Return dict or objects
        :return:            list
        """
        fields = ['id', 'name', 'short', 'brokerno', 'rating', 'logo', 'currency']
        
        if not as_instance:
            return await Broker.filter(userbrokers__user=self.usermod) \
                .values(*fields, is_primary='userbrokers__is_primary', wallet='userbrokers__wallet')

        broker_list = await Broker.filter(userbrokers__user=self.usermod).prefetch_related(
            Prefetch('userbrokers', UserBrokers.all()\
                     .only('id', 'broker_id', 'is_primary', 'wallet'), to_attr='ubs')
        ).only(*fields)

        if broker_list:
            for idx, i in enumerate(broker_list):
                broker_list[idx].is_primary = i.ubs[0].is_primary  # noqa
                broker_list[idx].wallet = i.ubs[0].wallet  # noqa
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
    
    
    # TESTME: Untested: ready
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
    
    
    # TESTME: Untested: ready
    async def remove_broker(self, brokers: Union[Broker, List[Broker]]) -> None:
        """
        Unassign a Broker from the UserMod
        :param brokers:     Broker
        :return:            None
        """
        brokers = listify(brokers)
        await self.usermod.brokers.remove(*brokers)
        
    
        
    
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


    async def buy_stock(self, equity_id: int, shares: int, price: float,
                        broker: Optional[Broker] = None):
        
        x = self.usermod
        ic(vars(x))
        
        # y = await x.brokers.all()
        # ic(y, vars(y[0]))
        # z = await x.userbrokers.all()
        # ic(z, vars(z[0]))
        
        # # Getting data from Broker and UserBrokers in one query
        # foo = await UserMod.filter(userbrokers__user=x).values(prime='userbrokers__is_primary',
        #                                                        broker='brokers__name')
        # ic(foo)
        
        
        
        
        
        # a = await x.brokers.userbrokers.all()
        # ic(a)
        
        
        # for i, idx in enumerate(y):
        #     ic(idx, i)
        # ic(vars(y[1]))
        
        return 1, 2, 3
        # # Check Stash
        # if broker := broker or await self.get_broker():
        #     if equity := await Equity.get_or_none(pk=equity_id).only('id'):
        #         stash, _ = await Stash.get_or_create(author=self.usermod, equity=equity)
        #
        #         gross = price * shares
        #         fees = gross * broker.buyfees
        #         total = gross + fees
        #         currency = self.currency
        #         # return gross, fees, total
        #
        #         async with in_transaction():
        #             stash.shares += shares
        #             await stash.save(update_fields=['shares'])
        #             trade = await Trade.create(stash=stash, equity=equity, broker=self.broker,
        #                                        action=1, price=price, shares=shares, gross=gross,
        #                                        fees=fees, total=total, currency=currency)
        #             return gross, fees, total
        
        

    async def sell_stock(self, equity: Equity, shares: int, price: float):
        pass
    
    async def get_ticket(self, ticket: str):
        return
    


def get_foo():
    return Equity.get(pk=1).prefetch_related(
        Prefetch('owner', queryset=Owner.all().only('id', 'name'))
    ).only('id', 'ticker', 'owner_id')

