# partners/forms.py

from django import forms
from .models import Supplier, Customer

# Supplier মডেলের জন্য ফর্ম
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        labels = {
            'name': 'Supplier Name', 'contact_person': 'Contact Person',
            'email': 'Email', 'phone': 'Phone', 'address': 'Address',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter supplier name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact person name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
        }

# Customer মডেলের জন্য ফর্ম
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'address']
        labels = {
            'name': 'Customer Name', 'email': 'Email',
            'phone': 'Phone', 'address': 'Address',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter customer name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
        }

class CustomerFilterForm(forms.Form):
    """
    এই فرمটি কাস্টমার লিস্ট পেজে ফিল্টার করার জন্য ব্যবহৃত হবে।
    """
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name, Email or Phone...'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="From Date"
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="To Date"
    )