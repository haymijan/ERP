# costing/admin.py (চূড়ান্ত এবং নির্ভুল সংস্করণ)

from django.contrib import admin
from .models import JobCost

@admin.register(JobCost)
class JobCostAdmin(admin.ModelAdmin):
    """
    JobCost মডেলটিকে Django অ্যাডমিন প্যানেলে দেখানোর জন্য কাস্টমাইজেশন।
    """
    list_display = (
        'sales_order_link', 
        'total_revenue', 
        'total_material_cost', 
        'profit', 
        'created_at'
    )
    search_fields = ('sales_order__id',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def sales_order_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        
        # সেলস অর্ডারের লিংকে যাওয়ার জন্য একটি কাস্টম মেথড
        link = reverse("admin:sales_salesorder_change", args=[obj.sales_order.id])
        return format_html('<a href="{}">SO-{}</a>', link, obj.sales_order.id)
    
    sales_order_link.short_description = 'Sales Order'