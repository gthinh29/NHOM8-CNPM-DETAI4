from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Product, Order, OrderItem
from .exceptions import InsufficientStockError

class CartService:
    @staticmethod
    def get_cart_context(session):
        cart_data = session.get('cart', {})
        items = []
        total = 0
        
        for product_id, quantity in cart_data.items():
            product = get_object_or_404(Product, id=int(product_id))
            subtotal = product.price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            total += subtotal
            
        return {'items': items, 'total': total}

    @staticmethod
    def add_item(session, product_id):
        product = get_object_or_404(Product, id=product_id)
        cart_data = session.get('cart', {})
        
        if product.stock > 0:
            cart_data[str(product.id)] = cart_data.get(str(product.id), 0) + 1
            session['cart'] = cart_data
        else:
            raise InsufficientStockError(product.name, product.stock)

    @staticmethod
    def update_item(session, product_id, quantity):
        cart_data = session.get('cart', {})
        product_id_str = str(product_id)
        
        if int(quantity) > 0:
            cart_data[product_id_str] = int(quantity)
        else:
            cart_data.pop(product_id_str, None)
        session['cart'] = cart_data

    @staticmethod
    def remove_item(session, product_id):
        cart_data = session.get('cart', {})
        product_id_str = str(product_id)
        if product_id_str in cart_data:
            del cart_data[product_id_str]
            session['cart'] = cart_data

class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user, cart_data):
        order = Order.objects.create(created_by=user, total_amount=0)
        products_to_update = []
        order_items = []
        total = 0
        
        for product_id_str, quantity in cart_data.items():
            product = Product.objects.get(id=int(product_id_str))
            if product.stock < quantity:
                raise ValidationError(f"Insufficient stock for {product.name}")
            
            product.stock -= quantity
            products_to_update.append(product)
            order_items.append(OrderItem(
                order=order,
                product=product,
                quantity=quantity
            ))
            total += product.price * quantity
        
        Product.objects.bulk_update(products_to_update, ['stock'])
        OrderItem.objects.bulk_create(order_items)
        order.total_amount = total
        order.save()
        return order