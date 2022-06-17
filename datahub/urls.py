from posixpath import basename
from sys import settrace
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from core import settings
from datahub import views
from datahub.views import ParticipantViewSet, MailInvitationViewSet, OrganizationViewSet

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename="participant")
router.register(r"send_invite", MailInvitationViewSet, basename="send_invite")
router.register(r"organization", OrganizationViewSet, basename="organization")
router.register("save_documents", views.DocumentSaveView, basename="document_save"),


urlpatterns = [
    path("", include(router.urls)),
]
