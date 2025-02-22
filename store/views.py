import logging
from datetime import timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Q, Sum
from django.forms import formset_factory
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .forms import (CounterForm, CustomUserChangeForm, CustomUserCreationForm,
                    OrderForm, OrderItemForm, ProductForm, SystemSettingForm)
from .mixins import (AccountantRequiredMixin, AdminRequiredMixin,
                     ManagerRequiredMixin, SalesStaffRequiredMixin)
from .models import (CustomUser, Debts, Order, OrderItem, Product, Role,
                     StoreCounter, SystemSetting)
from .services import CartService, OrderService

logger = logging.getLogger(__name__)

# Authentication Views
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Đăng ký thành công!")
            logger.info(f"New user registered: {user.username}")
            return redirect('store:dashboard')
        return render(request, 'store/auth/register.html', {'form': form})
    return render(request, 'store/auth/register.html', {'form': CustomUserCreationForm()})

def user_login(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            messages.success(request, f"Chào mừng {user.username}!")
            logger.info(f"User logged in: {user.username}")
            return redirect('store:dashboard')
        messages.error(request, "Thông tin đăng nhập không chính xác")
    return render(request, 'store/auth/login.html')

@login_required
def user_logout(request):
    logger.info(f"User logged out: {request.user.username}")
    logout(request)
    messages.success(request, "Đã đăng xuất thành công")
    return redirect('store:login')

# Core Views
@login_required
def dashboard(request):
    system_setting = SystemSetting.objects.first()    
    context = {
        'total_sales': Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        'orders_count': Order.objects.count(),
        'products_count': Product.objects.count(),
        'counters_count': StoreCounter.objects.count(),
        'total_debt': Debts.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'store_name': system_setting.store_name if system_setting else "Hệ thống",
    }
    return render(request, 'store/dashboard.html', context)

# Product Management
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'store/products/product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    ordering = ['-id']

class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'store/products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/products/add_product.html'
    success_url = reverse_lazy('store:product_list')

    def form_valid(self, form):
        product = form.save(commit=False)
        product.slug = product.name.replace(' ', '-').lower()
        product.save()
        messages.success(self.request, "Thêm sản phẩm thành công")
        logger.info(f"Product added by {self.request.user.username}")
        return super().form_valid(form)

class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/products/update_product.html'
    success_url = reverse_lazy('store:product_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def form_valid(self, form):
        product = form.save(commit=False)
        product.slug = product.name.replace(' ', '-').lower()
        product.save()
        messages.success(self.request, "Cập nhật sản phẩm thành công")
        logger.info(f"Product {self.object.id} updated by {self.request.user.username}")
        return super().form_valid(form)

class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'store/products/product_confirm_delete.html'
    success_url = reverse_lazy('store:product_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Xóa sản phẩm thành công")
        logger.info(f"Product {self.get_object().id} deleted by {request.user.username}")
        return super().delete(request, *args, **kwargs)

# Order Management
class OrderListView(LoginRequiredMixin, ListView):
    template_name = 'store/orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.role in [Role.STORE_MANAGER, Role.ACCOUNTANT]:
            return Order.objects.all()
        return Order.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sales'] = self.get_queryset().aggregate(total=Sum('total_amount'))['total'] or 0
        return context

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.prefetch_related('order_items__product')

    def dispatch(self, request, *args, **kwargs):
        order = self.get_object()
        if not (request.user.role in [Role.ADMIN, Role.ACCOUNTANT, Role.STORE_MANAGER] or order.created_by == request.user):
            raise PermissionDenied("Bạn không có quyền xem đơn hàng này")
        return super().dispatch(request, *args, **kwargs)

@login_required
@transaction.atomic
def checkout(request):
    try:
        order = OrderService.create_order_from_cart(request.user, request.session.get('cart', {}))
        request.session['cart'] = {}
        return render(request, 'store/orders/order_confirmation.html', {'order': order})
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}", exc_info=True)
        messages.error(request, f"Lỗi thanh toán: {str(e)}")
        return redirect('store:cart')

@login_required
def order_history(request):
    orders = Order.objects.filter(created_by=request.user).order_by('-date')
    return render(request, 'store/orders/order_history.html', {'orders': orders})

@login_required
@transaction.atomic
def create_order(request, counter_id):
    counter = get_object_or_404(StoreCounter, id=counter_id)
    if not (request.user.role == Role.STORE_MANAGER or counter.assigned_employee == request.user):
        raise PermissionDenied("Không có quyền tạo đơn hàng cho quầy này")

    OrderItemFormSet = formset_factory(OrderItemForm, extra=1)
    
    if request.method == 'POST':
        order_form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST, prefix="orderitem")
        
        if order_form.is_valid() and formset.is_valid():
            total = 0
            order = order_form.save(commit=False)
            order.created_by = request.user
            order.counter = counter
            order.save()

            for form in formset:
                if form.cleaned_data:
                    product = form.cleaned_data['product']
                    quantity = form.cleaned_data['quantity']
                    if product.update_stock(-quantity):
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity
                        )
                        total += product.price * quantity
            order.total_amount = total
            order.save()
            return redirect('store:main-order-detail', pk=order.pk)
    
    return render(request, 'store/orders/order_create.html', {
        'order_form': OrderForm(),
        'formset': OrderItemFormSet(prefix="orderitem"),
        'counter': counter
    })

