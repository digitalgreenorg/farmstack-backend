
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

from core.constants import Constants
from datahub.models import DatasetV2File, UsagePolicy


def protected_media_view(request, path):
    file = DatasetV2File.objects.get(id=path)
    if file.accessibility == Constants.PUBLIC:
        file_path = str(file.file)
    elif file.accessibility == Constants.REGISTERED:
        user_map = extract_jwt(request)
        if not user_map or isinstance(user_map, Response):
            return HttpResponse("Login to download this file.", status=404)
        file_path = str(file.file)
    elif file.accessibility == Constants.PRIVATE:
        user_map = extract_jwt(request)
        if not user_map or isinstance(user_map, Response):
            return HttpResponse("Login to download this file.", status=404)
        try:
            usage_policy = UsagePolicy.objects.select_related(Constants.USER_MAP_ORGANIZATION,).get(user_organization_map__user_id=user_map, dataset_file_id=file.id)
        except Exception as e:
            return HttpResponse("You don't have access to download this file, Send request to provider to get access.", status=403)
        if usage_policy.approval_status == Constants.APPROVED:
            file_path = str(file.file)
        else:
            return HttpResponse(f"You don't have access to download this file, Your request status is: {usage_policy.approval_status}.", status=403)
    file_path = os.path.join(settings.DATASET_FILES_URL, file_path)
    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found', 404)
    response = FileResponse(open(file_path, 'rb'))
    return response

def extract_jwt(request):
    refresh_token = request.headers.get(Constants.AUTHORIZATION)
    if refresh_token:
        try:
            refresh = AccessToken(refresh_token.replace("Bearer ", ""))
            user_map = refresh.payload
            return user_map.get(Constants.USER_ID, False) # type: ignore
        except TokenError as e:
            return Response(e, 401)
    else:
        return False
   