from django.db import models
from django.db.models import fields
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser

from accounts.models import User, UserRole


class UserRoleSerializer(serializers.ModelSerializer):
    """UserRoleSerializer"""

    class Meta:
        model = UserRole
        # exclude = ("id",)
        fields = "__all__"


class UserCreateSerializer(serializers.ModelSerializer):
    """UserCreateSerializer"""

    parser_classes = MultiPartParser

    role = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        required=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "subscription",
            "profile_picture",
            "on_boarded",
        )
        # fields = "__all__"
        depth = 1


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
            "on_boarded",
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    """UserUpdateSerializer"""

    role = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        required=True,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "profile_picture",
            "on_boarded",
        )
        depth = 1


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.CharField()


class OtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.IntegerField()
