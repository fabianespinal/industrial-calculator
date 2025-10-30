import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import re
import math
from math import sqrt

# Page configuration - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="RIGC - ERP",
    page_icon="➕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- LOAD EXTERNAL CSS ---
def load_css():
    if os.path.exists("style.css"):
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ style.css not found. Using default styling.")

load_css()

# Initialize the database AFTER page config
import database
database.setup_database()

# --- LOAD PROFILE WEIGHTS FROM EXCEL ---
@st.cache_data(ttl=60)
def load_steel_profiles():
    import os
    file_path = "steel_profiles.xlsx"
    if not os.path.exists(file_path):
        st.error(f"❌ File not found: {os.path.abspath(file_path)}")
        return {}
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower()  # normalize column names
        if "profile" in df.columns and "weight_lbs_per_ft" in df.columns:
            return dict(zip(df["profile"], df["weight_lbs_per_ft"]))
        else:
            st.error(f"❌ Columnas no válidas. Encontradas: {list(df.columns)}")
            return {}
    except Exception as e:
        st.error(f"❌ Error loading {file_path}: {e}")
        return {}

profile_weights = load_steel_profiles()
if not profile_weights:
    st.stop()

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

# LABOR RATES (not used directly, but kept for future)
LABOR_RATES = {
    "steel_installation_rate": 350.0,
    "roofing_rate": 8.5,
    "wall_cladding_rate": 12.0,
    "accessories_rate": 450.0,
    "supervision_days_factor": 0.05,
    "daily_supervisor_rate": 150.0,
}

