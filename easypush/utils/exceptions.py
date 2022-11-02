class EasyPushError(Exception):
    """Base class for all easypush errors."""


class FuncInvokeError(EasyPushError):
    pass


class InvalidTokenError(EasyPushError):
    pass


class BackendError(EasyPushError):
    pass


class BackendModuleError(BackendError):
    """ backend module is empty. """


class InvalidBackendConfigError(BackendError):
    pass


class MessageTypeError(EasyPushError):
    pass


class MessagePlatformError(EasyPushError):
    pass


class MessageBodyFieldError(EasyPushError):
    pass


class NotExistMessageBodyMethod(EasyPushError):
    pass


class ExceedContentMaxSizeError(EasyPushError):
    pass


class CeleryAppNotFoundError(EasyPushError):
    pass
