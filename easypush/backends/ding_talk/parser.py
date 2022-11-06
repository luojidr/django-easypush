import os.path

from dingtalk.model import message

from easypush.backends.base.body import ParserBodyBase
from easypush.utils.constants import DingTalkMessageTypeEnum, DingTalkMediaEnum


class DingMessageBodyParser(ParserBodyBase):
    MESSAGE_MEDIA_ENUM = DingTalkMediaEnum
    MESSAGE_TYPE_ENUM = DingTalkMessageTypeEnum

    def get_text_body(self, content, **kwargs):
        self.check_msg_type(message.TextBody)
        return message.TextBody(content=content, **kwargs)

    def get_media_body(self, media_id=None, img_file=None, duration=None):
        """ 图片、文件、语音的消息体
        @param media_id: 媒体文件id，可以调用上传媒体文件接口获取。建议宽600像素 x 400像素，宽高比3：2
        @param img_file: 文件路径
        @param duration: 正整数，小于60，表示音频时长

        图片: 最大1MB，支持JPG格式
        文件: 最大10MB
        语音: 最大2MB，播放长度不超过60s，AMR格式
        """
        assert self._msg_type in DingTalkMediaEnum.media_list(), "媒体文件类型错误"

        media_kwargs = {}
        media_enum = DingTalkMediaEnum.get_media_enum(self._msg_type)

        if media_id is None and img_file is None:
            raise ValueError("媒体消息体解析中 media_id 与 img_file 不能同时为空")

        if img_file and not os.path.exists(img_file):
            raise ValueError("媒体文件路径<%s>不存在" % img_file)

        if img_file and os.path.getsize(img_file) > media_enum.max_size:
            raise ValueError("媒体文件大小<%s>已经超过上限<%s>" % (img_file, media_enum.max_size))

        if media_id is None:
            media_data = self.media_upload(img_file)
            media_id = media_data["data"]["media_id"]

        if self._msg_type == DingTalkMediaEnum.VOICE.type:
            if duration > 60:
                raise ValueError("音频播放时长不能超过60s")

            media_kwargs["duration"] = duration

        return media_enum.body_class(media_id=media_id, **media_kwargs)

    def get_link_body(self, message_url, pic_url, title, content, **kwargs):
        """ 超链接消息
        @param message_url: 消息点击链接地址
        @param pic_url: 图片媒体文件id，可以调用上传媒体文件接口获取
        @param title: 消息标题
        @param content: 消息描述
        """
        self.check_msg_type(message.LinkBody)
        return message.LinkBody(message_url, pic_url, title, content, **kwargs)

    def get_markdown_body(self, title, content, **kwargs):
        """
        @param title: String, 标题
        @param content: String, 内容
        :return:
        """
        self.check_msg_type(message.MarkdownBody)

        if len(content) > 5000:
            raise ValueError("Markdown 格式消息")

        return message.MarkdownBody(title=title, text=content, **kwargs)

    def get_oa_body(self,
                    message_url='', head_bgcolor="FFab855d",
                    head_text=None, title=None, content=None, author=None,
                    media_id=None, file_count=None, forms=None, rich_num=None,
                    rich_unit=None, pc_message_url=None, **kwargs):
        """
        @param message_url: 客户端点击消息时跳转到的H5地址
        @param head_bgcolor: 消息头部的背景颜色。长度限制为8个英文字符，其中前2为表示透明度，后6位表示颜色值。不要添加0x
        @param head_text: 消息的头部标题（向普通会话发送时有效，向企业会话发送时会被替换为微应用的名字），长度限制为最多10个字符
        @param pc_message_url: PC端点击消息时跳转到的H5地址
        @param title: 消息体的标题
        @param content: 消息体的内容，最多显示3行
        @param author: 	自定义的作者名字
        @param media_id: 消息体中的图片 media_id
        @param file_count: 自定义的附件数目。此数字仅供显示，钉钉不作验证
        @param forms: 消息体的表单, eg:[{"key": "姓名:", "value": "张三"},{"key": "年龄:", "value": "20"}]
        @param rich_num: 单行富文本信息的数目
        @param rich_unit: 单行富文本信息的单位
        """
        self.check_msg_type(message.OaBody)

        forms = {item["key"]: item["value"] for item in forms or []}
        oa_body_content = message.OaBodyContent(
            title=title, content=content, author=author,
            image=media_id, file_count=file_count, forms=forms,
            rich_num=rich_num, rish_unit=rich_unit, **kwargs
        )

        oa_body = message.OaBody(
            head_bgcolor=head_bgcolor, head_text=head_text, body=oa_body_content,
            message_url=message_url, pc_message_url=pc_message_url, **kwargs
        )

        return oa_body
