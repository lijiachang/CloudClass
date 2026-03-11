from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from accounts.decorators import admin_required, student_required, teacher_required
from assignments.models import Assignment, AssignmentSubmission
from courses.models import Course, CourseEnrollment
from discussions.models import DiscussionPost
from resources.models import CourseMaterial

from .forms import AnnouncementForm, BannerForm
from .models import Announcement, Banner


def home(request):
    context = {
        "banners": Banner.objects.filter(is_active=True)[:3],
        "announcements": Announcement.objects.filter(is_published=True)[:5],
        "courses": Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher")[:6],
    }
    return render(request, "core/home.html", context)


@login_required
def dashboard_redirect(request):
    return redirect(request.user.get_dashboard_url())


@student_required
def student_dashboard(request):
    enrollments = CourseEnrollment.objects.filter(student=request.user).select_related("course", "course__teacher")
    submissions = AssignmentSubmission.objects.filter(student=request.user).select_related("assignment", "assignment__course")
    pending_assignments = Assignment.objects.filter(course__enrollments__student=request.user).exclude(
        submissions__student=request.user
    )[:5]
    stats = {
        "course_count": enrollments.count(),
        "submission_count": submissions.count(),
        "average_score": submissions.aggregate(avg=Avg("score"))["avg"] or 0,
    }
    return render(
        request,
        "core/student_dashboard.html",
        {
            "enrollments": enrollments,
            "submissions": submissions[:5],
            "pending_assignments": pending_assignments,
            "announcements": Announcement.objects.filter(is_published=True)[:5],
            "stats": stats,
        },
    )


@teacher_required
def teacher_dashboard(request):
    courses = Course.objects.filter(teacher=request.user).annotate(student_count=Count("enrollments"))
    pending_reviews = AssignmentSubmission.objects.filter(
        assignment__created_by=request.user, reviewed_at__isnull=True
    ).select_related("assignment", "student")[:8]
    stats = {
        "course_count": courses.count(),
        "material_count": CourseMaterial.objects.filter(uploaded_by=request.user).count(),
        "discussion_count": DiscussionPost.objects.filter(course__teacher=request.user).count(),
    }
    return render(
        request,
        "core/teacher_dashboard.html",
        {
            "courses": courses,
            "pending_reviews": pending_reviews,
            "stats": stats,
            "announcements": Announcement.objects.filter(is_published=True)[:5],
        },
    )


@admin_required
def admin_dashboard(request):
    stats = {
        "user_count": request.user.__class__.objects.count(),
        "course_count": Course.objects.count(),
        "material_count": CourseMaterial.objects.count(),
        "assignment_count": Assignment.objects.count(),
        "discussion_count": DiscussionPost.objects.count(),
    }
    return render(
        request,
        "core/admin_dashboard.html",
        {
            "stats": stats,
            "announcements": Announcement.objects.all()[:6],
            "banners": Banner.objects.all()[:6],
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
