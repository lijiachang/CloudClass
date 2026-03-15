from django.db.models import Count, F, IntegerField, Q, Value
from django.db.models.functions import Coalesce

from .models import Course, CourseEnrollment, CourseFavorite, CourseViewLog


def with_course_metrics(queryset):
    return queryset.annotate(
        enrollment_count=Count("enrollments", distinct=True),
        view_count=Count("view_logs", distinct=True),
        favorite_count=Count("favorites", distinct=True),
        discussion_count=Count("posts", distinct=True),
        material_count=Count("materials", distinct=True),
        submission_count=Count("assignments__submissions", distinct=True),
    ).annotate(
        heat_score=Coalesce(F("view_count"), Value(0), output_field=IntegerField())
        + Coalesce(F("favorite_count"), Value(0), output_field=IntegerField()) * 2
        + Coalesce(F("enrollment_count"), Value(0), output_field=IntegerField()) * 3
    )


def get_hot_courses(limit=6):
    queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category").prefetch_related("tags")
    return with_course_metrics(queryset).order_by("-heat_score", "-discussion_count", "-created_at")[:limit]


def get_active_courses(limit=6):
    queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category").prefetch_related("tags")
    return with_course_metrics(queryset).order_by("-discussion_count", "-submission_count", "-material_count", "-created_at")[:limit]


def get_latest_courses(limit=6):
    queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category").prefetch_related("tags")
    return with_course_metrics(queryset).order_by("-created_at")[:limit]


def get_recently_viewed_courses(user, limit=6):
    course_ids = list(
        CourseViewLog.objects.filter(student=user).order_by("-created_at").values_list("course_id", flat=True).distinct()[:limit]
    )
    courses = {
        course.id: course
        for course in with_course_metrics(
            Course.objects.filter(id__in=course_ids).select_related("teacher", "category").prefetch_related("tags")
        )
    }
    return [courses[course_id] for course_id in course_ids if course_id in courses]


def get_favorite_courses(user, limit=6):
    course_ids = list(
        CourseFavorite.objects.filter(student=user).order_by("-created_at").values_list("course_id", flat=True)[:limit]
    )
    courses = {
        course.id: course
        for course in with_course_metrics(
            Course.objects.filter(id__in=course_ids).select_related("teacher", "category").prefetch_related("tags")
        )
    }
    return [courses[course_id] for course_id in course_ids if course_id in courses]


def get_recommended_courses_for_user(user, limit=6):
    base_queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category").prefetch_related("tags")
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_student", False):
        return get_hot_courses(limit=limit)

    tag_ids = set(
        Course.objects.filter(enrollments__student=user).values_list("tags__id", flat=True)
    ) | set(
        Course.objects.filter(favorites__student=user).values_list("tags__id", flat=True)
    ) | set(
        Course.objects.filter(view_logs__student=user).values_list("tags__id", flat=True)
    )
    tag_ids.discard(None)

    interacted_course_ids = set(CourseEnrollment.objects.filter(student=user).values_list("course_id", flat=True)) | set(
        CourseFavorite.objects.filter(student=user).values_list("course_id", flat=True)
    )

    queryset = with_course_metrics(base_queryset.exclude(id__in=interacted_course_ids))
    if tag_ids:
        return queryset.annotate(
            matched_tag_count=Count("tags", filter=Q(tags__in=tag_ids), distinct=True)
        ).filter(matched_tag_count__gt=0).order_by("-matched_tag_count", "-heat_score", "-created_at")[:limit]

    return queryset.order_by("-heat_score", "-created_at")[:limit]
