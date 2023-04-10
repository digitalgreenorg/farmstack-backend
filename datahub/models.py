import uuid
from email.mime import application

from django.conf import settings
from django.db import models

from accounts.models import User
from core.base_models import TimeStampMixin
from core.constants import Constants
from utils.validators import (
    validate_25MB_file_size,
    validate_file_size,
    validate_image_type,
)


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
    logo = models.ImageField(
        upload_to=settings.ORGANIZATION_IMAGES_URL,
        null=True,
        blank=True,
        validators=[validate_file_size, validate_image_type],
    )
    hero_image = models.ImageField(
        upload_to=settings.ORGANIZATION_IMAGES_URL,
        null=True,
        blank=True,
        validators=[validate_file_size, validate_image_type],
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
APPROVAL_STATUS = (
    ("approved", "approved"),
    ("rejected", "rejected"),
    ("for_review", "for_review"),
)
USAGE_POLICY_REQUEST_STATUS = (
    ("approved", "approved"),
    ("rejected", "rejected")
)

USAGE_POLICY_APPROVAL_STATUS = (
    ("public", "public"),
    ("registered", "registered"),
    ("private", "private"),
)

@auto_str
class Datasets(TimeStampMixin):
    """Datasets model of all the users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_map = models.ForeignKey(UserOrganizationMap, on_delete=models.PROTECT)
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=500)
    category = models.JSONField()
    geography = models.CharField(max_length=255, blank=True)
    crop_detail = models.CharField(max_length=255, null=True, blank=True)  # field should update
    constantly_update = models.BooleanField(default=False)
    age_of_date = models.CharField(max_length=255, null=True, blank=True)
    data_capture_start = models.DateTimeField(null=True, blank=True)
    data_capture_end = models.DateTimeField(null=True, blank=True)
    dataset_size = models.CharField(max_length=255, null=True, blank=True)
    connector_availability = models.CharField(max_length=255, null=True, blank=True)
    sample_dataset = models.FileField(
        upload_to=settings.SAMPLE_DATASETS_URL,
        blank=True,
    )
    status = models.BooleanField(default=True)
    approval_status = models.CharField(max_length=255, null=True, choices=APPROVAL_STATUS, default="for_review")
    is_enabled = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    remarks = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]


@auto_str
class DatasetV2(TimeStampMixin):
    """
    Stores a single dataset entry, related to :model:`datahub_userorganizationmap` (UserOrganizationMap).
    New version of model for dataset - DatasetV2 to store Meta data of Datasets.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    user_map = models.ForeignKey(UserOrganizationMap, on_delete=models.PROTECT)
    description = models.TextField(max_length=512, null=True, blank=True)
    category = models.JSONField()
    geography = models.CharField(max_length=255, null=True, blank=True)
    data_capture_start = models.DateTimeField(null=True, blank=True)
    data_capture_end = models.DateTimeField(null=True, blank=True)
    constantly_update = models.BooleanField(default=False)
    status = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["name", "category"])]
@auto_str
class StandardisationTemplate(TimeStampMixin):
    """
    Data Standardisation Model.
    datapoint category - Name of the category for a group of attributes
    datapoint attribute - datapoints for each attribute (JSON)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    datapoint_category = models.CharField(max_length=50, unique=True)
    datapoint_description = models.TextField(max_length=255)
    datapoint_attributes = models.JSONField(default = dict)

class Policy(TimeStampMixin):
    """
    Policy documentation Model.
    name - Name of the Policy.
    description - datapoints of each Policy.
    file - file of each policy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=512, unique=False)
    file = models.FileField(
        upload_to=settings.POLICY_FILES_URL,
        validators=[validate_25MB_file_size],
    )


@auto_str
class DatasetV2File(TimeStampMixin):
    """
    Stores a single file (file paths/urls) entry for datasets with a reference to DatasetV2 instance.
    related to :model:`datahub_datasetv2` (DatasetV2)

    `Source` (enum): Enum to store file type
        `file`: dataset of file type
        `mysql`: dataset of mysql connection
        `postgresql`: dataset of postgresql connection
    """

    def dataset_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return "datasets/{0}/{1}".format(instance.dataset.name, filename)

    SOURCES = [
        (Constants.SOURCE_FILE_TYPE, Constants.SOURCE_FILE_TYPE),
        (Constants.SOURCE_MYSQL_FILE_TYPE, Constants.SOURCE_MYSQL_FILE_TYPE),
        (Constants.SOURCE_POSTGRESQL_FILE_TYPE, Constants.SOURCE_POSTGRESQL_FILE_TYPE),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(DatasetV2, on_delete=models.PROTECT, related_name="datasets")
    file = models.FileField(max_length=255, upload_to=dataset_directory_path, null=True, blank=True)
    source = models.CharField(max_length=50, choices=SOURCES)
    standardised_file = models.FileField(max_length=255, upload_to=dataset_directory_path, null=True, blank=True )
    standardised_configuration = models.JSONField(default = dict)
    accessibility = models.CharField(max_length=255, null=True, choices=USAGE_POLICY_APPROVAL_STATUS, default="public")

class UsagePolicy(TimeStampMixin):
    """
    Policy documentation Model.
    datapoint category - Name of the category for a group of attributes
    datapoint attribute - datapoints for each attribute (JSON)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="org")
    dataset_file = models.ForeignKey(DatasetV2File, on_delete=models.CASCADE, related_name="dataset_file")
    approval_status = models.CharField(max_length=255, null=True, choices=USAGE_POLICY_REQUEST_STATUS, default="public")
    accessibility_time =  models.DateField(null=True)

