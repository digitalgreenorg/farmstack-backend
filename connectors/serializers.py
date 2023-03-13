from rest_framework import serializers

from accounts.models import User
from connectors.models import Connectors, ConnectorsMap
from datahub.models import DatasetV2, DatasetV2File, Organization, UserOrganizationMap
from datahub.serializers import DatasetV2FileSerializer


class OrganizationRetriveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "org_email",
            "org_description",
            "name",
        ]

class UserOrganizationMapSerializer(serializers.ModelSerializer):
    organization = OrganizationRetriveSerializer(read_only=True, allow_null=True)
    class Meta:
        model = UserOrganizationMap
        exclude = ["created_at", "updated_at"]


class DatasetSerializerSerializr(serializers.ModelSerializer):
    user_map = UserOrganizationMapSerializer(read_only=True, allow_null=True)
    class Meta:
        model = DatasetV2
        fields = ["name", "description", "user_map"]

class DatasetV2FileSerializer(serializers.ModelSerializer):
    dataset = DatasetSerializerSerializr(read_only=True,  allow_null=True)
    class Meta:
        model = DatasetV2File
        exclude = ["created_at", "updated_at"]


class ConnectorsMapSerializer(serializers.ModelSerializer):
    left_dataset_file = DatasetV2FileSerializer(read_only=True, allow_null=True)
    right_dataset_file = DatasetV2FileSerializer(read_only=True, allow_null=True)
    class Meta:
        model = ConnectorsMap
        exclude = ["created_at", "updated_at"]


class ConnectorsSerializer(serializers.ModelSerializer):
    maps = ConnectorsMapSerializer(many=True, source='connectorsmap_set')
    class Meta:
        model = Connectors
        exclude = ["created_at", "updated_at"]

class ConnectorsCreateSerializer(serializers.ModelSerializer):
   class Meta:
        model = Connectors
        exclude = ["created_at", "updated_at"]


class ConnectorsMapCreateSerializer(serializers.ModelSerializer):
   class Meta:
        model = ConnectorsMap
        exclude = ["created_at", "updated_at"]