from django.conf import settings
from celery import current_app, current_task

from easypush.utils.exceptions import CeleryAppNotFoundError


def get_celery_app():
    try:
        celery_app = settings.EASYPUSH_CELERY_APP
    except AttributeError:
        celery_app = current_app

    if celery_app is None:
        errmsg = "Parameter `celery_app` not allowed empty, you could app.set_current() after instantiating"
        raise CeleryAppNotFoundError(errmsg)

    return celery_app

