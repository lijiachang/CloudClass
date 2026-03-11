from django.contrib import admin

from .models import Course, CourseCategory, CourseEnrollment


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "summary")


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "created_at")
