# purchase/forms.py
from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from .models import PurchaseOrder, PurchaseOrderItem, ProductSupplier, StockTransferRequest
from stock.models import Location
from partners.models import Supplier
from products.models import Product
from .models import Warehouse
from stock.models import LotSerialNumber, Stock

from django.contrib.auth import get_user_model

User = get_user_model()

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        # supplier ফিল্ডটি এখানে যোগ করা হয়েছে
        fields = ['supplier', 'expected_delivery_date', 'notes', 'status', 'warehouse', 'user']
        labels = {'supplier': 'Supplier', 'expected_delivery_date': 'Expected Delivery Date', 'notes': 'Notes'}
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.HiddenInput(),
            'warehouse': forms.HiddenInput(),
            'user': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # supplier ফিল্ডটি default-ভাবে required=False করা হয়েছে
        self.fields['supplier'].required = False


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': 1}),
            'unit_price': forms.TextInput(attrs={'class': 'form-control unit-price', 'type': 'number', 'step': 'any'}),
        }

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm,
    extra=1, can_delete=True, fields=['product', 'quantity', 'unit_price']
)

class PurchaseReceiveItemForm(forms.Form):
    purchase_order_item_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity_to_receive = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="Quantity to Receive",
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'})
    )
    destination_location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        label="Destination Location",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    lot_number = forms.CharField(max_length=100, required=False, label="Lot Number", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'}))
    expiration_date = forms.DateField(
        required=False,
        label="Expiration Date",
        widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'})
    )

PurchaseReceiveFormSet = forms.formset_factory(PurchaseReceiveItemForm, extra=0)

class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)
    status = forms.CharField(required=False, widget=forms.Select(choices=[('', 'All')] + PurchaseOrder.STATUS_CHOICES))
    order_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PO-123'}))

class ApproveForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all().order_by('name'),
        empty_label="--- Select a Supplier ---",
        required=True,
        label="Supplier",
        widget=forms.Select(attrs={'class': 'form-control select2-modal'})
    )

class ApproveOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'quantity', 'unit_price']
        widgets = {
            'id': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'readonly': 'readonly'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control form-control-sm unit-price-input', 'step': 'any'}),
        }

    product_name = forms.CharField(label="Product", required=False, widget=forms.TextInput(attrs={'class': 'form-control-plaintext text-muted', 'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'product', None):
            self.fields['product_name'].initial = self.instance.product.name

ApproveOrderItemFormSet = modelformset_factory(
    PurchaseOrderItem,
    form=ApproveOrderItemForm,
    fields=['id', 'quantity', 'unit_price'],
    extra=0,
    can_delete=False
)

class StockTransferRequestForm(forms.ModelForm):
    class Meta:
        model = StockTransferRequest
        fields = ['product', 'quantity', 'source_warehouse', 'notes']
        # ... (widgets and other logic)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            user_warehouse = getattr(user, 'warehouse', None)
            if user_warehouse:
                # ব্যবহারকারী যেন নিজেকেই সোর্স হিসেবে সিলেক্ট করতে না পারে
                self.fields['source_warehouse'].queryset = Warehouse.objects.exclude(id=user_warehouse.id)
        
        # শুধুমাত্র স্টক আছে এমন প্রোডাক্ট দেখানো হবে
        stocked_products = Product.objects.filter(stocks__quantity__gt=0).distinct()
        self.fields['product'].queryset = stocked_products
    
class ReceiveStockTransferForm(forms.Form):
    quantity_received = forms.IntegerField(
        label="Quantity Received", 
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    destination_location = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        label="Destination Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # রিসিভ করার সময় নতুন লট নম্বর দেওয়ার ব্যবস্থা
    lot_number = forms.CharField(
        max_length=100, 
        required=False, 
        label="New Lot/Serial Number (if applicable)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    expiration_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Expiration Date (if applicable)"
    )

class ProcessStockTransferForm(forms.Form):
    quantity_to_transfer = forms.IntegerField(
        label="Quantity to Dispatch", 
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    source_location = forms.ModelChoiceField(
        queryset=Location.objects.none(), # এই queryset-টি ভিউ থেকে ডায়নামিকভাবে সেট করা হবে
        label="Source Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # লট-ট্র্যাকড প্রোডাক্টের জন্য লট নম্বর ফিল্ড (ঐচ্ছিক)
    lot_serial = forms.ModelChoiceField(
        queryset=LotSerialNumber.objects.none(),
        required=False,
        label="Lot/Serial Number (if applicable)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class StockTransferFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Start Date"
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="End Date"
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    source_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        required=False,
        label="From Warehouse",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    destination_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        required=False,
        label="To Warehouse",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + StockTransferRequest.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    requested_by = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Requested By",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            user_warehouse = getattr(user, 'warehouse', None)
            if user_warehouse:
                self.fields['source_warehouse'].queryset = Warehouse.objects.filter(pk=user_warehouse.pk)
                self.fields['destination_warehouse'].queryset = Warehouse.objects.all()
                self.fields['requested_by'].queryset = User.objects.filter(warehouse=user_warehouse)