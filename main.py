
import os
import json
import pandas as pd
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from functools import wraps

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_key_for_deposit_tracker')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Data storage paths
DATA_DIR = 'data'
CUSTOMERS_FILE = os.path.join(DATA_DIR, 'customers.json')
DEPOSITS_FILE = os.path.join(DATA_DIR, 'deposits.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize data files if they don't exist
if not os.path.exists(CUSTOMERS_FILE):
    with open(CUSTOMERS_FILE, 'w') as f:
        json.dump([], f)

if not os.path.exists(DEPOSITS_FILE):
    with open(DEPOSITS_FILE, 'w') as f:
        json.dump([], f)
        
if not os.path.exists(USERS_FILE):
    # Create default admin user
    default_user = [{
        'id': 1,
        'username': 'admin',
        'email': 'admin@example.com',
        'password': 'admin123',  # In a real app, this should be hashed
        'role': 'admin',
        'created_at': datetime.now().isoformat()
    }]
    with open(USERS_FILE, 'w') as f:
        json.dump(default_user, f, indent=2)

# Helper functions
def load_customers():
    with open(CUSTOMERS_FILE, 'r') as f:
        return json.load(f)

def save_customers(customers):
    with open(CUSTOMERS_FILE, 'w') as f:
        json.dump(customers, f, indent=2)

def load_deposits():
    with open(DEPOSITS_FILE, 'r') as f:
        return json.load(f)

def save_deposits(deposits):
    with open(DEPOSITS_FILE, 'w') as f:
        json.dump(deposits, f, indent=2)

def get_next_customer_id():
    customers = load_customers()
    return max([c.get('id', 0) for c in customers], default=0) + 1

def get_next_deposit_id():
    deposits = load_deposits()
    return max([d.get('id', 0) for d in deposits], default=0) + 1

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_next_user_id():
    users = load_users()
    return max([u.get('id', 0) for u in users], default=0) + 1

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_users()
        user = next((u for u in users if u.get('username') == username and u.get('password') == password), None)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'user')
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    logo_present = os.path.exists('static/images/logo.png')
    return render_template('login.html', logo_present=logo_present)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

# Protected routes
@app.route('/')
@login_required
def index():
    customers = load_customers()
    logo_present = os.path.exists('static/images/logo.png')
    return render_template('index.html', customers=customers, logo_present=logo_present)

@app.route('/customers')
@login_required
def customer_list():
    customers = load_customers()
    logo_present = os.path.exists('static/images/logo.png')
    return render_template('customers.html', customers=customers, logo_present=logo_present)

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        loan_number = request.form.get('loan_number')
        address = request.form.get('address')
        
        if not name:
            flash('Customer name is required', 'error')
            return redirect(url_for('add_customer'))
        
        customers = load_customers()
        new_customer = {
            'id': get_next_customer_id(),
            'name': name,
            'phone': phone,
            'email': email,
            'loan_number': loan_number,
            'address': address,
            'created_at': datetime.now().isoformat()
        }
        customers.append(new_customer)
        save_customers(customers)
        
        flash('Customer added successfully', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('add_customer.html')

@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customers = load_customers()
    customer = next((c for c in customers if c.get('id') == customer_id), None)
    
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('customer_list'))
    
    if request.method == 'POST':
        customer['name'] = request.form.get('name')
        customer['phone'] = request.form.get('phone')
        customer['email'] = request.form.get('email')
        customer['loan_number'] = request.form.get('loan_number')
        customer['address'] = request.form.get('address')
        customer['updated_at'] = datetime.now().isoformat()
        
        save_customers(customers)
        flash('Customer updated successfully', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customers = load_customers()
    deposits = load_deposits()
    
    # Find the customer
    customer = next((c for c in customers if c.get('id') == customer_id), None)
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('customer_list'))
    
    # Check if customer has deposits
    customer_deposits = [d for d in deposits if d.get('customer_id') == customer_id]
    if customer_deposits:
        flash('Cannot delete customer with existing deposits. Remove deposits first.', 'error')
        return redirect(url_for('customer_list'))
    
    # Remove customer from list
    customers = [c for c in customers if c.get('id') != customer_id]
    save_customers(customers)
    
    flash('Customer deleted successfully', 'success')
    return redirect(url_for('customer_list'))

