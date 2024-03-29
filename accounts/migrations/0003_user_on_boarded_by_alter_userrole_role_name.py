
# Generated by Django 4.1.5 on 2023-02-10 11:52


from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_approval_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="on_boarded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="userrole",
            name="role_name",
            field=models.CharField(
                choices=[
                    ("datahub_admin", "datahub_admin"),
                    ("datahub_team_member", "datahub_team_member"),
                    ("datahub_participant_root", "datahub_participant_root"),
                    ("datahub_participant_team", "datahub_participant_team"),
                    ("datahub_guest_user", "datahub_guest_user"),
                    ("datahub_co_steward", "datahub_co_steward"),
                ],
                max_length=255,
            ),
        ),
    ]
