import re
import time
import logging
import inspect
import numbers
import importlib
from collections.abc import Mapping
from datetime import timedelta, datetime

from django.conf import settings

from celery import Celery
from celery import current_app, current_task
from celery.app import backends
from celery.app.task import Task
from celery.app.amqp import AMQP, task_message
from celery.states import SUCCESS
from celery.utils.nodenames import anon_nodename
from celery.utils.saferepr import saferepr
from celery.utils.time import maybe_make_aware
from celery.exceptions import BackendError, CeleryError


__all__ = ["ContextTask", "Amqp", "get_celery_app"]

# Equivalent to `from fosun_circle.libs.log import task_logger`
task_logger = logging.getLogger("celery.task")
worker_logger = logging.getLogger("celery.worker")

DEFAULT_COUNTDOWN = 0.1
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_KEY = "MAX_RETRY_CNT"
celery_app = None
empty = object()


def get_celery_app():
    global celery_app

    if celery_app is not None:
        return celery_app

    try:
        app_path = settings.EASYPUSH_CELERY_APP
        pkg_name, app_name = app_path.split(":", 1)

        module = importlib.import_module(pkg_name)
        celery_app = getattr(module, app_name, current_app)
    except (AttributeError, ValueError):
        celery_app = current_app

    if celery_app.conf.broker_url is None:
        raise CeleryError("Celery instance is empty, recommended set `EASYPUSH_CELERY_APP`")

    return celery_app


class Amqp(AMQP):
    """ celery version: 5.1.2 """

    def as_task_v2(self, task_id, name, args=None, kwargs=None,
                   countdown=None, eta=None, group_id=None, group_index=None,
                   expires=None, retries=0, chord=None,
                   callbacks=None, errbacks=None, reply_to=None,
                   time_limit=None, soft_time_limit=None,
                   create_sent_event=False, root_id=None, parent_id=None,
                   shadow=None, chain=None, now=None, timezone=None,
                   origin=None, ignore_result=False, argsrepr=None, kwargsrepr=None
                   ):
        args = args or ()
        kwargs = kwargs or {}

        if not isinstance(args, (list, tuple)):
            raise TypeError('task args must be a list or tuple')
        if not isinstance(kwargs, Mapping):
            raise TypeError('task keyword arguments must be a mapping')

        if countdown:  # convert countdown to ETA
            self._verify_seconds(countdown, 'countdown')
            now = now or self.app.now()
            timezone = timezone or self.app.timezone
            eta = maybe_make_aware(now + timedelta(seconds=countdown), tz=timezone)

        if isinstance(expires, numbers.Real):
            self._verify_seconds(expires, 'expires')
            now = now or self.app.now()
            timezone = timezone or self.app.timezone
            expires = maybe_make_aware(now + timedelta(seconds=expires), tz=timezone,)

        if not isinstance(eta, str):
            eta = eta and eta.isoformat()

        # If we retry a task `expires` will already be ISO8601-formatted.
        if not isinstance(expires, str):
            expires = expires and expires.isoformat()

        if argsrepr is None:
            argsrepr = saferepr(args, self.argsrepr_maxsize)
        if kwargsrepr is None:
            kwargsrepr = saferepr(kwargs, self.kwargsrepr_maxsize)

        if not root_id:  # empty root_id defaults to task_id
            root_id = task_id

        headers = dict(
            lang="py", task=name, id=task_id, shadow=shadow, eta=eta,
            expires=expires, group=group_id, group_index=group_index, retries=retries,
            timelimit=[time_limit, soft_time_limit], root_id=root_id, parent_id=parent_id,
            argsrepr=argsrepr, kwargsrepr=kwargsrepr, origin=origin or anon_nodename()
        )
        properties = dict(correlation_id=task_id, reply_to=reply_to or "")
        sent_event = dict(
            uuid=task_id, root_id=root_id, parent_id=parent_id, name=name,
            args=argsrepr, kwargs=kwargsrepr, retries=retries, eta=eta, expires=expires
        ) if create_sent_event else None

        # celery规范：(args, kwargs, {}); 如果适应其他开发语言(eg:java), 改造后celery发送消息 OK, 但不能消费
        payload = (args, kwargs, {})

        return task_message(headers=headers, properties=properties, body=payload, sent_event=sent_event)


