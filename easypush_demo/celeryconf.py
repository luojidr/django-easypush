import os
import urllib.parse

from kombu import Exchange, Queue
from celery.schedules import crontab

from easypush.core.mq.autodiscover import autodiscover_tasks

__all__ = ["CeleryConfig"]


class BaseConfig(object):
    """ Celery基本配置
    令人奇怪的原因：大写的配置可能会造成配置无效，eg: CELERY_BEAT_SCHEDULE；
    建议使用小写，如果使用大写：一定要检查版本是否支持
    """

    CELERY_TIMEZONE = "Asia/Shanghai"
    CELERY_ENABLE_UTC = False

    # 任务发送完成是否需要确认，对性能会稍有影响
    CELERY_ACKS_LATE = True

    # # 非常重要,有些情况下可以防止死锁 (celery4.4.7可能没有这个配置)
    CELERYD_FORCE_EXECV = True

    # 并发worker数, 也是命令行-c指定的数目
    # CELERYD_CONCURRENCY = os.cpu_count()

    # 每个worker执行了多少个任务就死掉
    CELERYD_MAX_TASKS_PER_CHILD = 10

    # 表示每个 worker 预取多少个消息,默认每个启动的worker下有 cpu_count 个子 worker 进程
    # 所有 worker 预取消息数量: cpu_count * CELERYD_PREFETCH_MULTIPLIER
    CELERYD_PREFETCH_MULTIPLIER = 10

    # celery日志存储位置 (celery4.4.7可能没有这个配置)
    # CELERYD_LOG_FILE = ""

    CELERY_ACCEPT_CONTENT = ['json', ]
    CELERY_SERIALIZER = "json"
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = "json"

    # django-celery-results
    # # -----------------------------------------------------------------------
    # https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
    # CELERY_RESULT_BACKEND = 'django-db'
    # CELERY_RESULT_BACKEND = 'redis://:Fosun!123456@127.0.0.1:6399/0'
    CELERY_CACHE_BACKEND = 'django-cache'
    CELERY_TASK_TO_BACKEND = "task_to_backend"

    # 调度器
    CELERYBEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

    # CELERY_TRACK_STARTED = True

    # 拦截根日志配置
    CELERYD_HIJACK_ROOT_LOGGER = False

    # 去掉心跳机制
    BROKER_HEARTBEAT = 0


class CeleryQueueRouterConfig(object):
    """ RabbitMq Queue """

    CELERY_IMPORTS = autodiscover_tasks()
    CELERY_QUEUES = (
        Queue(
            name="send_message_by_mq_q",
            exchange=Exchange("send_message_by_mq_exc"),
            routing_key="send_message_by_mq_rk",
        ),
    )

    CELERY_ROUTES = {
        "easypush.tasks.task_send_message.send_message_by_mq": {
            "queue": "send_message_by_mq_q", "routing_key": "send_message_by_mq_rk"
        },
    }


class CeleryConfig(BaseConfig, CeleryQueueRouterConfig):
    BROKER_URL = "amqp://{user}:{pwd}@{host}:{port}/{server}".format(
        user=os.getenv("MQ:USER"), pwd=os.getenv("MQ:PASSWORD"),
        host=os.getenv("MQ:HOST"), port=os.getenv("MQ:PORT"),
        server=urllib.parse.quote_plus(os.getenv("MQ:VIRTUAL_HOST"))
    )

    CELERYBEAT_SCHEDULE = {
        "cache_ding_message_fingerprint": {
            'task': 'easypush.tasks.task_cache_message.cache_message_fingerprints',
            'schedule': crontab(hour=1, minute=0),
            'args': (),
        },
    }

