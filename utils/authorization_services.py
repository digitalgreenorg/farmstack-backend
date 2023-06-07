from functools import wraps
from typing import Union

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from utils.jwt_services import JWTServices


class AuthorizationServices:
    @classmethod
    def extract_information_from_token(cls, request: Request):
        mapping = {}

        current_user, payload = JWTAuthentication().authenticate(request)
        mapping.update({
            "user_id": str(payload.get("user_id")),
            "org_id": str(payload.get("org_id")),
            "map_id": str(payload.get("map_id")),
            "role_id": str(payload.get("role")),
            "onboarded_by": str(payload.get("onboarded_by"))
        })
        return mapping


def role_authorization(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        payload = JWTServices.extract_information_from_token(request=request)

        request.META["user_id"] = payload.get("user_id")
        request.META["org_id"] = payload.get("org_id")
        request.META["map_id"] = payload.get("map_id")
        request.META["onboarded_by"] = payload.get("onboarded_by", None)
        request.META["role_id"] = payload.get("role_id")
        # check the relationship coupling

        role = identify_user()
        return view_func(self, request, *args, **kwargs)

    return wrapper


def identify_user():
    return True
