import uuid
from urllib import response

import pytest
from accounts.models import User, UserManager, UserRole
from datahub.views import ParticipantViewSet
from django.test import Client, TestCase
from django.urls import reverse
from requests import request
from rest_framework import serializers


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
    data = ''


class TestViews(TestCase):
    """_summary_

    Args:
        TestCase (_type_): _description_
    """
    def setUp(self) -> None:
        self.client = Client()
        self.create_url = reverse("participant-list")

    def test_team_member_post_add_user_invalid_email(self):
        """_summary_
        """
        # monkeypatch.setattr("datahub.views.UserSerializer", MockUserSerializer)
        response = self.client.post(self.create_url, {"email": "email", "first_name": "first_name", "last_name": "last_name",
                            "phone_number": "phone_number", "role": "222",
                            "profile_picture": "profile_picture", "status": True,
                            "subscription": "subscription" })
        # response = team_member.create(MockRequest)
        assert response.status_code == 400
        assert response.json().get("email") == ['Enter a valid email address.']
        assert response.json().get("role") == ['Invalid pk "222" - object does not exist.']

    def test_team_member_post_add_user_valid_email(self):
        """_summary_
        """
        # monkeypatch.setattr("datahub.views.UserSerializer", MockUserSerializer)
        response = self.client.post(self.create_url, {"email": "test.user@gmail.com", "first_name": "first_name", "last_name": "last_name",
                            "phone_number": "phone_number", "role": int(2),
                            "profile_picture": "profile_picture", "status": True,
                            "subscription": "subscription" })
        # response = team_member.create(MockRequest)
        print(response.json())
        assert response.status_code == 400
        assert response.json().get("email") == None
        assert response.json().get("role") == ['Invalid pk "2" - object does not exist.']
