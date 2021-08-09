from typing import Union, Optional, List
from limeutils import modstr, valid_str_only
from tortoise import fields, models
from tortoise.fields import (
    ForeignKeyRelation as FKRel, ManyToManyRelation as M2MRel, ReverseRelation as RRel,
    ForeignKeyField as FKField, ManyToManyField as M2MField
)
from tortoise.manager import Manager
from fastapi_users.db import TortoiseBaseUserModel
from tortoise.exceptions import BaseORMException
from tortoise.query_utils import Prefetch
from redis.exceptions import RedisError

from app import settings as s, exceptions as x, cache, red, ic
from app.validation import UpdateGroupVM, UpdatePermissionVM
from app.authentication.models.core import DTMixin, CuratorM, SharedMixin, Option




class UserMod(DTMixin, TortoiseBaseUserModel):
    username = fields.CharField(max_length=50, default='')
    display = fields.CharField(max_length=50, default='')
    first_name = fields.CharField(max_length=191, default='')
    middle_name = fields.CharField(max_length=191, default='')
    last_name = fields.CharField(max_length=191, default='')
    
    civil = fields.CharField(max_length=20, default='')
    bday = fields.DateField(null=True)
    mobile = fields.CharField(max_length=50, default='')
    telephone = fields.CharField(max_length=50, default='')
    avatar = fields.CharField(max_length=255, default='')
    status = fields.CharField(max_length=20, default='')
    bio = fields.CharField(max_length=191, default='')
    address1 = fields.CharField(max_length=191, default='')
    address2 = fields.CharField(max_length=191, default='')
    country = fields.CharField(max_length=2, default='')
    zipcode = fields.CharField(max_length=20, default='')
    timezone = fields.CharField(max_length=10, default=s.USER_TIMEZONE)
    website = fields.CharField(max_length=20, default='')
    currency = fields.CharField(max_length=5, default=s.CURRENCY)

    groups: M2MRel['Group'] = M2MField('models.Group', related_name='group_users',
                                       through='auth_user_groups', backward_key='user_id',
                                       forward_key='group_id')
    permissions: M2MRel['Permission'] = M2MField('models.Permission', related_name='permission_users',
                                                 through='auth_user_permissions',
                                                 backward_key='user_id',
                                                 forward_key='permission_id')
    # Stonksnote
    brokers: M2MRel['Broker'] = M2MField('models.Broker', related_name='broker_users',
                                         through='trades_xuserbrokers',
                                         backward_key='user_id', forward_key='broker_id')

    author_brokers: RRel['Broker']
    author_taxs: RRel['Taxonomy']
    author_owners: RRel['Owner']
    author_equity: RRel['Equity']
    author_collections: RRel['Collection']
    author_tokens: RRel['Token']
    author_media: RRel['Media']
    author_notes: RRel['Note']
    author_trades: RRel['Trade']
    author_stash: RRel['Stash']
    author_marks: RRel['Mark']
    author_userpermissions: RRel['UserPermissions']
    options: RRel['Option']
    visitors: RRel['Visitor']
    userbrokers: RRel['UserBrokers']
    userpermissions: RRel['UserPermissions']
    oauth_accounts: RRel['OAuthAccount']
    user_stash: RRel['Stash']

    full = Manager()

    class Meta:
        table = 'auth_user'
        manager = CuratorM()

    def __str__(self):
        return modstr(self, 'id')

    @property
    def fullname(self):
        return f'{self.first_name} {self.last_name}'.strip()

    # @property
    # async def display_name(self):
    #     if self.username:
    #         return self.username
    #     elif self.fullname:
    #         return self.fullname.split()[0]
    #     else:
    #         emailname = self.email.split('@')[0]
    #         return ' '.join(emailname.split('.'))

    # @classmethod
    # def has_perm(cls, id: str, *perms):
    #     partialkey = s.CACHE_USERNAME.format('id')
    #     if red.exists(partialkey):
    #         groups = red.get(partialkey).get('groups')

    async def to_dict(self, exclude: Optional[List[str]] = None, prefetch=False) -> dict:
        """
        Converts a UserMod instance into UserModComplete. Included fields are based on UserDB +
        groups, options, and permissions.
        :param exclude:     Fields not to explicitly include
        :param prefetch:    Query used prefetch_related to save on db hits
        :return:            UserDBComplete
        """
        d = {}
        exclude = ['created_at', 'deleted_at', 'updated_at'] if exclude is None else exclude
        for field in self._meta.db_fields:
            if hasattr(self, field) and field not in exclude:
                d[field] = getattr(self, field)
                if field == 'id':
                    d[field] = str(d[field])
    
        if hasattr(self, 'groups'):
            if prefetch:
                d['groups'] = [i.name for i in self.groups]
            else:
                d['groups'] = await self.groups.all().values_list('name', flat=True)
        if hasattr(self, 'options'):
            if prefetch:
                d['options'] = {i.name: i.value for i in self.options}
            else:
                d['options'] = {
                    i.name: i.value for i in await self.options.all().only('id', 'name', 'value', 'is_active') if i.is_active
                }
        if hasattr(self, 'permissions'):
            if prefetch:
                d['permissions'] = [i.code for i in self.permissions]
            else:
                d['permissions'] = await self.permissions.all().values_list('code', flat=True)
        # ic(d)
        return d

    @classmethod
    async def get_and_cache(cls, id, *, model=False):
        """
        Get a user's cachable data and cache it for future use. Replaces data if exists.
        Similar to the dependency current_user.
        :param id:      User id as str
        :param model:   Also return the UserMod instance
        :return:        DOESN'T NEED cache.restoreuser() since data is from the db not redis.
                        The id key in the hash is already formatted to a str from UUID.
                        Can be None if user doesn't exist.
        """
        from app.auth import userdb
        
        query = UserMod.get_or_none(pk=id) \
            .prefetch_related(
                Prefetch('groups', queryset=Group.all().only('id', 'name')),
                Prefetch('options', queryset=Option.all().only('user_id', 'name', 'value')),
                Prefetch('permissions', queryset=Permission.filter(deleted_at=None).only('id', 'code'))
            )
        if userdb.oauth_account_model is not None:
            query = query.prefetch_related("oauth_accounts")
        usermod = await query.only(*userdb.select_fields)
    
        if usermod:
            user_dict = await usermod.to_dict(prefetch=True)
            partialkey = s.CACHE_USERNAME.format(id)
            red.set(partialkey, cache.prepareuser_dict(user_dict), clear=True)
        
            if model:
                return userdb.usercomplete(**user_dict), usermod
            return userdb.usercomplete(**user_dict)

    @classmethod
    async def get_data(cls, id, force_query=False, debug=False):
        """
        Get the UserDBComplete data whether it be via cache or query. Checks cache first else query.
        :param force_query: Force use query instead of checking the cache
        :param id:          User id
        :param debug:       Debug data for tests
        :return:            UserDBComplete/tuple or None
        """
        from app.auth import userdb
    
        debug = debug if s.DEBUG else False
        partialkey = s.CACHE_USERNAME.format(id)
        if not force_query and red.exists(partialkey):
            source = 'CACHE'
            user_data = cache.restoreuser_dict(red.get(partialkey))
            user = userdb.usercomplete(**user_data)
        else:
            source = 'QUERY'
            user = await UserMod.get_and_cache(id)
    
        if debug:
            return user, source
        return user

    async def get_permissions(self, perm_type: Optional[str] = None) -> list:
        """
        Collate all the permissions a user has from groups + user
        :param perm_type:   user or group
        :return:            List of permission codes to match data with
        """
        group_perms, user_perms = [], []
        groups = await self.get_groups()
    
        if perm_type is None or perm_type == 'group':
            for group in groups:
                partialkey = s.CACHE_GROUPNAME.format(group)
                if perms := red.get(partialkey):
                    group_perms += perms
                else:
                    perms = Group.get_and_cache(group)
                    group_perms += perms
                    red.set(partialkey, perms)
    
        if perm_type is None or perm_type == 'user':
            partialkey = s.CACHE_USERNAME.format(self.id)
            if user_dict := red.get(partialkey):
                user_dict = cache.restoreuser_dict(user_dict)
                user_perms = user_dict.get('permissions')
            else:
                user = await UserMod.get_and_cache(self.id)
                user_perms = user.permissions
                
        return list(set(group_perms + user_perms))

    async def add_permission(self, *perms):
        current_user_perms = await self.get_permissions(perm_type='user')
        if not perms:
            return current_user_perms
        perms = [i for i in perms if i not in current_user_perms]
        if not perms:
            return
    
        ll = []
        userperms = await Permission.filter(code__in=perms).only('id')
        if not userperms:
            return
    
        for perm in userperms:
            ll.append(UserPermissions(user=self, permission=perm, author=self))
        if ll:
            await UserPermissions.bulk_create(ll)
            return await self.get_permissions(perm_type='user')
        return current_user_perms

    async def remove_permission(self, *perms):
        current_user_perms = await self.get_permissions(perm_type='user')
        if not perms:
            return current_user_perms
        perms = [i for i in perms if i in current_user_perms]
        if perms:
            userperms = await Permission.filter(code__in=perms).only('id')
            await self.permissions.remove(*userperms)
            # final_list = list(set(current_user_perms) - set(perms))
            user = await UserMod.get_and_cache(self.id)
            return user.permissions
        return current_user_perms

    async def has_perm(self, *perms, superuser=False) -> bool:
        """
        Check if a user has as specific permission code.
        :param perms:   Permission code
        :param superuser:   Check if user has the is_superuser flag
        :return:        bool
        """
        if superuser:
            return True
        perms = list(filter(None, perms))
        perms = list(filter(valid_str_only, perms))
        if not perms:
            return False
        return set(perms) <= set(await self.get_permissions())

    async def get_groups(self, force_query=False, debug=False) -> Union[list, tuple]:
        """
        Return a user's groups as a list from the cache or not. Uses cache else query.
        :param force_query: Don't use cache
        :param debug:       Return debug data for tests
        :return:            List of groups if not debug
        """
        from app.auth import userdb
    
        debug = debug if s.DEBUG else False
        partialkey = s.CACHE_USERNAME.format(self.id)
        if not force_query and red.exists(partialkey):
            user_dict = red.get(partialkey)
            source = 'CACHE'
            user_dict = cache.restoreuser_dict(user_dict)
            user = userdb.usercomplete(**user_dict)
        else:
            source = 'QUERY'
            user = await UserMod.get_and_cache(self.id)
        if debug:
            return user.groups, source
        return user.groups

    async def add_group(self, *groups) -> Optional[list]:
        """
        Add groups to a user and update redis
        :param groups:  Groups to add
        :return:        list The user's groups
        """
        from app.auth import userdb
    
        groups = list(filter(None, groups))
        groups = list(filter(valid_str_only, groups))
        if not groups:
            return
    
        groups = await Group.filter(name__in=groups).only('id', 'name')
        if not groups:
            return
    
        await self.groups.add(*groups)
        names = await Group.filter(group_users__id=self.id) \
            .values_list('name', flat=True)
    
        partialkey = s.CACHE_USERNAME.format(self.id)
        if user_dict := red.get(partialkey):
            user_dict = cache.restoreuser_dict(user_dict)
            user = userdb.usercomplete(**user_dict)
        else:
            user = await UserMod.get_and_cache(self.id)
    
        user.groups = names
        red.set(partialkey, cache.prepareuser_dict(user.dict()))
        return user.groups

    async def remove_group(self, *groups):
        user_groups = await self.get_groups()
        groups = list(filter(valid_str_only, groups))
        if not groups:
            return user_groups
    
        for i in [x for x in groups if x in user_groups]:               # noqa
            user_groups.remove(i)
    
        await self.update_groups(user_groups)
        return user_groups

    async def has_group(self, *groups) -> bool:
        """
        Check if a user is a part of a group. If 1+ groups are given then it's all or nothing.
        :param groups:  List of group names
        :return:        bool
        """
        allgroups = await self.get_groups()
        if not groups:
            return False
        return set(groups) <= set(allgroups)

    async def update_groups(self, new_groups: list):
        from app.auth import userdb
    
        new_groups = set(filter(valid_str_only, new_groups))
        valid_groups = set(
            await Group.filter(name__in=new_groups).values_list('name', flat=True)
        )
        if not valid_groups:
            return
        existing_groups = set(await self.get_groups())
        toadd: set = valid_groups - existing_groups
        toremove: set = existing_groups - valid_groups
    
        if toadd:
            toadd_obj = await Group.filter(name__in=toadd).only('id', 'name')
            if toadd_obj:
                await self.groups.add(*toadd_obj)
    
        if toremove:
            toremove_obj = await Group.filter(name__in=toremove).only('id', 'name')
            if toremove_obj:
                await self.groups.remove(*toremove_obj)
    
        partialkey = s.CACHE_USERNAME.format(self.id)
        if user_dict := red.get(partialkey):
            user_dict = cache.restoreuser_dict(user_dict)
            user = userdb.usercomplete(**user_dict)
        else:
            user = await userdb.get_and_cache(self.id)
    
        user.groups = await self.get_groups(force_query=True)
        red.set(partialkey, cache.prepareuser_dict(user.dict()))
        return user.groups
    
    async def get_currency(self):
        # TODO: Check the cache first
        return self.currency or s.CURRENCY
    

