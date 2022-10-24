import inspect
from inspect import Parameter

from easypush.utils import exceptions


class MsgBodyBase:
    _msgtype = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if callable(v):
                v = v()
            setattr(self, k, v)

    def get_dict(self):
        assert self._msgtype
        return {'msgtype': self._msgtype, self._msgtype: self._get_data()}

    def _get_data(self):
        ret = {}
        keys = [k for k in dir(self) if not k.startswith('_')]

        for k in keys:
            v = getattr(self, k, None)

            if v is None or hasattr(v, '__call__'):
                continue

            if v is not None:
                if isinstance(v, MsgBodyBase):
                    v = v._get_data()
                ret[k] = v

        return ret

    @property
    def msgtype(self):
        return self._msgtype


class ParserBodyBase:
    MESSAGE_TYPE_ENUM = None
    MESSAGE_MEDIA_ENUM = None

    def __init__(self, msg_type, **kwargs):
        self._msg_type = msg_type

        if self.MESSAGE_TYPE_ENUM is None:
            raise ValueError("MESSAGE_TYPE_ENUM attribute not allowed empty")

        if self.MESSAGE_MEDIA_ENUM is None:
            raise ValueError("MESSAGE_MEDIA_ENUM attribute not allowed empty")

    def check_msg_type(self, body_cls):
        if self._msg_type is None:
            raise exceptions.MessageTypeError("消息类型错误")

        msgtype = getattr(body_cls, "_msgtype", None)
        assert self._msg_type == msgtype

    def get_body_method(self):
        message_enum = self.MESSAGE_TYPE_ENUM.get_message_enum(self._msg_type)
        body_method_name = "get_%s_body" % message_enum.type
        body_method = getattr(self, body_method_name, None)

        if body_method is None:
            self.MESSAGE_MEDIA_ENUM.get_media_enum(self._msg_type)
            body_method = getattr(self, "get_media_body", None)

        if body_method is None:
            raise exceptions.NotExistMessageBodyMethod("消息类型方法不存在")

        return body_method

    def get_message_body(self, **body_kwargs):
        """ 根据不同的消息类型获取对应的消息体 """
        body_method = self.get_body_method()

        if body_method is None:
            raise exceptions.MessageTypeError("DingTalk消息类为空.")

        # 过滤消息体参数
        new_body_kwargs = dict()
        sig = inspect.signature(body_method)
        parameters = sig.parameters

        for key, param in parameters.items():
            default = param.default  # 参数签名默认值
            has_key = key not in body_kwargs
            value = body_kwargs.pop(key, None)

            if default is param.empty:
                # 位置参数必须赋值
                if param.kind not in [Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD] and has_key:
                    raise exceptions.MessageBodyFieldError("%s类型消息缺少 %s 参数" % (self._msg_type, key))

                new_body_kwargs[key] = value
            else:
                new_body_kwargs[key] = value or default

        # body_kwargs 其他参数
        new_body_kwargs.update(body_kwargs)
        return body_method(**new_body_kwargs)

