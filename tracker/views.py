from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db import transaction
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper, Exists, OuterRef, Case, When, Value, BooleanField
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .models import StationeryItem, Sale, SaleItem, Debt, Customer, Category, Product, Supplier
from .forms import SaleForm, SaleItemForm, DebtForm, PaymentForm, StationeryItemForm, CustomerForm, LoginForm, RegistrationForm, ProductForm, SupplierForm
from django.contrib.auth import authenticate, login

from .forms import ExpenditureForm
from .models import Expenditure
import csv
import logging
from django.http import HttpResponse
from io import BytesIO
import json

logger = logging.getLogger(__name__)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


@login_required
def product_list(request):
    """Display all products with supplier pricing and carton information"""
    products = Product.objects.select_related('category', 'supplier').filter(is_active=True)
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by supplier
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(supplier__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = Category.objects.all()
    suppliers = Supplier.objects.filter(is_active=True)
    
    # Calculate statistics
    total_products = products.count()
    low_stock_products = products.filter(cartons_in_stock__lte=models.F('minimum_cartons')).count()
    total_stock_value = sum(product.get_total_value() for product in products)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'suppliers': suppliers,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_stock_value': total_stock_value,
        'search_query': search_query or '',
        'selected_category': category_id or '',
        'selected_supplier': supplier_id or '',
    }
    
    return render(request, 'tracker/product_list.html', context)


@login_required
def product_detail(request, pk):
    """Display detailed product information"""
    product = get_object_or_404(Product, pk=pk)
    
    # Get recent sales for this product (only wholesale sales)
    recent_sales = Sale.objects.filter(
        items__wholesale_item=product
    ).order_by('-sale_date')[:10]
    
    context = {
        'product': product,
        'recent_sales': recent_sales,
    }
    
    return render(request, 'tracker/product_detail.html', context)


@login_required
def product_create(request):
    """Create a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" has been created successfully.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm()
    
    return render(request, 'tracker/product_form.html', {
        'form': form,
        'title': 'Create Whole Sale Product',
    })


@login_required
def product_update(request, pk):
    """Update an existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Whole sale product "{product.name}" has been updated successfully.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'tracker/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Update Whole Sale Product',
    })


@login_required
def supplier_list(request):
    """Display all suppliers"""
    suppliers = Supplier.objects.filter(is_active=True)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Calculate statistics
    total_suppliers = suppliers.count()
    total_products = sum(supplier.products.count() for supplier in suppliers)
    
    context = {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers,
        'total_products': total_products,
        'search_query': search_query or '',
    }
    
    return render(request, 'tracker/supplier_list.html', context)


@login_required
def supplier_create(request):
    """Create a new supplier"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" has been created successfully.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'tracker/supplier_form.html', {
        'form': form,
        'title': 'Create Supplier',
    })


@login_required
def supplier_update(request, pk):
    """Update an existing supplier"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" has been updated successfully.')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'tracker/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': 'Update Supplier',
    })


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'tracker/login.html', {'form': form})


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
    
    return render(request, 'tracker/register.html', {'form': form})

@login_required
def dashboard(request):

    """Main dashboard view"""
    # Get recent **paid** sales (exclude unpaid sales and sales with no items)
    recent_sales = (
        Sale.objects.select_related('customer')
        .prefetch_related('items__retail_item', 'items__wholesale_item')
        .annotate(item_count=Count('items'))
        .filter(is_paid=True, item_count__gt=0)
        .order_by('-sale_date')[:10]
    )

    # Get low stock items
    low_stock_items = StationeryItem.objects.filter(
        stock_quantity__lte=models.F('minimum_stock'),
        is_active=True
    )
    
    # Get overdue debts
    overdue_debts = Debt.objects.filter(
        due_date__lt=timezone.now().date(),
        status__in=['pending', 'partial']
    ).select_related('customer')
    
    # Calculate totals for today using timezone-aware range to avoid date-boundary issues
    now_local = timezone.localtime(timezone.now())
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    # Exclude unpaid sales from today's totals
    today_sales = Sale.objects.filter(sale_date__gte=today_start, sale_date__lt=today_end, is_paid=True).aggregate(
        total_sales=Sum('total_amount'),
        count_sales=Count('id')
    )

    # Today's expenditures (used to compute net sales)
    exp_today = Expenditure.objects.filter(expense_date__gte=today_start, expense_date__lt=today_end).aggregate(
        total=Sum('amount'), count=Count('id')
    )

    # Compute net today's sales (sales minus today's expenditures)
    today_total = today_sales.get('total_sales') or 0
    today_exp = exp_today.get('total') or 0
    net_today_sales = today_total - today_exp

    # Calculate monthly totals using local timezone month range (exclude unpaid sales)
    month_start = today_start.replace(day=1)
    # find start of next month
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    monthly_sales = Sale.objects.filter(sale_date__gte=month_start, sale_date__lt=next_month, is_paid=True).aggregate(
        total_sales=Sum('total_amount'),
        count_sales=Count('id')
    )

    exp_month = Expenditure.objects.filter(expense_date__gte=month_start, expense_date__lt=next_month).aggregate(
        total=Sum('amount'), count=Count('id')
    )
    month_total = monthly_sales.get('total_sales') or 0
    month_exp = exp_month.get('total') or 0
    net_monthly_sales = month_total - month_exp
    
    # Get total outstanding debt
    total_debt = Debt.objects.filter(status__in=['pending', 'partial']).aggregate(
        total=Sum('amount') - Sum('paid_amount')
    )['total'] or 0
    
    context = {
        'recent_sales': recent_sales,
        'low_stock_items': low_stock_items,
        'overdue_debts': overdue_debts,
        'today_sales': today_sales,
        'monthly_sales': monthly_sales,
        'total_debt': total_debt,
        'exp_today': exp_today,
        'exp_month': exp_month,
        'net_today_sales': net_today_sales,
        'net_monthly_sales': net_monthly_sales,
    }
    
    return render(request, 'tracker/dashboard.html', context)


