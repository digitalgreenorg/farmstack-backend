from django.db import models
from django.db.models import fields
from rest_framework import serializers

from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_staff", "", "", "", "", "", ""]