import time
import random
import string
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool

from django.test import TestCase

from easypush import pushes, easypush
from easypush.core.lock import atomic_task_with_lock


class RedisLockTestCase(TestCase):
    def setUp(self) -> None:
        self.count = 0
        self.lock_key = ''.join(random.choice(string.ascii_letters) for _ in range(26))

    def calculate(self, *args):
        self.count += 1

    def test_qps(self):
        maxsize = 50000
        pool = ThreadPool()
        task_fun = partial(atomic_task_with_lock, self.lock_key, self.calculate, delay=0.001, expire=2)

        start_time = time.time()
        iterable = [(i,) for i in range(maxsize)]
        pool.map(task_fun, iterable)

        cost_time = time.time() - start_time
        print("Cal ret: %s, maxsize:%s, cost:%s, qps:%.2f" % (self.count, maxsize, cost_time, maxsize / cost_time))

        pool.close()
        pool.join()


class DingTalkTestCase(TestCase):
    def setUp(self) -> None:
        self.is_send = True
        self.message = easypush

    def send(self, msgtype, body_kwargs):
        return self.message.async_send(msgtype=msgtype, body_kwargs=body_kwargs, userid_list=["manager8174"])

    def test_send_text(self):
        if not self.is_send:
            return

        ret = self.send("text", body_kwargs=dict(
            content="的就是废话缩短开发后端数据库"
        ))
        print('test_send_text ret:%s' % ret)


