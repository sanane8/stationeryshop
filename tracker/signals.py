"""Django signals for stock management.
Use post_delete on SaleItem as a reliable backup for bulk deletes.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from .models import SaleItem, Sale, Category


def _sync_debt_for_sale(sale):
    """Ensure a Debt exists/updated for an unpaid sale with a customer.

    Rules:
    - If sale has a customer and is unpaid and total_amount > 0, create or update a Debt linked to the sale.
    - If sale becomes paid, mark any linked Debt as paid and set paid_amount to amount.
    - If sale has no customer or total_amount is 0, remove any auto-created debt for this sale.
    """
    from datetime import timedelta
    from django.utils import timezone

    # Import Debt model lazily to avoid circular import issues
    from .models import Debt

    if sale.customer is None or sale.total_amount <= Decimal('0'):
        # If no customer or zero amount, remove auto-created debt if present
        try:
            d = Debt.objects.filter(sale=sale)
            # Only delete debts that we created (heuristic: description contains 'Auto-created')
            d = d.filter(description__icontains='Auto-created')
            if d.exists():
                d.delete()
        except Debt.DoesNotExist:
            pass
        return

    if sale.is_paid:
        # Mark any linked debt as paid, but ONLY if this is not a payment sale
        # Payment sales have notes like 'Payment for Debt #<id>'
        if sale.notes and 'Payment for Debt #' in sale.notes:
            # This is a payment sale, don't auto-update the debt status
            # The debt status is handled by the Payment model's save method
            return
        
        # This is a regular sale being marked as paid, update the debt
        try:
            d = Debt.objects.filter(sale=sale).first()
            if d:
                d.paid_amount = d.amount
                d.status = 'paid'
                d.save()
        except Debt.DoesNotExist:
            pass
        return

    # At this point sale is unpaid, has customer and positive total -> ensure debt exists/updated
    # Use the sale's local date (converted via timezone.localtime) as the base for due_date so it
    # matches the date users expect in their configured timezone and avoids off-by-one errors.
    if getattr(sale, 'sale_date', None):
        try:
            sale_local_date = timezone.localtime(sale.sale_date).date()
        except Exception:
            # If for any reason localtime conversion fails, fall back to the naive date
            sale_local_date = sale.sale_date.date()
        due_date = sale_local_date + timedelta(days=7)
    else:
        due_date = (timezone.now().date() + timedelta(days=7))

    # Determine a sensible item/quantity for the auto-created debt
    from .models import StationeryItem, SaleItem
    sale_first_item = SaleItem.objects.filter(sale=sale).order_by('pk').first()
    if sale_first_item:
        default_item = sale_first_item.item
        default_qty = sale_first_item.quantity
    else:
        # Create or reuse a generic placeholder item for non-item-specific debts
        default_item, _ = StationeryItem.objects.get_or_create(
            sku='MISC-DEBT',
            defaults={
                'name': 'Miscellaneous Debt',
                'category': Category.objects.first() or None,
                'unit_price': Decimal('0.01'),
                'cost_price': Decimal('0.01'),
                'stock_quantity': 0,
            }
        )
        default_qty = 1

    d, created = Debt.objects.get_or_create(
        sale=sale,
        defaults={
            'customer': sale.customer,
            'item': default_item,
            'quantity': default_qty,
            'amount': sale.total_amount,
            'paid_amount': Decimal('0'),
            'due_date': due_date,
            'status': 'pending',
            'description': f'Auto-created from sale #{sale.pk}'
        }
    )
    if not created:
        # Update amount/status as needed without overwriting paid_amount
        d.customer = sale.customer
        d.amount = sale.total_amount
        # Ensure an item is present for older records
        if not d.item:
            if sale_first_item:
                d.item = sale_first_item.item
                d.quantity = sale_first_item.quantity
            else:
                d.item = default_item
                if not d.quantity:
                    d.quantity = default_qty
        if d.paid_amount >= d.amount:
            d.status = 'paid'
        elif d.paid_amount > 0:
            d.status = 'partial'
        else:
            d.status = 'pending'
        # If this debt was auto-created originally, keep due_date aligned with the sale date
        if d.description and 'Auto-created' in d.description:
            # Recompute based on local sale_date to remain consistent
            if getattr(sale, 'sale_date', None):
                try:
                    sale_local_date = timezone.localtime(sale.sale_date).date()
                except Exception:
                    sale_local_date = sale.sale_date.date()
                d.due_date = sale_local_date + timedelta(days=7)
        d.save()


@receiver(post_save, sender=SaleItem)
def update_sale_total_on_save(sender, instance, **kwargs):
    """Recompute the parent Sale.total_amount whenever a SaleItem is saved."""
    total = SaleItem.objects.filter(sale=instance.sale).aggregate(total=Sum('total_price'))['total'] or Decimal('0')
    # Use update to avoid triggering save() side-effects on Sale
    Sale.objects.filter(pk=instance.sale.pk).update(total_amount=total)
    # Fetch the up-to-date Sale instance and sync debts
    try:
        sale = Sale.objects.get(pk=instance.sale.pk)
        _sync_debt_for_sale(sale)
    except Sale.DoesNotExist:
        pass


@receiver(post_delete, sender=SaleItem)
def restore_stock_on_sale_item_delete(sender, instance, **kwargs):
    """
    Signal to restore stock when a SaleItem is deleted.
    This ensures stock is restored for bulk deletes where model.delete()
    may not be called. If the model's delete() already restored stock,
    it sets `instance._stock_restored = True` and this handler will skip.
    Additionally, recompute the parent Sale.total_amount to reflect deletion.
    """
    if getattr(instance, '_stock_restored', False):
        # Stock was already restored in the model's delete; continue to adjust totals
        pass
    else:
        # Restore stock based on product type
        if instance.product_type == 'retail' and instance.retail_item:
            instance.retail_item.stock_quantity += instance.quantity
            instance.retail_item.save(update_fields=['stock_quantity'])
        elif instance.product_type == 'wholesale' and instance.wholesale_item:
            instance.wholesale_item.cartons_in_stock += instance.quantity
            instance.wholesale_item.save(update_fields=['cartons_in_stock'])

    # Recompute the sale total if the sale still exists (it may be being deleted)
    try:
        total = SaleItem.objects.filter(sale=instance.sale).aggregate(total=Sum('total_price'))['total'] or Decimal('0')
        Sale.objects.filter(pk=instance.sale.pk).update(total_amount=total)
        # Sync debts after updating total
        try:
            sale = Sale.objects.get(pk=instance.sale.pk)
            _sync_debt_for_sale(sale)
        except Sale.DoesNotExist:
            # If sale was deleted as part of cascade, nothing to update
            pass
    except Sale.DoesNotExist:
        # If sale was deleted as part of cascade, nothing to update
        pass


@receiver(post_save, sender=Sale)
def sync_debt_on_sale_save(sender, instance, created, **kwargs):
    """Keep debts in sync when a Sale instance is saved (e.g., payment status changes)."""
    _sync_debt_for_sale(instance)

