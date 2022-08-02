from django.shortcuts import render
from accounts.models import User, UserRole
from core.constants import Constants
from datahub.models import Organization, Datasets, UserOrganizationMap
from microsite.serializers import OrganizationMicrositeSerializer, DatasetsMicrositeSerializer
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """
    page_size = 5


class OrganizationMicrositeViewSet(GenericViewSet):
    """Organization viewset for microsite"""

    @action(detail=False, methods=["get"], permission_classes=[])
    def admin_organization(self, request):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        user_obj = User.objects.filter(role_id=1).first()
        user_org_queryset = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user=user_obj.id)
        )

        if not user_org_queryset:
            data = {Constants.ORGANIZATION: None}
            return Response(data, status=status.HTTP_200_OK)

        org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
        user_org_serializer = OrganizationMicrositeSerializer(org_obj)
        data = {Constants.ORGANIZATION: user_org_serializer.data}
        return Response(data, status=status.HTTP_200_OK)


class DatasetsMicrositeViewSet(GenericViewSet):
    """Datasets viewset for microsite"""
    serializer_class = DatasetsMicrositeSerializer
    queryset = Datasets.objects.all()
    pagination_class = DefaultPagination

    def list(self, request):
        """GET method: retrieve a list of dataset objects"""
        page = self.paginate_queryset(self.queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
