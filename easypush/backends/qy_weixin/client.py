import typing
from datetime import datetime

from .message import QyMessage
from .parser import QyWXMessageBodyParser
from easypush.backends.base.base import ClientMixin
from easypush.backends.base.body import MsgBodyBase
from easypush.utils.constants import QyWXMediaEnum
from easypush.utils.decorators import token_expire_cache


class QyWeixinBase(ClientMixin):
    CLIENT_NAME = "qy_weixin"
    TOKEN_EXPIRE_TIME = 2 * 60 * 60
    MEDIA_EXPIRE_TIME = 3 * 24 * 60 * 60
    API_BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/"

    def __init__(self, msg_type=None,  **kwargs):
        super().__init__(**kwargs)
        self._msg_type = msg_type

        self._token_cache = {}
        self._message = QyMessage(client=self)

    @token_expire_cache(name="qy_weixin.token", timeout=TOKEN_EXPIRE_TIME)
    def get_access_token(self):
        """ 获取应用 access token
        Data:
            {
                "errcode": 0,
                "errmsg": "ok",
                "access_token": "accesstoken000001",
                "expires_in": 7200
            }
        """
        params = dict(corpid=self._corp_id, corpsecret=self._app_secret)
        result = self._request(method="GET", endpoint="gettoken", params=params)
        self.logger.info("[%s] token: %s" % (self.__class__.__name__, result))
        return result


class QyWeixinClient(QyWeixinBase, QyWXMessageBodyParser):
    """ 企业内部应用消息 """
    def upload_media(self, media_type, filename=None, media_file=None):
        assert media_type in QyWXMediaEnum.media_list(), "媒体文件类型(仅限: image, voice, file)错误!"

        self._check_media_exist(filename, media_file)
        return self._message.media_upload(media_type, filename, media_file)

    def send(self, msgtype, body_kwargs, userid_list=(), dept_id_list=(), to_all_user=False):
        """ 企业会话消息异步发送
        :param msgtype: 消息类型
        :param body_kwargs: dict, 不同消息体对应的参数
        :param userid_list: list|tuple, 接收者的用户userid列表
        :param dept_id_list: list|tuple, 接收者的部门id列表
        :param to_all_user: bool, 暂未使用
        """
        if not isinstance(userid_list, (typing.Tuple, typing.List)):
            raise ValueError("parameter `user_id_list` must is list|tuple")

        self._msg_type = msgtype
        message_body = self.get_message_body(**body_kwargs)
        assert isinstance(message_body, MsgBodyBase), "Parameter `msg_body` must is a instance of MsgBodyBase"

        return self._message.send_message(
            message_body,
            agent_id=self._agent_id, touser=userid_list,
            toparty=dept_id_list, totag=()
        )

    def recall(self, task_id):
        return self._message.recall(msgid=task_id)

