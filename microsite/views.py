import datetime
import json
import logging
import math
import operator
import os
from functools import reduce

import pandas as pd
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, render
from python_http_client import exceptions
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.viewsets import GenericViewSet

from accounts.models import User, UserRole
from accounts.serializers import UserCreateSerializer
from connectors.models import Connectors
from core.constants import Constants
from core.utils import (
    CustomPagination,
    DefaultPagination,
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
    Policy,
    Resource,
    UsagePolicy,
    UserOrganizationMap,
)
from datahub.serializers import (
    DatahubDatasetsV2Serializer,
    DatasetV2Serializer,
    OrganizationSerializer,
    ParticipantSerializer,
    ResourceSerializer,
    micrositeOrganizationSerializer,
)
from microsite.serializers import (
    ConnectorsListSerializer,
    ConnectorsRetriveSerializer,
    ContactFormSerializer,
    DatahubDatasetFileDashboardFilterSerializer,
    DatasetsMicrositeSerializer,
    LegalDocumentSerializer,
    OrganizationMicrositeSerializer,
    PolicySerializer,
    UserDataMicrositeSerializer,
    UserSerializer,
)
from utils import custom_exceptions, file_operations
from utils.file_operations import (
    check_file_name_length,
    filter_dataframe_for_dashboard_counties,
)
from utils.jwt_services import http_request_mutation

LOGGER = logging.getLogger(__name__)


