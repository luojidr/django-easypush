from easypush.backends.base.body import MsgBodyBase


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

    def __init__(self, title, description="", url=None, picurl=None, appid=None, pagepath=None, **kwargs):
        """ 图文消息
        @:param title: string, 标题，不超过128个字节，超过会自动截断（支持id转译）
        @:param description: string, 描述，不超过512个字节，超过会自动截断（支持id转译）
        @:param url: string, 点击后跳转的链接。 最长2048字节，请确保包含了协议头(http/https)，小程序或者url必须填写一个
        @:param picurl: string, 图文消息的图片链接，最长2048字节，支持JPG、PNG格式，较好的效果为大图 1068*455，小图150*150
        @:param appid: string, 小程序appid，必须是与当前应用关联的小程序，appid和pagepath必须同时填写，填写后会忽略url字段
        @:param pagepath: string, 点击消息卡片后的小程序页面，最长128字节，仅限本小程序内的页面。
                          appid和pagepath必须同时填写，填写后会忽略url字段
        """
        articles = []

        article = self._add_article(title, description, url, picurl, appid, pagepath)
        articles.append(article)
        super().__init__(articles=articles, **kwargs)

    def _add_article(self, title, description="", url=None, picurl=None, appid=None, pagepath=None):
        return dict(
            title=title, description=description,
            url=url, picurl=picurl, appid=appid, pagepath=pagepath,
        )


class MpNewsBody(QyWXBodyBase):
    _msgtype = 'mpnews'

    def __init__(self, title, thumb_media_id, content, author="", content_source_url=None, digest=None, **kwargs):
        """ 图文消息
        @:param title: string, 标题，不超过128个字节，超过会自动截断（支持id转译）
        @:param thumb_media_id: string, 图文消息缩略图的media_id, 可以通过素材管理接口获得。
                                此处thumb_media_id即上传接口返回的media_id
        @:param content: string, 图文消息的内容，支持html标签，不超过666 K个字节（支持id转译）
        @:param author: string, 图文消息的作者，不超过64个字节
        @:param content_source_url: string, 图文消息点击“阅读原文”之后的页面链接
        @:param digest: string, 图文消息的描述，不超过512个字节，超过会自动截断（支持id转译）
        """
        articles = []

        article = self._add_article(title, thumb_media_id, content, author, content_source_url, digest)
        articles.append(article)
        super().__init__(articles=articles, **kwargs)

    def _add_article(self, title, thumb_media_id, content, author="", content_source_url=None, digest=None):
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



