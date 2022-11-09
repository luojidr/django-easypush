import logging

from django.conf import settings
from kombu import Exchange, Queue
from celery.schedules import crontab

from fosun_circle.core.mq.autodiscover import autodiscover_tasks

logging.warning("CeleryConfig go into env[%s]", settings.APP_ENV)

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
    # CELERYD_LOG_FILE = "/data/logs/fosun_circle/circle_celery.log"

    CELERY_ACCEPT_CONTENT = ['json', ]
    CELERY_SERIALIZER = "json"
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = "json"

    # django-celery-results
    # # -----------------------------------------------------------------------
    # https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
    CELERY_RESULT_BACKEND = 'django-db'
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


class CeleryQueueRouteConfig(object):
    """ RabbitMq Queue """

    CELERY_IMPORTS = autodiscover_tasks()
    CELERY_QUEUES = (
        Queue(
            name="test_concurrency_limit_q",
            exchange=Exchange("test_concurrency_limit_exc"),
            routing_key="test_concurrency_limit_rk",
        ),

        Queue(
            name="send_ding_message_q",
            exchange=Exchange("send_ding_message_exc"),
            routing_key="send_ding_message_rk",
        ),

        Queue(
            name="sync_ding_user_and_department_q",
            exchange=Exchange("sync_ding_user_and_department_exc"),
            routing_key="sync_ding_user_and_department_rk",
        ),

        Queue(
            name="cache_ding_message_fingerprint_q",
            exchange=Exchange("cache_ding_message_fingerprint_exc"),
            routing_key="cache_ding_message_fingerprint_rk",
        ),

        Queue(
            name="check_oss_anti_spam_q",
            exchange=Exchange("check_oss_anti_spam_exc"),
            routing_key="check_oss_anti_spam_rk",
        ),

        Queue(
            name="notify_star_or_comment_q",
            exchange=Exchange("notify_star_or_comment_exc"),
            routing_key="notify_star_or_comment_rk",
        ),
    )

    CELERY_ROUTES = {
        "fosun_circle.apps.users.tasks.test_concurrency_limit": {
            "queue": "test_concurrency_limit_q", "routing_key": "test_concurrency_limit_rk"
        },

        "fosun_circle.apps.users.tasks.sync_ding_user_and_department": {
            "queue": "sync_ding_user_and_department_q", "routing_key": "sync_ding_user_and_department_rk"
        },

        "fosun_circle.apps.ding_talk.tasks.task_send_ding_message.send_ding_message": {
            "queue": "send_ding_message_q", "routing_key": "send_ding_message_rk"
        },

        "fosun_circle.apps.ding_talk.tasks.task_cache_ding_message.cache_ding_message_fingerprint": {
            "queue": "cache_ding_message_fingerprint_q", "routing_key": "cache_ding_message_fingerprint_rk"
        },

        "fosun_circle.apps.aliyun.tasks.task_check_oss_anti_spam.check_oss_anti_spam": {
            "queue": "check_oss_anti_spam_q", "routing_key": "check_oss_anti_spam_rk"
        },

        "fosun_circle.apps.circle.tasks.task_notify.notify_star_or_comment": {
            "queue": "notify_star_or_comment_q", "routing_key": "notify_star_or_comment_rk"
        },
    }


class CeleryConfig(BaseConfig, CeleryQueueRouteConfig):
    """ Celery 配置文件 """

    APP_ENV = settings.APP_ENV

    if APP_ENV == "DEV":
        BROKER_URL = "amqp://admin:admin013431@127.0.0.1:5672/%2Fcircle"
    else:
        BROKER_URL = "amqp://admin:admin013431_Prd@127.0.0.1:5672/%2Fcircle"

    # 定时任务
    CELERYBEAT_SCHEDULE = {
        "sync_ding_user_and_department": {
            'task': 'fosun_circle.apps.users.tasks.sync_ding_user_and_department',
            'schedule': crontab(hour=3, minute=10),
            'args': (),
        },

        "cache_ding_message_fingerprint": {
            'task': 'fosun_circle.apps.ding_talk.tasks.task_cache_ding_message.cache_ding_message_fingerprint',
            'schedule': crontab(hour=1, minute=0),
            'args': (),
        },
    }

