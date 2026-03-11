from django.conf import settings
from django.db import models

from courses.models import Course


class CourseMaterial(models.Model):
    class MaterialTypes(models.TextChoices):
        DOCUMENT = "document", "文档"
        VIDEO = "video", "视频"
        LINK = "link", "外部链接"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials", verbose_name="所属课程")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_materials", verbose_name="上传教师")
    title = models.CharField("资料标题", max_length=200)
    material_type = models.CharField("资料类型", max_length=20, choices=MaterialTypes.choices, default=MaterialTypes.DOCUMENT)
    description = models.TextField("资料说明", blank=True)
    file = models.FileField("文件", upload_to="materials/", blank=True, null=True)
    external_url = models.URLField("外部链接", blank=True)
    created_at = models.DateTimeField("上传时间", auto_now_add=True)

    class Meta:
        verbose_name = "教学资料"
        verbose_name_plural = "教学资料"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
