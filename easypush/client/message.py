import os.path
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .loader import BackendLoader
from easypush.utils.exceptions import FuncInvokeError


class MessageBase:
    loader_cls = BackendLoader

    def __init__(self, using=None):
        conf = settings.EASYPUSH[using]
        backend = conf.get("BACKEND", None)

        if backend is None:
            raise ImproperlyConfigured("Not find config for 'BACKEND' in settings.EASYPUSH[%s]" % backend)

        backend_cls = self.loader_cls(backend).load_backend_cls()
        self._client = backend_cls(using=using)
        setattr(self, "logger", self._client.logger)


class AppMessage(MessageBase):
    """ 应用消息 """
    def upload_media(self, media_type, filename=None):
        return self._client.upload_media(media_type, filename=filename)

    def async_send(self, msgtype, body_kwargs, userid_list=(), dept_id_list=()):
        return self._client.async_send(
            msgtype=msgtype,
            body_kwargs=body_kwargs,
            userid_list=userid_list,
            dept_id_list=dept_id_list
        )

    def recall(self, task_id):
        pass

    def __getattr__(self, name):
        func = getattr(self._client, name, None)

        if not callable(func):
            raise FuncInvokeError("`%s` method not invoked." % name)

        def call(*args, **kwargs):
            return func(*args, **kwargs)

        return call






