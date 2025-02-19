from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Định nghĩa Role cho người dùng
class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    ACCOUNTANT = 'accountant', 'Accountant'
    STORE_MANAGER = 'store_manager', 'Store Manager'
    SALES_STAFF = 'sales_staff', 'Sales Staff'

# CustomUser: Một bảng duy nhất cho tất cả người dùng, phân biệt qua trường role
class CustomUser(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SALES_STAFF,
        help_text="Chọn vai trò của người dùng"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

# Product: Sản phẩm
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField(default=0.0)
    stock = models.PositiveIntegerField(default=0)

    def update_stock(self, quantity: int):
        self.stock = max(self.stock - quantity, 0)
        self.save()

    def set_price(self, new_price: float):
        self.price = new_price
        self.save()

    def apply_discount(self, discount_percentage: float):
        discount_amount = self.price * (discount_percentage / 100)
        self.price -= discount_amount
        self.save()

    def is_available(self) -> bool:
        return self.stock > 0

    def get_product_details(self) -> str:
        return f"{self.name} - Price: ${self.price}, Stock: {self.stock}"

    def __str__(self):
        return self.name

# Order & OrderItem: Đơn hàng và mục đơn hàng
class Order(models.Model):
    date = models.DateField(default=timezone.now)
    order_status = models.CharField(max_length=50, blank=True, null=True)
    total_amount = models.FloatField(default=0.0)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    products = models.ManyToManyField(Product, through='OrderItem', blank=True, related_name='orders')

    def add_item(self, product: Product, quantity: int):
        item, created = OrderItem.objects.get_or_create(order=self, product=product, defaults={'quantity': quantity})
        if not created:
            item.quantity += quantity
            item.save()

    def calculate_total(self) -> float:
        total = sum(item.product.price * item.quantity for item in self.order_items.all())
        self.total_amount = total
        self.save()
        return total

    def __str__(self):
        return f"Order #{self.pk} - {self.order_status or 'Not set'}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

# Counter: Quầy bán hàng
class Counter(models.Model):
    location = models.CharField(max_length=100)
    assigned_employee = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': Role.SALES_STAFF},
        related_name='counters'
    )
    orders = models.ManyToManyField(Order, blank=True, related_name='counters')
    products = models.ManyToManyField(Product, blank=True, related_name='counters')

    def manage_order(self):
        return self.orders.all()

    def manage_product(self):
        return self.products.all()

    def get_details(self) -> str:
        return f"Counter at {self.location}"

    def __str__(self):
        return f"Counter: {self.location}"

# Debts: Khoản nợ, liên kết với Accountant
class Debts(models.Model):
    amount = models.FloatField(default=0.0)
    interest = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)
    accountant = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='debts',
        limit_choices_to={'role': Role.ACCOUNTANT}
    )

    def calculate_debt(self):
        # Ví dụ: tính tiền lãi
        return self.amount * (self.interest / 100)

    def __str__(self):
        return f"Debt: ${self.amount} at {self.interest}%"
    
class SystemSetting(models.Model):
    store_name = models.CharField(max_length=100, default="Jewelry Sales Manager")
    contact_email = models.EmailField(default="info@example.com")
    tax_rate = models.FloatField(default=5.0, help_text="Tax rate in percentage")
    discount_rate = models.FloatField(default=0.0, help_text="Default discount rate in percentage")
    
    def __str__(self):
        return self.store_name