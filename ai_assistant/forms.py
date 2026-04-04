from django import forms

from assignments.models import Assignment
from courses.models import Course

from .models import AIInteractionLog


class TeacherAIAssistantForm(forms.Form):
    mode = forms.ChoiceField(label="AI 模式", choices=AIInteractionLog.Modes.choices)
    course = forms.ModelChoiceField(label="关联课程", queryset=Course.objects.none(), required=False)
    assignment = forms.ModelChoiceField(label="关联作业", queryset=Assignment.objects.none(), required=False)
    prompt = forms.CharField(
        label="输入内容",
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "请输入教学目标、课堂需求、评价要求等内容。"}),
    )

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            courses = Course.objects.filter(teacher=teacher).order_by("title")
            assignments = Assignment.objects.filter(created_by=teacher).select_related("course").order_by("title")
            self.fields["course"].queryset = courses
            self.fields["assignment"].queryset = assignments

