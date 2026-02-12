from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Supplier(models.Model):
    """Supplier information for products"""
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    """Product category for organizing products"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Product Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    """Category for stationery items"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model for items sold in cartons"""
    UNIT_CHOICES = [
        ('carton', 'Carton'),
        ('piece', 'Piece'),
        ('box', 'Box'),
        ('pack', 'Pack'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    stationery_item = models.OneToOneField('StationeryItem', on_delete=models.CASCADE, related_name='product', blank=True, null=True, help_text="Link to corresponding stationery item")
    
    # Pricing
    supplier_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], help_text="Price from supplier")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Carton information
    units_per_carton = models.PositiveIntegerField(default=1, help_text="Number of units in one carton")
    carton_weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Weight per carton (kg)")
    unit_type = models.CharField(max_length=10, choices=UNIT_CHOICES, default='carton')
    
    # Stock
    cartons_in_stock = models.PositiveIntegerField(default=0, help_text="Number of cartons in stock")
    minimum_cartons = models.PositiveIntegerField(default=0, help_text="Minimum cartons before reorder")
    
    # Additional info
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def total_units_in_stock(self):
        """Calculate total units in stock"""
        return self.cartons_in_stock * self.units_per_carton

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.supplier_price > 0:
            return ((self.selling_price - self.supplier_price) / self.supplier_price) * 100
        return 0

    @property
    def profit_per_carton(self):
        """Calculate profit per carton"""
        return self.selling_price - self.supplier_price

    @property
    def is_low_stock(self):
        """Check if product is below minimum stock level"""
        return self.cartons_in_stock <= self.minimum_cartons

    def get_total_value(self):
        """Get total value of current stock"""
        return self.cartons_in_stock * self.selling_price

    def save(self, *args, **kwargs):
        """Override save to sync with StationeryItem and generate SKU if needed"""
        # Generate SKU if not provided
        if not self.sku:
            self.sku = self.generate_sku()
        
        super().save(*args, **kwargs)
        self.sync_with_stationery_item()

    def generate_sku(self):
        """Generate automatic SKU based on product name and category"""
        import re
        import datetime
        
        # Get category abbreviation
        category_abbr = ""
        if self.category:
            # Take first 3 letters of category name, remove spaces/special chars
            category_abbr = re.sub(r'[^A-Za-z0-9]', '', self.category.name)[:3].upper()
        
        # Take first 3 letters of product name, remove spaces/special chars
        name_abbr = re.sub(r'[^A-Za-z0-9]', '', self.name)[:3].upper()
        
        # Get current year last 2 digits
        year_suffix = str(datetime.datetime.now().year)[-2:]
        
        # Get sequential number for today
        today = datetime.datetime.now().date()
        count_today = Product.objects.filter(
            created_at__date=today
        ).count()
        
        # Generate sequential number (3 digits, padded with zeros)
        sequential = str(count_today + 1).zfill(3)
        
        # Combine: CATEGORY-NAME-YEAR-SEQUENTIAL
        sku = f"{category_abbr}-{name_abbr}-{year_suffix}-{sequential}"
        
        # Ensure uniqueness
        original_sku = sku
        counter = 1
        while Product.objects.filter(sku=sku).exists():
            sku = f"{original_sku}-{counter}"
            counter += 1
        
        return sku

    def sync_with_stationery_item(self):
        """Sync product stock with corresponding stationery item"""
        if self.stationery_item:
            # Only update the stock quantity, not pricing
            self.stationery_item.stock_quantity = self.total_units_in_stock
            # Keep existing pricing in stationery item
            self.stationery_item.save()

    def create_stationery_item(self):
        """Create a corresponding stationery item for this product"""
        if not self.stationery_item:
            # Use the same category for the stationery item
            stationery_category = self.category
            
            # Create the stationery item with default pricing (user can update later)
            stationery_item = StationeryItem.objects.create(
                name=self.name,
                description=self.description,
                category=stationery_category,
                sku=self.sku,
                unit_price=self.selling_price,  # Initial value, user can change
                cost_price=self.supplier_price,  # Initial value, user can change
                stock_quantity=self.total_units_in_stock,
                minimum_stock=self.minimum_cartons * self.units_per_carton,  # Convert to units
                supplier=self.supplier.name,
                is_active=self.is_active
            )
            self.stationery_item = stationery_item
            self.save()


