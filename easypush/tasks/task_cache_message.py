import traceback
from django_redis import get_redis_connection

from . import get_celery_app
from easypush.serializers import AppMsgPushRecordSerializer

celery_app = get_celery_app()


@celery_app.task
def cache_message_fingerprints(**kwargs):
    """ 缓存应用消息这主体信息和推送记录信息，避免重发 """
    serializer = AppMsgPushRecordSerializer()

    try:
        fingerprint_mappings = serializer.get_fingerprints_history()
        serializer.batch_insert_fingerprint(fingerprint_mappings)
    except Exception as e:
        traceback.format_exc()

