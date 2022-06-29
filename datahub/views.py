import logging, os, shutil, json
from calendar import c
import django
from accounts.models import User, UserRole
from accounts.serializers import UserCreateSerializer
from core.constants import Constants
from core.utils import Utils
from django.conf import settings
from django.contrib.admin.utils import get_model_from_relation
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import DEFERRED, F
from django.db import transaction
from drf_braces.mixins import MultipleSerializersViewMixin
from participant.models import SupportTicket
from participant.serializers import (
    ParticipantSupportTicketSerializer,
    TicketSupportSerializer,
)
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial
from utils import file_operations, validators

from datahub.models import DatahubDocuments, Organization, UserOrganizationMap
from datahub.serializers import (
    DatahubThemeSerializer,
    DropDocumentSerializer,
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
    queryset = User.objects.filter(status=False)
    pagination_class = DefaultPagination
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        # print(request.data)
        # request.data["role"] = UserRole.objects.get(role_name=request.data["role"]).id
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

        # team_member.role = UserRole.objects.get(role_name=team_member.role).id
        serializer = self.get_serializer(team_member)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        # request.data["role"] = UserRole.objects.get(role_name=request.data["role"]).id
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        team_member = self.get_object()
        team_member.status = True
        # team_member.delete()
        team_member.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationViewSet(GenericViewSet):
    """
    Organisation Viewset.
    """

    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    pagination_class = DefaultPagination
    # permission_classes = [IsAuthenticated]

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
    # permission_classes = [IsAuthenticated]

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
            UserOrganizationMap.objects.select_related(
                Constants.USER, Constants.ORGANIZATION
            )
            .filter(user__status=False, user__role=3)
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
        product.status = True
        self.perform_create(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MailInvitationViewSet(GenericViewSet):
    """
    This class handles the mail invitation API views.
    """

    # permission_classes = [IsAuthenticated]

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
    # permission_classes = [IsAuthenticated]

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
        try:
            key = list(request.data.keys())[0]
            file_operations.remove_files(request.data[key], settings.TEMP_FILE_PATH)

            return Response({}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            LOGGER.error(e)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class DocumentSaveView(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = PolicyDocumentSerializer
    queryset = DatahubDocuments.objects.all()
    # permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        datahub_documents = self.get_object()
        serializer = self.get_serializer(datahub_documents)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()
            # save the document files
            file_operations.files_move(settings.TEMP_FILE_PATH, settings.STATIC_ROOT)

            return Response(
                {"message": "Documents and content saved!"},
                status=status.HTTP_201_CREATED,
            )

    def update(self, request, *args, **kwargs):
        """Saves the document content and files"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()
            # save the document files
            file_operations.files_move(settings.TEMP_FILE_PATH, settings.STATIC_ROOT)

            return Response(
                {"message": "Documents and content updated!"},
                status=status.HTTP_201_CREATED,
            )


class DatahubThemeView(GenericViewSet):
    """View for modifying datahub branding"""

    parser_class = MultiPartParser
    serializer_class = DatahubThemeSerializer
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """generates the override css for datahub"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.filter(email=data["email"])
        user = user.first()

        try:
            # get file, file name & type from the form-data
            file_key = list(request.FILES.keys())[0]
            file = data[file_key]
            file_type = data[file_key].content_type.split("/")[1]
            file_name = str(file_key) + "." + file_type

            # CSS generation
            # text_fields = []
            # for count in range(len(data.keys())):
            #     key = list(data.keys())[count]
            #     # get only text data fields and append them to text_fields list
            #     if type(data[key]) is not InMemoryUploadedFile:
            #         text_fields.append(data[key])
            #     count += 1

            with transaction.atomic():
                # save datahub banner image
                file_operations.file_save(file, file_name, settings.STATIC_ROOT)

                # save or override the CSS
                css = ".btn { background-color: " + data["button_color"] + "; }"
                file_operations.file_save(
                    ContentFile(css),
                    settings.CSS_FILE_NAME,
                    settings.STATIC_ROOT,
                )

                # set user status to True
                user.status = True
                user.save()

                return Response(
                    {"message": "Theme saved!"}, status=status.HTTP_201_CREATED
                )

        except Exception as e:
            LOGGER.error(e)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class SupportViewSet(GenericViewSet):
    """
    This class handles the participant support tickets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = TicketSupportSerializer
    queryset = SupportTicket
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        # roles = SupportTicket.objects.prefetch_related("user").filter(user__status=False).all()
        data = (
            SupportTicket.objects.select_related(
                Constants.USER_MAP,
                Constants.USER_MAP_USER,
                Constants.USER_MAP_ORGANIZATION,
            )
            .filter(user_map__user__status=False, **request.GET)
            .order_by("updated_at")
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
            .filter(user_map__user__status=False, id=pk)
            .all()
        )
        participant_serializer = ParticipantSupportTicketSerializer(data, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)
