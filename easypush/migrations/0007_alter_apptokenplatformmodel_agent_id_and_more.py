# Generated by Django 4.1.2 on 2022-11-11 21:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('easypush', '0006_alter_appmsgpushrecordmodel_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='agent_id',
            field=models.IntegerField(blank=True, default=0, verbose_name='AppId'),
        ),
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='app_key',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='应用 appKey'),
        ),
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='app_name',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='应用名称'),
        ),
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='app_secret',
            field=models.CharField(blank=True, default='', max_length=300, verbose_name='应用 appSecret'),
        ),
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='app_token',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='外部调用的唯一Token'),
        ),
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='corp_id',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='企业corpId'),
        ),
        migrations.AlterField(
            model_name='apptokenplatformmodel',
            name='platform_type',
            field=models.CharField(blank=True, choices=[('sms', '短信'), ('email', '邮件'), ('feishu', '飞书'), ('ding_talk', '钉钉'), ('qy_weixin', '企业微信')], default='', max_length=50, verbose_name='平台类型'),
        ),
    ]
