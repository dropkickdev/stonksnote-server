from datetime import datetime
from typing import Optional, List
from tortoise import models, fields as fl
from tortoise.fields import (
    ForeignKeyRelation as FKRel, ManyToManyRelation as M2MRel, ReverseRelation as RRel,
    ForeignKeyField as FKField, ManyToManyField as M2MField
)
from limeutils import modstr, setup_pagination

from app import ic
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
    
    is_online = fl.BooleanField(default=True)
    is_active = fl.BooleanField(default=True)
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_brokers')
    
    userbrokers: RRel['UserBroker']
    trades: RRel['Trade']
    
    class Meta:
        table = 'trades_broker'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'name')
    
    @classmethod
    async def get_fees(cls, ):
        pass


class UserBroker(DTMixin, SharedMixin, models.Model):
    user: FKRel[UserMod] = FKField('models.UserMod', related_name='userbrokers')
    broker: FKRel[Broker] = FKField('models.Broker', related_name='userbrokers')
    wallet = fl.DecimalField(max_digits=13, decimal_places=2, default=0)
    traded = fl.DecimalField(max_digits=13, decimal_places=2, default=0)
    status = fl.CharField(max_length=20)
    
    is_default = fl.BooleanField(default=True)
    meta = fl.JSONField(null=True)

    broker_users: M2MRel['UserMod']
    
    class Meta:
        table = 'trades_userbroker'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'broker')


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
                                      through='trades_xequitycollection', backward_key='collection_id')
    
    class Meta:
        table = 'trades_collection'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'name')


class Trade(DTMixin, SharedMixin, models.Model):
    stash: FKRel['Stash'] = FKField('models.Stash', related_name='trades')
    broker: FKRel['Broker'] = FKField('models.Broker', related_name='trades')

    action = fl.SmallIntField()    # ActionChoices
    price = fl.DecimalField(max_digits=12, decimal_places=4, default=0)
    shares = fl.IntField(default=0)
    gross = fl.DecimalField(max_digits=12, decimal_places=4, default=0)
    fees = fl.DecimalField(max_digits=12, decimal_places=4, default=0)
    total = fl.DecimalField(max_digits=10, decimal_places=4, default=0)
    currency = fl.CharField(max_length=3, default='PHP')

    status = fl.DatetimeField(null=True)  # pending, resolved...I think
    basetrade: FKRel['Trade'] = FKField('models.Trade', related_name='basetrade_trades', null=True)
    note: FKRel['Note'] = FKField('models.Note', related_name='note_trades', null=True)
    
    is_resolved = fl.BooleanField(default=False, index=True)
    meta = fl.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_trades')

    tags: M2MRel['Taxonomy'] = M2MField('models.Taxonomy', related_name='tag_trades',
                                        through='trades_xtags', backward_key='trade_id')

    basetrade_trades: RRel['Trade']
    
    class Meta:
        table = 'trades_trade'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'stash__equity')
    
    # TODO: Update this since the Stash table was added
    # TESTME: Untested
    @classmethod
    async def get_trades(cls, spec: TradeData, user: UserDB, start: Optional[datetime] = None,
                         end: Optional[datetime] = None) -> List[dict]:
        """
        Get list of trades for a specified user
        :param spec:    TradeData token from the route
        :param user:    User to search for
        :param start:   Starting date
        :param end:     Ending date
        :return:        list
        """
        try:
            countquery = cls.filter(author_id=user.id)
            tradequery = cls.filter(author_id=user.id)
            
            if spec.equity:
                tradequery = tradequery.filter(equity__ticker__icontains=spec.equity)
                countquery = countquery.filter(equity__ticker__icontains=spec.equity)
            if start:
                tradequery = tradequery.filter(created_at__gte=start)
                countquery = countquery.filter(created_at__gte=start)
            if end:
                tradequery = tradequery.filter(created_at__lte=end)
                countquery = countquery.filter(created_at__lte=end)
                
            count = await countquery.count()
            orderby, offset, limit = setup_pagination(**spec.dict(), total=count)
            tradequery = tradequery.order_by(orderby).limit(limit).offset(offset)
            tradequery = tradequery.values(
                'id', 'shares', 'action', 'price', 'created_at', 'author_id',
                'currency', ticker='equity__ticker',
            )
            trades = await tradequery
            
            clean_trades = cls.trades_cleaner(trades)
            return clean_trades
        except Exception as e:
            ic(e)

    # TODO: Update this since the Stash table was added
    # TESTME: Untested
    @classmethod
    def trades_cleaner(cls, trades: List[dict], buyfees: Optional[float] = None,
                       sellfees: Optional[float] = None) -> List[dict]:
        """
        Cleans data to be used by the react front-end
        :param trades:      Result of a DB query in dict format
        :param buyfees:     If there any any fees to include from broker
        :param sellfees:    If there any any fees to include from broker
        :return:            list
        """
        ll = []
        for i in trades:
            del i['author_id']
            i['minsell'] = 'n/a'
            i['gainloss'] = 'n/a'
            
            i['total'] = i.get('shares') * i.get('price')
            if buyfees:
                i['total'] = i['total'] * buyfees
            elif sellfees:
                i['total'] = i['total'] * sellfees
            
            # TODO: Convert to user's local time via offset
            created_at = i.get('created_at').strftime('%Y-%m-%d')
            i['bought'] = created_at if i.get('action') == 'buy' else ''
            i['sold'] = created_at if i.get('action') == 'sell' else ''
            
            ll.append(i)
        return ll


class Stash(DTMixin, SharedMixin, models.Model):
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