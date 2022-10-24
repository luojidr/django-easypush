import sys
from functools import partial

from werkzeug.local import LocalProxy
from werkzeug.local import LocalStack


def _lookup_local_object(name):
    top = _local_ctx_stack.top
    if top is None:
        raise RuntimeError("Working outside of request context.")
    return getattr(top, name)


def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError("Working outside of request context.")
    return getattr(top, name)


_local_ctx_stack = LocalStack()
_request_ctx_stack = LocalStack()

local_user = LocalProxy(partial(_lookup_local_object, "user"))
request = LocalProxy(partial(_lookup_req_object, "request"))
session = LocalProxy(partial(_lookup_req_object, "session"))


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


class LocalContext(object):
    """ Thread local """

    def __init__(self, user=None, request=None, session=None, ctx_label=None):
        self.user = user
        self.request = request
        self.session = session
        self._ctx_label = ctx_label

        # indicator if the context was preserved.  Next time another context
        # is pushed the preserved context is popped.
        self.preserved = False

        # remembers the exception for pop if there is one in case the context
        # preservation kicks in.
        self._preserved_exc = None

    @property
    def ctx(self):
        if self._ctx_label is None or self._ctx_label in ["user", "ctx"]:
            ctx = _local_ctx_stack
        elif self._ctx_label == "req":
            ctx = _request_ctx_stack
        else:
            raise ValueError("未发现上下文线程变量")

        return ctx

    def push(self):
        # If an exception occurs in debug mode or if context preservation is
        # activated under exception situations exactly one context stays
        # on the stack.  The rationale is that you want to access that
        # information under debug situations.  However if someone forgets to
        # pop that context again we want to make sure that on the next push
        # it's invalidated, otherwise we run at risk that something leaks
        # memory.  This is usually only a problem in test suite since this
        # functionality is not active in production environments.
        top = self.ctx.top
        if top is not None and top.preserved:
            top.pop(top._preserved_exc)

        if hasattr(sys, "exc_clear"):
            sys.exc_clear()

        self.ctx.push(self)

    def pop(self, exc=None):
        try:
            self.preserved = False
            self._preserved_exc = None
            if exc is None:
                exc = sys.exc_info()[1]

            # If this interpreter supports clearing the exception information
            # we do that now.  This will only go into effect on Python 2.x,
            # on 3.x it disappears automatically at the end of the exception
            # stack.
            if hasattr(sys, "exc_clear"):
                sys.exc_clear()
        finally:
            rv = self.ctx.pop()

            assert rv is self, "Popped wrong request context. (%r instead of %r)" % (rv, self)

    def auto_pop(self, exc):
        self.preserved = True
        self._preserved_exc = exc
        self.pop(exc)

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # do not pop the request stack if we are in debug mode and an
        # exception happened.  This will allow the debugger to still
        # access the request object in the interactive shell.  Furthermore
        # the context can be force kept alive for the test client.
        # See flask.testing for how this works.
        self.auto_pop(exc_value)

        if exc_type is not None:
            reraise(exc_type, exc_value, tb)

