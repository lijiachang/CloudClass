from django import forms
from django.contrib.auth import get_user_model

from courses.models import CourseEnrollment

from .models import CourseGroup, CourseGroupMember


class CourseGroupForm(forms.ModelForm):
    class Meta:
        model = CourseGroup
        fields = ("course", "name", "description")
        labels = {"course": "所属课程", "name": "小组名称", "description": "小组说明"}

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields["course"].queryset = teacher.teaching_courses.all().order_by("title")


class CourseGroupMemberForm(forms.ModelForm):
    class Meta:
        model = CourseGroupMember
        fields = ("student",)
        labels = {"student": "学生"}

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group is not None:
            taken_ids = CourseGroupMember.objects.filter(group__course=group.course).values_list("student_id", flat=True)
            student_ids = list(
                CourseEnrollment.objects.filter(course=group.course)
                .exclude(student_id__in=taken_ids)
                .values_list("student_id", flat=True)
            )
            self.fields["student"].queryset = get_user_model().objects.filter(pk__in=student_ids).order_by("username")
