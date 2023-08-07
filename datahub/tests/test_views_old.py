import binascii
import json
import os
from calendar import c
from urllib import response
from uuid import uuid4

import pytest
from _pytest.monkeypatch import MonkeyPatch
from django.db import models
from django.shortcuts import render
from django.test import Client, TestCase
from django.test.client import encode_multipart
from requests import request
from requests_toolbelt.multipart.encoder import MultipartEncoder
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User, UserRole
from conftest import postgres_test_container
from datahub.models import Datasets, Organization, Policy, UserOrganizationMap
from datahub.views import ParticipantViewSet

# from django.urls import reverse
from participant.models import Connectors, Department, Project, SupportTicket

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
    # "profile_picture": open("datahub/tests/test_data/pro.png", "rb"),
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
    "address": json.dumps({"address": "Banglore", "country": "India", "pincode": "501011"}),
    # "profile_picture": open("datahub/tests/test_data/pro.png", "rb"),
    "subscription": "aaaa",
}


class MockUtils:
    def send_email(self, to_email: list, content=None, subject=None):
        if to_email == []:
            return Response({"message": "Invalid email address"}, 400)
        else:
            return Response({"Message": "Invation sent to the participants"}, status=200)

ticket_valid_data = {
    "subject": "Not Able to Install",
    "issue_message": "Issue description",
    "issue_attachments": open("datahub/tests/test_data/pro.png", "rb"),
    "status": "open",
    "category": "connectors",
}
ticket_dump_data = {
    "subject": "Not Able to Install",
    "issue_message": "Issue description",
    "status": "open",
    "category": "connectors",
}
ticket_invalid_data = {
    "issue_message": "Issue description",
    "issue_attachments": open("datahub/tests/test_data/pro.png", "rb"),
}
ticket_update_data = {
    "subject": "Not Able to Install",
    "issue_message": "Issue description",
    "status": "closed",
    "category": "connectors",
    "solution_message": "Issue description",
}

datasets_valid_data = {
    "name": "chilli datasets",
    "description": "description",
    "category": "soil_data",
    "geography": "tpt",
    "crop_detail": "chilli",
    "constantly_update": False,
    "age_of_date": "3",
    "dataset_size": "155K",
    "connector_availability": "available",
    # "sample_dataset": open("datasets/tests/test_data/pro.csv", "rb"),
}
datasets_dump_data = {
    "name": "dump datasets",
    "description": "dump description",
    "category": "soil_data",
    "geography": "tpt",
    "crop_detail": "chilli",
    "constantly_update": False,
    "age_of_date": "3",
    "dataset_size": "155K",
    "connector_availability": "available",
    # "sample_dataset": open("datasets/tests/test_data/pro.csv", "rb"),
}
datasets_invalid_data = {
    "constantly_update": False,
    "age_of_date": "3",
    "dataset_size": "155K",
    "connector_availability": "available",
    # "sample_dataset": open("datasets/tests/test_data/pro.csv", "rb"),
}
datasets_update_data = {
    "geography": "bglor",
    "crop_detail": "green chilli",
    "constantly_update": False,
    "age_of_date": "12",
    "dataset_size": "255k",
}

##############################################################################################################################################################################################################
auth = {
    "token": "null"
}





policy_valid_data = {
    "name": "Some Policy Name",
    "description": "Some Policy Description"
}

policy_incomplete_data_no_description = {
    "name": "Some Policy Name",
    # "description": "Some Policy Description"
}

policy_incomplete_data_no_name = {
    # "name": "Some Policy Name",
    "description": "Some Policy Description"
}

policy_update_valid_data_update_name_only = {
    "name": "New Updated Policy Name",
}

policy_update_valid_data_update_description_only = {
    "description": "Some New Policy Description"
}

valid_data_for_categories = {
    "some_key": "some_value",
    "some_key_array": "[]"
}


class CategoriesTestCaseView(APITestCase):
    def setUp(self) -> None:
        super().setUpClass()
        # cls.client = Client()
        self.categories_url = reverse("dataset/v2-list")
        user_role = UserRole.objects.create(
            id="1",
            role_name="datahub_admin"
        )

        user_role_lower = UserRole.objects.create(
            id="6",
            role_name="datahub_co_steward"
        )

        user = User.objects.create(
            email="chandani@gmail.com",
            role_id=user_role.id,
        )

        unauthorized_user = User.objects.create(
            email="chandan_invalid@gmail.com",
            role_id=user_role_lower.id,
        )

        organization = Organization.objects.create(
            name="Some Organization",
            org_email="org@gmail.com",
            address="{}",
        )

        user_map = UserOrganizationMap.objects.create(
            user_id=user.id,
            organization_id=organization.id
        )

        policy = Policy.objects.create(
            name="Some Random Policy",
            description="Some Random Description",
            file=None,
        )

        refresh = RefreshToken.for_user(user)
        refresh["org_id"] = str(user_map.organization_id) if user_map else None
        refresh["map_id"] = str(user_map.id) if user_map else None
        refresh["role"] = str(user.role_id)
        refresh["onboarded_by"] = str(user.on_boarded_by_id)

        refresh.access_token["org_id"] = str(user_map.organization_id) if user_map else None
        refresh.access_token["map_id"] = str(user_map.id) if user_map else None
        refresh.access_token["role"] = str(user.role_id)
        refresh.access_token["onboarded_by"] = str(user.on_boarded_by_id)
        auth["token"] = refresh.access_token

        self.client = Client()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth["token"]}'
        }
        self.client.defaults['HTTP_AUTHORIZATION'] = headers['Authorization']
        self.client.defaults['CONTENT_TYPE'] = headers['Content-Type']
        self.policy_id = policy.id

    def test_get_categories_data(self):
        api_response = self.client.get(f"{self.categories_url}category/", secure=True,
                                       content_type='application/json')
        if api_response.status_code in [404]:
            assert api_response.json().get("detail") == 'Categories not found'
        elif api_response.status_code in [200]:
            assert type(api_response.json()) == dict
            assert len(api_response.json()) > 0

    def test_post_categories_data(self):
        api_response = self.client.post(f"{self.categories_url}category/", valid_data_for_categories, secure=True,
                                        content_type='application/json')

        assert api_response.status_code in [201]


