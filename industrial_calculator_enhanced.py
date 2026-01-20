import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import os
from fpdf import FPDF
import ast
import json

# ----------------------------
# PAGE CONFIG & CONSTANTS
# ----------------------------
st.set_page_config(
    page_title="METPRO ERP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "rigc_app.db"
PRODUCTS_CSV_PATH = "products.csv"
MAX_ATTEMPTS = 3
USER_PASSCODES = {"fabian": "rams20", "admin": "admin123"}

# ----------------------------
# DATABASE SETUP
# ----------------------------
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
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quote_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            snapshot_data TEXT NOT NULL
        )
        """)
        # Add missing columns if needed
        try:
            cur.execute("SELECT discount_type FROM quote_items LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE quote_items ADD COLUMN discount_type TEXT DEFAULT 'none'")
            cur.execute("ALTER TABLE quote_items ADD COLUMN discount_value REAL DEFAULT 0")
        
        # Insert sample products if empty
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            samples = [
                ("Steel Beam IPE 200", "European standard I-beam", 125.50),
                ("Galvanized Sheet 2mm", "Corrosion-resistant roofing", 45.75),
                ("Anchor Bolts M20", "Heavy-duty foundation bolts", 8.90),
            ]
            cur.executemany("INSERT INTO products (name, description, unit_price) VALUES (?, ?, ?)", samples)
        conn.commit()

if not os.path.exists(DB_PATH):
    init_db()
else:
    init_db()

# ----------------------------
# DATABASE HELPERS
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

def update_client(client_id, company, contact="", email="", phone="", address="", tax_id="", notes=""):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE clients SET
                company_name = ?, contact_name = ?, email = ?, phone = ?,
                address = ?, tax_id = ?, notes = ?
            WHERE id = ?
        """, (company, contact, email, phone, address, tax_id, notes, client_id))
        conn.commit()

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
                INSERT INTO quote_items (
                    quote_id, product_name, quantity, unit_price,
                    discount_type, discount_value, auto_imported
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                quote_id,
                item["product_name"],
                item["quantity"],
                item["unit_price"],
                item.get("discount_type", "none"),
                item.get("discount_value", 0),
                int(item.get("auto_imported", False))
            ))
        conn.commit()
    return quote_id

def update_quote_status(quote_id, status):
    if status == "Invoiced":
        invoice_id = quote_id.replace("COT-", "INV-")
        existing = query_db("SELECT quote_id FROM quotes WHERE quote_id = ?", (invoice_id,), fetch_one=True)
        if existing:
            query_db("UPDATE quotes SET status = ? WHERE quote_id = ?", (status, quote_id))
            return quote_id
        query_db("UPDATE quote_items SET quote_id = ? WHERE quote_id = ?", (invoice_id, quote_id))
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
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
        cur.execute("DELETE FROM quotes WHERE quote_id = ?", (quote_id,))
        conn.commit()

def get_all_quotes_for_client(client_id):
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
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO products (name, description, unit_price) VALUES (?, ?, ?)", 
                       (name, description, unit_price))
            conn.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None

def update_product(product_id, name, description, unit_price):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE products SET name = ?, description = ?, unit_price = ? WHERE id = ?",
                       (name, description, unit_price, product_id))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def delete_product(product_id):
    query_db("DELETE FROM products WHERE id = ?", (product_id,))

def sync_products_from_csv(csv_file_path=PRODUCTS_CSV_PATH):
    if not os.path.exists(csv_file_path):
        return None, "CSV file not found"
    
    try:
        df = pd.read_csv(csv_file_path)
        required_columns = ['name', 'unit_price']
        if not all(col in df.columns for col in required_columns):
            return None, f"CSV must have columns: {', '.join(required_columns)}"
        
        if 'description' not in df.columns:
            df['description'] = ''
        
        df['name'] = df['name'].str.strip()
        df['description'] = df['description'].fillna('').str.strip()
        df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
        df = df.dropna(subset=['name', 'unit_price'])
        df = df[df['unit_price'] > 0]
        
        if df.empty:
            return None, "No valid products found in CSV"
        
        added = updated = 0
        errors = []
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            for _, row in df.iterrows():
                try:
                    existing = cur.execute("SELECT id FROM products WHERE name = ?", (row['name'],)).fetchone()
                    if existing:
                        cur.execute("UPDATE products SET description = ?, unit_price = ? WHERE name = ?",
                                  (row['description'], row['unit_price'], row['name']))
                        updated += 1
                    else:
                        cur.execute("INSERT INTO products (name, description, unit_price) VALUES (?, ?, ?)",
                                  (row['name'], row['description'], row['unit_price']))
                        added += 1
                except Exception as e:
                    errors.append(f"{row['name']}: {str(e)}")
            conn.commit()
        
        message = f"✅ Synced: {added} added, {updated} updated"
        if errors:
            message += f"\n⚠️ {len(errors)} errors"
        return {'added': added, 'updated': updated, 'errors': errors}, message
    except Exception as e:
        return None, f"Error reading CSV: {str(e)}"

