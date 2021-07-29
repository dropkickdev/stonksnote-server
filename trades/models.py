from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from tortoise import models, fields as fl
from tortoise.fields import (
    ForeignKeyRelation as FKRel, ManyToManyRelation as M2MRel, ReverseRelation as RRel,
    ForeignKeyField as FKField, ManyToManyField as M2MField
)
from tortoise.queryset import Prefetch
from tortoise.transactions import in_transaction
from limeutils import modstr, setup_pagination

from app import ic
from app.settings import settings as s
from app.auth import UserDB, UserMod
from app.authentication.models.manager import ActiveManager
from app.authentication.models.core import DTMixin, SharedMixin, Taxonomy, Note
from .resource import TradeData


class Broker(DTMixin, SharedMixin, models.Model):
    name = fl.CharField(max_length=191)
    short = fl.CharField(max_length=10, default='')
    brokerno = fl.IntField(null=True)
    rating = fl.FloatField(max_digits=2, decimal_places=1, default=0)
    email = fl.CharField(max_length=191, default='')
    number = fl.CharField(max_length=191, default='')
    url = fl.CharField(max_length=191, default='')
    tel = fl.CharField(max_length=191, default='')
    country = fl.CharField(max_length=2, default='')
    logo = fl.CharField(max_length=255, default='')
    buyfees = fl.DecimalField(max_digits=6, decimal_places=4, default=0)
    sellfees = fl.DecimalField(max_digits=6, decimal_places=4, default=0)
    currency = fl.CharField(max_length=5, default=s.CURRENCY)
    
    is_online = fl.BooleanField(default=True)
    is_active = fl.BooleanField(default=True)
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_brokers')

    broker_users: M2MRel['UserMod']
    userbrokers: RRel['UserBrokers']
    trades: RRel['Trade']
    
    class Meta:
        table = 'trades_broker'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'name')
    
    # TESTME: Untested
    @classmethod
    async def get_fees(cls, ):
        pass
    
        

class UserBrokers(DTMixin, SharedMixin, models.Model):
    user: FKRel[UserMod] = FKField('models.UserMod', related_name='userbrokers')
    broker: FKRel[Broker] = FKField('models.Broker', related_name='userbrokers')
    wallet = fl.DecimalField(max_digits=13, decimal_places=2, default=0)
    traded = fl.DecimalField(max_digits=13, decimal_places=2, default=0)
    status = fl.CharField(max_length=20, default='active')
    
    is_primary = fl.BooleanField(default=False)
    meta = fl.JSONField(null=True)
    
    class Meta:
        table = 'trades_xuserbrokers'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'broker')

    # TESTME: Untested: ready
    async def reset_wallet(self, amount: float = 0, save_now: bool = False):
        self.wallet = amount
        await self.save(update_fields=['wallet'])

    # TESTME: Untested: ready
    async def incr_wallet(self, gross: float):
        self.wallet += gross
        await self.save(update_fields=['wallet'])

    # TESTME: Untested: ready
    async def decr_wallet(self, gross: float):
        # TODO: Doesn't check if you have enough funds
        self.wallet -= gross
        # self.wallet = 0 if self.wallet < 0 else self.wallet
        await self.save(update_fields=['wallet'])



class Owner(DTMixin, SharedMixin, models.Model):
    name = fl.CharField(max_length=191)
    description = fl.CharField(max_length=191, default='')
    website = fl.CharField(max_length=191, default='')
    founded = fl.DateField(null=True)
    country = fl.CharField(max_length=2, null=True)
    industry = fl.CharField(max_length=191, default='')
    logo: FKRel['Media'] = FKField('models.Media', related_name='logo_members', null=True)  # noqa
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_owners')

    owner_equity: RRel['owner_equity']

    class Meta:
        table = 'trades_owner'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


class Equity(DTMixin, SharedMixin, models.Model):
    ticker = fl.CharField(max_length=10)
    owner: FKRel[Owner] = FKField('models.Owner', related_name='owner_equity')
    sector: FKRel['Taxonomy'] = FKField('models.Taxonomy', related_name='sector_equity', null=True)
    industry: FKRel['Taxonomy'] = FKField('models.Taxonomy', related_name='industry_equity', null=True)
    exchange: FKRel['Taxonomy'] = FKField('models.Taxonomy', related_name='exchange_equity')
    stage: FKRel['Taxonomy'] = FKField('models.Taxonomy', related_name='stage_equity', null=True)
    category = fl.SmallIntField(default=1)     # EquityCategoryChoices
    status = fl.CharField(max_length=20, default='active')        # active, suspended, etc
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_equity')

    equity_collections: M2MRel['Collection']
    stash: RRel['Stash']
    equity_marks: RRel['Mark']

    class Meta:
        table = 'trades_equity'
        manager = ActiveManager()
        
    def __str__(self):
        return modstr(self, 'ticker')


