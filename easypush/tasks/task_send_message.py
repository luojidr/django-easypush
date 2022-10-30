"""
Example::
    >>> from django.conf import settings
    >>> from celery import Celery
    >>> from easypush.core.mq.context import ContextTask
    >>> app = Celery(settings.APP_NAME + '_celery', task_cls=ContextTask)
    >>> app.set_current()
    >>> platforms.C_FORCE_ROOT = True       # celery不能用root用户启动问题

    >>> from easypush.tasks.task_send_message import send_message_by_mq
    >>> task = send_message_by_mq
    >>> task.delay(...) | task.apply_async(...) | task.apply_async_raw(...)  # send message
"""
from __future__ import absolute_import
import traceback
from datetime import datetime
from operator import itemgetter
from itertools import groupby

from . import get_celery_app
from easypush import easypush
from easypush.models import (
    AppMessageModel,
    AppMsgPushRecordModel as LogModel
)

celery_app = get_celery_app()


@celery_app.task(ignore_result=True)
def send_message_by_mq(message_body_list=None, force_db=True, **kwargs):
    """ 消息统一发送任务
    eg: message_body_list = [
        {
            "msg_type": "oa",
            "msg_uid": "2702976118339",
            "body_kwargs": {....}       # 具体参考消息API
            "userid_list": [],
            "dept_id_list": []
        }
    ]
    """
    if message_body_list is None:
        return "message_body_list is empty"

    for message_body in message_body_list:
        # Parameter msg_uid is unique
        msg_uid = message_body.get("msg_uid")
        msg_type = message_body.get("msg_type")
        body_kwargs = message_body.get("body_kwargs")
        userid_list = message_body.get("userid_list")

        if force_db:
            if msg_uid is None:
                raise ValueError("Parameter `msg_uid` not allowed empty.")

            log_queryset_cnt = LogModel.objects.filter(msg_uid=msg_uid, is_del=False).count()
            if log_queryset_cnt == 0:
                raise ValueError("Parameter `msg_uid` is invalid.")
            elif log_queryset_cnt > 1:
                raise ValueError("Parameter `msg_uid` must unique.")

        # Standard result: {errcode:0, errmsg: "ok", task_id:"123", request_id: "456", data:{}}
        ret = dict(errcode=500, errmsg="failed", task_id="", request_id="", data=None)

        try:
            result = easypush.async_send(msgtype=msg_type, body_kwargs=body_kwargs, userid_list=userid_list)
            task_id = result.pop("task_id", "")
            ret.update(task_id=str(task_id), **result)
        except Exception:
            exc_msg = traceback.format_exc()
            ret.update(errmsg=exc_msg[-1000:])
        finally:
            try:
                update_kwargs = dict(
                    is_success=ret["errcode"] == 0, task_id=ret["task_id"],
                    traceback=ret["errmsg"], request_id=ret["request_id"]
                )
                update_kwargs["is_success"] and update_kwargs.update(receive_time=datetime.now())

                if force_db:
                    LogModel.objects.filter(msg_uid=msg_uid).update(**update_kwargs)
            except Exception:
                exc_msg = traceback.format_exc()
                ret.update(errmsg=exc_msg[-1000:])

        return ret


