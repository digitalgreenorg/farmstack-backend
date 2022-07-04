import uuid
from sre_constants import CATEGORY
from unicodedata import category

from accounts.models import User
from core import settings
from core.base_models import TimeStampMixin
from datahub.models import UserOrganizationMap
from django.db import models
from utils.validators import validate_file_size

CATEGORY = (
    ("connectors", "connectors"),
    ("datasets", "datasets"),
    ("others", "others"),
    ("user_accounts", "user_accounts"),
    ("usage_policy", "usage_policy"),
    ("certificate", "certificate"),
)

STATUS = (("open", "open"), ("hold", "hold"), ("closed", "closed"))


def auto_str(cls):
    def __str__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join("%s=%s" % item for item in vars(self).items()),
        )

    cls.__str__ = __str__
    return cls


@auto_str
class SupportTicket(TimeStampMixin):
    """SupportTicket model of all the participant users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_map = models.ForeignKey(UserOrganizationMap, on_delete=models.PROTECT)
    category = models.CharField(max_length=255, null=False, choices=CATEGORY)
    subject = models.CharField(
        max_length=255,
        null=False,
    )
    issue_message = models.CharField(max_length=1000, null=True)
    issue_attachments = models.FileField(
        upload_to=settings.ISSUE_ATTACHEMENT_URL,
        null=True,
        blank=True,
        validators=[validate_file_size],
    )
    soluction_message = models.CharField(max_length=1000, null=True)
    soluction_attachments = models.FileField(
        upload_to=settings.SOLUCTION_ATTACHEMENT_URL,
        null=True,
        blank=True,
        validators=[validate_file_size],
    )
    status = models.CharField(max_length=255, null=False, choices=STATUS)