class Collection(DTMixin, SharedMixin, models.Model):
    name = fl.CharField(max_length=191)
    category = fl.CharField(max_length=20)  # equity
    
    is_global = fl.BooleanField(default=False)
    is_locked = fl.BooleanField(default=False)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_collections')
    
    equity: M2MRel[Equity] = M2MField('models.Equity', related_name='equity_collections',
                                      through='trades_xequitycollections',
                                      backward_key='collection_id', forward_key='equity_id')
    
    class Meta:
        table = 'trades_collection'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'name')


class Trade(DTMixin, SharedMixin, models.Model):
    stash: FKRel['Stash'] = FKField('models.Stash', related_name='trades')
    broker: FKRel['Broker'] = FKField('models.Broker', related_name='trades')

    action = fl.SmallIntField()    # ActionChoices
    price = fl.DecimalField(max_digits=12, decimal_places=4)
    shares = fl.IntField(default=0)
    gross = fl.DecimalField(max_digits=12, decimal_places=4, default=0)
    fees = fl.DecimalField(max_digits=12, decimal_places=4, default=0)
    total = fl.DecimalField(max_digits=10, decimal_places=4, default=0)
    currency = fl.CharField(max_length=3, default=s.CURRENCY)

    status = fl.CharField(max_length=20, default='')  # Not sure what it's for right now
    basetrade: FKRel['Trade'] = FKField('models.Trade', related_name='basetrade_trades', null=True)
    note: FKRel['Note'] = FKField('models.Note', related_name='note_trades', null=True)
    
    is_resolved = fl.BooleanField(default=True, index=True)
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_trades')

    tags: M2MRel['Taxonomy'] = M2MField('models.Taxonomy', related_name='tag_trades',
                                        through='trades_xtags', backward_key='trade_id',
                                        forward_key='taxonomy_id')

    basetrade_trades: RRel['Trade']
    
    class Meta:
        table = 'trades_trade'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'stash__equity')
    

class Stash(DTMixin, SharedMixin, models.Model):
    user: FKRel['UserMod'] = FKField('models.UserMod', related_name='user_stash')
    equity: FKRel[Equity] = FKField('models.Equity', related_name='stash')
    shares = fl.IntField(default=0)

    is_resolved = fl.BooleanField(default=False, index=True)
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_stash')
    
    trades: RRel['Trade']

    class Meta:
        table = 'trades_stash'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'equity')

    # TESTME: Untested
    async def incr_stash(self, shares: int):
        self.shares += shares
        await self.save(update_fields=['shares'])
        

    # TESTME: Untested
    async def decr_stash(self, shares: int):
        self.shares -= shares
        await self.save(update_fields=['shares'])


class Mark(DTMixin, SharedMixin, models.Model):
    equity: FKRel[Equity] = FKField('models.Equity', related_name='equity_marks')
    title: FKRel['Taxonomy'] = FKField('models.Taxonomy', related_name='title_marks', null=True)
    expires = fl.DateField(null=True)
    
    is_active = fl.BooleanField(default=True)
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_marks')

    class Meta:
        table = 'trades_mark'
        manager = ActiveManager()


# class EquityHistory(DTMixin, SharedMixin, models.Model):
#     equity = FKField('models.Equity', related_name='equityhistory')
#     open = fl.DecimalField(max_digits=15, decimal_places=4, null=True)
#     close = fl.DecimalField(max_digits=15, decimal_places=4, null=True)
#     high = fl.DecimalField(max_digits=15, decimal_places=4, null=True)
#     low = fl.DecimalField(max_digits=15, decimal_places=4, null=True)
#     volume = fl.DecimalField(max_digits=15, decimal_places=4, null=True)
#     value = fl.DecimalField(max_digits=15, decimal_places=4, null=True)
#     marketcap = fl.DecimalField(max_digits=21, decimal_places=4, null=True)
#     trades = fl.DecimalField(max_digits=15, decimal_places=0, null=True)
#
#
#     todate = fl.JSONField(null=True)        # wtd, mtd, ytd
#     sma = fl.JSONField(null=True)
#     rsi = fl.JSONField(null=True)
#     macd = fl.JSONField(null=True)
#     atr = fl.JSONField(null=True)
#     cci = fl.JSONField(null=True)
#     sts = fl.JSONField(null=True)
#
#     meta = fl.JSONField(null=True)