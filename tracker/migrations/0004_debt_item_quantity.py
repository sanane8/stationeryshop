# Generated migration to add item and quantity to Debt model
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_expenditure'),
    ]

    operations = [
        migrations.AddField(
            model_name='debt',
            name='item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='debts', to='tracker.stationeryitem'),
        ),
        migrations.AddField(
            model_name='debt',
            name='quantity',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
