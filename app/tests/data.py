import importlib
from app import ic
from app.fixtures.permissions import AccountGroup, ContentGroup, StaffGroup, NoaddGroup



VERIFIED_EMAIL_DEMO = 'en.chance@gmail.com'
VERIFIED_ID_DEMO = 'abfb2e64-4f10-4d68-8104-c117a86635dc'
ACCESS_TOKEN_DEMO = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYWJmYjJlNjQtNGYxMC00ZDY4LTgxMDQtYzExN2E4NjYzNWRjIiwiYXVkIjoiZmFzdGFwaS11c2VyczphdXRoIiwiZXhwIjoxNjUzNzMzNzk0fQ.lzCatKcTVKTs7HKBvjyBEIOIcwhAaCfgUGVRMM9DrpA'
UNVERIFIED_EMAIL_DEMO = 'unverified@gmail.com'

EMAIL_VERIFICATION_TOKEN_DEMO = ''
PASSWORD_RESET_TOKEN_DEMO = ''
EMAIL_VERIFICATION_TOKEN_EXPIRED = ''


accountperms = []
groupname = 'AccountGroup'
for app, permlist in AccountGroup.items():
    for perm in permlist:
        code = f'{app}.{perm}'
        accountperms.append(code)

contentperms = []
groupname = 'ContentGroup'
for app, permlist in ContentGroup.items():
    for perm in permlist:
        code = f'{app}.{perm}'
        contentperms.append(code)

staffperms = []
groupname = 'StaffGroup'
for app, permlist in StaffGroup.items():
    for perm in permlist:
        code = f'{app}.{perm}'
        staffperms.append(code)

noaddperms = []
groupname = 'NoaddGroup'
for app, permlist in NoaddGroup.items():
    for perm in permlist:
        code = f'{app}.{perm}'
        noaddperms.append(code)
