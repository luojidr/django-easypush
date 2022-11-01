# Generated by Django 4.1.2 on 2022-11-01 07:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('easypush', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='media',
        ),
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='msg_extra_json',
        ),
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='msg_media',
        ),
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='msg_pc_url',
        ),
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='msg_text',
        ),
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='msg_title',
        ),
        migrations.RemoveField(
            model_name='appmessagemodel',
            name='msg_url',
        ),
        migrations.AddField(
            model_name='appmessagemodel',
            name='msg_body_json',
            field=models.CharField(blank=True, default='', max_length=2000, verbose_name='消息JSON数据'),
        ),
        migrations.AddField(
            model_name='appmessagemodel',
            name='remark',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='说明'),
        ),
        migrations.AddField(
            model_name='appmsgpushrecordmodel',
            name='msg_type',
            field=models.CharField(blank=True, choices=[('text', '文本消息'), ('image', '图片消息'), ('voice', '语音消息'), ('file', '文件消息'), ('news', '图文消息'), ('mpnews', '图文消息'), ('markdown', 'markdown 消息'), ('textcard', '文本卡片消息'), ('miniprogram_notice', '小程序通知消息'), ('template_card', '模板卡片消息'), ('text', '文本消息'), ('image', '图片消息'), ('voice', '语音消息'), ('file', '文件消息'), ('link', '链接消息'), ('oa', 'OA 消息'), ('markdown', 'markdown 消息'), ('action_card', 'action_card 消息'), ('single_action_card', 'action_card 消息'), ('btn_action_card', 'action_card 消息')], default=0, max_length=50, verbose_name='消息类型'),
        ),
        migrations.AlterField(
            model_name='appmediastoragemodel',
            name='access_token',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='共享token'),
        ),
        migrations.AlterField(
            model_name='appmessagemodel',
            name='app',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='easypush.apptokenplatformmodel', verbose_name='应用id'),
        ),
        migrations.AlterField(
            model_name='appmessagemodel',
            name='msg_type',
            field=models.CharField(blank=True, choices=[('text', '文本消息'), ('image', '图片消息'), ('voice', '语音消息'), ('file', '文件消息'), ('news', '图文消息'), ('mpnews', '图文消息'), ('markdown', 'markdown 消息'), ('textcard', '文本卡片消息'), ('miniprogram_notice', '小程序通知消息'), ('template_card', '模板卡片消息'), ('text', '文本消息'), ('image', '图片消息'), ('voice', '语音消息'), ('file', '文件消息'), ('link', '链接消息'), ('oa', 'OA 消息'), ('markdown', 'markdown 消息'), ('action_card', 'action_card 消息'), ('single_action_card', 'action_card 消息'), ('btn_action_card', 'action_card 消息')], default=0, max_length=50, verbose_name='消息类型'),
        ),
    ]