class OrganizationMicrositeViewSet(GenericViewSet):
    """Organization viewset for microsite"""

    permission_classes = []

    @action(detail=False, methods=["get"])
    def admin_organization(self, request):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        try:
            datahub_admin = User.objects.filter(role_id=1)

            if not datahub_admin:
                data = {Constants.USER: None, "message": ["Datahub admin not Found."]}
                return Response(data, status=status.HTTP_200_OK)

            user_queryset = datahub_admin.first()
            user_serializer = UserSerializer(user_queryset)
            user_org_queryset = UserOrganizationMap.objects.prefetch_related(
                Constants.USER, Constants.ORGANIZATION
            ).filter(user=user_queryset.id)

            if not user_org_queryset:
                data = {
                    Constants.USER: user_serializer.data,
                    Constants.ORGANIZATION: None,
                    "message": ["Datahub admin is not associated with any organization."],
                }
                return Response(data, status=status.HTTP_200_OK)

            org_obj = Organization.objects.get(id=user_org_queryset.first().organization_id)
            org_seriliazer = OrganizationMicrositeSerializer(org_obj)
            data = {
                Constants.USER: user_serializer.data,
                Constants.ORGANIZATION: org_seriliazer.data,
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatahubThemeMicrositeViewSet(GenericViewSet):
    permission_classes = []

    @action(detail=False, methods=["get"])
    def theme(self, request):
        """retrieves Datahub Theme attributes"""
        file_paths = file_operations.file_path(settings.THEME_URL)
        css_path = settings.CSS_ROOT + settings.CSS_FILE_NAME
        data = {}

        try:
            css_attribute = file_operations.get_css_attributes(css_path, "background-color")

            if not css_path and not file_paths:
                data = {"hero_image": None, "css": None}
            elif not css_path:
                data = {"hero_image": file_paths, "css": None}
            elif css_path and not file_paths:
                data = {"hero_image": None, "css": {"btnBackground": css_attribute}}
            elif css_path and file_paths:
                data = {
                    "hero_image": file_paths,
                    "css": {"btnBackground": css_attribute},
                }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            LOGGER.error(e)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class DatasetsMicrositeViewSet(GenericViewSet):
    """Datasets viewset for microsite"""

    serializer_class = DatasetV2Serializer
    queryset = DatasetV2.objects.all()
    pagination_class = CustomPagination
    permission_classes = [permissions.AllowAny]

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
        try:
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            return Response([], status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            path_ = os.path.join(settings.DATASET_FILES_URL, str(file.standardised_file))
            file_path = {}
            file_path["content"] = read_contents_from_csv_or_xlsx_file(path_)
            # Omitted the actual name of the file so the user can't manually download the file
            # Added file name : As they need to show the file name in frontend.
            file_path["id"] = file.id
            file_path["file"] = path_.split("/")[-1]
            file_path["source"] = file.source
            file_path["file_size"] = file.file_size
            file_path["accessibility"] = file.accessibility
            file_path["standardised_file"] = (
                os.path.join(settings.DATASET_FILES_URL, str(file.standardised_file))
                if file.accessibility == Constants.PUBLIC
                else None
            )
            data.append(file_path)

        serializer["datasets"] = data
        return Response(serializer, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["get"])
    def get_json_response(self, request, *args, **kwargs):
        try:
            next = False
            file_path = request.GET.get('file_path')
            page = int(request.GET.get('page', 1))
            start_index = 0  + 50*(page-1)  # Adjust the start index as needed
            end_index = 50*page
            if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                df_headers = pd.read_excel(file_path, nrows=1, header=None)
                df = pd.read_excel(file_path, index_col=None, skiprows=range(0, start_index), nrows=end_index - start_index+1)
            else:
                df_headers = pd.read_csv(file_path, nrows=1, header=None)
                df = pd.read_csv(file_path, index_col=False, skiprows=range(0, start_index), nrows=end_index - start_index+1)       
            if df.empty  :
                raise pd.errors.EmptyDataError("The file is empty or Reached end of file.")     
            for i, value in enumerate(df_headers.iloc[0]):
                df_headers[i] = str(value)
            df.columns = df_headers.iloc[0]
            df=df.fillna("")
            next, df = (True, df[0:-1]) if len(df) > 50 else (False,df)
            column = {
            "ellipsis": True,
            "width": 200
            }
            return JsonResponse({
            'columns': [{**column,"title": col.replace("_", " ").strip(), "dataIndex": col } for col in df.columns.to_list()],
            'next': next,
            'current_page': page,
            'data': df.to_dict(orient='records')
            }, safe=False,status=200)       
        except pd.errors.EmptyDataError:
            logging.info("The file is empty or Reached end of file.")
            return Response(str("Table is Empty or Reached End of the table"), status=400)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=False, methods=["post"])
    def dataset_filters(self, request, *args, **kwargs):
        """This function get the filter args in body. based on the filter args orm filters the data."""
        data = request.data
        org_id = data.pop(Constants.ORG_ID, "")
        others = data.pop(Constants.OTHERS, "")
        categories = data.pop(Constants.CATEGORY, None)
        user_id = data.pop(Constants.USER_ID, "")
        exclude, filters = {}, {}
        if others:
            exclude = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        else:
            filters = {Constants.USER_MAP_ORGANIZATION: org_id} if org_id else {}
        try:
            if categories is not None:
                data = (
                    DatasetV2.objects.select_related(
                        Constants.USER_MAP,
                        Constants.USER_MAP_USER,
                        Constants.USER_MAP_ORGANIZATION,
                    )
                    .filter(is_temp=False, **data, **filters)
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
                    DatasetV2.objects.select_related(
                        Constants.USER_MAP,
                        Constants.USER_MAP_USER,
                        Constants.USER_MAP_ORGANIZATION,
                    )
                    .filter(is_temp=False, **data, **filters)
                    .exclude(**exclude)
                    .order_by(Constants.UPDATED_AT)
                    .reverse()
                    .all()
                )
        except Exception as error:  # type: ignore
            logging.error("Error while filtering the datasets. ERROR: %s", error)
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)

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
            return Response(f"Invalid filter fields: {list(request.data.keys())}", status=500)
        return Response({"geography": geography, "category_detail": category_detail}, status=200)

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

    @action(detail=False, methods=["post"])
    def search_datasets(self, request, *args, **kwargs):
        data = request.data
        search_pattern = data.pop(Constants.SEARCH_PATTERNS, "")
        filters = {Constants.NAME_ICONTAINS: search_pattern} if search_pattern else {}
        try:
            data = (
                DatasetV2.objects.select_related(
                    Constants.USER_MAP,
                    Constants.USER_MAP_USER,
                    Constants.USER_MAP_ORGANIZATION,
                )
                .filter(user_map__user__status=True, is_temp=False, **filters)
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

    @action(detail=True, methods=["post"],throttle_classes=[AnonRateThrottle])
    def get_dashboard_chart_data(self, request, pk, *args, **kwargs):
        try:

            if str(pk) != "c6552c05-0ada-4522-b584-71e26286a2e3":
                return Response(
                    "Requested resource is currently unavailable. Please try again later.",
                    status=status.HTTP_200_OK,
                )

            serializer = DatahubDatasetFileDashboardFilterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            counties = []
            sub_counties = []
            gender = []
            value_chain = []

            if serializer.data.get("county"):
                counties = serializer.data.get("county")

            if serializer.data.get("sub_county"):
                sub_counties = serializer.data.get("sub_county")

            if serializer.data.get("gender"):
                gender = serializer.data.get("gender")

            if serializer.data.get("value_chain"):
                value_chain = serializer.data.get("value_chain")

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

            dataset_file_object = DatasetV2File.objects.get(id=pk)
            dataset_file = str(dataset_file_object.standardised_file)
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
                )

            except Exception as e:
                print(e)
                return Response(
                    f"Something went wrong, please try again. {e}",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                data,
                status=status.HTTP_200_OK,
            )

        except DatasetV2File.DoesNotExist:
            return Response(
                "No dataset file for the provided id.",
                status=status.HTTP_404_NOT_FOUND,
            )


