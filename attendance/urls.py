from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.session_list, name="session_list"),
    path("create/", views.session_create, name="session_create"),
    path("<int:session_id>/", views.session_detail, name="session_detail"),
    path("<int:session_id>/sign/", views.sign_in, name="sign_in"),
]

