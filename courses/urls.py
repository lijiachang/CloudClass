from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="list"),
    path("recommendations/", views.recommendation_center, name="recommendations"),
    path("<int:pk>/", views.course_detail, name="detail"),
    path("<int:pk>/enroll/", views.enroll_course, name="enroll"),
    path("<int:pk>/favorite/", views.toggle_favorite_course, name="favorite"),
    path("teacher/manage/", views.teacher_course_list, name="teacher_list"),
    path("teacher/create/", views.teacher_course_create, name="teacher_create"),
    path("teacher/<int:pk>/edit/", views.teacher_course_edit, name="teacher_edit"),
    path("teacher/<int:pk>/analytics/", views.teacher_course_analytics, name="teacher_analytics"),
]
