from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from assignments.models import Assignment, AssignmentSubmission
from core.models import Announcement, Banner
from courses.models import Course, CourseCategory, CourseEnrollment
from discussions.models import DiscussionComment, DiscussionPost
from resources.models import CourseMaterial


class Command(BaseCommand):
    help = "创建网络教学平台演示数据"

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "full_name": "平台管理员",
                "role": User.Roles.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "email": "admin@example.com",
            },
        )
        admin.set_password("admin123456")
        admin.save()

        teacher, _ = User.objects.get_or_create(
            username="teacher01",
            defaults={
                "full_name": "张老师",
                "role": User.Roles.TEACHER,
                "school_id": "T2026001",
                "email": "teacher@example.com",
            },
        )
        teacher.set_password("teacher123456")
        teacher.save()

        student, _ = User.objects.get_or_create(
            username="student01",
            defaults={
                "full_name": "李同学",
                "role": User.Roles.STUDENT,
                "school_id": "S2026001",
                "email": "student@example.com",
            },
        )
        student.set_password("student123456")
        student.save()

        category, _ = CourseCategory.objects.get_or_create(name="Python 开发")
        course, _ = Course.objects.get_or_create(
            title="Python Web 开发基础",
            teacher=teacher,
            defaults={
                "category": category,
                "summary": "涵盖 Django 基础、模板开发、数据库建模与平台实现。",
                "description": "本课程围绕网络教学平台开发，介绍 Python Web 项目从设计到实现的完整流程。",
                "status": Course.Status.PUBLISHED,
            },
        )

        CourseEnrollment.objects.get_or_create(course=course, student=student)

        CourseMaterial.objects.get_or_create(
            course=course,
            uploaded_by=teacher,
            title="项目任务书",
            defaults={
                "material_type": CourseMaterial.MaterialTypes.DOCUMENT,
                "description": "课程大作业说明、评分标准与提交要求。",
            },
        )
        CourseMaterial.objects.get_or_create(
            course=course,
            uploaded_by=teacher,
            title="Django 基础视频",
            defaults={
                "material_type": CourseMaterial.MaterialTypes.LINK,
                "description": "外部学习视频链接。",
                "external_url": "https://www.bilibili.com/video/BV1AE41117Up/",
            },
        )

        assignment, _ = Assignment.objects.get_or_create(
            course=course,
            created_by=teacher,
            title="网络教学平台需求分析",
            defaults={
                "description": "梳理平台角色、功能模块、数据库表结构和页面关系。",
                "due_date": timezone.now() + timedelta(days=7),
            },
        )

        submission, _ = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={"content": "已完成需求分析文档和功能流程设计。", "score": 92, "feedback": "结构完整，流程清晰。"},
        )
        if submission.reviewed_at is None and submission.score is not None:
            submission.reviewed_at = timezone.now()
            submission.save(update_fields=["reviewed_at"])

        post, _ = DiscussionPost.objects.get_or_create(
            course=course,
            author=student,
            title="关于课程项目数据库设计的疑问",
            defaults={"content": "课程、作业、讨论之间的表关系应该如何组织更清晰？"},
        )
        DiscussionComment.objects.get_or_create(
            post=post,
            author=teacher,
            content="建议以课程为主线组织资料、作业和讨论，这样结构最清楚。",
        )

        Announcement.objects.get_or_create(
            title="平台演示环境已开放",
            defaults={"content": "管理员、教师和学生演示账号已经初始化，可直接登录体验。", "is_published": True},
        )
        Banner.objects.get_or_create(
            title="课程大作业演示",
            defaults={"subtitle": "支持课程学习、资料共享、作业批改与讨论答疑", "is_active": True},
        )

        self.stdout.write(self.style.SUCCESS("演示数据初始化完成。"))
