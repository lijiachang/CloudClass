from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from assignments.models import Assignment, AssignmentSubmission
from attendance.models import AttendanceRecord, AttendanceSession
from core.models import Announcement, Banner
from courses.models import Course, CourseCategory, CourseEnrollment, CourseFavorite, CourseTag, CourseViewLog
from discussions.models import DiscussionComment, DiscussionPost
from groups.models import CourseGroup, CourseGroupMember
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

        teachers = []
        for index, name in enumerate(["张老师", "李老师", "王老师"], start=1):
            teacher, _ = User.objects.get_or_create(
                username=f"teacher{index:02d}",
                defaults={
                    "full_name": name,
                    "role": User.Roles.TEACHER,
                    "school_id": f"T20260{index:02d}",
                    "email": f"teacher{index}@example.com",
                },
            )
            teacher.set_password("teacher123456")
            teacher.save()
            teachers.append(teacher)

        students = []
        for index, name in enumerate(["李同学", "周同学", "陈同学", "吴同学", "郑同学"], start=1):
            student, _ = User.objects.get_or_create(
                username=f"student{index:02d}",
                defaults={
                    "full_name": name,
                    "role": User.Roles.STUDENT,
                    "school_id": f"S20260{index:03d}",
                    "email": f"student{index}@example.com",
                },
            )
            student.set_password("student123456")
            student.save()
            students.append(student)

        categories = {
            "Python 开发": CourseCategory.objects.get_or_create(name="Python 开发")[0],
            "数据分析": CourseCategory.objects.get_or_create(name="数据分析")[0],
            "人工智能": CourseCategory.objects.get_or_create(name="人工智能")[0],
            "前端基础": CourseCategory.objects.get_or_create(name="前端基础")[0],
        }

        tag_names = [
            "Django",
            "Flask",
            "MySQL",
            "数据可视化",
            "机器学习",
            "深度学习",
            "HTML",
            "JavaScript",
            "项目实战",
            "算法基础",
        ]
        tags = {name: CourseTag.objects.get_or_create(name=name)[0] for name in tag_names}

        course_specs = [
            ("Python Web 开发基础", "Python 开发", 0, ["Django", "MySQL", "项目实战"]),
            ("Django 项目实战", "Python 开发", 0, ["Django", "项目实战"]),
            ("Flask 轻量应用开发", "Python 开发", 1, ["Flask", "MySQL"]),
            ("Pandas 数据分析入门", "数据分析", 1, ["数据可视化", "算法基础"]),
            ("Python 数据可视化", "数据分析", 1, ["数据可视化", "项目实战"]),
            ("机器学习导论", "人工智能", 2, ["机器学习", "算法基础"]),
            ("深度学习基础", "人工智能", 2, ["深度学习", "机器学习"]),
            ("推荐系统概论", "人工智能", 2, ["机器学习", "项目实战"]),
            ("HTML5 页面设计", "前端基础", 0, ["HTML", "JavaScript"]),
            ("JavaScript 交互编程", "前端基础", 1, ["JavaScript", "项目实战"]),
        ]

        courses = []
        for index, (title, category_name, teacher_index, tag_list) in enumerate(course_specs, start=1):
            course, _ = Course.objects.get_or_create(
                title=title,
                teacher=teachers[teacher_index],
                defaults={
                    "category": categories[category_name],
                    "summary": f"{title} 覆盖课程核心知识、案例练习与平台化应用。",
                    "description": f"{title} 适合作为网络教学平台中的演示课程，包含资料、作业、讨论和推荐标签。",
                    "status": Course.Status.PUBLISHED,
                },
            )
            course.category = categories[category_name]
            course.summary = f"{title} 覆盖课程核心知识、案例练习与平台化应用。"
            course.description = f"{title} 适合作为网络教学平台中的演示课程，包含资料、作业、讨论和推荐标签。"
            course.status = Course.Status.PUBLISHED
            course.save()
            course.tags.set([tags[tag_name] for tag_name in tag_list])
            courses.append(course)

            CourseMaterial.objects.get_or_create(
                course=course,
                uploaded_by=teachers[teacher_index],
                title=f"{title} 课程讲义",
                defaults={
                    "material_type": CourseMaterial.MaterialTypes.DOCUMENT,
                    "description": f"{title} 的章节讲义和重点归纳。",
                },
            )
            CourseMaterial.objects.get_or_create(
                course=course,
                uploaded_by=teachers[teacher_index],
                title=f"{title} 学习视频",
                defaults={
                    "material_type": CourseMaterial.MaterialTypes.LINK,
                    "description": f"{title} 的站内学习导览。",
                    "content": f"这里整理了 {title} 的教学视频说明、重点知识和案例操作步骤。",
                    "external_url": "https://www.example.com/cloudclass-material-reference",
                },
            )

            assignment, _ = Assignment.objects.get_or_create(
                course=course,
                created_by=teachers[teacher_index],
                title=f"{title} 单元作业",
                defaults={
                    "description": f"请完成 {title} 的知识梳理与案例练习。",
                    "due_date": timezone.now() + timedelta(days=7 + index),
                },
            )

            post, _ = DiscussionPost.objects.get_or_create(
                course=course,
                author=students[index % len(students)],
                title=f"{title} 学习交流帖",
                defaults={
                    "content": f"欢迎在这里讨论 {title} 的重点、难点和作业思路。",
                    "post_type": DiscussionPost.PostTypes.CLASSROOM,
                },
            )
            DiscussionComment.objects.get_or_create(
                post=post,
                author=teachers[teacher_index],
                content=f"{title} 的学习建议：先看资料，再完成讨论和作业。",
            )

            for student in students[: 2 + index % 3]:
                CourseEnrollment.objects.get_or_create(course=course, student=student)
                CourseViewLog.objects.get_or_create(course=course, student=student)
                if (student.id + index) % 2 == 0:
                    CourseFavorite.objects.get_or_create(course=course, student=student)
                submission, _ = AssignmentSubmission.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={
                        "content": f"{student.full_name} 已完成 {title} 的学习作业。",
                        "score": 82 + ((student.id + index) % 15),
                        "feedback": "整体完成较好，注意补充案例分析。",
                    },
                )
                if submission.reviewed_at is None:
                    submission.reviewed_at = timezone.now() - timedelta(days=index % 3)
                    submission.save(update_fields=["reviewed_at"])

            group, _ = CourseGroup.objects.get_or_create(
                course=course,
                name="第一学习小组",
                defaults={"description": f"{title} 的示例分组。", "created_by": teachers[teacher_index]},
            )
            for student in students[:2]:
                CourseGroupMember.objects.get_or_create(group=group, student=student)

            session, _ = AttendanceSession.objects.get_or_create(
                course=course,
                title=f"{title} 第一讲签到",
                defaults={
                    "description": "演示环境初始化签到记录。",
                    "created_by": teachers[teacher_index],
                },
            )
            for student in students[:2]:
                AttendanceRecord.objects.get_or_create(session=session, student=student)

        target_student = students[0]
        for course in courses[:4]:
            CourseEnrollment.objects.get_or_create(course=course, student=target_student)
            CourseFavorite.objects.get_or_create(course=course, student=target_student)
            CourseViewLog.objects.get_or_create(course=course, student=target_student)

        for title, content in [
            ("平台演示环境已开放", "管理员、教师和学生演示账号已经初始化，可直接登录体验推荐、收藏与热门榜单。"),
            ("推荐中心功能上线", "平台已支持基于浏览、收藏和标签偏好的规则推荐。"),
        ]:
            Announcement.objects.get_or_create(title=title, defaults={"content": content, "is_published": True})

        for title, subtitle in [
            ("课程推荐升级", "支持标签筛选、个性化推荐和热门课程榜"),
            ("网络教学平台演示", "支持课程学习、作业提交、讨论答疑与教学统计"),
        ]:
            Banner.objects.get_or_create(title=title, defaults={"subtitle": subtitle, "is_active": True})

        self.stdout.write(self.style.SUCCESS("演示数据初始化完成。"))
