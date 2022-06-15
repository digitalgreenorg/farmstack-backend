from posixpath import basename
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from datahub import views
from datahub.views import ParticipantViewSet

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")
router.register("save_documents", views.DocumentSaveView, basename="document_save"),

urlpatterns = [
    path("", include(router.urls)),
    path("drop_document/", views.DropDocumentView.as_view()),
]
