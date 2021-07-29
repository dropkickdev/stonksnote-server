import random
from fastapi import APIRouter, FastAPI
from fastapi_users.user import get_create_user
from pydantic import EmailStr
from tortoise.transactions import in_transaction

from app import ic
from .datastore import options_dict, taxo_heads, taxo_global
from app.settings import settings as s
from app.auth import userdb, UserDB, UserCreate, UserMod, UserPermissions, Group, Permission, \
    Option, finish_account_setup, Taxonomy
from tests.app.data import VERIFIED_EMAIL_DEMO, UNVERIFIED_EMAIL_DEMO
from app.fixtures.permissions import ContentGroup, AccountGroup, StaffGroup, AdminGroup, \
    NoaddGroup, permission_set, full, banning, group_set



app = FastAPI()
fixturerouter = APIRouter()

perms = {
    'ContentGroup': ContentGroup,
    'AccountGroup': AccountGroup,
    'StaffGroup': StaffGroup,
    'AdminGroup': AdminGroup,
    'NoaddGroup': NoaddGroup,
}
enchance_only_perms = ['foo.delete', 'foo.hard_delete']


@fixturerouter.get('/all', summary='Runs everything in the correct order')
async def init_auth():
    try:
        async with in_transaction():
            ll = [
                await init(),
                await create_options(),
                await create_users(),
                await create_taxo(),
            ]
        return ll
    except Exception as e:
        ic(e)


@fixturerouter.get('/init', summary="Permissions, Groups, and Assignments of each")
async def init():
    try:
        ll = []
        # Create permissions
        for key, val in permission_set.items():
            for app in val:
                if key == 'full':
                    for perm in full:
                        code = f'{app}.{perm}'
                        ll.append(
                            Permission(name=f'{app.capitalize()} {perm.capitalize()}', code=code)
                        )
                elif key == 'banning':
                    for perm in banning:
                        code = f'{app}.{perm}'
                        ll.append(
                            Permission(name=f'{app.capitalize()} {perm.capitalize()}', code=code)
                        )
        await Permission.bulk_create(ll)
        
        # Create groups
        ll = []
        for group in group_set:
            ll.append(Group(name=group))
        await Group.bulk_create(ll)
        
        # Assign perms to groups
        grouplist = await Group.all().only('id', 'name')
        permlist = await Permission.all().only('id', 'code')
        perm_dict = {i.code: i for i in permlist}
        group_dict = {i.name: i for i in grouplist}
        
        ll = []
        groupname = 'AccountGroup'
        for app, permlist in AccountGroup.items():
            for perm in permlist:
                code = f'{app}.{perm}'
                to_add = perm_dict.get(code)
                ll.append(to_add)
        group = group_dict.get(groupname)
        await group.permissions.add(*ll)
        await Group.get_and_cache(groupname)

        ll = []
        groupname = 'ContentGroup'
        for app, permlist in ContentGroup.items():
            for perm in permlist:
                code = f'{app}.{perm}'
                to_add = perm_dict.get(code)
                ll.append(to_add)
        group = group_dict.get(groupname)
        await group.permissions.add(*ll)
        await Group.get_and_cache(groupname)

        ll = []
        groupname = 'StaffGroup'
        for app, permlist in StaffGroup.items():
            for perm in permlist:
                code = f'{app}.{perm}'
                to_add = perm_dict.get(code)
                ll.append(to_add)
        group = group_dict.get(groupname)
        await group.permissions.add(*ll)
        await Group.get_and_cache(groupname)

        ll = []
        groupname = 'AdminGroup'
        for app, permlist in AdminGroup.items():
            for perm in permlist:
                code = f'{app}.{perm}'
                to_add = perm_dict.get(code)
                ll.append(to_add)
        group = group_dict.get(groupname)
        await group.permissions.add(*ll)
        await Group.get_and_cache(groupname)

        ll = []
        groupname = 'NoaddGroup'
        for app, permlist in NoaddGroup.items():
            for perm in permlist:
                code = f'{app}.{perm}'
                to_add = perm_dict.get(code)
                ll.append(to_add)
        group = group_dict.get(groupname)
        await group.permissions.add(*ll)
        await Group.get_and_cache(groupname)
        
        return 'SUCCESS: Init'
    except Exception:
        return 'ERROR'


@fixturerouter.get('/options', summary='Create global options. User options will be inserted '
                                       'later.')
