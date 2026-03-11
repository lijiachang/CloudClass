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
