from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from accounts.decorators import admin_required, student_required, teacher_required
from accounts.models import User
from assignments.models import Assignment, AssignmentSubmission
from courses.models import Course, CourseFavorite, CourseTag, CourseViewLog
from courses.services import (
    get_active_courses,
    get_favorite_courses,
    get_hot_courses,
    get_latest_courses,
    get_recently_viewed_courses,
    get_recommended_courses_for_user,
    with_course_metrics,
)
from discussions.models import DiscussionPost
from resources.models import CourseMaterial

from .forms import AnnouncementForm, BannerForm
from .models import Announcement, Banner


def home(request):
    context = {
        "banners": Banner.objects.filter(is_active=True)[:3],
        "announcements": Announcement.objects.filter(is_published=True)[:5],
        "hot_courses": get_hot_courses(limit=6),
        "latest_courses": get_latest_courses(limit=6),
        "recommended_courses": get_recommended_courses_for_user(request.user, limit=4),
        "tags": CourseTag.objects.annotate(course_total=Count("courses")).filter(course_total__gt=0)[:10],
    }
    return render(request, "core/home.html", context)


@login_required
def dashboard_redirect(request):
    return redirect(request.user.get_dashboard_url())


@student_required
def student_dashboard(request):
    enrollments = Course.objects.filter(enrollments__student=request.user).select_related("teacher", "category").prefetch_related("tags")
    submissions = AssignmentSubmission.objects.filter(student=request.user).select_related("assignment", "assignment__course")
    pending_assignments = Assignment.objects.filter(course__enrollments__student=request.user).exclude(
        submissions__student=request.user
    )[:5]
    favorite_courses = get_favorite_courses(request.user, limit=5)
    recent_courses = get_recently_viewed_courses(request.user, limit=5)
    recommended_courses = get_recommended_courses_for_user(request.user, limit=4)
    stats = {
        "course_count": enrollments.count(),
        "submission_count": submissions.count(),
        "average_score": submissions.aggregate(avg=Avg("score"))["avg"] or 0,
        "favorite_count": CourseFavorite.objects.filter(student=request.user).count(),
        "view_count": CourseViewLog.objects.filter(student=request.user).count(),
    }
    return render(
        request,
        "core/student_dashboard.html",
        {
            "enrollments": with_course_metrics(enrollments)[:6],
            "submissions": submissions[:5],
            "pending_assignments": pending_assignments,
            "announcements": Announcement.objects.filter(is_published=True)[:5],
            "favorite_courses": favorite_courses,
            "recent_courses": recent_courses,
            "recommended_courses": recommended_courses,
            "stats": stats,
        },
    )


@teacher_required
def teacher_dashboard(request):
    courses = with_course_metrics(
        Course.objects.filter(teacher=request.user).select_related("category").prefetch_related("tags")
    ).order_by("-heat_score", "-created_at")
    pending_reviews = AssignmentSubmission.objects.filter(
        assignment__created_by=request.user, reviewed_at__isnull=True
    ).select_related("assignment", "student")[:8]
    stats = {
        "course_count": courses.count(),
        "material_count": CourseMaterial.objects.filter(uploaded_by=request.user).count(),
        "discussion_count": DiscussionPost.objects.filter(course__teacher=request.user).count(),
        "view_count": CourseViewLog.objects.filter(course__teacher=request.user).count(),
        "favorite_count": CourseFavorite.objects.filter(course__teacher=request.user).count(),
    }
    return render(
        request,
        "core/teacher_dashboard.html",
        {
            "courses": courses[:6],
            "pending_reviews": pending_reviews,
            "stats": stats,
            "announcements": Announcement.objects.filter(is_published=True)[:5],
        },
    )


@admin_required
def admin_dashboard(request):
    hot_courses = get_hot_courses(limit=6)
    popular_tags = CourseTag.objects.annotate(course_total=Count("courses")).order_by("-course_total", "name")[:8]
    stats = {
        "user_count": User.objects.count(),
        "course_count": Course.objects.count(),
        "material_count": CourseMaterial.objects.count(),
        "assignment_count": Assignment.objects.count(),
        "discussion_count": DiscussionPost.objects.count(),
        "tag_count": CourseTag.objects.count(),
        "active_student_count": User.objects.filter(role=User.Roles.STUDENT, enrollments__isnull=False).distinct().count(),
    }
    return render(
        request,
        "core/admin_dashboard.html",
        {
            "stats": stats,
            "announcements": Announcement.objects.all()[:6],
            "banners": Banner.objects.all()[:6],
            "hot_courses": hot_courses,
            "popular_tags": popular_tags,
        },
    )


@admin_required
def announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "公告已发布。")
        return redirect("core:admin_dashboard")
    return render(request, "common/form.html", {"form": form, "title": "发布公告"})


@admin_required
def banner_create(request):
    form = BannerForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Banner 已创建。")
        return redirect("core:admin_dashboard")
    return render(request, "common/form.html", {"form": form, "title": "发布 Banner"})
