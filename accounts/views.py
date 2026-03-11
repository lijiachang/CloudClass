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
