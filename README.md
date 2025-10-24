# Industrial Calculator with Client Management - Setup Guide

## 📋 Files You Need

1. **app_fixed.py** - Your main application (the fixed version)
2. **database.py** - Database management functions

## 🚀 Quick Setup Instructions

### Step 1: Backup Your Original File
```bash
# First, backup your original app.py
cp app.py app_backup.py
```

### Step 2: Replace Your Files
1. Delete or rename your current `app.py`
2. Rename `app_fixed.py` to `app.py`
3. Make sure `database.py` is in the same folder

### Step 3: Install Required Packages
```bash
pip install streamlit pandas numpy plotly matplotlib reportlab xlsxwriter
```

### Step 4: Run the Application
```bash
streamlit run app.py
```

## 🔐 Login Credentials
- Username: `fabian` Password: `rams20`
- Username: `admin` Password: `admin123`

## ✨ What's New/Fixed

### ✅ Fixed Issues:
1. **Fixed st.set_page_config error** - Was broken due to incorrect placement
2. **Fixed database initialization** - Now properly placed after page config
3. **Added complete client management system** in the sidebar
4. **Added Save Calculation tab** - New 4th tab for saving calculations
5. **Fixed import statements** - All imports properly ordered

### 🎯 New Features:
1. **Client Management Sidebar:**
   - Create new clients
   - Select existing clients
   - View client details
   - Load saved calculations

2. **Save Calculations:**
   - Save both steel and material calculations
   - Associate calculations with clients
   - Load previous calculations
   - Track project history

3. **Improved Workflow:**
   - Client status shown at top
   - Auto-fill client info in quotes
   - Load saved calculations into forms
   - Database persistence for all data

## 📖 How to Use

### Adding a New Client:
1. In the sidebar, select "Nuevo Cliente"
2. Fill in company information
3. Click "💾 Guardar Cliente"

### Saving a Calculation:
1. Select a client first (sidebar)
2. Perform your calculations (Steel or Materials tabs)
3. Go to the "💾 GUARDAR" tab
4. Enter project name and click "💾 Guardar en Base de Datos"

### Loading Previous Calculations:
1. Select a client in the sidebar
2. Under "📊 Cálculos Guardados", click the 📂 button
3. The calculation will load into the forms

### Creating a Quote:
1. Select a client
2. Do your calculations
3. Go to "📊 COTIZACIÓN" tab
4. Import products from calculations or add manually
5. Generate PDF

## 🗂️ Database Structure

Your data is stored in `calculator.db` with these tables:
- **clients** - Client information
- **calculations** - Saved calculations with dimensions and materials
- **quotations** - Generated quotes (optional tracking)

## ⚠️ Important Notes

1. **Database File**: The `calculator.db` file will be created automatically on first run
2. **Backup**: Always backup `calculator.db` regularly - it contains all your data
3. **Session State**: The app uses Streamlit session state for temporary data
4. **Client Required**: You must select/create a client before saving calculations

## 🐛 Troubleshooting

### If you get an error on startup:
```bash
# Make sure both files are in the same folder
ls -la
# Should show: app.py and database.py
```

### If database isn't working:
```bash
# Delete the database and let it recreate
rm calculator.db
python database.py  # This will recreate it
```

### If Streamlit won't start:
```bash
# Upgrade Streamlit
pip install --upgrade streamlit
```

## 📊 Database Management Tips

### View your database (optional):
```bash
# Install sqlite viewer
pip install sqlite-viewer

# Or use SQLite command line
sqlite3 calculator.db
.tables  # Show all tables
.schema  # Show structure
SELECT * FROM clients;  # View clients
.quit  # Exit
```

### Export client data to CSV:
```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('calculator.db')
df = pd.read_sql_query("SELECT * FROM clients", conn)
df.to_csv('clients_backup.csv', index=False)
conn.close()
```

## 🎨 Customization

### Change company default name:
In `app.py`, line ~1000, change:
```python
company_name = st.text_input("Nombre de Empresa", value="YOUR COMPANY NAME", key="company_name")
```

### Add more fields to clients:
1. Edit `database.py` - Add field to CREATE TABLE
2. Edit `app.py` - Add input field in sidebar form
3. Update the `add_new_client` function call

## 📧 Support

If you have issues:
1. Check the error message in terminal
2. Make sure all packages are installed
3. Verify both files are in the same directory
4. Check that you're using Python 3.7+

---
**Version:** 3.0
**Last Updated:** December 2024
**Features:** Full client management, calculation saving, PDF generation
