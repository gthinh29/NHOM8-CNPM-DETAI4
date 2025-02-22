from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import CustomUser, SystemSetting, StoreCounter, Product, Role, Order, OrderItem

# Form tạo người dùng mới
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].widget = forms.Select(choices=CustomUser.Role.choices)

# Form chỉnh sửa người dùng
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_form_controls()

    def _apply_form_controls(self):
        """Áp dụng style chung cho các field"""
        fields_to_style = [
            'username', 'email', 'first_name', 
            'last_name', 'phone', 'role'
        ]
        
        for field in fields_to_style:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ")}'
            })
        
        # Riêng cho field role
        self.fields['role'].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=Role.choices  # Thêm choices cho trường role
        )

# Form cài đặt hệ thống
class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['store_name', 'contact_email', 'tax_rate', 'discount_rate']
        widgets = {
            'store_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter store name'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact email'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tax rate (%)',
                'step': '0.01'
            }),
            'discount_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter discount rate (%)',
                'step': '0.01'
            }),
        }

# Form quản lý quầy hàng
from django import forms
from .models import StoreCounter

class CounterForm(forms.ModelForm):
    class Meta:
        model = StoreCounter
        fields = ['location', 'assigned_employee', 'products']
        widgets = {
            'products': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Giới hạn lựa chọn assigned_employee chỉ cho SALES_STAFF
        self.fields['assigned_employee'].queryset = CustomUser.objects.filter(role=Role.SALES_STAFF)

# Form quản lý sản phẩm
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock', 'description']  # Hoặc chỉ định các field cụ thể nếu cần
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price',
                'step': '0.01'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stock quantity'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter description',
                'rows': 3
            }),
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'customer_address']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter customer name'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter address', 'rows': 2}),
        }

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select or enter product code'
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
