from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('register', views.RegisterViewset, basename='register')
router.register('login', views.LoginViewset, basename='login')
router.register('otp', views.VerifyOTPViewset, basename='otp')
router.register('resend_otp', views.ResendOTP, basename='resend_otp')

urlpatterns = [
    path("", include(router.urls)),
]
