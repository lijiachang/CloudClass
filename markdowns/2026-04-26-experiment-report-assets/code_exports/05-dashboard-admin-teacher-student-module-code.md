# 管理员教师学生工作台模块代码

包含首页、三类工作台、公告 Banner 管理，以及基础布局和样式。

## core/models.py

```python
from django.db import models


class Announcement(models.Model):
    title = models.CharField("公告标题", max_length=200)
    content = models.TextField("公告内容")
    is_published = models.BooleanField("是否发布", default=True)
    created_at = models.DateTimeField("发布时间", auto_now_add=True)

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = "公告"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Banner(models.Model):
    title = models.CharField("Banner 标题", max_length=200)
    subtitle = models.CharField("副标题", max_length=255, blank=True)
    image = models.ImageField("Banner 图片", upload_to="banners/", blank=True, null=True)
    link = models.URLField("跳转链接", blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "Banner"
        verbose_name_plural = "Banner"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

```

## core/forms.py

```python
from django import forms

from .models import Announcement, Banner


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ("title", "content", "is_published")
        labels = {
            "title": "公告标题",
            "content": "公告内容",
            "is_published": "立即发布",
        }


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ("title", "subtitle", "image", "link", "is_active")
        labels = {
            "title": "Banner 标题",
            "subtitle": "副标题",
            "image": "Banner 图片",
            "link": "跳转链接",
            "is_active": "启用展示",
        }

```

## core/views.py

```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from accounts.decorators import admin_required, student_required, teacher_required
from accounts.models import User
from assignments.models import Assignment, AssignmentSubmission
from attendance.models import AttendanceSession
from courses.models import Course, CourseFavorite, CourseTag, CourseViewLog
from courses.services import (
    get_active_courses,
    get_favorite_courses,
    get_hot_courses,
    get_latest_courses,
    get_recently_viewed_courses,
    get_recommended_courses_for_user,
    with_course_metrics,
)
from discussions.models import DiscussionPost
from groups.models import CourseGroup
from resources.models import CourseMaterial

from .forms import AnnouncementForm, BannerForm
from .models import Announcement, Banner


def home(request):
    context = {
        "banners": Banner.objects.filter(is_active=True)[:3],
        "announcements": Announcement.objects.filter(is_published=True)[:5],
        "hot_courses": get_hot_courses(limit=6),
        "latest_courses": get_latest_courses(limit=6),
        "recommended_courses": get_recommended_courses_for_user(request.user, limit=4),
        "tags": CourseTag.objects.annotate(course_total=Count("courses")).filter(course_total__gt=0)[:10],
    }
    return render(request, "core/home.html", context)


@login_required
def dashboard_redirect(request):
    return redirect(request.user.get_dashboard_url())


@student_required
def student_dashboard(request):
    enrollments = Course.objects.filter(enrollments__student=request.user).select_related("teacher", "category").prefetch_related("tags")
    submissions = AssignmentSubmission.objects.filter(student=request.user).select_related("assignment", "assignment__course")
    pending_assignments = Assignment.objects.filter(course__enrollments__student=request.user).exclude(
        submissions__student=request.user
    )[:5]
    favorite_courses = get_favorite_courses(request.user, limit=5)
    recent_courses = get_recently_viewed_courses(request.user, limit=5)
    recommended_courses = get_recommended_courses_for_user(request.user, limit=4)
    stats = {
        "course_count": enrollments.count(),
        "submission_count": submissions.count(),
        "average_score": submissions.aggregate(avg=Avg("score"))["avg"] or 0,
        "favorite_count": CourseFavorite.objects.filter(student=request.user).count(),
        "view_count": CourseViewLog.objects.filter(student=request.user).count(),
    }
    return render(
        request,
        "core/student_dashboard.html",
        {
            "enrollments": with_course_metrics(enrollments)[:6],
            "submissions": submissions[:5],
            "pending_assignments": pending_assignments,
            "announcements": Announcement.objects.filter(is_published=True)[:5],
            "favorite_courses": favorite_courses,
            "recent_courses": recent_courses,
            "recommended_courses": recommended_courses,
            "stats": stats,
        },
    )


@teacher_required
def teacher_dashboard(request):
    courses = with_course_metrics(
        Course.objects.filter(teacher=request.user).select_related("category").prefetch_related("tags")
    ).order_by("-heat_score", "-created_at")
    pending_reviews = AssignmentSubmission.objects.filter(
        assignment__created_by=request.user, reviewed_at__isnull=True
    ).select_related("assignment", "student")[:8]
    stats = {
        "course_count": courses.count(),
        "material_count": CourseMaterial.objects.filter(uploaded_by=request.user).count(),
        "discussion_count": DiscussionPost.objects.filter(course__teacher=request.user).count(),
        "view_count": CourseViewLog.objects.filter(course__teacher=request.user).count(),
        "favorite_count": CourseFavorite.objects.filter(course__teacher=request.user).count(),
        "attendance_count": AttendanceSession.objects.filter(created_by=request.user).count(),
        "group_count": CourseGroup.objects.filter(created_by=request.user).count(),
    }
    return render(
        request,
        "core/teacher_dashboard.html",
        {
            "courses": courses[:6],
            "pending_reviews": pending_reviews,
            "stats": stats,
            "announcements": Announcement.objects.filter(is_published=True)[:5],
        },
    )


@admin_required
def admin_dashboard(request):
    hot_courses = get_hot_courses(limit=6)
    popular_tags = CourseTag.objects.annotate(course_total=Count("courses")).order_by("-course_total", "name")[:8]
    stats = {
        "user_count": User.objects.count(),
        "course_count": Course.objects.count(),
        "material_count": CourseMaterial.objects.count(),
        "assignment_count": Assignment.objects.count(),
        "discussion_count": DiscussionPost.objects.count(),
        "tag_count": CourseTag.objects.count(),
        "active_student_count": User.objects.filter(role=User.Roles.STUDENT, enrollments__isnull=False).distinct().count(),
    }
    return render(
        request,
        "core/admin_dashboard.html",
        {
            "stats": stats,
            "announcements": Announcement.objects.all()[:6],
            "banners": Banner.objects.all()[:6],
            "hot_courses": hot_courses,
            "popular_tags": popular_tags,
        },
    )


@admin_required
def announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "公告已发布。")
        return redirect("core:admin_dashboard")
    return render(request, "common/form.html", {"form": form, "title": "发布公告"})


@admin_required
def banner_create(request):
    form = BannerForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Banner 已创建。")
        return redirect("core:admin_dashboard")
    return render(request, "common/form.html", {"form": form, "title": "发布 Banner"})

```

