import pytz
from datetime import datetime
from typing import Optional, List
from tortoise import models, fields
from tortoise.fields import (
    ForeignKeyRelation as FKRel, ManyToManyRelation as M2MRel, ReverseRelation as RRel,
    ForeignKeyNullableRelation as FKNullRel,
    ForeignKeyField as FKField, ManyToManyField as M2MField
)
from tortoise.manager import Manager
from limeutils import modstr

from app.cache import red
from app.settings import settings as s
from app.authentication.models.manager import ActiveManager


class DTMixin(object):
    deleted_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class SharedMixin(object):
    full = Manager()

    def to_dict(self, *, exclude: Optional[List[str]] = None, only: Optional[List[str]] = None):
        """
        Convert an object to a dict
        :param exclude: Field names to exclude. If empty then all fields are taken.
        :param only:    Only use these names. If empty then the object's fields are used.
        :return:        dict
        """
        d = {}
        exclude = ['created_at', 'deleted_at', 'updated_at'] if exclude is None else exclude
        fieldlist = self._meta.db_fields if only is None else only                      # noqa
        for field in fieldlist:      # noqa
            if hasattr(self, field):
                if (only and field in only) or field not in exclude:
                    d[field] = getattr(self, field)
        return d

    async def soft_delete(self):
        self.deleted_at = datetime.now(tz=pytz.UTC)                 # noqa
        await self.save(update_fields=['deleted_at'])               # noqa
        

class Option(SharedMixin, models.Model):
    name = fields.CharField(max_length=20)
    value = fields.CharField(max_length=191)
    user: FKRel['UserMod'] = FKField('models.UserMod', related_name='options', null=True)
    is_active = fields.BooleanField(default=True)
    admin_only = fields.BooleanField(default=False)
    deleted_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'core_option'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


class Visitor(models.Model):
    user: FKRel['UserMod'] = FKField('models.UserMod', related_name='visitors')
    browser = fields.CharField(max_length=99)
    browser_fam = fields.CharField(max_length=99)
    browser_ver = fields.CharField(max_length=99)
    os = fields.CharField(max_length=99)
    os_fam = fields.CharField(max_length=99)
    os_ver = fields.CharField(max_length=99)
    device = fields.CharField(max_length=99)
    device_fam = fields.CharField(max_length=99)
    device_brand = fields.CharField(max_length=99)
    device_model = fields.CharField(max_length=99)
    from_ip = fields.CharField(max_length=99)
    
    user_agent = fields.CharField(max_length=191)
    etag = fields.CharField(max_length=99)
    last_login = fields.DatetimeField(auto_now_add=True)
    last_logout = fields.DatetimeField(null=True)
    meta = fields.JSONField(null=True)

    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'core_visitor'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'user')
    

class Taxonomy(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    tier = fields.CharField(max_length=20, index=True)
    label = fields.CharField(max_length=191, default='')  # Longer version of name
    description = fields.CharField(max_length=191, default='')
    sort = fields.SmallIntField(default=100)
    parent: FKNullRel['Taxonomy'] = FKField('models.Taxonomy', related_name='parent_taxs', null=True)

    is_verified = fields.BooleanField(default=True)
    is_global = fields.BooleanField(default=False)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_taxs', null=True)

    tag_trades: M2MRel['Trade']
    parent_taxs: RRel['Taxonomy']
    sector_equity: RRel['Equity']
    industry_equity: RRel['Equity']
    exchange_equity: RRel['Equity']
    stage_equity: RRel['Equity']
    title_marks: RRel['Mark']

    class Meta:
        table = 'core_taxonomy'
        unique_together = (('name', 'tier'),)
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')

    @classmethod
    async def get_and_cache(cls, tier: str, name: str):
        if tax := await cls.get_or_none(tier=tier, name=name).only('id'):
            tax_dict = tax.to_dict()
            partialkey = s.CACHE_TAXONOMY.format(tier, name)
            red.set(partialkey, tax_dict, clear=True)
            return tax

    # TESTME: Untested
    @classmethod
    async def get_tax(cls, tier: str, name: Optional[str] = None):
        if name:
            partialkey = s.CACHE_TAXONOMY.format(tier, name)
            if tax_dict := red.get(partialkey):
                return tax_dict
            else:
                tax = await cls.get_and_cache(tier, name)
                tax_dict = tax.to_dict()
                return tax_dict
        else:
            taxes = []
            partialkey = s.CACHE_TAXONOMY_SEARCH.format(tier)
            if keynames_list := red.keys(partialkey):
                for tax in keynames_list:
                    taxes.append(red.get_tax(tier, tax))
            else:
                taxes = await cls.filter(tier=tier).values('id', 'name', 'description')
            return taxes

    # @classmethod
    # async def get_buy_stages(cls):
    #     return await cls.get_tax('buy_stage')


# # class HashMod(SharedMixin, models.Model):
#: FKRel['XXX' #     user = FKField()('models.UserMod', related_name='hashes')
# #     hash = fields.CharField(max_length=199, index=True)
# #     use_type = fields.CharField(max_length=20)
# #     expires = fields.DatetimeField(null=True)
# #     created_at = fields.DatetimeField(auto_now_add=True)
# #
# #     class Meta:
# #         table = 'auth_hash'
# #
# #     def __str__(self):
# #         return modstr(self, 'hash')


class Token(DTMixin, SharedMixin, models.Model):
    token = fields.CharField(max_length=128, unique=True)
    expires = fields.DatetimeField(index=True)
    is_blacklisted = fields.BooleanField(default=False)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_tokens')

    class Meta:
        table = 'auth_token'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'token')


class Media(DTMixin, SharedMixin, models.Model):
    path = fields.CharField(max_length=256)
    filename = fields.CharField(max_length=199)
    ext = fields.CharField(max_length=10)
    width = fields.SmallIntField(null=True)
    height = fields.SmallIntField(null=True)
    size = fields.SmallIntField(null=True)
    status = fields.CharField(max_length=20)        # Set original, modified, delete
    
    is_active = fields.BooleanField(default=True)
    meta = fields.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_media')

    logo_members: RRel['Owner']
    
    class Meta:
        table = 'core_media'
        manager = ActiveManager()
    
    def __str__(self):
        return modstr(self, f'{self.filename}.{self.ext}')


class Note(DTMixin, SharedMixin, models.Model):
    note = fields.TextField()
    status = fields.CharField(max_length=20)
    meta = fields.JSONField(null=True)
    author: FKRel['UserMod'] = FKField('models.UserMod', related_name='author_notes')

    note_trades: RRel['Trade']
    
    class Meta:
        table = 'core_note'
        manager = ActiveManager()
    
    def __str__(self):
        split = self.note.split()
        words = 10
        if len(split) >= words:
            return f'{" ".join(split[:words])}...'
        return self.note