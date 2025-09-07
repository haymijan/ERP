from django import template
from purchase.models import PurchaseOrderItem

register = template.Library()

@register.filter
def get_purchase_order_item_name(item_id):
    try:
        item = PurchaseOrderItem.objects.get(id=item_id)
        return item.product.name
    except PurchaseOrderItem.DoesNotExist:
        return ""

@register.filter
def get_purchase_order_item_quantity(item_id):
    try:
        item = PurchaseOrderItem.objects.get(id=item_id)
        return item.quantity
    except PurchaseOrderItem.DoesNotExist:
        return 0