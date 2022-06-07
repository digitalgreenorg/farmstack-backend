import pytest
from sys import set_asyncgen_hooks
from requests import request
from rest_framework.viewsets import GenericViewSet
from django.db import models
from django.db.models import fields
from rest_framework import serializers
from accounts.models import User
from tests.test_datahub.mock_models import MockUser, MockUserManager, MockUserRole
from datahub.views import TeamMemberViewSet


class MockUserSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    class Meta:
        """_summary_
        """
        model = User
        fields = ["email", "first_name", "last_name", "phone_number", "role", "profile_picture",
         "status", "subscription"]

class MockRequest:
    data = {}

@pytest.mark.parametrize("test_input, expected",
                        [({"email": "email", "first_name": "first_name", "last_name": "last_name",
                         "phone_number": "phone_number", "role": "role",
                          "profile_picture": "profile_picture", "status": "status",
                           "subscription": "subscription"}, "sucess")])
def test_create_with_serializer(monkeypatch, test_input, expected):
    """_summary_
    """
    monkeypatch.setattr("datahub.views.UserSerializer", MockUserSerializer)
    monkeypatch.setattr("accounts.models.User", MockUser)
    request.data = test_input
    result = TeamMemberViewSet().create(request)
    assert result == expected