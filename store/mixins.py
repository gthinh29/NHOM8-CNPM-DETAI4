# mixins.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect

from store.models import Role

class RoleRequiredMixin(UserPassesTestMixin):
    role = None
    permission_denied_message = "Bạn không có quyền truy cập trang này"
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == self.role
    
    def handle_no_permission(self):
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())
        return super().handle_no_permission()

class AdminRequiredMixin(RoleRequiredMixin):
    role = 'admin'

class ManagerRequiredMixin(RoleRequiredMixin):
    role = 'store_manager'

class AccountantRequiredMixin(RoleRequiredMixin):
    role = 'accountant'

class SalesStaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'sales_staff'
    
    def handle_no_permission(self):
        return redirect('login')

class AdminOrManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role in [Role.ADMIN, Role.STORE_MANAGER]