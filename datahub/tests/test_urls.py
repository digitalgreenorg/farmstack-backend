import imp
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from datahub.views import TeamMemberViewSet

class TestUrls(SimpleTestCase):

    def test_participant_create(self):
        url = reverse("add")
        print(url)
        assert 1 == 3