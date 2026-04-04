from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import student_required, teacher_required
from assignments.models import AssignmentSubmission
from attendance.models import AttendanceRecord, AttendanceSession
from discussions.models import DiscussionPost
from groups.models import CourseGroup
from resources.models import CourseMaterial

from .forms import CourseForm
from .models import Course, CourseCategory, CourseEnrollment, CourseFavorite, CourseTag, CourseViewLog
from .services import (
    get_active_courses,
    get_favorite_courses,
    get_hot_courses,
    get_latest_courses,
    get_recently_viewed_courses,
    get_recommended_courses_for_user,
    with_course_metrics,
)


def course_list(request):
    keyword = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    tag_id = request.GET.get("tag", "").strip()

    courses = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category").prefetch_related("tags")
    if keyword:
        courses = courses.filter(title__icontains=keyword)
    if category_id:
        courses = courses.filter(category_id=category_id)
    if tag_id:
        courses = courses.filter(tags__id=tag_id)

    discovered_courses = with_course_metrics(courses).distinct().order_by("-heat_score", "-created_at")
    context = {
        "courses": discovered_courses,
        "latest_courses": get_latest_courses(limit=6),
        "hot_courses": get_hot_courses(limit=6),
        "recommended_courses": get_recommended_courses_for_user(request.user, limit=6),
        "categories": CourseCategory.objects.all(),
        "tags": CourseTag.objects.all(),
        "active_category": category_id,
        "active_tag": tag_id,
        "keyword": keyword,
    }
    return render(request, "courses/course_list.html", context)


def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.select_related("teacher", "category").prefetch_related("tags"),
        pk=pk,
    )
    if request.user.is_authenticated and request.user.is_student:
        CourseViewLog.objects.create(course=course, student=request.user)

    is_enrolled = request.user.is_authenticated and (
        request.user.is_teacher
        or request.user.is_platform_admin
        or CourseEnrollment.objects.filter(course=course, student=request.user).exists()
    )
    is_favorite = request.user.is_authenticated and request.user.is_student and CourseFavorite.objects.filter(
        course=course, student=request.user
    ).exists()
    related_courses = (
        with_course_metrics(
            Course.objects.filter(status=Course.Status.PUBLISHED, tags__in=course.tags.all())
            .exclude(pk=course.pk)
            .select_related("teacher", "category")
            .prefetch_related("tags")
        )
        .distinct()
        .order_by("-heat_score", "-created_at")[:4]
    )
    context = {
        "course": course,
        "is_enrolled": is_enrolled,
        "is_favorite": is_favorite,
        "materials": CourseMaterial.objects.filter(course=course),
        "assignments": course.assignments.all(),
        "posts": DiscussionPost.objects.filter(course=course).select_related("author")[:5],
        "groups": CourseGroup.objects.filter(course=course).prefetch_related("members__student"),
        "attendance_sessions": AttendanceSession.objects.filter(course=course)[:5],
        "related_courses": related_courses,
        "favorite_count": CourseFavorite.objects.filter(course=course).count(),
        "view_count": CourseViewLog.objects.filter(course=course).count(),
        "signed_session_ids": set(
            AttendanceRecord.objects.filter(session__course=course, student=request.user).values_list("session_id", flat=True)
        )
        if request.user.is_authenticated and request.user.is_student
        else set(),
    }
    return render(request, "courses/course_detail.html", context)


@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk, status=Course.Status.PUBLISHED)
    if not request.user.is_student:
        messages.error(request, "只有学生可以加入课程。")
        return redirect(course.get_absolute_url())
    CourseEnrollment.objects.get_or_create(course=course, student=request.user)
    messages.success(request, f"你已成功加入《{course.title}》。")
    return redirect(course.get_absolute_url())


@student_required
def toggle_favorite_course(request, pk):
    course = get_object_or_404(Course, pk=pk, status=Course.Status.PUBLISHED)
    favorite, created = CourseFavorite.objects.get_or_create(course=course, student=request.user)
    if created:
        messages.success(request, f"已收藏《{course.title}》。")
    else:
        favorite.delete()
        messages.info(request, f"已取消收藏《{course.title}》。")
    return redirect(request.META.get("HTTP_REFERER") or course.get_absolute_url())


@student_required
def recommendation_center(request):
    context = {
        "recommended_courses": get_recommended_courses_for_user(request.user, limit=8),
        "recent_courses": get_recently_viewed_courses(request.user, limit=6),
        "favorite_courses": get_favorite_courses(request.user, limit=6),
        "hot_courses": get_hot_courses(limit=6),
        "active_courses": get_active_courses(limit=6),
    }
    return render(request, "courses/recommendation_center.html", context)


@teacher_required
def teacher_course_list(request):
    courses = with_course_metrics(
        Course.objects.filter(teacher=request.user).select_related("category").prefetch_related("tags")
    ).order_by("-created_at")
    return render(request, "courses/teacher_course_list.html", {"courses": courses})


@teacher_required
def teacher_course_create(request):
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.teacher = request.user
        course.save()
        form.save_m2m()
        messages.success(request, "课程已创建。")
        return redirect("courses:teacher_list")
    return render(request, "common/form.html", {"form": form, "title": "创建课程"})


@teacher_required
def teacher_course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "课程已更新。")
        return redirect("courses:teacher_list")
    return render(request, "common/form.html", {"form": form, "title": "编辑课程"})


@teacher_required
def teacher_course_analytics(request, pk):
    course = get_object_or_404(
        with_course_metrics(
            Course.objects.filter(pk=pk, teacher=request.user).select_related("category").prefetch_related("tags")
        ),
        pk=pk,
    )
    submissions = AssignmentSubmission.objects.filter(assignment__course=course)
    stats = {
        "student_count": course.enrollment_count,
        "material_count": course.material_count,
        "discussion_count": course.discussion_count,
        "view_count": course.view_count,
        "favorite_count": course.favorite_count,
        "submission_rate": round((submissions.count() / max(course.enrollment_count, 1)) * 100, 1),
        "average_score": submissions.aggregate(avg=Avg("score"))["avg"] or 0,
    }
    return render(request, "courses/teacher_course_analytics.html", {"course": course, "stats": stats})
