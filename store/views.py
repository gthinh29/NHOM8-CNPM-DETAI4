from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F
from django.db import transaction
from .models import CustomUser, Product, Order, OrderItem, StoreCounter, Debts, SystemSetting, Role
from .forms import (
    CustomUserCreationForm,
    CustomUserChangeForm,
    CounterForm,
    SystemSettingForm,
    ProductForm
)

# 🚀 Dashboard
@login_required
def dashboard(request):
    context = {
        'total_sales': Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        'orders_count': Order.objects.count(),
        'products_count': Product.objects.count(),
        'counters_count': StoreCounter.objects.count(),
    }
    return render(request, 'store/dashboard.html', context)

# 🛒 Orders
@login_required
def orders(request):
    orders_qs = Order.objects.all() if request.user.role in [Role.STORE_MANAGER, Role.ACCOUNTANT] else Order.objects.filter(created_by=request.user)
    context = {
        'orders': orders_qs,
        'total_sales': orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    return render(request, 'store/orders.html', context)

# 🛍️ Cart
@login_required
def cart(request):
    cart_data = request.session.get('cart', {})
    items = []
    total = 0
    for product_id, quantity in cart_data.items():
        product = get_object_or_404(Product, id=product_id)
        subtotal = product.price * quantity
        items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
        total += subtotal
    return render(request, 'store/cart.html', {'items': items, 'total': total})

# ➕ Add to Cart
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_data = request.session.get('cart', {})

    if product.stock > 0:
        cart_data[str(product_id)] = cart_data.get(str(product_id), 0) + 1
        request.session['cart'] = cart_data
        messages.success(request, "Added to cart.")
    else:
        messages.error(request, "Out of stock.")

    return redirect('cart')

# 💳 Checkout
@login_required
@transaction.atomic
def checkout(request):
    cart_data = request.session.get('cart', {})

    if not cart_data:
        messages.warning(request, "Cart is empty.")
        return redirect('dashboard')

    total = 0
    for product_id, quantity in cart_data.items():
        product = get_object_or_404(Product, id=product_id)
        if product.stock < quantity:
            messages.error(request, f"Insufficient stock for {product.name}")
            return redirect('cart')
        total += product.price * quantity

    with transaction.atomic():
        order = Order.objects.create(created_by=request.user, total_amount=total)
        for product_id, quantity in cart_data.items():
            product = get_object_or_404(Product, id=product_id)
            product.stock -= quantity
            product.save()
            OrderItem.objects.create(order=order, product=product, quantity=quantity)

    request.session['cart'] = {}
    messages.success(request, "Order placed successfully.")
    return render(request, 'store/order_confirmation.html', {'order': order})

# 👤 Register
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})

# 🔐 Login
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Welcome {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'store/login.html')

# 🏪 Store Counter Management
@login_required
def manage_counters(request):
    if request.user.role != Role.STORE_MANAGER:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    counters = StoreCounter.objects.filter(manager=request.user)
    return render(request, 'store/counters/manage_counters.html', {'counters': counters})

# 📊 Revenue Reports
@login_required
def revenue_report(request):
    if request.user.role not in [Role.ADMIN, Role.ACCOUNTANT]:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    return render(request, 'store/revenue_report.html', {'total_revenue': total_revenue})

# 📦 Product Management
@login_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'store/products/product_list.html', {'products': products})

@login_required
def add_product(request):
    if request.user.role not in [Role.ADMIN, Role.ACCOUNTANT]:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added.")
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'store/products/add_product.html', {'form': form})

@login_required
def update_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/products/update_product.html', {'form': form, 'product': product})

# ⚙️ Settings
@login_required
def settings(request):
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    setting, created = SystemSetting.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = SystemSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated.")
            return redirect('settings')
    else:
        form = SystemSettingForm(instance=setting)
    return render(request, 'store/settings.html', {'form': form})

@login_required
def counter_list(request):
    counters = StoreCounter.objects.all()
    return render(request, 'store/counters/counter_list.html', {'counters': counters})
@login_required
def counter_detail(request, counter_id):
    counter = get_object_or_404(StoreCounter, id=counter_id)
    return render(request, 'store/counters/counter_detail.html', {'counter': counter})
