# 个性化推荐模块代码

包含基于浏览、收藏、选课标签和热度的推荐服务，以及推荐中心页面。

## courses/services.py

```python
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

## templates/courses/recommendation_center.html

```html
{% extends "base.html" %}
{% block title %}推荐中心{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-1">推荐中心</h1>
        <p class="text-muted mb-0">根据浏览、收藏、选课标签和平台热度生成个性化推荐。</p>
    </div>
    <a class="btn btn-outline-primary" href="{% url 'courses:list' %}">返回课程中心</a>
</div>

<div class="row g-4">
    <div class="col-lg-8">
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">为你推荐</h2>
            <div class="row g-3">
                {% for course in recommended_courses %}
                    <div class="col-md-6">
                        <div class="course-card h-100">
                            <h3 class="h5">{{ course.title }}</h3>
                            <p class="small text-muted">{{ course.teacher.full_name }} · 热度 {{ course.heat_score }}</p>
                            <p>{{ course.summary }}</p>
                            <div class="mb-3">
                                {% for tag in course.tags.all %}
                                    <span class="chip">{{ tag.name }}</span>
                                {% endfor %}
                            </div>
                            <a class="btn btn-sm btn-primary" href="{% url 'courses:detail' course.pk %}">查看课程</a>
                        </div>
                    </div>
                {% empty %}
                    <div class="col-12"><p class="text-muted mb-0">当前推荐不足，可以先多浏览和收藏课程。</p></div>
                {% endfor %}
            </div>
        </div>
        <div class="section-card">
            <h2 class="h5 mb-3">最近浏览</h2>
            {% for course in recent_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">浏览热度 {{ course.heat_score }}</div>
                    </div>
                    <a class="btn btn-sm btn-outline-primary" href="{% url 'courses:detail' course.pk %}">再次查看</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无最近浏览记录。</p>
            {% endfor %}
        </div>
    </div>
    <div class="col-lg-4">
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">我的收藏</h2>
            {% for course in favorite_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">{{ course.category.name|default:"未分类" }}</div>
                    </div>
                    <a href="{% url 'courses:detail' course.pk %}">查看</a>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂未收藏课程。</p>
            {% endfor %}
        </div>
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">热门课程榜</h2>
            {% for course in hot_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">热度 {{ course.heat_score }}</div>
                    </div>
                    <span class="small text-muted">收藏 {{ course.favorite_count }}</span>
                </div>
            {% endfor %}
        </div>
        <div class="section-card">
            <h2 class="h5 mb-3">活跃课程榜</h2>
            {% for course in active_courses %}
                <div class="list-item-row">
                    <div>
                        <div class="fw-semibold">{{ course.title }}</div>
                        <div class="small text-muted">讨论 {{ course.discussion_count }} · 提交 {{ course.submission_count }}</div>
                    </div>
                    <a href="{% url 'courses:detail' course.pk %}">查看</a>
                </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

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

## RECOMMENDATION_ALGORITHM_EXPLANATION.md

```markdown
# CloudClass 推荐算法详细说明

## 1. 先说结论：这个项目的推荐算法是什么

这个项目的推荐算法，不是深度学习模型，也不是复杂的协同过滤系统，而是一个非常典型、非常适合课程设计项目的方案：

> 基于用户行为 + 课程标签 + 平台热度的规则推荐算法

更准确地说，它包含 3 类和“推荐”有关的逻辑：

- 个性化推荐：根据学生的浏览、收藏、选课行为来推荐课程
- 相关推荐：根据当前课程的标签相似性推荐相关课程
- 榜单推荐：根据热度或活跃度对课程排序，形成热门榜和活跃榜

所以，如果有人问“你们项目里的推荐算法是什么”，比较完整的回答应该是：

> 本项目采用了基于行为数据和标签匹配的规则推荐方法，并结合课程热度分数进行排序，同时实现了课程详情页的标签相似相关推荐和平台热门榜单推荐。

---

## 2. 推荐逻辑的代码在哪

推荐逻辑主要集中在两个地方：

- `courses/services.py`
- `courses/views.py`

其中：

- `courses/services.py` 负责“怎么算”
- `courses/views.py` 负责“在哪里调用”

可以把它理解成：

- `services.py` 是推荐算法的“大脑”
- `views.py` 是推荐算法的“使用场景”

---

## 3. 推荐系统到底用到了哪些数据

这个项目的推荐不是凭空生成的，它依赖数据库中已经存在的用户行为和课程信息。

主要用到了 4 类数据。

### 3.1 课程标签数据

来自：

- `CourseTag`
- `Course.tags`

每门课程可以绑定多个标签，比如：

- `Django`
- `MySQL`
- `机器学习`
- `项目实战`

标签的作用相当于课程的“特征词”或者“兴趣主题”。

推荐系统就是通过这些标签，来判断：

- 学生喜欢什么方向
- 两门课程是不是相似

### 3.2 用户浏览数据

来自：

- `CourseViewLog`

每次学生进入课程详情页时，系统会自动写入一条浏览记录。

也就是说，只要学生点开看过，系统就认为：

- 这门课至少引起了他的兴趣

### 3.3 用户收藏数据

来自：

- `CourseFavorite`

收藏比浏览更强，因为浏览可能只是随便看看，但收藏通常意味着：

- 我对这门课比较感兴趣
- 我未来可能还会回来学习

所以收藏数据在热度计算里权重更高。

### 3.4 用户选课数据

来自：

- `CourseEnrollment`

选课是最强的一类行为，因为它代表学生已经从“感兴趣”变成了“正式参与”。

因此在热度计算里，选课的权重最高。

---

## 4. 系统里的“推荐”为什么要分成三种

很多同学第一次看这个项目时，会把“推荐课程”“相关推荐”“热门课程”都当成一回事。其实它们不是同一类逻辑。

### 4.1 个性化推荐

回答的是这个问题：

> 这个学生可能还会喜欢哪些课？

它看的是“用户”和“课程”的匹配关系。

### 4.2 相关推荐

回答的是这个问题：

> 你现在正在看的这门课，和哪些课比较相似？

它看的是“课程”和“课程”的相似关系。

### 4.3 热门榜 / 活跃榜

回答的是这个问题：

> 平台里哪些课现在最火？哪些课最活跃？

它看的是课程本身的整体表现，而不是某个具体学生的兴趣。

这三者一起出现，平台才会显得完整：

- 个性化推荐更像“猜你喜欢”
- 相关推荐更像“看过这个的人也可能关心这些”
- 热门榜更像“全站趋势”

---

## 5. 个性化推荐的核心思想是什么

个性化推荐对应的函数是：

- `get_recommended_courses_for_user(user, limit=6)`

这个函数的思想非常清晰，可以概括成一句话：

> 先根据学生过去的行为，推断他喜欢哪些标签；再去找标签相似、但他还没深入互动过的课程；最后按匹配度和热度排序。

这个逻辑可以拆成 4 步。

---

## 6. 第一步：先判断这个用户能不能做个性化推荐

代码里先做了一个判断：

- 如果用户没有登录
- 或者用户不是学生

那么系统就不做个性化推荐，而是直接返回热门课程。

### 6.1 为什么这样设计

因为：

- 教师和管理员不是平台主要的“被推荐对象”
- 未登录用户没有个人行为数据

如果硬做个性化推荐，系统根本没有依据。

所以这一步是：

- 没有用户画像，就退化成热门推荐

这其实就是推荐系统中的一个常见思路：

- 有画像时做个性化
- 没画像时做公共推荐

---

## 7. 第二步：提取学生的兴趣标签

这是整个个性化推荐里最关键的一步。

系统会分别从 3 类行为里提取标签：

- 已加入课程的标签
- 已收藏课程的标签
- 已浏览课程的标签

代码本质上做的是：

1. 找到学生加入过的课程
2. 取出这些课程对应的标签 id
3. 找到学生收藏过的课程
4. 取出这些课程对应的标签 id
5. 找到学生浏览过的课程
6. 取出这些课程对应的标签 id
7. 把这三部分标签合并成一个集合

### 7.1 为什么要用标签集合

因为标签集合最适合表达“兴趣范围”。

例如一个学生：

- 收藏了 `Django 项目实战`
- 浏览了 `Python Web 开发基础`
- 选了 `Flask 轻量应用开发`

那么系统可能提取出这些标签：

- `Django`
- `Flask`
- `MySQL`
- `项目实战`

这就相当于给这个学生建立了一个非常简化的兴趣画像：

> 他大概率对 Python Web 开发方向感兴趣。

### 7.2 为什么浏览、收藏、选课都要算进去

因为这 3 种行为代表兴趣强度不同，但都能提供线索：

- 浏览：弱兴趣
- 收藏：中等兴趣
- 选课：强兴趣

项目当前没有给这三类行为在“兴趣画像提取”阶段设置不同权重，而是统一当作“兴趣来源”。

这种做法的优点是：

- 实现简单
- 逻辑清晰
- 对课程设计项目足够实用

---

## 8. 第三步：排除已经深度互动过的课程

系统接下来会收集一批“不需要再推荐”的课程，也就是：

- 已经选过的课程
- 已经收藏过的课程

这些课程会被排除掉，不再进入推荐结果。

### 8.1 为什么只排除选课和收藏，没有排除浏览

这是一个很值得讲的细节。

在代码里，被排除的是：

- `CourseEnrollment`
- `CourseFavorite`

没有把 `CourseViewLog` 加进去。

这意味着：

- 浏览过但没收藏、没选课的课程，未来仍然可能再次被推荐

这种设计其实是合理的，因为：

- 浏览可能只是短暂看过
- 收藏和选课才说明“已经明确处理过”

所以系统默认认为：

- 看过一眼，不代表以后不需要再推
- 已经收藏或已经加入，才算真正不必重复推荐

---

## 9. 第四步：按标签匹配度做候选课程筛选

在排除学生已深度互动的课程后，系统会从剩余已发布课程中，找出和用户兴趣标签有交集的课程。

这里用了一个指标：

- `matched_tag_count`

它表示：

> 一门候选课程和用户兴趣标签集合，重合了多少个标签

### 9.1 举个简单例子

假设学生的兴趣标签集合是：

- `Django`
- `MySQL`
- `项目实战`

现在有三门候选课程：

课程 A 标签：

- `Django`
- `MySQL`

课程 B 标签：

- `机器学习`
- `算法基础`

课程 C 标签：

- `Django`
- `项目实战`
- `JavaScript`

那么：

- 课程 A 的匹配标签数是 2
- 课程 B 的匹配标签数是 0
- 课程 C 的匹配标签数是 2

系统会先把匹配数大于 0 的课程留下来，也就是：

- A 留下
- B 去掉
- C 留下

这一步可以理解成：

> 先保证“方向对”，再谈热度高不高。

---

## 10. 第五步：按什么顺序排序推荐结果

如果存在兴趣标签，系统最终排序规则是：

1. 先按 `matched_tag_count` 从高到低
2. 再按 `heat_score` 从高到低
3. 最后按 `created_at` 从新到旧

也就是说，推荐排序的优先级是：

- 先看像不像你喜欢的
- 再看这门课受不受欢迎
- 再看它新不新

### 10.1 这个排序逻辑的含义

#### 第一层：标签匹配

这是个性化推荐最重要的部分。

因为推荐系统首先要回答：

> 这门课是不是你可能感兴趣的方向？

#### 第二层：课程热度

如果两门课都符合用户兴趣，那系统更倾向推荐：

- 更多人看过
- 更多人收藏
- 更多人加入

的课程。

这相当于在个性化基础上叠加了“群体智慧”。

#### 第三层：新鲜度

如果匹配度和热度都差不多，那更近发布的课程优先。

这样可以避免系统总是推很老的内容。

---

## 11. 如果没有兴趣标签，会怎么推荐

如果学生虽然登录了，但还没有形成任何兴趣标签，比如：

- 没浏览过课程
- 没收藏过课程
- 没加入过课程

那么 `tag_ids` 就会是空的。

此时系统不会报错，也不会返回空结果，而是直接走：

- 按热度排序推荐

也就是：

1. 先算课程热度
2. 按热度从高到低排
3. 返回前 N 个课程

### 11.1 这就是冷启动处理

在推荐系统里，最常见的问题之一就是：

> 新用户没有历史数据，怎么推荐？

这个项目的解决办法很朴素，但很有效：

- 新用户看热门课
- 老用户看个性化课

这就是典型的冷启动策略。

---

## 12. 热度分数到底是什么

热度分数来自：

- `with_course_metrics(queryset)`

它除了给课程补充各种统计字段，还计算了一个 `heat_score`。

计算公式是：

`heat_score = 浏览数 + 收藏数 × 2 + 选课人数 × 3`

### 12.1 为什么要这样算

因为不同的行为，价值不同。

#### 浏览

表示：

- 用户点开看过

这是最轻的一层兴趣，所以权重是 1。

#### 收藏

表示：

- 用户明确觉得这门课值得保留

它比浏览更有价值，所以权重是 2。

#### 选课

表示：

- 用户真正加入了课程

这是最强的正向行为，所以权重是 3。

### 12.2 这个公式的本质是什么

本质上是在做一个非常简单的“行为打分模型”：

- 弱行为加少一点
- 强行为加多一点

虽然不复杂，但已经足够支持：

- 热门课排序
- 个性化推荐中的辅助排序
- 首页榜单展示

---

## 13. 热门课程榜是怎么来的

热门课程榜对应的函数是：

- `get_hot_courses(limit=6)`

它的逻辑是：

1. 找出所有已发布课程
2. 给每门课程计算各种统计指标和热度分数
3. 按以下顺序排序

排序规则是：

1. `heat_score` 降序
2. `discussion_count` 降序
3. `created_at` 降序

### 13.1 为什么讨论数也会参与排序

因为热度分数里只包含：

- 浏览
- 收藏
- 选课

但一门真正“活”的课程，往往还会有：

- 更多讨论

所以当热度相近时，讨论更多的课程会更靠前。

---

## 14. 活跃课程榜是怎么来的

活跃课程榜对应的是：

- `get_active_courses(limit=6)`

它不再主要看“受欢迎程度”，而是更看“课程有没有在持续发生教学活动”。

排序规则是：

1. `discussion_count` 降序
2. `submission_count` 降序
3. `material_count` 降序
4. `created_at` 降序

### 14.1 这说明了什么

热门课和活跃课是不同概念：

- 热门课：很多人关注
- 活跃课：老师和学生互动频繁

这个区分很有意义，因为：

- 有些课很火，但不一定真的在持续学习
- 有些课讨论和作业很多，说明教学活跃

---

## 15. 相关推荐是怎么来的

相关推荐出现在课程详情页，对应的是 `course_detail()` 里的这段逻辑。

它做的事情很简单：

1. 取出当前课程的所有标签
2. 查找所有和这些标签有交集的已发布课程
3. 排除当前课程本身
4. 计算热度指标
5. 去重
6. 按热度和时间排序
7. 取前 4 门

### 15.1 相关推荐的本质是什么

相关推荐本质上不是“根据用户推荐”，而是：

> 根据当前课程本身的内容特征，找相似课程

所以它更准确地说，属于：

- 内容相似推荐

### 15.2 举个例子

如果当前课程是：

- `Django 项目实战`

它的标签是：

- `Django`
- `项目实战`

那么系统会去找所有标签中包含：

- `Django`
或
- `项目实战`

的其他课程。

这样得到的课程通常会是：

- 主题类似
- 技术方向接近
- 学习人群相似

### 15.3 为什么相关推荐没有单独计算“相似度分数”

当前代码里，相关推荐只要求：

- 至少共享一个标签

然后直接按：

- 热度分数
- 创建时间

排序。

也就是说，在“相关推荐”逻辑中：

- 标签交集只用来做筛选
- 热度用来做排序

这是一种非常实用的简化设计。

如果后续要升级，可以进一步加上：

- 共同标签数量
- 标签权重
- 分类相似度

但目前这个版本已经足够支撑课程设计项目。

---

## 16. 课程中心里的推荐课程是怎么来的

课程中心页面里会显示一个“推荐课程”区域。

它调用的是：

- `get_recommended_courses_for_user(request.user, limit=6)`

所以它和推荐中心页中的“为你推荐”本质上是同一套个性化推荐算法，只是展示位置不同。

### 16.1 为什么要在多个地方复用

因为推荐本来就不是一个独立页面才需要的功能，它应该分散出现在多个场景：

- 首页
- 课程中心
- 推荐中心
- 学生工作台

这说明项目在设计时，已经把推荐做成了一个可复用服务函数，而不是写死在某个页面里。

这是一种比较规范的后端设计方式。

---

## 17. 推荐中心页面除了个性化推荐，还展示了什么

推荐中心页面并不只显示“推荐结果”，它还同时展示：

- 为你推荐
- 最近浏览
- 我的收藏
- 热门课程榜
- 活跃课程榜

### 17.1 为什么要这样设计

因为一个真正可用的推荐中心，不应该只给出“系统猜你喜欢什么”，还应该把推荐依据附近的内容也展示出来。

这样学生会更容易理解：

- 我最近看过什么
- 我收藏过什么
- 平台上哪些课最热门
- 哪些课最活跃

虽然代码里没有直接显示“因为你看过某某课程，所以推荐某某课程”，但页面结构已经把推荐上下文补出来了。

---

## 18. 这个推荐算法到底属于什么类型

如果从推荐系统理论角度来分类，这个项目主要属于下面两类的组合。

### 18.1 基于内容的推荐

体现在：

- 利用课程标签判断相似性
- 用标签匹配课程和用户兴趣
- 用标签交集寻找相关推荐

因为标签本身就是课程内容的抽象特征，所以这部分属于：

- Content-Based Recommendation

### 18.2 基于规则的推荐

体现在：

- 手动定义热度公式
- 手动定义排序优先级
- 手动定义冷启动策略

系统不是让模型自己学习，而是开发者直接规定规则，因此也属于：

- Rule-Based Recommendation

### 18.3 为什么不算协同过滤

协同过滤通常会看：

- 用户和用户之间的相似性
- 课程和课程之间的共同行为模式

比如：

- 喜欢 A 课的人，也常喜欢 B 课

而当前项目没有去计算：

- 相似学生群体
- 共现课程矩阵

所以它还不属于严格意义上的协同过滤推荐。

---

## 19. 这个算法的优点是什么

### 19.1 容易实现

全部逻辑都能通过 Django ORM 实现，不需要额外引入机器学习框架。

### 19.2 容易解释

每一步都很清楚：

- 用户喜欢哪些标签
- 课程标签匹配多少
- 课程热度高不高

这对答辩非常友好，因为老师一问“为什么推荐这门课”，你可以说得很明白。

### 19.3 可解释性强

复杂模型有时很准，但解释困难。

而这个项目里的推荐逻辑几乎完全可解释：

- 因为你之前看过或收藏过某类标签课程
- 因为这门课和你的兴趣标签匹配
- 因为这门课本身热度更高

### 19.4 对小数据量项目很合适

课程设计阶段数据量通常不大，使用这种规则推荐非常合适。

如果硬上复杂算法，反而可能：

- 数据不够
- 效果不稳定
- 很难讲清楚

---

## 20. 这个算法的局限性是什么

如果要更客观地评价，这个推荐算法也有明显局限。

### 20.1 没有行为权重细分到兴趣画像阶段

目前浏览、收藏、选课在“兴趣标签提取”时是同等对待的。

更合理的做法可能是：

- 浏览标签记 1 分
- 收藏标签记 2 分
- 选课标签记 3 分

这样兴趣画像会更细致。

### 20.2 没有时间衰减

系统不会区分：

- 昨天浏览的课程
- 半年前浏览的课程

它们都可能同样影响推荐。

而现实中，越新的行为通常越能代表当前兴趣。

### 20.3 没有真正的用户相似性建模

它不会分析：

- 和你相似的学生还喜欢什么

因此推荐结果更像“标签匹配”，而不是“群体协同推荐”。

### 20.4 相关推荐比较粗糙

相关推荐只判断：

- 是否共享标签

没有进一步比较：

- 共享标签数量
- 分类是否一致
- 教师是否相同
- 是否有共同学习路径

所以相关推荐是“能用”，但还不算很精细。

---

## 21. 如果要在答辩时解释相关推荐，可以怎么讲

最通俗的说法是：

> 相关推荐不是看当前用户喜欢什么，而是看当前这门课和其他课程像不像。项目通过课程标签来判断相似性，只要其他课程和当前课程共享标签，就认为它们相关，再结合课程热度进行排序，展示最相关、最热门的几门课程。

这个说法比较准确，也比较好懂。

---

## 22. 如果要在答辩时解释个性化推荐，可以怎么讲

可以这样说：

> 个性化推荐主要基于学生的历史行为，包括浏览、收藏和选课。系统会提取这些行为涉及课程的标签，形成用户兴趣标签集合；然后从未深度互动过的课程中，筛选出标签匹配的课程，并按照匹配标签数量、课程热度和发布时间排序，返回推荐结果。如果用户是新用户，没有足够行为数据，系统则退化为热门课程推荐。

这段话基本已经是比较标准的答辩表述。

---

## 23. 如果把整个推荐系统画成流程，可以怎么理解

### 23.1 个性化推荐流程

1. 用户进入系统
2. 系统判断是否登录且是否为学生
3. 如果不是学生或没登录，直接返回热门课程
4. 如果是学生，就统计其浏览、收藏、选课对应的课程标签
5. 得到兴趣标签集合
6. 排除已经选过和收藏过的课程
7. 在剩余课程中找标签匹配课程
8. 计算标签匹配数
9. 按匹配数、热度、时间排序
10. 输出推荐结果

### 23.2 相关推荐流程

1. 学生或教师打开某门课程详情页
2. 系统读取当前课程标签
3. 查找共享这些标签的其他课程
4. 排除当前课程本身
5. 计算这些课程的热度
6. 按热度和时间排序
7. 返回前 4 门课程作为相关推荐

### 23.3 热门榜流程

1. 统计每门课的浏览数、收藏数、选课人数
2. 计算热度分数
3. 按热度、讨论数、发布时间排序
4. 输出热门课程榜

---

## 24. 为什么说这个推荐系统很适合课程项目

因为它在三方面取得了平衡。

### 24.1 功能上够完整

它不是只有一个“推荐按钮”，而是形成了完整推荐生态：

- 个性化推荐
- 热门榜
- 活跃榜
- 相关推荐

### 24.2 技术上够现实

它完全基于现有数据库和 Django ORM 实现，不依赖复杂训练流程。

### 24.3 表达上够清楚

老师问：

- 为什么推荐这个？
- 数据从哪里来？
- 新用户怎么办？
- 相关推荐怎么算？

这些问题都能回答得很清楚。

这对课程设计来说，非常重要。

---

## 25. 如果后续要升级，可以怎么改进

这个推荐算法已经够用，但如果要继续升级，可以往下面方向发展。

### 25.1 给兴趣标签加权

例如：

- 浏览标签 +1
- 收藏标签 +2
- 选课标签 +3

然后按总分生成更精细的用户兴趣画像。

### 25.2 引入时间衰减

最近的行为权重更高，较早的行为权重更低。

### 25.3 提高相关推荐精度

可以新增相似度公式，例如：

- 相同标签数量越多，分数越高
- 同分类加分
- 同教师加分

### 25.4 加入协同过滤

可以进一步分析：

- 喜欢某类课的学生，还常喜欢什么别的课

这样推荐会更“像真人经验”。

### 25.5 结合作业和讨论行为

现在推荐主要依赖浏览、收藏、选课。

未来还可以把：

- 作业提交
- 讨论发帖
- 评论互动

也纳入兴趣建模。

---

## 26. 最后做一个总总结

CloudClass 的推荐算法，本质上是一个基于行为数据、标签匹配和课程热度的规则推荐系统。

它主要分为三部分：

- 个性化推荐：根据学生的浏览、收藏、选课行为提取兴趣标签，再推荐标签相似且未深度互动的课程
- 相关推荐：根据当前课程的标签，寻找内容相近的其他课程
- 热门/活跃榜：根据平台整体行为数据，对课程进行排序展示

它的特点是：

- 实现简单
- 逻辑清楚
- 可解释性强
- 适合课程设计和答辩展示

如果用一句最简洁的话概括，可以说：

> 这个项目的推荐系统不是“黑盒 AI”，而是一个基于用户行为和课程标签的可解释规则推荐系统，通过标签匹配判断兴趣方向，通过热度分数评估课程质量，再结合场景生成个性化推荐、相关推荐和热门榜单。


```

## RECOMMENDATION_ALGORITHM_SUMMARY.md

```markdown
# CloudClass 推荐算法简要总结

## 1. 推荐算法是什么

本项目的推荐算法属于：

- 基于用户行为的规则推荐
- 基于课程标签的内容推荐

它没有使用复杂的机器学习模型，而是根据学生的实际操作记录和课程标签来生成推荐结果。

---

## 2. 推荐主要依据什么

系统主要参考以下几类数据：

- 浏览记录：学生看过哪些课程
- 收藏记录：学生收藏了哪些课程
- 选课记录：学生加入了哪些课程
- 课程标签：课程属于哪些主题方向

通过这些数据，系统可以判断学生大概对什么类型的课程更感兴趣。

---

## 3. 个性化推荐怎么来的

个性化推荐的基本思路是：

1. 统计学生浏览、收藏、选过的课程
2. 提取这些课程对应的标签
3. 形成学生的兴趣标签集合
4. 从其他课程里找出标签相似的课程
5. 排除已经收藏或已经加入的课程
6. 按匹配度和课程热度排序
7. 返回推荐结果

简单说就是：

> 你以前对什么课程感兴趣，系统就继续给你推荐相近方向的课程。

---

## 4. 热门课程怎么来的

系统会给每门课程计算一个热度分数：

`热度 = 浏览数 + 收藏数 × 2 + 选课人数 × 3`

这个公式表示：

- 浏览说明有人关注
- 收藏说明兴趣更强
- 选课说明真正参与

所以选课权重最高，收藏次之，浏览最低。

热门课程榜就是按这个热度分数排序得到的。

---

## 5. 相关推荐怎么来的

相关推荐出现在课程详情页。

它的生成方式是：

1. 读取当前课程的标签
2. 查找其他拥有相同标签的课程
3. 排除当前课程本身
4. 按课程热度排序
5. 选出前几门作为相关推荐

所以相关推荐的核心不是“根据当前用户”，而是：

> 根据当前这门课本身的标签，找内容相似的课程。

---

## 6. 新用户怎么办

如果用户刚注册，还没有浏览、收藏、选课记录，系统就没有足够数据做个性化推荐。

这时会采用冷启动策略：

- 直接推荐热门课程

也就是说：

- 老用户看个性化推荐
- 新用户先看平台热门课

---

## 7. 这个推荐算法的特点

优点：

- 实现简单
- 容易解释
- 适合课程设计项目
- 不依赖复杂模型

不足：

- 还没有引入协同过滤
- 没有考虑时间衰减
- 浏览、收藏、选课在兴趣画像里没有进一步细分权重

---

## 8. 一句话总结

CloudClass 的推荐算法本质上是一个基于学生行为记录、课程标签和课程热度的规则推荐系统，通过“兴趣标签匹配 + 热度排序”生成个性化推荐，通过“共享标签 + 热度排序”生成相关推荐。


```

