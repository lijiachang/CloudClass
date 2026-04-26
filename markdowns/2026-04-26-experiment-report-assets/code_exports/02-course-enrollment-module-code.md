# 课程与选课模块代码

包含课程、分类、标签、选课、收藏、课程列表、详情和教师课程管理相关代码。

## courses/models.py

```python
from django.conf import settings
from django.db import models
from django.urls import reverse


class CourseCategory(models.Model):
    name = models.CharField("分类名称", max_length=100, unique=True)
    description = models.TextField("分类说明", blank=True)

    class Meta:
        verbose_name = "课程分类"
        verbose_name_plural = "课程分类"

    def __str__(self):
        return self.name


class CourseTag(models.Model):
    name = models.CharField("标签名称", max_length=50, unique=True)

    class Meta:
        verbose_name = "课程标签"
        verbose_name_plural = "课程标签"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"

    category = models.ForeignKey(
        CourseCategory, on_delete=models.SET_NULL, blank=True, null=True, related_name="courses", verbose_name="分类"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teaching_courses", verbose_name="授课教师"
    )
    tags = models.ManyToManyField(CourseTag, blank=True, related_name="courses", verbose_name="课程标签")
    title = models.CharField("课程名称", max_length=200)
    cover = models.ImageField("课程封面", upload_to="course_covers/", blank=True, null=True)
    summary = models.CharField("课程简介", max_length=255)
    description = models.TextField("课程详情", blank=True)
    status = models.CharField("课程状态", max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "课程"
        verbose_name_plural = "课程"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("courses:detail", args=[self.pk])

    def get_enrollment_count(self):
        return self.enrollments.count()

    @property
    def tag_names(self):
        return [tag.name for tag in self.tags.all()]


class CourseEnrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments", verbose_name="课程")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments", verbose_name="学生"
    )
    created_at = models.DateTimeField("加入时间", auto_now_add=True)

    class Meta:
        verbose_name = "选课记录"
        verbose_name_plural = "选课记录"
        unique_together = ("course", "student")

    def __str__(self):
        return f"{self.student} -> {self.course}"


class CourseViewLog(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="view_logs", verbose_name="课程")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_views", verbose_name="学生"
    )
    created_at = models.DateTimeField("浏览时间", auto_now_add=True)

    class Meta:
        verbose_name = "课程浏览记录"
        verbose_name_plural = "课程浏览记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} viewed {self.course}"


class CourseFavorite(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="favorites", verbose_name="课程")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_courses", verbose_name="学生"
    )
    created_at = models.DateTimeField("收藏时间", auto_now_add=True)

    class Meta:
        verbose_name = "课程收藏"
        verbose_name_plural = "课程收藏"
        unique_together = ("course", "student")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} favorited {self.course}"

```

## courses/forms.py

```python
from django import forms

from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("category", "tags", "title", "cover", "summary", "description", "status")
        labels = {
            "category": "课程分类",
            "tags": "课程标签",
            "title": "课程名称",
            "cover": "课程封面",
            "summary": "课程简介",
            "description": "课程详情",
            "status": "课程状态",
        }
        widgets = {
            "tags": forms.CheckboxSelectMultiple,
        }

```

## courses/views.py

