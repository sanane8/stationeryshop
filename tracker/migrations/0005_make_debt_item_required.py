# Generated data migration to make Debt.item required and backfill existing debts
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def backfill_debt_items(apps, schema_editor):
    Debt = apps.get_model('tracker', 'Debt')
    SaleItem = apps.get_model('tracker', 'SaleItem')
    StationeryItem = apps.get_model('tracker', 'StationeryItem')
    Category = apps.get_model('tracker', 'Category')

    # Ensure a placeholder category and item for non-item-specific debts
    category, _ = Category.objects.get_or_create(name='Uncategorized')
    misc_item, _ = StationeryItem.objects.get_or_create(
        sku='MISC-DEBT',
        defaults={
            'name': 'Miscellaneous Debt',
            'category': category,
            'unit_price': Decimal('0.01'),
            'cost_price': Decimal('0.01'),
            'stock_quantity': 0,
        }
    )

    for d in Debt.objects.filter(item__isnull=True):
        if d.sale_id:
            si = SaleItem.objects.filter(sale_id=d.sale_id).order_by('pk').first()
            if si:
                d.item_id = si.item_id
                d.quantity = si.quantity or 1
                d.save(update_fields=['item_id', 'quantity'])
                continue
        # Fallback
        d.item = misc_item
        if not d.quantity or d.quantity <= 0:
            d.quantity = 1
        d.save(update_fields=['item', 'quantity'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_debt_item_quantity'),
    ]

    operations = [
        migrations.RunPython(backfill_debt_items, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='debt',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='debts', to='tracker.stationeryitem'),
        ),
    ]
