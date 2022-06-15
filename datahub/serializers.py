from accounts import models
from rest_framework import serializers

from datahub.models import Organization, UserOrganizationMap, DatahubDocuments


class OrganizationSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        fields = [
            "org_email",
            "name",
            "hero_image",
            "address",
            "logo",
            "phone_number",
            "website",
        ]


class UserOrganizationMapSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = UserOrganizationMap
        fields = ["organization_id", "user_id"]


class PolicyDocumentSerializer(serializers.ModelSerializer):
    """PolicyDocumentSerializer class"""
    privacy_policy = serializers.CharField()
    tos = serializers.CharField()
    governing_law = serializers.CharField()
    limitations_of_liabilities = serializers.CharField()
    warranty = serializers.CharField()

    class Meta:
        model = DatahubDocuments
        fields = "__all__"
