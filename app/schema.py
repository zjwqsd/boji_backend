from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SubUserSchema(BaseModel):
    id: int
    user_id: Optional[str]
    nickname: Optional[str]
    email: Optional[str]
    email_verified: bool

    class Config:
        from_attributes = True  # 兼容 SQLAlchemy ORM

class UserSchema(BaseModel):
    id: int
    user_id: Optional[str]
    nickname: Optional[str]
    email: str
    email_verified: bool
    sub_users: List[SubUserSchema] = []

    class Config:
        from_attributes = True

class UserPDFPermissionCreate(BaseModel):
    user_id: int
    pdf_id: int
    has_access: Optional[bool] = True  # 默认允许访问

class UserCategoryPermissionCreate(BaseModel):
    user_id: int
    category_id: int
    has_access: Optional[bool] = True  # 默认允许访问

class UserPDFPermissionResponse(BaseModel):
    id: int
    user_id: int
    pdf_id: int
    has_access: bool
    created_at: datetime

    class Config:
        from_attributes = True  # 兼容 SQLAlchemy ORM
        
class HouseholdSchema(BaseModel):
    id: int
    name: str
    code: str
    category2: str
    description: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True

class CategoryGroupSchema(BaseModel):
    category2: str
    households: List[HouseholdSchema]