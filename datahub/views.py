import ast
import json
import logging
import operator
import os
import re
import shutil
import sys
from calendar import c
from functools import reduce

import django
import pandas as pd
from django.conf import settings
from django.contrib.admin.utils import get_model_from_relation
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import DEFERRED, F, Q
from django.shortcuts import render
from drf_braces.mixins import MultipleSerializersViewMixin
from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from python_http_client import exceptions
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial

from accounts.models import User, UserRole
from accounts.serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from core.constants import Constants
from core.settings import BASE_DIR
from core.utils import (
    CustomPagination,
    Utils,
    csv_and_xlsx_file_validatation,
    date_formater,
    read_contents_from_csv_or_xlsx_file,
)
from datahub.models import (
    DatahubDocuments,
    Datasets,
    DatasetV2,
    DatasetV2File,
    Organization,
    UserOrganizationMap,
)
from datahub.serializers import (
    DatahubDatasetsSerializer,
    DatahubDatasetsV2Serializer,
    DatahubThemeSerializer,
    DatasetSerializer,
    DatasetUpdateSerializer,
    DatasetV2Serializer,
    DatasetV2TempFileSerializer,
    DatasetV2Validation,
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
)
from participant.models import Connectors, SupportTicket
from participant.serializers import (
    ParticipantSupportTicketSerializer,
    TicketSupportSerializer,
)
from utils import custom_exceptions, file_operations, string_functions, validators

LOGGER = logging.getLogger(__name__)

