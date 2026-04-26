# AI 功能模块代码

包含教师 AI 助教、学生 AI 聊天、AI 交互日志模型、表单、服务、路由和模板。

## ai_assistant/models.py

```python
from django.conf import settings
from django.db import models

from assignments.models import Assignment, AssignmentSubmission
from courses.models import Course


class AIInteractionLog(models.Model):
    class Modes(models.TextChoices):
        LESSON_PREP = "lesson_prep", "AI 备课"
        LESSON_TEACHING = "lesson_teaching", "AI 授课"
        EVALUATION = "evaluation", "AI 评价"
        GRADING = "grading", "AI 辅助批阅"
        PLAGIARISM = "plagiarism", "AI 查重"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_logs", verbose_name="教师"
    )
    mode = models.CharField("AI 模式", max_length=32, choices=Modes.choices)
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, blank=True, null=True, related_name="ai_logs", verbose_name="课程"
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ai_logs",
        verbose_name="作业",
    )
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ai_logs",
        verbose_name="作业提交",
    )
    prompt = models.TextField("输入内容")
    response = models.TextField("AI 输出")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "AI 交互记录"
        verbose_name_plural = "AI 交互记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_mode_display()} - {self.teacher}"


class StudentAIChatMessage(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_ai_messages", verbose_name="学生"
    )
    question = models.TextField("提问内容")
    answer = models.TextField("AI 回复")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "学生 AI 聊天记录"
        verbose_name_plural = "学生 AI 聊天记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} - 学生AI聊天"

```

## ai_assistant/forms.py

```python
from django import forms

from assignments.models import Assignment
from courses.models import Course

from .models import AIInteractionLog


class TeacherAIAssistantForm(forms.Form):
    mode = forms.ChoiceField(label="AI 模式", choices=AIInteractionLog.Modes.choices)
    course = forms.ModelChoiceField(label="关联课程", queryset=Course.objects.none(), required=False)
    assignment = forms.ModelChoiceField(label="关联作业", queryset=Assignment.objects.none(), required=False)
    prompt = forms.CharField(
        label="输入内容",
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "请输入教学目标、课堂需求、评价要求等内容。"}),
    )

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            courses = Course.objects.filter(teacher=teacher).order_by("title")
            assignments = Assignment.objects.filter(created_by=teacher).select_related("course").order_by("title")
            self.fields["course"].queryset = courses
            self.fields["assignment"].queryset = assignments


class StudentAIChatForm(forms.Form):
    question = forms.CharField(
        label="想问 AI 的问题",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "比如：请帮我总结一下这门课的重点，或者解释一个知识点。",
            }
        ),
    )

```

## ai_assistant/services.py