def create_sample_csv():
    sample_data = {
        'name': ['Steel Beam IPE 200', 'Galvanized Sheet 2mm', 'Anchor Bolts M20', 'Concrete Mix 25MPa', 'Rebar 12mm'],
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

def save_quote_snapshot(quote_id, data_dict):
    timestamp = datetime.now().isoformat()
    snapshot = {"quote_id": quote_id, "snapshot_date": timestamp, "data": data_dict}
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO quote_history (quote_id, snapshot_date, snapshot_data) VALUES (?, ?, ?)",
                   (quote_id, timestamp, json.dumps(snapshot, default=str)))
        conn.commit()

def get_quote_history(quote_id):
    rows = query_db("SELECT snapshot_data FROM quote_history WHERE quote_id = ? ORDER BY snapshot_date DESC",
                   (quote_id,), fetch_all=True)
    return [json.loads(row[0]) for row in rows]

def duplicate_quote(original_quote_id):
    original_quote, items = get_quote_by_id(original_quote_id)
    if not original_quote:
        return None
    try:
        included_charges = ast.literal_eval(original_quote["included_charges"])
    except:
        included_charges = {k: True for k in ['supervision','admin','insurance','transport','contingency']}
    
    notes = original_quote.get('notes', '')
    notes = f"{notes}\n\nCopied from {original_quote_id}" if notes else f"Copied from {original_quote_id}"
    
    return save_quote_to_db(
        client_id=original_quote['client_id'],
        project_name=original_quote.get('project_name', ''),
        items=items,
        total=original_quote['total_amount'],
        notes=notes,
        included_charges=included_charges,
        status="Draft"
    )

# ----------------------------
# QUOTATION LOGIC
# ----------------------------
def calculate_item_discount(unit_price, quantity, discount_type, discount_value):
    subtotal = unit_price * quantity
    if discount_type == "percentage":
        return subtotal * (discount_value / 100)
    elif discount_type == "fixed":
        return discount_value
    return 0

def calculate_quote(products, included_charges):
    items_total = sum(float(p.get('quantity', 0)) * float(p.get('unit_price', 0)) for p in products)
    total_discounts = sum(calculate_item_discount(
        float(p.get('unit_price', 0)),
        float(p.get('quantity', 0)),
        p.get('discount_type', 'none'),
        float(p.get('discount_value', 0))
    ) for p in products)
    items_after_discount = items_total - total_discounts
    supervision = items_after_discount * 0.10 if included_charges.get('supervision') else 0.0
    admin = items_after_discount * 0.04 if included_charges.get('admin') else 0.0
    insurance = items_after_discount * 0.01 if included_charges.get('insurance') else 0.0
    transport = items_after_discount * 0.03 if included_charges.get('transport') else 0.0
    contingency = items_after_discount * 0.03 if included_charges.get('contingency') else 0.0
    subtotal = items_after_discount + supervision + admin + insurance + transport + contingency
    itbis = subtotal * 0.18
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
        'grand_total': subtotal + itbis,
    }

