import logging
from core.utils import (
    DefaultPagination,
    CustomPagination,
    Utils,
    csv_and_xlsx_file_validatation,
    date_formater,
    read_contents_from_csv_or_xlsx_file,
)
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from accounts.models import User, UserRole
from core.constants import Constants
from datahub.models import Organization, Datasets, UserOrganizationMap, DatahubDocuments
from microsite.serializers import (
    OrganizationMicrositeSerializer,
    DatasetsMicrositeSerializer,
    ContactFormSerializer,
    UserSerializer,
    LegalDocumentSerializer,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from utils import file_operations

LOGGER = logging.getLogger(__name__)


class OrganizationMicrositeViewSet(GenericViewSet):
    """Organization viewset for microsite"""

    permission_classes = []

    @action(detail=False, methods=["get"])
    def admin_organization(self, request):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        try:
            datahub_admin = User.objects.filter(role_id=1)
            if not datahub_admin:
                data = {Constants.USER: None, "message": ["Datahub admin not Found."]}
                return Response(data, status=status.HTTP_200_OK)

            user_queryset = datahub_admin.first()
            user_serializer = UserSerializer(user_queryset)
            user_org_queryset = UserOrganizationMap.objects.prefetch_related(
                Constants.USER, Constants.ORGANIZATION
            ).filter(user=user_queryset.id)

            if not user_org_queryset:
                data = {
                    Constants.USER: user_serializer.data,
                    Constants.ORGANIZATION: None,
                    "message": ["Datahub admin is not associated with any organization."],
                }
                return Response(data, status=status.HTTP_200_OK)

            org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
            org_seriliazer = OrganizationMicrositeSerializer(org_obj)
            data = {Constants.USER: user_serializer.data, Constants.ORGANIZATION: org_seriliazer.data}
            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatasetsMicrositeViewSet(GenericViewSet):
    """Datasets viewset for microsite"""

    serializer_class = DatasetsMicrositeSerializer
    pagination_class = CustomPagination
    permission_classes = []

    def list(self, request):
        """GET method: retrieve a list of dataset objects"""
        dataset = (
            Datasets.objects.select_related(
                Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION
            )
            .filter(
                Q(user_map__user__status=True, status=True, approval_status="approved")
                | Q(user_map__user__status=True, user_map__user__role_id=1, status=True)
            )
            .order_by(Constants.UPDATED_AT)
            .all()
        )

        page = self.paginate_queryset(dataset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def dataset_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.data
        range = {}
        updated_at__range = request.data.pop(Constants.UPDATED_AT__RANGE, None)
        if updated_at__range:
            range[Constants.UPDATED_AT__RANGE] = date_formater(updated_at__range)
        try:
            data = (
                Datasets.objects.filter(
                    Q(status=True, approval_status="approved", **data, **range)
                    | Q(user_map__user__role_id=1, status=True, **data, **range)
                )
                .order_by(Constants.UPDATED_AT)
                .all()
            )
        except Exception as error:  # type: ignore
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error, exc_info=True)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        page = self.paginate_queryset(data)
        serializer = DatasetsMicrositeSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"])
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        try:
            geography = (
                Datasets.objects.filter(Q(approval_status="approved") | Q(user_map__user__role_id=1))
                .values_list(Constants.GEOGRAPHY, flat=True)
                .distinct()
                .exclude(geography__isnull=True, geography__exact="")
            )
            crop_detail = (
                Datasets.objects.filter(Q(approval_status="approved") | Q(user_map__user__role_id=1))
                .values_list(Constants.CROP_DETAIL, flat=True)
                .distinct()
                .exclude(crop_detail__isnull=True, crop_detail__exact="")
            )

        except Exception as error:  # type: ignore
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error, exc_info=True)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"geography": geography, "crop_detail": crop_detail}, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            data = Datasets.objects.select_related(
                Constants.USER_MAP,
                Constants.USER_MAP_USER,
                Constants.USER_MAP_ORGANIZATION,
            ).filter(
                Q(user_map__user__status=True, status=True, id=pk)
                & (Q(user_map__user__role=1) | Q(user_map__user__role=3))
            )

            serializer = DatasetsMicrositeSerializer(data, many=True)
            if serializer.data:
                data = serializer.data[0]
                data[Constants.CONTENT] = read_contents_from_csv_or_xlsx_file(data.get(Constants.SAMPLE_DATASET))
                return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContactFormViewSet(GenericViewSet):
    """Contact Form for guest users to mail queries or application to become participant on datahub"""

    serializer_class = ContactFormSerializer
    permission_classes = []

    def create(self, request):
        """POST method to create a query and mail it to the datahub admin"""
        try:
            # datahub_admin = [request.data["datahub_admin"]]
            datahub_admin = [User.objects.filter(role_id=1).first().email]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # render email from query_email template
            email_render = render(request, "query_email.html", serializer.data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=datahub_admin,
                content=mail_body,
                subject=serializer.data["subject"],
            )

            return Response({"Message": "Your query is submitted! Thank you."}, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentsMicrositeViewSet(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = LegalDocumentSerializer
    queryset = DatahubDocuments.objects.all()
    permission_classes = []

    @action(detail=False, methods=["get"])
    def legal_documents(self, request):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            file_paths = file_operations.file_path(settings.DOCUMENTS_URL)
            datahub_obj = DatahubDocuments.objects.first()

            if not datahub_obj and not file_paths:
                data = {"Content": None, "Documents": None}
                return Response(data, status=status.HTTP_200_OK)
            elif not datahub_obj:
                data = {"Content": None, "Documents": file_paths}
                return Response(data, status=status.HTTP_200_OK)
            elif datahub_obj and not file_paths:
                documents_serializer = LegalDocumentSerializer(datahub_obj)
                data = {"Content": documents_serializer.data, "Documents": None}
                return Response(data, status=status.HTTP_200_OK)
            elif datahub_obj and file_paths:
                documents_serializer = LegalDocumentSerializer(datahub_obj)
                data = {"Content": documents_serializer.data, "Documents": file_paths}
                return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
