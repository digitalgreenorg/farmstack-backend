from django.urls import path, include
from datahub import views
from datahub.views import TeamMemberViewSet
from accounts.serializers import UserSerializer

team_member = TeamMemberViewSet()

urlpatterns = [
    path('participant', views.TeamMemberViewSet.create, name="add"),
]
