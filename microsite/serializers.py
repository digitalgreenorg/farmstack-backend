from core.utils import Constants
from accounts.models import User
from datahub.models import Organization, Datasets, DatahubDocuments, Policy
from rest_framework import serializers


class OrganizationMicrositeSerializer(serializers.ModelSerializer):
    """Organization Serializer for microsite"""

    class Meta:
        """_summary_"""

        model = Organization
        exclude = ["id", "created_at", "updated_at"]


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