## core/urls.py

```python
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("announcements/create/", views.announcement_create, name="announcement_create"),
    path("banners/create/", views.banner_create, name="banner_create"),
]

```

## templates/base.html

```html
{% load static %}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}CloudClass 网络教学平台{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{% static 'css/site.css' %}">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark app-navbar">
    <div class="container">
        <a class="navbar-brand fw-bold" href="{% url 'core:home' %}">CloudClass</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navMenu">
            <ul class="navbar-nav me-auto">
                <li class="nav-item"><a class="nav-link" href="{% url 'courses:list' %}">课程中心</a></li>
                {% if user.is_authenticated and user.is_student %}
                    <li class="nav-item"><a class="nav-link" href="{% url 'courses:recommendations' %}">推荐中心</a></li>
                    <li class="nav-item"><a class="nav-link" href="{% url 'ai_assistant:student_chat' %}">AI 聊天</a></li>
                {% endif %}
                {% if user.is_authenticated %}
                    <li class="nav-item"><a class="nav-link" href="{% url 'core:dashboard' %}">我的工作台</a></li>
                    <li class="nav-item"><a class="nav-link" href="{% url 'accounts:profile' %}">个人中心</a></li>
                {% endif %}
            </ul>
            <div class="d-flex gap-2 align-items-center">
                {% if user.is_authenticated %}
                    <span class="text-white-50 small">{{ user.full_name }} / {{ user.get_role_display }}</span>
                    <a class="btn btn-outline-light btn-sm" href="{% url 'accounts:logout' %}">退出</a>
                {% else %}
                    <a class="btn btn-outline-light btn-sm" href="{% url 'accounts:login' %}">登录</a>
                    <a class="btn btn-warning btn-sm" href="{% url 'accounts:register' %}">学生注册</a>
                {% endif %}
            </div>
        </div>
    </div>
</nav>

<main class="py-4">
    <div class="container">
        {% if messages %}
            <div class="mb-3">
                {% for message in messages %}
                    <div class="alert alert-{{ message.tags|default:'info' }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
        {% block content %}{% endblock %}
    </div>
</main>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>

```

