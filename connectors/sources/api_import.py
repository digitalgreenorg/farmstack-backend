from connectors.utils import create_dataset_v2_for_data_import
from core import settings
from utils import file_operations as file_ops
import requests
import json

from django.http import JsonResponse
from rest_framework import status
import logging

from rest_framework.response import Response

LOGGER = logging.getLogger(__name__)


def import_using_api_endpoint(auth_type, request, url, dataset, source, file_name, dataset_name):
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

        LOGGER.error("Fetch OK")

        # result = os.listdir(file_path)
        serializer = create_dataset_v2_for_data_import(
            dataset=dataset, source=source, dataset_name=dataset_name,
            file_name=file_name
        )
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)

    else:
        LOGGER.error("Failed to fetch data from api")
        return Response({"message": f"API Response: {response.json()}"}, status=status.HTTP_400_BAD_REQUEST)
