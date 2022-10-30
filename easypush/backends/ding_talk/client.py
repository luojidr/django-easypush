import uuid
import typing
import os.path
import traceback
from optionaldict import optionaldict

from dingtalk.model.message import BodyBase
from dingtalk.client.api.message import Message
from dingtalk import AppKeyClient
from dingtalk.core.exceptions import DingTalkClientException

from django.core.files.base import File

from .parser import DingMessageBodyParser
from easypush.backends.base.base import ClientMixin
from easypush.utils.constants import DingTalkMediaEnum
from easypush.utils.util import to_text


class DingBase(ClientMixin):
    CLIENT_NAME = "ding_talk"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._client = AppKeyClient(
            corp_id=self._corp_id,
            app_key=self._app_key,
            app_secret=self._app_secret
        )
        self._message = Message(client=self._client)

    def get_access_token(self):
        """ 获取应用 access token """
        return self._client.get_access_token()


class DingTalkClient(DingBase, DingMessageBodyParser):
    def __init__(self, msg_type=None, **kwargs):
        super().__init__(**kwargs)
        self._msg_type = msg_type

    def upload_media(self, media_type, filename=None, media_file=None):
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
        self._check_media_exist(filename, media_file)

        if isinstance(media_file, File):
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

    def async_send(self, msgtype, body_kwargs, userid_list=(),
                   dept_id_list=(), to_all_user=False, result_processor=None):
        """ 企业会话消息异步发送
        :param msgtype: 消息类型
        :param body_kwargs: dict, 不同消息体对应的参数
        :param userid_list: list|tuple, 接收者的用户userid列表
        :param dept_id_list: list|tuple, 接收者的部门id列表
        :param to_all_user: bool, 是否发送给企业全部用户
        :param result_processor, callable, 结果处理器
        """
        if not isinstance(userid_list, (typing.Tuple, typing.List)):
            raise ValueError("parameter `user_id_list` must is list|tuple")

        if not isinstance(dept_id_list, (typing.Tuple, typing.List)):
            raise ValueError("parameter `dept_id_list` must is list|tuple")

        self._msg_type = msgtype
        message_body = self.get_message_body(**body_kwargs)

        assert isinstance(message_body, BodyBase), "Parameter `msg_body` must is a instance of BodyBase"
        assert result_processor is None or callable(result_processor), "result_processor must be callable or None"

        userid_list = ",".join(map(to_text, userid_list))
        dept_id_list = ",".join(map(to_text, dept_id_list))

        params = optionaldict(dict(
            msg=message_body.get_dict(), agent_id=self._agent_id,
            userid_list=userid_list or None, dept_id_list=dept_id_list or None,
            to_all_user='true' if to_all_user else 'false'
        ))

        # Set result_processor
        method = 'dingtalk.oapi.message.corpconversation.asyncsend_v2'
        result = self._message._top_request(method, params=params, result_processor=result_processor)

        response_key = method.replace('.', '_') + "_response"
        return result.get(response_key, result)

    def recall(self, task_id):
        """ 撤回工作通知消息
        :param task_id: 发送工作通知返回的 taskId
        """
        return self._message.recall(agent_id=self._agent_id, msg_task_id=task_id)





