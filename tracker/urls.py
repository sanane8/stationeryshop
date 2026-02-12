from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        success_url='done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('login/password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/update/', views.supplier_update, name='supplier_update'),
    
    # Stationery items
    path('stationery/', views.stationery_list, name='stationery_list'),
    path('stationery/<int:pk>/', views.stationery_detail, name='stationery_detail'),
    path('stationery/create/', views.create_stationery_item, name='create_stationery_item'),
    
    # Sales
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/chart/', views.sales_chart, name='sales_chart'),
    path('sales/export/daily/', views.sales_daily_export_csv, name='sales_daily_export'),
    path('sales/export/daily/pdf/', views.sales_daily_export_pdf, name='sales_daily_export_pdf'),
    path('sales/print/daily/', views.sales_daily_print, name='sales_daily_print'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/invoice/', views.print_invoice, name='print_invoice'),
    path('sales/<int:pk>/delete/', views.delete_sale, name='delete_sale'),
    path('sales/create/', views.create_sale, name='create_sale'),
    path('sales/<int:sale_id>/add-item/', views.add_sale_item, name='add_sale_item'),
    
    # Debts
    path('debts/', views.debts_list, name='debts_list'),
    path('expenditures/', views.expenditures_list, name='expenditures_list'),
    path('expenditures/create/', views.create_expenditure, name='create_expenditure'),
    path('expenditures/export/', views.expenditures_export_csv, name='expenditures_export'),
    path('expenditures/export/pdf/', views.expenditures_export_pdf, name='expenditures_export_pdf'),
    path('expenditures/<int:pk>/delete/', views.delete_expenditure, name='delete_expenditure'),
    path('debts/<int:pk>/', views.debt_detail, name='debt_detail'),
    path('debts/create/', views.create_debt, name='create_debt'),
    path('debts/<int:debt_id>/payment/', views.add_payment, name='add_payment'),
    path('debts/<int:debt_id>/send-sms/', views.send_debt_sms, name='send_debt_sms'),
    path('debts/send-bulk-sms/', views.send_bulk_debt_sms, name='send_bulk_debt_sms'),
    path('debts/<int:debt_id>/send-whatsapp/', views.send_debt_whatsapp, name='send_debt_whatsapp'),
    path('debts/send-bulk-whatsapp/', views.send_bulk_debt_whatsapp, name='send_bulk_debt_whatsapp'),
    
    # Customers
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/create/', views.create_customer, name='create_customer'),
    
    # Dashboard (moved to root URLconf)
    path('dashboard/', views.dashboard, name='dashboard'),
]
