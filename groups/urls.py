from django.urls import path

from . import views

app_name = "groups"

urlpatterns = [
    path("", views.group_list, name="group_list"),
    path("create/", views.group_create, name="group_create"),
    path("<int:group_id>/", views.group_detail, name="group_detail"),
    path("member/<int:member_id>/remove/", views.member_remove, name="member_remove"),
]

