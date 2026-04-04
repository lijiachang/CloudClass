from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "status", "created_by", "created_at")
    list_filter = ("status",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "signed_at")