```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import student_required, teacher_required
from assignments.models import AssignmentSubmission
from attendance.models import AttendanceRecord, AttendanceSession
from discussions.models import DiscussionPost
from groups.models import CourseGroup
from resources.models import CourseMaterial

from .forms import CourseForm
from .models import Course, CourseCategory, CourseEnrollment, CourseFavorite, CourseTag, CourseViewLog
from .services import (
    get_active_courses,
    get_favorite_courses,
    get_hot_courses,
    get_latest_courses,
    get_recently_viewed_courses,
    get_recommended_courses_for_user,
    with_course_metrics,
)


def course_list(request):
    keyword = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    tag_id = request.GET.get("tag", "").strip()

    courses = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("teacher", "category").prefetch_related("tags")
    if keyword:
        courses = courses.filter(title__icontains=keyword)
    if category_id:
        courses = courses.filter(category_id=category_id)
    if tag_id:
        courses = courses.filter(tags__id=tag_id)

    discovered_courses = with_course_metrics(courses).distinct().order_by("-heat_score", "-created_at")
    context = {
        "courses": discovered_courses,
        "latest_courses": get_latest_courses(limit=6),
        "hot_courses": get_hot_courses(limit=6),
        "recommended_courses": get_recommended_courses_for_user(request.user, limit=6),
        "categories": CourseCategory.objects.all(),
        "tags": CourseTag.objects.all(),
        "active_category": category_id,
        "active_tag": tag_id,
        "keyword": keyword,
    }
    return render(request, "courses/course_list.html", context)


def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.select_related("teacher", "category").prefetch_related("tags"),
        pk=pk,
    )
    if request.user.is_authenticated and request.user.is_student:
        CourseViewLog.objects.create(course=course, student=request.user)

    is_enrolled = request.user.is_authenticated and (
        request.user.is_teacher
        or request.user.is_platform_admin
        or CourseEnrollment.objects.filter(course=course, student=request.user).exists()
    )
    is_favorite = request.user.is_authenticated and request.user.is_student and CourseFavorite.objects.filter(
        course=course, student=request.user
    ).exists()
    related_courses = (
        with_course_metrics(
            Course.objects.filter(status=Course.Status.PUBLISHED, tags__in=course.tags.all())
            .exclude(pk=course.pk)
            .select_related("teacher", "category")
            .prefetch_related("tags")
        )
        .distinct()
        .order_by("-heat_score", "-created_at")[:4]
    )
    context = {
        "course": course,
        "is_enrolled": is_enrolled,
        "is_favorite": is_favorite,
        "materials": CourseMaterial.objects.filter(course=course),
        "assignments": course.assignments.all(),
        "posts": DiscussionPost.objects.filter(course=course).select_related("author")[:5],
        "groups": CourseGroup.objects.filter(course=course).prefetch_related("members__student"),
        "attendance_sessions": AttendanceSession.objects.filter(course=course)[:5],
        "related_courses": related_courses,
        "favorite_count": CourseFavorite.objects.filter(course=course).count(),
        "view_count": CourseViewLog.objects.filter(course=course).count(),
        "signed_session_ids": set(
            AttendanceRecord.objects.filter(session__course=course, student=request.user).values_list("session_id", flat=True)
        )
        if request.user.is_authenticated and request.user.is_student
        else set(),
    }
    return render(request, "courses/course_detail.html", context)


@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk, status=Course.Status.PUBLISHED)
    if not request.user.is_student:
        messages.error(request, "只有学生可以加入课程。")
        return redirect(course.get_absolute_url())
    CourseEnrollment.objects.get_or_create(course=course, student=request.user)
    messages.success(request, f"你已成功加入《{course.title}》。")
    return redirect(course.get_absolute_url())


@student_required
def toggle_favorite_course(request, pk):
    course = get_object_or_404(Course, pk=pk, status=Course.Status.PUBLISHED)
    favorite, created = CourseFavorite.objects.get_or_create(course=course, student=request.user)
    if created:
        messages.success(request, f"已收藏《{course.title}》。")
    else:
        favorite.delete()
        messages.info(request, f"已取消收藏《{course.title}》。")
    return redirect(request.META.get("HTTP_REFERER") or course.get_absolute_url())


@student_required
def recommendation_center(request):
    context = {
        "recommended_courses": get_recommended_courses_for_user(request.user, limit=8),
        "recent_courses": get_recently_viewed_courses(request.user, limit=6),
        "favorite_courses": get_favorite_courses(request.user, limit=6),
        "hot_courses": get_hot_courses(limit=6),
        "active_courses": get_active_courses(limit=6),
    }
    return render(request, "courses/recommendation_center.html", context)


@teacher_required
def teacher_course_list(request):
    courses = with_course_metrics(
        Course.objects.filter(teacher=request.user).select_related("category").prefetch_related("tags")
    ).order_by("-created_at")
    return render(request, "courses/teacher_course_list.html", {"courses": courses})


@teacher_required
def teacher_course_create(request):
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.teacher = request.user
        course.save()
        form.save_m2m()
        messages.success(request, "课程已创建。")
        return redirect("courses:teacher_list")
    return render(request, "common/form.html", {"form": form, "title": "创建课程"})


@teacher_required
def teacher_course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "课程已更新。")
        return redirect("courses:teacher_list")
    return render(request, "common/form.html", {"form": form, "title": "编辑课程"})


@teacher_required
def teacher_course_analytics(request, pk):
    course = get_object_or_404(
        with_course_metrics(
            Course.objects.filter(pk=pk, teacher=request.user).select_related("category").prefetch_related("tags")
        ),
        pk=pk,
    )
    submissions = AssignmentSubmission.objects.filter(assignment__course=course)
    stats = {
        "student_count": course.enrollment_count,
        "material_count": course.material_count,
        "discussion_count": course.discussion_count,
        "view_count": course.view_count,
        "favorite_count": course.favorite_count,
        "submission_rate": round((submissions.count() / max(course.enrollment_count, 1)) * 100, 1),
        "average_score": submissions.aggregate(avg=Avg("score"))["avg"] or 0,
    }
    return render(request, "courses/teacher_course_analytics.html", {"course": course, "stats": stats})

```

