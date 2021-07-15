import jwt, secrets
from typing import Optional, cast
from datetime import datetime, timedelta
from tld import get_tld
from tld.exceptions import TldBadUrl
from urllib.parse import urlparse
from operator import itemgetter
from fastapi import APIRouter, Response, Depends, HTTPException, status, Body, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.router.common import ErrorCode
from fastapi_users.router.verify import VERIFY_USER_TOKEN_AUDIENCE
from fastapi_users.router.reset import RESET_PASSWORD_TOKEN_AUDIENCE
from fastapi_users.utils import JWT_ALGORITHM
from fastapi_users.user import UserNotExists, UserAlreadyVerified
from fastapi_users.password import get_password_hash
from tortoise.exceptions import DoesNotExist
from starlette.responses import RedirectResponse
from pydantic import EmailStr, UUID4
from google.oauth2 import id_token
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests

from app import ic, red, exceptions as x
from app.settings import settings as s
from app.auth import (
    userdb, fusers, jwtauth, current_user, User, UserDB, Token, UserMod, OAuthAccount, Option,
    REFRESH_TOKEN_KEY, ResetPasswordVM,
    register_callback, after_verification_request, verification_complete,
    after_forgot_password, after_reset_password,
    update_refresh_token, create_refresh_token,
    # refresh_cookie, send_password_email,
    expires, generate_token, refresh_cookie, create_oauth,
    # renew_refresh_token
    finish_account_setup,
)
from app.exceptions import PermissionDenied
from app.fixtures.datastore import options_dict



authrouter = APIRouter()
authrouter.include_router(fusers.get_register_router(register_callback))
authrouter.include_router(fusers.get_verify_router(s.SECRET_KEY_EMAIL,
                                                   after_verification_request=after_verification_request,
                                                   after_verification=verification_complete))
authrouter.include_router(
    fusers.get_reset_password_router(s.SECRET_KEY_EMAIL,
                                     after_forgot_password=after_forgot_password,
                                     after_reset_password=after_reset_password
    )
)


# For reference only. Do not use.
# authrouter.include_router(fapiuser.get_auth_router(jwtauth))    # login, logout
# authrouter.include_router(fapiuser.get_verify_router(s.SECRET_KEY, s.VERIFY_EMAIL_TTL))
# router.include_router(fapi_user.get_users_router(user_callback))
# authrouter.include_router(fapiuser.get_reset_password_router(
#     s.SECRET_KEY_TEMP,
#     after_forgot_password=password_after_forgot,
#     after_reset_password=password_after_reset)
# )



@authrouter.get('/reload_user_data')
async def get_user_data(_: Response, user=Depends(current_user)):
    # ic(user)
    return {
        'display': user.display,
        'username': user.username,
        'email': user.email,
        'is_verified': user.is_verified,
        'avatar': user.avatar
    }


# TODO: ATM you will have to test this manually.
@authrouter.post('/token')
async def new_access_token(response: Response, refresh_token: Optional[str] = Cookie(None)):
    """
    Create a new access_token with the refresh_token cookie. If the refresh_token is still valid
    then a new access_token is generated. If it's expired then it is equivalent to being logged out.

    The refresh_token is renewed for every login to prevent accidental logouts.
    """
    try:
        # ic(refresh_token)
        if refresh_token is None:
            raise PermissionDenied()
        
        # TODO: Access the cache instead of querying it
        token = await Token.get_or_none(token=refresh_token, is_blacklisted=False) \
            .only('id', 'token', 'expires', 'author_id')
        
        if not token:
            raise PermissionDenied()
        
        user = await userdb.get(token.author_id)
        # ic(type(user), user)
        
        mins = expires(token.expires)
        # ic(type(mins), mins)
        # mins = 1
        if mins <= 0:
            raise PermissionDenied('Refresh token expired')
        elif mins <= s.REFRESH_TOKEN_CUTOFF:
            ic('Remaining mins:', mins, '/', s.REFRESH_TOKEN_CUTOFF)
            # refresh the refresh_token anyway before it expires
            # renew_refresh_token(user, response, token=token)
            try:
                token_dict = await update_refresh_token(user, token=token)
            except DoesNotExist:
                token_dict = await create_refresh_token(user)

            # Generate a new cookie
            cookie = refresh_cookie(REFRESH_TOKEN_KEY, token_dict)
            response.set_cookie(**cookie)
        
        return await jwtauth.get_login_response(user, response)
    
    except PermissionDenied as e:
        ic(e.message)
        # Similar to logging out
        del response.headers['authorization']
        response.delete_cookie(REFRESH_TOKEN_KEY)
        raise x.PermissionDenied()


