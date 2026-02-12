from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone
from .models import Category, StationeryItem, Customer, Sale, SaleItem, Debt, Payment
from .models import Expenditure


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(StationeryItem)
class StationeryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'unit_price', 'cost_price', 'stock_quantity', 'profit_margin_display', 'is_low_stock_display', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku', 'supplier']
    list_editable = ['unit_price', 'cost_price', 'stock_quantity', 'is_active']
    readonly_fields = ['profit_margin_display', 'is_low_stock_display']

    def profit_margin_display(self, obj):
        return f"{obj.profit_margin:.1f}%"
    profit_margin_display.short_description = "Profit Margin"

    def is_low_stock_display(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color: red;">LOW STOCK</span>')
        return format_html('<span style="color: green;">OK</span>')
    is_low_stock_display.short_description = "Stock Status"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'phone']
    list_editable = ['is_active']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'sale_date_local', 'total_amount', 'payment_method', 'is_paid', 'profit_display', 'created_by']
    list_filter = ['payment_method', 'is_paid', 'sale_date', 'created_by']
    search_fields = ['customer__name', 'notes']
    readonly_fields = ['profit_display']
    inlines = [SaleItemInline]
    actions = ['delete_and_restore_stock']

    def profit_display(self, obj):
        return f"${obj.profit:.2f}"
    profit_display.short_description = "Profit"

    def sale_date_local(self, obj):
        if not obj.sale_date:
            return '-'
        local_dt = timezone.localtime(obj.sale_date)
        return local_dt.strftime('%b %d, %Y %H:%M')
    sale_date_local.admin_order_field = 'sale_date'
    sale_date_local.short_description = 'Sale Date'

    def delete_and_restore_stock(self, request, queryset):
        """Admin action to delete selected sales and show restored stock in a message."""
        # Collect restored quantities per item name
        restored = {}
        total_sales = queryset.count()
        for sale in queryset:
            for si in sale.items.all():
                name = si.item.name
                restored[name] = restored.get(name, 0) + si.quantity

        # Perform deletion (this will trigger signals to restore stock for bulk deletes)
        queryset.delete()

        if restored:
            parts = [f"{name} (+{qty})" for name, qty in restored.items()]
            messages.success(request, f"Deleted {total_sales} sale(s). Restored stock: {', '.join(parts)}")
        else:
            messages.success(request, f"Deleted {total_sales} sale(s).")

    delete_and_restore_stock.short_description = "Delete selected sales and restore stock (show restored items)"


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'item', 'quantity', 'unit_price', 'total_price']
    list_filter = ['sale__sale_date']


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'paid_amount', 'remaining_amount', 'due_date', 'status', 'is_overdue_display']
    list_filter = ['status', 'due_date', 'created_at']
    search_fields = ['customer__name', 'description']
    readonly_fields = ['remaining_amount', 'is_overdue_display']

    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">OVERDUE</span>')
        return format_html('<span style="color: green;">OK</span>')
    is_overdue_display.short_description = "Overdue Status"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['debt', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['debt__customer__name', 'notes']


@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'amount', 'expense_date', 'created_by']
    list_filter = ['category', 'expense_date']
    search_fields = ['description']
    readonly_fields = ['created_at']
