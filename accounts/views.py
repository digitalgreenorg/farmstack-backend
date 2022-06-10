from django.core.cache import cache
from django.shortcuts import render
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User
from accounts.serializers import UserCreateSerializer, UserUpdateSerializer
from accounts.email import send_otp_via_email, send_verification_email
from django.conf import settings
from .email import send_otp_via_email


class RegisterViewset(GenericViewSet):
    """ RegisterViewset for users to register """
    serializer_class = UserCreateSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user
            creates a new user with status False
            User uses OTP to verify account
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        email = request.data['email']
        send_otp_via_email(email)
        return Response({
            'status': status.HTTP_201_CREATED,
            'payload': serializer.data,
            'message': 'Please verify your account using OTP'
            })


class LoginViewset(GenericViewSet):
    """ LoginViewset for users to register """

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user"""
        email = request.data['email']
        user_obj = User.objects.filter(email=self.request.data['email']).values()
        send_otp_via_email(email)

        if not user_obj:
            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'User not registered'
                })

        elif user_obj[0]['status'] is False:
            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'User not verified, please verify using OTP.'
                })

        return Response({
            'status': status.HTTP_201_CREATED,
            'message': 'Enter the OTP to login'
            })


class VerifyOTPViewset(GenericViewSet):
    """ User verification with OTP  """

    def create(self, request, *args, **kwargs):
        """POST method: to verify registered users"""
        email = self.request.data['email']
        user_obj = User.objects.filter(email=self.request.data['email']).values()
        otp = self.request.data['otp']
        sentinel = object()     # to check otp expiration

        if not user_obj:
            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'User not registered'
                })

        elif cache.get('user_otp') != otp and cache.get('user_otp') is not None:
            try:
                if int(cache.get('otp_count')) <= int(settings.OTP_MAX):
                    cache.set('otp_count',int(cache.get('otp_count')) + 1)
                else:
                    user = User.objects.filter(email=email)
                    user = user.first()
                    user.status = False
                    user.save()

                    return Response({
                            'status': status.HTTP_401_UNAUTHORIZED,
                            'message': 'Please try after sometime'
                        })

            except Exception as e:
                print(e)

            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'Invalid OTP'
                })

        elif cache.get('user_otp', sentinel) is sentinel:
            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'OTP expired, verify again'
                })

        # elif cache.get('user_otp') == otp and cache.get('user_otp') is not None:
        #     return Response({
        #             'status': status.HTTP_401_UNAUTHORIZED,
        #             'message': 'User already validated!'
        #         })

        user = User.objects.filter(email=email)
        user = user.first()
        user.status = True
        user.save()
        cache.delete_many(['user_otp', 'creation_time'])

        send_otp_via_email(email)
        return Response({
            'status': status.HTTP_201_CREATED,
            'message': 'User Successfully verified!'
            })


class ResendOTP(GenericViewSet):
    """ Resend OTP for users """

    def create(self, request, *args, **kwargs):
        """POST method: to resend the otp for account verification"""
        email = request.data['email']

        send_otp_via_email(email)
        return Response({
            'status': status.HTTP_201_CREATED,
            'message': 'Please verify your account using OTP'
            })

