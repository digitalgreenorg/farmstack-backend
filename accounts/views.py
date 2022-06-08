from django.core.cache import cache
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User
from accounts.serializers import UserCreateSerializer, VerifyAccountSerializer
from accounts.email import send_otp_via_email, send_verification_email


class LoginViewset(GenericViewSet):
    """ Registration viewset for users to register """
    serializer_class = UserCreateSerializer
    # queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        """POST method: to save a newly registered user"""
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


class VerifyOTPViewset(GenericViewSet):
    """ Verification for OTP  """
    serializer_class = VerifyAccountSerializer

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

        elif cache.get('user_obj') != otp and cache.get('user_obj') is not None:
            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'Invalid OTP'
                })

        elif cache.get('user_obj', sentinel) is sentinel:
            return Response({
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'message': 'OTP expired, verify again'
                })

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=email)
        user = user.first()
        user.status = True
        user.save()
        cache.delete_many(['user_obj', 'creation_time'])

        # send_otp_via_email(email)
        return Response({
            'status': status.HTTP_201_CREATED,
            'payload': serializer.data,
            'message': 'created user'
            })

