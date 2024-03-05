import json
import logging
import os
import re
import secrets
import shutil
import string
import uuid
from urllib.parse import quote
from django.core.files.base import ContentFile

import plazy
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import URLValidator
from django.db.models import Count, Prefetch, Q
from django.utils.translation import gettext as _
from requests import Response
from rest_framework import serializers, status

from accounts import models
from accounts.models import User, UserRole
from accounts.serializers import (
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
)
from core.constants import Constants
from participant.models import (
    DatahubDocuments,
    DatasetV2,
    DatasetV2File,
    Organization,
    Resource,
    ResourceFile,
    ResourceUsagePolicy,
    StandardisationTemplate,
    UserOrganizationMap,
)

from datasets.models import Datasets


# TODO - REMOVED IMOPORT TO CONNECTOR MODEL TO AVOID CIRCULAR IMPORT
from participant.models import SupportTicket
from utils.custom_exceptions import NotFoundException
from utils.embeddings_creation import VectorDBBuilder
from utils.file_operations import create_directory, move_directory
from utils.string_functions import check_special_chars
from utils.validators import (
    validate_dataset_size,
    validate_dataset_type,
    validate_document_type,
    validate_file_size,
    validate_image_type,
)
from utils.youtube_helper import get_youtube_url

from participant.models import (  # Conversation,
    Category,
    DatasetSubCategoryMap,
    LangchainPgCollection,
    LangchainPgEmbedding,
    Messages,
    Policy,
    ResourceSubCategoryMap,
    SubCategory,
    UsagePolicy,
)


class DatasetSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    def validate_sample_dataset(self, value):
        """
        Validator function to check the file size limit.
        """
        MAX_FILE_SIZE = (
            Constants.MAX_PUBLIC_FILE_SIZE if self.initial_data.get("is_public") else Constants.MAX_FILE_SIZE
        )
        filesize = value.size
        if filesize > MAX_FILE_SIZE:
            raise ValidationError(
                _("You cannot upload a file more than %(value)s MB"),
                params={"value": MAX_FILE_SIZE / 1048576},
            )
        return value

    class Meta:
        """_summary_"""

        model = Datasets
        fields = [
            "user_map",
            "name",
            "description",
            "category",
            "geography",
            "crop_detail",
            "constantly_update",
            "dataset_size",
            "connector_availability",
            "age_of_date",
            "sample_dataset",
            "data_capture_start",
            "data_capture_end",
            "remarks",
            "is_enabled",
            "approval_status",
            "is_public",
        ]


class DatahubDatasetsSerializer(serializers.ModelSerializer):
    class OrganizationDatsetsListRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = [
                "org_email",
                "org_description",
                "name",
                "logo",
                "address",
                "phone_number",
            ]

    class UserDatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["last_name", "first_name", "email", "on_boarded_by"]

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source="user_map.organization",
    )

    organization = OrganizationDatsetsListRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )
    user = UserDatasetSerializer(required=False, allow_null=True, read_only=True, source="user_map.user")

    class Meta:
        model = Datasets
        fields = Constants.ALL


class DatasetUpdateSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Datasets
        fields = Constants.ALL