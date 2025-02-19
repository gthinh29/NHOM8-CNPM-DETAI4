from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import CustomUser, Role

@receiver(pre_save, sender=CustomUser)
def store_old_role(sender, instance, **kwargs):
    """
    Nếu user đã tồn tại, lưu lại role cũ vào thuộc tính tạm _old_role của instance.
    """
    if instance.pk:
        try:
            old_instance = CustomUser.objects.get(pk=instance.pk)
            instance._old_role = old_instance.role
        except CustomUser.DoesNotExist:
            instance._old_role = None
    else:
        instance._old_role = None

@receiver(post_save, sender=CustomUser)
def assign_user_group(sender, instance, created, **kwargs):
    """
    Nếu người dùng mới được tạo (created=True) hoặc nếu role thay đổi, 
    tự động gán người dùng vào nhóm tương ứng.
    """
    # Xác định nhóm dựa trên role của người dùng
    role_to_group = {
        Role.ADMIN: "Admin",
        Role.ACCOUNTANT: "Accountant",
        Role.STORE_MANAGER: "Store Manager",
        Role.SALES_STAFF: "Sales Staff",
    }
    desired_group_name = role_to_group.get(instance.role)

    # Xác định xem role có thay đổi hay không (nếu không phải user mới)
    role_changed = not created and (instance._old_role != instance.role)

    if created or role_changed:
        if desired_group_name:
            # Lấy hoặc tạo nhóm tương ứng
            group, _ = Group.objects.get_or_create(name=desired_group_name)
            # Danh sách tất cả các nhóm role để xoá nếu có thay đổi
            all_role_groups = list(role_to_group.values())
            # Loại bỏ tất cả các nhóm có liên quan đến role mà user đang có
            instance.groups.remove(*instance.groups.filter(name__in=all_role_groups))
            # Gán user vào nhóm tương ứng với role mới
            instance.groups.add(group)