## courses/urls.py

```python
from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="list"),
    path("recommendations/", views.recommendation_center, name="recommendations"),
    path("<int:pk>/", views.course_detail, name="detail"),
    path("<int:pk>/enroll/", views.enroll_course, name="enroll"),
    path("<int:pk>/favorite/", views.toggle_favorite_course, name="favorite"),
    path("teacher/manage/", views.teacher_course_list, name="teacher_list"),
    path("teacher/create/", views.teacher_course_create, name="teacher_create"),
    path("teacher/<int:pk>/edit/", views.teacher_course_edit, name="teacher_edit"),
    path("teacher/<int:pk>/analytics/", views.teacher_course_analytics, name="teacher_analytics"),
]

```

## templates/courses/course_list.html

```html
{% extends "base.html" %}
{% block title %}课程中心{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-1">课程中心</h1>
        <p class="text-muted mb-0">支持分类、标签和关键词检索，方便快速浏览课程内容。</p>
    </div>
    {% if user.is_authenticated and user.is_teacher %}
        <a class="btn btn-primary" href="{% url 'courses:teacher_create' %}">创建课程</a>
    {% endif %}
</div>

<div class="section-card mb-4">
    <form method="get" class="row g-3">
        <div class="col-md-4">
            <label for="q">关键词</label>
            <input id="q" type="text" name="q" value="{{ keyword }}" placeholder="搜索课程名称">
        </div>
        <div class="col-md-4">
            <label for="category">分类</label>
            <select id="category" name="category">
                <option value="">全部分类</option>
                {% for category in categories %}
                    <option value="{{ category.id }}" {% if active_category == category.id|stringformat:"s" %}selected{% endif %}>{{ category.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="col-md-4">
            <label for="tag">标签</label>
            <select id="tag" name="tag">
                <option value="">全部标签</option>
                {% for tag in tags %}
                    <option value="{{ tag.id }}" {% if active_tag == tag.id|stringformat:"s" %}selected{% endif %}>{{ tag.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="col-12 d-flex gap-2">
            <button class="btn btn-primary" type="submit">筛选课程</button>
            <a class="btn btn-outline-secondary" href="{% url 'courses:list' %}">重置</a>
        </div>
    </form>
</div>

<div class="row g-4">
    {% for course in courses %}
        <div class="col-md-6 col-xl-4">
            <div class="course-card h-100">
                {% if course.cover %}
                    <img src="{{ course.cover.url }}" class="course-thumb mb-3" alt="{{ course.title }}">
                {% else %}
                    <div class="course-thumb course-thumb-placeholder mb-3">
                        <span>{{ course.category.name|default:"课程" }}</span>
                    </div>
                {% endif %}
                <h2 class="h5">{{ course.title }}</h2>
                <p class="small text-muted">教师：{{ course.teacher.full_name }}</p>
                <p>{{ course.summary }}</p>
                <div class="mb-3">
                    {% for tag in course.tags.all %}
                        <span class="chip">{{ tag.name }}</span>
                    {% endfor %}
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="small text-muted">{{ course.category.name|default:"未分类" }}</span>
                    <a class="btn btn-sm btn-primary" href="{% url 'courses:detail' course.pk %}">查看详情</a>
                </div>
            </div>
        </div>
    {% empty %}
        <div class="col-12"><div class="alert alert-light border">暂无课程。</div></div>
    {% endfor %}
</div>
{% endblock %}

```

## templates/courses/course_detail.html

