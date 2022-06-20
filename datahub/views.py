import json
import logging
import os
import shutil
from calendar import c

import django
from accounts.models import User, UserRole
from accounts.serializers import UserCreateSerializer
from core.constants import Constants
from core.utils import Utils
from django.conf import settings
from django.contrib.admin.utils import get_model_from_relation
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db.models import DEFERRED, F
from drf_braces.mixins import MultipleSerializersViewMixin
from rest_framework import pagination, status
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial

from datahub.models import Organization, UserOrganizationMap
from datahub.serializers import (
    OrganizationSerializer,
    ParticipantSerializer,
    PolicyDocumentSerializer,
    UserOrganizationMapSerializer,
)

LOGGER = logging.getLogger(__name__)


class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """

    page_size = 5


class TeamMemberViewSet(GenericViewSet):
    """Viewset for Product model"""

    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    pagination_class = DefaultPagination

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        team_member = self.get_object()
        serializer = self.get_serializer(team_member)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        team_member = self.get_object()
        team_member.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationViewSet(GenericViewSet):
    """
    Organisation Viewset.
    """

    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    pagination_class = DefaultPagination

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        organization = self.get_object()
        serializer = self.get_serializer(organization)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
    pagination_class = DefaultPagination

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
            serializer = OrganizationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            org_queryset = self.perform_create(serializer)
            org_id = org_queryset.id
        else:
            org_id = org_queryset[0].get(Constants.ID)
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_saved = self.perform_create(serializer)

        user_org_serializer = UserOrganizationMapSerializer(
            data={Constants.USER: user_saved.id, Constants.ORGANIZATION: org_id}
        )
        user_org_serializer.is_valid(raise_exception=True)
        self.perform_create(user_org_serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        roles = (
            UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=False, user__role=3)
            .all()
        )
        page = self.paginate_queryset(roles)
        participant_serializer = ParticipantSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        roles = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=False, user__role=3, user=pk)
            .all()
        )
        participant_serializer = ParticipantSerializer(roles, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        organization = OrganizationSerializer(
            Organization.objects.get(id=request.data.get(Constants.ID)), data=request.data, partial=None
        )
        organization.is_valid(raise_exception=True)
        self.perform_create(organization)
        data = {Constants.USER: serializer.data, Constants.ORGANIZATION: organization.data}
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = True
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

    def create(self, request, *args, **kwargs):
        """Saves the document files in temp location before saving"""
        try:
            # get file, file name & type from the form-data
            file_key = list(request.data.keys())[0]
            file_uploaded = request.data[file_key]
            file_type = file_uploaded.content_type.split("/")[1]

            if file_uploaded.size > settings.FILE_UPLOAD_MAX_SIZE * 1000000:
                return Response({"message: please upload file with size lesser than 2MB"})
            # check for file types (pdf, doc, docx)
            elif file_type not in settings.FILE_TYPES_ALLOWED:
                return Response({"message: Please upload only pdf or doc files"})
            else:
                fs = FileSystemStorage(
                    settings.TEMP_FILE_PATH,
                    directory_permissions_mode=0o755,
                    file_permissions_mode=0o755,
                )
                file_name = str(file_key) + "." + file_type

                # replace if the files exist
                if fs.exists(file_name):
                    fs.delete(file_name)
                    fs.save(file_name, file_uploaded)
                    return Response({"message: uploading...."}, status=status.HTTP_201_CREATED)

                fs.save(file_name, file_uploaded)
                return Response({"message: uploading...."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            LOGGER.error(e)

        return Response(
            {"message: encountered an error while uploading"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DocumentSaveView(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = PolicyDocumentSerializer

    def create(self, request, *args, **kwargs):
        """Saves the document content and files"""
        try:
            serializer = PolicyDocumentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            for root, dirs, files in os.walk(settings.TEMP_FILE_PATH):
                for file in files:
                    # save the files in the destination directory
                    shutil.copyfile(root + file, settings.STATIC_ROOT + file)
                    os.remove(root + file)

            return Response({"message: Document content saved!"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            LOGGER.error(e)

        return Response({"message: not allowed"}, status=status.HTTP_400_BAD_REQUEST)


class DatahubThemeView(GenericViewSet):
    """View for modifying datahub branding"""

    parser_class = MultiPartParser

    def create(self, request, *args, **kwargs):
        """generates the override css for datahub"""
        try:
            hero_image = request.data["hero_image"]
            button_color = request.data["button_color"]
            file_type = hero_image.content_type.split("/")[1]

            if hero_image.size > settings.FILE_UPLOAD_MAX_SIZE * 1000000:
                return Response({"message: please upload file with size lesser than 2MB"})
            # check for image file types (jpg, jpeg, png)
            elif file_type not in settings.IMAGE_TYPES_ALLOWED:
                return Response({"message: Please upload only jpg or jpeg or png files"})
            else:
                fs = FileSystemStorage(settings.STATIC_ROOT)
                css = ".btn { background-color: " + button_color + "; }"

                # override if the files exist
                if fs.exists(str(hero_image)) and fs.exists(settings.CSS_FILE_NAME):
                    fs.delete(str(hero_image))
                    fs.delete(settings.CSS_FILE_NAME)
                    fs.save(settings.CSS_FILE_NAME, ContentFile(css))
                    fs.save(str(hero_image), hero_image)

                    return Response(
                        "Successfully created the brand identity",
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    fs.save(str(hero_image), hero_image)
                    fs.save(settings.CSS_FILE_NAME, ContentFile(css))
                    return Response(
                        "Successfully created the brand identity",
                        status=status.HTTP_201_CREATED,
                    )

        except Exception as e:
            LOGGER.error(e)
