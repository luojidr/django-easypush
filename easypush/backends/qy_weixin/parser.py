from .api import body as qy_body
from easypush.utils import exceptions
from easypush.utils.util import to_binary
from easypush.utils.constants import QyWXMediaEnum
from easypush.utils.constants import QyWXMessageTypeEnum
from easypush.backends.base.body import ParserBodyBase


class QyWXMessageBodyParser(ParserBodyBase):
    MESSAGE_MEDIA_ENUM = QyWXMediaEnum
    MESSAGE_TYPE_ENUM = QyWXMessageTypeEnum

    def _validate_field_length(self, fields, body_name=None):
        """校验消息体字段长度 """
        for field in fields:
            field_name = field[0]
            max_field_size = field[1]
            field_value = field[2]

            if field_value is not None and len(field_value) > max_field_size:
                args = (body_name, field_name, max_field_size)
                raise exceptions.ExceedContentMaxSizeError("QyWXBody.%s %s exceed %s length." % args)

    def get_text_body(self, content, **kwargs):
        self.check_msg_type(qy_body.TextBody)

        fields = [("content", 2048, to_binary(content))]
        self._validate_field_length(fields=fields, body_name="TextBody")

        return qy_body.TextBody(content=content, **kwargs)

    def get_media_body(self, media_id, **kwargs):
        media_enum = self.MESSAGE_MEDIA_ENUM.get_media_enum(self._msg_type)
        body_cls = media_enum.body_class

        self.check_msg_type(body_cls)
        return body_cls(media_id=media_id, **kwargs)

    def get_video_body(self, media_id, title="", description="", **kwargs):
        self.check_msg_type(qy_body.VideoBody)

        fields = [
            ("title", 128, to_binary(title)),
            ("description", 512, to_binary(description)),
        ]
        self._validate_field_length(fields=fields, body_name="VideoBody")

        return qy_body.VideoBody(media_id, title, description, **kwargs)

    def get_markdown_body(self, content, **kwargs):
        self.check_msg_type(qy_body.MarkdownBody)

        fields = [("content", 2048, to_binary(content))]
        self._validate_field_length(fields=fields, body_name="MarkdownBody")

        return qy_body.MarkdownBody(content=content, **kwargs)

    def get_textcard_body(self, title, description, url, btntxt="", **kwargs):
        self.check_msg_type(qy_body.TextCardBody)

        fields = [
            ("title", 128, to_binary(title)),
            ("description", 512, to_binary(description)),
            ("url", 2048, to_binary(url)),
            ("btntxt", 4, btntxt),
        ]
        self._validate_field_length(fields=fields, body_name="TextCardBody")

        return qy_body.TextCardBody(title, description, url, btntxt, **kwargs)

    def get_news_body(self, articles, **kwargs):
        self.check_msg_type(qy_body.NewsBody)

        for article in articles:
            fields = [
                ("title", 128, to_binary(article["title"])),
                ("description", 512, to_binary(article.get("description"))),
                ("url", 2048, to_binary(article.get("url"))),
                ("pagepath", 2048, to_binary(article.get("pagepath"))),
            ]
            self._validate_field_length(fields=fields, body_name="NewsBody")

        return qy_body.NewsBody(articles=articles, **kwargs)

    def get_mpnews_body(self, articles,  **kwargs):
        self.check_msg_type(qy_body.MpNewsBody)

        for article in articles:
            fields = [
                ("title", 128, to_binary(article["title"])),
                ("content", 666, to_binary(article["content"])),
                ("author", 64, to_binary(article.get("author"))),
                ("digest", 512, to_binary(article.get("digest"))),
            ]
            self._validate_field_length(fields=fields, body_name="MpNewsBody")

        return qy_body.MpNewsBody(articles=articles, **kwargs)

    def get_miniprogram_notice_body(self, appid, title, page="", description="",
                                    emphasis_first_item=False, content_item=None, **kwargs):
        content_item = content_item or []
        self.check_msg_type(qy_body.MiniProgramBody)

        fields = [("title", 4, 12, title), ("description", 4, 12, description),]
        self._validate_field_length(fields=fields, body_name="MiniProgramBody")

        if len(content_item) > 10:
            raise exceptions.ExceedContentMaxSizeError("QyWXBody.MiniProgramBody content_item exceed 10 size.")

        for item in content_item:
            key, value = item.items()
            if len(key) > 10:
                raise exceptions.ExceedContentMaxSizeError("QyWXBody.MiniProgramBody key exceed 10.")

            if len(value) > 30:
                raise exceptions.ExceedContentMaxSizeError("QyWXBody.MiniProgramBody value exceed 30.")

        return qy_body.MiniProgramBody(appid, title, page, description, emphasis_first_item, content_item, **kwargs)

    def get_template_card_body(self, card_type, **kwargs):
        cls_name = card_type.title().replace("_", "") + "Body"
        card_type_body_cls = getattr(qy_body, cls_name, None)

        if card_type_body_cls is None:
            raise ModuleNotFoundError("`QyWXBody` module not find `%s` class" % cls_name)

        return card_type_body_cls(**kwargs)
