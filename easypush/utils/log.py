import os.path

try:
    # https://github.com/Delgan/loguru
    import loguru   # v0.6.0
    import loguru._defaults as defaults
except ImportError:
    loguru = None
    defaults = None


class Logger:
    def __init__(
            self,
            filename,
            encoding="utf-8",
            rotation="200MB",
            retention="15 days",
            level=defaults.LOGURU_LEVEL,
            format=defaults.LOGURU_FORMAT,
            filter=defaults.LOGURU_FILTER,
            colorize=defaults.LOGURU_COLORIZE,
            serialize=defaults.LOGURU_SERIALIZE,
            backtrace=defaults.LOGURU_BACKTRACE,
            diagnose=defaults.LOGURU_DIAGNOSE,
            enqueue=defaults.LOGURU_ENQUEUE,
            catch=defaults.LOGURU_CATCH,
            **kwargs
    ):
        self._logger = loguru.logger
        log_path = os.path.dirname(filename)

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        self._logger.add(
            filename,
            encoding=encoding, rotation=rotation, retention=retention,
            level=level, format=format, filter=filter, colorize=colorize,
            serialize=serialize, backtrace=backtrace, diagnose=diagnose,
            enqueue=enqueue, catch=catch, **kwargs
        )

    @property
    def logger(self):
        return self._logger

    @property
    def traceback(self):
        return self._logger.catch

    def __getattr__(self, name):
        return getattr(self._logger, name)
