# costing/signals.py (সম্পূর্ণ এবং নতুন সংস্করণ)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, F, DecimalField
from django.db import models

from sales.models import SalesOrder, SalesOrderItem, SalesReturn, SalesReturnItem
from .models import JobCost

@receiver(post_save, sender=SalesOrder)
def create_or_update_job_cost_on_sale(sender, instance, created, **kwargs):
    # শুধুমাত্র 'delivered' স্ট্যাটাসের সেলস অর্ডারের জন্য এই কোডটি চলবে
    if instance.status == 'delivered':
        sales_order = instance
        
        total_revenue = sales_order.total_amount or 0
        material_cost_agg = sales_order.items.aggregate(
            total_cost=Sum(F('quantity') * F('product__cost_price'), output_field=models.DecimalField())
        )
        total_material_cost = material_cost_agg.get('total_cost') or 0
        profit = total_revenue - total_material_cost

        JobCost.objects.update_or_create(
            sales_order=sales_order,
            defaults={
                'total_revenue': total_revenue,
                'total_material_cost': total_material_cost,
                'profit': profit,
            }
        )

# --- সেলস রিটার্নের জন্য নতুন এবং উন্নত সিগন্যাল ---

@receiver(post_save, sender=SalesReturnItem)
def update_job_cost_on_return(sender, instance, created, **kwargs):
    """
    যখনই কোনো SalesReturnItem তৈরি হবে, এই সিগন্যালটি সংশ্লিষ্ট 
    JobCost রেকর্ডটিকে আপডেট করে দেবে।
    """
    if created: # শুধুমাত্র নতুন রিটার্ন আইটেমের জন্য কাজ করবে
        returned_item = instance
        original_order = returned_item.sales_return.sales_order

        try:
            job_cost = JobCost.objects.get(sales_order=original_order)

            # --- মূল পরিবর্তন: ফেরত আসা পণ্যের সঠিক মূল্য গণনা ---
            # SalesReturnItem মডেলে থাকা unit_price ব্যবহার করা হচ্ছে
            returned_revenue = returned_item.quantity * returned_item.unit_price
            returned_cost = returned_item.quantity * returned_item.product.cost_price

            # পুরোনো JobCost থেকে ফেরত আসা পরিমাণ বিয়োগ করা
            job_cost.total_revenue = F('total_revenue') - returned_revenue
            job_cost.total_material_cost = F('total_material_cost') - returned_cost
            job_cost.save()

            # লাভ/ক্ষতি পুনরায় গণনা করা
            job_cost.refresh_from_db() # ডেটাবেস থেকে সর্বশেষ মান আনা হচ্ছে
            job_cost.profit = job_cost.total_revenue - job_cost.total_material_cost
            job_cost.save()

        except JobCost.DoesNotExist:
            # যদি কোনো কারণে JobCost রেকর্ডটি না পাওয়া যায়
            pass