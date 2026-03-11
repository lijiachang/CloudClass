from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    class Roles(models.TextChoices):
        STUDENT = "student", "学生"
        TEACHER = "teacher", "教师"
        ADMIN = "admin", "管理员"

    role = models.CharField("角色", max_length=20, choices=Roles.choices, default=Roles.STUDENT)
    full_name = models.CharField("姓名", max_length=100)
    school_id = models.CharField("学号/工号", max_length=32, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    avatar = models.ImageField("头像", upload_to="avatars/", blank=True, null=True)
    bio = models.TextField("个人简介", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return f"{self.full_name or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.username
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Roles.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Roles.TEACHER

    @property
    def is_platform_admin(self):
        return self.role == self.Roles.ADMIN or self.is_superuser

    def get_dashboard_url(self):
        if self.is_platform_admin:
            return reverse("core:admin_dashboard")
        if self.is_teacher:
            return reverse("core:teacher_dashboard")
        return reverse("core:student_dashboard")
