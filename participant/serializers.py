from accounts import models
from accounts.serializers import UserSerializer
from core.constants import Constants
from datahub.models import Datasets, Organization, UserOrganizationMap
from datahub.serializers import (
    OrganizationRetriveSerializer,
    UserOrganizationMapSerializer,
)
from rest_framework import serializers

from participant.models import (
    Connectors,
    ConnectorsMap,
    Department,
    Project,
    SupportTicket,
)


class TicketSupportSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = SupportTicket
        fields = Constants.ALL


class ParticipantSupportTicketSerializer(serializers.ModelSerializer):

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
        model = SupportTicket
        # exclude = Constants.EXCLUDE_DATES
        fields = "__all__"


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
        ]


class ParticipantDatasetsDetailSerializer(serializers.ModelSerializer):
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


class ParticipantDatasetsSerializer(serializers.ModelSerializer):
    class OrganizationDatsetsListRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["org_email", "org_description", "name", "logo", "address"]

    class UserDatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.User
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
        # exclude = Constants.EXCLUDE_DATES
        fields = [
            "id",
            "name",
            "description",
            "is_enabled",
            "created_at",
            "organization",
            "organization_id",
            "user",
            "user_id",
            "category",
            "geography",
            "crop_detail",
            "age_of_date",
        ]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        exclude = Constants.EXCLUDE_DATES


class DepartmentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "department_name"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        exclude = Constants.EXCLUDE_DATES


class ProjectListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "project_name"]


class ConnectorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Connectors
        fields = Constants.ALL


class ConnectorsListSerializer(serializers.ModelSerializer):

    department_details = DepartmentSerializer(required=False, allow_null=True, read_only=True, source="project.department")
    project_details = ProjectSerializer(required=False, allow_null=True, read_only=True, source="project")

    class Meta:
        model = Connectors
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL


class ConnectorsRetriveSerializer(serializers.ModelSerializer):
    class DatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = Datasets
            fields = ["id", "name", "description"]
    class OrganizationConnectorSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "name", "website"]
    department_details = DepartmentSerializer(
        required=False, allow_null=True, read_only=True, source="project.department"
    )
    project_details = ProjectSerializer(required=False, allow_null=True, read_only=True, source="project")
    dataset_details = DatasetSerializer(required=False, allow_null=True, read_only=True, source="dataset")
    organization_details= OrganizationConnectorSerializer(required=False, allow_null=True, read_only=True, source="dataset.user_map.organization")
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), allow_null=True, required=False, source="dataset.user_map.user"
    )

    class Meta:
        model = Connectors
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL


class ConnectorsConsumerRelationSerializer(serializers.ModelSerializer):
    connectors = ConnectorsSerializer(required=False, allow_null=True, read_only=True, source="consumer")

    class Meta:
        model = ConnectorsMap
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL


class ConnectorsProviderRelationSerializer(serializers.ModelSerializer):
    connectors = ConnectorsSerializer(required=False, allow_null=True, read_only=True, source="provider")

    class Meta:
        model = ConnectorsMap
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL


class ConnectorsMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorsMap
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL

class ParticipantDatasetsDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasets
        fields=["id", "name"]

class ConnectorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Connectors
        fields=["id", "connector_name"]