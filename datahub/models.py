from django.db import models
from django.conf import settings

class Organization(models.Model):
    """ Organization model """
    IS_ACTIVE = 1
    IS_INACTIVE = 0
    STATUSES = [(IS_ACTIVE, 'is_active'),
            (IS_INACTIVE, 'is_inactive')
        ]

    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    address = models.JSONField()
    phone_number = models.CharField(max_length=50)
    logo = models.CharField(max_length=500, null=True, blank=True)
    hero_image = models.CharField(max_length=500, null=True, blank=True)
    website = models.CharField(max_length=255)
    status = models.CharField(max_length=10,
                            choices=STATUSES,
                            default=IS_ACTIVE)


class UserOrganizationMap(models.Model):
    """ UserOrganizationMap model """
    id = models.UUIDField(primary_key=True)
    user_id = models.UUIDField(settings.AUTH_USER_MODEL)
    organization_id = models.UUIDField(Organization)

