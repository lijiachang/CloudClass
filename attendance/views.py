from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import student_required, teacher_required
from courses.models import CourseEnrollment

from .forms import AttendanceSessionForm
from .models import AttendanceRecord, AttendanceSession


@teacher_required
def session_create(request):
    form = AttendanceSessionForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        session = form.save(commit=False)
        session.created_by = request.user
        session.save()
        messages.success(request, "签到已发起。")
        return redirect("attendance:session_detail", session_id=session.pk)
    return render(request, "common/form.html", {"form": form, "title": "发起签到"})


@teacher_required
def session_list(request):
    sessions = (
        AttendanceSession.objects.filter(created_by=request.user)
        .select_related("course")
        .annotate(signed_count=Count("records"))
    )
    return render(request, "attendance/session_list.html", {"sessions": sessions})


@teacher_required
def session_detail(request, session_id):
    session = get_object_or_404(
        AttendanceSession.objects.select_related("course", "created_by"),
        pk=session_id,
        created_by=request.user,
    )
    enrolled_students = list(CourseEnrollment.objects.filter(course=session.course).select_related("student"))
    records = {
        record.student_id: record
        for record in AttendanceRecord.objects.filter(session=session).select_related("student")
    }
    attendees = [item for item in enrolled_students if item.student_id in records]
    absentees = [item for item in enrolled_students if item.student_id not in records]
    return render(
        request,
        "attendance/session_detail.html",
        {
            "session": session,
            "attendees": attendees,
            "absentees": absentees,
            "signed_count": len(attendees),
            "total_count": len(enrolled_students),
        },
    )


@student_required
def sign_in(request, session_id):
    session = get_object_or_404(
        AttendanceSession.objects.select_related("course"),
        pk=session_id,
        status=AttendanceSession.Status.OPEN,
    )
    if not CourseEnrollment.objects.filter(course=session.course, student=request.user).exists():
        messages.error(request, "请先加入课程再签到。")
        return redirect("courses:detail", pk=session.course.pk)
    _, created = AttendanceRecord.objects.get_or_create(session=session, student=request.user)
    if created:
        messages.success(request, "签到成功。")
    else:
        messages.info(request, "你已经完成过本次签到。")
    return redirect("courses:detail", pk=session.course.pk)

