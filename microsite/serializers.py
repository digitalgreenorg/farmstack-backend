from accounts.models import User, UserRole
from datahub.models import Organization, Datasets
from rest_framework import serializers


class OrganizationMicrositeSerializer(serializers.ModelSerializer):
    """Organization Serializer for microsite"""
    class Meta:
        """_summary_"""
        model = Organization
        exclude = ["id", "status", "created_at", "updated_at"]


class DatasetsMicrositeSerializer(serializers.ModelSerializer):
    """Datasets Serializer for microsite"""
    class Meta:
        """_summary_"""
        model = Datasets
        exclude = ["id", "user_map", "created_at", "updated_at"]
