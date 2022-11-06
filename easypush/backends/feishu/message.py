import uuid
import os.path

from easypush.backends.base.base import RequestApiBase
from easypush.backends.base.body import MsgBodyBase
from easypush.utils.util import to_text
from easypush.utils import exceptions


class FeishuMessage(RequestApiBase):
    def __init__(self, client=None):
        super().__init__()

        self._client = client
        self._api_base_url = self._client.API_BASE_URL
        self._access_token = self._client.get_access_token()

        self._headers = {
            "Authorization": "Bearer %s" % self._access_token,
            "Content-Type": "application/json; charset=utf-8",
        }

    def send(self, msg_body, receive_id):
        new_msg_body = msg_body[self._client.msgtype]
        new_msg_body["msg_type"] = new_msg_body.pop("msgtype")
        new_msg_body.update(receive_id=receive_id, uuid=str(uuid.uuid1()))

        print(self._headers)
        return self._request(
            method="POST",
            endpoint="im.v1.messages",
            headers=self._headers,
            params=dict(receive_id_type="open_id"), data=new_msg_body,
        )
