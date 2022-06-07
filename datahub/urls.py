from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Local Modules.
from .views import TeamMemberViewSet

router = DefaultRouter()
router.register(r"team_member", TeamMemberViewSet, basename="team_member")

urlpatterns = [
    path("", include(router.urls)),
]
