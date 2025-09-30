import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import xlsxwriter
import os

# Page configuration
st.set_page_config(
    page_title="Calculadora de Nave Industrial 2030",
    page_icon="♾️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- AUTHENTICATION CONFIG ---
MAX_ATTEMPTS = 3
USER_PASSCODES = {
    "fabian": "rams20",
    "admin": "admin123"
}

# --- SESSION STATE INIT ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "username" not in st.session_state:
    st.session_state.username = ""
if 'last_steel_calc' not in st.session_state:
    st.session_state.last_steel_calc = {}
if 'last_materials_calc' not in st.session_state:
    st.session_state.last_materials_calc = {}
if 'quote_products' not in st.session_state:
    st.session_state.quote_products = []

# LABOR COST CONFIGURATION
LABOR_RATES = {
    "steel_installation_rate": 350.0,
    "roofing_rate": 8.5,
    "wall_cladding_rate": 12.0,
    "accessories_rate": 450.0,
    "supervision_days_factor": 0.05,
    "daily_supervisor_rate": 150.0,
}

def create_building_sketch_for_pdf(largo, ancho, alto_lateral, alto_techado):
    """Create a simple 2D sketch of the building for PDF inclusion"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor('white')
    
    # FRONT VIEW
    ax1.set_facecolor('white')
    ax1.set_aspect('equal')
    
    front_building = patches.Rectangle((0, 0), ancho, alto_lateral, 
                                      linewidth=2, edgecolor='black', 
                                      facecolor='lightgray', alpha=0.3)
    ax1.add_patch(front_building)
    
    roof_height = alto_techado - alto_lateral
    roof_points = [[0, alto_lateral], [ancho/2, alto_techado], [ancho, alto_lateral]]
    roof = patches.Polygon(roof_points, linewidth=2, edgecolor='black', 
                          facecolor='darkgray', alpha=0.3)
    ax1.add_patch(roof)
    
    ax1.annotate('', xy=(ancho, -1), xytext=(0, -1),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax1.text(ancho/2, -2, f'{ancho} m', ha='center', va='top', fontsize=10, fontweight='bold')
    
    ax1.annotate('', xy=(-1, alto_lateral), xytext=(-1, 0),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax1.text(-2, alto_lateral/2, f'{alto_lateral} m', ha='right', va='center', 
            fontsize=10, fontweight='bold', rotation=90)
    
    ax1.annotate('', xy=(ancho+1, alto_techado), xytext=(ancho+1, 0),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax1.text(ancho+2, alto_techado/2, f'{alto_techado} m', ha='left', va='center', 
            fontsize=10, fontweight='bold', rotation=90)
    
    ax1.set_xlim(-4, ancho+4)
    ax1.set_ylim(-4, alto_techado+2)
    ax1.set_title('VISTA FRONTAL', fontsize=12, fontweight='bold')
    ax1.axis('off')
    
    # SIDE VIEW
    ax2.set_facecolor('white')
    ax2.set_aspect('equal')
    
    side_building = patches.Rectangle((0, 0), largo, alto_lateral, 
                                     linewidth=2, edgecolor='black', 
                                     facecolor='lightgray', alpha=0.3)
    ax2.add_patch(side_building)
    
    roof_side = patches.Rectangle((0, alto_lateral), largo, roof_height, 
                                 linewidth=2, edgecolor='black', 
                                 facecolor='darkgray', alpha=0.3)
    ax2.add_patch(roof_side)
    
    ax2.annotate('', xy=(largo, -1), xytext=(0, -1),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax2.text(largo/2, -2, f'{largo} m', ha='center', va='top', fontsize=10, fontweight='bold')
    
    ax2.annotate('', xy=(-2, alto_lateral), xytext=(-2, 0),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax2.text(-3, alto_lateral/2, f'{alto_lateral} m', ha='right', va='center', 
            fontsize=10, fontweight='bold', rotation=90)
    
    ax2.set_xlim(-5, largo+3)
    ax2.set_ylim(-4, alto_techado+2)
    ax2.set_title('VISTA LATERAL', fontsize=12, fontweight='bold')
    ax2.axis('off')
    
    area = largo * ancho
    fig.text(0.5, 0.02, f'ÁREA TOTAL: {area:,.2f} m²', 
            ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()
    
    return buf

# Complete CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --primary-neon: #00ffff;
    --secondary-neon: #ff00ff;
    --accent-neon: #ffff00;
    --dark-bg: #0a0a0a;
    --card-bg: rgba(15, 15, 25, 0.95);
    --gradient-primary: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
    --gradient-secondary: linear-gradient(135deg, #ff00ff 0%, #ff6600 50%, #ffff00 100%);
    --shadow-glow: 0 0 30px rgba(0, 255, 255, 0.3);
}

.main, .stApp {
    background: radial-gradient(circle at 20% 50%, #1a0033 0%, #000000 50%, #001a33 100%);
    color: #ffffff;
    font-family: 'Space Grotesk', sans-serif;
    min-height: 100vh;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.login-container {
    max-width: 500px;
    margin: 5rem auto;
    padding: 3rem;
    background: var(--card-bg);
    border: 2px solid rgba(0, 255, 255, 0.3);
    border-radius: 30px;
    backdrop-filter: blur(25px);
    box-shadow: var(--shadow-glow);
}

.login-title {
    font-size: 42px;
    font-weight: 900;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 2rem;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--card-bg);
    border: 1px solid rgba(0, 255, 255, 0.3);
    border-radius: 25px;
    padding: 8px;
    margin: 2rem 0;
    backdrop-filter: blur(20px);
    box-shadow: var(--shadow-glow);
    gap: 12px;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 16px 28px;
    color: rgba(255, 255, 255, 0.7);
    font-weight: 600;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.4s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--gradient-primary);
    color: #000000;
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(0, 255, 255, 0.4);
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--gradient-primary);
    color: #000000;
    font-weight: 800;
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
}

.stNumberInput > div > div > input,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--card-bg) !important;
    border: 2px solid rgba(0, 255, 255, 0.3) !important;
    border-radius: 15px !important;
    color: #ffffff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 16px !important;
    padding: 16px 20px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s ease !important;
}

.stNumberInput > div > div > input:focus,
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary-neon) !important;
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.5) !important;
    outline: none !important;
}

.stSelectbox > div > div > div[role="button"] {
    background: var(--card-bg) !important;
    border: 2px solid rgba(0, 255, 255, 0.3) !important;
    border-radius: 15px !important;
    color: #ffffff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    min-height: 60px !important;
    padding: 18px 24px !important;
    backdrop-filter: blur(15px) !important;
    transition: all 0.3s ease !important;
}

.stButton > button {
    background: var(--gradient-primary) !important;
    border: none !important;
    border-radius: 20px !important;
    color: #000000 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    padding: 20px 40px !important;
    transition: all 0.4s ease !important;
    box-shadow: var(--shadow-glow) !important;
    width: 100% !important;
}

.stButton > button:hover {
    transform: translateY(-5px) scale(1.02) !important;
    box-shadow: 0 20px 60px rgba(0, 255, 255, 0.5) !important;
    background: var(--gradient-secondary) !important;
}

.metric-card {
    background: var(--card-bg) !important;
    border: 1px solid rgba(0, 255, 255, 0.3) !important;
    border-radius: 25px !important;
    padding: 32px !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: inset 0 0 30px rgba(0, 255, 255, 0.1), 0 10px 40px rgba(0, 0, 0, 0.6) !important;
    transition: all 0.4s ease !important;
    margin-bottom: 2rem !important;
}

.metric-card:hover {
    transform: translateY(-10px) !important;
    box-shadow: var(--shadow-glow), 0 20px 60px rgba(0, 0, 0, 0.8) !important;
    border-color: var(--primary-neon) !important;
}

.result-card {
    background: var(--card-bg);
    border: 3px solid transparent;
    background-clip: padding-box;
    border-radius: 30px;
    padding: 48px;
    text-align: center;
    margin: 3rem 0;
    backdrop-filter: blur(25px);
    border-image: var(--gradient-primary) 1;
}

.main-header {
    background: var(--card-bg);
    border: 2px solid rgba(0, 255, 255, 0.3);
    border-radius: 30px;
    padding: 60px 40px;
    text-align: center;
    margin: -2rem -2rem 4rem -2rem;
    backdrop-filter: blur(25px);
    box-shadow: var(--shadow-glow);
}

.section-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 32px;
    font-weight: 800;
    background: var(--gradient-secondary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 3rem 0 2rem 0;
    text-transform: uppercase;
    letter-spacing: 3px;
    border-left: 6px solid var(--primary-neon);
    padding-left: 24px;
}

@media (max-width: 768px) {
    .main-title { font-size: 36px; }
}
</style>
""", unsafe_allow_html=True)

