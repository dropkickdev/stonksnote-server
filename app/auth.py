import secrets, pytz
from datetime import datetime, timedelta
from fastapi import Response
from fastapi_users import FastAPIUsers
from fastapi.security import OAuth2PasswordBearer
from fastapi_users.authentication import JWTAuthentication
from fastapi_users.user import UserNotExists
from fastapi_users.router.reset import RESET_PASSWORD_TOKEN_AUDIENCE
from fastapi_users.router.verify import VERIFY_USER_TOKEN_AUDIENCE
from fastapi_users.utils import generate_jwt
from tortoise.exceptions import DoesNotExist

from .settings import settings as s
from .validation import *
from .authentication.models.manager import *
from .authentication.models.core import *
from .authentication.models.account import *
from .authentication.models.pydantic import *
from .authentication.Mailman import *
from .authentication.fapiusers import *




userdb = TortoiseUDB(UserDB, UserMod, include=['timezone', 'display', 'avatar'], alt=UserDBComplete)
jwtauth = JWTAuthentication(secret=s.SECRET_KEY, lifetime_seconds=s.ACCESS_TOKEN_EXPIRE)
fusers = FastAPIUsers(userdb, [jwtauth], User, UserCreate, UserUpdate, UserDB)

current_user = fusers.current_user()
tokenonly = OAuth2PasswordBearer(tokenUrl='token')

REFRESH_TOKEN_KEY = 'refresh_token'         # Don't change this. This is hard-coded as a variable.


async def register_callback(user: UserDB, _: Response):
    # TODO: Add default collections
    # TODO: Add defalt tags
    # TODO: Create display field value
    usermod = await UserMod.get_or_none(pk=user.id).only('id', 'display')
    
    # Grab email name
    usermod.display = ''.join((user.email.split('@')[0]).split('.'))
    await usermod.save(update_fields=['display'])
    
    ic(f'Registration complete by {user.email}')


def after_verification_request(user: UserDB, token: str, _: Response):
    ic(f'Requested verification token by {user.email}: {token}')


def verification_complete(user: UserDB, _: Response):
    ic(f'Verification completed for {user.email}')


def after_forgot_password(user: UserDB, token: str, _: Response):
    ic(f'Password change request for {user.email}: {token}')


def after_reset_password(user: UserDB, _: Response):
    ic(f'Password reset complete for {user.email}')


async def generate_token(user: UserDB, *, create: bool = True,
                         token: Optional[Token] = None, usermod: Optional[UserMod] = None):
    usermod = usermod or await UserMod.get(pk=user.id).only('id')
    token_hash = secrets.token_hex(nbytes=32)
    expires = datetime.now(tz=pytz.UTC) + timedelta(seconds=s.REFRESH_TOKEN_EXPIRE)
    if create:
        await Token.create(token=token_hash, expires=expires, author=usermod, is_blacklisted=False)
    else:
        token = token or (
            await Token.get(author=usermod, is_blacklisted=False).only('id', 'token', 'expires')
        )
        token.token = token_hash
        token.expires = expires
        await token.save(update_fields=['token', 'expires'])
        
    return {
        'value': token_hash,
        'expires': expires,
    }

async def create_oauth(provider: str, id: str, email: str, usermod: UserMod):
    if not (email == EmailStr(email)):
        raise ValueError('Not a valid email')
    oauth_d = dict(oauth_name=provider, account_id=id, account_email=email, user=usermod)
    return await OAuthAccount.create(**oauth_d)

