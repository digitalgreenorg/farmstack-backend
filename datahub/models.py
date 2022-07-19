import uuid

from accounts.models import User
from core.base_models import TimeStampMixin

# from utils.validators import validate_file_size
from django.conf import settings
from django.db import models
from utils.validators import validate_file_size


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
        upload_to=settings.ORGANIZATION_IMAGES_URL,
        null=True,
        blank=True,
        validators=[validate_file_size],
    )
    hero_image = models.FileField(
        upload_to=settings.ORGANIZATION_IMAGES_URL,
        null=True,
        blank=True,
        validators=[validate_file_size],
    )
    org_description = models.TextField(max_length=512, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)
    status = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


@auto_str
class DatahubDocuments(models.Model):
    """OrganizationDocuments model"""

    governing_law = models.TextField()
    warranty = models.TextField()
    limitations_of_liabilities = models.TextField()
    privacy_policy = models.TextField()
    tos = models.TextField()


@auto_str
class UserOrganizationMap(TimeStampMixin):
    """UserOrganizationMap model for mapping User and Organization model"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)


CATEGORY = (
    ("crop_data", "crop_data"),
    ("partice_data", "partice_data"),
    ("farmer_profile", "farmer_profile"),
    ("land_records", "land_records"),
    ("research_data", "research_data"),
    ("cultivation_data", "cultivation_data"),
    ("soil_data", "soil_data"),
    ("weather_data", "weather_data"),
)

CONNECTOR_TYPE = (("MYSQL", "MYSQL"), ("MONGODB", "MONDODB"), ("CSV", "CSV"))
APPROVAL_STATUS = (("approved", "approved"), ("in_progress", "in_progress"))
AVAILABLITY = (("available", "available"), ("not_available", "not_available"))


@auto_str
class Datasets(TimeStampMixin):
    """Datasets model of all the users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_map = models.ForeignKey(UserOrganizationMap, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=1000, choices=CATEGORY)
    geography = models.CharField(max_length=255)
    crop_detail = models.CharField(max_length=255, null=True)  # field should update
    constantly_update = models.BooleanField(default=False)
    age_of_date = models.CharField(max_length=255, null=True)
    data_capture_start = models.DateTimeField(null=True)
    data_capture_end = models.DateTimeField(null=True)
    dataset_size = models.CharField(max_length=255, null=True)
    connector_availability = models.CharField(max_length=255, null=True, choices=AVAILABLITY)
    sample_dataset = models.FileField(
        upload_to=settings.SAMPLE_DATASETS_URL,
        blank=True,
        validators=[validate_file_size],
    )
    status = models.BooleanField(default=True)
    approval_status = models.CharField(max_length=255, null=True, choices=APPROVAL_STATUS, default="IN_PROGRESS")
    is_enabled = models.BooleanField(default=True)
    remarks = models.CharField(max_length=1000, null=True)
