from accounts import models
from rest_framework import serializers

from datahub.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    class Meta:
        """_summary_
        """
        model = Organization
        fields = ["email", "name", "hero_image", "address", "logo", "phone_number", "website"]
        