@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not (request.user.role in [Role.ADMIN, Role.STORE_MANAGER] or order.created_by == request.user):
        raise PermissionDenied("Không có quyền chỉnh sửa đơn hàng này")

    if request.method == 'POST':
        for item in order.order_items.all():
            new_quantity = int(request.POST.get(f'quantity_{item.id}', item.quantity))
            if new_quantity != item.quantity:
                item.product.stock += item.quantity
                item.product.stock -= new_quantity
                item.product.save()
                item.quantity = new_quantity
                item.save()
        order.total_amount = sum(item.product.price * item.quantity for item in order.order_items.all())
        order.save()
        return redirect('store:main-order-detail', pk=order.id)
    
    return render(request, 'store/orders/edit_order.html', {'order': order})

# Cart Management
@login_required
def cart(request):
    return render(request, 'store/cart/cart.html', CartService.get_cart_context(request.session))

@login_required
def add_to_cart(request, product_id):
    try:
        CartService.add_item(request.session, product_id)
        messages.success(request, "Đã thêm vào giỏ hàng")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('store:cart')

@login_required
def update_cart_item(request, product_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        try:
            CartService.update_item(request.session, product_id, quantity)
            messages.success(request, "Cập nhật giỏ hàng thành công")
        except Exception as e:
            messages.error(request, str(e))
    return redirect('store:cart')

@login_required
def remove_from_cart(request, product_id):
    try:
        CartService.remove_item(request.session, product_id)
        messages.success(request, "Đã xóa sản phẩm khỏi giỏ hàng")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('store:cart')

# Counter Management
class CounterListView(LoginRequiredMixin, ListView):
    model = StoreCounter
    template_name = 'store/counters/counter_list.html'
    context_object_name = 'counters'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.role == Role.SALES_STAFF:
            return StoreCounter.objects.filter(assigned_employee=self.request.user)
        return StoreCounter.objects.all()

class CounterDetailView(LoginRequiredMixin, DetailView):
    model = StoreCounter
    template_name = 'store/counters/counter_detail.html'
    context_object_name = 'counter'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == Role.SALES_STAFF and self.get_object().assigned_employee != request.user:
            raise PermissionDenied("Bạn không có quyền truy cập quầy này")
        return super().dispatch(request, *args, **kwargs)

class CounterCreateView(ManagerRequiredMixin, CreateView):
    model = StoreCounter
    form_class = CounterForm
    template_name = 'store/counters/counter_create.html'
    success_url = reverse_lazy('store:counter-list')

    def form_valid(self, form):
        form.instance.manager = self.request.user
        messages.success(self.request, "Tạo quầy hàng thành công")
        logger.info(f"Counter created by {self.request.user.username}")
        return super().form_valid(form)

class CounterUpdateView(ManagerRequiredMixin, UpdateView):
    model = StoreCounter
    form_class = CounterForm
    template_name = 'store/counters/counter_update.html'
    success_url = reverse_lazy('store:counter-list')

    def form_valid(self, form):
        messages.success(self.request, "Cập nhật quầy hàng thành công")
        logger.info(f"Counter {self.object.id} updated by {self.request.user.username}")
        return super().form_valid(form)

class CounterDeleteView(ManagerRequiredMixin, DeleteView):
    model = StoreCounter
    template_name = 'store/counters/counter_confirm_delete.html'
    success_url = reverse_lazy('store:counter-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Xóa quầy hàng thành công")
        logger.info(f"Counter {self.get_object().id} deleted by {request.user.username}")
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(lambda u: u.role == Role.STORE_MANAGER)
def manage_counters(request):
    counters = StoreCounter.objects.all()
    return render(request, 'store/counters/manage_counters.html', {'counters': counters})

# Reports & Settings
class SalesReportView(AccountantRequiredMixin, TemplateView):
    template_name = 'store/reports/sales.html'

    def get_context_data(self, **kwargs):
        today = timezone.now().date()
        return {
            'today_sales': self._get_daily_sales(today),
            'weekly_sales': self._get_weekly_sales(today),
            'chart_labels': [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)],
            'chart_data': [self._get_daily_sales(today - timedelta(days=i)) for i in range(6, -1, -1)]
        }

    def _get_daily_sales(self, date):
        return Order.objects.filter(date=date).aggregate(total=Sum('total_amount'))['total'] or 0

    def _get_weekly_sales(self, date):
        return Order.objects.filter(date__gte=date - timedelta(days=7)).aggregate(total=Sum('total_amount'))['total'] or 0

class SystemSettingsView(AdminRequiredMixin, UpdateView):
    model = SystemSetting
    form_class = SystemSettingForm
    template_name = 'store/settings/settings.html'
    success_url = reverse_lazy('store:system-settings')

    def get_object(self):
        return SystemSetting.objects.first()

    def form_valid(self, form):
        messages.success(self.request, "Cập nhật cài đặt thành công")
        logger.info(f"System settings updated by {self.request.user.username}")
        return super().form_valid(form)

# Additional Features
@login_required
def export_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"HÓA ĐƠN #{order.id:06d}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Khách hàng: {order.created_by.get_full_name()}")
    p.drawString(100, 700, f"Ngày: {order.date.strftime('%d/%m/%Y %H:%M')}")
    
    y = 650
    p.line(100, y+10, 500, y+10)
    p.drawString(100, y, "Sản phẩm")
    p.drawString(300, y, "Số lượng")
    p.drawString(400, y, "Đơn giá")
    p.drawString(500, y, "Thành tiền")
    
    for item in order.order_items.all():
        y -= 20
        p.drawString(100, y, item.product.name)
        p.drawString(300, y, str(item.quantity))
        p.drawString(400, y, f"{item.product.price:,.0f} VNĐ")
        p.drawString(500, y, f"{item.product.price * item.quantity:,.0f} VNĐ")
    
    y -= 40
    p.line(100, y+30, 500, y+30)
    p.drawString(400, y, "TỔNG CỘNG:")
    p.drawString(500, y, f"{order.total_amount:,.0f} VNĐ")
    
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"invoice_{order.id}.pdf")

