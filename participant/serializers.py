from accounts import models
from accounts.serializers import UserSerializer
from datahub.models import Organization, UserOrganizationMap
from datahub.serializers import (
    OrganizationRetriveSerializer,
    UserOrganizationMapSerializer,
)
from rest_framework import serializers

from participant.models import SupportTicket


class TicketSupportSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = SupportTicket
        fields = "__all__"


class ParticipantSupportTicketSerializer(serializers.ModelSerializer):

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(),
        required=True,
        source="user_map.user",
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source="user_map.organization",
    )
    user = UserSerializer(read_only=False, required=False, allow_null=True, source="user_map.user")
    organization = OrganizationRetriveSerializer(
        required=False,
        allow_null=True,
        read_only=True,
        source="user_map.organization",
    )

    class Meta:
        model = SupportTicket
        exclude = ["created_at", "updated_at"]
