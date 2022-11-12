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

from easypush.core.mq.context import get_celery_app
from easypush.client.utils import get_push_backend
from easypush.models import AppMessageModel as MsgModel
from easypush.models import AppMsgPushRecordModel as LogModel

celery_app = get_celery_app()
logger = logging.getLogger("django")


@celery_app.task(ignore_result=True)
def send_message_by_mq(msg_uid_list=None, **kwargs):
    """ General task to send message by MQ
    :param msg_uid_list: list, eg: ["2702976118339", "2702976118349"]
    :return
    """
    start_time = time.time()
    msg_uid_list = msg_uid_list or []

    if not msg_uid_list:
        return

    log_query = dict(msg_uid__in=msg_uid_list)
    log_fields = ["msg_uid", "receiver_userid", "app_msg_id"]
    log_queryset = LogModel.objects.filter(**log_query).values(*log_fields)

    # Application of platform
    app_msg_ids = list({item["app_msg_id"] for item in log_queryset})
    msg_queryset = MsgModel.objects.filter(id__in=app_msg_ids, is_del=False).select_related("app")
    msg_mapping_dict = {msg_obj.id: msg_obj for msg_obj in msg_queryset}

    # Send message group by application
    for app_msg_id, iterator in groupby(log_queryset, key=itemgetter("app_msg_id")):
        log_list = list(iterator)
        app_msg_obj = msg_mapping_dict.get(app_msg_id)

        if not app_msg_obj:
            continue

        body_kwargs = json.loads(app_msg_obj.msg_body_json)
        group_msg_uid_list = [log_item["msg_uid"] for log_item in log_list]
        required_msg_uid_list = [item["msg_uid"] for item in log_list if item["msg_uid"]]
        userid_list = [item["receiver_userid"] for item in log_list if item["receiver_userid"]]

        api_start_time = time.time()
        # Standard result: {errcode:0, errmsg: "ok", task_id:"123", request_id: "456", data:{}}
        ret = dict(errcode=500, errmsg="failed", task_id="", request_id="", data=None)

        try:
            push = get_push_backend(instance=app_msg_obj.app)
            result = push.async_send(msgtype=app_msg_obj.msg_type, body_kwargs=body_kwargs, userid_list=userid_list)
            task_id = result.pop("task_id", "")
            ret.update(task_id=str(task_id), **result)
        except Exception:
            exc_msg = traceback.format_exc()
            ret.update(errmsg=exc_msg[-1000:])
        finally:
            _log_args = (app_msg_obj, len(log_list), time.time() - api_start_time)
            logger.info("send_message_by_mq => app_msg: %s, push_count: %s, Api Cost time:%.2fs", *_log_args)

            try:
                update_kwargs = dict(
                    is_success=ret["errcode"] == 0, task_id=ret["task_id"],
                    traceback=ret["errmsg"], request_id=ret["request_id"]
                )
                update_kwargs["is_success"] and update_kwargs.update(receive_time=datetime.now())
                LogModel.objects.filter(msg_uid__in=group_msg_uid_list).update(**update_kwargs)
            except Exception:
                traceback.format_exc()

            log_msg = "msg_uid Cnt:%s, userid_list Cnt:%s, app_msg:%s, Cost time:%.2fs\nRet: %s\nMsg uid:%s"
            log_args = (len(group_msg_uid_list), len(userid_list), app_msg_obj, time.time() - start_time, ret)
            logger.info("send_message_by_mq => " + log_msg, *log_args + (required_msg_uid_list, ))


