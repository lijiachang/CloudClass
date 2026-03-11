from django.contrib import admin

from .models import DiscussionComment, DiscussionPost


class DiscussionCommentInline(admin.TabularInline):
    model = DiscussionComment
    extra = 0


@admin.register(DiscussionPost)
class DiscussionPostAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "author", "is_pinned", "created_at")
    list_filter = ("is_pinned", "course")
    inlines = [DiscussionCommentInline]
