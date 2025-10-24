import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import database
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

# Page configuration - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Calculadora de Nave Industrial 2030",
    page_icon="➕",
    layout="wide",
    initial_sidebar_state="expanded",  # Changed to expanded for client management
)

# Initialize the database AFTER page config
database.setup_database()

# Initialize session state variables for client management
if 'current_client_id' not in st.session_state:
    st.session_state.current_client_id = None
if 'current_calculation' not in st.session_state:
    st.session_state.current_calculation = None

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
    text-align: center;
    font-size: 48px;
    font-weight: 800;
    margin-bottom: 1rem;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-transform: uppercase;
    letter-spacing: 3px;
}

.stTextInput > div > div > input {
    background: rgba(0, 0, 0, 0.5) !important;
    color: white !important;
    border: 2px solid rgba(0, 255, 255, 0.3) !important;
    border-radius: 15px !important;
    padding: 12px 20px !important;
    font-size: 16px !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--primary-neon) !important;
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.5) !important;
}

.stButton > button {
    background-color: #f0f2f6 !important;
    color: black !important;
    border: 1px solid #ced4da !important;
    font-weight: normal !important;
    padding: 8px 24px !important;
    border-radius: 4px !important;
    font-size: 14px !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    box-shadow: none !important;
    transition: none !important;
}

.stButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 5px 35px rgba(0, 255, 255, 0.6) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--card-bg);
    border: 1px solid rgba(0, 255, 255, 0.3);
    border-radius: 25px;
    padding: 8px;
    gap: 10px;
    justify-content: center;
    backdrop-filter: blur(15px);
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: rgba(255, 255, 255, 0.7);
    border: 1px solid transparent;
    padding: 10px 20px;
    border-radius: 18px;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.3s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(0, 255, 255, 0.1);
    border-color: rgba(0, 255, 255, 0.3);
    color: var(--primary-neon);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(0, 153, 255, 0.2)) !important;
    border: 1px solid var(--primary-neon) !important;
    color: var(--primary-neon) !important;
    box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
}

.result-card {
    background: var(--card-bg);
    border: 2px solid rgba(0, 255, 255, 0.3);
    border-radius: 20px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: var(--shadow-glow);
    backdrop-filter: blur(20px);
    text-align: center;
}

.metric-card {
    background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 153, 255, 0.1));
    border: 1px solid rgba(0, 255, 255, 0.3);
    border-radius: 15px;
    padding: 1.5rem;
    margin: 0.5rem 0;
    text-align: center;
}

.stSelectbox > div > div {
    background: rgba(0, 0, 0, 0.5) !important;
    border: 2px solid rgba(0, 255, 255, 0.3) !important;
    border-radius: 15px !important;
}

.stNumberInput > div > div > input {
    background: rgba(0, 0, 0, 0.5) !important;
    color: white !important;
    border: 2px solid rgba(0, 255, 255, 0.3) !important;
    border-radius: 15px !important;
}

.stDataFrame {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(0, 255, 255, 0.3);
    border-radius: 15px;
    padding: 10px;
}

[data-testid="stMetricValue"] {
    color: var(--primary-neon);
    font-size: 32px;
    font-weight: 700;
}

[data-testid="stMetricLabel"] {
    color: rgba(255, 255, 255, 0.8);
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)

# --- STEEL PROFILE DATA ---
STEEL_PROFILES_EXTENDED = {
    'W27': [178, 161, 146, 114, 102, 94, 84],
    'W24': [162, 146, 131, 117, 104, 94, 84, 76, 68, 62, 55],
    'W21': [147, 132, 122, 111, 101, 93, 83, 73, 68, 62, 57, 50, 44],
    'W18': [119, 106, 97, 86, 76, 71, 65, 60, 55, 50, 46, 40, 35],
    'W16': [100, 89, 77, 67, 57, 50, 45, 40, 36, 31, 26],
    'W14': [132, 120, 109, 99, 90, 82, 74, 68, 61, 53, 48, 43, 38, 34, 30, 26, 22],
    'W12': [136, 120, 106, 96, 87, 79, 72, 65, 58, 53, 50, 45, 40, 35, 30, 26, 22, 19, 16, 14],
    'W10': [112, 100, 88, 77, 68, 60, 54, 49, 45, 39, 33, 30, 26, 22, 19, 17, 15, 12],
    'W8': [67, 58, 48, 40, 35, 31, 28, 24, 21, 18, 15, 13, 10],
    'W6': [25, 20, 16, 15, 12, 9],
    'W5': [19, 16],
    'W4': [13]
}

