import os
import json
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from api_builder.serializers import APISerializer
from api_builder.utils import APIKeyAuthentication, generate_api_key, read_columns_from_csv_or_xlsx_file
from core import settings
from core.utils import read_contents_from_csv_or_xlsx_file
from .models import API
from datahub.models import DatasetV2File

class ListUserAPIsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        apis = API.objects.filter(endpoint__startswith=f"/api/{user.id}/")
        serializer = APISerializer(apis, many=True)
        return JsonResponse({'apis': serializer.data}, status=200)

class CreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        endpoint = request.data.get('endpoint', None)
        final_endpoint = f"/api/{user.id}/{endpoint}"
        dataset_file_id = request.data.get('dataset_file_id', None)
        print(dataset_file_id)
        try:
            dataset_file = DatasetV2File.objects.get(id=dataset_file_id)
        except DatasetV2File.DoesNotExist:
            return JsonResponse({'error': 'Dataset file not found'}, status=404)

        access_key = generate_api_key()
        dataset_file_path = os.path.join(settings.DATASET_FILES_URL, str(dataset_file.standardised_file))
        selected_columns_json = request.data.get('selected_columns', '[]')

        try:
            selected_columns = json.loads(selected_columns_json)
            if not isinstance(selected_columns, list):
                raise ValueError('Selected columns must be a list')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON for selected_columns'}, status=400)

        existing_columns = read_columns_from_csv_or_xlsx_file(dataset_file_path)

        if not existing_columns:
            return JsonResponse({'error': 'Failed to read dataset file'}, status=500)

        missing_columns = [col for col in selected_columns if col not in existing_columns]

        if missing_columns:
            return JsonResponse({'error': f'Selected columns do not exist: {", ".join(missing_columns)}'}, status=400)

        api = API.objects.create(
            dataset_file=dataset_file,
            endpoint=final_endpoint,
            selected_columns=selected_columns,
            access_key=access_key
        )
        serializer = APISerializer(api)
        return JsonResponse({'message': 'API created successfully', 'api': serializer.data}, status=status.HTTP_200_OK)

class APIViewWithData(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, endpoint_name, user_id):
        api_key = request.headers.get('Authorization', '').split()[-1]
        final_endpoint = f"/api/{user_id}/{endpoint_name}"
        try:
            api = API.objects.get(access_key=api_key, endpoint=final_endpoint)
        except API.DoesNotExist:
            return Response({'error': 'API endpoint not found or unauthorized.'}, status=404)

        selected_columns = api.selected_columns
        file_path = api.dataset_file.file.path
        content = read_contents_from_csv_or_xlsx_file(file_path)
        filtered_content = [{col: row[col] for col in selected_columns} for row in content]

        return Response({'data': filtered_content}, status=status.HTTP_200_OK)
