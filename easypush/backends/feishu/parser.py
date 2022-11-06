from .api import body as fs_body

from easypush.backends.base.body import ParserBodyBase
from easypush.utils.constants import FeishuMediaEnum
from easypush.utils.constants import FeishuMessageTypeEnum


class FeishuMessageBodyParser(ParserBodyBase):
    MESSAGE_MEDIA_ENUM = FeishuMediaEnum
    MESSAGE_TYPE_ENUM = FeishuMessageTypeEnum

    def get_text_body(self, text="", user_id=None, at_name=None):
        self.check_msg_type(fs_body.TextBody)
        return fs_body.TextBody(text, user_id, at_name)
