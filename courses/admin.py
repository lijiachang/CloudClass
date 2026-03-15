from django.contrib import admin

from .models import Course, CourseCategory, CourseEnrollment, CourseFavorite, CourseTag, CourseViewLog


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(CourseTag)
class CourseTagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "summary")
    filter_horizontal = ("tags",)


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "created_at")


@admin.register(CourseViewLog)
class CourseViewLogAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "created_at")
    list_filter = ("course",)


@admin.register(CourseFavorite)
class CourseFavoriteAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "created_at")
    list_filter = ("course",)
