from functools import reduce
import json
import logging, datetime
import operator
import os
from accounts.serializers import UserCreateSerializer
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
from datahub.models import (
    DatasetV2,
    DatasetV2File,
    Organization,
    Datasets,
    UserOrganizationMap,
    DatahubDocuments,
)
from datahub.serializers import DatahubDatasetsV2Serializer, DatasetV2Serializer, ParticipantSerializer
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
                    "message": [
                        "Datahub admin is not associated with any organization."
                    ],
                }
                return Response(data, status=status.HTTP_200_OK)

            org_obj = Organization.objects.get(
                id=user_org_queryset.first().organization_id
            )
            org_seriliazer = OrganizationMicrositeSerializer(org_obj)
            data = {
                Constants.USER: user_serializer.data,
                Constants.ORGANIZATION: org_seriliazer.data,
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatahubThemeMicrositeViewSet(GenericViewSet):
    permission_classes = []

    @action(detail=False, methods=["get"])
    def theme(self, request):
        """retrieves Datahub Theme attributes"""
        file_paths = file_operations.file_path(settings.THEME_URL)
        css_path = settings.CSS_ROOT + settings.CSS_FILE_NAME
        data = {}

        try:
            css_attribute = file_operations.get_css_attributes(
                css_path, "background-color"
            )

            if not css_path and not file_paths:
                data = {"hero_image": None, "css": None}
            elif not css_path:
                data = {"hero_image": file_paths, "css": None}
            elif css_path and not file_paths:
                data = {"hero_image": None, "css": {"btnBackground": css_attribute}}
            elif css_path and file_paths:
                data = {
                    "hero_image": file_paths,
                    "css": {"btnBackground": css_attribute},
                }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            LOGGER.error(e)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class DatasetsMicrositeViewSet(GenericViewSet):
    """Datasets viewset for microsite"""

    serializer_class = DatasetV2Serializer
    queryset = DatasetV2.objects.all()
    pagination_class = CustomPagination
    permission_classes = []

    def list(self, request, *args, **kwargs):
        """
        ``GET`` method Endpoint: list action to view the list of Datasets via GET request. [see here][ref].

        **Endpoint**
        [ref]: /datahub/dataset/v2/
        """
        queryset = self.get_queryset()
        # serializer = self.get_serializer(queryset, many=True)
        # return Response(serializer.data, status=status.HTTP_200_OK)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response([], status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        ``GET`` method Endpoint: retrieve action for the detail view of Dataset via GET request
            Returns dataset object view with content of XLX/XLSX file and file URLS. [see here][ref].

        **Endpoint**
        [ref]: /datahub/dataset/v2/<id>/
        """
        obj = self.get_object()
        serializer = self.get_serializer(obj).data

        dataset_file_obj = DatasetV2File.objects.filter(dataset_id=obj.id)
        data = []
        for file in dataset_file_obj:
            path_ = os.path.join("/media/", str(file.file))
            file_path = {}
            file_path["content"] = read_contents_from_csv_or_xlsx_file(path_)
            # Omitted the actual name of the file so the user can't manually download the file
            # file_path["file"] = path_.split("/")[-1]
            file_path["source"] = file.source
            data.append(file_path)

        serializer["datasets"] = data
        return Response(serializer, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def dataset_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        categories = data.pop(Constants.CATEGORY, None)
        user_id = data.pop(Constants.USER_ID, "")
        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            if categories is not None:
                data = (
                    DatasetV2.objects.select_related(
                        Constants.USER_MAP,
                        Constants.USER_MAP_USER,
                        Constants.USER_MAP_ORGANIZATION,
                    )
                    .filter(status=True, **data, **filters)
                    .filter(
                        reduce(
                            operator.or_,
                            (Q(category__contains=cat) for cat in categories),
                        )
                    )
                    .exclude(**exclude)
                    .order_by(Constants.UPDATED_AT)
                    .reverse()
                    .all()
                )
            else:
                data = (
                    DatasetV2.objects.select_related(
                        Constants.USER_MAP,
                        Constants.USER_MAP_USER,
                        Constants.USER_MAP_ORGANIZATION,
                    )
                    .filter(status=True, **data, **filters)
                    .exclude(**exclude)
                    .order_by(Constants.UPDATED_AT)
                    .reverse()
                    .all()
                )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=500
            )

        page = self.paginate_queryset(data)
        participant_serializer = DatahubDatasetsV2Serializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")
        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            # filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            geography = (
                DatasetV2.objects.values_list(Constants.GEOGRAPHY, flat=True)
                .filter(status=True, **filters)
                .exclude(geography="null")
                .exclude(geography__isnull=True)
                .exclude(geography="")
                .exclude(**exclude)
                .all()
                .distinct()
            )
            # crop_detail = (
            #     Datasets.objects.values_list(Constants.CROP_DETAIL, flat=True)
            #     .filter(status=True, **filters)
            #     .exclude(crop_detail="null")
            #     .exclude(crop_detail__isnull=True)
            #     .exclude(crop_detail="")
            #     .exclude(**exclude)
            #     .all()
            #     .distinct()
            # )
            if os.path.exists(Constants.CATEGORIES_FILE):
                with open(Constants.CATEGORIES_FILE, "r") as json_obj:
                    category_detail = json.loads(json_obj.read())
            else:
                category_detail = []
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=500
            )
        return Response(
            {"geography": geography, "category_detail": category_detail}, status=200
        )

    @action(detail=False, methods=["post"])
    def search_datasets(self, request, *args, **kwargs):
        data = request.data
        search_pattern = data.pop(Constants.SEARCH_PATTERNS, "")
        filters = {Constants.NAME_ICONTAINS: search_pattern} if search_pattern else {}     
        try:
            data = (
                DatasetV2.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, status=True, **filters)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
            page = self.paginate_queryset(data)
            participant_serializer = DatahubDatasetsV2Serializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ContactFormViewSet(GenericViewSet):
    """Contact Form for guest users to mail queries or application to become participant on datahub"""

    serializer_class = ContactFormSerializer
    permission_classes = []

    def create(self, request):
        """POST method to create a query and mail it to the datahub admin"""
        try:
            datahub_admin = User.objects.filter(role_id=1).first()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            date = datetime.datetime.now().strftime("%d-%m-%Y")
            data = serializer.data
            data.update({"date": date})
            print(data)

            # render email from query_email template
            email_render = render(request, "user_fills_in_contact_form.html", data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=[datahub_admin.email],
                content=mail_body,
                subject=serializer.data.get("subject", Constants.DATAHUB),
            )
            return Response(
                {"Message": "Your query is submitted! Thank you."},
                status=status.HTTP_200_OK,
            )

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
            datahub_obj = DatahubDocuments.objects.last()

            content = {
                Constants.GOVERNING_LAW: datahub_obj.governing_law
                if datahub_obj
                else None,
                Constants.PRIVACY_POLICY: datahub_obj.privacy_policy
                if datahub_obj
                else None,
                Constants.TOS: datahub_obj.tos if datahub_obj else None,
                Constants.LIMITATIONS_OF_LIABILITIES: datahub_obj.limitations_of_liabilities
                if datahub_obj
                else None,
                Constants.WARRANTY: datahub_obj.warranty if datahub_obj else None,
            }

            documents = {
                Constants.GOVERNING_LAW: file_paths.get("governing_law"),
                Constants.PRIVACY_POLICY: file_paths.get("privacy_policy"),
                Constants.TOS: file_paths.get("tos"),
                Constants.LIMITATIONS_OF_LIABILITIES: file_paths.get(
                    "limitations_of_liabilities"
                ),
                Constants.WARRANTY: file_paths.get("warranty"),
            }

            if not datahub_obj and not file_paths:
                data = {"content": content, "documents": documents}
                return Response(data, status=status.HTTP_200_OK)
            elif not datahub_obj:
                data = {"content": content, "documents": documents}
                return Response(data, status=status.HTTP_200_OK)
            elif datahub_obj and not file_paths:
                data = {"content": content, "documents": documents}
                return Response(data, status=status.HTTP_200_OK)
            elif datahub_obj and file_paths:
                data = {"content": content, "documents": documents}
                return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ParticipantMicrositeViewSet(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    pagination_class = CustomPagination
    permission_classes = []

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        co_steward = request.GET.get("co_steward", False)
        if co_steward:
            roles = (
                UserOrganizationMap.objects.select_related(
                    Constants.USER, Constants.ORGANIZATION
                )
                .filter(user__status=True, user__role=6)
                .all()
            )
        else:
            roles = (
                UserOrganizationMap.objects.select_related(
                    Constants.USER, Constants.ORGANIZATION
                )
                .filter(user__status=True, user__role=3)
                .all()
            )
        page = self.paginate_queryset(roles)
        participant_serializer = ParticipantSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        roles = (
            UserOrganizationMap.objects.prefetch_related(
                Constants.USER, Constants.ORGANIZATION
            )
            .filter(user__status=True, user=pk)
            .all()
        )
        participant_serializer = ParticipantSerializer(roles, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)