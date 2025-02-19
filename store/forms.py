from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import SystemSetting

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'phone', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter email'
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter phone number'
        })
        self.fields['role'].widget = forms.Select(attrs={'class': 'form-select'})

class CustomUserChangeForm(UserChangeForm):
    role = forms.ChoiceField(
        choices=get_user_model()._meta.get_field('role').choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter email'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter last name'
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter phone number'
        })

class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['store_name', 'contact_email', 'tax_rate', 'discount_rate']
        widgets = {
            'store_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter store name'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact email'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter tax rate (%)'}),
            'discount_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter discount rate (%)'}),
        }
