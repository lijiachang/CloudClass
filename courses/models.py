from django.conf import settings
from django.db import models
from django.urls import reverse


class CourseCategory(models.Model):
    name = models.CharField("分类名称", max_length=100, unique=True)
    description = models.TextField("分类说明", blank=True)

    class Meta:
        verbose_name = "课程分类"
        verbose_name_plural = "课程分类"

    def __str__(self):
        return self.name


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"

    category = models.ForeignKey(
        CourseCategory, on_delete=models.SET_NULL, blank=True, null=True, related_name="courses", verbose_name="分类"
    )
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teaching_courses", verbose_name="授课教师")
    title = models.CharField("课程名称", max_length=200)
    cover = models.ImageField("课程封面", upload_to="course_covers/", blank=True, null=True)
    summary = models.CharField("课程简介", max_length=255)
    description = models.TextField("课程详情", blank=True)
    status = models.CharField("课程状态", max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "课程"
        verbose_name_plural = "课程"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("courses:detail", args=[self.pk])

    @property
    def enrollment_count(self):
        return self.enrollments.count()


class CourseEnrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments", verbose_name="课程")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments", verbose_name="学生")
    created_at = models.DateTimeField("加入时间", auto_now_add=True)

    class Meta:
        verbose_name = "选课记录"
        verbose_name_plural = "选课记录"
        unique_together = ("course", "student")

    def __str__(self):
        return f"{self.student} -> {self.course}"
