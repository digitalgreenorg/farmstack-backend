from rest_framework.reverse import reverse
from django.test import Client, TestCase
from rest_framework import status
import json
from datahub.models import  DatasetV2,Organization, UserOrganizationMap,DatasetV2File
from accounts.models import User, UserRole
from connectors.models import Connectors, ConnectorsMap
from participant.tests.test_util import TestUtils
from django.core.files.base import File
from django.core.files.uploadedfile import SimpleUploadedFile


left_datasets_dump_data = {
    "name": "dump_datasets",
    "description": "dataset description",
    "geography": "tpt",
    "constantly_update": False,
}

right_datasets_dump_data = {
    "name": "fhgjhjkkj_datasets",
    "description": "description about data set",
    "geography": "tpt",
    "constantly_update": False,
}

connectors_dump_data={
    'name':"connector one",
    "description":"description about...."
}

connectors_data={
    'name':"Agri connect Hub ",
    "description":"AgriConnect Hub is an innovative and comprehensive platform designed to bridge the gap between farmers and the agricultural ecosystem."
}

auth = {
    "token": "null"
}

auth_co_steward = {
    "token": "null"
}

auth_participant= {
    "token": "null"
}

class TestCasesConnectors(TestCase):

    def setUp(self) -> None:
        self.user=Client()
        self.client_admin = Client()
        self.connectors_url=reverse("connectors-list")

        ################# create user roles #############
        self.admin_role = UserRole.objects.create(
            id="1",
            role_name="datahub_admin"
        )
        self.participant_role = UserRole.objects.create(id=3, role_name="datahub_participant_root")
        self.co_steward_role = UserRole.objects.create(id=6, role_name="datahub_co_steward")

        ############# create users #################
        self.admin = User.objects.create(
            email="akshata@digitalgreen.org",
            role_id=self.admin_role.id,
        )
    
        self.co_steward = User.objects.create(
            email="costeward@digitalgreen.org",
            role_id=self.co_steward_role.id,
          
        )
        self.participant = User.objects.create(
            email="participant@digitalgreen.org",
            role_id=self.participant_role.id,
            
        )

        ############# create organization ###############
        self.admin_org = Organization.objects.create(
            org_email="akshata@dg.org",
            name="Akshata Naik",
            phone_number="5678909876",
            website="htttps://google.com",
            address=json.dumps({"city": "Banglore"}),
        ) 
        self.co_steward_org = Organization.objects.create(
            org_email="costeward@dg.org",
            name="Co steward",
            phone_number="5678909876",
            website="htttps://google.com",
            address=json.dumps({"city": "Banglore"}),
        ) 
        self.participant_org = Organization.objects.create(
            org_email="aman@dg.org",
            name="Aman",
            phone_number="5678909876",
            website="htttps://google.com",
            address=json.dumps({"city": "Banglore"}),
        ) 

        ################# user map #################
        self.admin_map=UserOrganizationMap.objects.create(user_id=self.admin.id, organization_id=self.admin_org.id)
        self.co_steward_map=UserOrganizationMap.objects.create(user_id=self.co_steward.id, organization_id=self.co_steward_org.id)
        self.participant_map=UserOrganizationMap.objects.create(user_id=self.participant.id, organization_id=self.participant_org.id)

        ################ admin token ##################
        auth["token"] = TestUtils.create_token_for_user(self.admin, self.admin_map)
        admin_header=self.set_auth_headers()
        self.client_admin.defaults['HTTP_AUTHORIZATION'] = admin_header[0]
        self.client_admin.defaults['CONTENT_TYPE'] = admin_header[1]

        ########## data set ############
        left_dataset = DatasetV2.objects.create(user_map=self.admin_map, **left_datasets_dump_data)
        right_dataset = DatasetV2.objects.create(user_map=self.admin_map, **right_datasets_dump_data)

        ############# create datasetv2 file
        datasetv2_file_one=DatasetV2File.objects.create(dataset_id=left_dataset.id,)
        with open("connectors/tests/test_files/file.xls", "rb") as file:
            datasetv2_file_one.source="file"
            datasetv2_file_one.save()
            datasetv2_file_one.file.save("name_new_file.xls",File(file))
            datasetv2_file_one.save()

        self.file_one_id = datasetv2_file_one.id
        with open('connectors/tests/test_files/file_example_XLS_10.xls','rb') as file:
            file_obj = file.read()
        file = SimpleUploadedFile("file_example_XLS_10.xls", file_obj)  
        datasetv2_file_two=DatasetV2File.objects.create(dataset_id=right_dataset.id, file=file )
        connector = Connectors.objects.create(user_id=self.admin.id, **connectors_dump_data)
        agri_connector_hub = Connectors.objects.create(user_id=self.admin.id, **connectors_data)
        self.agri_connector_id=agri_connector_hub.id
        connector_map = ConnectorsMap.objects.create(connectors_id=agri_connector_hub.id, left_dataset_file_id=datasetv2_file_one.id, right_dataset_file_id=datasetv2_file_two.id)
        agri_connector_hub_map = ConnectorsMap.objects.create(connectors_id=connector.id, left_dataset_file_id=datasetv2_file_one.id, right_dataset_file_id=datasetv2_file_two.id)
        self.agri_connector_hub_map_id=agri_connector_hub_map.id
    ######### Generic function to return headers #############
    def set_auth_headers(self,participant=False, co_steward=False):  
        auth_data = auth_participant if participant else (auth_co_steward if co_steward else auth)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_data["token"]}'
        }
        return headers['Authorization'],headers['Content-Type']

    ##################### List of connectors #######################
    def test_get_connector_list_valid(self):
        params=f'?user={self.admin.id}&co_steward=false'
        response = self.client_admin.get(self.connectors_url+params)
        assert response.status_code == 200
        assert response.json()['results'][0]['name']==connectors_data['name']
        assert response.json()['results'][0]['description']==connectors_data['description']
        assert response.json()['results'][1]['name']==connectors_dump_data["name"]
        assert response.json()['results'][1]['description']==connectors_dump_data["description"]

    ################## Retrive single connector #####################
    def test_get_single_connectors(self):
        params=f'{self.agri_connector_id}/?user={self.admin.id}&co_steward=false'
        response = self.client_admin.get(self.connectors_url+params)
        response_data = response.json()
        assert response.status_code == 200
        assert response_data['name']==connectors_data['name']
        assert response_data['description']==connectors_data['description']
        left_dataset_name = response_data['maps'][0]['left_dataset_file']['dataset']['name']
        left_dataset_description = response_data['maps'][0]['left_dataset_file']['dataset']['description']
        assert left_dataset_name==left_datasets_dump_data['name']
        assert left_dataset_description==left_datasets_dump_data['description']
        right_dataset_name = response_data['maps'][0]['right_dataset_file']['dataset']['name']
        right_dataset_description = response_data['maps'][0]['right_dataset_file']['dataset']['description']
        assert right_dataset_name==right_datasets_dump_data['name']
        assert right_dataset_description==right_datasets_dump_data["description"]

    #####################  Negative test cases ###############################
    def test_get_connector_list_invalid(self):
        params=f'?user=90908989&co_steward=false'
        data={'i':'jkmkjmkjm'}
        response = self.user.get(self.connectors_url+params,**data )
        assert response.status_code == 401
        assert response.json()=={'message': 'Invalid auth credentials provided.'}


    def test_get_single_connectors_invalid(self):
        params=f'{self.agri_connector_hub_map_id}/?user={self.admin.id}&co_steward=false'
        response = self.client_admin.get(self.connectors_url+params)
        response_data = response.json()
        assert response.status_code == 400
        assert response_data=='No Connectors matches the given query.'