## templates/core/home.html

```html
{% extends "base.html" %}
{% block content %}
<section class="hero-card mb-4">
    <div class="row align-items-center">
        <div class="col-lg-7">
            <span class="badge text-bg-warning mb-3">Python + Django 4.2 + MySQL 8.0</span>
            <h1 class="display-5 fw-bold">基于 Python 的网络教学平台</h1>
            <p class="lead text-muted">面向学生、教师、管理员的课程学习、资料共享、作业处理与讨论答疑一体化系统。</p>
            <div class="d-flex gap-2 flex-wrap">
                <a class="btn btn-primary" href="{% url 'courses:list' %}">进入课程中心</a>
                {% if user.is_authenticated %}
                    <a class="btn btn-outline-dark" href="{% url 'core:dashboard' %}">进入我的工作台</a>
                {% else %}
                    <a class="btn btn-outline-dark" href="{% url 'accounts:login' %}">登录系统</a>
                {% endif %}
            </div>
        </div>
        <div class="col-lg-5 mt-4 mt-lg-0">
            <div class="hero-visual">
                {% with hero_banner=banners|first %}
                    {% if hero_banner and hero_banner.image %}
                        <img src="{{ hero_banner.image.url }}" class="hero-visual-image" alt="{{ hero_banner.title }}">
                    {% else %}
                        <div class="hero-visual-placeholder">
                            <div class="hero-orb hero-orb-a"></div>
                            <div class="hero-orb hero-orb-b"></div>
                            <div class="hero-screen">
                                <div class="hero-screen-bar"></div>
                                <div class="hero-screen-lines"></div>
                            </div>
                        </div>
                    {% endif %}
                {% endwith %}
                <div class="hero-visual-note">
                    <div class="hero-note-title">平台亮点</div>
                    <div class="hero-note-grid">
                        <div class="hero-note-item">课程学习</div>
                        <div class="hero-note-item">AI 助教</div>
                        <div class="hero-note-item">签到分组</div>
                        <div class="hero-note-item">作业批改</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="mb-4">
    <div class="row g-4">
        {% for banner in banners %}
            <div class="col-md-4">
                <div class="card border-0 shadow-sm h-100">
                    {% if banner.image %}
                        <img src="{{ banner.image.url }}" class="card-img-top banner-image" alt="{{ banner.title }}">
                    {% endif %}
                    <div class="card-body">
                        <h3 class="h5">{{ banner.title }}</h3>
                        <p class="text-muted">{{ banner.subtitle }}</p>
                        {% if banner.link %}
                            <a href="{{ banner.link }}" class="btn btn-sm btn-outline-primary" target="_blank">查看链接</a>
                        {% endif %}
                    </div>
                </div>
            </div>
        {% empty %}
            <div class="col-12">
                <div class="alert alert-light border">当前暂无 Banner，管理员可在后台或管理页补充展示内容。</div>
            </div>
        {% endfor %}
    </div>
</section>

<section class="row g-4">
    <div class="col-lg-7">
        <div class="section-card">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2 class="h4 mb-0">热门课程</h2>
                <a href="{% url 'courses:list' %}">查看全部</a>
            </div>
            <div class="row g-3">
                {% for course in hot_courses %}
                    <div class="col-md-6">
                        <div class="course-card h-100">
                            {% if course.cover %}
                                <img src="{{ course.cover.url }}" class="course-thumb mb-3" alt="{{ course.title }}">
                            {% else %}
                                <div class="course-thumb course-thumb-placeholder mb-3">
                                    <span>{{ course.category.name|default:"课程" }}</span>
                                </div>
                            {% endif %}
                            <h3 class="h5">{{ course.title }}</h3>
                            <p class="small text-muted mb-2">教师：{{ course.teacher.full_name }}</p>
                            <p class="mb-3">{{ course.summary }}</p>
                            <div class="mb-3">
                                {% for tag in course.tags.all %}
                                    <span class="chip">{{ tag.name }}</span>
                                {% endfor %}
                            </div>
                            <div class="small text-muted mb-3">{{ course.category.name|default:"未分类" }} · 课程资料与作业已集成</div>
                            <a class="btn btn-sm btn-primary" href="{% url 'courses:detail' course.pk %}">查看课程</a>
                        </div>
                    </div>
                {% empty %}
                    <div class="col-12"><p class="text-muted mb-0">暂无课程数据。</p></div>
                {% endfor %}
            </div>
        </div>
    </div>
    <div class="col-lg-5">
        <div class="section-card h-100">
            <h2 class="h4 mb-3">最新公告</h2>
            <div class="list-group list-group-flush">
                {% for item in announcements %}
                    <div class="list-group-item px-0">
                        <div class="fw-semibold">{{ item.title }}</div>
                        <div class="small text-muted">{{ item.created_at|date:"Y-m-d H:i" }}</div>
                        <p class="mb-0 mt-2">{{ item.content|truncatechars:100 }}</p>
                    </div>
                {% empty %}
                    <p class="text-muted mb-0">暂无公告。</p>
                {% endfor %}
            </div>
        </div>
    </div>
</section>

<section class="row g-4 mt-1">
    <div class="col-lg-6">
        <div class="section-card h-100">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2 class="h5 mb-0">最新上架</h2>
                <a href="{% url 'courses:list' %}">更多课程</a>
            </div>
            {% for course in latest_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">{{ course.category.name|default:"未分类" }} · {{ course.teacher.full_name }}</div>
                    </div>
                    <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:detail' course.pk %}">查看</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无课程。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-6">
        <div class="section-card h-100">
            <h2 class="h5 mb-3">热门标签</h2>
            <div class="d-flex flex-wrap gap-2 mb-4">
                {% for tag in tags %}
                    <a class="chip chip-link" href="{% url 'courses:list' %}?tag={{ tag.id }}">{{ tag.name }} ({{ tag.course_total }})</a>
                {% empty %}
                    <span class="text-muted">暂无标签</span>
                {% endfor %}
            </div>
            <div class="home-side-panel">
                <h2 class="h5 mb-3">学习入口</h2>
                <p class="text-muted mb-3">课程浏览、推荐中心、教师工作台和 AI 助手都已经整合进同一套平台流程中。</p>
                <div class="d-flex gap-2 flex-wrap">
                    <a class="btn btn-sm btn-outline-dark" href="{% url 'courses:list' %}">课程中心</a>
                    {% if user.is_authenticated and user.is_student %}
                        <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:recommendations' %}">推荐中心</a>
                        <a class="btn btn-sm btn-outline-primary" href="{% url 'ai_assistant:student_chat' %}">AI 聊天</a>
                    {% elif user.is_authenticated %}
                        <a class="btn btn-sm btn-outline-primary" href="{% url 'core:dashboard' %}">我的工作台</a>
                    {% else %}
                        <a class="btn btn-sm btn-outline-primary" href="{% url 'accounts:login' %}">登录体验</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}

```

