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
    SupportTicketResolutionsViewset, ParticipantViewSet, MailInvitationViewSet, OrganizationViewSet, TeamMemberViewSet,
    DropDocumentView, DocumentSaveView, DatahubThemeView, SupportViewSet, DatahubDatasetsViewSet, DatahubDashboard,
    DatasetV2ViewSet, DatasetV2View, DatasetFileV2View, DatasetV2ViewSetOps, StandardisationTemplateView,
    DatahubNewDashboard, ResourceFileManagementViewSet, ResourceManagementViewSet, CategoryViewSet, SubCategoryViewSet,
    EmbeddingsViewSet, PolicyListAPIView, UsagePolicyListCreateView, UsagePolicyRetrieveUpdateDestroyView,
    ResourceUsagePolicyListCreateView, ResourceUsagePolicyRetrieveUpdateDestroyView, MessagesViewSet,
    MessagesCreateViewSet, PolicyDetailAPIView

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


router.register(r"v2/participant", ParticipantViewSet, basename=Constants.PARTICIPANT)
router.register(r"v2/send_invite", MailInvitationViewSet, basename=Constants.SEND_INVITE)
router.register(r"v2/organization", OrganizationViewSet, basename=Constants.ORGANIZATION)
router.register(r"v2/team_member", TeamMemberViewSet, basename=Constants.TEAM_MEMBER)
router.register("v2/drop_document", DropDocumentView, basename=Constants.DROP_DOCUMENT)
router.register("v2/save_documents", DocumentSaveView, basename=Constants.SAVE_DOCUMENTS)
router.register("v2/theme", DatahubThemeView, basename=Constants.THEME)
router.register(r"v2/support", SupportViewSet, basename=Constants.SUPPORT_TICKETS)
router.register(r"v2/datasets", DatahubDatasetsViewSet, basename=Constants.DATAHUB_DATASETS)
router.register(r"v2", DatahubDashboard, basename="")
router.register(r"v2/dataset/v2", DatasetV2ViewSet, basename=Constants.DATASET_V2_URL)
router.register(r"v2/new_dataset_v2", DatasetV2View, basename=Constants.DATASETS_V2_URL)
router.register(r"v2/dataset_files", DatasetFileV2View, basename=Constants.DATASET_FILES)
router.register(r"v2/dataset_ops", DatasetV2ViewSetOps, basename="")
router.register(r"v2/standardise", StandardisationTemplateView, basename=Constants.STANDARDISE)
router.register(r"v2/newdashboard", DatahubNewDashboard, basename=Constants.NEW_DASHBOARD)
router.register(r"v2/resource_management", ResourceManagementViewSet, basename=Constants.RESOURCE_MANAGEMENT)
router.register(r"v2/resource_file", ResourceFileManagementViewSet, basename=Constants.RESOURCE_FILE_MANAGEMENT)
router.register(r'v2/categories', CategoryViewSet, basename=Constants.CATEGORY)
router.register(r'v2/subcategories', SubCategoryViewSet, basename=Constants.SUBCATEGORY)
router.register(r'v2/embeddings', EmbeddingsViewSet, basename='embeddings')

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









