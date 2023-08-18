from posixpath import basename
from sys import settrace

from core import settings
from core.constants import Constants
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from datahub import views
from datahub.views import (
    DatahubDashboard,
    DatahubDatasetsViewSet,
    DatahubThemeView,
    DatasetFileV2View,
    DatasetV2View,
    DatasetV2ViewSet,
    DatasetV2ViewSetOps,
    DocumentSaveView,
    DropDocumentView,
    MailInvitationViewSet,
    OrganizationViewSet,
    ParticipantViewSet,
    PolicyDetailAPIView,
    PolicyListAPIView,
    ResourceFileManagementViewSet,
    StandardisationTemplateView,
    SupportViewSet,
    TeamMemberViewSet,
    UsagePolicyListCreateView,
    UsagePolicyRetrieveUpdateDestroyView,
    DatahubNewDashboard,
    ResourceManagementViewSet,
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
router.register(r"new_dataset_v2", DatasetV2View, basename=Constants.DATASETS_V2_URL)
router.register(r"dataset_files", DatasetFileV2View, basename=Constants.DATASET_FILES)
router.register(r"dataset_ops", DatasetV2ViewSetOps, basename="")
router.register(r"standardise", StandardisationTemplateView, basename=Constants.STANDARDISE)
router.register(r"newdashboard", DatahubNewDashboard, basename=Constants.NEW_DASHBOARD)
router.register(r"resource_management", ResourceManagementViewSet, basename=Constants.RESOURCE_MANAGEMENT)
router.register(r"resource_file", ResourceFileManagementViewSet, basename=Constants.RESOURCE_FILE_MANAGEMENT)

urlpatterns = [
    path("", include(router.urls)),
    path('policy/', PolicyListAPIView.as_view(), name='policy-list'),
    path('policy/<uuid:pk>/', PolicyDetailAPIView.as_view(), name='policy-detail'),
    path('usage_policies/', UsagePolicyListCreateView.as_view(), name='usage-policy-list-create'),
    path('usage_policies/<uuid:pk>/', UsagePolicyRetrieveUpdateDestroyView.as_view(), name='usage-policy-retrieve-update-destroy'),
]
