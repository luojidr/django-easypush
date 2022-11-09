import os, sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easypush_demo.settings")
django.setup()

from .celery import celery_app

# app.worker_main()
celery_app.start(argv=["-A", "config.celery", "worker", "-l", "info", "-c", "10"])