# ----------------------------
# PDF GENERATOR
# ----------------------------
class QuotePDF(FPDF):
    def header(self):
        self.set_fill_color(41, 128, 185)
        self.rect(0, 0, 210, 40, 'F')
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 25)
        logo_offset = 40 if os.path.exists("logo.png") else 10
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 4)
        self.set_xy(logo_offset, 12)
        lines = [
            "Parque Industrial Disdo",
            "Calle Central No. 1, Hato Nuevo Palave",
            "Santo Domingo Oeste",
            "Tel: 829-439-8476 | RNC: 131-71683-2"
        ]
        for line in lines:
            self.cell(0, 2, line, 0, 1, "R")
        self.set_font("Helvetica", "B", 16)
        self.set_xy(logo_offset, 28)
        self.cell(0, 8, "COTIZACION", 0, 1, "R")
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-50)

        col_width = 85
        left_x = 20
        right_x = 115

        line_width = col_width - 20

        # ---------- LEFT SIGNATURE (AUTHORIZED) ----------
        left_text_x = left_x + 10

        self.set_font("Helvetica", "B", 10)
        self.set_xy(left_text_x, -45)
        self.line(
            left_text_x,
            self.get_y(),
            left_text_x + line_width,
            self.get_y()
        )

        self.set_xy(left_text_x, -40)
        self.set_font("Helvetica", "", 8)
        self.cell(line_width, 4, "Autorizado Por:", 0, 0, "C")

        self.set_xy(left_text_x, -36)
        self.cell(line_width, 4, "Karmary Mata", 0, 0, "C")


    # ---------- RIGHT SIGNATURE (CLIENT) ----------
        right_text_x = right_x + 10

        self.set_xy(right_text_x, -45)
        self.line(
            right_text_x,
            self.get_y(),
            right_text_x + line_width,
            self.get_y()
        )

        self.set_xy(right_text_x, -40)
        self.cell(line_width, 4, "Firma Cliente", 0, 1, "C")

        # ---------- FOOTER INFO ----------
        self.set_y(-25)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(128, 128, 128)

        self.cell(
            0,
            4,
            "Parque Industrial Disdo, Calle Central No. 1, Hato Nuevo Palave",
            0,
            1,
            "C"
        )
        self.cell(
            0,
            4,
            "Santo Domingo Oeste | Tel: 829-439-8476 | RNC: 131-71683-2",
            0,
            1,
            "C"
        )

        self.set_y(-15)
        self.cell(0, 4, f"Pagina {self.page_no()}", 0, 0, "C")


    def quote_info(self, quote_data, client_data):
        self.set_xy(10, 55)
        self.set_fill_color(240, 240, 240)
        self.set_font("Helvetica", "B", 11)
        self.cell(90, 8, "DATOS PEDIDO", 0, 1, "L", True)
        self.set_font("Helvetica", "", 9)
        for label, key in [("Cotizacion #:", 'quote_id'), ("Fecha:", 'date'), ("Proyecto:", 'project_name')]:
            self.set_x(10)
            self.cell(40, 6, label, 0, 0, "L")
            self.set_font("Helvetica", "B", 9)
            self.cell(50, 6, str(quote_data.get(key, 'N/A')), 0, 1, "L")
            self.set_font("Helvetica", "", 9)
        self.set_xy(110, 55)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.cell(90, 8, "CLIENTE", 0, 1, "L", True)
        self.set_font("Helvetica", "", 9)
        for label, key in [("Empresa:", 'company_name'), ("Contacto:", 'contact_name'),
                           ("RNC/Cedula:", 'tax_id'), ("Email:", 'email'), ("Telefono:", 'phone')]:
            if client_data.get(key):
                self.set_x(110)
                self.cell(40, 6, label, 0, 0, "L")
                self.set_font("Helvetica", "B", 9)
                if key == 'company_name':
                    self.multi_cell(50, 6, str(client_data[key]), 0, "L")
                else:
                    self.cell(50, 6, str(client_data[key]), 0, 1, "L")
                self.set_font("Helvetica", "", 9)
        self.ln(10)

    def items_table(self, items_list):
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        for text, width in [("DESCRIPCION", 90), ("CANTIDAD", 30), ("PRECIO UNIT.", 35), ("TOTAL", 35)]:
            self.cell(width, 9, text, 1, 0, "C" if width < 90 else "L", True)
        self.ln()
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        fill = False
        for item in items_list:
            desc = self._clean_text(str(item["product_name"]))
            self.set_fill_color(245, 245, 245) if fill else self.set_fill_color(255, 255, 255)
            self.cell(90, 6, desc[:50], 1, 0, "L", fill)
            self.cell(30, 6, f"{item['quantity']:,.2f}", 1, 0, "C", fill)
            self.cell(35, 6, f"${item['unit_price']:,.2f}", 1, 0, "R", fill)
            total = item["quantity"] * item["unit_price"]
            self.cell(35, 6, f"${total:,.2f}", 1, 1, "R", fill)
            fill = not fill
        self.ln(5)

    def cost_summary(self, totals, included_charges):
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.5)
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(240, 248, 255)
        self.cell(0, 8, "RESUMEN FINANCIERO", 1, 1, "L", True)
        self.set_font("Helvetica", "", 9)
        self.set_line_width(0.2)
        self.cell(130, 6, "Subtotal de Items:", 1, 0, "L")
        self.cell(60, 6, f"${totals['items_total']:,.2f}", 1, 1, "R")
        if totals.get('total_discounts', 0) > 0:
            self.set_text_color(220, 53, 69)
            self.cell(130, 6, "Descuentos Aplicados:", 1, 0, "L")
            self.cell(60, 6, f"-${totals['total_discounts']:,.2f}", 1, 1, "R")
            self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "B", 9)
        self.cell(130, 6, "Total Despues de Descuentos:", 1, 0, "L")
        self.cell(60, 6, f"${totals['items_after_discount']:,.2f}", 1, 1, "R")
        self.set_font("Helvetica", "", 9)
        for key, label in [
            ('supervision', "Supervision Tecnica (10%):"),
            ('admin', "Gastos Administrativos (4%):"),
            ('insurance', "Seguro de Riesgo (1%):"),
            ('transport', "Transporte (3%):"),
            ('contingency', "Imprevisto (3%):")
        ]:
            if included_charges.get(key):
                self.cell(130, 6, label, 1, 0, "L")
                self.cell(60, 6, f"${totals[key]:,.2f}", 1, 1, "R")
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(230, 240, 250)
        self.cell(130, 7, "SUBTOTAL GENERAL:", 1, 0, "L", True)
        self.cell(60, 7, f"${totals['subtotal_general']:,.2f}", 1, 1, "R", True)
        self.set_font("Helvetica", "", 9)
        self.cell(130, 6, "ITBIS (18%):", 1, 0, "L")
        self.cell(60, 6, f"${totals['itbis']:,.2f}", 1, 1, "R")
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        self.cell(130, 10, "TOTAL GENERAL:", 1, 0, "L", True)
        self.cell(60, 10, f"${totals['grand_total']:,.2f}", 1, 1, "R", True)
        self.set_text_color(0, 0, 0)

    def notes_section(self, notes):
        if notes and notes.strip():
            self.ln(5)

            # Section title
            self.set_font("Helvetica", "B", 8.5)
            self.set_text_color(40, 40, 40)
            self.cell(0, 5, "NOTAS Y CONDICIONES", 0, 1, "L")

            # Notes text (bold but compact)
            self.set_font("Helvetica", "B", 6.5)
            self.set_text_color(80, 80, 80)
            self.multi_cell(
                0,
                3.6,
                self._clean_text(notes),
                0,
                "L"
            )

        self.set_text_color(0, 0, 0)


    def _clean_text(self, text):
        replacements = {
            "\u2022": "-", "\u2013": "-", "\u2014": "--", "\u2018": "'",
            "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode('latin1', errors='replace').decode('latin1')

class InvoicePDF(QuotePDF):
    def header(self):
        self.set_fill_color(231, 76, 60)
        self.rect(0, 0, 210, 40, 'F')
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 25)
        logo_offset = 40 if os.path.exists("logo.png") else 10
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 4)
        self.set_xy(logo_offset, 12)
        lines = [
            "Parque Industrial Disdo",
            "Calle Central No. 1, Hato Nuevo Palave",
            "Santo Domingo Oeste",
            "Tel: 829-439-8476 | RNC: 131-71683-2"
        ]
        for line in lines:
            self.cell(0, 2, line, 0, 1, "R")
        self.set_font("Helvetica", "B", 16)
        self.set_xy(logo_offset, 28)
        self.cell(0, 8, "FACTURA", 0, 1, "R")
        self.set_text_color(0, 0, 0)
        self.ln(10)

