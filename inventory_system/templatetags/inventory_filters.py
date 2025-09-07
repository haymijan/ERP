# inventory/templatetags/inventory_filters.py

from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """
    Multiplies the value with the argument.
    Usage: {{ value|mul:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''