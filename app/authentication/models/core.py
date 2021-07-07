import pytz
from datetime import datetime
from typing import Optional, List
from tortoise import models, fields
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
    user = fields.ForeignKeyField('models.UserMod', related_name='options', null=True)
    is_active = fields.BooleanField(default=True)
    admin_only = fields.BooleanField(default=False)
    deleted_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'core_option'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


class UserHistory(models.Model):
    user = fields.ForeignKeyField('models.UserMod', related_name='userhistory')
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
    

class Taxonomy(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    tier = fields.CharField(max_length=20, index=True)
    label = fields.CharField(max_length=191, default='')  # Longer version of name
    description = fields.CharField(max_length=191, default='')
    sort = fields.SmallIntField(default=100)
    author = fields.ForeignKeyField('models.UserMod', related_name='tax_of_author')
    parent = fields.ForeignKeyField('models.Taxonomy', related_name='tax_of_parent')

    is_verified = fields.BooleanField(default=True)
    is_locked = fields.BooleanField(default=False)

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

    @classmethod
    async def get_buy_stages(cls):
        return await cls.get_tax('buy_stage')


# # class HashMod(SharedMixin, models.Model):
# #     user = fields.ForeignKeyField('models.UserMod', related_name='hashes')
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


class TokenMod(models.Model):
    token = fields.CharField(max_length=128, unique=True)
    expires = fields.DatetimeField(index=True)
    is_blacklisted = fields.BooleanField(default=False)
    author = fields.ForeignKeyField('models.UserMod', on_delete=fields.CASCADE,
                                    related_name='author_tokens')

    full = Manager()

    class Meta:
        table = 'auth_token'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'token')