class QyWeixinTestCase(TestCase):
    def setUp(self) -> None:
        self.is_send = False
        self.task_list = []
        self.message = pushes["qy_weixin"]

    def send(self, msgtype, body_kwargs):
        return self.message.async_send(msgtype=msgtype, body_kwargs=body_kwargs, userid_list=["DingXuTao"])

    def test_send_media(self):
        print("test_upload_media ")
        media_type = "image"

        media_list = [
            ("image", "C:/Users/dingxt/Desktop/xx/x/z/Jangjoo/JUNe6dk3vG8EPQxt.jpg"),
            ("video", "C:/Users/dingxt/Videos/VID_20220824220030.mp4"),
            ("file", "C:/Users/dingxt/Desktop/xx/x/z/Jangjoo/v8ZYw6dlJCxJu-jn.jpg"),
        ]

        if not self.is_send:
            return

        for items in media_list:
            media_ret = self.message.upload_media(
                media_type=items[0], filename=items[1]
            )
            media_id = media_ret["media_id"]
            ret = self.send(media_type, body_kwargs=dict(media_id=media_id))
            print("test_upload_media ret:%s" % ret)
            self.task_list.append(ret["task_id"])

    def test_send_text(self):
        if not self.is_send:
            return

        ret = self.send("text", body_kwargs=dict(content="你的快递已到，请携带工卡前往邮件中心领取。\n出发前可查看<a href=\"http://work.weixin.qq.com\">邮件中心视频实况</a>，聪明避开排队。"))
        print("test_send_text ret:%s" % ret)
        self.task_list.append(ret["task_id"])

    def test_send_textcard(self):
        if not self.is_send:
            return

        ret = self.send(
            "textcard",
            body_kwargs=dict(
                title="textcard领奖通知",
                description="<div class=\"gray\">2016年9月26日</div> <div class=\"normal\">恭喜你抽中iPhone 7一台，领奖码：xxxx</div><div class=\"highlight\">请于2016年10月10日前联系行政同事领取</div>",
                url="https://wx4.sinaimg.cn/mw2000/6d989a5cgy1h6uosqucwtj21zj2nd1ky.jpg",
                btntxt="More"
            ))
        print("test_send_text ret:%s" % ret)
        self.task_list.append(ret["task_id"])

    def test_send_news(self):
        if not self.is_send:
            return

        ret = self.send(
            "news",
            body_kwargs=dict(
                articles=[
                    dict(
                        title="new消息",
                        description="今年中秋节公司有豪礼相送，一大波好礼正在走来，赶快来看看瞧瞧吧...!",
                        url="https://wx3.sinaimg.cn/mw1024/6d989a5cgy1gr1gfjv6gqj21oox6p.jpg",
                        picurl="https://wx2.sinaimg.cn/mw1024/6d989a5cgy1gr1gforhl1o02yox6p.jpg",
                    )
                ]
            ))
        print("test_send_text ret:%s" % ret)
        self.task_list.append(ret["task_id"])

    def test_send_mpnews(self):
        if not self.is_send:
            return

        ret = self.send(
            "mpnews",
            body_kwargs=dict(
                articles=[
                    dict(
                        title="mpnews 消息",
                        thumb_media_id='3wQQAB3eS28ctNYtNUsFob_qE639xyLPSsUo68WmvDSQJc_yok0PK_Aoo4nTWrC9j',
                        author="王大大的LP",
                        content="今年中秋节公司有豪礼相送，一大波好礼正在走来，赶快来看看瞧瞧吧...!",
                        digest="<img src=https://wx3.sinaimg.cn/mw1024/6d989a5cgy1gr1gfjv6gqj02yox6p.jpg>",
                        content_source_url="https://wx2.sinaimg.cn/mw1024/6d989a5cgy1gr1gforhl2j0ox6p.jpg",
                    )
                ]
            ))
        print("test_send_text ret:%s" % ret)
        self.task_list.append(ret["task_id"])

    def test_send_markdown(self):
        if not self.is_send:
            return

        ret = self.send(
            "markdown",
            body_kwargs=dict(
                content="您的会议室已经预定，稍后会同步到`邮箱` \n"
                        "**事项详情** \n"
                        "事　项：<font color=\"info\">开会</font> \n"
                        "组织者：@miglioguan \n"
                        "参与者：@miglioguan、@kunliu、@jamdeezhou、@kanexiong、@kisonwang \n"
                        "会议室：<font color=\"info\">广州TIT 1楼 301</font> \n"
                        "日　期：<font color=\"warning\">2018年5月18日</font> \n"
                        "时　间：<font color=\"comment\">上午9:00-11:00</font> \n"
                        "请准时参加会议。 \n"
                        "如需修改会议信息，请点击：[修改会议信息](https://work.weixin.qq.com)",

            ))
        print("test_send_text ret:%s" % ret)
        self.task_list.append(ret["task_id"])

    def test_send_template_card(self):
        if not self.is_send:
            return

        ret = self.send(
            "template_card",
            body_kwargs=dict(
                card_type="text_notice",
                source={
                    "icon_url": "图片的url",
                    "desc": "企业微信",
                    "desc_color": 1
                },
                action_menu={
                    "desc": "卡片副交互辅助文本说明",
                    "action_list": [
                        {"text": "接受推送", "key": "A"},
                        {"text": "不再推送", "key": "B"}
                    ]
                },
                task_id="1234dftrygcv",
                main_title={
                    "title" : "欢迎使用企业微信",
                    "desc" : "您的好友正在邀请您加入企业微信"
                },
                quote_area={
                    "type": 1,
                    "url": "https://work.weixin.qq.com",
                    "title": "企业微信的引用样式",
                    "quote_text": "企业微信真好用呀真好用"
                },
                emphasis_content={
                    "title": "100",
                    "desc": "核心数据"
                },
                sub_title_text="下载企业微信还能抢红包！",
                horizontal_content_list=[
                    {
                        "keyname": "邀请人",
                        "value": "张三"
                    },
                    {
                        "type": 1,
                        "keyname": "企业微信官网",
                        "value": "点击访问",
                        "url": "https://work.weixin.qq.com"
                    },
                    {
                        "type": 2,
                        "keyname": "企业微信下载",
                        "value": "企业微信.apk",
                        "media_id": "文件的media_id"
                    },
                    {
                        "type": 3,
                        "keyname": "员工信息",
                        "value": "点击查看",
                        "userid": "zhangsan"
                    }
                ],
                # jump_list=[
                #     {
                #         "type": 1,
                #         "title": "企业微信官网",
                #         "url": "https://work.weixin.qq.com"
                #     },
                #     # {
                #     #     "type": 2,
                #     #     "title": "跳转小程序",
                #     #     "appid": "小程序的appid",
                #     #     "pagepath": "/index.html"
                #     # }
                # ],
                # card_action={
                #     "type": 1,
                #     "url": "https://work.weixin.qq.com",
                #     # "appid": "小程序的appid",
                #     # "pagepath": "/index.html"
                # }
            ))
        print("test_send_text ret:%s" % ret)
        self.task_list.append(ret["task_id"])

    def tearDown(self) -> None:
        super().tearDown()

        # for task_id in self.task_list:
            # ret = self.message.recall(task_id=task_id)
            # print("Recall task_id:%s, ret:%s" % (task_id, ret))


class ApiTestCase(TestCase):
    def setUp(self) -> None:
        pass