@login_required
def stationery_list(request):
    """List all stationery items"""
    # Include active items and any legacy items where is_active might be null
    # Start from all items; we'll restrict to active-only unless 'inactive' toggle is set
    items = StationeryItem.objects.select_related('category').all()

    # Filter by category if specified
    category_id = request.GET.get('category')
    if category_id:
        items = items.filter(category_id=category_id)

    # Search functionality (apply before computing counts so counts reflect the current scope)
    raw_search = request.GET.get('search')
    if raw_search and raw_search.strip().lower() != 'none':
        search_query = raw_search.strip()
        items = items.filter(
            Q(name__icontains=search_query) | 
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    else:
        search_query = ''

    # Low-stock and inactive filters
    low_stock_flag = request.GET.get('low_stock')
    inactive_flag = request.GET.get('inactive')

    selected_low_stock = False
    selected_inactive = False

    # By default, show only active items; if inactive checkbox is set, we'll defer filtering until after counts
    if inactive_flag in (None, '', 'None'):
        items = items.filter(Q(is_active=True) | Q(is_active__isnull=True))
    else:
        selected_inactive = True

    # Compute counts in the current search/category scope (respecting the default active/inactive selection)
    low_stock_count = items.filter(stock_quantity__lte=models.F('minimum_stock')).count()
    inactive_count = items.filter(is_active=False).count()

    if low_stock_flag not in (None, '', 'None'):
        selected_low_stock = True
        items = items.filter(stock_quantity__lte=models.F('minimum_stock'))

    # If inactive checkbox is explicitly selected, show only inactive items
    if selected_inactive:
        items = items.filter(is_active=False)
    
    categories = Category.objects.all()
    
    # Calculate statistics (similar to product_list)
    total_products = items.count()
    low_stock_products = items.filter(stock_quantity__lte=models.F('minimum_stock')).count()
    total_stock_value = sum(item.get_total_value() for item in items)
    
    # Paginate
    page = request.GET.get('page')
    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(page)

    context = {
        'items': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'paginator': paginator,
        'page_obj': page_obj,
        'selected_low_stock': selected_low_stock,
        'low_stock_count': low_stock_count,
        'selected_inactive': selected_inactive,
        'inactive_count': inactive_count,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_stock_value': total_stock_value,
    }
    
    return render(request, 'tracker/stationery_list.html', context)


@login_required
def stationery_detail(request, pk):
    """Detail view for a stationery item"""
    item = get_object_or_404(StationeryItem, pk=pk)
    
    # Get recent sales for this stationery item (only retail sales)
    recent_sales = Sale.objects.filter(
        items__retail_item=item
    ).order_by('-sale_date')[:10]
    
    context = {
        'item': item,
        'recent_sales': recent_sales,
    }
    
    return render(request, 'tracker/stationery_detail.html', context)


@login_required
def sales_list(request):
    """List all sales"""
    # Show all sales including payment-related sales (those without items)
    # Payment sales are stored as sales with no items but notes like 'Payment for Debt #<id>'
    sales = Sale.objects.select_related('customer', 'created_by').prefetch_related('items__retail_item', 'items__wholesale_item').annotate(
        item_count=Count('items')
    ).filter(
        Q(item_count__gt=0) | Q(notes__contains='Payment for Debt')
    ).order_by('-sale_date')
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    # guard against literal 'None' or empty strings passed from templates
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    
    # Filter by payment status
    raw_payment_status = request.GET.get('payment_status')
    if raw_payment_status in (None, '', 'None'):
        # No explicit filter provided by user; default to showing paid sales
        payment_status = 'paid'
        payment_status_explicit = False
    else:
        payment_status = raw_payment_status
        payment_status_explicit = True

    if payment_status == 'paid':
        sales = sales.filter(is_paid=True)
    elif payment_status == 'unpaid':
        sales = sales.filter(is_paid=False)

    elif payment_status == 'all':
        # explicit request to include all sales
        pass

    # Filter by product (items sold): sales that contain at least one item whose name matches
    product_search = request.GET.get('product') or request.GET.get('search_product')
    if product_search in (None, '', 'None'):
        product_search = None
    else:
        product_search = str(product_search).strip() or None
    if product_search:
        has_product = SaleItem.objects.filter(
            sale=OuterRef('pk')
        ).filter(
            Q(retail_item__name__icontains=product_search) |
            Q(wholesale_item__name__icontains=product_search)
        )
        sales = sales.filter(Exists(has_product))

    # Paginate before converting to list
    page = request.GET.get('page')
    paginator = Paginator(sales, 20)
    page_obj = paginator.get_page(page)

    # Annotate per-sale total_cost and profit to avoid N+1 queries in template
    # We'll calculate this in Python instead of using complex annotations
    for sale in page_obj.object_list:
        # Calculate total cost for this sale
        total_cost = Decimal('0')
        for item in sale.items.all():
            if item.product_type == 'retail' and item.retail_item:
                total_cost += item.quantity * (item.retail_item.cost_price or Decimal('0'))
        sale.total_cost = total_cost
        sale.annotated_profit = sale.total_amount - total_cost

    # Compute total expenditures for the same filter window (if date filters applied)
    exp_qs = Expenditure.objects.all()
    if start_date:
        exp_qs = exp_qs.filter(expense_date__date__gte=start_date)
    if end_date:
        exp_qs = exp_qs.filter(expense_date__date__lte=end_date)
    total_expenditure = exp_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Calculate total amount and overall profit for filtered sales (using full queryset)
    # We need to get the full queryset without pagination for totals
    # Reset the queryset to get all results for calculations
    sales_queryset = sales
    total_amount = sum(sale.total_amount or Decimal('0') for sale in sales_queryset)
    
    # Calculate costs for all sales
    overall_cost = Decimal('0')
    for sale in sales_queryset:
        sale_cost = Decimal('0')
        for item in sale.items.all():
            if item.product_type == 'retail' and item.retail_item:
                sale_cost += item.quantity * (item.retail_item.cost_price or Decimal('0'))
        sale.total_cost = sale_cost  # Store for daily aggregates
        overall_cost += sale_cost
    
    overall_profit = total_amount - overall_cost

    # Calculate daily aggregates (local timezone-aware) for the filtered sales.
    # We group sales by their *local* date (timezone.localtime(sale.sale_date).date()) so
    # daily buckets match what's shown in the dashboard and templates.
    daily_map = {}
    
    product_search_lower = (product_search or '').lower()

    for sale in sales_queryset:
        local_date = timezone.localtime(sale.sale_date).date()
        rev = sale.total_amount or Decimal('0')
        cost = getattr(sale, 'total_cost', Decimal('0'))

        entry = daily_map.setdefault(local_date, {
            'revenue': Decimal('0'), 'cost': Decimal('0'), 'count': 0,
            'product_qty': 0, 'product_revenue': Decimal('0'), 'product_cost': Decimal('0'),
            'product_names': set(),
        })
        entry['revenue'] += rev
        entry['cost'] += cost
        entry['count'] += 1

        # Product-specific aggregation
        if product_search_lower:
            matching_item_revenue = Decimal('0')
            matching_item_cost = Decimal('0')
            for si in sale.items.all():
                item_name = si.item_name.lower()
                if product_search_lower in item_name:
                    entry['product_qty'] += si.quantity
                    # Calculate the actual revenue and cost for this specific item
                    item_revenue = si.total_price or Decimal('0')
                    matching_item_revenue += item_revenue
                    
                    # Calculate cost for this specific item
                    item_cost = Decimal('0')
                    if si.product_type == 'retail' and si.retail_item:
                        item_cost = si.quantity * (si.retail_item.cost_price or Decimal('0'))
                    matching_item_cost += item_cost
                    
                    entry['product_names'].add(si.item_name)
            
            # Add only the matching item revenue and cost
            entry['product_revenue'] += matching_item_revenue
            entry['product_cost'] += matching_item_cost

    # Convert map into sorted list (newest date first)
    daily_sales = []
    for date_key in sorted(daily_map.keys(), reverse=True):
        data = daily_map[date_key]
        exp_for_date = Expenditure.objects.filter(expense_date__date=date_key).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if product_search:
            # Product filter: Total Sold = revenue from matching items only; Profit = that revenue − cost of those items.
            # Qty and Total Sold are then from the same line items (mathematically consistent).
            revenue = data.get('product_revenue') or Decimal('0')
            cost = data.get('product_cost') or Decimal('0')
            profit = revenue - cost
        else:
            net_revenue = data['revenue'] - (exp_for_date or Decimal('0'))
            revenue = net_revenue
            cost = data['cost']
            profit = net_revenue - cost
        product_names = data.get('product_names') or set()
        daily_sales.append({
            'date': date_key,
            'revenue': revenue,
            'cost': cost,
            'expenditure': exp_for_date,
            'profit': profit,
            'count': data['count'],
            'product_qty': data.get('product_qty', 0),
            'product_names': sorted(product_names),
        })

    # By default (when no filters applied) show only the most recent two days
    # Use `payment_status_explicit` to detect whether user provided a filter;
    # if not provided, we treat the page as having no user filters and shorten the summary.
    if not (start_date or end_date or (locals().get('payment_status_explicit', False)) or product_search):
        daily_sales = daily_sales[:2]

    # Totals for daily summary (sum of Total Sold and Profit columns); respect date filters.
    daily_summary_total_sold = sum(d['revenue'] for d in daily_sales)
    daily_summary_total_profit = sum(d['profit'] for d in daily_sales)
    daily_summary_total_product_qty = sum(d.get('product_qty', 0) for d in daily_sales)
    
    # Ensure payment-sales (which have no SaleItem rows) display a sensible profit
    # annotated_profit may be NULL for such rows; compute from model property in Python
    for sale in page_obj.object_list:
        if getattr(sale, 'annotated_profit', None) is None:
            try:
                sale.annotated_profit = sale.profit
            except Exception:
                sale.annotated_profit = Decimal('0')
        # Build a products string for display on the sales list for payment-only sales
        try:
            sale_items = list(sale.items.select_related('retail_item', 'wholesale_item').all())
        except Exception:
            sale_items = []

        products_list = []
        if sale_items:
            for si in sale_items:
                products_list.append(f"{si.item_name} ({si.quantity})")
        else:
            import re
            m = re.search(r'Payment for Debt #(\d+)', (sale.notes or ''))
            if m:
                try:
                    debt = Debt.objects.select_related('item', 'sale').get(pk=int(m.group(1)))
                    if debt.sale and debt.sale.items.exists():
                        for si in debt.sale.items.select_related('retail_item', 'wholesale_item').all():
                            products_list.append(f"{si.item_name} ({si.quantity})")
                    elif debt.item:
                        products_list.append(f"{debt.item.name} ({debt.quantity})")
                except Debt.DoesNotExist:
                    pass

        sale.products = ', '.join(products_list) if products_list else None

        # Determine a display name for the 'Created By' column. For payment-only
        # sales that reference a Debt, prefer the original sale's creator if available.
        created_by_name = None
        if sale.created_by:
            try:
                created_by_name = sale.created_by.get_full_name() or sale.created_by.username
            except Exception:
                try:
                    created_by_name = sale.created_by.username
                except Exception:
                    created_by_name = None

        if not created_by_name:
            # If this is a payment-sale, try to infer creator from the originating debt/sale
            import re
            m2 = re.search(r'Payment for Debt #(\d+)', (sale.notes or ''))
            if m2:
                try:
                    debt = Debt.objects.select_related('sale__created_by').get(pk=int(m2.group(1)))
                    if debt.sale and debt.sale.created_by:
                        try:
                            created_by_name = debt.sale.created_by.get_full_name() or debt.sale.created_by.username
                        except Exception:
                            created_by_name = getattr(debt.sale.created_by, 'username', None)
                except Debt.DoesNotExist:
                    pass

        sale.created_by_display = created_by_name

    context = {
        'sales': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'payment_status': payment_status,
        'product_search': product_search or '',
        'total_amount': total_amount,
        'total_expenditure': total_expenditure,
        'daily_sales': daily_sales,
        'daily_summary_total_sold': daily_summary_total_sold,
        'daily_summary_total_profit': daily_summary_total_profit,
        'daily_summary_total_product_qty': daily_summary_total_product_qty,
        'overall_profit': overall_profit,
        'paginator': paginator,
        'page_obj': page_obj,
    }
    
    return render(request, 'tracker/sales_list.html', context)


@login_required
def sale_detail(request, pk):
    """Detail view for a sale"""
    sale = get_object_or_404(Sale, pk=pk)
    sale_items = sale.items.select_related('retail_item', 'wholesale_item')
    
    context = {
        'sale': sale,
        'sale_items': sale_items,
    }
    
    return render(request, 'tracker/sale_detail.html', context)


@login_required
def print_invoice(request, pk):
    """Render a printable invoice for a single sale."""
    sale = get_object_or_404(Sale, pk=pk)
    sale_items = sale.items.select_related('retail_item', 'wholesale_item')

    # Calculate totals and cost
    try:
        total_cost = sum((si.quantity * (si.retail_item.cost_price if si.product_type == 'retail' and si.retail_item else Decimal('0'))) for si in sale_items)
    except Exception:
        total_cost = Decimal('0')
    revenue = sale.total_amount or Decimal('0')
    profit = revenue - (total_cost or Decimal('0'))

    context = {
        'sale': sale,
        'sale_items': sale_items,
        'total_cost': total_cost,
        'revenue': revenue,
        'profit': profit,
    }

    return render(request, 'tracker/sale_invoice.html', context)

@login_required
def create_sale(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.created_by = request.user
            sale.save()
            messages.success(request, 'Sale created successfully.')
            return redirect('sale_detail', pk=sale.pk)
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = SaleForm()
    return render(request, 'tracker/sale_form.html', {'form': form})



@login_required
def sales_chart(request):
    """Graphical representation of sales"""
    # Get sales data for chart
    sales = Sale.objects.filter(is_paid=True).order_by('sale_date')
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    
    # Group by date
    from django.db.models.functions import TruncDate
    daily_sales = sales.annotate(date=TruncDate('sale_date')).values('date').annotate(
        total=Sum('total_amount')
    ).order_by('date')
    
    # Prepare data for Chart.js
    labels = [item['date'].strftime('%Y-%m-%d') for item in daily_sales]
    data = [float(item['total']) for item in daily_sales]
    
    context = {
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'tracker/sales_chart.html', context)


@login_required
def sales_daily_export_csv(request):
    """Export daily sales summary (respecting same filters) as CSV."""
    sales = Sale.objects.select_related('customer', 'created_by').order_by('-sale_date')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_status = request.GET.get('payment_status')
    # guard against literal 'None' or empty strings
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    if payment_status in (None, '', 'None'):
        payment_status = None

    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if payment_status == 'paid':
        sales = sales.filter(is_paid=True)
    elif payment_status == 'unpaid':
        sales = sales.filter(is_paid=False)

    product_search = request.GET.get('product') or request.GET.get('search_product')
    if product_search not in (None, '', 'None') and str(product_search).strip():
        product_search = str(product_search).strip()
        has_product = SaleItem.objects.filter(
            sale=OuterRef('pk'),
            retail_item__name__icontains=product_search,
        ) | SaleItem.objects.filter(
            sale=OuterRef('pk'),
            wholesale_item__name__icontains=product_search,
        )
        sales = sales.filter(Exists(has_product))

    # Export all matching sales (row per sale) as CSV
    sales = sales.select_related('customer').prefetch_related('items__retail_item', 'items__wholesale_item')

    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="all_sales.csv"'
        writer = csv.writer(response)
        # Header
        writer.writerow(['Sale ID', 'Date', 'Customer', 'Amount', 'Profit', 'Payment Method', 'Status', 'Created By'])

        for sale in sales:
            # compute total cost for the sale
            try:
                total_cost = sum((si.quantity * (si.item.cost_price or Decimal('0'))) for si in sale.items.all())
            except Exception:
                total_cost = Decimal('0')
            revenue = sale.total_amount or Decimal('0')
            # If sale has items, profit is revenue - total_cost; otherwise, try to use Sale.profit
            if sale.items.exists():
                profit = revenue - (total_cost or Decimal('0'))
            else:
                try:
                    profit = sale.profit
                except Exception:
                    profit = Decimal('0')

            # format
            try:
                date_str = timezone.localtime(sale.sale_date).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                date_str = str(sale.sale_date)

            created_by = sale.created_by.get_full_name() if sale.created_by else ''
            customer = sale.customer.name if sale.customer else 'Walk-in'

            amount_str = format(revenue, ',.0f')
            profit_str = format(profit, ',.0f')

            writer.writerow([
                sale.id,
                date_str,
                customer,
                amount_str,
                profit_str,
                sale.get_payment_method_display(),
                'Paid' if sale.is_paid else 'Unpaid',
                created_by,
            ])

        return response
    except Exception:
        messages.error(request, 'Failed to export sales CSV. Please try again.')
        return redirect('sales_list')


@login_required
def sales_daily_export_pdf(request):
    """Export daily sales summary as PDF using ReportLab."""
    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'PDF export requires the ReportLab package. Install it with `pip install reportlab`.')
        return redirect('sales_list')

    sales = Sale.objects.select_related('customer', 'created_by').order_by('-sale_date')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_status = request.GET.get('payment_status')
    # guard against literal 'None' or empty strings
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    if payment_status in (None, '', 'None'):
        payment_status = None

    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if payment_status == 'paid':
        sales = sales.filter(is_paid=True)
    elif payment_status == 'unpaid':
        sales = sales.filter(is_paid=False)

    product_search = request.GET.get('product') or request.GET.get('search_product')
    if product_search not in (None, '', 'None') and str(product_search).strip():
        product_search = str(product_search).strip()
        has_product = SaleItem.objects.filter(
            sale=OuterRef('pk'),
            item__name__icontains=product_search,
        )
        sales = sales.filter(Exists(has_product))

    # Export all matching sales (no two-day cap) as a PDF listing individual sales
    # Build list of sales respecting filters
    sales = sales.select_related('customer').prefetch_related('items__retail_item', 'items__wholesale_item')

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 15 * mm
    y = height - margin

    p.setFont('Helvetica-Bold', 14)
    p.drawString(margin, y, 'All Sales Report')
    y -= 10 * mm
    p.setFont('Helvetica-Bold', 10)
    # Header row
    p.drawString(margin, y, 'Sale #')
    p.drawString(margin + 25 * mm, y, 'Date')
    p.drawString(margin + 65 * mm, y, 'Customer')
    p.drawString(margin + 120 * mm, y, 'Amount')
    p.drawString(margin + 150 * mm, y, 'Profit')
    y -= 6 * mm
    p.setFont('Helvetica', 10)

    for sale in sales:
        # Paginate
        if y < margin + 20 * mm:
            p.showPage()
            y = height - margin
            p.setFont('Helvetica', 10)

        # Compute cost for the sale by summing related items
        try:
            total_cost = sum((si.quantity * (si.item.cost_price or Decimal('0'))) for si in sale.items.all())
        except Exception:
            total_cost = Decimal('0')
        revenue = sale.total_amount or Decimal('0')
        profit = revenue - (total_cost or Decimal('0'))

        date_str = ''
        try:
            date_str = timezone.localtime(sale.sale_date).strftime('%Y-%m-%d')
        except Exception:
            date_str = str(sale.sale_date)

        customer_name = sale.customer.name if sale.customer else 'Walk-in'

        amount_str = format(revenue, ',.0f')
        profit_str = format(profit, ',.0f')

        p.drawString(margin, y, f"#{sale.id}")
        p.drawString(margin + 25 * mm, y, date_str)
        p.drawString(margin + 65 * mm, y, customer_name[:22])
        p.drawRightString(margin + 145 * mm, y, amount_str)
        p.drawRightString(margin + 175 * mm, y, profit_str)

        y -= 6 * mm

    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="all_sales.pdf"'
    return response


@login_required
def sales_daily_print(request):
    """Render a print-friendly HTML view of the daily sales summary."""
    # Render a print-friendly HTML listing of all matching sales (one row per sale)
    sales = Sale.objects.select_related('customer', 'created_by').order_by('-sale_date')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_status = request.GET.get('payment_status')
    # guard against literal 'None' or empty strings
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    if payment_status in (None, '', 'None'):
        payment_status = None

    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)
    if payment_status == 'paid':
        sales = sales.filter(is_paid=True)
    elif payment_status == 'unpaid':
        sales = sales.filter(is_paid=False)

    product_search = request.GET.get('product') or request.GET.get('search_product')
    if product_search not in (None, '', 'None') and str(product_search).strip():
        product_search = str(product_search).strip()
        has_product = SaleItem.objects.filter(
            sale=OuterRef('pk'),
            item__name__icontains=product_search,
        )
        sales = sales.filter(Exists(has_product))

    sales = sales.select_related('customer').prefetch_related('items__retail_item', 'items__wholesale_item')

    rows = []
    for sale in sales:
        try:
            total_cost = sum(
                (si.quantity * (si.retail_item.cost_price if si.product_type == 'retail' and si.retail_item else Decimal('0'))) 
                for si in sale.items.all()
            )
        except Exception:
            total_cost = Decimal('0')
        revenue = sale.total_amount or Decimal('0')
        profit = revenue - (total_cost or Decimal('0'))

        try:
            date_str = timezone.localtime(sale.sale_date).strftime('%Y-%m-%d %H:%M')
        except Exception:
            date_str = str(sale.sale_date)

        # Determine products for this sale. For payment-only sales (no items)
        # try to infer the original product(s) from an associated Debt.
        products_list = []
        try:
            sale_items = list(sale.items.select_related('item').all())
        except Exception:
            sale_items = []

        if sale_items:
            for si in sale_items:
                products_list.append(f"{si.item.name} ({si.quantity})")
        else:
            # Try to infer from notes like 'Payment for Debt #<id>'
            import re
            m = re.search(r'Payment for Debt #(\d+)', (sale.notes or ''))
            if m:
                from .models import Debt
                try:
                    debt = Debt.objects.select_related('item', 'sale').get(pk=int(m.group(1)))
                    # If the debt references an originating sale with items, use those
                    if debt.sale and debt.sale.items.exists():
                        for si in debt.sale.items.select_related('item').all():
                            products_list.append(f"{si.item.name} ({si.quantity})")
                    elif debt.item:
                        products_list.append(f"{debt.item.name} ({debt.quantity})")
                except Debt.DoesNotExist:
                    pass

        products_str = ', '.join(products_list) if products_list else ''

        # Determine created_by for print rows. Prefer sale.created_by, then
        # originating sale's created_by (if debt.sale), then debt.created_by.
        created_by_name = ''
        if sale.created_by:
            try:
                created_by_name = sale.created_by.get_full_name() or sale.created_by.username
            except Exception:
                created_by_name = getattr(sale.created_by, 'username', '')
        else:
            import re
            m2 = re.search(r'Payment for Debt #(\d+)', (sale.notes or ''))
            if m2:
                try:
                    debt = Debt.objects.select_related('sale__created_by', 'created_by').get(pk=int(m2.group(1)))
                    if debt.sale and debt.sale.created_by:
                        try:
                            created_by_name = debt.sale.created_by.get_full_name() or debt.sale.created_by.username
                        except Exception:
                            created_by_name = getattr(debt.sale.created_by, 'username', '')
                    elif debt.created_by:
                        try:
                            created_by_name = debt.created_by.get_full_name() or debt.created_by.username
                        except Exception:
                            created_by_name = getattr(debt.created_by, 'username', '')
                except Debt.DoesNotExist:
                    created_by_name = ''

        rows.append({
            'id': sale.id,
            'date': date_str,
            'customer': sale.customer.name if sale.customer else 'Walk-in',
            'amount': revenue,
            'profit': profit,
            'products': products_str,
            'payment_method': sale.get_payment_method_display(),
            'status': 'Paid' if sale.is_paid else 'Unpaid',
            'created_by': created_by_name,
        })

    context = {
        'sales_rows': rows,
        'start_date': start_date,
        'end_date': end_date,
        'payment_status': payment_status,
    }

    return render(request, 'tracker/sales_all_print.html', context)


