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

import time
import json
import logging
import traceback
from datetime import datetime
from operator import itemgetter
from itertools import groupby

from . import get_celery_app
from easypush import easypush
from easypush.models import (
    AppMessageModel as MsgModel,
    AppMsgPushRecordModel as LogModel
)

celery_app = get_celery_app()
logger = logging.getLogger("django")


@celery_app.task(ignore_result=True)
def send_message_by_mq(msg_uid_list=None, force_db=True, **kwargs):
    """ 消息统一发送任务
        eg: msg_uid_list = ["2702976118339", "2702976118349"]
    """
    start_time = time.time()
    msg_uid_list = msg_uid_list or []

    if not msg_uid_list:
        return

    log_query = dict(msg_uid__in=msg_uid_list)
    log_fields = ["msg_uid", "receiver_userid", "app_msg_id"]
    log_queryset = LogModel.objects.filter(**log_query).values(*log_fields)
    logger.info("send_message_by_mq => log_queryset: %s, msg_uid_list:%s", len(log_queryset), msg_uid_list)

    # Application of platform
    app_msg_ids = list({item["app_msg_id"] for item in log_queryset})
    msg_queryset = MsgModel.objects.filter(id__in=app_msg_ids, is_del=False)
    msg_mapping_dict = {msg_obj.id: msg_obj for msg_obj in msg_queryset}

    # Send message group by application
    for app_msg_id, iterator in groupby(log_queryset, key=itemgetter("app_msg_id")):
        log_list = list(iterator)
        app_msg = msg_mapping_dict.get(app_msg_id)

        start_time2 = time.time()
        _log_args = (app_msg_id, app_msg, len(log_list))
        logger.info("send_message_by_mq => app_msg_id: %s, app_msg: %s, push_count: %s", *_log_args)

        if not app_msg:
            continue

        body_kwargs = json.loads(app_msg.msg_extra_json)
        group_msg_uid_list = [log_item["msg_uid"] for log_item in log_list]
        userid_list = [item["receiver_userid"] for item in log_list if item["receiver_userid"]]

        # Standard result: {errcode:0, errmsg: "ok", task_id:"123", request_id: "456", data:{}}
        ret = dict(errcode=500, errmsg="failed", task_id="", request_id="", data=None)

        try:
            result = easypush.async_send(
                msgtype=app_msg.msg_type, body_kwargs=body_kwargs, userid_list=userid_list
            )
            task_id = result.pop("task_id", "")
            ret.update(task_id=str(task_id), **result)
        except Exception:
            exc_msg = traceback.format_exc()
            ret.update(errmsg=exc_msg[-1000:])
        finally:
            cost_time3 = time.time() - start_time2
            logger.info("send_message_by_mq => Api Cost time:%s", cost_time3)

            try:
                update_kwargs = dict(
                    is_success=ret["errcode"] == 0, task_id=ret["task_id"],
                    traceback=ret["errmsg"], request_id=ret["request_id"]
                )
                update_kwargs["is_success"] and update_kwargs.update(receive_time=datetime.now())

                if force_db:
                    LogModel.objects.filter(msg_uid__in=group_msg_uid_list).update(**update_kwargs)
            except Exception:
                traceback.format_exc()

            log_msg = "msg_uid cnt:%s, userid_list cnt:%s, app_msg:%s, Ret: %s, Cost time:%s"
            log_args = (len(group_msg_uid_list), len(userid_list), app_msg, ret, time.time() - start_time)
            logger.info("send_message_by_mq => " + log_msg, *log_args)


