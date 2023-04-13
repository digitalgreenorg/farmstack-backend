
import os

from django.conf import settings
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseNotFound


def protected_media_view(request, path):
    if '..' in path:
        return HttpResponseBadRequest('Invalid path')
    print(path)
    file_path = os.path.join(settings.PROTECTED_MEDIA_ROOT, 'datasets', path.replace("media/", ''))
    print(file_path)
    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')
    # Add logic here to check if the user is authorized to access the file
    # For example, you could check if the user is logged in and has permission to access the file
    # If the user is not authorized, return a 403 Forbidden response
    response = FileResponse(open(file_path, 'rb'))
    return response