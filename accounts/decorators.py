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