@login_required
def delete_sale(request, pk):
    """Delete a sale and inform the user about restored stock."""
    sale = get_object_or_404(Sale, pk=pk)

    if request.method == 'POST':
        # Capture restored items info before deletion and restore stock
        restored_items = []
        for si in sale.items.all():
            # Restore stock based on product type
            if si.product_type == 'retail' and si.retail_item:
                si.retail_item.stock_quantity += si.quantity
                si.retail_item.save(update_fields=['stock_quantity'])
                restored_items.append(f"{si.retail_item.name} (+{si.quantity} units)")
            elif si.product_type == 'wholesale' and si.wholesale_item:
                si.wholesale_item.cartons_in_stock += si.quantity
                si.wholesale_item.save(update_fields=['cartons_in_stock'])
                restored_items.append(f"{si.wholesale_item.name} (+{si.quantity} cartons)")

        # Check if this is a payment sale for a debt
        if not sale.items.exists() and sale.notes and 'Payment for Debt #' in sale.notes:
            import re
            match = re.search(r'Payment for Debt #(\d+)', sale.notes)
            if match:
                debt_id = int(match.group(1))
                try:
                    from .models import Debt
                    debt = Debt.objects.get(pk=debt_id)
                    # Restore stock for the debt's item and quantity
                    if debt.item:
                        debt.item.stock_quantity += debt.quantity
                        debt.item.save(update_fields=['stock_quantity'])
                        restored_items.append(f"{debt.item.name} (+{debt.quantity})")
                    # Reverse the payment
                    debt.paid_amount -= sale.total_amount
                    if debt.paid_amount < 0:
                        debt.paid_amount = Decimal('0')
                    # Update debt status
                    if debt.paid_amount >= debt.amount:
                        debt.status = 'paid'
                    elif debt.paid_amount > 0:
                        debt.status = 'partial'
                    else:
                        debt.status = 'pending'
                    debt.save()
                except Debt.DoesNotExist:
                    pass  # Debt might have been deleted already

        sale.delete()

        if restored_items:
            messages.success(request, f"Sale deleted. Restored stock: {', '.join(restored_items)}")
        else:
            messages.success(request, "Sale deleted.")

        return redirect('sales_list')

    # GET -> show confirmation
    return render(request, 'tracker/confirm_delete_sale.html', {'sale': sale})


