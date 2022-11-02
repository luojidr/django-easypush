from django.db import models
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from easypush.utils.util import DEFAULT_DATETIME
from easypush.utils.constants import AppPlatformEnum, QyWXMediaEnum
from easypush.utils.constants import QyWXMessageTypeEnum
from easypush.utils.constants import DingTalkMessageTypeEnum
from easypush.core.db.base import BaseAbstractModel
from easypush.core.crypto import AESHelper
from easypush.core.path_builder import PathBuilder

default_storage = FileSystemStorage()
PLATFORM_CHOICES = [(p_enum.type, p_enum.desc) for p_enum in AppPlatformEnum.iterator()]
MSG_CHOICES = QyWXMessageTypeEnum.get_items() + DingTalkMessageTypeEnum.get_items()


class AppTokenPlatformModel(BaseAbstractModel):
    """ Application info(ding_talk、qy_weixin、feishu etc.) """

    # from django.core.management.utils import get_random_secret_key
    TOKEN_KEY = "jvum7is)@ftae=iv"      # 固定值: 16位

    corp_id = models.CharField(verbose_name="企业corpId", max_length=100, db_index=True, default="")
    app_name = models.CharField(verbose_name="应用名称", max_length=100, default="")
    agent_id = models.IntegerField(verbose_name="AppId", unique=True, default=0)
    app_key = models.CharField(verbose_name="应用 appKey", max_length=200, default="")
    app_secret = models.CharField(verbose_name="应用 appSecret", max_length=500, default="")
    app_token = models.CharField(verbose_name="外部调用的唯一Token", max_length=500, db_index=True, default="")
    expire_time = models.BigIntegerField(verbose_name="Token过期时间", default=0)
    platform_type = models.CharField(verbose_name="平台类型", max_length=100, choices=PLATFORM_CHOICES, default="")

    class Meta:
        db_table = "easypush_app_token_platform"

    def __str__(self):
        return "<Platform:%s agentId: %s>" % (self.platform_type, self.agent_id)

    def encrypt_token(self):
        raw_text_fmt = "%s:%s:%s:%s:%s"  # agent_id:corp_id:app_key:app_secret:platform_type
        raw = raw_text_fmt % (self.agent_id, self.corp_id, self.app_key, self.app_secret, self.platform_type)
        cipher_text = AESHelper(key=self.TOKEN_KEY).encrypt(raw=raw)

        return cipher_text

    def decrypt_token(self):
        return self.decipher_text(self.app_token)

    @classmethod
    def decipher_text(cls, app_token):
        cipher_text = app_token
        plain_text = AESHelper(key=cls.TOKEN_KEY).decrypt(text=cipher_text)

        return plain_text

    @classmethod
    def get_agent_id_by_token(cls, app_token):
        plain_token = cls.decipher_text(app_token)
        agent_id = int(plain_token.split(":", 1)[0])

        return agent_id

    @classmethod
    def get_app_by_token(cls, app_token):
        try:
            agent_id = cls.get_agent_id_by_token(app_token)
            app_obj = cls.objects.get(agent_id=agent_id)

            return app_obj
        except Exception:
            raise ObjectDoesNotExist("应用 app_token 不合法！")


