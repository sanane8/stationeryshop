from django.core.management.base import BaseCommand
from tracker.models import Category

class Command(BaseCommand):
    help = 'Create default categories for the stationery tracker'

    def handle(self, *args, **options):
        categories = [
            {'name': 'Pens', 'description': 'Ballpoint pens, gel pens, fountain pens'},
            {'name': 'Pencils', 'description': 'Graphite pencils, colored pencils, mechanical pencils'},
            {'name': 'Paper', 'description': 'Copy paper, notebook paper, specialty paper'},
            {'name': 'Notebooks', 'description': 'Spiral notebooks, composition books, journals'},
            {'name': 'Office Supplies', 'description': 'Staplers, paper clips, folders, binders'},
            {'name': 'Art Supplies', 'description': 'Markers, crayons, paint, brushes'},
            {'name': 'Erasers & Correctors', 'description': 'Erasers, correction tape, white-out'},
            {'name': 'Rulers & Measuring', 'description': 'Rulers, protractors, measuring tools'},
            {'name': 'Storage & Organization', 'description': 'Folders, file organizers, desk accessories'},
            {'name': 'Labels & Stickers', 'description': 'Address labels, decorative stickers, name tags'},
        ]
        
        created_count = 0
        for category_data in categories:
            category, created = Category.objects.get_or_create(
                name=category_data['name'],
                defaults={'description': category_data['description']}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created category: {category.name}')
                )
                created_count += 1
            else:
                self.stdout.write(f'- Category already exists: {category.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal categories created: {created_count}')
        )
        self.stdout.write('You can now add stationery items with these categories!')

