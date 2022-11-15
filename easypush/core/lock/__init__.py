try:
    from redlock import Redlock
except ImportError:
    Redlock = None

import time
import string
import random

from django_redis import get_redis_connection

unlock_script = """
    if redis.call("get",KEYS[1]) == ARGV[1] then
        return redis.call("del",KEYS[1])
    else
        return 0
    end
"""
redis_conn = get_redis_connection()
# script_sha is str, Same as script_sha, same result every time
script_sha = redis_conn.script_load(unlock_script)


class AcquireLockError(Exception):
    pass


class ReleaseLockError(Exception):
    pass


class TaskRunningError(Exception):
    pass


def atomic_task_with_lock(lock_key,
                          task, task_args=(), task_kwargs=None,
                          task_pre=None, task_pre_args=(), task_pre_kwargs=None,
                          expire=10 * 60, delay=0.1):

    global redis_conn, script_sha

    timestamp = int(time.time())
    uniq_val = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(22)).encode()

    # Here is Distributed Lock
    # 1: Self-implemented lock(distributed lock) for a single redis instance, redis.set is atomic,
    #      but not blocking, so use `while` for checking, then must sleep
    # 2: The redlock-py package is a distributed lock on multiple instances of redis，
    #      after the lock is acquired, it is not blocking, you still need to use `while` for checking
    while int(time.time()) - timestamp < expire:
        if callable(task_pre):
            pre_result = task_pre(*task_pre_args, **(task_pre_kwargs or {}))
            if pre_result is not None:
                return pre_result

        # If the `task_run` business fails to be handle within 10 minutes or exception, the lock does not work
        if redis_conn.set(lock_key, uniq_val, px=int(expire * 1000), nx=True):
            try:
                if callable(task):
                    return task(*task_args, **(task_kwargs or {}))

                raise ValueError("task must a callable object")
            except Exception as e:
                raise TaskRunningError("Task running business error: {0}".format(e))
            finally:
                # Recommend to use, only release the lock you put on yourself
                try:
                    # You could use `eval` or `evalsha` cmd, but performance of `evalsha might be better
                    # redis_conn.eval(unlock_script, 1, lock_key, uniq_val)
                    redis_conn.evalsha(script_sha, 1, lock_key, uniq_val)

                    # Also use register_script method,
                    # command = redis_conn.register_script(unlock_script)
                    # command(keys=[lock_key], args=[uniq_val])
                    pass
                except Exception as e:
                    raise ReleaseLockError("Release lock error: {0}".format(e))

                # Deprecated: The lock may not release by itself
                # redis_conn.delete(lock_key)  # Delete lock to success or fail [redis_conn.expire(lock_key, 0)] is same

        time.sleep(delay)  # Sleep 10 milliseconds

    raise AcquireLockError("Acquire lock is failed with single redis instance")