@app.route('/deposits')
@login_required
def deposit_list():
    deposits = load_deposits()
    customers = load_customers()
    customer_map = {c['id']: c for c in customers}
    
    for deposit in deposits:
        customer = customer_map.get(deposit['customer_id'])
        deposit['customer_name'] = customer['name'] if customer else 'Unknown'
    
    return render_template('deposits.html', deposits=deposits)

@app.route('/add_deposit', methods=['GET', 'POST'])
@login_required
def add_deposit():
    customers = load_customers()
    today = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        customer_id = int(request.form.get('customer_id'))
        amount = float(request.form.get('amount'))
        date = request.form.get('date')
        notes = request.form.get('notes', '')
        
        if not customer_id or not amount or not date:
            flash('Customer, amount, and date are required', 'error')
            return redirect(url_for('add_deposit'))
        
        deposits = load_deposits()
        new_deposit = {
            'id': get_next_deposit_id(),
            'customer_id': customer_id,
            'amount': amount,
            'date': date,
            'notes': notes,
            'created_at': datetime.now().isoformat()
        }
        deposits.append(new_deposit)
        save_deposits(deposits)
        
        flash('Deposit added successfully', 'success')
        return redirect(url_for('deposit_list'))
    
    return render_template('add_deposit.html', customers=customers, today=today)

