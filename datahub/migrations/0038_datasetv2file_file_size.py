# Generated by Django 4.1.5 on 2023-04-23 14:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("datahub", "0037_alter_datasetv2file_source_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasetv2file",
            name="file_size",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
