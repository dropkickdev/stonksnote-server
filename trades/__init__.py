from typing import Optional, Tuple, Union, List
from tortoise.query_utils import Prefetch
from tortoise.transactions import in_transaction
from pydantic import UUID4
from limeutils import listify

from .models import *
from app.settings import settings as s
from app.auth import UserMod



class Trader:
    usermod: UserMod
    broker_list: list
    broker: Broker
    
    def __init__(self, usermod: UserMod):
        self.usermod = usermod
        # self.currency = self.usermod.get_currency
        
        # TODO: Find out when to actually run the queries
        # These aren't saved to the user's db yet until to save on db hits until
        # you actually run them. Only then will it run the queries needed.
        # self.broker_list = brokers and listify(brokers) or []       # Not saved to db yet
        # self.broker = self.broker_list and self.broker_list[0] or None

    async def preaction_setup(self):
        # Gather the brokers
        userbrokers = await self.usermod.brokers.all()
        
    
    async def get_broker(self):
        pass
        # ic(await x.brokers.all())
        # ic(await self.usermod.brokers.all())
        
        # if self.broker:
        #     return self.broker
        
        # if broker := await Broker.get_or_none(userbrokers__user=self.usermod,
        #                                       userbrokers__is_primary=True).only('id'):
        #     self.broker = broker
        #     return broker

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

