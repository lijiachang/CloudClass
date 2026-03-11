from django import forms

from courses.models import Course

from .models import CourseMaterial


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = ("course", "title", "material_type", "description", "file", "external_url")
        labels = {
            "course": "所属课程",
            "title": "资料标题",
            "material_type": "资料类型",
            "description": "资料说明",
            "file": "上传文件",
            "external_url": "外部链接",
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields["course"].queryset = Course.objects.filter(teacher=teacher)
