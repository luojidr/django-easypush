from copy import copy
from django.conf import settings

DEFAULTS = {
    "log_path": "",

    "default": {
        "BACKEND": "easypush.backends.ding_talk.DingTalkClient",
        # dingtalk
        "CORP_ID": None,
        "AGENT_ID": None,
        "APP_KEY": None,
        "APP_SECRET": None,
    },
}

DEFAULT_EASYPUSH_ALIAS = 'default'


class Singleton(type, metaclass=object):
    def __init__(cls, name, bases, d):
        super(Singleton, cls).__init__(name, bases, d)
        cls.instance = None

    def __call__(cls, *args):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args)
        return cls.instance


class EasyPushConfig(metaclass=Singleton):
    def _setup(self):
        options = {option: value for option, value in settings.EASYPUSH.items()}

        self.attrs = copy(DEFAULTS)
        self.attrs.update(options)

    def __init__(self):
        super(EasyPushConfig, self).__init__()
        self._setup()

    def __getattr__(self, attr):
        if attr not in self.attrs:
            raise ValueError("EASYPUSH config not include `%s`." % attr)

        return self.attrs[attr]

    def __getitem__(self, name):
        if name not in self.attrs:
            raise ValueError("EASYPUSH config not include `%s`." % name)

        return self.attrs[name]


config = EasyPushConfig()
