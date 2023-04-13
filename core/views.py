
import os
from tokenize import TokenError

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)

# from requests import Response
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from datahub.models import DatasetV2File, UsagePolicy


def protected_media_view(request, path):
    file = DatasetV2File.objects.get(id=path)
    print(file)
    if file.accessibility == 'public':
        print("its a public file")
        file_path = str(file.file)
    elif file.accessibility == 'registered':
        # import pdb; pdb.set_trace()
        print("its a registered file")
        user_map = extract_jwt(request)
        if not user_map or isinstance(user_map, Response):
            return HttpResponse("Login to download this file", status=401)
        file_path = str(file.file)
    elif file.accessibility == 'private':
        user_map = extract_jwt(request)
        if not user_map or isinstance(user_map, Response):
            return HttpResponse("Login to download this file", status=401)
        try:
            usage_policy = UsagePolicy.objects.get(user_organization_map_id=user_map, dataset_file_id=file.id)
        except Exception as e:
            return HttpResponse("You don't have access to download this file, Send request to provider to get access.", status=404)
        if usage_policy.approval_status == "approved":
            file_path = str(file.file)
        else:
            return HttpResponse(f"You don't have access to download this file, You request status is: {usage_policy.approval_status}", status=404)
    file_path = os.path.join(settings.PROTECTED_MEDIA_ROOT, 'datasets', file_path)
    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')
    # Add logic here to check if the user is authorized to access the file
    # For example, you could check if the user is logged in and has permission to access the file
    # If the user is not authorized, return a 403 Forbidden response
    response = FileResponse(open(file_path, 'rb'))
    return response

def extract_jwt(request):
    refresh_token = request.headers.get('Authorization')
    if refresh_token:
        try:
            refresh = AccessToken(refresh_token.replace("Bearer ", ""))
            user_map = refresh.payload
            return user_map.get("user_id", False) # type: ignore
        except TokenError as e:
            return Response(e, 401)
    else:
        return False
   