def create_building_sketch(dimensions):
    length = dimensions.get('length', 20.0)
    width = dimensions.get('width', 15.0)
    wall_height = dimensions.get('wall_height', 4.0)
    roof_rise = dimensions.get('roof_height', 2.0)  # This is the *rise*, not total height
    total_height = wall_height + roof_rise
    area = length * width
    fig, (ax_top, ax_front, ax_side) = plt.subplots(1, 3, figsize=(12, 4))
    fig.patch.set_facecolor('white')

    # TOP VIEW
    ax_top.set_xlim(0, length)
    ax_top.set_ylim(0, width)
    top_rect = patches.Rectangle((0, 0), length, width,
                                linewidth=2, edgecolor='black',
                                facecolor='lightgray', alpha=0.4)
    ax_top.add_patch(top_rect)
    ax_top.annotate('', xy=(0, -0.8), xytext=(length, -0.8),
                    arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_top.text(length/2, -1.2, f'{length} m', ha='center', va='top', fontsize=9)
    ax_top.annotate('', xy=(-0.8, 0), xytext=(-0.8, width),
                    arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_top.text(-1.2, width/2, f'{width} m', ha='right', va='center', rotation=90, fontsize=9)
    ax_top.set_title('PLANTA', fontsize=10, fontweight='bold')
    ax_top.set_aspect('equal')
    ax_top.axis('off')

    # FRONT VIEW
    ax_front.set_xlim(-1, width + 1)
    ax_front.set_ylim(0, total_height + 1)
    front_wall = patches.Rectangle((0, 0), width, wall_height,
                                   linewidth=2, edgecolor='black',
                                   facecolor='lightgray', alpha=0.4)
    ax_front.add_patch(front_wall)
    roof_points = [(0, wall_height), (width/2, total_height), (width, wall_height)]
    front_roof = patches.Polygon(roof_points, linewidth=2, edgecolor='black',
                                 facecolor='darkgray', alpha=0.5)
    ax_front.add_patch(front_roof)
    ax_front.annotate('', xy=(0, -0.5), xytext=(width, -0.5),
                      arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_front.text(width/2, -0.8, f'{width} m', ha='center', va='top', fontsize=9)
    ax_front.annotate('', xy=(-0.5, 0), xytext=(-0.5, wall_height),
                      arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_front.text(-0.8, wall_height/2, f'{wall_height} m', ha='right', va='center', rotation=90, fontsize=9)
    ax_front.annotate('', xy=(width + 0.5, 0), xytext=(width + 0.5, total_height),
                      arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_front.text(width + 0.8, total_height/2, f'{total_height} m', ha='left', va='center', rotation=90, fontsize=9)
    ax_front.set_title('VISTA FRONTAL', fontsize=10, fontweight='bold')
    ax_front.set_aspect('equal')
    ax_front.axis('off')

    # SIDE VIEW
    ax_side.set_xlim(-1, length + 1)
    ax_side.set_ylim(0, total_height + 1)
    side_wall = patches.Rectangle((0, 0), length, wall_height,
                                  linewidth=2, edgecolor='black',
                                  facecolor='lightgray', alpha=0.4)
    ax_side.add_patch(side_wall)
    roof_side = patches.Rectangle((0, wall_height), length, roof_rise,
                                  linewidth=2, edgecolor='black',
                                  facecolor='darkgray', alpha=0.5)
    ax_side.add_patch(roof_side)
    ax_side.annotate('', xy=(0, -0.5), xytext=(length, -0.5),
                     arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_side.text(length/2, -0.8, f'{length} m', ha='center', va='top', fontsize=9)
    ax_side.annotate('', xy=(-0.5, 0), xytext=(-0.5, wall_height),
                     arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax_side.text(-0.8, wall_height/2, f'{wall_height} m', ha='right', va='center', rotation=90, fontsize=9)
    ax_side.set_title('VISTA LATERAL', fontsize=10, fontweight='bold')
    ax_side.set_aspect('equal')
    ax_side.axis('off')

    fig.text(0.5, 0.02, f'ÁREA TOTAL: {area:,.2f} m²', 
             ha='center', fontsize=10, fontweight='bold')
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf

    # Create 3D Sketch

def create_3d_building_sketch(dimensions):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    length = dimensions.get('length', 20.0)
    width = dimensions.get('width', 15.0)
    wall_height = dimensions.get('wall_height', 4.0)
    roof_rise = max(0.1, dimensions.get('roof_height', 2.0))  # vertical rise only
    total_height = wall_height + roof_rise

    # Create figure sized for PDF (6.5" x 9" safe area)
    fig = plt.figure(figsize=(6.5, 9))
    ax = fig.add_subplot(111, projection='3d')

    # Set equal aspect
    max_dim = max(length, width, total_height)
    ax.set_xlim(0, length)
    ax.set_ylim(0, width)
    ax.set_zlim(0, total_height)

    # === Define vertices ===
    # Floor corners
    floor = [
        [0, 0, 0],
        [length, 0, 0],
        [length, width, 0],
        [0, width, 0]
    ]

    # Wall top corners
    wall_top = [
        [0, 0, wall_height],
        [length, 0, wall_height],
        [length, width, wall_height],
        [0, width, wall_height]
    ]

    # Roof peak (center line along length)
    roof_peak_front = [length / 2, 0, total_height]
    roof_peak_back = [length / 2, width, total_height]

    # === Faces ===
    faces = []

    # Floor
    faces.append(floor)

    # Walls
    faces.append([floor[0], floor[1], wall_top[1], wall_top[0]])  # front
    faces.append([floor[1], floor[2], wall_top[2], wall_top[1]])  # right
    faces.append([floor[2], floor[3], wall_top[3], wall_top[2]])  # back
    faces.append([floor[3], floor[0], wall_top[0], wall_top[3]])  # left

    # Roof (two slopes)
    # Front slope
    faces.append([wall_top[0], wall_top[1], roof_peak_front])
    # Back slope
    faces.append([wall_top[2], wall_top[3], roof_peak_back])
    # Left gable
    faces.append([wall_top[0], wall_top[3], roof_peak_back, roof_peak_front])
    # Right gable
    faces.append([wall_top[1], wall_top[2], roof_peak_back, roof_peak_front])

    # Create collection
    poly3d = Poly3DCollection(faces, facecolors='lightgray', edgecolors='black', linewidths=0.8, alpha=0.9)
    ax.add_collection3d(poly3d)

    # Remove axes and ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_axis_off()

    # Adjust view angle for warehouse look
    ax.view_init(elev=20, azim=-60)

    plt.tight_layout(pad=0)

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf

def parse_fraction(s):
    if '/' in s:
        num, den = map(int, s.split('/'))
        return num / den
    return float(s)

def sort_key(profile):
    match = re.match(r'([A-Z]+)', profile)
    if not match:
        return (99, 0, 0, 0)
    prefix = match.group(1)
    types_order = {'W': 0, 'S': 1, 'C': 2, 'MC': 3, 'L': 4, 'HSS': 5}
    type_idx = types_order.get(prefix, 99)
    if prefix in ['W', 'S', 'C', 'MC']:
        parts = profile[len(prefix):].split('x')
        depth = float(parts[0]) if parts[0] else 0
        weight = parse_fraction(parts[1]) if len(parts) > 1 else 0
        return (type_idx, depth, weight)
    elif prefix == 'L':
        parts = profile[len(prefix):].split('x')
        if len(parts) == 3:
            s1 = float(parts[0])
            s2 = float(parts[1])
            thick = parse_fraction(parts[2])
            return (type_idx, max(s1, s2), min(s1, s2), thick)
        return (type_idx, 0, 0, 0)
    elif prefix == 'HSS':
        parts = profile[len(prefix):].split('x')
        if len(parts) == 3:
            h = float(parts[0])
            w = float(parts[1])
            thick = parse_fraction(parts[2])
            return (type_idx, max(h, w), min(h, w), thick)
        return (type_idx, 0, 0, 0)
    return (type_idx, 0, 0, 0)

def better_sort(profiles):
    return sorted(profiles, key=sort_key)

all_profiles = better_sort(list(profile_weights.keys()))

# --- AUTHENTICATION FUNCTIONS ---
def show_login_page():
    st.set_page_config(layout="centered")
    login_css = """
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            height: 100vh;
            overflow: hidden;
            background: radial-gradient(circle at top, #0f0f19 0%, #050510 100%);
        }
        .login-frame {
            max-width: 500px;
            margin: auto;
            padding: 2rem;
            background: rgba(20, 20, 30, 0.95);
            border-radius: 20px;
            box-shadow: 0 0 40px rgba(0, 255, 255, 0.2);
            border: 1px solid rgba(0, 255, 255, 0.2);
            backdrop-filter: blur(20px);
        }
        .login-title {
            font-size: 40px;
            font-weight: 800;
            text-align: center;
            background: linear-gradient(135deg, #00ffff, #0099ff, #ff00ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            text-align: center;
            color: rgba(255,255,255,0.6);
            font-size: 14px;
            letter-spacing: 1.5px;
            margin-bottom: 2rem;
        }
        .logo {
            display: block;
            margin: 2rem auto 1rem auto;
            max-width: 300px;
        }
    </style>
    """
    st.markdown(login_css, unsafe_allow_html=True)
    logo = next((p for p in ["logo.png", "assets/logo.png", "logo.jpg", "assets/logo.jpg"] 
                 if os.path.exists(p)), None)
    if logo:
        st.image(logo, use_container_width=True)
    else:
        st.markdown('<div style="text-align:center; font-size:72px; margin:2rem 0;">🏗️</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">RIGC 2030</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">SISTEMA DE CÁLCULO INDUSTRIAL</div>', unsafe_allow_html=True)
    if st.session_state.attempts >= MAX_ATTEMPTS:
        st.error("⚠️ Máximo de intentos alcanzado. Contacte al administrador.")
        return
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
        password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
        submit = st.form_submit_button("ACCEDER", use_container_width=True, type="primary")
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
def calculate_materials(largo, ancho, alto_lateral, alto_techado):
    perimetro = 2 * (largo + ancho)
    aluzinc_techo = largo * ancho * 1.1 * 3.28
    aluzinc_pared = perimetro * alto_lateral * 3.28
    correa_techo = (ancho + 2) * largo * 3.28
    correa_pared = perimetro * ((alto_techado - alto_lateral) / 2 + 1) * 3.28
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
        items_total = sum(
            float(p.get('quantity', 0)) * float(p.get('unit_price', 0))
            for p in products
        )
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
            'grand_total': grand_total,
        }

    @staticmethod
    def generate_pdf(quote_data, company_info, products, totals, show_products=True, create_building_sketch=None, create_building_sketch_3d=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=40, bottomMargin=40, leftMargin=36, rightMargin=36)
        story = []
        styles = getSampleStyleSheet()
        base_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'
        logo_added = False
        for logo_path in ["assets/logo.png", "logo.png", "assets/logo.jpg", "logo.jpg"]:
            if os.path.exists(logo_path):
                try:
                    logo = Image(logo_path, width=1 * inch, height=0.4 * inch)
                    logo.hAlign = 'LEFT'
                    story.append(logo)
                    story.append(Spacer(1, 6))
                    logo_added = True
                    break
                except:
                    pass
        if not logo_added:
            fallback_style = ParagraphStyle(
                'FallbackHeader',
                fontName=bold_font,
                fontSize=12,
                textColor=colors.HexColor('#004898'),
                spaceAfter=6,
                alignment=0
            )
            story.append(Paragraph("EMPRESA CONSTRUCTORA", fallback_style))
            story.append(Spacer(1, 4))
        company_info_style = ParagraphStyle(
            'CompanyInfo',
            fontName=base_font,
            fontSize=7,
            leading=9,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8
        )
        company_info_text = (
            "PARQUE INDUSTRIAL DISDO - CALLE CENTRAL No. 1<br/>"
            "HATO NUEVO PALAVE - SECTOR MANOGUAYABO<br/>"
            "SANTO DOMINGO OESTE • TEL: 829-439-8476<br/>"
            "RNC: 131-71683-2"
        )
        story.append(Paragraph(company_info_text, company_info_style))
        story.append(Spacer(1, 4))
        divider = Table([['']], colWidths=[6.5 * inch])
        divider.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.8, colors.HexColor('#004898')),
        ]))
        story.append(divider)
        story.append(Spacer(1, 12))
        title_style = ParagraphStyle(
            'QuoteTitle',
            fontName=bold_font,
            fontSize=14,
            textColor=colors.HexColor('#004898'),
            alignment=TA_RIGHT,
            spaceAfter=12
        )
        story.append(Paragraph("ESTIMADO PRELIMINAR", title_style))
        info_data = [
            ['INFORMACIÓN DEL PROYECTO', ''],
            ['Cliente:', company_info['client']],
            ['Proyecto:', company_info['project']],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y')],
            ['Validez:', f"{company_info['validity']} días"],
            ['Cotizado por:', company_info['quoted_by']]
        ]
        info_table = Table(info_data, colWidths=[180, 370])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f7fa')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#004898')),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -1), base_font),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 16))
        if create_building_sketch:
            try:
                sketch_img = Image(create_building_sketch, width=4 * inch, height=3 * inch)
                sketch_img.hAlign = 'CENTER'
                story.append(sketch_img)
                story.append(Spacer(1, 12))
            except Exception as e:
                print(f"Sketch image failed: {e}")
        if show_products and products:
            products_data = [['DESCRIPCIÓN', 'CANTIDAD', 'PRECIO UNIT.', 'SUBTOTAL']]
            for p in products:
                products_data.append([
                    p.get('product_name', ''),
                    f"{p.get('quantity', 0):,.2f}",
                    f"${p.get('unit_price', 0):,.2f}",
                    f"${p.get('subtotal', 0):,.2f}"
                ])
            products_table = Table(products_data, colWidths=[250, 70, 90, 90])
            products_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#004898')),
                ('FONTNAME', (0, 0), (-1, 0), bold_font),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 1), (-1, -1), base_font),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(products_table)
            story.append(Spacer(1, 16))
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
        totals_table = Table(totals_data, colWidths=[330, 170])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#004898')),
            ('FONTNAME', (0, 1), (-1, -2), base_font),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (0, -1), (0, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f9fbfd')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
         ]))
        story.append(totals_table)
        story.append(Spacer(1, 20))
        if company_info.get('notes'):
            story.append(Spacer(1, 14))
            notes_header = Paragraph("<b>Notas:</b>", styles['Normal'])
            notes_header.fontName = bold_font
            notes_header.fontSize = 9
            story.append(notes_header)
            notes_style = ParagraphStyle(
                'Notes',
                fontName=base_font,
                fontSize=8,
                leading=11,
                spaceAfter=4
            )
            for note in company_info['notes'].split('\n'):
                if note.strip():
                    story.append(Paragraph(note.strip(), notes_style))

            # Add full-page 3D sketch if requested
            if create_building_sketch_3d:
                from reportlab.platypus import PageBreak
                story.append(PageBreak())
                try:
                    img_3d = Image(create_building_sketch_3d, width=6.5*inch, height=9*inch)
                    img_3d.hAlign = 'CENTER'
                    story.append(img_3d)
                except Exception as e:
                    print(f"3D sketch error: {e}")

        disclaimer_text = (
            "<b>Aviso legal:</b> <b>Esta cotización es solo un estimado preliminar.</b> "
            "Todos los precios están sujetos a cambios. El precio final será confirmado al momento de emitir la orden de compra. "
            "Será necesaria una cotización formal para validar los términos y condiciones definitivos."
        )
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            fontName=base_font,
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor('#444444')
        )
        disclaimer_para = Paragraph(disclaimer_text, disclaimer_style)
        disclaimer_table = Table([[disclaimer_para]], colWidths=[6.5 * inch])
        disclaimer_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fcfcfc')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 10))
        story.append(disclaimer_table)
        doc.build(story)
        buffer.seek(0)
        return buffer

