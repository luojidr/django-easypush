import types
import typing
import inspect

from easypush.backends.base.body import MsgBodyBase
from easypush.backends.base.body import BodyFieldValidator


class QyWXBodyBase(MsgBodyBase):
    # https://developer.work.weixin.qq.com/document/path/90236
    touser = ()
    toparty = ()
    totag = ()
    agentid = 0
    safe = 0
    enable_id_trans = 0
    enable_duplicate_check = 0
    duplicate_check_interval = 4 * 60 * 60

    def __init__(self, **kwargs):
        new_kwargs = {k: val for k, val in kwargs.items() if val}
        super().__init__(**{self.msgtype: dict(new_kwargs)})


class TextBody(QyWXBodyBase):
    _msgtype = 'text'

    def __init__(self, content, **kwargs):
        """ 文本消息
        :param content: string, 消息内容，最长不超过2048个字节，超过将截断（支持id转译）
        """
        super().__init__(content=content, **kwargs)


class FileBody(QyWXBodyBase):
    _msgtype = 'file'

    def __init__(self, media_id, **kwargs):
        """ 文件消息
        @:param media_id: string, 图片|视频|语音 媒体文件id，可以调用上传临时素材接口获取
        """
        super().__init__(media_id=media_id, **kwargs)


class ImageBody(FileBody):
    """ 图片消息 """
    _msgtype = 'image'


class VoiceBody(FileBody):
    """ 语音消息 """
    _msgtype = 'voice'


class VideoBody(FileBody):
    _msgtype = 'video'

    def __init__(self, media_id, title="", description="", **kwargs):
        """ 视频消息
        @:param media_id: string, 视频媒体文件id，可以调用上传临时素材接口获取
        @:param title: string, 视频消息的标题，不超过128个字节，超过会自动截断
        @:param description: string, 视频消息的描述，不超过512个字节，超过会自动截断
        """
        super().__init__(media_id=media_id, title=title, description=description, **kwargs)


class MarkdownBody(QyWXBodyBase):
    _msgtype = "markdown"

    def __init__(self, content, **kwargs):
        """ markdown消息
        @:param content: string, markdown内容，最长不超过2048个字节，必须是utf8编码
        """
        super().__init__(content=content, **kwargs)


class NewsBody(QyWXBodyBase):
    _msgtype = 'news'

    def __init__(self, articles, **kwargs):
        """ 图文消息
        @:param title: string, 标题，不超过128个字节，超过会自动截断（支持id转译）
        @:param description: string, 描述，不超过512个字节，超过会自动截断（支持id转译）
        @:param url: string, 点击后跳转的链接。 最长2048字节，请确保包含了协议头(http/https)，小程序或者url必须填写一个
        @:param picurl: string, 图文消息的图片链接，最长2048字节，支持JPG、PNG格式，较好的效果为大图 1068*455，小图150*150
        @:param appid: string, 小程序appid，必须是与当前应用关联的小程序，appid和pagepath必须同时填写，填写后会忽略url字段
        @:param pagepath: string, 点击消息卡片后的小程序页面，最长128字节，仅限本小程序内的页面。
                          appid和pagepath必须同时填写，填写后会忽略url字段
        """
        article_list = []

        for item in articles:
            article = self._add_article(**item)
            article and article_list.append(article)

        super().__init__(articles=article_list, **kwargs)

    def _add_article(self, title, description="", url=None, picurl=None, appid=None, pagepath=None):
        if title or description or url or picurl or appid or pagepath:
            return dict(
                title=title, description=description,
                url=url, picurl=picurl, appid=appid, pagepath=pagepath,
            )


