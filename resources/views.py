from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import teacher_required
from courses.models import Course

from .forms import CourseMaterialForm
from .models import CourseMaterial


@teacher_required
def material_create(request):
    form = CourseMaterialForm(request.POST or None, request.FILES or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        material = form.save(commit=False)
        material.uploaded_by = request.user
        material.save()
        messages.success(request, "教学资料已上传。")
        return redirect("courses:detail", pk=material.course.pk)
    return render(request, "common/form.html", {"form": form, "title": "上传教学资料"})


@teacher_required
def material_manage(request, course_id):
    course = get_object_or_404(Course, pk=course_id, teacher=request.user)
    materials = CourseMaterial.objects.filter(course=course)
    return render(request, "resources/material_manage.html", {"course": course, "materials": materials})


def material_detail(request, pk):
    material = get_object_or_404(CourseMaterial.objects.select_related("course", "uploaded_by"), pk=pk)
    return render(request, "resources/material_detail.html", {"material": material})
