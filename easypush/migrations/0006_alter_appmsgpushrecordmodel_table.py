# Generated by Django 4.1.2 on 2022-11-11 16:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('easypush', '0005_alter_appmediastoragemodel_expire_time_and_more'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='appmsgpushrecordmodel',
            table='easypush_app_msg_push_log',
        ),
    ]
