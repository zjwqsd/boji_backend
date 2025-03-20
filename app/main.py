from fastapi import FastAPI
from fastapi.responses import FileResponse
# from app.routes import  item
# from fastapi import FastAPI
from app.routes import auth,admin,item
from app.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
# from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis 
# from app.config import REDIS_URL
app = FastAPI()

@app.on_event("startup")
async def startup():
    try:
        # 🔹 创建异步 Redis 连接
        redis_client = redis.Redis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)
        app.state.redis = redis_client  # 存储到 FastAPI 的 state
        await FastAPILimiter.init(redis_client)
        print("✅ Redis 连接成功")
    except Exception as e:
        print(f"⚠️ Redis 连接失败，限流功能将禁用: {e}")
        
@app.on_event("shutdown")
async def shutdown():
    redis_client = app.state.redis
    if redis_client:
        await redis_client.close()
        print("🛑 Redis 连接已关闭")
# 添加 CORS 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域访问（可以改成特定域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法 (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # 允许所有请求头
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}
# 提供 favicon.ico 文件
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/ping")
def ping():
    return {"status": "running"}

# **创建表**
Base.metadata.create_all(bind=engine)

# **注册路由**
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(item.router)