## templates/core/admin_dashboard.html

```html
{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-1">管理员工作台</h1>
        <p class="text-muted mb-0">管理用户、公告、Banner 和平台概况。</p>
    </div>
    <div class="d-flex gap-2">
        <a class="btn btn-primary" href="{% url 'core:announcement_create' %}">发布公告</a>
        <a class="btn btn-outline-primary" href="{% url 'core:banner_create' %}">发布 Banner</a>
    </div>
</div>

<div class="row g-3 mb-4">
    <div class="col-md-2"><div class="stat-card"><span>用户</span><strong>{{ stats.user_count }}</strong></div></div>
    <div class="col-md-2"><div class="stat-card"><span>课程</span><strong>{{ stats.course_count }}</strong></div></div>
    <div class="col-md-2"><div class="stat-card"><span>资料</span><strong>{{ stats.material_count }}</strong></div></div>
    <div class="col-md-2"><div class="stat-card"><span>作业</span><strong>{{ stats.assignment_count }}</strong></div></div>
    <div class="col-md-2"><div class="stat-card"><span>讨论</span><strong>{{ stats.discussion_count }}</strong></div></div>
    <div class="col-md-2"><div class="stat-card"><span>标签</span><strong>{{ stats.tag_count }}</strong></div></div>
    <div class="col-md-4"><div class="stat-card"><span>活跃学生</span><strong>{{ stats.active_student_count }}</strong></div></div>
</div>

<div class="row g-4">
    <div class="col-lg-6">
        <div class="section-card">
            <h2 class="h5 mb-3">公告管理</h2>
            {% for item in announcements %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ item.title }}</div>
                        <div class="small text-muted">{{ item.created_at|date:"Y-m-d H:i" }}</div>
                    </div>
                    <span class="badge {% if item.is_published %}text-bg-success{% else %}text-bg-secondary{% endif %}">
                        {% if item.is_published %}已发布{% else %}草稿{% endif %}
                    </span>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无公告。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-6">
        <div class="section-card">
            <h2 class="h5 mb-3">Banner 管理</h2>
            {% for banner in banners %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ banner.title }}</div>
                        <div class="small text-muted">{{ banner.subtitle }}</div>
                    </div>
                    <span class="badge {% if banner.is_active %}text-bg-success{% else %}text-bg-secondary{% endif %}">
                        {% if banner.is_active %}启用{% else %}停用{% endif %}
                    </span>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无 Banner。</p>
            {% endfor %}
        </div>
    </div>
</div>

<div class="row g-4 mt-1">
    <div class="col-lg-6">
        <div class="section-card">
            <h2 class="h5 mb-3">热门课程 Top</h2>
            {% for course in hot_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">热度 {{ course.heat_score }} · 收藏 {{ course.favorite_count }}</div>
                    </div>
                    <span class="small text-muted">浏览 {{ course.view_count }}</span>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无课程数据。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-6">
        <div class="section-card">
            <h2 class="h5 mb-3">标签分布</h2>
            {% for tag in popular_tags %}
                <div class="list-item-row">
                    <div class="fw-semibold">{{ tag.name }}</div>
                    <span class="badge text-bg-primary">{{ tag.course_total }} 门课程</span>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无标签。</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

```

