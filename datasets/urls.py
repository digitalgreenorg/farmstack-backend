from posixpath import basename
from sys import settrace

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core import settings
from core.constants import Constants
from datasets.views import DatasetsViewSetV2

router = DefaultRouter()
router.register(r"datasets", DatasetsViewSetV2, basename=Constants.PARTICIPANT)

urlpatterns = [
    path("v2/", include(router.urls)),
    path("v2/<uuid:pk>/", include(router.urls)),
]