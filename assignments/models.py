from django.conf import settings
from django.db import models

from courses.models import Course


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments", verbose_name="所属课程")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_assignments", verbose_name="发布教师")
    title = models.CharField("作业标题", max_length=200)
    description = models.TextField("作业说明")
    attachment = models.FileField("附件", upload_to="assignments/", blank=True, null=True)
    due_date = models.DateTimeField("截止时间")
    created_at = models.DateTimeField("发布时间", auto_now_add=True)

    class Meta:
        verbose_name = "作业"
        verbose_name_plural = "作业"
        ordering = ["due_date"]

    def __str__(self):
        return self.title


class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions", verbose_name="所属作业")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_submissions", verbose_name="学生")
    content = models.TextField("提交说明", blank=True)
    attachment = models.FileField("提交附件", upload_to="assignment_submissions/", blank=True, null=True)
    score = models.DecimalField("分数", max_digits=5, decimal_places=2, blank=True, null=True)
    feedback = models.TextField("教师评语", blank=True)
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True)
    reviewed_at = models.DateTimeField("批改时间", blank=True, null=True)

    class Meta:
        verbose_name = "作业提交"
        verbose_name_plural = "作业提交"
        unique_together = ("assignment", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment}"
