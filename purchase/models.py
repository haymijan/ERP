# purchase/models.py
from django.db import models
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from products.models import Product
from partners.models import Supplier
from stock.models import Warehouse, Location
from stock.models import LotSerialNumber


class ProductSupplier(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='supplier_prices')
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.CASCADE, related_name='supplied_products')
    supplier_product_code = models.CharField(max_length=100, blank=True, null=True, help_text="Supplier's internal product code")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at which this product is purchased from the supplier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'supplier')
        db_table = 'inventory_productsupplier'
        verbose_name_plural = "Product Suppliers"

    def __str__(self):
        return f"{self.product.name} from {self.supplier.name}"

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('purchase_request', 'Purchase Request'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders', null=True, blank=True)
    
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='purchase_orders'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders_created'
    )
    
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='purchase_request')
    notes = models.TextField(blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"PO-{self.id}"

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchase_order_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product.name} ({self.quantity} pcs)"

# --- নতুন মডেল: স্টক ট্রান্সফার রিকোয়েস্ট ---
class StockTransferRequest(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('in_transit', 'In Transit'),
        ('received', 'Received'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='transfer_requests')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transfer_requests')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_transferred = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="The actual quantity sent from the source warehouse.")
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="The actual quantity received at the destination warehouse.")
    
    # --- নতুন ফিল্ডটি এখানে যোগ করা হয়েছে ---
    dispatched_lot = models.ForeignKey(
        LotSerialNumber, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='transfer_dispatches',
        help_text="The specific lot from which stock was dispatched."
    )
    # --- নতুন ফিল্ড শেষ ---

    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='source_transfers')
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='destination_transfers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transfer Request #{self.id} for {self.product.name}"

    class Meta:
        db_table = 'inventory_stock_transfer_request'
        verbose_name = "Stock Transfer Request"
        verbose_name_plural = "Stock Transfer Requests"