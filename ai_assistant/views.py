from django.contrib import messages
from django.shortcuts import get_object_or_404, render

from accounts.decorators import teacher_required
from assignments.models import Assignment, AssignmentSubmission

from .forms import TeacherAIAssistantForm
from .models import AIInteractionLog
from .services import TeacherAIService


@teacher_required
def assistant_center(request):
    result = None
    plagiarism_result = None
    form = TeacherAIAssistantForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        mode = form.cleaned_data["mode"]
        course = form.cleaned_data["course"]
        assignment = form.cleaned_data["assignment"]
        prompt = form.cleaned_data["prompt"]
        if mode == AIInteractionLog.Modes.PLAGIARISM:
            if not assignment:
                messages.error(request, "AI 查重模式需要先选择作业。")
            else:
                plagiarism_result = TeacherAIService.analyze_similarity(assignment)
                AIInteractionLog.objects.create(
                    teacher=request.user,
                    mode=mode,
                    course=course or assignment.course,
                    assignment=assignment,
                    prompt=prompt or f"查重作业：{assignment.title}",
                    response=plagiarism_result["content"],
                )
        else:
            result = TeacherAIService.generate(mode, prompt)
            AIInteractionLog.objects.create(
                teacher=request.user,
                mode=mode,
                course=course,
                assignment=assignment,
                prompt=prompt,
                response=result["content"],
            )
    recent_logs = AIInteractionLog.objects.filter(teacher=request.user).select_related("course", "assignment")[:8]
    return render(
        request,
        "ai_assistant/center.html",
        {"form": form, "result": result, "plagiarism_result": plagiarism_result, "recent_logs": recent_logs},
    )


@teacher_required
def generate_review_suggestion(request, submission_id):
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related("assignment", "student", "assignment__course"),
        pk=submission_id,
        assignment__created_by=request.user,
    )
    prompt = (
        f"课程：{submission.assignment.course.title}\n"
        f"作业：{submission.assignment.title}\n"
        f"作业说明：{submission.assignment.description}\n"
        f"学生：{submission.student.full_name}\n"
        f"提交说明：{submission.content or '无'}\n"
        f"是否有附件：{'有' if submission.attachment else '无'}"
    )
    result = TeacherAIService.generate(AIInteractionLog.Modes.GRADING, prompt)
    AIInteractionLog.objects.create(
        teacher=request.user,
        mode=AIInteractionLog.Modes.GRADING,
        course=submission.assignment.course,
        assignment=submission.assignment,
        submission=submission,
        prompt=prompt,
        response=result["content"],
    )
    return render(
        request,
        "ai_assistant/review_suggestion.html",
        {"submission": submission, "result": result},
    )