```python
import json
import os
from difflib import SequenceMatcher
from urllib import error, request

from assignments.models import AssignmentSubmission


class TeacherAIService:
    api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model = "qwen-plus"

    MODE_INSTRUCTIONS = {
        "lesson_prep": "你是一名高校课程助教，请输出备课建议，包含教学目标、知识点大纲、课堂活动和课后建议。",
        "lesson_teaching": "你是一名高校课堂助教，请输出授课提纲，包含讲解步骤、互动提问和随堂练习。",
        "evaluation": "你是一名高校教师助教，请针对学生表现输出评价草稿和改进建议。",
        "grading": "你是一名严谨的助教，请基于作业要求给出建议分数、评分依据和教师评语草稿。",
    }

    @classmethod
    def generate(cls, mode, prompt):
        instruction = cls.MODE_INSTRUCTIONS.get(mode)
        if not instruction:
            raise ValueError("不支持的 AI 模式")

        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            return cls._build_demo_response(mode, prompt, "未检测到 DASHSCOPE_API_KEY，当前返回本地演示建议。")

        result = cls._call_dashscope(
            api_key=api_key,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        if result.get("error_notice"):
            return cls._build_demo_response(mode, prompt, result["error_notice"])

        content = (
            result["data"].get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if not content:
            return cls._build_demo_response(mode, prompt, "千问暂未返回有效结果，当前返回本地演示建议。")
        return {"content": content, "notice": "结果由千问生成，仅供教师参考。"}

    @classmethod
    def student_chat(cls, question):
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            return {
                "content": (
                    "这是学生 AI 聊天的本地演示回复。\n"
                    "你可以继续追问课程重点、作业思路、知识点解释、复习建议等内容。\n"
                    f"本次问题参考：{question.strip()[:180] or '未提供问题'}"
                ),
                "notice": "未检测到 DASHSCOPE_API_KEY，当前返回本地演示回复。",
            }

        result = cls._call_dashscope(
            api_key=api_key,
            messages=[
                {
                    "role": "system",
                    "content": "你是一名面向大学生的课程学习助手，请用通俗、友好的中文回答问题，帮助学生理解课程内容。",
                },
                {"role": "user", "content": question},
            ],
            temperature=0.6,
        )
        if result.get("error_notice"):
            return {
                "content": (
                    "千问暂时不可用，当前返回本地演示回复。\n"
                    "建议你从课程目标、知识点、作业要求这几个角度继续整理问题，再和老师确认。"
                ),
                "notice": result["error_notice"],
            }

        content = result["data"].get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            return {
                "content": "当前没有拿到有效回复，你可以换个问法再试一次。",
                "notice": "千问暂未返回有效结果。",
            }
        return {"content": content, "notice": "结果由千问生成，仅供学习参考。"}

    @classmethod
    def analyze_similarity(cls, assignment):
        submissions = list(
            AssignmentSubmission.objects.filter(assignment=assignment).select_related("student").order_by("student__username")
        )
        pairs = []
        for index, left in enumerate(submissions):
            for right in submissions[index + 1 :]:
                left_text = (left.content or "").strip()
                right_text = (right.content or "").strip()
                if not left_text or not right_text:
                    continue
                ratio = SequenceMatcher(None, left_text, right_text).ratio()
                if ratio >= 0.55:
                    pairs.append(
                        {
                            "left": left,
                            "right": right,
                            "ratio": round(ratio * 100, 1),
                            "summary": "两份文本存在较高相似度，建议教师进一步人工核查。",
                        }
                    )
        if not pairs:
            return {
                "content": "未发现高相似度提交，建议仍结合附件与答题结构进行人工复核。",
                "pairs": [],
                "notice": "查重基于文本相似度计算，仅供教师参考。",
            }
        lines = [
            f"{item['left'].student.full_name} 与 {item['right'].student.full_name} 相似度约 {item['ratio']}%"
            for item in pairs
        ]
        return {
            "content": "\n".join(lines),
            "pairs": pairs,
            "notice": "查重基于文本相似度计算，仅供教师参考。",
        }

    @classmethod
    def _build_demo_response(cls, mode, prompt, notice):
        short_prompt = prompt.strip()[:180] or "未提供具体内容"
        templates = {
            "lesson_prep": (
                "1. 教学目标：明确本节课核心能力与产出。\n"
                "2. 知识点大纲：按基础概念、案例演示、课堂练习展开。\n"
                "3. 课堂活动：安排 1 次提问互动和 1 次小练习。\n"
                f"4. 结合你的输入继续完善：{short_prompt}"
            ),
            "lesson_teaching": (
                "1. 导入：用实际场景引出主题。\n"
                "2. 讲授：按知识点逐步讲解并穿插示例。\n"
                "3. 互动：准备 3 个课堂提问和 1 个随堂练习。\n"
                f"4. 当前授课重点：{short_prompt}"
            ),
            "evaluation": (
                "1. 学习表现：整体完成度较好，能围绕任务要求展开。\n"
                "2. 优点：结构清晰，关键知识点覆盖较完整。\n"
                "3. 建议：补充案例分析与个人思考，提升深度。\n"
                f"4. 评价依据参考：{short_prompt}"
            ),
            "grading": (
                "建议分数：88 分\n"
                "评分依据：完成了主要要求，结构较清晰，但分析深度仍有提升空间。\n"
                "教师评语：整体完成较好，建议补充案例论证，并进一步展开关键步骤说明。\n"
                f"参考内容：{short_prompt}"
            ),
        }
        return {"content": templates[mode], "notice": notice}

    @classmethod
    def _call_dashscope(cls, api_key, messages, temperature):
        payload = {
            "model": os.getenv("DASHSCOPE_MODEL", cls.model),
            "messages": messages,
            "temperature": temperature,
        }
        req = request.Request(
            cls.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"data": data}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                error_data = json.loads(body).get("error", {})
            except json.JSONDecodeError:
                error_data = {}
            code = error_data.get("code", "")
            if code == "AccessDenied.Unpurchased":
                model_name = os.getenv("DASHSCOPE_MODEL", cls.model)
                return {"error_notice": f"当前 DashScope 账号没有 `{model_name}` 的调用权限，已返回本地演示内容。"}
            message = error_data.get("message") or f"HTTP {exc.code}"
            return {"error_notice": f"千问调用失败：{message}，已返回本地演示内容。"}
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return {"error_notice": "千问调用失败，当前返回本地演示内容。"}

```

## ai_assistant/views.py

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, render

from accounts.decorators import student_required, teacher_required
from assignments.models import AssignmentSubmission

from .forms import StudentAIChatForm, TeacherAIAssistantForm
from .models import AIInteractionLog, StudentAIChatMessage
from .services import TeacherAIService