# ----------------------------
# CSS LOADER
# ----------------------------
def load_css(file_path):
    """Load external CSS file into Streamlit app."""
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ----------------------------
# MODULES
# ----------------------------
def show_product_manager():
    st.markdown("---")
    st.markdown("## 📦 Gestión de Productos")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista", "📁 CSV Sync", "➕ Agregar/Editar"])
    
    with tab1:
        products = get_products_for_dropdown()
        if products:
            df = pd.DataFrame(products).rename(columns={'id': 'ID', 'name': 'Nombre', 
                                                        'description': 'Descripción', 'unit_price': 'Precio'})
            st.dataframe(df, column_config={"Precio": st.column_config.NumberColumn("Precio", format="$%.2f")},
                        hide_index=True, use_container_width=True)
            st.info(f"📊 Total: {len(products)} productos")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                product_to_edit = st.selectbox("Seleccionar", options=[p['id'] for p in products],
                    format_func=lambda x: next(p['name'] for p in products if p['id'] == x))
            with col2:
                if st.button("✏️ Editar", use_container_width=True):
                    st.session_state.editing_product_id = product_to_edit
                    st.rerun()
            
            if st.button("🗑️ Eliminar Producto", type="secondary"):
                st.session_state.confirm_delete_product = product_to_edit
            
            if 'confirm_delete_product' in st.session_state:
                product = next(p for p in products if p['id'] == st.session_state.confirm_delete_product)
                st.warning(f"⚠️ ¿Eliminar '{product['name']}'?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Sí", type="primary"):
                        delete_product(st.session_state.confirm_delete_product)
                        del st.session_state.confirm_delete_product
                        st.success("Eliminado")
                        st.rerun()
                with col2:
                    if st.button("❌ No"):
                        del st.session_state.confirm_delete_product
                        st.rerun()
        else:
            st.info("No hay productos.")
    
    with tab2:
        st.markdown("### 📁 CSV Sync")
        if os.path.exists(PRODUCTS_CSV_PATH):
            st.success(f"✅ Found: `{PRODUCTS_CSV_PATH}`")
            try:
                preview = pd.read_csv(PRODUCTS_CSV_PATH)
                st.dataframe(preview.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
            
            if st.button("🔄 Sync from CSV", type="primary"):
                result, msg = sync_products_from_csv()
                if result:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.warning(f"⚠️ No `{PRODUCTS_CSV_PATH}` found")
            if st.button("📄 Create Sample"):
                create_sample_csv()
                st.success("✅ Created")
                st.rerun()
    
    with tab3:
        editing = None
        if st.session_state.editing_product_id:
            products = get_products_for_dropdown()
            editing = next((p for p in products if p['id'] == st.session_state.editing_product_id), None)
        
        with st.form("product_form"):
            st.markdown(f"#### {'✏️ Editar' if editing else '➕ Nuevo'} Producto")
            name = st.text_input("Nombre *", value=editing['name'] if editing else "")
            desc = st.text_area("Descripción", value=editing['description'] if editing else "")
            price = st.number_input("Precio ($)", min_value=0.01, step=0.01, 
                                   value=float(editing['unit_price']) if editing else 1.00)
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("💾 " + ("Actualizar" if editing else "Agregar"), 
                                              use_container_width=True, type="primary")
            with col2:
                if editing and st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.session_state.editing_product_id = None
                    st.rerun()
            
            if submit and name and price > 0:
                if editing:
                    if update_product(editing['id'], name, desc, price):
                        st.success(f"✅ '{name}' actualizado")
                        st.session_state.editing_product_id = None
                        st.rerun()
                    else:
                        st.error("❌ Nombre duplicado")
                else:
                    if add_product(name, desc, price):
                        st.success(f"✅ '{name}' agregado")
                        st.rerun()
                    else:
                        st.error("❌ Nombre duplicado")

def show_saved_quotes():
    if not st.session_state.current_client_id:
        return
    
    # Search & Filters
    search = st.text_input("🔍 Buscar", value=st.session_state.global_search_query, key="search")
    st.session_state.global_search_query = search.lower().strip()
    
    with st.expander("Filtros"):
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Estado", ["All", "Draft", "Invoiced"], 
                                key="filter_status_select")
        with col2:
            if st.button("🧹 Limpiar"):
                st.session_state.filter_status = "All"
                st.session_state.global_search_query = ""
                st.rerun()
    
    st.session_state.filter_status = status
    
    # Get and filter quotes
    all_quotes = get_all_quotes_for_client(st.session_state.current_client_id)
    
    filtered = []
    for q in all_quotes:
        if st.session_state.filter_status != "All" and q['status'] != st.session_state.filter_status:
            continue
        
        if st.session_state.global_search_query:
            query = st.session_state.global_search_query
            if not (query in q['quote_id'].lower() or 
                   query in q.get('project_name', '').lower() or
                   query in q.get('notes', '').lower()):
                continue
        
        filtered.append(q)
    
    # Display quotes
    if filtered:
        for q in filtered:
            with st.expander(f"{q['quote_id']} - {q['project_name']} (${q['total_amount']:,.2f}) - {q['status']}"):
                st.write(f"**Fecha:** {q['date']}")
                
                quote_data, items = get_quote_by_id(q["quote_id"])
                client_data = get_client_by_id(st.session_state.current_client_id)
                
                try:
                    charges = ast.literal_eval(quote_data["included_charges"])
                except:
                    charges = {k: True for k in ['supervision','admin','insurance','transport','contingency']}
                
                totals = calculate_quote(items, charges)
                
                # Items table
                if items:
                    items_df = pd.DataFrame(items)[['product_name', 'quantity', 'unit_price']]
                    items_df['total'] = items_df['quantity'] * items_df['unit_price']
                    st.dataframe(items_df, use_container_width=True, hide_index=True)
                
                if q["status"] == "Draft":
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("✏️ Editar", key=f"edit_{q['quote_id']}", use_container_width=True):
                            st.session_state.editing_quote_id = q['quote_id']
                            st.session_state.editing_quote_data = quote_data
                            st.session_state.quote_products = items
                            st.session_state.included_charges = charges
                            st.rerun()
                    
                    with col2:
                        if st.button("🔄 Duplicar", key=f"dup_{q['quote_id']}", use_container_width=True):
                            new_id = duplicate_quote(q['quote_id'])
                            if new_id:
                                st.success(f"✅ Duplicado: {new_id}")
                                st.rerun()
                    
                    with col3:
                        if st.button("🕰️ Historial", key=f"hist_{q['quote_id']}", use_container_width=True):
                            st.session_state.viewing_history_for = q['quote_id']
                            st.rerun()
                    
                    with col4:
                        pdf = QuotePDF()
                        pdf.add_page()
                        pdf.quote_info(quote_data, client_data)
                        pdf.items_table(items)
                        pdf.cost_summary(totals, charges)
                        if quote_data.get('notes'):
                            pdf.notes_section(quote_data['notes'])
                        
                        raw = pdf.output(dest="S")
                        pdf_bytes = raw.encode("latin-1") if isinstance(raw, str) else bytes(raw)
                        
                        st.download_button("📄 PDF", pdf_bytes, f"{q['quote_id']}_cotizacion.pdf",
                                         "application/pdf", use_container_width=True, key=f"dl_{q['quote_id']}")
                    
                    st.markdown("---")
                    if st.button("🖨️ Convertir a Factura", key=f"inv_{q['quote_id']}", use_container_width=True):
                        st.session_state.confirm_convert = q["quote_id"]
                    
                    if st.session_state.get('confirm_convert') == q["quote_id"]:
                        st.warning(f"⚠️ ¿Convertir {q['quote_id']} en factura?")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Sí", key=f"conf_{q['quote_id']}", use_container_width=True):
                                new_id = update_quote_status(q["quote_id"], "Invoiced")
                                st.success(f"✅ Factura: {new_id}")
                                del st.session_state.confirm_convert
                                st.rerun()
                        with col_b:
                            if st.button("❌ No", key=f"canc_{q['quote_id']}", use_container_width=True):
                                del st.session_state.confirm_convert
                                st.rerun()
                    
                    if st.button(f"🗑️ Eliminar", key=f"del_{q['quote_id']}", type="secondary"):
                        st.session_state.confirm_delete_quote = q["quote_id"]
                    
                    if st.session_state.get('confirm_delete_quote') == q["quote_id"]:
                        st.error(f"⚠️ ¿Eliminar {q['quote_id']}?")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Eliminar", key=f"cdel_{q['quote_id']}", type="primary"):
                                delete_quote(q["quote_id"])
                                del st.session_state.confirm_delete_quote
                                st.success("Eliminado")
                                st.rerun()
                        with col_b:
                            if st.button("❌ Cancelar", key=f"xdel_{q['quote_id']}"):
                                del st.session_state.confirm_delete_quote
                                st.rerun()
                
                elif q["status"] == "Invoiced":
                    pdf = InvoicePDF()
                    pdf.add_page()
                    pdf.quote_info(quote_data, client_data)
                    pdf.items_table(items)
                    pdf.cost_summary(totals, charges)
                    if quote_data.get('notes'):
                        pdf.notes_section(quote_data['notes'])
                    
                    raw = pdf.output(dest="S")
                    pdf_bytes = raw.encode("latin-1") if isinstance(raw, str) else bytes(raw)
                    
                    st.download_button("📥 Descargar Factura", pdf_bytes, f"{q['quote_id']}_factura.pdf",
                                     "application/pdf", use_container_width=True, key=f"dl_inv_{q['quote_id']}")
                    
                    if st.button(f"🗑️ Eliminar Factura", key=f"del_inv_{q['quote_id']}", type="secondary"):
                        st.session_state.confirm_delete_invoice = q["quote_id"]
                    
                    if st.session_state.get('confirm_delete_invoice') == q["quote_id"]:
                        st.error(f"⚠️ ¿Eliminar factura {q['quote_id']}?")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Eliminar", key=f"cdel_inv_{q['quote_id']}", type="primary"):
                                delete_quote(q["quote_id"])
                                del st.session_state.confirm_delete_invoice
                                st.success("Eliminado")
                                st.rerun()
                        with col_b:
                            if st.button("❌ Cancelar", key=f"xdel_inv_{q['quote_id']}"):
                                del st.session_state.confirm_delete_invoice
                                st.rerun()
    else:
        st.info("No hay cotizaciones guardadas")

