from django.urls import path, include
from microsite.views import OrganizationMicrositeViewSet, DatasetsMicrositeViewSet, ContactFormViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"", OrganizationMicrositeViewSet, basename="org_admin")
router.register(r"contact_form", ContactFormViewSet, basename="contact_form")
router.register(r"datasets", DatasetsMicrositeViewSet, basename="datasets")

urlpatterns = [
    path("", include(router.urls)),
]
