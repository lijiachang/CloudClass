from django.urls import path

from . import views

app_name = "discussions"

urlpatterns = [
    path("create/", views.post_create, name="create"),
    path("course/<int:course_id>/create/", views.post_create, name="course_create"),
    path("<int:pk>/", views.post_detail, name="detail"),
    path("<int:pk>/delete/", views.post_delete, name="delete"),
]
