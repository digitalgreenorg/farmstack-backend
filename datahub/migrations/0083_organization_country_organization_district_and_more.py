# Generated by Django 4.1.5 on 2024-11-19 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datahub', '0082_resource_district_resource_state_resource_village_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='country',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='organization',
            name='district',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='organization',
            name='state',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='organization',
            name='village',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='resource',
            name='country',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='resource',
            name='district',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='resource',
            name='state',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='resource',
            name='village',
            field=models.JSONField(default=dict),
        ),
    ]