## templates/core/teacher_dashboard.html

```html
{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-1">教师工作台</h1>
        <p class="text-muted mb-0">管理课程、资料、作业和教学统计。</p>
    </div>
    <div class="d-flex gap-2">
        <a class="btn btn-primary" href="{% url 'courses:teacher_create' %}">创建课程</a>
        <a class="btn btn-outline-primary" href="{% url 'assignments:create' %}">发布作业</a>
        <a class="btn btn-outline-dark" href="{% url 'ai_assistant:center' %}">AI 助手</a>
    </div>
</div>

<div class="row g-3 mb-4">
    <div class="col-md-4"><div class="stat-card"><span>课程数</span><strong>{{ stats.course_count }}</strong></div></div>
    <div class="col-md-4"><div class="stat-card"><span>资料数</span><strong>{{ stats.material_count }}</strong></div></div>
    <div class="col-md-4"><div class="stat-card"><span>讨论帖数</span><strong>{{ stats.discussion_count }}</strong></div></div>
    <div class="col-md-3"><div class="stat-card"><span>课程浏览量</span><strong>{{ stats.view_count }}</strong></div></div>
    <div class="col-md-3"><div class="stat-card"><span>课程收藏量</span><strong>{{ stats.favorite_count }}</strong></div></div>
    <div class="col-md-3"><div class="stat-card"><span>签到数</span><strong>{{ stats.attendance_count }}</strong></div></div>
    <div class="col-md-3"><div class="stat-card"><span>分组数</span><strong>{{ stats.group_count }}</strong></div></div>
</div>

<div class="row g-3 mb-4">
    <div class="col-md-3"><a class="section-card d-block text-decoration-none" href="{% url 'ai_assistant:center' %}"><strong>AI 助手</strong><div class="small text-muted mt-2">备课、授课、评价、查重</div></a></div>
    <div class="col-md-3"><a class="section-card d-block text-decoration-none" href="{% url 'attendance:session_list' %}"><strong>签到管理</strong><div class="small text-muted mt-2">发起课堂签到与查看记录</div></a></div>
    <div class="col-md-3"><a class="section-card d-block text-decoration-none" href="{% url 'groups:group_list' %}"><strong>分组管理</strong><div class="small text-muted mt-2">手动创建小组并分配学生</div></a></div>
    <div class="col-md-3"><a class="section-card d-block text-decoration-none" href="{% url 'courses:teacher_list' %}"><strong>成绩导出</strong><div class="small text-muted mt-2">进入作业提交列表导出 CSV</div></a></div>
</div>

<div class="row g-4">
    <div class="col-lg-7">
        <div class="section-card">
            <h2 class="h5 mb-3">我负责的课程</h2>
            {% for course in courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">{{ course.category.name|default:"未分类" }} · 学生 {{ course.enrollment_count }}</div>
                    </div>
                    <div class="d-flex gap-2">
                        <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:teacher_edit' course.pk %}">编辑</a>
                        <a class="btn btn-sm btn-outline-secondary" href="{% url 'courses:teacher_analytics' course.pk %}">统计</a>
                    </div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂未创建课程。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-5">
        <div class="section-card">
            <h2 class="h5 mb-3">待批改作业</h2>
            {% for submission in pending_reviews %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ submission.assignment.title }}</div>
                        <div class="small text-muted">{{ submission.student.full_name }}</div>
                    </div>
                    <a class="btn btn-sm btn-primary" href="{% url 'assignments:review' submission.pk %}">批改</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">当前没有待批改作业。</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

```

