from django.test import SimpleTestCase
from django.urls import resolve, reverse
from microsite.views import PolicyAPIView
from participant.views import SupportTicketV2ModelViewSet



class SupportTicketsTestCaseForUrls(SimpleTestCase):
    
    def test_support_tickets_with_Invalid_fun(self):
        url = reverse('support_tickets-list')
        resolved_func_path = resolve(url)._func_path
        expected_func_path = "microsite.views.ParticipantMicrositeViewSet"
        assert resolved_func_path!= expected_func_path

    def test_support_tickets_with_valid_func(self):
        url = reverse("support_tickets-list")
        assert resolve(url)._func_path == "participant.views.SupportTicketV2ModelViewSet"