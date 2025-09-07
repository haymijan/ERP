# costing/models.py

from django.db import models
from sales.models import SalesOrder

class JobCost(models.Model):
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.CASCADE, related_name='job_cost')
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job Cost for SO-{self.sales_order.id}"

    class Meta:
        db_table = 'inventory_job_cost'
        verbose_name = "Job Cost"
        verbose_name_plural = "Job Costs"