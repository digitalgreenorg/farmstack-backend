import datetime, logging
from asyncio import exceptions
from asyncio.log import logger

from core.constants import Constants
from core.utils import Utils
from datahub.models import UserOrganizationMap
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from rest_framework import serializers, status
from rest_framework.decorators import action, permission_classes
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User, UserRole
from accounts.serializers import (
    LoginSerializer,
    OtpSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)
from utils import login_helper, string_functions

LOGGER = logging.getLogger(__name__)


@permission_classes([])
class RegisterViewset(GenericViewSet):
    """RegisterViewset for users to register"""

    parser_classes = (MultiPartParser, FileUploadParser)
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return UserUpdateSerializer
        return UserCreateSerializer

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user
        creates a new user with status False
        """
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                # "message": "Please verify your using OTP",
                "message": "Successfully created the account!",
                "response": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    # def list(self, request, *args, **kwargs):
    #     """GET method: query all the list of objects from the Product model"""
    #     queryset = self.filter_queryset(self.get_queryset())
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)

    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        user = self.get_object()
        serializer = self.get_serializer(user)
        # serializer = UserUpdateSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        # serializer = UserUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "updated user details", "response": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        user = self.get_object()
        # user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@permission_classes([])
class LoginViewset(GenericViewSet):
    """LoginViewset for users to register"""

    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user_obj = User.objects.filter(email=email)
        user = user_obj.first()
        user_role_obj = UserRole.objects.filter(role_name=request.data.get("role")) 
        user_role = user_role_obj.first().id if user_role_obj else None

        try:
            if not user:
                return Response(
                    {"email": "User not registered"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            elif user.status == False:
                return Response(
                    {"email": "User is deleted"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # check user role
            if user_role != user.role_id:
                message = "This email is not registered as "
                switcher = {
                    1: "admin",
                    3: "participant"
                }

                message += str(switcher.get(user_role, request.data.get("role")))
                return Response({
                    "message": message
                }, status=status.HTTP_401_UNAUTHORIZED)

            # check if user is suspended
            if cache.get(user.id) is not None:
                if cache.get(user.id)["email"] == email and cache.get(user.id)["cache_type"] == "user_suspension":
                    return Response(
                        {
                            "email": email,
                            "message": "Your account is suspended, please try after some time",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

            # generate and send OTP to the the user
            gen_key = login_helper.generateKey()
            otp = gen_key.returnValue().get("OTP")
            full_name = string_functions.get_full_name(user.first_name, user.last_name)
            data = {"otp": otp, "participant_admin_name": full_name}

            email_render = render(request, "otp.html", data)
            mail_body = email_render.content.decode("utf-8")

            Utils().send_email(
                to_email=email,
                # content=f"Your OTP is {otp}",
                content=mail_body,
                subject=f"Your account verification OTP",
            )

            # assign OTP to the user using cache
            login_helper.set_user_otp(email, otp, settings.OTP_DURATION)
            print(cache.get(email))

            return Response(
                {
                    "id": user.id,
                    "email": email,
                    "message": "Enter the OTP to login",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            LOGGER.warning(e)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def onboarded(self, request):
        """This method makes the user on-boarded"""
        try:
            user = User.objects.get(id=request.data.get(Constants.USER_ID, ""))
        except Exception as error:
            LOGGER.error("Invalid user id: %s", error)
            return Response(["Invalid User id"], 400)
        if User:
            user.on_boarded = request.data.get("on_boarded", True)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(["Invalid User id"], 400)


@permission_classes([])
class ResendOTPViewset(GenericViewSet):
    """ResendOTPViewset for users to register"""

    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email)
        user = user.first()

        try:
            if not user:
                return Response(
                    {"email": "User not registered"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # check if user is suspended
            if cache.get(user.id) is not None:
                if cache.get(user.id)["email"] == email and cache.get(user.id)["cache_type"] == "user_suspension":
                    return Response(
                        {"email": email, "message": "Maximum attempts taken, please retry after some time"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            gen_key = login_helper.generateKey()

            # update the current attempts of OTP
            if cache.get(email):
                otp = gen_key.returnValue()["OTP"]
                Utils().send_email(
                    to_email=email,
                    content=f"Your OTP is {otp}",
                    subject=f"Your account verification OTP",
                )

                otp_attempt = int(cache.get(email)["otp_attempt"])
                login_helper.set_user_otp(email, otp, settings.OTP_DURATION, otp_attempt)
                print(cache.get(email))

            # generate a new attempts of OTP
            elif not cache.get(email):
                otp = gen_key.returnValue()["OTP"]
                Utils().send_email(
                    to_email=email,
                    content=f"Your OTP is {otp}",
                    subject=f"Your account verification OTP",
                )

                login_helper.set_user_otp(email, otp, settings.OTP_DURATION)

            return Response(
                {
                    "id": user.id,
                    "email": email,
                    "message": "Enter the resent OTP to login",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            LOGGER.warning(e)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([])
class VerifyLoginOTPViewset(GenericViewSet):
    """User verification with OTP"""

    serializer_class = OtpSerializer

    def create(self, request, *args, **kwargs):
        """POST method: to verify registered users"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_entered = serializer.validated_data["otp"]
        # user = User.objects.filter(user__email=email).select_related()
        user_map = UserOrganizationMap.objects.select_related("user").filter(user__email=email).first()
        user = User.objects.filter(email=email)
        user = user.first()

        try:
            # check if user is suspended
            if cache.get(user.id) is not None:
                if cache.get(user.id)["email"] == email and cache.get(user.id)["cache_type"] == "user_suspension":
                    return Response(
                        {"email": email, "message": "Maximum attempts taken, please retry after some time"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            elif cache.get(user.id) is None:
                if cache.get(email) is not None:
                    # get current user otp object's data
                    user_otp = cache.get(email)
                    correct_otp = int(user_otp["user_otp"])
                    otp_created = user_otp["updation_time"]
                    # increment the otp counter
                    otp_attempt = int(user_otp["otp_attempt"]) + 1
                    # update the expiry duration of otp
                    new_duration = settings.OTP_DURATION - (datetime.datetime.now().second - otp_created.second)

                    # On successful validation generate JWT tokens
                    if correct_otp == int(otp_entered) and cache.get(email)["email"] == email:
                        cache.delete(email)
                        refresh = RefreshToken.for_user(user)
                        return Response(
                            {
                                "user": user.id,
                                "user_map": user_map.id if user_map else None,
                                "org_id": user_map.organization_id if user_map else None,
                                "email": user.email,
                                "status": user.status,
                                "on_boarded": user.on_boarded,
                                "role": str(user.role),
                                "role_id": str(user.role_id),
                                "refresh": str(refresh),
                                "access": str(refresh.access_token),
                                "message": "Successfully logged in!",
                            },
                            status=status.HTTP_201_CREATED,
                        )

                    elif correct_otp != int(otp_entered) or cache.get(email)["email"] != email:
                        # check for otp limit
                        if cache.get(email)["otp_attempt"] < int(settings.OTP_LIMIT):
                            # update the user otp data in cache
                            login_helper.set_user_otp(email, correct_otp, new_duration, otp_attempt)
                            print(cache.get(email))

                            return Response(
                                {
                                    "message": "Invalid OTP, remaining attempts left: "
                                    + str((int(settings.OTP_LIMIT) - int(otp_attempt)) + 1)
                                },
                                status=status.HTTP_401_UNAUTHORIZED,
                            )
                        else:
                            # On maximum invalid OTP attempts set user status to False
                            cache.delete(email)
                            login_helper.user_suspension(user.id, email)
                            # user.status = False
                            # user.save()

                            return Response(
                                {"email": email, "message": "Maximum attempts taken, please retry after some time"},
                                status=status.HTTP_403_FORBIDDEN,
                            )
                    # check otp expiration
                    elif cache.get(email) is None:
                        return Response(
                            {"message": "OTP expired verify again!"},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )

        except Exception as e:
            LOGGER.error(e)
            print("Please click on resend OTP and enter the new OTP")

        return Response(
            {"message": "Please click on resend OTP and enter the new OTP"},
            status=status.HTTP_403_FORBIDDEN,
        )
