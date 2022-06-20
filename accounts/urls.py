from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("register", views.RegisterViewset, basename="register")
router.register("login", views.LoginViewset, basename="login")
router.register("otp", views.VerifyLoginOTPViewset, basename="otp")
router.register("resend_otp", views.LoginViewset, basename="resend_otp")

urlpatterns = [
    path("", include(router.urls)),
    path("policy_docs/", views.PolicyDocumentsView.as_view()),
]
