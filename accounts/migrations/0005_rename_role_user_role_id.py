# Generated by Django 4.0.5 on 2022-06-07 03:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_userrole_id_alter_userrole_role_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='role',
            new_name='role_id',
        ),
    ]
