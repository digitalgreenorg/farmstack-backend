import pytest, os, shutil
from django.core.exceptions import ValidationError
from django.conf import settings
from faker import Factory, Faker

from datahub.models import UserOrganizationMap, DatasetV2
from datahub.tests.tests_v2.factories import UserMapFactory, dataset_file_uploads_valid, dataset_file_uploads_invalid, dataset_creation_valid, dataset_creation_invalid

faker = Factory.create()
fake = Faker()

# class TestDatasetV2Viewsets(TestCase):
#     def setUp(self):
#         self.datasetv2 = DatasetV2Factory()
#         self.url = reverse("dataset/v2-list")
#
#     def test_datasetv2_detailed_view(self):
#         dataset_obj = DatasetV2.objects.last()
#         response = self.client.get(
#                  self.url+str(dataset_obj.id)+"/",
#                 )
#         print("Dataset  obj: ", dataset_obj)
#         print("URL: ", self.url+str(dataset_obj.id)+"/")
#         self.assertEqual(200, response.status_code)


# @pytest.mark.dependency()
@pytest.mark.parametrize(
            "dataset_name, source, datasets", dataset_file_uploads_valid
        )
def test_datasetv2_upload_files_valid(db, client, dataset_name, source, datasets):
    """
    Unit Test case to test uploaded with valid data.
    This test case should be preceded by `test_datasetv2_create_valid` unit test case as
    dataset creation endpoint (`/datahub/dataset/v2/`) is dependent on the file upload endpoint i.e, being tested by this.

    **Endpoint**
        /datahub/dataset/v2/temp_datasets/

    **Assert**
    Test if the endpoint accepts valid data via POST request and returns 201 status code.
        assert `201`
    """
    for file in datasets:
        with open(os.path.join(file), 'rb') as file_content:
            response = client.post(
                     "/datahub/dataset/v2/temp_datasets/",
                     data={
                         "dataset_name": dataset_name,
                         "source": source,
                         "datasets": file_content,
                         },
                     # content_type= "multipart/form-data",
                     format="multipart"
                     )

        assert response.status_code == 201


# @pytest.mark.dependency(depends=['test_datasetv2_upload_files_valid'])
@pytest.mark.parametrize(
        "name, description, category, geography, data_capture_start, data_capture_end, constantly_update",
         dataset_creation_valid                )
def test_datasetv2_create_valid(
        db, client, name, description, category, geography, data_capture_start, data_capture_end, constantly_update
        ):
    """
    Unit Test case to test dataset creation with valid data.
    This test case should be succeeded by `test_datasetv2_upload_files_valid` unit test case as
    dataset creation is dependent on the file upload endpoint (`/datahub/datasets/v2/temp_datasets/`).

    **Endpoint**
        /datahub/dataset/v2/

    **Assert**
    Test if the endpoint accepts valid data via POST request along with storing the dataset files
    uploaded by via the previous endpoint and returns 201 status code.
        assert `201`
    """

    UserMapFactory()
    user_map_obj = UserOrganizationMap.objects.last()

    response = client.post(
            "/datahub/dataset/v2/",
            data={
                "name": name,
                "user_map": str(user_map_obj.id),
                "description": description,
                "category": category,
                "geography": geography,
                "data_capture_start": data_capture_start,
                "data_capture_end": data_capture_end,
                "constantly_update": constantly_update
                }
            )

    datasetv2_obj = DatasetV2.objects.all()
    print("DatasetV2: ", datasetv2_obj)

    # teardown the datasets dir
    directory_created = os.path.join(settings.DATASET_FILES_URL, name)
    if os.path.exists(directory_created):
        shutil.rmtree(directory_created)

    assert response.status_code == 201


@pytest.mark.parametrize(
            "dataset_name, source, datasets", dataset_file_uploads_invalid
        )
def test_datasetv2_upload_files_invalid(db, client, dataset_name, source, datasets):
    """
    Unit Test case for testing invalid data sent through POST request to `/datahub/dataset/v2/temp_datasets/`.

    **Endpoint**
        /datahub/dataset/v2/temp_datasets/

    **Assert**
    Test if the test cases pass to raise ValidationError and results in 400 error status code.
        assert `400`
    """
    response = client.post(
             "/datahub/dataset/v2/temp_datasets/",
             data={
                 "dataset_name": dataset_name,
                 "source": source,
                 "datasets": datasets,
                 },
             # content_type= "multipart/form-data",
             format="multipart"
             )
    print("ERRORS: ", response.data)
    assert response.status_code == 400

@pytest.mark.parametrize(
        "name, user_map, description, category, geography, data_capture_start, data_capture_end, constantly_update", dataset_creation_invalid
        )
def test_datasetv2_create_invalid(
        db, client, name, user_map, description, category, geography, data_capture_start, data_capture_end, constantly_update
        ):
    """
    Unit Test case for testing dataset creation with invalid data sent through POST request to `/datahub/dataset/v2/`.

    **Endpoint**
        /datahub/dataset/v2/

    **Assert**
    Test if the test cases pass to raise ValidationError and results in 400 error status code.
        assert `400`
    """
    if not user_map:
        UserMapFactory()
        user_map = UserOrganizationMap.objects.last().id

    response = client.post(
            "/datahub/dataset/v2/",
            data={
                "name": name,
                "user_map": str(user_map),
                "description": description,
                "category": category,
                "geography": geography,
                "data_capture_start": data_capture_start,
                "data_capture_end": data_capture_end,
                "constantly_update": constantly_update
                }
            )

    # teardown the datasets dir if created any
    directory_created = os.path.join(settings.DATASET_FILES_URL, name)
    if os.path.exists(directory_created):
        shutil.rmtree(directory_created)

    print("ERRORS: ", response.data)
    assert response.status_code == 400

