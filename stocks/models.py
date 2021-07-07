from tortoise import models, fields
from tortoise.manager import Manager
from limeutils import modstr

from app.authentication.models.manager import ActiveManager
from app.authentication.models.core import DTMixin, SharedMixin



class Equity(DTMixin, SharedMixin, models.Model):
    code = fields.CharField(max_length=10)
    exchange = fields.ForeignKeyField('models.Taxonomy', related_name='exchange_equities')
    name = fields.CharField(max_length=191, default='')
    
    country = fields.CharField(max_length=2, default='')
    industry = fields.CharField(max_length=191, default='')
    meta = fields.JSONField(null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_equities')
    
    class Meta:
        table = 'stocks_equity'
        manager = ActiveManager()
        
    def __str__(self):
        return modstr(self, 'code')

    
class UserEquity(DTMixin, SharedMixin, models.Model):
    user = fields.ForeignKeyField('models.UserMod', related_name='userequity')
    equity = fields.ForeignKeyField('models.Equity', related_name='userequity')
    stage = fields.ForeignKeyField('models.Taxonomy', related_name='stage_equity', null=True)
    meta = fields.JSONField(null=True)

    groups = fields.ManyToManyField('models.Taxonomy', related_name='userequities',
                                    through='stocks_userequitygroups',
                                    backward_key='userequity_id')
    
    class Meta:
        table = 'stocks_userequity'
        unique_together = (('user', 'equity'),)
        manager = ActiveManager()
        
    def __str__(self):
        return f'{self.user}:{self.equity}'


class UserBroker(DTMixin, SharedMixin, models.Model):
    user = fields.ForeignKeyField('models.UserMod', related_name='userbrokers')
    broker = fields.ForeignKeyField('models.Broker', related_name='userbrokers')
    wallet = fields.DecimalField(max_digits=13, decimal_places=2, default=0)
    logo = fields.CharField(max_length=255)
    meta = fields.JSONField(null=True)

    class Meta:
        table = 'stocks_userbroker'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'broker')


class Wallet(DTMixin, SharedMixin, models.Model):
    broker = fields.ForeignKeyField('models.UserBroker', related_name='broker_wallet')
    amount = fields.DecimalField(max_digits=13, decimal_places=2, default=0)
    type = fields.CharField(max_length=20, default='')
    status = fields.CharField(max_length=20, default='')

    class Meta:
        table = 'stocks_wallet'
        manager = ActiveManager()
        

class Broker(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    rating = fields.FloatField(max_digits=2, decimal_places=1, default=0)
    email = fields.CharField(max_length=191, default='')
    number = fields.CharField(max_length=191, default='')
    url = fields.CharField(max_length=191, default='')
    tel = fields.CharField(max_length=191, default='')
    country = fields.CharField(max_length=2, default='')

    is_online = fields.BooleanField(default=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = 'stocks_broker'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')
    

class Trade(DTMixin, SharedMixin, models.Model):
    equity = fields.ForeignKeyField('models.Equity', related_name='equity_trades')
    broker = fields.ForeignKeyField('models.Taxonomy', related_name='broker_trades', null=True)
    status = fields.CharField(max_length=20)
    
    shares = fields.IntField(default=0)
    entrypoint = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
    stoploss = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
    takeprofit = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
    gross = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    fees = fields.JSONField(null=True)
    total = fields.DecimalField(max_digits=10, decimal_places=4, default=0)
    gainloss = fields.DecimalField(max_digits=10, decimal_places=4)
    
    meta = fields.JSONField(null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_trades')

    is_action = fields.BooleanField(default=False)          # For action
    resolved_at = fields.DatetimeField(null=True)           # For action

    notes = fields.ManyToManyField('models.Note', related_name='note_trades',
                                   through='stocks_tradenotes', backward_key='trade_id')
    tags = fields.ManyToManyField('models.Taxonomy', related_name='tag_trades',
                                  through='stocks_tradetags', backward_key='trade_id')
    uploads = fields.ManyToManyField('models.Media', related_name='upload_trades',
                                     through='stocks_tradeuploads', backward_key='trade_id')
    
    class Meta:
        table = 'stocks_trade'
        manager = ActiveManager()
        
    def __str__(self):
        return f'{self.id}:{self.equity}:{self.shares} shares'              # noqa


class Media(DTMixin, SharedMixin, models.Model):
    path = fields.CharField(max_length=256)
    trade = fields.ForeignKeyField('models.Trade', related_name='trade_medias')
    source = fields.ForeignKeyField('models.Media', related_name='media_medias', null=True)
    status = fields.CharField(max_length=20)        # Set original or modified
    author = fields.ForeignKeyField('models.UserMod', related_name='author_medias')

    class Meta:
        table = 'stocks_media'
        manager = ActiveManager()
        
    def __str__(self):
        return modstr(self, 'path')
    

class Note(DTMixin, SharedMixin, models.Model):
    note = fields.TextField()
    status = fields.CharField(max_length=20)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_notes')
    
    class Meta:
        table = 'stocks_note'
        manager = ActiveManager()

    def __str__(self):
        split = self.note.split()
        words = 10
        if len(split) >= words:
            return f'{" ".join(split[:words])}...'
        return self.note


class Transaction(DTMixin, SharedMixin, models.Model):
    status = fields.CharField(max_length=20)                        # Buy/Sell/Others
    amount = fields.DecimalField(max_digits=13, decimal_places=2, default=0)
    trade = fields.ForeignKeyField('models.Trade', related_name='transactions', null=True)
    author = fields.ForeignKeyField('models.UserMod', related_name='author_transactions')

    class Meta:
        table = 'stocks_transaction'
        manager = ActiveManager()
        
    def __str__(self):
        return f'{self.id}:{self.status}'                                   # noqa


# class TradeNote(DTMixin, models.Model):
#     trade = fields.ForeignKeyField('models.Trade', related_name='tradenotes')
#     note = fields.ForeignKeyField('models.Note', related_name='tradenotes')
#     status = fields.ForeignKeyField('models.Taxonomy', related_name='tradenotes', null=True)
#
#     class Meta:
#         table = 'stocks_note_status'
#         unique_together = (('trade_id', 'note_id'),)


# class Timeline(DTMixin, SharedMixin, models.Model):
#     equity = fields.ForeignKeyField('models.Equity', related_name='equity_timelines')
#     status = fields.ForeignKeyField('models.Taxonomy', related_name='status_trades')
#     author = fields.ForeignKeyField('models.UserMod', related_name='author_timelines')
#
#     class Meta:
#         table = 'stocks_timeline'
#         manager = ActiveManager()
#
#     def __str__(self):
#         return self.id                                                              # noqa


# class Collection(DTMixin, SharedMixin, models.Model):
#     name = fields.CharField(max_length=191)
#     description = fields.CharField(max_length=191)
#     author = fields.ForeignKeyField('models.UserMod', related_name='author_collections')
#
#     class Meta:
#         table = 'stocks_collection'
#         manager = ActiveManager()
#
#     def __str__(self):
#         return self.name