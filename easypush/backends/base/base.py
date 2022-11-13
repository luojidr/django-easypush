import io
import time
import logging
import os.path
import datetime
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.base import File
from django_redis import get_redis_connection

from easypush.utils.log import Logger
from easypush.utils.settings import config
from easypush.utils.settings import DEFAULT_EASYPUSH_ALIAS
from easypush.core.crypto import AESCipher
from easypush.core.request.http_client import HttpFactory
from easypush.core.request.multipart import MultiPartForm


class RequestApiBase:
    API_BASE_URL = None
    log_cls = Logger

    REQUEST_CLS = HttpFactory
    MULTIPART_FORM_CLS = MultiPartForm

    def __init__(self, *args, **kwargs):
        self._logger = None
        self._log_path = config.log_path

    def _request(self, method, endpoint, **kwargs):
        api_base_url = self.API_BASE_URL or self._api_base_url

        if not api_base_url:
            raise ValueError("One Push Client `API_BASE_URL` not allowed empty.")

        req_func = self._get if method == "GET" else self._post
        base_url = endpoint.replace(".", "/")
        url = urljoin(api_base_url, base_url)

        headers = kwargs.get("headers", {})
        upload_files = kwargs.pop("upload_files", [])

        if upload_files:
            form = self.MULTIPART_FORM_CLS()
            for post_key, post_val in kwargs.pop("data", {}).items():
                form.add_field(post_key, post_val)

            # Upload => upload_files: a tuple of list, eg: [(fieldname, filename, file_bytes, mimetype)]
            for file_args in upload_files:
                file_bytes = file_args[2]
                mimetype = file_args[3] if len(file_args) > 3 else None

                form.add_file(
                    fieldname=file_args[0], filename=file_args[1],
                    file_handle=io.BytesIO(file_bytes), mimetype=mimetype
                )

            kwargs["data"] = bytes(form)
            headers["Content-Type"] = form.get_content_type()
            headers["Content-length"] = len(kwargs["data"])
        elif not headers:
            headers['Content-Type'] = 'application/json'  # default header

        kwargs["headers"] = headers
        return req_func(url, **kwargs)

    def _get(self, url, params=None, **kwargs):
        return self.REQUEST_CLS(url, params=params, **kwargs).get()

    def _post(self, url, params=None, data=None, **kwargs):
        return self.REQUEST_CLS(url, params=params, **kwargs).post(data=data)

    @property
    def logger(self):
        if self._logger is None:
            dirname = os.path.dirname(self._log_path)

            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)

            if self._log_path:
                self._logger = self.log_cls(filename=self._log_path)
            else:
                self._logger = logging.getLogger("django")

        return self._logger


class ClientMixin(RequestApiBase):
    def __init__(self, corp_id="", agent_id=None, app_key=None, app_secret=None, **kwargs):
        super().__init__()
        self._kwargs = dict(**kwargs)
        self.using = self._kwargs.get("using", DEFAULT_EASYPUSH_ALIAS)

        self._corp_id = corp_id or self.conf["corp_id"]
        self._agent_id = agent_id or self.conf["agent_id"]
        self._app_key = app_key or self.conf["app_key"]
        self._app_secret = app_secret or self.conf["app_secret"]

    @property
    def filepath(self):
        path = os.path.join(settings.MEDIA_ROOT, self.CLIENT_NAME, str(datetime.date.today()))

        if not os.path.exists(path):
            os.makedirs(path)

        return path

    def write_file(self, filename, content=None, file_obj=None):
        with open(filename, 'wb+') as fd:
            if isinstance(file_obj, File):
                iter_chunks = file_obj.chunks()
            else:
                iter_chunks = [content]

            for chunk in iter_chunks:
                fd.write(chunk)

    def get_size(self, file_obj):
        pos = file_obj.tell()
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(pos)
        return size

    def _check_media_exist(self, filename=None, media_file=None):
        if not media_file and not filename:
            raise ValueError("未选择媒体文件!")

        if filename and not os.path.exists(filename):
            raise ValueError("媒体文件不存在")

    def get_access_token(self):
        raise NotImplementedError

    @property
    def access_token(self):
        conn = get_redis_connection()

        expire_time = 10 * 60
        timestamp = int(time.time())

        raw_key = "{agent_id}:{corp_id}:{app_key}:{app_secret}:{using}".format(using=self.using, **self.conf)
        redis_key = AESCipher.crypt_md5(raw_key)

        while int(time.time()) - timestamp < expire_time:
            cache_token = conn.hgetall(redis_key) or {}
            access_token = cache_token.get("access_token")

            if access_token is not None:
                self.logger.info("[%s] => From redis token: %s" % (self.__class__.__name__, cache_token))
                return access_token

            # redis.set is atomic, but not blocking, so use `while`, then must sleep
            lock_key = "AccessTokenLock_%s" % redis_key
            if conn.set(lock_key, 1, ex=expire_time, nx=True):
                token = self.get_access_token()
                self.logger.info("[%s] => From api token: %s" % (self.__class__.__name__, token))

                conn.hmset(redis_key, token)
                conn.expire(redis_key, self.TOKEN_EXPIRE_TIME - 10 * 60)
                conn.expire(lock_key, 0)  # Delete distributed lock
                return token["access_token"]

            time.sleep(.01)

    @property
    def conf(self):
        return dict(
            backend=config[self.using]["BACKEND"],
            corp_id=config[self.using]["CORP_ID"],
            agent_id=config[self.using]["AGENT_ID"],
            app_key=config[self.using]["APP_KEY"],
            app_secret=config[self.using]["APP_SECRET"],
        )

    @property
    def msgtype(self):
        return self._msg_type

    @property
    def client_name(self):
        return self.CLIENT_NAME


