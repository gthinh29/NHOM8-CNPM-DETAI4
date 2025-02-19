from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Product, Order, OrderItem, Counter, Debts
from .forms import CustomUserCreationForm, CustomUserChangeForm

# Dashboard view: hiển thị số liệu thống kê
@login_required
def dashboard(request):
    total_sales = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    orders_count = Order.objects.count()
    products_count = Product.objects.count()
    context = {
        'total_sales': total_sales,
        'orders_count': orders_count,
        'products_count': products_count,
    }
    return render(request, 'store/dashboard.html', context)

# Placeholder view cho Sales Management
@login_required
def sales(request):
    # Bạn có thể tích hợp logic doanh số bán hàng tại đây
    return render(request, 'store/sales.html')

# Placeholder view cho Inventory Management
@login_required
def inventory(request):
    return render(request, 'store/inventory.html')

# View Orders: hiển thị danh sách đơn hàng
@login_required
def orders(request):
    orders_qs = Order.objects.filter(created_by=request.user).order_by('-date')
    total_sales = orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0
    context = {
        'orders': orders_qs,
        'total_sales': total_sales,
    }
    return render(request, 'store/orders.html', context)

# Placeholder view cho Customers Management
@login_required
def customers(request):
    return render(request, 'store/customers.html')

# Placeholder view cho Reports
@login_required
def reports(request):
    return render(request, 'store/reports.html')

# Placeholder view cho Settings
@login_required
def settings(request):
    return render(request, 'store/settings.html')

# Home view: danh sách sản phẩm (có thể dùng làm trang hiển thị bên ngoài dashboard)
def home(request):
    products = Product.objects.all()
    return render(request, 'store/home.html', {'products': products})

# Chi tiết sản phẩm
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

# View đăng ký
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Đăng ký thành công. Chào mừng bạn!")
            return redirect('dashboard')
        else:
            messages.error(request, "Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin đăng ký.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})

# View đăng nhập
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Chào mừng {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Thông tin đăng nhập không chính xác.")
            return render(request, 'store/login.html')
    return render(request, 'store/login.html')

# View đăng xuất
def user_logout(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect('dashboard')

# View giỏ hàng
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

# View thêm sản phẩm vào giỏ hàng
@login_required
def add_to_cart(request, product_id):
    if request.method != 'POST':
        messages.info(request, "Sản phẩm đã được thêm vào giỏ hàng.")
    cart_data = request.session.get('cart', {})
    cart_data[str(product_id)] = cart_data.get(str(product_id), 0) + 1
    request.session['cart'] = cart_data
    messages.success(request, "Sản phẩm đã được thêm vào giỏ hàng.")
    return redirect('cart')

# View thanh toán (checkout)
@login_required
def checkout(request):
    cart_data = request.session.get('cart', {})
    if not cart_data:
        messages.warning(request, "Giỏ hàng của bạn trống.")
        return redirect('dashboard')
    total = 0
    for product_id, quantity in cart_data.items():
        product = get_object_or_404(Product, id=product_id)
        total += product.price * quantity
    try:
        order = Order.objects.create(created_by=request.user, total_amount=total)
        for product_id, quantity in cart_data.items():
            product = get_object_or_404(Product, id=product_id)
            OrderItem.objects.create(order=order, product=product, quantity=quantity)
        request.session['cart'] = {}
        messages.success(request, "Đơn hàng của bạn đã được đặt thành công.")
    except Exception as e:
        messages.error(request, "Có lỗi xảy ra khi đặt hàng. Vui lòng thử lại sau.")
        return redirect('cart')
    return render(request, 'store/order_confirmation.html', {'order': order})

# View lịch sử đơn hàng
@login_required
def order_history(request):
    orders_qs = Order.objects.filter(created_by=request.user).order_by('-date')
    context = {
        'orders': orders_qs,
    }
    return render(request, 'store/order_history.html', context)

# View hồ sơ cá nhân (profile)
@login_required
def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Thông tin cá nhân đã được cập nhật.")
            return redirect('profile')
        else:
            messages.error(request, "Có lỗi khi cập nhật thông tin. Vui lòng kiểm tra lại.")
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'store/profile.html', {'form': form})

# View quản lý người dùng (cho Admin)
@login_required
def manage_users(request):
    # Chỉ cho phép Admin truy cập
    if request.user.role != 'admin':
        messages.error(request, "Bạn không có quyền truy cập trang này.")
        return redirect('dashboard')
    users = get_user_model().objects.all()
    return render(request, 'store/manage_users.html', {'users': users})
from django.contrib.auth import get_user_model
from .models import SystemSetting
from .forms import SystemSettingForm

@login_required
def settings(request):
    # Chỉ cho phép Admin truy cập trang cài đặt
    if request.user.role != 'admin':
        messages.error(request, "Bạn không có quyền truy cập trang này.")
        return redirect('dashboard')
    
    # Lấy hoặc tạo một instance của SystemSetting (giả sử chỉ có một instance duy nhất)
    setting, created = SystemSetting.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        form = SystemSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "System settings updated successfully.")
            return redirect('settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SystemSettingForm(instance=setting)
    
    return render(request, 'store/settings.html', {'form': form})
