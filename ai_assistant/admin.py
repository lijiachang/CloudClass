from django.contrib import admin

from .models import AIInteractionLog


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ("mode", "teacher", "course", "assignment", "created_at")
    list_filter = ("mode",)
    search_fields = ("teacher__full_name", "prompt", "response")

