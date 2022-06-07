from django.urls import path, include
from datahub import views

urlpatterns = [
    path('participant', views.participant_add),

]
