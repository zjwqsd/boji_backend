from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.utils import verify_super_admin, generate_user_id

router = APIRouter(prefix="/admin", tags=["Admin"])

class AssignSubUserRequest(BaseModel):
    parent_user_id: int  # 绑定的普通用户 ID

@router.post("/assign-sub-user")
def assign_sub_user(request: AssignSubUserRequest, db: Session = Depends(get_db), admin=Depends(verify_super_admin)):
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
    )
    db.add(sub_user)
    db.commit()
    return {"message": "附属用户已创建", "sub_user_id": sub_user.user_id}
