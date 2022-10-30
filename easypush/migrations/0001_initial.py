# Generated by Django 4.1.2 on 2022-10-30 06:53

import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion
import easypush.core.db.base
import easypush.core.path_builder


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AppMediaStorageModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('media_type', models.SmallIntegerField(blank=True, choices=[('image', '图片'), ('file', '普通文件'), ('voice', '语音'), ('video', '视频')], default=1, verbose_name='媒体类型')),
                ('media_title', models.CharField(blank=True, default='', max_length=500, verbose_name='媒体名称')),
                ('media_id', models.CharField(blank=True, default='', max_length=100, verbose_name='媒体id')),
                ('media', models.FileField(blank=True, max_length=500, storage=django.core.files.storage.FileSystemStorage(), upload_to=easypush.core.path_builder.PathBuilder('media'), verbose_name='媒体链接')),
                ('key', models.CharField(blank=True, default='', max_length=50, unique=True, verbose_name='上传文件key')),
                ('media_url', models.URLField(blank=True, default='', max_length=500, verbose_name='媒体文件URL')),
                ('file_size', models.IntegerField(blank=True, default=0, verbose_name='文件大小')),
                ('check_sum', models.CharField(blank=True, default='', max_length=64, verbose_name='源文件md5')),
                ('src_filename', models.CharField(blank=True, default='', max_length=200, verbose_name='源文件名称')),
                ('post_filename', models.CharField(blank=True, default='', max_length=200, verbose_name='处理后的文件名称')),
                ('is_share', models.BooleanField(blank=True, default=False, verbose_name='是否共享')),
                ('is_success', models.BooleanField(blank=True, default=False, verbose_name='是否成功')),
                ('access_token', models.CharField(blank=True, default='', max_length=100, verbose_name='token秘钥(如果不共享)')),
            ],
            options={
                'db_table': 'easypush_app_media_storage',
            },
        ),
        migrations.CreateModel(
            name='AppMsgPushRecordModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('app_msg_id', models.IntegerField(blank=True, default=None, verbose_name='消息主体')),
                ('sender', models.CharField(blank=True, default='sys', max_length=100, verbose_name='推送人(默认系统)')),
                ('send_time', models.DateTimeField(auto_now_add=True, verbose_name='推送时间')),
                ('receiver_mobile', models.CharField(blank=True, db_index=True, default='', max_length=20, verbose_name='接收人手机号')),
                ('receiver_userid', models.CharField(blank=True, default='', max_length=100, verbose_name='接收人userid')),
                ('receive_time', models.DateTimeField(blank=True, default='1979-01-01 00:00:00', verbose_name='接收时间')),
                ('is_read', models.BooleanField(blank=True, default=False, verbose_name='接收人是否已读')),
                ('read_time', models.DateTimeField(blank=True, default='1979-01-01 00:00:00', verbose_name='接收人已读时间')),
                ('is_success', models.BooleanField(blank=True, default=False, verbose_name='推送是否成功')),
                ('traceback', models.CharField(blank=True, default='', max_length=1200, verbose_name='推送异常')),
                ('task_id', models.CharField(blank=True, db_index=True, default='', max_length=100, verbose_name='钉钉创建的异步发送任务ID')),
                ('request_id', models.CharField(blank=True, default='', max_length=100, verbose_name='钉钉推送的请求ID')),
                ('msg_uid', models.CharField(blank=True, default='', max_length=100, unique=True, verbose_name='消息唯一id')),
                ('is_recall', models.BooleanField(blank=True, default=False, verbose_name='消息是否撤回')),
                ('recall_time', models.DateTimeField(blank=True, default='1979-01-01 00:00:00', verbose_name='撤回时间')),
                ('platform_type', models.CharField(choices=[('sms', '短信'), ('email', '邮件'), ('feishu', '飞书'), ('ding_talk', '钉钉'), ('qy_weixin', '企业微信')], default='', max_length=100, verbose_name='平台类型')),
            ],
            options={
                'db_table': 'easypush_app_msg_push_records',
            },
        ),
        migrations.CreateModel(
            name='AppTokenPlatformModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('corp_id', models.CharField(db_index=True, default='', max_length=100, verbose_name='企业corpId')),
                ('app_name', models.CharField(default='', max_length=100, unique=True, verbose_name='应用名称')),
                ('agent_id', models.IntegerField(default=0, unique=True, verbose_name='AppId')),
                ('app_key', models.CharField(default='', max_length=200, verbose_name='应用 appKey')),
                ('app_secret', models.CharField(default='', max_length=500, verbose_name='应用 appSecret')),
                ('app_token', models.CharField(db_index=True, default='', max_length=500, verbose_name='外部调用的唯一Token')),
                ('expire_time', models.BigIntegerField(default=0, verbose_name='Token过期时间')),
                ('platform_type', models.CharField(choices=[('sms', '短信'), ('email', '邮件'), ('feishu', '飞书'), ('ding_talk', '钉钉'), ('qy_weixin', '企业微信')], default='', max_length=100, verbose_name='平台类型')),
            ],
            options={
                'db_table': 'easypush_app_token_platform',
            },
        ),
        migrations.CreateModel(
            name='AppMessageModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=easypush.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('msg_title', models.CharField(blank=True, default='', max_length=500, verbose_name='消息标题')),
                ('msg_media', models.CharField(blank=True, default='', max_length=500, verbose_name='消息图片')),
                ('msg_type', models.SmallIntegerField(blank=True, choices=[('text', '文本消息'), ('image', '图片消息'), ('voice', '语音消息'), ('file', '文件消息'), ('news', '图文消息'), ('mpnews', '图文消息'), ('markdown', 'markdown 消息'), ('textcard', '文本卡片消息'), ('miniprogram_notice', '小程序通知消息'), ('template_card', '模板卡片消息'), ('text', '文本消息'), ('image', '图片消息'), ('voice', '语音消息'), ('file', '文件消息'), ('link', '链接消息'), ('oa', 'OA 消息'), ('markdown', 'markdown 消息'), ('action_card', 'action_card 消息'), ('single_action_card', 'action_card 消息'), ('btn_action_card', 'action_card 消息')], default=0, verbose_name='消息类型')),
                ('msg_text', models.CharField(blank=True, default='', max_length=1000, verbose_name='消息文本')),
                ('msg_url', models.CharField(blank=True, default='', max_length=500, verbose_name='APP跳转链接')),
                ('msg_pc_url', models.CharField(blank=True, default='', max_length=500, verbose_name='PC跳转链接')),
                ('msg_extra_json', models.CharField(blank=True, default='', max_length=1000, verbose_name='消息JSON数据')),
                ('platform_type', models.CharField(choices=[('sms', '短信'), ('email', '邮件'), ('feishu', '飞书'), ('ding_talk', '钉钉'), ('qy_weixin', '企业微信')], default='', max_length=100, verbose_name='平台类型')),
                ('app', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='easypush.apptokenplatformmodel', verbose_name='应用id')),
                ('media', models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='easypush.appmediastoragemodel', verbose_name='媒体id')),
            ],
            options={
                'db_table': 'easypush_app_message_info',
            },
        ),
        migrations.AddField(
            model_name='appmediastoragemodel',
            name='app',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='app', to='easypush.apptokenplatformmodel', verbose_name='应用id'),
        ),
    ]