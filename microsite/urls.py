from django.urls import include, path
from rest_framework.routers import DefaultRouter

from microsite.views import (
    ConnectorMicrositeViewSet,
    ContactFormViewSet,
    DatahubThemeMicrositeViewSet,
    DatasetsMicrositeViewSet,
    DocumentsMicrositeViewSet,
    OrganizationMicrositeViewSet,
    ParticipantMicrositeViewSet,
    PolicyAPIView,
    UserDataMicrositeViewSet,
    microsite_media_view,
    ResourceMicrositeViewSet,
)

router = DefaultRouter()
router.register(r"", OrganizationMicrositeViewSet, basename="o")
router.register(r"contact_form", ContactFormViewSet, basename="contact_form")
router.register(r"datasets", DatasetsMicrositeViewSet, basename="datasets")
router.register(r"", DocumentsMicrositeViewSet, basename="d")
router.register(r"", DatahubThemeMicrositeViewSet, basename="t")
router.register(r"participant", ParticipantMicrositeViewSet, basename="participant_microsite")
router.register(r"policy", PolicyAPIView, basename="policy_microsite")
router.register(r"microsite_user_data", UserDataMicrositeViewSet, basename="microsite_user_data")
router.register(r"connectors", ConnectorMicrositeViewSet, basename="microsite_connectors")
router.register(r"resources", ResourceMicrositeViewSet, basename="microsite_resource")

urlpatterns = [
    path("", include(router.urls)),
    # path('policy/', PolicyListAPIView.as_view(), name='microsite-policy-list'),
    # path('policy/<uuid:pk>/', PolicyDetailAPIView.as_view(), name='microsite-policy-detail'),
    path("microsite_media_view", microsite_media_view, name="microsite_media_view"),
]
