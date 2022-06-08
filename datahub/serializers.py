from accounts import models
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
        

class UserOrganizationMapSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    class Meta:
        """_summary_
        """
        model = UserOrganizationMap
        fields = ["organization_id", "user_id"]
        