@login_required
def create_sale(request):
    """Create a new sale with items"""
    if request.method == 'POST':
        # Handle both sale creation and first item addition in one step
        sale_form = SaleForm(request.POST)
        item_form = SaleItemForm(request.POST)
        
        if sale_form.is_valid() and item_form.is_valid():
            try:
                with transaction.atomic():
                    # Create sale first
                    sale = sale_form.save(commit=False)
                    sale.created_by = request.user
                    sale.total_amount = 0.00  # Will be calculated
                    sale.save()
                    
                    # Add the first item
                    sale_item = item_form.save(commit=False)
                    sale_item.sale = sale
                    
                    # Check stock availability based on product type
                    stock_error = None
                    if sale_item.product_type == 'retail' and sale_item.retail_item:
                        if sale_item.retail_item.stock_quantity < sale_item.quantity:
                            stock_error = f'Insufficient stock for {sale_item.retail_item.name}! Available: {sale_item.retail_item.stock_quantity}, Requested: {sale_item.quantity}'
                    elif sale_item.product_type == 'wholesale' and sale_item.wholesale_item:
                        if sale_item.wholesale_item.cartons_in_stock < sale_item.quantity:
                            stock_error = f'Insufficient stock for {sale_item.wholesale_item.name}! Available: {sale_item.wholesale_item.cartons_in_stock}, Requested: {sale_item.quantity}'
                    else:
                        stock_error = 'Please select a valid product.'
                    
                    if stock_error:
                        messages.error(request, stock_error)
                        sale.delete()  # Clean up the sale since no items were added
                        context = {
                            'sale_form': sale_form,
                            'item_form': item_form,
                        }
                        return render(request, 'tracker/sale_form.html', context)
                    
                    # Save the sale item (this will reduce stock)
                    sale_item.save()
                    
                    # Update sale total
                    sale.total_amount = sale_item.total_price
                    sale.save(update_fields=['total_amount'])
                    
                    messages.success(request, 'Sale created successfully with first item!')
                    return redirect('sale_detail', pk=sale.pk)
                    
            except Exception as e:
                messages.error(request, f'Error creating sale: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        sale_form = SaleForm()
        item_form = SaleItemForm()
    
    context = {
        'sale_form': sale_form,
        'item_form': item_form,
    }
    
    return render(request, 'tracker/sale_form.html', context)


@login_required
def add_sale_item(request, sale_id):
    """Add an item to a sale"""
    # We will lock the Sale row during item addition to avoid race conditions
    if request.method == 'POST':
        form = SaleItemForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Lock the sale row for this transaction so concurrent requests serialize
                    sale = Sale.objects.select_for_update().get(pk=sale_id)

                    sale_item = form.save(commit=False)
                    sale_item.sale = sale

                    # Check if this sale already has the same item
                    existing_item = None
                    try:
                        if sale_item.product_type == 'retail' and sale_item.retail_item:
                            existing_item = SaleItem.objects.get(sale=sale, product_type='retail', retail_item=sale_item.retail_item)
                        elif sale_item.product_type == 'wholesale' and sale_item.wholesale_item:
                            existing_item = SaleItem.objects.get(sale=sale, product_type='wholesale', wholesale_item=sale_item.wholesale_item)
                    except SaleItem.DoesNotExist:
                        existing_item = None

                    # Check stock availability based on product type
                    stock_error = None
                    if sale_item.product_type == 'retail' and sale_item.retail_item:
                        if existing_item is None and sale_item.retail_item.stock_quantity < sale_item.quantity:
                            stock_error = f'Insufficient stock for {sale_item.retail_item.name}! Available: {sale_item.retail_item.stock_quantity}, Requested: {sale_item.quantity}'
                    elif sale_item.product_type == 'wholesale' and sale_item.wholesale_item:
                        if existing_item is None and sale_item.wholesale_item.cartons_in_stock < sale_item.quantity:
                            stock_error = f'Insufficient stock for {sale_item.wholesale_item.name}! Available: {sale_item.wholesale_item.cartons_in_stock}, Requested: {sale_item.quantity}'
                    
                    if stock_error:
                        messages.error(request, stock_error)
                        context = {
                            'form': form,
                            'sale': sale,
                        }
                        return render(request, 'tracker/add_sale_item.html', context)

                    try:
                        # If the item already exists on the sale, increase its quantity instead of creating a duplicate
                        merged = False
                        additional = 0
                        if existing_item:
                            additional = sale_item.quantity
                            # Check stock for additional quantity
                            stock_error = None
                            if sale_item.product_type == 'retail' and sale_item.retail_item:
                                if sale_item.retail_item.stock_quantity < additional:
                                    stock_error = f'Insufficient stock for {sale_item.retail_item.name}! Available: {sale_item.retail_item.stock_quantity}, Requested additional: {additional}'
                            elif sale_item.product_type == 'wholesale' and sale_item.wholesale_item:
                                if sale_item.wholesale_item.cartons_in_stock < additional:
                                    stock_error = f'Insufficient stock for {sale_item.wholesale_item.name}! Available: {sale_item.wholesale_item.cartons_in_stock}, Requested additional: {additional}'
                            
                            if stock_error:
                                messages.error(request, stock_error)
                                context = {
                                    'form': form,
                                    'sale': sale,
                                }
                                return render(request, 'tracker/add_sale_item.html', context)

                            existing_item.quantity = existing_item.quantity + additional
                            # Update unit_price to the latest provided price (could choose to keep existing)
                            existing_item.unit_price = sale_item.unit_price
                            existing_item.save()
                            merged = True
                        else:
                            sale_item.save()

                        # Recompute sale total from DB to ensure accuracy under concurrency
                        aggregated = SaleItem.objects.filter(sale=sale).aggregate(total=Sum('total_price'))
                        total = aggregated['total'] or Decimal('0')
                        sale.total_amount = total
                        sale.save(update_fields=['total_amount'])

                        if merged:
                            messages.success(request, f'Item quantity updated; merged additional {additional} units into the existing line.')
                        else:
                            messages.success(request, 'Item added to sale successfully! Stock has been updated.')

                        return redirect('sale_detail', pk=sale.pk)
                    except ValueError as e:
                        # Handle stock validation error from model (for updates or race conditions)
                        messages.error(request, str(e))
                        context = {
                            'form': form,
                            'sale': sale,
                        }
                        return render(request, 'tracker/add_sale_item.html', context)
            except Sale.DoesNotExist:
                messages.error(request, 'Sale not found.')
                return redirect('sales_list')
    else:
        # For GET, just fetch the sale for context
        sale = get_object_or_404(Sale, pk=sale_id)
        form = SaleItemForm()

    context = {
        'form': form,
        'sale': sale,
    }

    return render(request, 'tracker/add_sale_item.html', context)


@login_required
def debts_list(request):
    """List all debts"""
    debts = Debt.objects.select_related('customer').order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        if status == 'overdue':
            debts = debts.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'partial']
            )
        else:
            debts = debts.filter(status=status)
    
    # Filter by customer
    customer_id = request.GET.get('customer')
    if customer_id:
        debts = debts.filter(customer_id=customer_id)
    
    # Filter by overdue
    overdue_only = request.GET.get('overdue')
    if overdue_only:
        debts = debts.filter(due_date__lt=timezone.now().date(), status__in=['pending', 'partial'])

    # Search functionality (searches description when customer is selected, or customer name + description when not)
    search_query = request.GET.get('search')
    if search_query:
        if customer_id:
            # When customer is selected, only search in description
            debts = debts.filter(description__icontains=search_query)
        else:
            # When no customer selected, search in customer name and description
            debts = debts.filter(
                Q(customer__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
    
    # Get all customers for the dropdown
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    # Totals for the filtered dataset
    totals = debts.aggregate(
        total_amount=Sum('amount'),
        total_paid=Sum('paid_amount')
    )
    total_amount = totals['total_amount'] or Decimal('0')
    total_paid = totals['total_paid'] or Decimal('0')
    total_remaining = total_amount - total_paid
    
    # Paginate
    page = request.GET.get('page')
    paginator = Paginator(debts, 20)
    page_obj = paginator.get_page(page)

    context = {
        'debts': page_obj,
        'customers': customers,
        'selected_status': status,
        'selected_customer': customer_id,
        'overdue_only': overdue_only,
        'search_query': search_query,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'paginator': paginator,
        'page_obj': page_obj,
    }

    return render(request, 'tracker/debts_list.html', context)


@login_required
def expenditures_list(request):
    """List expenditures and totals"""
    expenditures = Expenditure.objects.all().order_by('-expense_date')

    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    # guard against literal 'None' or empty strings from template/query
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    if start_date:
        expenditures = expenditures.filter(expense_date__date__gte=start_date)
    if end_date:
        expenditures = expenditures.filter(expense_date__date__lte=end_date)

    total_spent = expenditures.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Paginate
    page = request.GET.get('page')
    paginator = Paginator(expenditures, 20)
    page_obj = paginator.get_page(page)

    context = {
        'expenditures': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'total_spent': total_spent,
        'paginator': paginator,
        'page_obj': page_obj,
    }
    return render(request, 'tracker/expenditures_list.html', context)


@login_required
def create_expenditure(request):
    if request.method == 'POST':
        form = ExpenditureForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.created_by = request.user
            exp.save()
            messages.success(request, 'Expenditure recorded successfully.')
            return redirect('expenditures_list')
    else:
        form = ExpenditureForm()

    return render(request, 'tracker/expenditure_form.html', {'form': form})


@login_required
def delete_expenditure(request, pk):
    """Delete an expenditure entry after confirmation."""
    exp = get_object_or_404(Expenditure, pk=pk)

    if request.method == 'POST':
        exp.delete()
        messages.success(request, 'Expenditure deleted successfully.')
        return redirect('expenditures_list')

    return render(request, 'tracker/confirm_delete_expenditure.html', {'expenditure': exp})


@login_required
def expenditures_export_csv(request):
    """Export filtered expenditures as CSV"""
    expenditures = Expenditure.objects.all().order_by('-expense_date')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    if start_date:
        expenditures = expenditures.filter(expense_date__date__gte=start_date)
    if end_date:
        expenditures = expenditures.filter(expense_date__date__lte=end_date)

    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="expenditures.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Category', 'Description', 'Date', 'Amount', 'Created By'])
        for e in expenditures:
            # ensure we can format fields safely
            date_str = ''
            try:
                date_str = timezone.localtime(e.expense_date).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                date_str = str(e.expense_date)

            created_by = ''
            try:
                created_by = e.created_by.username if e.created_by else ''
            except Exception:
                created_by = ''

            writer.writerow([
                e.id,
                e.get_category_display(),
                e.description or '',
                date_str,
                f"{e.amount}",
                created_by,
            ])
        return response
    except Exception as exc:
        # Log and show a friendly message if CSV generation fails in production
        messages.error(request, 'Failed to export expenditures as CSV. Please try again or contact support.')
        return redirect('expenditures_list')


@login_required
def expenditures_export_pdf(request):
    """Export filtered expenditures as PDF using ReportLab. Falls back to a friendly message if ReportLab missing."""
    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'PDF export requires the ReportLab package. Install it with `pip install reportlab`.')
        return redirect('expenditures_list')

    expenditures = Expenditure.objects.all().order_by('-expense_date')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date in (None, '', 'None'):
        start_date = None
    if end_date in (None, '', 'None'):
        end_date = None
    if start_date:
        expenditures = expenditures.filter(expense_date__date__gte=start_date)
    if end_date:
        expenditures = expenditures.filter(expense_date__date__lte=end_date)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin

    # Header
    p.setFont('Helvetica-Bold', 14)
    p.drawString(margin, y, 'Expenditures Report')
    y -= 10 * mm
    p.setFont('Helvetica', 10)

    # Table header
    p.drawString(margin, y, 'ID')
    p.drawString(margin + 20 * mm, y, 'Category')
    p.drawString(margin + 60 * mm, y, 'Date')
    p.drawString(margin + 100 * mm, y, 'Amount')
    p.drawString(margin + 130 * mm, y, 'Description')
    y -= 6 * mm

    for e in expenditures:
        if y < margin + 20 * mm:
            p.showPage()
            y = height - margin
        date_str = ''
        try:
            date_str = timezone.localtime(e.expense_date).strftime('%Y-%m-%d %H:%M')
        except Exception:
            date_str = str(e.expense_date)

        p.drawString(margin, y, str(e.id))
        p.drawString(margin + 20 * mm, y, e.get_category_display())
        p.drawString(margin + 60 * mm, y, date_str)
        p.drawString(margin + 100 * mm, y, f"{e.amount}")
        # description may be long — wrap rudimentarily
        desc = (e.description or '')[:80]
        p.drawString(margin + 130 * mm, y, desc)
        y -= 6 * mm

    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="expenditures.pdf"'
    return response


@login_required
def debt_detail(request, pk):
    """Detail view for a debt"""
    debt = get_object_or_404(Debt, pk=pk)
    payments = debt.payments.all().order_by('-payment_date')
    
    context = {
        'debt': debt,
        'payments': payments,
    }
    
    return render(request, 'tracker/debt_detail.html', context)


@login_required
def create_debt(request):
    """Create a new debt. If an item and quantity are provided, reduce stock accordingly."""
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            # If an item is provided and amount left blank, auto-calc from item price
            if debt.item and (debt.amount is None or debt.amount == 0):
                debt.amount = (debt.item.unit_price or Decimal('0.00')) * debt.quantity
            # If an item is provided and the user entered the item unit price (not the total),
            # treat it as a per-unit price and multiply by the quantity to store the total debt.
            elif debt.item and debt.amount is not None:
                try:
                    unit_price = (debt.item.unit_price or Decimal('0.00'))
                    # If the entered amount equals the unit price, assume it's a per-unit value
                    if debt.amount == unit_price:
                        debt.amount = debt.amount * debt.quantity
                except Exception:
                    # If anything goes wrong with comparison, fall back to using the provided amount
                    pass
            # record which user created this debt (if available)
            try:
                debt.created_by = request.user
            except Exception:
                pass

            # Reduce stock if item provided
            if debt.item:
                if debt.item.stock_quantity < debt.quantity:
                    form.add_error('quantity', 'Insufficient stock to create debt for this quantity.')
                    return render(request, 'tracker/debt_form.html', {'form': form})
                else:
                    # deduct stock
                    debt.item.stock_quantity -= debt.quantity
                    debt.item.save(update_fields=['stock_quantity'])
            debt.save()
            messages.success(request, 'Debt created successfully!')
            return redirect('debts_list')
    else:
        form = DebtForm()
    
    context = {
        'form': form,
        'unit_prices': form.unit_prices,
    }
    
    return render(request, 'tracker/debt_form.html', context)


@login_required
def add_payment(request, debt_id):
    """Add a payment to a debt"""
    debt = get_object_or_404(Debt, pk=debt_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, debt=debt)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.debt = debt
            payment.save()

            # Create a Sale corresponding to this payment so sales dashboards reflect payments received
            try:
                # Create detailed notes showing the debt items and information
                debt_items_info = f"Debt #{debt.pk}: {debt.item.name}"
                if debt.quantity > 1:
                    debt_items_info += f" (Qty: {debt.quantity})"
                debt_items_info += f" - Total: TZS {debt.amount:,.0f}"
                if debt.description:
                    debt_items_info += f" - {debt.description}"
                
                sale = Sale.objects.create(
                    customer=debt.customer,
                    total_amount=payment.amount,
                    payment_method=payment.payment_method,
                    is_paid=True,
                    notes=f'Payment for {debt_items_info}',
                    created_by=request.user
                )
                # Only link the created sale to the debt if the debt had no originating sale
                # (we don't want to overwrite an original sale that generated the debt)
                if not debt.sale:
                    debt.sale = sale
                    debt.save(update_fields=['sale'])
            except Exception:
                # Don't prevent the payment from being recorded if sale creation fails
                sale = None

            messages.success(request, 'Payment added successfully!')
            return redirect('debt_detail', pk=debt.pk)
    else:
        # GET - display empty payment form
        form = PaymentForm(debt=debt)

    context = {
        'form': form,
        'debt': debt,
    }
    
    return render(request, 'tracker/payment_form.html', context)


@login_required
def customers_list(request):
    """List all customers"""
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Paginate
    page = request.GET.get('page')
    paginator = Paginator(customers, 20)
    page_obj = paginator.get_page(page)

    context = {
        'customers': page_obj,
        'search_query': search_query,
        'paginator': paginator,
        'page_obj': page_obj,
    }
    
    return render(request, 'tracker/customers_list.html', context)


@login_required
def customer_detail(request, pk):
    """Detail view for a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    sales = customer.sale_set.all().order_by('-sale_date')[:10]
    debts = customer.debts.all().order_by('-created_at')
    
    context = {
        'customer': customer,
        'sales': sales,
        'debts': debts,
    }
    
    return render(request, 'tracker/customer_detail.html', context)


@login_required
def create_customer(request):
    """Create a new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer created successfully!')
            return redirect('customers_list')
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'tracker/customer_form.html', context)