# --- LOGIN PAGE ---
def show_login_page():
    logo_paths = ["logo.png", "assets/logo.png", "logo.jpg", "assets/logo.jpg"]
    logo_displayed = False
    
    for logo_path in logo_paths:
        if os.path.exists(logo_path):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo_path, use_container_width=True)
            logo_displayed = True
            break
    
    if not logo_displayed:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="font-size: 72px;">🏗️</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="login-container">
        <div class="login-title">🔐 ACCESO SEGURO</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Sistema de Cotización Industrial")
        st.markdown("---")
        
        username = st.text_input("👤 Usuario", key="login_username")
        passcode = st.text_input("🔑 Contraseña", type="password", key="login_passcode")
        
        st.markdown("")
        
        if st.button("🚀 INGRESAR", key="login_btn"):
            if username and passcode:
                expected_passcode = USER_PASSCODES.get(username.lower())
                
                if expected_passcode and passcode == expected_passcode:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.attempts = 0
                    st.success(f"✅ Bienvenido, {username.capitalize()}!")
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    
                    if st.session_state.attempts >= MAX_ATTEMPTS:
                        st.error("❌ Demasiados intentos fallidos. Por favor recargue la página.")
                        st.stop()
                    else:
                        remaining = MAX_ATTEMPTS - st.session_state.attempts
                        st.warning(f"⚠️ Credenciales incorrectas. Intentos restantes: {remaining}")
            else:
                st.warning("⚠️ Por favor ingrese usuario y contraseña")
        
        st.markdown("---")
        st.caption("© 2030 Calculadora Industrial — Acceso Seguro")

# Steel profiles data
@st.cache_data
def get_steel_profiles():
    try:
        df = pd.read_excel("steel_profiles.xlsx")
        profiles_list = []
        for _, row in df.iterrows():
            series = str(row['Series']).strip()
            weight = row['Weight']
            full_name = f"{series}x{weight}"
            profiles_list.append((full_name, weight))
        return profiles_list
    except Exception as e:
        st.warning(f"Could not load steel_profiles.xlsx: {e}")
        hardcoded_profiles = {
            'IPE-80': 6.0, 'IPE-100': 8.1, 'IPE-120': 10.4, 'IPE-140': 12.9,
            'IPE-160': 15.8, 'IPE-180': 18.8, 'IPE-200': 22.4, 'IPE-220': 26.2,
            'IPE-240': 30.7, 'IPE-270': 36.1, 'IPE-300': 42.2, 'IPE-330': 49.1,
            'IPE-360': 57.1, 'IPE-400': 66.3, 'IPE-450': 77.6, 'IPE-500': 90.7,
            'IPE-550': 106.0, 'IPE-600': 122.0
        }
        return [(profile, weight) for profile, weight in hardcoded_profiles.items()]

