from django.db import models
from datahub.models import DatasetV2File


class API(models.Model):
    """
    API Model - Represents an API configuration.

    Attributes:
        - dataset_file: ForeignKey to the associated DatasetV2File.
        - endpoint: The API endpoint (unique).
        - selected_columns: JSONField for storing selected columns.
        - access_key: API access key.
    """

    dataset_file = models.ForeignKey(DatasetV2File, on_delete=models.CASCADE, related_name="apis")
    endpoint = models.CharField(max_length=100, unique=True)
    selected_columns = models.JSONField()
    access_key = models.CharField(max_length=100)

    def __str__(self):
        """
        Returns a string representation of the API instance.
        """
        return self.endpoint
