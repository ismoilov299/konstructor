import json
import logging
from functools import wraps
from json import JSONDecodeError

from loader import redis

logger = logging.getLogger()


def redis_cache(ex: int, key: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if _val := await redis.get(key):
                try:
                    _val = json.loads(_val)
                except JSONDecodeError:
                    pass
            else:
                _val = await func(*args, **kwargs)
                _val_to_cache = _val
                if isinstance(_val, dict):
                    _val_to_cache = json.dumps(_val)
                elif isinstance(_val, str):
                    try:
                        _val = json.loads(_val)
                    except JSONDecodeError:
                        pass
                else:
                    _val = str(_val)
                    _val_to_cache = _val
                await redis.set(key, _val_to_cache, ex=ex)
            return _val

        return wrapper

    return decorator
