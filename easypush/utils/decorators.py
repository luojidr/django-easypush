from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


def exempt_view_csrf(view_cls):
    def deco(*args, **kwargs):
        return method_decorator(csrf_exempt, name="dispatch")(view_cls)

    return deco()

