from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "full_name", "role", "school_id", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("扩展信息", {"fields": ("full_name", "role", "school_id", "phone", "avatar", "bio", "created_at")}),
    )
    readonly_fields = ("created_at",)
