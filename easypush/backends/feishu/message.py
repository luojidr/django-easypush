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

    def send(self, payload, receive_id):
        new_payload = payload[self._client.msgtype]
        new_payload["msg_type"] = new_payload.pop("msgtype")
        new_payload.update(receive_id=receive_id, uuid=str(uuid.uuid1()))

        return self._request(
            method="POST",
            endpoint="im.v1.messages",
            headers=self._headers, ignore_error=True,
            params=dict(receive_id_type="open_id"), data=new_payload,
        )
