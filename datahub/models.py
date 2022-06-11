import uuid

from django.conf import settings
from django.db import models

from datahub.base_models import TimeStampMixin


class Organization(TimeStampMixin):
    """Organization model

    status:
        active = 1
        inactive = 0
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    org_email = models.CharField(max_length=255, unique=True)
    address = models.JSONField()
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    logo = models.FileField(
        upload_to=settings.ORGANIZATION_IMAGES_URL, null=True, blank=True
    )
    hero_image = models.FileField(
        upload_to=settings.ORGANIZATION_IMAGES_URL, null=True, blank=True
    )
    website = models.CharField(max_length=255, null=True, blank=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserOrganizationMap(TimeStampMixin):
    """UserOrganizationMap model for mapping User and Organization model"""

    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization_id = models.ForeignKey(Organization, on_delete=models.CASCADE)
