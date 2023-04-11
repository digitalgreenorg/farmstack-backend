import json
import logging
import os
import re
import shutil

import plazy
from accounts import models
from accounts.models import User, UserRole
from accounts.serializers import (
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
)
from core.constants import Constants
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext as _
from participant.models import Connectors, SupportTicket
from rest_framework import serializers, status
from utils.custom_exceptions import NotFoundException
from utils.file_operations import create_directory, move_directory
from utils.string_functions import check_special_chars
from utils.validators import (
    validate_dataset_size,
    validate_dataset_type,
    validate_document_type,
    validate_file_size,
    validate_image_type,
)

from datahub.models import (
    DatahubDocuments,
    Datasets,
    DatasetV2,
    DatasetV2File,
    Organization,
    StandardisationTemplate,
    UserOrganizationMap,
)

from .models import Policy, UsagePolicy

LOGGER = logging.getLogger(__name__)


class OrganizationRetriveSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        exclude = Constants.EXCLUDE_DATES


class OrganizationSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Organization
        exclude = Constants.EXCLUDE_DATES
        # fields = Constants.ALL


class UserOrganizationCreateSerializer(serializers.Serializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    user = UserSerializer(
        read_only=True,
        allow_null=True,
        required=False,
    )
    organization = OrganizationRetriveSerializer(
        read_only=True,
        allow_null=True,
        required=False,
    )

    # class Meta:
    #     """_summary_"""

    # model = UserOrganizationMap
    # fields = [Constants.ORGANIZATION, Constants.USER]
    # exclude = Constants.EXCLUDE_DATES


class UserOrganizationMapSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = UserOrganizationMap
        fields = Constants.ALL
        # exclude = Constants.EXCLUDE_DATES


class ParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(),
        required=True,
        source=Constants.USER,
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source=Constants.ORGANIZATION,
    )
    user = UserSerializer(
        read_only=False,
        required=False,
    )
    organization = OrganizationRetriveSerializer(
        required=False,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = UserOrganizationMap
        exclude = Constants.EXCLUDE_DATES

    dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
    connector_count = serializers.SerializerMethodField(method_name="get_connector_count")
    number_of_participants = serializers.SerializerMethodField()

    def get_dataset_count(self, user_org_map):
        return DatasetV2.objects.filter(status=True, user_map__user=user_org_map.user.id).count()

    def get_connector_count(self, user_org_map):
        return Connectors.objects.filter(status=True, user_map__user=user_org_map.user.id).count()

    def get_number_of_participants(self, user_org_map):
        return (
            UserOrganizationMap.objects.select_related(Constants.USER, Constants.ORGANIZATION)
            .filter(user__status=True, user__on_boarded_by=user_org_map.user.id, user__role=3)
            .all()
            .count()
        )


class DropDocumentSerializer(serializers.Serializer):
    """DropDocumentSerializer class"""

    governing_law = serializers.FileField(validators=[validate_file_size, validate_document_type])
    privacy_policy = serializers.FileField(validators=[validate_file_size, validate_document_type])
    tos = serializers.FileField(validators=[validate_file_size, validate_document_type])
    limitations_of_liabilities = serializers.FileField(validators=[validate_file_size, validate_document_type])
    warranty = serializers.FileField(validators=[validate_file_size, validate_document_type])


class PolicyDocumentSerializer(serializers.ModelSerializer):
    """PolicyDocumentSerializer class"""

    governing_law = serializers.CharField()
    privacy_policy = serializers.CharField()
    tos = serializers.CharField()
    limitations_of_liabilities = serializers.CharField()
    warranty = serializers.CharField()

    class Meta:
        model = DatahubDocuments
        fields = Constants.ALL


class DatahubThemeSerializer(serializers.Serializer):
    """DatahubThemeSerializer class"""

    banner = serializers.ImageField(
        validators=[validate_file_size, validate_image_type],
        required=False,
        allow_null=True,
    )
    button_color = serializers.CharField(required=False, allow_null=True)
    # email = serializers.EmailField()


class TeamMemberListSerializer(serializers.Serializer):
    """
    Create Team Member Serializer.
    """

    class Meta:
        model = User

    id = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.PrimaryKeyRelatedField(queryset=UserRole.objects.all(), read_only=False)
    profile_picture = serializers.FileField()
    status = serializers.BooleanField()
    on_boarded = serializers.BooleanField()


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """
    Create a Team Member
    """

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role", "on_boarded_by", "on_boarded")


class TeamMemberDetailsSerializer(serializers.ModelSerializer):
    """
    Details of a Team Member
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "on_boarded_by", "on_boarded")


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    """
    Update Team Member
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "on_boarded_by", "on_boarded")


class DatasetSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    def validate_sample_dataset(self, value):
        """
        Validator function to check the file size limit.
        """
        MAX_FILE_SIZE = (
            Constants.MAX_PUBLIC_FILE_SIZE if self.initial_data.get("is_public") else Constants.MAX_FILE_SIZE
        )
        filesize = value.size
        if filesize > MAX_FILE_SIZE:
            raise ValidationError(
                _("You cannot upload a file more than %(value)s MB"),
                params={"value": MAX_FILE_SIZE / 1048576},
            )
        return value

    class Meta:
        """_summary_"""

        model = Datasets
        fields = [
            "user_map",
            "name",
            "description",
            "category",
            "geography",
            "crop_detail",
            "constantly_update",
            "dataset_size",
            "connector_availability",
            "age_of_date",
            "sample_dataset",
            "data_capture_start",
            "data_capture_end",
            "remarks",
            "is_enabled",
            "approval_status",
            "is_public",
        ]


class DatasetUpdateSerializer(serializers.ModelSerializer):
    """_summary_

    Args:
        serializers (_type_): _description_
    """

    class Meta:
        """_summary_"""

        model = Datasets
        fields = Constants.ALL


class DatahubDatasetsDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source="user_map.organization",
    )
    user = UserSerializer(
        read_only=False,
        required=False,
        allow_null=True,
        source="user_map.user",
    )
    organization = OrganizationRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )

    class Meta:
        model = Datasets
        exclude = Constants.EXCLUDE_DATES


class DatahubDatasetsSerializer(serializers.ModelSerializer):
    class OrganizationDatsetsListRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = [
                "org_email",
                "org_description",
                "name",
                "logo",
                "address",
                "phone_number",
            ]

    class UserDatasetSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["last_name", "first_name", "email", "on_boarded_by"]

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source="user_map.organization",
    )

    organization = OrganizationDatsetsListRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )
    user = UserDatasetSerializer(required=False, allow_null=True, read_only=True, source="user_map.user")

    class Meta:
        model = Datasets
        fields = Constants.ALL


class RecentSupportTicketSerializer(serializers.ModelSerializer):
    class OrganizationRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "org_email", "name"]

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["id", "first_name", "last_name", "email", "role", "on_boarded_by"]

    organization = OrganizationRetriveSerializer(
        allow_null=True, required=False, read_only=True, source="user_map.organization"
    )

    user = UserSerializer(allow_null=True, required=False, read_only=True, source="user_map.user")

    class Meta:
        model = SupportTicket
        fields = ["id", "subject", "category", "updated_at", "organization", "user"]


# class RecentConnectorListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Connectors
#         fields = ["id", "connector_name", "updated_at", "dataset_count", "activity"]
#
#     dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
#     activity = serializers.SerializerMethodField(method_name="get_activity")
#
#     def get_dataset_count(self, connectors_queryset):
#         return Datasets.objects.filter(status=True, user_map__user=connectors_queryset.user_map.user_id).count()
#
#     def get_activity(self, connectors_queryset):
#         try:
#             if Connectors.objects.filter(status=True, user_map__id=connectors_queryset.user_map.id).first().status == True:
#                 return Constants.ACTIVE
#             else:
#                 return Constants.NOT_ACTIVE
#         except Exception as error:
#             LOGGER.error(error, exc_info=True)
#
#         return None


class RecentDatasetListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasets
        fields = ["id", "name", "updated_at", "connector_count", "activity"]

    connector_count = serializers.SerializerMethodField(method_name="get_connector_count")
    activity = serializers.SerializerMethodField(method_name="get_activity")

    def get_connector_count(self, datasets_queryset):
        return Connectors.objects.filter(status=True, dataset_id=datasets_queryset.id).count()

    def get_activity(self, datasets_queryset):
        try:
            datasets_queryset = Datasets.objects.filter(status=True, id=datasets_queryset.id)
            if datasets_queryset:
                if datasets_queryset.first().status == True:
                    return Constants.ACTIVE
                else:
                    return Constants.NOT_ACTIVE
            else:
                return Constants.NOT_ACTIVE
        except Exception as error:
            LOGGER.error(error, exc_info=True)

        return None


class DatasetV2Validation(serializers.Serializer):
    """
    Serializer to validate dataset name & dataset description.
    """

    def validate_dataset_name(self, name):
        """
        Validator function to check if the dataset name includes special characters.

        **Parameters**
        ``name`` (str): dataset name to validate
        """
        if check_special_chars(name):
            raise ValidationError("dataset name cannot include special characters.")
        name = re.sub(r"\s+", " ", name)

        if not self.context.get("dataset_exists") and self.context.get("queryset"):
            queryset = self.context.get("queryset")
            if queryset.filter(name=name).exists():
                raise ValidationError("dataset v2 with this name already exists.")

        return name

    dataset_name = serializers.CharField(max_length=100, allow_null=False)
    description = serializers.CharField(max_length=512, allow_null=False)


