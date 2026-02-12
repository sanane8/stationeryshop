from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from tracker.models import Debt

class Command(BaseCommand):
    help = 'Backfill and correct due_date for auto-created debts based on their sale.sale_date (local time)'

    def handle(self, *args, **options):
        qs = Debt.objects.filter(description__icontains='Auto-created').select_related('sale')
        updated = 0
        total = qs.count()
        for d in qs:
            if not d.sale:
                continue
            sale = d.sale
            if getattr(sale, 'sale_date', None):
                try:
                    sale_local_date = timezone.localtime(sale.sale_date).date()
                except Exception:
                    sale_local_date = sale.sale_date.date()
                expected = sale_local_date + timedelta(days=7)
            else:
                expected = (timezone.now().date() + timedelta(days=7))

            if d.due_date != expected:
                d.due_date = expected
                d.save(update_fields=['due_date'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Processed {total} auto-created debts, updated {updated} due_date(s).'))
