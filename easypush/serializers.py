import time
import json
import logging
import traceback
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django_redis import get_redis_connection

from . import models
from .core.crypto import BaseCipher
from .utils.snowflake import IdGenerator

USER_MODEL = get_user_model()
logger = logging.getLogger("django")


class AppTokenPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AppTokenPlatformModel
        fields = models.AppTokenPlatformModel.fields()
        read_only_fields = ["app_token"]

    def create(self, validated_data):
        model_cls = self.Meta.model
        instance = model_cls.objects.filter(agent_id=validated_data.get("agent_id", 0)).first()

        if instance is None:
            instance = model_cls(**validated_data)
        else:
            instance.save_attributes(**validated_data)

        instance.app_token = instance.encrypt_token()
        instance.expire_time = int(time.time()) + 20 * 365 * 24 * 60 * 60
        instance.save()

        return instance

    def update(self, instance, validated_data):
        validated_data["app_token"] = instance.encrypt_token()
        validated_data["expire_time"] = int(time.time()) + 20 * 365 * 24 * 60 * 60

        return super().update(instance, validated_data)


class AppMediaStorageSerializer(serializers.ModelSerializer):
    app = AppTokenPlatformSerializer()
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = models.AppMediaStorageModel
        fields = models.AppMediaStorageModel.fields(exclude=("media", )) + ["app", "creator", "create_time"]


class AppMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AppMessageModel
        fields = models.AppMessageModel.fields()


class ListAppMsgPushRecordSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        """ 暂未用到批量更新 """

    def create(self, validated_data):
        """ Batch to create pushed messages
        @:param validated_data: list
        """
    #     # 校验通过后, self.initial_data 与 validated_data 数据一致, 除了 validated_data 的每个字典中不包含 app_token
    #     # mobile与jobCode
    #     mobile_list = [item["receiver_mobile"] for item in validated_data]
    #     user_query_kwargs = dict(phone_number__in=mobile_list, is_del=False)
    #     user_queryset = CircleUsersModel.objects.filter(**user_query_kwargs).values("phone_number", "ding_job_code")
    #     mobile_jobCode_dict = {user_item["phone_number"]: user_item["ding_job_code"] for user_item in user_queryset}
    #
    #     # 微应用信息
    #     app_token_list = [item["app_token"] for item in self.initial_data]
    #     plain_token_list = [DingAppTokenModel.decipher_text(_app_token) for _app_token in app_token_list]
    #     agent_id_list = [int(_plain_token.split(":", 1)[0]) for _plain_token in plain_token_list]
    #
    #     app_query_kwargs = dict(agent_id__in=agent_id_list, is_del=False)
    #     app_queryset = DingAppTokenModel.objects.filter(**app_query_kwargs).values("id", "agent_id")
    #     app_agent_dict = {app_item["agent_id"]: app_item["id"] for app_item in app_queryset}
    #
    #     bulk_obj_list = []
    #     model_cls = self.child.Meta.model
    #
    #     # 根据消息记录指纹过滤重复记录(钉钉消息记录) => 被优化了
    #     # app_ids = list(app_agent_dict.values())
    #     # mobile_list = list(mobile_jobCode_dict.keys())
    #     # msg_log_fingerprint_set = self.child.get_sent_message_log_fingerprints(mobile_list, app_ids=app_ids)
    #
    #     # 钉钉消息主体指纹
    #     ding_message_body_mapping = {}
    #     ding_message_log_mapping = {}
    #     cost_start_time = time.time()
    #
    #     for index, data in enumerate(self.initial_data):
    #         message_data = dict(data, **validated_data[index])
    #         new_validated_data = self.child.derive_value(message_data)
    #
    #         plain_token = DingAppTokenModel.decipher_text(new_validated_data["app_token"])
    #         agent_id = int(plain_token.split(":", 1)[0])
    #
    #         # 消息主体指纹
    #         app_id = app_agent_dict.get(agent_id)
    #         new_validated_data["app_id"] = app_id
    #         message_body_fingerprint = self.child.get_message_body_fingerprint(new_validated_data)
    #
    #         # _ding_msg_id = ding_message_results.get(message_body_fingerprint)
    #         _ding_msg_id = self.child._get_app_id_by_msg_fingerprint(message_body_fingerprint)
    #
    #         if not _ding_msg_id:
    #             ding_msg_obj = DingMessageModel.create_object(**new_validated_data)
    #             _ding_msg_id = ding_msg_obj.id
    #
    #         # 暂存
    #         ding_message_body_mapping[message_body_fingerprint] = _ding_msg_id
    #
    #         # 补充消息记录信息并过滤消息记录指纹
    #         mobile = new_validated_data["receiver_mobile"]
    #         new_validated_data.update(
    #             ding_msg_id=_ding_msg_id,
    #             receiver_job_code=mobile_jobCode_dict.get(mobile, ""),
    #         )
    #         log_fingerprint = self.child.get_fingerprint(validated_data=new_validated_data)
    #
    #         # if log_fingerprint not in msg_log_fingerprint_set:
    #         if not self.child._has_msg_log_fingerprint(app_id, _ding_msg_id, mobile, log_fingerprint):
    #             ding_message_log_mapping[(app_id, _ding_msg_id, mobile)] = log_fingerprint
    #             bulk_obj_list.append(model_cls.create_object(force_insert=False, **new_validated_data))
    #
    #     instance_list = model_cls.objects.bulk_create(bulk_obj_list)
    #
    #     self.child.bulk_insert_fingerprint_to_redis(ding_message_body_mapping, ding_message_log_mapping)
    #     return instance_list


