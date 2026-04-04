from django.conf import settings
from django.db import models

from courses.models import Course


class CourseGroup(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_groups", verbose_name="课程")
    name = models.CharField("小组名称", max_length=100)
    description = models.TextField("小组说明", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_course_groups", verbose_name="教师"
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "课程小组"
        verbose_name_plural = "课程小组"
        ordering = ["created_at"]
        unique_together = ("course", "name")

    def __str__(self):
        return f"{self.course} - {self.name}"


class CourseGroupMember(models.Model):
    group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name="members", verbose_name="小组")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_group_memberships", verbose_name="学生"
    )
    joined_at = models.DateTimeField("加入时间", auto_now_add=True)

    class Meta:
        verbose_name = "小组成员"
        verbose_name_plural = "小组成员"
        unique_together = ("group", "student")

    def __str__(self):
        return f"{self.student} -> {self.group}"