# Materials prices data
@st.cache_data
def get_materials_prices():
    try:
        df = pd.read_excel("precios_materiales.xlsx")
        
        material_col = None
        precio_col = None
        unidad_col = None
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in ['material', 'materiales', 'producto', 'item', 'nombre', 'product_name', 'product']:
                material_col = col
                break
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in ['precio', 'price', 'costo', 'valor', 'unit_price', 'unitprice']:
                precio_col = col
                break
                
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in ['unidad', 'unit', 'medida', 'um', 'unit ']:
                unidad_col = col
                break
        
        if not material_col or not precio_col:
            raise ValueError(f"Columnas requeridas no encontradas")
        
        prices_dict = {}
        for _, row in df.iterrows():
            material_name = str(row[material_col]).strip()
            price = float(row[precio_col])
            unit = str(row[unidad_col]).strip() if unidad_col else 'unidades'
            prices_dict[material_name] = {'precio': price, 'unidad': unit}
        
        return prices_dict
        
    except Exception as e:
        st.warning(f"No se pudo cargar precios_materiales.xlsx: {e}")
        return {
            'Aluzinc Techo': {'precio': 8.5, 'unidad': 'pies'},
            'Aluzinc Paredes': {'precio': 8.5, 'unidad': 'pies'},
            'Correas Techo': {'precio': 12.0, 'unidad': 'pies'},
            'Correas Paredes': {'precio': 12.0, 'unidad': 'pies'},
            'Tornillos para Techo': {'precio': 0.15, 'unidad': 'unidades'},
            'Tornillos 3/4"': {'precio': 0.25, 'unidad': 'unidades'},
            'Tillas': {'precio': 15.0, 'unidad': 'unidades'},
            'Tornillos 1/2"': {'precio': 0.18, 'unidad': 'unidades'},
            'Caños': {'precio': 18.0, 'unidad': 'pies'},
            'Caballetes': {'precio': 20.0, 'unidad': 'pies'},
            'Cubrefaltas': {'precio': 12.5, 'unidad': 'pies'},
            'Bajantes': {'precio': 35.0, 'unidad': 'unidades'},
            'Boquillas': {'precio': 8.0, 'unidad': 'unidades'},
            'Pernos': {'precio': 2.5, 'unidad': 'unidades'},
            'Acero Estructural': {'precio': 2800.0, 'unidad': 'ton'}
        }

class QuotationGenerator:
    @staticmethod
    def calculate_quote(products):
        items_total = 0
        for p in products:
            if p.get('subtotal') and isinstance(p.get('subtotal'), (int, float)):
                items_total += float(p.get('subtotal', 0))
            elif p.get('quantity') and p.get('unit_price'):
                quantity = float(p.get('quantity', 0))
                unit_price = float(p.get('unit_price', 0))
                items_total += quantity * unit_price

        supervision = items_total * 0.10
        admin = items_total * 0.04
        insurance = items_total * 0.01
        transport = items_total * 0.03
        contingency = items_total * 0.03

        subtotal_general = items_total + supervision + admin + insurance + transport + contingency
        itbis = subtotal_general * 0.18
        grand_total = subtotal_general + itbis

        return {
            'items_total': round(items_total, 2),
            'supervision': round(supervision, 2),
            'admin': round(admin, 2),
            'insurance': round(insurance, 2),
            'transport': round(transport, 2),
            'contingency': round(contingency, 2),
            'subtotal_general': round(subtotal_general, 2),
            'itbis': round(itbis, 2),
            'grand_total': round(grand_total, 2)
        }

    @staticmethod
    def generate_pdf(quote_data, company_info, products, totals, show_products=True, building_sketch_buffer=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        story = []
        styles = getSampleStyleSheet()

        # Logo
        logo_paths = ["assets/logo.png", "logo.png", "assets/logo.jpg", "logo.jpg"]
        logo_added = False
        for logo_path in logo_paths:
            try:
                if os.path.exists(logo_path):
                    logo = Image(logo_path, width=1 * inch, height=0.5 * inch)
                    logo.hAlign = 'LEFT'
                    story.append(logo)
                    story.append(Spacer(0.5, 0.1 * inch))
                    logo_added = True
                    break
            except Exception:
                continue
        
        if not logo_added:
            company_header = ParagraphStyle(
                'CompanyHeader',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                textColor=colors.HexColor('#004898'),
                alignment=0,
                spaceAfter=12
            )
            story.append(Paragraph("EMPRESA CONSTRUCTORA", company_header))
            story.append(Spacer(1, 0.1 * inch))

        # Company information
        company_info_style = ParagraphStyle(
            'CompanyInfo',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6,
            leading=9,
            textColor=colors.black,
            alignment=0,
            spaceAfter=6
        )
        
        company_info_text = (
            "PARQUE INDUSTRIAL DISDO - CALLE CENTRAL No. 1<br/>"
            "HATO NUEVO PALAVE - SECTOR MANOGUAYABO<br/>"
            "SANTO DOMINGO OESTE • TEL: 829-439-8476<br/>"
            "RNC: 131-71683-2"
        )
        
        story.append(Paragraph(company_info_text, company_info_style))
        story.append(Spacer(1, 0.15 * inch))
        
        # Divider line
        divider_table = Table([['']], colWidths=[6.5 * inch])
        divider_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#004898')),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(divider_table)
        story.append(Spacer(1, 0.2 * inch))

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#004898'),
            alignment=TA_RIGHT,
            spaceAfter=12
        )
        story.append(Paragraph("ESTIMADO", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Quote number logic
        client_name = company_info.get('client', '').strip()
        initials = ''.join([word[0].upper() for word in client_name.split() if word]) if client_name and client_name != "Cliente No Especificado" else 'SC'
        quote_date = datetime.now().strftime('%Y%m%d')
        quote_number = f"{initials}-{quote_date}/1"

        # Info block
        info_data = [
            ['INFORMACIÓN DEL PROYECTO', ''],
            ['Compañía:', company_info.get('company_name', 'N/A')],
            ['Teléfono:', company_info.get('phone', 'N/A')],
            ['Email:', company_info.get('email', 'N/A')],
            ['Cotización Nº:', quote_number],
            ['Cliente:', company_info['client']],
            ['Proyecto:', company_info['project']],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y')],
            ['Validez:', company_info['validity']],
            ['Cotizado por:', company_info.get('quoted_by', 'N/A')]
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004898')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 1), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.2 * inch))

        # Add 2D Building Sketch if provided
        if building_sketch_buffer:
            try:
                sketch_image = Image(building_sketch_buffer, width=6 * inch, height=2.4 * inch)
                sketch_image.hAlign = 'CENTER'
                story.append(sketch_image)
                story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                print(f"Error adding sketch to PDF: {e}")

        # Notes section
        if company_info.get('notes'):
            notes_text = company_info['notes']
            notes_style = ParagraphStyle(
                'NotesStyle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=12,
                textColor=colors.black,
                alignment=0,
                leftIndent=0,
                rightIndent=0,
                spaceAfter=6,
                spaceBefore=0
            )
            
            formatted_notes = notes_text.replace('\n', '<br/>')
            notes_para = Paragraph(formatted_notes, notes_style)
            notes_table = Table([[notes_para]], colWidths=[6.5 * inch])
            notes_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, colors.gray),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(notes_table)
            story.append(Spacer(1, 0.2 * inch))
        
        story.append(Spacer(1, 0.2 * inch))

        # Products table
        if show_products and products:
            products_data = [['Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']]
            for product in products:
                if product.get('product_name'):
                    products_data.append([
                        product['product_name'],
                        f"{product.get('quantity', 0):,.2f}",
                        f"${product.get('unit_price', 0):,.2f}",
                        f"${product.get('subtotal', 0):,.2f}"
                    ])

            products_table = Table(products_data, colWidths=[3 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
            products_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fc')]),
            ]))
            story.append(products_table)
            story.append(Spacer(1, 0.2 * inch))

        # Totals table
        totals_data = [
            ['RESUMEN DE COSTOS', ''],
            ['Total Items:', f"${totals['items_total']:,.2f}"],
            ['Supervisión Técnica e Ingeniería (10%):', f"${totals['supervision']:,.2f}"],
            ['Gastos Administrativos (4%):', f"${totals['admin']:,.2f}"],
            ['Seguro de Riesgo (1%):', f"${totals['insurance']:,.2f}"],
            ['Transporte (3%):', f"${totals['transport']:,.2f}"],
            ['Imprevisto (3%):', f"${totals['contingency']:,.2f}"],
            ['', ''],
            ['Subtotal General:', f"${totals['subtotal_general']:,.2f}"],
            ['ITBIS (18%):', f"${totals['itbis']:,.2f}"],
            ['', ''],
            ['TOTAL GENERAL:', f"${totals['grand_total']:,.2f}"]
        ]

        totals_table = Table(totals_data, colWidths=[4 * inch, 2 * inch])
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004898')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 11), (-1, 11), colors.HexColor('#004898')),
            ('TEXTCOLOR', (0, 11), (-1, 11), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 11), (-1, 11), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 1), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(totals_table)

        # Disclaimer
        nota_texto = (
            "<b>Nota:</b> "
            "<b>Esta cotización es solo un estimado.</b>"
            "Todos los precios están sujetos a cambios. "
            "El precio final será confirmado al momento de emitir la orden de compra. "
            "Será necesaria una cotización formal para validar los términos y condiciones definitivos."
        )
        
        nota_style = ParagraphStyle(
            'FinePrintBold',
            fontName='Helvetica-Bold',
            fontSize=6,
            leading=8,
            textColor=colors.black,
            alignment=0
        )
        
        nota_parrafo = Paragraph(nota_texto, nota_style)
        nota_table = Table([[nota_parrafo]], colWidths=[6.5 * inch])
        nota_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.gray),
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(Spacer(1, 0.3 * inch))
        story.append(nota_table)

        doc.build(story)
        buffer.seek(0)
        return buffer

