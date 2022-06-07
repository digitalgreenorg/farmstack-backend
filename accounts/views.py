from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User
from accounts.serializers import UserCreateSerializer, VerifyAccountSerializer
from accounts.email import send_otp_via_email, send_verification_email


class SignupAPIView(APIView):
    """SignupAPI view to regiter new users"""

    def post(self, request):
        data = request.data
        serializer = UserCreateSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            email = serializer.data["email"]
            send_otp_via_email(email)
            return Response(
                {
                    "status": 200,
                    "messsage": "registration successful! Check email for verification",
                    "data": serializer.data,
                }
            )

        else:
            return Response(
                {
                    "status": 400,
                    "message": "something went wrong",
                    "data": serializer.errors,
                }
            )


class VerifyOTPView(APIView):
    """Verify OTP for Signup"""

    def post(self, request):
        data = request.data
        serializer = VerifyAccountSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            email = serializer.data["email"]
            otp = serializer.data["otp"]
            user = User.objects.filter(email=email)

            if not user.exists():
                return Response(
                    {
                        "status": 400,
                        "message": "invalid email",
                        "data": serializer.errors,
                    }
                )

            elif user[0].otp != otp:
                return Response(
                    {"status": 400, "message": "wrong OTP!", "data": serializer._errors}
                )

            user = user.first()
            # user.is_active = True
            user.status = True
            user.save()
            send_verification_email(email)
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "status": 200,
                    "message": "Account verified!",
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
