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







##########################
# import uuid
# from django.test import Client, TestCase
import json
from turtle import st
from django.urls import reverse
from datahub.models import StandardisationTemplate
from rest_framework.test import APIClient, APITestCase
from rest_framework import status



class TestViews(APITestCase):
    
    # Create your tests here.
    def setUp(self) -> None:
        self.client = APIClient()
        self.datahub_stardardise_url = reverse("standardise-list")
        datapoint_attributes_data = {
                    "data_attribute1": "",
                    "data_attribute2": ""
                }
        StandardisationTemplate.objects.create(
            datapoint_category= "farmers info",
            datapoint_description= "farmer details is here",
            datapoint_attributes= datapoint_attributes_data
            )
        # print("***set up****", StandardisationTemplate.objects.get(datapoint_category="farmers info").id)
    
    #test case for create method(valid case)        
    def test_stardardise_create_valid(self):
        stardardise_valid_data = [
            {
            "datapoint_category": "farmers",
            "datapoint_description": "farmer details is here"
        }]
        response = self.client.post(self.datahub_stardardise_url, json.dumps(stardardise_valid_data), content_type="application/json",secure=True)
        data = response.json()
        # print("***test_stardardise_create_valid data***", data[0])
        # print("***test_stardardise_create_valid status_code***", response.status_code)
        assert response.status_code == 201
        assert data[0]['datapoint_category'] == stardardise_valid_data[0]["datapoint_category"]
        
    #test case for create method(invalid case)        
    def test_stardardise_create_invalid_length_category(self):
        datapoint_attributes_data = {
                    "data_attribute1": "",
                    "data_attribute2": ""
                }
        datapoint_category_invalid_data = [{
                "datapoint_category": "farmersinfonvefjhfjhfjfjfjhfjffffffiurnnnfurrfmnjfnfrd",
                "datapoint_description": "farmer details is here",
                "datapoint_attributes": datapoint_attributes_data
        }]
        response = self.client.post(self.datahub_stardardise_url, json.dumps(datapoint_category_invalid_data), content_type="application/json", secure=True)
        data = response.json()
        # print("***test_stardardise_create_invalid***", data[0]['datapoint_category'])
        # print("***test_stardardise_create_invalid***", response.status_code)
        assert response.status_code == 400
        assert data[0]['datapoint_category'] == ['Ensure this field has no more than 50 characters.']
        
    #test case for create method(invalid case)  
    def test_stardardise_create_invalid_length_description(self):
        datapoint_attributes_data = {
                    "data_attribute1": "",
                    "data_attribute2": ""
                }
        datapoint_category_invalid_data = [{
                "datapoint_category": "farmers",
                "datapoint_description": "dnjsnjdnksanmckadmcnkdmndnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckmnckdmclakdscamdnjsnjdnksanmckadmcnkdmnckm",
                "datapoint_attributes": datapoint_attributes_data
        }]
        response = self.client.post(self.datahub_stardardise_url, json.dumps(datapoint_category_invalid_data), content_type="application/json", secure=True)
        data = response.json()
        # print("***test_stardardise_create_invalid***", data[0]['datapoint_description'])
        # print("***test_stardardise_create_invalid***", response.status_code)
        assert response.status_code == 400
        assert data[0]['datapoint_description'] == ['Ensure this field has no more than 255 characters.']
        
    #test case for list method(valid case) 
    def test_stardardise_retrieve_valid(self):
        response = self.client.get(self.datahub_stardardise_url)
        data = response.json()
        # print("***test_stardardise_retrieve_valid data***", data)
        # print("***test_stardardise_retrieve_valid status_code***", response.status_code)
        assert response.status_code == 200
        assert data[0]['datapoint_category'] == 'farmers info'

        
    # def test_stardardise_update_valid(self):
    #     user_update_data = {'first_name': 'kanhaiya updated'}
    #     response = self.client.get(self.datahub_stardardise_url)
    #     data = response.json()
        # print("***test_user_update_valid***", data)
        # print("***test_user_update_valid***", response.status_code)
        # assert response.status_code == 201
        # assert data['response']['first_name'] == "kanhaiya updated"
        # assert data['message'] == "updated user details"
        
    # def test_user_update_invalid(self):
    #     user_update_invalid_data = {
    #         'email': 'kanhaiya_updated_invalid@digitalgreen.org'
    #     }
    #     user_id = User.objects.get(email="kanhaiyaaa@digitalgreen.org").id
    #     response = self.client.put(self.account_register_url+f"{user_id}/", user_update_invalid_data, secure=True)
    #     data = response.json()
    #     # print("***test_user_update_valid***", data)
    #     # print("***test_user_update_valid***", response.status_code)
    #     assert response.status_code == 201
    #     assert data['response'].get("email", '') == ''
        
    #test case for destroy method(valid case) 
    def test_stardardise_delete_valid_category(self):
        category_id =StandardisationTemplate.objects.get(datapoint_category="farmers info").id
        response = self.client.delete(self.datahub_stardardise_url+f"{category_id}/")
        # print("***test_stardardise_delete_valid_category***", response)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        
    # def test_user_delete_invalid(self):
    #     random_uuid = uuid.uuid4()
    #     response = self.client.delete(self.account_register_url+f"{random_uuid}/")
    #     data = response.json()
    #     # print("***test_user_delete_invalid***", data)
    #     assert response.status_code == 404
    #     assert data == {'detail': 'Not found.'}
        
    