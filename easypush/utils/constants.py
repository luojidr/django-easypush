import enum
import importlib

from dingtalk.model import message


class EnumBase(enum.Enum):
    @classmethod
    def iterator(cls):
        members = [
            one for one in cls._member_map_.values()
            if one.name.isupper() and not one.name.startswith("_")
        ]
        return iter(members)


class AppPlatformEnum(EnumBase):
    SMS = ("sms", "短信")
    EMAIL = ("email", "邮件")
    FEISHU = ("feishu", "飞书")
    DING_DING = ("ding_talk", "钉钉")
    QY_WEIXIN = ("qy_weixin", "企业微信")

    @property
    def type(self):
        return self.value[0]

    @property
    def desc(self):
        return self.value[1]


class _MediaEnumBase(EnumBase):
    @property
    def type(self):
        return self.value[0]

    @property
    def max_size(self):
        return self.value[1]

    @property
    def body_class(self):
        cls = self.value[2]

        if isinstance(cls, str):
            cls_name = cls
            body_module = getattr(self, "_BODY_MODULE", None)

            if body_module is None or body_module.value is None:
                raise ValueError("_MediaEnumBase._BODY_MODULE is empty.")

            module = importlib.import_module(body_module.value)
            cls = getattr(module, cls_name)

        return cls

    @property
    def desc(self):
        return self.value[3]

    @classmethod
    def media_list(cls):
        return [each_enum.type for each_enum in cls.iterator()]

    @classmethod
    def get_media_enum(cls, msg_type):
        enum_list = [each_enum for each_enum in cls.iterator() if each_enum.type == msg_type]

        if not enum_list:
            raise ValueError("Not exist `%s` DingTalkMediaEnum" % msg_type)

        return enum_list[0]


class DingTalkMediaEnum(_MediaEnumBase):
    IMAGE = ("image", 1024 * 1024, message.ImageBody, "图片")
    FILE = ("file", 10 * 1024 * 1024, message.FileBody, "普通文件")
    VOICE = ("voice", 2 * 1024 * 1024, message.VoiceBody, "语音")


class QyWXMediaEnum(_MediaEnumBase):
    _BODY_MODULE = "easypush.backends.qy_weixin.api.body"

    IMAGE = ("image", 10 * 1024 * 1024, "ImageBody", "图片")
    FILE = ("file", 20 * 1024 * 1024, "FileBody", "普通文件")
    VOICE = ("voice", 2 * 1024 * 1024, "VoiceBody", "语音")
    VIDEO = ("video", 10 * 1024 * 1024, "VoiceBody", "视频")


class _MessageTypeEnumBase(EnumBase):
    @property
    def type(self):
        return self.value[0]

    @property
    def desc(self):
        return self.value[1]

    @classmethod
    def get_message_enum(cls, msg_type):
        enum_list = [each_enum for each_enum in cls.iterator() if each_enum.type == msg_type]

        if not enum_list:
            raise ValueError("%s not exist `%s` enum" % (cls.__name__, msg_type))

        return enum_list[0]

    @classmethod
    def get_items(cls):
        msg_type_result = {_enum.type: _enum.desc for _enum in cls.iterator()}
        return list(msg_type_result.items())


class DingTalkMessageTypeEnum(_MessageTypeEnumBase):
    TEXT = ("text", "文本消息")
    IMAGE = ("image", "图片消息")
    VOICE = ("voice", "语音消息")
    FILE = ("file", "文件消息")
    LINK = ("link", "链接消息")
    OA = ("oa", "OA 消息")
    MARKDOWN = ("markdown", "markdown 消息")
    ACTION_CARD = ("action_card", "action_card 消息")
    SINGLE_ACTION_CARD = ("single_action_card", "action_card 消息")
    BTN_ACTION_CARD = ("btn_action_card", "action_card 消息")


class QyWXMessageTypeEnum(_MessageTypeEnumBase):
    TEXT = ("text", "文本消息")
    IMAGE = ("image", "图片消息")
    VOICE = ("voice", "语音消息")
    FILE = ("file", "文件消息")
    NEWS = ("news", "图文消息")
    MP_NEWS = ("mpnews", "图文消息")
    MARKDOWN = ("markdown", "markdown 消息")
    TEXT_CARD = ("textcard", "文本卡片消息")
    MINI_PROGRAM_NOTICE = ("miniprogram_notice", "小程序通知消息")
    TEMPLATE_CARD = ("template_card", "模板卡片消息")


