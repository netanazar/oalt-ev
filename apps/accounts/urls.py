from django.urls import path

from .views import (
    UserLoginView,
    UserPasswordResetCompleteView,
    UserPasswordResetConfirmView,
    UserPasswordResetDoneView,
    UserPasswordResetView,
    UserRegisterView,
    VerifyEmailView,
    dashboard,
    download_warranty_card,
    logout_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", UserRegisterView.as_view(), name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("warranty-card/<str:claim_number>/download/", download_warranty_card, name="download_warranty_card"),
    path("verify-email/<uidb64>/<token>/", VerifyEmailView.as_view(), name="verify_email"),
    path("password-reset/", UserPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", UserPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", UserPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/complete/", UserPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
