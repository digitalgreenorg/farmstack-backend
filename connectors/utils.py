# common utility functions comes here
import json
from contextlib import closing
import mysql.connector
import os
import psycopg2
from django.http import HttpResponse, JsonResponse
from rest_framework import pagination, serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from core import settings
from core.constants import Constants, NumericalConstants
import logging
import datetime
from rest_framework.exceptions import ValidationError

from datahub.models import DatasetV2File
from datahub.serializers import DatasetFileV2NewSerializer

LOGGER = logging.getLogger(__name__)


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


def create_dataset_v2_for_data_import(
        dataset, source, dataset_name, file_name
):
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
    return serializer
