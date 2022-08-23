import json
import logging
import os
import shutil
from calendar import c

import django
import pandas as pd
from accounts.models import User, UserRole
from accounts.serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from core.constants import Constants
from core.utils import (
    CustomPagination,
    Utils,
    csv_and_xlsx_file_validatation,
    date_formater,
    read_contents_from_csv_or_xlsx_file,
)
from django.conf import settings
from django.contrib.admin.utils import get_model_from_relation
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import DEFERRED, F, Q
from drf_braces.mixins import MultipleSerializersViewMixin
from participant.models import SupportTicket, Connectors
from participant.serializers import (
    ParticipantSupportTicketSerializer,
    TicketSupportSerializer,
)
from python_http_client import exceptions
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial
from utils import file_operations, validators

from datahub.models import DatahubDocuments, Datasets, Organization, UserOrganizationMap
from datahub.serializers import (
    DatahubDatasetsSerializer,
    DatahubThemeSerializer,
    DatasetSerializer,
    DatasetUpdateSerializer,
    DropDocumentSerializer,
    OrganizationSerializer,
    ParticipantSerializer,
    PolicyDocumentSerializer,
    TeamMemberCreateSerializer,
    TeamMemberDetailsSerializer,
    TeamMemberListSerializer,
    TeamMemberUpdateSerializer,
    UserOrganizationCreateSerializer,
    UserOrganizationMapSerializer,
    RecentSupportTicketSerializer,
    RecentConnectorListSerializer,
)

LOGGER = logging.getLogger(__name__)