@teacher_required
def assistant_center(request):
    result = None
    plagiarism_result = None
    form = TeacherAIAssistantForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        mode = form.cleaned_data["mode"]
        course = form.cleaned_data["course"]
        assignment = form.cleaned_data["assignment"]
        prompt = form.cleaned_data["prompt"]
        if mode == AIInteractionLog.Modes.PLAGIARISM:
            if not assignment:
                messages.error(request, "AI 查重模式需要先选择作业。")
            else:
                plagiarism_result = TeacherAIService.analyze_similarity(assignment)
                AIInteractionLog.objects.create(
                    teacher=request.user,
                    mode=mode,
                    course=course or assignment.course,
                    assignment=assignment,
                    prompt=prompt or f"查重作业：{assignment.title}",
                    response=plagiarism_result["content"],
                )
        else:
            result = TeacherAIService.generate(mode, prompt)
            AIInteractionLog.objects.create(
                teacher=request.user,
                mode=mode,
                course=course,
                assignment=assignment,
                prompt=prompt,
                response=result["content"],
            )
    recent_logs = AIInteractionLog.objects.filter(teacher=request.user).select_related("course", "assignment")[:8]
    return render(
        request,
        "ai_assistant/center.html",
        {"form": form, "result": result, "plagiarism_result": plagiarism_result, "recent_logs": recent_logs},
    )


@teacher_required
def generate_review_suggestion(request, submission_id):
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related("assignment", "student", "assignment__course"),
        pk=submission_id,
        assignment__created_by=request.user,
    )
    prompt = (
        f"课程：{submission.assignment.course.title}\n"
        f"作业：{submission.assignment.title}\n"
        f"作业说明：{submission.assignment.description}\n"
        f"学生：{submission.student.full_name}\n"
        f"提交说明：{submission.content or '无'}\n"
        f"是否有附件：{'有' if submission.attachment else '无'}"
    )
    result = TeacherAIService.generate(AIInteractionLog.Modes.GRADING, prompt)
    AIInteractionLog.objects.create(
        teacher=request.user,
        mode=AIInteractionLog.Modes.GRADING,
        course=submission.assignment.course,
        assignment=submission.assignment,
        submission=submission,
        prompt=prompt,
        response=result["content"],
    )
    return render(
        request,
        "ai_assistant/review_suggestion.html",
        {"submission": submission, "result": result},
    )


@student_required
def student_chat(request):
    result = None
    form = StudentAIChatForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        question = form.cleaned_data["question"]
        result = TeacherAIService.student_chat(question)
        StudentAIChatMessage.objects.create(student=request.user, question=question, answer=result["content"])
    chat_history = StudentAIChatMessage.objects.filter(student=request.user)[:10]
    return render(
        request,
        "ai_assistant/student_chat.html",
        {"form": form, "result": result, "chat_history": chat_history},
    )

```

## ai_assistant/urls.py

```python
from django.urls import path

from . import views

app_name = "ai_assistant"

urlpatterns = [
    path("", views.assistant_center, name="center"),
    path("student-chat/", views.student_chat, name="student_chat"),
    path("submission/<int:submission_id>/review-suggestion/", views.generate_review_suggestion, name="review_suggestion"),
]

```

## templates/ai_assistant/center.html

```html
{% extends "base.html" %}
{% block title %}AI 助手中心{% endblock %}
{% block content %}
<div class="row g-4">
    <div class="col-lg-7">
        <div class="section-card">
            <h1 class="h3 mb-3">AI 助手中心</h1>
            <p class="text-muted">支持 AI 备课、AI 授课、AI 评价、AI 辅助批阅、AI 查重。所有结果仅供教师参考。</p>
            <form method="post">
                {% csrf_token %}
                {{ form.as_p }}
                <button type="submit" class="btn btn-primary">生成建议</button>
            </form>
        </div>
        {% if result %}
            <div class="section-card mt-4">
                <h2 class="h5 mb-3">AI 结果</h2>
                <div class="alert alert-info">{{ result.notice }}</div>
                <div style="white-space: pre-wrap;">{{ result.content }}</div>
            </div>
        {% endif %}
        {% if plagiarism_result %}
            <div class="section-card mt-4">
                <h2 class="h5 mb-3">查重结果</h2>
                <div class="alert alert-info">{{ plagiarism_result.notice }}</div>
                <div style="white-space: pre-wrap;">{{ plagiarism_result.content }}</div>
                {% if plagiarism_result.pairs %}
                    <hr>
                    {% for item in plagiarism_result.pairs %}
                        <div class="mb-2">
                            <strong>{{ item.left.student.full_name }}</strong> 与 <strong>{{ item.right.student.full_name }}</strong>
                            <span class="text-muted">相似度 {{ item.ratio }}%</span>
                        </div>
                    {% endfor %}
                {% endif %}
            </div>
        {% endif %}
    </div>
    <div class="col-lg-5">
        <div class="section-card">
            <h2 class="h5 mb-3">最近 AI 记录</h2>
            {% for item in recent_logs %}
                <div class="mb-3">
                    <div class="fw-semibold">{{ item.get_mode_display }}</div>
                    <div class="small text-muted">
                        {{ item.course.title|default:"未关联课程" }}
                        {% if item.assignment %} · {{ item.assignment.title }}{% endif %}
                        · {{ item.created_at|date:"Y-m-d H:i" }}
                    </div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">暂无 AI 记录。</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

