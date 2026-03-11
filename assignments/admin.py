from django.contrib import admin

from .models import Assignment, AssignmentSubmission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "due_date", "created_by")
    list_filter = ("course",)


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "score", "submitted_at", "reviewed_at")
    search_fields = ("student__username", "assignment__title")
