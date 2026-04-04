from django.conf import settings
from django.db import models

from courses.models import Course


class AttendanceSession(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "进行中"
        CLOSED = "closed", "已结束"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_sessions", verbose_name="课程")
    title = models.CharField("签到标题", max_length=200)
    description = models.TextField("签到说明", blank=True)
    status = models.CharField("签到状态", max_length=20, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_attendance_sessions", verbose_name="教师"
    )
    created_at = models.DateTimeField("发起时间", auto_now_add=True)

    class Meta:
        verbose_name = "签到活动"
        verbose_name_plural = "签到活动"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AttendanceRecord(models.Model):
    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="records", verbose_name="签到活动"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records", verbose_name="学生"
    )
    signed_at = models.DateTimeField("签到时间", auto_now_add=True)

    class Meta:
        verbose_name = "签到记录"
        verbose_name_plural = "签到记录"
        unique_together = ("session", "student")
        ordering = ["signed_at"]

    def __str__(self):
        return f"{self.student} - {self.session}"

