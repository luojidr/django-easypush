import json
import types
import typing

from easypush.backends.base.body import MsgBodyBase
from easypush.backends.base.body import BodyFieldValidator


class FeishuBodyBase(MsgBodyBase):
    def __init__(self, **kwargs):
        new_kwargs = {k: val for k, val in kwargs.items() if val}
        super().__init__(content=json.dumps(new_kwargs))


class TextBody(FeishuBodyBase):
    _msgtype = 'text'

    def __init__(self, text="", user_id=None, at_name=None, **kwargs):
        """ 文本消息
        :param text: string, 文本消息，如果需要文本中进行换行，需要增加转义
                     @用法说明：
                        <at user_id="ou_xxx">名字</at>  // @ 单个用户
                        <at user_id="all">所有人</at>   // @ 所有人
        :param user_id: string,
                        @单个用户时，user_id字段可填open_id，union_id和user_id，必须是有效值，否则取名字展示，没有@效果。
                        @所有人必须满足所在群开启@所有人功能
                        同一条消息内的ID类型必须保持一致。
        """
        if user_id is None:
            if not text:
                raise ValueError("文本消息不能为空")
        else:
            text = '<at user_id="%s">%s</at>' % (user_id, at_name)

        super().__init__(text=text, **kwargs)
