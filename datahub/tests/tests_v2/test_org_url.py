from django.test import SimpleTestCase
from django.urls import resolve, reverse
from datahub.views import OrganizationViewSet


class TestUrls(SimpleTestCase):
    def test_org_Invalid(self):
        url = reverse('organization-list')
        self.assertNotEqual(resolve(url).func, OrganizationViewSet)

    def test_org_valid_func(self):
        url = reverse("organization-list")
        assert resolve(url)._func_path == "datahub.views.OrganizationViewSet"
