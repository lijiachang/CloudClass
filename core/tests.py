from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from assignments.models import Assignment
from core.models import Announcement
from courses.models import Course, CourseCategory, CourseEnrollment


class PlatformFlowTests(TestCase):
    def setUp(self):
        self.category = CourseCategory.objects.create(name="测试分类")
        self.teacher = User.objects.create_user(
            username="teacher",
            password="pass123456",
            full_name="测试教师",
            role=User.Roles.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            password="pass123456",
            full_name="测试学生",
            role=User.Roles.STUDENT,
        )
        self.admin = User.objects.create_user(
            username="adminuser",
            password="pass123456",
            full_name="测试管理员",
            role=User.Roles.ADMIN,
        )
        self.course = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="测试课程",
            summary="课程简介",
            description="课程详情",
            status=Course.Status.PUBLISHED,
        )
        self.assignment = Assignment.objects.create(
            course=self.course,
            created_by=self.teacher,
            title="测试作业",
            description="请提交测试文档",
            due_date=timezone.now(),
        )
        Announcement.objects.create(title="测试公告", content="公告内容", is_published=True)

    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CloudClass")

    def test_student_dashboard_redirect(self):
        self.client.login(username="student", password="pass123456")
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, reverse("core:student_dashboard"))

    def test_student_can_enroll_course(self):
        self.client.login(username="student", password="pass123456")
        response = self.client.get(reverse("courses:enroll", args=[self.course.pk]))
        self.assertRedirects(response, reverse("courses:detail", args=[self.course.pk]))
        self.assertTrue(CourseEnrollment.objects.filter(course=self.course, student=self.student).exists())

    def test_admin_dashboard_requires_admin_role(self):
        self.client.login(username="student", password="pass123456")
        response = self.client.get(reverse("core:admin_dashboard"))
        self.assertEqual(response.status_code, 403)
