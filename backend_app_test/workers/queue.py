import os
import logging

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

try:
    from arq import create_pool
    from arq.connections import RedisSettings
    redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, conn_timeout=10)
    HAS_ARQ = True
except ImportError:
    HAS_ARQ = False
    redis_settings = None

_redis_pool = None

async def get_redis_pool():
    global _redis_pool
    if not HAS_ARQ:
        return None
    if _redis_pool is None:
        try:
            _redis_pool = await create_pool(redis_settings)
        except Exception:
            return None
    return _redis_pool

async def close_redis_pool():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
