from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.constants import Constants
from participant.views import (
    ParticipantConnectorsMapViewSet,
    ParticipantConnectorsViewSet,
    ParticipantDatasetsViewSet,
    ParticipantDepatrmentViewSet,
    ParticipantProjectViewSet,
    ParticipantSupportViewSet,
    DataBaseViewSet,
    SupportTicketV2ModelViewSet,
    SupportTicketResolutionsViewset

)
from participant.views import (
    CategoryViewSet,
    DatahubDashboard,
    DatahubNewDashboard,
    DatahubThemeView,
    DatasetFileV2View,
    DatasetV2View,
    DatasetV2ViewSet,
    DatasetV2ViewSetOps,
    DocumentSaveView,
    DropDocumentView,
    EmbeddingsViewSet,
    MailInvitationViewSet,
    MessagesCreateViewSet,
    MessagesViewSet,
    OrganizationViewSet,
    ParticipantViewSet,
    PolicyDetailAPIView,
    PolicyListAPIView,
    ResourceFileManagementViewSet,
    ResourceManagementViewSet,
    ResourceUsagePolicyListCreateView,
    ResourceUsagePolicyRetrieveUpdateDestroyView,
    StandardisationTemplateView,
    SubCategoryViewSet,
    SupportViewSet,
    TeamMemberViewSet,
    UsagePolicyListCreateView,
    UsagePolicyRetrieveUpdateDestroyView,

)

router = DefaultRouter()
router.register(r"support", ParticipantSupportViewSet, basename=Constants.SUPPORT)
router.register(r"datasets", ParticipantDatasetsViewSet, basename="participant_datasets")
router.register(r"connectors", ParticipantConnectorsViewSet, basename="participant_connectors")
router.register(r"connectors_map", ParticipantConnectorsMapViewSet, basename="participant_connectors_map")
router.register(r"department", ParticipantDepatrmentViewSet, basename="participant_department")
router.register(r"project", ParticipantProjectViewSet, basename="participant_project")
router.register(r"database", DataBaseViewSet,basename="database")
router.register(r"support_ticket", SupportTicketV2ModelViewSet,basename="support_tickets")
router.register(r"ticket_resolution", SupportTicketResolutionsViewset,basename="support_tickets_resolutions")
router.register(r"participant", ParticipantViewSet, basename=Constants.PARTICIPANT)
router.register(r"send_invite", MailInvitationViewSet, basename=Constants.SEND_INVITE)
router.register(r"organization", OrganizationViewSet, basename=Constants.ORGANIZATION)
router.register(r"team_member", TeamMemberViewSet, basename=Constants.TEAM_MEMBER)
router.register("drop_document", DropDocumentView, basename=Constants.DROP_DOCUMENT)
router.register("save_documents", DocumentSaveView, basename=Constants.SAVE_DOCUMENTS)
router.register("theme", DatahubThemeView, basename=Constants.THEME)
router.register(r"support", SupportViewSet, basename=Constants.SUPPORT_TICKETS)
router.register(r"", DatahubDashboard, basename="")
router.register(r"dataset/v2", DatasetV2ViewSet, basename=Constants.DATASET_V2_URL)
router.register(r"new_dataset_v2", DatasetV2View, basename=Constants.DATASETS_V2_URL)
router.register(r"dataset_files", DatasetFileV2View, basename=Constants.DATASET_FILES)
router.register(r"dataset_ops", DatasetV2ViewSetOps, basename="")
router.register(r"standardise", StandardisationTemplateView, basename=Constants.STANDARDISE)
router.register(r"newdashboard", DatahubNewDashboard, basename=Constants.NEW_DASHBOARD)
router.register(r"resource_management", ResourceManagementViewSet, basename=Constants.RESOURCE_MANAGEMENT)
router.register(r"resource_file", ResourceFileManagementViewSet, basename=Constants.RESOURCE_FILE_MANAGEMENT)
router.register(r'categories', CategoryViewSet, basename=Constants.CATEGORY)
router.register(r'subcategories', SubCategoryViewSet, basename=Constants.SUBCATEGORY)
router.register(r'embeddings', EmbeddingsViewSet, basename='embeddings')


urlpatterns = [
    path("", include(router.urls)),
    path('policy/', PolicyListAPIView.as_view(), name='policy-list'),
    path('policy/<uuid:pk>/', PolicyDetailAPIView.as_view(), name='policy-detail'),
    path('usage_policies/', UsagePolicyListCreateView.as_view(), name='usage-policy-list-create'),
    path('usage_policies/<uuid:pk>/', UsagePolicyRetrieveUpdateDestroyView.as_view(), name='usage-policy-retrieve-update-destroy'),
    path('resource_usage_policies/', ResourceUsagePolicyListCreateView.as_view(), name='resource_usage-policy-list-create'),
    path('resource_usage_policies/<uuid:pk>/', ResourceUsagePolicyRetrieveUpdateDestroyView.as_view(), name='resource_usage-policy-retrieve-update-destroy'),
    path('messages/<uuid:pk>/', MessagesViewSet.as_view(), name='messages-retrieve-update-destroy'),
    path('messages/', MessagesCreateViewSet.as_view(), name='messages_create'),
]

# from django.urls import path

# from . import views

# urlpatterns = [
#     path('database-config/', views.test_database_config, name='test_database_config'),
# ]









