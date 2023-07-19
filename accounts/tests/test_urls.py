from datahub.views import ParticipantViewSet
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class TestUrls(SimpleTestCase):
    def test_self_register_endpoint_exists(self):
        """_summary_"""
        url = reverse("self_register-list")
        assert resolve(url)._func_path == "accounts.views.SelfRegisterParticipantViewSet"

    def test_self_register_endpoint_does_not_exist(self):
        """_summary_"""
        url = reverse("self_register-list")
        assert resolve(url)._func_path != "SelfRegisterParticipantViewSet"
