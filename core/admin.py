from django.contrib import admin

from .models import Announcement, Banner


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "created_at")


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
