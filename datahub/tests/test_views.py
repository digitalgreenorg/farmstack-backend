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
        print(kwargs)
        return None

    def save(*args, **kwargs):
        return MockUser

    class Meta:
        model = User
        fields = ["role"]



class MockOrganization:
    class objects:
        def filter(*argss, **kwargs):
            return {"query_set": {"id": 1}}


class UserOrganizationMapSerializerMock(serializers.ModelSerializer):

    def is_valid(*args, **kwargs):
        return None

    def save(*args, **kwargs):
        return MockUser

    class Meta:
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
        UserRole.objects.create(role_name="datahub_participant_root")
        User.objects.create(email= "ugeshbasa45@digitalgreen.org",
            first_name = "ugesh",
            last_name = "nani",
            role = UserRole.objects.get(role_name="datahub_participant_root"),
            phone_number= "9985750356",
            profile_picture= "sasas",
            subscription= "aaaa")
        Organization.objects.create(
                    org_email = "bglordg@digitalgreen.org",
                    name= "digitalgreen",
                    phone_number = "9985750356",
                    website = "website.com",
                    address = json.dumps({"city": "Banglore"}))
        UserOrganizationMap.objects.create(
            user=User.objects.get(first_name="ugesh"),
            organization=Organization.objects.get(org_email = "bglordg@digitalgreen.org")
        )


    def test_participant_post_add_user_valid_email(self):
        """_summary_
        """       
        self.monkeypatch.setattr("datahub.views.Organization", MockOrganization)
        self.monkeypatch.setattr("datahub.views.UserCreateSerializer", MockUserSerializer)
        self.monkeypatch.setattr("datahub.views.UserOrganizationMapSerializer", UserOrganizationMapSerializerMock)
        response = self.client.post(self.create_url, valid_data)
        assert response.status_code == 201
        assert response.json() == MockUserSerializer.data


    def test_participant_post_add_user_invalid_fields_asserts(self):
        """_summary_
        """
        response = self.client.post(self.create_url, invalid_role_data)
        assert response.status_code == 400
        assert response.json().get("role") == ['Invalid pk "3" - object does not exist.']
        invalid_role_data["email"] = ""
        response = self.client.post(self.create_url, invalid_role_data)
        assert response.status_code == 400
        assert response.json()== {'email': ['This field may not be blank.'], 'role': ['Invalid pk "3" - object does not exist.']}


    def test_participant_post_add_user_valid_email(self):
        """_summary_
        """       
        self.monkeypatch.setattr("datahub.views.Organization", MockOrganization)

        self.monkeypatch.setattr("datahub.views.UserCreateSerializer", MockUserSerializer)
        self.monkeypatch.setattr("datahub.views.UserOrganizationMapSerializer", UserOrganizationMapSerializerMock)
        response = self.client.post(self.create_url, valid_data)
        assert response.status_code == 201
        assert response.json() == MockUserSerializer.data

    def test_participant_get_list(self):
        response = self.client.get(self.create_url)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count")== 1
        assert len(data.get("results")) == 1
        assert data.get("results")[0].get("user").get("phone_number") == "9985750356"
        assert data.get("results")[0].get("organization").get("website") == "website.com"

    def test_participant_delete(self):
        id = User.objects.get(first_name="ugesh").id
        response = self.client.delete(self.create_url+str(id)+"/")
        assert response.status_code == 204
        # Testing get after deleteing
        response = self.client.get(self.create_url)
        data = response.json()
        assert data.get("count")== 0
        assert len(data.get("results")) == 0

    
