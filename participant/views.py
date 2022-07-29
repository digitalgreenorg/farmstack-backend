import logging
from struct import unpack

import pandas as pd
from accounts.models import User
from core.constants import Constants
from core.utils import (
    CustomPagination,
    DefaultPagination,
    csv_and_xlsx_file_validatation,
    date_formater,
    read_contents_from_csv_or_xlsx_file,
)
from datahub.models import Datasets, Organization, UserOrganizationMap
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial

from participant.models import SupportTicket
from participant.serializers import (
    DatasetSerializer,
    ParticipantDatasetsDetailSerializer,
    ParticipantDatasetsSerializer,
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

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        user_id = request.GET.get(Constants.USER_ID)
        data = (
            SupportTicket.objects.select_related(
                Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION
            )
            .filter(user_map__user__status=True, user_map__user=user_id)
            .order_by(Constants.UPDATED_AT)
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

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ParticipantDatasetsViewSet(GenericViewSet):
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
        if not csv_and_xlsx_file_validatation(request.data.get(Constants.SAMPLE_DATASET)):
            return Response(
                {
                    Constants.SAMPLE_DATASET: [
                        "Invalid Sample dataset file (or) Atleast 5 rows should be available. please upload valid file"
                    ]
                },
                400,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        user_id = request.query_params.get(Constants.USER_ID, "")
        org_id = request.query_params.get(Constants.ORG_ID)
        exclude = {Constants.USER_MAP_USER: user_id} if org_id else {}
        filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {Constants.USER_MAP_USER: user_id}
        if filters:
            data = (
                Datasets.objects.select_related(
                    Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION
                )
                .filter(user_map__user__status=True, status=True, **filters)
                .exclude(**exclude)
                .order_by(Constants.UPDATED_AT)
                .all()
            )
        page = self.paginate_queryset(data)
        participant_serializer = ParticipantDatasetsSerializer(page, many=True)
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
        participant_serializer = ParticipantDatasetsDetailSerializer(data, many=True)
        if participant_serializer.data:
            data = participant_serializer.data[0]
            data[Constants.CONTENT] = read_contents_from_csv_or_xlsx_file(data.get(Constants.SAMPLE_DATASET))

            return Response(data, status=status.HTTP_200_OK)
        return Response({}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
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
        org_id = data.pop(Constants.ORG_ID, None)
        user_id = data.pop(Constants.USER_ID, "")
        exclude = {Constants.USER_MAP_USER: user_id} if org_id else {}
        filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {Constants.USER_MAP_USER: user_id}
        cretated_range = {}
        created_at__range = request.data.pop(Constants.CREATED_AT__RANGE, None)
        if created_at__range:
            cretated_range[Constants.CREATED_AT__RANGE] = date_formater(created_at__range)
        try:
            data = (
                Datasets.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(status=True, **data, **filters, **cretated_range)
                .exclude(**exclude)
                .order_by(Constants.UPDATED_AT)
                .all()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = ParticipantDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)
