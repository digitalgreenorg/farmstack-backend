from uuid import uuid4
from rest_framework.reverse import reverse
from django.test import Client, TestCase
from rest_framework import status
import json
from datahub.models import  Organization, UserOrganizationMap
from accounts.models import User, UserRole

organisation_InvalidData = {
    "user_id": "None",
    "org_email": "asdfbg@sdfgh.com",
    "name": "dnjsnjdnksanmckadmcnkdmndnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmghhjhjjhnjnn",
    "website": "https://datahubethdev.farmstack.co/datahub/settings/1",
    "address": {
        "country": "Andorra",
        "pincode": "2345675432",
        "address": "asdfghn",
        "city": ""
    },
    "phone_number": "+91 12345-65432",
    "org_description": "fc"
}

organisation_InvalidData_without_user_id = {
    "user_id": "None",
    "org_email": "asdfbg@sdfgh.com",
    "name": "dnjsnjdnksanmckadmcnkdmndnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmghhjhjjhnjnn",
    "website": "https://datahubethdev.farmstack.co/datahub/settings/1",
    "address": {
        "country": "Andorra",
        "pincode": "2345675432",
        "address": "asdfghn",
        "city": ""
    },
    "phone_number": "+91 12345-65432",
    "org_description": "fc"
}

organisation_validData = {
    "user_id": "None",
    "org_email": "asdfbg@sdfgh.com",
    "name": "Creating User Akshata",
    "website": "https://datahubethdev.farmstack.co/datahub/settings/1",
    "address": "{}",
    "phone_number": "+91 12345-65432",
    "org_description": "description about org "
}

updated_org_data = {
    "org_email": "updatedemail@gmail.com",
    "name": "Updated Name",
    "website": "https://datahubethdev.farmstack.co/datahub/settings/1",
    "address": "{}",
    "phone_number": "+91 7878787878",
    "org_description": "org org org org"
}



class OrganizationTestCaseForViews(TestCase):

    def setUp(self) -> None:
        self.client = Client()
        self.organization_url = reverse("organization-list")
        self.user_role = UserRole.objects.create(
            id="6",
            role_name="datahub_co_steward"
        )
        self.user = User.objects.create(
            email="dummy@gmail.com",
            role_id=self.user_role.id,
        )
        self.user_with_no_org = User.objects.create(
            email="notorg@gmail.com",
            role_id=self.user_role.id,
        )

        self.deleted_user = User.objects.create(
            email="dummy1@gmail.com",
            role_id=self.user_role.id,
            status=False
        )
        self.address = {"street": "4th Main", "city": "Bengaluru", "country": "India", "pincode": "53789"}

        self.creating_org = Organization.objects.create(
            org_email="akshata@dg.org",
            name="digitalgreen",
            phone_number="5678909876",
            website="htttps://google.com",
            address=json.dumps({"city": "Banglore"}),
        )
 
        UserOrganizationMap.objects.create(user_id=self.user.id, organization_id=self.creating_org.id)
        organisation_validData["user_id"] = str(self.user.id)


    def test_create_org_user(self):
        other_user = User.objects.create(
            email="user@gmail.com",
            role_id=self.user_role.id,
        )
        org_to_create = {
            "org_email": "akshata_company@email.com",
            "name": "Creating User Akshata",
            "website": "https://datahubethdev.farmstack.co/datahub/settings/1",
            "address": "{}",
            "phone_number": "+91 65432-12345",
            "org_description": "description about org "
        }
        org_to_create.update({'user_id': str(other_user.id)})
        response = self.client.post(self.organization_url, org_to_create)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert response.json().get("organization").get("name")==org_to_create["name"]

    def test_no_user_org_get(self):
        response = self.client.get(self.organization_url+f"{str(self.user_with_no_org.id)}/")
        assert response.status_code == 200

    def test_no_user_org_update(self):
        org_data = {
            "name": "updated name",
            "org_description": "Organization description ....",
        }
        response = self.client.put(self.organization_url+f"{str(self.user_with_no_org.id)}/", org_data,content_type="application/json")
        assert response.status_code == 404
        assert response.json()=={}

    # Testing Organization POST Method with Invalid Data
    def test_org_post_method_with_invalid_data(self):
        response = self.client.post(self.organization_url, organisation_InvalidData)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert response.json()=={}

    # Testing Organization POST Method with valid Data
    def test_org_post_method_with_valid_data(self):
        response = self.client.post(self.organization_url, organisation_validData)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert response.json() == {'message': ['User is already associated with an organization']}

    # Testing Organization List (GET)
    def test_org_get_data(self):
        response = self.client.get(self.organization_url)
        assert response.status_code == 200
        assert response.json()['results'][0]['organization']['org_email']==self.creating_org.org_email

    # Testing Organization Update data (PUT) with valid data
    def test_org_update_with_valid_data(self):
        org_data = {
            "name": "updated name",
            "org_description": "Organization description ....",
        }
        response_update = self.client.put(self.organization_url + f"{str(self.user.id)}/", org_data,
                                          content_type="application/json")
        self.assertEqual(response_update.status_code, status.HTTP_201_CREATED)
        assert response_update.json().get("organization").get("name") == org_data.get("name")
        assert response_update.json().get("organization").get("org_description") == org_data.get("org_description")

    # Testing Organization Update data (PUT) with Invalid data
    def test_org_update_with_Invalid_data(self):
        updated_org_data = {
            "name": "",
            "org_email": "",
            "address": "",
            "phone_number": "",
            "org_description": "",
            "logo": "",
        }
        response_update = self.client.put(self.organization_url + f"{str(self.user.id)}/", updated_org_data,
                                          content_type="application/json")
        self.assertEqual(response_update.status_code, status.HTTP_400_BAD_REQUEST)
        assert response_update.json() == {'org_email': ['This field may not be blank.'],
                                          'name': ['This field may not be blank.'],
                                          'logo': ['The submitted data was not a file. Check the encoding type on the form.']}
        updated_another_data = {
            "name": "Akshata Naik",
            "org_email": "gvhbgjhnk",
            "website": "fjndjnjd",
            "address": "jnj",
            "phone_number": "jnjn",
            "org_description": "",
            "logo": "nkmk",
        }
        response_update = self.client.put(self.organization_url + f"{str(self.user.id)}/", updated_another_data,
                                          content_type="application/json")
        self.assertEqual(response_update.status_code, status.HTTP_400_BAD_REQUEST)
        assert response_update.json() == {'org_email': ['Enter a valid email address.'],
                                          'logo': ['The submitted data was not a file. Check the encoding type on the form.']}
        response_update = self.client.put(self.organization_url + f"{str(self.user.id)}/", organisation_InvalidData,
                                          content_type="application/json")
        self.assertEqual(response_update.status_code, status.HTTP_400_BAD_REQUEST)
        assert response_update.json() == {'name': ['Ensure this field has no more than 255 characters.']}

    # Testing Organization DELETE Method
    def test_delete_org_user(self):
        response = self.client.delete(self.organization_url + f"{str(self.user.id)}/")
        response = self.client.get(self.organization_url)
        assert response.status_code == 200
        assert response.json().get("count") == 0

    # Testing Organization GET Method (single)
    def test_get_single_org_user(self):
        response = self.client.get(self.organization_url + f"{str(self.user.id)}/")
        assert response.status_code == 200
        assert response.json().get("organization").get("name") == "digitalgreen"
