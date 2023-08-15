from django.urls import path
from api_builder.views import APIViewWithData, CreateAPIView

urlpatterns = [
    path('create/', CreateAPIView.as_view(), name='create_api'),
    path('<str:user_id>/<str:endpoint_name>/', APIViewWithData.as_view(), name='api-with-data'),
]
