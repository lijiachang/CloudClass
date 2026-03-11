from django.contrib import admin

from .models import CourseMaterial


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "material_type", "uploaded_by", "created_at")
    list_filter = ("material_type",)
    search_fields = ("title", "description")
