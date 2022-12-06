from core.constants import Constants
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from participant.views import (
    ParticipantConnectorsMapViewSet,
    ParticipantConnectorsViewSet,
    ParticipantDatasetsViewSet,
    ParticipantDepatrmentViewSet,
    ParticipantProjectViewSet,
    ParticipantSupportViewSet,
)

router = DefaultRouter()
router.register(r"support", ParticipantSupportViewSet, basename=Constants.SUPPORT)
router.register(r"datasets", ParticipantDatasetsViewSet, basename="participant_datasets")
router.register(r"connectors", ParticipantConnectorsViewSet, basename="participant_connectors")
router.register(r"connectors_map", ParticipantConnectorsMapViewSet, basename="participant_connectors_map")
router.register(r"department", ParticipantDepatrmentViewSet, basename="participant_department")
router.register(r"project", ParticipantProjectViewSet, basename="participant_project")


urlpatterns = [
    path("", include(router.urls)),
]


