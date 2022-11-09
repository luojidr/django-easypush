import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easypush_demo.settings")
django.setup()

from easypush_demo.celery_app import celery_app


if __name__ == "__main__":
    # app.worker_main()
    celery_app.start(argv=["-A", "easypush_demo.celery_app", "worker", "-l", "info", "-c", "10"])

