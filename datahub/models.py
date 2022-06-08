import uuid
from django.db import models
from django.conf import settings
from datahub.base_models import TimeStampMixin

class Organization(TimeStampMixin):
    """ Organization model """
    IS_ACTIVE = 1
    IS_INACTIVE = 0
    STATUSES = [(IS_ACTIVE, 'is_active'),
            (IS_INACTIVE, 'is_inactive')
        ]

    id = models.UUIDField(primary_key=True,  default=uuid.uuid4,
            editable=False)
    name = models.CharField(max_length=255)
    org_email = models.CharField(max_length=255, unique=True)
    address = models.JSONField()
    phone_number = models.CharField(max_length=50)
    logo = models.CharField(max_length=500, null=True, blank=True)
    hero_image = models.CharField(max_length=500, null=True, blank=True)
    website = models.CharField(max_length=255)
    status = models.CharField(max_length=10,
                            choices=STATUSES,
                            default=IS_ACTIVE)

    def __str__(self):
        return self.name


class UserOrganizationMap(models.Model):
    """ UserOrganizationMap model for mapping User and Organization model """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,
            editable=False)
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization_id = models.ForeignKey(Organization, on_delete=models.CASCADE)
