from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from pydantic import BaseModel, EmailStr
from app.utils import hash_password, verify_email_code
from app.utils import generate_email_code
from app.utils import verify_password, create_access_token,decode_jwt_token
from app.utils import authenticate_super_admin,generate_user_id
from fastapi.security import OAuth2PasswordBearer

# generate_email_code("test@example.com")
router = APIRouter(prefix="/auth", tags=["Auth"])
# 🔹 定义 JSON 请求体
class EmailRequest(BaseModel):
    email: EmailStr  # 确保 email 格式正确

# 🔹 用户注册请求体
class RegisterRequest(BaseModel):
    nickname: str 
    realname: str | None = None
    address: str | None = None
    company: str | None = None
    phone: str | None = None
    email: EmailStr
    password: str
    emailcode: int  # 验证码
    user_id : str | None = None # 绑定到附属用户的 ID
# 🔹 用户注册 API

# 🔹 登录请求体
class UserLoginRequest(BaseModel):
    identifier: str  # 可以是 email 或 user_id
    password: str

# 🔹 重置密码请求体
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    newpassword: str
    emailcode: int  # 验证码

# 🔹 超级用户登录请求体
class SuperAdminLoginRequest(BaseModel):
    username: str
    password: str

# 🔹 OAuth2 认证（提取 Bearer Token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/register", response_model=dict)
def register(Regrequest: RegisterRequest, request:Request, db: Session = Depends(get_db)):
    # 如果注册时提供 user_id，说明是附属用户
        # 1️⃣ 验证邮箱验证码
    # print(Regrequest.email)
    if not verify_email_code(Regrequest.email, Regrequest.emailcode,request):
        raise HTTPException(status_code=400, detail="注册失败：验证码错误")
    else:
        print("验证码验证成功")
    # 2️⃣ 如果提供 user_id，则绑定到已存在的用户
    if Regrequest.user_id:
        existing_user = db.query(User).filter(User.user_id == Regrequest.user_id).first()
        if not existing_user:
            raise HTTPException(status_code=404, detail="绑定失败：用户 ID 不存在")
        
        if existing_user.email:
            raise HTTPException(status_code=400, detail="绑定失败：该用户已绑定邮箱")

        # 绑定邮箱并更新数据库
        existing_user.email = Regrequest.email
        existing_user.email_verified = True
        existing_user.nickname = Regrequest.nickname
        existing_user.realname = Regrequest.realname
        # existing_user.address = Regrequest.address
        # existing_user.company = Regrequest.company
        existing_user.phone = Regrequest.phone
        db.commit()
        db.refresh(existing_user)
        
        return {"message": "附属用户绑定成功", "user_id": existing_user.user_id, "email": existing_user.email}
    
    if db.query(User).filter(User.email == Regrequest.email).first():
        raise HTTPException(status_code=400, detail="注册失败：邮箱已被绑定")

    print("开始注册")
    # 如果未提供 user_id 则自动分配 id
    user_id = generate_user_id()
    while db.query(User).filter(User.user_id == user_id).first():
        user_id = generate_user_id()  # 确保 user_id 唯一
    # 3️⃣ 存储用户信息（密码加密）
    hashed_password = hash_password(Regrequest.password)
    new_user = User(
        user_id=user_id,
        nickname=Regrequest.nickname,
        realname=Regrequest.realname,
        address=Regrequest.address,
        company=Regrequest.company,
        phone=Regrequest.phone,
        email=Regrequest.email,
        password=hashed_password,
        email_verified=True,
        is_sub_user = False,
        parent_id = None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return  {"message": "注册成功", "user_id": new_user.user_id, "email": new_user.email}



# 🔹 发送验证码 API
# 🔹 发送验证码 API（使用 JSON）
@router.post("/send-email", response_model=dict)
async def send_email(email_request: EmailRequest,request: Request):
    try:
        print(email_request.email)
        await generate_email_code(email_request.email,request)
        return {"message": "验证码已发送"}
    except Exception:
        raise HTTPException(status_code=500, detail="验证码发送失败")
    

    

# 🔹 用户登录 API（使用 JSON）
@router.post("/login", response_model=dict)
def login(login_request: UserLoginRequest,db: Session = Depends(get_db)):
    # 1️⃣ 检查用户是否存在
    user = db.query(User).filter(User.email == login_request.identifier).first()
    if not user:
        user = db.query(User).filter(User.user_id == login_request.identifier).first()
    if not user:
        raise HTTPException(status_code=400, detail="登录失败：用户不存在")
    # 检查是否绑定邮箱
    if not user.email_verified:
        raise HTTPException(status_code=400, detail="登录失败：邮箱未验证")
    # 2️⃣ 验证密码
    if not verify_password(login_request.password, user.password):
        raise HTTPException(status_code=400, detail="登录失败：密码错误")

    # 3️⃣ 生成 JWT 令牌
    token = create_access_token({"user_id": user.id, "email": user.email})

    return {"message": "登录成功", "token": token,"nickname":user.nickname}

# 🔹 重置密码 API
@router.post("/reset-password", response_model=dict)
def reset_password(reset_request: ResetPasswordRequest, request:Request,db: Session = Depends(get_db)):
    # 1️⃣ 验证邮箱验证码
    if not verify_email_code(reset_request.email, reset_request.emailcode,request):
        raise HTTPException(status_code=400, detail="重置密码失败：验证码错误")

    # 2️⃣ 查找用户
    user = db.query(User).filter(User.email == reset_request.email).first()
    
    
    if not user:
        raise HTTPException(status_code=400, detail="重置密码失败：用户不存在")

    # 3️⃣ 更新密码（哈希加密）
    user.password = hash_password(reset_request.newpassword)
    db.commit()

    return {"message": "密码已重置"}


# 🔹 获取当前用户信息
@router.get("/me", response_model=dict)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # 1️⃣ 解析 JWT 令牌
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="认证失败：无效令牌")

    # 2️⃣ 获取用户信息
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": user.user_id,
        "email": user.email,
        "realname": user.realname,
        "nickname": user.nickname,
        "phone": user.phone,
        "company": user.company,
        "address": user.address,
        "is_sub_user": user.is_sub_user,
        # 如果是附属用户，返回主用户的
        # "parent_id": user.parent_id,
    }


@router.post("/superlogin", response_model=dict)
def super_admin_login(request: SuperAdminLoginRequest, db: Session = Depends(get_db)):
    token = authenticate_super_admin(request.username, request.password, db)
    return {"message": "登录成功", "token": token}