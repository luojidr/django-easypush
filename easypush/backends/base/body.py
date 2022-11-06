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

    def _get_data(self, ):
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


class BodyFieldValidator:
    """
    >>> raw_data = {
        "select_list": {
            "key": "multi",
            "text": "Sample",
            "list": [
                {
                    "question_key": "question_key1",
                    "title": "选择器标签1",
                    "selected_id": "selection_id1",
                    "option_list": [
                        {
                            "id": "selection_id1",
                            "text": "选择器选项1"
                        },
                        {
                            "id": "selection_id2",
                            "text": "选择器选项2"
                        }
                    ]
                },
            ],
        }
    }

    >>> select_list = BodyFieldValidator("select_list", type="dict", required=True)
    >>> select_list.add_field("key", required=True)
    >>> select_list.add_field("text", required=False)

    >>> _list = BodyFieldValidator("list", type="list", required=True)
    >>> _list.add_field("question_key", required=True)
    >>> _list.add_field("title", required=False)
    >>> _list.add_field("selected_id", required=False)

    >>> option_list = BodyFieldValidator("option_list", type="list", required=True)
    >>> option_list.add_field("id", required=True)
    >>> option_list.add_field("text", required=False)
    >>> _list.add_field(validator=option_list)

    >>> select_list.add_field(validator=_list)
    """

    def __init__(self, key=None, type=None, required=False, fields=()):
        self.field_name = key
        self.field_type = type
        self.required = required
        self._item_fields = fields or []
        self._factory = type and eval(self.field_type) or None

    def add_field(self, key=None, type=None, required=False, validator=None):
        if validator is not None:
            v = validator
        else:
            v = BodyFieldValidator(key=key, type=type, required=required)

        self._item_fields.append(v)

    def get_valid_data(self, raw_data):
        if self.field_name is None or not isinstance(self.field_name, str):
            raise ValueError("BodyFieldValidator.field_name is empty")

        if self.required and self.field_name not in raw_data:
            raise ValueError("BodyFieldValidator field: %s is required" % self.field_name)

        if not self._item_fields:
            return raw_data.get(self.field_name)

        result = self._factory()
        raw_data = raw_data.get(self.field_name, self._factory())

        if self.field_type == "dict":
            data = result.setdefault(self.field_name, {})

            for v in self._item_fields:
                v_data = v.get_valid_data(raw_data)
                if v_data is not None:
                    data[v.field_name] = v_data[v.field_name] if isinstance(v_data, dict) else v_data

        elif self.field_type == "list":
            for raw_items in raw_data:
                new_items = {}

                for v in self._item_fields:
                    v_data = v.get_valid_data(raw_items)
                    new_items[v.field_name] = v_data

                result.append(new_items)

            result = {self.field_name: result}

        return result


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
            try:
                self.MESSAGE_MEDIA_ENUM.get_media_enum(self._msg_type)
            except AttributeError:
                msg = "[%s] `MessageBodyParser` class haven't MESSAGE_MEDIA_ENUM attribute"
                raise AttributeError(msg % self.CLIENT_NAME)
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

