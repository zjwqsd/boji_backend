import hashlib
import hashlib
import jwt
from fastapi import HTTPException
import datetime
import uuid
from app.models import SuperAdminSession
from sqlalchemy.orm import Session
import random
import string
from app.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM
# from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from app.config import EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import  Depends, Request
import redis.asyncio as redis
from app.dependencies import get_redis
# email_verification_codes = {}

# 生成验证码（生产环境请发送邮件）
async def generate_email_code(email: str, request: Request) -> bool:
    import random
    code = random.randint(100000, 999999)
    print(code)
    # 发送邮件
    # email_verification_codes[email] = code
    redis_client = await get_redis(request)
    await redis_client.setex(f"email_code:{email}", 300, code)  # 5 分钟后自动删除

    subject = "【您的验证码】请勿泄露"
    content = f"""
    <html>
    <body>
        <h2>您的验证码</h2>
        <p>您好，您的验证码是：<strong>{code}</strong></p>
        <p>请在 5 分钟内使用该验证码。</p>
    </body>
    </html>
    """

    # 构建邮件
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(content, "html"))
    try:
        # 连接 SMTP 服务器
        print(f"📧 正在连接邮件服务器 {SMTP_SERVER}...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)  # 使用 SSL 连接
        print(f"📧 正在登录邮箱 {EMAIL_SENDER}...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        print(f"📧 正在发送邮件验证码到 {email}...")
        # 发送邮件
        response = server.sendmail(EMAIL_SENDER, email, msg.as_string())

        server.quit()

        # sendmail() 返回值：如果是空字典 `{}`，说明邮件成功发送
        if not response:
            # print(f"✅ 邮件已成功发送到 {email}")
            print(f"验证码已发送至 {email}: {code}")  # 模拟发送
            return True
        else:
            print(f"❌ 邮件发送失败，服务器返回：{response}")
            return False
    except Exception as e:
        print(f"❌ 发送邮件时发生错误: {e}")
        return False
    

# 验证邮箱验证码
async def verify_email_code(email: str, code: int,request:Request) -> bool:
    redis_client = await get_redis(request )
    stored_code = redis_client.get(f"email_code:{email}")
    # stored_code = email_verification_codes.get(email)
    if stored_code and stored_code == code:
        await redis_client.delete(f"email_code:{email}")  # 验证成功后删除
        # del email_verification_codes[email]
        return True
    return False

# 哈希密码
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# 🔹 验证密码（哈希对比）
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# 🔹 生成 JWT 令牌
def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



# 🔹 解析 JWT 令牌
def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="认证失败：令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="认证失败：无效令牌")
    
# 🔹 生成会话
def create_super_admin_session(admin_id: int, db: Session):
    session_id = str(uuid.uuid4())
    new_session = SuperAdminSession(admin_id=admin_id, session_id=session_id)
    db.add(new_session)
    db.commit()
    return session_id

# 🔹 检查会话是否有效
def verify_super_admin_session(session_id: str, db: Session):
    session = db.query(SuperAdminSession).filter(SuperAdminSession.session_id == session_id).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="会话已失效，请重新登录")
    return session
# 🔹 生成 JWT 令牌
def create_jwt_token(data: dict):
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
# 🔹 验证超级用户
def authenticate_super_admin(username: str, password: str, db):
    print(username)
    print(password)
    from app.models import SuperAdmin
    super_admin = db.query(SuperAdmin).filter(SuperAdmin.username == username).first()
    # 打印数据库中的密码
    # print(super_admin.password)
    # 打印输入的密码
    print(super_admin)
    print(hash_password(password))
    if not super_admin or super_admin.password != hash_password(password):
        raise HTTPException(status_code=401, detail="超级用户认证失败")
    return create_jwt_token({"role": "super_admin"})


# 🔹 解析 JWT 令牌
def verify_super_admin(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="无权限")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效令牌")
    
def generate_user_id():
    return "U" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))  # 生成 `UABCDEFGH`
