from typing import List, Union, Optional
from pydantic import BaseModel, Field, validator, EmailStr, SecretStr

from app import ic
from app.settings import settings as s



class CommonVM:
    @staticmethod
    def not_empty(val):
        if isinstance(val, str):
            val = val.strip()
        if isinstance(val, list):
            val = list(filter(None, val))
        if not val:
            raise ValueError('Value cannot be empty.')
        return val


class CreatePermissionVM(BaseModel):
    code: str = Field(..., min_length=3, max_length=20)
    name: str = Field(..., max_length=191)

    @validator('code')
    def notempty(cls, val):
        return CommonVM.not_empty(val)
    

class UpdatePermissionVM(CreatePermissionVM):
    id: int


class CreateGroupVM(BaseModel):
    name: str = Field(..., max_length=20)
    summary: str = Field('', max_length=191)
    
    @validator('name')
    def notempty(cls, val):
        return CommonVM.not_empty(val)


class UpdateGroupVM(CreateGroupVM):
    id: int


class UserPermissionVM(BaseModel):
    # User id will be taken from access_token
    codes: Union[str, List[str]]

    @validator('codes')
    def notempty(cls, val):
        return CommonVM.not_empty(val)


class GroupPermissionVM(BaseModel):
    name: str
    codes: Union[str, List[str]]

    @validator('name', 'codes')
    def notempty(cls, val):
        return CommonVM.not_empty(val)


class ResetPasswordVM(BaseModel):
    token: str
    password: str


class UniqueFieldsRegistrationVM(BaseModel):
    email: EmailStr
    username: str = Field('', min_length=s.USERNAME_MIN)
    password: SecretStr = Field(..., min_length=s.PASSWORD_MIN)