class UserManagementView(AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'store/users/manage_users.html'
    context_object_name = 'users'
    paginate_by = 20

class InventoryView(LoginRequiredMixin, ListView):
    template_name = 'store/inventory/inventory.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        return Product.objects.annotate(total_value=F('price') * F('stock')).order_by('-stock')

@login_required
def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật thông tin thành công")
            return redirect('store:profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'store/users/profile.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        if user.check_password(request.POST.get('password')):
            user.delete()
            logout(request)
            messages.success(request, "Tài khoản của bạn đã được xóa vĩnh viễn")
            return redirect('store:login')
        messages.error(request, "Mật khẩu không chính xác")
    return HttpResponseForbidden("Phương thức không được hỗ trợ")

class SalesDashboard(LoginRequiredMixin, TemplateView):
    template_name = 'store/sales/counter_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'pending_orders': Order.objects.filter(
                counter=self.request.user.assigned_counter,
                status='pending'
            ).count(),
            'today_sales': Order.objects.today_sales(
                counter=self.request.user.assigned_counter
            )
        })
        return context
    
from django.views.generic import ListView
from .models import Customer  # Đảm bảo đã import model Customer

class SalesCustomerListView(LoginRequiredMixin, ListView):
    template_name = 'store/sales/customer_list.html'
    context_object_name = 'customers'
    
    def get_queryset(self):
        # Lấy danh sách khách hàng liên quan đến quầy của nhân viên
        return Customer.objects.filter(
            user__assigned_counter=self.request.user.assigned_counter
        )
class SalesProductListView(LoginRequiredMixin, ListView):
    template_name = 'store/sales/product_list.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        """Lấy danh sách sản phẩm cho quầy của nhân viên"""
        return Product.objects.filter(
            counters=self.request.user.assigned_counter
        ).order_by('-stock')
from django.views.generic import ListView
from .models import Order

class SalesOrderListView(LoginRequiredMixin, ListView):
    template_name = 'store/sales/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        """Lấy danh sách đơn hàng cho nhân viên bán hàng"""
        return Order.objects.filter(
            created_by=self.request.user
        ).select_related('counter').prefetch_related('order_items__product')
    
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .models import Order
from .forms import OrderForm

