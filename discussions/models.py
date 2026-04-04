from django.conf import settings
from django.db import models

from courses.models import Course


class DiscussionPost(models.Model):
    class PostTypes(models.TextChoices):
        GENERAL = "general", "普通讨论"
        CLASSROOM = "classroom", "课堂讨论"
        GROUP = "group", "分组讨论"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="posts", verbose_name="所属课程")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discussion_posts", verbose_name="作者")
    post_type = models.CharField("讨论类型", max_length=20, choices=PostTypes.choices, default=PostTypes.GENERAL)
    title = models.CharField("帖子标题", max_length=200)
    content = models.TextField("帖子内容")
    is_pinned = models.BooleanField("是否置顶", default=False)
    created_at = models.DateTimeField("发布时间", auto_now_add=True)

    class Meta:
        verbose_name = "讨论帖子"
        verbose_name_plural = "讨论帖子"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class DiscussionComment(models.Model):
    post = models.ForeignKey(DiscussionPost, on_delete=models.CASCADE, related_name="comments", verbose_name="所属帖子")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discussion_comments", verbose_name="作者")
    content = models.TextField("评论内容")
    created_at = models.DateTimeField("评论时间", auto_now_add=True)

    class Meta:
        verbose_name = "帖子评论"
        verbose_name_plural = "帖子评论"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} - {self.post}"
