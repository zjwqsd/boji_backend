from fastapi import Request
import redis.asyncio as redis

async def get_redis(request: Request) -> redis.Redis:
    # print(request.app.state.redis)
    print("🔗 正在获取 Redis 连接...")
    redis_client = request.app.state.redis
    if redis_client is None:
        raise ValueError("❌ 获取 Redis 连接失败")
    return redis_client