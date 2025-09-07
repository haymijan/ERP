# sales/admin.py

from django.contrib import admin
from .models import SalesOrder, SalesOrderItem

# SalesOrderItem কে SalesOrder এর ইনলাইন হিসেবে যোগ করা হয়েছে
# এটি SalesOrder সম্পাদনা করার সময় একই পৃষ্ঠায় আইটেমগুলি যোগ বা সম্পাদনা করতে দেয়
class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 1 # ডিফল্টরূপে একটি অতিরিক্ত খালি ফর্ম দেখাবে
    fields = ('product', 'quantity', 'unit_price')
    raw_id_fields = ('product',) # পণ্য নির্বাচনের জন্য একটি পপআপ উইন্ডো দেখাবে

# SalesOrder মডেলকে Django অ্যাডমিন প্যানেলে রেজিস্টার করা হয়েছে।
@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'status', 'total_amount', 'user', 'warehouse')
    list_filter = ('status', 'order_date', 'user', 'warehouse')
    search_fields = ('id', 'customer__name', 'user__username')
    inlines = [SalesOrderItemInline] # ইনলাইন আইটেম যোগ করা হয়েছে
    readonly_fields = ('total_amount', 'created_at', 'updated_at') # মোট পরিমাণ, তৈরি/আপডেট তারিখ শুধুমাত্র পঠনযোগ্য
    fieldsets = (
        (None, {
            'fields': ('customer', 'user', 'warehouse', 'order_date', 'expected_delivery_date', 'status', 'notes')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'amount_tendered', 'change_due', 'total_amount')
        }),
    )

