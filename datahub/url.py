from django.urls import path, include
from datahub import views
from datahub.views import TeamMemberViewSet

team_member = TeamMemberViewSet()

urlpatterns = [
    path('participant', views.TeamMemberViewSet.create),
]
