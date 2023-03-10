from posixpath import basename
from sys import settrace

from core import settings
from core.constants import Constants
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from datahub import views
from datahub.views import (
    DatahubDatasetsViewSet,
    DatahubThemeView,
    DocumentSaveView,
    DropDocumentView,
    MailInvitationViewSet,
    OrganizationViewSet,
    ParticipantViewSet,
    SupportViewSet,
    TeamMemberViewSet,
    DatahubDashboard,
    DatasetV2ViewSet,
    DatasetV2ViewSetOps,
    DataPointViewSet,
)

router = DefaultRouter()
router.register(r"participant", ParticipantViewSet, basename=Constants.PARTICIPANT)
router.register(r"send_invite", MailInvitationViewSet, basename=Constants.SEND_INVITE)
router.register(r"organization", OrganizationViewSet, basename=Constants.ORGANIZATION)
router.register(r"team_member", TeamMemberViewSet, basename=Constants.TEAM_MEMBER)
router.register("drop_document", DropDocumentView, basename=Constants.DROP_DOCUMENT)
router.register("save_documents", DocumentSaveView, basename=Constants.SAVE_DOCUMENTS)
router.register("theme", DatahubThemeView, basename=Constants.THEME)
router.register(r"support", SupportViewSet, basename=Constants.SUPPORT_TICKETS)
router.register(r"datasets", DatahubDatasetsViewSet, basename=Constants.DATAHUB_DATASETS)
router.register(r"", DatahubDashboard, basename="")
router.register(r"dataset/v2", DatasetV2ViewSet, basename=Constants.DATASET_V2_URL)
router.register(r"dataset_ops",DatasetV2ViewSetOps,basename="")
router.register(r"standardization",DataPointViewSet,basename="")



urlpatterns = [
    path("", include(router.urls)),
]
