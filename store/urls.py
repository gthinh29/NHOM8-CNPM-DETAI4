from django.urls import path
from .views import (
    dashboard, manage_counters, sales, inventory, orders, customers, 
    reports, settings, profile, register, user_login,
    user_logout, cart, product_detail, add_to_cart,
    checkout, order_history, manage_users, counter_list,
    counter_detail, counter_create, counter_update,
    counter_delete, order_detail,manage_counters
)

urlpatterns = [
    # Core URLs
    path('', dashboard, name='dashboard'),
    path('sales/', sales, name='sales'),
    path('inventory/', inventory, name='inventory'),
    path('orders/', orders, name='orders'),
    path('customers/', customers, name='customers'),
    path('reports/', reports, name='reports'),
    path('settings/', settings, name='settings'),
    path('profile/', profile, name='profile'),
    
    # Auth URLs
    path('register/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    
    # Cart & Orders
    path('cart/', cart, name='cart'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('add_to_cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('checkout/', checkout, name='checkout'),
    path('order_history/', order_history, name='order_history'),
    
    # Management URLs
    path('manage_users/', manage_users, name='manage_users'),
    
    # Counter Management
    path('manage-counters/', manage_counters, name='manage_counters'),
    path('counters/', counter_list, name='counter_list'),
    path('counters/<int:counter_id>/', counter_detail, name='counter_detail'),
    path('counters/new/', counter_create, name='counter_create'),
    path('counters/<int:counter_id>/edit/', counter_update, name='counter_update'),
    path('counters/<int:counter_id>/delete/', counter_delete, name='counter_delete'),
    
    # Order Details
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
]