class MpNewsBody(QyWXBodyBase):
    _msgtype = 'mpnews'

    def __init__(self, articles, **kwargs):
        """ 图文消息
        @:param title: string, 标题，不超过128个字节，超过会自动截断（支持id转译）
        @:param thumb_media_id: string, 图文消息缩略图的media_id, 可以通过素材管理接口获得。
                                此处thumb_media_id即上传接口返回的media_id
        @:param content: string, 图文消息的内容，支持html标签，不超过666 K个字节（支持id转译）
        @:param author: string, 图文消息的作者，不超过64个字节
        @:param content_source_url: string, 图文消息点击“阅读原文”之后的页面链接
        @:param digest: string, 图文消息的描述，不超过512个字节，超过会自动截断（支持id转译）
        """
        article_list = []

        for item in articles:
            article = self._add_article(**item)
            article and article_list.append(article)

        super().__init__(articles=article_list, **kwargs)

    def _add_article(self, title, thumb_media_id, content, author="", content_source_url=None, digest=None):
        if title or thumb_media_id or content or author or content_source_url or digest:
            return dict(
                title=title, thumb_media_id=thumb_media_id, content=content,
                author=author, content_source_url=content_source_url, digest=digest,
            )


class TextCardBody(QyWXBodyBase):
    _msgtype = 'textcard'

    def __init__(self, title, description, url, btntxt="详情", **kwargs):
        """ 文本卡片消息
        @:param title: string, 标题，不超过128个字节，超过会自动截断（支持id转译）
        @:param description: string, 描述，不超过512个字节，超过会自动截断（支持id转译）
        @:param url: string, 点击后跳转的链接。最长2048字节，请确保包含了协议头(http/https)
        @:param btntxt: string, 按钮文字。 默认为“详情”， 不超过4个文字，超过自动截断。
        """
        super().__init__(title=title, description=description, url=url, btntxt=btntxt, **kwargs)


class MiniProgramBody(QyWXBodyBase):
    _msgtype = 'miniprogram_notice'

    def __init__(self, appid, title, page="", description="", emphasis_first_item=False, content_item=None, **kwargs):
        """ 小程序通知消息
        @:param appid: string, 小程序appid，必须是与当前应用关联的小程序
        @:param title: string, 消息标题，长度限制4-12个汉字（支持id转译）
        @:param page: string, 点击消息卡片后的小程序页面，最长1024个字节，仅限本小程序内的页面。该字段不填则消息点击后不跳转
        @:param description: string, 消息描述，长度限制4-12个汉字（支持id转译）
        @:param emphasis_first_item: bool, 是否放大第一个content_item
        @:param content_item: dict, 消息内容键值对，最多允许10个item, like, eg:
          [
            {
                "key": "会议室",
                "value": "402"
            }
          ]

        """
        super().__init__(
            appid=appid, title=title, page=page, description=description,
            emphasis_first_item=emphasis_first_item, content_item=content_item,
            **kwargs
        )


