import json
import logging
import operator
import os
from functools import reduce
from django.db.models import Q
from django.shortcuts import render
from jsonschema import ValidationError
from rest_framework import generics, pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from accounts.models import User, UserRole
from core.constants import Constants, NumericalConstants
from core.utils import (
    CustomPagination,
    Utils,
    csv_and_xlsx_file_validatation,
    read_contents_from_csv_or_xlsx_file,
)
from datasets.models import (
    Datasets,
    UserOrganizationMap,
)
from datasets.serializers import (
    DatasetSerializer,
    DatasetUpdateSerializer,
    DatahubDatasetsSerializer,
)

from utils import custom_exceptions, file_operations, string_functions, validators
from utils.jwt_services import http_request_mutation
LOGGER = logging.getLogger(__name__)
con = None


# Create your views here.
class DatasetsViewSetV2(GenericViewSet):
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