class ContextBaseTask(Task):
    @property
    def backend(self):
        """ Default backend: self.app.backend (celery.app.base:Celery.backend)

        根据 task 指定的存储方式将结果存储到不同的物理介质:
            celery.app.backends:BACKEND_ALIASES OR django-db
        """
        task_run = self.run
        backend_aliases = backends.BACKEND_ALIASES

        sig = inspect.signature(task_run)
        parameters = sig.parameters
        task_to_backend = parameters.get(self.app.conf.CELERY_TASK_TO_BACKEND)
        to_backend = task_to_backend.default if task_to_backend else None
        to_backend = None if to_backend == "default" else to_backend

        if to_backend:
            # 任务结果存储到不同介质
            result_backend = getattr(self.app.conf, "CELERY_RESULT_BACKEND_" + to_backend.upper(), None)

            if to_backend not in backend_aliases:
                raise BackendError("Celery result backend is unknown!")

            if result_backend is None:
                raise BackendError("Celery configuration don't `%s`" % result_backend)

            var_backend_name = "_%s_result_backend" % to_backend
            _backend = getattr(self, var_backend_name, None)

            if _backend:
                return _backend

            new_backend, url = backends.by_url(result_backend, self.app.loader)
            _backend = new_backend(app=self.app, url=url)
            setattr(self, var_backend_name, _backend)

            return _backend

        else:
            # 与 celery 原生一样, 取决于 CELERY_RESULT_BACKEND
            backend = self._backend
            if backend is None:
                return self.app.backend

            return backend

    @backend.setter
    def backend(self, value):  # noqa
        self._backend = value
        worker_logger.info("ContextTask.backend -> Set value: %s", value)

    def log_info(self, log_kwargs, current_running_fun=None):
        if self is empty:
            worker_logger.info(">>>>>> ContextTask.log have't bond task instance !!!")

        log_kwargs.pop("self", None)
        log_kwargs["self_id"] = id(self)
        log_msg = log_kwargs.pop("log_msg", "")
        task_cls_name = self.app.task_cls.__name__

        log_msg = "{task_cls_name}.{current_running_fun} {log_msg} -> {running_fun_kwargs}".format(
            task_cls_name=task_cls_name, log_msg=log_msg,
            current_running_fun=current_running_fun, running_fun_kwargs=log_kwargs
        )
        worker_logger.info(log_msg)

    @classmethod
    def on_bound(cls, app):
        worker_logger.info("ContextTask.on_bound -> app: %s, type(app): %s", app, type(app))

    def on_success(self, retval, task_id, args, kwargs):
        log_kwargs = dict(locals(), requestId=self.request.id, delivery_info=self.request.delivery_info)
        self.log_info(current_running_fun=inspect.stack()[0][3], log_kwargs=log_kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        self.log_info(current_running_fun=inspect.stack()[0][3], log_kwargs=dict(locals()))

        # super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.log_info(current_running_fun=inspect.stack()[0][3], log_kwargs=dict(locals()))

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        log_kwargs = dict(locals(), requestId=self.request.id)
        current_running_fun = inspect.stack()[0][3]
        self.log_info(current_running_fun=current_running_fun, log_kwargs=log_kwargs)

        # 任意多的消息绑定的任务(self)有且仅有一个实例, self.request 也如此
        # 消息消费失败，将重新推回rabbitmq队列
        # ??? 最好的方法是消息重试结束后不能ack，让消息继续在mq中
        if status != SUCCESS:
            retry_log_kwargs = dict(Retry=True, args=args, kwargs=kwargs, task_id=task_id)
            self.log_info(current_running_fun=current_running_fun, log_kwargs=retry_log_kwargs)

            # 默认最大尝试3次
            # 方法一: 使用 apply_async 将消息再次推入到 RabbitMQ 中, 时间消耗在于将消息再次推入MQ
            #        需要每个task参数中必须带有关键字参数kwargs, 若task_id相同，任务结果入库只有一条记录，相反会有3条.
            #        注意: 每次 self.request 实例可能相同
            #
            # 方法二: 在每个具体的 task 里，使用self.retry(....)
            #        消息仍在 RabbitMQ 中， 因为没有 ACK, 性能比[方法一]好点, 但是会与[方法一]冲突
            #        注意: 每次 self.request 实例也可能相同
            if not self._check_task_retry():
                has_keyword = self._has_keyword_params_from_task()

                if has_keyword:
                    default_max_retries = kwargs.get(DEFAULT_RETRY_KEY, DEFAULT_MAX_RETRIES)
                    current_retry_cnt = default_max_retries - 1
                else:
                    current_retry_cnt = getattr(self, DEFAULT_RETRY_KEY, 3) - 1

                worker_logger.info("after_return.task: %s, %s, current_retry_cnt:%s", self, id(self), current_retry_cnt)

                if current_retry_cnt > 0:
                    if has_keyword:
                        kwargs[DEFAULT_RETRY_KEY] = current_retry_cnt
                    else:
                        setattr(self, DEFAULT_RETRY_KEY, current_retry_cnt)

                    self.apply_async(args, kwargs, task_id=task_id, countdown=DEFAULT_COUNTDOWN)

    def run(self, *args, **kwargs):
        """The body of the task executed by workers."""
        self.log_info(current_running_fun=inspect.stack()[0][3], log_kwargs=dict(locals()))

        raise NotImplementedError('BaseJobTask must define the run method.')

    def __call__(self, *args, **kwargs):
        """ @核心: billiard.pool:Worker.workloop, 任务执行体: self.run 即@celery_app.task修饰的任务部分

        @任务执行: celery.app.trace:build_tracer 方法类的450行，然后跳转到本self.__call__
                  # 448   -*- TRACE -*-
                  # 449   try:
                  # 450       R = retval = fun(*args, **kwargs)
                  # 451       state = SUCCESS
                  # 452   except Reject as exc:

        @super().__call__: Task被修饰后的产物, celery.app.trace:_install_stack_protection, 733与734行, 即：
                           super().__call__ => __protected_call__

                  # def __protected_call__(self, *args, **kwargs):
                  #     stack = self.request_stack
                  #     req = stack.top
                  #     if req and not req._protected and \
                  #             len(stack) == 1 and not req.called_directly:
                  #         req._protected = 1
                  #         return self.run(*args, **kwargs)      # *** self.run 自定义真正的任务函数 ***
                  #     return orig(self, *args, **kwargs)
                  # BaseTask.__call__ = __protected_call__

        """
        start = time.time()     # 这种方式统计task耗时很不准确
        request_id = self.request.id
        log_kwargs = dict(request_id=request_id, self=self, log_msg='Start')
        self.log_info(current_running_fun=inspect.stack()[0][3], log_kwargs=dict(log_kwargs, args=args, kwargs=kwargs))

        result = super().__call__(*args, **kwargs)

        log_kwargs.update(log_msg="End", costTime=time.time() - start)
        self.log_info(current_running_fun=inspect.stack()[0][3], log_kwargs=log_kwargs)

        return result

    def _check_task_retry(self):
        """ 自定义方法：检查任务函数是否自带重试机制
        Example:
            @celery_app.task(bind=True)
            def test_retry_message(self, *args, **kwargs):
                try:
                    pass
                except Exception as e:
                    '''
                    retry的参数可以有：
                        exc：指定抛出的异常
                        throw：重试时是否通知worker是重试任务
                        eta：指定重试的时间／日期
                        countdown：在多久之后重试（每多少秒重试一次）
                        max_retries：最大重试次数
                    '''
                    raise self.retry(exc=e, countdown=10, max_retries=3)
        """
        task_retry_key = "_auto_task_retry"
        auto_task_retry = getattr(self, task_retry_key, None)

        if auto_task_retry:
            return auto_task_retry

        run = self.run
        source_code = inspect.getsource(run)

        retry_pattern = r"^\s+?raise\s+%s\.retry\(.*?\)"
        deco_regex = re.compile(r"@.*?\.task\(bind=True\)", re.S | re.M)
        fun_declaration_regex = re.compile(r"def\s.*?\((.*?),.*?\)", re.S | re.M)

        deco_m = deco_regex.search(source_code)
        fun_declaration_m = fun_declaration_regex.search(source_code)

        if deco_m and fun_declaration_m and fun_declaration_m.group(1):
            instance_var = fun_declaration_m.group(1)
            retry_regex = re.compile(retry_pattern % instance_var, re.S | re.M)
            retry_m = retry_regex.search(source_code)

            if retry_m:
                setattr(self, task_retry_key, True)
                return True

        setattr(self, task_retry_key, False)
        return False

    def _has_keyword_params_from_task(self):
        """ 判断任务函数的参数签名 """
        wrapped_func = self.__wrapped__
        params = inspect.signature(wrapped_func).parameters

        worker_logger.info("_has_keyword_params_from_task.task_name: %s, wrapped_func:%s", self.name, wrapped_func)

        for name, param in params.items():
            if name == DEFAULT_RETRY_KEY:
                return True

            kind = param.kind
            if kind == inspect._ParameterKind.VAR_KEYWORD:
                return True

        return False


class ContextTask(ContextBaseTask):
    """ celery version: 5.1.2
    Default config: celery.app.defaults
    """

    def _get_raw_app(self):
        cls = self.__class__
        _app_name = "RAW_CELERY_APP"
        raw_app = getattr(cls, _app_name, None)

        if raw_app:
            return raw_app

        raw_app = Celery(main="raw_msg_app", amqp="property.core.mq.context:Amqp", task_cls=cls)
        raw_app.config_from_object(obj=self.app.conf)

        setattr(cls, _app_name, raw_app)
        return raw_app

    def apply_async_raw(self, args=None, kwargs=None, task_id=None, producer=None,
                        link=None, link_error=None, shadow=None, **options):
        """ Send raw message
        task_always_eager:
            默认值：禁用, 本方法丢弃同步发送消息
            如果设置成 True，所有的任务都将在本地执行知道任务返回。apply_async() 以及Task.delay()将返回一个
            EagerResult 实例，模拟AsyncResult实例的API和行为，除了这个结果是已经计算过的之外。
        """
        if self.typing:
            try:
                check_arguments = self.__header__
            except AttributeError:  # pragma: no cover
                pass
            else:
                check_arguments(*(args or ()), **(kwargs or {}))

        if self.__v2_compat__:
            shadow = shadow or self.shadow_name(self(), args, kwargs, options)
        else:
            shadow = shadow or self.shadow_name(args, kwargs, options)

        preopts = self._get_exec_options()
        options = dict(preopts, **options) if options else preopts

        options.setdefault('ignore_result', self.ignore_result)
        if self.priority:
            options.setdefault('priority', self.priority)

        app = self._get_raw_app()

        # 异步发送消息
        return app.send_task(
            self.name, args, kwargs, task_id=task_id, producer=producer,
            link=link, link_error=link_error, result_cls=self.AsyncResult,
            shadow=shadow, task_type=self, **options
        )

    def delay(self, *args, **kwargs):
        """ 追踪 task 日志 """
        task_logger.info("ContextTask.delay <%s> send message ==>>> args:%s, kwargs: %s", self.name, args, kwargs)

        return self.apply_async(args, kwargs)

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):
        """ 追踪 task 日志 """
        task_logger.info("ContextTask.apply_async <%s> send message ==>>> args:%s, kwargs: %s", self.name, args, kwargs)

        return super().apply_async(
            args=args, kwargs=kwargs, task_id=task_id,
            producer=producer, link=link, link_error=link_error, shadow=shadow,
            **options
        )
