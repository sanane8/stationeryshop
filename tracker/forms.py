from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StationeryItem, Sale, SaleItem, Debt, Payment, Customer, Category, Product, Supplier, ProductCategory
from .models import Expenditure


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProductForm(forms.ModelForm):
    sku = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Leave blank to auto-generate SKU',
            'readonly': 'readonly'
        }),
        help_text="Stock Keeping Unit (leave blank to auto-generate)"
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'sku', 'supplier', 
                 'supplier_price', 'selling_price', 'units_per_carton', 
                 'carton_weight', 'unit_type', 'cartons_in_stock', 
                 'minimum_cartons', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'supplier_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'units_per_carton': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'carton_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'cartons_in_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'minimum_cartons': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For existing products, make SKU editable
        if self.instance and self.instance.pk:
            self.fields['sku'].widget.attrs.pop('readonly', None)
            self.fields['sku'].widget.attrs.pop('placeholder', None)
            self.fields['sku'].required = True
            self.fields['sku'].help_text = "Stock Keeping Unit (unique identifier)"

    def clean_sku(self):
        """Validate SKU uniqueness"""
        sku = self.cleaned_data.get('sku')
        if sku:
            # Check if SKU already exists (excluding current instance)
            existing_products = Product.objects.filter(sku=sku)
            if self.instance and self.instance.pk:
                existing_products = existing_products.exclude(pk=self.instance.pk)
            
            if existing_products.exists():
                raise forms.ValidationError("A product with this SKU already exists.")
        
        return sku

    def save(self, commit=True):
        """Override save to create/update corresponding stationery item"""
        product = super().save(commit=False)
        
        if commit:
            product.save()
            
            # Create or update the corresponding stationery item
            if not product.stationery_item:
                product.create_stationery_item()
            
        return product


class StationeryItemForm(forms.ModelForm):
    sku = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Leave blank to auto-generate SKU',
            'readonly': 'readonly'
        }),
        help_text="Stock Keeping Unit (leave blank to auto-generate)"
    )

    class Meta:
        model = StationeryItem
        fields = ['name', 'description', 'category', 'sku', 'supplier', 
                 'unit_price', 'cost_price', 'stock_quantity', 
                 'minimum_stock', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'payment_method', 'is_paid', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}),
        }

class SaleItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default quantity to 1 for new forms
        if not self.instance.pk:
            self.fields['quantity'].initial = 1
        
        # Set up product type choices
        self.fields['product_type'].choices = [
            ('retail', '🏪 Retail Sale Product'),
            ('wholesale', '📦 Whole Sale Product'),
        ]
    
    class Meta:
        model = SaleItem
        fields = ['product_type', 'retail_item', 'wholesale_item', 'quantity', 'unit_price']
        widgets = {
            'product_type': forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleProductFields()'}),
            'retail_item': forms.Select(attrs={'class': 'form-control'}),
            'wholesale_item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get('product_type')
        retail_item = cleaned_data.get('retail_item')
        wholesale_item = cleaned_data.get('wholesale_item')
        
        if product_type == 'retail' and not retail_item:
            raise forms.ValidationError("Please select a retail sale product.")
        elif product_type == 'wholesale' and not wholesale_item:
            raise forms.ValidationError("Please select a whole sale product.")
        
        # Clear the irrelevant field
        if product_type == 'retail':
            cleaned_data['wholesale_item'] = None
        elif product_type == 'wholesale':
            cleaned_data['retail_item'] = None
        
        return cleaned_data

class DebtForm(forms.ModelForm):
    unit_prices = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate unit prices for JavaScript
        self.unit_prices = {
            str(item.pk): str(item.unit_price) 
            for item in StationeryItem.objects.filter(is_active=True)
        }
    
    class Meta:
        model = Debt
        fields = ['customer', 'sale', 'item', 'quantity', 'amount', 'due_date', 'description']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'sale': forms.Select(attrs={'class': 'form-control'}),
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.debt = kwargs.pop('debt', None)
        super().__init__(*args, **kwargs)
        
        # Set max amount attribute for client-side validation
        if self.debt:
            self.fields['amount'].widget.attrs.update({
                'max': self.debt.remaining_amount,
                'data-remaining': self.debt.remaining_amount
            })
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.debt and amount > self.debt.remaining_amount:
            raise forms.ValidationError(
                f'Payment amount cannot exceed the remaining debt amount of TZS {self.debt.remaining_amount:,.0f}'
            )
        return amount
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ExpenditureForm(forms.ModelForm):
    class Meta:
        model = Expenditure
        fields = ['description', 'amount', 'category']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        
        # Add help text placeholders
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