## templates/core/student_dashboard.html

```html
{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-1">学生工作台</h1>
        <p class="text-muted mb-0">查看课程、作业和学习统计。</p>
    </div>
    <div class="d-flex gap-2">
        <a class="btn btn-outline-dark" href="{% url 'ai_assistant:student_chat' %}">AI 聊天</a>
        <a class="btn btn-outline-secondary" href="{% url 'courses:recommendations' %}">推荐中心</a>
        <a class="btn btn-outline-primary" href="{% url 'courses:list' %}">浏览课程</a>
    </div>
</div>

<div class="row g-3 mb-4">
    <div class="col-md-4"><div class="stat-card"><span>已加入课程</span><strong>{{ stats.course_count }}</strong></div></div>
    <div class="col-md-4"><div class="stat-card"><span>已提交作业</span><strong>{{ stats.submission_count }}</strong></div></div>
    <div class="col-md-4"><div class="stat-card"><span>平均成绩</span><strong>{{ stats.average_score|floatformat:1 }}</strong></div></div>
    <div class="col-md-6"><div class="stat-card"><span>收藏课程</span><strong>{{ stats.favorite_count }}</strong></div></div>
    <div class="col-md-6"><div class="stat-card"><span>浏览次数</span><strong>{{ stats.view_count }}</strong></div></div>
</div>

<div class="section-card mb-4">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <h2 class="h5 mb-1">学生 AI 聊天</h2>
            <p class="text-muted mb-0">可以让 AI 帮你总结知识点、解释概念、整理复习思路。</p>
        </div>
        <a class="btn btn-primary" href="{% url 'ai_assistant:student_chat' %}">进入聊天</a>
    </div>
</div>

<div class="row g-4">
    <div class="col-lg-7">
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">我的课程</h2>
            {% for course in enrollments %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">教师：{{ course.teacher.full_name }}</div>
                    </div>
                    <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:detail' course.pk %}">进入</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">你还没有加入课程。</p>
            {% endfor %}
        </div>
        <div class="section-card">
            <h2 class="h5 mb-3">待完成作业</h2>
            {% for assignment in pending_assignments %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ assignment.title }}</div>
                        <div class="small text-muted">截止：{{ assignment.due_date|date:"Y-m-d H:i" }}</div>
                    </div>
                    <a class="btn btn-sm btn-primary" href="{% url 'assignments:submit' assignment.pk %}">提交</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">当前没有待提交作业。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-5">
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">我的收藏</h2>
            {% for course in favorite_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">{{ course.category.name|default:"未分类" }}</div>
                    </div>
                    <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:detail' course.pk %}">进入</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂未收藏课程。</p>
            {% endfor %}
        </div>
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">最近浏览</h2>
            {% for course in recent_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">{{ course.category.name|default:"未分类" }} · {{ course.teacher.full_name }}</div>
                    </div>
                    <a class="btn btn-sm btn-outline-secondary" href="{% url 'courses:detail' course.pk %}">查看</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">最近还没有浏览记录。</p>
            {% endfor %}
        </div>
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">最近成绩</h2>
            {% for submission in submissions %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ submission.assignment.title }}</div>
                        <div class="small text-muted">{{ submission.assignment.course.title }}</div>
                    </div>
                    <span class="badge text-bg-primary">{{ submission.score|default:"待批改" }}</span>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无作业记录。</p>
            {% endfor %}
        </div>
        <div class="section-card">
            <h2 class="h5 mb-3">最新通知</h2>
            {% for item in announcements %}
                <div class="mb-3">
                    <div class="fw-semibold">{{ item.title }}</div>
                    <div class="small text-muted">{{ item.created_at|date:"Y-m-d" }}</div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无公告。</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

```

