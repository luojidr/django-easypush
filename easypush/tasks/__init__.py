from django.conf import settings
from celery import current_app, current_task

from easypush.utils.exceptions import CeleryAppNotFoundError

_celery_app = None


def get_celery_app():
    global _celery_app

    if _celery_app is not None:
        return _celery_app

    try:
        _app = settings.EASYPUSH_CELERY_APP
    except AttributeError:
        _app = current_app

    if _app is None:
        errmsg = "Parameter `celery_app` not allowed empty, you could app.set_current() after instantiating"
        raise CeleryAppNotFoundError(errmsg)

    _celery_app = _app
    return _app


celery_app = get_celery_app()

