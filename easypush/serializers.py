import time
import logging
import traceback
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.db.models import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django_redis import get_redis_connection

from . import models
from .core.crypto import BaseCipher
from .utils.snowflake import IdGenerator
from .utils.exceptions import MessagePlatformError

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

        # platform_type_mapping = dict(models.PLATFORM_CHOICES)
        # if instance.platform_type not in platform_type_mapping:
        #     raise MessagePlatformError("platform `%s` not exit" % instance.platform_type)

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
        """ 批量创建
        @:param validated_data: list
        """
        # 校验通过后, self.initial_data 与 validated_data 数据一致, 除了 validated_data 的每个字典中不包含 app_token
        # mobile与jobCode
        mobile_list = [item["receiver_mobile"] for item in validated_data]
        user_query_kwargs = dict(phone_number__in=mobile_list, is_del=False)
        user_queryset = CircleUsersModel.objects.filter(**user_query_kwargs).values("phone_number", "ding_job_code")
        mobile_jobCode_dict = {user_item["phone_number"]: user_item["ding_job_code"] for user_item in user_queryset}

        # 微应用信息
        app_token_list = [item["app_token"] for item in self.initial_data]
        plain_token_list = [DingAppTokenModel.decipher_text(_app_token) for _app_token in app_token_list]
        agent_id_list = [int(_plain_token.split(":", 1)[0]) for _plain_token in plain_token_list]

        app_query_kwargs = dict(agent_id__in=agent_id_list, is_del=False)
        app_queryset = DingAppTokenModel.objects.filter(**app_query_kwargs).values("id", "agent_id")
        app_agent_dict = {app_item["agent_id"]: app_item["id"] for app_item in app_queryset}

        bulk_obj_list = []
        model_cls = self.child.Meta.model

        # 根据消息记录指纹过滤重复记录(钉钉消息记录) => 被优化了
        # app_ids = list(app_agent_dict.values())
        # mobile_list = list(mobile_jobCode_dict.keys())
        # msg_log_fingerprint_set = self.child.get_sent_message_log_fingerprints(mobile_list, app_ids=app_ids)

        # 钉钉消息主体指纹
        ding_message_body_mapping = {}
        ding_message_log_mapping = {}
        cost_start_time = time.time()

        for index, data in enumerate(self.initial_data):
            message_data = dict(data, **validated_data[index])
            new_validated_data = self.child.derive_value(message_data)

            plain_token = DingAppTokenModel.decipher_text(new_validated_data["app_token"])
            agent_id = int(plain_token.split(":", 1)[0])

            # 消息主体指纹
            app_id = app_agent_dict.get(agent_id)
            new_validated_data["app_id"] = app_id
            message_body_fingerprint = self.child.get_message_body_fingerprint(new_validated_data)

            # _ding_msg_id = ding_message_results.get(message_body_fingerprint)
            _ding_msg_id = self.child._get_app_id_by_msg_fingerprint(message_body_fingerprint)

            if not _ding_msg_id:
                ding_msg_obj = DingMessageModel.create_object(**new_validated_data)
                _ding_msg_id = ding_msg_obj.id

            # 暂存
            ding_message_body_mapping[message_body_fingerprint] = _ding_msg_id

            # 补充消息记录信息并过滤消息记录指纹
            mobile = new_validated_data["receiver_mobile"]
            new_validated_data.update(
                ding_msg_id=_ding_msg_id,
                receiver_job_code=mobile_jobCode_dict.get(mobile, ""),
            )
            log_fingerprint = self.child.get_fingerprint(validated_data=new_validated_data)

            # if log_fingerprint not in msg_log_fingerprint_set:
            if not self.child._has_msg_log_fingerprint(app_id, _ding_msg_id, mobile, log_fingerprint):
                ding_message_log_mapping[(app_id, _ding_msg_id, mobile)] = log_fingerprint
                bulk_obj_list.append(model_cls.create_object(force_insert=False, **new_validated_data))

        instance_list = model_cls.objects.bulk_create(bulk_obj_list)

        self.child.bulk_insert_fingerprint_to_redis(ding_message_body_mapping, ding_message_log_mapping)
        return instance_list


