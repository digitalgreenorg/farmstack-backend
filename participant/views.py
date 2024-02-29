import ast
import datetime
import json
import logging
import operator
import os
import re
import shutil
import subprocess
import threading
import time
from bdb import set_trace
from calendar import c
from contextlib import closing
from functools import reduce
from sre_compile import isstring
from struct import unpack
from timeit import Timer
from urllib.parse import unquote

import mysql.connector
import pandas as pd
import psycopg2
import requests
import xlwt
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, F, Count, Sum, Func, CharField, Value, Subquery
from django.db.models.functions import Lower, Concat
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from psycopg2 import errorcodes
from python_http_client import exceptions
from rest_framework import pagination, serializers, status, generics, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from uritemplate import partial

from accounts.models import User
from accounts.serializers import UserCreateSerializer
from core.constants import Constants, NumericalConstants
from core.serializer_validation import OrganizationSerializerValidator, UserCreateSerializerValidator
from core.utils import (
    CustomPagination,
    Utils,
    csv_and_xlsx_file_validatation,
    date_formater,
    one_day_date_formater,
    read_contents_from_csv_or_xlsx_file,
    timer, generate_hash_key_for_dashboard, generate_api_key,
)
from participant.models import (
    DatasetV2,
    DatasetV2File,
    Organization,
    UserOrganizationMap,
)

from datasets.models import Datasets
from participant.serializers import DatasetFileV2NewSerializer

from participant.internal_services.support_ticket_internal_services import (
    SupportTicketInternalServices,
)


# TODO - REMOVED IMOPORT TO CONNECTOR MODEL TO AVOID CIRCULAR IMPORT
from participant.models import (
    # Connectors,
    # ConnectorsMap,
    Department,
    Project,
    Resolution,
    SupportTicket,
    SupportTicketV2, DatahubDocuments, DatasetSubCategoryMap, SubCategory, StandardisationTemplate, Policy, UsagePolicy,
    Resource, ResourceSubCategoryMap, ResourceUsagePolicy, ResourceFile, LangchainPgCollection, Category,
    LangchainPgEmbedding, Messages,
)


# TODO - REMOVED IMOPORT TO CONNECTOR MODEL TO AVOID CIRCULAR IMPORT
from participant.serializers import (
    ConnectorListSerializer,
    ConnectorsConsumerRelationSerializer,
    ConnectorsListSerializer,
    ConnectorsMapConsumerRetriveSerializer,
    ConnectorsMapProviderRetriveSerializer,
    ConnectorsMapSerializer,
    ConnectorsProviderRelationSerializer,
    ConnectorsRetriveSerializer,
    # ConnectorsSerializer,
    ConnectorsSerializerForEmail,
    CreateSupportTicketResolutionsSerializer,
    CreateSupportTicketV2Serializer,
    DatabaseColumnRetrieveSerializer,
    DatabaseConfigSerializer,
    DatabaseDataExportSerializer,
    DatasetSerializer,
    DepartmentSerializer,
    ParticipantDatasetsDetailSerializer,
    ParticipantDatasetsDropDownSerializer,
    ParticipantDatasetsSerializer,
    ParticipantDatasetsSerializerForEmail,
    ParticipantSupportTicketSerializer,
    ProjectDepartmentSerializer,
    ProjectSerializer,
    SupportTicketResolutionsSerializer,
    SupportTicketResolutionsSerializerMinimised,
    SupportTicketV2Serializer,
    TicketSupportSerializer,
    UpdateSupportTicketV2Serializer, TeamMemberListSerializer, TeamMemberCreateSerializer, TeamMemberDetailsSerializer,
    TeamMemberUpdateSerializer, OrganizationSerializerExhaustive, UserOrganizationMapSerializer, ParticipantSerializer,
    ParticipantCostewardSerializer, DropDocumentSerializer, PolicyDocumentSerializer, DatahubThemeSerializer,
    DatasetV2Serializer, DatasetV2Validation, DatasetV2TempFileSerializer, UsagePolicyDetailSerializer,
    DatahubDatasetsV2Serializer, StandardisationTemplateViewSerializer, PolicySerializer, DatasetV2NewListSerializer,
    UsagePolicySerializer, UsageUpdatePolicySerializer, APIBuilderSerializer, DatasetV2ListNewSerializer,
    ResourceSerializer, ResourceListSerializer, ResourceFileSerializer, CategorySerializer, MessagesRetriveSerializer,
    ResourceUsagePolicySerializer, ResourceAPIBuilderSerializer, MessagesChunksRetriveSerializer, MessagesSerializer,
    LangChainEmbeddingsSerializer, SubCategorySerializer, DatasetV2DetailNewSerializer,
    StandardisationTemplateUpdateSerializer, RecentDatasetListSerializer, RecentSupportTicketSerializer,
    DatasetUpdateSerializer, DatahubDatasetsSerializer,
)
from utils import file_operations as file_ops, file_operations, custom_exceptions
from utils import string_functions
from utils.authentication_services import authenticate_user
from utils.authorization_services import support_ticket_role_authorization
from utils.embeddings_creation import VectorDBBuilder

# from utils.connector_utils import run_containers, stop_containers
from utils.file_operations import check_file_name_length, filter_dataframe_for_dashboard_counties, \
    generate_omfp_dashboard, generate_fsp_dashboard, generate_knfd_dashboard
from utils.jwt_services import http_request_mutation
from utils.youtube_helper import get_youtube_url

LOGGER = logging.getLogger(__name__)

