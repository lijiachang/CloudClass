from django.urls import path

from .views import ProfileUpdateView, UserLoginView, UserLogoutView, register

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
]