con = None

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
            if user_saved.on_boarded_by:
                # datahub_admin = User.objects.filter(id=user_saved.on_boarded_by).first()
                admin_full_name = string_functions.get_full_name(
                    user_saved.on_boarded_by.first_name, user_saved.on_boarded_by.last_name
                )
            else:   
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
                "as_user": "Co-Steward" if user_saved.role == 6 else "Participant",
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
        on_boarded_by = request.GET.get("on_boarded_by", None)
        co_steward = request.GET.get("co_steward", False)
        if on_boarded_by:
            roles = (
                UserOrganizationMap.objects.select_related(
                    Constants.USER, Constants.ORGANIZATION
                )
                .filter(user__status=True, user__on_boarded_by=on_boarded_by, user__role=3)
                .all()
            )
        elif co_steward:
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
        user_data = self.perform_create(user_serializer)
        self.perform_create(organization_serializer)
        try:
            if user_data.on_boarded_by:
                admin_full_name = string_functions.get_full_name(
                    user_data.first_name, user_data.last_name
                )
            else:   
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

        if participant.status:

            participant.status = False
            organization.status = False

            try:
                if participant.on_boarded_by:
                    datahub_admin = User.objects.filter(id=participant.on_boarded_by).first()
                else:
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
                    {"message": ["Internal server error"]}, status=500
                )

        elif participant.status is False:
            return Response(
                {"message": ["participant/co-steward already deleted"]},
                status=status.HTTP_204_NO_CONTENT,
            )

        return Response({"message": ["Internal server error"]}, status=500)


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
            file_operations.remove_files(file_name, settings.TEMP_FILE_PATH)
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
                file_operations.create_directory(settings.DOCUMENTS_ROOT, [])
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
                file_operations.create_directory(settings.DOCUMENTS_ROOT, [])
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
                file_name = file_operations.file_rename(str(banner), "banner")
                file_operations.remove_files(file_name, settings.THEME_ROOT)
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)
                data = {"banner": file_name, "button_color": "null"}

            elif not banner and button_color:
                css = ".btn { background-color: " + button_color + "; }"
                file_operations.remove_files(file_name, settings.THEME_ROOT)
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.CSS_ROOT,
                )
                data = {"banner": "null", "button_color": settings.CSS_FILE_NAME}

            elif banner and button_color:
                file_name = file_operations.file_rename(str(banner), "banner")
                file_operations.remove_files(file_name, settings.THEME_ROOT)
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)

                css = ".btn { background-color: " + button_color + "; }"
                file_operations.remove_files(file_name, settings.THEME_ROOT)
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
                file_name = file_operations.file_rename(str(banner), "banner")
                file_operations.remove_files(file_name, settings.THEME_ROOT)
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)
                data = {"banner": file_name, "button_color": "null"}

            elif not banner and button_color:
                css = ".btn { background-color: " + button_color + "; }"
                file_operations.remove_files(settings.CSS_FILE_NAME, settings.CSS_ROOT)
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.CSS_ROOT,
                )
                data = {"banner": "null", "button_color": settings.CSS_FILE_NAME}

            elif banner and button_color:
                file_name = file_operations.file_rename(str(banner), "banner")
                file_operations.remove_files(file_name, settings.THEME_ROOT)
                file_operations.file_save(banner, file_name, settings.THEME_ROOT)

                css = ".btn { background-color: " + button_color + "; }"
                file_operations.remove_files(settings.CSS_FILE_NAME, settings.CSS_ROOT)
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
        try:
            data = (
                SupportTicket.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, **request.data)
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
        categories = data.pop(Constants.CATEGORY, None)
        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
      
        try:
            if categories is not None:

                data = (
                    Datasets.objects.select_related(
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
                    Datasets.objects.select_related(
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
            {
                "geography": geography,
                "crop_detail": crop_detail,
                "category_detail": category_detail,
            },
            status=200,
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

    **Authorization**
        ``ROLE`` only authenticated users/participants with following roles are allowed to make a POST request to this endpoint.
            :role: `datahub_admin` (:role_id: `1`)
            :role: `datahub_participant_root` (:role_id: `3`)
    """

    serializer_class = DatasetV2Serializer
    queryset = DatasetV2.objects.all()
    pagination_class = CustomPagination

    @action(detail=False, methods=["post"])
    def validate_dataset(self, request, *args, **kwargs):
        """
        ``POST`` method Endpoint: POST method to check the validation of dataset name and dataset description. [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/dataset_validation/
        """
        serializer = DatasetV2Validation(
            data=request.data,
            context={
                "request_method": request.method,
                 "dataset_exists": request.query_params.get("dataset_exists"),
                 "queryset": self.queryset,
                },
            )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=["post", "delete"])
    def temp_datasets(self, request, *args, **kwargs):
        """
        ``POST`` method Endpoint: POST method to save the datasets in a temporary location with
            under a newly created dataset name & source_file directory.
        ``DELETE`` method Endpoint: DELETE method to delete the dataset named directory containing
            the datasets. [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/temp_datasets/
        """
        try:
            files = request.FILES.getlist("datasets")

            if request.method == "POST":
                """Create a temporary directory containing dataset files uploaded as source.
                ``Example:``
                    Create below directories with dataset files uploaded
                    /temp/<dataset-name>/file/<files>
                """
                # serializer = DatasetV2TempFileSerializer(data=request.data, context={"request_method": request.method})
                serializer = DatasetV2TempFileSerializer(
                    data=request.data,
                    context={
                        "request_method": request.method,
                        "dataset_exists": request.query_params.get("dataset_exists"),
                        "queryset": self.queryset,
                    },
                )
                if not serializer.is_valid():
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                directory_created = file_operations.create_directory(
                    settings.TEMP_DATASET_URL,
                    [
                        serializer.data.get("dataset_name"),
                        serializer.data.get("source"),
                    ],
                )

                files_saved = []
                for file in files:
                    file_operations.file_save(file, file.name, directory_created)
                    files_saved.append(file.name)

                data = {"datasets": files_saved}
                data.update(serializer.data)
                return Response(data, status=status.HTTP_201_CREATED)

            elif request.method == "DELETE":
                """
                Delete the temporary directory containing datasets created by the POST endpoint
                with the dataset files uploaded as source.
                ``Example:``
                    Delete the below directory:
                    /temp/<dataset-name>/
                """
                serializer = DatasetV2TempFileSerializer(
                    data=request.data,
                    context={
                        "request_method": request.method,
                        "query_params": request.query_params.get("delete_dir"),
                    },
                )

                if not serializer.is_valid():
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                directory = string_functions.format_dir_name(
                    settings.TEMP_DATASET_URL, [request.data.get("dataset_name")]
                )

                """Delete directory temp directory as requested"""
                if request.query_params.get("delete_dir") and os.path.exists(directory):
                    shutil.rmtree(directory)
                    LOGGER.info(f"Deleting directory: {directory}")
                    data = {request.data.get("dataset_name"): "Dataset not created"}
                    return Response(data, status=status.HTTP_204_NO_CONTENT)

                elif not request.query_params.get("delete_dir"):
                    """Delete a single file as requested"""
                    file_name = request.data.get("file_name")
                    file_path = os.path.join(
                        directory, request.data.get("source"), file_name
                    )
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        LOGGER.info(f"Deleting file: {file_name}")
                        data = {file_name: "File deleted"}
                        return Response(data, status=status.HTTP_204_NO_CONTENT)

                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get", "post"])
    def category(self, request, *args, **kwargs):
        """
        ``GET`` method: GET method to retrieve the dataset category & sub categories from JSON file obj
        ``POST`` method: POST method to create and/or edit the dataset categories &
            sub categories and finally write it to JSON file obj. [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/category/
        [JSON File Object]: "/categories.json"
        """
        if request.method == "GET":
            try:
                with open(Constants.CATEGORIES_FILE, "r") as json_obj:
                    data = json.loads(json_obj.read())
                return Response(data, status=status.HTTP_200_OK)
            except Exception as error:
                LOGGER.error(error, exc_info=True)
                raise custom_exceptions.NotFoundException(detail="Categories not found")
        elif request.method == "POST":
            try:
                data = request.data
                with open(Constants.CATEGORIES_FILE, "w+", encoding="utf8") as json_obj:
                    json.dump(data, json_obj, ensure_ascii=False)
                    LOGGER.info(f"Updated Categories: {Constants.CATEGORIES_FILE}")
                return Response(data, status=status.HTTP_201_CREATED)
            except Exception as error:
                LOGGER.error(error, exc_info=True)
                raise exceptions.InternalServerError("Internal Server Error")

    def create(self, request, *args, **kwargs):
        """
        ``POST`` method Endpoint: create action to save the Dataset's Meta data
            with datasets sent through POST request. [see here][ref].

        **Endpoint**
        [ref]: /datahub/dataset/v2/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk, *args, **kwargs):
        """
        ``PUT`` method: PUT method to edit or update the dataset (DatasetV2) and its files (DatasetV2File). [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/<uuid>
        """
        # setattr(request.data, "_mutable", True)
        data = request.data
        to_delete = ast.literal_eval(data.get("deleted", "[]"))
        self.dataset_files(data, to_delete)
        datasetv2 = self.get_object()
        serializer = self.get_serializer(datasetv2, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"])
    def dataset_files(self, request, id=[]):
        """
        ``DELETE`` method: DELETE method to delete the dataset files (DatasetV2File) referenced by DatasetV2 model. [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/dataset_files/
        """
        ids = {}
        for file_id in id:
            dataset_file = DatasetV2File.objects.filter(id=int(file_id))
            if dataset_file.exists():
                LOGGER.info(f"Deleting file: {dataset_file[0].id}")
                file_path = os.path.join("media", str(dataset_file[0].file))
                if os.path.exists(file_path):
                    os.remove(file_path)
                dataset_file.delete()
                ids[file_id] = "File deleted"
        return Response(ids, status=status.HTTP_204_NO_CONTENT)

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
            file_path["id"] = file.id
            file_path["content"] = read_contents_from_csv_or_xlsx_file(path_)
            file_path["file"] = path_
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
        on_boarded_by = data.pop("on_boarded_by", "")

        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            data = DatasetV2.objects.select_related(
            Constants.USER_MAP,
            Constants.USER_MAP_USER,
            Constants.USER_MAP_ORGANIZATION,
            ).filter(status=True, **data, **filters).exclude(**exclude).order_by(Constants.UPDATED_AT).reverse().all()
            if on_boarded_by:
                data = data.filter(user_map__user__on_boarded_by=on_boarded_by) if not others else data.filter(
                    Q(user_map__user__on_boarded_by=on_boarded_by) | Q(user_map__user_id=on_boarded_by)
                )
            if categories is not None:
                data = data.filter(
                    reduce(
                        operator.or_,
                        (Q(category__contains=cat) for cat in categories),
                    )
                )
            # else:
            #     data = data.exclude(**exclude).order_by(Constants.UPDATED_AT).reverse().all()
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error, exc_info=True)
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
                DatasetV2.objects.select_related(
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
            page = self.paginate_queryset(data)
            participant_serializer = DatahubDatasetsV2Serializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

 
    def destroy(self, request, pk, *args, **kwargs):
        """
        ``DELETE`` method: DELETE method to delete the DatasetV2 instance and its reference DatasetV2File instances,
        along with dataset files stored at the URL. [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/
        """
        dataset_obj = self.get_object()
        if dataset_obj:
            dataset_files = DatasetV2File.objects.filter(dataset_id=dataset_obj.id)
            dataset_dir = os.path.join(
                settings.DATASET_FILES_URL, str(dataset_obj.name)
            )

            if os.path.exists(dataset_dir):
                shutil.rmtree(dataset_dir)
                LOGGER.info(f"Deleting file: {dataset_dir}")

            # delete DatasetV2File & DatasetV2 instances
            LOGGER.info(f"Deleting dataset obj: {dataset_obj}")
            dataset_files.delete()
            dataset_obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=False, methods=["post"])
    def create_db(self, request, *args, **kwargs):
        try:
            data = request.data
            # con = connect(dbname=data.get("org"), user='postgres', host='datahubtest.farmstack.co', password='$farmstack@!21')
            db_settings = open("/datahub/core/settings.json") 
            db_data = json.load(db_settings)
            db_data[data.get("org")] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": data.get("org"),
            "USER": "postgres",
            "PASSWORD": "$farmstack@!21",
            "HOST": "datahubethdev.farmstack.co",
            "PORT": 7000,
            "OPTIONS": {
                "client_encoding": "UTF8",
            }
        }
            with open('../datahub/core/settings.json', 'w') as fp:
                json.dump(db_data, fp)
            import ruamel.yaml

            file_name = '../datahub/test_db.yaml'
            print(file_name)
            config, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(open(file_name))
            # print(config)

            instances = config['services']["datahub-be"]
            commands = [f" && python manage.py migrate --dataset {keys}" for keys in db_data.keys()]
            print(commands)
            command = instances['command'].replace("&& python manage.py migrate", " ".join(commands))
        
            instances['command'] = command

            from python_on_whales import DockerClient

            yaml = ruamel.yaml.YAML()
            yaml.indent(mapping=ind, sequence=ind, offset=bsi) 
            with open('../datahub/test_db.yaml', 'w') as fp:
                yaml.dump(config, fp)
            # docker_clients_consumer = DockerClient(compose_files=["../datahub/test_db.yaml"])
            # # print(docker_clients)
            # docker_clients_consumer.compose.stop()

            import signal

            # def sigterm_handler(_signo, _stack_frame):
            #     # Raises SystemExit(0):
            #     sys.exit(0)
            # signal.signal(signal.SIGTERM, sigterm_handler)
            os.popen("docker stop 43f56891b063")
            # atexit.register(exit_handler)            # docker_clients_consumer.compose.restart() # type: ignore
            return Response({}, 200)
        except Exception as e:
            logging.error(str(e), exc_info=True)
            return Response({}, 500)


class DatasetV2ViewSetOps(GenericViewSet):
    """
        A viewset for performing operations on datasets with Excel files.

        This viewset supports the following actions:

        - `dataset_names`: Returns the names of all datasets that have at least one Excel file.
        - `dataset_file_names`: Given two dataset names, returns the names of all Excel files associated with each dataset.
        - `dataset_col_names`: Given the paths to two Excel files, returns the column names of each file as a response.
        - `dataset_join_on_columns`: Given the paths to two Excel files and the names of two columns, returns a JSON response with the result of an inner join operation on the two files based on the selected columns.
        """

    serializer_class = DatasetV2Serializer
    queryset = DatasetV2.objects.all()
    pagination_class = CustomPagination


 
    @action(detail=False, methods=["post"])
    def datasets_names(self, request, *args, **kwargs):
        datasets_with_excel_files = DatasetV2.objects.select_related(DatasetV2File).filter(Q(datasetv2file__file__endswith='.xls') | Q(datasetv2file__file__endswith='.xlsx'))

        try:
            datasets_with_excel_files = DatasetV2.objects.select_related(DatasetV2File).filter(Q(datasetv2file__file__endswith='.xls') | Q(datasetv2file__file__endswith='.xlsx'))
            import pdb;pdb.set_trace()
            # dataset_list = [{'dataset_name': dataset_name, 'id': dataset_id} for dataset_name, dataset_id in datasets_with_excel_files]
            return Response(datasets_with_excel_files, status=status.HTTP_200_OK)
        except Exception as e:
            error_message = f"An error occurred while fetching dataset names: {e}"
            print(e)
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=["post"])
    def datasets_file_names(self,request,*args,**kwargs):
        try:
            d1_id = request.data.get("dataset_id1")
            d2_id = request.data.get("dataset_id2")

            # Check if datasets exist
            d1 = DatasetV2.objects.get(id=d1_id)
            d2 = DatasetV2.objects.get(id=d2_id)

            # Get list of files for each dataset
            files1 = DatasetV2File.objects.filter(dataset_id=d1).filter(Q(file__endswith='.xls') | Q(file__endswith='.xlsx'))
            files2 = DatasetV2File.objects.filter(dataset_id=d2).filter(Q(file__endswith='.xls') | Q(file__endswith='.xlsx'))

            # Create response data with list of files
            response_data = {
                "id": d1_id,
                "files": [{"file_name": os.path.basename(file.file.name), "file": file.file.url} for file in files1]
            }
            response_data2 = {
                "id": d2_id,
                "files": [{"file_name": os.path.basename(file.file.name), "file": file.file.url} for file in files2]
            }

            # Return response
            return Response({"files1":response_data,"files2":response_data2}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=["post"])
    def datasets_col_names(self, request, *args, **kwargs):
        import ast
        try:
            file_paths = ast.literal_eval(request.data.get("file_paths"))
            result = {}
            for file_path in file_paths:
                df = pd.read_excel(file_path)
                result[file_path] = df.columns.tolist()

            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



    @action(detail=False, methods=["post"])
    def datasets_join_condition(self, request, *args, **kwargs):
        try:
            file_path1 = request.data.get("file_path1")
            file_path2 = request.data.get("file_path2")
            columns1 = ast.literal_eval(request.data.get("columns1"))
            columns2 = ast.literal_eval(request.data.get("columns2"))
            condition = request.data.get("condition")

            # Load the files into dataframes
            df1 = pd.read_excel(file_path1, usecols=columns1)
            df2 = pd.read_excel(file_path2, usecols=columns2)

            # Join the dataframes
            result = pd.merge(df1, df2, on=condition)

            # Return the joined dataframe as JSON
            return Response(result.to_json(orient="records"), status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