class TemplateCardBase(QyWXBodyBase):
    _msgtype = 'template_card'

    card_type = None
    task_id = None
    sub_title_text = None
    source = None
    action_menu = None
    main_title = None
    quote_area = None
    horizontal_content_list = None
    jump_list = None
    card_action = None

    emphasis_content = None
    image_text_area = None
    card_image = None
    vertical_content_list = None
    button_selection = None
    button_list = None

    checkbox = None
    submit_button = None

    select_list = None

    def __init__(self, **kwargs):
        if self.card_type is None:
            raise ValueError(" TemplateCard.card_type not allowed empty")

        self._cleaned_kwargs = {}
        self._raw_kwargs = kwargs

        for name in self._get_template_card_attrs():
            if not self._raw_kwargs.get(name):
                continue

            attr_or_method = getattr(self, "_get_%s" % name, None)
            if attr_or_method and callable(attr_or_method):
                valid_data = attr_or_method()
                self._cleaned_kwargs.update(valid_data)
            else:
                self._cleaned_kwargs[name] = self._raw_kwargs[name]

        super().__init__(**self._cleaned_kwargs)

    def _get_template_card_attrs(self):
        """ Not parent class attributes """
        attrs = getattr(self, "_template_card_attrs", None)
        if attrs:
            return attrs

        predicate = (lambda o: not isinstance(o, (typing.Callable, types.GeneratorType)))
        self_members = inspect.getmembers(TemplateCardBase, predicate=predicate)
        self_attrs = [item[0] for item in self_members if not item[0].startswith("_")]

        base_members = inspect.getmembers(TemplateCardBase.__base__, predicate)
        base_attrs = [item[0] for item in base_members if not item[0].startswith("_")]

        attrs = list(set(self_attrs) - set(base_attrs))
        setattr(self, "_template_card_attrs", attrs)
        return attrs

    def _get_source(self):
        source = BodyFieldValidator("source", type="dict", required=False)
        source.add_field("icon_url", required=False)
        source.add_field("desc", required=False)
        source.add_field("desc_color", required=False)

        return source.get_valid_data(self._raw_kwargs)

    def _get_action_menu(self):
        action_menu = BodyFieldValidator("action_menu", type="dict", required=False)
        action_menu.add_field("desc", required=False)

        action_list = BodyFieldValidator("action_list", type="list", required=True)
        action_list.add_field("key", required=True)
        action_list.add_field("text", required=True)

        action_menu.add_field(validator=action_list)
        return action_menu.get_valid_data(self._raw_kwargs)

    def _get_main_title(self):
        main_title = BodyFieldValidator("main_title", type="dict", required=False)
        main_title.add_field("title", required=False)
        main_title.add_field("desc", required=False)

        return main_title.get_valid_data(self._raw_kwargs)

    def _get_quote_area(self):
        quote_area = BodyFieldValidator("quote_area", type="dict", required=False)
        quote_area.add_field("type", required=False)
        quote_area.add_field("url", required=False)
        quote_area.add_field("appid", required=False)
        quote_area.add_field("pagepath", required=False)
        quote_area.add_field("title", required=False)
        quote_area.add_field("quote_text", required=False)

        return quote_area.get_valid_data(self._raw_kwargs)

    def _get_horizontal_content_list(self):
        horizontal_content_list = BodyFieldValidator("horizontal_content_list", type="list", required=False)
        horizontal_content_list.add_field("type", required=False)
        horizontal_content_list.add_field("keyname", required=True)
        horizontal_content_list.add_field("value", required=False)
        horizontal_content_list.add_field("url", required=False)
        horizontal_content_list.add_field("media_id", required=False)
        horizontal_content_list.add_field("userid", required=False)

        return horizontal_content_list.get_valid_data(self._raw_kwargs)

    def _get_jump_list(self):
        jump_list = BodyFieldValidator("jump_list", type="list", required=False)
        jump_list.add_field("type", required=False)
        jump_list.add_field("title", required=True)
        jump_list.add_field("url", required=False)
        jump_list.add_field("appid", required=False)
        jump_list.add_field("pagepath", required=False)

        return jump_list.get_valid_data(self._raw_kwargs)

    def _get_card_action(self):
        card_action = BodyFieldValidator("card_action", type="dict", required=True)
        card_action.add_field("type", required=True)
        card_action.add_field("url", required=False)
        card_action.add_field("appid", required=False)
        card_action.add_field("pagepath", required=False)

        return card_action.get_valid_data(self._raw_kwargs)

    def _get_emphasis_content(self):
        emphasis_content = BodyFieldValidator("emphasis_content", type="dict", required=False)
        emphasis_content.add_field("title", required=False)
        emphasis_content.add_field("desc", required=False)

        return emphasis_content.get_valid_data(self._raw_kwargs)

    def _get_image_text_area(self):
        image_text_area = BodyFieldValidator("image_text_area", type="dict", required=False)
        image_text_area.add_field("type", required=False)
        image_text_area.add_field("url", required=False)
        image_text_area.add_field("appid", required=False)
        image_text_area.add_field("pagepath", required=False)
        image_text_area.add_field("title", required=False)
        image_text_area.add_field("desc", required=False)
        image_text_area.add_field("image_url", required=True)

        return image_text_area.get_valid_data(self._raw_kwargs)

    def _get_card_image(self):
        card_image = BodyFieldValidator("card_image", type="dict", required=False)
        card_image.add_field("url", required=True)
        card_image.add_field("aspect_ratio", required=False)

        return card_image.get_valid_data(self._raw_kwargs)

    def _get_vertical_content_list(self):
        vertical_content_list = BodyFieldValidator("vertical_content_list", type="list", required=False)
        vertical_content_list.add_field("title", required=True)
        vertical_content_list.add_field("desc", required=False)

        return vertical_content_list.get_valid_data(self._raw_kwargs)

    def _get_button_selection(self):
        button_selection = BodyFieldValidator("button_selection", type="dict", required=True)
        button_selection.add_field("question_key", required=True)
        button_selection.add_field("selected_id", required=False)
        button_selection.add_field("title", required=False)

        option_list = BodyFieldValidator("option_list", type="list", required=True)
        option_list.add_field("id", required=True)
        option_list.add_field("text", required=True)

        button_selection.add_field(validator=option_list)
        return button_selection.get_valid_data(self._raw_kwargs)

    def _get_button_list(self):
        button_list = BodyFieldValidator("button_list", type="list", required=True)
        button_list.add_field("type", required=False)
        button_list.add_field("text", required=True)
        button_list.add_field("style", required=False)
        button_list.add_field("key", required=False)
        button_list.add_field("url", required=False)

        return button_list.get_valid_data(self._raw_kwargs)

    def _get_checkbox(self):
        checkbox = BodyFieldValidator("checkbox", type="dict", required=False)
        checkbox.add_field("question_key", required=True)
        checkbox.add_field("mode", required=False)

        option_list = BodyFieldValidator("option_list", type="list", required=False)
        option_list.add_field("id", required=True)
        option_list.add_field("text", required=True)
        option_list.add_field("is_checked", required=True)

        checkbox.add_field(option_list)
        return checkbox.get_valid_data(self._raw_kwargs)

    def _get_submit_button(self):
        submit_button = BodyFieldValidator("button_list", type="dict", required=False)
        submit_button.add_field("text", required=True)
        submit_button.add_field("key", required=True)

        return submit_button.get_valid_data(self._raw_kwargs)

    def _get_select_list(self):
        select_list = BodyFieldValidator("select_list", type="list", required=True)
        select_list.add_field("question_key", required=True)
        select_list.add_field("title", required=False)
        select_list.add_field("selected_id", required=False)

        option_list = BodyFieldValidator("option_list", type="list", required=False)
        option_list.add_field("id", required=True)
        option_list.add_field("text", required=True)

        select_list.add_field(option_list)
        return select_list.get_valid_data(self._raw_kwargs)


class TextNoticeBody(TemplateCardBase):
    card_type = 'text_notice'

    def __init__(self, emphasis_content=None, **kwargs):
        super().__init__(emphasis_content=emphasis_content, **kwargs)


class NewsNoticeBody(TemplateCardBase):
    card_type = 'news_notice'

    def __init__(self, image_text_area=None, card_image=None, vertical_content_list=None, **kwargs):
        super().__init__(
            image_text_area=image_text_area, card_image=card_image,
            vertical_content_list=vertical_content_list, **kwargs
        )


class ButtonInteractionBody(TemplateCardBase):
    card_type = 'button_interaction'

    def __init__(self, button_selection, button_list, **kwargs):
        super().__init__(button_selection=button_selection, button_list=button_list, **kwargs)


class VoteInteractionBody(TemplateCardBase):
    card_type = 'vote_interaction'

    def __init__(self, checkbox=None, submit_button=None, **kwargs):
        super().__init__(checkbox=checkbox, submit_button=submit_button, **kwargs)


class MultipleInteractionBody(TemplateCardBase):
    card_type = 'multiple_interaction'

    def __init__(self, select_list, submit_button, **kwargs):
        super().__init__(select_list=select_list, submit_button=submit_button, **kwargs)