class AppMsgPushRecordSerializer(serializers.ModelSerializer):
    DEFAULT_EXPIRE = 7 * 60 * 60
    APP_MSG_FINGERPRINT_KEY = "app_id:{app_id}:msg_fingerprint:{msg_fingerprint}"
    APP_LOG_FINGERPRINT_KEY = "app_id:{app_id}:msg_fingerprint:{msg_fingerprint}:mobile:{mobile}"

    app_token = serializers.SerializerMethodField(help_text="微应用token")
    receiver_mobile = serializers.CharField(max_length=50000, help_text="推送的手机号")

    class Meta:
        model = models.AppMsgPushRecordModel
        fields = models.AppMsgPushRecordModel.fields() + ["app_token"]
        read_only_fields = [
            "app_id", "msg_type_cn", "sender", "send_time", "receiver_userid", "receive_time", "is_read",
            "read_time", "is_success", "traceback", "task_id", "request_id", "source_cn", "is_done"
        ]

        list_serializer_class = ListAppMsgPushRecordSerializer

    def get_app_token(self, obj):
        return obj.app.app_token

    def get_fingerprint(self, validated_data=None):
        """ Unique message fingerprint """
        fingerprint_fields = ["msg_body_json"]

        if not validated_data:
            raise ValidationError("Unable to get message fingerprint")

        fields = [key for key in validated_data if key in fingerprint_fields]
        fingerprint_fmt = ":".join(["{%s}" % name for name in fields])
        fingerprint_kwargs = {name: validated_data.get(name, "") for name in fields}

        fingerprint_msg = fingerprint_fmt.format(**fingerprint_kwargs)
        fingerprint = BaseCipher.crypt_md5(fingerprint_msg)

        return fingerprint

    def query_by_sql(self, sql, params=None, using=None, columns=()):
        """ native SQL query """
        model_cls = self.Meta.model
        connection = connections[using or DEFAULT_DB_ALIAS]
        cursor = connection.cursor()

        cursor.execute(sql, params=params)
        result = cursor.fetchall()
        mapping_result = [dict(zip(columns, item)) for item in result]

        return mapping_result

    def _get_cache_from_redis(self, app_id, msg_fingerprint, mobile=None):
        fp_kwargs = dict(app_id=app_id, msg_fingerprint=msg_fingerprint)

        if mobile is not None:
            fp_kwargs["mobile"] = mobile
            key = self.APP_LOG_FINGERPRINT_KEY.format(**fp_kwargs)
        else:
            key = self.APP_MSG_FINGERPRINT_KEY.format(**fp_kwargs)

        redis_conn = get_redis_connection()
        return redis_conn.get(key)

    def clean_data(self, data):
        id_yield = IdGenerator(1, 1)
        app_obj = data.get("app_obj")
        msg_body_json = data.get("msg_body_json")

        if not isinstance(msg_body_json, dict):
            raise ValueError("request.data not include 'msg_body_json' field")

        cleaned_data = dict(
            app_id=app_obj.id, sender="sys", send_time=datetime.now(),
            receiver_mobile=data.get("receiver_mobile", ""),
            receiver_userid=data.get("receiver_userid", ""),
            is_read=False, is_success=False, msg_uid=id_yield.get_id(),
            msg_type=data.get("msg_type"), platform_type=app_obj.platform_type,
            msg_body_json=json.dumps(msg_body_json, sort_keys=True),
        )

        return cleaned_data

    def get_fingerprints_history(self, days=30, is_raw_sql=False):
        """ Used for filtering to obtain the fingerprint of messages sent in the last 30 days.
            If rapid filtration is achieved: Bloom filtration

        :param days: int
        :param is_raw_sql: bool, Whether to use native sql query
        """
        fingerprint_mapping = {}
        model_cls = self.Meta.model

        # Message body and related applications
        msg_fields = ["id", "app_id", "msg_body_json"]
        log_fields = ["id", "app_msg_id", "receiver_mobile"]

        if not is_raw_sql:
            msg_queryset = models.AppMessageModel.objects.filter(is_del=False).values(*msg_fields)
            msg_mappings = {msg_item["id"]: msg_item for msg_item in msg_queryset}
        else:
            sql_where = "where is_del=false "
            msg_sql = "SELECT %s FROM %s ".format(", ".join(msg_fields), models.AppMessageModel._meta.db_table)
            msg_queryset = self.query_by_sql(msg_sql + sql_where, columns=msg_fields)
            msg_mappings = {msg_item["id"]: msg_item for msg_item in msg_queryset}

        # Filter the corresponding message record
        app_msg_ids = list(msg_mappings.keys())
        recent_sent_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        if not is_raw_sql:
            orm_query = dict(app_msg_id__in=app_msg_ids, send_time__gt=recent_sent_time)
            log_queryset = model_cls.objects.filter(**orm_query).values(*log_fields)
        else:
            sql_where = " where send_time >= '%s' " % recent_sent_time
            sql_where += " app_msg_id in (%s) " % ",".join([str(did) for did in app_msg_ids])

            log_msg_sql = "SELECT %s FROM %s ".format(",".join(log_fields), model_cls._meta.db_table)
            log_queryset = self.query_by_sql(log_msg_sql + sql_where, columns=log_fields)

        for log_items in log_queryset:
            log_id = log_items["id"]
            app_msg_id = log_items["app_msg_id"]
            mobile = log_items["receiver_mobile"]

            if app_msg_id in msg_mappings:
                msg_items = msg_mappings[app_msg_id]
                msg_fingerprint = self.get_fingerprint(validated_data=dict(zip(msg_fields, msg_items)))

                fp_kwargs = dict(app_id=msg_items["app_id"], msg_fingerprint=msg_fingerprint, mobile=mobile)
                fingerprint_mapping[self.APP_LOG_FINGERPRINT_KEY.format(**fp_kwargs)] = log_id
                fingerprint_mapping[self.APP_MSG_FINGERPRINT_KEY.format(**fp_kwargs)] = app_msg_id

        return fingerprint_mapping

    def batch_insert_fingerprint(self, msg_fingerprint_mapping=None, log_fingerprint_mapping=None, timeout=None):
        """
        :param msg_fingerprint_mapping: dict,
        :param log_fingerprint_mapping: dict,
        :param timeout: int, expire time to redis key

        Note that: Using pipeline is better than setting the expiration time for a single time,
                   but it is still slow when the data volume is large

            with redis_conn.pipeline(transaction=False) as p:
                for key, value in bulk_mappings.items():
                    # redis_conn.set(key, value, expire_time)
                    redis_conn.expire(key, expire_time)

                p.execute()  # batch execution

        Redis-cli: redis-cli -h [ip] -p [port] -a [pwd] keys "key_*" | xargs -i redis-cli -h ip -p [port] -a [pwd] expire {} [seconds]
               eg: redis-cli -h 127.0.0.1 -p 6481 -a 123456 keys "falconSing*" | xargs -i redis-cli -h 127.0.0.1 -p 6481 -a pxf12t expire {} 3600
        """
        redis_conn = get_redis_connection()
        expire_lua = """
            for i=1, ARGV[1], 1 do
                redis.call("EXPIRE", KEYS[i], ARGV[2]);
            end
        """
        timeout = timeout or self.DEFAULT_EXPIRE
        bulk_fingerprint_mapping = dict(msg_fingerprint_mapping or {}, **(log_fingerprint_mapping or {}))

        if not bulk_fingerprint_mapping:
            return

        try:
            cmd = redis_conn.register_script(expire_lua)
            redis_conn.mset(bulk_fingerprint_mapping)

            total_cnt = len(bulk_fingerprint_mapping)
            cmd(keys=list(bulk_fingerprint_mapping.keys()), args=[total_cnt, timeout])

            logger.info("bulk_insert_fingerprint_to_redis => set %s ok", total_cnt)
        except Exception as e:
            logger.error(traceback.format_exc())

    def create(self, validated_data):
        # `app_token` field is read-only, Only from `self.initial_ Data`
        model_cls = self.Meta.model
        app_token = self.initial_data.get("app_token")

        if not app_token:
            raise PermissionError("<app_token> is empty, App message cannot be pushed.")

        app_obj = models.AppTokenPlatformModel.get_app_by_token(app_token=app_token)
        app_id = app_obj.id
        new_validated_data = self.clean_data(dict(validated_data, app_obj=app_obj, **self.initial_data))

        # Message body fingerprint mapping
        message_fingerprint_mapping = {}
        message_fingerprint = self.get_fingerprint(new_validated_data)
        new_validated_data["fingerprint"] = message_fingerprint

        cache_val = self._get_cache_from_redis(app_id, message_fingerprint)
        app_msg_id = cache_val and int(cache_val) or None
        fp_kwargs = dict(app_id=app_id, msg_fingerprint=message_fingerprint)

        if not app_msg_id:
            app_msg_obj = models.AppMessageModel.create_object(**new_validated_data)
            app_msg_id = app_msg_obj.id
            message_fingerprint_mapping[self.APP_MSG_FINGERPRINT_KEY.format(**fp_kwargs)] = app_msg_id

        # Message Push Fingerprint Mapping
        log_fingerprint_mapping = {}
        mobile = new_validated_data["receiver_mobile"]

        if not self._get_cache_from_redis(app_obj.id, message_fingerprint, mobile):
            new_validated_data["app_msg_id"] = app_msg_id
            instance_list = model_cls.create_object(**new_validated_data)
            fp_kwargs["mobile"] = mobile
            log_fingerprint_mapping[self.APP_LOG_FINGERPRINT_KEY.format(**fp_kwargs)] = instance_list.id
        else:
            logger.info("%s.create() App message already exists" % self.__class__.__name__)
            instance_list = []

        self.batch_insert_fingerprint(message_fingerprint_mapping, log_fingerprint_mapping)
        return instance_list

