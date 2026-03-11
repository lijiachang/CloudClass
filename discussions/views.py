from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import CourseEnrollment

from .forms import DiscussionCommentForm, DiscussionPostForm
from .models import DiscussionComment, DiscussionPost


@login_required
def post_create(request, course_id=None):
    initial = {"course": course_id} if course_id else None
    form = DiscussionPostForm(request.POST or None, initial=initial)
    if request.user.is_student:
        form.fields["is_pinned"].widget = forms.HiddenInput()  # type: ignore[name-defined]
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        if request.user.is_student and not CourseEnrollment.objects.filter(course=post.course, student=request.user).exists():
            messages.error(request, "请先加入课程再参与讨论。")
            return redirect("courses:detail", pk=post.course.pk)
        post.author = request.user
        if request.user.is_student:
            post.is_pinned = False
        post.save()
        messages.success(request, "帖子发布成功。")
        return redirect("discussions:detail", pk=post.pk)
    return render(request, "common/form.html", {"form": form, "title": "发布讨论帖"})


def post_detail(request, pk):
    post = get_object_or_404(DiscussionPost.objects.select_related("course", "author"), pk=pk)
    form = DiscussionCommentForm(request.POST or None)
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if form.is_valid():
            DiscussionComment.objects.create(post=post, author=request.user, content=form.cleaned_data["content"])
            messages.success(request, "评论已发布。")
            return redirect("discussions:detail", pk=pk)
    return render(request, "discussions/post_detail.html", {"post": post, "form": form})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(DiscussionPost, pk=pk)
    if request.user != post.author and not request.user.is_teacher and not request.user.is_platform_admin:
        messages.error(request, "你无权删除该帖子。")
        return redirect("discussions:detail", pk=pk)
    course_id = post.course.pk
    post.delete()
    messages.success(request, "帖子已删除。")
    return redirect("courses:detail", pk=course_id)
