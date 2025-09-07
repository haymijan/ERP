# stock/forms.py

from django import forms
from django.db.models import Q
from .models import Warehouse, Location, LotSerialNumber, InventoryTransaction
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'address']
        labels = {'name': 'Warehouse Name', 'address': 'Address'}
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter warehouse name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter warehouse address'}),
        }

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'warehouse', 'parent_location', 'description']
        labels = {
            'name': 'Location Name', 'warehouse': 'Warehouse',
            'parent_location': 'Parent Location', 'description': 'Description',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter location name (e.g., Aisle 1, Shelf B)'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
            'parent_location': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter location description'}),
        }

class LotSerialNumberForm(forms.ModelForm):
    class Meta:
        model = LotSerialNumber
        fields = ['product', 'location', 'lot_number', 'quantity', 'expiration_date']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'lot_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., BN12345 or SER98765'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # শুধুমাত্র যে প্রোডাক্টগুলো লট বা সিরিয়াল দিয়ে ট্র্যাক করা হয়, সেগুলোই দেখানো হবে
        self.fields['product'].queryset = Product.objects.filter(
            Q(tracking_method='lot') | Q(tracking_method='serial') # <-- 'models.Q' থেকে 'Q' করা হয়েছে
        ).order_by('name')

class InventoryTransactionForm(forms.ModelForm):
    new_lot_number = forms.CharField(
        label="New Lot/Batch Number",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter new lot/serial number'})
    )
    new_lot_expiration_date = forms.DateField(
        label="Expiration Date for New Lot",
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = InventoryTransaction
        fields = ['product', 'transaction_type', 'quantity', 'lot_serial', 'customer', 'supplier', 
                  'source_location', 'destination_location', 'notes']
        labels = {
            'lot_serial': 'Select Existing Lot/Serial (for Sales/Transfers)',
            'customer': 'Customer (for Sales)', 'supplier': 'Supplier (for Receipts)',
            'source_location': 'Source Location (for Sale/Transfer)',
            'destination_location': 'Destination Location (for Receipt/Transfer)',
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lot_serial'].required = False
        self.fields['lot_serial'].queryset = LotSerialNumber.objects.none()
        
class InventoryAdjustmentForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by('name'), 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    new_quantity = forms.IntegerField(
        min_value=0, 
        label="New Counted Quantity",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)

class StockMovementFilterForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    transaction_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [
            ('purchase', 'Purchase'),
            ('sale', 'Sale'),
            ('adjustment_in', 'Adjustment In'),
            ('adjustment_out', 'Adjustment Out'),
            ('transfer_in', 'Transfer In'),
            ('transfer_out', 'Transfer Out'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class TransactionFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        required=False,
        label="Branch",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )

    def __init__(self, *args, **kwargs):
        # ব্যবহারকারীর ভূমিকার উপর ভিত্তি করে ফর্মের ফিল্ড পরিবর্তন করার জন্য
        request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if request_user and not request_user.is_superuser:
            user_warehouse = getattr(request_user, 'warehouse', None)
            if user_warehouse:
                # ব্রাঞ্চ ম্যানেজারের জন্য শুধুমাত্র তার ব্রাঞ্চের ইউজারদের দেখানো হবে
                self.fields['user'].queryset = User.objects.filter(warehouse=user_warehouse)
                # ব্রাঞ্চ ম্যানেজারের জন্য ওয়্যারহাউস ফিল্ডটি দেখানো হবে না
                del self.fields['warehouse']