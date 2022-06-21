from calendar import c
from django.core.files.uploadedfile import InMemoryUploadedFile
import django
from accounts.models import User, UserRole
from accounts.serializers import UserCreateSerializer
from core.utils import Utils
from django.contrib.admin.utils import get_model_from_relation
from django.db.models import F
from drf_braces.mixins import MultipleSerializersViewMixin
import logging

from accounts.models import User
from accounts.serializers import UserCreateSerializer
from django.conf import settings
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.parsers import (
    MultiPartParser,
    FileUploadParser,
    JSONParser,
    FormParser,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSet
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from datahub.models import Organization, UserOrganizationMap, DatahubDocuments
from datahub.serializers import (
    OrganizationSerializer,
    ParticipantSerializer,
    UserOrganizationMapSerializer,
    PolicyDocumentSerializer,
    DropDocumentSerializer,
    DatahubThemeSerializer,
)
import logging, os, shutil
from utils import file_operations, validators

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
    """Viewset for Product model"""

    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        # self.retrieve(request, request.data.get("email", ""))
        # filter email from the queryset
        org_queryset = list(
            Organization.objects.filter(
                org_email=self.request.data.get("org_email", "")
            ).values()
        )
        if not org_queryset:
            serializer = OrganizationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            org_queryset = self.perform_create(serializer)
            org_id = org_queryset.id
        else:
            org_id = org_queryset[0].get("id")
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_saved = self.perform_create(serializer)

        user_org_serializer = UserOrganizationMapSerializer(
            data={"user": user_saved.id, "organization": org_id}
        )
        user_org_serializer.is_valid(raise_exception=True)
        self.perform_create(user_org_serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        roles = (
            UserOrganizationMap.objects.select_related("user", "organization")
            .filter(user__status=False)
            .all()
        )
        page = self.paginate_queryset(roles)
        if page is not None:
            participant_serializer = ParticipantSerializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)

        participant_serializer = ParticipantSerializer(roles, many=True)
        return Response(participant_serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            roles = UserOrganizationMap.objects.prefetch_related(
                "user", "organization"
            ).filter(user__status=False, user=pk)
        except django.core.exceptions.ValidationError as error:
            return Response(error, status=400)

        participant_serializer = ParticipantSerializer(roles, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = True
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MailInvitationViewSet(GenericViewSet):
    """_summary_

    Args:
        GenericViewSet (_type_): _description_
    """

    def create(self, request, *args, **kwargs):
        """_summary_

        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_
        """
        data = request.data
        return Utils().send_email(
            to_email=data.get("to_email", []),
            content=data.get("content"),
            subject="Participant Invitation",
        )


class DropDocumentView(GenericViewSet):
    """View for uploading organization document files"""

    parser_class = MultiPartParser
    serializer_class = DropDocumentSerializer

    def create(self, request, *args, **kwargs):
        """Saves the document files in temp location before saving"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # get file, file name & type from the form-data
        key = list(request.data.keys())[0]
        file = serializer.validated_data[key]
        file_type = serializer.validated_data[key].content_type.split("/")[1]
        file_name = str(key) + "." + file_type
        file_operations.file_save(file, file_name, settings.TEMP_FILE_PATH)

        return Response(
            {key: "uploading in progress..."}, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["delete"])
    def delete(self, request):
        """remove the dropped documents"""
        file_key = list(request.data.keys())[0]
        file_operations.remove_files(file_key, settings.TEMP_FILE_PATH)

        return Response({}, status=status.HTTP_204_NO_CONTENT)


class DocumentSaveView(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = PolicyDocumentSerializer
    queryset = DatahubDocuments.objects.all()

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        organization = self.get_object()
        serializer = self.get_serializer(organization)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # def create(self, request, *args, **kwargs):
    def update(self, request, *args, **kwargs):
        """Saves the document content and files"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # save the document files
        file_operations.files_move(settings.TEMP_FILE_PATH, settings.STATIC_ROOT)

        return Response(
            {"message": "Documents and content saved!"}, status=status.HTTP_201_CREATED
        )


class DatahubThemeView(GenericViewSet):
    """View for modifying datahub branding"""

    parser_class = MultiPartParser
    serializer_class = DatahubThemeSerializer

    def create(self, request, *args, **kwargs):
        """generates the override css for datahub"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # get file, file name & type from the form-data
        file_key = list(request.FILES.keys())[0]
        file = data[file_key]
        file_type = data[file_key].content_type.split("/")[1]
        file_name = str(file_key) + "." + file_type

        # save datahub banner image
        file_operations.file_save(file, file_name, settings.STATIC_ROOT)

        # CSS generation
        text_fields = []
        for count in range(len(data.keys())):
            key = list(data.keys())[count]
            # get only text data fields and append them to text_fields list
            if type(data[key]) is not InMemoryUploadedFile:
                text_fields.append(data[key])
            count += 1

        # save or override the CSS
        css = ".btn { background-color: " + text_fields[0] + "; }"
        file_operations.file_save(
            ContentFile(css), settings.CSS_FILE_NAME, settings.STATIC_ROOT
        )

        return Response({"message": "Theme saved!"}, status=status.HTTP_201_CREATED)
