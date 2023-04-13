
import os
from tokenize import TokenError

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseNotFound
from requests import Response
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from datahub.models import DatasetV2File, UsagePolicy


def protected_media_view(request, path):
    file = DatasetV2File.objects.get(id=path)
    print(file)
    import pdb; pdb.set_trace()
    if file.accessibility == 'public':
        print("its a public file")
        file_path = file.file

    if file.accessibility == 'registered':
        user_map = extract_jwt(request)
        print("its a registered file")

        file_path = file.file
    else:
        return {"message": "Login to download this file"}
    if file.accessibility == 'private':
        user_map = extract_jwt(request)
        if UsagePolicy.objects.get(user_map=user_map, dataset_file=file.id):
            print("its a Private file")
            file_path = file.file
        else:
            return {"message": "You don't have access to download this file"}
    # file_path = os.path.join(settings.PROTECTED_MEDIA_ROOT, 'datasets', path.replace("media/", ''))
    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')
    # Add logic here to check if the user is authorized to access the file
    # For example, you could check if the user is logged in and has permission to access the file
    # If the user is not authorized, return a 403 Forbidden response
    response = FileResponse(open(file_path, 'rb'))
    return response

def extract_jwt(request):
    refresh_token = request.data.get('refresh_token')
    if refresh_token:
        try:
            refresh = RefreshToken(refresh_token)
            user_map = refresh.payload
            return user_map.id # type: ignore
        except TokenError as e:
            return False
   