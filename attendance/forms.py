from django import forms

from courses.models import Course

from .models import AttendanceSession


class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ("course", "title", "description", "status")
        labels = {
            "course": "所属课程",
            "title": "签到标题",
            "description": "签到说明",
            "status": "签到状态",
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields["course"].queryset = Course.objects.filter(teacher=teacher)

