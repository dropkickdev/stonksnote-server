from tortoise import models, fields
from tortoise.manager import Manager
from limeutils import modstr

from app.authentication.models.manager import ActiveManager
from app.authentication.models.core import DTMixin, SharedMixin




class Broker(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    rating = fields.FloatField(max_digits=2, decimal_places=1, default=0)
    email = fields.CharField(max_length=191, default='')
    number = fields.CharField(max_length=191, default='')
    url = fields.CharField(max_length=191, default='')
    tel = fields.CharField(max_length=191, default='')
    country = fields.CharField(max_length=2, default='')
    logo = fields.CharField(max_length=255)
    
    is_online = fields.BooleanField(default=True)
    is_active = fields.BooleanField(default=True)
    meta = fields.JSONField(null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_brokers')
    
    class Meta:
        table = 'trades_broker'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'name')


class UserBroker(DTMixin, SharedMixin, models.Model):
    user = fields.ForeignKeyField('models.UserMod', related_name='userbrokers')
    broker = fields.ForeignKeyField('models.Broker', related_name='userbrokers')
    wallet = fields.DecimalField(max_digits=13, decimal_places=2, default=0)
    traded = fields.DecimalField(max_digits=13, decimal_places=2, default=0)
    status = fields.CharField(max_length=20)
    is_default = fields.BooleanField(default=True)
    meta = fields.JSONField(null=True)
    
    class Meta:
        table = 'trades_userbroker'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, 'broker')


class Owner(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    description = fields.CharField(max_length=191)
    website = fields.CharField(max_length=191)
    founded = fields.DateField(null=True)
    country = fields.CharField(max_length=2, null=True)
    industry = fields.CharField(max_length=191, default='')
    logo = fields.ForeignKeyField('models.Media', related_name='logo_members')
    meta = fields.JSONField(null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_members')

    class Meta:
        table = 'trades_member'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


class Equity(DTMixin, SharedMixin, models.Model):
    ticker = fields.CharField(max_length=10)
    member = fields.ForeignKeyField('models.Owner', related_name='member_equity')
    sector = fields.ForeignKeyField('models.Taxonomy', related_name='sector_equity')
    industry = fields.ForeignKeyField('models.Taxonomy', related_name='industry_equity', null=True)
    
    exchange = fields.ForeignKeyField('models.Taxonomy', related_name='exchange_equity')
    category = fields.CharField(max_length=20)  # stock, index, forex, commodity, crypto, preferred
    currency = fields.CharField(max_length=3)
    
    # stage = fields.ForeignKeyField('models.Taxonomy', related_name='stage_equity', null=True)
    status = fields.CharField(max_length=20)        # active, suspended, etc
    meta = fields.JSONField(null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_equity')

    collections = fields.ManyToManyField('models.Collection', related_name='collection_equity',
                                    through='trades_equitycollection', backward_key='equity_id')
    class Meta:
        table = 'trades_equity'
        manager = ActiveManager()
        
    def __str__(self):
        return modstr(self, 'ticker')

    
# class EquityHistory(DTMixin, SharedMixin, models.Model):
#     equity = fields.ForeignKeyField('models.Equity', related_name='equityhistory')
#     open = fields.DecimalField(max_digits=15, decimal_places=4, null=True)
#     close = fields.DecimalField(max_digits=15, decimal_places=4, null=True)
#     high = fields.DecimalField(max_digits=15, decimal_places=4, null=True)
#     low = fields.DecimalField(max_digits=15, decimal_places=4, null=True)
#     volume = fields.DecimalField(max_digits=15, decimal_places=4, null=True)
#     value = fields.DecimalField(max_digits=15, decimal_places=4, null=True)
#     marketcap = fields.DecimalField(max_digits=21, decimal_places=4, null=True)
#     trades = fields.DecimalField(max_digits=15, decimal_places=0, null=True)
#
#
#     todate = fields.JSONField(null=True)        # wtd, mtd, ytd
#     sma = fields.JSONField(null=True)
#     rsi = fields.JSONField(null=True)
#     macd = fields.JSONField(null=True)
#     atr = fields.JSONField(null=True)
#     cci = fields.JSONField(null=True)
#     sts = fields.JSONField(null=True)
#
#     meta = fields.JSONField(null=True)


class Trade(DTMixin, SharedMixin, models.Model):
    user = fields.ForeignKeyField('models.UserMod', related_name='trades')
    equity = fields.ForeignKeyField('models.Equity', related_name='trades')
    broker = fields.ForeignKeyField('models.Broker', related_name='trades')

    action = fields.CharField(max_length=20)    # buy, sell
    marketprice = fields.DecimalField(max_digits=12, decimal_places=4, default=0)
    shares = fields.IntField(default=0)
    gross = fields.DecimalField(max_digits=12, decimal_places=4, default=0)
    fees = fields.DecimalField(max_digits=12, decimal_places=4, default=0)
    total = fields.DecimalField(max_digits=10, decimal_places=4, default=0)

    status = fields.DatetimeField(null=True)  # pending, resolved...I think
    note = fields.ForeignKeyField('models.Note', related_name='note_trades')
    meta = fields.JSONField(null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_trades')

    tags = fields.ManyToManyField('models.Taxonomy', related_name='tag_trades',
                                  through='trades_tags', backward_key='trade_id')
    collections = fields.ManyToManyField('models.Collection', related_name='collection_trades',
                                         through='trades_tradecollection', backward_key='trade_id')
#
    class Meta:
        table = 'trades_trade'
        unique_together = (('user', 'equity', 'broker'),)
        manager = ActiveManager()

    def __str__(self):
        return f'{self.user}:{self.equity}'


class Collection(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    category = fields.CharField(max_length=20)      # equity
    is_global = fields.BooleanField(default=False)
    is_locked = fields.BooleanField(default=False)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_collections')

    class Meta:
        table = 'trades_collection'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


class Mark(DTMixin, SharedMixin, models.Model):
    symbol = fields.CharField(max_length=10)
    title = fields.ForeignKeyField('models.Taxonomy', related_name='marks', null=True)
    expires = fields.DateField(null=True)
    
    meta = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_marks')

    class Meta:
        table = 'trades_mark'
        manager = ActiveManager()




# class Trade(DTMixin, SharedMixin, models.Model):
#     equity = fields.ForeignKeyField('models.Equity', related_name='equity_trades')
#     broker = fields.ForeignKeyField('models.Taxonomy', related_name='broker_trades', null=True)
#     status = fields.CharField(max_length=20)
##
#     stoploss = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
#     takeprofit = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
#

#     gainloss = fields.DecimalField(max_digits=10, decimal_places=4)
#
#     meta = fields.JSONField(null=True)
#     author = fields.ForeignKeyField('models.UserMod', related_name='author_trades')
#
#     is_action = fields.BooleanField(default=False)          # For action
#     resolved_at = fields.DatetimeField(null=True)           # For action
#

#
#     class Meta:
#         table = 'trades_trade'
#         manager = ActiveManager()
#
#     def __str__(self):
#         return f'{self.id}:{self.equity}:{self.shares} shares'              # noqa
