# Generated by Django 4.1.5 on 2023-12-18 04:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datahub", "0057_alter_resourcefile_transcription"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resourcefile",
            name="transcription",
            field=models.CharField(blank=True, max_length=10000, null=True),
        ),
        migrations.AlterField(
            model_name="resourcefile",
            name="type",
            field=models.CharField(
                choices=[("youtube", "youtube"), ("pdf", "pdf"), ("file", "file")],
                max_length=20,
                null=True,
            ),
        ),
    ]
