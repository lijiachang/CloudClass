from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Course, CourseCategory, CourseFavorite, CourseTag, CourseViewLog
from .services import get_recommended_courses_for_user


class CourseEnhancementTests(TestCase):
    def setUp(self):
        self.category = CourseCategory.objects.create(name="Python")
        self.tag_django = CourseTag.objects.create(name="Django")
        self.tag_ml = CourseTag.objects.create(name="机器学习")
        self.teacher = User.objects.create_user(
            username="teacherx",
            password="pass123456",
            full_name="教师甲",
            role=User.Roles.TEACHER,
        )
        self.student = User.objects.create_user(
            username="studentx",
            password="pass123456",
            full_name="学生甲",
            role=User.Roles.STUDENT,
        )
        self.course_a = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="Django 基础",
            summary="课程 A",
            description="课程 A 详情",
            status=Course.Status.PUBLISHED,
        )
        self.course_a.tags.add(self.tag_django)
        self.course_b = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="Django 进阶",
            summary="课程 B",
            description="课程 B 详情",
            status=Course.Status.PUBLISHED,
        )
        self.course_b.tags.add(self.tag_django)
        self.course_c = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="机器学习导论",
            summary="课程 C",
            description="课程 C 详情",
            status=Course.Status.PUBLISHED,
        )
        self.course_c.tags.add(self.tag_ml)

    def test_course_list_can_filter_by_tag(self):
        response = self.client.get(reverse("courses:list"), {"tag": self.tag_django.id})
        self.assertEqual(response.status_code, 200)
        filtered_titles = {course.title for course in response.context["courses"]}
        self.assertIn("Django 基础", filtered_titles)
        self.assertIn("Django 进阶", filtered_titles)
        self.assertNotIn("机器学习导论", filtered_titles)

    def test_favorite_toggle_creates_and_removes_favorite(self):
        self.client.login(username="studentx", password="pass123456")
        self.client.get(reverse("courses:favorite", args=[self.course_a.pk]))
        self.assertTrue(CourseFavorite.objects.filter(course=self.course_a, student=self.student).exists())
        self.client.get(reverse("courses:favorite", args=[self.course_a.pk]))
        self.assertFalse(CourseFavorite.objects.filter(course=self.course_a, student=self.student).exists())

    def test_view_log_created_on_detail_visit(self):
        self.client.login(username="studentx", password="pass123456")
        self.client.get(reverse("courses:detail", args=[self.course_a.pk]))
        self.assertTrue(CourseViewLog.objects.filter(course=self.course_a, student=self.student).exists())

    def test_recommendation_prefers_matching_tags(self):
        CourseViewLog.objects.create(course=self.course_a, student=self.student)
        recommended = list(get_recommended_courses_for_user(self.student, limit=5))
        self.assertIn(self.course_b, recommended)
