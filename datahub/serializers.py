from accounts import models
from rest_framework import serializers

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ['id', 'account_name', 'users', 'created']