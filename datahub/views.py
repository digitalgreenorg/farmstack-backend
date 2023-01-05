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
from django.shortcuts import render
from drf_braces.mixins import MultipleSerializersViewMixin
from participant.models import Connectors, SupportTicket
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
from utils import file_operations, string_functions, validators

from datahub.models import (
    DatahubDocuments,
    Datasets,
    Organization,
    UserOrganizationMap,
    DatasetV2,
)
from datahub.serializers import (
    DatahubDatasetsSerializer,
    DatahubThemeSerializer,
    DatasetSerializer,
    DatasetUpdateSerializer,
    DropDocumentSerializer,
    OrganizationSerializer,
    ParticipantSerializer,
    PolicyDocumentSerializer,
    RecentDatasetListSerializer,
    RecentSupportTicketSerializer,
    TeamMemberCreateSerializer,
    TeamMemberDetailsSerializer,
    TeamMemberListSerializer,
    TeamMemberUpdateSerializer,
    UserOrganizationCreateSerializer,
    UserOrganizationMapSerializer,
    DatasetV2Serializer,
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
        serializer = TeamMemberUpdateSerializer(
            instance, data=request.data, partial=True
        )
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
            user_obj = User.objects.get(id=request.data.get(Constants.USER_ID))
            org_queryset = Organization.objects.filter(
                org_email=request.data.get(Constants.ORG_EMAIL), status=True
            )
            user_org_queryset = (
                UserOrganizationMap.objects.filter(
                    organization_id=org_queryset.first().id
                )
                if org_queryset
                else None
            )

            if not user_obj:
                return Response(
                    {"message": ["User is not available"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if user_org_queryset:
                return Response(
                    {"message": ["User is already associated with an organization"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            elif not org_queryset and not user_org_queryset:
                with transaction.atomic():
                    # create organization and userorganizationmap object
                    print("Creating org & user_org_map")
                    org_serializer = OrganizationSerializer(
                        data=request.data, partial=True
                    )
                    org_serializer.is_valid(raise_exception=True)
                    org_queryset = self.perform_create(org_serializer)

                    user_org_serializer = UserOrganizationMapSerializer(
                        data={
                            Constants.USER: user_obj.id,
                            Constants.ORGANIZATION: org_queryset.id,
                        }
                    )
                    user_org_serializer.is_valid(raise_exception=True)
                    self.perform_create(user_org_serializer)
                    data = {
                        "user_map": user_org_serializer.data.get("id"),
                        "org_id": org_queryset.id,
                        "organization": org_serializer.data,
                    }
                    return Response(data, status=status.HTTP_201_CREATED)

            elif org_queryset and not user_org_queryset:
                with transaction.atomic():
                    # map user to org by creating userorganizationmap object
                    print("creating only user_org_map")
                    user_org_serializer = UserOrganizationMapSerializer(
                        data={
                            Constants.USER: user_obj.id,
                            Constants.ORGANIZATION: org_queryset.first().id,
                        }
                    )
                    user_org_serializer.is_valid(raise_exception=True)
                    self.perform_create(user_org_serializer)
                    data = {
                        "user_map": user_org_serializer.data.get("id"),
                        "org_id": org_queryset.first().id,
                    }
                    return Response(data, status=status.HTTP_201_CREATED)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        """GET method: query the list of Organization objects"""
        user_org_queryset = (
            UserOrganizationMap.objects.select_related(
                Constants.USER, Constants.ORGANIZATION
            )
            .filter(organization__status=True)
            .all()
        )
        page = self.paginate_queryset(user_org_queryset)
        user_organization_serializer = ParticipantSerializer(page, many=True)
        return self.get_paginated_response(user_organization_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        user_obj = User.objects.get(id=pk, status=True)
        user_org_queryset = UserOrganizationMap.objects.prefetch_related(
            Constants.USER, Constants.ORGANIZATION
        ).filter(organization__status=True, user=pk)

        if not user_org_queryset:
            data = {Constants.USER: {"id": user_obj.id}, Constants.ORGANIZATION: "null"}
            return Response(data, status=status.HTTP_200_OK)

        org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
        user_org_serializer = OrganizationSerializer(org_obj)
        data = {
            Constants.USER: {"id": user_obj.id},
            Constants.ORGANIZATION: user_org_serializer.data,
        }
        return Response(data, status=status.HTTP_200_OK)

    def update(self, request, pk):
        """PUT method: update or PUT request for Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        user_obj = User.objects.get(id=pk, status=True)
        user_org_queryset = (
            UserOrganizationMap.objects.prefetch_related(
                Constants.USER, Constants.ORGANIZATION
            )
            .filter(user=pk)
            .all()
        )

        if not user_org_queryset:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        organization_serializer = OrganizationSerializer(
            Organization.objects.get(id=user_org_queryset.first().organization_id),
            data=request.data,
            partial=True,
        )

        organization_serializer.is_valid(raise_exception=True)
        self.perform_create(organization_serializer)
        data = {
            Constants.USER: {"id": pk},
            Constants.ORGANIZATION: organization_serializer.data,
            "user_map": user_org_queryset.first().id,
            "org_id": user_org_queryset.first().organization_id,
        }
        return Response(
            data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        user_obj = User.objects.get(id=pk, status=True)
        user_org_queryset = UserOrganizationMap.objects.select_related(
            Constants.ORGANIZATION
        ).get(user_id=pk)
        org_queryset = Organization.objects.get(id=user_org_queryset.organization_id)
        org_queryset.status = False
        self.perform_create(org_queryset)
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
            Organization.objects.filter(
                org_email=self.request.data.get(Constants.ORG_EMAIL, "")
            ).values()
        )
        if not org_queryset:
            org_serializer = OrganizationSerializer(data=request.data, partial=True)
            org_serializer.is_valid(raise_exception=True)
            org_queryset = self.perform_create(org_serializer)
            org_id = org_queryset.id
        else:
            org_id = org_queryset[0].get(Constants.ID)
        user_serializer = UserCreateSerializer(data=request.data)
        user_serializer.is_valid(raise_exception=True)
        user_saved = self.perform_create(user_serializer)

        user_org_serializer = UserOrganizationMapSerializer(
            data={
                Constants.USER: user_saved.id,
                Constants.ORGANIZATION: org_id,
            }
        )
        user_org_serializer.is_valid(raise_exception=True)
        self.perform_create(user_org_serializer)

        try:
            datahub_admin = User.objects.filter(role_id=1).first()
            admin_full_name = string_functions.get_full_name(
                datahub_admin.first_name, datahub_admin.last_name
            )
            participant_full_name = string_functions.get_full_name(
                request.data.get("first_name"), request.data.get("last_name")
            )

            data = {
                Constants.datahub_name: os.environ.get(
                    Constants.DATAHUB_NAME, Constants.datahub_name
                ),
                "participant_admin_name": participant_full_name,
                "participant_organization_name": request.data.get("name"),
                "datahub_admin": admin_full_name,
                Constants.datahub_site: os.environ.get(
                    Constants.DATAHUB_SITE, Constants.datahub_site
                ),
            }

            email_render = render(
                request, Constants.WHEN_DATAHUB_ADMIN_ADDS_PARTICIPANT, data
            )
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=request.data.get("email"),
                content=mail_body,
                subject=Constants.PARTICIPANT_ORG_ADDITION_SUBJECT
                + os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
            )
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(
                {"message": ["An error occured"]}, status=status.HTTP_200_OK
            )

        return Response(user_org_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
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
            .filter(user__status=True, user__role=3, user=pk)
            .all()
        )
        participant_serializer = ParticipantSerializer(roles, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        participant = self.get_object()
        user_serializer = self.get_serializer(
            participant, data=request.data, partial=True
        )
        user_serializer.is_valid(raise_exception=True)
        organization = Organization.objects.get(id=request.data.get(Constants.ID))
        organization_serializer = OrganizationSerializer(
            organization, data=request.data, partial=True
        )
        organization_serializer.is_valid(raise_exception=True)

        try:
            datahub_admin = User.objects.filter(role_id=1).first()
            admin_full_name = string_functions.get_full_name(
                datahub_admin.first_name, datahub_admin.last_name
            )
            participant_full_name = string_functions.get_full_name(
                participant.first_name, participant.last_name
            )

            data = {
                Constants.datahub_name: os.environ.get(
                    Constants.DATAHUB_NAME, Constants.datahub_name
                ),
                "participant_admin_name": participant_full_name,
                "participant_organization_name": organization.name,
                "datahub_admin": admin_full_name,
                Constants.datahub_site: os.environ.get(
                    Constants.DATAHUB_SITE, Constants.datahub_site
                ),
            }

            # update data & trigger_email
            self.perform_create(user_serializer)
            self.perform_create(organization_serializer)
            email_render = render(
                request, Constants.DATAHUB_ADMIN_UPDATES_PARTICIPANT_ORGANIZATION, data
            )
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=participant.email,
                content=mail_body,
                subject=Constants.PARTICIPANT_ORG_UPDATION_SUBJECT
                + os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
            )

            data = {
                Constants.USER: user_serializer.data,
                Constants.ORGANIZATION: organization_serializer.data,
            }
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(
                {"message": ["An error occured"]}, status=status.HTTP_200_OK
            )

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        participant = self.get_object()
        user_organization = UserOrganizationMap.objects.select_related(
            Constants.ORGANIZATION
        ).get(user_id=pk)
        organization = Organization.objects.get(id=user_organization.organization_id)

        if participant.status is not False and organization.status is not False:
            participant.status = False
            organization.status = False

            try:
                datahub_admin = User.objects.filter(role_id=1).first()
                admin_full_name = string_functions.get_full_name(
                    datahub_admin.first_name, datahub_admin.last_name
                )
                participant_full_name = string_functions.get_full_name(
                    participant.first_name, participant.last_name
                )

                data = {
                    Constants.datahub_name: os.environ.get(
                        Constants.DATAHUB_NAME, Constants.datahub_name
                    ),
                    "participant_admin_name": participant_full_name,
                    "participant_organization_name": organization.name,
                    "datahub_admin": admin_full_name,
                    Constants.datahub_site: os.environ.get(
                        Constants.DATAHUB_SITE, Constants.datahub_site
                    ),
                }

                # delete data & trigger_email
                self.perform_create(participant)
                self.perform_create(organization)
                email_render = render(
                    request,
                    Constants.DATAHUB_ADMIN_DELETES_PARTICIPANT_ORGANIZATION,
                    data,
                )
                mail_body = email_render.content.decode("utf-8")
                Utils().send_email(
                    to_email=participant.email,
                    content=mail_body,
                    subject=Constants.PARTICIPANT_ORG_DELETION_SUBJECT
                    + os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                )

                return Response(
                    {"message": ["Participant deleted"]},
                    status=status.HTTP_204_NO_CONTENT,
                )
            except Exception as error:
                LOGGER.error(error, exc_info=True)
                return Response(
                    {"message": ["An error occured"]}, status=status.HTTP_200_OK
                )

        elif participant.status is False and organization.status is False:
            return Response(
                {"message": ["Object already deleted"]},
                status=status.HTTP_204_NO_CONTENT,
            )

        return Response({"message": ["An error occured"]}, status=status.HTTP_200_OK)


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
        try:
            email_list = request.data.get("to_email")
            emails_found, emails_not_found = ([] for i in range(2))
            for email in email_list:
                if User.objects.filter(email=email):
                    emails_found.append(email)
                else:
                    emails_not_found.append(email)

            for user in User.objects.filter(email__in=emails_found):
                full_name = (
                    user.first_name + " " + str(user.last_name)
                    if user.last_name
                    else user.first_name
                )
                data = {
                    "datahub_name": os.environ.get("DATAHUB_NAME", "datahub_name"),
                    "participant_admin_name": full_name,
                    "datahub_site": os.environ.get("DATAHUB_SITE", "datahub_site"),
                }

                # render email from query_email template
                email_render = render(
                    request, "datahub_admin_invites_participants.html", data
                )
                mail_body = email_render.content.decode("utf-8")

                Utils().send_email(
                    to_email=[user.email],
                    content=mail_body,
                    subject=os.environ.get("DATAHUB_NAME", "datahub_name")
                    + Constants.PARTICIPANT_INVITATION_SUBJECT,
                )

            failed = f"No participants found for emails: {emails_not_found}"
            LOGGER.warning(failed)
            return Response(
                {
                    "message": f"Email successfully sent to {emails_found}",
                    "failed": failed,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({"Error": f"Failed to send email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # type: ignore


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
            return Response(
                {key: [f"{file_name} uploading in progress ..."]},
                status=status.HTTP_201_CREATED,
            )

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

        return Response({}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                serializer.save()
                # save the document files
                file_operations.files_move(
                    settings.TEMP_FILE_PATH, settings.DOCUMENTS_ROOT
                )
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
                file_operations.files_move(
                    settings.TEMP_FILE_PATH, settings.DOCUMENTS_ROOT
                )
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
            css_attribute = file_operations.get_css_attributes(
                css_path, "background-color"
            )

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
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=400
            )

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

    def trigger_email(
        self, request, template, to_email, subject, first_name, last_name, dataset_name
    ):
        # trigger email to the participant as they are being added
        try:
            datahub_admin = User.objects.filter(role_id=1).first()
            admin_full_name = string_functions.get_full_name(
                datahub_admin.first_name, datahub_admin.last_name
            )
            participant_full_name = string_functions.get_full_name(
                first_name, last_name
            )

            data = {
                "datahub_name": os.environ.get("DATAHUB_NAME", "datahub_name"),
                "participant_admin_name": participant_full_name,
                "datahub_admin": admin_full_name,
                "dataset_name": dataset_name,
                "datahub_site": os.environ.get("DATAHUB_SITE", "datahub_site"),
            }

            email_render = render(request, template, data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=to_email,
                content=mail_body,
                subject=subject + os.environ.get("DATAHUB_NAME", "datahub_name"),
            )

        except Exception as error:
            LOGGER.error(error, exc_info=True)

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        setattr(request.data, "_mutable", True)
        data = request.data

        if not data.get("is_public"):
            if not csv_and_xlsx_file_validatation(
                request.data.get(Constants.SAMPLE_DATASET)
            ):
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
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
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
            if not data.get("is_public"):
                data[Constants.CONTENT] = read_contents_from_csv_or_xlsx_file(
                    data.get(Constants.SAMPLE_DATASET)
                )
            return Response(data, status=status.HTTP_200_OK)
        return Response({}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        setattr(request.data, "_mutable", True)
        data = request.data
        data = {key: value for key, value in data.items() if value != "null"}
        if not data.get("is_public"):
            if data.get(Constants.SAMPLE_DATASET):
                if not csv_and_xlsx_file_validatation(
                    data.get(Constants.SAMPLE_DATASET)
                ):
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
            data[Constants.CATEGORY] = (
                json.loads(category) if isinstance(category, str) else category
            )
        instance = self.get_object()

        # trigger email to the participant
        user_map_queryset = UserOrganizationMap.objects.select_related(
            Constants.USER
        ).get(id=instance.user_map_id)
        user_obj = user_map_queryset.user

        # reset the approval status b/c the user modified the dataset after an approval
        if getattr(instance, Constants.APPROVAL_STATUS) == Constants.APPROVED and (
            user_obj.role_id == 3 or user_obj.role_id == 4
        ):
            data[Constants.APPROVAL_STATUS] = Constants.AWAITING_REVIEW

        serializer = DatasetUpdateSerializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        data = request.data

        if data.get(Constants.APPROVAL_STATUS) == Constants.APPROVED:
            self.trigger_email(
                request,
                "datahub_admin_approves_dataset.html",
                user_obj.email,
                Constants.APPROVED_NEW_DATASET_SUBJECT,
                user_obj.first_name,
                user_obj.last_name,
                instance.name,
            )

        elif data.get(Constants.APPROVAL_STATUS) == Constants.REJECTED:
            self.trigger_email(
                request,
                "datahub_admin_rejects_dataset.html",
                user_obj.email,
                Constants.REJECTED_NEW_DATASET_SUBJECT,
                user_obj.first_name,
                user_obj.last_name,
                instance.name,
            )

        elif data.get(Constants.IS_ENABLED) == str(True) or data.get(
            Constants.IS_ENABLED
        ) == str("true"):
            self.trigger_email(
                request,
                "datahub_admin_enables_dataset.html",
                user_obj.email,
                Constants.ENABLE_DATASET_SUBJECT,
                user_obj.first_name,
                user_obj.last_name,
                instance.name,
            )

        elif data.get(Constants.IS_ENABLED) == str(False) or data.get(
            Constants.IS_ENABLED
        ) == str("false"):
            self.trigger_email(
                request,
                "datahub_admin_disables_dataset.html",
                user_obj.email,
                Constants.DISABLE_DATASET_SUBJECT,
                user_obj.first_name,
                user_obj.last_name,
                instance.name,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        dataset = self.get_object()
        dataset.status = False
        self.perform_create(dataset)
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
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=500
            )

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
                Datasets.objects.values_list(Constants.GEOGRAPHY, flat=True)
                .filter(status=True, **filters)
                .exclude(geography="null")
                .exclude(geography__isnull=True)
                .exclude(geography="")
                .exclude(**exclude)
                .all()
                .distinct()
            )
            crop_detail = (
                Datasets.objects.values_list(Constants.CROP_DETAIL, flat=True)
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
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}", status=500
            )
        return Response(
            {"geography": geography, "crop_detail": crop_detail}, status=200
        )

    @action(detail=False, methods=["post"])
    def search_datasets(self, request, *args, **kwargs):
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")
        search_pattern = data.pop(Constants.SEARCH_PATTERNS, "")
        exclude, filters = {}, {}

        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            filters = (
                {Constants.NAME_ICONTAINS: search_pattern} if search_pattern else {}
            )
        else:
            filters = (
                {
                    Constants.USER_MAP_ORGANIZATION: org_id,
                    Constants.NAME_ICONTAINS: search_pattern,
                }
                if org_id
                else {}
            )
        try:
            data = (
                Datasets.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, status=True, **data, **filters)
                .exclude(**exclude)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        page = self.paginate_queryset(data)
        participant_serializer = DatahubDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)


class DatahubDashboard(GenericViewSet):
    """Datahub Dashboard viewset"""

    pagination_class = CustomPagination

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Retrieve datahub dashboard details"""
        try:
            # total_participants = User.objects.filter(role_id=3, status=True).count()
            total_participants = (
                UserOrganizationMap.objects.select_related(
                    Constants.USER, Constants.ORGANIZATION
                )
                .filter(user__role=3, user__status=True)
                .count()
            )
            total_datasets = (
                Datasets.objects.select_related(
                    "user_map", "user_map__user", "user_map__organization"
                )
                .filter(
                    user_map__user__status=True,
                    status=True,
                    approval_status="approved",
                    is_enabled=True,
                )
                .order_by("updated_at")
                .count()
            )
            # write a function to compute data exchange
            active_connectors = Connectors.objects.filter(status=True).count()
            total_data_exchange = {"total_data": 50, "unit": "Gbs"}

            datasets = Datasets.objects.filter(status=True).values_list(
                "category", flat=True
            )
            categories = set()
            categories_dict = {}

            for data in datasets:
                if data and type(data) == dict:
                    for element in data.keys():
                        categories.add(element)

            categories_dict = {key: 0 for key in categories}
            for data in datasets:
                if data and type(data) == dict:
                    for key, value in data.items():
                        if value == True:
                            categories_dict[key] += 1

            open_support_tickets = SupportTicket.objects.filter(status="open").count()
            closed_support_tickets = SupportTicket.objects.filter(
                status="closed"
            ).count()
            hold_support_tickets = SupportTicket.objects.filter(status="hold").count()

            # retrieve 3 recent support tickets
            recent_tickets_queryset = SupportTicket.objects.order_by("updated_at")[0:3]
            recent_tickets_serializer = RecentSupportTicketSerializer(
                recent_tickets_queryset, many=True
            )
            support_tickets = {
                "open_requests": open_support_tickets,
                "closed_requests": closed_support_tickets,
                "hold_requests": hold_support_tickets,
                "recent_tickets": recent_tickets_serializer.data,
            }

            # retrieve 3 recent updated datasets
            # datasets_queryset = Datasets.objects.order_by("updated_at")[0:3]
            datasets_queryset = (
                Datasets.objects.filter(status=True).order_by("-updated_at").all()
            )
            datasets_queryset_pages = self.paginate_queryset(
                datasets_queryset
            )  # paginaged connectors list
            datasets_serializer = RecentDatasetListSerializer(
                datasets_queryset_pages, many=True
            )

            data = {
                "total_participants": total_participants,
                "total_datasets": total_datasets,
                "active_connectors": active_connectors,
                "total_data_exchange": total_data_exchange,
                "categories": categories_dict,
                "support_tickets": support_tickets,
                "datasets": self.get_paginated_response(datasets_serializer.data).data,
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatasetV2ViewSet(GenericViewSet):
    """
    ViewSet for DatasetV2 model for create, update, detail/list view, & delete endpoints.

    **Context**
    ``DatasetV2``
        An instance of :model:`datahub_datasetv2`

    **Serializer**
    ``DatasetV2Serializer``
        :serializer:`datahub.serializer.DatasetV2Serializer`

    """

    serializer_class = DatasetV2Serializer
    queryset = DatasetV2.objects.all()

    def create(self, request, *args, **kwargs):
        """
        ``POST`` method Endpoint: create action to save the Dataset's Meta data
            with datasets sent through POST request. [see here][ref].

        **Endpoint**
        [ref]: /datahub/v2/dataset/

        **Authorization**
        ``ROLE`` only authenticated users/participants with following roles are allowed to make a POST request to this endpoint.
            :role: `datahub_admin` (:role_id: `1`)
            :role: `datahub_participant_root` (:role_id: `3`)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """
        ``GET`` method Endpoint: list action to view the list of Datasets via GET request. [see here][ref].

        **Endpoint**
        [ref]: /datahub/v2/dataset/

        **Authorization**
        ``ROLE`` only authenticated users/participants with following roles are allowed to make a GET request to this endpoint.
            :role: `datahub_admin` (:role_id: `1`)
            :role: `datahub_participant_root` (:role_id: `3`)
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        ``GET`` method Endpoint: retrieve action for the detail view of Dataset via GET request. [see here][ref].

        **Endpoint**
        [ref]: /datahub/v2/dataset/<id>/

        **Authorization**
        ``ROLE`` only authenticated users/participants with following roles are allowed to make a GET request to this endpoint.
            :role: `datahub_admin` (:role_id: `1`)
            :role: `datahub_participant_root` (:role_id: `3`)
        """
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)
