from utils.jwt_services import JWTServices
import logging
from functools import wraps

from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

LOGGER = logging.getLogger(__name__)


def kenyan_only(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        try:
            authorization_header = request.META.get('HTTP_AUTHORIZATION')
            if not authorization_header:
                raise ValueError("Missing Authorization header.")

            payload = JWTServices.extract_information_from_token(request=request)
            if not payload:
                raise ValueError("Token extraction failed.")

            if payload["context"] != "Kenyan":
                return Response(
                    {"message": "You do not have access to this resource."},
                    status=status.HTTP_403_FORBIDDEN
                )

            return view_func(self, request, *args, **kwargs)

        except Exception as e:

            LOGGER.error(f"Unexpected error during JWT authentication: {e}")
            return Response(
                {"message": "Error During excution"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return wrapper
def indian_only(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        try:
            authorization_header = request.META.get('HTTP_AUTHORIZATION')
            if not authorization_header:
                raise ValueError("Missing Authorization header.")

            payload = JWTServices.extract_information_from_token(request=request)
            if not payload:
                raise ValueError("Token extraction failed.")

            if payload["context"] != "Indian":
                return Response(
                    {"message": "You do not have access to this resource."},
                    status=status.HTTP_403_FORBIDDEN
                )

            return view_func(self, request, *args, **kwargs)

        except Exception as e:

            LOGGER.error(f"Unexpected error during JWT authentication: {e}")
            return Response(
                {"message": "Error During excution"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return wrapper
def ethiopian_only(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        try:
            authorization_header = request.META.get('HTTP_AUTHORIZATION')
            if not authorization_header:
                raise ValueError("Missing Authorization header.")

            payload = JWTServices.extract_information_from_token(request=request)
            if not payload:
                raise ValueError("Token extraction failed.")

            if payload["context"] != "Ethiopian":
                return Response(
                    {"message": "You do not have access to this resource."},
                    status=status.HTTP_403_FORBIDDEN
                )

            return view_func(self, request, *args, **kwargs)

        except Exception as e:

            LOGGER.error(f"Unexpected error during JWT authentication: {e}")
            return Response(
                {"message": "Error During excution"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return wrapper
