import os
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserRole
from api_builder.models import API
from rest_framework import status
from datahub.models import DatasetV2, DatasetV2File, Organization, UserOrganizationMap
from participant.tests.test_util import TestUtils
from django.core.files.uploadedfile import SimpleUploadedFile

datasets_dump_data = {
    "name": "dump_datasets3",
    "description": "dataset description",
    "geography": "tpt",
    "constantly_update": False,
}
auth = {"token": "null"}
auth_co_steward = {"token": "null"}
auth_participant = {"token": "null"}

class APITestViews(TestCase):
    """
    Test cases for the views in the 'api_builder' app.
    """

    @classmethod
    def setUpClass(self):
        """
        Set up test data and initialize the test client.
        """
        super().setUpClass()
        self.client_admin = Client()
        self.admin_role = UserRole.objects.create(id="3", role_name="datahub_admin")
        self.admin_user = User.objects.create(
            email="sahajpreets12@gmail.com",
            role_id=self.admin_role.id,
        )
        self.admin_org = Organization.objects.create(
            org_email="sahajpreets12@gmail.com",
            name="admin org",
            phone_number="+91 83602-11483",
            website="htttps://google.com",
            address=({"city": "Banglore"}),
        )
        self.admin_map = UserOrganizationMap.objects.create(
            user_id=self.admin_user.id,
            organization_id=self.admin_org.id,
        )
        self.dataset = DatasetV2.objects.create(user_map=self.admin_map, **datasets_dump_data)
        self.dataset_id = self.dataset.id
        with open("api_builder/tests/test_data/File.csv", "rb") as file:
            file_obj = file.read()
        file = SimpleUploadedFile("File.csv", file_obj)
        self.dataset_file = DatasetV2File.objects.create(file=file, dataset=self.dataset, standardised_file=file)
        auth["token"] = TestUtils.create_token_for_user(self.admin_user, self.admin_map)
        admin_header = self.set_auth_headers(self)  # type:ignore
        self.client_admin.defaults["HTTP_AUTHORIZATION"] = admin_header[0]
        self.client_admin.defaults["CONTENT_TYPE"] = admin_header[1]

    def set_auth_headers(self):
        """
        Set the authentication headers for API requests.
        """
        headers = {"Content-Type": "application/json", "Authorization": f'Bearer {auth["token"]}'}
        return headers["Authorization"], headers["Content-Type"]

    def test_create_api_view(self):
        """
        Test the 'create_api' view.
        """
        api_data = {
            "endpoint": "test_endpoint",
            "dataset_file_id": self.dataset_file.id,
            "selected_columns": '["Period", "Data_value"]',
        }
        response = self.client_admin.post(reverse("create_api"), api_data, format="json")
        data = response.json()
        print(data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(API.objects.filter(endpoint=data["api"]["endpoint"]).exists())

    def test_list_user_apis_view(self):
        """
        Test the 'list-user-apis' view.
        """
        api = API.objects.create(
            dataset_file=self.dataset_file,
            endpoint=f"/api/{self.admin_user.id}/test_endpoint",
            selected_columns=["Period", "Data_value"],
            access_key="test_key",
        )

        self.client_admin.force_login(self.admin_user)
        response = self.client_admin.get(reverse("list-user-apis"), format="json")
        data = response.json()
        print(data, API.objects.all()[0].endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data["apis"]), 1)
        self.assertEqual(data["apis"][0]["endpoint"], api.endpoint)

    def test_access_api_with_valid_key(self):
        """
        Test accessing an API with a valid access key.
        """
        api = API.objects.create(
            dataset_file=self.dataset_file,
            endpoint=f"/api/{self.admin_user.id}/test_endpoint",
            selected_columns=["Period", "Data_value"],
            access_key="test_key",
        )
        response = self.client_admin.get(
            reverse("api-with-data", args=[str(self.admin_user.id), "test_endpoint"]),
            format="json",
            HTTP_AUTHORIZATION=f"{api.access_key}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_access_api_with_invalid_key(self):
        """
        Test accessing an API with an invalid access key.
        """
        api = API.objects.create(
            dataset_file=self.dataset_file,
            endpoint=f"/api/{self.admin_user.id}/test_endpoint",
            selected_columns=["Period", "Data_value"],
            access_key="test_key",
        )

        response = self.client.get(
            reverse("api-with-data", args=[str(self.admin_user.id), "test_endpoint"]),
            format="json",
            HTTP_AUTHORIZATION="invalid_key",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @classmethod
    def tearDownClass(cls):
        """
        Clean up resources and database records after running the tests.
        """
        for dataset_file in DatasetV2File.objects.all():
            file_path = os.path.join(settings.MEDIA_ROOT, str(dataset_file.file))
            standardised_file_path = os.path.join(settings.MEDIA_ROOT, str(dataset_file.standardised_file))
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(standardised_file_path):
                os.remove(standardised_file_path)
        super(APITestViews, cls).tearDownClass()
