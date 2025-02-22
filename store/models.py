from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    ACCOUNTANT = 'accountant', 'Accountant'
    STORE_MANAGER = 'store_manager', 'Store Manager'
    SALES_STAFF = 'sales_staff', 'Sales Staff'
    CUSTOMER = 'customer', 'Khách hàng'

class CustomUser(AbstractUser):
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

    def clean(self):
        if self.role == Role.customer and not (self.phone and self.email):
            raise ValidationError("Khách hàng cần có số điện thoại và email hợp lệ")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_full_info(self) -> str:
        return f"Username: {self.username}, Email: {self.email}, Phone: {self.phone}, Role: {self.get_role_display()}"

    def change_password(self, new_password: str):
        self.set_password(new_password)
        self.save()

class Customer(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={'role': Role.CUSTOMER}
    )
    address = models.TextField()
    loyalty_points = models.IntegerField(default=0)
    registration_date = models.DateField(auto_now_add=True)

    def get_purchase_history(self):
        return Order.objects.filter(customer=self).order_by('-date')

    def update_loyalty_points(self, points: int):
        self.loyalty_points += points
        self.save()

    def get_customer_status(self):
        if self.loyalty_points > 1000:
            return "VIP"
        elif self.loyalty_points > 500:
            return "Thân thiết"
        return "Mới"

    def __str__(self):
        return f"{self.user.username} - {self.get_customer_status()}"

from django.db import models
from django.template.defaultfilters import slugify

class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    price = models.FloatField(default=0.0)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)  # Thêm trường mô tả
    orders = models.ManyToManyField(
        'Order',  
        through='OrderItem',
        blank=True,
        related_name='products_orders'
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def update_stock(self, quantity: int) -> bool:
        if quantity < 0 and self.stock < abs(quantity):
            return False
        self.stock += quantity
        self.save()
        return True

    def set_price(self, new_price: float):
        self.price = new_price
        self.save()

    def apply_discount(self, discount_percentage: float):
        if 0 <= discount_percentage <= 100:
            discount_amount = self.price * (discount_percentage / 100)
            self.price -= discount_amount
            self.save()

    def is_available(self) -> bool:
        return self.stock > 0

    def is_low_stock(self, threshold: int = 5) -> bool:
        return self.stock < threshold

    def get_details(self) -> str:
        return f"Product: {self.name}, Price: ${self.price:.2f}, Stock: {self.stock}"

    def __str__(self):
        return self.name

class StoreCounter(models.Model):
    location = models.CharField(max_length=100)
    manager = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': Role.STORE_MANAGER},
        related_name='managed_counters',
        editable=False
    )
    
    assigned_employee = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': Role.SALES_STAFF},
        related_name='assigned_counter'
    )
    products = models.ManyToManyField(Product, blank=True, related_name='counters')

    def assign_employee(self, employee: CustomUser):
        if employee.role == Role.SALES_STAFF:
            self.assigned_employee = employee
            self.save()

    def get_details(self) -> str:
        return f"Counter at {self.location} managed by {self.manager.username}"

    def is_managed_by(self, user: CustomUser) -> bool:
        return self.manager == user

    def __str__(self):
        return f"Counter: {self.location}"

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
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_products'
    )
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    products = models.ManyToManyField(Product, through='OrderItem', blank=True, related_name='order_products')

    def add_item(self, product, quantity):
        if product.update_stock(-quantity):
            item, created = OrderItem.objects.get_or_create(
                order=self, 
                product=product, 
                defaults={'quantity': quantity}
            )
            if not created:
                item.quantity += quantity
                item.save()
            self.calculate_total()
            return True
        return False

    def calculate_total(self):
        total = sum(item.product.price * item.quantity for item in self.order_items.all())
        self.total_amount = total
        self.save()
        return total

    def process_payment(self):
        if self.order_status == 'pending':
            self.order_status = 'paid'
            self.save()
            return True
        return False

    def cancel_order(self):
        if self.order_status == 'pending':
            self.order_status = 'canceled'
            for item in self.order_items.all():
                item.product.update_stock(item.quantity)
            self.save()
            return True
        return False

    def refund(self):
        if self.order_status == 'paid':
            self.order_status = 'refunded'
            for item in self.order_items.all():
                item.product.update_stock(item.quantity)
            self.save()
            return True
        return False

    def generate_invoice(self):
        items = "\n".join(
            [f"{item.product.name} x {item.quantity} - ${item.product.price * item.quantity:.2f}"
             for item in self.order_items.all()]
        )
        return f"Invoice for Order #{self.pk}:\n{items}\nTotal: ${self.total_amount:.2f}"

    def __str__(self):
        return f"Order #{self.pk} - {self.order_status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)

    def update_quantity(self, new_quantity: int):
        if new_quantity > 0:
            self.quantity = new_quantity
            self.save()

    def delete_item(self):
        self.delete()

    def get_item_info(self) -> str:
        return f"Product: {self.product.name}, Quantity: {self.quantity}, Total Price: ${self.product.price * self.quantity:.2f}"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

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

    def calculate_debt(self) -> float:
        return self.amount * (self.interest / 100)

    def is_debt_paid(self) -> bool:
        return self.amount <= 0

    def get_debt_info(self) -> str:
        return f"Debt Amount: ${self.amount:.2f}, Interest Rate: {self.interest:.2f}%"

    def pay_debt(self, amount: float) -> bool:
        if amount > 0 and amount <= self.amount:
            self.amount -= amount
            self.save()
            return True
        return False

    def __str__(self):
        return f"Debt: ${self.amount:.2f} at {self.interest:.2f}%"

class SystemSetting(models.Model):
    store_name = models.CharField(max_length=100, default="Jewelry Sales Manager")
    contact_email = models.EmailField(default="info@example.com")
    tax_rate = models.FloatField(default=5.0, help_text="Tax rate in percentage")
    discount_rate = models.FloatField(default=0.0, help_text="Default discount rate in percentage")

    def apply_tax(self, amount: float) -> float:
        return amount + (amount * (self.tax_rate / 100))

    def apply_discount(self, amount: float) -> float:
        return amount - (amount * (self.discount_rate / 100))

    def is_valid_email(self) -> bool:
        return '@' in self.contact_email and '.' in self.contact_email.split('@')[-1]

    def is_tax_rate_valid(self) -> bool:
        return 0 <= self.tax_rate <= 100

    def is_discount_rate_valid(self) -> bool:
        return 0 <= self.discount_rate <= 100

    def is_settings_complete(self) -> bool:
        return all([self.store_name, self.contact_email, self.tax_rate is not None, self.discount_rate is not None])

    def get_settings_info(self) -> str:
        return f"Store Name: {self.store_name}, Contact Email: {self.contact_email}, Tax Rate: {self.tax_rate:.2f}%, Discount Rate: {self.discount_rate:.2f}%"

    def update_settings(self, store_name: str = None, contact_email: str = None, tax_rate: float = None, discount_rate: float = None):
        if store_name:
            self.store_name = store_name
        if contact_email:
            self.contact_email = contact_email
        if tax_rate is not None:
            self.tax_rate = tax_rate
        if discount_rate is not None:
            self.discount_rate = discount_rate
        self.save()