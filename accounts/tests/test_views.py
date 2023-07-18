import uuid
from django.test import Client, TestCase
from django.urls import reverse
from accounts.models import User, UserRole
from rest_framework.test import APIClient, APITestCase

class TestViews(APITestCase):
    # Create your tests here.
    def setUp(self) -> None:
        self.client = APIClient()
        self.account_register_url = reverse("register-list")
        UserRole.objects.create(id = 1, role_name="datahub_admin")
        
        User.objects.create(
            email="kanhaiyaaa@digitalgreen.org",
            first_name="kanhaiya",
            last_name="suthar",
            role= UserRole.objects.get(id=1),
            phone_number="+91 99876-62188"
        )
    
    def test_user_create_valid(self):
        user_valid_data = {
            "email" : "ektakm@digitalgreen.org",
            "first_name": "ekta",
            "last_name": "kumari",
            "role": UserRole.objects.get(role_name="datahub_admin").id,
            "phone_number": "+91 98204-62188"
        }
        response = self.client.post(self.account_register_url, data=user_valid_data, secure=True)
        data = response.json()
        # print("***test_user_create_valid***", data)
        # print("***test_user_create_valid***", response.status_code)
        assert response.status_code == 201
        assert data['message'] == 'Successfully created the account!'
        assert data['response']['last_name'] == user_valid_data.get("last_name")
    
    def test_user_create_invalid(self):
        user_invalid_data = {
            "email" : "ektakumarii",
            "first_name": "ekta",
            "last_name": "kumari",
            "role": UserRole.objects.get(role_name="datahub_admin").id,
            "phone_number": "+91 98204-62188"
        }
        response = self.client.post(self.account_register_url, data=user_invalid_data, secure=True)
        data = response.json()
        # print("***test_user_create_invalid***", data)
        # print("***test_user_create_invalid***", response.status_code)
        assert response.status_code == 400
        assert data == {"email": ['Enter a valid email address.']}
        
        
    def test_user_retrieve_valid(self):
        user_id = User.objects.get(email="kanhaiyaaa@digitalgreen.org").id
        response = self.client.get(self.account_register_url+f"{user_id}/", secure=True)
        data = response.json()
        assert response.status_code == 200
        # print("***test_user_retrieve_valid***", data)
        # print("***test_user_retrieve_valid***", response.status_code)
        assert data['id'] == str(user_id)
        assert data['email'] == 'kanhaiyaaa@digitalgreen.org'

    def test_user_retrieve_invalid(self):
        random_uuid = uuid.uuid4()
        response = self.client.get(self.account_register_url+f"{random_uuid}/", secure=True)
        data = response.json()
        # print("***test_user_retrieve_invalid***", data)
        # print("***test_user_retrieve_invalid***", response.status_code)
        assert response.status_code == 404
        assert data == {'detail': 'Not found.'}
        
    def test_user_update_valid(self):
        user_update_data = {'first_name': 'kanhaiya updated'}
        user_id = User.objects.get(email="kanhaiyaaa@digitalgreen.org").id
        response = self.client.put(self.account_register_url+f"{user_id}/", user_update_data , secure=True)
        data = response.json()
        # print("***test_user_update_valid***", data)
        # print("***test_user_update_valid***", response.status_code)
        assert response.status_code == 201
        assert data['response']['first_name'] == "kanhaiya updated"
        assert data['message'] == "updated user details"
        
    def test_user_update_invalid(self):
        user_update_invalid_data = {
            'email': 'kanhaiya_updated_invalid@digitalgreen.org'
        }
        user_id = User.objects.get(email="kanhaiyaaa@digitalgreen.org").id
        response = self.client.put(self.account_register_url+f"{user_id}/", user_update_invalid_data, secure=True)
        data = response.json()
        # print("***test_user_update_valid***", data)
        # print("***test_user_update_valid***", response.status_code)
        assert response.status_code == 201
        assert data['response'].get("email", '') == ''
        
    def test_user_delete_valid(self):
        user_id = str(User.objects.get(email="kanhaiyaaa@digitalgreen.org").id)
        response = self.client.delete(self.account_register_url+f"{user_id}/", secure=True)
        # print("***test_user_delete_valid***", response)
        assert response.status_code == 204
        
    def test_user_delete_invalid(self):
        random_uuid = uuid.uuid4()
        response = self.client.delete(self.account_register_url+f"{random_uuid}/")
        data = response.json()
        # print("***test_user_delete_invalid***", data)
        assert response.status_code == 404
        assert data == {'detail': 'Not found.'}
        