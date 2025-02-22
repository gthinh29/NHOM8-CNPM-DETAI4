# managers.py
from django.db import models, transaction
from django.db.models import F, Sum
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache

from store.models import Product

class InsufficientStockError(ValidationError):
    def __init__(self, product, available, requested):
        super().__init__(f"Insufficient stock for {product.name}. Available: {available}, Requested: {requested}")
        self.product = product
        self.available = available
        self.requested = requested

class ProductUnavailableError(ValidationError):
    def __init__(self, product_id):
        super().__init__(f"Product ID {product_id} is unavailable or out of stock")
        self.product_id = product_id

class ProductManager(models.Manager):
    def with_stock_info(self):
        return self.annotate(
            total_value=models.F('price') * models.F('stock')
        ).order_by('-created_at')

    def get_available_product(self, product_id):
        try:
            product = self.get(id=product_id, is_active=True)
            if product.stock > 0:
                return product
            raise ProductUnavailableError(product_id)
        except self.model.DoesNotExist:
            raise ProductUnavailableError(product_id)

    @transaction.atomic
    def decrease_stock(self, product_id, quantity):
        product = self.select_for_update().get(pk=product_id)
        if product.stock < quantity:
            raise InsufficientStockError(
                product=product,
                available=product.stock,
                requested=quantity
            )
        product.stock = models.F('stock') - quantity
        product.save(update_fields=['stock'])
        return product.refresh_from_db()

class OrderManager(models.Manager):
    @transaction.atomic
    def create_order_from_cart(self, user, cart_data):
        from .models import OrderItem  # Avoid circular import

        order = self.model(
            user=user,
            total_amount=0,
            status=self.model.Status.PENDING
        )
        order.full_clean()
        order.save()

        total = 0
        order_items = []
        products_to_update = []

        for product_id_str, quantity in cart_data.items():
            product_id = int(product_id_str)
            quantity = int(quantity)

            product = Product.objects.get_available_product(product_id)
            
            if product.stock < quantity:
                raise InsufficientStockError(
                    product=product,
                    available=product.stock,
                    requested=quantity
                )

            order_items.append(OrderItem(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            ))

            product.stock -= quantity
            products_to_update.append(product)
            total += product.price * quantity

        # Bulk operations
        self.bulk_update_stock(products_to_update)
        OrderItem.objects.bulk_create(order_items)
        
        order.total_amount = total
        order.status = self.model.Status.COMPLETED
        order.save(update_fields=['total_amount', 'status', 'updated_at'])
        
        self._clear_order_cache(user)
        return order

    def bulk_update_stock(self, products):
        self.bulk_update(
            products,
            ['stock'],
            batch_size=100
        )

    def get_sales_periods(self, date=None):
        date = date or timezone.now().date()
        return {
            'daily': self._get_daily_sales(date),
            'weekly': self._get_weekly_sales(date),
            'monthly': self._get_monthly_sales(date),
            'yearly': self._get_yearly_sales(date),
            'chart_data': self._get_sales_chart_data(date)
        }

    def _get_daily_sales(self, date):
        return self.filter(
            created_at__date=date,
            status=self.model.Status.COMPLETED
        ).aggregate(total=Sum('total_amount'))['total'] or 0

    def _get_sales_chart_data(self, date):
        return [
            {
                'date': (date - timedelta(days=i)).strftime("%a"),
                'total': self._get_daily_sales(date - timedelta(days=i))
            }
            for i in range(6, -1, -1)
        ]

    def _clear_order_cache(self, user):
        cache_keys = [
            f'user_orders_{user.id}',
            'recent_sales',
            'total_sales'
        ]
        cache.delete_many(cache_keys)