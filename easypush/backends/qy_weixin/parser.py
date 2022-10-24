from .api import body as QyWXBody
from easypush.utils import exceptions
from easypush.utils.util import to_binary
from easypush.utils.constants import QyWXMediaEnum
from easypush.backends.base.body import ParserBodyBase


class QyWXMessageBodyParser(ParserBodyBase):
    MESSAGE_MEDIA_ENUM = QyWXMediaEnum

    def validate_field_length(self, fields, body_name=None):
        """校验消息体字段长度 """
        for field in fields:
            name = field[0]
            max_size = field[1]

            if len(field[2]) > max_size:
                args = (body_name, name, max_size)
                raise exceptions.ExceedContentMaxSizeError("QyWXBody.%s %s exceed %s length." % args)

    def get_text_body(self, content, **kwargs):
        self.check_msg_type(QyWXBody.TextBody)

        fields = [("content", 2048, to_binary(content))]
        self.validate_field_length(fields=fields, body_name="TextBody")

        return QyWXBody.TextBody(content=content, **kwargs)

    def get_media_body(self, media_id, **kwargs):
        media_enum = self.MESSAGE_MEDIA_ENUM.get_media_enum(self._msg_type)
        body_cls = media_enum.body_class

        self.check_msg_type(body_cls)
        return body_cls(media_id=media_id, **kwargs)

    def get_video_body(self, media_id, title="", description="", **kwargs):
        self.check_msg_type(QyWXBody.VideoBody)

        fields = [
            ("title", 128, to_binary(title)),
            ("description", 512, to_binary(description)),
        ]
        self.validate_field_length(fields=fields, body_name="VideoBody")

        return QyWXBody.VideoBody(media_id, title, description, **kwargs)

    def get_markdown_body(self, content, **kwargs):
        self.check_msg_type(QyWXBody.MarkdownBody)

        fields = [("content", 2048, to_binary(content))]
        self.validate_field_length(fields=fields, body_name="MarkdownBody")

        return QyWXBody.MarkdownBody(content=content, **kwargs)

    def get_textcard_body(self, title, description, url, btntxt="", **kwargs):
        self.check_msg_type(QyWXBody.TextCardBody)

        fields = [
            ("title", 128, to_binary(title)),
            ("description", 512, to_binary(description)),
            ("url", 2048, to_binary(url)),
            ("btntxt", 4, btntxt),
        ]
        self.validate_field_length(fields=fields, body_name="TextCardBody")

        return QyWXBody.TextCardBody(title, description, url, btntxt, **kwargs)

    def get_news_body(self, title, description="", url="", picurl="", appid="", pagepath="", **kwargs):
        self.check_msg_type(QyWXBody.NewsBody)

        fields = [
            ("title", 128, to_binary(title)),
            ("description", 512, to_binary(description)),
            ("url", 2048, to_binary(url)),
            ("pagepath", 2048, to_binary(pagepath)),
        ]
        self.validate_field_length(fields=fields, body_name="NewsBody")

        return QyWXBody.NewsBody(title, description, url, picurl, appid, pagepath, **kwargs)

    def get_mpnews_body(self, title, thumb_media_id, content, author="",
                        content_source_url=None, digest="", **kwargs):
        self.check_msg_type(QyWXBody.MpNewsBody)

        fields = [
            ("title", 128, to_binary(title)),
            ("content", 666, to_binary(content)),
            ("author", 64, to_binary(author)),
            ("digest", 512, to_binary(digest)),
        ]
        self.validate_field_length(fields=fields, body_name="MpNewsBody")

        return QyWXBody.MpNewsBody(title, thumb_media_id, content, author, content_source_url, digest, **kwargs)

    def get_miniprogram_notice_body(self, appid, title, page="", description="",
                                    emphasis_first_item=False, content_item=None, **kwargs):
        content_item = content_item or []
        self.check_msg_type(QyWXBody.MiniProgramBody)

        fields = [("title", 4, 12, title), ("description", 4, 12, description),]
        self.validate_field_length(fields=fields, body_name="MiniProgramBody")

        if len(content_item) > 10:
            raise exceptions.ExceedContentMaxSizeError("QyWXBody.MiniProgramBody content_item exceed 10 size.")

        for item in content_item:
            key, value = item.items()
            if len(key) > 10:
                raise exceptions.ExceedContentMaxSizeError("QyWXBody.MiniProgramBody key exceed 10.")

            if len(value) > 30:
                raise exceptions.ExceedContentMaxSizeError("QyWXBody.MiniProgramBody value exceed 30.")

        return QyWXBody.MiniProgramBody(appid, title, page, description, emphasis_first_item, content_item, **kwargs)
