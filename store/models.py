from django.contrib.auth.models import AbstractUser 
from django.db import models
from django.utils import timezone

# Định nghĩa Role cho người dùng
class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    ACCOUNTANT = 'accountant', 'Accountant'
    STORE_MANAGER = 'store_manager', 'Store Manager'
    SALES_STAFF = 'sales_staff', 'Sales Staff'

# Custom:User  Một bảng duy nhất cho tất cả người dùng, phân biệt qua trường role
class CustomUser (AbstractUser ):
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SALES_STAFF,
        help_text="Chọn vai trò của người dùng"
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = [
            ("can_manage_counters", "Can manage store counters"),
            ("can_view_reports", "Can view financial reports"),
            ("can_manage_inventory", "Can manage product inventory"),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_full_info(self) -> str:
        """Lấy thông tin đầy đủ của người dùng."""
        return f"Username: {self.username}, Email: {self.email}, Phone: {self.phone}, Role: {self.get_role_display()}"

    def change_password(self, new_password: str):
        """Thay đổi mật khẩu cho người dùng."""
        self.set_password(new_password)
        self.save()


# Product: Sản phẩm
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField(default=0.0)
    stock = models.PositiveIntegerField(default=0)
    orders = models.ManyToManyField(
        'Order',  # <-- Thêm dấu nháy đơn
        through='OrderItem',
        blank=True,
        related_name='products_orders'
    )

    def update_stock(self, quantity: int) -> bool:
        """Cập nhật tồn kho, đảm bảo không bị âm."""
        if quantity < 0 and self.stock < abs(quantity):
            return False
        self.stock += quantity
        self.save()
        return True

    def set_price(self, new_price: float):
        """Cập nhật giá sản phẩm."""
        self.price = new_price
        self.save()

    def apply_discount(self, discount_percentage: float):
        """Giảm giá sản phẩm theo phần trăm."""
        if 0 <= discount_percentage <= 100:
            discount_amount = self.price * (discount_percentage / 100)
            self.price -= discount_amount
            self.save()

    def is_available(self) -> bool:
        """Kiểm tra sản phẩm còn hàng hay không."""
        return self.stock > 0

    def is_low_stock(self, threshold: int = 5) -> bool:
        """Kiểm tra xem sản phẩm có tồn kho thấp hay không."""
        return self.stock < threshold

    def get_details(self) -> str:
        """Lấy thông tin chi tiết về sản phẩm."""
        return f"Product: {self.name}, Price: ${self.price:.2f}, Stock: {self.stock}"

    def __str__(self):
        return self.name

# Quản lý quầy hàng
class StoreCounter(models.Model):
    location = models.CharField(max_length=100)
    manager = models.ForeignKey(
        CustomUser ,
        on_delete=models.CASCADE,
        limit_choices_to={'role': Role.STORE_MANAGER},
        related_name='managed_counters',
        editable=False
    )
    
    assigned_employee = models.ForeignKey(
        CustomUser ,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': Role.SALES_STAFF},
        related_name='assigned_counter'
    )
    products = models.ManyToManyField(Product, blank=True, related_name='counters')

    def assign_employee(self, employee: CustomUser ):
        """Phân công nhân viên bán hàng cho quầy."""
        if employee.role == Role.SALES_STAFF:
            self.assigned_employee = employee
            self.save()

    def get_details(self) -> str:
        return f"Counter at {self.location} managed by {self.manager.username}"

    def is_managed_by(self, user: CustomUser ) -> bool:
        """Kiểm tra xem quầy hàng có được quản lý bởi người dùng không."""
        return self.manager == user

    def __str__(self):
        return f"Counter: {self.location}"

# Order & OrderItem: Đơn hàng và mục đơn hàng
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded')
    ]

    date = models.DateField(default=timezone.now)
    order_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    counter = models.ForeignKey(
        StoreCounter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_products'
    )
    total_amount = models.FloatField(default=0.0)
    created_by = models.ForeignKey(
        CustomUser ,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_products'
    )
    products = models.ManyToManyField(Product, through='OrderItem', blank=True, related_name='order_products')

    def add_item(self, product: Product, quantity: int) -> bool:
        """Thêm sản phẩm vào đơn hàng nếu còn hàng."""
        if product.update_stock(-quantity):
            item, created = OrderItem.objects.get_or_create(order=self, product=product, defaults={'quantity': quantity})
            if not created:
                item.quantity += quantity
                item.save()
            self.calculate_total()
            return True
        return False

    def calculate_total(self) -> float:
        """Tính tổng tiền đơn hàng."""
        total = sum(item.product.price * item.quantity for item in self.order_items.all())
        self.total_amount = total
        self.save()
        return total

    def process_payment(self) -> bool:
        """Xử lý thanh toán đơn hàng."""
        if self.order_status == 'pending':
            self.order_status = 'paid'
            self.save()
            return True
        return False

    def cancel_order(self) -> bool:
        """Hủy đơn hàng nếu nó đang trong trạng thái 'pending'."""
        if self.order_status == 'pending':
            self.order_status = 'canceled'
            for item in self.order_items.all():
                item.product.update_stock(item.quantity)  # Trả lại hàng vào kho
            self.save()
            return True
        return False

    def refund(self) -> bool:
        """Hoàn tiền cho đơn hàng nếu đã thanh toán."""
        if self.order_status == 'paid':
            self.order_status = 'refunded'
            for item in self.order_items.all():
                item.product.update_stock(item.quantity)  # Trả lại hàng vào kho
            self.save()
            return True
        return False

    def generate_invoice(self) -> str:
        """Xuất hóa đơn chi tiết."""
        items = "\n".join([f"{item.product.name} x {item.quantity} - ${item.product.price * item.quantity:.2f}" for item in self.order_items.all()])
        return f"Invoice for Order #{self.pk}:\n{items}\nTotal: ${self.total_amount:.2f}"

    def __str__(self):
        return f"Order #{self.pk} - {self.order_status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)

    def update_quantity(self, new_quantity: int):
        """Cập nhật số lượng của mục đơn hàng."""
        if new_quantity > 0:
            self.quantity = new_quantity
            self.save()

    def delete_item(self):
        """Xóa mục đơn hàng."""
        self.delete()

    def get_item_info(self) -> str:
        """Lấy thông tin chi tiết về mục đơn hàng."""
        return f"Product: {self.product.name}, Quantity: {self.quantity}, Total Price: ${self.product.price * self.quantity:.2f}"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

