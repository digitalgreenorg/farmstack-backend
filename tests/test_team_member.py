import json

from accounts.models import User
from django.test import Client, TestCase
from django.urls import reverse

client = Client()


class TeamMemberTestCase(TestCase):
    def setUp(self):
        # url = reverse("team_member-list")
        pass

    def test_create_url(self):

        payload = {"email": "jashwanth@digitalgreen.org", "first_name": "Waseem", "role": 1}
        print(payload)
        # print(reverse("team_member-list"))
        response = client.post(reverse("team_member-list"), json.dumps(payload))
        # response = client.get("http://localhost:8000/datahub/team_member/")

        print(response)

    # def test_print_2(self):
    #     assert True == True
