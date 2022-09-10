import re, datetime, json
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


class ParticipantDatasetsSerializerForEmail(serializers.ModelSerializer):
    class Meta:
        model = Datasets
        fields = ["name", "description", "category", "geography", "crop_detail", "constantly_update", "age_of_date", "data_capture_start", "data_capture_end", "dataset_size", "connector_availability"]

    def to_representation(self, instance):
        """Return formatted data for email template"""
        ret = super().to_representation(instance)
        data = []
        if ret.get("category"):
            for key, value in json.loads(ret.get("category")).items():
                if value == True:
                    data.append(re.sub("_", " ", key).title())
                ret["category"] = data
        else:
            ret["category"] = None

        ret["name"] = ret.get("name").title() if ret.get("name") else None
        ret["crop_detail"] = ret.get("crop_detail").title() if ret.get("crop_detail") else None
        ret["geography"] = ret.get("geography").title() if ret.get("geography") else None
        ret["connector_availability"] = re.sub("_", " ", ret.get("connector_availability")).title() if ret.get("connector_availability") else None

        if ret.get("constantly_update"):
            if ret["constantly_update"] == True:
                ret["constantly_update"] = "Yes"
            elif ret["constantly_update"] == False:
                ret["constantly_update"] = "No"
        else:
            ret["constantly_update"] = None

        if ret.get("data_capture_start"):
            date = ret["data_capture_start"].split("T")[0]
            ret["data_capture_start"] = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            ret["data_capture_start"] = None

        if ret.get("data_capture_end"):
            date = ret["data_capture_end"].split("T")[0]
            ret["data_capture_end"] = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            ret["data_capture_end"] = None

        return ret


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "department_name", "department_discription", "organization"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "project_name", "project_discription", "department"]


class ProjectDepartmentSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(
        read_only=True,
    )

    class Meta:
        model = Project
        fields = ["id", "project_name", "project_discription", "department"]


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
    organization_details= OrganizationConnectorSerializer(required=False, allow_null=True, read_only=True, source="user_map.organization")
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), allow_null=True, required=False, source="user_map.user"
    )

    class Meta:
        model = Connectors
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL

class ConnectorsMapProviderRetriveSerializer(serializers.ModelSerializer):
    class DatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = Datasets
            fields = ["id", "name", "description"]
    class OrganizationConnectorSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "name", "website"]
    department_details = DepartmentSerializer(
        required=False, allow_null=True, read_only=True, source="provider.project.department"
    )
    project_details = ProjectSerializer(required=False, allow_null=True, read_only=True, source="provider.project")
    dataset_details = DatasetSerializer(required=False, allow_null=True, read_only=True, source="provider.dataset")
    organization_details= OrganizationConnectorSerializer(required=False, allow_null=True, read_only=True, source="provider.user_map.organization")
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), allow_null=True, required=False, source="provider.user_map.user"
    )
    connector_details = ConnectorsSerializer(required=False, allow_null=True, read_only=True, source="provider")
    class Meta:
        model = ConnectorsMap
        # exclude = Constants.EXCLUDE_DATES
        fields = Constants.ALL

class ConnectorsMapConsumerRetriveSerializer(serializers.ModelSerializer):
    class DatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = Datasets
            fields = ["id", "name", "description"]
    class OrganizationConnectorSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "name", "website"]
    department_details = DepartmentSerializer(
        required=False, allow_null=True, read_only=True, source="consumer.project.department"
    )
    project_details = ProjectSerializer(required=False, allow_null=True, read_only=True, source="consumer.project")
    dataset_details = DatasetSerializer(required=False, allow_null=True, read_only=True, source="consumer.dataset")
    organization_details= OrganizationConnectorSerializer(required=False, allow_null=True, read_only=True, source="consumer.user_map.organization")
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), allow_null=True, required=False, source="consumer.user_map.user"
    )
    connector_details = ConnectorsSerializer(required=False, allow_null=True, read_only=True, source="consumer")

    class Meta:
        model = ConnectorsMap
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
