# Generated by Django 4.0.5 on 2023-04-11 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datahub', '0029_merge_20230411_1049'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetv2',
            name='category',
            field=models.JSONField(default=dict),
        ),
    ]