@login_required
def create_stationery_item(request):
    """Create a new stationery item"""
    if request.method == 'POST':
        form = StationeryItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stationery item created successfully!')
            return redirect('stationery_list')
    else:
        form = StationeryItemForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'tracker/stationery_form.html', context)


@login_required
def send_debt_sms(request, debt_id):
    """Send SMS reminder for a specific debt"""
    debt = get_object_or_404(Debt, pk=debt_id)

    if request.method == 'POST':
        from .sms_utils import send_debt_reminder_sms

        result = send_debt_reminder_sms(debt)

        if result['success']:
            messages.success(request, f'SMS sent successfully to {debt.customer.name}')
        else:
            messages.error(request, f'Failed to send SMS: {result.get("error", "Unknown error")}')

        return redirect('debt_detail', pk=debt.pk)

    # GET request - show confirmation page
    context = {
        'debt': debt,
    }

    return render(request, 'tracker/send_debt_sms.html', context)


@login_required
def send_bulk_debt_sms(request):
    """Send SMS reminders to multiple customers with outstanding debts"""
    if request.method == 'POST':
        try:
            try:
                from .sms_utils import send_debt_reminder_sms
            except Exception as e:
                logger.exception("Failed to import sms_utils: %s", e)
                messages.error(request, 'SMS module could not be loaded. Check configuration.')
                return redirect('send_bulk_debt_sms')

            # Parse and validate debt_ids
            raw_ids = request.POST.getlist('debt_ids')
            debt_ids = []
            for sid in raw_ids:
                if not sid:
                    continue
                try:
                    debt_ids.append(int(sid))
                except (ValueError, TypeError):
                    continue

            if not debt_ids:
                messages.warning(request, 'No debts selected. Please select at least one debt.')
                return redirect('send_bulk_debt_sms')

            debts = Debt.objects.select_related('customer').filter(
                id__in=debt_ids,
                customer__phone__isnull=False
            ).exclude(customer__phone='')

            sent_count = 0
            failed_count = 0
            errors = []

            for debt in debts:
                try:
                    result = send_debt_reminder_sms(debt)
                    if result.get('success'):
                        sent_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{debt.customer.name}: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.exception("Bulk SMS failed for debt id=%s: %s", debt.pk, e)
                    failed_count += 1
                    errors.append(f"{debt.customer.name}: {str(e)}")

            if sent_count > 0:
                messages.success(request, f'SMS sent to {sent_count} customers')

            if failed_count > 0:
                messages.warning(request, f'Failed to send SMS to {failed_count} customers')
                for err in errors[:5]:
                    messages.warning(request, err)

            if sent_count == 0 and failed_count == 0:
                messages.warning(request, 'No eligible debts with phone numbers found for the selected items.')

            return redirect('debts_list')

        except Exception as e:
            logger.exception("Bulk SMS request failed: %s", e)
            messages.error(
                request,
                'An unexpected error occurred while sending bulk SMS. Please try again or contact support.'
            )
            return redirect('send_bulk_debt_sms')

    # GET request - show form to select debts
    debts = Debt.objects.select_related('customer').filter(
        status__in=['pending', 'partial', 'overdue'],
        customer__phone__isnull=False
    ).exclude(customer__phone='').order_by('due_date')

    context = {
        'debts': debts,
    }

    return render(request, 'tracker/send_bulk_debt_sms.html', context)


