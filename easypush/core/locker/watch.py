import time

from django_redis import get_redis_connection
from django.utils.functional import cached_property


class LockWatcher:
    delay_script = """
        if redis.call("get",KEYS[1]) == ARGV[1] then
            return redis.call("pexpire",KEYS[1],ARGV[2])
        else
            return 0
        end
    """
    exit_script = """
        if redis.call("get",KEYS[1]) == ARGV[1] then
            return 0
        else
            return 1
        end
    """

    def __init__(self, key, value, expire, conn=None):
        self.key = key
        self.value = str(value)
        self.expire = int(expire * 1000)  # milliseconds
        self.redis_conn = conn or get_redis_connection()

    @staticmethod
    def get_timestamp():
        return time.time() * 1000

    @cached_property
    def exit_sha(self):
        return self.redis_conn.script_load(self.exit_script)

    @cached_property
    def delay_sha(self):
        return self.redis_conn.script_load(self.delay_script)

    def watchdog(self):
        timestamp = self.get_timestamp()  # milliseconds

        while True:
            if self.redis_conn.evalsha(self.exit_sha, 1, self.key, self.value):
                break

            elapsed_time = int(self.get_timestamp() - timestamp)
            percentage = int(elapsed_time / self.expire * 100)

            # 每次锁的过期时间达到70%时，自动续命
            if percentage >= 70:
                delay_time = self.expire
                self.redis_conn.evalsha(self.delay_sha, 1, self.key, self.value, delay_time)
                timestamp = self.get_timestamp()

            time.sleep(0.1)
