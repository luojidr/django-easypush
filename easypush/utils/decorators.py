import sys
import functools
import traceback


def std_response(fun):
    @functools.wraps(fun)
    def wrap(*args, **kwargs):
        code, msg, result = 200, "ok", None
        self = args[0] if args else None
        logger = getattr(self, "logger", None)

        try:
            data = fun(*args, **kwargs)

            if "data" in data:
                result = data["data"]
            else:
                result = data
        except Exception as e:
            code, msg = 5000, str(msg)
            format_exc = traceback.format_exc()
            log_msg = "Client[%s] invoke func[%s] err: %s" % (self.__class__.__name__, fun.__name__, e)

            if logger:
                logger.error(log_msg)
                logger.error(format_exc)
            else:
                sys.stdout.write(log_msg)
                sys.stdout.write(format_exc)

        return dict(code=code, msg=msg, data=result)

    return wrap
