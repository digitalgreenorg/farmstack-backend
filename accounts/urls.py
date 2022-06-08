from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# router = DefaultRouter()
# router.register()

urlpatterns = [
    # path('', router.urls,
    path("signup/", views.SignupAPIView.as_view()),
    path("otp/", views.VerifyOTPView.as_view()),
]
