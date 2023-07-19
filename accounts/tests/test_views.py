from django.test import Client, TestCase
from django.urls import reverse
import json

from accounts.models import UserRole, User


# Create your tests here.
def test_user_can_login():
    """User can successfully login"""
    pass


self_register_valid_data = {
    "email": "jai+999@digitalgreen.org",
    "org_email": "jai+999@digitalgreen.org",
    "first_name": "farmstack",
    "last_name": "farmstack",
    "name": "Self Register Organization",
    "phone_number": "+91 87575-73616",
    "website": "https://datahubethdev.farmstack.co/home/https://datahubethdev.farmstack.co/home/register",
    "address": {"address": "https://datahubethdev.farmstack.co/home/register", "country": "India", "pincode": "302020"},
    "on_boarded_by": ""
}

self_register_invalid_org_email = {
    "email": "jai+999@digitalgreen.org",
    "org_email": "jai999digitalgreenorg",
    "first_name": "farmstack",
    "last_name": "farmstack",
    "name": "Self Register Organization",
    "phone_number": "+91 87575-73616",
    "website": "https://datahubethdev.farmstack.co/home/https://datahubethdev.farmstack.co/home/register",
    "address": {"address": "https://datahubethdev.farmstack.co/home/register", "country": "India", "pincode": "302020"},
    "on_boarded_by": ""
}

self_register_invalid_website = {
    "email": "jai+999@digitalgreen.org",
    "org_email": "jai+999@digitalgreen.org",
    "first_name": "farmstack",
    "last_name": "farmstack",
    "name": "Self Register Organization",
    "phone_number": "+91 87575-73616",
    "website": "https//datahubethdevfarmstackco/home/https://datahubethdev.farmstack.co/home/register",
    "address": {"address": "https://datahubethdev.farmstack.co/home/register", "country": "India", "pincode": "302020"},
    "on_boarded_by": ""
}

self_register_invalid_mobile = {
    "email": "jai+999@digitalgreen.org",
    "org_email": "jai+999@digitalgreen.org",
    "first_name": "farmstack",
    "last_name": "farmstack",
    "name": "Self Register Organization",
    "phone_number": "+91 00000-00000",
    "website": "https://datahubethdev.farmstack.co/home/https://datahubethdev.farmstack.co/home/register",
    "address": {"address": "https://datahubethdev.farmstack.co/home/register", "country": "India", "pincode": "302020"},
    "on_boarded_by": ""
}


class SelfRegisterTestViews(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.self_register_url = reverse("self_register-list")
        user_role_admin = UserRole.objects.create(
            id="1",
            role_name="datahub_admin"
        )
        user_role_participant = UserRole.objects.create(
            id="3",
            role_name="datahub_participant_root"
        )

        system_admin = User.objects.create(
            first_name="SYSTEM",
            last_name="ADMIN",
            email="admin@gmail.com",
            role_id=user_role_admin.id,
        )

    def test_self_register_invalid_request_type(self):
        form_data = self_register_valid_data.copy()
        form_data["address"] = json.dumps(form_data["address"])

        api_response = self.client.get(self.self_register_url, data=form_data)
        assert api_response.status_code in [405]
        assert api_response.json().get("detail") == 'Method "GET" not allowed.'

    def test_self_register_valid_data(self):
        form_data = self_register_valid_data.copy()
        form_data["address"] = json.dumps(form_data["address"])

        api_response = self.client.post(self.self_register_url, data=form_data)
        assert api_response.status_code in [201]

    def test_self_register_invalid_org_email(self):
        form_data = self_register_invalid_org_email.copy()
        form_data["address"] = json.dumps(form_data["address"])

        api_response = self.client.post(self.self_register_url, data=form_data)
        assert api_response.status_code in [400]
        assert api_response.json().get("org_email") == ['Enter a valid email address.']

    def test_self_register_invalid_website(self):
        form_data = self_register_invalid_website.copy()
        form_data["address"] = json.dumps(form_data["address"])

        api_response = self.client.post(self.self_register_url, data=form_data)
        assert api_response.status_code in [400]
        assert api_response.json().get("website") == ['Invalid website URL']

    def test_self_register_invalid_phone(self):
        form_data = self_register_invalid_mobile.copy()
        form_data["address"] = json.dumps(form_data["address"])

        api_response = self.client.post(self.self_register_url, data=form_data)
        assert api_response.status_code in [400]
        assert api_response.json().get("phone_number") == ["Invalid phone number format."]
