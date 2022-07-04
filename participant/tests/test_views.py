import json
from calendar import c
from unicodedata import category
from urllib import response
from uuid import uuid4

from _pytest.monkeypatch import MonkeyPatch
from accounts.models import User, UserRole
from datahub.models import Organization, UserOrganizationMap
from django.test import Client, TestCase
from django.urls import reverse
from participant.models import SupportTicket
from requests import request
from requests_toolbelt.multipart.encoder import MultipartEncoder
from rest_framework import serializers

valid_data = {
    "subject": "Not Able to Install",
    "issue_message": "Issue description",
    "issue_attachments": open("datahub/tests/test_data/pro.png", "rb"),
    "status": "open",
    "category": "connectors",
}
dump_data = {
    "subject": "Not Able to Install",
    "issue_message": "Issue description",
    "status": "open",
    "category": "connectors",
}
invalid_data = {
    "issue_message": "Issue description",
    "issue_attachments": open("datahub/tests/test_data/pro.png", "rb"),
}
update_data = {
    "subject": "Not Able to Install",
    "issue_message": "Issue description",
    "status": "closed",
    "category": "connectors",
    "solution_message": "Issue description",
}


class TestViews(TestCase):
    """_summary_

    Args:
        TestCase (_type_): _description_
    """

    def setUp(self) -> None:
        self.client = Client()
        self.support_url = reverse("support-list")

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
        user_map = UserOrganizationMap.objects.create(
            user=User.objects.get(first_name="ugesh"),
            organization=Organization.objects.get(org_email="bglordg@digitalgreen.org"),
        )
        self.user_map_id = user_map.id
        sup_ticket = SupportTicket.objects.create(
            **dump_data, user_map=UserOrganizationMap.objects.get(id=user_map.id)
        )
        print(sup_ticket)

    def test_participant_support_invalid(self):
        """_summary_"""
        invalid_data["user_map"] = 4
        response = self.client.post(self.support_url, invalid_data, secure=True)
        assert response.status_code == 400
        assert response.json().get("user_map") == ["“4” is not a valid UUID."]
        assert response.json() == {
            "category": ["This field is required."],
            "subject": ["This field is required."],
            "status": ["This field is required."],
            "user_map": ["“4” is not a valid UUID."],
        }

    def test_participant_support_valid_ticket(self):
        """_summary_"""
        user_id = UserOrganizationMap.objects.get(user_id=User.objects.get(first_name="ugesh").id).id
        valid_data["user_map"] = user_id
        response = self.client.post(self.support_url, valid_data, secure=True)
        assert response.status_code == 201
        assert response.json().get("category") == valid_data.get("category")
        assert response.json().get("status") == valid_data.get("status")

    def test_participant_support_get_list(self):
        user_id = User.objects.get(first_name="ugesh").id
        response = self.client.get(self.support_url, args={"user_id": user_id}, secure=True)
        data = response.json()
        assert response.status_code == 200
        assert data.get("count") == 0
        assert len(data.get("results")) == 0

    def test_participant_support_update_ticket_details(self):

        id = SupportTicket.objects.get(category="connectors").id
        update_data["user_map"] = self.user_map_id
        response = self.client.put(
            self.support_url + str(id) + "/",
            update_data,
            secure=True,
            content_type="application/json",
        )
        data = response.json()
        assert response.status_code == 201
        assert data.get("subject") == update_data.get("subject")
        assert data.get("status") == update_data.get("status")

    def test_participant_update_ticket_error(self):
        response = self.client.put(
            self.support_url + str(uuid4()) + "/",
            update_data,
            secure=True,
            content_type="application/json",
        )
        data = response.json()
        assert response.status_code == 404
        assert data == {"detail": "Not found."}

    def test_participant_user_details_after_update(self):
        response = self.client.get(self.support_url, secure=True)
        data = response.json()
        assert response.status_code == 200
        # assert data.get("count") == 1
        assert len(data.get("results")) == 0
        # assert data.get("results")[0].get("subject") == update_data.get("subject")
        # assert data.get("results")[0].get("status") == update_data.get("status")

    def test_participant_support_details_empty(self):
        url = self.support_url + str(uuid4()) + "/"
        response = self.client.get(url, secure=True)
        data = response.json()
        assert response.status_code == 200
        assert data == []

    def test_participant_support_details(self):
        id = SupportTicket.objects.get(subject="Not Able to Install").id
        url = self.support_url + str(id) + "/"
        response = self.client.get(url, secure=True)
        data = response.json()
        print(data)
        assert response.status_code == 200
        assert data.get("subject") == "Not Able to Install"
        assert data.get("user").get("email") == "ugeshbasa45@digitalgreen.org"
