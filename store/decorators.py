

from functools import wraps
from django.http import HttpResponseForbidden

def allowed_roles(allowed_roles=[]):
    """
    Decorator kiểm tra nếu người dùng có thuộc tính 'role' và role đó nằm trong danh sách allowed_roles.
    Nếu không, trả về HttpResponseForbidden.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Kiểm tra nếu người dùng đã đăng nhập và có role
            if request.user.is_authenticated and hasattr(request.user, 'role'):
                if request.user.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
            # Nếu không có quyền, trả về Forbidden
            return HttpResponseForbidden("Bạn không có quyền truy cập trang này.")
        return _wrapped_view
    return decorator
