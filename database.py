# database.py
# This file handles all database operations for client management

import sqlite3
import json
from datetime import datetime

def create_connection():
    """Create a connection to the SQLite database"""
    # This creates a file called 'calculator.db' in your project folder
    conn = sqlite3.connect('calculator.db')
    return conn

def setup_database():
    """Create all the tables we need"""
    conn = create_connection()
    cursor = conn.cursor()
    
    # Create the clients table
    # This is like creating a spreadsheet for client information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            tax_id TEXT,
            notes TEXT,
            created_date TEXT,
            updated_date TEXT
        )
    ''')
    
    # Create the calculations table
    # This stores all calculations for each client
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            project_name TEXT,
            warehouse_length REAL,
            warehouse_width REAL,
            lateral_height REAL,
            roof_height REAL,
            materials_json TEXT,
            total_amount REAL,
            created_date TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    # Create the quotations table
    # This stores generated quotes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            calculation_id INTEGER,
            quote_number TEXT,
            quote_date TEXT,
            valid_until TEXT,
            status TEXT,
            total_amount REAL,
            notes TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (calculation_id) REFERENCES calculations (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database setup complete!")

# CLIENT FUNCTIONS

def add_new_client(company_name, contact_name="", email="", phone="", address="", tax_id="", notes=""):
    """Add a new client to the database"""
    conn = create_connection()
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO clients (company_name, contact_name, email, phone, address, tax_id, notes, created_date, updated_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (company_name, contact_name, email, phone, address, tax_id, notes, current_date, current_date))
    
    client_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return client_id

def get_all_clients():
    """Get a list of all clients"""
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, company_name, contact_name, email, phone 
        FROM clients 
        ORDER BY company_name
    ''')
    
    clients = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for easier use
    client_list = []
    for client in clients:
        client_list.append({
            'id': client[0],
            'company_name': client[1],
            'contact_name': client[2],
            'email': client[3],
            'phone': client[4]
        })
    
    return client_list

def get_client_by_id(client_id):
    """Get details of a specific client"""
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
    client = cursor.fetchone()
    conn.close()
    
    if client:
        return {
            'id': client[0],
            'company_name': client[1],
            'contact_name': client[2],
            'email': client[3],
            'phone': client[4],
            'address': client[5],
            'tax_id': client[6],
            'notes': client[7],
            'created_date': client[8],
            'updated_date': client[9]
        }
    return None

def update_client(client_id, company_name, contact_name="", email="", phone="", address="", tax_id="", notes=""):
    """Update client information"""
    conn = create_connection()
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        UPDATE clients 
        SET company_name=?, contact_name=?, email=?, phone=?, address=?, tax_id=?, notes=?, updated_date=?
        WHERE id=?
    ''', (company_name, contact_name, email, phone, address, tax_id, notes, current_date, client_id))
    
    conn.commit()
    conn.close()

def delete_client(client_id):
    """Delete a client and all their data"""
    conn = create_connection()
    cursor = conn.cursor()
    
    # Delete client's calculations first
    cursor.execute('DELETE FROM calculations WHERE client_id = ?', (client_id,))
    cursor.execute('DELETE FROM quotations WHERE client_id = ?', (client_id,))
    cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    
    conn.commit()
    conn.close()

# CALCULATION FUNCTIONS

def save_calculation(client_id, project_name, length, width, lateral_height, roof_height, materials_dict, total_amount):
    """Save a calculation for a client"""
    conn = create_connection()
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    materials_json = json.dumps(materials_dict)  # Convert dictionary to JSON string
    
    cursor.execute('''
        INSERT INTO calculations (client_id, project_name, warehouse_length, warehouse_width, 
                                 lateral_height, roof_height, materials_json, total_amount, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, project_name, length, width, lateral_height, roof_height, materials_json, total_amount, current_date))
    
    calculation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return calculation_id

def get_client_calculations(client_id):
    """Get all calculations for a specific client"""
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, project_name, warehouse_length, warehouse_width, total_amount, created_date
        FROM calculations 
        WHERE client_id = ?
        ORDER BY created_date DESC
    ''', (client_id,))
    
    calculations = cursor.fetchall()
    conn.close()
    
    calc_list = []
    for calc in calculations:
        calc_list.append({
            'id': calc[0],
            'project_name': calc[1],
            'length': calc[2],
            'width': calc[3],
            'total_amount': calc[4],
            'created_date': calc[5]
        })
    
    return calc_list

def get_calculation_details(calculation_id):
    """Get full details of a specific calculation"""
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM calculations WHERE id = ?', (calculation_id,))
    calc = cursor.fetchone()
    conn.close()
    
    if calc:
        return {
            'id': calc[0],
            'client_id': calc[1],
            'project_name': calc[2],
            'warehouse_length': calc[3],
            'warehouse_width': calc[4],
            'lateral_height': calc[5],
            'roof_height': calc[6],
            'materials': json.loads(calc[7]),  # Convert JSON string back to dictionary
            'total_amount': calc[8],
            'created_date': calc[9]
        }
    return None

def delete_calculation(calculation_id):
    """Delete a specific calculation"""
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM calculations WHERE id = ?', (calculation_id,))
    
    conn.commit()
    conn.close()

# SEARCH FUNCTIONS

def search_clients(search_term):
    """Search for clients by name, email, or phone"""
    conn = create_connection()
    cursor = conn.cursor()
    
    search_pattern = f'%{search_term}%'
    
    cursor.execute('''
        SELECT id, company_name, contact_name, email, phone
        FROM clients 
        WHERE company_name LIKE ? OR contact_name LIKE ? OR email LIKE ? OR phone LIKE ?
        ORDER BY company_name
    ''', (search_pattern, search_pattern, search_pattern, search_pattern))
    
    clients = cursor.fetchall()
    conn.close()
    
    client_list = []
    for client in clients:
        client_list.append({
            'id': client[0],
            'company_name': client[1],
            'contact_name': client[2],
            'email': client[3],
            'phone': client[4]
        })
    
    return client_list

# QUOTATION FUNCTIONS

def save_quotation(client_id, calculation_id, quote_number, total_amount, valid_days=30, notes=""):
    """Save a quotation record"""
    conn = create_connection()
    cursor = conn.cursor()
    
    current_date = datetime.now()
    quote_date = current_date.strftime("%Y-%m-%d")
    valid_until = (current_date + datetime.timedelta(days=valid_days)).strftime("%Y-%m-%d")
    
    cursor.execute('''
        INSERT INTO quotations (client_id, calculation_id, quote_number, quote_date, 
                              valid_until, status, total_amount, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, calculation_id, quote_number, quote_date, valid_until, 'draft', total_amount, notes))
    
    quote_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return quote_id

def get_client_quotations(client_id):
    """Get all quotations for a specific client"""
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, quote_number, quote_date, valid_until, status, total_amount
        FROM quotations 
        WHERE client_id = ?
        ORDER BY quote_date DESC
    ''', (client_id,))
    
    quotes = cursor.fetchall()
    conn.close()
    
    quote_list = []
    for quote in quotes:
        quote_list.append({
            'id': quote[0],
            'quote_number': quote[1],
            'quote_date': quote[2],
            'valid_until': quote[3],
            'status': quote[4],
            'total_amount': quote[5]
        })
    
    return quote_list

# Run this when the file is imported to ensure database exists
if __name__ == "__main__":
    setup_database()