# --- AUTHENTICATION FUNCTIONS ---
def show_login_page():
    # Check for logo in common paths
    logo = next((p for p in ["logo.png", "assets/logo.png", "logo.jpg", "assets/logo.jpg"] 
                 if os.path.exists(p)), None)
    
    # Create centered layout
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Display logo or icon
        if logo:
            st.image(logo, use_container_width=True)
        else:
            st.markdown('<div style="text-align:center; font-size:72px; margin:2rem 0;">🏗️</div>', 
                       unsafe_allow_html=True)
        
        # Login container with title
        st.markdown("""
        <div class="login-container" style="
            background: rgba(15, 15, 25, 0.95);
            border: 2px solid rgba(0, 255, 255, 0.3);
            border-radius: 30px;
            padding: 2rem;
            backdrop-filter: blur(25px);
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
            margin-top: 1rem;
        ">
            <h1 style="
                text-align: center;
                font-size: 48px;
                font-weight: 800;
                background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
            ">RIGC 2030</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.7); font-size: 14px; 
                      letter-spacing: 2px; margin-bottom: 2rem;">
                SISTEMA DE CÁLCULO INDUSTRIAL
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check attempts
        if st.session_state.attempts >= MAX_ATTEMPTS:
            st.error("⚠️ Máximo de intentos alcanzado. Contacte al administrador.")
            return
        
        # Login form
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
            
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                submit = st.form_submit_button("ACCEDER", use_container_width=True, type="primary")
        
        # Handle authentication
        if submit:
            if username in USER_PASSCODES and password == USER_PASSCODES[username]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Acceso exitoso")
                st.rerun()
            else:
                st.session_state.attempts += 1
                remaining = MAX_ATTEMPTS - st.session_state.attempts
                st.error(f"❌ Credenciales incorrectas. {'Intentos: ' + str(remaining) if remaining > 0 else 'Último intento'}")
                if remaining == 0:
                    st.rerun()

# --- CALCULATION FUNCTIONS ---
def calculate_steel_structure(largo, ancho, alto_lateral, alto_techado, separacion_ejes, tipo_columna, tipo_viga, tipo_correa):
    """Calculate steel structure requirements"""
    num_ejes = int(largo / separacion_ejes) + 1
    columnas_laterales = num_ejes * 2
    columnas_frontales = int(ancho / 5) + 1
    columnas_frontales *= 2
    total_columnas = columnas_laterales + columnas_frontales
    vigas_principales = num_ejes
    correas_techo = int(ancho / 2) * num_ejes * 2
    correas_pared = int(alto_lateral / 2) * num_ejes * 4
    total_correas = correas_techo + correas_pared
    tijerillas = num_ejes
    
    # Get weights
    peso_columna = STEEL_PROFILES_EXTENDED[tipo_columna.split('x')[0]][0]
    peso_viga = STEEL_PROFILES_EXTENDED[tipo_viga.split('x')[0]][0]
    peso_correa = STEEL_PROFILES_EXTENDED[tipo_correa.split('x')[0]][0]
    
    peso_columnas = total_columnas * alto_lateral * peso_columna * 3.28 / 1000
    peso_vigas = vigas_principales * ancho * peso_viga * 3.28 / 1000
    peso_correas = total_correas * 6 * peso_correa * 3.28 / 1000
    peso_tijerillas = tijerillas * (ancho/2) * 50 * 3.28 / 1000
    peso_conexiones = (peso_columnas + peso_vigas + peso_correas + peso_tijerillas) * 0.05
    peso_total = peso_columnas + peso_vigas + peso_correas + peso_tijerillas + peso_conexiones
    
    return {
        'num_ejes': num_ejes,
        'columnas_laterales': columnas_laterales,
        'columnas_frontales': columnas_frontales,
        'total_columnas': total_columnas,
        'vigas_principales': vigas_principales,
        'correas_techo': correas_techo,
        'correas_pared': correas_pared,
        'total_correas': total_correas,
        'tijerillas': tijerillas,
        'peso_columnas': peso_columnas,
        'peso_vigas': peso_vigas,
        'peso_correas': peso_correas,
        'peso_tijerillas': peso_tijerillas,
        'peso_conexiones': peso_conexiones,
        'peso_total': peso_total,
        'largo': largo,
        'ancho': ancho,
        'alto_lateral': alto_lateral,
        'alto_techado': alto_techado
    }

def calculate_materials(largo, ancho, alto_lateral, alto_techado):
    """Calculate material requirements"""
    perimetro = 2 * (largo + ancho)
    
    aluzinc_techo = largo * ancho * 1.1 * 3.28
    aluzinc_pared = perimetro * alto_lateral * 3.28
    correa_techo = (ancho + 2) * ancho * 3.28
    correa_pared = perimetro * ((alto_techado / 2) + 1) * 3.28
    tornillos_techo = (aluzinc_techo + aluzinc_pared) * 5
    cubrefaltas = ((ancho * 2) + (alto_lateral * 4)) * 1.1 * 3.28
    canaletas = largo * 2 * 1.1 * 3.28
    bajantes = int(largo / 7) + 1
    caballetes = largo * 1.1 * 3.28
    
    return {
        'aluzinc_techo': aluzinc_techo,
        'aluzinc_pared': aluzinc_pared,
        'correa_techo': correa_techo,
        'correa_pared': correa_pared,
        'tornillos_techo': tornillos_techo,
        'cubrefaltas': cubrefaltas,
        'canaletas': canaletas,
        'bajantes': bajantes,
        'caballetes': caballetes,
        'largo': largo,
        'ancho': ancho,
        'alto_lateral': alto_lateral,
        'alto_techado': alto_techado
    }

# --- QUOTATION GENERATOR CLASS ---
class QuotationGenerator:
    @staticmethod
    def calculate_quote(products):
        """Calculate quote totals with indirect costs"""
        items_total = sum(p.get('subtotal', 0) for p in products)
        supervision = items_total * 0.10
        admin = items_total * 0.04
        insurance = items_total * 0.01
        transport = items_total * 0.03
        contingency = items_total * 0.03
        
        subtotal_general = items_total + supervision + admin + insurance + transport + contingency
        itbis = subtotal_general * 0.18
        grand_total = subtotal_general + itbis
        
        return {
            'items_total': items_total,
            'supervision': supervision,
            'admin': admin,
            'insurance': insurance,
            'transport': transport,
            'contingency': contingency,
            'subtotal_general': subtotal_general,
            'itbis': itbis,
            'grand_total': grand_total
        }
    
    @staticmethod
    def generate_pdf(quote_data, company_info, products, totals, show_products=True, building_sketch_buffer=None):
        """Generate PDF quotation"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=50, bottomMargin=50)
        story = []
        styles = getSampleStyleSheet()
        # --- NEW: Add Logo and Company Details at the Top ---
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
            fontSize=16,
            textColor=colors.HexColor('#004898'),
            alignment=TA_RIGHT,
            spaceAfter=12
        )
        story.append(Paragraph("ESTIMADO", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#003366'),
            alignment=1,
            spaceAfter=30
        )
        
        # Header
        story.append(Paragraph(f"<b>{company_info['company_name']}</b>", title_style))
        story.append(Spacer(1, 12))
        
        # Quote info
        info_data = [
            ['INFORMACIÓN DEL PROYECTO', ''],
            ['Cliente:', company_info['client']],
            ['Proyecto:', company_info['project']],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y')],
            ['Validez:', f"{company_info['validity']} días"],
            ['Cotizado por:', company_info['quoted_by']]
        ]
        
        info_table = Table(info_data, colWidths=[200, 350])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#003366')),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Add building sketch if provided
        if building_sketch_buffer:
            img = Image(building_sketch_buffer, width=400, height=160)
            story.append(img)
            story.append(Spacer(1, 20))
        
        # Products table
        if show_products and products:
            products_data = [['DESCRIPCIÓN', 'CANTIDAD', 'PRECIO UNIT.', 'SUBTOTAL']]
            for p in products:
                products_data.append([
                    p.get('product_name', ''),
                    f"{p.get('quantity', 0):,.2f}",
                    f"${p.get('unit_price', 0):,.2f}",
                    f"${p.get('subtotal', 0):,.2f}"
                ])
            
            products_table = Table(products_data, colWidths=[250, 80, 100, 100])
            products_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ]))
            story.append(products_table)
            story.append(Spacer(1, 20))
        
        # Totals
        totals_data = [
            ['RESUMEN DE COSTOS', ''],
            ['Total Items:', f"${totals['items_total']:,.2f}"],
            ['Supervisión Técnica (10%):', f"${totals['supervision']:,.2f}"],
            ['Gastos Administrativos (4%):', f"${totals['admin']:,.2f}"],
            ['Seguro de Riesgo (1%):', f"${totals['insurance']:,.2f}"],
            ['Transporte (3%):', f"${totals['transport']:,.2f}"],
            ['Imprevisto (3%):', f"${totals['contingency']:,.2f}"],
            ['', ''],
            ['SUBTOTAL GENERAL:', f"${totals['subtotal_general']:,.2f}"],
            ['ITBIS (18%):', f"${totals['itbis']:,.2f}"],
            ['', ''],
            ['TOTAL GENERAL:', f"${totals['grand_total']:,.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[350, 150])
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e6f2ff')),
        ]))
        
        story.append(totals_table)
        
        # Notes
        if company_info.get('notes'):
            story.append(Spacer(1, 20))
            story.append(Paragraph("<b>Notas:</b>", styles['Heading4']))

            notes_style = ParagraphStyle(
                'NotesStyle',
                parent=styles['Normal'],
                wordWrap='LTR',
                fontSize=10,
                leading=14,
                spaceAfter=6,
         )

        for note in company_info['notes'].split('\n'):
            if note.strip():
                story.append(Paragraph(note.strip(), notes_style))

        # Disclaimer
        nota_texto = (
            "<b>Aviso legal:</b> "
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
    
# --- MAIN APPLICATION ---
def show_main_app():
    # Add CLIENT MANAGEMENT to sidebar
    st.sidebar.header("👥 Gestión de Clientes")
    st.sidebar.markdown("---")
    
    # Client selection/creation
    client_mode = st.sidebar.radio("Modo:", ["Seleccionar Cliente", "Nuevo Cliente"], key="client_mode_radio")
    
    if client_mode == "Seleccionar Cliente":
        # Get all clients
        clients = database.get_all_clients()
        
        if clients:
            client_names = ["Seleccione..."] + [f"{c['company_name']}" for c in clients]
            selected_index = st.sidebar.selectbox("Cliente:", range(len(client_names)), format_func=lambda x: client_names[x], key="client_selector")
            
            if selected_index > 0:
                selected_client = clients[selected_index - 1]
                st.session_state.current_client_id = selected_client['id']
                st.sidebar.success(f"✅ {selected_client['company_name']}")
                
                # Show client details in expander
                with st.sidebar.expander("📋 Detalles del Cliente"):
                    st.write(f"**Empresa:** {selected_client['company_name']}")
                    st.write(f"**Contacto:** {selected_client.get('contact_name', 'N/A')}")
                    st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
                    st.write(f"**Teléfono:** {selected_client.get('phone', 'N/A')}")
                
                # Show saved calculations
                st.sidebar.markdown("**📊 Cálculos Guardados:**")
                calculations = database.get_client_calculations(selected_client['id'])
                
                if calculations:
                    for calc in calculations:
                        col1, col2 = st.sidebar.columns([3, 1])
                        with col1:
                            st.write(f"📁 {calc['project_name']}")
                        with col2:
                            if st.button("📂", key=f"load_{calc['id']}"):
                                calc_details = database.get_calculation_details(calc['id'])
                                st.session_state.current_calculation = calc_details
                                st.rerun()
                else:
                    st.sidebar.info("Sin cálculos guardados")
        else:
            st.sidebar.info("No hay clientes guardados")
    
    else:  # New Client mode
        with st.sidebar.form("new_client_form", clear_on_submit=True):
            company = st.text_input("Empresa *")
            contact = st.text_input("Contacto")
            email = st.text_input("Email")
            phone = st.text_input("Teléfono")
            address = st.text_area("Dirección")
            tax_id = st.text_input("RNC/Cédula")
            notes = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar Cliente"):
                if company:
                    client_id = database.add_new_client(
                        company_name=company,
                        contact_name=contact,
                        email=email,
                        phone=phone,
                        address=address,
                        tax_id=tax_id,
                        notes=notes
                    )
                    st.sidebar.success("✅ Cliente guardado!")
                    st.session_state.current_client_id = client_id
                    st.rerun()
                else:
                    st.sidebar.error("Nombre de empresa requerido")
    
    st.sidebar.markdown("---")
    
    # Logout button
    if st.sidebar.button("🚪 Cerrar Sesión", key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()
    
    # MAIN CONTENT
    st.markdown(f"""
    <div style='text-align: center; padding: 1rem 0 2rem 0;'>
        <h1 style='
            font-size: 72px;
            font-weight: 900;
            background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
            letter-spacing: 4px;
            margin-bottom: 0;
            line-height: 1.2;
        '>RIGC 2030</h1>
        <p style='
            font-size: 24px;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 300;
            letter-spacing: 8px;
            text-transform: uppercase;
            margin-top: -10px;
        '>Sistema de Cálculo Industrial</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show current client status
    if st.session_state.current_client_id:
        client = database.get_client_by_id(st.session_state.current_client_id)
        st.info(f"**Cliente Activo:** {client['company_name']} - {client.get('contact_name', 'Sin contacto')}")
    else:
        st.warning("⚠️ No hay cliente seleccionado. Seleccione o cree un cliente en la barra lateral.")
    
    # Check if loading a saved calculation
    if st.session_state.current_calculation:
        calc = st.session_state.current_calculation
        st.success(f"📂 Cálculo cargado: {calc['project_name']}")
        if st.button("🔄 Nuevo Cálculo"):
            st.session_state.current_calculation = None
            st.rerun()
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📐 CÁLCULO DE ACERO", "🧱 MATERIALES DE CIERRE", "🧮 COTIZACIÓN", "💾 GUARDAR"])
    
    # TAB 1: STEEL CALCULATION
    with tab1:
        st.markdown("### ⚙️ Configuración de la Estructura")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Load values from saved calculation if available
        if st.session_state.current_calculation:
            calc_data = st.session_state.current_calculation
            default_largo = calc_data.get('warehouse_length', 80)
            default_ancho = calc_data.get('warehouse_width', 25)
            default_alto_lateral = calc_data.get('lateral_height', 9)
            default_alto_techado = calc_data.get('roof_height', 12)
        else:
            default_largo = 80
            default_ancho = 25
            default_alto_lateral = 9
            default_alto_techado = 12
        
        with col1:
            largo = st.number_input("Largo (m)", min_value=10, max_value=200, value=default_largo, step=5)
        with col2:
            ancho = st.number_input("Ancho (m)", min_value=10, max_value=100, value=default_ancho, step=5)
        with col3:
            alto_lateral = st.number_input("Alto Lateral (m)", min_value=4, max_value=20, value=default_alto_lateral, step=1)
        with col4:
            alto_techado = st.number_input("Alto Techado (m)", min_value=5, max_value=25, value=default_alto_techado, step=1)
        
        st.markdown("### 🔧 Selección de Perfiles")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            separacion_ejes = st.selectbox("Separación Ejes (m)", [5, 6, 7, 8, 10])
        with col2:
            tipo_columna = st.selectbox("Columna", ["W12x136", "W14x132", "W16x100", "W18x119"])
        with col3:
            tipo_viga = st.selectbox("Viga Principal", ["W24x162", "W27x178", "W21x147", "W18x119"])
        with col4:
            tipo_correa = st.selectbox("Correas", ["W8x24", "W10x30", "W12x26", "W8x31"])
        
        if st.button("🔬 CALCULAR ESTRUCTURA", type="primary", key="calc_steel"):
            calc_results = calculate_steel_structure(largo, ancho, alto_lateral, alto_techado, 
                                                    separacion_ejes, tipo_columna, tipo_viga, tipo_correa)
            
            st.session_state.last_steel_calc = calc_results
            
            # Display results
            st.markdown("### 📊 RESULTADOS DEL CÁLCULO ESTRUCTURAL")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Número de Ejes", calc_results['num_ejes'])
                st.metric("Columnas Laterales", calc_results['columnas_laterales'])
                st.metric("Columnas Frontales", calc_results['columnas_frontales'])
            
            with col2:
                st.metric("Total Columnas", calc_results['total_columnas'])
                st.metric("Vigas Principales", calc_results['vigas_principales'])
                st.metric("Tijerillas", calc_results['tijerillas'])
            
            with col3:
                st.metric("Correas Techo", calc_results['correas_techo'])
                st.metric("Correas Pared", calc_results['correas_pared'])
                st.metric("Total Correas", calc_results['total_correas'])
            
            st.markdown("### ⚖️ PESO DE COMPONENTES (TONELADAS)")
            
            weights_df = pd.DataFrame({
                'Componente': ['Columnas', 'Vigas', 'Correas', 'Tijerillas', 'Conexiones', 'TOTAL'],
                'Peso (Ton)': [
                    calc_results['peso_columnas'],
                    calc_results['peso_vigas'],
                    calc_results['peso_correas'],
                    calc_results['peso_tijerillas'],
                    calc_results['peso_conexiones'],
                    calc_results['peso_total']
                ]
            })
            
            st.dataframe(weights_df, use_container_width=True)
            
            st.markdown(f"""
            <div class="result-card">
                <h2 style="color: var(--primary-neon); margin-bottom: 1rem;">PESO TOTAL ESTIMADO</h2>
                <h1 style="font-size: 48px; color: var(--accent-neon);">{calc_results['peso_total']:.2f} TONELADAS</h1>
            </div>
            """, unsafe_allow_html=True)
    
    # TAB 2: MATERIALS CALCULATION
    with tab2:
        st.markdown("### 📏 Dimensiones de la Nave")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Load values from saved calculation if available
        if st.session_state.current_calculation:
            calc_data = st.session_state.current_calculation
            default_largo_mat = calc_data.get('warehouse_length', 30)
            default_ancho_mat = calc_data.get('warehouse_width', 20)
            default_alto_lateral_mat = calc_data.get('lateral_height', 6)
            default_alto_techado_mat = calc_data.get('roof_height', 8)
        else:
            default_largo_mat = 30
            default_ancho_mat = 20
            default_alto_lateral_mat = 6
            default_alto_techado_mat = 8
        
        with col1:
            largo_mat = st.number_input("Largo (m)", min_value=5, max_value=200, value=default_largo_mat, 
                                       step=1, key="largo_mat")
        with col2:
            ancho_mat = st.number_input("Ancho (m)", min_value=5, max_value=100, value=default_ancho_mat, 
                                       step=1, key="ancho_mat")
        with col3:
            alto_lateral_mat = st.number_input("Alto Lateral (m)", min_value=3, max_value=20, 
                                              value=default_alto_lateral_mat, step=1, key="alto_lateral_mat")
        with col4:
            alto_techado_mat = st.number_input("Alto Techado (m)", min_value=4, max_value=25, 
                                              value=default_alto_techado_mat, step=1, key="alto_techado_mat")
        
        if st.button("🔧 CALCULAR MATERIALES", type="primary", key="calc_materials"):
            materials = calculate_materials(largo_mat, ancho_mat, alto_lateral_mat, alto_techado_mat)
            
            st.session_state.last_materials_calc = materials
            
            st.markdown("### 📋 MATERIALES REQUERIDOS")
            
            materials_df = pd.DataFrame([
                {"Material": "Aluzinc Techo", "Cantidad": f"{materials['aluzinc_techo']:,.2f}", 
                 "Unidad": "pies²", "Fórmula": "Largo × Ancho × 1.1 × 3.28"},
                {"Material": "Aluzinc Pared", "Cantidad": f"{materials['aluzinc_pared']:,.2f}", 
                 "Unidad": "pies²", "Fórmula": "Perímetro × Alto × 3.28"},
                {"Material": "Correa de Techo", "Cantidad": f"{materials['correa_techo']:,.2f}", 
                 "Unidad": "pies", "Fórmula": "(Ancho + 2) × Ancho × 3.28"},
                {"Material": "Correa de Pared", "Cantidad": f"{materials['correa_pared']:,.2f}", 
                 "Unidad": "pies", "Fórmula": "Perímetro × (Altura/2 + 1) × 3.28"},
                {"Material": "Tornillos", "Cantidad": f"{materials['tornillos_techo']:,.0f}", 
                 "Unidad": "unidades", "Fórmula": "Total Aluzinc × 5"},
                {"Material": "Cubrefaltas", "Cantidad": f"{materials['cubrefaltas']:,.2f}", 
                 "Unidad": "pies", "Fórmula": "(Ancho×2 + Alto×4) × 1.1 × 3.28"},
                {"Material": "Canaletas", "Cantidad": f"{materials['canaletas']:,.2f}", 
                 "Unidad": "pies", "Fórmula": "Largo × 2 × 1.1 × 3.28"},
                {"Material": "Bajantes", "Cantidad": f"{materials['bajantes']:,.0f}", 
                 "Unidad": "unidades", "Fórmula": "Largo ÷ 7 + 1"},
                {"Material": "Caballetes", "Cantidad": f"{materials['caballetes']:,.2f}", 
                 "Unidad": "pies", "Fórmula": "Largo × 1.1 × 3.28"}
            ])
            
            st.dataframe(materials_df, use_container_width=True)
            
            # Area calculation
            area_total = largo_mat * ancho_mat
            
            st.markdown(f"""
            <div class="result-card">
                <h3 style="color: var(--primary-neon);">ÁREA TOTAL DE LA NAVE</h3>
                <h2 style="font-size: 36px; color: var(--accent-neon);">{area_total:,.0f} m²</h2>
            </div>
            """, unsafe_allow_html=True)
    
    # TAB 3: QUOTATION
    with tab3:
        st.markdown("### 📝 INFORMACIÓN DE LA EMPRESA")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            company_name = st.text_input("Nombre de Empresa", value="RIGC INDUSTRIAL", key="company_name")
            phone = st.text_input("Teléfono", value="809-555-0100", key="company_phone")
        with col2:
            email = st.text_input("Email", value="info@rigc.com", key="company_email")
            quoted_by = st.text_input("Cotizado por", value=st.session_state.username, key="quoted_by")
        with col3:
            quote_validity = st.number_input("Validez (días)", value=30, min_value=1, key="quote_validity")
        
        st.markdown("### 👤 INFORMACIÓN DEL CLIENTE")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.current_client_id:
                client = database.get_client_by_id(st.session_state.current_client_id)
                client_name = st.text_input("Cliente", value=client['company_name'], key="client_name")
            else:
                client_name = st.text_input("Cliente", placeholder="Nombre del cliente", key="client_name")
        with col2:
            project_name = st.text_input("Proyecto", placeholder="Nombre del proyecto", key="project_name")
        
        notes = st.text_area("Notas adicionales", placeholder="Condiciones especiales, observaciones...", key="notes")
        
        # Product management
        st.markdown("### 📦 GESTIÓN DE PRODUCTOS")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Importar desde Cálculo de Acero", key="import_steel"):
                if st.session_state.last_steel_calc:
                    calc = st.session_state.last_steel_calc
                    steel_products = [
                        {"product_name": "Estructura de Acero - Columnas", 
                         "quantity": calc['peso_columnas'], "unit_price": 1200.0,
                         "subtotal": calc['peso_columnas'] * 1200.0},
                        {"product_name": "Estructura de Acero - Vigas", 
                         "quantity": calc['peso_vigas'], "unit_price": 1200.0,
                         "subtotal": calc['peso_vigas'] * 1200.0},
                        {"product_name": "Estructura de Acero - Correas", 
                         "quantity": calc['peso_correas'], "unit_price": 1200.0,
                         "subtotal": calc['peso_correas'] * 1200.0},
                        {"product_name": "Estructura de Acero - Tijerillas", 
                         "quantity": calc['peso_tijerillas'], "unit_price": 1200.0,
                         "subtotal": calc['peso_tijerillas'] * 1200.0},
                        {"product_name": "Conexiones y Accesorios", 
                         "quantity": calc['peso_conexiones'], "unit_price": 1500.0,
                         "subtotal": calc['peso_conexiones'] * 1500.0}
                    ]
                    st.session_state.quote_products.extend(steel_products)
                    st.success("✅ Productos de acero importados")
                    st.rerun()
                else:
                    st.warning("⚠️ No hay cálculo de acero disponible")
        
        with col2:
            if st.button("📥 Importar desde Materiales", key="import_materials"):
                if st.session_state.last_materials_calc:
                    materials = st.session_state.last_materials_calc
                    material_products = [
                        {"product_name": "Aluzinc Techo", 
                         "quantity": materials['aluzinc_techo'], "unit_price": 3.5,
                         "subtotal": materials['aluzinc_techo'] * 3.5},
                        {"product_name": "Aluzinc Pared", 
                         "quantity": materials['aluzinc_pared'], "unit_price": 3.5,
                         "subtotal": materials['aluzinc_pared'] * 3.5},
                        {"product_name": "Tornillos de Techo", 
                         "quantity": materials['tornillos_techo'], "unit_price": 0.15,
                         "subtotal": materials['tornillos_techo'] * 0.15},
                        {"product_name": "Canaletas", 
                         "quantity": materials['canaletas'], "unit_price": 12.0,
                         "subtotal": materials['canaletas'] * 12.0},
                        {"product_name": "Bajantes", 
                         "quantity": materials['bajantes'], "unit_price": 85.0,
                         "subtotal": materials['bajantes'] * 85.0}
                    ]
                    st.session_state.quote_products.extend(material_products)
                    st.success("✅ Materiales importados")
                    st.rerun()
                else:
                    st.warning("⚠️ No hay cálculo de materiales disponible")
        
        # Manual product entry
        st.markdown("#### ➕ Agregar Producto Manual")
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                new_product_name = st.text_input("Producto")
            with col2:
                new_quantity = st.number_input("Cantidad", min_value=0.0, step=1.0)
            with col3:
                new_unit_price = st.number_input("Precio Unit.", min_value=0.0, step=0.01)
            with col4:
                st.write("")
                st.write("")
                add_product = st.form_submit_button("➕")
            
            if add_product:
                if new_product_name and new_quantity > 0 and new_unit_price > 0:
                    new_product = {
                        'product_name': new_product_name,
                        'quantity': new_quantity,
                        'unit_price': new_unit_price,
                        'subtotal': new_quantity * new_unit_price
                    }
                    st.session_state.quote_products.append(new_product)
                    st.success(f"Producto '{new_product_name}' agregado")
                else:
                    st.error("Complete todos los campos")
        
        # Display current products
        if st.session_state.quote_products:
            st.markdown("### Productos en la Cotización")
            
            products_df = pd.DataFrame(st.session_state.quote_products)
            
            # Ensure columns exist
            for col in ['product_name', 'quantity', 'unit_price', 'subtotal']:
                if col not in products_df.columns:
                    products_df[col] = 0.0 if col != 'product_name' else ''
            
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
                num_rows="dynamic"
            )
            
            # Update session state with edited data
            if not edited_df.empty:
                valid_products = edited_df[
                    (edited_df['product_name'].notna()) & 
                    (edited_df['product_name'] != '') &
                    (edited_df['quantity'] > 0)
                ].copy()
                
                valid_products['quantity'] = valid_products['quantity'].astype(float)
                valid_products['unit_price'] = valid_products['unit_price'].astype(float)
                valid_products['subtotal'] = valid_products['quantity'] * valid_products['unit_price']
                
                st.session_state.quote_products = valid_products.to_dict('records')
            
            # Clear products button
            if st.button("🔄 Limpiar Productos"):
                st.session_state.quote_products = []
                st.rerun()
            
            # Calculate totals
            if st.session_state.quote_products:
                totals = QuotationGenerator.calculate_quote(st.session_state.quote_products)
                
                # Display totals
                st.markdown("### Resumen de Costos")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Items", f"${totals['items_total']:,.2f}")
                    st.metric("Supervisión (10%)", f"${totals['supervision']:,.2f}")
                    st.metric("Admin. (4%)", f"${totals['admin']:,.2f}")
                
                with col2:
                    st.metric("Seguro (1%)", f"${totals['insurance']:,.2f}")
                    st.metric("Transporte (3%)", f"${totals['transport']:,.2f}")
                    st.metric("Imprevisto (3%)", f"${totals['contingency']:,.2f}")
                
                with col3:
                    st.metric("Subtotal", f"${totals['subtotal_general']:,.2f}")
                    st.metric("ITBIS (18%)", f"${totals['itbis']:,.2f}")
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-size: 24px; color: rgba(0, 255, 0, 0.9);">TOTAL GENERAL</div>
                        <div style="font-size: 48px; font-weight: 900; color: var(--accent-neon);">
                            ${totals['grand_total']:,.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Generate PDF button
                st.markdown("### Generar Cotización")
                
                col1, col2 = st.columns(2)
                with col1:
                    show_products_in_pdf = st.checkbox("Mostrar productos en PDF", value=True)
                with col2:
                    include_sketch = st.checkbox("Incluir diagrama 2D", value=True)
                
                if st.button("📄 Generar PDF", type="primary"):
                    try:
                        company_info = {
                            'company_name': company_name,
                            'phone': phone,
                            'email': email,
                            'client': client_name if client_name else "Cliente No Especificado",
                            'project': project_name if project_name else "Proyecto No Especificado",
                            'validity': quote_validity,
                            'quoted_by': quoted_by,
                            'notes': notes
                        }
                        
                        sketch_buffer = None
                        if include_sketch and st.session_state.last_steel_calc:
                            calc = st.session_state.last_steel_calc
                            sketch_buffer = create_building_sketch_for_pdf(
                                calc.get('largo', 80),
                                calc.get('ancho', 25),
                                calc.get('alto_lateral', 9),
                                calc.get('alto_techado', 12)
                            )
                        
                        pdf_buffer = QuotationGenerator.generate_pdf(
                            quote_data={},
                            company_info=company_info,
                            products=st.session_state.quote_products,
                            totals=totals,
                            show_products=show_products_in_pdf,
                            building_sketch_buffer=sketch_buffer
                        )
                        
                        st.download_button(
                            label="📥 Descargar PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
                        
                        st.success("✅ Cotización generada")
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        else:
            st.info("No hay productos en la cotización")
    
    # TAB 4: SAVE CALCULATION
    with tab4:
        st.markdown("### 💾 GUARDAR CÁLCULO")
        
        if st.session_state.current_client_id:
            client = database.get_client_by_id(st.session_state.current_client_id)
            st.info(f"**Cliente:** {client['company_name']}")
            
            # Check what calculations are available
            has_steel = bool(st.session_state.last_steel_calc)
            has_materials = bool(st.session_state.last_materials_calc)
            
            if has_steel or has_materials:
                with st.form("save_calculation_form"):
                    project_save_name = st.text_input("Nombre del Proyecto", 
                                                     value=project_name if 'project_name' in locals() else "")
                    
                    calc_type = st.selectbox("Tipo de Cálculo a Guardar",
                                            ["Ambos (Acero + Materiales)", "Solo Acero", "Solo Materiales"])
                    
                    total_amount = st.number_input("Monto Total (opcional)", value=0.0, min_value=0.0)
                    
                    save_notes = st.text_area("Notas del Cálculo")
                    
                    if st.form_submit_button("💾 Guardar en Base de Datos", type="primary"):
                        # Prepare data based on calculation type
                        if calc_type == "Ambos (Acero + Materiales)":
                            if has_steel and has_materials:
                                steel = st.session_state.last_steel_calc
                                materials = st.session_state.last_materials_calc
                                
                                combined_data = {
                                    "tipo": "completo",
                                    "acero": steel,
                                    "materiales": materials
                                }
                                
                                # Use dimensions from steel calc preferentially
                                save_largo = steel.get('largo', materials.get('largo', 30))
                                save_ancho = steel.get('ancho', materials.get('ancho', 20))
                                save_alto_lateral = steel.get('alto_lateral', materials.get('alto_lateral', 6))
                                save_alto_techado = steel.get('alto_techado', materials.get('alto_techado', 8))
                            else:
                                st.error("Faltan cálculos. Realice ambos cálculos primero.")
                                st.stop()
                        
                        elif calc_type == "Solo Acero":
                            if has_steel:
                                steel = st.session_state.last_steel_calc
                                combined_data = {"tipo": "acero", "acero": steel}
                                save_largo = steel['largo']
                                save_ancho = steel['ancho']
                                save_alto_lateral = steel['alto_lateral']
                                save_alto_techado = steel['alto_techado']
                            else:
                                st.error("No hay cálculo de acero disponible")
                                st.stop()
                        
                        else:  # Solo Materiales
                            if has_materials:
                                materials = st.session_state.last_materials_calc
                                combined_data = {"tipo": "materiales", "materiales": materials}
                                save_largo = materials['largo']
                                save_ancho = materials['ancho']
                                save_alto_lateral = materials['alto_lateral']
                                save_alto_techado = materials['alto_techado']
                            else:
                                st.error("No hay cálculo de materiales disponible")
                                st.stop()
                        
                        # Save to database
                        calc_id = database.save_calculation(
                            client_id=st.session_state.current_client_id,
                            project_name=project_save_name or f"Nave {save_largo}x{save_ancho}",
                            length=save_largo,
                            width=save_ancho,
                            lateral_height=save_alto_lateral,
                            roof_height=save_alto_techado,
                            materials_dict=combined_data,
                            total_amount=total_amount
                        )
                        
                        st.success(f"✅ Cálculo guardado exitosamente: {project_save_name}")
                        st.balloons()
                
                # Show saved calculations for this client
                st.markdown("### 📋 Cálculos Guardados del Cliente")
                calculations = database.get_client_calculations(st.session_state.current_client_id)
                
                if calculations:
                    calc_df = pd.DataFrame(calculations)
                    calc_df = calc_df[['project_name', 'length', 'width', 'total_amount', 'created_date']]
                    calc_df.columns = ['Proyecto', 'Largo', 'Ancho', 'Monto Total', 'Fecha']
                    
                    st.dataframe(calc_df, use_container_width=True)
                else:
                    st.info("No hay cálculos guardados para este cliente")
            
            else:
                st.warning("⚠️ No hay cálculos disponibles para guardar. Realice un cálculo primero.")
        
        else:
            st.error("❌ Debe seleccionar un cliente antes de guardar un cálculo")
            st.info("👈 Seleccione o cree un cliente en la barra lateral")
    
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
    ">
        ➕ <strong>RIGC Industrial Calculator 2030</strong><br>
        Sistema Avanzado con Gestión de Clientes<br>
        © 2030 | Versión 3.0
    </div>
    """, unsafe_allow_html=True)

# --- ROUTER ---
if st.session_state.authenticated:
    show_main_app()
else:
    show_login_page()


