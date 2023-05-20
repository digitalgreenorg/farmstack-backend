from functools import wraps
from rest_framework import status
from rest_framework.response import Response

from connectors.models import Connectors
from core.constants import Constants
from datahub.models import Datasets, DatasetV2File, Organization, DatasetV2
from utils.jwt_services import JWTServices


def authenticate_user(model):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            payload = JWTServices.extract_information_from_token(
                request=request
            )

            if model == DatasetV2File:
                query_id = kwargs.get('pk')
                dsv = DatasetV2File.objects.filter(id=query_id, dataset__user_map_id=payload.get("map_id"))
                if not dsv:
                    return Response({
                        "message": "Authorization Failed"
                    }, status=status.HTTP_403_FORBIDDEN)

            if model == DatasetV2:
                query_id = kwargs.get('pk')
                dsv = DatasetV2.objects.filter(id=query_id, user_map_id=payload.get("map_id"))
                if not dsv:
                    return Response({
                        "message": "Authorization Failed"
                    }, status=status.HTTP_403_FORBIDDEN)

            elif model == Connectors:
                query_id = kwargs.get('pk')
                con = Connectors.objects.filter(id=query_id, user_id=payload.get("user_id"))
                if not con:
                    return Response({
                        "message": "Authorization Failed"
                    }, status=status.HTTP_403_FORBIDDEN)

            # participants
            elif model == Organization:
                if str(payload.get("role_id")) == str(1):
                    pass
                if str(payload.get("role_id")) == str(6) and str(payload.get("onboarded_by")) == str(
                        payload.get("user_id")):
                    pass

                else:
                    return Response({
                        "message": "No resource found."
                    }, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({
                    "message": "No resource found."
                }, status=status.HTTP_400_BAD_REQUEST)

            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator
