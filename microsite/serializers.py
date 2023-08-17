import json
import os

import pandas as pd
from rest_framework import serializers

from accounts.models import User
from connectors.models import Connectors, ConnectorsMap
from core import settings
from core.utils import Constants
from datahub.models import DatahubDocuments, Datasets, DatasetV2, Organization, Policy
from datahub.serializers import DatasetV2FileSerializer


class OrganizationMicrositeSerializer(serializers.ModelSerializer):
    """Organization Serializer for microsite"""

    class Meta:
        """_summary_"""

        model = Organization
        exclude = ["created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    """User serializer for Datasets of microsite"""

    class Meta:
        """_summary_"""

        model = User
        fields = ["first_name", "last_name", "email", "phone_number"]


class DatasetsMicrositeSerializer(serializers.ModelSerializer):
    """Datasets Serializer for microsite"""

    user = UserSerializer(
        read_only=False,
        required=False,
        allow_null=True,
        source="user_map.user",
    )
    organization = OrganizationMicrositeSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )

    class Meta:
        """_summary_"""

        model = Datasets
        exclude = ["user_map"]


class ContactFormSerializer(serializers.Serializer):
    """Contact Form serilizer for microsite guest users or visitors"""

    # SUBJECT_CHOICES = (("Become a Participant", "become_participant"), ("Other queries", "other_queries"))
    # subject = serializers.ChoiceField(choices=SUBJECT_CHOICES)

    first_name = serializers.CharField()
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField()
    contact_number = serializers.CharField()
    subject = serializers.CharField(required=False)
    describe_query = serializers.CharField()


class UserDataMicrositeSerializer(serializers.ModelSerializer):
    class Meta:
        """_summary_"""

        model = User
        fields = ["id", "role_id", "on_boarded"]


class LegalDocumentSerializer(serializers.ModelSerializer):
    """Legal DocumentSerializer class"""

    governing_law = serializers.CharField()
    privacy_policy = serializers.CharField()
    tos = serializers.CharField()
    limitations_of_liabilities = serializers.CharField()
    warranty = serializers.CharField()

    class Meta:
        model = DatahubDocuments
        fields = Constants.ALL


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = Constants.ALL

class ConnectorsMapSerializer(serializers.ModelSerializer):
    left_dataset_file = DatasetV2FileSerializer(read_only=True, allow_null=True)
    right_dataset_file = DatasetV2FileSerializer(read_only=True, allow_null=True)
    class Meta:
        model = ConnectorsMap
        exclude = ["created_at", "updated_at"]



class ConnectorsListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Connectors
        exclude = ["integrated_file","created_at", "updated_at", "config"]
    
    dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
    providers_count = serializers.SerializerMethodField(method_name="get_providers_count")

    def get_dataset_count(self, connectors):
        count = ConnectorsMap.objects.filter(connectors=connectors.id).count()
        return  count+1 if count else 0
    
    def get_providers_count(self, connectors):
        query = ConnectorsMap.objects.select_related('left_dataset_file_id__dataset', 'right_dataset_file_id__dataset').filter(connectors=connectors.id).filter(connectors=connectors.id)
        count = query.distinct("left_dataset_file_id__dataset__user_map", "right_dataset_file_id__dataset__user_map").count()
        return count
    
class DatasetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetV2
        exclude = ["created_at", "updated_at"]


class ConnectorsRetriveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Connectors
        fields = Constants.ALL

    dataset_and_organizations = serializers.SerializerMethodField(method_name="datasets_data") # type: ignore

    def datasets_data(self, organizations):
        organizations_query = ConnectorsMap.objects.filter(connectors_id=organizations.id).select_related(
            'left_dataset_file__dataset__user_map__organization',
            'right_dataset_file__dataset__user_map__organization'
        )
        datasets =  organizations_query.values_list(
            'left_dataset_file__dataset',
            'right_dataset_file__dataset'
        ).distinct()
        organizations = organizations_query.values_list(
            'left_dataset_file__dataset__user_map__organization',
            'right_dataset_file__dataset__user_map__organization'
        ).distinct()
        data = Organization.objects.all().filter(id__in = organizations[0])
        searilezer = OrganizationMicrositeSerializer(data, many=True)
        dataset_data = DatasetV2.objects.all().filter(id__in = datasets[0])
        dataset_searilezer = DatasetsSerializer(dataset_data, many=True)
        return {"organizations": searilezer.data, "datasets": dataset_searilezer.data}
      
    