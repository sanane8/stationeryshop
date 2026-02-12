from django import template

register = template.Library()

@register.filter
def tzs(value):
    """Format value as Tanzanian Shillings"""
    if value is None:
        return "TZS 0"
    try:
        return f"TZS {value:,.0f}"
    except (ValueError, TypeError):
        return "TZS 0"

@register.filter
def tzs_decimal(value):
    """Format value as Tanzanian Shillings with decimal places"""
    if value is None:
        return "TZS 0.00"
    try:
        return f"TZS {value:,.2f}"
    except (ValueError, TypeError):
        return "TZS 0.00"

