from accounts import models
from accounts.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from datahub.models import Organization, UserOrganizationMap


class OrganizationSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    class Meta:
        """_summary_
        """
        model = Organization
        fields = ["org_email", "name", "hero_image", "address", "logo", "phone_number", "website"]
        

class OrganizationRetriveSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    class Meta:
        """_summary_
        """
        model = Organization
        fields = ["id","org_email", "name", "hero_image", "address", "logo", "phone_number", "website"]


class UserOrganizationMapSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    class Meta:
        """_summary_
        """
        model = UserOrganizationMap
        fields = ["organization", "user"]
        


class ParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(),
        required=True,
        source='user',
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source='organization',
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
        exclude = ["created_at", "updated_at"]
