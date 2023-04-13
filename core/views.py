
from django.http import HttpResponseBadRequest, HttpResponseNotFound, FileResponse
from django.conf import settings
import os

def protected_media_view(request, path):
    if '..' in path:
        return HttpResponseBadRequest('Invalid path')
    file_path = os.path.join(settings.MEDIA_ROOT, 'protected_media', path)
    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')
    # Add logic here to check if the user is authorized to access the file
    # For example, you could check if the user is logged in and has permission to access the file
    # If the user is not authorized, return a 403 Forbidden response
    response = FileResponse(open(file_path, 'rb'))
    return response