@login_required
def counter_create(request):
    if request.user.role != Role.STORE_MANAGER:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = CounterForm(request.POST)
        if form.is_valid():
            # Tự động gán manager là người dùng hiện tại
            counter = form.save(commit=False)
            counter.manager = request.user
            counter.save()
            form.save_m2m()  # Lưu many-to-many fields (products)
            
            messages.success(request, "Counter created successfully.")
            return redirect('manage_counters')
    else:
        form = CounterForm()
    
    return render(request, 'store/counters/counter_create.html', {'form': form})
# 🛑 Logout
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

# 📝 Order Detail
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Kiểm tra quyền truy cập
    if request.user.role not in [Role.ADMIN, Role.ACCOUNTANT] and order.created_by != request.user:
        return HttpResponseForbidden("You don't have permission to view this order.")
    
    return render(request, 'store/orders/order_detail.html', {'order': order})

# 🔄 Counter Update
@login_required
def counter_update(request, counter_id):
    if request.user.role != Role.STORE_MANAGER:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    counter = get_object_or_404(StoreCounter, id=counter_id)
    
    if request.method == 'POST':
        form = CounterForm(request.POST, instance=counter)
        if form.is_valid():
            form.save()
            messages.success(request, "Counter updated successfully.")
            return redirect('manage_counters')
    else:
        form = CounterForm(instance=counter)
    
    return render(request, 'store/counters/counter_update.html', {'form': form, 'counter': counter})

# ❌ Counter Delete
@login_required
def counter_delete(request, counter_id):
    if request.user.role != Role.STORE_MANAGER:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    counter = get_object_or_404(StoreCounter, id=counter_id)
    
    if request.method == 'POST':
        counter.delete()
        messages.success(request, "Counter deleted successfully.")
        return redirect('manage_counters')
    
    return render(request, 'store/counters/counter_confirm_delete.html', {'counter': counter})

# 👥 Manage Users
@login_required
def manage_users(request):
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    users = CustomUser.objects.all()
    return render(request, 'store/users/manage_users.html', {'users': users})

# 📈 Sales Dashboard
@login_required
def sales(request):
    # Lấy ngày hiện tại
    today = timezone.now().date()

    # Tính toán doanh thu
    today_sales = Order.objects.filter(date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    weekly_sales = Order.objects.filter(date__gte=today - timedelta(days=7)).aggregate(total=Sum('total_amount'))['total'] or 0
    monthly_sales = Order.objects.filter(date__month=today.month, date__year=today.year).aggregate(total=Sum('total_amount'))['total'] or 0
    yearly_sales = Order.objects.filter(date__year=today.year).aggregate(total=Sum('total_amount'))['total'] or 0

    # Lấy danh sách đơn hàng gần nhất
    recent_orders = Order.objects.order_by('-date')[:10]

    # Dữ liệu biểu đồ (7 ngày gần nhất)
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        chart_labels.append(date.strftime("%a"))  # Tên ngày (Mon, Tue, ...)
        total = Order.objects.filter(date=date).aggregate(total=Sum('total_amount'))['total'] or 0
        chart_data.append(total)

    context = {
        'today_sales': today_sales,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'yearly_sales': yearly_sales,
        'orders': recent_orders,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request, 'store/sales.html', context)

# 📦 Inventory Management
@login_required
def inventory(request):
    products = Product.objects.annotate(
        total_value=F('price') * F('stock')
    )
    return render(request, 'store/inventory/inventory.html', {'products': products})

# 👤 Customer Management
@login_required
def customers(request):
    customers = CustomUser.objects.filter(role=Role.SALES_STAFF)
    return render(request, 'store/customers/customers.html', {'customers': customers})

# 📄 Reports
@login_required
def reports(request):
    if request.user.role not in [Role.ADMIN, Role.ACCOUNTANT]:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    return render(request, 'store/reports/reports.html')

# 👤 User Profile
@login_required
def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'store/profile.html', {'form': form})

# 🛍️ Product Detail
@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/products/product_detail.html', {'product': product})

# 📜 Order History
@login_required
def order_history(request):
    orders = Order.objects.filter(created_by=request.user).order_by('-date')
    return render(request, 'store/orders/order_history.html', {'orders': orders})