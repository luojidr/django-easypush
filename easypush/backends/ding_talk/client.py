import uuid
import typing
import os.path
import traceback
import datetime

from dingtalk.model.message import BodyBase
from dingtalk.client.api.message import Message
from dingtalk import AppKeyClient, DingTalkException
from dingtalk.core.exceptions import DingTalkClientException

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from .parser import DingMessageBodyParser
from easypush.backends.base.base import ClientMixin
from easypush.utils.decorators import wrapper_response
from easypush.utils.constants import DingTalkMediaEnum


class DingBase(ClientMixin):
    CLIENT_NAME = "dingtalk"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._client = AppKeyClient(
            corp_id=self._corp_id,
            app_key=self._app_key,
            app_secret=self._app_secret
        )
        self._message = Message(client=self._client)

    @wrapper_response
    def get_access_token(self):
        """ 获取应用 access token """
        return self._client.get_access_token()


class DingTalkClient(DingBase, DingMessageBodyParser):
    def __init__(self, msg_type=None, **kwargs):
        super().__init__(**kwargs)
        self._msg_type = msg_type

    @wrapper_response
    def media_upload(self, media_type, filename=None, media_file=None):
        """ Upload Image, file, voice
        :param media_type: 媒体文件类型，分别有图片（image）、语音（voice）、普通文件(file)
        :param media_file: 要上传的文件，一个 File-object
        :param filename: 文件路径

        result: {
            'errcode': 0, 'errmsg': 'ok', 'media_id': '@lALPDeC2zDlm8IpiYg',
            'created_at': 1603962089663, 'type': 'image'
        }
        """
        assert media_type in DingTalkMediaEnum.media_list(), "媒体文件类型(仅限: image, voice, file)错误!"

        if not media_file and not filename:
            raise ValueError("未选择媒体文件!")

        if filename and not os.path.exists(filename):
            raise ValueError("媒体文件不存在")

        if isinstance(media_file, UploadedFile):
            _fn = str(uuid.uuid1()).replace("-", "") + os.path.splitext(media_file.name)[-1]
            filename = os.path.join(self.filepath, _fn)
            self.write_file(filename, file_obj=media_file)

        try:
            media_file = open(filename, "rb")
            result = self._message.media_upload(media_type, media_file=media_file)
        except DingTalkClientException:
            result = {}
            traceback.format_exc()
        finally:
            media_file.close()
            os.remove(filename)

        self.logger.info("<%s>.media_upload filename:%s, upload resp:%s", self.__class__.__name__, filename, result)

        if result.get("errcode") != 0:
            raise ValueError("上传上传失败: {}".format(result.get("errmsg")))

        return result

    @wrapper_response
    def async_send(self, msgtype, body_kwargs, userid_list=(), dept_id_list=(), to_all_user=False):
        """ 企业会话消息异步发送
        :param msgtype: 消息类型
        :param body_kwargs: dict, 不同消息体对应的参数
        :param userid_list: list|tuple, 接收者的用户userid列表
        :param dept_id_list: list|tuple, 接收者的部门id列表
        :param to_all_user: bool, 是否发送给企业全部用户
        """
        if not isinstance(userid_list, (typing.Tuple, typing.List)):
            raise ValueError("parameter `user_id_list` must is list|tuple")

        self._msg_type = msgtype
        message_body = self.get_message_body(**body_kwargs)
        assert isinstance(message_body, BodyBase), "Parameter `msg_body` must is a instance of BodyBase"

        return self._message.asyncsend_v2(
            message_body,
            agent_id=self._agent_id, userid_list=userid_list,
            dept_id_list=dept_id_list, to_all_user=to_all_user
        )

    @wrapper_response
    def recall(self, task_id):
        """ 撤回工作通知消息
        :param task_id: 发送工作通知返回的 taskId
        """
        return self._message.recall(agent_id=self._agent_id, msg_task_id=task_id)





