from django import forms
from django.utils import timezone

from courses.models import Course

from .models import Assignment, AssignmentSubmission


class AssignmentForm(forms.ModelForm):
    due_date = forms.DateTimeField(
        label="截止时间",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        initial=timezone.now,
    )

    class Meta:
        model = Assignment
        fields = ("course", "title", "description", "attachment", "due_date")
        labels = {
            "course": "所属课程",
            "title": "作业标题",
            "description": "作业说明",
            "attachment": "附件",
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields["course"].queryset = Course.objects.filter(teacher=teacher)


class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ("content", "attachment")
        labels = {
            "content": "提交说明",
            "attachment": "提交附件",
        }


class ReviewForm(forms.ModelForm):
    score = forms.DecimalField(label="得分", max_digits=5, decimal_places=2, required=False)
    feedback = forms.CharField(label="教师评语", required=False, widget=forms.Textarea(attrs={"rows": 5}))

    class Meta:
        model = AssignmentSubmission
        fields = ("score", "feedback")
