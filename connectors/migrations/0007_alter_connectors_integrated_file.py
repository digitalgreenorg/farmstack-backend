# Generated by Django 4.1.5 on 2024-07-15 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('connectors', '0006_connectors_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='connectors',
            name='integrated_file',
            field=models.FileField(blank=True, max_length=255, null=True, upload_to='https://.s3.amazonaws.com/connectors/'),
        ),
    ]
