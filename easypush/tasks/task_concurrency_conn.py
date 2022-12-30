import logging
import random
import string

from datetime import datetime
from faker import Faker

from easypush.core.mq.context import get_celery_app
from easypush.utils.constants import QyWXMessageTypeEnum
from easypush.models import AppMsgPushRecordModel, AppMessageModel

celery_app = get_celery_app()
logger = logging.getLogger("django")


@celery_app.task
def concurrency_orm_conn(msg_uid, **kwargs):
    """ database-conn-poll concurrency test """
    f = Faker(locale="zh_CN")  # f._factories[0].__dict__
    # app_msg_queryset = AppMessageModel.objects.filter(is_del=False).values_list("id", flat=True)
    app_msg_queryset = list(range(1, 132))
    msg_type_list = [_enum.type for _enum in QyWXMessageTypeEnum.iterator()]

    push_log = AppMsgPushRecordModel.objects.filter(msg_uid=msg_uid).first()

    if push_log:
        push_log.traceback = "x_upt"
    else:
        push_log = AppMsgPushRecordModel(
            creator='sys', modifier='sys', app_msg_id=random.choice(app_msg_queryset),
            sender='sys', send_time=datetime.now(), receiver_mobile=f.phone_number(),
            receiver_userid=f.credit_card_number(), msg_uid=msg_uid,
            task_id="".join([random.choice(string.ascii_letters + string.digits) for _ in range(30)]),
            msg_type=random.choice(msg_type_list), platform_type='qy_weixin',
        )

    push_log.save()
    return dict(id=push_log.id, task_id=push_log.task_id)
