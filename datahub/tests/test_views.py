import json
from calendar import c
from urllib import response

import pytest
from _pytest.monkeypatch import MonkeyPatch
from accounts.models import User, UserManager, UserRole
from datahub.models import Organization, UserOrganizationMap
from datahub.views import ParticipantViewSet
from django.test import Client, TestCase
from django.urls import reverse
from requests import request
from rest_framework import serializers


class MockUser:
    id = 1

class MockOrganization:
    id = 1

class MockUserSerializer(serializers.ModelSerializer):
  
    
    data = {'email': 'ugeshbasa7@digitalgreen.org',
            'first_name': 'ugesh', 'last_name': 'nani',
            'phone_number': '9985750356', 'role': "3",
            'profile_picture': 'sasas', 'status': "False", 
            'subscription': 'aaaa'}

    def is_valid(*args, **kwargs):
        """_summary_

        Returns:
            _type_: _description_
        """
        return None

    def save(*args, **kwargs):
        """_summary_

        Returns:
            _type_: _description_
        """
        return MockUser

    class Meta:
        """_summary_
        """
        model = User
        fields = ["role"]


class UserOrganizationMapSerializerMock(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """
    
    def is_valid(*args, **kwargs):
        """_summary_

        Returns:
            _type_: _description_
        """
        return None

    def save(*args, **kwargs):
        """_summary_

        Returns:
            _type_: _description_
        """
        return MockUser

    class Meta:
        """_summary_
        """
        model = UserOrganizationMap
        fields = []

valid_data  = {
            "email": "ugeshbasa45@digitalgreen.org",
            "org_email": "bglordg@digitalgreen.org",
            "first_name": "ugesh",
            "last_name": "nani",
            "role": int(3),
            "name": "digitalgreen",
            "phone_number": "9985750356",
            "website": "website.com",
            "address": json.dumps({"city": "Banglore"}),
            "profile_picture": "sasas",
            "subscription": "aaaa"
        }
invalid_role_data = {
                    "email": "ugeshbasa44@digitalgreen.org",
                    "org_email": "bglordg@digitalgreen.org",
                    "first_name": "ugesh",
                    "last_name": "nani",
                    "role": "3",
                    "name": "digitalgreen",
                    "phone_number": "9985750356",
                    "website": "website.com",
                    "address": json.dumps({"city": "Banglore"}),
                    "profile_picture": "sasas",
                    "subscription": "aaaa"
                }

class TestViews(TestCase):
    """_summary_

    Args:
        TestCase (_type_): _description_
    """
    def setUp(self) -> None:
        self.client = Client()
        self.create_url = reverse("participant-list")
        self.monkeypatch = MonkeyPatch()
        # monkeypatch.setattr("datahub.views.UserSerializer", 'save', data)

    def test_team_member_post_add_user_valid_email(self):
        """_summary_
        """
        self.monkeypatch.setattr("datahub.views.UserSerializer", MockUserSerializer)
        self.monkeypatch.setattr("datahub.views.UserOrganizationMapSerializer", UserOrganizationMapSerializerMock)
        response = self.client.post(self.create_url, valid_data)
        assert response.status_code == 201
        assert response.json() == MockUserSerializer.data


    def test_team_member_post_add_user_invalid_role(self):
        """_summary_
        """
        response = self.client.post(self.create_url, invalid_role_data)
        assert response.status_code == 400
        assert response.json().get("role") == ['Invalid pk "3" - object does not exist.']

