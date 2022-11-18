try:
    from redlock import Redlock
except ImportError:
    Redlock = None

import time
import string
import random
import threading

from django_redis import get_redis_connection

unlock_script = """
    if redis.call("get",KEYS[1]) == ARGV[1] then
        return redis.call("del",KEYS[1])
    else
        return 0
    end
"""
delay_script = """
    if redis.call("get",KEYS[1]) == ARGV[1] then
        return redis.call("pexpire",KEYS[1],ARGV[2])
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


class LockWatch:
    def __init__(self, key, value, expire):
        self.key = key
        self.value = str(value)
        self.expire = int(expire * 1000)  # milliseconds

    @classmethod
    def delay_sha(cls):
        delay_sha = getattr(cls, "_delay_sha", None)
        if delay_sha:
            return getattr(cls, "_delay_sha")

        delay_sha = redis_conn.script_load(delay_script)
        getattr(cls, "_delay_sha", delay_sha)
        return delay_sha

    def watchdog(self, conn):
        timestamp = time.time() * 1000  # milliseconds

        while True:
            cache_value = str(conn.get(self.key) or b"")

            if cache_value != self.value:
                break

            elapsed_time = int(time.time() * 1000 - timestamp)
            percentage = int(elapsed_time / self.expire * 100)
            # print("elapsed_time:%s, percentage:%s" % (elapsed_time, percentage))

            if percentage >= 70:
                delay_time = self.expire
                ret = conn.evalsha(LockWatch.delay_sha(), 1, self.key, self.value, delay_time)
                timestamp = time.time() * 1000
                # print("ret:%s" % ret)

            time.sleep(0.1)


def atomic_task_with_lock(lock_key,
                          task, task_args=(), task_kwargs=None,
                          task_before=None, task_before_args=(), task_before_kwargs=None,
                          expire=10 * 60, delay=0.1, watch_on=False):
    """ 分布式锁, 当任务需要唯一执行时可使用该方法
    :param lock_key: str, 分布式锁 Key
    :param task: callable, 执行的任务的可调用对象
    :param task_args: tuple, 任务的位置参数
    :param task_kwargs: dict, 任务的关键字参数
    :param task_before: callable, 预处理任务的可调用对象, 若结果不为空，则跳过task直接返回
    :param task_before_args: tuple, 预处理任务的位置参数
    :param task_before_kwargs: dict, 预处理任务的关键字参数
    :param expire: int, 锁和task最大过期时间(秒)
    :param delay: int, 下一次获取锁的间隔时间(秒)
    :param watch_on: bool, 是否给锁续命，直至task结束
    :return:
    """
    global redis_conn, script_sha

    uniq_val = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(22))
    watch = LockWatch(lock_key, uniq_val, expire)

    # Here is Distributed Lock
    # 1: Self-implemented lock(distributed lock) for a single redis instance, redis.set is atomic,
    #      but not blocking, so use `while` for checking, then must sleep
    # 2: The redlock-py package is a distributed lock on multiple instances of redis，
    #      after the lock is acquired, it is not blocking, you still need to use `while` for checking
    while True:
        if callable(task_before):
            pre_result = task_before(*task_before_args, **(task_before_kwargs or {}))
            if pre_result is not None:
                return pre_result

        # Warning(Important): If the `task` spend time than the `expire`, the lock will not work,
        # so you must prolong Time To Live for the lock
        if redis_conn.set(lock_key, uniq_val, px=watch.expire, nx=True):
            # print("calculate-%s：%s" % (threading.get_ident(), datetime.now()))
            try:
                # 大量启动守护线程给lock_key续命，目前测试发现整体上会降低整个系统的效率
                if watch_on:
                    t = threading.Thread(target=watch.watchdog, args=(redis_conn,))
                    t.setDaemon(True)
                    t.start()

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

        time.sleep(delay)  # Sleep `delay` seconds
