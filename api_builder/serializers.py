from rest_framework import serializers
from api_builder.models import API
from datahub.models import DatasetV2File


class DatasetV2FileSerializer(serializers.ModelSerializer):
    """
    Serializer for DatasetV2File model.

    Serializes DatasetV2File fields and includes a method for getting the dataset name.
    """

    dataset = serializers.SerializerMethodField()

    class Meta:
        model = DatasetV2File
        fields = "__all__"

    def get_dataset(self, obj):
        """
        Get the dataset name associated with the DatasetV2File.

        Args:
            obj: The DatasetV2File instance.

        Returns:
            The dataset name.
        """
        return obj.dataset.name


class APISerializer(serializers.ModelSerializer):
    """
    Serializer for the API model.

    Includes serialization of the associated DatasetV2File using DatasetV2FileSerializer.
    """

    dataset_file = DatasetV2FileSerializer()

    class Meta:
        model = API
        fields = "__all__"