class DatasetV2TempFileSerializer(serializers.Serializer):
    """
    Serializer for DatasetV2File model to serialize dataset files.
    Following are the fields required by the serializer:
        `datasets` (Files, mandatory): Multi upload Dataset files
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        """Remove fields based on the request type"""
        if "context" in kwargs:
            if "request_method" in kwargs["context"]:
                request_method = kwargs.get("context").get("request_method")
                if request_method == "DELETE" and not kwargs.get("context").get("query_params"):
                    # remove `datasets` field as `DELETE` method only requires `dataset_name`, `file_name` & `source` fields
                    self.fields.pop("datasets")
                elif request_method == "DELETE" and kwargs.get("context").get("query_params"):
                    # remove `datasets` & `file_name` fields as `DELETE` method to delete directory only requires `dataset_name` & `source` field
                    self.fields.pop("datasets")
                    self.fields.pop("file_name")
                    self.fields.pop("source")
                elif request_method == "POST":
                    # remove `file_name` field as `POST` method only requires `dataset_name`, `datasets` & `source` fields
                    self.fields.pop("file_name")

    def validate_datasets(self, files):
        """
        Validator function to check for dataset file types & dataset file size (Constants.DATASET_MAX_FILE_SIZE) in MB.

        **Parameters**
        ``files`` ([Files]): list of files to validate the file type included in Constants.DATASET_FILE_TYPES.
        """
        for file in files:
            if not validate_dataset_type(file, Constants.DATASET_FILE_TYPES):
                raise ValidationError(
                    f"Document type not supported. Only following documents are allowed: {Constants.DATASET_FILE_TYPES}"
                )

            if not validate_dataset_size(file, Constants.DATASET_MAX_FILE_SIZE):
                raise ValidationError(
                    f"You cannot upload/export file size more than {Constants.DATASET_MAX_FILE_SIZE}MB."
                )

        return files

    def validate_dataset_name(self, name):
        """
        Validator function to check if the dataset name includes special characters.

        **Parameters**
        ``name`` (str): dataset name to validate
        """
        if check_special_chars(name):
            raise ValidationError("dataset name cannot include special characters.")
        name = re.sub(r"\s+", " ", name)

        if not self.context.get("dataset_exists") and self.context.get("queryset"):
            queryset = self.context.get("queryset")
            if queryset.filter(name=name).exists():
                raise ValidationError("dataset v2 with this name already exists.")

        return name

    dataset_name = serializers.CharField(max_length=100, allow_null=False)
    datasets = serializers.ListField(
        child=serializers.FileField(max_length=255, use_url=False, allow_empty_file=False),
        write_only=True,
    )
    file_name = serializers.CharField(allow_null=False)
    source = serializers.CharField(allow_null=False)


class DatasetV2FileSerializer(serializers.ModelSerializer):
    """
    Serializer for DatasetV2File model to serialize dataset files.
    Following are the fields required by the serializer:
        `id` (int): auto-generated Identifier
        `dataset` (DatasetV2, FK): DatasetV2 reference object
        `file` (File, mandatory): Dataset file
    """

    class Meta:
        model = DatasetV2File
        fields = ["id", "dataset", "file", "source", "standardised_file", "standardised_configuration"]


class DatasetV2Serializer(serializers.ModelSerializer):
    """
    Serializer for DatasetV2 model to serialize the Meta Data of Datasets.
    Following are the fields required by the serializer:
        `id` (UUID): auto-generated Identifier
        `name` (String, unique, mandatory): Dataset name
        `user_map` (UUID, mandatory): User Organization map ID, related to :model:`datahub_userorganizationmap` (UserOrganizationMap)
        `description` (Text): Dataset description
        `category` (JSON, mandatory): Category as JSON object
        `geography` (String): Geography of the dataset
        `data_capture_start` (DateTime): Start DateTime of the dataset captured
        `data_capture_end` (DateTime): End DateTime of the dataset captured
        `datasets` (Files, FK, read only): Dataset files stored
        `upload_datasets` (List, mandatory): List of dataset files to be uploaded
    """

    class OrganizationRetriveSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = [
                "org_email",
                "org_description",
                "name",
                "logo",
                "phone_number",
                "address",
            ]

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["id", "first_name", "last_name", "email", "on_boarded_by"]

    organization = OrganizationRetriveSerializer(
        allow_null=True, required=False, read_only=True, source="user_map.organization"
    )

    user = UserSerializer(allow_null=True, required=False, read_only=True, source="user_map.user")

    datasets = DatasetV2FileSerializer(many=True, read_only=True)
    upload_datasets = serializers.ListField(
        child=serializers.FileField(max_length=255, use_url=False, allow_empty_file=False),
        write_only=True,
        required=False,
    )

    def validate_name(self, name):
        if check_special_chars(name):
            raise ValidationError("dataset name cannot include special characters.")
        name = re.sub(r"\s+", " ", name)
        return name

    class Meta:
        model = DatasetV2
        fields = [
            "id",
            "name",
            "user_map",
            "description",
            "category",
            "geography",
            "constantly_update",
            "data_capture_start",
            "data_capture_end",
            "organization",
            "user",
            "datasets",
            "upload_datasets",
        ]

    def create(self, validated_data):
        """
        Override the create method to save meta data (DatasetV2) with multiple dataset files on to the referenced model (DatasetV2File).

        **Parameters**
        ``validated_data`` (Dict): Validated data from the serializer

        **Returns**
        ``dataset_obj`` (DatasetV2 instance): Save & return the dataset
        """
        # create meta dataset obj
        # uploaded_files = validated_data.pop("upload_datasets")
        file_paths = {}

        try:
            # create_directory()
            directory_created = move_directory(
                os.path.join(settings.BASE_DIR, settings.TEMP_DATASET_URL, validated_data.get("name")),
                settings.DATASET_FILES_URL,
            )
            to_find = [
                Constants.SOURCE_FILE_TYPE,
                Constants.SOURCE_MYSQL_FILE_TYPE,
                Constants.SOURCE_POSTGRESQL_FILE_TYPE,
            ]

            # import pdb
            # pdb.set_trace()

            standardised_directory_created = move_directory(
                os.path.join(settings.BASE_DIR, settings.TEMP_STANDARDISED_DIR, validated_data.get("name")),
                settings.STANDARDISED_FILES_URL,
            )

            file_paths = plazy.list_files(root=directory_created, is_include_root=True)
            standardisation_template = json.loads(self.context.get("standardisation_template"))
            standardisation_config = json.loads(self.context.get("standardisation_config", {}))
            if file_paths:
                dataset_obj = DatasetV2.objects.create(**validated_data)
                for file_path in file_paths:
                    dataset_file_path = file_path.replace("media/", "")
                    dataset_name_file_path = "/".join(dataset_file_path.split("/")[-3:])
                    DatasetV2File.objects.create(
                        dataset=dataset_obj,
                        file=dataset_file_path,
                        source=file_path.split("/")[-2],
                        standardised_file=(settings.STANDARDISED_FILES_URL + dataset_name_file_path).replace(
                            "media/", ""
                        )
                        if os.path.isfile(
                            settings.STANDARDISED_FILES_URL
                            + standardisation_template.get("temp/datasets/" + dataset_name_file_path, "")
                        )
                        else dataset_file_path,
                        standardised_configuration=standardisation_config.get(
                            "temp/datasets/" + dataset_name_file_path
                        )
                        if standardisation_config.get("temp/datasets/" + dataset_name_file_path, "")
                        else {},
                    )
                return dataset_obj

        except Exception as error:
            LOGGER.error(error, exc_info=True)
            raise NotFoundException(
                detail="Dataset files are not uploaded or missing. Failed to create meta dataset.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, instance, validated_data):
        """
        Override the update method to save meta data (DatasetV2) with multiple new dataset files on to the referenced model (DatasetV2File).

        **Parameters**
        ``instance`` (obj): Instance of DatasetV2 model
        ``validated_data`` (Dict): Validated data from the serializer

        **Returns**
        ``instance`` (DatasetV2 instance): Save & return the dataset
        """
        temp_directory = os.path.join(settings.TEMP_DATASET_URL, instance.name)
        file_paths = {}
        to_find = [
            Constants.SOURCE_FILE_TYPE,
            Constants.SOURCE_MYSQL_FILE_TYPE,
            Constants.SOURCE_POSTGRESQL_FILE_TYPE,
        ]

        # iterate through temp_directory to fetch file paths & file names
        # for sub_dir in to_find:
        #     direct = os.path.join(temp_directory, sub_dir)
        #     if os.path.exists(direct):
        #         file_paths.update({
        #             os.path.join(direct, f): [sub_dir, f]
        #             for f in os.listdir(direct)
        #             if os.path.isfile(os.path.join(direct, f))
        #         })

        # # save the files at actual dataset location & update in DatasetV2File table
        # if file_paths:
        #     for file_path, sub_file in file_paths.items():
        #         directory_created = create_directory(os.path.join(settings.DATASET_FILES_URL), [instance.name, sub_file[0]])
        #         shutil.copy(file_path, directory_created)

        #         path_to_save = os.path.join(directory_created, sub_file[1])
        #         if not DatasetV2File.objects.filter(file=path_to_save.replace("media/", "")):
        #             DatasetV2File.objects.create(dataset=instance, file=path_to_save.replace("media/", ""), source=sub_file[0])

        # save the files at actual dataset location & update in DatasetV2File table
        # standardised_directory_created = move_directory(
        #         os.path.join(settings.TEMP_STANDARDISED_DIR,instance.name), settings.STANDARDISED_FILES_URL
        # )
        standardised_temp_directory = os.path.join(settings.TEMP_STANDARDISED_DIR, instance.name)
        standardised_file_paths = (
            plazy.list_files(root=standardised_temp_directory, is_include_root=True)
            if os.path.exists(standardised_temp_directory)
            else None
        )
        standardisation_template = json.loads(self.context.get("standardisation_template"))
        standardisation_config = json.loads(self.context.get("standardisation_config", {}))

        # import pdb
        # pdb.set_trace()

        if standardised_file_paths:
            for file_path in standardised_file_paths:
                directory_created = create_directory(
                    os.path.join(settings.STANDARDISED_FILES_URL), [instance.name, file_path.split("/")[-2]]
                )
                # file_path = file_path.replace("temp/standardised/","")
                shutil.copy2(file_path, directory_created)

                dataset_name_file_path = str(directory_created).replace("media/", "") + file_path.split("/")[-1]
                dataset_file_path_alone = "datasets/" + "/".join(file_path.split("/")[-3:])
                standardised_dataset_file_path_alone = "standardised/" + "/".join(file_path.split("/")[-3:])
                print("*****", dataset_name_file_path)
                # import pdb; pdb.set_trace()
                # path_to_save = os.path.join(directory_created, file_path.split("/")[-1])
                DatasetV2File.objects.filter(file=dataset_file_path_alone).update(
                    dataset=instance,
                    source=file_path.split("/")[-2],
                    standardised_file=standardised_dataset_file_path_alone,
                    standardised_configuration=standardisation_config.get(
                        str(directory_created) + file_path.split("/")[-1]
                    )
                    if standardisation_config.get(str(directory_created) + file_path.split("/")[-1], "")
                    else {},
                )
            # delete the temp directory
            shutil.rmtree(standardised_temp_directory)

        if os.path.exists(temp_directory):
            file_paths = (
                plazy.list_files(root=temp_directory, is_include_root=True) if os.path.exists(temp_directory) else None
            )

            if file_paths:
                for file_path in file_paths:
                    directory_created = create_directory(
                        os.path.join(settings.DATASET_FILES_URL), [instance.name, file_path.split("/")[-2]]
                    )
                    shutil.copy2(file_path, directory_created)
                    dataset_file_path = file_path.replace("media/", "")
                    dataset_name_file_path = "/".join(dataset_file_path.split("/")[-3:])

                    path_to_save = os.path.join(directory_created, file_path.split("/")[-1])
                    if not DatasetV2File.objects.filter(standardised_file=path_to_save.replace("media/", "")):
                        DatasetV2File.objects.create(
                            dataset=instance,
                            file=path_to_save.replace("media/", ""),
                            source=file_path.split("/")[-2],
                            standardised_file=(settings.STANDARDISED_FILES_URL + dataset_name_file_path).replace(
                                "media/", ""
                            )
                            if os.path.isfile(
                                settings.STANDARDISED_FILES_URL
                                + standardisation_template.get("temp/datasets/" + dataset_name_file_path, "")
                            )
                            else dataset_file_path,
                            standardised_configuration=standardisation_config.get(
                                "temp/datasets/" + dataset_name_file_path
                            )
                            if standardisation_config.get("temp/datasets/" + dataset_name_file_path, "")
                            else {},
                        )

            # delete the temp directory
            shutil.rmtree(temp_directory)

        instance = super(DatasetV2Serializer, self).update(instance, validated_data)
        return instance


class DatahubDatasetsV2Serializer(serializers.ModelSerializer):
    """
    Serializer for filtered list of datasets.
    """

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(), required=True, source="user_map.user"
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source="user_map.organization",
    )

    organization = DatahubDatasetsSerializer.OrganizationDatsetsListRetriveSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.organization"
    )
    user = DatahubDatasetsSerializer.UserDatasetSerializer(
        required=False, allow_null=True, read_only=True, source="user_map.user"
    )

    class Meta:
        model = DatasetV2
        fields = Constants.ALL


class micrositeOrganizationSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        source=Constants.ORGANIZATION,
    )
    organization = OrganizationRetriveSerializer(
        required=False,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = UserOrganizationMap
        exclude = Constants.EXCLUDE_DATES

    dataset_count = serializers.SerializerMethodField(method_name="get_dataset_count")
    users_count = serializers.SerializerMethodField(method_name="get_users_count")

    def get_dataset_count(self, user_org_map):
        return DatasetV2.objects.filter(status=True, user_map__organization=user_org_map.organization.id).count()

    def get_users_count(self, user_org_map):
        return UserOrganizationMap.objects.filter(
            user__status=True, organization_id=user_org_map.organization.id
        ).count()


class StandardisationTemplateViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardisationTemplate
        exclude = Constants.EXCLUDE_DATES


class StandardisationTemplateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardisationTemplate
        exclude = Constants.EXCLUDE_DATES


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = Constants.ALL


class DatasetV2NewListSerializer(serializers.ModelSerializer):
    # dataset = DatasetFileV2NewSerializer()
    class Meta:
        model = DatasetV2
        fields = Constants.ALL


class DatasetFileV2NewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetV2File
        fields = Constants.ALL

class DatasetV2DetailNewSerializer(serializers.ModelSerializer):
    dataset_files = DatasetFileV2NewSerializer(many=True, source='datasets')
    class Meta:
        model = DatasetV2
        fields = Constants.ALL
        # fields = ['id', 'name', 'geography', 'category', 'dataset_files']
        
class UsagePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = UsagePolicy
        fields = '__all__'
