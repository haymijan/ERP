# purchase/admin.py

from django.contrib import admin
from .models import ProductSupplier, PurchaseOrder, PurchaseOrderItem

# PurchaseOrderItem কে PurchaseOrder এর ইনলাইন হিসেবে যোগ করা হয়েছে
# এটি PurchaseOrder সম্পাদনা করার সময় একই পৃষ্ঠায় আইটেমগুলি যোগ বা সম্পাদনা করতে দেয়
class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1 # ডিফল্টরূপে একটি অতিরিক্ত খালি ফর্ম দেখাবে
    fields = ('product', 'quantity', 'unit_price')
    raw_id_fields = ('product',) # পণ্য নির্বাচনের জন্য একটি পপআপ উইন্ডো দেখাবে, যা অনেক পণ্য থাকলে কার্যকর

# PurchaseOrder মডেলকে Django অ্যাডমিন প্যানেলে রেজিস্টার করা হয়েছে।
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'order_date', 'expected_delivery_date', 'status', 'total_amount')
    list_filter = ('status', 'supplier', 'order_date')
    search_fields = ('id', 'supplier__name')
    inlines = [PurchaseOrderItemInline] # ইনলাইন আইটেম যোগ করা হয়েছে
    readonly_fields = ('total_amount',) # মোট পরিমাণ স্বয়ংক্রিয়ভাবে গণনা করা হয়, তাই এটি শুধুমাত্র পঠনযোগ্য

# ProductSupplier মডেলকে Django অ্যাডমিন প্যানেলে রেজিস্টার করা হয়েছে।
@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'supplier_product_code', 'price')
    list_filter = ('supplier', 'product__category')
    search_fields = ('product__name', 'supplier__name', 'supplier_product_code')

