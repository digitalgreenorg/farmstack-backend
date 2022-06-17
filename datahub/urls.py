from posixpath import basename
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from datahub import views
from datahub.views import ParticipantViewSet, DropDocumentView, DocumentSaveView, DatahubThemeView

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")
router.register("drop_document", DropDocumentView, basename='drop_document')
router.register("save_documents", DocumentSaveView, basename="document_save"),
router.register("theme", DatahubThemeView, basename="theme")


urlpatterns = [
    path("", include(router.urls)),
    # path("drop_document/", views.DropDocumentView.as_view()),
    # path("theme/", views.DatahubThemeView.as_view())
]
