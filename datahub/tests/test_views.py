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
from requests_toolbelt.multipart.encoder import MultipartEncoder
from rest_framework import serializers
from rest_framework.response import Response


valid_data = {
    "email": "ugeshbasa4ss5@digitalgreen.org",
    "org_email": "bglordg@digitalgreen.org",
    "first_name": "ugesh",
    "last_name": "nani",
    "role": 1,
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
    "role": 1,
    "name": "digitalgreen",
    "phone_number": "9985750356",
    "website": "website.com",
    "address": json.dumps({"city": "Banglore"}),
    "subscription": "aaaa",
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
    "address": json.dumps({"address": "Banglore", "country": "India", "pincode": "501011"}),
    "profile_picture": open("datahub/tests/test_data/pro.png", "rb"),
    "subscription": "aaaa",
}


class MockUtils:
    def send_email(self, to_email: list, content=None, subject=None):
        if to_email == []:
            return Response({"message": "Invalid email address"}, 400)
        else:
            return Response({"Message": "Invation sent to the participants"}, status=200)


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
        Organization.objects.create(
            org_email="bglordg@digitalgreen.org",
            name="digitalgreen",
            phone_number="9985750356",
            website="website.com",
            address=json.dumps({"city": "Banglore"}),
        )
        UserOrganizationMap.objects.create(
            user=User.objects.get(first_name="ugesh"),
            organization=Organization.objects.get(org_email="bglordg@digitalgreen.org"),
        )

    def test_participant_post_add_user_valid_email(self):
        """_summary_"""
        # self.monkeypatch.setattr("datahub.views.Organization", MockOrganization)
        # self.monkeypatch.setattr("datahub.views.UserCreateSerializer", MockUserSerializer)
        # self.monkeypatch.setattr("datahub.views.UserOrganizationMapSerializer", UserOrganizationMapSerializerMock)
        response = self.client.post(self.participant_url, valid_data)
        assert response.status_code == 201
        assert response.json().get("email") == "ugeshbasa4ss5@digitalgreen.org"

    def test_participant_post_add_user_invalid_fields_asserts(self):
        """_summary_"""
        response = self.client.post(self.participant_url, invalid_role_data)
        assert response.status_code == 400
        assert response.json().get("role") == ['Invalid pk "3" - object does not exist.']
        invalid_role_data["email"] = ""
        response = self.client.post(self.participant_url, invalid_role_data)
        assert response.status_code == 400
        assert response.json() == {
            "email": ["This field may not be blank."],
            "profile_picture": ["The submitted file is empty."],
            "role": ['Invalid pk "3" - object does not exist.'],
        }

    def test_participant_get_list(self):
        response = self.client.get(self.participant_url)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 1
        assert len(data.get("results")) == 1
        assert data.get("results")[0].get("user").get("phone_number") == "9985750356"
        assert data.get("results")[0].get("organization").get("website") == "website.com"

    def test_participant_update_user_details(self):
        id = User.objects.get(first_name="ugesh").id
        response = self.client.put(
            self.participant_url + str(id) + "/", data=json.dumps(update_data), content_type="application/json"
        )
        data = response.json()
        assert response.status_code == 201
        assert data.get("phone_number") == "9985750356"
        assert data.get("first_name") == "ugeshBasa"

    def test_participant_user_details_after_update(self):
        response = self.client.get(self.participant_url)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 1
        assert len(data.get("results")) == 1
        assert data.get("results")[0].get("user").get("first_name") == "ugesh"
        assert data.get("results")[0].get("organization").get("website") == "website.com"

    def test_participant_delete(self):
        id = User.objects.get(first_name="ugesh").id
        response = self.client.delete(self.participant_url + str(id) + "/")
        assert response.status_code == 204
        # Testing get after deleteing
        response = self.client.get(self.participant_url)
        data = response.json()
        assert data.get("count") == 0
        assert len(data.get("results")) == 0

    def test_send_invite(self):
        data = {"to_email": ["ugesh@gmail.com"], "content": "Sample email for participant invitdation"}
        self.monkeypatch.setattr("core.utils.Utils", MockUtils)
        response = self.client.post(self.send_invite, data)
        assert response.json() == {"Message": "Invation sent to the participants"}
        assert response.status_code == 200

    def test_send_invite_error(self):
        data = {"to_email": [], "content": "Sample email for participant invitdation"}
        self.monkeypatch.setattr("datahub.views.Utils", MockUtils)
        response = self.client.post(self.send_invite, data)
        assert response.json() == {"message": "Invalid email address"}
        assert response.status_code == 400
