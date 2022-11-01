import os.path

from easypush.backends.base.base import PushApiBase
from easypush.backends.base.body import MsgBodyBase
from easypush.utils.util import to_text
from easypush.utils import exceptions


class QyMessage(PushApiBase):
    def __init__(self, client=None):
        super().__init__()

        self._client = client
        self._api_base_url = self._client.API_BASE_URL
        self._access_token = self._client.access_token

    @property
    def corp_id(self):
        return self._client._corp_id

    def media_upload(self, media_type, filename=None, media_file=None):
        """
        :param media_type:
        :param filename:
        :param media_file:
        :return:  {
            'errcode': 0,
            'errmsg': 'ok',
            'type': 'image',
            'media_id': '3b_4G7-rJKtKakG4B-iGpt4k4pdYEn5CIDHSL2v9ugTApXEQjZesJWhU31Ms4rDbV',
            'created_at': '1667296036'
        }
        """
        params = dict(access_token=self._access_token, type=media_type)

        fp = open(filename, "rb") if filename else media_file
        filename = filename or media_file.name
        media_enum = self._client.MESSAGE_MEDIA_ENUM.get_media_enum(media_type)

        if self._client.get_size(fp) > media_enum.max_size:
            raise exceptions.ExceedContentMaxSizeError("Media[%s] exceed %s size" % (filename, media_enum.max_size))

        upload_files = [("media", os.path.basename(filename), fp.read())]
        fp.close()

        return self._request(
            method="POST", endpoint="media.upload",
            params=params, upload_files=upload_files,
        )

    def media_download(self, media_id):
        pass

    def send_to_conversation(self, sender, cid, msg_body):
        """ 发送普通消息 """

    def asyncsend_v2(self, msg_body, agent_id, touser=(), toparty=(), totag=()):
        """ 应用支持推送文本、图片、视频、文件、图文等类型
        @:param msg_body:
        @:param touser: 成员ID列表（消息接收者，多个接收者用‘|’分隔，最多支持1000个）
        @:param toparty: 部门ID列表，多个接收者用‘|’分隔，最多支持100个
        @:param totag: 标签ID列表，多个接收者用‘|’分隔，最多支持100个
        """
        if isinstance(touser, (list, tuple)):
            touser = "|".join(map(to_text, touser))

        if isinstance(toparty, (list, tuple)):
            toparty = "|".join(map(to_text, toparty))

        if isinstance(totag, (list, tuple)):
            totag = "|".join(map(to_text, totag))

        if isinstance(msg_body, MsgBodyBase):
            msg_body = msg_body.get_dict()

        new_msg_body = msg_body[self._client.msgtype]
        new_msg_body.update(
            agentid=agent_id, touser=touser,
            toparty=toparty, totag=totag
        )
        return self._request(
            method="POST", endpoint="message.send",
            params=dict(access_token=self._access_token), data=new_msg_body,
        )

    def get_send_progress(self, agent_id, task_id):
        pass

    def get_send_result(self, agent_id=None, task_id=None):
        pass

    def recall(self, msgid):
        """ 撤回应用消息
        :param msgid: string, 消息ID。从应用发送消息接口处获得
        """
        params = dict(access_token=self._access_token)
        return self._request(
            method="POST", endpoint="message.recall",
            params=params, data=dict(msgid=msgid),
        )
