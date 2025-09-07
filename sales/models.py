# sales/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from stock.models import Warehouse, LotSerialNumber

class SalesOrder(models.Model):
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user who created the sales order."
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The branch/warehouse from which the sale was made."
    )
    expected_delivery_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=20, default='cash')
    amount_tendered = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_due = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): 
        return f"SO-{self.id} ({self.customer.name if self.customer else 'N/A'})"
    
    class Meta:
        db_table = 'inventory_salesorder'
    
class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # --- নতুন ফিল্ডটি এখানে যোগ করা হয়েছে ---
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Cost of the product at the time of sale."
    )
    # --- পরিবর্তন শেষ ---

    quantity_fulfilled = models.PositiveIntegerField(default=0)
    lot_serial = models.ForeignKey(
        LotSerialNumber, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="The specific lot this item was sold from."
    )

    def __str__(self): return f"{self.quantity} x {self.product.name} for SO-{self.sales_order.id}"
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price
    
    class Meta:
        db_table = 'inventory_salesorderitem'

# --- Sales Return মডেলগুলো নিচে যোগ করা হয়েছে ---
class SalesReturn(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, help_text="The original sales order being returned.")
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True, null=True, help_text="Reason for the return.")
    return_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Return for SO-{self.sales_order.id}"

class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturn, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Price of the item at the time of return."
    )
    lot_serial = models.ForeignKey(LotSerialNumber, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.product.name} for Return #{self.sales_return.id}"