import uuid
from django.db import models

from core.base_models import TimeStampMixin

# Create your models here.

class FeedBack(TimeStampMixin):
    """
    FeedBack Model- this is feed back table from the bot
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    query = models.TextField()
    feedback = models.TextField()
    response = models.TextField()
