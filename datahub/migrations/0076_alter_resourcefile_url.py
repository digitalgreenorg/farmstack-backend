# Generated by Django 4.1.5 on 2024-06-25 16:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datahub', '0075_messages_output_resource_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resourcefile',
            name='url',
            field=models.CharField(max_length=2000, null=True),
        ),
    ]