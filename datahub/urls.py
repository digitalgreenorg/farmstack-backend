from posixpath import basename
from sys import settrace

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core import settings
from core.constants import Constants
from datahub import views
from datahub.views import (
    DatahubDashboard,
    DatahubDatasetsViewSet,
    DatahubThemeView,
    DatasetV2ViewSet,
    DatasetV2ViewSetOps,
    DocumentSaveView,
    DropDocumentView,
    MailInvitationViewSet,
    OrganizationViewSet,
    ParticipantViewSet,
    PolicyDetailAPIView,
    PolicyListAPIView,
    StandardisationTemplateView,
    SupportViewSet,
    TeamMemberViewSet,
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
router.register(r"standardise", StandardisationTemplateView, basename=Constants.STANDARDISE)
 
urlpatterns = [
    path("", include(router.urls)),
    path('v2/', PolicyListAPIView.as_view(), name='policy-list'),
    path('v2/<uuid:pk>/', PolicyDetailAPIView.as_view(), name='policy-detail')
]
