import json
from calendar import c
from urllib import response
from uuid import uuid4

import pytest
from _pytest.monkeypatch import MonkeyPatch
from accounts.models import User, UserManager, UserRole
from datahub.models import Organization, UserOrganizationMap
from datahub.views import ParticipantViewSet
from django.test import Client, TestCase
from django.urls import reverse
from requests import request
from requests_toolbelt.multipart.encoder import MultipartEncoder
from rest_framework import serializers
from rest_framework.response import Response

valid_data = {
    "email": "ugeshbasa4ss5@digitalgreen.org",
    "org_email": "bglordg1@digitalgreen.org",
    "first_name": "ugesh",
    "last_name": "nani",
    "role": 3,
    "name": "digitalgreen",
    "phone_number": "9985750356",
    "website": "website.com",
    "address": json.dumps({"city": "Banglore"}),
    "profile_picture": open("datahub/tests/test_data/pro.png", "rb"),
    "subscription": "aaaa",
}
update_data = {
    "email": "ugeshbasa4ss5@digitalgreen.org",
    "org_email": "bglordg@digitalgreen.org",
    "first_name": "ugeshBasa",
    "last_name": "nani",
    "role": 3,
    "name": "digitalgreen",
    "phone_number": "1234567890",
    "website": "website.com",
    "address": json.dumps({"city": "Banglore"}),
    "subscription": "aaaa",
    # "profile_picture": open("datahub/tests/test_data/pro.png", "rb"),
}

invalid_role_data = {
    "email": "ugeshbasa44@digitalgreen.org",
    "org_email": "bglordg@digitalgreen.org",
    "first_name": "ugesh",
    "last_name": "nani",
    "role": "33",
    "name": "digitalgreen",
    "phone_number": "9985750356",
    "website": "website.com",
    "address": json.dumps(
        {"address": "Banglore", "country": "India", "pincode": "501011"}
    ),
    "profile_picture": open("datahub/tests/test_data/pro.png", "rb"),
    "subscription": "aaaa",
}


class MockUtils:
    def send_email(self, to_email: list, content=None, subject=None):
        if to_email == []:
            return Response({"message": "Invalid email address"}, 400)
        else:
            return Response(
                {"Message": "Invation sent to the participants"}, status=200
            )


