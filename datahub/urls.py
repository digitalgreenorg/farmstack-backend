from posixpath import basename
from sys import settrace
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from core import settings
from datahub import views
from datahub.views import (
    ParticipantViewSet,
    DropDocumentView,
    DocumentSaveView,
    DatahubThemeView,
    MailInvitationViewSet,
    OrganizationViewSet,
)

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")
router.register(r"send_invite", MailInvitationViewSet, basename="send_invite")
router.register(r"organization", OrganizationViewSet, basename="organization")
router.register("drop_document", DropDocumentView, basename="drop_document")
router.register("save_documents", DocumentSaveView, basename="document_save"),
router.register("theme", DatahubThemeView, basename="theme")


urlpatterns = [
    path("", include(router.urls)),
]
