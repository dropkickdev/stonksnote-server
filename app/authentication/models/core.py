import pytz
from datetime import datetime
from typing import Optional, List
from tortoise import models, fields
from tortoise.manager import Manager
from limeutils import modstr

from app.authentication.models.manager import ActiveManager


class DTMixin(object):
    deleted_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class SharedMixin(object):
    full = Manager()
    
    def to_dict(self, exclude: Optional[List[str]] = None):
        d = {}
        exclude = ['created_at', 'deleted_at', 'updated_at'] if exclude is None else exclude
        for field in self._meta.db_fields:      # noqa
            if hasattr(self, field) and field not in exclude:
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

    full = Manager()

    class Meta:
        table = 'core_option'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


class Taxonomy(DTMixin, SharedMixin, models.Model):
    name = fields.CharField(max_length=191)
    type = fields.CharField(max_length=20)
    sort = fields.SmallIntField(default=100)
    author = fields.ForeignKeyField('models.UserMod', related_name='tax_of_author')
    parent = fields.ForeignKeyField('models.Taxonomy', related_name='tax_of_parent')

    class Meta:
        table = 'core_taxonomy'
        manager = ActiveManager()

    def __str__(self):
        return modstr(self, 'name')


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