class ContactFormViewSet(GenericViewSet):
    """Contact Form for guest users to mail queries or application to become participant on datahub"""

    serializer_class = ContactFormSerializer
    permission_classes = []

    def create(self, request):
        """POST method to create a query and mail it to the datahub admin"""
        datahub_admin = User.objects.filter(role_id=1).first()
        serializer = self.get_serializer(data=request.data)
        print(serializer)
        serializer.is_valid(raise_exception=True)
        try:
            date = datetime.datetime.now().strftime("%d-%m-%Y")
            data = serializer.data
            data.update({"date": date})
            print(data)

            # render email from query_email template
            email_render = render(request, "user_fills_in_contact_form.html", data)
            mail_body = email_render.content.decode("utf-8")
            Utils().send_email(
                to_email=[datahub_admin.email],
                content=mail_body,
                subject=serializer.data.get("subject", Constants.DATAHUB),
            )
            return Response(
                {"Message": "Your query is submitted! Thank you."},
                status=status.HTTP_200_OK,
            )

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentsMicrositeViewSet(GenericViewSet):
    """View for uploading all the datahub documents and content"""

    serializer_class = LegalDocumentSerializer
    queryset = DatahubDocuments.objects.all()
    permission_classes = []

    @action(detail=False, methods=["get"])
    def legal_documents(self, request):
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
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParticipantMicrositeViewSet(GenericViewSet):

    """View for uploading all the datahub documents and content"""

    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    pagination_class = CustomPagination
    permission_classes = []

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        on_boarded_by = request.GET.get("on_boarded_by", None)
        co_steward = request.GET.get("co_steward", False)
        approval_status = request.GET.get(Constants.APPROVAL_STATUS, True)
        name = request.GET.get(Constants.NAME, "")
        filter = {Constants.ORGANIZATION_NAME_ICONTAINS: name} if name else {}
        try:
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
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error.__context__), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        roles = (
            UserOrganizationMap.objects.prefetch_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=True, user=pk)
            .all()
        )
        participant_serializer = ParticipantSerializer(roles, many=True)
        try:
            if participant_serializer.data:
                return Response(participant_serializer.data[0], status=status.HTTP_200_OK)
            return Response([], status=status.HTTP_200_OK)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def organizations(self, request, *args, **kwargs):
        """GET method: query the list of Organization objects"""
        co_steward = request.GET.get("co_steward", False)
        try:
            if co_steward:
                roles = (
                    UserOrganizationMap.objects.select_related(Constants.ORGANIZATION)
                    .filter(user__status=True, user__role=6)
                    .all()
                )
            else:
                roles = (
                    UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
                    .filter((Q(user__role=3) | Q(user__role=1)), user__status=True)
                    .all()
                )
            page = self.paginate_queryset(roles)
            participant_serializer = micrositeOrganizationSerializer(page, many=True)
            return self.get_paginated_response(participant_serializer.data)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PolicyAPIView(GenericViewSet):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = []

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class APIResponseViewSet(GenericViewSet):
    permission_classes = []

    @action(detail=False, methods=["get"])
    def api(self, request, *args, **kwargs):
        try:
            get_api_key = request.META.get("HTTP_API_KEY", None)
            page = int(request.GET.get('page', 1))
            if get_api_key is None:
                return Response(
                {
                    "message" : "Invalid auth credentials provided."
                },
                status=status.HTTP_401_UNAUTHORIZED
            )          
            file_path_query_set=UsagePolicy.objects.select_related('dataset_file').filter(api_key=get_api_key).values('dataset_file__standardised_file')
            file_path = file_path_query_set[0]["dataset_file__standardised_file"]
            protected_file_path = os.path.join(settings.DATASET_FILES_URL, str(file_path))
            next=False
            start_index = 0  + 50*(page-1) 
            end_index = 50*page  
            if protected_file_path.endswith(".xlsx") or protected_file_path.endswith(".xls"):
                df_header = pd.read_excel(protected_file_path, nrows=1, header=None)                       
                df = pd.read_excel(protected_file_path, index_col=None,  header=0, skiprows=range(0, start_index), nrows=end_index - start_index+1)
            else:
                df_header = pd.read_csv(protected_file_path, nrows=1, header=None)
                df = pd.read_csv(protected_file_path, index_col=False, header=0, skiprows=range(0, start_index), nrows=end_index - start_index+1)
            if df.empty  :
                raise pd.errors.EmptyDataError("The file is empty or Reached end of file.")      
            for i, value in enumerate(df_header.iloc[0]):
                df_header[i] = str(value)
            df.columns = df_header.iloc[0]
            df=df.fillna("")
            next, df = (True, df[0:-1]) if len(df) > 50 else (False,df)   
            return JsonResponse(
            {
            'next': next,
            'current_page': page,
            'data': df.to_dict(orient='records')
            }, safe=False,status=200)       
        except pd.errors.EmptyDataError:
            logging.info("The file is empty or Reached end of file.")
            return Response(str("File is Empty or Reached End of the file"), status=400)
        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response(str(error), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserDataMicrositeViewSet(GenericViewSet):
    """UserData Microsite ViewSet for microsite"""

    permission_classes = []

    @action(detail=False, methods=["get"])
    def user_data(self, request):
        """GET method: retrieve an object of Organization using User ID of the User (IMPORTANT: Using USER ID instead of Organization ID)"""
        try:
            datahub_admin = User.objects.get(id=request.GET.get("user_id", ""))
            print(datahub_admin, "datahub_admin")

            serializer = UserDataMicrositeSerializer(datahub_admin)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @permissions.AllowAny
# class PolicyDetailAPIView(generics.RetrieveAPIView):
#     queryset = Policy.objects.all()
#     serializer_class = PolicySerializer


def microsite_media_view(request):
    file = get_object_or_404(DatasetV2File, id=request.GET.get("id"))
    file_path = ""
    try:
        if file.accessibility == Constants.PUBLIC:
            file_path = str(file.file)
            file_path = os.path.join(settings.DATASET_FILES_URL, file_path)
            if not os.path.exists(file_path):
                return HttpResponseNotFound("File not found", 404)
            response = FileResponse(open(file_path, "rb"))
        else:
            return HttpResponse(
                f"You don't have access to download this private file, Your request status is", status=403
            )

        return response
    except Exception as error:
        LOGGER.error(error, exc_info=True)
        return Response({str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConnectorMicrositeViewSet(GenericViewSet):
    """Viewset for Product model"""

    permission_classes = []
    queryset = Connectors.objects.all()
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        data = Connectors.objects.all().order_by(Constants.UPDATED_AT).reverse()
        page = self.paginate_queryset(data)
        connectors_data = ConnectorsListSerializer(page, many=True)
        return self.get_paginated_response(connectors_data.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        try:
            instance = self.get_object()
            serializer = ConnectorsRetriveSerializer(instance=instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            return Response(str(error), status=status.HTTP_400_BAD_REQUEST)


class ResourceMicrositeViewSet(GenericViewSet):
    permission_classes = []
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    pagination_class = CustomPagination

    # @http_request_mutation
    def list(self, request, *args, **kwargs):
        try:
            page = self.paginate_queryset(self.get_queryset().order_by("-updated_at"))
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LOGGER.error(e)
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        resource = self.get_object()
        serializer = self.get_serializer(resource)
        # serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
