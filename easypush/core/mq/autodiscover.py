import os
import pathlib
import logging
import pkgutil
import importlib

from django.conf import settings


def autodiscover_tasks(packages=None, related_name='tasks', task_prefix='task_'):
    """
    :param packages: list of string, eg ['config.tasks', 'config.auto_tasks']
    :param related_name: find directory or package of task
    :param task_prefix, find detail task module

    Automatically discover django app tasks, compatible with the application directory task, as follows:
    Rules:
        (1): Load the directory of `tasks` name first
            tasks/
                task_aaa.py
                task_bbb.py
        (2): application the tasks.py file in the directory
        (3): tasks for the other packages specified
    """
    all_task_list = []
    project_name = settings.APP_NAME

    if not os.getenv("DJANGO_SETTINGS_MODULE"):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', Config.DJANGO_SETTINGS_MODULE)
        logging.warning("autodiscover_dj_tasks --->>> config: [%s]", Config.DJANGO_SETTINGS_MODULE)

    packages = packages() if callable(packages) else packages or ()
    packages_or_apps = list(packages) + settings.INSTALLED_APPS

    for name in packages_or_apps:
        is_app = name in settings.INSTALLED_APPS
        package = importlib.import_module(name)

        file_path = os.path.dirname(os.path.abspath(package.__file__))
        package_name = package.__package__

        for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            mod_name = module_info.name

            if mod_name == package_name + "." + related_name:
                path = pathlib.Path(file_path)
                parent_parts_list = path.parent.parts
                app_path_list = list(parent_parts_list[parent_parts_list.index(project_name) + 1:])

                if not module_info.ispkg:
                    app_task_path = ".".join(app_path_list + [mod_name])
                    all_task_list.append(app_task_path)

                    logging.warning("autodiscover_dj_tasks --->>> task path: %s", app_task_path)
                else:
                    task_path = path / related_name
                    sub_mod_info_list = list(pkgutil.iter_modules([str(task_path)]))

                    for sub_mod_info in sub_mod_info_list:
                        if not sub_mod_info.name.startswith(task_prefix):
                            continue

                        app_task_path = ".".join(app_path_list + [mod_name, sub_mod_info.name])
                        all_task_list.append(app_task_path)
                        logging.warning("autodiscover_dj_tasks --->>> task path: %s", app_task_path)

    logging.warning("===>>> Easypush autodiscover tasks are as below\n")
    return all_task_list