class AppMediaStorageModel(BaseAbstractModel):
    MEDIA_CHOICES = [(q_enum.type, q_enum.desc) for q_enum in QyWXMediaEnum.iterator()]

    app = models.ForeignKey(to="AppTokenPlatformModel", verbose_name="应用id", on_delete=models.CASCADE, related_name="app")
    media_type = models.CharField(verbose_name="媒体类型", max_length=50, choices=MEDIA_CHOICES, blank=True)
    media_title = models.CharField(verbose_name="媒体名称", max_length=500, default="", blank=True)
    media_id = models.CharField(verbose_name="媒体id", max_length=100, default="", blank=True)

    # 图片保存在服务器端(字段名media是前端传过来的文件字段)
    media = models.FileField("存储路径", upload_to=PathBuilder("media"), storage=default_storage, max_length=200, blank=True)
    key = models.CharField("上传文件key", unique=True, max_length=50, default="", blank=True)
    media_url = models.URLField("媒体文件URL", max_length=500, default="", blank=True)
    file_size = models.IntegerField("文件大小", default=0, blank=True)
    check_sum = models.CharField("源文件md5", max_length=64, default="", blank=True)
    src_filename = models.CharField("源文件名称", max_length=200, default="", blank=True)
    post_filename = models.CharField("处理后的文件名称", max_length=200, default="", blank=True)
    is_share = models.BooleanField("是否共享", default=False, blank=True)
    is_success = models.BooleanField("是否成功", default=False, blank=True)
    access_token = models.CharField("共享token", max_length=100, default="", blank=True)

    class Meta:
        db_table = "easypush_app_media_storage"

    @classmethod
    def get_media_by_key(cls, key):
        try:
            return cls.objects.get(key=key, is_del=False)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            pass


class AppMessageModel(BaseAbstractModel):
    app = models.ForeignKey(to=AppTokenPlatformModel, verbose_name="应用id", default=None, on_delete=models.DO_NOTHING)
    msg_type = models.CharField(verbose_name="消息类型", max_length=50, choices=MSG_CHOICES, default=0, blank=True)
    msg_body_json = models.CharField(verbose_name="消息JSON数据", max_length=2000, default="", blank=True)
    platform_type = models.CharField(verbose_name="平台类型", max_length=100, choices=PLATFORM_CHOICES, default="")
    # fingerprint = models.CharField(verbose_name="消息指纹", max_length=100, default="", blank=True)
    remark = models.CharField(verbose_name="说明", max_length=200, default="", blank=True)

    class Meta:
        db_table = "easypush_app_message_info"


class AppMsgPushRecordModel(BaseAbstractModel):
    """ Application pushed message log """

    # 建议不要使用外键, 推送记录没必要过分要求数据一致性和完整性
    # app_msg = models.ForeignKey(to=AppMessageModel, related_name="app_msg", default=None, on_delete=models.CASCADE)
    app_msg_id = models.IntegerField(verbose_name="消息主体", default=None, blank=True)
    sender = models.CharField(verbose_name="推送人(默认系统)", max_length=100, default="sys", blank=True)
    send_time = models.DateTimeField(verbose_name="推送时间", auto_now_add=True, blank=True)
    receiver_mobile = models.CharField(verbose_name="接收人手机号", max_length=20, default="", db_index=True, blank=True)
    receiver_userid = models.CharField(verbose_name="接收人userid", max_length=100, default="", blank=True)
    receive_time = models.DateTimeField(verbose_name="接收时间", default=DEFAULT_DATETIME, blank=True)
    is_read = models.BooleanField(verbose_name="接收人是否已读", default=False, blank=True)
    read_time = models.DateTimeField(verbose_name="接收人已读时间", default=DEFAULT_DATETIME, blank=True)
    is_success = models.BooleanField(verbose_name="推送是否成功", default=False, blank=True)
    traceback = models.CharField(verbose_name="推送异常", max_length=1200, default="", blank=True)
    task_id = models.CharField(verbose_name="钉钉创建的异步发送任务ID", default="", max_length=100, db_index=True, blank=True)
    request_id = models.CharField(verbose_name="钉钉推送的请求ID", max_length=100, default="", blank=True)
    msg_uid = models.CharField(verbose_name="消息唯一id", default="", max_length=100, unique=True, blank=True)
    is_recall = models.BooleanField(verbose_name="消息是否撤回", default=False, blank=True)
    recall_time = models.DateTimeField(verbose_name="撤回时间", default=DEFAULT_DATETIME, blank=True)
    msg_type = models.CharField(verbose_name="消息类型", max_length=50, choices=MSG_CHOICES, default=0, blank=True)
    platform_type = models.CharField(verbose_name="平台类型", max_length=100, choices=PLATFORM_CHOICES, default="")

    class Meta:
        db_table = "easypush_app_msg_push_records"
