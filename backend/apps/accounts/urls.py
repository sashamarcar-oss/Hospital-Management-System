from django.urls import path

from apps.accounts import views
from apps.accounts.views_users import MyPermissionsView

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="token_refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("my-permissions/", MyPermissionsView.as_view({"get": "list"}), name="my-permissions"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
]