@authrouter.post('/google/login')
async def google_login(response: Response, token: str = Body(...)):
    try:
        data = id_token.verify_oauth2_token(token, requests.Request(), s.GOOGLE_CLIENT_ID)
        # ic(data)
        email, sub, name, picture = itemgetter('email', 'sub', 'name', 'picture')(data)
        
        if await UserMod.exists(email=email):
            # User exists
            usermod = await UserMod.get(email=email).only('id', 'is_verified', 'display',
                                                          'avatar', 'username')
            if not usermod.avatar:
                usermod.avatar = picture
                await usermod.save(update_fields=['avatar'])
            else:
                try:
                    _ = get_tld(usermod.avatar, as_object=True)
                    if urlparse(usermod.avatar) != urlparse(picture):
                        usermod.avatar = picture
                        await usermod.save(update_fields=['avatar'])
                except TldBadUrl:
                    pass
            
            if not await OAuthAccount.exists(oauth_name='google', user=usermod):
                await create_oauth('google', sub, email, usermod)
        else:
            # New user
            filler = secrets.token_hex(nbytes=32)
            display = ''.join((email.split('@')[0]).split('.'))
            usermod_d = dict(email=email, hashed_password=filler, is_verified=True,
                             avatar=picture, display=display)
            usermod = await UserMod.create(**usermod_d)
            await create_oauth('google', sub, email, usermod)

            # Setup the rest of the requirements
            await finish_account_setup(usermod)

        user = UserDB(**await usermod.to_dict())
        # user = UserDB(id=usermod.id, is_verified=True, display=usermod.display)

        # renew_refresh_token(user, response, usermod=usermod)
        try:
            token_dict = await update_refresh_token(user, usermod=usermod)
        except DoesNotExist:
            token_dict = await create_refresh_token(user, usermod=usermod)

        # Generate a new cookie
        cookie = refresh_cookie(REFRESH_TOKEN_KEY, token_dict)
        response.set_cookie(**cookie)

        # Save to cache
        _, usermod = await UserMod.get_and_cache(user.id, model=True)

        data = {
            'display': usermod.display,
            'username': usermod.username,
            'email': usermod.email,
            'is_verified': usermod.is_verified,
            'avatar': usermod.avatar,
            'timezone': usermod.timezone,
            **await jwtauth.get_login_response(user, response),
        }
        ic(data)
        return data
    except GoogleAuthError:
        raise GoogleAuthError()



@authrouter.post("/login")
async def login(response: Response, credentials: OAuth2PasswordRequestForm = Depends()):
    # user = await fusers.db.authenticate(credentials)
    user = await userdb.authenticate(credentials)

    if user is None or not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        )
    
    # renew_refresh_token(user, response)
    try:
        token_dict = await update_refresh_token(user)
    except DoesNotExist:
        token_dict = await create_refresh_token(user)

    # Generate a new cookie
    cookie = refresh_cookie(REFRESH_TOKEN_KEY, token_dict)
    response.set_cookie(**cookie)

    # Save to cache
    _, usermod = await UserMod.get_and_cache(user.id, model=True)
    
    data = {
        'display': usermod.display,
        'username': usermod.username,
        'email': usermod.email,
        'is_verified': usermod.is_verified,
        'avatar': usermod.avatar,
        'timezone': usermod.timezone,
        **await jwtauth.get_login_response(user, response),
    }
    ic(data)
    if not user.is_verified:
        data.update(dict(details='User is not verified yet so user cannot log in.'))
    # ic(data)
    return data


@authrouter.get("/logout")
async def logout(response: Response):
    """
    Logout the user by deleting all tokens.
    """
    del response.headers['authorization']
    response.delete_cookie('refresh_token')
    return



# @authrouter.post('/facebook/login')
# async def facebook_login(response: Response, data: dict = Body(...)):
#     # ic(type(data), data)
#     email, userID, name, picture = itemgetter('email', 'userID', 'name', 'picture')(data)
#
#     try:
#         if await UserMod.exists(email=email):
#             # User exists
#             usermod = await UserMod.get(email=email).only('id', 'is_verified')
#             if not await OAuthAccount.exists(oauth_name='facebook', user=usermod):
#                 await create_oauth('facebook', userID, email, usermod)
#         else:
#             # New user
#             filler = generate_token().get('value')
#             usermod_d = dict(email=email, hashed_password=filler, is_verified=True, avatar=picture)
#             usermod = await UserMod.create(**usermod_d)
#             await create_oauth('facebook', userID, email, usermod)
#
#         token = generate_token()
#         cookie = refresh_cookie('refresh_token', token)
#         response.set_cookie(**cookie)
#
#         user = User(id=usermod.id, is_verified=True)
#         d = {
#             **await jwtauth.get_login_response(user, response),
#             'is_verified': user.is_verified,
#             'avatar': picture,
#             # 'display': user.display,
#         }
#         return d
#     except Exception as e:
#         ic(e)