class UserPermissions(models.Model):
    user: FKRel[UserMod] = FKField('models.UserMod', related_name='userpermissions')
    permission: FKRel['Permission'] = FKField('models.Permission', related_name='userpermissions')
    author: FKRel[UserMod] = FKField('models.UserMod', related_name='author_userpermissions')
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = 'auth_user_permissions'
        unique_together = (('user_id', 'permission_id'),)


class Group(SharedMixin, models.Model):
    name = fields.CharField(max_length=191, index=True, unique=True)
    summary = fields.TextField(default='')
    deleted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    permissions: M2MRel['Permission'] = M2MField('models.Permission', related_name='groups',
                                                 through='auth_group_permissions', backward_key='group_id')
    group_users: M2MRel['UserMod']
    
    class Meta:
        table = 'auth_group'
        manager = CuratorM()
    
    def __str__(self):
        return modstr(self, 'name')
    
    @classmethod
    async def get_and_cache(cls, group: str) -> list:
        """
        Get a group's permissions and cache it for future use. Replaces data if exists.
        Only one group must be given so each can be cached separately.
        :param group:   Group name
        :return:        list
        """
        perms = await Permission.filter(groups__name=group).values_list('code', flat=True)
        perms = perms or []
        
        if perms:
            # Save back to cache
            partialkey = s.CACHE_GROUPNAME.format(group)
            red.set(partialkey, perms, ttl=-1, clear=True)
            
            grouplist = red.exists('groups') and red.get('groups') or []
            if group not in grouplist:
                grouplist.append(group)
                red.set('groups', grouplist, clear=True)
        return perms
    
    @classmethod
    async def get_permissions(cls, *groups, debug=False) -> Union[list, tuple]:
        """
        Get a consolidated list of permissions for groups. Uses cache else query.
        :param groups:  Names of groups
        :param debug:   Return debug data for tests
        :return:        List of permissions for that group
        """
        debug = debug if s.DEBUG else False
        allperms, sources = set(), []
        for group in groups:
            partialkey = s.CACHE_GROUPNAME.format(group)
            if perms := red.get(partialkey):
                sources.append('CACHE')
            else:
                sources.append('QUERY')
                perms = await cls.get_and_cache(group)
            # ic(group, perms)
            if perms:
                allperms.update(perms)
        
        if debug:
            return list(allperms), sources
        return list(allperms)

    @classmethod
    async def create_group(cls, name: str, summary: Optional[str] = ''):
        """
        Create a group and update the cache
        """
        if await Group.get_or_none(name=name):
            return
        group = await Group.create(name=name, summary=summary)
        
        # Update cache
        if groups := red.get('groups'):
            groups.append(name)
        else:
            groups = await Group.all().values_list('name', flat=True)
        red.set('groups', groups, clear=True)
        return group
        
    
    @classmethod
    async def delete_group(cls, name: str):
        """
        Delete a group
        :param name:    Name of group
        :return:
        """
        try:
            # Delete from db
            if name:
                if group := await Group.get_or_none(name=name).only('id'):
                    await group.delete()
                    
                    # Update cache
                    partialkey = s.CACHE_GROUPNAME.format(name)
                    red.delete(partialkey)
                    if groups := red.get('groups'):
                        groups = list(filter(lambda y: y != name, groups))
                    else:
                        groups = await Group.all().values_list('name', flat=True)
                    red.set('groups', groups, clear=True)
                    return True
        except (BaseORMException, RedisError):
            raise x.ServiceError()
    
    async def update_group(self, group: UpdateGroupVM):
        """
        Update the name and summary of a group.
        :param:     Pydantic instance with fields: id, name, summary
        :return:    dict
        """
        self.name = group.name
        self.summary = group.summary
        await self.save(update_fields=['name', 'summary'])


