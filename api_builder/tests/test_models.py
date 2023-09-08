from django.test import Client, TestCase
from accounts.models import User, UserRole
from api_builder.models import API
from datahub.models import (
    DatasetV2,
    DatasetV2File,
    Organization,
    UserOrganizationMap,
)

datasets_dump_data = {
    "name": "dump_datasets1",
    "description": "dataset description",
    "geography": "tpt",
    "constantly_update": False,
}

class APITestModels(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment for the APITestModels test case.

        This method is called once before any test methods in this class run.
        It creates necessary test objects and clients.
        """
        super().setUpClass()
        cls.user = Client()
        cls.client_admin = Client()
        cls.admin_role = UserRole.objects.create(id="1", role_name="datahub_admin")
        cls.admin_user = User.objects.create(
            email="sp.code2003@gmail.com",
            role_id=cls.admin_role.id,
        )
        cls.admin_org = Organization.objects.create(
            org_email="admin_org@dg.org",
            name="admin org",
            phone_number="+91 83602-11483",
            website="htttps://google.com",
            address=({"city": "Bangalore"}),
        )
        cls.admin_map = UserOrganizationMap.objects.create(
            user_id=cls.admin_user.id,
            organization_id=cls.admin_org.id,
        )
        cls.dataset = DatasetV2.objects.create(user_map=cls.admin_map, **datasets_dump_data)
        cls.dataset_id = cls.dataset.id
        cls.dataset_file = DatasetV2File.objects.create(
            file="api_builder/tests/test_data/File.csv", dataset=cls.dataset
        )

    def test_create_api(self):
        """
        Test the creation of an API object.

        This method creates an API object and asserts that its attributes
        are correctly set.
        """
        api = API.objects.create(
            dataset_file=self.dataset_file,
            endpoint="test_endpoint",
            selected_columns=["column1", "column2"],
            access_key="test_key",
        )
        self.assertEqual(api.endpoint, "test_endpoint")
        self.assertEqual(api.dataset_file, self.dataset_file)
        self.assertEqual(api.access_key, "test_key")

    def test_duplicate_endpoint(self):
        """
        Test the prevention of duplicate endpoint creation.

        This method creates an API object with a duplicate endpoint and
        asserts that it raises an exception.
        """
        API.objects.create(
            dataset_file=self.dataset_file,
            endpoint="test_endpoint",
            selected_columns=["Period", "Data_value"],
            access_key="test_key",
        )
        with self.assertRaises(Exception):
            API.objects.create(
                dataset_file=self.dataset_file,
                endpoint="test_endpoint",
                selected_columns=["Period", "Data_value"],
                access_key="test_key2",
            )
