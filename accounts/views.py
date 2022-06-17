from django.contrib.auth import authenticate
from django.core.cache import cache
from django.shortcuts import render
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User
from accounts.serializers import UserCreateSerializer, UserUpdateSerializer
from accounts.email import send_otp_via_email, send_verification_email
from django.conf import settings
from .email import send_otp_via_email
import datetime, logging, os, shutil
from .utils import OTPManager
from rest_framework.parsers import MultiPartParser, FileUploadParser
from PIL import Image
from datahub.models import DatahubDocuments
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

LOGGER = logging.getLogger(__name__)

class RegisterViewset(GenericViewSet):
    """RegisterViewset for users to register"""

    parser_classes = (MultiPartParser, FileUploadParser)
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return UserUpdateSerializer
        return UserCreateSerializer

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
        return Response({"message": "Please verify your account using OTP", "response": serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        product = self.get_object()
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "updated user details", "response": serializer.data}, status=status.HTTP_201_CREATED)


class LoginViewset(GenericViewSet):
    """LoginViewset for users to register"""
    serializer_class = UserCreateSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user"""

        email = request.data["email"]
        user_obj = User.objects.filter(email=self.request.data["email"]).values()
        user_id = user_obj[0]['id']

        if not user_obj:
            return Response(
                {"message": "User not registered"}, status=status.HTTP_401_UNAUTHORIZED
            )

        elif user_obj[0]["status"] is False:
            return Response(
                {"message": "User not verified, please verify using OTP"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        send_otp_via_email(email)
        return Response({"message": "Enter the OTP to login", "id": user_id, "email": user_obj[0]["email"]}, status=status.HTTP_201_CREATED)


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
            otp_count = (
                int(cache.get(email)["otp_count"]) + 1
            )  # increment the otp counter
            new_duration = settings.OTP_DURATION - (
                datetime.datetime.now().second - otp_created.second
            )  # reduce expiry duration of otp

            if correct_otp == int(otp_entered) and cache.get(email)["email"] == email:
                cache.delete(email)
                return Response(
                    {"message": "Successfully logged in!",
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }, status=status.HTTP_200_OK
                )

            elif correct_otp != int(otp_entered) or cache.get(email)["email"] != email:
                # check for otp limit
                if cache.get(email)["otp_count"] <= int(settings.OTP_LIMIT):
                    # update the user otp data
                    otp_manager.create_user_otp(
                        email, correct_otp, new_duration, otp_count
                    )
                    return Response(
                        {"message": "Invalid OTP, please enter valid credentials"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                else:
                    # when reached otp limit set user status = False
                    user.status = False
                    user.save()

                    return Response(
                        {
                            "message": "Maximum attempts taken, please retry after some time"
                        },
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


class PolicyDocumentsView(APIView):
    """ View for Policy document uploads """
    # serializer_class = PolicyDocumentSerializer
    parser_class = (MultiPartParser, FileUploadParser)

    def post(self, request):
        try:
            files = dict((request.data).lists())['file']

            for file in files:
                with open(settings.CONTENT_URL + file.name, 'wb+') as file_upload_path:

                    if not file_upload_path:
                        for chunk in file.chunks():
                            file_upload_path.write(chunk)
                            print(str(file) + " uploaded!")
                        return Response({'message: files successfully uploaded!'}, status=status.HTTP_201_CREATED)
                    else:
                        print(str(file) + " already present")
            return Response({'message: files are already present!'}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            LOGGER.error(e)

        return Response({'message: encountered an error while uploading'}, status=status.HTTP_400_BAD_REQUEST)
