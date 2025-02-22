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
    role_to_group = {
        'admin': "Admin",
        'accountant': "Accountant",
        'store_manager': "Store Manager",
        'sales_staff': "Sales Staff",
    }
    desired_group_name = role_to_group.get(instance.role)

    role_changed = not created and (instance._old_role != instance.role)

    if created or role_changed:
        if desired_group_name:
            all_role_groups = list(role_to_group.values())
            instance.groups.remove(*instance.groups.filter(name__in=all_role_groups))
            group, _ = Group.objects.get_or_create(name=desired_group_name)
            instance.groups.add(group)
