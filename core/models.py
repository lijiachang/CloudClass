from django.db import models


class Announcement(models.Model):
    title = models.CharField("公告标题", max_length=200)
    content = models.TextField("公告内容")
    is_published = models.BooleanField("是否发布", default=True)
    created_at = models.DateTimeField("发布时间", auto_now_add=True)

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = "公告"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Banner(models.Model):
    title = models.CharField("Banner 标题", max_length=200)
    subtitle = models.CharField("副标题", max_length=255, blank=True)
    image = models.ImageField("Banner 图片", upload_to="banners/", blank=True, null=True)
    link = models.URLField("跳转链接", blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "Banner"
        verbose_name_plural = "Banner"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
