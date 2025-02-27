from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import CustomUser, Customer, SystemSetting, StoreCounter, Product, Role, Order, OrderItem

# Form tạo người dùng mới
class CustomerCreateForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['user', 'address', 'loyalty_points']
        widgets = {
            'user': forms.HiddenInput(),  # Ẩn trường user vì sẽ tự động gán
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nhập địa chỉ khách hàng'
            }),
            'loyalty_points': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Nhập điểm tích lũy'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['loyalty_points'].initial = 0  # Mặc định điểm tích lũy là 0

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
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),  # Mặc định rỗng, sẽ cập nhật sau
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Chọn sản phẩm"
    )

    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'customer_address', 'products']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter customer name'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter address', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Nhận user từ view
        super().__init__(*args, **kwargs)
        
        if user and user.assigned_counter.exists():
            self.fields['products'].queryset = user.assigned_counter.first().products.all()


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

from django import forms
from django.core.validators import MinValueValidator
from .models import Order

class PaymentForm(forms.Form):
    PAYMENT_METHODS = [
        ('cash', 'Tiền mặt'),
        ('credit_card', 'Thẻ tín dụng'),
        ('bank_transfer', 'Chuyển khoản'),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        label="Phương thức thanh toán",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'aria-label': 'Chọn phương thức thanh toán'
        }),
        initial='cash'  # Mặc định là tiền mặt
    )

    amount = forms.DecimalField(
        label="Số tiền nhận",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1000',
            'placeholder': 'Nhập số tiền khách đưa',
            'aria-label': 'Số tiền nhận'
        }),
        validators=[MinValueValidator(0)]
    )

    def __init__(self, *args, **kwargs):
        self.order_total = kwargs.pop('order_total', None)
        super().__init__(*args, **kwargs)

        # Thiết lập giá trị tối thiểu cho trường amount
        if self.order_total:
            self.fields['amount'].widget.attrs['min'] = str(self.order_total)
            self.fields['amount'].help_text = f"Số tiền tối thiểu: {self.order_total:,.0f} VNĐ"

    def clean_amount(self):
        """
        Kiểm tra số tiền nhận có đủ để thanh toán hay không
        """
        amount = self.cleaned_data.get('amount')
        if self.order_total and amount < self.order_total:
            raise forms.ValidationError(
                f"Số tiền nhận không đủ. Cần ít nhất {self.order_total:,.0f} VNĐ."
            )
        return amount

    def clean(self):
        """
        Kiểm tra tổng thể form
        """
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        amount = cleaned_data.get('amount')

        # Kiểm tra nếu phương thức thanh toán là thẻ tín dụng hoặc chuyển khoản
        if payment_method in ['credit_card', 'bank_transfer'] and not amount:
            raise forms.ValidationError(
                "Vui lòng nhập số tiền khi thanh toán bằng thẻ tín dụng hoặc chuyển khoản."
            )

        return cleaned_data