```html
{% extends "base.html" %}
{% block title %}{{ course.title }}{% endblock %}
{% block content %}
<div class="section-card mb-4">
    <div class="d-flex flex-wrap justify-content-between gap-3">
        <div>
            <h1 class="h3 mb-2">{{ course.title }}</h1>
            <p class="text-muted mb-2">教师：{{ course.teacher.full_name }} | 分类：{{ course.category.name|default:"未分类" }}</p>
            <div class="mb-2">
                {% for tag in course.tags.all %}
                    <span class="chip">{{ tag.name }}</span>
                {% empty %}
                    <span class="small text-muted">暂未设置标签</span>
                {% endfor %}
            </div>
            <p class="small text-muted">浏览 {{ view_count }} · 收藏 {{ favorite_count }}</p>
            <p class="mb-0">{{ course.description|default:course.summary }}</p>
        </div>
        <div class="d-flex gap-2 align-items-start">
            {% if user.is_authenticated and user.is_student and not is_enrolled %}
                <a class="btn btn-primary" href="{% url 'courses:enroll' course.pk %}">加入课程</a>
            {% endif %}
            {% if user.is_authenticated and user.is_student %}
                <a class="btn btn-outline-dark" href="{% url 'courses:favorite' course.pk %}">
                    {% if is_favorite %}取消收藏{% else %}收藏课程{% endif %}
                </a>
            {% endif %}
            {% if user.is_authenticated and user == course.teacher %}
                <a class="btn btn-outline-dark" href="{% url 'ai_assistant:center' %}">AI 助手</a>
                <a class="btn btn-outline-primary" href="{% url 'resources:create' %}">上传资料</a>
                <a class="btn btn-outline-secondary" href="{% url 'assignments:create' %}">发布作业</a>
            {% endif %}
        </div>
    </div>
</div>

<div class="row g-4">
    <div class="col-lg-4">
        <div class="section-card mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2 class="h5 mb-0">教学资料</h2>
                {% if user.is_authenticated and user == course.teacher %}
                    <a href="{% url 'resources:manage' course.pk %}">管理</a>
                {% endif %}
            </div>
            {% for material in materials %}
                <div class="mb-3">
                    <div class="fw-semibold">{{ material.title }}</div>
                    <div class="small text-muted">{{ material.get_material_type_display }}</div>
                    <a href="{% url 'resources:detail' material.pk %}">查看资料详情</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无资料。</p>
            {% endfor %}
        </div>
        <div class="section-card">
            <h2 class="h5 mb-3">讨论区</h2>
            {% if user.is_authenticated %}
                <a class="btn btn-sm btn-primary mb-3" href="{% url 'discussions:course_create' course.pk %}">发帖交流</a>
            {% endif %}
            {% for post in posts %}
                <div class="mb-3">
                    <div class="fw-semibold">
                        {% if post.is_pinned %}<span class="badge text-bg-warning">置顶</span>{% endif %}
                        <span class="badge text-bg-light">{{ post.get_post_type_display }}</span>
                        <a href="{% url 'discussions:detail' post.pk %}">{{ post.title }}</a>
                    </div>
                    <div class="small text-muted">{{ post.author.full_name }} · {{ post.created_at|date:"Y-m-d H:i" }}</div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无讨论内容。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-8">
        <div class="section-card">
            <h2 class="h5 mb-3">课程作业</h2>
            {% for assignment in assignments %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ assignment.title }}</div>
                        <div class="small text-muted">截止：{{ assignment.due_date|date:"Y-m-d H:i" }}</div>
                    </div>
                    <div class="d-flex gap-2">
                        {% if user.is_authenticated and user.is_student and is_enrolled %}
                            <a class="btn btn-sm btn-primary" href="{% url 'assignments:submit' assignment.pk %}">提交作业</a>
                        {% endif %}
                        {% if user.is_authenticated and user == course.teacher %}
                            <a class="btn btn-sm btn-outline-secondary" href="{% url 'assignments:review_list' assignment.pk %}">查看提交</a>
                        {% endif %}
                    </div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无作业。</p>
            {% endfor %}
        </div>
        <div class="section-card mt-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2 class="h5 mb-0">课堂签到</h2>
                {% if user.is_authenticated and user == course.teacher %}
                    <a href="{% url 'attendance:session_create' %}">发起签到</a>
                {% endif %}
            </div>
            {% for session in attendance_sessions %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ session.title }}</div>
                        <div class="small text-muted">{{ session.get_status_display }} · {{ session.created_at|date:"Y-m-d H:i" }}</div>
                    </div>
                    <div class="d-flex gap-2">
                        {% if user.is_authenticated and user == course.teacher %}
                            <a href="{% url 'attendance:session_detail' session.pk %}">查看签到</a>
                        {% elif user.is_authenticated and user.is_student and is_enrolled %}
                            {% if session.pk in signed_session_ids %}
                                <span class="badge text-bg-success">已签到</span>
                            {% else %}
                                <a class="btn btn-sm btn-primary" href="{% url 'attendance:sign_in' session.pk %}">立即签到</a>
                            {% endif %}
                        {% endif %}
                    </div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无签到活动。</p>
            {% endfor %}
        </div>
        <div class="section-card mt-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2 class="h5 mb-0">课程分组</h2>
                {% if user.is_authenticated and user == course.teacher %}
                    <a href="{% url 'groups:group_create' %}">创建小组</a>
                {% endif %}
            </div>
            {% for group in groups %}
                <div class="mb-3">
                    <div class="fw-semibold">{{ group.name }}</div>
                    <div class="small text-muted">{{ group.description|default:"暂无小组说明" }}</div>
                    <div class="small text-muted mt-1">
                        成员：
                        {% for member in group.members.all %}
                            {{ member.student.full_name }}{% if not forloop.last %}、{% endif %}
                        {% empty %}
                            暂无成员
                        {% endfor %}
                    </div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无分组信息。</p>
            {% endfor %}
        </div>
        <div class="section-card mt-4">
            <h2 class="h5 mb-3">相关推荐</h2>
            {% for related in related_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ related.title }}</div>
                        <div class="small text-muted">热度 {{ related.heat_score }} · {{ related.category.name|default:"未分类" }}</div>
                    </div>
                    <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:detail' related.pk %}">查看</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无相关推荐。</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

```

