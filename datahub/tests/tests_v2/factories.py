import json, factory, pytest
from faker import Faker
from accounts.models import UserRole, User
from datahub.models import Organization, UserOrganizationMap, DatasetV2, DatasetV2File

fake = Faker()

dataset_file_uploads_valid = [
                                pytest.param(
                                    "Rice Dataset", "file",
                                    ["./datahub/tests/tests_v2/test_data/file_example_JPG_100kB.jpg",
                                     "./datahub/tests/tests_v2/test_data/file_example_XLS_50.xls"],
                                    id="ideal_file_uploads"
                                 ),
                                pytest.param(
                                    "Wheat Dataset", "mysql",
                                    ["./datahub/tests/tests_v2/test_data/file_example_XLS_50.xls"],
                                    id="dataset_test_2"
                                 ),
                                pytest.param(
                                    "Chilly Dataset", "postgresql",
                                    ["./datahub/tests/tests_v2/test_data/file_example_XLS_50.xls"],
                                    id="dataset_test_3"
                                 ),
                                pytest.param(
                                    "Millet Dataset", "file",
                                    ["./datahub/tests/tests_v2/test_data/file_example_XLS_50.xls"],
                                    id="dataset_test_4"
                                 ),

                            ]

dataset_file_uploads_invalid = [
                                    pytest.param(
                                        "", "postgresql",
                                        ["./datahub/tests/tests_v2/test_data/file_example_XLS_50.xls"],
                                        id="missing_dataset_name"
                                     ),
                                    pytest.param(
                                        "Rice Dataset", "",
                                        ["./datahub/tests/tests_v2/test_data/file_example_XLS_50.xls"],
                                        id="missing_source_field"
                                     ),
                                    pytest.param(
                                        "Wheat Dataset", "mysql",
                                        [],
                                        id="missing_files"
                                     ),
                                    pytest.param(
                                        "Rice Dataset", "file",
                                        ["./datahub/tests/tests_v2/test_data/file_example_XML_24kb.xml"],
                                        id="invalid_file_format"
                                     ),
                                    # pytest.param(
                                    #     "Rice Dataset", "file",
                                    #     ["./datahub/tests/tests_v2/test_data/file_example_XML_24kb.xml"],
                                    #     id="invalid_file_size"
                                    #  ),
                                ]

dataset_creation_valid = [
                            pytest.param(
                                "Rice Dataset", fake.text(), fake.json(), fake.city(), fake.date_time(), fake.date_time(), False,
                                id="ideal_dataset_creation"),
                            pytest.param(
                                "Wheat Dataset", "", fake.json(), fake.city(), fake.date_time(), fake.date_time(), False,
                                id="without_description"),
                            pytest.param(
                                "Chilly Dataset", fake.text(), fake.json(), "", fake.date_time(), fake.date_time(), False,
                                id="no_geography_selected"),
                            pytest.param(
                                "Millet Dataset", fake.text(), fake.json(), fake.city(), "", "", True,
                                id="selected_constantly_update"),
                         ]

dataset_creation_invalid = [
                            pytest.param(
                                "", None, fake.text(), fake.json(), [], fake.date_time(), fake.date_time(), False,
                                id="missing_dataset_name"),
                            pytest.param(
                                "Rice Dataset", None, fake.text(max_nb_chars=600), fake.json(), fake.city(), fake.date_time(), fake.date_time(), False,
                                id="exceeded_description_length"),
                            pytest.param(
                                "Rice Dataset", None, fake.text(), [], fake.city(), fake.date_time(), fake.date_time(), False,
                                id="missing_category"),
                            pytest.param(
                                "Rice Dataset", None, fake.text(),
                                {
                                    "\nResearch Data": ["\nPesticides"],
                                    "\nAgriculture Data": ["\nHorticulture", "\nMonoculture"]
                                },
                                fake.city(), fake.date_time(), fake.date_time(), False,
                                id="invalid_category_json"),
                            pytest.param(
                                "Rice Dataset", None, fake.text(), fake.json(), fake.city(), "1991-08-0422n$%", fake.date_time(), False,
                                id="invalid_datetime"),
                            pytest.param(
                                "Rice Dataset", "ceddb196-166c-4530-b98b-f5e19382aa1c", fake.text(), fake.json(), fake.city(), fake.date_time(), fake.date_time(), False,
                                id="invalid_user_map_id"),
                         ]


class UserRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRole

    id = 3
    # id = fake.unique.random_int()
    role_name = 'datahub_participant_root'
    # id = factory.Sequence(lambda n: n)
    # role_name = factory.sequence(lambda n: n)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    # id = fake.unique.uuid4()
    first_name = fake.first_name()
    email = fake.unique.free_email()
    role = factory.SubFactory(UserRoleFactory)


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    id = factory.Sequence(lambda n: n)
    # id = fake.unique.uuid4()
    name = fake.company()
    org_email = fake.unique.company_email()
    address = json.dumps({"city": "Banglore"}),
    org_description = fake.text()
    website = fake.domain_name()
    phone_number = fake.phone_number()
    logo = fake.file_path(depth=3, category='image')


class UserMapFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserOrganizationMap

    id = factory.Sequence(lambda n: n)
    # id = fake.unique.uuid4()
    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)


class DatasetV2Factory(factory.django.DjangoModelFactory):
    class Meta:
        model = DatasetV2

    id = factory.Sequence(lambda n: n)
    # id = fake.unique.uuid4()
    name = fake.name()
    user_map = factory.SubFactory(UserMapFactory)
    category = {
                    "Research Data": ["Pesticides"],
                    "Agriculture Data": ["Horticulture", "Monoculture"]
                }
    description = fake.text()
    geography = fake.city()
    data_capture_start = fake.date_time()
    data_capture_end = fake.date_time()

