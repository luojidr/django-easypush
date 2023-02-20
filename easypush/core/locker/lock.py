import time
import string
import random
import threading

try:
    from redlock import Redlock
except ImportError:
    Redlock = None

from django_redis import get_redis_connection
from django.utils.functional import cached_property

from .watch import LockWatcher


class AcquireLockError(Exception):
    pass


class ReleaseLockError(Exception):
    pass


class TaskRunningError(Exception):
    pass


class TaskCallableError(Exception):
    pass


class DistributedLock:
    UNLOCK_SCRIPT = """
        if redis.call("get",KEYS[1]) == ARGV[1] then
            return redis.call("del",KEYS[1])
        else
            return 0
        end
    """

    def __init__(self, key,
                 func, func_args=(), func_kwargs=None,
                 before_func=None, before_func_args=(), before_func_kwargs=None,
                 expire=None, interval_waits=None, watch_on=False):
        """ 分布式锁, 当任务需要唯一执行时可使用该方法
            :param key: str, 分布式锁 Key
            :param func: callable, 执行的任务的可调用对象
            :param func_args: tuple, 任务的位置参数
            :param func_kwargs: dict, 任务的关键字参数
            :param before_func: callable, 预处理任务的可调用对象, 若结果不为空，则跳过task直接返回
            :param func_args: tuple, 预处理任务的位置参数
            :param before_func_kwargs: dict, 预处理任务的关键字参数
            :param expire: int, 锁和task最大过期时间(秒)
            :param interval_waits: int, 下一次获取锁的间隔时间(秒)
            :param watch_on: bool, 是否给锁续命，直至task结束
            :return:
        """
        self.key = key

        self.func = func
        self.func_args = func_args
        self.func_kwargs = func_kwargs

        self.before_func = before_func
        self.before_func_args = before_func_args
        self.before_func_kwargs = before_func_kwargs

        self.expire = expire or 10 * 60
        self.interval_waits = interval_waits or 0.1
        self.watch_on = watch_on

    @cached_property
    def script_sha(self):
        # script_sha is str, Same as script_sha, same result every time
        return self.redis_conn.script_load(self.UNLOCK_SCRIPT)

    @cached_property
    def redis_conn(self):
        return get_redis_connection()

    def get_unique_id(self):
        CHARACTERS = string.ascii_letters + string.digits
        return ''.join(random.choice(CHARACTERS) for _ in range(22)).encode()

    def lock(self):
        uniq_val = self.get_unique_id()
        lock_watcher = LockWatcher(self.key, uniq_val, self.expire, conn=self.redis_conn)

        # Here is Distributed Lock
        # 1: Self-implemented locker(distributed locker) for a single redis instance, redis.set is atomic,
        #      but not blocking, so use `while` for checking, then must sleep
        # 2: The redlock-py package is a distributed locker on multiple instances of redis，
        #      after the locker is acquired, it is not blocking, you still need to use `while` for checking
        while True:
            if callable(self.before_func):
                args = self.before_func_args
                kwargs = self.before_func_kwargs
                pre_result = self.before_func(*args, **(kwargs or {}))

                if pre_result is not None:
                    return pre_result

            # Warning(Important): If the `task` spend time than the `expire`, the locker will not work,
            # so you must prolong Time To Live for the locker
            if self.redis_conn.set(self.key, uniq_val, px=lock_watcher.expire, nx=True):
                # print("calculate-%s：%s" % (threading.get_ident(), datetime.now()))
                try:
                    # 护线程给lock_key续命，目前测试发现整体上会稍微降低整个系统的效率
                    if self.watch_on:
                        t = threading.Thread(target=lock_watcher.watchdog)
                        t.setDaemon(True)  # When the main thread terminates, the daemon thread automatically terminates
                        t.start()

                    if callable(self.func):
                        return self.func(*self.func_args, **(self.func_kwargs or {}))

                    raise TaskCallableError("Task must a callable")
                except Exception as e:
                    raise TaskRunningError("Task running business error: {0}".format(e))
                finally:
                    self._unlock(uniq_val)

            time.sleep(self.interval_waits)  # Sleep `delay` seconds

    def _unlock(self, uniq_val):
        # Recommend to use, only release the locker you put on yourself
        try:
            # You could use `eval` or `evalsha` cmd, but performance of `evalsha might be better
            # redis_conn.eval(unlock_script, 1, lock_key, uniq_val)
            self.redis_conn.evalsha(self.script_sha, 1, self.key, uniq_val)

            # Also use register_script method,
            # command = redis_conn.register_script(unlock_script)
            # command(keys=[lock_key], args=[uniq_val])
            pass
        except Exception as e:
            raise ReleaseLockError("Release locker error: {0}".format(e))

        # Deprecated: The locker may not release by itself
        # redis_conn.delete(lock_key)  # Delete locker to success or fail [redis_conn.expire(lock_key, 0)] is same
