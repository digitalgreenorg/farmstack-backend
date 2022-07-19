from core.constants import Constants
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from participant.views import ParticipantDatasetsViewSet, ParticipantSupportViewSet

router = DefaultRouter()
router.register(r"support", ParticipantSupportViewSet, basename=Constants.SUPPORT)
router.register(r"datasets", ParticipantDatasetsViewSet, basename="participant_datasets")

urlpatterns = [
    path("", include(router.urls)),
]
