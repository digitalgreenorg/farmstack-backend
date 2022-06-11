from django.db import models
from django.db.models import fields
from rest_framework import serializers
from accounts.models import User

from accounts.models import User


class UserCreateSerializer(serializers.ModelSerializer):
    """UserCreateSerializer"""

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


class UserUpdateSerializer(serializers.ModelSerializer):
    """UserUpdateSerializer"""

    class Meta:
        model = User
        fields = "__all__"
