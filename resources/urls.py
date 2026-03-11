from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    path("create/", views.material_create, name="create"),
    path("course/<int:course_id>/manage/", views.material_manage, name="manage"),
]
