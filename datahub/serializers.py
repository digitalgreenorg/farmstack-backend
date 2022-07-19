import uuid

from accounts import models
from accounts.models import User, UserRole
from accounts.serializers import (
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
)
from rest_framework import serializers
from core.constants import Constants

from datahub.models import DatahubDocuments, Datasets, Organization, UserOrganizationMap
from datahub.models import Organization, UserOrganizationMap, DatahubDocuments

from utils.validators import (
    validate_document_type,
    validate_file_size,
    validate_image_type,
)

from datahub.models import DatahubDocuments, Organization, UserOrganizationMap


class OrganizationRetriveSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        exclude = Constants.EXCLUDE_DATES


class OrganizationSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        exclude = Constants.EXCLUDE_DATES
        # fields = Constants.ALL


class UserOrganizationCreateSerializer(serializers.Serializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    user = UserSerializer(
        read_only=True,
        allow_null=True,
        required=False,
    )
    organization = OrganizationRetriveSerializer(
        read_only=True,
        allow_null=True,
        required=False,
    )

    # class Meta:
    #     """_summary_"""

    # model = UserOrganizationMap
    # fields = [Constants.ORGANIZATION, Constants.USER]
    # exclude = Constants.EXCLUDE_DATES


class UserOrganizationMapSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = UserOrganizationMap
        fields = [Constants.ORGANIZATION, Constants.USER]
        # exclude = Constants.EXCLUDE_DATES


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

    governing_law = serializers.FileField(validators=[validate_file_size, validate_document_type])
    privacy_policy = serializers.FileField(validators=[validate_file_size, validate_document_type])
    tos = serializers.FileField(validators=[validate_file_size, validate_document_type])
    limitations_of_liabilities = serializers.FileField(validators=[validate_file_size, validate_document_type])
    warranty = serializers.FileField(validators=[validate_file_size, validate_document_type])


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
        validators=[validate_file_size, validate_image_type], required=False, allow_null=True
    )
    button_color = serializers.CharField(required=False, allow_null=True)
    email = serializers.EmailField()


class TeamMemberListSerializer(serializers.Serializer):
    """
    Create Team Member Serializer.
    """

    class Meta:
        model = User

    id = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.PrimaryKeyRelatedField(queryset=UserRole.objects.all(), read_only=False)
    profile_picture = serializers.FileField()
    status = serializers.BooleanField()


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """
    Create a Team Member
    """

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role")


class TeamMemberDetailsSerializer(serializers.ModelSerializer):
    """
    Details of a Team Member
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    """
    Update Team Member
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")




class DatasetSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Datasets
        fields = Constants.ALL


class DatahubDatasetsDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), allow_null=True, required=False, source="user_map.organization"
    )
    user = UserSerializer(
        read_only=False,
        required=False,
        allow_null=True,
        source="user_map.user",
    )
    organization = OrganizationRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )

    class Meta:
        model = Datasets
        exclude = Constants.EXCLUDE_DATES


class DatahubDatasetsSerializer(serializers.ModelSerializer):
    class OrganizationDatsetsListRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["org_email", "org_description", "name", "logo"]

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), allow_null=True, required=False, source="user_map.organization"
    )

    organization = OrganizationDatsetsListRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )

    class Meta:
        model = Datasets
        fields = Constants.ALL
