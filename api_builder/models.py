from django.db import models
from datahub.models import DatasetV2File

class API(models.Model):
    dataset_file = models.ForeignKey(DatasetV2File, on_delete=models.CASCADE, related_name='apis')
    endpoint = models.CharField(max_length=100)
    selected_columns = models.JSONField()
    access_key = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.endpoint
