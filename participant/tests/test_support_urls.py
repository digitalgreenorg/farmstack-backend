from participant.views import SupportTicketV2ModelViewSet, SupportTicketResolutionsViewset
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class TestUrls(SimpleTestCase):
    def test_support_ticket_valid(self):
        """_summary_"""
        url = reverse("support_tickets-list")
        print(resolve(url)._func_path) # type: ignore
        assert resolve(url)._func_path == "participant.views.SupportTicketV2ModelViewSet" # type: ignore

    def test_support_ticket_invalid(self):
        """_summary_"""
        url = reverse("support_tickets-list")
        # print(resolve(url))
        self.assertNotEqual(resolve(url).func, "SupportTicketV2ModelViewSet")
        
    def test_support_resolution_valid(self):
        """_summary_"""
        url = reverse("support_tickets_resolutions-list")
        print(resolve(url)._func_path) # type: ignore
        assert resolve(url)._func_path == "participant.views.SupportTicketResolutionsViewset" # type: ignore

    def test_support_resolution_invalid(self):
        """_summary_"""
        url = reverse("support_tickets_resolutions-list")
        # print(resolve(url))
        self.assertNotEqual(resolve(url).func, "SupportTicketResolutionsViewset")