class ParticipantCostewardsListingTestViews(APITestCase):
    
    @pytest.mark.django_db
    def setUp(self) -> None:
        self.client = Client()
        self.participant_url = reverse("participant-list")

        user_role_admin = UserRole.objects.create(
            id="1",
            role_name="datahub_admin"
        )

        user_role_participant = UserRole.objects.create(
            id="3",
            role_name="datahub_participant_root"
        )

        user_role_co_steward = UserRole.objects.create(
            id="6",
            role_name="datahub_co_steward"
        )

        user = User.objects.create(
            first_name="SYSTEM",
            last_name="ADMIN",
            email="admin@gmail.com",
            role_id=user_role_admin.id,
        )

        organization = Organization.objects.create(
            name="Some Organization",
            org_email="org@gmail.com",
            address="{}",
        )

        user_map = UserOrganizationMap.objects.create(
            user_id=user.id,
            organization_id=organization.id
        )

        self.costewards = 10
        for item in range(0, self.costewards):
            self.co_steward = User.objects.create(
                first_name="Costeward",
                last_name=f"Number{item}",
                email=f"csteward{item}@gmail.com",
                role_id=user_role_co_steward.id,
                on_boarded_by_id=user.id
            )

            co_steward_user_map = UserOrganizationMap.objects.create(
                user_id=self.co_steward.id,
                organization_id=organization.id
            )

        self.participants = 10
        for item in range(0, self.participants):
            self.participant = User.objects.create(
                first_name="Participant",
                last_name=f"Number{item}",
                email=f"Participant{item}@gmail.com",
                role_id=user_role_participant.id,
                # on_boarded_by_id=user.id
            )

            participant_user_map = UserOrganizationMap.objects.create(
                user_id=self.participant.id,
                organization_id=organization.id
            )

        refresh = RefreshToken.for_user(user)
        refresh["org_id"] = str(user_map.organization_id) if user_map else None
        refresh["map_id"] = str(user_map.id) if user_map else None
        refresh["role"] = str(user.role_id)
        refresh["onboarded_by"] = str(user.on_boarded_by_id)

        refresh.access_token["org_id"] = str(user_map.organization_id) if user_map else None
        refresh.access_token["map_id"] = str(user_map.id) if user_map else None
        refresh.access_token["role"] = str(user.role_id)
        refresh.access_token["onboarded_by"] = str(user.on_boarded_by_id)
        auth["token"] = refresh.access_token

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth["token"]}'
        }

        self.client.defaults['HTTP_AUTHORIZATION'] = headers['Authorization']
        self.client.defaults['CONTENT_TYPE'] = headers['Content-Type']

    @pytest.mark.django_db
    def test_list_co_steward_endpoint(self):
        api_response = self.client.get(f"{self.participant_url}?co_steward=True", secure=True,
                                       content_type='application/json')
        assert api_response.status_code in [200]
        assert api_response.json().get("count") == self.costewards

    @pytest.mark.django_db
    def test_get_co_steward_details_endpoint(self):
        api_response = self.client.get(f"{self.participant_url}{self.co_steward.id}/", secure=True,
                                       content_type='application/json')
        assert api_response.status_code in [200]
        assert str(api_response.json().get("user_id")) == str(self.co_steward.id)

    
    @pytest.mark.django_db
    def test_get_co_steward_details_not_found_endpoint(self):
        api_response = self.client.get(f"{self.participant_url}/582bc65d-4034-4f2d-a19f-4c14d5d69521", secure=True,
                                       content_type='application/json')
        assert api_response.status_code in [404]
    
    @pytest.mark.django_db
    def test_list_participant_endpoint(self):
        api_response = self.client.get(self.participant_url, secure =True, content_type='application/json')
        assert api_response.json().get("count") == self.participants

    
    @pytest.mark.django_db
    def test_get_participant_details_endpoint(self):
        api_response = self.client.get(f"{self.participant_url}{self.participant.id}/", secure=True,
                                       content_type='application/json')
        assert api_response.status_code in [200]
        assert str(api_response.json().get("user_id")) == str(self.participant.id)

    @pytest.mark.django_db
    def test_get_participant_details_not_found_endpoint(self):
        api_response = self.client.get(f"{self.participant_url}/582bc65d-4034-4f2d-a19f-4c14d5d69521/", secure=True,
                                       content_type='application/json')
        assert api_response.status_code in [404]
