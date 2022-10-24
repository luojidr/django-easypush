class EasyPushError(Exception):
    """Base class for all easypush errors."""


class FuncInvokeError(EasyPushError):
    pass


class BackendModuleError(EasyPushError):
    """ backend module is empty. """


class InvalidBackendConfigError(EasyPushError):
    pass


class MessageTypeError(EasyPushError):
    pass


class MessageBodyFieldError(EasyPushError):
    pass


class NotExistMessageBodyMethod(EasyPushError):
    pass


class ExceedContentMaxSizeError(EasyPushError):
    pass
