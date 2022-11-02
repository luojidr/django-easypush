"""
企业内部推送消息推送平台，目前支持钉钉、企业微信、短信、邮箱，飞书
openapi.py 公共开放接口，继承上述所有平台开发
"""

from asgiref.local import Local

from django.conf import settings
from easypush.client import AppMessageHandler
from easypush.utils.settings import DEFAULT_EASYPUSH_ALIAS
from easypush.utils.exceptions import InvalidBackendConfigError


class EasyPushHandler:
    def __init__(self):
        self._pushes = Local()

    def __getitem__(self, alias):
        try:
            return self._pushes.caches[alias]
        except AttributeError:
            self._pushes.caches = {}
        except KeyError:
            pass

        if alias not in settings.EASYPUSH:
            raise InvalidBackendConfigError("Could not find config for '%s' in settings.EASYPUSH" % alias)

        push = AppMessageHandler(using=alias)
        self._pushes.caches[alias] = push
        return push

    def all(self):
        return getattr(self._pushes, 'caches', {}).values()


pushes = EasyPushHandler()


class DefaultEasyPushProxy:
    def __getattr__(self, name):
        return getattr(pushes[DEFAULT_EASYPUSH_ALIAS], name)

    def __setattr__(self, name, value):
        return setattr(pushes[DEFAULT_EASYPUSH_ALIAS], name, value)

    def __contains__(self, key):
        return key in pushes[DEFAULT_EASYPUSH_ALIAS]


easypush = DefaultEasyPushProxy()
