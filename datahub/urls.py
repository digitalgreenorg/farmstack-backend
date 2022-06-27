from posixpath import basename
from sys import settrace

from core import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from datahub import views
from datahub.views import (
    DatahubThemeView,
    DocumentSaveView,
    DropDocumentView,
    MailInvitationViewSet,
    OrganizationViewSet,
    ParticipantViewSet,
    SupportViewSet,
)

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")
router.register(r"send_invite", MailInvitationViewSet, basename="send_invite")
router.register(r"organization", OrganizationViewSet, basename="organization")
router.register("drop_document", DropDocumentView, basename="drop_document")
router.register("save_documents", DocumentSaveView, basename="document_save")
router.register("theme", DatahubThemeView, basename="theme")
router.register(r"support", SupportViewSet, basename="support_tickets")


urlpatterns = [
    path("", include(router.urls)),
]
