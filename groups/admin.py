from django.contrib import admin

from .models import CourseGroup, CourseGroupMember


class CourseGroupMemberInline(admin.TabularInline):
    model = CourseGroupMember
    extra = 0


@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "created_by", "created_at")
    inlines = [CourseGroupMemberInline]