@login_required
def send_debt_whatsapp(request, debt_id):
    """Send WhatsApp reminder for a specific debt"""
    debt = get_object_or_404(Debt, pk=debt_id)

    if request.method == 'POST':
        from .sms_utils import send_debt_reminder_whatsapp

        result = send_debt_reminder_whatsapp(debt)

        if result['success']:
            messages.success(request, f'WhatsApp message sent successfully to {debt.customer.name}')
        else:
            messages.error(request, f'Failed to send WhatsApp message: {result.get("error", "Unknown error")}')

        return redirect('debt_detail', pk=debt.pk)

    # GET request - show confirmation page
    context = {
        'debt': debt,
    }

    return render(request, 'tracker/send_debt_whatsapp.html', context)


@login_required
def send_bulk_debt_whatsapp(request):
    """Send WhatsApp reminders to multiple customers with outstanding debts"""
    if request.method == 'POST':
        from .sms_utils import send_debt_reminder_whatsapp

        # Get debts to send WhatsApp to
        debt_ids = request.POST.getlist('debt_ids')
        debts = Debt.objects.filter(
            id__in=debt_ids,
            customer__phone__isnull=False
        ).exclude(customer__phone='')

        sent_count = 0
        failed_count = 0
        errors = []

        for debt in debts:
            result = send_debt_reminder_whatsapp(debt)
            if result['success']:
                sent_count += 1
            else:
                failed_count += 1
                errors.append(f"{debt.customer.name}: {result.get('error', 'Unknown error')}")

        if sent_count > 0:
            messages.success(request, f'WhatsApp messages sent to {sent_count} customers')

        if failed_count > 0:
            messages.warning(request, f'Failed to send WhatsApp to {failed_count} customers')
            for error in errors[:5]:  # Show first 5 errors
                messages.warning(request, error)

        return redirect('debts_list')

    # GET request - show form to select debts
    debts = Debt.objects.select_related('customer').filter(
        status__in=['pending', 'partial', 'overdue'],
        customer__phone__isnull=False
    ).exclude(customer__phone='').order_by('due_date')

    context = {
        'debts': debts,
    }

    return render(request, 'tracker/send_bulk_debt_whatsapp.html', context)