class TestViews(TestCase):
    """_summary_

    Args:
        TestCase (_type_): _description_
    """

    def setUp(self) -> None:
        self.client = Client()
        self.participant_url = reverse("participant-list")
        self.send_invite = reverse("send_invite-list")

        self.monkeypatch = MonkeyPatch()
        UserRole.objects.create(role_name="datahub_admin")
        UserRole.objects.create(role_name="datahub_team_member")
        UserRole.objects.create(role_name="datahub_participant_root")
        User.objects.create(
            email="ugeshbasa45@digitalgreen.org",
            first_name="ugesh",
            last_name="nani",
            role=UserRole.objects.get(role_name="datahub_participant_root"),
            phone_number="9985750356",
            profile_picture="sasas",
            subscription="aaaa",
        )
        org = Organization.objects.create(
            org_email="bglordg@digitalgreen.org",
            name="digitalgreen",
            phone_number="9985750356",
            website="website.com",
            address=json.dumps({"city": "Banglore"}),
        )
        # Test model str class
        print(Organization(org).__str__())
        UserOrganizationMap.objects.create(
            user=User.objects.get(first_name="ugesh"),
            organization=Organization.objects.get(org_email="bglordg@digitalgreen.org"),
        )

    def test_participant_post_add_user_valid_email(self):
        """_summary_"""
        # self.monkeypatch.setattr("datahub.views.Organization", MockOrganization)
        # self.monkeypatch.setattr("datahub.views.UserCreateSerializer", MockUserSerializer)
        # self.monkeypatch.setattr("datahub.views.UserOrganizationMapSerializer", UserOrganizationMapSerializerMock)
        response = self.client.post(self.participant_url, valid_data, secure=True)
        assert response.status_code == 201
        assert response.json().get("email") == "ugeshbasa4ss5@digitalgreen.org"

    def test_participant_post_add_user_invalid_fields_asserts(self):
        """_summary_"""
        response = self.client.post(self.participant_url, invalid_role_data, secure=True)
        assert response.status_code == 400
        assert response.json().get("role") == ['Invalid pk "33" - object does not exist.']
        invalid_role_data["email"] = ""
        response = self.client.post(self.participant_url, invalid_role_data, secure=True)
        assert response.status_code == 400
        assert response.json() == {
            "email": ["This field may not be blank."],
            "profile_picture": ["The submitted file is empty."],
            "role": ['Invalid pk "33" - object does not exist.'],
        }

    def test_participant_get_list(self):
        response = self.client.get(self.participant_url, secure=True)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 1
        assert len(data.get("results")) == 1
        assert data.get("results")[0].get("user").get("phone_number") == "9985750356"
        assert (
            data.get("results")[0].get("organization").get("website") == "website.com"
        )

    def test_participant_update_user_details(self):
        id = User.objects.get(first_name="ugesh").id
        update_data["id"] = Organization.objects.get(org_email="bglordg@digitalgreen.org").id
        response = self.client.put(
            self.participant_url + str(id) + "/", update_data, secure=True, content_type="application/json"
        )
        data = response.json()
        assert response.status_code == 201
        assert data.get("user").get("phone_number") == "1234567890"
        assert data.get("user").get("first_name") == "ugeshBasa"

    def test_participant_update_user_details_error(self):
        id = User.objects.get(first_name="ugesh").id
        update_data["id"] = Organization.objects.get(org_email="bglordg@digitalgreen.org").id
        response = self.client.put(
            self.participant_url + str(uuid4()) + "/", update_data, secure=True, content_type="application/json"
        )
        data = response.json()
        assert response.status_code == 404
        assert data == {"detail": "Not found."}

    def test_participant_user_details_after_update(self):
        response = self.client.get(self.participant_url, secure=True)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 1
        assert len(data.get("results")) == 1
        assert data.get("results")[0].get("user").get("first_name") == "ugesh"
        assert (
            data.get("results")[0].get("organization").get("website") == "website.com"
        )

    def test_participant_delete(self):
        id = User.objects.get(first_name="ugesh").id
        response = self.client.delete(self.participant_url + str(id) + "/", secure=True)
        assert response.status_code == 204
        # Testing get after deleteing
        response = self.client.get(self.participant_url, secure=True)
        data = response.json()
        assert data.get("count") == 0
        assert len(data.get("results")) == 0

    def test_participant_get_user_details(self):
        id = User.objects.get(first_name="ugesh").id
        response = self.client.get(self.participant_url + str(id) + "/", secure=True)
        response = self.client.get(self.participant_url, secure=True)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 1

    def test_participant_get_user_details_empty(self):
        url = self.participant_url + str(uuid4()) + "/"
        response = self.client.get(url, secure=True)
        data = response.json()
        print(response)
        print(data)
        assert response.status_code == 200
        assert data == []

    def test_participant_get_list_after_deleate(self):
        id = User.objects.get(first_name="ugesh").id
        response = self.client.delete(self.participant_url + str(id) + "/", secure=True)
        response = self.client.get(self.participant_url, secure=True)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 0

    def test_send_invite(self):
        data = {"to_email": ["ugesh@gmail.com"], "content": "Sample email for participant invitdation"}
        self.monkeypatch.setattr("datahub.views.Utils", MockUtils)
        response = self.client.post(self.send_invite, data, secure=True)
        assert response.json() == {"Message": "Invation sent to the participants"}
        assert response.status_code == 200

    def test_send_invite_error(self):
        data = {"to_email": [], "content": "Sample email for participant invitdation"}
        self.monkeypatch.setattr("datahub.views.Utils", MockUtils)
        response = self.client.post(self.send_invite, data, secure=True)
        assert response.json() == {"message": "Invalid email address"}
        assert response.status_code == 400
