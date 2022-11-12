import os.path
import importlib
from datetime import datetime

from django.conf import settings
from django.utils.datastructures import MultiValueDict
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import InMemoryUploadedFile

from .loader import BackendLoader
from easypush.utils.constants import AppPlatformEnum
from easypush.utils.exceptions import FuncInvokeError, BackendError

__all__ = ["AppMessageHandler"]


class MessageBase:
    loader_cls = BackendLoader

    def __init__(self, using=None, **kwargs):
        self.auto_save = False      # whether to automatically save to the database
        self.async_mode = False     # whether to send message using mq
        self._loaded_cache = {}

        if using is None:
            name = kwargs.pop("backend")
            backend = "easypush.backends.%s.%sClient" % (name, name.title().replace("_", ""))

            if not any([name == e.type for e in AppPlatformEnum.iterator()]):
                raise BackendError("`%s` Backend not exist." % backend)

            using = name
            self._conf = {
                "BACKEND": backend,
                "CORP_ID": kwargs["corp_id"],
                "AGENT_ID": kwargs["agent_id"],
                "APP_KEY": kwargs["app_key"],
                "APP_SECRET": kwargs["app_secret"],
            }
        else:
            self._conf = settings.EASYPUSH[using]

        self.using = using
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

    def _get_module_with_registered(self, name):
        pkg_name = __package__.split(".", 1)[0]
        pkg_path = "%s.%s" % (pkg_name, name)

        if pkg_path in self._loaded_cache:
            return self._loaded_cache[pkg_path]

        module = importlib.import_module(pkg_path)
        self._loaded_cache[pkg_path] = module
        return module


class AppMessageHandler(MessageBase):
    """ Application send handler """
    def _get_app_object(self):
        models = self._get_module_with_registered("models")
        app_model_cls = models.AppTokenPlatformModel
        app_obj = app_model_cls.objects.filter(
            corp_id=self._conf["CORP_ID"], agent_id=self._conf["AGENT_ID"],
            app_key=self._conf["APP_KEY"], app_secret=self._conf["APP_SECRET"],
        ).first()

        if app_obj is None:
            raise ObjectDoesNotExist("No app token record in `%s` table" % app_model_cls._meta.db_table)

        return app_obj

    def upload_media(self, media_type, filename=None, media_file=None, auto_save=False):
        auto_save = auto_save or self.auto_save

        if auto_save:
            app_obj = self._get_app_object()
            using = app_obj.platform_type
            forms = self._get_module_with_registered("forms")

            fp = open(filename, "rb")
            # print(fp.read())
            # fp.seek(0, os.SEEK_END)
            size = os.path.getsize(filename)
            # fp.seek(0)
            # print(fp.read())

            files = MultiValueDict()
            files["media"] = InMemoryUploadedFile(
                fp, field_name="media", name=filename,
                content_type=None, size=size, charset=None
            )
            media_data = dict(media_title=os.path.basename(filename), media_type=media_type, app=app_obj.id, **files)

            try:
                media_obj = forms.UploadAppMediaForm.create_media(media_data, files=files, using=using)
                return dict(
                    errcode=0, errmsg="ok", media_id=media_obj.media_id,
                    type=media_obj.media_type, created_at=int(datetime.now().timestamp())
                )
            finally:
                fp.close()
        else:
            return self._client.upload_media(media_type, filename=filename, media_file=media_file)

    def async_send(self, msgtype, body_kwargs, userid_list=(), dept_id_list=(), async_mode=False):
        async_mode = async_mode or self.async_mode

        if async_mode:
            app_obj = self._get_app_object()
            serializers = self._get_module_with_registered("serializers")
            tasks = self._get_module_with_registered("tasks.task_send_message")

            data = dict(
                app_token=app_obj.app_token, msg_type=msgtype, receiver_mobile="",
                msg_body_json=body_kwargs, receiver_userid=",".join(userid_list),
            )
            serializers.AppMsgPushRecordSerializer.async_send_mq(
                data=data,  task_fun=tasks.send_message_by_mq
            )
            return dict(self._get_result(), errmsg="async mq")

        result = self._client.send(
            msgtype=msgtype, body_kwargs=body_kwargs,
            userid_list=userid_list, dept_id_list=dept_id_list
        )
        return self._get_result(data=result)

    def recall(self, task_id):
        return self._client.recall(task_id=task_id)

    def __getattr__(self, name):
        func = getattr(self._client, name, None)

        if not callable(func):
            raise FuncInvokeError("`%s` method not invoked." % name)

        def call(*args, **kwargs):
            return func(*args, **kwargs)

        return call

    def _get_result(self, data=None):
        client_name = self._client.client_name
        std_data = {"errcode": 0, "errmsg": "ok", "task_id": "", "request_id": "", "data": None}

        if data is None:
            return std_data

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
                errcode=data.pop("code", -1), errmsg=data.pop("msg", "error"),
                task_id=data.get("data", {}).get("message_id", ""), request_id="", data=data
            )
        else:
            std_data = data

        return std_data

    def get_expire_time(self, timestamp):
        """ media expiration """
        if len(str(timestamp)) > 10:
            # millisecond
            timestamp = str(timestamp)[:10]

        timestamp = int(timestamp) + self._client.MEDIA_EXPIRE_TIME
        return datetime.fromtimestamp(timestamp)




