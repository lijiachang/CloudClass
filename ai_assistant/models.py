from django.conf import settings
from django.db import models

from assignments.models import Assignment, AssignmentSubmission
from courses.models import Course


class AIInteractionLog(models.Model):
    class Modes(models.TextChoices):
        LESSON_PREP = "lesson_prep", "AI 备课"
        LESSON_TEACHING = "lesson_teaching", "AI 授课"
        EVALUATION = "evaluation", "AI 评价"
        GRADING = "grading", "AI 辅助批阅"
        PLAGIARISM = "plagiarism", "AI 查重"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_logs", verbose_name="教师"
    )
    mode = models.CharField("AI 模式", max_length=32, choices=Modes.choices)
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, blank=True, null=True, related_name="ai_logs", verbose_name="课程"
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ai_logs",
        verbose_name="作业",
    )
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ai_logs",
        verbose_name="作业提交",
    )
    prompt = models.TextField("输入内容")
    response = models.TextField("AI 输出")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "AI 交互记录"
        verbose_name_plural = "AI 交互记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_mode_display()} - {self.teacher}"

