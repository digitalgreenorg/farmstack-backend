from posixpath import basename
from sys import settrace
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from core import settings
from datahub import views
from datahub.views import ParticipantViewSet

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")

urlpatterns = [
    path("", include(router.urls)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += path("__debug__/", include(debug_toolbar.urls)),