class SalesOrderCreateView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'store/sales/order_create.html'
    success_url = reverse_lazy('store:sales-main-order-list')

    def form_valid(self, form):
        """Tự động gán người tạo đơn hàng"""
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
class SalesOrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/sales/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        """Chỉ cho phép xem đơn hàng của chính nhân viên"""
        return Order.objects.filter(created_by=self.request.user)

class SalesOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = 'store/sales/order_edit.html'
    success_url = reverse_lazy('store:sales-main-order-list')

    def get_queryset(self):
        return Order.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Cập nhật đơn hàng thành công")
        return super().form_valid(form)

class SalesInvoicePDFView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/sales/invoice_pdf.html'  # Có thể xóa nếu không dùng template HTML

    def get(self, request, *args, **kwargs):
        return self.generate_pdf_invoice()

    def generate_pdf_invoice(self):
        """Tạo hóa đơn PDF với ReportLab"""
        order = self.get_object()
        buffer = BytesIO()
        
        # Tạo canvas PDF
        p = canvas.Canvas(buffer, pagesize=letter)
        self._draw_header(p, order)
        self._draw_customer_info(p, order)
        self._draw_items_table(p, order)
        self._draw_footer(p, order)
        
        p.save()
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"invoice_{order.id}.pdf",
            content_type='application/pdf'
        )

    def _draw_header(self, p, order):
        """Vẽ phần header hóa đơn"""
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, f"HÓA ĐƠN #{order.id:06d}")
        p.setFont("Helvetica", 10)
        p.drawString(100, 730, f"Ngày xuất: {timezone.now().strftime('%d/%m/%Y %H:%M')}")

    def _draw_customer_info(self, p, order):
        """Vẽ thông tin khách hàng"""
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, 700, "Thông tin khách hàng:")
        p.setFont("Helvetica", 10)
        p.drawString(100, 680, f"Tên: {order.customer_name}")
        p.drawString(100, 660, f"Điện thoại: {order.customer_phone}")
        p.drawString(100, 640, f"Địa chỉ: {order.customer_address}")

    def _draw_items_table(self, p, order):
        """Vẽ bảng sản phẩm"""
        y = 600
        # Header bảng
        p.setFont("Helvetica-Bold", 10)
        p.drawString(100, y, "STT")
        p.drawString(150, y, "Sản phẩm")
        p.drawString(300, y, "Đơn giá")
        p.drawString(400, y, "Số lượng")
        p.drawString(500, y, "Thành tiền")
        p.line(100, y-10, 550, y-10)

        # Dữ liệu sản phẩm
        p.setFont("Helvetica", 10)
        for idx, item in enumerate(order.order_items.all(), start=1):
            y -= 20
            p.drawString(100, y, str(idx))
            p.drawString(150, y, item.product.name)
            p.drawString(300, y, f"{item.product.price:,.0f} VNĐ")
            p.drawString(400, y, str(item.quantity))
            p.drawString(500, y, f"{item.total_price():,.0f} VNĐ")

    def _draw_footer(self, p, order):
        """Vẽ phần chân trang"""
        y = 200
        p.setFont("Helvetica-Bold", 12)
        p.drawString(400, y, "TỔNG CỘNG:")
        p.drawString(500, y, f"{order.total_amount:,.0f} VNĐ")
        p.line(400, y-10, 550, y-10)

        # Thông tin cửa hàng
        p.setFont("Helvetica", 8)
        p.drawString(100, 50, "Cảm ơn quý khách đã mua hàng!")
        p.drawString(100, 40, "Hẹn gặp lại quý khách trong các dịch vụ tiếp theo")

    def dispatch(self, request, *args, **kwargs):
        """Kiểm tra quyền truy cập"""
        order = self.get_object()
        if not (request.user == order.created_by or request.user.is_staff):
            raise PermissionDenied("Bạn không có quyền xem hóa đơn này")
        return super().dispatch(request, *args, **kwargs)
# views.py (phần bổ sung)

from django.views.generic import TemplateView

class RevenueReportView(AccountantRequiredMixin, TemplateView):
    template_name = 'store/reports/revenue_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        revenue = Order.objects.filter(date__gte=last_7_days).aggregate(total=Sum('total_amount'))['total'] or 0
        context.update({
            'revenue_last_7_days': revenue,
            'today': today,
        })
        return context
    
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from .models import CustomUser, Role

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'store/customers/customer_detail.html'
    context_object_name = 'customer'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        # Chỉ cho phép truy cập các tài khoản có role là CUSTOMER
        return CustomUser.objects.filter(role=Role.CUSTOMER)
    
class ProductDetailByPkView(DetailView):
    model = Product
    template_name = 'store/products/product_detail.html'
    context_object_name = 'product'

