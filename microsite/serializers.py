import json
import os

import pandas as pd
from rest_framework import serializers

from accounts.models import User
from connectors.models import Connectors, ConnectorsMap
from connectors.serializers import OrganizationRetriveSerializer
from core import settings
from core.utils import Constants
from datahub.models import (
    DatahubDocuments,
    Datasets,
    DatasetV2,
    Organization,
    Policy,
    Resource,
    ResourceFile,
    UserOrganizationMap,
)
from datahub.serializers import DatasetV2FileSerializer

from .models import FeedBack


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
        exclude = ["integrated_file","config"]
    
    dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
    providers_count = serializers.SerializerMethodField(method_name="get_providers_count")

    def get_dataset_count(self, connectors):
        count = ConnectorsMap.objects.filter(connectors=connectors.id).count()
        return  count+1 if count else 0
    
    def get_providers_count(self, connectors):
        query = ConnectorsMap.objects.select_related('left_dataset_file_id__dataset', 'right_dataset_file_id__dataset').filter(connectors=connectors.id)
        user_map_ids = list(query.values_list("left_dataset_file_id__dataset__user_map").distinct())
        user_map_ids.extend(list(query.values_list("right_dataset_file_id__dataset__user_map").distinct()))
        count= len(set(user_map_ids))
        return count
    
class DatasetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetV2
        exclude = ["updated_at"]
        
class ParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
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
    organization = OrganizationMicrositeSerializer(
        required=False,
        allow_null=True,
        read_only=True,
    )
    class Meta:
        model = UserOrganizationMap
        exclude = Constants.EXCLUDE_DATES

class ConnectorsRetriveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Connectors
        fields = Constants.ALL

    dataset_and_organizations = serializers.SerializerMethodField(method_name="datasets_data") # type: ignore

    def datasets_data(self, connoctors):
        dastaset_query = ConnectorsMap.objects.filter(connectors_id=connoctors.id).select_related(
            'left_dataset_file__dataset',
            'right_dataset_file__dataset',
        )
        datasets =  dastaset_query.values_list(
            'left_dataset_file__dataset',
            'right_dataset_file__dataset'
        ).distinct()
        organizations = dastaset_query.values_list(
            'left_dataset_file__dataset__user_map__organization',
            'right_dataset_file__dataset__user_map__organization'
        ).distinct()
        organization_ids = list(set([id for tuples in organizations for id in tuples]))
        dataset_ids = list(set([id for tuples in datasets for id in tuples]))

        data = UserOrganizationMap.objects.select_related("user", "organization").all().filter(organization_id__in=organization_ids).distinct()
        searilezer = ParticipantSerializer(data, many=True)
        dataset_data = DatasetV2.objects.all().filter(id__in = dataset_ids).distinct()
        dataset_searilezer = DatasetsSerializer(dataset_data, many=True)
        return {"organizations": searilezer.data, "datasets": dataset_searilezer.data}
      
class DatahubDatasetFileDashboardFilterSerializer(serializers.Serializer):
    county = serializers.ListField(allow_empty=False, required=True)
    sub_county = serializers.ListField(allow_empty=False, required=False)
    gender = serializers.ListField(allow_empty=False, required=False)
    value_chain = serializers.ListField(allow_empty=False, required=False)


class ContentFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceFile
        fields = ["id", "type", "url", "transcription", "updated_at"]

class ContentSerializer(serializers.ModelSerializer):
    resources = ContentFileSerializer(many=True, read_only=True)
    class Meta:
        model = Resource
        fields = ["id", "title", "description", "category", "resources"]

class FeedBackSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedBack
        fields = '__all__'
