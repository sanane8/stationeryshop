# Stationery Tracker (TZS)

A comprehensive Django application for tracking sales, stationery commodities, and debt management for stationery businesses in Tanzania. All amounts are displayed in Tanzanian Shillings (TZS).

## Features

- **Stationery Management**: Track inventory, pricing, stock levels, and supplier information
- **Sales Tracking**: Record sales transactions with customer information and payment methods
- **Debt Management**: Track customer debts, payments, and overdue accounts
- **Customer Management**: Maintain customer database with contact information
- **Dashboard**: Overview of key metrics including sales, stock levels, and outstanding debts
- **Admin Interface**: Full Django admin interface for data management

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd Stationery
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser account**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main application: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Usage

### Getting Started

1. **Set up Categories**: Go to Admin Panel → Categories and add stationery categories (e.g., Pens, Paper, Office Supplies)

2. **Add Stationery Items**: 
   - Use the "Add Item" button on the Stationery Items page
   - Fill in item details including name, SKU, category, prices, and stock levels

3. **Add Customers**:
   - Use the "Add Customer" button on the Customers page
   - Enter customer contact information

4. **Record Sales**:
   - Use the "New Sale" button on the Sales page
   - Select customer, payment method, and add notes

5. **Manage Debts**:
   - Create debt records for unpaid sales or credit transactions
   - Track payments and update debt status

### Key Features

- **Low Stock Alerts**: Items below minimum stock level are highlighted
- **Overdue Debt Tracking**: Debts past due date are flagged
- **Sales Analytics**: View daily and monthly sales totals
- **Profit Margin Calculation**: Automatic calculation of profit margins
- **Search and Filter**: Find items, customers, and transactions quickly

## Models

### StationeryItem
- Item details (name, SKU, description)
- Pricing (unit price, cost price)
- Inventory (stock quantity, minimum stock)
- Supplier information

### Sale
- Customer and transaction details
- Payment method and status
- Total amount and profit calculation

### Debt
- Customer debt tracking
- Payment history
- Due dates and status

### Customer
- Contact information
- Sales and debt history

## Admin Features

The Django admin interface provides:
- Full CRUD operations for all models
- Advanced filtering and search
- Bulk actions
- Data export capabilities
- User management

## Customization

### Adding New Fields
1. Modify the models in `tracker/models.py`
2. Update the admin interface in `tracker/admin.py`
3. Create and run migrations
4. Update forms and templates as needed

### Styling
- Modify CSS in `templates/base.html`
- Bootstrap 5 is used for responsive design
- Font Awesome icons are included