# Debts: Khoản nợ, liên kết với Accountant
class Debts(models.Model):
    amount = models.FloatField(default=0.0)
    interest = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)
    accountant = models.ForeignKey(
        CustomUser ,
        on_delete=models.CASCADE,
        related_name='debts',
        limit_choices_to={'role': Role.ACCOUNTANT}
    )

    def calculate_debt(self) -> float:
        """Tính tiền lãi dựa trên số dư và lãi suất."""
        return self.amount * (self.interest / 100)

    def is_debt_paid(self) -> bool:
        """Kiểm tra xem khoản nợ đã được thanh toán hay chưa."""
        return self.amount <= 0

    def get_debt_info(self) -> str:
        """Lấy thông tin chi tiết về khoản nợ."""
        return f"Debt Amount: ${self.amount:.2f}, Interest Rate: {self.interest:.2f}%"

    def pay_debt(self, amount: float) -> bool:
        """Thanh toán một phần hoặc toàn bộ khoản nợ."""
        if amount > 0 and amount <= self.amount:
            self.amount -= amount
            self.save()
            return True
        return False

    def __str__(self):
        return f"Debt: ${self.amount:.2f} at {self.interest:.2f}%"

# SystemSetting: Cài đặt hệ thống
class SystemSetting(models.Model):
    store_name = models.CharField(max_length =100, default="Jewelry Sales Manager")
    contact_email = models.EmailField(default="info@example.com")
    tax_rate = models.FloatField(default=5.0, help_text="Tax rate in percentage")
    discount_rate = models.FloatField(default=0.0, help_text="Default discount rate in percentage")

    def apply_tax(self, amount: float) -> float:
        """Tính toán số tiền sau thuế."""
        return amount + (amount * (self.tax_rate / 100))

    def apply_discount(self, amount: float) -> float:
        """Tính toán số tiền sau khi áp dụng giảm giá."""
        return amount - (amount * (self.discount_rate / 100))

    def is_valid_email(self) -> bool:
        """Kiểm tra định dạng email có hợp lệ hay không."""
        return '@' in self.contact_email and '.' in self.contact_email.split('@')[-1]

    def is_tax_rate_valid(self) -> bool:
        """Kiểm tra tỷ lệ thuế có hợp lệ hay không."""
        return 0 <= self.tax_rate <= 100

    def is_discount_rate_valid(self) -> bool:
        """Kiểm tra tỷ lệ giảm giá có hợp lệ hay không."""
        return 0 <= self.discount_rate <= 100

    def is_settings_complete(self) -> bool:
        """Kiểm tra xem tất cả thông tin cài đặt đã được hoàn thành hay chưa."""
        return all([self.store_name, self.contact_email, self.tax_rate is not None, self.discount_rate is not None])

    def get_settings_info(self) -> str:
        """Lấy thông tin cài đặt hệ thống."""
        return f"Store Name: {self.store_name}, Contact Email: {self.contact_email}, Tax Rate: {self.tax_rate:.2f}%, Discount Rate: {self.discount_rate:.2f}%"

    def update_settings(self, store_name: str = None, contact_email: str = None, tax_rate: float = None, discount_rate: float = None):
        """Cập nhật thông tin cài đặt hệ thống."""
        if store_name:
            self.store_name = store_name
        if contact_email:
            self.contact_email = contact_email
        if tax_rate is not None:
            self.tax_rate = tax_rate
        if discount_rate is not None:
            self.discount_rate = discount_rate
        self.save()