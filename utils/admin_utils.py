# utils.py

from core.utils import LOGGER
from rest_framework import status
from rest_framework.response import Response
from accounts.models import User
from datahub.models import UserOrganizationMap, Organization
from datahub.serializers import UserSerializer
from microsite.serializers import OrganizationMicrositeSerializer
from core.constants import Constants

def get_organization_info():
    try:
        datahub_admin = User.objects.filter(role_id=1)

        if not datahub_admin:
            return "https://dev-vistaar.digitalgreen.org/static/media/vistaar_logo.e5fe6066.svg"

        user_queryset = datahub_admin.first()
        user_org_queryset = UserOrganizationMap.objects.prefetch_related(
            Constants.USER, Constants.ORGANIZATION
        ).filter(user=user_queryset.id)

        if not user_org_queryset:
            return "https://dev-vistaar.digitalgreen.org/static/media/vistaar_logo.e5fe6066.svg"

        org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
        org_serializer = OrganizationMicrositeSerializer(org_obj)
        return "https://dev-vistaar.digitalgreen.org" + org_serializer.data.get('logo')

    except Exception as error:
        LOGGER.error(f"Error occurred in get_organization_info ERROR: {error}", exc_info=True)
        return {}