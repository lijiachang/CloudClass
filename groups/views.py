from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import teacher_required

from .forms import CourseGroupForm, CourseGroupMemberForm
from .models import CourseGroup, CourseGroupMember


@teacher_required
def group_list(request):
    groups = CourseGroup.objects.filter(created_by=request.user).select_related("course").prefetch_related("members__student")
    return render(request, "groups/group_list.html", {"groups": groups})


@teacher_required
def group_create(request):
    form = CourseGroupForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.created_by = request.user
        group.save()
        messages.success(request, "课程小组已创建。")
        return redirect("groups:group_detail", group_id=group.pk)
    return render(request, "common/form.html", {"form": form, "title": "创建课程小组"})


@teacher_required
def group_detail(request, group_id):
    group = get_object_or_404(
        CourseGroup.objects.select_related("course", "created_by").prefetch_related("members__student"),
        pk=group_id,
        created_by=request.user,
    )
    form = CourseGroupMemberForm(request.POST or None, group=group)
    if request.method == "POST" and form.is_valid():
        student = form.cleaned_data["student"]
        _, created = CourseGroupMember.objects.get_or_create(group=group, student=student)
        if created:
            messages.success(request, "学生已加入小组。")
        else:
            messages.info(request, "该学生已经在当前小组中。")
        return redirect("groups:group_detail", group_id=group.pk)
    return render(request, "groups/group_detail.html", {"group": group, "form": form})


@teacher_required
def member_remove(request, member_id):
    member = get_object_or_404(CourseGroupMember.objects.select_related("group"), pk=member_id, group__created_by=request.user)
    group_id = member.group_id
    member.delete()
    messages.success(request, "小组成员已移除。")
    return redirect("groups:group_detail", group_id=group_id)
