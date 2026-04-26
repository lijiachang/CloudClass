# 登录注册模块代码

包含自定义用户模型、登录/注册表单、视图、路由和页面模板。

## accounts/models.py

```python
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    class Roles(models.TextChoices):
        STUDENT = "student", "学生"
        TEACHER = "teacher", "教师"
        ADMIN = "admin", "管理员"

    role = models.CharField("角色", max_length=20, choices=Roles.choices, default=Roles.STUDENT)
    full_name = models.CharField("姓名", max_length=100)
    school_id = models.CharField("学号/工号", max_length=32, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    avatar = models.ImageField("头像", upload_to="avatars/", blank=True, null=True)
    bio = models.TextField("个人简介", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return f"{self.full_name or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.username
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Roles.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Roles.TEACHER

    @property
    def is_platform_admin(self):
        return self.role == self.Roles.ADMIN or self.is_superuser

    def get_dashboard_url(self):
        if self.is_platform_admin:
            return reverse("core:admin_dashboard")
        if self.is_teacher:
            return reverse("core:teacher_dashboard")
        return reverse("core:student_dashboard")

```

## accounts/forms.py

```python
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="用户名")
    password = forms.CharField(label="密码", widget=forms.PasswordInput)


class StudentRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "full_name", "school_id", "phone")
        labels = {
            "username": "用户名",
            "full_name": "姓名",
            "school_id": "学号",
            "phone": "手机号",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Roles.STUDENT
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "phone", "bio", "avatar")
        labels = {
            "full_name": "姓名",
            "phone": "手机号",
            "bio": "个人简介",
            "avatar": "头像",
        }

```

## accounts/views.py

```python
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import LoginForm, ProfileForm, StudentRegisterForm
from .mixins import RoleRequiredMixin
from .models import User


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm

    def get_success_url(self):
        return self.request.user.get_dashboard_url()


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("core:home")


def register(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    form = StudentRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "注册成功，欢迎使用网络教学平台。")
        return redirect(user.get_dashboard_url())
    return render(request, "accounts/register.html", {"form": form})


class ProfileUpdateView(RoleRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:profile")
    extra_context = {"title": "个人信息维护"}

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "个人信息已更新。")
        return super().form_valid(form)

```

## accounts/urls.py

```python
from django.urls import path

from .views import ProfileUpdateView, UserLoginView, UserLogoutView, register

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
]

```

## accounts/decorators.py

```python
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import User


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.user.role not in roles and not request.user.is_superuser:
                raise PermissionDenied("你没有权限访问该页面。")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


student_required = role_required(User.Roles.STUDENT)
teacher_required = role_required(User.Roles.TEACHER)
admin_required = role_required(User.Roles.ADMIN)

```

## templates/accounts/login.html

```html
{% extends "base.html" %}
{% block title %}登录{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-5">
        <div class="card border-0 shadow-sm">
            <div class="card-body p-4">
                <h2 class="h4 mb-4">登录系统</h2>
                <form method="post">
                    {% csrf_token %}
                    {{ form.as_p }}
                    <button class="btn btn-primary w-100" type="submit">登录</button>
                </form>
                <p class="mt-3 mb-0 text-muted small">没有账号？<a href="{% url 'accounts:register' %}">学生注册</a></p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

```

## templates/accounts/register.html

```html
{% extends "base.html" %}
{% block title %}学生注册{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-6">
        <div class="card border-0 shadow-sm">
            <div class="card-body p-4">
                <h2 class="h4 mb-4">学生注册</h2>
                <form method="post">
                    {% csrf_token %}
                    {{ form.as_p }}
                    <button class="btn btn-primary" type="submit">注册并登录</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

```

## templates/accounts/profile_form.html

```html
{% extends "common/form.html" %}
{% block title %}个人信息维护{% endblock %}

```

