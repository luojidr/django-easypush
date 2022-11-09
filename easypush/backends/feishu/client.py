import typing
import os.path
from datetime import datetime

from .message import FeishuMessage
from .parser import FeishuMessageBodyParser

from .api.token import FeishuAccessToken as Token
from easypush.backends.base.base import ClientMixin
from easypush.backends.base.body import MsgBodyBase


class FeishuBase(ClientMixin):
    CLIENT_NAME = "feishu"
    API_BASE_URL = "https://open.feishu.cn/open-apis/"

    def __init__(self, msg_type=None, token_type=None, **kwargs):
        super().__init__(**kwargs)
        self._msg_type = msg_type

        self._token_mapping = {}
        self._token = Token(client=self, token_type=token_type, **kwargs)
        self._message = FeishuMessage(client=self)

    def get_access_token(self):
        return self._token.access_token


class FeishuClient(FeishuBase, FeishuMessageBodyParser):
    """ 企业自建应用(非商店应用) """

    def upload_media(self, media_type, filename=None, media_file=None):
        pass

    def send(self, msgtype, body_kwargs, userid_list=(), dept_id_list=(), to_all_user=False):
        self._msg_type = msgtype
        message_body = self.get_message_body(**body_kwargs)
        assert isinstance(message_body, MsgBodyBase), "Parameter `msg_body` must is a instance of MsgBodyBase"

        payload = message_body.get_dict()
        # return self._message.send(payload, receive_id=userid_list[0])
        raise NotImplementedError("Not Implemented")

    def recall(self, task_id):
        pass
