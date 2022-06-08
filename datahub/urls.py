from posixpath import basename
from accounts.serializers import UserSerializer
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from datahub import views
from datahub.views import ParticipantViewSet

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")

urlpatterns = [
    path("", include(router.urls)),
]
