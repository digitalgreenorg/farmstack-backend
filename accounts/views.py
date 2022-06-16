import datetime
import logging

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.shortcuts import render
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.email import send_otp_via_email, send_verification_email
from accounts.models import User
from accounts.serializers import UserCreateSerializer, UserUpdateSerializer

from .email import send_otp_via_email
from .utils import OTPManager

LOGGER = logging.getLogger(__name__)


class RegisterViewset(GenericViewSet):
    """RegisterViewset for users to register"""

    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user
        creates a new user with status False
        User uses OTP to verify account
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        email = request.data["email"]
        send_otp_via_email(email)
        return Response(
            {"message": "Please verify your account using OTP"},
            status=status.HTTP_201_CREATED,
        )


class LoginViewset(GenericViewSet):
    """LoginViewset for users to register"""

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user"""
        email = request.data["email"]
        user_obj = User.objects.filter(email=self.request.data["email"]).values()

        if not user_obj:
            return Response({"message": "User not registered"}, status=status.HTTP_401_UNAUTHORIZED)

        elif user_obj[0]["status"] is False:
            return Response(
                {"message": "User not verified, please verify using OTP"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        send_otp_via_email(email)
        return Response({"message": "Enter the OTP to login"}, status=status.HTTP_201_CREATED)


class VerifyLoginOTPViewset(GenericViewSet):
    """User verification with OTP"""

    def create(self, request, *args, **kwargs):
        """POST method: to verify registered users"""
        email = self.request.data["email"]
        otp_entered = self.request.data["otp"]
        user = User.objects.filter(email=email)
        user = user.first()
        refresh = RefreshToken.for_user(user)

        try:
            # get current user otp object's data
            otp_manager = OTPManager()
            correct_otp = int(cache.get(email)["user_otp"])
            otp_created = cache.get(email)["updation_time"]
            otp_count = int(cache.get(email)["otp_count"]) + 1  # increment the otp counter
            new_duration = settings.OTP_DURATION - (
                datetime.datetime.now().second - otp_created.second
            )  # reduce expiry duration of otp

            if correct_otp == int(otp_entered) and cache.get(email)["email"] == email:
                cache.delete(email)
                return Response(
                    {
                        "message": "Successfully logged in!",
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    status=status.HTTP_200_OK,
                )

            elif correct_otp != int(otp_entered) or cache.get(email)["email"] != email:
                # check for otp limit
                if cache.get(email)["otp_count"] <= int(settings.OTP_LIMIT):
                    # update the user otp data
                    otp_manager.create_user_otp(email, correct_otp, new_duration, otp_count)
                    return Response(
                        {"message": "Invalid OTP, please enter valid credentials"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                else:
                    # when reached otp limit set user status = False
                    user.status = False
                    user.save()

                    return Response(
                        {"message": "Maximum attempts taken, please retry after some time"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            # check otp expiration
            elif cache.get(email) is None:
                return Response(
                    {"message": "OTP expired Verify again!"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as e:
            LOGGER.warning(e)

        return Response({"message": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
