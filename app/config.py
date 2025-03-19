import os
from dotenv import load_dotenv

# 加载 .env 文件（仅用于开发环境）
load_dotenv()

# 读取环境变量
SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")


ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)  # JWT 过期时间
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # JWT
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_DB = os.getenv("REDIS_DB", 0)  # 使用 Redis 默认数据库



# 你的邮件服务器配置
# SMTP_SERVER = "smtp.qq.com"  # Gmail SMTP 服务器
SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = 465  # TLS 端口
SMTP_PORT = os.getenv("SMTP_PORT")
# EMAIL_SENDER = "你的邮箱"  # 你的邮箱
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
# EMAIL_PASSWORD = "你的邮箱密码"  # 你的邮箱密码
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


# 确保密钥存在，否则抛出异常
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 未设置！请在环境变量或 .env 文件中配置")
# 确保数据库 URL 存在，否则抛出异常
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 未设置！请在环境变量或 .env 文件中配置")
# 确保邮件服务器配置存在，否则抛出异常
if not SMTP_SERVER or not SMTP_PORT or not EMAIL_SENDER or not EMAIL_PASSWORD:
    raise ValueError("请在环境变量或 .env 文件中配置邮件服务器")


