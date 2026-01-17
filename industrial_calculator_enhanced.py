import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
import os
from fpdf import FPDF
import ast

# ----------------------------
# DATABASE SETUP (SQLite)
# ----------------------------

DB_PATH = "rigc_app.db"
PRODUCTS_CSV_PATH = "products.csv"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                tax_id TEXT,
                notes TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                unit_price REAL NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id TEXT UNIQUE NOT NULL,
                client_id INTEGER NOT NULL,
                project_name TEXT,
                date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Draft',
                notes TEXT,
                included_charges TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS quote_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                discount_type TEXT DEFAULT 'none',
                discount_value REAL DEFAULT 0,
                auto_imported BOOLEAN DEFAULT 0,
                FOREIGN KEY (quote_id) REFERENCES quotes(quote_id)
            )
        """)
        
        # Migration: Add discount columns if they don't exist
        try:
            cur.execute("SELECT discount_type FROM quote_items LIMIT 1")
        except sqlite3.OperationalError:
            # Columns don't exist, add them
            cur.execute("ALTER TABLE quote_items ADD COLUMN discount_type TEXT DEFAULT 'none'")
            cur.execute("ALTER TABLE quote_items ADD COLUMN discount_value REAL DEFAULT 0")
            conn.commit()

        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            samples = [
                ("Steel Beam IPE 200", "European standard I-beam", 125.50),
                ("Galvanized Sheet 2mm", "Corrosion-resistant roofing", 45.75),
                ("Anchor Bolts M20", "Heavy-duty foundation bolts", 8.90),
            ]
            cur.executemany(
                "INSERT INTO products (name, description, unit_price) VALUES (?, ?, ?)",
                samples
            )
        conn.commit()

if not os.path.exists(DB_PATH):
    init_db()
else:
    # Run migration on existing database
    init_db()

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def query_db(query, params=(), fetch_one=False, fetch_all=False):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch_one:
            return cur.fetchone()
        elif fetch_all:
            return cur.fetchall()
        else:
            conn.commit()
            return None

def get_next_quote_id():
    year = datetime.now().year
    result = query_db(
        f"SELECT quote_id FROM quotes WHERE quote_id LIKE 'COT-{year}-%' ORDER BY quote_id DESC LIMIT 1",
        fetch_one=True
    )
    if not result:
        return f"COT-{year}-001"
    last_id = result[0]
    try:
        num = int(last_id.split("-")[-1])
        return f"COT-{year}-{num+1:03d}"
    except:
        return f"COT-{year}-001"

def add_client(company, contact="", email="", phone="", address="", tax_id="", notes=""):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO clients (company_name, contact_name, email, phone, address, tax_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (company, contact, email, phone, address, tax_id, notes))
        conn.commit()
        return cur.lastrowid

def get_all_clients():
    rows = query_db("SELECT * FROM clients ORDER BY company_name", fetch_all=True)
    return [dict(row) for row in rows]

def get_client_by_id(client_id):
    row = query_db("SELECT * FROM clients WHERE id = ?", (client_id,), fetch_one=True)
    return dict(row) if row else None

def save_quote_to_db(client_id, project_name, items, total, notes, included_charges, status="Draft"):
    quote_id = get_next_quote_id()
    date_str = datetime.now().strftime("%Y-%m-%d")
    charges_str = str(included_charges)

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO quotes (quote_id, client_id, project_name, date, total_amount, status, notes, included_charges)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (quote_id, client_id, project_name, date_str, total, status, notes, charges_str))
        
        for item in items:
            cur.execute("""
                INSERT INTO quote_items (quote_id, product_name, quantity, unit_price, discount_type, discount_value, auto_imported)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (quote_id, item["product_name"], item["quantity"], item["unit_price"],
                  item.get("discount_type", "none"), item.get("discount_value", 0),
                  int(item.get("auto_imported", False))))
        conn.commit()
    return quote_id

def update_quote_status(quote_id, status):
    """Update quote status and convert quote ID to invoice ID when converting to invoice"""
    if status == "Invoiced":
        # Convert COT- to INV- when converting to invoice
        invoice_id = quote_id.replace("COT-", "INV-")
        
        # Check if invoice ID already exists
        existing = query_db("SELECT quote_id FROM quotes WHERE quote_id = ?", (invoice_id,), fetch_one=True)
        if existing:
            # If it already exists, just update the status
            query_db("UPDATE quotes SET status = ? WHERE quote_id = ?", (status, quote_id))
            return quote_id
        
        # Update quote_items first (foreign key constraint)
        query_db("UPDATE quote_items SET quote_id = ? WHERE quote_id = ?", (invoice_id, quote_id))
        # Then update quotes
        query_db("UPDATE quotes SET status = ?, quote_id = ? WHERE quote_id = ?", (status, invoice_id, quote_id))
        return invoice_id
    else:
        query_db("UPDATE quotes SET status = ? WHERE quote_id = ?", (status, quote_id))
        return quote_id

