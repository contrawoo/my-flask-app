
import os
import json
import pandas as pd
from datetime import datetime

# Data storage paths
DATA_DIR = 'data'
CUSTOMERS_FILE = os.path.join(DATA_DIR, 'customers.json')

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

def load_customers():
    if os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_customers(customers):
    with open(CUSTOMERS_FILE, 'w') as f:
        json.dump(customers, f, indent=2)

def get_next_customer_id():
    customers = load_customers()
    return max([c.get('id', 0) for c in customers], default=0) + 1

def import_excel_customers(excel_file):
    try:
        # Read the Excel file
        df = pd.read_excel(excel_file)
        
        # Load existing customers
        customers = load_customers()
        current_id = get_next_customer_id()
        imported_count = 0
        
        # List of expected columns
        expected_columns = ['name', 'phone', 'email', 'loan_number', 'address']
        
        # Normalize column names (convert to lowercase)
        df.columns = [str(col).lower() for col in df.columns]
        
        # Process each row
        for _, row in df.iterrows():
            # Try to get name from various possible column names
            name = None
            for col in df.columns:
                if 'name' in col.lower():
                    name = row[col]
                    break
            
            if not name or pd.isna(name):
                continue
                
            # Create new customer dictionary
            new_customer = {
                'id': current_id,
                'name': str(name),
                'phone': '',
                'email': '',
                'loan_number': '',
                'address': '',
                'created_at': datetime.now().isoformat()
            }
            
            # Try to get other fields from various column names
            for col in df.columns:
                if pd.isna(row[col]):
                    continue
                    
                col_lower = col.lower()
                if 'phone' in col_lower:
                    new_customer['phone'] = str(row[col])
                elif 'email' in col_lower:
                    new_customer['email'] = str(row[col])
                elif 'loan' in col_lower or 'number' in col_lower:
                    new_customer['loan_number'] = str(row[col])
                elif 'address' in col_lower:
                    new_customer['address'] = str(row[col])
            
            customers.append(new_customer)
            current_id += 1
            imported_count += 1
        
        # Save the updated customer list
        save_customers(customers)
        print(f"Successfully imported {imported_count} customers")
        
    except Exception as e:
        print(f"Error importing customers: {str(e)}")

if __name__ == '__main__':
    # Import customers from the Excel file
    excel_file = 'attached_assets/CUSTOMER DETAILS.xlsx'
    if os.path.exists(excel_file):
        import_excel_customers(excel_file)
    else:
        print(f"File not found: {excel_file}")