class Permission(SharedMixin, models.Model):
    name = fields.CharField(max_length=191, unique=True)
    code = fields.CharField(max_length=30, index=True, unique=True)
    deleted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # groups: fields.ReverseRelation[Group]
    # permission_users: fields.ReverseRelation['UserMod']

    permission_users: M2MRel[UserMod]
    groups: M2MRel[Group]
    userpermissions: FKRel[UserPermissions]
    
    class Meta:
        table = 'auth_permission'
        manager = CuratorM()
    
    def __str__(self):
        return modstr(self, 'name')
    
    @classmethod
    async def add(cls, code: str, name: Optional[str] = ''):
        if not code:
            raise ValueError
        if not name:
            words = code.split('.')
            words = [i.capitalize() for i in words]
            name = ' '.join(words)
        return await cls.create(code=code, name=name)
    
    @classmethod
    async def get_groups(cls, *code) -> list:
        """
        Get the groups which contain a permission.
        :param code:    Permission code
        :return:        list
        """
        if not code:
            return []
        groups = await Group.filter(permissions__code__in=[*code]).values_list('name', flat=True)
        return list(set(groups))
    
    @classmethod
    async def update_permission(cls, perm: UpdatePermissionVM):
        if perminst := await Permission.get_or_none(pk=perm.id).only('id', 'code', 'name'):
            ll = []
            if perm.code is not None:
                ll.append('code')
                perminst.code = perm.code
            if perm.name is not None:
                ll.append('name')
                perminst.name = perm.name
            if ll:
                await perminst.save(update_fields=ll)


# Instead of inheriting from TortoiseBaseOAuthAccountModel
class OAuthAccount(SharedMixin, models.Model):
    id = fields.UUIDField(pk=True, generated=False, max_length=255)
    oauth_name = fields.CharField(max_length=255)
    # access_token = fields.CharField(max_length=255, default='')
    # expires_at = fields.IntField(default=None)
    # refresh_token = fields.CharField(max_length=255, default='')
    account_id = fields.CharField(index=True, max_length=255)
    account_email = fields.CharField(null=False, max_length=255)
    
    # Keep the related_name to "oauth_accounts". Fastapi-users uses it.
    user: FKRel[UserMod] = FKField("models.UserMod", related_name="oauth_accounts")
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = 'auth_oauth2'
        unique_together = (('oauth_name', 'account_id'),)