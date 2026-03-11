from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if self.allowed_roles and request.user.role not in self.allowed_roles and not request.user.is_superuser:
            raise PermissionDenied("你没有权限访问该页面。")
        return super().dispatch(request, *args, **kwargs)
