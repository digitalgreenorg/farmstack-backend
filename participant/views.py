import json
import logging
import os
import subprocess
from sre_compile import isstring
from struct import unpack

import pandas as pd
import requests
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
from django.db.models import Q
from django.db.models.functions import Lower
from rest_framework import pagination, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial

from participant.models import (
    Connectors,
    ConnectorsMap,
    Department,
    Project,
    SupportTicket,
)
from participant.serializers import (
    ConnectorListSerializer,
    ConnectorsConsumerRelationSerializer,
    ConnectorsListSerializer,
    ConnectorsMapConsumerRetriveSerializer,
    ConnectorsMapProviderRetriveSerializer,
    ConnectorsMapSerializer,
    ConnectorsProviderRelationSerializer,
    ConnectorsRetriveSerializer,
    ConnectorsSerializer,
    DatasetSerializer,
    DepartmentListSerializer,
    DepartmentSerializer,
    ParticipantDatasetsDetailSerializer,
    ParticipantDatasetsDropDownSerializer,
    ParticipantDatasetsSerializer,
    ParticipantSupportTicketSerializer,
    ProjectListSerializer,
    ProjectSerializer,
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
                .reverse()
                .all()
            )
        page = self.paginate_queryset(data)
        participant_serializer = ParticipantDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["get"])
    def list_of_datasets(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        user_id = request.query_params.get(Constants.USER_ID, "")
        filters = {Constants.USER_MAP_USER: user_id} if user_id else {}
        data = (
            Datasets.objects.select_related(
                Constants.USER_MAP, Constants.USER_MAP_USER, Constants.USER_MAP_ORGANIZATION
            )
            .filter(user_map__user__status=True, status=True, approval_status="approved", **filters)
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        participant_serializer = ParticipantDatasetsDropDownSerializer(data, many=True)
        return Response(participant_serializer.data, status=status.HTTP_200_OK)

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
        setattr(request.data, "_mutable", True)
        data = request.data
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
        serializer = self.get_serializer(instance, data=data, partial=True)
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
        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id}
            filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id}
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
                .filter(user_map__user__status=True, status=True, **data, **filters, **cretated_range)
                .exclude(**exclude)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = ParticipantDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id}
            filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id}
        try:
            geography = (
                Datasets.objects.all()
                .select_related(Constants.USER_MAP_ORGANIZATION, Constants.USER_MAP_USER)
                .values_list(Constants.GEOGRAPHY, flat=True)
                .filter(user_map__user__status=True, status=True, **filters)
                .exclude(geography="")
                .exclude(**exclude)
                .all()
                .distinct()
            )
            crop_detail = (
                Datasets.objects.all()
                .select_related(Constants.USER_MAP_ORGANIZATION, Constants.USER_MAP_USER)
                .values_list(Constants.CROP_DETAIL, flat=True)
                .filter(user_map__user__status=True, status=True, **filters)
                .exclude(crop_detail="")
                .exclude(**exclude)
                .all()
                .distinct()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response({"geography": geography, "crop_detail": crop_detail}, status=200)


class ParticipantConnectorsViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = ConnectorsSerializer
    queryset = Connectors
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
        docker_image = data.get("docker_image_url")
        try:
            docker = docker_image.split(":")
            response = requests.get(f"https://hub.docker.com/v2/repositories/{docker[0]}/tags/{docker[1]}")
            images = response.json().get("images", [{}])
            hash = [image.get("digest", "") for image in images if image.get("architecture") == "amd64"]
            data["usage_policy"] = hash[0].split(":")[1].strip()
        except Exception as error:
            logging.error("Error while fetching the hash value. ERROR: %s", error)
            return Response({"docker_image_url": [f"Invalid docker Image: {docker_image}"]}, status=400)
        serializer = self.get_serializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        user_id = request.query_params.get(Constants.USER_ID, "")
        filters = {"user_map__user": user_id} if user_id else {}
        if filters:
            data = (
                Connectors.objects.select_related("dataset" "user_map", Constants.PROJECT, "project__department")
                .filter(user_map__user__status=True, dataset__status=True, status=True, **filters)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        page = self.paginate_queryset(data)
        participant_serializer = ConnectorsListSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        data = (
            Connectors.objects.select_related("dataset", "user_map", "user_map__user", "user_map__organization")
            .filter(user_map__user__status=True, dataset__status=True, status=True, id=pk)
            .all()
        )
        participant_serializer = ConnectorsRetriveSerializer(data, many=True)
        if participant_serializer.data:
            data = participant_serializer.data[0]
            if data.get("connector_type") == "Provider":
                relation = (
                    ConnectorsMap.objects.select_related(
                        "consumer",
                        "consumer__dataset",
                        "consumer__project",
                        "consumer__project__department",
                        "consumer__user_map__organization",
                    )
                    .filter(
                        status=True,
                        provider=pk,
                        consumer__status=True,
                        connector_pair_status__in=["paired", "awaiting for approval"],
                    )
                    .all()
                )
                relation_serializer = ConnectorsMapConsumerRetriveSerializer(relation, many=True)
            else:
                relation = (
                    ConnectorsMap.objects.select_related(
                        "provider",
                        "provider__dataset",
                        "provider__project",
                        "provider__project__department",
                        "provider__user_map__organization",
                    )
                    .filter(
                        status=True,
                        consumer=pk,
                        provider__status=True,
                        connector_pair_status__in=["paired", "awaiting for approval"],
                    )
                    .all()
                )
                relation_serializer = ConnectorsMapProviderRetriveSerializer(relation, many=True)
            data["relation"] = relation_serializer.data
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
    def connectors_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.data
        user_id = data.pop(Constants.USER_ID, "")
        filters = {"user_map__user": user_id} if user_id else {}
        cretated_range = {}
        created_at__range = request.data.pop(Constants.CREATED_AT__RANGE, None)
        if created_at__range:
            cretated_range[Constants.CREATED_AT__RANGE] = date_formater(created_at__range)
        try:
            data = (
                Connectors.objects.select_related("dataset", "user_map", "project", "project__department")
                .filter(status=True, dataset__status=True, **data, **filters, **cretated_range)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = ConnectorsListSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        data = request.data
        user_id = data.pop(Constants.USER_ID)
        filters = {"user_map__user": user_id} if user_id else {}
        try:
            projects = (
                Connectors.objects.select_related("dataset", "project", "user_map")
                .values_list("project__project_name", flat=True)
                .distinct()
                .filter(dataset__status=True, status=True, **filters)
                .exclude(project__project_name__isnull=True, project__project_name__exact="")
            )
            departments = (
                Connectors.objects.select_related("dataset", "project", "project__department" "dataset__user_map")
                .values_list("project__department__department_name", flat=True)
                .distinct()
                .filter(dataset__status=True, status=True, **filters)
                .exclude(
                    project__department__department_name__isnull=True, project__department__department_name__exact=""
                )
            )
            datasests = (
                Datasets.objects.all()
                .select_related("user_map", "user_map__user")
                .filter(user_map__user=user_id, user_map__user__status=True, status=True)
            )
            is_datset_present = True if datasests else False
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response(
            {"projects": list(projects), "departments": list(departments), "is_dataset_present": is_datset_present},
            status=200,
        )

    @action(detail=False, methods=["get"])
    def get_connectors(self, request, *args, **kwargs):
        dataset_id = request.query_params.get("dataset_id", "")
        data = Connectors.objects.all().filter(
            dataset=dataset_id,
            status=True,
            connector_status__in=["unpaired", "pairing request received"],
            connector_type="Provider",
        )
        connector_serializer = ConnectorListSerializer(data, many=True)
        return Response(connector_serializer.data, status=200)


class ParticipantConnectorsMapViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = ConnectorsMapSerializer
    queryset = ConnectorsMap
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
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        provider = request.data.get("provider")
        consumer = request.data.get("consumer")
        provider_obj = Connectors.objects.get(id=provider)
        provider_obj.connector_status = "pairing request received"
        consumer_obj = Connectors.objects.get(id=consumer)
        consumer_obj.connector_status = "awaiting for approval"
        self.perform_create(provider_obj)
        self.perform_create(consumer_obj)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        provider_obj = Connectors.objects.get(id=instance.provider.id)
        consumer_obj = Connectors.objects.get(id=instance.consumer.id)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if request.data.get("connector_pair_status") == "rejected":
            connectors = Connectors.objects.get(id=instance.consumer.id)
            connectors.connector_status = "rejected"
            self.perform_create(connectors)
            if (
                not ConnectorsMap.objects.all()
                .filter(provider=instance.provider.id, connector_pair_status="awaiting for approval")
                .exclude(id=instance.id)
            ):
                connectors = Connectors.objects.get(id=instance.provider.id)
                connectors.connector_status = "unpaired"
                self.perform_create(connectors)
        elif request.data.get("connector_pair_status") == "paired":
            ports = get_ports()
            consumer_connectors = Connectors.objects.get(id=instance.consumer.id)
            provider_connectors = Connectors.objects.get(id=instance.provider.id)
            provider_connectors.connector_status = "paired"
            consumer_connectors.connector_status = "paired"
            self.perform_create(consumer_connectors)
            self.perform_create(provider_connectors)
            rejection_needed_connectors = (
                ConnectorsMap.objects.all()
                .filter(provider=instance.provider.id, connector_pair_status="awaiting for approval")
                .exclude(id=instance.id)
            )
            if rejection_needed_connectors:
                for map_connectors in rejection_needed_connectors:
                    map_connectors.connector_pair_status = "rejected"
                    map_connectors_consumer = Connectors.objects.get(id=map_connectors.consumer.id)
                    map_connectors_consumer.connector_status = "rejected"
                    self.perform_create(map_connectors)
                    self.perform_create(map_connectors_consumer)
            serializer.ports = ports
        elif request.data.get("connector_pair_status") == "unpaired":
            consumer_connectors = Connectors.objects.get(id=instance.consumer.id)
            provider_connectors = Connectors.objects.get(id=instance.provider.id)
            provider_connectors.connector_status = "unpaired"
            consumer_connectors.connector_status = "unpaired"
            self.perform_create(consumer_connectors)
            self.perform_create(provider_connectors)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        data = ConnectorsMap.objects.filter(id=pk).all()
        participant_serializer = ConnectorsMapSerializer(data, many=True)
        if participant_serializer.data:
            return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = False
        self.perform_create(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantDepatrmentViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = DepartmentSerializer
    queryset = Department
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
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        queryset = self.get_object()
        serializer = self.serializer_class(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        org_id = request.query_params.get(Constants.ORG_ID)
        filters = {Constants.ORGANIZATION: org_id} if org_id else {}
        data = (
            Department.objects.filter(Q(status=True, **filters) | Q(department_name="default"))
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        department_serializer = DepartmentListSerializer(data, many=True)
        return Response(department_serializer.data, status=200)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = False
        self.perform_create(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantProjectViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = ProjectSerializer
    queryset = Department
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
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        department = request.query_params.get(Constants.DEPARTMENT)
        filters = {Constants.DEPARTMENT: department} if department else {}
        data = (
            Project.objects.filter(Q(status=True, **filters) | Q(project_name="default"))
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        project_serializer = ProjectListSerializer(data, many=True)
        return Response(project_serializer.data, status=200)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.status = False
        self.perform_create(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


def get_ports():
    """This function give the ports for the connectors"""
    with open("./ports.json", "r") as openfile:
        ports_object = json.load(openfile)
    provider_core = int(ports_object.get(Constants.PROVIDER_CORE)) + 1
    consumer_core = int(ports_object.get(Constants.CONSUMER_CORE)) + 1
    provider_app = int(ports_object.get(Constants.PROVIDER_APP)) + 1
    consumer_app = int(ports_object.get(Constants.CONSUMER_APP)) + 1
    new_ports = {
        Constants.PROVIDER_CORE: provider_core,
        Constants.CONSUMER_CORE: consumer_core,
        Constants.CONSUMER_APP: consumer_app,
        Constants.PROVIDER_APP: provider_app,
    }
    with open("./ports.json", "w") as outfile:
        json.dump(new_ports, outfile)
    return new_ports
