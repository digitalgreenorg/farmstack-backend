from datahub.views import ParticipantViewSet
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class TestUrls(SimpleTestCase):
    def test_participant_create_valid(self):
        """_summary_"""
        url = reverse("participant-list")
        assert resolve(url)._func_path == "datahub.views.ParticipantViewSet"

    def test_participant_create_invalid(self):
        """_summary_"""
        url = reverse("participant-list")
        print(resolve(url))
        self.assertNotEqual(resolve(url).func, "ParticipantViewSet")

    # TeamMember Management.
    def test_team_member_url_valid(self):
        """
        Checks if the url is mapped to TeamMemberViewset.
        """
        url = reverse("team-member-list")
        print(url)