## templates/common/form.html

```html
{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-8">
        <div class="card shadow-sm border-0">
            <div class="card-body p-4">
                <h2 class="h4 mb-4">{{ title }}</h2>
                <form method="post" enctype="multipart/form-data">
                    {% csrf_token %}
                    {{ form.as_p }}
                    <button type="submit" class="btn btn-primary">提交</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

```

## static/css/site.css

```css
:root {
    --bg: #f4efe5;
    --surface: #fffdf8;
    --primary: #1f4b99;
    --accent: #d48a1f;
    --ink: #1d2939;
    --muted: #667085;
}

body {
    background:
        linear-gradient(rgba(244, 239, 229, 0.58), rgba(244, 239, 229, 0.72)),
        url("../images/background.jpg") center center / cover fixed no-repeat,
        var(--bg);
    color: var(--ink);
    min-height: 100vh;
}

.app-navbar {
    background: linear-gradient(90deg, rgba(16, 44, 87, 0.94), rgba(31, 75, 153, 0.94));
    backdrop-filter: blur(10px);
}

.hero-card,
.section-card,
.stat-card,
.course-card,
.glass-panel {
    border-radius: 20px;
    background: rgba(255, 253, 248, 0.84);
    border: 1px solid rgba(255, 255, 255, 0.52);
    box-shadow: 0 18px 46px rgba(16, 44, 87, 0.13);
    backdrop-filter: blur(12px);
}

.hero-card,
.section-card,
.glass-panel {
    padding: 2rem;
}

.course-card {
    padding: 1.5rem;
}

.banner-image {
    height: 180px;
    object-fit: cover;
}

.hero-visual {
    position: relative;
    min-height: 320px;
    border-radius: 24px;
    overflow: hidden;
    background: linear-gradient(140deg, rgba(16, 44, 87, 0.12), rgba(212, 138, 31, 0.14));
    border: 1px solid rgba(16, 44, 87, 0.08);
}

.hero-visual-image {
    width: 100%;
    height: 320px;
    object-fit: cover;
    display: block;
}

.hero-visual-placeholder {
    position: relative;
    height: 320px;
    overflow: hidden;
    background: linear-gradient(135deg, #163d77, #e9b25f);
}

.hero-orb {
    position: absolute;
    border-radius: 999px;
    opacity: 0.7;
}

.hero-orb-a {
    width: 160px;
    height: 160px;
    background: rgba(255, 255, 255, 0.18);
    top: 28px;
    left: 24px;
}

.hero-orb-b {
    width: 220px;
    height: 220px;
    background: rgba(255, 255, 255, 0.12);
    right: -30px;
    bottom: -40px;
}

.hero-screen {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%) rotate(-4deg);
    width: 240px;
    height: 150px;
    border-radius: 18px;
    background: rgba(255, 253, 248, 0.95);
    box-shadow: 0 18px 42px rgba(16, 44, 87, 0.18);
    padding: 1rem;
}

.hero-screen-bar {
    height: 12px;
    width: 72px;
    border-radius: 999px;
    background: rgba(31, 75, 153, 0.2);
    margin-bottom: 1rem;
}

.hero-screen-lines {
    height: calc(100% - 28px);
    border-radius: 12px;
    background:
        linear-gradient(rgba(31, 75, 153, 0.18), rgba(31, 75, 153, 0.18)) 0 0 / 75% 10px no-repeat,
        linear-gradient(rgba(31, 75, 153, 0.12), rgba(31, 75, 153, 0.12)) 0 28px / 100% 10px no-repeat,
        linear-gradient(rgba(31, 75, 153, 0.12), rgba(31, 75, 153, 0.12)) 0 56px / 85% 10px no-repeat,
        linear-gradient(rgba(212, 138, 31, 0.18), rgba(212, 138, 31, 0.18)) 0 92px / 60% 10px no-repeat;
}

.hero-visual-note {
    position: absolute;
    right: 16px;
    bottom: 16px;
    width: min(240px, calc(100% - 32px));
    padding: 1rem;
    border-radius: 18px;
    background: rgba(255, 253, 248, 0.92);
    box-shadow: 0 12px 30px rgba(16, 44, 87, 0.12);
}

.hero-note-title {
    font-weight: 700;
    margin-bottom: 0.75rem;
}

.hero-note-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem;
}

.hero-note-item {
    padding: 0.6rem 0.7rem;
    border-radius: 14px;
    background: rgba(31, 75, 153, 0.08);
    color: var(--primary);
    text-align: center;
    font-size: 0.9rem;
}

.stat-tile,
.stat-card {
    padding: 1rem 1.2rem;
}

.stat-label,
.stat-card span {
    display: block;
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 0.4rem;
}

.stat-value,
.stat-card strong {
    font-size: 1.6rem;
    font-weight: 700;
}

.list-item-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.9rem 0;
    border-bottom: 1px solid rgba(102, 112, 133, 0.16);
}

.list-item-row:last-child {
    border-bottom: 0;
}

.comment-card {
    background: #fff;
    border: 1px solid rgba(16, 44, 87, 0.08);
    border-radius: 14px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.course-thumb {
    width: 100%;
    height: 180px;
    object-fit: cover;
    border-radius: 16px;
    display: block;
}

.course-thumb-placeholder {
    display: flex;
    align-items: end;
    justify-content: start;
    padding: 1rem;
    background:
        linear-gradient(135deg, rgba(31, 75, 153, 0.95), rgba(212, 138, 31, 0.9)),
        var(--surface);
    color: white;
    font-weight: 700;
}

.home-side-panel {
    padding: 1rem 1.1rem;
    border-radius: 18px;
    background: rgba(31, 75, 153, 0.05);
}

.chip {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: rgba(31, 75, 153, 0.08);
    color: var(--primary);
    font-size: 0.82rem;
    margin-right: 0.35rem;
    margin-bottom: 0.35rem;
}

.chip-link {
    text-decoration: none;
}

form p {
    margin-bottom: 1rem;
}

form label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
}

form input,
form textarea,
form select {
    width: 100%;
    border: 1px solid #d0d5dd;
    border-radius: 12px;
    padding: 0.75rem 0.9rem;
}

textarea {
    min-height: 120px;
}

.ai-chat-hero {
    background:
        radial-gradient(circle at top right, rgba(212, 138, 31, 0.18), transparent 26%),
        radial-gradient(circle at bottom left, rgba(31, 75, 153, 0.12), transparent 26%),
        rgba(255, 253, 248, 0.92);
}

.ai-chat-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: flex-end;
}

.ai-chat-panel {
    min-height: 620px;
}

.ai-chat-header {
    margin-bottom: 1rem;
}

.ai-chat-thread {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.chat-bubble {
    max-width: 88%;
    padding: 1rem 1.1rem;
    border-radius: 18px;
    box-shadow: 0 10px 24px rgba(16, 44, 87, 0.08);
}

.chat-bubble-user {
    align-self: flex-end;
    background: linear-gradient(135deg, #1f4b99, #3469c1);
    color: white;
    border-bottom-right-radius: 6px;
}

.chat-bubble-ai {
    align-self: flex-start;
    background: #fff;
    border: 1px solid rgba(16, 44, 87, 0.08);
    border-bottom-left-radius: 6px;
}

.chat-role {
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 0.45rem;
    opacity: 0.85;
}

.ai-chat-empty {
    border: 1px dashed rgba(31, 75, 153, 0.24);
    border-radius: 18px;
    padding: 2rem 1.25rem;
    text-align: center;
    background: rgba(31, 75, 153, 0.03);
}

.ai-chat-empty-title {
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.ai-chat-form {
    padding-top: 1rem;
    border-top: 1px solid rgba(102, 112, 133, 0.16);
}

.suggestion-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.suggestion-card,
.history-card {
    padding: 0.95rem 1rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(16, 44, 87, 0.08);
}

@media (max-width: 768px) {
    .hero-card,
    .section-card,
    .glass-panel {
        padding: 1.25rem;
    }

    .list-item-row {
        flex-direction: column;
        align-items: flex-start;
    }

    .hero-visual,
    .hero-visual-image,
    .hero-visual-placeholder {
        min-height: 260px;
        height: 260px;
    }

    .hero-visual-note {
        position: static;
        width: auto;
        margin: 1rem;
    }

    .hero-screen {
        width: 200px;
        height: 132px;
    }

    .ai-chat-badges {
        justify-content: flex-start;
    }

    .chat-bubble {
        max-width: 100%;
    }
}

```

