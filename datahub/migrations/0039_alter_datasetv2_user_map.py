# Generated by Django 4.0.5 on 2023-04-24 11:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datahub', '0038_datasetv2file_file_size'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetv2',
            name='user_map',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_org_map', to='datahub.userorganizationmap'),
        ),
    ]
