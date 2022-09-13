import re, datetime, json
from accounts import models
from accounts.serializers import UserSerializer
from core.constants import Constants
from accounts.models import User
from datahub.models import Datasets, Organization, UserOrganizationMap
from datahub.serializers import (
    OrganizationRetriveSerializer,
    UserOrganizationMapSerializer,
)
from rest_framework import serializers
from utils import string_functions

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
            ret["category"] = "N/A"

        ret["name"] = ret.get("name").title() if ret.get("name") else "N/A"
        ret["crop_detail"] = ret.get("crop_detail").title() if ret.get("crop_detail") else "N/A"
        ret["geography"] = ret.get("geography").title() if ret.get("geography") else "N/A"
        ret["connector_availability"] = re.sub("_", " ", ret.get("connector_availability")).title() if ret.get("connector_availability") else "N/A"
        ret["dataset_size"] = ret.get("dataset_size") if ret.get("dataset_size") else "N/A"
        ret["age_of_date"] = ret.get("age_of_date") if ret.get("age_of_date") else "N/A"

        if ret.get("constantly_update"):
            if ret["constantly_update"] == True:
                ret["constantly_update"] = "Yes"
            elif ret["constantly_update"] == False:
                ret["constantly_update"] = "No"
        else:
            ret["constantly_update"] = "N/A"

        if ret.get("data_capture_start"):
            date = ret["data_capture_start"].split("T")[0]
            ret["data_capture_start"] = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            ret["data_capture_start"] = "N/A"

        if ret.get("data_capture_end"):
            date = ret["data_capture_end"].split("T")[0]
            ret["data_capture_end"] = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            ret["data_capture_end"] = "N/A"

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


class ConnectorsSerializerForEmail(serializers.ModelSerializer):
    class OrganizationSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["org_email", "org_description", "name", "logo", "address"]

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.User
            fields = ["last_name", "first_name", "email"]

    organization = OrganizationSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )

    user = UserSerializer(required=False, allow_null=True, read_only=True, source="user_map.user")

    class Meta:
        model = Connectors
        # fields = ["connector_name", "connector_type", "connector_description", "dataset_name", "participant_org"]
        fields = ["connector_name", "connector_type", "connector_description", "dataset_name", "user", "organization"]

    dataset_name = serializers.SerializerMethodField(method_name="get_dataset_name")
    # participant_org = serializers.SerializerMethodField(method_name="get_participant_org")

    def get_dataset_name(self, connector):
        return Datasets.objects.get(id=connector.dataset_id).name

    # def get_participant_org(self, connector):
    #     connector = Connectors.objects.filter(user_map=connector.user_map)
    #     user_org_map = UserOrganizationMap.objects.get(id=connector.first().user_map.id) if connector else None
    #     participant = User.objects.get(id=user_org_map.user_id) if user_org_map else None
    #     participant_full_name = string_functions.get_full_name(participant.first_name, participant.last_name)
    #     organization = Organization.objects.get(id=user_org_map.organization_id) if user_org_map else None
    #     org_address = string_functions.get_full_address(organization.address) if organization else None

    #     data = {"participant_admin_name": participant_full_name, "organization": organization, "org_address": org_address}
    #     return data


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
