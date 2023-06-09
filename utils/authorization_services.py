from functools import wraps
from typing import Union

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from participant.models import SupportTicketV2, Resolution
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


def support_ticket_role_authorization(model_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            payload = JWTServices.extract_information_from_token(request=request)

            request.META["user_id"] = payload.get("user_id")
            request.META["org_id"] = payload.get("org_id")
            request.META["map_id"] = payload.get("map_id")
            request.META["onboarded_by"] = payload.get("onboarded_by")
            request.META["role_id"] = payload.get("role_id")

            if model_name == "Resolution":
                if not kwargs.get("pk"):
                    # not a update / delete api def create api
                    # pk = ticket ID from body
                    primary_key = request.data.get("ticket")
                else:
                    # pk = resolution ID from path for update / delete
                    try:
                        res = Resolution.objects.get(id=kwargs.get("pk")).ticket_id
                        primary_key = res
                    except Resolution.DoesNotExist:
                        return Response(
                            {"message": "Invalid Resolution ID."},
                            status=status.HTTP_403_FORBIDDEN,
                        )

            elif model_name == "SupportTicketV2":
                # pk = ticket ID from path for update / delete
                primary_key = kwargs.get("pk")
            else:
                return Response(
                    {"message": "Invalid parameters."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            validation = validate_role_modify(
                onboarding_by_id=payload.get("onboarded_by"),
                user_id=payload.get("user_id"),
                role_id=payload.get("role_id"),
                map_id=payload.get("map_id"),
                pk=primary_key,
            )

            if not validation:
                return Response(
                    {"message": "Authorization Failed. You do not have access to this resource."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def validate_role_modify(onboarding_by_id: Union[str, None], user_id: str, role_id: str, map_id: str, pk: str):
    if onboarding_by_id is None and role_id == 1:
        return True
    elif onboarding_by_id is not None and onboarding_by_id == user_id:
        return True
    else:
        try:
            ticket = SupportTicketV2.objects.get(id=pk, user_map_id=map_id)
            return True if ticket else False
        except SupportTicketV2.DoesNotExist:
            return False