def get_quote_by_id(quote_id):
    quote_row = query_db("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,), fetch_one=True)
    if not quote_row:
        return None, None
    items_rows = query_db("SELECT * FROM quote_items WHERE quote_id = ?", (quote_id,), fetch_all=True)
    items = [dict(row) for row in items_rows]
    return dict(quote_row), items

def delete_quote(quote_id):
    """Delete a quote and all its items"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        # Delete items first (foreign key)
        cur.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
        # Then delete quote
        cur.execute("DELETE FROM quotes WHERE quote_id = ?", (quote_id,))
        conn.commit()

def get_all_quotes_for_client(client_id):
    """Get all quotes for a specific client"""
    quotes_rows = query_db(
        "SELECT quote_id, project_name, date, total_amount, status, notes, included_charges FROM quotes WHERE client_id = ? ORDER BY date DESC",
        (client_id,),
        fetch_all=True
    )
    return [dict(row) for row in quotes_rows]

def get_products_for_dropdown():
    rows = query_db("SELECT id, name, description, unit_price FROM products ORDER BY name", fetch_all=True)
    return [dict(row) for row in rows]

def add_product(name, description, unit_price):
    """Add a new product to the database"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (name, description, unit_price)
                VALUES (?, ?, ?)
            """, (name, description, unit_price))
            conn.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  # Product name already exists

def update_product(product_id, name, description, unit_price):
    """Update an existing product"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE products 
                SET name = ?, description = ?, unit_price = ?
                WHERE id = ?
            """, (name, description, unit_price, product_id))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def delete_product(product_id):
    """Delete a product"""
    query_db("DELETE FROM products WHERE id = ?", (product_id,))

def sync_products_from_csv(csv_file_path=PRODUCTS_CSV_PATH):
    """Sync products from CSV file to database"""
    if not os.path.exists(csv_file_path):
        return None, "CSV file not found"
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file_path)
        
        # Validate required columns
        required_columns = ['name', 'unit_price']
        if not all(col in df.columns for col in required_columns):
            return None, f"CSV must have columns: {', '.join(required_columns)}"
        
        # Optional description column
        if 'description' not in df.columns:
            df['description'] = ''
        
        # Clean data
        df['name'] = df['name'].str.strip()
        df['description'] = df['description'].fillna('').str.strip()
        df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
        
        # Remove invalid rows
        df = df.dropna(subset=['name', 'unit_price'])
        df = df[df['unit_price'] > 0]
        
        if df.empty:
            return None, "No valid products found in CSV"
        
        # Sync to database
        added = 0
        updated = 0
        errors = []
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            for _, row in df.iterrows():
                try:
                    # Check if product exists
                    existing = cur.execute(
                        "SELECT id FROM products WHERE name = ?", 
                        (row['name'],)
                    ).fetchone()
                    
                    if existing:
                        # Update existing product
                        cur.execute("""
                            UPDATE products 
                            SET description = ?, unit_price = ?
                            WHERE name = ?
                        """, (row['description'], row['unit_price'], row['name']))
                        updated += 1
                    else:
                        # Insert new product
                        cur.execute("""
                            INSERT INTO products (name, description, unit_price)
                            VALUES (?, ?, ?)
                        """, (row['name'], row['description'], row['unit_price']))
                        added += 1
                except Exception as e:
                    errors.append(f"{row['name']}: {str(e)}")
            
            conn.commit()
        
        message = f"✅ Sincronizado: {added} agregados, {updated} actualizados"
        if errors:
            message += f"\n⚠️ {len(errors)} errores"
        
        return {'added': added, 'updated': updated, 'errors': errors}, message
        
    except Exception as e:
        return None, f"Error reading CSV: {str(e)}"

def create_sample_csv():
    """Create a sample products.csv file"""
    sample_data = {
        'name': [
            'Steel Beam IPE 200',
            'Galvanized Sheet 2mm',
            'Anchor Bolts M20',
            'Concrete Mix 25MPa',
            'Rebar 12mm'
        ],
        'description': [
            'European standard I-beam',
            'Corrosion-resistant roofing',
            'Heavy-duty foundation bolts',
            'High-strength concrete',
            'Reinforcement steel bar'
        ],
        'unit_price': [125.50, 45.75, 8.90, 95.00, 12.50]
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv(PRODUCTS_CSV_PATH, index=False)
    return df

# ----------------------------
# QUOTATION LOGIC
# ----------------------------

def calculate_item_discount(unit_price, quantity, discount_type, discount_value):
    """Calculate discount for a single item"""
    subtotal = unit_price * quantity
    if discount_type == "percentage":
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == "fixed":
        discount_amount = discount_value
    else:
        discount_amount = 0
    return discount_amount

def calculate_quote(products, included_charges):
    items_total = 0
    total_discounts = 0
    
    for p in products:
        qty = float(p.get('quantity', 0))
        price = float(p.get('unit_price', 0))
        discount_type = p.get('discount_type', 'none')
        discount_value = float(p.get('discount_value', 0))
        
        subtotal = qty * price
        discount = calculate_item_discount(price, qty, discount_type, discount_value)
        
        items_total += subtotal
        total_discounts += discount
    
    # Apply discounts first
    items_after_discount = items_total - total_discounts
    
    supervision = items_after_discount * 0.10 if included_charges.get('supervision', True) else 0.0
    admin = items_after_discount * 0.04 if included_charges.get('admin', True) else 0.0
    insurance = items_after_discount * 0.01 if included_charges.get('insurance', True) else 0.0
    transport = items_after_discount * 0.03 if included_charges.get('transport', True) else 0.0
    contingency = items_after_discount * 0.03 if included_charges.get('contingency', True) else 0.0
    subtotal = items_after_discount + supervision + admin + insurance + transport + contingency
    itbis = subtotal * 0.18
    grand_total = subtotal + itbis
    
    return {
        'items_total': items_total,
        'total_discounts': total_discounts,
        'items_after_discount': items_after_discount,
        'supervision': supervision,
        'admin': admin,
        'insurance': insurance,
        'transport': transport,
        'contingency': contingency,
        'subtotal_general': subtotal,
        'itbis': itbis,
        'grand_total': grand_total,
    }

# ----------------------------
# PDF GENERATOR
# ----------------------------

class QuotePDF(FPDF):
    """Modern Quote PDF Generator"""
    
    def header(self):
        # Add a colored header bar
        self.set_fill_color(41, 128, 185)  # Modern blue
        self.rect(0, 0, 210, 40, 'F')
        
        # Add logo if it exists
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 25)  # x, y, width
            logo_offset = 40
        else:
            logo_offset = 10
        
        # Company address in white, font size 6
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 4)  # <-- fixed font size
        self.set_xy(logo_offset, 12)
        address_lines = [
            "Parque Industrial",
            "Disdo, Calle Central No. 1,",
            "Hato Nuevo Palave",
            "Santo Domingo Oeste",
            "Tel: 829-439-8476",
            "RNC: 131-71683-2"
        ]
        for line in address_lines:
            self.cell(0,2, line, 0, 1, "R")  # reduced line height to 4
        
        # Quote label – moved down to avoid overlap
        self.set_font("Helvetica", "B", 16)
        self.set_xy(logo_offset, 28)  # adjusted Y position
        self.cell(0, 8, "COTIZACION", 0, 1, "R")
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, "Parque Industrial Disdo, Calle Central No. 1, Hato Nuevo Palave", 0, 1, "C")
        self.cell(0, 5, "Santo Domingo Oeste | Tel: 829-439-8476 | RNC: 131-71683-2", 0, 1, "C")
        self.cell(0, 5, f"Pagina {self.page_no()}", 0, 0, "C")

    def quote_info(self, quote_data, client_data):
        # Two-column layout for quote info
        self.set_font("Helvetica", "B", 11)
        
        # Left column - Quote details
        self.set_xy(10, 55)
        self.set_fill_color(240, 240, 240)
        self.cell(90, 8, "INFORMACION DE COTIZACION", 0, 1, "L", True)
        
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Cotizacion #:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, quote_data['quote_id'], 0, 1, "L")
        
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Fecha:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, quote_data['date'], 0, 1, "L")
        
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Proyecto:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, quote_data.get('project_name', 'N/A'), 0, 1, "L")
        
        # Right column - Client details
        self.set_xy(110, 55)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.cell(90, 8, "CLIENTE", 0, 1, "L", True)
        
        self.set_font("Helvetica", "", 9)
        self.set_x(110)
        self.cell(40, 6, "Empresa:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.multi_cell(50, 6, client_data['company_name'], 0, "L")
        
        if client_data.get('contact_name'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "Contacto:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['contact_name'], 0, 1, "L")
        
        if client_data.get('tax_id'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "RNC/Cedula:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['tax_id'], 0, 1, "L")
        
        if client_data.get('email'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "Email:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['email'], 0, 1, "L")
        
        if client_data.get('phone'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "Telefono:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['phone'], 0, 1, "L")
        
        self.ln(10)

    def items_table(self, items_list):
        # Modern table header
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        
        self.cell(90, 9, "DESCRIPCION", 1, 0, "L", True)
        self.cell(30, 9, "CANTIDAD", 1, 0, "C", True)
        self.cell(35, 9, "PRECIO UNIT.", 1, 0, "R", True)
        self.cell(35, 9, "TOTAL", 1, 1, "R", True)
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        
        # Alternating row colors
        fill = False
        for item in items_list:
            desc = self._clean_text(str(item["product_name"]))
            x = self.get_x()
            y = self.get_y()
            
            # Set alternating background
            if fill:
                self.set_fill_color(245, 245, 245)
            else:
                self.set_fill_color(255, 255, 255)
            
            # Description with word wrap
            if len(desc) > 50:
                self.multi_cell(90, 6, desc, 1, "L", fill)
                lines = len(desc) // 50 + 1
                self.set_xy(x + 90, y)
            else:
                self.cell(90, 6, desc, 1, 0, "L", fill)
            
            self.cell(30, 6, f"{item['quantity']:,.2f}", 1, 0, "C", fill)
            self.cell(35, 6, f"${item['unit_price']:,.2f}", 1, 0, "R", fill)
            total = item["quantity"] * item["unit_price"]
            self.cell(35, 6, f"${total:,.2f}", 1, 1, "R", fill)
            
            fill = not fill
        
        self.ln(5)

    def cost_summary(self, totals, included_charges):
        # Summary box with border
        start_y = self.get_y()
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.5)
        
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(240, 248, 255)
        self.cell(0, 8, "RESUMEN FINANCIERO", 1, 1, "L", True)
        
        self.set_font("Helvetica", "", 9)
        self.set_line_width(0.2)
        
        # Items total
        self.cell(130, 6, "Subtotal de Items:", 1, 0, "L")
        self.cell(60, 6, f"${totals['items_total']:,.2f}", 1, 1, "R")
        
        # Show discounts if any
        if totals.get('total_discounts', 0) > 0:
            self.set_text_color(220, 53, 69)  # Red for discounts
            self.cell(130, 6, "Descuentos Aplicados:", 1, 0, "L")
            self.cell(60, 6, f"-${totals['total_discounts']:,.2f}", 1, 1, "R")
            self.set_text_color(0, 0, 0)
            
            self.set_font("Helvetica", "B", 9)
            self.cell(130, 6, "Total Despues de Descuentos:", 1, 0, "L")
            self.cell(60, 6, f"${totals['items_after_discount']:,.2f}", 1, 1, "R")
            self.set_font("Helvetica", "", 9)
        
        # Additional charges
        if included_charges.get('supervision'):
            self.cell(130, 6, "Supervision Tecnica (10%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['supervision']:,.2f}", 1, 1, "R")
        if included_charges.get('admin'):
            self.cell(130, 6, "Gastos Administrativos (4%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['admin']:,.2f}", 1, 1, "R")
        if included_charges.get('insurance'):
            self.cell(130, 6, "Seguro de Riesgo (1%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['insurance']:,.2f}", 1, 1, "R")
        if included_charges.get('transport'):
            self.cell(130, 6, "Transporte (3%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['transport']:,.2f}", 1, 1, "R")
        if included_charges.get('contingency'):
            self.cell(130, 6, "Imprevisto (3%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['contingency']:,.2f}", 1, 1, "R")
        
        # Subtotal
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(230, 240, 250)
        self.cell(130, 7, "SUBTOTAL GENERAL:", 1, 0, "L", True)
        self.cell(60, 7, f"${totals['subtotal_general']:,.2f}", 1, 1, "R", True)
        
        # Tax
        self.set_font("Helvetica", "", 9)
        self.cell(130, 6, "ITBIS (18%):", 1, 0, "L")
        self.cell(60, 6, f"${totals['itbis']:,.2f}", 1, 1, "R")
        
        # Grand total with highlight
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        self.cell(130, 10, "TOTAL GENERAL:", 1, 0, "L", True)
        self.cell(60, 10, f"${totals['grand_total']:,.2f}", 1, 1, "R", True)
        
        # Reset colors
        self.set_text_color(0, 0, 0)
        self.set_line_width(0.2)

    def notes_section(self, notes):
        """Add notes section to quote"""
        if notes and notes.strip():
            self.ln(8)
            self.set_font("Helvetica", "B", 10)
            self.set_fill_color(240, 248, 255)
            self.cell(0, 7, "NOTAS Y CONDICIONES", 0, 1, "L", True)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(60, 60, 60)
            self.multi_cell(0, 5, self._clean_text(notes), 0, "L")
            self.set_text_color(0, 0, 0)

    def _clean_text(self, text):
        replacements = {
            "\u2022": "-", "\u2013": "-", "\u2014": "--",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode('latin1', errors='replace').decode('latin1')


class InvoicePDF(FPDF):
    """Modern Invoice PDF Generator"""
    
    def header(self):
        # Add a colored header bar - different color for invoices
        self.set_fill_color(231, 76, 60)  # Red/Orange for invoice
        self.rect(0, 0, 210, 40, 'F')
        
        # Add logo if it exists
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 25)  # x, y, width
            logo_offset = 40
        else:
            logo_offset = 10
        
        # Company address in white, font size 6
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 4)  # <-- fixed font size
        self.set_xy(logo_offset, 12)
        address_lines = [
            "Parque Industrial",
            "Disdo, Calle Central No. 1,",
            "Hato Nuevo Palave",
            "Santo Domingo Oeste",
            "Tel: 829-439-8476",
            "RNC: 131-71683-2"
        ]
        for line in address_lines:
            self.cell(0,2, line, 0, 1, "R")  # reduced line height to 4
        
        # Invoice label – moved down to avoid overlap
        self.set_font("Helvetica", "B", 16)
        self.set_xy(logo_offset, 28)  # adjusted Y position
        self.cell(0, 8, "FACTURA", 0, 1, "R")
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, "Parque Industrial Disdo, Calle Central No. 1, Hato Nuevo Palave", 0, 1, "C")
        self.cell(0, 5, "Santo Domingo Oeste | Tel: 829-439-8476 | RNC: 131-71683-2", 0, 1, "C")
        self.cell(0, 5, f"Pagina {self.page_no()}", 0, 0, "C")

    def invoice_info(self, quote_data, client_data):
        # Two-column layout for invoice info
        self.set_font("Helvetica", "B", 11)
        
        # Left column - Invoice details
        self.set_xy(10, 55)
        self.set_fill_color(255, 240, 240)
        self.cell(90, 8, "INFORMACION DE FACTURA", 0, 1, "L", True)
        
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Factura #:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, quote_data['quote_id'], 0, 1, "L")
        
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Fecha Emision:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, quote_data['date'], 0, 1, "L")
        
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Proyecto:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, quote_data.get('project_name', 'N/A'), 0, 1, "L")
        
        # Payment terms
        self.set_font("Helvetica", "", 9)
        self.set_x(10)
        self.cell(40, 6, "Terminos:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, "Net 30", 0, 1, "L")
        
        # Right column - Client details
        self.set_xy(110, 55)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(255, 240, 240)
        self.cell(90, 8, "FACTURAR A", 0, 1, "L", True)
        
        self.set_font("Helvetica", "", 9)
        self.set_x(110)
        self.cell(40, 6, "Empresa:", 0, 0, "L")
        self.set_font("Helvetica", "B", 9)
        self.multi_cell(50, 6, client_data['company_name'], 0, "L")
        
        if client_data.get('contact_name'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "Contacto:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['contact_name'], 0, 1, "L")
        
        if client_data.get('tax_id'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "RNC/Cedula:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['tax_id'], 0, 1, "L")
        
        if client_data.get('email'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "Email:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['email'], 0, 1, "L")
        
        if client_data.get('phone'):
            self.set_font("Helvetica", "", 9)
            self.set_x(110)
            self.cell(40, 6, "Telefono:", 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, client_data['phone'], 0, 1, "L")
        
        self.ln(10)

    def items_table(self, items_list):
        # Modern table header - different color for invoices
        self.set_fill_color(231, 76, 60)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        
        self.cell(90, 9, "DESCRIPCION", 1, 0, "L", True)
        self.cell(30, 9, "CANTIDAD", 1, 0, "C", True)
        self.cell(35, 9, "PRECIO UNIT.", 1, 0, "R", True)
        self.cell(35, 9, "TOTAL", 1, 1, "R", True)
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        
        # Alternating row colors
        fill = False
        for item in items_list:
            desc = self._clean_text(str(item["product_name"]))
            x = self.get_x()
            y = self.get_y()
            
            # Set alternating background
            if fill:
                self.set_fill_color(245, 245, 245)
            else:
                self.set_fill_color(255, 255, 255)
            
            # Description with word wrap
            if len(desc) > 50:
                self.multi_cell(90, 6, desc, 1, "L", fill)
                lines = len(desc) // 50 + 1
                self.set_xy(x + 90, y)
            else:
                self.cell(90, 6, desc, 1, 0, "L", fill)
            
            self.cell(30, 6, f"{item['quantity']:,.2f}", 1, 0, "C", fill)
            self.cell(35, 6, f"${item['unit_price']:,.2f}", 1, 0, "R", fill)
            total = item["quantity"] * item["unit_price"]
            self.cell(35, 6, f"${total:,.2f}", 1, 1, "R", fill)
            
            fill = not fill
        
        self.ln(5)

    def cost_summary(self, totals, included_charges):
        # Summary box with border
        start_y = self.get_y()
        self.set_draw_color(231, 76, 60)
        self.set_line_width(0.5)
        
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(255, 245, 245)
        self.cell(0, 8, "RESUMEN DE PAGO", 1, 1, "L", True)
        
        self.set_font("Helvetica", "", 9)
        self.set_line_width(0.2)
        
        # Items total
        self.cell(130, 6, "Subtotal de Items:", 1, 0, "L")
        self.cell(60, 6, f"${totals['items_total']:,.2f}", 1, 1, "R")
        
        # Show discounts if any
        if totals.get('total_discounts', 0) > 0:
            self.set_text_color(220, 53, 69)  # Red for discounts
            self.cell(130, 6, "Descuentos Aplicados:", 1, 0, "L")
            self.cell(60, 6, f"-${totals['total_discounts']:,.2f}", 1, 1, "R")
            self.set_text_color(0, 0, 0)
            
            self.set_font("Helvetica", "B", 9)
            self.cell(130, 6, "Total Despues de Descuentos:", 1, 0, "L")
            self.cell(60, 6, f"${totals['items_after_discount']:,.2f}", 1, 1, "R")
            self.set_font("Helvetica", "", 9)
        
        # Additional charges
        if included_charges.get('supervision'):
            self.cell(130, 6, "Supervision Tecnica (10%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['supervision']:,.2f}", 1, 1, "R")
        if included_charges.get('admin'):
            self.cell(130, 6, "Gastos Administrativos (4%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['admin']:,.2f}", 1, 1, "R")
        if included_charges.get('insurance'):
            self.cell(130, 6, "Seguro de Riesgo (1%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['insurance']:,.2f}", 1, 1, "R")
        if included_charges.get('transport'):
            self.cell(130, 6, "Transporte (3%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['transport']:,.2f}", 1, 1, "R")
        if included_charges.get('contingency'):
            self.cell(130, 6, "Imprevisto (3%):", 1, 0, "L")
            self.cell(60, 6, f"${totals['contingency']:,.2f}", 1, 1, "R")
        
        # Subtotal
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(255, 235, 235)
        self.cell(130, 7, "SUBTOTAL GENERAL:", 1, 0, "L", True)
        self.cell(60, 7, f"${totals['subtotal_general']:,.2f}", 1, 1, "R", True)
        
        # Tax
        self.set_font("Helvetica", "", 9)
        self.cell(130, 6, "ITBIS (18%):", 1, 0, "L")
        self.cell(60, 6, f"${totals['itbis']:,.2f}", 1, 1, "R")
        
        # Grand total with highlight
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(231, 76, 60)
        self.set_text_color(255, 255, 255)
        self.cell(130, 10, "TOTAL A PAGAR:", 1, 0, "L", True)
        self.cell(60, 10, f"${totals['grand_total']:,.2f}", 1, 1, "R", True)
        
        # Reset colors
        self.set_text_color(0, 0, 0)
        self.set_line_width(0.2)
        
        # Payment instructions
        self.ln(5)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 4, "Favor realizar pago mediante transferencia bancaria o cheque a nombre de RIGC INDUSTRIAL.\nPara consultas sobre esta factura, contactar al 829-439-8476.", 0, "L")

    def notes_section(self, notes):
        """Add notes section to invoice"""
        if notes and notes.strip():
            self.ln(5)
            self.set_font("Helvetica", "B", 10)
            self.set_fill_color(255, 245, 245)
            self.cell(0, 7, "NOTAS ADICIONALES", 0, 1, "L", True)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(60, 60, 60)
            self.multi_cell(0, 5, self._clean_text(notes), 0, "L")
            self.set_text_color(0, 0, 0)

    def _clean_text(self, text):
        replacements = {
            "\u2022": "-", "\u2013": "-", "\u2014": "--",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode('latin1', errors='replace').decode('latin1')

# ----------------------------
# AUTHENTICATION
# ----------------------------

MAX_ATTEMPTS = 3
USER_PASSCODES = {"fabian": "rams20", "admin": "admin123"}

def show_login_page():
    st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            height: 100vh; background: radial-gradient(circle at top, #0f0f19 0%, #050510 100%);
        }
        .login-title { font-size: 40px; font-weight: 800; text-align: center;
            background: linear-gradient(135deg, #00ffff, #0099ff, #ff00ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;
        }
        .login-subtitle { text-align: center; color: rgba(255,255,255,0.6); font-size: 14px; letter-spacing: 1.5px; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="text-align:center; font-size:72px; margin:2rem 0;">🏗️</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">RIGC 2030</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">SISTEMA DE CÁLCULO INDUSTRIAL</div>', unsafe_allow_html=True)

    if st.session_state.attempts >= MAX_ATTEMPTS:
        st.error("⚠️ Máximo de intentos alcanzado. Contacte al administrador.")
        return

    with st.form("login_form"):
        username = st.text_input("👤 Usuario")
        password = st.text_input("🔒 Contraseña", type="password")
        submit = st.form_submit_button("ACCEDER", use_container_width=True)
        if submit:
            if username in USER_PASSCODES and password == USER_PASSCODES[username]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Acceso exitoso")
                st.rerun()
            else:
                st.session_state.attempts += 1
                remaining = MAX_ATTEMPTS - st.session_state.attempts
                st.error(f"❌ Credenciales incorrectas. Intentos restantes: {remaining}")
                if remaining <= 0:
                    st.rerun()

# ----------------------------
# MAIN APP
# ----------------------------

def show_main_app():
    # Initialize session state
    defaults = {
        'authenticated': False,
        'attempts': 0,
        'username': "",
        'current_client_id': None,
        'quote_products': [],
        'included_charges': {
            'supervision': True,
            'admin': True,
            'insurance': True,
            'transport': True,
            'contingency': True,
        },
        'show_product_manager': False,
        'editing_product_id': None,
        'editing_quote_id': None,
        'editing_quote_data': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Sidebar
    st.sidebar.header("👥 Gestión de Clientes")
    mode = st.sidebar.radio("Modo:", ["Seleccionar Cliente", "Nuevo Cliente"])
    
    if mode == "Seleccionar Cliente":
        clients = get_all_clients()
        if len(clients) == 0:
            st.sidebar.info("No hay clientes.")
        else:
            names = ["Seleccione..."] + [c["company_name"] for c in clients]
            idx = st.sidebar.selectbox("Cliente:", range(len(names)), format_func=lambda x: names[x])
            if idx > 0:
                client = clients[idx - 1]
                st.session_state.current_client_id = client["id"]
                st.sidebar.success(f"✅ {client['company_name']}")
    else:
        with st.sidebar.form("new_client"):
            company = st.text_input("Empresa *")
            contact = st.text_input("Contacto")
            email = st.text_input("Email")
            phone = st.text_input("Teléfono")
            address = st.text_area("Dirección")
            tax_id = st.text_input("RNC/Cédula")
            notes = st.text_area("Notas")
            if st.form_submit_button("🟥 Guardar Cliente"):
                if company:
                    cid = add_client(company, contact, email, phone, address, tax_id, notes)
                    st.session_state.current_client_id = cid
                    st.sidebar.success("✅ Cliente guardado!")
                    st.rerun()
                else:
                    st.sidebar.error("Empresa requerida.")

    st.sidebar.markdown("---")
    
    # Product Management Toggle
    if st.sidebar.button("📦 Gestión de Productos", use_container_width=True):
        st.session_state.show_product_manager = not st.session_state.show_product_manager
    
    if st.sidebar.button("🟥 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # Header
    st.markdown('<h1 style="text-align:center; font-size:48px;">RIGC 2030</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#a3a3a3; margin-top:-10px;">Sistema de Cálculo Industrial</p>', unsafe_allow_html=True)

    # Product Management Section
    if st.session_state.show_product_manager:
        st.markdown("---")
        st.markdown("## 📦 Gestión de Productos")
        
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Productos", "📁 Sincronizar desde CSV", "➕ Agregar/Editar Producto"])
        
        with tab1:
            products = get_products_for_dropdown()
            if products:
                # Display products in a table
                products_df = pd.DataFrame(products)
                products_df = products_df.rename(columns={
                    'id': 'ID',
                    'name': 'Nombre',
                    'description': 'Descripción',
                    'unit_price': 'Precio Unitario'
                })
                
                st.dataframe(
                    products_df,
                    column_config={
                        "Precio Unitario": st.column_config.NumberColumn(
                            "Precio Unitario",
                            format="$%.2f"
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                st.info(f"📊 Total de productos: {len(products)}")
                
                # Edit/Delete buttons
                st.markdown("#### Acciones")
                col1, col2 = st.columns([3, 1])
                with col1:
                    product_to_edit = st.selectbox(
                        "Seleccionar producto para editar/eliminar",
                        options=[p['id'] for p in products],
                        format_func=lambda x: next(p['name'] for p in products if p['id'] == x)
                    )
                with col2:
                    if st.button("✏️ Editar", use_container_width=True):
                        st.session_state.editing_product_id = product_to_edit
                        st.rerun()
                
                # Delete with confirmation
                if st.button("🗑️ Eliminar Producto Seleccionado", type="secondary"):
                    st.session_state.confirm_delete_product = product_to_edit
                
                # Confirmation dialog for delete
                if 'confirm_delete_product' in st.session_state:
                    product = next(p for p in products if p['id'] == st.session_state.confirm_delete_product)
                    st.warning(f"⚠️ ¿Está seguro que desea eliminar '{product['name']}'?")
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("✅ Sí, Eliminar", type="primary"):
                            delete_product(st.session_state.confirm_delete_product)
                            del st.session_state.confirm_delete_product
                            st.success("Producto eliminado exitosamente")
                            st.rerun()
                    with col2:
                        if st.button("❌ Cancelar"):
                            del st.session_state.confirm_delete_product
                            st.rerun()
            else:
                st.info("No hay productos en el catálogo. Agregue uno en la pestaña siguiente.")
        
        with tab2:
            st.markdown("### 📁 Cargar Productos desde CSV")
            
            # Info box
            st.info("""
            **Formato del CSV:**
            - Columnas requeridas: `name`, `unit_price`
            - Columna opcional: `description`
            - El archivo debe llamarse `products.csv` o puede subirlo manualmente
            """)
            
            # Check if products.csv exists
            if os.path.exists(PRODUCTS_CSV_PATH):
                st.success(f"✅ Archivo encontrado: `{PRODUCTS_CSV_PATH}`")
                
                # Preview CSV
                try:
                    preview_df = pd.read_csv(PRODUCTS_CSV_PATH)
                    st.markdown("#### Vista Previa del CSV")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    st.caption(f"Mostrando {min(10, len(preview_df))} de {len(preview_df)} productos")
                except Exception as e:
                    st.error(f"Error leyendo CSV: {str(e)}")
                
                # Sync button
                if st.button("🔄 Sincronizar Productos desde CSV", type="primary", use_container_width=True):
                    result, message = sync_products_from_csv()
                    if result:
                        st.success(message)
                        if result['errors']:
                            with st.expander("⚠️ Ver errores"):
                                for error in result['errors']:
                                    st.warning(error)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning(f"⚠️ No se encontró `{PRODUCTS_CSV_PATH}`")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Create sample CSV
                    if st.button("📄 Crear CSV de Ejemplo", use_container_width=True):
                        sample_df = create_sample_csv()
                        st.success(f"✅ Creado: `{PRODUCTS_CSV_PATH}`")
                        st.dataframe(sample_df, use_container_width=True)
                        st.rerun()
                
                with col2:
                    # Download template
                    template_csv = "name,description,unit_price\nProducto Ejemplo,Descripción del producto,100.00\n"
                    st.download_button(
                        "📥 Descargar Plantilla CSV",
                        template_csv,
                        "products_template.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            st.markdown("---")
            
            # Manual CSV upload
            st.markdown("#### 📤 Subir CSV Manualmente")
            uploaded_file = st.file_uploader(
                "Seleccione archivo CSV",
                type=['csv'],
                help="Formato: name, description, unit_price"
            )
            
            if uploaded_file is not None:
                try:
                    # Save uploaded file
                    with open(PRODUCTS_CSV_PATH, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    st.success(f"✅ Archivo guardado como `{PRODUCTS_CSV_PATH}`")
                    
                    # Preview
                    preview_df = pd.read_csv(PRODUCTS_CSV_PATH)
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    
                    # Auto-sync option
                    if st.button("🔄 Sincronizar Ahora", type="primary"):
                        result, message = sync_products_from_csv()
                        if result:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                            
                except Exception as e:
                    st.error(f"Error procesando archivo: {str(e)}")
            
            # Export current products to CSV
            st.markdown("---")
            st.markdown("#### 📥 Exportar Productos Actuales")
            
            if st.button("💾 Exportar a CSV", use_container_width=True):
                products = get_products_for_dropdown()
                if products:
                    export_df = pd.DataFrame(products)
                    export_df = export_df[['name', 'description', 'unit_price']]
                    csv_data = export_df.to_csv(index=False)
                    
                    st.download_button(
                        "📥 Descargar products.csv",
                        csv_data,
                        "products_export.csv",
                        "text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(products)} productos listos para descargar")
                else:
                    st.warning("No hay productos para exportar")
        
        with tab3:
            # Check if editing
            editing_product = None
            if st.session_state.editing_product_id:
                products = get_products_for_dropdown()
                editing_product = next((p for p in products if p['id'] == st.session_state.editing_product_id), None)
            
            with st.form("product_form"):
                st.markdown(f"#### {'✏️ Editar Producto' if editing_product else '➕ Nuevo Producto'}")
                
                name = st.text_input(
                    "Nombre del Producto *",
                    value=editing_product['name'] if editing_product else ""
                )
                description = st.text_area(
                    "Descripción",
                    value=editing_product['description'] if editing_product else ""
                )
                unit_price = st.number_input(
                    "Precio Unitario ($) *",
                    min_value=0.01,
                    step=0.01,
                    value=float(editing_product['unit_price']) if editing_product else 1.00
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button(
                        "💾 Actualizar Producto" if editing_product else "➕ Agregar Producto",
                        use_container_width=True,
                        type="primary"
                    )
                with col2:
                    if editing_product:
                        cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
                        if cancel:
                            st.session_state.editing_product_id = None
                            st.rerun()
                
                if submit:
                    if name and unit_price > 0:
                        if editing_product:
                            # Update existing product
                            success = update_product(
                                editing_product['id'],
                                name,
                                description,
                                unit_price
                            )
                            if success:
                                st.success(f"✅ Producto '{name}' actualizado exitosamente")
                                st.session_state.editing_product_id = None
                                st.rerun()
                            else:
                                st.error("❌ Error: Ya existe un producto con ese nombre")
                        else:
                            # Add new product
                            result = add_product(name, description, unit_price)
                            if result:
                                st.success(f"✅ Producto '{name}' agregado exitosamente")
                                st.rerun()
                            else:
                                st.error("❌ Error: Ya existe un producto con ese nombre")
                    else:
                        st.error("❌ Complete todos los campos requeridos (*)")
        
        st.markdown("---")
        return  # Don't show quote form when in product manager

    if st.session_state.current_client_id:
        client = get_client_by_id(st.session_state.current_client_id)
        # Display client info in a nice card
        st.markdown(f"""
        <div style="background:rgba(41,128,185,0.1); padding:1rem; border-radius:8px; border-left:4px solid #2980b9;">
            <div style="font-size:18px; font-weight:600; color:#2980b9; margin-bottom:0.5rem;">
                👤 Cliente Activo
            </div>
            <div style="font-size:16px; font-weight:500; margin-bottom:0.3rem;">
                {client['company_name']}
            </div>
            <div style="font-size:14px; color:#a3a3a3;">
                {'📞 ' + client.get('contact_name', 'Sin contacto') if client.get('contact_name') else '📞 Sin contacto'}
                {' | 🆔 RNC/Cédula: ' + client.get('tax_id', 'N/A') if client.get('tax_id') else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Seleccione o cree un cliente en la barra lateral.")

    st.divider()

    # Quotation Form
    st.markdown("### 📝 Información de la Cotización")
    
    # Check if we're editing a quote
    editing_mode = st.session_state.editing_quote_id is not None
    if editing_mode:
        st.info(f"✏️ **Modo Edición**: Editando cotización {st.session_state.editing_quote_id}")
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_quote_id = None
            st.session_state.editing_quote_data = None
            st.session_state.quote_products = []
            st.rerun()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        company_name_info = st.text_input("Nombre de Empresa", value="RIGC INDUSTRIAL", key="company_info")
        phone_info = st.text_input("Teléfono", value="809-555-0100", key="phone_info")
    with col2:
        email_info = st.text_input("Email", value="info@rigc.com", key="email_info")
        quoted_by = st.text_input("Cotizado por", value=st.session_state.username)
    with col3:
        validity = st.number_input("Validez (días)", value=30, min_value=1)

    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.current_client_id:
            client = get_client_by_id(st.session_state.current_client_id)
            client_name = st.text_input("Nombre del Cliente", value=client['company_name'], key="client_name_display")
        else:
            client_name = st.text_input("Nombre del Cliente", placeholder="Nombre del cliente", key="client_name_input")
    with col2:
        # Pre-fill project name if editing
        default_project = st.session_state.editing_quote_data.get('project_name', '') if st.session_state.editing_quote_data else ''
        project_name = st.text_input("Proyecto", placeholder="Nombre del proyecto", value=default_project)

    # Pre-fill notes if editing
    default_notes = st.session_state.editing_quote_data.get('notes', '') if st.session_state.editing_quote_data else ''
    notes = st.text_area("Notas adicionales", placeholder="Condiciones especiales...", value=default_notes)

    # Product Selection
    st.markdown("#### ➕ Agregar Producto")
    products_list = get_products_for_dropdown()
    if not products_list:
        st.warning("No hay productos. Use el formulario manual.")
    else:
        selected_id = st.selectbox(
            "Producto desde base de datos",
            options=[p["id"] for p in products_list],
            format_func=lambda x: next(p["name"] for p in products_list if p["id"] == x)
        )
        prod = next(p for p in products_list if p["id"] == selected_id)
        col1, col2 = st.columns(2)
        with col1:
            qty = st.number_input("Cantidad", min_value=0.0, step=1.0, key="db_qty")
        with col2:
            add_discount = st.checkbox("Agregar Descuento", key="db_discount_check")
        
        if add_discount:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                discount_type_db = st.selectbox("Tipo", ["percentage", "fixed"], 
                                            format_func=lambda x: {"percentage": "Porcentaje (%)", "fixed": "Monto Fijo ($)"}[x],
                                            key="db_disc_type")
            with col_d2:
                if discount_type_db == "percentage":
                    discount_value_db = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.1, value=0.0, key="db_disc_val")
                else:
                    discount_value_db = st.number_input("Descuento ($)", min_value=0.0, step=0.01, value=0.0, key="db_disc_val")
        else:
            discount_type_db = "none"
            discount_value_db = 0.0
        
        if st.button("➕ Agregar desde DB"):
            if qty > 0:
                st.session_state.quote_products.append({
                    "product_name": prod["name"],
                    "quantity": qty,
                    "unit_price": prod["unit_price"],
                    "discount_type": discount_type_db,
                    "discount_value": discount_value_db
                })
                st.rerun()
            else:
                st.warning("La cantidad debe ser mayor a 0")

    # Manual Product Entry
    with st.form("manual_product"):
        st.markdown("#### ➕ Producto Manual")
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        name = col1.text_input("Nombre")
        qty = col2.number_input("Cantidad", min_value=0.0, step=1.0)
        price = col3.number_input("Precio Unit.", min_value=0.0, step=0.01)
        
        # Discount options
        st.markdown("##### 💰 Descuento (Opcional)")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            discount_type = st.selectbox("Tipo de Descuento", ["none", "percentage", "fixed"], 
                                        format_func=lambda x: {"none": "Sin Descuento", "percentage": "Porcentaje (%)", "fixed": "Monto Fijo ($)"}[x])
        with col_d2:
            if discount_type != "none":
                if discount_type == "percentage":
                    discount_value = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
                else:
                    discount_value = st.number_input("Descuento ($)", min_value=0.0, step=0.01, value=0.0)
            else:
                discount_value = 0.0
        
        submitted = col4.form_submit_button("➕")
        if submitted and name and qty > 0 and price > 0:
            st.session_state.quote_products.append({
                "product_name": name,
                "quantity": qty,
                "unit_price": price,
                "discount_type": discount_type,
                "discount_value": discount_value
            })
            st.rerun()

    # Quote Display & Controls
    if st.session_state.quote_products:
        # Calculate item discounts for display
        for p in st.session_state.quote_products:
            discount_amt = calculate_item_discount(
                p.get('unit_price', 0),
                p.get('quantity', 0),
                p.get('discount_type', 'none'),
                p.get('discount_value', 0)
            )
            p['discount_amount'] = discount_amt
            p['final_price'] = (p.get('quantity', 0) * p.get('unit_price', 0)) - discount_amt
        
        df = pd.DataFrame(st.session_state.quote_products)
        df["subtotal"] = df["quantity"] * df["unit_price"]
        
        edited = st.data_editor(
            df,
            column_config={
                "product_name": st.column_config.TextColumn("Producto", width="large"),
                "quantity": st.column_config.NumberColumn("Cantidad", format="%.2f"),
                "unit_price": st.column_config.NumberColumn("Precio Unit. ($)", format="%.2f"),
                "discount_type": st.column_config.SelectboxColumn(
                    "Tipo Desc.",
                    options=["none", "percentage", "fixed"],
                    width="small"
                ),
                "discount_value": st.column_config.NumberColumn("Valor Desc.", format="%.2f"),
                "discount_amount": st.column_config.NumberColumn("Desc. ($)", disabled=True, format="%.2f"),
                "subtotal": st.column_config.NumberColumn("Subtotal ($)", disabled=True, format="%.2f"),
                "final_price": st.column_config.NumberColumn("Precio Final ($)", disabled=True, format="%.2f")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        st.session_state.quote_products = edited.to_dict('records')

        # Charge toggles
        st.markdown("### ⚙️ Incluir Cargos Adicionales")
        cols = st.columns(5)
        charges = st.session_state.included_charges
        charges['supervision'] = cols[0].checkbox("Supervisión\n(10%)", value=charges['supervision'])
        charges['admin'] = cols[1].checkbox("Admin.\n(4%)", value=charges['admin'])
        charges['insurance'] = cols[2].checkbox("Seguro\n(1%)", value=charges['insurance'])
        charges['transport'] = cols[3].checkbox("Transporte\n(3%)", value=charges['transport'])
        charges['contingency'] = cols[4].checkbox("Imprevisto\n(3%)", value=charges['contingency'])

        totals = calculate_quote(st.session_state.quote_products, charges)

        # Metrics
        st.markdown("### 💰 Resumen de Costos")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Items", f"${totals['items_total']:,.2f}")
            if totals.get('total_discounts', 0) > 0:
                st.metric("Descuentos", f"-${totals['total_discounts']:,.2f}", delta=f"-{(totals['total_discounts']/totals['items_total']*100):.1f}%", delta_color="inverse")
                st.metric("Después de Desc.", f"${totals['items_after_discount']:,.2f}")
            if charges['supervision']:
                st.metric("Supervisión (10%)", f"${totals['supervision']:,.2f}")
            if charges['admin']:
                st.metric("Admin. (4%)", f"${totals['admin']:,.2f}")
        with c2:
            if charges['insurance']:
                st.metric("Seguro (1%)", f"${totals['insurance']:,.2f}")
            if charges['transport']:
                st.metric("Transporte (3%)", f"${totals['transport']:,.2f}")
            if charges['contingency']:
                st.metric("Imprevisto (3%)", f"${totals['contingency']:,.2f}")
        with c3:
            st.metric("Subtotal", f"${totals['subtotal_general']:,.2f}")
            st.metric("ITBIS (18%)", f"${totals['itbis']:,.2f}")
            st.markdown(f"""
            <div style="background:rgba(18,18,36,0.7); padding:1rem; border-radius:16px; text-align:center; border:1px solid rgba(100,180,255,0.2);">
                <div style="font-size:20px; font-weight:600; color:#4deeea;">TOTAL GENERAL</div>
                <div style="font-size:36px; font-weight:700; color:white;">${totals['grand_total']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # Save and Clear buttons
        col1, col2 = st.columns(2)
        with col1:
            save_button_text = "💾 Actualizar Cotización" if editing_mode else "💾 Guardar Cotización"
            if st.button(save_button_text, type="primary", use_container_width=True):
                if st.session_state.current_client_id and client_name.strip():
                    if editing_mode:
                        # Update existing quote
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            # Update quote
                            charges_str = str(charges)
                            cur.execute("""
                                UPDATE quotes 
                                SET project_name = ?, notes = ?, total_amount = ?, included_charges = ?
                                WHERE quote_id = ?
                            """, (project_name, notes, totals['grand_total'], charges_str, st.session_state.editing_quote_id))
                            
                            # Delete old items
                            cur.execute("DELETE FROM quote_items WHERE quote_id = ?", (st.session_state.editing_quote_id,))
                            
                            # Insert new items
                            for item in st.session_state.quote_products:
                                cur.execute("""
                                    INSERT INTO quote_items (quote_id, product_name, quantity, unit_price, discount_type, discount_value, auto_imported)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (st.session_state.editing_quote_id, item["product_name"], item["quantity"], 
                                      item["unit_price"], item.get("discount_type", "none"), 
                                      item.get("discount_value", 0), int(item.get("auto_imported", False))))
                            conn.commit()
                        
                        st.success(f"✅ Cotización {st.session_state.editing_quote_id} actualizada exitosamente")
                        st.session_state.editing_quote_id = None
                        st.session_state.editing_quote_data = None
                        st.session_state.quote_products = []
                        st.rerun()
                    else:
                        # Create new quote
                        quote_id = save_quote_to_db(
                            st.session_state.current_client_id,
                            project_name,
                            st.session_state.quote_products,
                            totals['grand_total'],
                            notes,
                            charges,
                            status="Draft"
                        )
                        st.success(f"✅ Cotización guardada: {quote_id}")
                        st.session_state.quote_products = []
                        st.rerun()
                else:
                    st.error("Seleccione un cliente y nombre de empresa.")
        
        with col2:
            if st.button("🔄 Limpiar Cotización", use_container_width=True):
                st.session_state.quote_products = []
                st.session_state.editing_quote_id = None
                st.session_state.editing_quote_data = None
                st.rerun()

    else:
        st.info("👆 Agregue productos para crear una cotización.")

    # Manage Existing Quotes
    st.markdown("### 📂 Cotizaciones Guardadas")
    if st.session_state.current_client_id:
        quotes = get_all_quotes_for_client(st.session_state.current_client_id)
        
        if quotes:
            for q in quotes:
                with st.expander(f"{q['quote_id']} - {q['project_name']} (${q['total_amount']:,.2f}) - {q['status']}"):
                    st.write(f"**Fecha:** {q['date']}")
                    items_rows = query_db(
                        "SELECT product_name, quantity, unit_price FROM quote_items WHERE quote_id = ?",
                        (q["quote_id"],),
                        fetch_all=True
                    )
                    items_df = pd.DataFrame([dict(row) for row in items_rows])
                    if not items_df.empty:
                        items_df['subtotal'] = items_df['quantity'] * items_df['unit_price']
                        st.dataframe(items_df, use_container_width=True)
                    
                    quote_data, items_list = get_quote_by_id(q["quote_id"])
                    client_data = get_client_by_id(st.session_state.current_client_id)
                    try:
                        included_charges = ast.literal_eval(quote_data["included_charges"])
                    except:
                        included_charges = {k: True for k in ['supervision','admin','insurance','transport','contingency']}
                    totals = calculate_quote(items_list, included_charges)

                    if q["status"] == "Draft":
                        # Action buttons for draft quotes
                        col1, col2, col3 = st.columns(3)
                        
                        # Edit button
                        with col1:
                            if st.button("✏️ Editar", key=f"edit_{q['quote_id']}", use_container_width=True):
                                # Load quote data into editing mode
                                st.session_state.editing_quote_id = q['quote_id']
                                st.session_state.editing_quote_data = quote_data
                                st.session_state.quote_products = items_list
                                st.session_state.included_charges = included_charges
                                st.rerun()
                        
                        # Download PDF
                        with col2:
                            pdf = QuotePDF()
                            pdf.add_page()
                            pdf.quote_info(quote_data, client_data)
                            pdf.items_table(items_list)
                            pdf.cost_summary(totals, included_charges)
                            # Add notes section if notes exist
                            if quote_data.get('notes'):
                                pdf.notes_section(quote_data['notes'])
                            pdf_bytes = bytes(pdf.output())
                            
                            st.download_button(
                                "📄 PDF",
                                pdf_bytes,
                                f"{q['quote_id']}_cotizacion.pdf",
                                "application/pdf",
                                use_container_width=True,
                                key=f"dl_quote_{q['quote_id']}"
                            )

                        # Convert to invoice
                        with col3:
                            if st.button("🖨️ Factura", key=f"inv_{q['quote_id']}", use_container_width=True):
                                # Show confirmation dialog
                                st.session_state.confirm_convert = q["quote_id"]
                            
                        # Confirmation dialog for convert
                        if st.session_state.get('confirm_convert') == q["quote_id"]:
                            st.warning(f"⚠️ ¿Convertir cotización {q['quote_id']} en factura?")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✅ Sí, Convertir", key=f"confirm_{q['quote_id']}", use_container_width=True):
                                    new_invoice_id = update_quote_status(q["quote_id"], "Invoiced")
                                    st.success(f"✅ Convertido a factura: {new_invoice_id}")
                                    del st.session_state.confirm_convert
                                    st.rerun()
                            with col_b:
                                if st.button("❌ Cancelar", key=f"cancel_{q['quote_id']}", use_container_width=True):
                                    del st.session_state.confirm_convert
                                    st.rerun()
                        
                        # Delete button with confirmation
                        st.markdown("---")
                        if st.button(f"🗑️ Eliminar Cotización {q['quote_id']}", key=f"del_{q['quote_id']}", type="secondary"):
                            st.session_state.confirm_delete_quote = q["quote_id"]
                        
                        # Confirmation dialog for delete
                        if st.session_state.get('confirm_delete_quote') == q["quote_id"]:
                            st.error(f"⚠️ ¿Está seguro que desea eliminar la cotización {q['quote_id']}? Esta acción no se puede deshacer.")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✅ Sí, Eliminar", key=f"confirm_del_{q['quote_id']}", type="primary"):
                                    delete_quote(q["quote_id"])
                                    del st.session_state.confirm_delete_quote
                                    st.success("Cotización eliminada exitosamente")
                                    st.rerun()
                            with col_b:
                                if st.button("❌ Cancelar", key=f"cancel_del_{q['quote_id']}"):
                                    del st.session_state.confirm_delete_quote
                                    st.rerun()

                    elif q["status"] == "Invoiced":
                        # Download INVOICE PDF
                        pdf = InvoicePDF()
                        pdf.add_page()
                        pdf.invoice_info(quote_data, client_data)
                        pdf.items_table(items_list)
                        pdf.cost_summary(totals, included_charges)
                        # Add notes section if notes exist
                        if quote_data.get('notes'):
                            pdf.notes_section(quote_data['notes'])
                        pdf_bytes = bytes(pdf.output())
                        
                        st.download_button(
                            "📥 Descargar Factura PDF",
                            pdf_bytes,
                            f"{q['quote_id']}_factura.pdf",
                            "application/pdf",
                            use_container_width=True,
                            key=f"dl_invoice_{q['quote_id']}"
                        )
                        st.success("✅ Factura lista para descargar")
                        
                        # Delete invoice with confirmation
                        st.markdown("---")
                        if st.button(f"🗑️ Eliminar Factura {q['quote_id']}", key=f"del_inv_{q['quote_id']}", type="secondary"):
                            st.session_state.confirm_delete_invoice = q["quote_id"]
                        
                        # Confirmation dialog for delete invoice
                        if st.session_state.get('confirm_delete_invoice') == q["quote_id"]:
                            st.error(f"⚠️ ¿Está seguro que desea eliminar la factura {q['quote_id']}? Esta acción no se puede deshacer.")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✅ Sí, Eliminar", key=f"confirm_del_inv_{q['quote_id']}", type="primary"):
                                    delete_quote(q["quote_id"])
                                    del st.session_state.confirm_delete_invoice
                                    st.success("Factura eliminada exitosamente")
                                    st.rerun()
                            with col_b:
                                if st.button("❌ Cancelar", key=f"cancel_del_inv_{q['quote_id']}"):
                                    del st.session_state.confirm_delete_invoice
                                    st.rerun()
        else:
            st.info("No hay cotizaciones guardadas para este cliente.")
    else:
        st.info("Seleccione un cliente para ver sus cotizaciones.")

# ----------------------------
# APP ROUTER
# ----------------------------

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.attempts = 0
    st.session_state.username = ""

if st.session_state.authenticated:
    show_main_app()
else:
    show_login_page()
