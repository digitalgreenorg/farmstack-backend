from datahub.views import PolicyDetailAPIView, PolicyListAPIView
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from microsite.views import (
    ContactFormViewSet,
    DatahubThemeMicrositeViewSet,
    DatasetsMicrositeViewSet,
    DocumentsMicrositeViewSet,
    OrganizationMicrositeViewSet,
    ParticipantMicrositeViewSet,
    microsite_media_view,
)

router = DefaultRouter()
router.register(r"", OrganizationMicrositeViewSet, basename="o")
router.register(r"contact_form", ContactFormViewSet, basename="contact_form")
router.register(r"datasets", DatasetsMicrositeViewSet, basename="datasets")
router.register(r"", DocumentsMicrositeViewSet, basename="d")
router.register(r"", DatahubThemeMicrositeViewSet, basename="t")
router.register(r"participant", ParticipantMicrositeViewSet, basename="participant_microsite")
router.register(r"microsite_media_view", microsite_media_view, basename="microsite_media_view")

urlpatterns = [
    path("", include(router.urls)),
    path('policy/', PolicyListAPIView.as_view(), name='microsite-policy-list'),
    path('policy/<uuid:pk>/', PolicyDetailAPIView.as_view(), name='microsite-policy-detail'),

]
