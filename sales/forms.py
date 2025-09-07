# sales/forms.py

from django import forms
from django.forms import inlineformset_factory, formset_factory
from .models import SalesOrder, SalesOrderItem, SalesReturn, SalesReturnItem
from partners.models import Customer
from stock.models import Location, LotSerialNumber, Warehouse, Stock # Stock মডেল ইম্পোর্ট করুন
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer', 'expected_delivery_date', 'status', 'notes', 'warehouse']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control select2'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'warehouse': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and not user.is_superuser:
            user_warehouse = getattr(user, 'warehouse', None)
            if user_warehouse:
                self.fields['warehouse'].queryset = Warehouse.objects.filter(id=user_warehouse.id)
                self.fields['warehouse'].initial = user_warehouse
                self.fields['warehouse'].widget.attrs['disabled'] = True
            else:
                self.fields['warehouse'].queryset = Warehouse.objects.none()

class SalesOrderItemForm(forms.ModelForm):
    class Meta:
        model = SalesOrderItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control unit-price-input'}),
        }

    def __init__(self, *args, **kwargs):
        user_warehouse = kwargs.pop('warehouse', None)
        kwargs.pop('user', None) # TypeError এড়ানোর জন্য user-কে সরানো হলো
        super().__init__(*args, **kwargs)
        
        products_qs = Product.objects.filter(is_active=True)
        if user_warehouse:
            # ================== আপনার পুরনো এবং সঠিক লজিক ফিরিয়ে আনা হলো ==================
            # শুধুমাত্র ডাটাবেজ ফিল্ডটি ('location__warehouse' -> 'warehouse') আপডেট করা হয়েছে
            products_in_warehouse = Stock.objects.filter(
                warehouse=user_warehouse, 
                quantity__gt=0
            ).values_list('product_id', flat=True)
            
            products_qs = products_qs.filter(id__in=products_in_warehouse)
            # =========================================================================
        
        self.fields['product'].queryset = products_qs.distinct().order_by('name')

SalesOrderItemFormSet = inlineformset_factory(
    SalesOrder, SalesOrderItem, form=SalesOrderItemForm,
    fields=['product', 'quantity', 'unit_price'], extra=1, can_delete=True
)

# আপনার বাকি ফর্ম এবং ফর্মসেটগুলো অপরিবর্তিত থাকবে
class SalesOrderItemFulfillmentForm(forms.Form):
    sales_order_item_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity_fulfilled = forms.IntegerField(min_value=0, label="Fulfill Quantity", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    source_location = forms.ModelChoiceField(queryset=Location.objects.none(), label="Source Location", widget=forms.Select(attrs={'class': 'form-control'}))
    lot_serial = forms.ModelChoiceField(queryset=LotSerialNumber.objects.none(), required=False, label="Lot/Serial", widget=forms.Select(attrs={'class': 'form-control'}))

SalesOrderItemFulfillmentFormSet = formset_factory(SalesOrderItemFulfillmentForm, extra=0)

class SalesOrderFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), label="Start Date")
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), label="End Date")
    order_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Order #'}), label="Order Number")
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-control select2'}), label="User")
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-control select2'}), label="Branch")

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if request_user and not request_user.is_superuser:
            user_warehouse = getattr(request_user, 'warehouse', None)
            if user_warehouse:
                self.fields['warehouse'].queryset = Warehouse.objects.filter(id=user_warehouse.id)
                self.fields['warehouse'].initial = user_warehouse
            else:
                self.fields['warehouse'].queryset = Warehouse.objects.none()

class FindSalesOrderForm(forms.Form):
    """
    এই فرمটি ব্যবহার করে ব্যবহারকারী পুরোনো সেলস অর্ডার খুঁজে বের করবেন।
    """
    order_id = forms.IntegerField(
        label="Enter Sales Order ID (e.g., 13)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter SO Number'})
    )

class SalesReturnForm(forms.ModelForm):
    """
    এই فرمটি ফেরতের মূল তথ্যগুলো (যেমন কারণ) ধারণ করবে।
    """
    class Meta:
        model = SalesReturn
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SalesReturnItemForm(forms.ModelForm):
    """
    এই فرمটি প্রতিটি ফেরত আসা আইটেমের জন্য তৈরি হবে।
    এটি ব্যবহারকারীকে ফেরত আসা পণ্যের পরিমাণ লিখতে দেবে।
    """
    # মূল বিক্রয়ের পরিমাণ দেখানোর জন্য একটি বাড়তি ফিল্ড
    original_quantity = forms.IntegerField(disabled=True, required=False)

    class Meta:
        model = SalesReturnItem
        fields = ['product', 'quantity', 'lot_serial']
        widgets = {
            'product': forms.HiddenInput(),
            'lot_serial': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        # মূল সেলস অর্ডার আইটেমটি এখানে পাস করা হবে
        self.sales_order_item = kwargs.pop('sales_order_item', None)
        super().__init__(*args, **kwargs)

        if self.sales_order_item:
            self.fields['original_quantity'].initial = self.sales_order_item.quantity
            # ব্যবহারকারী যেন বিক্রিত পরিমাণের চেয়ে বেশি ফেরত দিতে না পারে
            self.fields['quantity'].widget.attrs['max'] = self.sales_order_item.quantity


# Formset ব্যবহার করে একাধিক আইটেম একসাথে প্রসেস করা হবে
SalesReturnItemFormSet = inlineformset_factory(
    SalesReturn,
    SalesReturnItem,
    form=SalesReturnItemForm,
    extra=0, # কোনো অতিরিক্ত খালি فرم দেখানো হবে না
    can_delete=False,
    fields=['product', 'quantity', 'lot_serial']
)