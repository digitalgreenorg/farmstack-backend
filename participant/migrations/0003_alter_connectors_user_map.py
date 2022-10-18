# Generated by Django 4.0.5 on 2022-08-11 19:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datahub', '0001_initial'),
        ('participant', '0002_alter_connectors_user_map'),
    ]

    operations = [
        migrations.AlterField(
            model_name='connectors',
            name='user_map',
            field=models.ForeignKey(blank=True, default='', on_delete=django.db.models.deletion.PROTECT, to='datahub.userorganizationmap'),
        ),
    ]