# async def register_callback(user: UserDB, _: Response):
#     """
#     Send an email containing a link the user can use to verify their account. This email directly
#     shows the success/fail notice upon completion.
#     """
#     # Set the groups for this new user
#     groups = await Group.filter(name__in=s.USER_GROUPS)
#     user = await UserMod.get(pk=user.id).only('id', 'email')
#     await user.groups.add(*groups)
#
#
#     if s.VERIFY_EMAIL:
#         await send_registration_email(
#             user,
#             'app/authentication/templates/emails/account/registration_verify_text.jinja2',
#             'app/authentication/templates/emails/account/registration_verify_html.jinja2'
#         )
#
#
# async def send_registration_email(user: UserMod, text_path: str, html_path: Optional[str] = None,
#                                   debug=False):
#     debug = debug if s.DEBUG else False
#     try:
#         user = await fapiuser.get_user(user.email)
#     except UserNotExists:
#         return
#
#     if not user.is_verified and user.is_active:
#         token_data = {
#             "user_id": str(user.id),
#             "email": user.email,
#             "aud": VERIFY_USER_TOKEN_AUDIENCE,
#         }
#         token = generate_jwt(
#             data=token_data,
#             secret=s.SECRET_KEY_EMAIL,
#             lifetime_seconds=s.VERIFY_EMAIL_TTL,
#         )
#         context = {
#             'verify_code': token,
#             'fake_code': secrets.token_hex(32),
#             'url': f'{s.SITE_URL}/authentication/verify?t={token}',
#             'site_name': s.SITE_NAME,
#             'title': 'Email Verification'
#         }
#
#         # Prepare the email
#         mailman = Mailman(recipient=user.email)
#         mailman.setup_email(subject=context['title'])
#         mailman.send(text=text_path, html=html_path, context=context)
#
#
# async def send_password_email(user: UserMod, text_path: str, html_path: Optional[str] = None,
#                               reset_form_url=None, debug=False):
#     debug = debug if s.DEBUG else False
#     reset_form_url = reset_form_url or s.FORM_RESET_PASSWORD
#     try:
#         user = await fapiuser.get_user(user.email)
#     except UserNotExists:
#         return
#
#     if user.is_active and user.is_verified:
#         token_data = {
#             "user_id": str(user.id),
#             "aud": RESET_PASSWORD_TOKEN_AUDIENCE
#         }
#         token = generate_jwt(
#             data=token_data,
#             secret=s.SECRET_KEY_EMAIL,
#             lifetime_seconds=s.VERIFY_EMAIL_TTL,
#         )
#         context = {
#             'verify_code': token,
#             'fake_code': secrets.token_hex(32),
#             # 'url': f'{s.SITE_URL}/authentication/reset-password?t={token}',
#             'url': f'{s.SITE_URL}{reset_form_url}?t={token}',
#             'site_name': s.SITE_NAME,
#             'title': 'Change Password'
#         }
#
#         # Prepare the email
#         mailman = Mailman(recipient=user.email)
#         mailman.setup_email(subject=context['title'])
#         mailman.send(text=text_path, html=html_path, context=context)
#
#         if debug:
#             return context.get('verify_code', None)
#
#
# def generate_refresh_token(nbytes: int = 32):
#     return secrets.token_hex(nbytes=nbytes)


# TESTME: Test manually
async def create_refresh_token(user: UserDB, usermod: Optional[UserMod] = None) -> dict:
    """
    Create and save a new refresh token
    :param user     Pydantic model for the user
    :param usermod  UserMod if there is one
    """
    return await generate_token(user, usermod=usermod)

# TESTME: Test manually
async def update_refresh_token(user: UserDB, token: Optional[Token] = None,
                               usermod: Optional[UserMod] = None) -> dict:
    """
    Update the refresh token of the user
    :param user     Pydantic model for the user
    :param token    Use an existing Token instance if there is one and save a query
    :param usermod  UserMod if there is one
    """
    return await generate_token(user, create=False, token=token, usermod=usermod)


# def renew_refresh_token(user: UserDB, response: Response, *, usermod: Optional[UserMod] = None,
#                         token: Optional[Token] = None):
#     try:
#         # Update
#         token_dict = await generate_token(user, create=False, token=token, usermod=usermod)
#     except DoesNotExist:
#         # Create
#         token_dict = await generate_token(user, usermod=usermod)
# #
#     # Generate a new cookie
#     cookie = refresh_cookie(REFRESH_TOKEN_KEY, token_dict)
#     response.set_cookie(**cookie)
# #
#     return token_dict


def refresh_cookie(name: str, token: dict, **kwargs):
    if token['expires'] <= datetime.now(tz=pytz.UTC):
        raise ValueError('Cookie expires date must be greater than the date now')
    
    cookie_data = {
        'key': name,
        'value': token['value'],
        'httponly': True,
        'expires': s.REFRESH_TOKEN_EXPIRE,
        'path': '/',
        **kwargs,
    }
    if not s.DEBUG:
        cookie_data.update({
            'secure': True
        })
    return cookie_data


def time_difference(expires: datetime, now: datetime = None):
    """Get the diff between 2 dates"""
    now = now or datetime.now(tz=pytz.UTC)
    diff = expires - now
    return {
        'days': diff.days,
        'hours': int(diff.total_seconds()) // 3600,
        'minutes': int(diff.total_seconds()) // 60,
        'seconds': int(diff.total_seconds()),
    }


def expires(expires: datetime, units: str = 'minutes'):
    diff = time_difference(expires)
    return diff[units]


