from importlib import import_module

from easypush.utils.exceptions import BackendModuleError


def import_string(module_path):
    """ like "easypush.backends.ding_talk.DingTalkBackend" string

    Import a module path and return the class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = module_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % module_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (
            module_path, class_name)
        ) from err


class BackendLoader:
    def __init__(self, push_backend=None):
        self.backend_cls = None
        self._push_backend = push_backend

    def load_backend_cls(self):
        if not self._push_backend:
            raise BackendModuleError("EasyPush `BACKEND` is allowed empty.")

        if self.backend_cls is None:
            self.backend_cls = import_string(module_path=self._push_backend)

        return self.backend_cls
