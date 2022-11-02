import os.path
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .loader import BackendLoader
from easypush.utils.constants import AppPlatformEnum
from easypush.utils.exceptions import FuncInvokeError

__all__ = ["AppMessageHandler"]


class MessageBase:
    loader_cls = BackendLoader

    def __init__(self, using=None, **kwargs):
        if kwargs:
            name = kwargs.pop("backend")
            self._conf = {
                "BACKEND": "easypush.backends.%s.%sClient" % (name, name.title().replace("_", "")),
                "CORP_ID": kwargs["corp_id"],
                "AGENT_ID": kwargs["agent_id"],
                "APP_KEY": kwargs["app_key"],
                "APP_SECRET": kwargs["app_secret"],
            }
        else:
            self._conf = settings.EASYPUSH[using]

        backend_engine = self._conf.get("BACKEND", None)
        if backend_engine is None:
            raise ImproperlyConfigured("Not find config for 'BACKEND' any settings.")

        backend_cls = self.loader_cls(backend_engine).load_backend_cls()
        self._client = backend_cls(using=using, **kwargs)
        setattr(self, "logger", self._client.logger)

    @property
    def backend(self):
        return self._client.client_name

    @property
    def agent_id(self):
        return self._conf["AGENT_ID"]


class AppMessageHandler(MessageBase):
    """ 应用消息 """
    def upload_media(self, media_type, filename=None, media_file=None):
        return self._client.upload_media(media_type, filename=filename, media_file=media_file)

    def async_send(self, msgtype, body_kwargs, userid_list=(), dept_id_list=()):
        result = self._client.async_send(
            msgtype=msgtype, body_kwargs=body_kwargs,
            userid_list=userid_list, dept_id_list=dept_id_list
        )

        return self._get_result(data=result)

    def recall(self, task_id):
        pass

    def __getattr__(self, name):
        func = getattr(self._client, name, None)

        if not callable(func):
            raise FuncInvokeError("`%s` method not invoked." % name)

        def call(*args, **kwargs):
            return func(*args, **kwargs)

        return call

    def _get_result(self, data):
        client_name = self._client.client_name
        std_data = {"errcode": 0, "errmsg": "ok", "task_id": "", "request_id": "", "data": None}

        if client_name == AppPlatformEnum.DING_DING.type:
            std_data.update(
                errcode=data["errcode"], errmsg=data["errmsg"],
                task_id=str(data["task_id"]), request_id=data["request_id"]
            )
        elif client_name == AppPlatformEnum.QY_WEIXIN.type:
            std_data.update(
                errcode=data["errcode"], errmsg=data["errmsg"], task_id=data["msgid"],
                data=dict(
                    invalidtag=data.get("invalidtag"), invaliduser=data.get("invaliduser"),
                    invalidparty=data.get("invalidparty"), response_code=data.get("response_code"),
                )
            )
        elif client_name == AppPlatformEnum.FEISHU.type:
            std_data.update(
                errcode=data["code"], errmsg=data["msg"],
                task_id=data["data"].pop("message_id"), request_id=data.pop("data")
            )
        else:
            std_data = data

        return std_data




