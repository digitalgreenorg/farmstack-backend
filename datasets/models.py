from django.db import models
import os
import uuid
from datetime import timedelta
from email.mime import application

from django.conf import settings
from django.core.files.storage import Storage
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField

from accounts.models import User
from core.base_models import TimeStampMixin
from core.constants import Constants
from participant.models import UserOrganizationMap
from utils.validators import (
    validate_25MB_file_size,
    validate_file_size,
    validate_image_type,
)


APPROVAL_STATUS = (
    ("approved", "approved"),
    ("rejected", "rejected"),
    ("for_review", "for_review"),
)

def auto_str(cls):
    def __str__(self):
        return "%s" % (", ".join("%s=%s" % item for item in vars(self).items()))

    cls.__str__ = __str__
    return cls

# Create your models here.
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