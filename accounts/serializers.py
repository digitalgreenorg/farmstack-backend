from rest_framework import serializers
from accounts.models import User


class UserCreateSerializer(serializers.ModelSerializer):
    """UserCreateSerializer"""
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "status",
            "subscription"
            )


class UserUpdateSerializer(serializers.ModelSerializer):
    """UserUpdateSerializer"""
    class Meta:
        model = User
        fields = '__all__'


class VerifyAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.IntegerField()
