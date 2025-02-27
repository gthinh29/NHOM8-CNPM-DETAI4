# Generated by Django 4.2.19 on 2025-02-20 18:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_order_counter'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customuser',
            options={'permissions': [('can_manage_counters', 'Can manage store counters'), ('can_view_reports', 'Can view financial reports'), ('can_manage_inventory', 'Can manage product inventory')], 'verbose_name': 'User', 'verbose_name_plural': 'Users'},
        ),
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('canceled', 'Canceled'), ('refunded', 'Refunded')], default='pending', max_length=50),
        ),
        migrations.CreateModel(
            name='StoreCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=100)),
                ('assigned_employee', models.ForeignKey(blank=True, limit_choices_to={'role': 'sales_staff'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_counter', to=settings.AUTH_USER_MODEL)),
                ('manager', models.ForeignKey(limit_choices_to={'role': 'store_manager'}, on_delete=django.db.models.deletion.CASCADE, related_name='managed_counters', to=settings.AUTH_USER_MODEL)),
                ('products', models.ManyToManyField(blank=True, related_name='counters', to='store.product')),
            ],
        ),
        migrations.AlterField(
            model_name='order',
            name='counter',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='store.storecounter'),
        ),
        migrations.DeleteModel(
            name='Counter',
        ),
    ]
