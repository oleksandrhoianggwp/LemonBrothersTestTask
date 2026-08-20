import logging

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY = "trends:rate_limited"


def _redis_client(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def cooldown_remaining_seconds(settings: Settings) -> int:
    try:
        with _redis_client(settings) as client:
            remaining = client.ttl(RATE_LIMIT_KEY)
    except RedisError as exc:
        logger.warning("trends_cooldown_read_failed failure=%s", type(exc).__name__)
        return 0
    return max(0, int(remaining))


def activate_rate_limit_cooldown(settings: Settings) -> int:
    ttl = settings.trends_rate_limit_cooldown_seconds
    try:
        with _redis_client(settings) as client:
            client.set(RATE_LIMIT_KEY, "1", ex=ttl)
    except RedisError as exc:
        logger.warning("trends_cooldown_write_failed failure=%s", type(exc).__name__)
        return 0
    return ttl
