import logging

from rest_framework import serializers

from accounts import models
from accounts.models import User, UserRole
from accounts.serializers import (
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
)
from core.constants import Constants
from datahub.models import DatahubDocuments, Datasets, Organization, UserOrganizationMap
from participant.models import Connectors, SupportTicket
from utils.validators import (
    validate_document_type,
    validate_file_size,
    validate_image_type,
)

LOGGER = logging.getLogger(__name__)


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
        fields = Constants.ALL
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

    dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
    connector_count = serializers.SerializerMethodField(method_name="get_connector_count")

    def get_dataset_count(self, user_org_map):
        return Datasets.objects.filter(status=True, user_map__user=user_org_map.user.id).count()

    def get_connector_count(self, user_org_map):
        return Connectors.objects.filter(status=True, user_map__user=user_org_map.user.id).count()


class DropDocumentSerializer(serializers.Serializer):
    """DropDocumentSerializer class"""

    governing_law = serializers.FileField(validators=[validate_file_size, validate_document_type])
    privacy_policy = serializers.FileField(validators=[validate_file_size, validate_document_type])
    tos = serializers.FileField(validators=[validate_file_size, validate_document_type])
    limitations_of_liabilities = serializers.FileField(validators=[validate_file_size, validate_document_type])
    warranty = serializers.FileField(validators=[validate_file_size, validate_document_type])


class PolicyDocumentSerializer(serializers.ModelSerializer):
    """PolicyDocumentSerializer class"""

    governing_law = serializers.CharField()
    privacy_policy = serializers.CharField()
    tos = serializers.CharField()
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
    # email = serializers.EmailField()


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
    on_boarded = serializers.BooleanField()


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """
    Create a Team Member
    """

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role", "on_boarded")


class TeamMemberDetailsSerializer(serializers.ModelSerializer):
    """
    Details of a Team Member
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "on_boarded")


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    """
    Update Team Member
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "on_boarded")


class DatasetSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

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


class DatasetUpdateSerializer(serializers.ModelSerializer):
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
            fields = ["org_email", "org_description", "name", "logo", "address", "phone_number"]

    class UserDatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["last_name", "first_name", "email"]

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), allow_null=True, required=False, source="user_map.organization"
    )

    organization = OrganizationDatsetsListRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )
    user = UserDatasetSerializer(required=False, allow_null=True, read_only=True, source="user_map.user")

    class Meta:
        model = Datasets
        fields = Constants.ALL


class RecentSupportTicketSerializer(serializers.ModelSerializer):
    class OrganizationRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "org_email", "name"]

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["id", "first_name", "last_name", "email", "role"]

    organization = OrganizationRetriveSerializer(
        allow_null=True, required=False, read_only=True, source="user_map.organization"
    )

    user = UserSerializer(allow_null=True, required=False, read_only=True, source="user_map.user")

    class Meta:
        model = SupportTicket
        fields = ["id", "subject", "category", "updated_at", "organization", "user"]


# class RecentConnectorListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Connectors
#         fields = ["id", "connector_name", "updated_at", "dataset_count", "activity"]
#
#     dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
#     activity = serializers.SerializerMethodField(method_name="get_activity")
#
#     def get_dataset_count(self, connectors_queryset):
#         return Datasets.objects.filter(status=True, user_map__user=connectors_queryset.user_map.user_id).count()
#
#     def get_activity(self, connectors_queryset):
#         try:
#             if Connectors.objects.filter(status=True, user_map__id=connectors_queryset.user_map.id).first().status == True:
#                 return Constants.ACTIVE
#             else:
#                 return Constants.NOT_ACTIVE
#         except Exception as error:
#             LOGGER.error(error, exc_info=True)
#
#         return None


class RecentDatasetListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasets
        fields = ["id", "name", "updated_at", "connector_count", "activity"]

    connector_count = serializers.SerializerMethodField(method_name="get_connector_count")
    activity = serializers.SerializerMethodField(method_name="get_activity")

    def get_connector_count(self, datasets_queryset):
        return Connectors.objects.filter(status=True, dataset_id=datasets_queryset.id).count()

    def get_activity(self, datasets_queryset):
        try:
            datasets_queryset = Datasets.objects.filter(status=True, id=datasets_queryset.id)
            if datasets_queryset:
                if datasets_queryset.first().status == True:
                    return Constants.ACTIVE
                else:
                    return Constants.NOT_ACTIVE
            else:
                return Constants.NOT_ACTIVE
        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return None
