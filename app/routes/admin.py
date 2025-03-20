from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.utils import verify_super_admin, generate_user_id
from typing import List
from app.schema import UserSchema   # 导入 UserSchema
from app.schema import UserPDFPermissionCreate, UserPDFPermissionResponse
from app.models import UserPDFPermission, PDFItem

router = APIRouter(prefix="/admin", tags=["Admin"])

# 🔹 依赖项：检查是否是超级用户
def super_admin_auth(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证失败，缺少 Bearer 令牌")
    
    token = authorization.split(" ")[1]
    return verify_super_admin(token)  # 验证超级用户身份

class AssignSubUserRequest(BaseModel):
    parent_user_id: str  # 绑定的普通用户 ID

@router.post("/assign-sub-user")
def assign_sub_user(request: AssignSubUserRequest, db: Session = Depends(get_db), admin=Depends(super_admin_auth)):
    parent_user = db.query(User).filter(User.user_id == request.parent_user_id, User.is_sub_user == False).first()
    if not parent_user:
        raise HTTPException(status_code=404, detail="用户不存在或者无法绑定附属用户")

    # 生成唯一 user_id
    sub_user_id = generate_user_id()
    while db.query(User).filter(User.user_id == sub_user_id).first():
        sub_user_id = generate_user_id()

    sub_user = User(
        user_id=sub_user_id, 
        is_sub_user=True, 
        parent_id=parent_user.id,
        email_verified=False,
        address = parent_user.address,
        company = parent_user.company,
        password = parent_user.password,
    )
    db.add(sub_user)
    db.commit()
    return {"message": "附属用户已创建", "sub_user_id": sub_user.user_id}


@router.get("/users_with_subs", response_model=List[UserSchema])
def get_users_with_subs(db: Session = Depends(get_db),admin=Depends(super_admin_auth)):
    # 查询所有主用户（is_sub_user=False），并预加载 sub_users 关系
    users = db.query(User).filter(User.is_sub_user == False).all()
    return users  # FastAPI 会自动转换为 JSON

@router.post("/permissions", response_model=UserPDFPermissionResponse)
def add_pdf_permission(permission_data: UserPDFPermissionCreate, db: Session = Depends(get_db), admin=Depends(super_admin_auth)):
    # 检查用户是否存在
    user = db.query(User).filter(User.id == permission_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查 PDF 是否存在
    pdf = db.query(PDFItem).filter(PDFItem.id == permission_data.pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF 文件不存在")

    # 检查权限是否已经存在
    existing_permission = (
        db.query(UserPDFPermission)
        .filter(
            UserPDFPermission.user_id == permission_data.user_id,
            UserPDFPermission.pdf_id == permission_data.pdf_id,
        )
        .first()
    )
    if existing_permission:
        raise HTTPException(status_code=400, detail="该用户已经拥有该 PDF 的访问权限")

    # 创建新权限
    new_permission = UserPDFPermission(
        user_id=permission_data.user_id,
        pdf_id=permission_data.pdf_id,
        has_access=permission_data.has_access
    )
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)

    return new_permission


@router.get("/permissions/user/{user_id}", response_model=List[UserPDFPermissionResponse])
def get_user_permissions(user_id: int, db: Session = Depends(get_db)):
# 查询用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 如果是附属用户，查询主用户的权限
    if user.is_sub_user and user.parent_id:
        user_id = user.parent_id  # 替换为主用户ID

    # 查询该用户（主用户或附属用户）的 PDF 权限
    permissions = db.query(UserPDFPermission).filter(UserPDFPermission.user_id == user_id).all()

    return permissions

@router.delete("/permissions/{permission_id}")
def remove_pdf_permission(permission_id: int, db: Session = Depends(get_db)):
    permission = db.query(UserPDFPermission).filter(UserPDFPermission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")

    db.delete(permission)
    db.commit()
    return {"message": "权限已删除"}
