from accounts.models import User
from datahub.models import Organization, Datasets
from rest_framework import serializers


class OrganizationMicrositeSerializer(serializers.ModelSerializer):
    """Organization Serializer for microsite"""
    class Meta:
        """_summary_"""
        model = Organization
        exclude = ["id", "created_at", "updated_at"]


class UserDatasetSerializer(serializers.ModelSerializer):
    """User serializer for Datasets of microsite"""
    class Meta:
        """_summary_"""
        model = User
        fields = ["first_name", "email", "phone_number"]

class DatasetsMicrositeSerializer(serializers.ModelSerializer):
    """Datasets Serializer for microsite"""
    user = UserDatasetSerializer(
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
        exclude = ["user_map", "created_at", "updated_at"]
