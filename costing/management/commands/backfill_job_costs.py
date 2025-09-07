# costing/management/commands/backfill_job_costs.py

from django.core.management.base import BaseCommand
from django.db.models import Sum, F, DecimalField
from sales.models import SalesOrder
from costing.models import JobCost

class Command(BaseCommand):
    help = 'Creates missing JobCost records for past delivered Sales Orders.'

    def handle(self, *args, **options):
        self.stdout.write("Starting to backfill JobCost data...")
        
        delivered_orders = SalesOrder.objects.filter(status='delivered')
        created_count = 0

        for order in delivered_orders:
            # চেক করা হচ্ছে এই অর্ডারের জন্য JobCost আগে থেকেই আছে কি না
            if not hasattr(order, 'job_cost'):
                total_revenue = order.total_amount or 0
                
                material_cost_agg = order.items.aggregate(
                    total_cost=Sum(F('quantity') * F('product__cost_price'), output_field=DecimalField())
                )
                total_material_cost = material_cost_agg.get('total_cost') or 0
                
                profit = total_revenue - total_material_cost

                JobCost.objects.create(
                    sales_order=order,
                    total_revenue=total_revenue,
                    total_material_cost=total_material_cost,
                    profit=profit
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created JobCost for SO-{order.id}"))

        self.stdout.write(self.style.SUCCESS(f"Backfill complete. Created {created_count} new JobCost records."))