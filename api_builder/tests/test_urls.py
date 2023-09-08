from django.test import TestCase
from django.urls import reverse, resolve
from api_builder import views

class APITestUrls(TestCase):
    def test_create_api_url(self):
        """
        Test that the 'create_api' URL resolves to the CreateAPIView view.
        """
        url = reverse("create_api")
        self.assertEqual(resolve(url).func.view_class, views.CreateAPIView)

    def test_api_with_data_url(self):
        """
        Test that the 'api-with-data' URL with arguments 'user_id' and 'endpoint_name'
        resolves to the APIViewWithData view.
        """
        url = reverse("api-with-data", args=["user_id", "endpoint_name"])
        self.assertEqual(resolve(url).func.view_class, views.APIViewWithData)

    def test_list_user_apis_url(self):
        """
        Test that the 'list-user-apis' URL resolves to the ListUserAPIsView view.
        """
        url = reverse("list-user-apis")
        self.assertEqual(resolve(url).func.view_class, views.ListUserAPIsView)
