from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy, path, include
from . import views

app_name = "store"

urlpatterns = [
    # Core URLs
    path("", views.dashboard, name="dashboard"),
    path("inventory/", views.InventoryView.as_view(), name="inventory"),
    
    # Authentication
    path("auth/", include([
        path("register/", views.register, name="register"),
        path("login/", views.user_login, name="login"),
        path("logout/", views.user_logout, name="logout"),
        path("password_change/", auth_views.PasswordChangeView.as_view(
            template_name='store/auth/password_change.html',
            success_url=reverse_lazy('store:change_password_done')
        ), name='password_change'),
        path("password_change/done/", auth_views.PasswordChangeDoneView.as_view(
            template_name='store/auth/password_change_done.html'
        ), name='password_change_done'),
    ])),
    
    # User Management
    path("users/", include([
        path("profile/", views.profile, name="profile"),
        path("delete-account/", views.delete_account, name="delete-account"),
        path("manage/", views.UserManagementView.as_view(), name="user-management"),
    ])),
    
    # Product Management
     path("products/", include([
        path("", views.ProductListView.as_view(), name="product_list"),
        path("add/", views.ProductCreateView.as_view(), name="add_product.html"),
        path("<slug:slug>/", include([
            path("", views.ProductDetailView.as_view(), name="product-detail"),
            path("edit/", views.ProductUpdateView.as_view(), name="product-update"),
            path("delete/", views.ProductDeleteView.as_view(), name="product-delete"),
        ])),
        path("detail/<int:pk>/", views.ProductDetailByPkView.as_view(), name="product-detail-pk"),
    ])),
    
    # Main Order Management (For Admin/Manager)
    path("main-orders/", include([
        path("", views.OrderListView.as_view(), name="main-order-list"),
        path("history/", views.order_history, name="main-order-history"),
        path("<int:pk>/", include([
            path("", views.OrderDetailView.as_view(), name="main-order-detail"),
            path("edit/", views.edit_order, name="main-order-edit"),
            path("invoice/", views.export_invoice, name="main-order-invoice"),
        ])),
    ])),
    
    # Counter Management
    path("counters/", include([
        path("", views.CounterListView.as_view(), name="counter-list"),
        path("new/", views.CounterCreateView.as_view(), name="counter-create"),
        path("manage/", views.manage_counters, name="manage-counters"),
        path("<int:pk>/", include([
            path("", views.CounterDetailView.as_view(), name="counter-detail"),
            path("edit/", views.CounterUpdateView.as_view(), name="counter-update"),
            path("delete/", views.CounterDeleteView.as_view(), name="counter-delete"),
            path("orders/new/", views.CounterCreateView.as_view(), name="counter-order-create"),
        ])),
    ])),
    
    # Sales Interface
    path("sales/", include([
        path("dashboard/", views.SalesDashboard.as_view(), name="sales-dashboard"),
        path('counter/', views.SalesCounterView.as_view(), name='sales_counter'),
        path('counter/create/', views.CounterCreateView.as_view(), name='counter_create'),
        path('orders/create/', views.SalesOrderCreateView.as_view(), name='sales_order_create'),
        path('orders/<int:pk>/payment/', views.process_payment, name='sales_order_payment'),
        path('orders/<int:pk>/', views.SalesOrderDetailView.as_view(), name='sales_order_detail'),
        path('sales/products/', views.sales_products, name='sales_products'),
        path('sales/customers/', views.SalesCustomerListView.as_view(), name='sales-customer-list'),
        path('sales/customers/create/', views.SalesCustomerCreateView.as_view(), name='sales-customer-create'),
        # Sales Orders
        path("orders/", include([
            path("", views.SalesOrderListView.as_view(), name="sales-order-list"),
            path("create/", views.SalesOrderCreateView.as_view(), name="sales-order-create"),
            path("checkout/", views.checkout, name="sales-checkout"),
            path("<int:pk>/", include([
                path("", views.SalesOrderDetailView.as_view(), name="sales-order-detail"),
                path("edit/", views.SalesOrderUpdateView.as_view(), name="sales-order-edit"),
                path("invoice-pdf/", views.SalesInvoicePDFView.as_view(), name="sales-order-invoice-pdf"),
            ])),
        ])),
        
        # Sales Catalog
        path("catalog/", include([
            path("products/", views.SalesProductListView.as_view(), name="sales-product-list"),
            path("customers/", views.SalesCustomerListView.as_view(), name="sales-customer-list"),
        ])),
    ])),
    
    # Customer Management
    path("clients/", include([
        path("", views.Customer, name="client-list"),
        path("<slug:username>/", views.CustomerDetailView.as_view(), name="customer-detail"),
    ])),
    
    # System Settings
    path("system/", include([
        path("settings/", views.SystemSettingsView.as_view(), name="system-settings"),
        path("reports/", include([
            path("sales/", views.SalesReportView.as_view(), name="sales-report"),
            path("revenue/", views.RevenueReportView.as_view(), name="revenue-report"),
        ])),
    ])),
    
    # Cart System
    path("cart/", include([
        path("", views.cart, name="cart"),
        path("add/<int:product_id>/", views.add_to_cart, name="add-to-cart"),
        path("update/<int:product_id>/", views.update_cart_item, name="update-cart"),
        path("remove/<int:product_id>/", views.remove_from_cart, name="remove-from-cart"),
    ])),
]

path("counters/", include([
    path("", views.CounterListView.as_view(), name="counter-list"),
    path("new/", views.CounterCreateView.as_view(), name="counter-create"),
    path("manage/", views.manage_counters, name="manage-counters"),
    path("<int:pk>/", include([
        path("", views.CounterDetailView.as_view(), name="counter-detail"),
        path("edit/", views.CounterUpdateView.as_view(), name="counter-update"),
        path("delete/", views.CounterDeleteView.as_view(), name="counter-delete"),
        path("orders/new/", views.CounterCreateView.as_view(), name="counter-order-create"),
    ])),
])),

# Product Management
path("products/", include([
    path("", views.ProductListView.as_view(), name="product_list"),
    path("add/", views.ProductCreateView.as_view(), name="add_product"),
    path("<slug:slug>/", include([
        path("", views.ProductDetailView.as_view(), name="product-detail"),
        path("edit/", views.ProductUpdateView.as_view(), name="product-update"),
        path("delete/", views.ProductDeleteView.as_view(), name="product-delete"),
    ])),
    path("detail/<int:pk>/", views.ProductDetailByPkView.as_view(), name="product-detail-pk"),
])),