class AppMsgPushRecordSerializer(serializers.ModelSerializer):
    APP_MSG_BODY_KEY = "msg_body:%s"
    APP_MSG_LOG_KEY = "msg_log:app_id:%s:msg_id:%s:mobile:%s"

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

    @property
    def fingerprint_fields(self):
        return ["msg_extra_json"]

    def get_fingerprint(self, validated_data=None):
        """ 消息唯一性指纹 """
        fingerprint_fields = self.fingerprint_fields
        fingerprint_info = ":".join(["{%s}" % _field for _field in fingerprint_fields])

        if validated_data:
            msg_kwargs = {k: validated_data.get(k, "") for k in fingerprint_fields}
        else:
            raise ValidationError("无法获取消息指纹")

        fingerprint_msg = fingerprint_info.format(**msg_kwargs)
        md5 = BaseCipher.crypt_md5(fingerprint_msg)

        return md5

    def query_raw_sql(self, sql, params=None, using=None, columns=()):
        """ 原生sql查询 """
        model_cls = self.Meta.model
        connection = connections[using or DEFAULT_DB_ALIAS]
        cursor = connection.cursor()

        cursor.execute(sql, params=params)
        result = cursor.fetchall()
        mapping_result = [dict(zip(columns, item)) for item in result]

        return mapping_result

    def get_one_message_fingerprint(self, message_value):
        """ 消息主体指纹 """
        fields = models.AppMessageModel.fields()
        required_fields = [name for name in self.fingerprint_fields if name in fields]

        message_fingerprint_rule = ":".join(["{%s}" % col for col in required_fields])
        message_fingerprint = message_fingerprint_rule.format(**message_value)

        return BaseCipher.crypt_md5(message_fingerprint)

    def get_message_fingerprints_mapping(self):
        """ 钉钉消息体的指纹映射 """
        msg_body_mappings = {}
        msg_model_cls = models.AppMessageModel

        exclude_fields = ("source_cn", "msg_type_cn", "ihcm_survey_id")
        fields = msg_model_cls.fields(exclude=exclude_fields)
        sql = "SELECT {columns} FROM {tb_name} " \
                  "WHERE is_del=false".format(columns=",".join(fields), tb_name=msg_model_cls._meta.db_table)
        msg_body_results = self.query_raw_sql(sql, using=None, columns=fields)

        for msg_body_item in msg_body_results:
            fingerprint = self.get_message_body_fingerprint(msg_body_item)
            msg_body_mappings[fingerprint] = msg_body_item["id"]

        return msg_body_mappings

    def _get_app_id_by_fingerprint(self, msg_fingerprint):
        redis_conn = get_redis_connection()

        key = self.APP_MSG_BODY_KEY % msg_fingerprint
        app_msg_id = redis_conn.get(key)

        return app_msg_id and int(app_msg_id) or None

    def clean_data(self, data):
        id_yield = IdGenerator(1, 1)

        data.update(
            is_read=False, is_success=False, sender="sys",
            send_time=datetime.now(), msg_uid=id_yield.get_id(),
        )

        return data

    def get_sent_log_fingerprints(self, mobile_list=None, app_ids=None, is_raw=False):
        """ 已发送的消息的指纹,用于过滤目的(最近30个月)
            达到快速过滤: 布隆过滤

        :param mobile_list, 手机号列表
        :param app_ids, 微应用列表
        :param is_raw, 是否使用原生sql查询
        """
        validated_data_list = []
        app_ids = app_ids or []
        mobile_list = mobile_list or []
        start_time = time.time()

        model_cls = self.Meta.model
        model_fields = model_cls.fields()
        fingerprint_fields = self.fingerprint_fields

        # 钉钉消息体和关联微应用
        start_ts002 = time.time()
        msg_fields = models.AppMessageModel.fields(exclude=("source_cn", "msg_type_cn", "ihcm_survey_id"))

        if not is_raw:
            orm_query = dict(is_del=False)
            app_ids and orm_query.update(app_id__in=app_ids)
            msg_queryset = models.AppMessageModel.objects.filter(**orm_query).values(*msg_fields)
            msg_mapping_dict = {msg_item["id"]: msg_item for msg_item in msg_queryset}
        else:
            sql_where = "where is_del=false "
            if app_ids:
                sql_where += " and app_id in (%s)" % ",".join([str(_id) for _id in app_ids])

            msg_sql = "SELECT {msg_columns} FROM circle_ding_message_info ".format(msg_columns=", ".join(msg_fields))
            msg_queryset = self.query_raw_sql(msg_sql + sql_where, columns=msg_fields)
            msg_mapping_dict = {msg_item["id"]: msg_item for msg_item in msg_queryset}

        start_ts003 = time.time()
        msg_cost_time = start_ts003 - start_ts002
        # logger.info("get_sent_messages_fingerprint MsgInfo cost time: %s, is_raw: %s", msg_cost_time, is_raw)

        # 筛选对应的消息记录
        ding_msg_ids = list(msg_mapping_dict.keys())
        latest_sent_time = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        if not is_raw:
            orm_query = dict(ding_msg_id__in=ding_msg_ids, send_time__gt=latest_sent_time)
            mobile_list and orm_query.update(receiver_mobile__in=list(set(mobile_list)))
            log_msg_queryset = model_cls.objects.filter(**orm_query).values("receiver_mobile", "ding_msg_id")
            # logger.info("log_msg_queryset SQL:%s", log_msg_queryset.query)
        else:
            sql_where = " where send_time >= '%s' " % latest_sent_time
            sql_where += " ding_msg_id in (%s) " % ",".join([str(did) for did in ding_msg_ids])
            if mobile_list:
                sql_where += " receiver_mobile in (%s)".join(set(mobile_list))

            log_msg_columns = ["receiver_mobile", "ding_msg_id"]
            log_msg_sql = "SELECT {columns} FROM circle_ding_msg_push_log ".format(columns=",".join(log_msg_columns))
            log_msg_queryset = self.query_raw_sql(log_msg_sql + sql_where, columns=log_msg_columns)

        for log_msg_item in log_msg_queryset:
            ding_msg_id = log_msg_item["ding_msg_id"]
            item = dict(ding_msg_id=ding_msg_id)

            for field_name in fingerprint_fields:
                if field_name not in model_fields:
                    ding_msg_item = msg_mapping_dict.get(ding_msg_id) or {}
                    item[field_name] = ding_msg_item.get(field_name, "")
                else:
                    item[field_name] = log_msg_item[field_name]

            validated_data_list.append(item)

        # logger.info("get_sent_messages_fingerprint MsgLog cost time: %s", time.time() - start_ts003)
        # logger.info("get_sent_messages_fingerprint all cost time: %s", time.time() - start_time)

        return {self.get_fingerprint(validated_data=item): item for item in validated_data_list}

    def _has_log_fingerprint(self, app_id, ding_msg_id, mobile, fingerprint):
        redis_conn = get_redis_connection()

        key = self.APP_MSG_LOG_KEY % (app_id, ding_msg_id, mobile)
        old_fingerprint = redis_conn.get(key)

        return old_fingerprint == fingerprint

    def bulk_insert_fingerprint_to_redis(self, bulk_msg_mappings=None, bulk_log_mappings=None, timeout=15 * 60 * 60):
        """ 批量插入Redis,使用 Lua 可极大提升性能

        :param bulk_body_mappings: dict,
            eg: {'804cac0dc22aff073fgy': 1234} => ｛fingerprint: ding_msg_id｝
        :param bulk_log_mappings: dict,
            eg： {(1, 2134, '13570921106'): '476743867646a97'} => {(app_id, ding_msg_id, mobile): fingerprint}
        :param timeout: int, expire time to redis key

        # 使用 pipeline 优于单次设置过期时间，但是量大时依然很慢
            with redis_conn.pipeline(transaction=False) as p:
                for key, value in bulk_mappings.items():
                    # redis_conn.set(key, value, expire_time)
                    redis_conn.expire(key, expire_time)

                p.execute()  # 批量执行

        """
        redis_conn = get_redis_connection()
        expire_lua = """
            for i=1, ARGV[1], 1 do
                redis.call("EXPIRE", KEYS[i], ARGV[2]);
            end
        """

        bulk_body_mappings = bulk_body_mappings or {}
        bulk_log_mappings = bulk_log_mappings or {}

        try:
            if not isinstance(bulk_body_mappings, dict) or not isinstance(bulk_log_mappings, dict):
                raise ValueError("bulk_body_mappings or bulk_log_mappings not dict")

            cmd = redis_conn.register_script(expire_lua)

            if bulk_body_mappings:
                bulk_body_mappings = {self.APP_MSG_BODY_KEY % body_fp: value for body_fp, value in
                                      bulk_body_mappings.items()}
                redis_conn.mset(bulk_body_mappings)
                cmd(keys=list(bulk_body_mappings.keys()), args=[len(bulk_body_mappings), timeout])

            if bulk_log_mappings:
                # {(app_id, ding_msg_id, mobile): fingerprint}
                bulk_log_mappings = {self.APP_MSG_LOG_KEY % key: log_fp for key, log_fp in
                                     bulk_log_mappings.items()}
                redis_conn.mset(bulk_log_mappings)
                cmd(keys=list(bulk_log_mappings.keys()), args=[len(bulk_log_mappings), timeout])

            # logger.info("bulk_insert_fingerprint_to_redis(msg_body) ok: Cnt:%s", len(bulk_body_mappings))
            # logger.info("bulk_insert_fingerprint_to_redis(msg_log) ok: Cnt:%s", len(bulk_body_mappings))
        except Exception as e:
            traceback.format_exc()

    def create(self, validated_data):
        # app_token = validated_data.pop("app_token", None)  # app_token 只读字段,只能从 initial_data 中获取
        model_cls = self.Meta.model
        app_token = self.initial_data.get("app_token")

        if not app_token:
            raise PermissionError("<app_token> 为空, 应用消息无法推送")

        app_obj = models.AppTokenPlatformModel.get_app_by_token(app_token=app_token)
        # agent_id = app_obj.agent_id

        message_data = dict(validated_data, app_id=app_obj.id, **self.initial_data)
        new_validated_data = self.clean_data(message_data)

        # 消息主体指纹映射
        message_body_mapping = {}
        message_body_fingerprint = self.get_one_message_fingerprint(new_validated_data)
        app_msg_id = self._get_app_id_by_fingerprint(msg_fingerprint=message_body_fingerprint)

        if not app_msg_id:
            app_msg_obj = models.AppMessageModel.create_object(**new_validated_data)
            app_msg_id = app_msg_obj.id
            message_body_mapping[message_body_fingerprint] = app_msg_id

        # 消息推送指纹映射
        message_log_mapping = {}
        new_validated_data["app_msg_id"] = app_msg_id
        log_fingerprint = self.get_fingerprint(validated_data=new_validated_data)

        # if log_fingerprint not in msg_log_fingerprint_set:
        if not self._has_msg_log_fingerprint(app_obj.id, ding_msg_id, receiver_mobile, log_fingerprint):
            instance_list = model_cls.create_object(**new_validated_data)
            ding_message_log_mapping[(app_obj.id, ding_msg_id, receiver_mobile)] = log_fingerprint
        else:
            logger.info("%s.create() 钉钉消息已存在" % self.__class__.__name__)
            instance_list = []

        self.bulk_insert_fingerprint_to_redis(ding_message_body_mapping, ding_message_log_mapping)
        return instance_list

