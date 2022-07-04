from django.urls import include, path
from rest_framework.routers import DefaultRouter
from core.constants import Constants

from participant.views import ParticipantSupportViewSet

router = DefaultRouter()
router.register(r"support", ParticipantSupportViewSet, basename=Constants.SUPPORT)
urlpatterns = [
    path("", include(router.urls)),
]