class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """

    page_size = 5

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
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @http_request_mutation
    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        try:
            user_id = request.META.get(Constants.USER_ID)
            data = (
                SupportTicket.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, user_map__user=user_id)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
            page = self.paginate_queryset(data)
            participant_serializer = ParticipantSupportTicketSerializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
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
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=None)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        """creates a new participant dataset and triggers an email to the datahub admin requesting for approval of dataset"""
        setattr(request.data, "_mutable", True)

        data = request.data
        user_org_map = UserOrganizationMap.objects.get(
            id=data.get(Constants.USER_MAP))
        user = User.objects.get(id=user_org_map.user_id)

        if not data.get("is_public"):
            if not csv_and_xlsx_file_validatation(request.data.get(Constants.SAMPLE_DATASET)):
                return Response(
                    {
                        Constants.SAMPLE_DATASET: [
                            "Invalid Sample dataset file (or) Atleast 5 rows should be available. please upload valid file"
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if data.get("constantly_update") == "false":
            formatted_date = one_day_date_formater(
                [data.get("data_capture_start", ""), data.get("data_capture_end")])
            data["data_capture_start"] = formatted_date[0]
            data["data_capture_end"] = formatted_date[1]
        if user.approval_status == True:
            data["approval_status"] = Constants.APPROVED
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)  # save data

        try:
            # initialize an email to datahub admin for approval of the dataset and save the data
            serializer_email = ParticipantDatasetsSerializerForEmail(data)
            recepient = User.objects.filter(role_id=1).first()
            subject = Constants.ADDED_NEW_DATASET_SUBJECT + os.environ.get(
                Constants.DATAHUB_NAME, Constants.datahub_name
            )
            datahub_admin_name = string_functions.get_full_name(
                recepient.first_name, recepient.last_name)
            formatted_date = one_day_date_formater(
                [data.get("data_capture_start", ""), data.get("data_capture_end")])
            email_data = {
                Constants.datahub_name: os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                "datahub_admin_name": datahub_admin_name,
                Constants.datahub_site: os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
                "dataset": serializer_email.data,
            }

            email_render = render(
                request, Constants.NEW_DATASET_UPLOAD_REQUEST_IN_DATAHUB, email_data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=recepient.email,
                content=mail_body,
                subject=subject,
            )
            LOGGER.info(
                f"Successfully saved the dataset and emailed datahub admin: {recepient.email} for approval of dataset. \n dataset saved: {serializer.data}"
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({"Error": ["Bad Request"]}, status=status.HTTP_400_BAD_REQUEST)

    @http_request_mutation
    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        try:
            data = []
            user_id = request.META.get(Constants.USER_ID, "")
            org_id = request.META.get(Constants.ORG_ID)
            exclude = {Constants.USER_MAP_USER: user_id} if org_id else {}
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {Constants.USER_MAP_USER: user_id}
            if filters:
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
            participant_serializer = ParticipantDatasetsSerializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    @http_request_mutation
    def list_of_datasets(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        try:
            data = []
            user_id = request.META.get(Constants.USER_ID, "")
            filters = {Constants.USER_MAP_USER: user_id} if user_id else {}
            data = (
                Datasets.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(
                    user_map__user__status=True,
                    status=True,
                    approval_status="approved",
                    **filters,
                )
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
            participant_serializer = ParticipantDatasetsDropDownSerializer(data, many=True)
            return Response(participant_serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
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
                if not data.get("is_public"):
                    data[Constants.CONTENT] = read_contents_from_csv_or_xlsx_file(data.get(Constants.SAMPLE_DATASET))

                return Response(data, status=status.HTTP_200_OK)
            return Response({}, status=status.HTTP_200_OK)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        setattr(request.data, "_mutable", True)
        data = request.data
        data = {key: value for key, value in data.items() if value != "null"}
        if not data.get("is_public"):
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
        if data.get("constantly_update") == "false":
            if "data_capture_start" in data and "data_capture_end" in data:
                formatted_date = one_day_date_formater(
                    [data.get("data_capture_start", ""),
                     data.get("data_capture_end")]
                )
                data["data_capture_start"] = formatted_date[0]
                data["data_capture_end"] = formatted_date[1]
        category = data.get(Constants.CATEGORY)
        if category:
            data[Constants.CATEGORY] = json.dumps(json.loads(
                category)) if isinstance(category, str) else category
        instance = self.get_object()

        # trigger email to the participant
        user_map_queryset = UserOrganizationMap.objects.select_related(
            Constants.USER).get(id=instance.user_map_id)
        user_obj = user_map_queryset.user

        # reset the approval status b/c the user modified the dataset after an approval
        if getattr(instance, Constants.APPROVAL_STATUS) == Constants.APPROVED and (
                user_obj.role_id == 3 or user_obj.role_id == 4
        ):
            data[Constants.APPROVAL_STATUS] = Constants.AWAITING_REVIEW

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        try:
            # initialize an email to datahub admin for approval of the dataset and save the data
            serializer_email = ParticipantDatasetsSerializerForEmail(data)
            recepient = User.objects.filter(role_id=1).first()
            subject = Constants.UPDATED_DATASET_SUBJECT + os.environ.get(
                Constants.DATAHUB_NAME, Constants.datahub_name
            )
            datahub_admin_name = string_functions.get_full_name(
                recepient.first_name, recepient.last_name)
            formatted_date = one_day_date_formater(
                [data.get("data_capture_start", ""), data.get("data_capture_end")])
            email_data = {
                Constants.datahub_name: os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                "datahub_admin_name": datahub_admin_name,
                Constants.datahub_site: os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
                "dataset": serializer_email.data,
            }

            email_render = render(
                request, Constants.DATASET_UPDATE_REQUEST_IN_DATAHUB, email_data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=recepient.email,
                content=mail_body,
                subject=subject,
            )
            LOGGER.info(
                f"Successfully updated the dataset and emailed datahub admin: {recepient.email} for approval of dataset. \n dataset saved: {serializer.data}"
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({"Error": ["Bad Request"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        try:
            product = self.get_object()
            product.status = False
            self.perform_create(product)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def dataset_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")

        org_id = request.META.pop(Constants.ORG_ID, "")
        others = request.META.pop(Constants.OTHERS, "")
        user_id = request.META.pop(Constants.USER_ID, "")

        categories = data.pop(Constants.CATEGORY, None)
        exclude, filters = {}, {}
        if others:
            exclude = {
                Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {
                Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
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
                    .filter(
                        user_map__user__status=True,
                        status=True,
                        **data,
                        **filters,
                    )
                    .exclude(**exclude)
                    .order_by(Constants.UPDATED_AT)
                    .reverse()
                    .all()
                )
        except Exception as error:  # type: ignore
            LOGGER.error(
                "Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = ParticipantDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")

        org_id = request.META.pop(Constants.ORG_ID, "")
        others = request.META.pop(Constants.OTHERS, "")
        user_id = request.META.pop(Constants.USER_ID, "")

        exclude, filters = {}, {}
        if others:
            exclude = {
                Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {
                Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
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
            with open(Constants.CATEGORIES_FILE, "r") as json_obj:
                category_detail = json.loads(json_obj.read())
        except Exception as error:  # type: ignore
            LOGGER.error(
                "Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response(
            {
                "geography": geography,
                "crop_detail": crop_detail,
                "category_detail": category_detail,
            },
            status=200,
        )

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def search_datasets(self, request, *args, **kwargs):
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")

        org_id = request.META.pop(Constants.ORG_ID, "")
        others = request.META.pop(Constants.OTHERS, "")
        user_id = request.META.pop(Constants.USER_ID, "")

        search_pattern = data.pop(Constants.SEARCH_PATTERNS, "")
        exclude, filters = {}, {}

        if others:
            exclude = {
                Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            filters = (
                {
                    Constants.APPROVAL_STATUS: Constants.APPROVED,
                    Constants.NAME_ICONTAINS: search_pattern,
                }
                if search_pattern
                else {}
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
            LOGGER.error(
                "Error while filtering the datasets. ERROR: %s", error)
            return Response(
                f"Invalid filter fields: {list(request.data.keys())}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        page = self.paginate_queryset(data)
        participant_serializer = ParticipantDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)


class ParticipantConnectorsViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    # serializer_class = ConnectorsSerializer
    # queryset = Connectors
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

    def trigger_email(self, request, template, subject, user_org_map, connector_data, dataset):
        """trigger email to the respective users"""
        try:
            datahub_admin = User.objects.filter(role_id=1).first()
            admin_full_name = string_functions.get_full_name(
                datahub_admin.first_name, datahub_admin.last_name)
            participant_org = Organization.objects.get(
                id=user_org_map.organization_id) if user_org_map else None
            participant_org_address = string_functions.get_full_address(
                participant_org.address)
            participant = User.objects.get(id=user_org_map.user_id)
            participant_full_name = string_functions.get_full_name(
                participant.first_name, participant.last_name)

            data = {
                "datahub_name": os.environ.get("DATAHUB_NAME", "datahub_name"),
                "datahub_admin": admin_full_name,
                "participant_admin_name": participant_full_name,
                "participant_email": participant.email,
                "connector": connector_data,
                "participant_org": participant_org,
                "participant_org_address": participant_org_address,
                "dataset": dataset,
                "datahub_site": os.environ.get("DATAHUB_SITE", "datahub_site"),
            }

            email_render = render(request, template, data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=datahub_admin.email,
                content=mail_body,
                subject=subject,
            )

        except Exception as error:
            LOGGER.error(error, exc_info=True)

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        setattr(request.data, "_mutable", True)
        data = request.data
        docker_image = data.get(Constants.DOCKER_IMAGE_URL)
        try:
            docker = docker_image.split(":")
            response = requests.get(
                f"https://hub.docker.com/v2/repositories/{docker[0]}/tags/{docker[1]}")
            images = response.json().get(Constants.IMAGES, [{}])
            hash = [image.get(Constants.DIGEST, "")
                    for image in images if image.get("architecture") == "amd64"]
            data[Constants.USAGE_POLICY] = hash[0].split(":")[1].strip()
        except Exception as error:
            LOGGER.error(
                "Error while fetching the hash value. ERROR: %s", error)
            return Response(
                {Constants.DOCKER_IMAGE_URL: [
                    f"Invalid docker Image: {docker_image}"]},
                status=400,
            )
        serializer = self.get_serializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        user_org_map = UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).get(
            id=serializer.data.get(Constants.USER_MAP)
        )
        dataset = Datasets.objects.get(
            id=serializer.data.get(Constants.DATASET))
        self.trigger_email(
            request,
            Constants.CREATE_CONNECTOR_AND_REQUEST_CERTIFICATE,
            Constants.CREATE_CONNECTOR_AND_REQUEST_CERTIFICATE_SUBJECT,
            user_org_map,
            serializer.data,
            dataset,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        try:
            data = []
            user_id = request.query_params.get(Constants.USER_ID, "")
            filters = {Constants.USER_MAP_USER: user_id} if user_id else {}
            if filters:
                data = (
                    Connectors.objects.select_related(
                        Constants.DATASET,
                        Constants.USER_MAP,
                        Constants.PROJECT,
                        Constants.PROJECT_DEPARTMENT,
                    )
                    .filter(
                        user_map__user__status=True,
                        dataset__status=True,
                        status=True,
                        **filters,
                    )
                    .order_by(Constants.UPDATED_AT)
                    .reverse()
                    .all()
                )
            page = self.paginate_queryset(data)
            participant_serializer = ConnectorsListSerializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            data = (
                Connectors.objects.select_related(
                    Constants.DATASET,
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, dataset__status=True, status=True, id=pk)
                .all()
            )
            participant_serializer = ConnectorsRetriveSerializer(data, many=True)
            if participant_serializer.data:
                data = participant_serializer.data[0]
                if data.get(Constants.CONNECTOR_TYPE) == "Provider":
                    relation = (
                        ConnectorsMap.objects.select_related(
                            Constants.CONSUMER,
                            Constants.CONSUMER_DATASET,
                            Constants.CONSUMER_PROJECT,
                            Constants.CONSUMER_PROJECT_DEPARTMENT,
                            Constants.CONSUMER_USER_MAP_ORGANIZATION,
                        )
                        .filter(
                            status=True,
                            provider=pk,
                            consumer__status=True,
                            connector_pair_status__in=[
                                Constants.PAIRED,
                                Constants.AWAITING_FOR_APPROVAL,
                            ],
                        )
                        .all()

                    )
                    relation_serializer = ConnectorsMapConsumerRetriveSerializer(relation, many=True)
                else:
                    relation = (
                        ConnectorsMap.objects.select_related(
                            Constants.PROVIDER,
                            Constants.PROVIDER_DATASET,
                            Constants.PROVIDER_PROJECT,
                            Constants.PROVIDER_PROJECT_DEPARTMENT,
                            Constants.PROVIDER_USER_MAP_ORGANIZATION,
                        )
                        .filter(
                            status=True,
                            consumer=pk,
                            provider__status=True,
                            connector_pair_status__in=[
                                Constants.PAIRED,
                                Constants.AWAITING_FOR_APPROVAL,
                            ],
                        )
                        .all()
                    )
                    relation_serializer = ConnectorsMapProviderRetriveSerializer(relation, many=True)
                data[Constants.RELATION] = relation_serializer.data
                return Response(data, status=status.HTTP_200_OK)
            return Response({}, status=status.HTTP_200_OK)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        setattr(request.data, "_mutable", True)
        data = request.data
        docker_image = data.get(Constants.DOCKER_IMAGE_URL)
        if docker_image:
            try:
                docker = docker_image.split(":")
                response = requests.get(
                    f"https://hub.docker.com/v2/repositories/{docker[0]}/tags/{docker[1]}")
                images = response.json().get(Constants.IMAGES, [{}])
                hash = [image.get(Constants.DIGEST, "") for image in images if image.get(
                    "architecture") == "amd64"]
                data[Constants.USAGE_POLICY] = hash[0].split(":")[1].strip()
            except Exception as error:
                LOGGER.error(
                    "Error while fetching the hash value. ERROR: %s", error)
                return Response(
                    {Constants.DOCKER_IMAGE_URL: [
                        f"Invalid docker Image: {docker_image}"]},
                    status=400,
                )
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        if request.data.get(Constants.CERTIFICATE):
            user_org_map = UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).get(
                id=serializer.data.get(Constants.USER_MAP)
            )
            dataset = Datasets.objects.get(
                id=serializer.data.get(Constants.DATASET))
            subject = (
                    "A certificate on " +
                    os.environ.get("DATAHUB_NAME", "datahub_name") +
                    " was successfully installed"
            )
            self.trigger_email(
                request,
                Constants.PARTICIPANT_INSTALLS_CERTIFICATE,
                subject,
                user_org_map,
                serializer.data,
                dataset,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        try:
            connector = self.get_object()
            if connector.connector_status in [Constants.UNPAIRED, Constants.REJECTED]:
                connector.status = False
                self.perform_create(connector)
            else:
                return Response(
                    ["Connector status should be either unpaired or rejected to delete"],
                    status=400,
                )
            user_org_map = UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).get(
                id=connector.user_map_id
            )
            dataset = Datasets.objects.get(id=connector.dataset_id)
            self.trigger_email(
                request,
                "deleting_connector.html",
                Constants.CONNECTOR_DELETION +
                os.environ.get("DATAHUB_NAME", "datahub_name"),
                user_org_map,
                connector,
                dataset,
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def connectors_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.META
        user_id = data.pop(Constants.USER_ID, "")
        filters = {Constants.USER_MAP_USER: user_id} if user_id else {}
        try:
            data = (
                Connectors.objects.select_related(
                    Constants.DATASET,
                    Constants.USER_MAP,
                    Constants.PROJECT,
                    Constants.DEPARTMENT,
                )
                .filter(
                    status=True,
                    dataset__status=True,
                    **data,
                    **filters,
                )
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
        except Exception as error:  # type: ignore
            LOGGER.error(
                "Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = ConnectorsListSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        data = request.META
        user_id = data.pop(Constants.USER_ID)
        filters = {Constants.USER_MAP_USER: user_id} if user_id else {}
        try:
            projects = (
                Connectors.objects.select_related(
                    Constants.DATASET, Constants.PROJECT, Constants.USER_MAP)
                .values_list(Constants.PROJECT_PROJECT_NAME, flat=True)
                .distinct()
                .filter(dataset__status=True, status=True, **filters)
                .exclude(project__project_name__isnull=True, project__project_name__exact="")
            )
            departments = (
                Connectors.objects.select_related(
                    Constants.DATASET, Constants.DEPARTMENT, Constants.DATASET_USER_MAP)
                .values_list(Constants.DEPARTMENT_DEPARTMENT_NAME, flat=True)
                .distinct()
                .filter(dataset__status=True, status=True, **filters)
                .exclude(
                    project__department__department_name__isnull=True,
                    project__department__department_name__exact="",
                )
            )
            datasests = (
                Datasets.objects.all()
                .select_related(Constants.USER_MAP, Constants.USER_MAP_USER)
                .filter(user_map__user=user_id, user_map__user__status=True, status=True)
            )
            is_datset_present = True if datasests else False
        except Exception as error:  # type: ignore
            LOGGER.error(
                "Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response(
            {
                Constants.PROJECTS: list(projects),
                Constants.DEPARTMENTS: list(departments),
                Constants.IS_DATASET_PRESENT: is_datset_present,
            },
            status=200,
        )

    @action(detail=False, methods=["get"])
    def get_connectors(self, request, *args, **kwargs):
        try:
            dataset_id = request.query_params.get(Constants.DATASET_ID, "")
            data = Connectors.objects.all().filter(
                dataset=dataset_id,
                status=True,
                connector_status__in=[
                    Constants.UNPAIRED,
                    Constants.PAIRING_REQUEST_RECIEVED,
                ],
                connector_type="Provider",
            )
            connector_serializer = ConnectorListSerializer(data, many=True)
            return Response(connector_serializer.data, status=200)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def show_data(self, request, *args, **kwargs):
        port = request.query_params.get("port", "")
        return Response(
            requests.get(
                f'{os.environ.get("REACT_APP_BASEURL_without_slash_view_data")}{port}/show_data').json(),
            200,
        )


class ParticipantConnectorsMapViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    # serializer_class = ConnectorsMapSerializer
    # queryset = ConnectorsMap
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

    def trigger_email_for_pairing(self, request, template, subject, consumer_connector, provider_connector):
        # trigger email to the participant as they are being added
        try:
            consumer_org_map = (
                UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).get(
                    id=consumer_connector.user_map_id
                )
                if consumer_connector.user_map_id
                else None
            )
            consumer_org = Organization.objects.get(
                id=consumer_org_map.organization_id) if consumer_org_map else None
            consumer = User.objects.get(
                id=consumer_org_map.user_id) if consumer_org_map else None
            consumer_full_name = string_functions.get_full_name(
                consumer.first_name, consumer.last_name)
            provider_org_map = (
                UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).get(
                    id=provider_connector.user_map_id
                )
                if provider_connector.user_map_id
                else None
            )
            provider_org = Organization.objects.get(
                id=provider_org_map.organization_id) if provider_org_map else None
            provider = User.objects.get(
                id=provider_org_map.user_id) if provider_org_map else None
            provider_full_name = string_functions.get_full_name(
                provider.first_name, provider.last_name)
            dataset = Datasets.objects.get(id=provider_connector.dataset_id)

            if str(provider_connector.user_map_id) == request.data.get("user_map"):
                print("CTA by provider. Trigger email to consumer")
                data = {
                    "consumer_admin_name": consumer_full_name,
                    "consumer_connector": consumer_connector,
                    "provider_org": provider_org,
                    "dataset": dataset,
                    "provider_connector": provider_connector,
                    "datahub_site": os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
                }

                email_render = render(request, template, data)
                mail_body = email_render.content.decode("utf-8")
                Utils().send_email(
                    to_email=consumer.email,
                    content=mail_body,
                    subject=subject,
                )

            elif str(consumer_connector.user_map_id) == request.data.get("user_map"):
                print("CTA by consumer. Trigger email to provider")
                data = {
                    "provider_admin_name": provider_full_name,
                    "consumer_connector": consumer_connector,
                    "consumer_org": consumer_org,
                    "dataset": dataset,
                    "provider_connector": provider_connector,
                    "datahub_site": os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
                }

                email_render = render(request, template, data)
                mail_body = email_render.content.decode("utf-8")
                Utils().send_email(
                    to_email=provider.email,
                    content=mail_body,
                    subject=subject,
                )

        except Exception as error:
            LOGGER.error(error, exc_info=True)

    @action(detail=False, methods=["get"])
    def data_size(self, request, *args, **kwargs):
        try:
            size = request.query_params.get("size", "")
            print("**********SIZE OF DATA************************")
            print(size)
            return Response([], status=200)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        provider = request.data.get(Constants.PROVIDER)
        consumer = request.data.get(Constants.CONSUMER)
        provider_obj = Connectors.objects.get(id=provider)
        consumer_obj = Connectors.objects.get(id=consumer)
        if provider_obj.connector_status == Constants.PAIRED:
            return Response(
                [f"Provider connector ({({provider_obj.connector_name})}) is already paired with another connector"],
                400,
            )
        elif consumer_obj.connector_status == Constants.PAIRED:
            return Response(
                [f"Consumer connector ({consumer_obj.connector_name}) is already paired with another connector"],
                400,
            )
        consumer_obj.connector_status = Constants.AWAITING_FOR_APPROVAL
        provider_obj.connector_status = Constants.PAIRING_REQUEST_RECIEVED
        self.perform_create(provider_obj)
        self.perform_create(consumer_obj)
        self.perform_create(serializer)

        try:
            # trigger email
            consumer_serializer = ConnectorsSerializerForEmail(consumer_obj)
            provider_serializer = ConnectorsSerializerForEmail(provider_obj)
            data = {
                "consumer": consumer_serializer.data,
                "provider": provider_serializer.data,
                "datahub_site": os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
                "datahub_name": os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
            }
            to_email = provider_serializer.data.get("user").get("email")

            email_render = render(
                request, Constants.REQUEST_CONNECTOR_PAIRING, data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=to_email,
                content=mail_body,
                subject=Constants.PAIRING_REQUEST_RECIEVED_SUBJECT,
            )

        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        setattr(request.data, "_mutable", True)
        instance = self.get_object()
        data = request.data
        if request.data.get(Constants.CONNECTOR_PAIR_STATUS) == Constants.REJECTED:
            connectors = Connectors.objects.get(id=instance.consumer.id)
            connectors.connector_status = Constants.REJECTED
            self.perform_create(connectors)

            if (
                    not ConnectorsMap.objects.all()
                            .filter(
                        provider=instance.provider.id,
                        connector_pair_status=Constants.AWAITING_FOR_APPROVAL,
                    )
                            .exclude(id=instance.id)
            ):
                connectors = Connectors.objects.get(id=instance.provider.id)
                connectors.connector_status = Constants.UNPAIRED
                self.perform_create(connectors)

            provider_connectors = Connectors.objects.get(
                id=instance.provider.id)
            consumer_connectors = Connectors.objects.get(
                id=instance.consumer.id)

            self.trigger_email_for_pairing(
                request,
                Constants.PAIRING_REQUEST_REJECTED,
                Constants.PAIRING_REQUEST_REJECTED_SUBJECT
                + os.environ.get(Constants.DATAHUB_NAME,
                                 Constants.datahub_name),
                consumer_connectors,
                provider_connectors,
            )

        elif request.data.get(Constants.CONNECTOR_PAIR_STATUS) == Constants.PAIRED:
            consumer_connectors = Connectors.objects.get(
                id=instance.consumer.id)
            provider_connectors = Connectors.objects.get(
                id=instance.provider.id)
            if provider_connectors.connector_status == Constants.PAIRED:
                return Response(
                    [
                        f"Provider connector ({({provider_connectors.connector_name})}) is already paired with another connector"
                    ],
                    400,
                )
            elif consumer_connectors.connector_status == Constants.PAIRED:
                return Response(
                    [
                        f"Consumer connector ({consumer_connectors.connector_name}) is already paired with another connector"
                    ],
                    400,
                )
            # ports = run_containers(provider_connectors, consumer_connectors)
            provider_connectors.connector_status = Constants.PAIRED
            consumer_connectors.connector_status = Constants.PAIRED
            self.perform_create(consumer_connectors)
            self.perform_create(provider_connectors)

            self.trigger_email_for_pairing(
                request,
                Constants.PAIRING_REQUEST_APPROVED,
                Constants.PAIRING_REQUEST_APPROVED_SUBJECT
                + os.environ.get(Constants.DATAHUB_NAME,
                                 Constants.datahub_name),
                consumer_connectors,
                provider_connectors,
            )

            rejection_needed_connectors = (
                ConnectorsMap.objects.all()
                .filter(
                    provider=instance.provider.id,
                    connector_pair_status=Constants.AWAITING_FOR_APPROVAL,
                )
                .exclude(id=instance.id)
            )
            if rejection_needed_connectors:
                for map_connectors in rejection_needed_connectors:
                    map_connectors.connector_pair_status = Constants.REJECTED
                    map_connectors_consumer = Connectors.objects.get(
                        id=map_connectors.consumer.id)
                    map_connectors_consumer.connector_status = Constants.REJECTED
                    self.perform_create(map_connectors)
                    self.perform_create(map_connectors_consumer)
            print(ports)
            data["ports"] = json.dumps(ports)
        elif request.data.get(Constants.CONNECTOR_PAIR_STATUS) == Constants.UNPAIRED:
            consumer_connectors = Connectors.objects.get(
                id=instance.consumer.id)
            provider_connectors = Connectors.objects.get(
                id=instance.provider.id)
            provider_connectors.connector_status = Constants.UNPAIRED
            consumer_connectors.connector_status = Constants.UNPAIRED
            self.perform_create(consumer_connectors)
            self.perform_create(provider_connectors)
            # stop_containers(provider_connectors, consumer_connectors)

            self.trigger_email_for_pairing(
                request,
                Constants.WHEN_CONNECTOR_UNPAIRED,
                Constants.CONNECTOR_UNPAIRED_SUBJECT +
                os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                consumer_connectors,
                provider_connectors,
            )

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            data = ConnectorsMap.objects.filter(id=pk).all()
            participant_serializer = ConnectorsMapSerializer(data, many=True)
            if participant_serializer.data:
                return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
            return Response([], status=status.HTTP_200_OK)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        try:
            connector = self.get_object()
            connector.status = False
            self.perform_create(connector)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        try:
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            queryset = Department.objects.filter(Q(status=True, id=pk) | Q(department_name=Constants.DEFAULT, id=pk))
            serializer = self.serializer_class(queryset, many=True)
            if serializer.data:
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response([], status=status.HTTP_200_OK)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    @http_request_mutation
    def department_list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        org_id = request.META.get(Constants.ORG_ID)
        filters = {Constants.ORGANIZATION: org_id} if org_id else {}
        data = (
            # Department.objects.filter(Q(status=True, **filters) | Q(department_name=Constants.DEFAULT))
            Department.objects.filter(status=True, **filters)
            .exclude(department_name=Constants.DEFAULT)
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        page = self.paginate_queryset(data)
        department_serializer = DepartmentSerializer(page, many=True)
        return self.get_paginated_response(department_serializer.data)

    @http_request_mutation
    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        org_id = request.META.get(Constants.ORG_ID)
        filters = {Constants.ORGANIZATION: org_id} if org_id else {}
        data = (
            Department.objects.filter(
                Q(status=True, **filters) | Q(department_name=Constants.DEFAULT))
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        department_serializer = DepartmentSerializer(data, many=True)
        return Response(department_serializer.data)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        try:
            Connectors.objects.filter(department=pk).update(department="e459f452-2b4b-4129-ba8b-1e1180c87888")
            product = self.get_object()
            product.status = False
            self.perform_create(product)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParticipantProjectViewSet(GenericViewSet):
    """
    This class handles the participant Datsets CRUD operations.
    """

    parser_class = JSONParser
    serializer_class = ProjectSerializer
    queryset = Project
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
        try:
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk):
        """PUT method: update or send a PUT request on an object of the Product model"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            queryset = Project.objects.filter(
                Q(status=True, id=pk) | Q(project_name=Constants.DEFAULT, id=pk))
            serializer = ProjectDepartmentSerializer(queryset, many=True)
            if serializer.data:
                return Response(serializer.data[0], status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({"message": error}, status=status.HTTP_200_OK)
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def project_list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = []
        org_id = request.META.get(Constants.ORG_ID)
        filters = {Constants.ORGANIZATION: org_id} if org_id else {}
        data = (
            Project.objects.select_related(Constants.DEPARTMENT_ORGANIZATION)
            # .filter(Q(status=True, **filters) | Q(project_name=Constants.DEFAULT))
            .filter(status=True, **filters)
            .exclude(project_name=Constants.DEFAULT)
            .order_by(Constants.UPDATED_AT)
            .reverse()
            .all()
        )
        page = self.paginate_queryset(data)
        project_serializer = ProjectDepartmentSerializer(page, many=True)
        return self.get_paginated_response(project_serializer.data)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        try:
            data = []
            department = request.query_params.get(Constants.DEPARTMENT)
            org_id = request.query_params.get(Constants.ORG_ID)
            # filters = {Constants.DEPARTMENT: department} if department else {}
            filters = {Constants.DEPARTMENT: department, Constants.ORGANIZATION: org_id} if department or org_id else {}
            data = (
                Project.objects.select_related(Constants.DEPARTMENT_ORGANIZATION)
                .filter(Q(status=True, **filters) | Q(project_name=Constants.DEFAULT))
                # .filter(status=True, **filters)
                # .exclude(project_name=Constants.DEFAULT)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
            project_serializer = ProjectDepartmentSerializer(data, many=True)
            return Response(project_serializer.data)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        try:
            Connectors.objects.filter(project=pk).update(project="3526bd39-4514-43fe-bbc4-ee0980bde252")
            project = self.get_object()
            project.status = False
            self.perform_create(project)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def update_cookies(key, value, response):
    try:
        max_age = 1 * 24 * 60 * 60
        expires = datetime.datetime.strftime(
            datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age),
            "%a, %d-%b-%Y %H:%M:%S GMT",
        )
        response.set_cookie(
            key,
            value,
            max_age=max_age,
            expires=expires,
            domain=os.environ.get("PUBLIC_DOMAIN"),
            secure=False,
        )
        return response

    except ValidationError as e:
        LOGGER.error(e, exc_info=True)
        return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        LOGGER.error(e, exc_info=True)
        return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DataBaseViewSet(GenericViewSet):
    """
    This class handles the participant external Databases  operations.
    """

    parser_class = JSONParser
    serializer_class = DatabaseConfigSerializer

    @action(detail=False, methods=["post"])
    def database_config(self, request):
        """
        Configure the database connection based on the database type.
        Return tables retrieved from the database and set database configuration in the cookies.
        """
        database_type = request.data.get("database_type")
        serializer = self.get_serializer(data=request.data, context={
            "source": database_type})
        serializer.is_valid(raise_exception=True)
        cookie_data = serializer.data
        config = serializer.validated_data
        # remove database_type before passing it to db conn
        config.pop("database_type")
        if database_type == Constants.SOURCE_MYSQL_FILE_TYPE:
            """Create a MySQL connection object on valid database credentials and return tables"""
            LOGGER.info(f"Connecting to {database_type}")

            try:
                # Try to connect to the database using the provided configuration
                mydb = mysql.connector.connect(**config)
                mycursor = mydb.cursor()
                db_name = request.data.get("database")
                mycursor.execute("use " + db_name + ";")
                mycursor.execute("show tables;")
                table_list = mycursor.fetchall()
                table_list = [
                    element for innerList in table_list for element in innerList]

                # send the tables as a list in response body
                response = HttpResponse(json.dumps(
                    table_list), status=status.HTTP_200_OK)
                # set the cookies in response
                response = update_cookies(
                    "conn_details", cookie_data, response)
                return response
            except mysql.connector.Error as err:
                if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
                    return Response(
                        {
                            "username": ["Incorrect username or password"],
                            "password": ["Incorrect username or password"],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif err.errno == mysql.connector.errorcode.ER_NO_SUCH_TABLE:
                    return Response({"table": ["Table does not exist"]},
                                    status=status.HTTP_400_BAD_REQUEST)
                elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                    # Port is incorrect
                    return Response({
                        "dbname": ["Invalid database name. Connection Failed."]}, status=status.HTTP_400_BAD_REQUEST)
                # Return an error message if the connection fails
                return Response({"host": ["Invalid host . Connection Failed."]}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        elif database_type == Constants.SOURCE_POSTGRESQL_FILE_TYPE:
            """Create a PostgreSQL connection object on valid database credentials"""
            LOGGER.info(f"Connecting to {database_type}")
            try:
                tables = []
                with closing(psycopg2.connect(**config)) as conn:
                    with closing(conn.cursor()) as cursor:
                        cursor.execute(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                        table_list = cursor.fetchall()
                # send the tables as a list in response body & set cookies
                tables = [
                    table for inner_list in table_list for table in inner_list]
                response = HttpResponse(json.dumps(
                    tables), status=status.HTTP_200_OK)
                response = update_cookies(
                    "conn_details", cookie_data, response)
                return response
            except psycopg2.Error as err:
                print(err)
                if "password authentication failed for user" in str(err) or "role" in str(err):
                    # Incorrect username or password
                    return Response(
                        {
                            "username": ["Incorrect username or password"],
                            "password": ["Incorrect username or password"],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif "database" in str(err):
                    # Database does not exist
                    return Response({"dbname": ["Database does not exist"]}, status=status.HTTP_400_BAD_REQUEST)
                elif "could not translate host name" in str(err):
                    # Database does not exist
                    return Response({"host": ["Invalid Host address"]}, status=status.HTTP_400_BAD_REQUEST)

                elif "Operation timed out" in str(err):
                    # Server is not available
                    return Response({"port": ["Invalid port or DB Server is down"]}, status=status.HTTP_400_BAD_REQUEST)

                # Return an error message if the connection fails
                return Response({"error": [str(err)]}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def database_col_names(self, request):
        """Return the column names as a list from the requested table by reading the db config from cookies."""
        conn_details = request.COOKIES.get("conn_details", request.data)
        config = ast.literal_eval(conn_details)
        database_type = config.get("database_type")
        table_name = request.data.get("table_name")
        # remove database_type before passing it to db conn
        config.pop("database_type")

        serializer = DatabaseColumnRetrieveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if database_type == Constants.SOURCE_MYSQL_FILE_TYPE:
            """Create a PostgreSQL connection object on valid database credentials"""
            LOGGER.info(f"Connecting to {database_type}")
            try:
                # Try to connect to the database using the provided configuration
                connection = mysql.connector.connect(**config)
                mydb = connection
                mycursor = mydb.cursor()
                db_name = config["database"]
                mycursor.execute("use " + db_name + ";")
                mycursor.execute("SHOW COLUMNS FROM " +
                                 db_name + "." + table_name + ";")

                # Fetch columns & return as a response
                col_list = mycursor.fetchall()
                cols = [column_details[0] for column_details in col_list]
                response = HttpResponse(json.dumps(
                    cols), status=status.HTTP_200_OK)
                return response

            except mysql.connector.Error as err:
                if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
                    return Response(
                        {
                            "username": ["Incorrect username or password"],
                            "password": ["Incorrect username or password"],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif err.errno == mysql.connector.errorcode.ER_NO_SUCH_TABLE:
                    return Response({"table_name": ["Table does not exist"]}, status=status.HTTP_400_BAD_REQUEST)
                elif err.errno == mysql.connector.errorcode.ER_KEY_COLUMN_DOES_NOT_EXITS:
                    return Response({"col": ["Columns does not exist."]}, status=status.HTTP_400_BAD_REQUEST)
                # Return an error message if the connection fails
                return Response({"error": [str(err)]}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                LOGGER.error(e, exc_info=True)
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        elif database_type == Constants.SOURCE_POSTGRESQL_FILE_TYPE:
            """Create a PostgreSQL connection object on valid database credentials"""
            LOGGER.info(f"Connecting to {database_type}")
            try:
                col_list = []
                with closing(psycopg2.connect(**config)) as conn:
                    with closing(conn.cursor()) as cursor:
                        cursor = conn.cursor()
                        # Fetch columns & return as a response
                        cursor.execute(
                            "SELECT column_name FROM information_schema.columns WHERE table_name='{0}';".format(
                                table_name
                            )
                        )
                        col_list = cursor.fetchall()

                if len(col_list) <= 0:
                    return Response({"table_name": ["Table does not exist."]}, status=status.HTTP_400_BAD_REQUEST)

                cols = [column_details[0] for column_details in col_list]
                return HttpResponse(json.dumps(cols), status=status.HTTP_200_OK)
            except psycopg2.Error as error:
                LOGGER.error(error, exc_info=True)

    @action(detail=False, methods=["post"])
    def database_xls_file(self, request):
        """
        Export the data extracted from the database by reading the db config from cookies to a temporary location.
        """
        dataset_name = request.data.get("dataset_name")

        # if not request.query_params.get("dataset_exists"):
        #     if DatasetV2.objects.filter(name=dataset_name).exists():
        #         return Response(
        #             {"dataset_name": ["dataset v2 with this name already exists."]}, status=status.HTTP_400_BAD_REQUEST
        #         )

        conn_details = request.COOKIES.get("conn_details", request.data)

        config = ast.literal_eval(conn_details)
        database_type = config.get("database_type")
        serializer = DatabaseDataExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset = DatasetV2(id=request.data.get("dataset"))
        t_name = request.data.get("table_name")
        col_names = request.data.get("col")
        col_names = ast.literal_eval(col_names)
        col_names = ", ".join(col_names)
        source = request.data.get("source")
        file_name = request.data.get("file_name")
        # remove database_type before passing it to db conn
        config.pop("database_type")

        if database_type == Constants.SOURCE_MYSQL_FILE_TYPE:
            """Create a PostgreSQL connection object on valid database credentials"""
            LOGGER.info(f"Connecting to {database_type}")

            try:
                mydb = mysql.connector.connect(**config)
                mycursor = mydb.cursor()
                db_name = config["database"]
                mycursor.execute("use " + db_name + ";")

                query_string = f"SELECT {col_names} FROM {t_name}"
                sub_queries = []  # List to store individual filter sub-queries
                if serializer.data.get("filter_data"):

                    filter_data = json.loads(serializer.data.get("filter_data")[0])
                    for query_dict in filter_data:
                        query_string = f"SELECT {col_names} FROM {t_name} WHERE "
                        column_name = query_dict.get('column_name')
                        operation = query_dict.get('operation')
                        value = query_dict.get('value')
                        sub_query = f"{column_name} {operation} '{value}'"  # Using %s as a placeholder for the value
                        sub_queries.append(sub_query)
                    query_string += " AND ".join(sub_queries)

                mycursor.execute(query_string)
                result = mycursor.fetchall()

                # save the list of files to a temp directory
                file_path = file_ops.create_directory(
                    settings.DATASET_FILES_URL, [dataset_name, source])
                df = pd.read_sql(query_string, mydb)
                if df.empty:
                    return Response({"data": [f"No data was found for the filter applied. Please try again."]},
                                    status=status.HTTP_400_BAD_REQUEST)
                df = df.astype(str)
                df.to_excel(file_path + "/" + file_name + ".xls")
                instance = DatasetV2File.objects.create(
                    dataset=dataset,
                    source=source,
                    file=os.path.join(dataset_name, source,
                                      file_name + ".xls"),
                    file_size=os.path.getsize(
                        os.path.join(settings.DATASET_FILES_URL, dataset_name, source, file_name + ".xls")),
                    standardised_file=os.path.join(
                        dataset_name, source, file_name + ".xls"),
                )
                # result = os.listdir(file_path)
                serializer = DatasetFileV2NewSerializer(instance)
                return JsonResponse(serializer.data, status=status.HTTP_200_OK)
                # return HttpResponse(json.dumps(result), status=status.HTTP_200_OK)

            except mysql.connector.Error as err:
                LOGGER.error(err, exc_info=True)
                if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
                    return Response(
                        {
                            "username": ["Incorrect username or password"],
                            "password": ["Incorrect username or password"],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif err.errno == mysql.connector.errorcode.ER_NO_SUCH_TABLE:
                    return Response({"table_name": ["Table does not exist"]}, status=status.HTTP_400_BAD_REQUEST)
                # elif err.errno == mysql.connector.errorcode.ER_KEY_COLUMN_DOES_NOT_EXITS:
                elif str(err).__contains__("Unknown column"):
                    return Response({"col": ["Columns does not exist."]}, status=status.HTTP_400_BAD_REQUEST)
                # Return an error message if the connection fails
                return Response({"": [str(err)]}, status=status.HTTP_400_BAD_REQUEST)

        elif database_type == Constants.SOURCE_POSTGRESQL_FILE_TYPE:
            """Create a PostgreSQL connection object on valid database credentials"""
            LOGGER.info(f"Connecting to {database_type}")
            try:
                with closing(psycopg2.connect(**config)) as conn:
                    try:

                        query_string = f"SELECT {col_names} FROM {t_name}"
                        sub_queries = []  # List to store individual filter sub-queries

                        if serializer.data.get("filter_data"):
                            filter_data = json.loads(serializer.data.get("filter_data")[0])

                            for query_dict in filter_data:
                                query_string = f"SELECT {col_names} FROM {t_name} WHERE "
                                column_name = query_dict.get('column_name')
                                operation = query_dict.get('operation')
                                value = query_dict.get('value')
                                sub_query = f"{column_name} {operation} '{value}'"  # Using %s as a placeholder for the value
                                sub_queries.append(sub_query)
                            query_string += " AND ".join(sub_queries)
                        df = pd.read_sql(query_string, conn)
                        if df.empty:
                            return Response({"data": [f"No data was found for the filter applied. Please try again."]},
                                            status=status.HTTP_400_BAD_REQUEST)

                        df = df.astype(str)
                    except pd.errors.DatabaseError as error:
                        LOGGER.error(error, exc_info=True)
                        return Response({"col": ["Columns does not exist."]}, status=status.HTTP_400_BAD_REQUEST)

                file_path = file_ops.create_directory(
                    settings.DATASET_FILES_URL, [dataset_name, source])
                df.to_excel(os.path.join(
                    file_path, file_name + ".xls"))
                instance = DatasetV2File.objects.create(
                    dataset=dataset,
                    source=source,
                    file=os.path.join(dataset_name, source,
                                      file_name + ".xls"),
                    file_size=os.path.getsize(
                        os.path.join(settings.DATASET_FILES_URL, dataset_name, source, file_name + ".xls")),
                    standardised_file=os.path.join(
                        dataset_name, source, file_name + ".xls"),
                )
                # result = os.listdir(file_path)
                serializer = DatasetFileV2NewSerializer(instance)
                return JsonResponse(serializer.data, status=status.HTTP_200_OK)

            except psycopg2.Error as error:
                LOGGER.error(error, exc_info=True)

    @action(detail=False, methods=["post"])
    def database_live_api_export(self, request):
        """This is an API to fetch the data from an External API with an auth token
        and store it in JSON format."""
        try:
            dataset = DatasetV2(id=request.data.get("dataset"))
            url = request.data.get("url")
            auth_type = request.data.get("auth_type")
            dataset_name = request.data.get("dataset_name")
            source = request.data.get("source")
            file_name = request.data.get("file_name")

            if auth_type == 'NO_AUTH':
                response = requests.get(url)
            elif auth_type == 'API_KEY':
                headers = {request.data.get(
                    "api_key_name"): request.data.get("api_key_value")}
                response = requests.get(url, headers=headers)
            elif auth_type == 'BEARER':
                headers = {"Authorization": "Bearer " +
                                            request.data.get("token")}
                response = requests.get(url, headers=headers)

            # response = requests.get(url)
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except ValueError:
                    data = response.text

                file_path = file_ops.create_directory(
                    settings.DATASET_FILES_URL, [dataset_name, source])
                with open(file_path + "/" + file_name + ".json", "w") as outfile:
                    if type(data) == list:
                        json.dump(data, outfile)
                    else:
                        outfile.write(json.dumps(data))

                # result = os.listdir(file_path)
                instance = DatasetV2File.objects.create(
                    dataset=dataset,
                    source=source,
                    file=os.path.join(dataset_name, source,
                                      file_name + ".json"),
                    file_size=os.path.getsize(
                        os.path.join(settings.DATASET_FILES_URL, dataset_name, source, file_name + ".json")),
                    standardised_file=os.path.join(
                        dataset_name, source, file_name + ".json"),
                )
                serializer = DatasetFileV2NewSerializer(instance)
                return JsonResponse(serializer.data, status=status.HTTP_200_OK)

            LOGGER.error("Failed to fetch data from api")
            return Response({"message": f"API Response: {response.json()}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(
                f"Failed to fetch data from api ERROR: {e} and input fields: {request.data}")
            return Response({"message": f"API Response: {e}"}, status=status.HTTP_400_BAD_REQUEST)


class SupportTicketV2ModelViewSet(GenericViewSet):
    parser_class = JSONParser
    queryset = SupportTicketV2.objects.all()
    # serializer_class = SupportTicketV2Serializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return UpdateSupportTicketV2Serializer
        return SupportTicketV2Serializer

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def list_tickets(self, request, *args, **kwargs):
        data = request.data
        others = bool(data.pop("others", False))
        filters_data = data
        role_id = request.META.get("role_id")
        map_id = request.META.get("map_id")
        user_id = request.META.get("user_id")
        queryset = SupportTicketV2.objects.select_related(
            "user_map__organization", "user_map__user", "user_map__user__role", "user_map"
        ).order_by("-updated_at").all()
        # print(filters_data)
        # import pdb; pdb.set_trace()
        try:
            if str(role_id) == "1":
                # the person is an admin/steward so he should be able to view tickets:
                # 1. raise by co-stewards
                # 2. raised by participants under the steward.
                filter = {"user_map__user__role_id": 3} if others else {"user_map__user__role_id": 6}
                queryset = queryset.filter(user_map__user__on_boarded_by_id=None).filter(**filter, **filters_data)

            elif str(role_id) == "6":
                # the person is co-steward
                # 1. raised by himself
                # 2. raised by participants under himself.
                filter = {"user_map__user__on_boarded_by_id": user_id} if others else {"user_map_id": map_id}
                queryset = queryset.filter(**filter, **filters_data)

            elif str(role_id) == "3":
                print(filters_data)
                # participant
                # can only see his tickets
                queryset = queryset.filter(
                    user_map_id=map_id, **filters_data
                )
            page = self.paginate_queryset(queryset)
            support_tickets_serializer = SupportTicketV2Serializer(page, many=True)
            return self.get_paginated_response(support_tickets_serializer.data)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # API to retrieve a single object by its ID
    @timer
    @http_request_mutation
    def retrieve(self, request, pk):
        try:
            ticket_instance = SupportTicketV2.objects.prefetch_related(
                'resolution_set').get(id=pk)
        except SupportTicketV2.DoesNotExist as e:
            LOGGER.error(e, exc_info=True)
            return Response({
                "message": "No ticket found for this id.",
            }, status=status.HTTP_404_NOT_FOUND)
        try:
            current_user = UserOrganizationMap.objects.select_related(
                "organization").get(id=request.META.get("map_id"))
        except UserOrganizationMap.DoesNotExist:
            return Response(
                {
                    "message": "No user found for the map id."
                }, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            ticket_serializer = SupportTicketV2Serializer(ticket_instance)
            resolution_serializer = SupportTicketResolutionsSerializerMinimised(
                ticket_instance.resolution_set.order_by("created_at"),
                many=True)
            data = {
                'ticket': ticket_serializer.data,
                'resolutions': resolution_serializer.data,
                "logged_in_organization": {
                    "org_id": str(current_user.organization.id),
                    "org_logo": str(f"/media/{current_user.organization.logo}")
                }
            }
            return Response(data)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # API to create a new object

    @http_request_mutation
    def create(self, request):
        try:
            if request.data.get("ticket_attachment"):
                validity = check_file_name_length(incoming_file_name=request.data.get("ticket_attachment"),
                                                  accepted_file_name_size=NumericalConstants.FILE_NAME_LENGTH)
                if not validity:
                    file_length = len(str(request.data.get("ticket_attachment")))
                    return Response(
                        {"ticket_attachment": [
                            f"Ensure this filename has at most 100 characters ( it has {file_length} )."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            serializer = CreateSupportTicketV2Serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            object = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @timer
    @support_ticket_role_authorization(model_name="SupportTicketV2")
    def update(self, request, pk=None):
        try:
            queryset = self.get_queryset().select_related(
                "user_map__organization",
                "user_map__user", "user_map__user__role", "user_map"
            )
            object = get_object_or_404(queryset, pk=pk)
            serializer = self.get_serializer(
                object, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            object = serializer.save()
            return Response(serializer.data)
        except ValidationError as error:
            LOGGER.error(error, exc_info=True)
            return Response(error.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # API to delete an existing object by its ID
    @timer
    @support_ticket_role_authorization(model_name="SupportTicketV2")
    def destroy(self, request, pk=None):
        try:
            queryset = self.get_queryset()
            object = get_object_or_404(queryset, pk=pk)
            object.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # @http_request_mutation
    # @action(detail=False, methods=["get"])
    # def filter_support_tickets(self, request, *args, **kwargs):
    #     org_id = request.META.get("org_id")
    #     map_id = request.META.get("map_id")
    #     user_id = request.META.get("user_id")
    #     tickets = SupportTicketInternalServices.filter_support_ticket_service(
    #         map_id=map_id,
    #         org_id=org_id,
    #         role_id=request.META.get("role_id"),
    #         onboarded_by_id=request.META.get("onboarded_by"),
    #         status=request.GET.dict().get("status", None),
    #         category=request.GET.dict().get("category", None),
    #         start_date=request.GET.dict().get("start_date", None),
    #         end_date=request.GET.dict().get("end_date", None),
    #         results_for=request.GET.dict().get("results_for"),
    #         user_id=user_id
    #     )
    #
    #     page = self.paginate_queryset(tickets)
    #     support_tickets_serializer = SupportTicketV2Serializer(page, many=True)
    #     return self.get_paginated_response(support_tickets_serializer.data)

    @timer
    @http_request_mutation
    @action(detail=False, methods=["post"])
    def search_support_tickets(self, request, *args, **kwargs):
        try:
            tickets = SupportTicketInternalServices.search_tickets(
                search_text=request.data.get("name__icontains"),
                user_id=request.META.get("user_id")
            )

            page = self.paginate_queryset(tickets)
            support_tickets_serializer = SupportTicketV2Serializer(page, many=True)
            return self.get_paginated_response(support_tickets_serializer.data)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupportTicketResolutionsViewset(GenericViewSet):
    parser_class = JSONParser
    queryset = Resolution.objects.all()
    serializer_class = SupportTicketResolutionsSerializer
    pagination_class = CustomPagination

    @timer
    @support_ticket_role_authorization(model_name="Resolution")
    def create(self, request):
        # set map in in request object
        try:
            setattr(request.data, "_mutable", True)
            request_data = request.data
            request_data["user_map"] = request.META.get("map_id")
            serializer = CreateSupportTicketResolutionsSerializer(
                data=request_data)
            serializer.is_valid(raise_exception=True)
            object = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as error:
            LOGGER.error(error, exc_info=True)
            return Response(error.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # API to update an existing object by its ID
    @timer
    @support_ticket_role_authorization(model_name="Resolution")
    def update(self, request, pk=None):
        try:
            queryset = self.get_queryset()
            object = get_object_or_404(queryset, pk=pk)
            serializer = self.get_serializer(
                object, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            object = serializer.save()
            return Response(serializer.data)
        except ValidationError as error:
            LOGGER.error(error, exc_info=True)
            return Response(error.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # API to delete an existing object by its ID
    @timer
    @support_ticket_role_authorization(model_name="Resolution")
    def destroy(self, request, pk=None):
        try:
            queryset = self.get_queryset()
            object = get_object_or_404(queryset, pk=pk)
            object.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# LOGGER = logging.getLogger(__name__)
con = None





class TeamMemberViewSet(GenericViewSet):
    """Viewset for Product model"""

    serializer_class = TeamMemberListSerializer
    queryset = User.objects.all()
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        try:
            serializer = TeamMemberCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        try:
            instance = self.get_object()
            # request.data["role"] = UserRole.objects.get(role_name=request.data["role"]).id
            serializer = TeamMemberUpdateSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    serializer_class = OrganizationSerializerExhaustive
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
            user_org_queryset = UserOrganizationMap.objects.filter(user_id=request.data.get(Constants.USER_ID)).first()
            if user_org_queryset:
                return Response(
                    {"message": ["User is already associated with an organization"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                with transaction.atomic():
                    # create organization and userorganizationmap object
                    print("Creating org & user_org_map")
                    OrganizationSerializerValidator.validate_website(request.data)
                    org_serializer = OrganizationSerializerExhaustive(data=request.data, partial=True)
                    org_serializer.is_valid(raise_exception=True)
                    org_queryset = self.perform_create(org_serializer)

                    user_org_serializer = UserOrganizationMapSerializer(
                        data={
                            Constants.USER: user_obj.id,
                            Constants.ORGANIZATION: org_queryset.id,
                        }  # type: ignore
                    )
                    user_org_serializer.is_valid(raise_exception=True)
                    self.perform_create(user_org_serializer)
                    data = {
                        "user_map": user_org_serializer.data.get("id"),
                        "org_id": org_queryset.id,
                        "organization": org_serializer.data,
                    }
                    return Response(data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        """GET method: query the list of Organization objects"""
        try:
            user_org_queryset = (
                UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                .filter(organization__status=True)
                .all()
            )
            page = self.paginate_queryset(user_org_queryset)
            user_organization_serializer = ParticipantSerializer(page, many=True)
            return self.get_paginated_response(user_organization_serializer.data)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        try:
            user_obj = User.objects.get(id=pk, status=True)
            user_org_queryset = UserOrganizationMap.objects.prefetch_related(
                Constants.USER, Constants.ORGANIZATION
            ).filter(user=pk)

            if not user_org_queryset:
                data = {Constants.USER: {"id": user_obj.id}, Constants.ORGANIZATION: "null"}
                return Response(data, status=status.HTTP_200_OK)

            org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
            user_org_serializer = OrganizationSerializerExhaustive(org_obj)
            data = {
                Constants.USER: {"id": user_obj.id},
                Constants.ORGANIZATION: user_org_serializer.data,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk):
        """PUT method: update or PUT request for Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        user_obj = User.objects.get(id=pk, status=True)
        user_org_queryset = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION).filter(user=pk).all()
        )

        if not user_org_queryset:
            return Response({}, status=status.HTTP_404_NOT_FOUND)  # 310-360 not covered 4
        OrganizationSerializerValidator.validate_website(request.data)
        organization_serializer = OrganizationSerializerExhaustive(
            Organization.objects.get(id=user_org_queryset.first().organization_id),
            data=request.data,
            partial=True,
        )
        try:
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
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        try:
            user_obj = User.objects.get(id=pk, status=True)
            user_org_queryset = UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).get(user_id=pk)
            org_queryset = Organization.objects.get(id=user_org_queryset.organization_id)
            org_queryset.status = False
            self.perform_create(org_queryset)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    @authenticate_user(model=Organization)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        OrganizationSerializerValidator.validate_website(request.data)
        org_serializer = UserCreateSerializer(data=request.data, partial=True)
        org_serializer.is_valid(raise_exception=True)
        org_queryset = self.perform_create(org_serializer)
        org_id = org_queryset.id
        UserCreateSerializerValidator.validate_phone_number_format(request.data)
        user_serializer = UserCreateSerializer(data=request.data)
        user_serializer.is_valid(raise_exception=True)
        user_saved = self.perform_create(user_serializer)
        user_org_serializer = UserOrganizationMapSerializer(
            data={
                Constants.USER: user_saved.id,
                Constants.ORGANIZATION: org_id,
            }  # type: ignore
        )
        user_org_serializer.is_valid(raise_exception=True)
        self.perform_create(user_org_serializer)
        try:
            if user_saved.on_boarded_by:
                # datahub_admin = User.objects.filter(id=user_saved.on_boarded_by).first()
                admin_full_name = string_functions.get_full_name(
                    user_saved.on_boarded_by.first_name,
                    user_saved.on_boarded_by.last_name,
                )
            else:
                datahub_admin = User.objects.filter(role_id=1).first()
                admin_full_name = string_functions.get_full_name(datahub_admin.first_name, datahub_admin.last_name)
            participant_full_name = string_functions.get_full_name(
                request.data.get("first_name"), request.data.get("last_name")
            )
            data = {
                Constants.datahub_name: os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                "as_user": "Co-Steward" if user_saved.role == 6 else "Participant",
                "participant_admin_name": participant_full_name,
                "participant_organization_name": request.data.get("name"),
                "datahub_admin": admin_full_name,
                Constants.datahub_site: os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
            }

            email_render = render(request, Constants.WHEN_DATAHUB_ADMIN_ADDS_PARTICIPANT, data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=request.data.get("email"),
                content=mail_body,
                subject=Constants.PARTICIPANT_ORG_ADDITION_SUBJECT
                        + os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(user_org_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        on_boarded_by = request.GET.get("on_boarded_by", None)
        co_steward = request.GET.get("co_steward", False)
        approval_status = request.GET.get(Constants.APPROVAL_STATUS, True)
        name = request.GET.get(Constants.NAME, "")
        filter = {Constants.ORGANIZATION_NAME_ICONTAINS: name} if name else {}
        if on_boarded_by:
            roles = (
                UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                .filter(
                    user__status=True,
                    user__on_boarded_by=on_boarded_by,
                    user__role=3,
                    user__approval_status=approval_status,
                    **filter,
                )
                .order_by("-user__updated_at")
                .all()
            )
        elif co_steward:
            roles = (
                UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                .filter(user__status=True, user__role=6, **filter)
                .order_by("-user__updated_at")
                .all()
            )
            page = self.paginate_queryset(roles)
            participant_serializer = ParticipantCostewardSerializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        else:
            roles = (
                UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                .filter(
                    user__status=True,
                    user__role=3,
                    user__on_boarded_by=None,
                    user__approval_status=approval_status,
                    **filter,
                )
                .order_by("-user__updated_at")
                .all()
            )

        page = self.paginate_queryset(roles)
        participant_serializer = ParticipantSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        roles = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=True, user=pk)
            .first()
        )

        participant_serializer = ParticipantSerializer(roles, many=False)
        if participant_serializer.data:
            return Response(participant_serializer.data, status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_200_OK)

    @authenticate_user(model=Organization)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        try:
            participant = self.get_object()
            user_serializer = self.get_serializer(participant, data=request.data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            organization = Organization.objects.get(id=request.data.get(Constants.ID))
            OrganizationSerializerValidator.validate_website(request.data)
            organization_serializer = OrganizationSerializerExhaustive(organization, data=request.data, partial=True)
            organization_serializer.is_valid(raise_exception=True)
            user_data = self.perform_create(user_serializer)
            self.perform_create(organization_serializer)

            if user_data.on_boarded_by:
                admin_full_name = string_functions.get_full_name(user_data.first_name, user_data.last_name)
            else:
                datahub_admin = User.objects.filter(role_id=1).first()
                admin_full_name = string_functions.get_full_name(datahub_admin.first_name, datahub_admin.last_name)
            participant_full_name = string_functions.get_full_name(participant.first_name, participant.last_name)

            data = {
                Constants.datahub_name: os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                "participant_admin_name": participant_full_name,
                "participant_organization_name": organization.name,
                "datahub_admin": admin_full_name,
                Constants.datahub_site: os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
            }

            # update data & trigger_email
            email_render = render(request, Constants.DATAHUB_ADMIN_UPDATES_PARTICIPANT_ORGANIZATION, data)
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
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @authenticate_user(model=Organization)
    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        participant = self.get_object()
        user_organization = (
            UserOrganizationMap.objects.select_related(Constants.ORGANIZATION).filter(user_id=pk).first()
        )
        organization = Organization.objects.get(id=user_organization.organization_id)
        if participant.status:
            participant.status = False
            try:
                if participant.on_boarded_by:
                    datahub_admin = participant.on_boarded_by
                else:
                    datahub_admin = User.objects.filter(role_id=1).first()
                admin_full_name = string_functions.get_full_name(datahub_admin.first_name, datahub_admin.last_name)
                participant_full_name = string_functions.get_full_name(participant.first_name, participant.last_name)

                data = {
                    Constants.datahub_name: os.environ.get(Constants.DATAHUB_NAME, Constants.datahub_name),
                    "participant_admin_name": participant_full_name,
                    "participant_organization_name": organization.name,
                    "datahub_admin": admin_full_name,
                    Constants.datahub_site: os.environ.get(Constants.DATAHUB_SITE, Constants.datahub_site),
                }

                # delete data & trigger_email
                self.perform_create(participant)
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

                # Set the on_boarded_by_id to null if co_steward is deleted
                User.objects.filter(on_boarded_by=pk).update(on_boarded_by=None)

                return Response(
                    {"message": ["Participant deleted"]},
                    status=status.HTTP_204_NO_CONTENT,
                )
            except Exception as error:
                LOGGER.error(error, exc_info=True)
                return Response({"message": ["Internal server error"]}, status=500)

        elif participant.status is False:
            return Response(
                {"message": ["participant/co-steward already deleted"]},
                status=status.HTTP_204_NO_CONTENT,
            )

        return Response({"message": ["Internal server error"]}, status=500)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def get_list_co_steward(self, request, *args, **kwargs):
        try:
            users = (
                User.objects.filter(role__id=6, status=True)
                .values("id", "userorganizationmap__organization__name")
                .distinct("userorganizationmap__organization__name")
            )

            data = [
                {
                    "user": user["id"],
                    "organization_name": user["userorganizationmap__organization__name"],
                }
                for user in users
            ]
            return Response(data, status=200)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response({"message": str(e)}, status=500)


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
            # for email in email_list:
            #     if User.objects.filter(email=email):
            #         emails_found.append(email)
            #     else:
            #         emails_not_found.append(email)
            user = User.objects.filter(role_id=1).first()
            full_name = user.first_name + " " + str(user.last_name) if user.last_name else user.first_name
            data = {
                "datahub_name": os.environ.get("DATAHUB_NAME", "datahub_name"),
                "participant_admin_name": full_name,
                "datahub_site": os.environ.get("DATAHUB_SITE", "datahub_site"),
            }
            # render email from query_email template
            for email in email_list:
                try:
                    email_render = render(request, "datahub_admin_invites_participants.html", data)
                    mail_body = email_render.content.decode("utf-8")
                    Utils().send_email(
                        to_email=[email],
                        content=mail_body,
                        subject=os.environ.get("DATAHUB_NAME", "datahub_name")
                                + Constants.PARTICIPANT_INVITATION_SUBJECT,
                    )
                except Exception as e:
                    emails_not_found.append()
            failed = f"No able to send emails to this emails: {emails_not_found}"
            LOGGER.warning(failed)
            return Response(
                {
                    "message": f"Email successfully sent to {emails_found}",
                    "failed": failed,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(
                {"Error": f"Failed to send email"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )  # type: ignore


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
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
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
                Constants.GOVERNING_LAW: datahub_obj.governing_law if datahub_obj else None,
                Constants.PRIVACY_POLICY: datahub_obj.privacy_policy if datahub_obj else None,
                Constants.TOS: datahub_obj.tos if datahub_obj else None,
                Constants.LIMITATIONS_OF_LIABILITIES: datahub_obj.limitations_of_liabilities if datahub_obj else None,
                Constants.WARRANTY: datahub_obj.warranty if datahub_obj else None,
            }

            documents = {
                Constants.GOVERNING_LAW: file_paths.get("governing_law"),
                Constants.PRIVACY_POLICY: file_paths.get("privacy_policy"),
                Constants.TOS: file_paths.get("tos"),
                Constants.LIMITATIONS_OF_LIABILITIES: file_paths.get("limitations_of_liabilities"),
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
                file_operations.files_move(settings.TEMP_FILE_PATH, settings.DOCUMENTS_ROOT)
                return Response(
                    {"message": "Documents and content saved!"},
                    status=status.HTTP_201_CREATED,
                )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
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
                file_name = file_operations.file_rename(str(banner), "banner")
                shutil.rmtree(settings.THEME_ROOT)
                os.mkdir(settings.THEME_ROOT)
                os.makedirs(settings.CSS_ROOT)
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
                shutil.rmtree(settings.THEME_ROOT)
                os.mkdir(settings.THEME_ROOT)
                os.makedirs(settings.CSS_ROOT)
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

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
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
                shutil.rmtree(settings.THEME_ROOT)
                os.mkdir(settings.THEME_ROOT)
                os.makedirs(settings.CSS_ROOT)
                file_name = file_operations.file_rename(str(banner), "banner")
                # file_operations.remove_files(file_name, settings.THEME_ROOT)
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
                shutil.rmtree(settings.THEME_ROOT)
                os.mkdir(settings.THEME_ROOT)
                os.makedirs(settings.CSS_ROOT)
                file_name = file_operations.file_rename(str(banner), "banner")
                # file_operations.remove_files(file_name, settings.THEME_ROOT)
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
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            LOGGER.error(f"Error while filtering the ticketd ERROR: {error}")
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=400)

        page = self.paginate_queryset(data)
        participant_serializer = ParticipantSupportTicketSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    def trigger_email(self, request, template, to_email, subject, first_name, last_name, dataset_name):
        # trigger email to the participant as they are being added
        try:
            datahub_admin = User.objects.filter(role_id=1).first()
            admin_full_name = string_functions.get_full_name(datahub_admin.first_name, datahub_admin.last_name)
            participant_full_name = string_functions.get_full_name(first_name, last_name)

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
            if not csv_and_xlsx_file_validatation(request.data.get(Constants.SAMPLE_DATASET)):
                return Response(
                    {
                        Constants.SAMPLE_DATASET: [
                            "Invalid Sample dataset file (or) Atleast 5 rows should be available. please upload valid file"
                        ]
                    },
                    400,
                )
        try:
            data[Constants.APPROVAL_STATUS] = Constants.APPROVED
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @http_request_mutation
    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        try:
            data = []
            user_id = request.META.get(Constants.USER_ID)
            others = request.data.get(Constants.OTHERS)
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
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)

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
                data[Constants.CONTENT] = read_contents_from_csv_or_xlsx_file(data.get(Constants.SAMPLE_DATASET))
            return Response(data, status=status.HTTP_200_OK)
        return Response({}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        setattr(request.data, "_mutable", True)
        data = request.data
        data = {key: value for key, value in data.items() if value != "null"}
        if not data.get("is_public"):
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

        # trigger email to the participant
        user_map_queryset = UserOrganizationMap.objects.select_related(Constants.USER).get(id=instance.user_map_id)
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

        elif data.get(Constants.IS_ENABLED) == str(True) or data.get(Constants.IS_ENABLED) == str("true"):
            self.trigger_email(
                request,
                "datahub_admin_enables_dataset.html",
                user_obj.email,
                Constants.ENABLE_DATASET_SUBJECT,
                user_obj.first_name,
                user_obj.last_name,
                instance.name,
            )

        elif data.get(Constants.IS_ENABLED) == str(False) or data.get(Constants.IS_ENABLED) == str("false"):
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
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

        page = self.paginate_queryset(data)
        participant_serializer = DatahubDatasetsSerializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        try:
            data = request.data
            org_id = data.pop(Constants.ORG_ID, "")
            others = data.pop(Constants.OTHERS, "")
            user_id = data.pop(Constants.USER_ID, "")

            ####

            org_id = request.META.pop(Constants.ORG_ID, "")
            others = request.META.pop(Constants.OTHERS, "")
            user_id = request.META.pop(Constants.USER_ID, "")

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
                LOGGER.error("Error while filtering the datasets. ERROR: %s", error)
                return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
            return Response(
                {
                    "geography": geography,
                    "crop_detail": crop_detail,
                    "category_detail": category_detail,
                },
                status=200,
            )
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def search_datasets(self, request, *args, **kwargs):
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")

        org_id = request.META.pop(Constants.ORG_ID, "")
        others = request.META.pop(Constants.OTHERS, "")
        user_id = request.META.pop(Constants.USER_ID, "")

        search_pattern = data.pop(Constants.SEARCH_PATTERNS, "")
        exclude, filters = {}, {}

        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            filters = {Constants.NAME_ICONTAINS: search_pattern} if search_pattern else {}
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
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error)
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
                UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                .filter(user__role=3, user__status=True, is_temp=False)
                .count()
            )
            total_datasets = (
                DatasetV2.objects.select_related("user_map", "user_map__user", "user_map__organization")
                .filter(user_map__user__status=True, is_temp=False)
                .count()
            )
            # write a function to compute data exchange
            active_connectors = Connectors.objects.filter(status=True).count()
            total_data_exchange = {"total_data": 50, "unit": "Gbs"}

            datasets = Datasets.objects.filter(status=True).values_list("category", flat=True)
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
            closed_support_tickets = SupportTicket.objects.filter(status="closed").count()
            hold_support_tickets = SupportTicket.objects.filter(status="hold").count()

            # retrieve 3 recent support tickets
            recent_tickets_queryset = SupportTicket.objects.order_by("updated_at")[0:3]
            recent_tickets_serializer = RecentSupportTicketSerializer(recent_tickets_queryset, many=True)
            support_tickets = {
                "open_requests": open_support_tickets,
                "closed_requests": closed_support_tickets,
                "hold_requests": hold_support_tickets,
                "recent_tickets": recent_tickets_serializer.data,
            }

            # retrieve 3 recent updated datasets
            # datasets_queryset = Datasets.objects.order_by("updated_at")[0:3]
            datasets_queryset = Datasets.objects.filter(status=True).order_by("-updated_at").all()
            datasets_queryset_pages = self.paginate_queryset(datasets_queryset)  # paginaged connectors list
            datasets_serializer = RecentDatasetListSerializer(datasets_queryset_pages, many=True)

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
    queryset = DatasetV2.objects.prefetch_related('dataset_cat_map', 'dataset_cat_map__sub_category',
                                                  'dataset_cat_map__sub_category__category').all()
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
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                    file_path = os.path.join(directory, request.data.get("source"), file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        LOGGER.info(f"Deleting file: {file_name}")
                        data = {file_name: "File deleted"}
                        return Response(data, status=status.HTTP_204_NO_CONTENT)

                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def get_dataset_files(self, request, *args, **kwargs):
        """
        Get list of dataset files from temporary location.
        """
        try:
            # files_list = file_operations.get_csv_or_xls_files_from_directory(settings.TEMP_DATASET_URL + request.query_params.get(Constants.DATASET_NAME))
            dataset = request.data.get("dataset")
            queryset = DatasetV2File.objects.filter(dataset=dataset)
            serializer = DatasetFileV2NewSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            return Response(f"No such dataset created {error}", status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def get_dataset_file_columns(self, request, *args, **kwargs):
        """
        To retrieve the list of columns of a dataset file from temporary location
        """
        try:
            dataset_file = DatasetV2File.objects.get(id=request.data.get("id"))
            file_path = str(dataset_file.file)
            if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                df = pd.read_excel(os.path.join(settings.DATASET_FILES_URL, file_path), index_col=None, nrows=1)
            else:
                df = pd.read_csv(os.path.join(settings.DATASET_FILES_URL, file_path), index_col=False, nrows=1)
            df.columns = df.columns.astype(str)
            result = df.columns.tolist()
            return Response(result, status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error(f"Cannot get the columns of the selected file: {error}")
            return Response(
                f"Cannot get the columns of the selected file: {error}",
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def standardise(self, request, *args, **kwargs):
        """
        Method to standardise a dataset and generate a file along with it.
        """

        # 1. Take the standardisation configuration variables.
        try:
            standardisation_configuration = request.data.get("standardisation_configuration")
            mask_columns = request.data.get("mask_columns")
            file_path = request.data.get("file_path")
            is_standardised = request.data.get("is_standardised", None)

            if is_standardised:
                file_path = file_path.replace("/standardised", "/datasets")

            if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                df = pd.read_excel(os.path.join(settings.DATASET_FILES_URL, file_path), index_col=None)
            else:
                df = pd.read_csv(os.path.join(settings.DATASET_FILES_URL, file_path), index_col=False)

            df["status"] = True
            df.loc[df["status"] == True, mask_columns] = "######"
            # df[mask_columns] = df[mask_columns].mask(True)
            del df["status"]
            # print()
            df.rename(columns=standardisation_configuration, inplace=True)
            df.columns = df.columns.astype(str)
            file_dir = file_path.split("/")
            standardised_dir_path = "/".join(file_dir[-3:-1])
            file_name = file_dir[-1]
            if not os.path.exists(os.path.join(settings.TEMP_STANDARDISED_DIR, standardised_dir_path)):
                os.makedirs(os.path.join(settings.TEMP_STANDARDISED_DIR, standardised_dir_path))
            # print(df)
            if file_name.endswith(".csv"):
                df.to_csv(
                    os.path.join(settings.TEMP_STANDARDISED_DIR, standardised_dir_path, file_name)
                )  # type: ignore
            else:
                df.to_excel(
                    os.path.join(settings.TEMP_STANDARDISED_DIR, standardised_dir_path, file_name)
                )  # type: ignore
            return Response(
                {"standardised_file_path": f"{standardised_dir_path}/{file_name}"},
                status=status.HTTP_200_OK,
            )

        except Exception as error:
            LOGGER.error(f"Could not standardise {error}")
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

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
        try:
            serializer = self.get_serializer(
                data=request.data,
                context={
                    "standardisation_template": request.data.get("standardisation_template"),
                    "standardisation_config": request.data.get("standardisation_config"),
                },
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @authenticate_user(model=DatasetV2)
    def update(self, request, pk, *args, **kwargs):
        """
        ``PUT`` method: PUT method to edit or update the dataset (DatasetV2) and its files (DatasetV2File). [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/<uuid>
        """
        # setattr(request.data, "_mutable", True)
        try:
            data = request.data.copy()
            to_delete = ast.literal_eval(data.get("deleted", "[]"))
            sub_categories_map = data.pop("sub_categories_map")
            self.dataset_files(data, to_delete)
            datasetv2 = self.get_object()
            serializer = self.get_serializer(
                datasetv2,
                data=data,
                partial=True,
                context={
                    "standardisation_template": request.data.get("standardisation_template"),
                    "standardisation_config": request.data.get("standardisation_config"),
                },
            )
            serializer.is_valid(raise_exception=True)
            a = DatasetSubCategoryMap.objects.filter(dataset_id=datasetv2).delete()
            serializer.save()
            sub_categories_map = json.loads(sub_categories_map[0]) if c else []
            dataset_sub_cat_instances = [
                DatasetSubCategoryMap(dataset=datasetv2, sub_category=SubCategory.objects.get(id=sub_cat)
                                      ) for sub_cat in sub_categories_map]

            DatasetSubCategoryMap.objects.bulk_create(dataset_sub_cat_instances)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # not being used
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
        user_map = request.GET.get("user_map")
        type = request.GET.get("type", None)
        obj = self.get_object()
        serializer = self.get_serializer(obj).data
        dataset_file_obj = DatasetV2File.objects.prefetch_related("dataset_v2_file").filter(dataset_id=obj.id)
        data = []
        for file in dataset_file_obj:
            path_ = os.path.join(settings.DATASET_FILES_URL, str(file.standardised_file))
            file_path = {}
            file_path["id"] = file.id
            file_path["content"] = read_contents_from_csv_or_xlsx_file(
                os.path.join(settings.DATASET_FILES_URL, str(file.standardised_file)), file.standardised_configuration
            )
            file_path["file"] = path_
            file_path["source"] = file.source
            file_path["file_size"] = file.file_size
            file_path["accessibility"] = file.accessibility
            file_path["standardised_file"] = os.path.join(settings.DATASET_FILES_URL, str(file.standardised_file))
            file_path["standardisation_config"] = file.standardised_configuration
            type_filter = type if type == "api" else "dataset_file"
            queryset = file.dataset_v2_file.filter(type=type_filter)
            if user_map:
                queryset = queryset.filter(user_organization_map=user_map)
            usage_policy = UsagePolicyDetailSerializer(
                queryset.order_by("-updated_at").all(),
                many=True
            ).data if queryset.exists() else []
            file_path["usage_policy"] = usage_policy
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
        exclude_filters, filters = {}, {}
        if others:
            exclude_filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            data = (
                DatasetV2.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                ).prefetch_related(
                    'dataset_cat_map')
                .filter(**data, **filters)
                .exclude(is_temp=True)
                .exclude(**exclude_filters)
                .order_by(Constants.UPDATED_AT)
                .reverse()
                .all()
            )
            # if categories is not None:
            #     data = data.filter(
            #         reduce(
            #             operator.or_,
            #             (Q(category__contains=cat) for cat in categories),
            #         )
            #     )
            if on_boarded_by:
                data = (
                    data.filter(user_map__user__on_boarded_by=user_id)
                    if others
                    else data.filter(user_map__user_id=user_id)
                )
            else:
                user_onboarded_by = User.objects.get(id=user_id).on_boarded_by
                if user_onboarded_by:
                    data = (
                        data.filter(
                            Q(user_map__user__on_boarded_by=user_onboarded_by.id)
                            | Q(user_map__user_id=user_onboarded_by.id)
                        )
                        if others
                        else data.filter(user_map__user_id=user_id)
                    )
                else:
                    data = (
                        data.filter(user_map__user__on_boarded_by=None).exclude(user_map__user__role_id=6)
                        if others
                        else data
                    )
        except Exception as error:  # type: ignore
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error, exc_info=True)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        page = self.paginate_queryset(data)
        participant_serializer = DatahubDatasetsV2Serializer(page, many=True)
        return self.get_paginated_response(participant_serializer.data)

    @action(detail=False, methods=["post"])
    @http_request_mutation
    def filters_data(self, request, *args, **kwargs):
        """This function provides the filters data"""
        data = request.META
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        user_id = data.pop(Constants.USER_ID, "")

        org_id = request.META.pop(Constants.ORG_ID, "")
        others = request.META.pop(Constants.OTHERS, "")
        user_id = request.META.pop(Constants.USER_ID, "")

        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
            # filters = {Constants.APPROVAL_STATUS: Constants.APPROVED}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            geography = (
                DatasetV2.objects.values_list(Constants.GEOGRAPHY, flat=True)
                .filter(**filters)
                .exclude(geography="null")
                .exclude(geography__isnull=True)
                .exclude(geography="")
                .exclude(is_temp=True, **exclude)
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
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response({"geography": geography, "category_detail": category_detail}, status=200)

    # @action(detail=False, methods=["post"])
    # def search_datasets(self, request, *args, **kwargs):
    #     data = request.data
    #     org_id = data.pop(Constants.ORG_ID, "")
    #     others = data.pop(Constants.OTHERS, "")
    #     user_id = data.pop(Constants.USER_ID, "")
    #     search_pattern = data.pop(Constants.SEARCH_PATTERNS, "")
    #     exclude, filters = {}, {}

    #     if others:
    #         exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
    #         filters = {Constants.NAME_ICONTAINS: search_pattern} if search_pattern else {}
    #     else:
    #         filters = (
    #             {
    #                 Constants.USER_MAP_ORGANIZATION: org_id,
    #                 Constants.NAME_ICONTAINS: search_pattern,
    #             }
    #             if org_id
    #             else {}
    #         )
    #     try:
    #         data = (
    #             DatasetV2.objects.select_related(
    #                 Constants.USER_MAP,
    #                 Constants.USER_MAP_USER,
    #                 Constants.USER_MAP_ORGANIZATION,
    #             )
    #             .filter(user_map__user__status=True, status=True, **data, **filters)
    #             .exclude(**exclude)
    #             .order_by(Constants.UPDATED_AT)
    #             .reverse()
    #             .all()
    #         )
    #         page = self.paginate_queryset(data)
    #         participant_serializer = DatahubDatasetsV2Serializer(page, many=True)
    #         return self.get_paginated_response(participant_serializer.data)
    #     except Exception as error:  # type: ignore
    #         LOGGER.error("Error while filtering the datasets. ERROR: %s", error)
    #         return Response(
    #             f"Invalid filter fields: {list(request.data.keys())}",
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         )

    @authenticate_user(model=DatasetV2File)
    def destroy(self, request, pk, *args, **kwargs):
        """
        ``DELETE`` method: DELETE method to delete the DatasetV2 instance and its reference DatasetV2File instances,
        along with dataset files stored at the URL. [see here][ref]

        **Endpoint**
        [ref]: /datahub/dataset/v2/
        """
        try:
            dataset_obj = self.get_object()
            if dataset_obj:
                dataset_files = DatasetV2File.objects.filter(dataset_id=dataset_obj.id)
                dataset_dir = os.path.join(settings.DATASET_FILES_URL, str(dataset_obj.name))

                if os.path.exists(dataset_dir):
                    shutil.rmtree(dataset_dir)
                    LOGGER.info(f"Deleting file: {dataset_dir}")

                # delete DatasetV2File & DatasetV2 instances
                LOGGER.info(f"Deleting dataset obj: {dataset_obj}")
                dataset_files.delete()
                dataset_obj.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)


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

    @action(detail=False, methods=["get"])
    def datasets_names(self, request, *args, **kwargs):
        try:
            datasets_with_excel_files = (
                DatasetV2.objects.prefetch_related("datasets")
                .select_related("user_map")
                .filter(
                    Q(datasets__file__endswith=".xls")
                    | Q(datasets__file__endswith=".xlsx")
                    | Q(datasets__file__endswith=".csv")
                )
                .filter(user_map__organization_id=request.GET.get("org_id"), is_temp=False)
                .distinct()
                .values("name", "id", org_name=F("user_map__organization__name"))
            )
            return Response(datasets_with_excel_files, status=status.HTTP_200_OK)
        except Exception as e:
            error_message = f"An error occurred while fetching dataset names: {e}"
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def datasets_file_names(self, request, *args, **kwargs):
        dataset_ids = request.data.get("datasets")
        user_map = request.data.get("user_map")
        if dataset_ids:
            try:
                # Get list of files for each dataset
                files = (
                    DatasetV2File.objects.select_related("dataset_v2_file", "dataset")
                    .filter(dataset_id__in=dataset_ids)
                    .filter(Q(file__endswith=".xls") | Q(file__endswith=".xlsx") | Q(file__endswith=".csv"))
                    .filter(
                        Q(accessibility__in=["public", "registered"])
                        | Q(dataset__user_map_id=user_map)
                        | Q(dataset_v2_file__approval_status="approved")
                    )
                    .values(
                        "id",
                        "dataset",
                        "standardised_file",
                        dataset_name=F("dataset__name"),
                    )
                    .distinct()
                )
                files = [
                    {
                        **row,
                        "file_name": row.get("standardised_file", "").split("/")[-1],
                    }
                    for row in files
                ]
                return Response(files, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response([], status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def datasets_col_names(self, request, *args, **kwargs):
        try:
            file_paths = request.data.get("files")
            result = {}
            for file_path in file_paths:
                path = file_path
                file_path = unquote(file_path).replace("/media/", "")
                if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                    df = pd.read_excel(
                        os.path.join(settings.DATASET_FILES_URL, file_path),
                        index_col=None,
                        nrows=3,
                    )
                else:
                    df = pd.read_csv(
                        os.path.join(settings.DATASET_FILES_URL, file_path),
                        index_col=False,
                        nrows=3,
                    )
                df = df.drop(df.filter(regex="Unnamed").columns, axis=1)
                result[path] = df.columns.tolist()
                result[Constants.ID] = DatasetV2File.objects.get(standardised_file=file_path).id
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def datasets_join_condition(self, request, *args, **kwargs):
        try:
            file_path1 = request.data.get("file_path1")
            file_path2 = request.data.get("file_path2")
            columns1 = request.data.get("columns1")
            columns2 = request.data.get("columns2")
            condition = request.data.get("condition")

            # Load the files into dataframes
            if file_path1.endswith(".xlsx") or file_path1.endswith(".xls"):
                df1 = pd.read_excel(os.path.join(settings.MEDIA_ROOT, file_path1), usecols=columns1)
            else:
                df1 = pd.read_csv(os.path.join(settings.MEDIA_ROOT, file_path1), usecols=columns1)
            if file_path2.endswith(".xlsx") or file_path2.endswith(".xls"):
                df2 = pd.read_excel(os.path.join(settings.MEDIA_ROOT, file_path2), usecols=columns2)
            else:
                df2 = pd.read_csv(os.path.join(settings.MEDIA_ROOT, file_path2), usecols=columns2)
            # Join the dataframes
            result = pd.merge(
                df1,
                df2,
                how=request.data.get("how", "left"),
                left_on=request.data.get("left_on"),
                right_on=request.data.get("right_on"),
            )

            # Return the joined dataframe as JSON
            return Response(result.to_json(orient="records", index=False), status=status.HTTP_200_OK)

        except Exception as e:
            LOGGER.error(str(e), exc_info=True)
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=["get"])
    def organization(self, request, *args, **kwargs):
        """GET method: query the list of Organization objects"""
        on_boarded_by = request.GET.get("on_boarded_by", "")
        user_id = request.GET.get("user_id", "")
        try:
            user_org_queryset = (
                UserOrganizationMap.objects.prefetch_related("user_org_map")
                .select_related("organization", "user")
                .annotate(dataset_count=Count("user_org_map__id"))
                .values(
                    name=F("organization__name"),
                    org_id=F("organization_id"),
                    org_description=F("organization__org_description"),
                )
                .filter(user__status=True, dataset_count__gt=0)
                .all()
            )
            if on_boarded_by:
                user_org_queryset = user_org_queryset.filter(
                    Q(user__on_boarded_by=on_boarded_by) | Q(user_id=on_boarded_by)
                )
            else:
                user_onboarded_by = User.objects.get(id=user_id).on_boarded_by
                if user_onboarded_by:
                    user_org_queryset = user_org_queryset.filter(
                        Q(user__on_boarded_by=user_onboarded_by.id) | Q(user__id=user_onboarded_by.id)
                    )
                else:
                    user_org_queryset = user_org_queryset.filter(user__on_boarded_by=None).exclude(user__role_id=6)
            return Response(user_org_queryset, 200)
        except Exception as e:
            error_message = f"An error occurred while fetching Organization details: {e}"
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StandardisationTemplateView(GenericViewSet):
    serializer_class = StandardisationTemplateViewSerializer
    queryset = StandardisationTemplate.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            LOGGER.info("Standardisation Template Created Successfully.")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["put"])
    def update_standardisation_template(self, request, *args, **kwargs):
        update_list = list()
        create_list = list()
        try:
            for data in request.data:
                if data.get(Constants.ID, None):
                    # Update
                    id = data.pop(Constants.ID)
                    instance = StandardisationTemplate.objects.get(id=id)
                    serializer = StandardisationTemplateUpdateSerializer(instance, data=data, partial=True)
                    serializer.is_valid(raise_exception=True)
                    update_list.append(StandardisationTemplate(id=id, **data))
                else:
                    # Create
                    create_list.append(data)

            create_serializer = self.get_serializer(data=create_list, many=True)
            create_serializer.is_valid(raise_exception=True)
            StandardisationTemplate.objects.bulk_update(
                update_list, fields=["datapoint_category", "datapoint_attributes"]
            )
            create_serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        except Exception as error:
            LOGGER.error("Issue while Updating Standardisation Template", exc_info=True)
            return Response(
                f"Issue while Updating Standardisation Template {error}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        LOGGER.info(f"Deleted datapoint Category from standardisation template {instance.datapoint_category}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PolicyListAPIView(generics.ListCreateAPIView):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer


class PolicyDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer


class DatasetV2View(GenericViewSet):
    queryset = DatasetV2.objects.all()
    serializer_class = DatasetV2NewListSerializer
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            LOGGER.info("Dataset created Successfully.")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        serializer = DatasetV2DetailNewSerializer(instance=self.get_object())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @authenticate_user(model=DatasetV2)
    def update(self, request, *args, **kwargs):
        # setattr(request.data, "_mutable", True)
        try:
            instance = self.get_object()
            data = request.data.copy()
            sub_categories_map = data.pop("sub_categories_map")
            data["is_temp"] = False
            serializer = self.get_serializer(instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            DatasetSubCategoryMap.objects.filter(dataset_id=instance).delete()
            serializer.save()
            # sub_categories_map = json.loads(sub_categories_map[0]) if c else []
            dataset_sub_cat_instances = [
                DatasetSubCategoryMap(dataset=instance, sub_category=SubCategory.objects.get(id=sub_cat)
                                      ) for sub_cat in sub_categories_map]

            DatasetSubCategoryMap.objects.bulk_create(dataset_sub_cat_instances)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @authenticate_user(model=DatasetV2)
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def requested_datasets(self, request, *args, **kwargs):
        try:
            user_map_id = request.data.get("user_map")
            policy_type = request.data.get("type", None)
            if policy_type == "api":
                dataset_file_id = request.data.get("dataset_file")
                requested_recieved = (
                    UsagePolicy.objects.select_related(
                        "dataset_file",
                        "dataset_file__dataset",
                        "user_organization_map__organization",
                    )
                    .filter(dataset_file__dataset__user_map_id=user_map_id, dataset_file_id=dataset_file_id)
                    .values(
                        "id",
                        "approval_status",
                        "accessibility_time",
                        "updated_at",
                        "created_at",
                        dataset_id=F("dataset_file__dataset_id"),
                        dataset_name=F("dataset_file__dataset__name"),
                        file_name=F("dataset_file__file"),
                        organization_name=F("user_organization_map__organization__name"),
                        organization_email=F("user_organization_map__organization__org_email"),
                        organization_phone_number=F("user_organization_map__organization__phone_number"),
                    )
                    .order_by("-updated_at")
                )
                response_data = []
                for values in requested_recieved:
                    org = {
                        "org_email": values["organization_email"],
                        "name": values["organization_name"],
                        "phone_number": values["organization_phone_number"],
                    }
                    values.pop("organization_email")
                    values.pop("organization_name")
                    values.pop("organization_phone_number")
                    values["file_name"] = values.get("file_name", "").split("/")[-1]

                    values["organization"] = org
                    response_data.append(values)
                return Response(
                    {
                        "recieved": response_data,
                    },
                    200,
                )
            requested_sent = (
                UsagePolicy.objects.select_related(
                    "dataset_file",
                    "dataset_file__dataset",
                    "user_organization_map__organization",
                )
                .filter(user_organization_map=user_map_id, type="dataset_file")
                .values(
                    "approval_status",
                    "updated_at",
                    "accessibility_time",
                    "type",
                    dataset_id=F("dataset_file__dataset_id"),
                    dataset_name=F("dataset_file__dataset__name"),
                    file_name=F("dataset_file__file"),
                    organization_name=F("dataset_file__dataset__user_map__organization__name"),
                    organization_email=F("dataset_file__dataset__user_map__organization__org_email"),
                )
                .order_by("-updated_at")
            )

            requested_recieved = (
                UsagePolicy.objects.select_related(
                    "dataset_file",
                    "dataset_file__dataset",
                    "user_organization_map__organization",
                )
                .filter(dataset_file__dataset__user_map_id=user_map_id, type="dataset_file")
                .values(
                    "id",
                    "approval_status",
                    "accessibility_time",
                    "updated_at",
                    "type",
                    dataset_id=F("dataset_file__dataset_id"),
                    dataset_name=F("dataset_file__dataset__name"),
                    file_name=F("dataset_file__file"),
                    organization_name=F("user_organization_map__organization__name"),
                    organization_email=F("user_organization_map__organization__org_email"),
                )
                .order_by("-updated_at")
            )
            return Response(
                {
                    "sent": [
                        {
                            **values,
                            "file_name": values.get("file_name", "").split("/")[-1],
                        }
                        for values in requested_sent
                    ],
                    "recieved": [
                        {
                            **values,
                            "file_name": values.get("file_name", "").split("/")[-1],
                        }
                        for values in requested_recieved
                    ],
                },
                200,
            )
        except Exception as error:
            LOGGER.error("Issue while Retrive requeted data", exc_info=True)
            return Response(
                f"Issue while Retrive requeted data {error}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # def list(self, request, *args, **kwargs):
    #     page = self.paginate_queryset(self.queryset)
    #     serializer = self.get_serializer(page, many=True).exclude(is_temp = True)
    #     return self.get_paginated_response(serializer.data)

    @http_request_mutation
    @action(detail=True, methods=["post"])
    def get_dashboard_chart_data(self, request, pk, *args, **kwargs):
        try:
            filters = True
            role_id = request.META.get("role_id")
            map_id = request.META.get("map_id")
            dataset_file_obj = DatasetV2File.objects.get(id=pk)
            dataset_file = str(dataset_file_obj.file)
            if role_id != str(1):
                if UsagePolicy.objects.filter(
                        user_organization_map=map_id,
                        dataset_file_id=pk,
                        approval_status="approved"
                ).order_by("-updated_at").first():
                    filters = True
                elif DatasetV2File.objects.select_related("dataset").filter(id=pk, dataset__user_map_id=map_id).first():
                    filters = True
                else:
                    filters = False
            # Create a dictionary mapping dataset types to dashboard generation functions
            dataset_type_to_dashboard_function = {
                "omfp": generate_omfp_dashboard,
                "fsp": generate_fsp_dashboard,
                "knfd": generate_knfd_dashboard,
                "kiamis": "generate_kiamis_dashboard",
            }

            # Determine the dataset type based on the filename
            dataset_type = None
            for key in dataset_type_to_dashboard_function:
                if key in dataset_file.lower():
                    dataset_type = key
                    break

            # If dataset_type is not found, return an error response
            if dataset_type is None:
                return Response(
                    "Requested resource is currently unavailable. Please try again later.",
                    status=status.HTTP_200_OK,
                )

            # Generate the base hash key
            hash_key = generate_hash_key_for_dashboard(
                dataset_type if role_id == str(1) else pk,
                request.data, role_id, filters
            )

            # Check if the data is already cached
            cache_data = cache.get(hash_key, {})
            if cache_data:
                LOGGER.info("Dashboard details found in cache", exc_info=True)
                return Response(cache_data, status=status.HTTP_200_OK)

            # Get the appropriate dashboard generation function
            dashboard_generator = dataset_type_to_dashboard_function.get(dataset_type)

            if dashboard_generator and dataset_type != 'kiamis':
                # Generate the dashboard data using the selected function
                return dashboard_generator(
                    dataset_file if role_id != str(1) else self.get_consolidated_file(dataset_type),
                    request.data, hash_key, filters
                )

            # serializer = DatahubDatasetFileDashboardFilterSerializer(data=request.data)
            # serializer.is_valid(raise_exception=True)
            counties = []
            sub_counties = []
            gender = []
            value_chain = []

            # if serializer.data.get("county"):
            counties = request.data.get("county")

            # if serializer.data.get("sub_county"):
            sub_counties = request.data.get("sub_county")

            # if serializer.data.get("gender"):
            gender = request.data.get("gender")

            # if serializer.data.get("value_chain"):
            value_chain = request.data.get("value_chain")
            cols_to_read = ['Gender', 'Constituency', 'Millet', 'County', 'Sub County', 'Crop Production',
                            'farmer_mobile_number',
                            'Livestock Production', 'Ducks', 'Other Sheep', 'Total Area Irrigation', 'Family',
                            'Ward',
                            'Other Money Lenders', 'Micro-finance institution', 'Self (Salary or Savings)',
                            "Natural rivers and stream", "Water Pan",
                            'NPK', 'Superphosphate', 'CAN',
                            'Urea', 'Other', 'Do you insure your crops?',
                            'Do you insure your farm buildings and other assets?', 'Other Dual Cattle',
                            'Cross breed Cattle', 'Cattle boma',
                            'Small East African Goats', 'Somali Goat', 'Other Goat', 'Chicken -Indigenous',
                            'Chicken -Broilers', 'Chicken -Layers', 'Highest Level of Formal Education',
                            'Maize food crop', "Beans", 'Cassava', 'Sorghum', 'Potatoes', 'Cowpeas']
            if role_id == str(1):
                dataset_file = self.get_consolidated_file("kiamis")
            try:
                if dataset_file.endswith(".xlsx") or dataset_file.endswith(".xls"):
                    df = pd.read_excel(os.path.join(settings.DATASET_FILES_URL, dataset_file))
                elif dataset_file.endswith(".csv"):
                    df = pd.read_csv(os.path.join(settings.DATASET_FILES_URL, dataset_file), usecols=cols_to_read,
                                     low_memory=False)
                    # df.columns = df.columns.str.strip()
                else:
                    return Response(
                        "Unsupported file please use .xls or .csv.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                df['Ducks'] = pd.to_numeric(df['Ducks'], errors='coerce')
                df['Other Sheep'] = pd.to_numeric(df['Other Sheep'], errors='coerce')
                df['Family'] = pd.to_numeric(df['Family'], errors='coerce')
                df['Other Money Lenders'] = pd.to_numeric(df['Other Money Lenders'], errors='coerce')
                df['Micro-finance institution'] = pd.to_numeric(df['Micro-finance institution'], errors='coerce')
                df['Self (Salary or Savings)'] = pd.to_numeric(df['Self (Salary or Savings)'], errors='coerce')
                df['Natural rivers and stream'] = pd.to_numeric(df['Natural rivers and stream'], errors='coerce')
                df["Water Pan"] = pd.to_numeric(df["Water Pan"], errors='coerce')
                df['Total Area Irrigation'] = pd.to_numeric(df['Total Area Irrigation'], errors='coerce')
                df['NPK'] = pd.to_numeric(df['NPK'], errors='coerce')
                df['Superphosphate'] = pd.to_numeric(df['Superphosphate'], errors='coerce')
                df['CAN'] = pd.to_numeric(df['CAN'], errors='coerce')
                df['Urea'] = pd.to_numeric(df['Urea'], errors='coerce')
                df['Other'] = pd.to_numeric(df['Other'], errors='coerce')
                df['Other Dual Cattle'] = pd.to_numeric(df['Other Dual Cattle'], errors='coerce')
                df['Cross breed Cattle'] = pd.to_numeric(df['Cross breed Cattle'], errors='coerce')
                df['Cattle boma'] = pd.to_numeric(df['Cattle boma'], errors='coerce')
                df['Small East African Goats'] = pd.to_numeric(df['Small East African Goats'], errors='coerce')
                df['Somali Goat'] = pd.to_numeric(df['Somali Goat'], errors='coerce')
                df['Other Goat'] = pd.to_numeric(df['Other Goat'], errors='coerce')
                df['Chicken -Indigenous'] = pd.to_numeric(df['Chicken -Indigenous'], errors='coerce')
                df['Chicken -Broilers'] = pd.to_numeric(df['Chicken -Broilers'], errors='coerce')
                df['Chicken -Layers'] = pd.to_numeric(df['Chicken -Layers'], errors='coerce')
                df['Do you insure your crops?'] = pd.to_numeric(df['Do you insure your crops?'], errors='coerce')
                df['Highest Level of Formal Education'] = pd.to_numeric(df['Highest Level of Formal Education'],
                                                                        errors='coerce')
                df['Do you insure your farm buildings and other assets?'] = pd.to_numeric(
                    df['Do you insure your farm buildings and other assets?'], errors='coerce')

                data = filter_dataframe_for_dashboard_counties(
                    df=df,
                    counties=counties if counties else [],
                    sub_counties=sub_counties if sub_counties else [],
                    gender=gender if gender else [],
                    value_chain=value_chain if value_chain else [],
                    hash_key=hash_key,
                    filters=filters
                )
            except Exception as e:
                LOGGER.error(e, exc_info=True)
                return Response(
                    f"Something went wrong, please try again. {e}",
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                data,
                status=status.HTTP_200_OK,
            )

        except DatasetV2File.DoesNotExist as e:
            LOGGER.error(e, exc_info=True)
            return Response(
                "No dataset file for the provided id.",
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(
                f"Something went wrong, please try again. {e}",
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_consolidated_file(self, name):
        consolidated_file = f"consolidated_{name}.csv"
        dataframes = []
        thread_list = []
        combined_df = pd.DataFrame([])
        try:
            if os.path.exists(os.path.join(settings.DATASET_FILES_URL, consolidated_file)):
                LOGGER.info(f"{consolidated_file} file available")
                return consolidated_file
            else:
                dataset_file_objects = (
                    DatasetV2File.objects
                    .select_related("dataset")
                    .filter(dataset__name__icontains=name, file__iendswith=".csv")
                    .values_list('file', flat=True).distinct()  # Flatten the list of values
                )

                def read_csv_file(file_path):
                    chunk_size = 50000
                    chunk_df = pd.DataFrame([])
                    chunks = 0
                    try:
                        LOGGER.info(f"{file_path} Consolidation started")
                        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                            # Append the processed chunk to the combined DataFrame
                            chunk_df = pd.concat([chunk_df, chunk], ignore_index=True)
                            chunks = chunks + 1
                        LOGGER.info(f"{file_path} Consolidated {chunks} chunks")
                        dataframes.append(chunk_df)
                    except Exception as e:
                        LOGGER.error(f"Error reading CSV file {file_path}", exc_info=True)

                for csv_file in dataset_file_objects:
                    file_path = os.path.join(settings.DATASET_FILES_URL, csv_file)
                    thread = threading.Thread(target=read_csv_file, args=(file_path,))
                    thread_list.append(thread)
                    thread.start()

                # Wait for all threads to complete
                for thread in thread_list:
                    thread.join()
            combined_df = pd.concat(dataframes, ignore_index=True)
            combined_df.to_csv(os.path.join(settings.DATASET_FILES_URL, consolidated_file), index=False)
            LOGGER.info(f"{consolidated_file} file created")
            return consolidated_file
        except Exception as e:
            LOGGER.error(f"Error occoured while creating {consolidated_file}", exc_info=True)
            return Response(
                "Requested resource is currently unavailable. Please try again later.",
                status=500,
            )


class DatasetFileV2View(GenericViewSet):
    queryset = DatasetV2File.objects.all()
    serializer_class = DatasetFileV2NewSerializer

    def create(self, request, *args, **kwargs):
        validity = check_file_name_length(incoming_file_name=request.data.get("file"),
                                          accepted_file_name_size=NumericalConstants.FILE_NAME_LENGTH)
        if not validity:
            return Response(
                {"message": f"File name should not be more than {NumericalConstants.FILE_NAME_LENGTH} characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            data = serializer.data
            instance = DatasetV2File.objects.get(id=data.get("id"))
            instance.standardised_file = instance.file  # type: ignore
            instance.file_size = os.path.getsize(os.path.join(settings.DATASET_FILES_URL, str(instance.file)))
            instance.save()
            LOGGER.info("Dataset created Successfully.")
            data = DatasetFileV2NewSerializer(instance)
            return Response(data.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @authenticate_user(model=DatasetV2File)
    def update(self, request, *args, **kwargs):
        # setattr(request.data, "_mutable", True)
        try:
            data = request.data
            instance = self.get_object()
            # Generate the file and write the path to standardised file.
            standardised_configuration = request.data.get("standardised_configuration")
            # mask_columns = request.data.get(
            #     "mask_columns",
            # )
            config = request.data.get("config")
            file_path = str(instance.file)
            if standardised_configuration:
                if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                    df = pd.read_excel(os.path.join(settings.DATASET_FILES_URL, file_path), index_col=None)
                else:
                    df = pd.read_csv(os.path.join(settings.DATASET_FILES_URL, file_path), index_col=False)

                df.rename(columns=standardised_configuration, inplace=True)
                df.columns = df.columns.astype(str)
                df = df.drop(df.filter(regex="Unnamed").columns, axis=1)

                if not os.path.exists(os.path.join(settings.DATASET_FILES_URL, instance.dataset.name, instance.source)):
                    os.makedirs(os.path.join(settings.DATASET_FILES_URL, instance.dataset.name, instance.source))

                file_name = os.path.basename(file_path).replace(".", "_standerdise.")
                if file_path.endswith(".csv"):
                    df.to_csv(
                        os.path.join(
                            settings.DATASET_FILES_URL,
                            instance.dataset.name,
                            instance.source,
                            file_name,
                        )
                    )  # type: ignore
                else:
                    df.to_excel(
                        os.path.join(
                            settings.DATASET_FILES_URL,
                            instance.dataset.name,
                            instance.source,
                            file_name,
                        )
                    )  # type: ignore
                # data = request.data
                standardised_file_path = os.path.join(instance.dataset.name, instance.source, file_name)
                data["file_size"] = os.path.getsize(
                    os.path.join(settings.DATASET_FILES_URL, str(standardised_file_path)))
            else:
                file_name = os.path.basename(file_path)
                standardised_file_path = os.path.join(instance.dataset.name, instance.source, file_name)
                # data["file_size"] = os.path.getsize(os.path.join(settings.DATASET_FILES_URL, str(standardised_file_path)))
            data["standardised_configuration"] = config
            serializer = self.get_serializer(instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            DatasetV2File.objects.filter(id=serializer.data.get("id")).update(standardised_file=standardised_file_path)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        data = DatasetV2File.objects.filter(dataset=request.GET.get("dataset")).values("id", "file")
        return Response(data, status=status.HTTP_200_OK)

    @authenticate_user(model=DatasetV2File)
    def destroy(self, request, *args, **kwargs):
        try:
            dataset_file = self.get_object()
            dataset_file.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)

    # @action(detail=False, methods=["put"])
    @authenticate_user(model=DatasetV2File)
    def patch(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)


class UsagePolicyListCreateView(generics.ListCreateAPIView):
    queryset = UsagePolicy.objects.all()
    serializer_class = UsagePolicySerializer


class UsagePolicyRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UsagePolicy.objects.all()
    serializer_class = UsageUpdatePolicySerializer
    api_builder_serializer_class = APIBuilderSerializer

    @authenticate_user(model=UsagePolicy)
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        approval_status = request.data.get('approval_status')
        policy_type = request.data.get('type', None)
        instance.api_key = None
        try:
            if policy_type == 'api':
                if approval_status == 'approved':
                    instance.api_key = generate_api_key()
            serializer = self.api_builder_serializer_class(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=200)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatahubNewDashboard(GenericViewSet):
    """Datahub Dashboard viewset"""

    pagination_class = CustomPagination

    def participant_metics(self, data):
        on_boarded_by = data.get("onboarded_by")
        role_id = data.get("role_id")
        user_id = data.get("user_id")
        result = {}
        try:
            if on_boarded_by != "None" or role_id == str(6):
                result["participants_count"] = (
                    UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                    .filter(
                        user__status=True,
                        user__on_boarded_by=on_boarded_by if on_boarded_by != "None" else user_id,
                        user__role=3,
                        user__approval_status=True,
                    )
                    .count()
                )
            elif role_id == str(1):
                result["co_steward_count"] = (
                    UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                    .filter(user__status=True, user__role=6)
                    .count()
                )
                result["participants_count"] = (
                    UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                    .filter(
                        user__status=True,
                        user__role=3,
                        user__on_boarded_by=None,
                        user__approval_status=True,
                    )
                    .count()
                )
            else:
                result["participants_count"] = (
                    UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                    .filter(
                        user__status=True,
                        user__role=3,
                        user__on_boarded_by=None,
                        user__approval_status=True,
                    )
                    .count()
                )
            LOGGER.info("Participants Metrics completed")
            return result
        except Exception as error:  # type: ignore
            LOGGER.error(
                "Error while filtering the participants. ERROR: %s",
                error,
                exc_info=True,
            )
            raise Exception(str(error))

    def dataset_metrics(self, data, request):
        on_boarded_by = data.get("onboarded_by")
        role_id = data.get("role_id")
        user_id = data.get("user_id")
        user_org_map = data.get("map_id")
        try:
            query = (
                DatasetV2.objects.prefetch_related("datasets")
                .select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .exclude(is_temp=True)
            )
            if on_boarded_by != "None" or role_id == str(6):
                query = query.filter(
                    Q(user_map__user__on_boarded_by=on_boarded_by if on_boarded_by != "None" else user_id)
                    | Q(user_map__user_id=on_boarded_by if on_boarded_by != "None" else user_id)
                )
            else:
                query = query.filter(user_map__user__on_boarded_by=None).exclude(user_map__user__role_id=6)
            LOGGER.info("Datasets Metrics completed")
            return query
        except Exception as error:  # type: ignore
            LOGGER.error("Error while filtering the datasets. ERROR: %s", error, exc_info=True)
            raise Exception(str(error))

    def connector_metrics(self, data, dataset_query, request):
        # on_boarded_by = data.get("onboarded_by")
        # role_id = data.get("role_id")
        user_id = data.get("user_id")
        user_org_map = data.get("map_id")
        my_dataset_used_in_connectors = (
                dataset_query.prefetch_related("datasets__right_dataset_file")
                .values("datasets__right_dataset_file")
                .filter(datasets__right_dataset_file__connectors__user_id=user_id)
                .distinct()
                .count()
                + dataset_query.prefetch_related("datasets__left_dataset_file")
                .values("datasets__left_dataset_file")
                .filter(datasets__left_dataset_file__connectors__user_id=user_id)
                .distinct()
                .count()
        )
        connectors_query = Connectors.objects.filter(user_id=user_id).all()

        other_datasets_used_in_my_connectors = (
                                                   dataset_query.prefetch_related("datasets__right_dataset_file")
                                                   .select_related("datasets__right_dataset_file__connectors")
                                                   .filter(datasets__right_dataset_file__connectors__user_id=user_id)
                                                   .values("datasets__right_dataset_file")
                                                   .exclude(user_map_id=user_org_map)
                                                   .distinct()
                                                   .count()
                                               ) + (
                                                   dataset_query.prefetch_related("datasets__left_dataset_file")
                                                   .select_related("datasets__left_dataset_file__connectors")
                                                   .filter(datasets__left_dataset_file__connectors__user_id=user_id)
                                                   .values("datasets__left_dataset_file")
                                                   .exclude(user_map_id=user_org_map)
                                                   .distinct()
                                                   .count()
                                               )
        return {
            "total_connectors_count": connectors_query.count(),
            "other_datasets_used_in_my_connectors": other_datasets_used_in_my_connectors,
            "my_dataset_used_in_connectors": my_dataset_used_in_connectors,
            "recent_connectors": ConnectorsListSerializer(
                connectors_query.order_by("-updated_at")[0:3], many=True
            ).data,
        }

    @action(detail=False, methods=["get"])
    @http_request_mutation
    def dashboard(self, request):
        """Retrieve datahub dashboard details"""
        data = request.META
        try:
            participant_metrics = self.participant_metics(data)
            dataset_query = self.dataset_metrics(data, request)
            # This will fetch connectors metrics
            connector_metrics = self.connector_metrics(data, dataset_query, request)
            if request.GET.get("my_org", False):
                dataset_query = dataset_query.filter(user_map_id=data.get("map_id"))
            dataset_file_metrics = (
                dataset_query.values("datasets__source")
                .annotate(
                    dataset_count=Count("id", distinct=True),
                    file_count=Count("datasets__file", distinct=True),
                    total_size=Sum("datasets__file_size"),
                )
                .filter(file_count__gt=0)
            )

            dataset_state_metrics = dataset_query.values(state_name=F("geography__state__name")).annotate(
                dataset_count=Count("id", distinct=True)
            )
            distinct_keys = (
                DatasetV2.objects.annotate(
                    key=Func(
                        "category",
                        function="JSONB_OBJECT_KEYS",
                        output_field=CharField(),
                    )
                )
                .values_list("key", flat=True)
                .distinct()
            )

            # Iterate over the distinct keys and find the count for each key
            dataset_category_metrics = {}
            for key in distinct_keys:
                dataset_count = dataset_query.filter(category__has_key=key).count()
                if dataset_count:
                    dataset_category_metrics[key] = dataset_count
            recent_datasets = DatasetV2ListNewSerializer(dataset_query.order_by("-updated_at")[0:3], many=True).data
            data = {
                "user": UserOrganizationMap.objects.select_related("user", "organization")
                .filter(id=data.get("map_id"))
                .values(
                    first_name=F("user__first_name"),
                    last_name=F("user__last_name"),
                    logo=Concat(
                        Value("media/"),
                        F("organization__logo"),
                        output_field=CharField(),
                    ),
                    org_email=F("organization__org_email"),
                    name=F("organization__name"),
                )
                .first(),
                "total_participants": participant_metrics,
                "dataset_file_metrics": dataset_file_metrics,
                "dataset_state_metrics": dataset_state_metrics,
                "total_dataset_count": dataset_query.count(),
                "dataset_category_metrics": dataset_category_metrics,
                "recent_datasets": recent_datasets,
                **connector_metrics,
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @http_request_mutation
class ResourceManagementViewSet(GenericViewSet):
    """
    Resource Management viewset.
    """

    queryset = Resource.objects.prefetch_related().all()
    serializer_class = ResourceSerializer
    pagination_class = CustomPagination

    @http_request_mutation
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            user_map = request.META.get("map_id")
            # request.data._mutable = True
            data = request.data.copy()
            files = request.FILES.getlist('files')  # 'files' is the key used in FormData
            data["files"] = files
            data["user_map"] = user_map

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = request.data.copy()
            sub_categories_map = data.pop("sub_categories_map")
            serializer = self.get_serializer(instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            resource_id = serializer.data.get("id")
            ResourceSubCategoryMap.objects.filter(resource=instance).delete()

            sub_categories_map = json.loads(sub_categories_map[0]) if sub_categories_map else []
            resource_sub_cat_instances = [
                ResourceSubCategoryMap(resource=instance, sub_category=SubCategory.objects.get(id=sub_cat)
                                       ) for sub_cat in sub_categories_map]
            ResourceSubCategoryMap.objects.bulk_create(resource_sub_cat_instances)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @http_request_mutation
    def list(self, request, *args, **kwargs):
        try:
            user_map = request.META.get("map_id")
            if request.GET.get("others", None):
                queryset = Resource.objects.exclude(user_map=user_map).order_by("-updated_at")
            else:
                queryset = Resource.objects.filter(user_map=user_map).order_by("-updated_at")

            page = self.paginate_queryset(queryset)
            serializer = ResourceListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        resource = self.get_object()
        resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @http_request_mutation
    def retrieve(self, request, *args, **kwargs):
        user_map = request.META.get("map_id")
        resource = self.get_object()
        serializer = self.get_serializer(resource)
        data = serializer.data.copy()
        try:
            if str(resource.user_map_id) == str(user_map):
                resource_usage_policy = (
                    ResourceUsagePolicy.objects.select_related(
                        "resource",
                    )
                    .filter(resource=resource)
                    .values(
                        "id",
                        "approval_status",
                        "accessibility_time",
                        "updated_at",
                        "type",
                        "api_key",
                        "created_at",
                        "resource_id",
                        resource_title=F("resource__title"),
                        organization_name=F("user_organization_map__organization__name"),
                        organization_email=F("user_organization_map__organization__org_email"),
                        organization_phone_number=F("user_organization_map__organization__phone_number"),
                    )
                    .order_by("-updated_at")
                )
                # data["retrival"] = MessagesChunksRetriveSerializer(Messages.objects.filter(resource_id=resource.id).order_by("-created_at").all(), many=True).data
            else:
                resource_usage_policy = (
                    ResourceUsagePolicy.objects.select_related(
                        "resource"
                    )
                    .filter(user_organization_map_id=user_map, resource=resource)
                    .values(
                        "id",
                        "approval_status",
                        "updated_at",
                        "accessibility_time",
                        "type",
                        "resource_id",
                        "api_key",
                        organization_name=F("user_organization_map__organization__name"),
                        organization_email=F("user_organization_map__organization__org_email"),
                        organization_phone_number=F("user_organization_map__organization__phone_number"),
                    )
                    .order_by("-updated_at")
                )
            data["resource_usage_policy"] = resource_usage_policy
            print(data.get(resource_usage_policy))
            return Response(data, status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error("Issue while Retrive Resource details", exc_info=True)
            return Response(
                f"Issue while Retrive Retrive Resource details {error}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @http_request_mutation
    @action(detail=False, methods=["post"])
    def resources_filter(self, request, *args, **kwargs):
        try:
            data = request.data
            user_map = request.META.get("map_id")
            categories = data.pop(Constants.CATEGORY, None)
            others = data.pop(Constants.OTHERS, "")
            filters = {key: value for key, value in data.items() if value}
            query_set = self.get_queryset().filter(**filters).order_by("-updated_at")
            if categories:
                query_set = query_set.filter(
                    reduce(
                        operator.or_,
                        (Q(category__contains=cat) for cat in categories),
                    )
                )
            query_set = query_set.exclude(user_map=user_map) if others else query_set.filter(
                user_map=user_map)

            page = self.paginate_queryset(query_set)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def requested_resources(self, request, *args, **kwargs):
        try:
            user_map_id = request.data.get("user_map")
            # policy_type = request.data.get("type", None)
            # resource_id = request.data.get("resource")
            requested_recieved = (
                ResourceUsagePolicy.objects.select_related(
                    "resource",
                )
                .filter(resource__user_map_id=user_map_id)
                .values(
                    "id",
                    "approval_status",
                    "accessibility_time",
                    "updated_at",
                    "type",
                    "created_at",
                    "resource_id",
                    resource_title=F("resource__title"),
                    organization_name=F("user_organization_map__organization__name"),
                    organization_email=F("user_organization_map__organization__org_email"),
                    organization_phone_number=F("user_organization_map__organization__phone_number"),
                )
                .order_by("-updated_at")
            )

            requested_sent = (
                ResourceUsagePolicy.objects.select_related(
                    "resource"
                )
                .filter(user_organization_map_id=user_map_id)
                .values(
                    "id",
                    "approval_status",
                    "updated_at",
                    "accessibility_time",
                    "type",
                    "resource_id",
                    resource_title=F("resource__title"),
                    organization_name=F("resource__user_map__organization__name"),
                    organization_email=F("resource__user_map__organization__org_email"),
                )
                .order_by("-updated_at")
            )

            return Response(
                {
                    "sent": requested_sent,
                    "recieved": requested_recieved,
                },
                200,
            )
        except Exception as error:
            LOGGER.error("Issue while Retrive Resource requeted data", exc_info=True)
            return Response(
                f"Issue while Retrive Resource requeted data {error}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResourceFileManagementViewSet(GenericViewSet):
    """
    Resource File Management
    """

    queryset = ResourceFile.objects.all()
    serializer_class = ResourceFileSerializer

    @http_request_mutation
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            resource = data.get("resource")
            if data.get("type") == "youtube":
                youtube_urls_response = get_youtube_url(data.get("url"))
                if youtube_urls_response.status_code == 400:
                    return youtube_urls_response
                youtube_urls = youtube_urls_response.data
                playlist_urls = [{"resource": resource, "type": "youtube", **row} for row in youtube_urls]
                for row in playlist_urls:
                    serializer = self.get_serializer(data=row)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    LOGGER.info(f"Embeding creation started for youtube url: {row.get('url')}")
                    VectorDBBuilder.create_vector_db.delay(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                serializer = self.get_serializer(data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                VectorDBBuilder.create_vector_db.delay(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        resourcefile_id = instance.id
        collections_to_delete = LangchainPgCollection.objects.filter(name=resourcefile_id)
        collections_to_delete.delete()
        instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def resource_live_api_export(self, request):
        """This is an API to fetch the data from an External API with an auth token
        and store it in JSON format."""
        try:
            url = request.data.get("url")
            auth_type = request.data.get("auth_type")
            title = request.data.get("title")
            source = request.data.get("source")
            file_name = request.data.get("file_name")
            resource = request.data.get("resource")
            if auth_type == 'NO_AUTH':
                response = requests.get(url)
            elif auth_type == 'API_KEY':
                headers = {request.data.get(
                    "api_key_name"): request.data.get("api_key_value")}
                response = requests.get(url, headers=headers)
            elif auth_type == 'BEARER':
                headers = {"Authorization": "Bearer " +
                                            request.data.get("token")}
                response = requests.get(url, headers=headers)

            # response = requests.get(url)
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except ValueError:
                    data = response.text
                file_path = settings.RESOURCES_URL + f"file {str(uuid.uuid4())}.json"
                format = "w" if os.path.exists(file_path) else "x"
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, format) as outfile:
                    if type(data) == list:
                        json.dump(data, outfile)
                    else:
                        outfile.write(json.dumps(data))
                if resource:
                    with open(file_path, "rb") as outfile:  # Open the file in binary read mode
                        # Wrap the file content using Django's ContentFile
                        django_file = ContentFile(outfile.read(),
                                                  name=f"{file_name}.json")  # You can give it any name you prefer

                        # Prepare data for serializer
                        serializer_data = {"resource": resource, "type": "api", "file": django_file}

                        # Initialize and validate serializer
                        serializer = ResourceFileSerializer(data=serializer_data)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()
                        VectorDBBuilder.create_vector_db.delay(serializer.data)
                        return JsonResponse(serializer.data, status=status.HTTP_200_OK)
                return Response(file_path)
            LOGGER.error("Failed to fetch data from api")
            return Response({"message": f"API Response: {response.json()}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(
                f"Failed to fetch data from api ERROR: {e} and input fields: {request.data}")
            return Response({"message": f"API Response: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def fetch_videos(self, request):
        url = request.GET.get("url")
        return get_youtube_url(url)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        team_member = self.get_object()
        serializer = self.get_serializer(team_member)
        # serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


#
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.prefetch_related("subcategory_category").all()
    serializer_class = CategorySerializer

    @action(detail=False, methods=["get"])
    def categories_and_sub_categories(self, request):
        categories_with_subcategories = {}
        # Retrieve all categories and their related subcategories
        categories = Category.objects.all()

        for category in categories:
            # Retrieve the names of all subcategories related to this category
            subcategory_names = [sub_category.name for sub_category in
                                 SubCategory.objects.filter(category=category).all()]
            # Assign the list of subcategory names to the category name in the dictionary
            categories_with_subcategories[category.name] = subcategory_names

        return Response(categories_with_subcategories, 200)


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = []

    @action(detail=False, methods=["post"])
    def dump_categories(self, request):
        data = request.data
        for category_name, sub_categories in data.items():
            category, created = Category.objects.get_or_create(name=category_name)
            print(category)
            for sub_category_name in sub_categories:
                SubCategory.objects.get_or_create(category=category, name=sub_category_name)
        return Response("Data dumped")

    @action(detail=False, methods=["get"])
    @transaction.atomic
    def dump_resource_categories_map(self, request):
        # Parse the category JSON field
        resources = Resource.objects.all()
        for resource in resources:
            categories = resource.category
            for category_name, sub_category_names in categories.items():
                category = Category.objects.filter(name=category_name).first()
                for sub_category_name in sub_category_names:
                    # Find the corresponding SubCategory instance
                    try:
                        sub_category = SubCategory.objects.filter(name=sub_category_name, category=category).first()
                        print(sub_category)
                        print(resource)
                        if sub_category:
                            ResourceSubCategoryMap.objects.get_or_create(
                                sub_category=sub_category,
                                resource=resource
                            )
                    except SubCategory.DoesNotExist:
                        print(f"SubCategory '{sub_category_name}' does not exist.")
        return Response("Data dumped")

    @action(detail=False, methods=["get"])
    @transaction.atomic
    def dump_dataset_map(self, request):
        # Parse the category JSON field
        resources = DatasetV2.objects.all()
        for resource in resources:
            categories = resource.category
            for category_name, sub_category_names in categories.items():
                category = Category.objects.filter(name=category_name).first()
                for sub_category_name in sub_category_names:
                    # Find the corresponding SubCategory instance
                    try:
                        sub_category = SubCategory.objects.filter(name=sub_category_name, category=category).first()
                        if sub_category:
                            DatasetSubCategoryMap.objects.get_or_create(
                                sub_category=sub_category,
                                dataset=resource
                            )
                    except SubCategory.DoesNotExist:
                        print(f"SubCategory '{sub_category_name}' does not exist.")
        return Response("Data dumped")


class EmbeddingsViewSet(viewsets.ModelViewSet):
    queryset = LangchainPgEmbedding.objects.all()
    serializer_class = LangChainEmbeddingsSerializer
    lookup_field = 'uuid'  # Specify the UUID field as the lookup field

    @action(detail=False, methods=['get'])
    def embeddings_and_chunks(self, request):
        embeddings = []
        collection_id = request.GET.get("resource_file")
        collection = LangchainPgCollection.objects.filter(name=str(collection_id)).first()
        if collection:
            embeddings = LangchainPgEmbedding.objects.filter(collection_id=collection.uuid).values("document")
        return Response(embeddings)

    @action(detail=False, methods=['post'])
    def get_embeddings(self, request):
        # Use the 'uuid' field to look up the instance
        # instance = self.get_object()
        uuid = request.data.get("uuid")
        data = LangchainPgEmbedding.objects.filter(uuid=uuid).values("embedding", "document")
        # print(data)
        # import pdb; pdb.set_trace()
        # serializer = self.get_serializer(data)
        return Response(data)

    @http_request_mutation
    @action(detail=False, methods=['post'])
    def chat_api(self, request):
        map_id = request.META.get("map_id")
        user_id = request.META.get("user_id")
        data = request.data
        query = request.data.get("query")
        resource_id = request.data.get("resource")
        try:
            user_name = User.objects.get(id=user_id).first_name
            history = Messages.objects.filter(user_map=map_id).order_by("-created_at")
            history = history.filter(resource_id=resource_id).first() if resource_id else history.first()

            # print(chat_history)
            # chat_history = history.condensed_question if history else ""
            summary, chunks, condensed_question, prompt_usage = VectorDBBuilder.get_input_embeddings(query, user_name,
                                                                                                     resource_id,
                                                                                                     history)
            data = {"user_map": UserOrganizationMap.objects.get(id=map_id).id, "resource": resource_id, "query": query,
                    "query_response": summary, "condensed_question": condensed_question, "prompt_usage": prompt_usage}
            messages_serializer = MessagesSerializer(data=data)
            messages_serializer.is_valid(raise_exception=True)
            message_instance = messages_serializer.save()  # This returns the Messages model instance
            data = messages_serializer.data
            if chunks:
                message_instance.retrieved_chunks.set(chunks.values_list("uuid", flat=True))
            return Response(data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(f"Error During the execution: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @http_request_mutation
    @action(detail=False, methods=['post'])
    def chat_histroy(self, request):
        try:
            map_id = request.META.get("map_id")
            resource_id = request.data.get("resource")
            history = Messages.objects.filter(user_map=map_id, bot_type="vistaar").order_by("created_at")
            if resource_id:
                history = history.filter(resource_id=resource_id).all()
            else:
                history = history.filter(resource_id__isnull=True).all()
            total = len(history)
            slice = 0 if total <= 10 else total - 10
            history = history[slice:total]
            messages_serializer = MessagesRetriveSerializer(history, many=True)
            return Response(messages_serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def dump_embeddings(self, request):
        # queryset = ResourceFile.objects.all()
        from django.db import models
        from django.db.models.functions import Cast

        queryset = ResourceFile.objects.exclude(
            id__in=Subquery(
                LangchainPgCollection.objects.annotate(
                    uuid_name=Cast('name', models.UUIDField())
                ).values('uuid_name')
            )
        ).all()
        serializer = ResourceFileSerializer(queryset, many=True)
        data = serializer.data
        total_files = len(data)
        count = 0
        for row in data:
            count += 1
            VectorDBBuilder.create_vector_db(row)
            print(f"resource {row} is completed")
            print(f"{count} completed out of {total_files}")
        return Response("embeddings created for all the files")


class ResourceUsagePolicyListCreateView(generics.ListCreateAPIView):
    queryset = ResourceUsagePolicy.objects.all()
    serializer_class = ResourceUsagePolicySerializer


class ResourceUsagePolicyRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ResourceUsagePolicy.objects.all()
    serializer_class = ResourceUsagePolicySerializer
    api_builder_serializer_class = ResourceAPIBuilderSerializer

    @authenticate_user(model=ResourceUsagePolicy)
    def patch(self, request, *args, **kwargs):
        # import pdb;pdb.set_trace()
        instance = self.get_object()
        approval_status = request.data.get('approval_status')
        policy_type = request.data.get('type', None)
        instance.api_key = None
        try:
            if approval_status == 'approved':
                instance.api_key = generate_api_key()
            serializer = self.api_builder_serializer_class(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=200)

        except ValidationError as e:
            LOGGER.error(e, exc_info=True)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessagesViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset = Messages.objects.all()
    serializer_class = MessagesSerializer

    def delete(self, request, *args, **kwargs):
        return Response("You don't have access to delete the chat history", status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = MessagesRetriveSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)


class MessagesCreateViewSet(generics.ListCreateAPIView):
    queryset = Messages.objects.all()
    serializer_class = MessagesSerializer
    pagination_class = CustomPagination

    @http_request_mutation
    def list(self, request, *args, **kwargs):
        resource_id = request.GET.get("resource")
        user_map = request.META.get("map_id")
        if resource_id:
            queryset = Messages.objects.filter(resource_id=resource_id).order_by("-created_at").all()
        else:
            queryset = Messages.objects.filter(user_map=user_map).order_by("-created_at").all()
        page = self.paginate_queryset(queryset)
        serializer = MessagesChunksRetriveSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