```

## templates/ai_assistant/student_chat.html

```html
{% extends "base.html" %}
{% block title %}学生 AI 聊天{% endblock %}
{% block content %}
<div class="ai-chat-hero section-card mb-4">
    <div class="row align-items-center g-4">
        <div class="col-lg-8">
            <h1 class="h3 mb-2">学生 AI 聊天</h1>
            <p class="text-muted mb-0">可以把它当成一个学习搭子，用来问课程重点、概念解释、作业理解和复习建议。</p>
        </div>
        <div class="col-lg-4">
            <div class="ai-chat-badges">
                <span class="chip">知识点解释</span>
                <span class="chip">复习建议</span>
                <span class="chip">作业思路</span>
                <span class="chip">学习规划</span>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <div class="col-lg-8">
        <div class="section-card ai-chat-panel">
            <div class="ai-chat-header">
                <h2 class="h5 mb-1">对话区</h2>
                <p class="text-muted mb-0">输入一个问题，AI 会给你一段学习参考答案。</p>
            </div>
            {% if result %}
                <div class="alert alert-info">{{ result.notice }}</div>
            {% endif %}
            <div class="ai-chat-thread mb-4">
                {% if result %}
                    <div class="chat-bubble chat-bubble-user">
                        <div class="chat-role">我</div>
                        <div style="white-space: pre-wrap;">{{ form.question.value }}</div>
                    </div>
                    <div class="chat-bubble chat-bubble-ai">
                        <div class="chat-role">AI 学习助手</div>
                        <div style="white-space: pre-wrap;">{{ result.content }}</div>
                    </div>
                {% elif chat_history %}
                    {% with latest=chat_history|first %}
                        <div class="chat-bubble chat-bubble-user">
                            <div class="chat-role">我</div>
                            <div style="white-space: pre-wrap;">{{ latest.question }}</div>
                        </div>
                        <div class="chat-bubble chat-bubble-ai">
                            <div class="chat-role">AI 学习助手</div>
                            <div style="white-space: pre-wrap;">{{ latest.answer }}</div>
                        </div>
                    {% endwith %}
                {% else %}
                    <div class="ai-chat-empty">
                        <div class="ai-chat-empty-title">开始你的第一轮提问</div>
                        <p class="text-muted mb-0">比如让 AI 帮你总结课程重点，或者解释某个看不懂的概念。</p>
                    </div>
                {% endif %}
            </div>
            <form method="post" class="ai-chat-form">
                {% csrf_token %}
                {{ form.as_p }}
                <button type="submit" class="btn btn-primary">发送给 AI</button>
            </form>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="section-card mb-4">
            <h2 class="h5 mb-3">建议提问</h2>
            <div class="suggestion-list">
                <div class="suggestion-card">帮我总结一下这门课的重点知识。</div>
                <div class="suggestion-card">请用通俗的话解释一个我没学懂的概念。</div>
                <div class="suggestion-card">给我一份期末复习计划。</div>
                <div class="suggestion-card">这道作业题我应该从哪里下手？</div>
            </div>
        </div>
        <div class="section-card">
            <h2 class="h5 mb-3">最近聊天记录</h2>
            {% for item in chat_history %}
                <div class="history-card">
                    <div class="fw-semibold">问：{{ item.question|truncatechars:60 }}</div>
                    <div class="small text-muted mb-2">{{ item.created_at|date:"Y-m-d H:i" }}</div>
                    <div class="small" style="white-space: pre-wrap;">{{ item.answer|truncatechars:160 }}</div>
                </div>
            {% empty %}
                <p class="text-muted mb-0">还没有聊天记录，先试着问一个课程问题吧。</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}

```

## templates/ai_assistant/review_suggestion.html

```html
{% extends "base.html" %}
{% block title %}AI 辅助批阅{% endblock %}
{% block content %}
<div class="section-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h1 class="h4 mb-0">AI 辅助批阅建议</h1>
        <a class="btn btn-outline-secondary" href="{% url 'assignments:review' submission.pk %}">返回批改页</a>
    </div>
    <p class="text-muted">学生：{{ submission.student.full_name }} · 作业：{{ submission.assignment.title }}</p>
    <div class="alert alert-info">{{ result.notice }}</div>
    <div style="white-space: pre-wrap;">{{ result.content }}</div>
</div>
{% endblock %}

```

