import datetime, logging

from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers, status
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.serializers import (
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
)

from core.utils import Utils
from utils import login_helper

LOGGER = logging.getLogger(__name__)


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
        email = serializer.validated_data["email"]
        serializer.save()

        gen_key = login_helper.generateKey()  # generate otp
        otp = gen_key.returnValue()["OTP"]

        # send OTP to the the user
        Utils().send_email(
            to_email=email,
            content=f"Your OTP is {otp}",
            subject=f"Your account verification OTP",
        )

        return Response(
            {
                "message": "Please verify your using OTP",
                "response": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        product = self.get_object()
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "updated user details", "response": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class LoginViewset(GenericViewSet):
    """LoginViewset for users to register"""

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
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # check if user is suspended
            if cache.get(user.id) is not None:
                if (
                    cache.get(user.id)["email"] == email
                    and cache.get(user.id)["cache_type"] == "user_suspension"
                ):
                    return Response(
                        {
                            "email": email,
                            "message": "Your account is suspended, please try after some time",
                        },
                        # status=status.HTTP_403_FORBIDDEN,
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

            # generate and send OTP to the the user
            gen_key = login_helper.generateKey()
            otp = gen_key.returnValue()["OTP"]
            Utils().send_email(
                to_email=email,
                content=f"Your OTP is {otp}",
                subject=f"Your account verification OTP",
            )

            # assign OTP to the user
            login_helper.create_user_otp(email, otp, settings.OTP_DURATION)
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


class VerifyLoginOTPViewset(GenericViewSet):
    """User verification with OTP"""

    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        """POST method: to verify registered users"""

        serializer = self.get_serializer(data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_entered = serializer.validated_data["otp"]
        user = User.objects.filter(email=email)
        user = user.first()

        try:
            # get current user otp object's data
            correct_otp = int(cache.get(email)["user_otp"])
            otp_created = cache.get(email)["updation_time"]
            # increment the otp counter
            otp_attempt = int(cache.get(email)["otp_attempt"]) + 1
            # update the expiry duration of otp
            new_duration = settings.OTP_DURATION - (
                datetime.datetime.now().second - otp_created.second
            )

            if correct_otp == int(otp_entered) and cache.get(email)["email"] == email:

                cache.delete(email)
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "user": user.id,
                        "email": user.email,
                        "status": user.status,
                        "role": str(user.role),
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "message": "Successfully logged in!",
                    },
                    status=status.HTTP_201_CREATED,
                )

            elif correct_otp != int(otp_entered) or cache.get(email)["email"] != email:
                # check for otp limit
                if cache.get(email)["otp_attempt"] < int(settings.OTP_LIMIT):
                    # update the user otp data
                    login_helper.create_user_otp(
                        email, correct_otp, new_duration, otp_attempt
                    )
                    print(cache.get(email))
                    return Response(
                        {
                            "message": "Invalid OTP, remaining attempts left: "
                            + str((int(settings.OTP_LIMIT) - int(otp_attempt)) + 1)
                        },
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                else:
                    cache.delete(email)
                    login_helper.user_suspension(user.id, email)
                    # print(cache.get(user.id))
                    return Response(
                        {
                            "message": "Maximum attempts taken, please retry after some time"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            # check otp expiration
            elif cache.get(email) is None:
                return Response(
                    {"message": "OTP expired verify again!"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as e:
            LOGGER.warning(e)

        return Response({"message": "Not allowed"}, status=status.HTTP_400_BAD_REQUEST)