# --- MAIN APPLICATION ---
def show_main_app():
    # SIDEBAR
    st.sidebar.header("👥 Gestión de Clientes")
    st.sidebar.markdown("---")
    client_mode = st.sidebar.radio("Modo:", ["Seleccionar Cliente", "Nuevo Cliente"], key="client_mode_radio")
    if client_mode == "Seleccionar Cliente":
        clients = database.get_all_clients()
        if clients:
            client_names = ["Seleccione..."] + [f"{c['company_name']}" for c in clients]
            selected_index = st.sidebar.selectbox("Cliente:", range(len(client_names)), format_func=lambda x: client_names[x], key="client_selector")
            if selected_index > 0:
                selected_client = clients[selected_index - 1]
                st.session_state.current_client_id = selected_client['id']
                st.sidebar.success(f"✅ {selected_client['company_name']}")
                with st.sidebar.expander("📋 Detalles del Cliente"):
                    st.write(f"**Empresa:** {selected_client['company_name']}")
                    st.write(f"**Contacto:** {selected_client.get('contact_name', 'N/A')}")
                    st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
                    st.write(f"**Teléfono:** {selected_client.get('phone', 'N/A')}")
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
    else:
        with st.sidebar.form("new_client_form", clear_on_submit=True):
            company = st.text_input("Empresa *")
            contact = st.text_input("Contacto")
            email = st.text_input("Email")
            phone = st.text_input("Teléfono")
            address = st.text_area("Dirección")
            tax_id = st.text_input("RNC/Cédula")
            notes = st.text_area("Notas")
            if st.form_submit_button("🟥 Guardar Cliente"):
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
    if st.sidebar.button("🟥 Cerrar Sesión", key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    # MAIN HEADER
    st.markdown("""
    <div class="header-container">
        <h1 class="main-title">RIGC 2030</h1>
        <p class="subtitle">Sistema de Cálculo Industrial</p>
    </div>
    """, unsafe_allow_html=True)

    # CLIENT CONTEXT
    if st.session_state.current_client_id:
        client = database.get_client_by_id(st.session_state.current_client_id)
        st.info(f"**Cliente Activo:** {client['company_name']} - {client.get('contact_name', 'Sin contacto')}")
    else:
        st.warning("⚠️ No hay cliente seleccionado. Seleccione o cree un cliente en la barra lateral.")
    if st.session_state.current_calculation:
        calc = st.session_state.current_calculation
        st.success(f"📂 Cálculo cargado: {calc['project_name']}")
        if st.button("🔄 Nuevo Cálculo"):
            st.session_state.current_calculation = None
            st.rerun()
    st.divider()

    # SECTION 1: FULL CALCULATION
    st.markdown("""
        <div class="header-container">
            <h1 class="main-title">CÁLCULO COMPLETO</h1>
            <p class="subtitle">ESTRUCTURA ➕ MATERIALES</p>
        </div>
    """, unsafe_allow_html=True)

    # Load defaults
    if st.session_state.get('current_calculation'):
        calc_data = st.session_state.current_calculation
        default_largo = calc_data.get('warehouse_length', 80)
        default_ancho = calc_data.get('warehouse_width', 25)
        default_alto_lateral = calc_data.get('lateral_height', 7)
        default_alto_techado = calc_data.get('roof_height', 9)
        default_distancia = calc_data.get('axis_distance', 7.27)
    else:
        default_largo = 80
        default_ancho = 25
        default_alto_lateral = 7
        default_alto_techado = 9
        default_distancia = 7.27

    st.markdown("### ⚙️ Configuración de la Estructura")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        largo = st.number_input("Largo (m)", min_value=10.0, max_value=200.0, value=float(default_largo), step=0.1, key="steel_largo")
    with col2:
        ancho = st.number_input("Ancho (m)", min_value=10.0, max_value=100.0, value=float(default_ancho), step=0.1, key="steel_ancho")
    with col3:
        alto_lateral = st.number_input("Altura Lateral (m)", min_value=4.0, max_value=20.0, value=float(default_alto_lateral), step=0.1, key="steel_alto_lateral")
    with col4:
        alto_techado = st.number_input("Altura Techado (m)", min_value=5.0, max_value=25.0, value=float(default_alto_techado), step=0.1, key="steel_alto_techado")
    with col5:
        distancia = st.number_input("Distancia entre ejes (m)", min_value=0.1, max_value=20.0, value=float(default_distancia), step=0.01, key="axis_distance")

    if alto_techado < alto_lateral:
        st.warning("⚠️ La altura del techado debe ser mayor o igual a la altura lateral.")
        st.stop()

    # Profile selection
    st.markdown("### 🔧 Selección de Perfiles")
    default_columna = "W12x136"
    default_portico = "W16x100"
    default_tijerilla = "W14x159"
    default_lateral = "W12x87"
    default_bracing = "L6x4x1/2"
    default_sagrod = "L3x3x1/4"
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Perfiles Principales**")
        col1a, col1b = st.columns(2)
        with col1a:
            columnas = st.selectbox("Perfil Columnas centrales", options=all_profiles, index=all_profiles.index(default_columna) if default_columna in all_profiles else 0, key="col_profile")
            tijerillas = st.selectbox("Perfil Tijerillas", options=all_profiles, index=all_profiles.index(default_tijerilla) if default_tijerilla in all_profiles else 0, key="beam_profile")
        with col1b:
            porticos = st.selectbox("Perfil Pórticos de frenado", options=all_profiles, index=all_profiles.index(default_portico) if default_portico in all_profiles else 0, key="frame_profile")
        st.markdown("**Perfiles de Refuerzo**")
        bracing = st.selectbox("Perfil Bracing (arriostramiento)", options=all_profiles, index=all_profiles.index(default_bracing) if default_bracing in all_profiles else 0, key="bracing_profile")
        sagrods = st.selectbox("Perfil Sag Rods (tensores)", options=all_profiles, index=all_profiles.index(default_sagrod) if default_sagrod in all_profiles else 0, key="sagrod_profile")
    with col2:
        st.markdown("**Configuración Lateral**")
        col2a, col2b = st.columns(2)
        with col2a:
            columnas_laterales = st.selectbox("Perfil Columnas laterales", options=all_profiles, index=all_profiles.index(default_lateral) if default_lateral in all_profiles else 0, key="lat_profile")
            num_lados = st.selectbox("Lados laterales", options=[1, 2], index=1, key="lat_lados")
        with col2b:
            incluir_laterales = st.checkbox("Incluir Columnas laterales", value=True, key="include_lateral")

    with st.expander("📊 Ver Pesos de Perfiles Seleccionados"):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Columnas centrales", f"{profile_weights.get(columnas, 0)} lbs/ft")
        with col2:
            st.metric("Tijerillas", f"{profile_weights.get(tijerillas, 0)} lbs/ft")
        with col3:
            st.metric("Pórticos de frenado", f"{profile_weights.get(porticos, 0)} lbs/ft")
        with col4:
            st.metric("Columnas laterales", f"{profile_weights.get(columnas_laterales, 0)} lbs/ft")
        with col5:
            st.metric("Bracing", f"{profile_weights.get(bracing, 0)} lbs/ft")
        with col6:
            st.metric("Sag Rods", f"{profile_weights.get(sagrods, 0)} lbs/ft")

    if st.button("🟥 CALCULAR ESTRUCTURA + MATERIALES", type="primary", key="calc_full_btn", use_container_width=True):
        try:
            num_ejes = int((largo / distancia) + 1)
            num_bays_largo = num_ejes - 1
            if incluir_laterales:
                num_columnas_laterales = (num_bays_largo + 1) * num_lados
            else:
                num_columnas_laterales = 0

            steel_data = [
                {"perfil": columnas, "funcion": "Columnas centrales", "peso_m": profile_weights.get(columnas, 0) * 1.488, "cantidad": num_ejes * 2, "longitud": alto_lateral, "eje": "E1-E6", "proveedor": "AceroDominicana", "acero": "A992"},
                {"perfil": porticos, "funcion": "Pórticos de frenado", "peso_m": profile_weights.get(porticos, 0) * 1.488, "cantidad": 2, "longitud": ancho, "eje": "F1-F3", "proveedor": "AceroDominicana", "acero": "A572"},
                {"perfil": tijerillas, "funcion": "Tijerillas", "peso_m": profile_weights.get(tijerillas, 0) * 1.488, "cantidad": num_ejes * 2, "longitud": ancho * 1.1, "eje": "Cubierta", "proveedor": "Metalmecánica SRL", "acero": "A992"},
                {"perfil": columnas_laterales, "funcion": "Columnas laterales", "peso_m": profile_weights.get(columnas_laterales, 0) * 1.488, "cantidad": num_columnas_laterales, "longitud": alto_lateral, "eje": "L1-L5", "proveedor": "Metalmecánica SRL", "acero": "A36"},
                {"perfil": bracing, "funcion": "Bracing (arriostramiento)", "peso_m": profile_weights.get(bracing, 0) * 1.488, "cantidad": 2 * num_bays_largo * num_lados, "longitud": math.sqrt(distancia**2 + alto_lateral**2), "eje": "Entre columnas", "proveedor": "AceroDominicana", "acero": "A36"},
                {"perfil": sagrods, "funcion": "Sag Rods (tensores)", "peso_m": profile_weights.get(sagrods, 0) * 1.488, "cantidad": int((largo / 1.5) * (num_ejes * 2)), "longitud": 3.5, "eje": "Cubierta", "proveedor": "Metalmecánica SRL", "acero": "A36"},
            ]
            df_steel = pd.DataFrame(steel_data)
            df_steel["peso_total"] = df_steel["peso_m"] * df_steel["cantidad"] * df_steel["longitud"]
            df_steel["tipo"] = "Acero Estructural"

            mats = calculate_materials(largo, ancho, alto_lateral, alto_techado)
            materials_data = [
                {"perfil": "Aluzinc Techo", "funcion": "Cubierta", "peso_m": 0, "cantidad": mats['aluzinc_techo'], "longitud": 0, "eje": "Cubierta", "proveedor": "Laminas RD", "acero": "Aluzinc", "tipo": "Material de Cierre"},
                {"perfil": "Aluzinc Pared", "funcion": "Muros", "peso_m": 0, "cantidad": mats['aluzinc_pared'], "longitud": 0, "eje": "Perímetro", "proveedor": "Laminas RD", "acero": "Aluzinc", "tipo": "Material de Cierre"},
                {"perfil": "Correa de Techo", "funcion": "Soporte Techo", "peso_m": 0, "cantidad": mats['correa_techo'], "longitud": 0, "eje": "Cubierta", "proveedor": "Metalmecánica SRL", "acero": "Acero", "tipo": "Material de Cierre"},
                {"perfil": "Correa de Pared", "funcion": "Soporte Muro", "peso_m": 0, "cantidad": mats['correa_pared'], "longitud": 0, "eje": "Perímetro", "proveedor": "Metalmecánica SRL", "acero": "Acero", "tipo": "Material de Cierre"},
                {"perfil": "Tornillos", "funcion": "Fijación", "peso_m": 0, "cantidad": mats['tornillos_techo'], "longitud": 0, "eje": "General", "proveedor": "Ferretería", "acero": "Acero", "tipo": "Material de Cierre"},
                {"perfil": "Cubrefaltas", "funcion": "Cierre Perimetral", "peso_m": 0, "cantidad": mats['cubrefaltas'], "longitud": 0, "eje": "Cubierta", "proveedor": "Laminas RD", "acero": "Aluzinc", "tipo": "Material de Cierre"},
                {"perfil": "Canaletas", "funcion": "Drenaje", "peso_m": 0, "cantidad": mats['canaletas'], "longitud": 0, "eje": "Perímetro", "proveedor": "Laminas RD", "acero": "Aluzinc", "tipo": "Material de Cierre"},
                {"perfil": "Bajantes", "funcion": "Drenaje Vertical", "peso_m": 0, "cantidad": mats['bajantes'], "longitud": 0, "eje": "Esquinas", "proveedor": "Laminas RD", "acero": "Aluzinc", "tipo": "Material de Cierre"},
                {"perfil": "Caballetes", "funcion": "Caballete", "peso_m": 0, "cantidad": mats['caballetes'], "longitud": 0, "eje": "Cubierta", "proveedor": "Laminas RD", "acero": "Aluzinc", "tipo": "Material de Cierre"},
            ]
            df_materials = pd.DataFrame(materials_data)
            df_materials["peso_total"] = df_materials["cantidad"]

            df_combined = pd.concat([df_steel, df_materials], ignore_index=True)
            st.session_state.full_calculation_result = df_combined

            st.divider()
            st.markdown('<h3 style="color: #1023c9;">📊 Resultados del Cálculo</h3>', unsafe_allow_html=True)
            total_peso_acero = df_combined[df_combined["tipo"] == "Acero Estructural"]["peso_total"].sum()
            total_materiales = len(df_combined[df_combined["tipo"] == "Material de Cierre"])
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Peso Total de Acero", f"{total_peso_acero:,.2f} kg")
            with col_r2:
                st.metric("Ítems de Materiales", f"{total_materiales}")
            with col_r3:
                st.metric("Área Total", f"{largo * ancho:,.0f} m²")

            st.markdown("#### 🔹 Acero Estructural")
            peso_acero = df_combined[df_combined["tipo"] == "Acero Estructural"]
            if not peso_acero.empty:
                res = peso_acero.groupby("funcion")["peso_total"].sum().reset_index()
                res.columns = ["Elemento", "Peso (kg)"]
                res["Peso (kg)"] = res["Peso (kg)"].map("{:,.2f}".format)
                st.dataframe(res, use_container_width=True, hide_index=True)

            st.markdown("#### 📦 Materiales de Cierre")
            materiales_df = df_combined[df_combined["tipo"] == "Material de Cierre"]
            if not materiales_df.empty:
                display = materiales_df[["perfil", "cantidad", "eje", "proveedor"]].rename(columns={
                    "perfil": "Material", "cantidad": "Cantidad", "eje": "Ubicación", "proveedor": "Proveedor"
                })
                def fmt(q, mat):
                    if mat in ["Bajantes"]: return f"{q:,.0f} und"
                    elif "Tornillos" in mat: return f"{q:,.0f} und"
                    else: return f"{q:,.2f} pies"
                display["Cantidad"] = display.apply(lambda row: fmt(row["Cantidad"], row["Material"]), axis=1)
                st.dataframe(display[["Material", "Cantidad", "Ubicación", "Proveedor"]], use_container_width=True, hide_index=True)

            with st.expander("📋 Ver Desglose Detallado"):
                df_display = df_combined[[
                    "tipo", "perfil", "funcion", "cantidad", "longitud", "peso_m", "peso_total", "eje", "proveedor", "acero"
                ]].copy()
                df_display.rename(columns={
                    "tipo": "Tipo", "perfil": "Perfil/Material", "funcion": "Función",
                    "cantidad": "Cant.", "longitud": "Long. (m)", "peso_m": "Peso/m (kg)",
                    "peso_total": "Total (kg)", "eje": "Eje", "proveedor": "Proveedor", "acero": "Material"
                }, inplace=True)
                df_display["Total (kg)"] = df_display["Total (kg)"].map(lambda x: f"{x:,.2f}" if x != 0 else "N/A")
                df_display["Peso/m (kg)"] = df_display["Peso/m (kg)"].map(lambda x: f"{x:,.2f}" if x != 0 else "N/A")
                st.dataframe(df_display, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"❌ Error en el cálculo: {str(e)}")
            st.info("Verifica que todos los perfiles tengan pesos definidos en el diccionario profile_weights")

    st.divider()

    # SECTION 2: QUOTATION
    st.markdown("""
    <style>
        /* ===== Custom Header Styling ===== */
        .header-container {
            text-align: center;
            padding: 3rem 0 3rem 0;
            margin-bottom: 2.5rem;
            position: relative;
        }

        /* Elegant glow behind text */
        .header-container::after {
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 280px;
            height: 280px;
            background: radial-gradient(circle, rgba(0,150,255,0.12) 0%, rgba(0,0,0,0) 70%);
            filter: blur(40px);
            z-index: 0;
        }

        .main-title {
            position: relative;
            z-index: 1;
            font-size: 100px;
            font-weight: 900;
            background: linear-gradient(120deg, #00d4ff 0%, #007bff 45%, #9b00ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
            letter-spacing: 4px;
            margin-bottom: 0.3rem;
            line-height: 1.1;
            animation: fadeIn 1.2s ease;
        }

        .subtitle {
            position: relative;
            z-index: 1;
            font-size: 22px;
            color: #a3a3a3;
            font-weight: 400;
            letter-spacing: 6px;
            text-transform: uppercase;
            margin-top: -4px;
            animation: fadeIn 1.8s ease;
        }

        .main-title, .subtitle {
            text-shadow: 0px 0px 20px rgba(0, 100, 255, 0.15);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 768px) {
            .main-title {
                font-size: 50px;
                letter-spacing: 3px;
            }
            .subtitle {
                font-size: 18px;
                letter-spacing: 4px;
            }
        }
    </style>

    <!-- Gradient header block -->
    <div class="header-container">
        <h1 class="main-title">COTIZACION</h1>
        <p class="subtitle">ESTRUCTURA ➕ MATERIALES</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📝 Información de la Cotización")
    col1, col2, col3 = st.columns(3)
    with col1:
        company_name = st.text_input("Nombre de Empresa", value="RIGC INDUSTRIAL", key="company_name")
        phone = st.text_input("Teléfono", value="809-555-0100", key="company_phone")
    with col2:
        email = st.text_input("Email", value="info@rigc.com", key="company_email")
        quoted_by = st.text_input("Cotizado por", value=st.session_state.username, key="quoted_by")
    with col3:
        quote_validity = st.number_input("Validez (días)", value=30, min_value=1, key="quote_validity")

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

    if st.button("🟥 IMPORTAR CALCULO COMPLETO", type="primary", key="import_full", use_container_width=True):
        if 'full_calculation_result' in st.session_state and not st.session_state.full_calculation_result.empty:
            df = st.session_state.full_calculation_result.copy()
            # Preserve existing manual products (not auto-generated)
            existing_manual = [
                p for p in st.session_state.get('quote_products', [])
                if not p.get('auto_imported', False)
            ]
            new_products = []

            # --- 1. Process structural steel (grouped by function) ---
            steel_df = df[df["tipo"] == "Acero Estructural"].copy()
            steel_df["toneladas"] = steel_df["peso_total"] / 1000
            steel_grouped = steel_df.groupby("funcion")["toneladas"].sum().to_dict()
            ton_estructura_total = sum(steel_grouped.values())
            ton_conexiones = ton_estructura_total * 0.08

            steel_mapping = {
                "Columnas centrales": "Estructura de Acero - Columnas Centrales",
                "Columnas laterales": "Estructura de Acero - Columnas Laterales",
                "Tijerillas": "Estructura de Acero - Tijerillas",
                "Pórticos de frenado": "Estructura de Acero - Pórticos",
                "Bracing (arriostramiento)": "Estructura de Acero - Bracing",
                "Sag Rods (tensores)": "Estructura de Acero - Sag Rods"
            }
            for func, tons in steel_grouped.items():
                product_name = steel_mapping.get(func, f"Estructura de Acero - {func}")
                new_products.append({
                    "product_name": product_name,
                    "quantity": round(tons, 2),
                    "unit_price": 1200.0,
                    "auto_imported": True
                })

            new_products.append({
                "product_name": "Conexiones y Accesorios",
                "quantity": round(ton_conexiones, 2),
                "unit_price": 1500.0,
                "auto_imported": True
            })

            # --- 2. Process ALL closure materials (one line per material) ---
            materials_df = df[df["tipo"] == "Material de Cierre"].copy()
            for _, row in materials_df.iterrows():
                perfil = row["perfil"]
                cantidad = row["cantidad"]
                unit_price_map = {
                    "Aluzinc Techo": 3.5,
                    "Aluzinc Pared": 3.5,
                    "Tornillos": 0.15,
                    "Canaletas": 12.0,
                    "Bajantes": 85.0,
                    "Cubrefaltas": 4.2,
                    "Correa de Techo": 2.8,
                    "Correa de Pared": 2.6,
                    "Caballetes": 5.0,
                }
                unit_price = unit_price_map.get(perfil, 1.0)
                if perfil in ["Bajantes", "Tornillos"]:
                    qty = int(round(cantidad))
                else:
                    qty = round(cantidad, 2)
                new_products.append({
                    "product_name": perfil,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "auto_imported": True
                })

            for p in new_products:
                p["subtotal"] = p["quantity"] * p["unit_price"]

            st.session_state.quote_products = existing_manual + new_products
            st.success("✅ Todos los productos del cálculo importados (estructura + materiales)")
            st.rerun()
        else:
            st.warning("⚠️ Ejecute primero el cálculo en la sección superior.")

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
            add_product = st.form_submit_button("➕")
        if add_product and new_product_name and new_quantity > 0 and new_unit_price > 0:
            st.session_state.quote_products = st.session_state.get('quote_products', [])
            st.session_state.quote_products.append({
                'product_name': new_product_name,
                'quantity': new_quantity,
                'unit_price': new_unit_price,
                'subtotal': new_quantity * new_unit_price
            })
            st.rerun()

    if st.session_state.get('quote_products'):
        df_prod = pd.DataFrame(st.session_state.quote_products)
        df_prod['subtotal'] = df_prod['quantity'] * df_prod['unit_price']
        edited = st.data_editor(
            df_prod,
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
        st.session_state.quote_products = edited.to_dict('records')
        totals = QuotationGenerator.calculate_quote(st.session_state.quote_products)

        st.markdown("### 💰 Resumen de Costos")
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
            <div style="
                background: rgba(18, 18, 36, 0.7);
                padding: 1rem;
                border-radius: 16px;
                text-align: center;
                border: 1px solid rgba(100, 180, 255, 0.2);
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            ">
                <div style="font-size: 20px; font-weight: 600; color: #4deeea; font-family: 'Inter', sans-serif;">
                    TOTAL GENERAL
                </div>
                <div style="font-size: 36px; font-weight: 700; color: white; font-family: 'Inter', sans-serif;">
                    ${totals['grand_total']:,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            show_products_in_pdf = st.checkbox("Mostrar productos en PDF", value=True)
        with col2:
            include_sketch = st.checkbox("Incluir diagrama 2D", value=True)
        with col3:
            include_3d_sketch = st.checkbox("Incluir vista 3D", value=False)

        if st.button("🟥GENERAR PDF", type="primary", use_container_width=True):
            try:
                company_info = {
                    'company_name': company_name,
                    'phone': phone,
                    'email': email,
                    'client': client_name or "Cliente No Especificado",
                    'project': project_name or "Proyecto No Especificado",
                    'validity': quote_validity,
                    'quoted_by': quoted_by,
                    'notes': notes
                }
                sketch = None
                if include_sketch and 'full_calculation_result' in st.session_state:
                    sketch = create_building_sketch({
                        'length': largo,
                        'width': ancho,
                        'wall_height': alto_lateral,
                        'roof_height': max(0.1, alto_techado - alto_lateral)
                    })

                sketch_3d = None
                if include_3d_sketch and 'full_calculation_result' in st.session_state:
                    sketch_3d = create_3d_building_sketch({
                        'length': largo,
                        'width': ancho,
                        'wall_height': alto_lateral,
                        'roof_height': max(0.1, alto_techado - alto_lateral)
                    })

                pdf = QuotationGenerator.generate_pdf(
                    quote_data={},
                    company_info=company_info,
                    products=st.session_state.quote_products,
                    totals=totals,
                    show_products=show_products_in_pdf,
                    create_building_sketch=sketch,
                    create_building_sketch_3d=sketch_3d
)
                st.download_button(
                    "⏬ Descargar Cotización PDF",
                    pdf.getvalue(),
                    f"cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
    else:
        st.info("👆 Importe productos desde el cálculo o agréguelos manualmente para generar una cotización.")

    # SECTION 3: SAVE CALCULATION
    st.markdown("""
        <div class="header-container">
            <h1 class="main-title">GUARDAR CÁLCULO</h1>
            <p class="subtitle">ESTRUCTURA ➕ MATERIALES</p>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.current_client_id:
        with st.form("save_calc_form"):
            project_save_name = st.text_input("Nombre del Proyecto", value=project_name or f"Nave {largo}x{ancho}")
            total_amount = st.number_input("Monto Total (USD)", value=float(totals.get('grand_total', 0)) if 'totals' in locals() else 0.0, min_value=0.0)
            save_notes = st.text_area("Notas", value=notes)
            if st.form_submit_button("🟥 Guardar Cálculo en Base de Datos", type="primary", use_container_width=True):
                try:
                    calc_data = {
                        "largo": largo,
                        "ancho": ancho,
                        "alto_lateral": alto_lateral,
                        "alto_techado": alto_techado,
                        "distancia_ejes": distancia,
                        "acero_result": st.session_state.get('full_calculation_result', {}).to_dict() if 'full_calculation_result' in st.session_state else {}
                    }
                    calc_id = database.save_calculation(
                        client_id=st.session_state.current_client_id,
                        project_name=project_save_name,
                        length=largo,
                        width=ancho,
                        lateral_height=alto_lateral,
                        roof_height=alto_techado,
                        materials_dict=calc_data,
                        total_amount=total_amount
                    )
                    st.success(f"✅ Cálculo guardado: {project_save_name}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")
    else:
        st.error("❌ Seleccione un cliente en la barra lateral para guardar cálculos.")

    # FOOTER
    st.markdown("""
        <div class="footer">
            <div class="footer-title">RIGC Industrial Calculator 2030</div>
            <div>Sistema Avanzado con Gestión de Clientes</div>
            <small>© 2030 | Versión Unificada</small>
        </div>
        """, unsafe_allow_html=True)

# --- ROUTER ---
if st.session_state.authenticated:
    show_main_app()
else:
    show_login_page()