from django.urls import include, path
from rest_framework.routers import DefaultRouter

from participant.views import ParticipantSupportViewSet

router = DefaultRouter()
router.register(r"support", ParticipantSupportViewSet, basename="support")
urlpatterns = [
    path("", include(router.urls)),
]
