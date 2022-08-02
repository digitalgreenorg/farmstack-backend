from django.urls import path, include
from microsite.views import OrganizationMicrositeViewSet, DatasetsMicrositeViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"", OrganizationMicrositeViewSet, basename="org_admin")
router.register(r"datasets", DatasetsMicrositeViewSet, basename="datasets")

urlpatterns = [
    path("", include(router.urls)),
]
