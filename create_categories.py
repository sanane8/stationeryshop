#!/usr/bin/env python
"""
Script to create default categories for the stationery tracker
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stationery_tracker.settings')
django.setup()

from tracker.models import Category

def create_default_categories():
    """Create default categories for the stationery tracker"""
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
            print(f"✓ Created category: {category.name}")
            created_count += 1
        else:
            print(f"- Category already exists: {category.name}")
    
    print(f"\nTotal categories created: {created_count}")
    print("You can now add stationery items with these categories!")

if __name__ == "__main__":
    create_default_categories()