class StationeryItem(models.Model):
    """Model for stationery items/commodities"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock_quantity = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0, help_text="Minimum stock level before reorder")
    supplier = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.unit_price - self.cost_price) / self.cost_price) * 100
        return 0

    @property
    def is_low_stock(self):
        """Check if item is below minimum stock level"""
        return self.stock_quantity <= self.minimum_stock

    def get_total_value(self):
        """Get total value of current stock"""
        return self.stock_quantity * self.unit_price

    def generate_sku(self):
        """Generate automatic SKU based on product name and category"""
        import re
        import datetime
        
        # Get category abbreviation
        category_abbr = ""
        if self.category:
            # Take first 3 letters of category name, remove spaces/special chars
            category_abbr = re.sub(r'[^A-Za-z0-9]', '', self.category.name)[:3].upper()
        
        # Take first 3 letters of product name, remove spaces/special chars
        name_abbr = re.sub(r'[^A-Za-z0-9]', '', self.name)[:3].upper()
        
        # Get current year last 2 digits
        year_suffix = str(datetime.datetime.now().year)[-2:]
        
        # Get sequential number for today
        today = datetime.datetime.now().date()
        count_today = StationeryItem.objects.filter(
            created_at__date=today
        ).count()
        
        # Generate sequential number (3 digits, padded with zeros)
        sequential = str(count_today + 1).zfill(3)
        
        # Combine: CATEGORY-NAME-YEAR-SEQUENTIAL
        sku = f"{category_abbr}-{name_abbr}-{year_suffix}-{sequential}"
        
        # Ensure uniqueness
        original_sku = sku
        counter = 1
        while StationeryItem.objects.filter(sku=sku).exists():
            sku = f"{original_sku}-{counter}"
            counter += 1
        
        return sku

    def save(self, *args, **kwargs):
        """Override save to generate SKU if needed"""
        # Generate SKU if not provided
        if not self.sku:
            self.sku = self.generate_sku()
        
        super().save(*args, **kwargs)


class Customer(models.Model):
    """Customer information"""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Sale(models.Model):
    """Sales transaction model"""
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(Decimal('0.00'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    is_paid = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-sale_date']

    def __str__(self):
        return f"Sale #{self.id} - {self.customer or 'Walk-in'} - TZS {self.total_amount:,.0f}"

    @property
    def profit(self):
        """Calculate total profit for this sale.

        If the sale has line items, profit = revenue - cost of goods sold.
        If the sale has no items and appears to be a payment for a Debt, compute a
        proportional profit based on the originating sale (if any). For example,
        a partial payment for a debt created from a sale will carry the same
        fraction of the original sale's profit.
        """
        # Normal case: sale with items
        items = list(self.items.all())
        if items:
            total_cost = sum(
                (item.retail_item.cost_price if item.product_type == 'retail' and item.retail_item else Decimal('0')) * item.quantity 
                for item in items
            )
            return self.total_amount - total_cost

        # Payment-sale case: try to infer associated debt and originating sale
        notes = (self.notes or '')
        import re
        m = re.search(r'Payment for Debt #(?P<debt_id>\d+)', notes)
        if m:
            from .models import Debt
            debt_id = int(m.group('debt_id'))
            try:
                debt = Debt.objects.get(pk=debt_id)
            except Debt.DoesNotExist:
                return self.total_amount

            # If debt points to an originating sale (the sale that created the debt), use it
            orig_sale = None
            if debt.sale and debt.sale.pk != self.pk:
                orig_sale = debt.sale

            # If we have an originating sale with calculable profit, allocate proportionally
            try:
                if orig_sale:
                    orig_profit = orig_sale.profit
                    if debt.amount and debt.amount > 0:
                        ratio = (self.total_amount / debt.amount)
                        return (orig_profit * ratio)
                # If there is no originating sale but the debt references an item/quantity
                # (i.e., manually created debt), compute the original profit as (debt.amount - total_cost)
                # where total_cost = item.cost_price * quantity, and allocate proportionally.
                if debt.item and debt.amount and debt.amount > 0:
                    total_cost = (debt.item.cost_price or Decimal('0.00')) * (debt.quantity or 1)
                    orig_profit = debt.amount - total_cost
                    ratio = (self.total_amount / debt.amount)
                    return (orig_profit * ratio)
            except Exception:
                # fall back to returning revenue if anything goes wrong
                return self.total_amount

        # Fallback for payments without originating sale: no cost information -> profit undefined
        # Treat profit as 0 to avoid overstating profit for a pure cash receipt with no COGS
        return Decimal('0')


class SaleItem(models.Model):
    """Individual items in a sale"""
    PRODUCT_TYPE_CHOICES = [
        ('retail', 'Retail Sale Product'),
        ('wholesale', 'Whole Sale Product'),
    ]
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default='retail')
    retail_item = models.ForeignKey(StationeryItem, on_delete=models.CASCADE, null=True, blank=True, related_name='retail_sale_items')
    wholesale_item = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='wholesale_sale_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sale', 'retail_item'], condition=models.Q(product_type='retail'), name='unique_retail_sale_item'),
            models.UniqueConstraint(fields=['sale', 'wholesale_item'], condition=models.Q(product_type='wholesale'), name='unique_wholesale_sale_item'),
        ]

    def __str__(self):
        if self.product_type == 'retail' and self.retail_item:
            return f"{self.retail_item.name} x {self.quantity} = TZS {self.total_price:,.0f}"
        elif self.product_type == 'wholesale' and self.wholesale_item:
            return f"{self.wholesale_item.name} x {self.quantity} = TZS {self.total_price:,.0f}"
        return f"Item x {self.quantity} = TZS {self.total_price:,.0f}"

    @property
    def item(self):
        """Get the appropriate item based on product type"""
        if self.product_type == 'retail':
            return self.retail_item
        elif self.product_type == 'wholesale':
            return self.wholesale_item
        return None

    @property
    def item_name(self):
        """Get the item name for display"""
        if self.product_type == 'retail' and self.retail_item:
            return self.retail_item.name
        elif self.product_type == 'wholesale' and self.wholesale_item:
            return self.wholesale_item.name
        return "Unknown Item"

    @property
    def item_sku(self):
        """Get the item SKU for display"""
        if self.product_type == 'retail' and self.retail_item:
            return self.retail_item.sku
        elif self.product_type == 'wholesale' and self.wholesale_item:
            return self.wholesale_item.sku
        return ""

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        
        # Handle stock reduction
        is_new = self.pk is None
        
        if is_new:
            # New sale item - reduce stock
            if self.product_type == 'retail' and self.retail_item:
                if self.retail_item.stock_quantity < self.quantity:
                    raise ValueError(f'Insufficient stock for {self.retail_item.name}. Available: {self.retail_item.stock_quantity}, Requested: {self.quantity}')
                self.retail_item.stock_quantity -= self.quantity
                self.retail_item.save()
            elif self.product_type == 'wholesale' and self.wholesale_item:
                if self.wholesale_item.cartons_in_stock < self.quantity:
                    raise ValueError(f'Insufficient stock for {self.wholesale_item.name}. Available: {self.wholesale_item.cartons_in_stock}, Requested: {self.quantity}')
                self.wholesale_item.cartons_in_stock -= self.quantity
                self.wholesale_item.save()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Restore stock when sale item is deleted
        if self.product_type == 'retail' and self.retail_item:
            self.retail_item.stock_quantity += self.quantity
            self.retail_item.save()
        elif self.product_type == 'wholesale' and self.wholesale_item:
            self.wholesale_item.cartons_in_stock += self.quantity
            self.wholesale_item.save()
        
        super().delete(*args, **kwargs)


class Debt(models.Model):
    """Debt tracking model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='debts')
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, related_name='debts', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    # Link to an item and the quantity owed (required for all debts)
    # Use PROTECT to avoid accidental deletion of items referenced by debts
    item = models.ForeignKey(StationeryItem, on_delete=models.PROTECT, related_name='debts')
    quantity = models.PositiveIntegerField(default=1)

    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.name} - TZS {self.amount:,.0f} ({self.status})"

    @property
    def remaining_amount(self):
        return self.amount - self.paid_amount

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status != 'paid'


class Payment(models.Model):
    """Payment records for debts"""
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=Sale.PAYMENT_CHOICES, default='cash')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of TZS {self.amount:,.0f} for {self.debt.customer.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update debt status
        self.debt.paid_amount += self.amount
        if self.debt.paid_amount >= self.debt.amount:
            self.debt.status = 'paid'
        elif self.debt.paid_amount > 0:
            self.debt.status = 'partial'
        # Use update_fields to avoid triggering unnecessary signals/cascades
        self.debt.save(update_fields=['paid_amount', 'status'])


class Expenditure(models.Model):
    """Track business expenditures (money going out)."""
    CATEGORY_CHOICES = [
        ('supplies', 'Supplies'),
        ('rent', 'Rent'),
        ('utilities', 'Utilities'),
        ('salary', 'Salary'),
        ('marketing', 'Marketing'),
        ('other', 'Other'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    expense_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.get_category_display()} - TZS {self.amount:,.0f} on {self.expense_date.date()}"
