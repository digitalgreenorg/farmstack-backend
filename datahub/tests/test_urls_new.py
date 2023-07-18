from django.test import SimpleTestCase
from django.urls import resolve, reverse
from datahub.views import StandardisationTemplateView

class TestUrls(SimpleTestCase):
    # def test_org_invalid(self):
    #     url = reverse('STANDARDISE-list')
    #     self.assertNotEqual(resolve(url).func, StandardisationTemplateView)

    # def test_org_valid_func(self):
    #     url = reverse("STANDARDISE-list")
    #     assert resolve(url)._func_path == "datahub.views.StandardisationTemplateView" # type: ignore
        
    def test_standardise_create_valid(self):
        url = reverse("stardardise-list")

        print(resolve(url))
        print(resolve(url)._func_path) # type: ignore
        assert resolve(url)._func_path == "datahub.views.StandardisationTemplateView" # type: ignore
