from functools import wraps
from datetime import datetime

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

token_cache = {}


def exempt_view_csrf(view_cls):
    def deco(*args, **kwargs):
        return method_decorator(csrf_exempt, name="dispatch")(view_cls)

    return deco()


def token_expire_cache(name, timeout=None, maxsize=128):
    global token_cache
    default_expire = 2 * 60 * 60

    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            timestamp = datetime.now().timestamp()

            # Clear expired tokens
            for key in token_cache.keys():
                token = token_cache[key]
                expire = token.get("timeout", default_expire)
                token_timestamp = token.get("timestamp", 0)

                if timestamp - token_timestamp > expire:
                    del token_cache[key]

            token = token_cache.get(name, {})

            if token:
                return token["ret"]
            else:
                if len(token_cache) > maxsize:
                    raise ValueError("Exceed maximum capacity:%s" % maxsize)

                token_ret = func(*args, **kwargs)
                token.update(timeout=timeout or default_expire, timestamp=timestamp, ret=token_ret)
                token_cache[name] = token

                return token_ret

        return inner
    return wrapper

