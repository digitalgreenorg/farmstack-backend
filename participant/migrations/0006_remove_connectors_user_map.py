# Generated by Django 4.1.5 on 2023-10-05 09:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('participant', '0005_alter_supportticketv2_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='connectors',
            name='user_map',
        ),
    ]