#
# @authrouter.get("/verify")
# async def verify(_: Response, t: Optional[str] = None, debug: bool = False):
#     """
#     Email verification sent for new registrations then redirect to success/fail notice.
#     In the docs this was POST (via react) but I changed it to use GET (via email).
#     """
#     debug = debug if s.DEBUG else False
#     headers = s.NOTICE_HEADER
#
#     if not t:
#         if debug:
#             return False
#         return RedirectResponse(url=s.NOTICE_TOKEN_BAD, headers=headers)
#
#     try:
#         data = jwt.decode(t, s.SECRET_KEY_EMAIL, audience=VERIFY_USER_TOKEN_AUDIENCE,
#                           algorithms=[JWT_ALGORITHM])
#         user_id = data.get("user_id")
#         email = cast(EmailStr, data.get("email"))
#
#         if user_id is None:
#             if debug:
#                 return False
#             return RedirectResponse(url=s.NOTICE_TOKEN_BAD, headers=headers)
#
#         user_check = UserDB(**(await fapiuser.get_user(email)).dict())
#         if str(user_check.id) != user_id:
#             if debug:
#                 return False
#             return RedirectResponse(url=s.NOTICE_TOKEN_BAD, headers=headers)
#
#         # Set is_verified as True
#         user = await fapiuser.verify_user(user_check)
#
#         if debug:
#             return user
#         name = user.username or email
#         return RedirectResponse(url=f'{s.NOTICE_VERIFY_REGISTER_OK}?name={name}', headers=headers)
#
#     except jwt.exceptions.ExpiredSignatureError:
#         if debug:
#             return False
#         return RedirectResponse(url=s.NOTICE_TOKEN_EXPIRED, headers=headers)
#
#     except (jwt.PyJWTError, UserNotExists, ValueError):
#         if debug:
#             return False
#         return RedirectResponse(url=s.NOTICE_TOKEN_BAD, headers=headers)
#
#     except UserAlreadyVerified:
#         if debug:
#             return False
#         return RedirectResponse(url=s.NOTICE_USER_ALREADY_VERIFIED, headers=headers)
#
#
# @authrouter.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
# async def forgot_password(_: Response, email: EmailStr = Body(...), debug: bool = Body(False)):
#     """Sends an email containing the token to use to access the form to change their password."""
#     user = await userdb.get_by_email(email)
#     if user is None or not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#         )
#
#     # TODO: Queue this with celery
#     return await send_password_email(
#         user,
#         'app/authentication/templates/emails/account/password_verify_text.jinja2',
#         'app/authentication/templates/emails/account/password_verify_html.jinja2',
#         debug=debug
#     )
#
#
# @authrouter.post("/reset-password")
# async def reset_password(_: Response, formdata: ResetPasswordVM):
#     token = formdata.token
#     password = formdata.password
#
#     try:
#         data = jwt.decode(token, s.SECRET_KEY_EMAIL, audience=RESET_PASSWORD_TOKEN_AUDIENCE,
#                           algorithms=[JWT_ALGORITHM])
#         user_id = data.get("user_id")
#         if user_id is None:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
#             )
#
#         try:
#             user_uuid = UUID4(user_id)
#         except ValueError:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
#             )
#
#         user = await userdb.get(user_uuid)
#         if user is None or not user.is_active:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
#             )
#
#         user.hashed_password = get_password_hash(password)
#         # Use UserDB in order to remove the extra attributes generated by UserDBComplete
#         user = UserDB(**user.dict())
#         await userdb.update(user)
#         return True
#     except jwt.PyJWTError:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
#         )


# @authrouter.delete('/{id}', dependencies=[Depends(fapiuser.get_current_superuser)])
# async def delete_user(userid: UUID4):
#     """
#     Soft-deletes the user instead of hard deleting them.
#     """
#     try:
#         user = await UserMod.get(id=userid).only('id', 'deleted_at')
#         user.deleted_at = datetime.now(tz=pytz.UTC)
#         await user.save(update_fields=['deleted_at'])
#         return True
#     except DoesNotExist:
#         raise status.HTTP_404_NOT_FOUND