# --- MAIN APP ---
def show_main_app():
    # Logout button in sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username.capitalize()}")
        st.markdown("---")
        if st.button("🔓 Cerrar Sesión", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <div style="font-size: 56px; font-weight: 900; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            🏗️ Calculadora Componentes Nave Signature
        </div>
        <div style="font-size: 18px; color: rgba(255, 255, 255, 0.8); margin-top: 1rem;">
            Sistema RIGC. Cálculo Estructural + Cotización 2030
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load profiles and materials prices
    try:
        profiles = get_steel_profiles()
        profile_options = [f"{p[0]}" for p in profiles]
        profile_weights = {f"{p[0]}": p[1] for p in profiles}
    except:
        profile_weights = {
            'IPE-80': 6.0, 'IPE-100': 8.1, 'IPE-120': 10.4, 'IPE-140': 12.9,
            'IPE-160': 15.8, 'IPE-180': 18.8, 'IPE-200': 22.4, 'IPE-220': 26.2,
            'IPE-240': 30.7, 'IPE-270': 36.1, 'IPE-300': 42.2, 'IPE-330': 49.1,
            'IPE-360': 57.1, 'IPE-400': 66.3, 'IPE-450': 77.6, 'IPE-500': 90.7,
            'IPE-550': 106.0, 'IPE-600': 122.0
        }
        profile_options = list(profile_weights.keys())

    materials_prices = get_materials_prices()

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "🔩 Cálculo de Acero", 
        "📦 Materiales",  
        "📋 Cotización"
    ])

    # TAB 1: STEEL CALCULATION
    with tab1:
        st.markdown('<div class="section-header">Cálculo de Acero Estructural</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            largo = st.number_input("Largo (m)", min_value=0.0, value=80.0, step=0.1, key="steel_largo")
        with col2:
            ancho = st.number_input("Ancho (m)", min_value=0.0, value=25.0, step=0.1, key="steel_ancho")
        with col3:
            alto_lateral = st.number_input("Altura Lateral (m)", min_value=0.0, value=9.0, step=0.1, key="steel_alto_lateral")
        with col4:
            distancia = st.number_input("Distancia entre Ejes (m)", min_value=0.1, value=7.27, step=0.01, key="steel_distancia")
        
        st.markdown('<div class="section-header">Selección de Perfiles</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            columnas_idx = st.selectbox("Perfil Columnas", options=range(len(profile_options)), 
                                         format_func=lambda x: profile_options[x], key="col_profile")
            columnas = profile_options[columnas_idx]
        with col2:
            tijerillas_idx = st.selectbox("Perfil Tijerillas", options=range(len(profile_options)), 
                                           format_func=lambda x: profile_options[x], key="beam_profile")
            tijerillas = profile_options[tijerillas_idx]
        with col3:
            porticos_idx = st.selectbox("Perfil Pórticos", options=range(len(profile_options)), 
                                         format_func=lambda x: profile_options[x], key="frame_profile")
            porticos = profile_options[porticos_idx]
        with col4:
            laterales_idx = st.selectbox("Perfil Columnas Laterales", options=range(len(profile_options)), 
                                          format_func=lambda x: profile_options[x], key="lat_profile")
            columnas_laterales = profile_options[laterales_idx]
        
        col1, col2, col3 = st.columns([2, 2, 4])
        
        with col1:
            num_lados = st.selectbox("Lados Laterales", options=[1, 2], index=1, key="lat_lados")
        with col2:
            incluir_laterales = st.checkbox("Incluir Columnas Laterales", value=True, key="include_lateral")
        with col3:
            st.info("Columnas Laterales se calculan: (Largo ÷ Distancia + 1) × Lados × Altura × Peso × 3.28")
        
        if st.button("🔩 Calcular Acero Estructural Completo", type="primary", key="calc_steel_btn"):
            try:
                peso_columnas = profile_weights[columnas]
                peso_tijerillas = profile_weights[tijerillas]
                peso_porticos = profile_weights[porticos]
                peso_laterales = profile_weights[columnas_laterales]
                
                num_columnas = ((largo / distancia) + 1) * 2
                libras_columnas = num_columnas * alto_lateral * peso_columnas * 3.28
                ton_columnas = libras_columnas / 2204.62
                
                num_tijerillas_calc = ((largo / distancia) + 1) * 2
                libras_tijerillas = num_tijerillas_calc * 1.1 * ancho * peso_tijerillas * 3.28
                ton_tijerillas = libras_tijerillas / 2204.62
                
                perimetro = (ancho * 2) + (largo * 2)
                libras_porticos = perimetro * peso_porticos * 3.28
                ton_porticos = libras_porticos / 2204.62
                
                num_columnas_frontales = ((ancho / distancia) + 1) * 2
                libras_columnas_frontales = num_columnas_frontales * alto_lateral * 1.1 * 3.28 * peso_columnas
                ton_columnas_frontales = libras_columnas_frontales / 2204.62
                
                if incluir_laterales:
                    num_columnas_laterales = ((largo / distancia) + 1) * num_lados
                    libras_columnas_laterales = num_columnas_laterales * alto_lateral * peso_laterales * 3.28
                    ton_columnas_laterales = libras_columnas_laterales / 2204.62
                else:
                    num_columnas_laterales = 0
                    libras_columnas_laterales = 0
                    ton_columnas_laterales = 0
                
                total_libras = (libras_columnas + libras_tijerillas + libras_porticos + 
                               libras_columnas_frontales + libras_columnas_laterales)
                libras_conexiones = total_libras * 0.15
                ton_conexiones = libras_conexiones / 2204.62
                
                cantidad_pernos = ((largo / distancia) + 1) * 2
                tornillos_3_4 = int(libras_conexiones / 5)
                
                total_ton = (ton_columnas + ton_tijerillas + ton_porticos + 
                            ton_columnas_frontales + ton_columnas_laterales + ton_conexiones)
                
                st.session_state.last_steel_calc = {
                    'num_columnas': num_columnas,
                    'num_tijerillas': num_tijerillas_calc,
                    'num_porticos': perimetro,
                    'ton_columnas': ton_columnas,
                    'ton_tijerillas': ton_tijerillas,
                    'ton_porticos': ton_porticos,
                    'ton_frontales': ton_columnas_frontales,
                    'ton_laterales': ton_columnas_laterales,
                    'ton_conexiones': ton_conexiones,
                    'total_ton': total_ton,
                    'pernos': cantidad_pernos,
                    'tornillos_3_4': tornillos_3_4,
                    'largo': largo,
                    'ancho': ancho,
                    'alto_lateral': alto_lateral
                }
                
                st.success("✅ Cálculo de Acero Estructural Completado Exitosamente")
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8); margin-bottom: 12px;">COLUMNAS PRINCIPALES</div>
                        <div style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{num_columnas:.0f}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">unidades</div>
                        <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                        <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8);">TONELAJE</div>
                        <div style="font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{ton_columnas:.2f}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">ton</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8); margin-bottom: 12px;">TIJERILLAS</div>
                        <div style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{num_tijerillas_calc:.0f}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">unidades</div>
                        <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                        <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8);">TONELAJE</div>
                        <div style="font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{ton_tijerillas:.2f}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">ton</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8); margin-bottom: 12px;">PÓRTICOS DE FRENADO</div>
                        <div style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{perimetro:.1f}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">m perímetro</div>
                        <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                        <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8);">TONELAJE</div>
                        <div style="font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{ton_porticos:.2f}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">ton</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                lateral_text = f" | Laterales: {ton_columnas_laterales:,.2f} ton" if incluir_laterales else ""
                st.markdown(f"""
                <div class="result-card">
                    <div style="font-size: 24px; font-weight: 800; color: rgba(0, 255, 255, 0.9); margin-bottom: 24px;">TOTAL ACERO ESTRUCTURAL</div>
                    <div style="font-size: 64px; font-weight: 900; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 24px 0;">{total_ton:,.2f} TON</div>
                    <div style="font-size: 16px; color: rgba(255, 255, 255, 0.7);">
                        Columnas: {ton_columnas:,.2f} | Tijerillas: {ton_tijerillas:,.2f} | Pórticos: {ton_porticos:,.2f} | 
                        Frontales: {ton_columnas_frontales:,.2f}{lateral_text} | Conexiones: {ton_conexiones:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Create chart
                fig = go.Figure()
                
                components = ['Columnas', 'Tijerillas', 'Pórticos', 'Col. Frontales']
                tonnages = [ton_columnas, ton_tijerillas, ton_porticos, ton_columnas_frontales]
                colors_chart = ['rgba(0, 255, 255, 0.8)', 'rgba(255, 0, 255, 0.8)', 'rgba(255, 255, 0, 0.8)', 'rgba(0, 255, 0, 0.8)']
                
                if incluir_laterales:
                    components.append('Col. Laterales')
                    tonnages.append(ton_columnas_laterales)
                    colors_chart.append('rgba(255, 150, 0, 0.8)')
                
                components.append('Conexiones')
                tonnages.append(ton_conexiones)
                colors_chart.append('rgba(150, 0, 255, 0.8)')
                
                for i, (component, tonnage, color) in enumerate(zip(components, tonnages, colors_chart)):
                    fig.add_trace(go.Bar(
                        name=component,
                        x=[component],
                        y=[tonnage],
                        marker=dict(color=color, line=dict(color=color.replace('0.8', '1'), width=2)),
                        hovertemplate=f'<b>{component}</b><br>Tonelaje: %{{y:.2f}} ton<extra></extra>'
                    ))
                
                fig.update_layout(
                    title=dict(text='Distribución Completa de Tonelaje de Acero', font=dict(size=24, color='white', family='Space Grotesk')),
                    plot_bgcolor='rgba(0, 0, 0, 0)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    font=dict(color='white', family='JetBrains Mono'),
                    showlegend=False,
                    height=500,
                    xaxis=dict(showgrid=True, gridcolor='rgba(0, 255, 255, 0.2)', color='white'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(0, 255, 255, 0.2)', color='white', title='Tonelaje (ton)')
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error en el cálculo: {str(e)}")

    # TAB 2: MATERIALS
    with tab2:
        st.markdown('<div class="section-header">Cálculo de Materiales</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            mat_ancho = st.number_input("Ancho (m)", min_value=0.0, value=25.0, step=0.1, key="mat_ancho")
        with col2:
            mat_largo = st.number_input("Largo (m)", min_value=0.0, value=80.0, step=0.1, key="mat_largo")
        with col3:
            mat_alt_lat = st.number_input("Altura Laterales (m)", min_value=0.0, value=9.0, step=0.1, key="mat_alt_lat")
        with col4:
            mat_alt_tech = st.number_input("Altura Techado (m)", min_value=0.0, value=12.0, step=0.1, key="mat_alt_tech")
        with col5:
            mat_dist = st.number_input("Distancia Ejes (m)", min_value=0.1, value=7.27, step=0.01, key="mat_dist")
        
        if st.button("📦 Calcular Materiales + Instalación", type="primary", key="calc_materials_btn"):
            try:
                # Material calculations
                aluzinc_techo = (mat_ancho * mat_largo) * 1.1 * 3.28
                aluzinc_paredes = (mat_ancho * 2 + mat_largo * 2) * mat_alt_tech * 3.28
                correas_techo = (mat_ancho + 2) * mat_largo * 3.28
                correas_paredes = (mat_ancho * 2 + mat_largo * 2) * (mat_alt_tech + 1) * 3.28
                tornillos_Techo = (aluzinc_techo + aluzinc_paredes) * 5
                tornillos_3_4 = int((aluzinc_techo + aluzinc_paredes) * 3)
                tillas = (mat_largo / mat_dist) * (mat_ancho + 2)
                tornillos_media = (((correas_techo + correas_paredes) / 3.28) / mat_dist) * 4
                canos = (mat_largo * 2) * 1.1 * 3.28
                caballetes = canos / 2
                cubrefaltas = ((mat_ancho * 2) + (mat_alt_tech * 4)) * 1.1 * 3.28
                bajantes = ((mat_largo / mat_dist) + 1) * 2
                boquillas = ((mat_largo / mat_dist) + 1) * 2
                pernos = (mat_largo / 7.27 + 1) * 2
                area_total = mat_ancho * mat_largo
                
                # Calculate labor costs
                steel_tons = st.session_state.last_steel_calc.get('total_ton', 0) if st.session_state.last_steel_calc else 0
                roof_area = mat_ancho * mat_largo
                wall_area = (mat_largo * 2 + mat_ancho * 2) * mat_alt_lat
                
                steel_labor = steel_tons * LABOR_RATES["steel_installation_rate"]
                roofing_labor = roof_area * LABOR_RATES["roofing_rate"]
                wall_labor = wall_area * LABOR_RATES["wall_cladding_rate"]
                accessories_labor = LABOR_RATES["accessories_rate"]
                supervision_days = area_total * LABOR_RATES["supervision_days_factor"]
                supervision_cost = supervision_days * LABOR_RATES["daily_supervisor_rate"]
                total_labor = steel_labor + roofing_labor + wall_labor + accessories_labor + supervision_cost
                
                # Save calculations
                st.session_state.last_materials_calc = {
                    'aluzinc_techo': aluzinc_techo,
                    'aluzinc_paredes': aluzinc_paredes,
                    'correas_techo': correas_techo,
                    'correas_paredes': correas_paredes,
                    'tornillos_techo': tornillos_Techo,
                    'tornillos_3_4': tornillos_3_4,
                    'tillas': tillas,
                    'tornillos_media': tornillos_media,
                    'canos': canos,
                    'caballetes': caballetes,
                    'cubrefaltas': cubrefaltas,
                    'bajantes': bajantes,
                    'boquillas': boquillas,
                    'pernos': pernos,
                    'area_total': area_total,
                    'steel_labor': steel_labor,
                    'roofing_labor': roofing_labor,
                    'wall_labor': wall_labor,
                    'accessories_labor': accessories_labor,
                    'supervision_cost': supervision_cost,
                    'supervision_days': supervision_days,
                    'total_labor': total_labor
                }
                
                st.success("✅ Cálculo de materiales e instalación completado exitosamente")
                
                # Materials table
                materials_data = {
                    'Material': [
                        'Aluzinc Techo', 'Aluzinc Paredes', 'Correas Techo', 'Correas Paredes',
                        'Tornillos', 'Tornillos 3/4"', 'Tillas', 'Tornillos 1/2"', 'Caños', 'Caballetes',
                        'Cubrefaltas', 'Bajantes', 'Boquillas', 'Pernos',
                        '--- INSTALACIÓN ---',
                        'Instalación Acero', 'Instalación Techo', 'Instalación Paredes',
                        'Accesorios', 'Supervisión'
                    ],
                    'Cantidad': [
                        f"{aluzinc_techo:,.0f} pies", f"{aluzinc_paredes:,.0f} pies",
                        f"{correas_techo:,.0f} pies", f"{correas_paredes:,.0f} pies",
                        f"{tornillos_Techo:,.0f} unidades",
                        f"{tornillos_3_4:,.0f} unidades",
                        f"{tillas:,.0f} unidades", f"{tornillos_media:,.0f} unidades",
                        f"{canos:,.0f} pies", f"{caballetes:,.0f} pies",
                        f"{cubrefaltas:,.0f} pies", f"{bajantes:,.0f} unidades",
                        f"{boquillas:,.0f} unidades", f"{pernos:,.0f} unidades",
                        '',
                        f"{steel_tons:.2f} ton × ${LABOR_RATES['steel_installation_rate']}/ton",
                        f"{roof_area:,.2f} m² × ${LABOR_RATES['roofing_rate']}/m²",
                        f"{wall_area:,.2f} m² × ${LABOR_RATES['wall_cladding_rate']}/m²",
                        f"Tarifa fija",
                        f"{supervision_days:.1f} días × ${LABOR_RATES['daily_supervisor_rate']}/día"
                    ],
                    'Costo': [
                        '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-',
                        '',
                        f"${steel_labor:,.2f}",
                        f"${roofing_labor:,.2f}",
                        f"${wall_labor:,.2f}",
                        f"${accessories_labor:,.2f}",
                        f"${supervision_cost:,.2f}"
                    ]
                }
                
                df_materials = pd.DataFrame(materials_data)
                st.dataframe(df_materials, hide_index=True, use_container_width=True, height=600)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-size: 24px; font-weight: 800; color: rgba(0, 255, 255, 0.9); margin-bottom: 24px;">ÁREA TOTAL</div>
                        <div style="font-size: 48px; font-weight: 900; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{area_total:,.2f} m²</div>
                        <div style="font-size: 16px; color: rgba(255, 255, 255, 0.7); margin-top: 12px;">{area_total * 10.764:,.2f} pies²</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-size: 24px; font-weight: 800; color: rgba(255, 255, 0, 0.9); margin-bottom: 24px;">COSTO INSTALACIÓN</div>
                        <div style="font-size: 48px; font-weight: 900; background: linear-gradient(135deg, #ffff00 0%, #ff6600 50%, #ff00ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">${total_labor:,.2f}</div>
                        <div style="font-size: 16px; color: rgba(255, 255, 255, 0.7); margin-top: 12px;">Mano de obra completa</div>
                    </div>
                    """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error en el cálculo de materiales: {str(e)}")

    # TAB 3: QUOTATION
    with tab3:
        st.markdown('<div class="section-header">Generador de Cotizaciones</div>', unsafe_allow_html=True)
        
        st.markdown("### Información de la Cotización")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Nombre de Compañía", key="company_name", value="")
            client_name = st.text_input("Cliente", key="client_name", value="")
            project_name = st.text_input("Proyecto", key="project_name", value="")
            quoted_by = st.text_input("Cotizado por", key="quoted_by", value="")
        with col2:
            phone = st.text_input("Teléfono", key="phone", value="", placeholder="809-123-4567")
            email = st.text_input("Email", key="email", value="", placeholder="contacto@empresa.com")
            quote_date = st.date_input("Fecha", datetime.now())
            quote_validity = st.selectbox("Validez", ["15 días", "30 días", "45 días", "60 días"])
        
        notes = st.text_area("Notas/Observaciones", height=100, value="")
        
        # Import from calculations section
        st.markdown("### Importar desde Cálculos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔩 Importar Cálculo de Acero", key="import_steel_btn"):
                if st.session_state.last_steel_calc:
                    calc = st.session_state.last_steel_calc
                    steel_price = materials_prices.get('Acero Estructural', {}).get('precio', 2800.0)
                    
                    steel_product = {
                        'product_name': f"Acero Estructural - {calc['total_ton']:.2f} ton",
                        'quantity': calc['total_ton'],
                        'unit_price': steel_price,
                        'subtotal': calc['total_ton'] * steel_price
                    }
                    st.session_state.quote_products.append(steel_product)
                    st.success("Cálculo de acero importado exitosamente")
                else:
                    st.warning("No hay cálculo de acero disponible. Calcule primero en la pestaña correspondiente.")
        
        with col2:
            if st.button("📦 Importar Materiales + Instalación", key="import_materials_btn"):
                if st.session_state.last_materials_calc:
                    calc = st.session_state.last_materials_calc
                    
                    # Material names to match with Excel
                    materials_mapping = [
                        ('Aluzinc Techo', calc['aluzinc_techo']),
                        ('Aluzinc Paredes', calc['aluzinc_paredes']),
                        ('Correas Techo', calc['correas_techo']),
                        ('Correas Paredes', calc['correas_paredes']),
                        ('Tornillos para Techo', calc['tornillos_techo']),
                        ('Tornillos 3/4"', calc['tornillos_3_4']),
                        ('Tillas', calc['tillas']),
                        ('Tornillos 1/2"', calc['tornillos_media']),
                        ('Caños', calc['canos']),
                        ('Caballetes', calc['caballetes']),
                        ('Cubrefaltas', calc['cubrefaltas']),
                        ('Bajantes', calc['bajantes']),
                        ('Boquillas', calc['boquillas']),
                        ('Pernos', calc['pernos']),
                    ]
                    
                    imported_count = 0
                    for material_name, quantity in materials_mapping:
                        if quantity > 0:
                            price_info = materials_prices.get(material_name, {'precio': 0.0, 'unidad': 'unidades'})
                            unit_price = price_info['precio']
                            unit = price_info['unidad']
                            
                            material_product = {
                                'product_name': f"{material_name} - {quantity:,.0f} {unit}",
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'subtotal': quantity * unit_price
                            }
                            st.session_state.quote_products.append(material_product)
                            imported_count += 1
                    
                    # Add labor costs as products
                    labor_items = [
                        ('Instalación de Acero Estructural', 1, calc['steel_labor']),
                        ('Instalación de Techo', 1, calc['roofing_labor']),
                        ('Instalación de Paredes', 1, calc['wall_labor']),
                        ('Accesorios e Instalaciones Menores', 1, calc['accessories_labor']),
                        ('Supervisión Técnica', 1, calc['supervision_cost'])
                    ]
                    
                    for labor_name, qty, cost in labor_items:
                        st.session_state.quote_products.append({
                            'product_name': labor_name,
                            'quantity': qty,
                            'unit_price': cost,
                            'subtotal': cost
                        })
                        imported_count += 1
                    
                    st.success(f"Se importaron {imported_count} items (materiales + instalación)")
                else:
                    st.warning("No hay cálculo de materiales disponible. Calcule primero en la pestaña correspondiente.")
        
        # Products Section
        st.markdown("### Productos")
        
        # Add new product form
        with st.expander("➕ Agregar Producto"):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_product_name = st.text_input("Nombre del Producto", key="new_product_name")
            with col2:
                new_quantity = st.number_input("Cantidad", min_value=0.0, value=1.0, step=0.1, key="new_quantity")
            with col3:
                new_unit_price = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=0.01, key="new_unit_price")
            
            if st.button("Agregar Producto", key="add_product_btn"):
                if new_product_name and new_quantity > 0 and new_unit_price > 0:
                    new_product = {
                        'product_name': new_product_name,
                        'quantity': new_quantity,
                        'unit_price': new_unit_price,
                        'subtotal': new_quantity * new_unit_price
                    }
                    st.session_state.quote_products.append(new_product)
                    st.success(f"Producto '{new_product_name}' agregado exitosamente")
                else:
                    st.error("Por favor complete todos los campos con valores válidos")
        
        # Display current products
        if st.session_state.quote_products:
            st.markdown("### Productos en la Cotización")
            
            # Create editable data frame
            products_df = pd.DataFrame(st.session_state.quote_products)
            
            # Ensure all columns exist
            if 'product_name' not in products_df.columns:
                products_df['product_name'] = ''
            if 'quantity' not in products_df.columns:
                products_df['quantity'] = 0.0
            if 'unit_price' not in products_df.columns:
                products_df['unit_price'] = 0.0
            if 'subtotal' not in products_df.columns:
                products_df['subtotal'] = 0.0
            
            # Convert types
            products_df['quantity'] = pd.to_numeric(products_df['quantity'], errors='coerce').fillna(0)
            products_df['unit_price'] = pd.to_numeric(products_df['unit_price'], errors='coerce').fillna(0)
            products_df['subtotal'] = products_df['quantity'] * products_df['unit_price']
            
            # Show editable table
            edited_df = st.data_editor(
                products_df,
                column_config={
                    "product_name": st.column_config.TextColumn("Producto", width="large"),
                    "quantity": st.column_config.NumberColumn("Cantidad", format="%.2f"),
                    "unit_price": st.column_config.NumberColumn("Precio Unit. ($)", format="%.2f"),
                    "subtotal": st.column_config.NumberColumn("Subtotal ($)", format="%.2f", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",
                key="products_editor"
            )
            
            # Update session state with edited data
            if not edited_df.empty:
                # Filter valid products and convert to records
                valid_products = edited_df[
                    (edited_df['product_name'].notna()) & 
                    (edited_df['product_name'] != '') &
                    (edited_df['quantity'] > 0)
                ].copy()
                
                # Ensure all numeric fields are properly converted
                valid_products['quantity'] = valid_products['quantity'].astype(float)
                valid_products['unit_price'] = valid_products['unit_price'].astype(float)
                valid_products['subtotal'] = valid_products['quantity'] * valid_products['unit_price']
                
                st.session_state.quote_products = valid_products.to_dict('records')
            
            # Remove products section
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Limpiar Productos", key="clear_products_btn"):
                    st.session_state.quote_products = []
                    st.rerun()
            
            # Calculate totals if there are valid products
            if st.session_state.quote_products:
                totals = QuotationGenerator.calculate_quote(st.session_state.quote_products)
                
                # Display totals
                st.markdown("### Resumen de Costos")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Items", f"${totals['items_total']:,.2f}")
                    st.metric("Supervisión Técnica (10%)", f"${totals['supervision']:,.2f}")
                    st.metric("Gastos Admin. (4%)", f"${totals['admin']:,.2f}")
                
                with col2:
                    st.metric("Seguro de Riesgo (1%)", f"${totals['insurance']:,.2f}")
                    st.metric("Transporte (3%)", f"${totals['transport']:,.2f}")
                    st.metric("Imprevisto (3%)", f"${totals['contingency']:,.2f}")
                
                with col3:
                    st.metric("Subtotal General", f"${totals['subtotal_general']:,.2f}")
                    st.metric("ITBIS (18%)", f"${totals['itbis']:,.2f}")
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-size: 24px; font-weight: 800; color: rgba(0, 255, 0, 0.9); margin-bottom: 24px;">TOTAL GENERAL</div>
                        <div style="font-size: 48px; font-weight: 900; background: linear-gradient(135deg, #00ff00 0%, #00ffff 50%, #0099ff 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">${totals['grand_total']:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Generate PDF button
                st.markdown("### Generar Cotización")
                
                col1, col2 = st.columns(2)
                with col1:
                    show_products_in_pdf = st.checkbox("Mostrar productos en PDF", value=True)
                with col2:
                    include_sketch = st.checkbox("Incluir diagrama 2D en PDF", value=True)
                
                if st.button("📄 Generar PDF", type="primary", key="generate_pdf_btn"):
                    try:
                        # Validate required fields
                        company_info = {
                            'company_name': company_name if company_name else "N/A",
                            'phone': phone if phone else "N/A",
                            'email': email if email else "N/A",
                            'client': client_name if client_name else "Cliente No Especificado",
                            'project': project_name if project_name else "Proyecto No Especificado",
                            'validity': quote_validity,
                            'quoted_by': quoted_by if quoted_by else "N/A",
                            'notes': notes
                        }
                        
                        # Generate building sketch if requested
                        sketch_buffer = None
                        if include_sketch and st.session_state.last_steel_calc:
                            calc = st.session_state.last_steel_calc
                            largo = calc.get('largo', 80)
                            ancho = calc.get('ancho', 25)
                            alto_lateral = calc.get('alto_lateral', 9)
                            alto_techado = alto_lateral + 3
                            sketch_buffer = create_building_sketch_for_pdf(largo, ancho, alto_lateral, alto_techado)
                        
                        # Generate PDF
                        pdf_buffer = QuotationGenerator.generate_pdf(
                            quote_data={},
                            company_info=company_info,
                            products=st.session_state.quote_products,
                            totals=totals,
                            show_products=show_products_in_pdf,
                            building_sketch_buffer=sketch_buffer
                        )
                        
                        # Create download button
                        st.download_button(
                            label="📥 Descargar Cotización PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"cotizacion_{client_name.replace(' ', '_') if client_name else 'cotizacion'}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            key="download_pdf_btn"
                        )
                        
                        st.success("✅ Cotización generada exitosamente")
                        
                    except Exception as e:
                        st.error(f"Error al generar la cotización: {str(e)}")
        
        else:
            st.info("No hay productos en la cotización. Agregue productos manualmente o importe desde los cálculos.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(to right, #0f0f19, #1a1a2e);
        border-radius: 16px;
        border: 1px solid rgba(0, 255, 255, 0.3);
        color: rgba(255, 255, 255, 0.85);
        font-size: 15px;
        margin-top: 3rem;
        box-shadow: 0 0 10px rgba(0,255,255,0.1);
    ">
        🏗️ <strong>Calculadora de Nave Industrial Signature 2030</strong><br>
        Sistema Avanzado de Cálculo Estructural + Cotización<br>
        © 2030 | Versión 2.0
    </div>
    """, unsafe_allow_html=True)

# --- ROUTER ---
if st.session_state.authenticated:
    show_main_app()
else:

    show_login_page()


