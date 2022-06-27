from participant.views import ParticipantSupportViewSet
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class TestUrls(SimpleTestCase):
    def test_participant_support_valid(self):
        """_summary_"""
        url = reverse("support-list")
        assert resolve(url)._func_path == "participant.views.ParticipantSupportViewSet"

    def test_participant_support_invalid(self):
        """_summary_"""
        url = reverse("support-list")
        self.assertNotEqual(resolve(url).func, "ParticipantSupportViewSet")
        