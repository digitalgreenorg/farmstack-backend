from accounts.models import User
from core.constants import Constants
from core.utils import DefaultPagination
from datahub.models import Organization, UserOrganizationMap
from datahub.serializers import (
    OrganizationSerializer,
    ParticipantSerializer,
    PolicyDocumentSerializer,
    UserOrganizationMapSerializer,
)
from rest_framework import pagination, status
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial

from participant.models import SupportTicket
from participant.serializers import (
    ParticipantSupportTicketSerializer,
    TicketSupportSerializer,
)


class ParticipantSupportViewSet(GenericViewSet):
    """
    This class handles the participant CRUD operations.
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

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        user_id = request.GET.get(Constants.USER_ID)
        data = (
            SupportTicket.objects.select_related(Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION)
            .filter(user_map__user__status=False, user_map__user=user_id).order_by(Constants.UPDATED_AT)
            .all()
        )
        page = self.paginate_queryset(data)
        participant_serializer = ParticipantSupportTicketSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        data = (
            SupportTicket.objects.select_related(Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION)
            .filter(user_map__user__status=False, id=pk)
            .all()
        )
        participant_serializer = ParticipantSupportTicketSerializer(data, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
