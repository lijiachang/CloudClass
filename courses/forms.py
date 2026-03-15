from django import forms

from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("category", "tags", "title", "cover", "summary", "description", "status")
        labels = {
            "category": "课程分类",
            "tags": "课程标签",
            "title": "课程名称",
            "cover": "课程封面",
            "summary": "课程简介",
            "description": "课程详情",
            "status": "课程状态",
        }
        widgets = {
            "tags": forms.CheckboxSelectMultiple,
        }
