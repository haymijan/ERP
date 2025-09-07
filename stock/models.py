# stock/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
# content_object-এর জন্য এই দুটি লাইন ইম্পোর্ট করুন
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name
    
    class Meta:
        db_table = 'inventory_warehouse'
        
class Location(models.Model):
    name = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    parent_location = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_locations')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        path = [self.name]
        current = self
        count = 0 
        while current.parent_location and count < 10:
            current = current.parent_location
            path.insert(0, current.name)
            count += 1
        return f"{self.warehouse.name} / {' / '.join(path)}"

    def clean(self):
        if self.parent_location and self.parent_location.pk == self.pk:
            raise ValidationError("A location cannot be its own parent.")
        
        p = self.parent_location
        while p:
            if p.pk == self.pk:
                raise ValidationError("Circular dependency detected in location hierarchy.")
            p = p.parent_location
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta: 
        unique_together = ('name', 'warehouse', 'parent_location')
        db_table = 'inventory_location'

class Stock(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'warehouse') 
        verbose_name_plural = "Stocks"
        db_table = 'inventory_stock'
    
    def __str__(self): return f"{self.product.name} ({self.quantity}) at {self.warehouse.name}"

class LotSerialNumber(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='lots')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='lots')
    lot_number = models.CharField(max_length=100, help_text="The batch or serial number")
    quantity = models.IntegerField()
    expiration_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.lot_number} ({self.quantity} in {self.location.name})"

    class Meta:
        unique_together = ('product', 'location', 'lot_number')
        db_table = 'inventory_lotserialnumber'

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment_in', 'Adjustment In'),
        ('adjustment_out', 'Adjustment Out'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # ================== নতুন ফিল্ডগুলো এখানে যোগ করা হলো ==================
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_transactions', null=True, blank=True)
    
    # GenericForeignKey (SalesOrder বা PurchaseOrder-এর সাথে লিংক করার জন্য)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    # =====================================================================

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    lot_serial = models.ForeignKey('LotSerialNumber', on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    source_location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='outgoing_transactions')
    destination_location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transactions')
    transaction_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.quantity} x {self.product.name}"

    class Meta:
        db_table = 'inventory_inventorytransaction'