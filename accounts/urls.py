from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('signup', views.LoginViewset, basename='signup')
router.register('otp', views.VerifyOTPViewset, basename='otp')

urlpatterns = [
    path("", include(router.urls)),
]
