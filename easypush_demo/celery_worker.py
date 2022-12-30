"""
Windows:
File "C:/Python392/lib/site-packages/celery/app/trace.py", line 638, in fast_trace_task
    tasks, accept, hostname = _loc
ValueError: not enough values to unpack (expected 3, got 0)

Solution：
    Use `eventlet` or `gevent`, not running on windows, but use `--pool=solo` is ok
    Error:  app.start(argv=["-A", "easypush_demo.celery_app", "worker", "-l", "info", "-c", "1", '-P', 'gevent'])
    OK Run: app.start(argv=["-A", "easypush_demo.celery_app", "worker", '--pool=solo', "-l", "info", "-c", "1"])
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easypush_demo.settings")
django.setup()

from easypush_demo.celery_app import app
from easypush.utils.snowflake import IdGenerator
from easypush.tasks.task_concurrency_conn import concurrency_orm_conn


def send_message_to_mq(max_size=5000):
    sf = IdGenerator(1, 1)

    for i in range(max_size):
        concurrency_orm_conn.delay(msg_uid=str(sf.get_id()))


if __name__ == "__main__":
    # app.worker_main()

    # Raise error on windows:
    #   tasks, accept, hostname = _loc
    #   ValueError: not enough values to unpack (expected 3, got 0)
    # app.start(argv=["-A", "easypush_demo.celery_app", "worker", "-l", "info", "-c", "1"])

    # Use `eventlet` or `gevent`, not running on windows, but use `--pool=solo` or `threads` is ok
    # app.start(argv=["-A", "easypush_demo.celery_app", "worker", "-l", "info", "-c", "1", '-P', 'gevent'])
    # app.start(argv=["-A", "easypush_demo.celery_app", "worker", '--pool=solo', "-l", "info", "-c", "30"])
    app.start(argv=["-A", "easypush_demo.celery_app", "worker", '-P', 'threads', "-l", "info", "-c", "30"])
    pass

    # Only send message to mq
    # send_message_to_mq()
