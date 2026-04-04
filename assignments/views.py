import csv

from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import student_required, teacher_required
from courses.models import CourseEnrollment

from .forms import AssignmentForm, AssignmentSubmissionForm, ReviewForm
from .models import Assignment, AssignmentSubmission


@teacher_required
def assignment_create(request):
    form = AssignmentForm(request.POST or None, request.FILES or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.created_by = request.user
        assignment.save()
        messages.success(request, "作业已发布。")
        return redirect("courses:detail", pk=assignment.course.pk)
    return render(request, "common/form.html", {"form": form, "title": "发布作业"})


@student_required
def assignment_submit(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    if not CourseEnrollment.objects.filter(course=assignment.course, student=request.user).exists():
        messages.error(request, "请先加入课程再提交作业。")
        return redirect("courses:detail", pk=assignment.course.pk)
    submission = AssignmentSubmission.objects.filter(assignment=assignment, student=request.user).first()
    form = AssignmentSubmissionForm(request.POST or None, request.FILES or None, instance=submission)
    if request.method == "POST" and form.is_valid():
        submission = form.save(commit=False)
        submission.assignment = assignment
        submission.student = request.user
        submission.save()
        messages.success(request, "作业已提交。")
        return redirect("core:student_dashboard")
    return render(
        request,
        "assignments/submit.html",
        {"form": form, "assignment": assignment, "submission": submission},
    )


@teacher_required
def assignment_review_list(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)
    submissions = assignment.submissions.select_related("student")
    return render(request, "assignments/review_list.html", {"assignment": assignment, "submissions": submissions})


@teacher_required
def assignment_review(request, submission_id):
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related("assignment", "student"),
        pk=submission_id,
        assignment__created_by=request.user,
    )
    form = ReviewForm(request.POST or None, instance=submission)
    if request.method == "POST" and form.is_valid():
        reviewed = form.save(commit=False)
        reviewed.reviewed_at = timezone.now()
        reviewed.save()
        messages.success(request, "作业已批改。")
        return redirect("assignments:review_list", pk=submission.assignment.pk)
    return render(
        request,
        "assignments/review_form.html",
        {"form": form, "submission": submission, "title": f"批改作业：{submission.assignment.title}"},
    )


@teacher_required
def export_scores(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)
    submissions = assignment.submissions.select_related("student").order_by("student__username")
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{assignment.title}-scores.csv"'
    writer = csv.writer(response)
    writer.writerow(["学生姓名", "学号/工号", "用户名", "提交时间", "附件状态", "分数", "教师评语", "批改时间"])
    for submission in submissions:
        writer.writerow(
            [
                submission.student.full_name,
                submission.student.school_id,
                submission.student.username,
                timezone.localtime(submission.submitted_at).strftime("%Y-%m-%d %H:%M"),
                "有附件" if submission.attachment else "无附件",
                submission.score or "",
                submission.feedback,
                timezone.localtime(submission.reviewed_at).strftime("%Y-%m-%d %H:%M") if submission.reviewed_at else "",
            ]
        )
    return response
