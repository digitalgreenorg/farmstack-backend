# Generated by Django 4.0.5 on 2023-01-04 20:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datahub', '0008_datasetv2file'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datasetv2',
            name='dataset',
        ),
    ]
