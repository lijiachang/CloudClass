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
