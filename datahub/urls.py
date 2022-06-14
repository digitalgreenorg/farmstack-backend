from posixpath import basename

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Local Modules.
from .views import OrganizationViewSet, TeamMemberViewSet

router = DefaultRouter()
router.register(r"team_member", TeamMemberViewSet, basename="team_member")
router.register(r"organization", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("", include(router.urls)),
]