@app.route('/export_excel')
@login_required
def export_excel():
    customers = load_customers()
    deposits = load_deposits()
    
    # Create customer lookup
    customer_map = {c['id']: c for c in customers}
    
    # Prepare data for export
    export_data = []
    for deposit in deposits:
        customer = customer_map.get(deposit['customer_id'], {})
        export_data.append({
            'Deposit ID': deposit['id'],
            'Date': deposit['date'],
            'Customer Name': customer.get('name', 'Unknown'),
            'Customer Phone': customer.get('phone', ''),
            'Loan Number': customer.get('loan_number', ''),
            'Amount': deposit['amount'],
            'Notes': deposit['notes']
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(export_data)
    
    # Create an Excel file
    export_file = os.path.join(DATA_DIR, 'deposit_report.xlsx')
    df.to_excel(export_file, index=False, engine='openpyxl')
    
    return send_file(export_file, as_attachment=True, download_name=f'deposit_report_{datetime.now().strftime("%Y%m%d")}.xlsx')

@app.route('/customer_report/<int:customer_id>')
@login_required
def customer_report(customer_id):
    customers = load_customers()
    deposits = load_deposits()
    
    customer = next((c for c in customers if c.get('id') == customer_id), None)
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('customer_list'))
    
    customer_deposits = [d for d in deposits if d.get('customer_id') == customer_id]
    
    # Create customer report DataFrame
    export_data = []
    for deposit in customer_deposits:
        export_data.append({
            'Date': deposit['date'],
            'Amount': deposit['amount'],
            'Notes': deposit['notes']
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(export_data)
    
    # Create an Excel file
    export_file = os.path.join(DATA_DIR, f'customer_{customer_id}_report.xlsx')
    df.to_excel(export_file, index=False, engine='openpyxl')
    
    return send_file(export_file, as_attachment=True, download_name=f'customer_{customer["name"].replace(" ", "_")}_report.xlsx')

@app.route('/import_customers', methods=['GET', 'POST'])
@login_required
def import_customers():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('import_customers'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('import_customers'))
        
        # Check file extension
        if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            flash('Only CSV and Excel files are supported', 'error')
            return redirect(url_for('import_customers'))
        
        try:
            # Read the file
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Validate the structure (must have at least a name column)
            if 'name' not in df.columns and 'Name' not in df.columns:
                flash('The file must contain a "name" or "Name" column', 'error')
                return redirect(url_for('import_customers'))
            
            # Normalize column names
            df.columns = [col.lower() for col in df.columns]
            
            # Load existing customers
            customers = load_customers()
            current_id = get_next_customer_id()
            imported_count = 0
            
            # Process each row
            for _, row in df.iterrows():
                name = row.get('name', '')
                if not name:
                    continue
                
                new_customer = {
                    'id': current_id,
                    'name': name,
                    'phone': str(row.get('phone', '')) if 'phone' in row else '',
                    'email': row.get('email', '') if 'email' in row else '',
                    'loan_number': str(row.get('loan_number', '')) if 'loan_number' in row else '',
                    'address': row.get('address', '') if 'address' in row else '',
                    'created_at': datetime.now().isoformat()
                }
                
                customers.append(new_customer)
                current_id += 1
                imported_count += 1
            
            # Save the updated customer list
            save_customers(customers)
            
            flash(f'Successfully imported {imported_count} customers', 'success')
            return redirect(url_for('customer_list'))
            
        except Exception as e:
            flash(f'Error importing customers: {str(e)}', 'error')
            return redirect(url_for('import_customers'))
    
    return render_template('import_customers.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    logo_present = os.path.exists('static/images/logo.png')
    
    if request.method == 'POST':
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename != '':
                # Create static/images directory if it doesn't exist
                os.makedirs('static/images', exist_ok=True)
                
                # Save the uploaded logo
                filename = secure_filename('logo.png')
                logo_path = os.path.join('static/images', filename)
                logo_file.save(logo_path)
                flash('Logo uploaded successfully', 'success')
                return redirect(url_for('settings'))
                
        if 'remove_logo' in request.form:
            if os.path.exists('static/images/logo.png'):
                os.remove('static/images/logo.png')
                flash('Logo removed successfully', 'success')
                return redirect(url_for('settings'))
                
    return render_template('settings.html', logo_present=logo_present)

@app.route('/users')
@login_required
def user_list():
    users = load_users()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if not username or not email or not password:
            flash('Username, email, and password are required', 'error')
            return redirect(url_for('add_user'))
        
        users = load_users()
        
        # Check if username already exists
        if any(user['username'] == username for user in users):
            flash('Username already exists', 'error')
            return redirect(url_for('add_user'))
        
        # Create new user
        new_user = {
            'id': get_next_user_id(),
            'username': username,
            'email': email,
            'password': password,  # In a real app, you should hash this password
            'role': role,
            'created_at': datetime.now().isoformat()
        }
        
        users.append(new_user)
        save_users(users)
        
        flash('User added successfully', 'success')
        return redirect(url_for('user_list'))
    
    return render_template('add_user.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    users = load_users()
    user = next((u for u in users if u.get('id') == user_id), None)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('user_list'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if not username or not email:
            flash('Username and email are required', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Check if username already exists (excluding current user)
        if any(u['username'] == username and u['id'] != user_id for u in users):
            flash('Username already exists', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Update user
        user['username'] = username
        user['email'] = email
        if password:  # Only update password if provided
            user['password'] = password  # In a real app, you should hash this password
        user['role'] = role
        user['updated_at'] = datetime.now().isoformat()
        
        save_users(users)
        flash('User updated successfully', 'success')
        return redirect(url_for('user_list'))
    
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    users = load_users()
    
    # Find the user
    user = next((u for u in users if u.get('id') == user_id), None)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('user_list'))
    
    # Remove user from list
    users = [u for u in users if u.get('id') != user_id]
    save_users(users)
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('user_list'))

if __name__ == '__main__':
    # Create directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    app.run(host='0.0.0.0', port=8080)
