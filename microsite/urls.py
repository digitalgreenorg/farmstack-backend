from django.urls import path, include
from microsite.views import (
    OrganizationMicrositeViewSet,
    DatahubThemeMicrositeViewSet,
    DatasetsMicrositeViewSet,
    ContactFormViewSet,
    DocumentsMicrositeViewSet,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"", OrganizationMicrositeViewSet, basename="o")
router.register(r"contact_form", ContactFormViewSet, basename="contact_form")
router.register(r"datasets", DatasetsMicrositeViewSet, basename="datasets")
router.register(r"", DocumentsMicrositeViewSet, basename="d")
router.register(r"", DatahubThemeMicrositeViewSet, basename="t")

urlpatterns = [
    path("", include(router.urls)),
]
