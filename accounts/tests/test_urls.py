from django.test import SimpleTestCase
from django.urls import resolve, reverse
from accounts.views import RegisterViewset

class TestUrls(SimpleTestCase):
    def test_org_invalid(self):
        url = reverse('register-list')
        self.assertNotEqual(resolve(url).func, RegisterViewset)

    def test_org_valid_func(self):
        url = reverse("register-list")
        assert resolve(url)._func_path == "accounts.views.RegisterViewset" # type: ignore