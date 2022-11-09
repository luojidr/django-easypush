import importlib

from django.conf import settings
from celery import current_app, current_task

from easypush.utils.exceptions import CeleryAppNotFoundError

celery_app = None


def get_celery_app():
    global celery_app

    if celery_app is not None:
        return celery_app

    try:
        app_path = settings.EASYPUSH_CELERY_APP
        pkg_name, app_name = app_path.split(":", 1)

        module = importlib.import_module(pkg_name)
        celery_app = getattr(module, app_name, current_app)
    except (AttributeError, ValueError):
        celery_app = current_app

    if celery_app.conf.broker_url is None:
        errmsg = "Celery instance is empty, recommended set `EASYPUSH_CELERY_APP`"
        raise CeleryAppNotFoundError(errmsg)

    return celery_app


