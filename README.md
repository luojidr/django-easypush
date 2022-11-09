Push messages with different backends for the Django framework.
===============================================================

[![MIT License](https://img.shields.io/pypi/l/django-easypush.svg)](https://opensource.org/licenses/MIT)
[![django-easypush can be installed via wheel](https://img.shields.io/pypi/wheel/django-easypush.svg)](http://pypi.python.org/pypi/django-easypush/)
[![Supported Python versions.](https://img.shields.io/pypi/pyversions/django-easypush.svg)](http://pypi.python.org/pypi/django-easypush/)

|          |               |   
| ---------|:--------------| 
| Version  |1.1.1           | 
| Web      |               |  
| Download |<http://pypi.python.org/pypi/django-easypush>  |  
| Source   |<https://github.com/luojidr/django-easypush>   | 
| Keywords |django, push message, ding_talk, qy_weixin     | 


About
-----

The purpose of developing this package is to simplify the push of
Dingding, enterprise wechat messages

Installation
------------

You can install django-easypush either via the Python Package Index
(PyPI) or from source.

To install using **pip**:

``` {.sh}
$ pip install -U django-easypush
```

and then add it to your installed apps:

``` {.python}
INSTALLED_APPS = [
    ...,
    'easypush',
    ...,
]

EASYPUSH = {
    "default": {
        "BACKEND": 'easypush.backends.ding_talk.DingTalkClient',
        "CORP_ID": 'dingfdjrriexckcuirjskd',
        "AGENT_ID": 100002834,
        "APP_KEY": 'dgfrhfyewuiry347jdshckjdsh',
        "APP_SECRET": 'd8QkPEi9YqQl8W9cv_se_Cre417ZwHEXehdteifncyyw5hdJdMRUkzZQ96D4Yvycv3'),
    },
    ...,
}
EASYPUSH_CELERY_APP = "easypush_demo.celery_app:celery_app"  # auto to send message by async
```

### Downloading and installing from source

Download the latest version of django-easypush from
<http://pypi.python.org/pypi/django-easypush>

You can install it by doing the following,:

    $ tar xvfz django-easypush-0.0.0.tar.gz
    $ cd django-easypush-0.0.0
    $ python setup.py build
    # python setup.py install

The last command must be executed as a privileged user if you are not
currently using a virtualenv.
