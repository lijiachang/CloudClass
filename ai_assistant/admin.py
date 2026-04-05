from django.contrib import admin

from .models import AIInteractionLog, StudentAIChatMessage


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ("mode", "teacher", "course", "assignment", "created_at")
    list_filter = ("mode",)
    search_fields = ("teacher__full_name", "prompt", "response")


@admin.register(StudentAIChatMessage)
class StudentAIChatMessageAdmin(admin.ModelAdmin):
    list_display = ("student", "created_at")
    search_fields = ("student__full_name", "question", "answer")
