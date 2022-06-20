import uuid

from accounts.models import User

# from utils.validators import validate_file_size
from django.conf import settings
from django.db import models
from utils.validators import validate_file_size

from datahub.base_models import TimeStampMixin


def auto_str(cls):
    def __str__(self):
        return "%s" % (", ".join("%s=%s" % item for item in vars(self).items()))

    cls.__str__ = __str__
    return cls


@auto_str
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
        upload_to=settings.ORGANIZATION_IMAGES_URL, null=True, blank=True, validators=[validate_file_size]
    )
    hero_image = models.FileField(
        upload_to=settings.ORGANIZATION_IMAGES_URL, null=True, blank=True, validators=[validate_file_size]
    )
    website = models.CharField(max_length=255, null=True, blank=True)
    status = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class UserOrganizationMap(TimeStampMixin):
    """UserOrganizationMap model for mapping User and Organization model"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