async def create_options():
    try:
        # users = await UserMod.all().only('id')
        # if not users:
        #     return 'foo'
        ll = []
        for cat, data in options_dict.items():
            for name, val in data.items():
                # if cat == 'user':
                #     for user in users:
                #         ll.append(Option(name=name, value=val, user_id=user.id))
                if cat == 'site':
                    ll.append(Option(name=name, value=val))
                elif cat == 'admin':
                    ll.append(Option(name=name, value=val, admin_only=True))
        await Option.bulk_create(ll)
        return 'SUCCESS: Options'
    except Exception:
        return 'ERROR'


@fixturerouter.get('/users', summary="Create users")
async def create_users():
    # # Generate random email
    # with open('/usr/share/dict/cracklib-small', 'r') as w:
    #     words = w.read().splitlines()
    # random_word = random.choice(words)
    # host = random.choice(['gmail', 'yahoo', 'amazon', 'yahoo', 'microsoft', 'google'])
    # tld = random.choice(['org', 'com', 'net', 'io', 'com.ph', 'co.uk'])
    # email = f'{random_word}@{host}.{tld}'
    # from app.app import userdb
    
    async with in_transaction():
        groups = await Group.filter(name__in=s.USER_GROUPS)
        
        # User 1
        userdata = UserCreate(email=EmailStr(VERIFIED_EMAIL_DEMO), password='pass123')
        create_user = get_create_user(userdb, UserDB)
        created_user = await create_user(userdata, safe=True)

        user = await UserMod.get(pk=created_user.id)
        user.is_verified = True
        user.is_superuser = True
        await user.save()
        await user.groups.add(*groups)
        user = await finish_account_setup(user)

        # Perms for User 1
        ll = []
        userperms = await Permission.filter(code__in=enchance_only_perms).only('id')
        for perm in userperms:
            ll.append(UserPermissions(user=user, permission=perm, author=user))
        await UserPermissions.bulk_create(ll)
        ret = user

        # User 2
        userdata = UserCreate(email=EmailStr(UNVERIFIED_EMAIL_DEMO), password='pass123')
        create_user = get_create_user(userdb, UserDB)
        created_user = await create_user(userdata, safe=True)
        user = await UserMod.get(pk=created_user.id)
        await user.groups.add(*groups)
        await finish_account_setup(user)

        # Dev users
        for num in range(1, 4):
            host = random.choice(['gmail', 'yahoo', 'amazon', 'yahoo', 'microsoft', 'google'])
            tld = random.choice(['org', 'com', 'net', 'io', 'com.ph', 'co.uk'])
            userdata = UserCreate(email=EmailStr(f'devuser-{num}@{host}.{tld}'),
                                  password='pass123')
            create_user = get_create_user(userdb, UserDB)
            created_user = await create_user(userdata, safe=True)
            user = await UserMod.get(pk=created_user.id)
            user.is_verified = True
            await user.save()
            await user.groups.add(*groups)
            await finish_account_setup(user)
    
        # Tests use this ret so keep it as is (don't make it a succcess string)
        return ret


@fixturerouter.get('/taxo', summary='Taxonomy items')
async def create_taxo():
    try:
        async with in_transaction():
            usermod = await UserMod.get(email=VERIFIED_EMAIL_DEMO).only('id')
            
            ll = []
            for i in taxo_heads:
                ll.append(Taxonomy(name=i, is_global=True, author=usermod, tier='base'))
            await Taxonomy.bulk_create(ll)
            
            taxos = await Taxonomy.all().only('id', 'name')
            ll = []
            for ins in taxos:
                if data_list := taxo_global.get(ins.name, None):
                    for i in data_list:
                        if isinstance(i, dict):
                            # For dict
                            ll.append(Taxonomy(**i, author=usermod, parent=ins, tier=ins.name))
                        elif isinstance(i, (str, int, float)):
                            # For str, int, float
                            ll.append(Taxonomy(name=i, is_global=True, author=usermod,
                                               parent=ins, tier=ins.name))
            await Taxonomy.bulk_create(ll)
            
        return 'SUCCESS: Taxo'
    except Exception as e:
        ic(e)




# @router.get('/testing')
# async def testing():
#     try:
#         # rtoken = await Token.filter(id__in=[1,2]).update(is_blacklisted=False)
#         rtoken = await Token.get(id=1).only('id')
#         rtoken.is_blacklisted=True
#         await rtoken.save(update_fields=['is_blacklisted'])
#         return rtoken
#     except DoesNotExist:
#         return 'ERROR

