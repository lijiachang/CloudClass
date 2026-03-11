from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import teacher_required
from assignments.models import AssignmentSubmission
from discussions.models import DiscussionPost
from resources.models import CourseMaterial

from .forms import CourseForm
from .models import Course, CourseEnrollment


def course_list(request):
    courses = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category")
    return render(request, "courses/course_list.html", {"courses": courses})


def course_detail(request, pk):
    course = get_object_or_404(Course.objects.select_related("teacher", "category"), pk=pk)
    is_enrolled = request.user.is_authenticated and (
        request.user.is_teacher
        or request.user.is_platform_admin
        or CourseEnrollment.objects.filter(course=course, student=request.user).exists()
    )
    context = {
        "course": course,
        "is_enrolled": is_enrolled,
        "materials": CourseMaterial.objects.filter(course=course),
        "assignments": course.assignments.all(),
        "posts": DiscussionPost.objects.filter(course=course).select_related("author")[:5],
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


@teacher_required
def teacher_course_list(request):
    courses = Course.objects.filter(teacher=request.user).annotate(student_count=Count("enrollments"))
    return render(request, "courses/teacher_course_list.html", {"courses": courses})


@teacher_required
def teacher_course_create(request):
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.teacher = request.user
        course.save()
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
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    submissions = AssignmentSubmission.objects.filter(assignment__course=course)
    stats = {
        "student_count": course.enrollments.count(),
        "material_count": CourseMaterial.objects.filter(course=course).count(),
        "discussion_count": DiscussionPost.objects.filter(course=course).count(),
        "submission_rate": round(
            (submissions.count() / max(course.enrollments.count(), 1)) * 100,
            1,
        ),
        "average_score": submissions.aggregate(avg=Avg("score"))["avg"] or 0,
    }
    return render(request, "courses/teacher_course_analytics.html", {"course": course, "stats": stats})
