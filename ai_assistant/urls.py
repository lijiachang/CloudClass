from django.urls import path

from . import views

app_name = "ai_assistant"

urlpatterns = [
    path("", views.assistant_center, name="center"),
    path("submission/<int:submission_id>/review-suggestion/", views.generate_review_suggestion, name="review_suggestion"),
]