def show_quote_form():
    st.markdown("Información de la Cotización")
    
    if st.session_state.editing_quote_id:
        st.info(f"✏️ Editando: {st.session_state.editing_quote_id}")
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_quote_id = None
            st.session_state.editing_quote_data = None
            st.session_state.quote_products = []
            st.rerun()
    
    # Project info
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.current_client_id:
            client = get_client_by_id(st.session_state.current_client_id)
            client_name = st.text_input("Cliente", value=client['company_name'], disabled=True)
        else:
            client_name = st.text_input("Cliente", placeholder="Seleccione cliente")
    
    with col2:
        default_project = st.session_state.editing_quote_data.get('project_name', '') if st.session_state.editing_quote_data else ''
        project_name = st.text_input("Proyecto", value=default_project)
    
    default_notes = st.session_state.editing_quote_data.get('notes', '') if st.session_state.editing_quote_data else ''
    notes = st.text_area("Notas", value=default_notes)
    
    # Add products
    st.markdown("Agregar Producto")
    products_list = get_products_for_dropdown()
    
    if products_list:
        col1, col2 = st.columns([3, 2])
        with col1:
            selected_id = st.selectbox("Desde catálogo", options=[p["id"] for p in products_list],
                format_func=lambda x: next(p["name"] for p in products_list if p["id"] == x))
            prod = next(p for p in products_list if p["id"] == selected_id)
        
        with col2:
            qty = st.number_input("Cantidad", min_value=0.0, step=1.0, key="db_qty")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            add_disc = st.checkbox("Descuento", key="db_disc")
        if add_disc:
            with col2:
                disc_type = st.selectbox("Tipo", ["percentage", "fixed"],
                    format_func=lambda x: "%" if x == "percentage" else "$", key="db_disc_type")
            with col3:
                disc_val = st.number_input("Valor", min_value=0.0, step=0.1, key="db_disc_val")
        else:
            disc_type, disc_val = "none", 0.0
        
        if st.button("➕ Agregar desde Catálogo"):
            if qty > 0:
                st.session_state.quote_products.append({
                    "product_name": prod["name"], "quantity": qty, "unit_price": prod["unit_price"],
                    "discount_type": disc_type, "discount_value": disc_val
                })
                st.rerun()
    
    # Manual entry
    with st.form("manual_product"):
        st.markdown("#### Producto Manual")
        col1, col2, col3 = st.columns(3)
        name = col1.text_input("Nombre")
        qty_m = col2.number_input("Cantidad", min_value=0.0, step=1.0)
        price = col3.number_input("Precio", min_value=0.0, step=0.01)
        
        if st.form_submit_button("➕ Agregar Manual") and name and qty_m > 0 and price > 0:
            st.session_state.quote_products.append({
                "product_name": name, "quantity": qty_m, "unit_price": price,
                "discount_type": "none", "discount_value": 0
            })
            st.rerun()
    
    # Display products
    if st.session_state.quote_products:
        for p in st.session_state.quote_products:
            p['discount_amount'] = calculate_item_discount(p.get('unit_price', 0), p.get('quantity', 0),
                p.get('discount_type', 'none'), p.get('discount_value', 0))
            p['subtotal'] = (p.get('quantity', 0) * p.get('unit_price', 0)) - p['discount_amount']
        
        df = pd.DataFrame(st.session_state.quote_products)
        
        edited = st.data_editor(df, 
            column_config={
                "product_name": "Producto",
                "quantity": st.column_config.NumberColumn("Cant.", format="%.2f"),
                "unit_price": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "discount_type": st.column_config.SelectboxColumn("Desc.Tipo", options=["none", "percentage", "fixed"]),
                "discount_value": st.column_config.NumberColumn("Desc.Val", format="%.2f"),
                "discount_amount": st.column_config.NumberColumn("Desc.$", format="$%.2f"),
                "subtotal": st.column_config.NumberColumn("Total", format="$%.2f")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="products_editor"
        )
        
        st.session_state.quote_products = edited.to_dict('records')
        
        # Charges
        st.markdown("### ⚙️ Cargos Adicionales")
        cols = st.columns(5)
        charges = st.session_state.included_charges
        charges['supervision'] = cols[0].checkbox("Supervisión (10%)", value=charges['supervision'])
        charges['admin'] = cols[1].checkbox("Admin (4%)", value=charges['admin'])
        charges['insurance'] = cols[2].checkbox("Seguro (1%)", value=charges['insurance'])
        charges['transport'] = cols[3].checkbox("Transporte (3%)", value=charges['transport'])
        charges['contingency'] = cols[4].checkbox("Imprevisto (3%)", value=charges['contingency'])
        
        totals = calculate_quote(st.session_state.quote_products, charges)
        
        # Summary
        st.markdown("### 💰 Resumen")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Items", f"${totals['items_total']:,.2f}")
            if totals['total_discounts'] > 0:
                st.metric("Descuentos", f"-${totals['total_discounts']:,.2f}")
        with c2:
            st.metric("Subtotal", f"${totals['subtotal_general']:,.2f}")
            st.metric("ITBIS (18%)", f"${totals['itbis']:,.2f}")
        with c3:
            st.markdown(f"""
            <div style="background:rgba(18,18,36,0.7); padding:1rem; border-radius:16px; text-align:center;">
            <div style="font-size:20px; font-weight:600; color:#4deeea;">TOTAL</div>
            <div style="font-size:36px; font-weight:700; color:white;">${totals['grand_total']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Save/Clear buttons
        col1, col2 = st.columns(2)
        with col1:
            btn_text = "💾 Actualizar" if st.session_state.editing_quote_id else "💾 Guardar"
            if st.button(btn_text, type="primary", use_container_width=True):
                if not st.session_state.current_client_id:
                    st.error("Seleccione un cliente")
                    return
                
                if st.session_state.editing_quote_id:
                    # Save snapshot before update
                    current_quote, current_items = get_quote_by_id(st.session_state.editing_quote_id)
                    if current_quote:
                        save_quote_snapshot(st.session_state.editing_quote_id, 
                                          {"quote": current_quote, "items": current_items})
                    
                    # Update
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("""UPDATE quotes SET project_name = ?, notes = ?, total_amount = ?, 
                                     included_charges = ? WHERE quote_id = ?""",
                                  (project_name, notes, totals['grand_total'], str(charges), 
                                   st.session_state.editing_quote_id))
                        cur.execute("DELETE FROM quote_items WHERE quote_id = ?", 
                                  (st.session_state.editing_quote_id,))
                        for item in st.session_state.quote_products:
                            cur.execute("""INSERT INTO quote_items (quote_id, product_name, quantity, unit_price, 
                                         discount_type, discount_value, auto_imported) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                      (st.session_state.editing_quote_id, item["product_name"], item["quantity"],
                                       item["unit_price"], item.get("discount_type", "none"),
                                       item.get("discount_value", 0), 0))
                        conn.commit()
                    
                    st.success(f"✅ Actualizado: {st.session_state.editing_quote_id}")
                    st.session_state.editing_quote_id = None
                    st.session_state.editing_quote_data = None
                    st.session_state.quote_products = []
                    st.rerun()
                else:
                    # New quote
                    quote_id = save_quote_to_db(st.session_state.current_client_id, project_name,
                        st.session_state.quote_products, totals['grand_total'], notes, charges)
                    st.success(f"✅ Guardado: {quote_id}")
                    st.session_state.quote_products = []
                    st.rerun()
        
        with col2:
            if st.button("🔄 Limpiar", use_container_width=True):
                st.session_state.quote_products = []
                st.session_state.editing_quote_id = None
                st.session_state.editing_quote_data = None
                st.rerun()
    else:
        st.info("👆 Agregue productos")

# ----------------------------
# SESSION STATE INIT
# ----------------------------
def init_session_state():
    defaults = {
        'authenticated': False,
        'attempts': 0,
        'username': "",
        'current_client_id': None,
        'quote_products': [],
        'included_charges': {'supervision': True, 'admin': True, 'insurance': True, 'transport': True, 'contingency': True},
        'show_product_manager': False,
        'editing_product_id': None,
        'editing_quote_id': None,
        'editing_quote_data': None,
        'viewing_history_for': None,
        'global_search_query': "",
        'filter_status': "All",
        'editing_client_id': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ----------------------------
# LOGIN PAGE
# ----------------------------
def show_login_page():
    st.markdown('<div style="text-align:center; font-size:72px; margin:2rem 0;">🏗️</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:40px; font-weight:800; color:#2563eb;">METPRO ERP</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; color:#6b7280; font-size:14px; margin-bottom:2rem;">Sistema de Gestión Empresarial</div>', unsafe_allow_html=True)
    
    if st.session_state.attempts >= MAX_ATTEMPTS:
        st.error("⚠️ Máximo de intentos alcanzado")
        return
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuario")
        password = st.text_input("🔒 Contraseña", type="password")
        submit = st.form_submit_button("ACCEDER", use_container_width=True, type="primary")
        if submit:
            if username in USER_PASSCODES and password == USER_PASSCODES[username]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.attempts = 0
                st.rerun()
            else:
                st.session_state.attempts += 1
                st.error(f"❌ Credenciales incorrectas. Intentos: {st.session_state.attempts}/{MAX_ATTEMPTS}")

# ----------------------------
# MAIN APP
# ----------------------------
def show_main_app():
    # Sidebar
    with st.sidebar:
        st.header("👥 Gestión de Clientes")
        mode = st.radio("Modo:", ["Seleccionar Cliente", "Nuevo Cliente"])
        
        if mode == "Seleccionar Cliente":
            clients = get_all_clients()
            if not clients:
                st.info("No hay clientes.")
            else:
                client_names = [c["company_name"] for c in clients]
                selected_idx = st.selectbox("Cliente:", range(len(client_names)), 
                                            format_func=lambda i: client_names[i])
                selected_client = clients[selected_idx]

                # Horizontal buttons
                edit_col, select_col = st.columns(2)
                with edit_col:
                    if st.button("Editar", use_container_width=True):
                        st.session_state.editing_client_id = selected_client["id"]
                        st.rerun()
                with select_col:
                    if st.button("Seleccionar", use_container_width=True):
                        st.session_state.current_client_id = selected_client["id"]
                        st.rerun()

                # Edit form (only if editing this client)
                if st.session_state.get('editing_client_id') == selected_client["id"]:
                    st.markdown("### 📝 Editar Cliente")
                    with st.form("edit_client_form"):
                        company = st.text_input("Empresa *", value=selected_client["company_name"])
                        contact = st.text_input("Contacto", value=selected_client.get("contact_name") or "")
                        email = st.text_input("Email", value=selected_client.get("email") or "")
                        phone = st.text_input("Teléfono", value=selected_client.get("phone") or "")
                        address = st.text_area("Dirección", value=selected_client.get("address") or "")
                        tax_id = st.text_input("RNC/Cédula", value=selected_client.get("tax_id") or "")
                        notes = st.text_area("Notas", value=selected_client.get("notes") or "")
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_clicked = st.form_submit_button("💾 Guardar Cambios", type="primary")
                        with col_cancel:
                            if st.form_submit_button("❌ Cancelar"):
                                del st.session_state.editing_client_id
                                st.rerun()
                        
                        if save_clicked:
                            if company.strip():
                                update_client(
                                    selected_client["id"], company, contact, email,
                                    phone, address, tax_id, notes
                                )
                                st.success("✅ Cliente actualizado")
                                del st.session_state.editing_client_id
                                st.rerun()
                            else:
                                st.error("Empresa es obligatoria.")
        else:
            # New Client Form
            with st.form("new_client"):
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
                        st.success("✅ Cliente guardado!")
                        st.rerun()
                    else:
                        st.error("Empresa requerida.")
        
        st.markdown("---")
        if st.button("📦 Gestión de Productos", use_container_width=True):
            st.session_state.show_product_manager = not st.session_state.show_product_manager
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Header
    st.markdown("""
    <h1 style="
        text-align: center;
        font-size: 48px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 4px;
        letter-spacing: -0.5px;
    ">
        METPRO SISTEMA ERP
    </h1>
    <p style="
        text-align: center;
        color: #4b5563;
        font-size: 18px;
        margin-top: 0;
        letter-spacing: 0.5px;
        font-weight: 500;
    ">
        Sistema de Cálculo Industrial
    </p>
    <div style="
        width: 80px;
        height: 4px;
        background: #111827;
        margin: 12px auto;
        border-radius: 2px;
    "></div>
    """, unsafe_allow_html=True)
    
    # Product Manager Modal
    if st.session_state.show_product_manager:
        show_product_manager()
        return
    
    # Client Info Banner
    if st.session_state.current_client_id:
        client = get_client_by_id(st.session_state.current_client_id)
        if not client:
            st.warning("⚠️ Cliente no encontrado. Seleccione uno válido.")
            st.session_state.current_client_id = None
            st.rerun()
        contact_info = f"📞 {client.get('contact_name', 'Sin contacto')}" if client.get('contact_name') else "📞 Sin contacto"
        tax_info = f" | 🆔 RNC/Cédula: {client.get('tax_id', 'N/A')}" if client.get('tax_id') else ""
        st.markdown(f"""
        <div style="background:rgba(41,128,185,0.15); padding:1rem; border-radius:8px; border-left:4px solid #2980b9; margin-bottom: 1.5rem;">
        <div style="font-size:18px; font-weight:600; color:#ffffff; margin-bottom:0.5rem;">👤 Cliente Activo</div>
        <div style="font-size:16px; font-weight:500; margin-bottom:0.3rem;">{client['company_name']}</div>
        <div style="font-size:14px; color:#cccccc;">{contact_info}{tax_info}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Seleccione o cree un cliente en la barra lateral.")
        st.stop()  # Prevent quote form from rendering
    
    st.divider()
    
    # Quote Form & Saved Quotes
    show_quote_form()
    st.markdown("### 📂 Cotizaciones Guardadas")
    show_saved_quotes()

# ----------------------------
# ENTRY POINT
# ----------------------------
def main():
    # Initialize session state FIRST
    init_session_state()
    
    # Load external CSS if exists
    if os.path.exists("style.css"):
        load_css("style.css")
    
    # Route
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()