class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """

    page_size = 5


class TeamMemberViewSet(GenericViewSet):
    """Viewset for Product model"""

    serializer_class = TeamMemberListSerializer
    queryset = User.objects.all()
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = TeamMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        # queryset = self.filter_queryset(self.get_queryset())
        queryset = User.objects.filter(Q(status=True) & (Q(role__id=2) | Q(role__id=5)))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        team_member = self.get_object()
        serializer = TeamMemberDetailsSerializer(team_member)
        # serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        # request.data["role"] = UserRole.objects.get(role_name=request.data["role"]).id
        serializer = TeamMemberUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        team_member = self.get_object()
        team_member.status = False
        # team_member.delete()
        team_member.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationViewSet(GenericViewSet):
    """
    Organisation Viewset.
    """

    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    pagination_class = CustomPagination
    parser_class = MultiPartParser

    def perform_create(self, serializer):
        """
        This function performs the create operation of requested serializer.
        Args:
            serializer (_type_): serializer class object.

        Returns:
            _type_: Returns the saved details.
        """
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an organization object using User ID (IMPORTANT: Using USER ID instead of Organization ID)"""
        try:
            user_queryset = User.objects.filter(id=request.data.get("user_id", None))
            if not user_queryset:
                return Response({"message": ["User is not available"]}, status=status.HTTP_400_BAD_REQUEST)

            org_queryset = Organization.objects.filter(org_email=request.data.get("org_email", None))
            user_org_queryset = UserOrganizationMap.objects.filter(user_id=user_queryset.first().id)

            if user_org_queryset:
                return Response(
                        {"message": ["User is already associated with an organization"]}, status=status.HTTP_400_BAD_REQUEST
                )

            elif not org_queryset and not user_org_queryset:
                with transaction.atomic():
                    # create organization and userorganizationmap object
                    org_serializer = OrganizationSerializer(data=request.data, partial=True)
                    org_serializer.is_valid(raise_exception=True)
                    org_queryset = self.perform_create(org_serializer)

                    user_org_serializer = UserOrganizationMapSerializer(
                        data={
                            Constants.USER: user_queryset.first().id,
                            Constants.ORGANIZATION: org_queryset.id,
                        }
                    )
                    user_org_serializer.is_valid(raise_exception=True)
                    self.perform_create(user_org_serializer)
                    return Response(org_serializer.data, status=status.HTTP_201_CREATED)

            elif org_queryset and not user_org_queryset:
                with transaction.atomic():
                    # map user to org by creating userorganizationmap object
                    user_org_serializer = UserOrganizationMapSerializer(
                        data={
                            Constants.USER: user_queryset.first().id,
                            Constants.ORGANIZATION: org_queryset.first().id,
                        }
                    )
                    user_org_serializer.is_valid(raise_exception=True)
                    self.perform_create(user_org_serializer)
                    return Response(user_org_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        """GET method: query the list of Organization objects"""
        user_org_queryset = (
            UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
            # .filter(organization__status=True)
            .all()
        )
        page = self.paginate_queryset(user_org_queryset)
        user_organization_serializer = ParticipantSerializer(page, many=True)
        return self.get_paginated_response(user_organization_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        user_obj = User.objects.get(id=pk)
        user_org_queryset = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION)
            # .filter(organization__status=True, user=pk)
            .filter(user=pk)
        )

        if not user_org_queryset:
            data = {Constants.USER: {"id": user_obj.id}, Constants.ORGANIZATION: "null"}
            return Response(data, status=status.HTTP_200_OK)

        org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
        user_org_serializer = OrganizationSerializer(org_obj)
        data = {Constants.USER: {"id": user_obj.id}, Constants.ORGANIZATION: user_org_serializer.data}
        return Response(data, status=status.HTTP_200_OK)

    def update(self, request, pk):
        """PUT method: update or PUT request for Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        user_org_queryset = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION).filter(user=pk).all()
        )

        if not user_org_queryset:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        user_org_map = user_org_queryset.first()
        user_org_id = user_org_map.organization_id
        user_map_id = user_org_map.id
        organization_serializer = OrganizationSerializer(
            Organization.objects.get(id=user_org_id),
            data=request.data,
            partial=True,
        )

        organization_serializer.is_valid(raise_exception=True)
        self.perform_create(organization_serializer)
        data = {
            Constants.USER: {"id": pk},
            Constants.ORGANIZATION: organization_serializer.data,
            "user_map": user_map_id,
            "org_id": user_org_id,
        }
        return Response(
            data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        organization = self.get_object()
        # organization.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantViewSet(GenericViewSet):
    """
    This class handles the participant CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    pagination_class = CustomPagination

    def perform_create(self, serializer):
        """
        This function performs the create operation of requested serializer.
        Args:
            serializer (_type_): serializer class object.

        Returns:
            _type_: Returns the saved details.
        """
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        org_queryset = list(
            Organization.objects.filter(org_email=self.request.data.get(Constants.ORG_EMAIL, "")).values()
        )
        if not org_queryset:
            serializer = OrganizationSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            org_queryset = self.perform_create(serializer)
            org_id = org_queryset.id
        else:
            org_id = org_queryset[0].get(Constants.ID)
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_saved = self.perform_create(serializer)

        user_org_serializer = UserOrganizationMapSerializer(
            data={
                Constants.USER: user_saved.id,
                Constants.ORGANIZATION: org_id,
            }
        )
        user_org_serializer.is_valid(raise_exception=True)
        self.perform_create(user_org_serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        roles = (
            UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=True, user__role=3)
            .all()
        )
        page = self.paginate_queryset(roles)
        participant_serializer = ParticipantSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        roles = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=True, user__role=3, user=pk)
            .all()
        )
        participant_serializer = ParticipantSerializer(roles, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        organization = OrganizationSerializer(
            Organization.objects.get(id=request.data.get(Constants.ID)),
            data=request.data,
            partial=None,
        )
        organization.is_valid(raise_exception=True)
        self.perform_create(organization)
        data = {
            Constants.USER: serializer.data,
            Constants.ORGANIZATION: organization.data,
        }
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = False
        self.perform_create(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MailInvitationViewSet(GenericViewSet):
    """
    This class handles the mail invitation API views.
    """

    def create(self, request, *args, **kwargs):
        """
        This will send the mail to the requested user with content.
        Args:
            request (_type_): Api request object.

        Returns:
            _type_: Retuns the sucess response with message and status code.
        """
        data = request.data
        return Utils().send_email(
            to_email=data.get(Constants.TO_EMAIL, []),
            content=data.get(Constants.CONTENT),
            subject=Constants.PARTICIPANT_INVITATION,
        )


class DropDocumentView(GenericViewSet):
    """View for uploading organization document files"""

    parser_class = MultiPartParser
    serializer_class = DropDocumentSerializer

    def create(self, request, *args, **kwargs):
        """Saves the document files in temp location before saving"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            # get file, file name & type from the form-data
            key = list(request.data.keys())[0]
            file = serializer.validated_data[key]
            file_type = str(file).split(".")[-1]
            file_name = str(key) + "." + file_type
            file_operations.file_save(file, file_name, settings.TEMP_FILE_PATH)
            return Response({key: [f"{file_name} uploading in progress ..."]}, status=status.HTTP_201_CREATED)

        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["delete"])
    def delete(self, request):
        """remove the dropped documents"""
        try:
            key = list(request.data.keys())[0]
            file_operations.remove_files(key, settings.TEMP_FILE_PATH)
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class DocumentSaveView(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = PolicyDocumentSerializer
    queryset = DatahubDocuments.objects.all()

    @action(detail=False, methods=["get"])
    def get(self, request):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            file_paths = file_operations.file_path(settings.DOCUMENTS_URL)
            datahub_obj = DatahubDocuments.objects.last()

            if not datahub_obj and not file_paths:
                data = {"Content": None, "Documents": None}
                return Response(data, status=status.HTTP_200_OK)
            elif not datahub_obj:
                data = {"Content": None, "Documents": file_paths}
                return Response(data, status=status.HTTP_200_OK)
            elif datahub_obj and not file_paths:
                documents_serializer = PolicyDocumentSerializer(datahub_obj)
                data = {"Content": documents_serializer.data, "Documents": None}
                return Response(data, status=status.HTTP_200_OK)
            elif datahub_obj and file_paths:
                documents_serializer = PolicyDocumentSerializer(datahub_obj)
                data = {"Content": documents_serializer.data, "Documents": file_paths}
                return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                serializer.save()
                # save the document files
                file_operations.files_move(settings.TEMP_FILE_PATH, settings.DOCUMENTS_ROOT)
                return Response(
                    {"message": "Documents and content saved!"},
                    status=status.HTTP_201_CREATED,
                )
        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def put(self, request, *args, **kwargs):
        """Saves the document content and files"""
        try:
            # instance = self.get_object()
            datahub_obj = DatahubDocuments.objects.last()
            serializer = self.get_serializer(datahub_obj, data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                serializer.save()
                file_operations.files_move(settings.TEMP_FILE_PATH, settings.DOCUMENTS_ROOT)
                return Response(
                    {"message": "Documents and content updated!"},
                    status=status.HTTP_201_CREATED,
                )
        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class DatahubThemeView(GenericViewSet):
    """View for modifying datahub branding"""

    parser_class = MultiPartParser
    serializer_class = DatahubThemeSerializer

    def create(self, request, *args, **kwargs):
        """generates the override css for datahub"""
        # user = User.objects.filter(email=request.data.get("email", ""))
        # user = user.first()
        data = {}

        try:
            banner = request.data.get("banner", "null")
            banner = None if banner == "null" else banner
            button_color = request.data.get("button_color", "null")
            button_color = None if button_color == "null" else button_color

            if not banner and not button_color:
                data = {"banner": "null", "button_color": "null"}

            elif banner and not button_color:
                file_name = file_operations.get_file_name(str(banner), "banner")
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)
                data = {"banner": file_name, "button_color": "null"}

            elif not banner and button_color:
                css = ".btn { background-color: " + button_color + "; }"
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.CSS_ROOT,
                )
                data = {"banner": "null", "button_color": settings.CSS_FILE_NAME}

            elif banner and button_color:
                file_name = file_operations.get_file_name(str(banner), "banner")
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)

                css = ".btn { background-color: " + button_color + "; }"
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.CSS_ROOT,
                )
                data = {"banner": file_name, "button_color": settings.CSS_FILE_NAME}

            # set datahub admin user status to True
            # user.on_boarded = True
            # user.save()
            return Response(data, status=status.HTTP_201_CREATED)

        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def get(self, request):
        """retrieves Datahub Theme attributes"""
        file_paths = file_operations.file_path(settings.THEME_URL)
        # css_path = file_operations.file_path(settings.CSS_ROOT)
        css_path = settings.CSS_ROOT + settings.CSS_FILE_NAME
        data = {}

        try:
            css_attribute = file_operations.get_css_attributes(css_path, "background-color")

            if not css_path and not file_paths:
                data = {"banner": "null", "css": "null"}
            elif not css_path:
                data = {"banner": file_paths, "css": "null"}
            elif css_path and not file_paths:
                data = {"banner": "null", "css": {"btnBackground": css_attribute}}
            elif css_path and file_paths:
                data = {"banner": file_paths, "css": {"btnBackground": css_attribute}}

            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False)
    def put(self, request, *args, **kwargs):
        data = {}
        try:
            banner = request.data.get("banner", "null")
            banner = None if banner == "null" else banner
            button_color = request.data.get("button_color", "null")
            button_color = None if button_color == "null" else button_color

            if banner is None and button_color is None:
                data = {"banner": "null", "button_color": "null"}

            elif banner and button_color is None:
                file_name = file_operations.get_file_name(str(banner), "banner")
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)
                data = {"banner": file_name, "button_color": "null"}

            elif not banner and button_color:
                css = ".btn { background-color: " + button_color + "; }"
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.CSS_ROOT,
                )
                data = {"banner": "null", "button_color": settings.CSS_FILE_NAME}

            elif banner and button_color:
                file_name = file_operations.get_file_name(str(banner), "banner")
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)

                css = ".btn { background-color: " + button_color + "; }"
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.CSS_ROOT,
                )
                data = {"banner": file_name, "button_color": settings.CSS_FILE_NAME}

            return Response(data, status=status.HTTP_201_CREATED)

        except exceptions as error:
            LOGGER.error(error, exc_info=True)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class SupportViewSet(GenericViewSet):
    """
    This class handles the participant support tickets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = TicketSupportSerializer
    queryset = SupportTicket
    pagination_class = CustomPagination

    def perform_create(self, serializer):
        """
        This function performs the create operation of requested serializer.
        Args:
            serializer (_type_): serializer class object.

        Returns:
            _type_: Returns the saved details.
        """
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def filters_tickets(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        range = {}
        updated_range_at = request.data.pop("updated_at__range", None)
        if updated_range_at:
            range["updated_at__range"] = date_formater(updated_range_at)
        try:
            data = (
                SupportTicket.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, **request.data, **range)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        except django.core.exceptions.FieldError as error:  # type: ignore
            logging.error(f"Error while filtering the ticketd ERROR: {error}")
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=400)

        page = self.paginate_queryset(data)
        participant_serializer = ParticipantSupportTicketSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = (
            SupportTicket.objects.select_related(
                Constants.USER_MAP,
                Constants.USER_MAP_USER,
                Constants.USER_MAP_ORGANIZATION,
            )
            .filter(user_map__user__status=True, **request.GET)
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        page = self.paginate_queryset(data)
        participant_serializer = ParticipantSupportTicketSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        data = (
            SupportTicket.objects.select_related(
                Constants.USER_MAP,
                Constants.USER_MAP_USER,
                Constants.USER_MAP_ORGANIZATION,
            )
            .filter(user_map__user__status=True, id=pk)
            .all()
        )
        participant_serializer = ParticipantSupportTicketSerializer(data, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)


class DatahubDatasetsViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = DatasetSerializer
    queryset = Datasets
    pagination_class = CustomPagination

    def perform_create(self, serializer):
        """
        This function performs the create operation of requested serializer.
        Args:
            serializer (_type_): serializer class object.

        Returns:
            _type_: Returns the saved details.
        """
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        setattr(request.data, "_mutable", True)
        data = request.data
        if not csv_and_xlsx_file_validatation(request.data.get(Constants.SAMPLE_DATASET)):
            return Response(
                {
                    Constants.SAMPLE_DATASET: [
                        "Invalid Sample dataset file (or) Atleast 5 rows should be available. please upload valid file"
                    ]
                },
                400,
            )
        data[Constants.APPROVAL_STATUS] = Constants.APPROVED
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        user_id = request.query_params.get(Constants.USER_ID)
        others = request.query_params.get(Constants.OTHERS)
        filters = {Constants.USER_MAP_USER: user_id} if user_id and not others else {}
        exclude = {Constants.USER_MAP_USER: user_id} if others else {}
        if exclude or filters:
            data = (
                Datasets.objects.select_related(
                    Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION
                )
                .filter(user_map__user__status=True, status=True, **filters)
                .exclude(**exclude)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        page = self.paginate_queryset(data)
        participant_serializer = DatahubDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        data = (
            Datasets.objects.select_related(
                Constants.USER_MAP,
                Constants.USER_MAP_USER,
                Constants.USER_MAP_ORGANIZATION,
            )
            .filter(user_map__user__status=True, status=True, id=pk)
            .all()
        )
        participant_serializer = DatahubDatasetsSerializer(data, many=True)
        if participant_serializer.data:
            data = participant_serializer.data[0]
            data[Constants.CONTENT] = read_contents_from_csv_or_xlsx_file(data.get(Constants.SAMPLE_DATASET))
            return Response(data, status=status.HTTP_200_OK)
        return Response({}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        setattr(request.data, "_mutable", True)
        data = request.data
        data = {key: value for key, value in data.items() if value != "null"}
        if data.get(Constants.SAMPLE_DATASET):
            if not csv_and_xlsx_file_validatation(data.get(Constants.SAMPLE_DATASET)):
                return Response(
                    {
                        Constants.SAMPLE_DATASET: [
                            "Invalid Sample dataset file (or) Atleast 5 rows should be available. please upload valid file"
                        ]
                    },
                    400,
                )
        category = data.get(Constants.CATEGORY)
        if category:
            data[Constants.CATEGORY] = json.loads(category) if isinstance(category, str) else category
        instance = self.get_object()
        serializer = DatasetUpdateSerializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = False
        self.perform_create(product)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def dataset_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")
        exclude, filters, range = {}, {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        created_at__range = request.data.pop(Constants.CREATED_AT__RANGE, None)
        if created_at__range:
            range[Constants.CREATED_AT__RANGE] = date_formater(created_at__range)
        try:
            data = (
                Datasets.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(status=True, **data, **filters, **range)
                .exclude(**exclude)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = DatahubDatasetsSerializer(page, many=True)
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
            filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            geography = (
                Datasets.objects
                .values_list(Constants.GEOGRAPHY, flat=True)
                .filter(status=True, **filters)
                .exclude(geography="null")
                .exclude(geography__isnull=True)
                .exclude(geography="")
                .exclude(**exclude)
                .all()
                .distinct()
            )
            crop_detail = (
                Datasets.objects
                .values_list(Constants.CROP_DETAIL, flat=True)
                .filter(status=True, **filters)
                .exclude(crop_detail="null")
                .exclude(crop_detail__isnull=True)
                .exclude(crop_detail="")
                .exclude(**exclude)
                .all()
                .distinct()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response({"geography": geography, "crop_detail": crop_detail}, status=200)


class DatahubDashboard(GenericViewSet):
    """Datahub Dashboard viewset"""
    pagination_class = CustomPagination

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Retrieve datahub dashboard details"""
        try:
            total_participants = User.objects.filter(role_id=3, status=True).count()
            total_datasets = (
                Datasets.objects.select_related("user_map", "user_map__user", "user_map__organization")
                .filter(user_map__user__status=True, status=True)
                .order_by("updated_at")
                .count()
            )
            # write a function to compute data exchange
            active_connectors = Connectors.objects.filter(status=True).count()
            total_data_exchange = {"total_data": 50, "unit": "Gbs"}

            datasets = Datasets.objects.filter(status=True).values_list("category")
            categories = set()
            categories_dict = {}
            for data in datasets:
                for element in data[0].keys():
                    categories.add(element)

            categories_dict = {key:0 for key in categories}
            for data in datasets:
                for key,value in data[0].items():
                    if value == True:
                        categories_dict[key] += 1


            open_support_tickets = SupportTicket.objects.filter(status="open").count()
            closed_support_tickets = SupportTicket.objects.filter(status="closed").count()
            hold_support_tickets = SupportTicket.objects.filter(status="hold").count()

            # retrieve 3 recent support tickets
            recent_tickets_queryset = SupportTicket.objects.order_by("updated_at")[0:3]
            recent_tickets_serializer = RecentSupportTicketSerializer(recent_tickets_queryset, many=True)
            support_tickets = {"open_requests": open_support_tickets, "closed_requests": closed_support_tickets, "hold_requests": hold_support_tickets, "recent_tickets": recent_tickets_serializer.data}

            # retrieve 3 recent updated connectors
            # connectors_queryset = Connectors.objects.order_by("updated_at")[0:3]
            connectors_queryset = Connectors.objects.order_by("updated_at").all()
            connector_pages = self.paginate_queryset(connectors_queryset)               # paginaged connectors list
            connectors_serializer = RecentConnectorListSerializer(connector_pages, many=True)

            data = {"total_participants": total_participants, "total_datasets": total_datasets, "active_connectors": active_connectors, "total_data_exchange": total_data_exchange, "categories": categories_dict, "support_tickets": support_tickets, "connectors": self.get_paginated_response(connectors_serializer.data).data}
            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

