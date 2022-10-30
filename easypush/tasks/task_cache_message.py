import traceback
from django_redis import get_redis_connection

from . import get_celery_app
from easypush.serializers import AppMsgPushRecordSerializer

celery_app = get_celery_app()
step_size = 2000
expire_time = 24 * 60 * 60
expire_keys_lua = """
for i=1, ARGV[1], 1 do
    redis.call("EXPIRE", KEYS[i], ARGV[2]);
end
"""


def bulk_insert_fingerprints(mappings):
    """
        # with redis_conn.pipeline(transaction=False) as p:
        #     for key, value in bulk_mappings.items():
        #         # redis_conn.set(key, value, expire_time)
        #         redis_conn.expire(key, expire_time)
        #
        #     p.execute()  # 批量执行, 效率有点低

    redis-cli -h [ip] -p [端口] -a [密码] keys "key_*" | xargs -i redis-cli -h ip -p [端口] -a [密码] expire {} [秒]
    eg: redis-cli -h 127.0.0.1 -p 6481 -a 123456 keys "falconSing*" | xargs -i redis-cli -h 127.0.0.1 -p 6481 -a 123456 expire {} 3600
    """
    redis_conn = get_redis_connection()

    try:
        if not isinstance(mappings, dict):
            raise ValueError("bulk_mappings must be dict")

        redis_conn.mset(mappings)
        cmd = redis_conn.register_script(expire_keys_lua)
        cmd(keys=list(mappings.keys()), args=[len(mappings), expire_time])
    except Exception as e:
        traceback.format_exc()


@celery_app.task
def cache_message_fingerprints(**kwargs):
    """ 缓存应用消息这主体信息和推送记录信息，避免重发 """
    bulk_mappings_list = []
    body_fingerprint_dict = {}
    log_fingerprint_dict = {}

    serializer = AppMsgPushRecordSerializer()

    log_fingerprint_mappings = serializer.get_sent_message_log_fingerprints()
    message_fingerprint_mappings = serializer.get_multi_message_body_fingerprints()

    try:
        # 钉钉消息体的指纹与主键的映射
        for index, (fingerprint, app_msg_id) in enumerate(message_fingerprint_mappings.items(), 1):
            key = serializer.APP_MSG_BODY_KEY % fingerprint
            body_fingerprint_dict[key] = app_msg_id

            if len(body_fingerprint_dict) % step_size == 0:
                bulk_mappings_list.append(dict(body_fingerprint_dict))
                body_fingerprint_dict = {}
        else:
            bulk_mappings_list.append(dict(body_fingerprint_dict))

        # 已发送钉钉消息记录的redis缓存
        for index, (fingerprint, log_item) in enumerate(log_fingerprint_mappings.items(), 1):
            app_id = log_item.get("app_id")
            app_msg_id = log_item.get("app_msg_id")
            receiver_mobile = log_item.get("receiver_mobile")

            if app_id and receiver_mobile:
                key = serializer.APP_MSG_LOG_KEY % (app_id, app_msg_id, receiver_mobile)
                log_fingerprint_dict[key] = fingerprint

                if len(log_fingerprint_dict) % step_size == 0:
                    bulk_mappings_list.append(dict(log_fingerprint_dict))
                    log_fingerprint_dict = {}
        else:
            bulk_mappings_list.append(dict(log_fingerprint_dict))

        for bulk_mappings in bulk_mappings_list:
            bulk_insert_fingerprints(bulk_mappings)
    except Exception as e:
        traceback.format_exc()

