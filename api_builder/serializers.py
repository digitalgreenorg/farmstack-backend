from rest_framework import serializers
from api_builder.models import API
from datahub.models import DatasetV2File

class DatasetV2FileSerializer(serializers.ModelSerializer):
    dataset = serializers.SerializerMethodField()

    class Meta:
        model = DatasetV2File
        fields = '__all__'

    def get_dataset(self, obj):
        return obj.dataset.name

class APISerializer(serializers.ModelSerializer):
    dataset_file = DatasetV2FileSerializer()

    class Meta:
        model = API
        fields = '__all__'