## templates/courses/teacher_course_list.html

```html
{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1 class="h3 mb-0">我的课程管理</h1>
    <a class="btn btn-primary" href="{% url 'courses:teacher_create' %}">创建课程</a>
</div>
<div class="section-card">
    {% for course in courses %}
        <div class="list-item-row">
            <div>
                <div class="fw-semibold">{{ course.title }}</div>
                <div class="small text-muted">学生 {{ course.enrollment_count }} · 浏览 {{ course.view_count }} · 收藏 {{ course.favorite_count }}</div>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:teacher_edit' course.pk %}">编辑</a>
                <a class="btn btn-sm btn-outline-secondary" href="{% url 'courses:teacher_analytics' course.pk %}">统计</a>
            </div>
        </div>
    {% empty %}
        <p class="text-muted mb-0">暂无课程。</p>
    {% endfor %}
</div>
{% endblock %}

```

## templates/courses/teacher_course_analytics.html

```html
{% extends "base.html" %}
{% block content %}
<div class="section-card">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h1 class="h3 mb-1">{{ course.title }} 统计概览</h1>
            <p class="text-muted mb-0">展示选课、资料、讨论与作业完成情况。</p>
        </div>
    </div>
    <div class="row g-3 mb-4">
        <div class="col-md-3"><div class="stat-card"><span>学生数</span><strong>{{ stats.student_count }}</strong></div></div>
        <div class="col-md-3"><div class="stat-card"><span>资料数</span><strong>{{ stats.material_count }}</strong></div></div>
        <div class="col-md-3"><div class="stat-card"><span>讨论帖</span><strong>{{ stats.discussion_count }}</strong></div></div>
        <div class="col-md-3"><div class="stat-card"><span>提交率</span><strong>{{ stats.submission_rate }}%</strong></div></div>
        <div class="col-md-6"><div class="stat-card"><span>浏览量</span><strong>{{ stats.view_count }}</strong></div></div>
        <div class="col-md-6"><div class="stat-card"><span>收藏量</span><strong>{{ stats.favorite_count }}</strong></div></div>
    </div>
    <canvas id="analyticsChart" height="120"></canvas>
</div>
{% endblock %}
{% block scripts %}
<script>
new Chart(document.getElementById('analyticsChart'), {
    type: 'bar',
    data: {
        labels: ['学生数', '资料数', '讨论帖', '平均分', '浏览量', '收藏量'],
        datasets: [{
            label: '课程统计',
            data: [{{ stats.student_count }}, {{ stats.material_count }}, {{ stats.discussion_count }}, {{ stats.average_score|floatformat:1 }}, {{ stats.view_count }}, {{ stats.favorite_count }}],
            backgroundColor: ['#1d4ed8', '#0f766e', '#d97706', '#9333ea', '#e11d48', '#0f766e']
        }]
    },
    options: {responsive: true, plugins: {legend: {display: false}}}
});
</script>
{% endblock %}

```

