# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-05-15 01:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FOSS_Analysis', '0002_auto_20160515_0120'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='path',
            field=models.CharField(max_length=128, unique=True),
        ),
    ]