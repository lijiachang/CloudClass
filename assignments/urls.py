from django.urls import path

from . import views

app_name = "assignments"

urlpatterns = [
    path("create/", views.assignment_create, name="create"),
    path("<int:pk>/submit/", views.assignment_submit, name="submit"),
    path("<int:pk>/reviews/", views.assignment_review_list, name="review_list"),
    path("<int:pk>/export/", views.export_scores, name="export_scores"),
    path("submission/<int:submission_id>/review/", views.assignment_review, name="review"),
]
