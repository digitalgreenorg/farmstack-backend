from accounts import models
from accounts.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from core.constants import Constants

from datahub.models import DatahubDocuments, Organization, UserOrganizationMap
from datahub.models import Organization, UserOrganizationMap, DatahubDocuments
from utils.validators import (
    validate_file_size,
    validate_document_type,
    validate_image_type,
)


class OrganizationSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        fields = Constants.ALL


class OrganizationRetriveSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        exclude = Constants.EXCLUDE_DATES


class UserOrganizationMapSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = UserOrganizationMap
        fields = [Constants.ORGANIZATION, Constants.USER]


class ParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(),
        required=True,
        source=Constants.USER,
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source=Constants.ORGANIZATION,
    )

    user = UserSerializer(
        read_only=False,
        required=False,
    )
    organization = OrganizationRetriveSerializer(
        required=False,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = UserOrganizationMap
        exclude = Constants.EXCLUDE_DATES


class DropDocumentSerializer(serializers.Serializer):
    """DropDocumentSerializer class"""

    governing_law = serializers.FileField(
        validators=[validate_file_size, validate_document_type]
    )
    privacy_policy = serializers.FileField(
        validators=[validate_file_size, validate_document_type]
    )
    tos = serializers.FileField(validators=[validate_file_size, validate_document_type])
    limitations_of_liabilities = serializers.FileField(
        validators=[validate_file_size, validate_document_type]
    )
    warranty = serializers.FileField(
        validators=[validate_file_size, validate_document_type]
    )


class PolicyDocumentSerializer(serializers.ModelSerializer):
    """PolicyDocumentSerializer class"""

    privacy_policy = serializers.CharField()
    tos = serializers.CharField()
    governing_law = serializers.CharField()
    limitations_of_liabilities = serializers.CharField()
    warranty = serializers.CharField()

    class Meta:
        model = DatahubDocuments
        fields = Constants.ALL


class DatahubThemeSerializer(serializers.Serializer):
    """DatahubThemeSerializer class"""

    banner = serializers.ImageField(
        validators=[validate_file_size, validate_image_type]
    )
    file = serializers.ImageField(validators=[validate_file_size, validate_image_type])
    button_color = serializers.CharField()
