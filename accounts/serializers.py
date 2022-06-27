from django.db import models
from django.db.models import fields
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser

from accounts.models import User


class UserCreateSerializer(serializers.ModelSerializer):
    """UserCreateSerializer"""

    parser_classes = MultiPartParser

    class Meta:
        model = User
        # fields = (
        #     "email",
        #     "first_name",
        #     "last_name",
        #     "phone_number",
        #     "role",
        #     "status",
        #     "subscription"
        #     )
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "status",
            "subscription",
            "profile_picture",
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    """UserUpdateSerializer"""

    class Meta:
        model = User
        # exclude = ("created_at", "updated_at")
        fields = ("email", "first_name", "last_name", "phone_number")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.IntegerField()
