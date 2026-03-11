from django import forms

from .models import DiscussionComment, DiscussionPost


class DiscussionPostForm(forms.ModelForm):
    class Meta:
        model = DiscussionPost
        fields = ("course", "title", "content", "is_pinned")
        labels = {
            "course": "所属课程",
            "title": "帖子标题",
            "content": "帖子内容",
            "is_pinned": "置顶显示",
        }


class DiscussionCommentForm(forms.ModelForm):
    class Meta:
        model = DiscussionComment
        fields = ("content",)
        labels = {"content": "回复内容"}
