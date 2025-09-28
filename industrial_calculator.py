import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus import Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_RIGHT


# Page configuration
st.set_page_config(
    page_title="Calculadora de Nave Industrial 2030",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

.metric-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: rgba(0, 255, 255, 0.8);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 36px;
    font-weight: 800;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
}

.metric-subtitle {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
    text-transform: uppercase;
    letter-spacing: 1px;
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

.result-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 24px;
    font-weight: 800;
    color: rgba(0, 255, 255, 0.9);
    text-transform: uppercase;
    letter-spacing: 4px;
    margin-bottom: 24px;
}

.result-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 64px;
    font-weight: 900;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 24px 0;
}

.result-subtitle {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 16px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.7);
    letter-spacing: 2px;
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

.main-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 56px;
    font-weight: 900;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 4px;
}

.main-subtitle {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.8);
    letter-spacing: 2px;
    text-transform: uppercase;
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

.stSuccess {
    background: linear-gradient(135deg, rgba(0, 255, 0, 0.2), rgba(0, 255, 255, 0.2)) !important;
    border: 2px solid rgba(0, 255, 0, 0.4) !important;
    border-radius: 15px !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    backdrop-filter: blur(10px) !important;
}

.stInfo {
    background: linear-gradient(135deg, rgba(0, 100, 255, 0.2), rgba(0, 255, 255, 0.2)) !important;
    border: 2px solid rgba(0, 255, 255, 0.4) !important;
    border-radius: 15px !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    backdrop-filter: blur(10px) !important;
}

@media (max-width: 768px) {
    .main-title { font-size: 36px; }
    .result-value { font-size: 42px; }
    .metric-value { font-size: 24px; }
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <div class="main-title">🏗️ Calculadora Componentes Nave Signature</div>
    <div class="main-subtitle">Sistema RIGC. Cálculo Estructural + Cotización 2030</div>
</div>
""", unsafe_allow_html=True)

# Steel profiles data
@st.cache_data
def get_steel_profiles():
    profiles = []
    series_data = {
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
    
    for series, weights in series_data.items():
        for weight in weights:
            profiles.append((series, weight))
    
    return profiles

# Quotation Generator Class
class QuotationGenerator:
    @staticmethod
    def calculate_quote(products):
        items_total = sum([p.get('subtotal', 0) for p in products if p.get('subtotal')])
        
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
    def generate_pdf(quote_data, company_info, products, totals, show_products=True):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        story = []
        styles = getSampleStyleSheet()

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
        story.append(Paragraph("COTIZACIÓN", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Quote number logic
        client_name = company_info.get('client', '').strip()
        initials = ''.join([word[0].upper() for word in client_name.split() if word]) if client_name and client_name != "Cliente No Especificado" else 'SC'
        quote_date = datetime.now().strftime('%Y%m%d')
        quote_number = f"{initials}-{quote_date}/1"

        # Project info
        info_data = [
            ['INFORMACIÓN DEL PROYECTO'],
            ['Cotización Nº:', quote_number],
            ['Cliente:', company_info.get('client', '')],
            ['Proyecto:', company_info.get('project', '')],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y')],
            ['Validez:', company_info.get('validity', '30 días')]
        ]
        info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004898')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 1), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(info_table)
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

        # Notes section
        if company_info.get('notes'):
            notes_text = f"Notas:\n\n{company_info['notes']}"
            notes_style = styles['Normal']
            notes_style.fontName = 'Helvetica'
            notes_style.fontSize = 8
            notes_style.leading = 10
            notes_para = Preformatted(notes_text, notes_style, maxLineLength=90)
            story.append(Spacer(1, 0.2 * inch))
            story.append(notes_para)

        doc.build(story)
        buffer.seek(0)
        return buffer

# Initialize data
profiles = get_steel_profiles()
profile_options = [f"{p[0]} x {p[1]} ({p[1]} lb/ft)" for p in profiles]
profile_weights = {f"{p[0]} x {p[1]} ({p[1]} lb/ft)": p[1] for p in profiles}

# Initialize session state
if 'quote_products' not in st.session_state:
    st.session_state.quote_products = []
if 'last_steel_calc' not in st.session_state:
    st.session_state.last_steel_calc = {}
if 'last_materials_calc' not in st.session_state:
    st.session_state.last_materials_calc = {}

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Cálculo de Acero", 
    "📦 Materiales", 
    "📚 Base de Datos", 
    "📋 Cotización"
])

# TAB 1: STEEL CALCULATION
with tab1:
    st.markdown('<div class="section-header">Cálculo de Acero Estructural</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        largo = st.number_input("Largo (m)", min_value=0.0, value=80.0, step=0.1)
    with col2:
        ancho = st.number_input("Ancho (m)", min_value=0.0, value=25.0, step=0.1)
    with col3:
        alto_lateral = st.number_input("Altura Lateral (m)", min_value=0.0, value=9.0, step=0.1)
    with col4:
        distancia = st.number_input("Distancia entre Ejes (m)", min_value=0.1, value=7.27, step=0.01)
    
    st.markdown('<div class="section-header">Selección de Perfiles</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        columnas = st.selectbox("Perfil Columnas", options=profile_options, key="col_profile")
    with col2:
        tijerillas = st.selectbox("Perfil Tijerillas", options=profile_options, key="beam_profile")
    with col3:
        porticos = st.selectbox("Perfil Pórticos", options=profile_options, key="frame_profile")
    with col4:
        columnas_laterales = st.selectbox("Perfil Columnas Laterales", options=profile_options, key="lat_profile")
    
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        num_lados = st.selectbox("Lados Laterales", options=[1, 2], index=1, key="lat_lados")
    with col2:
        incluir_laterales = st.checkbox("Incluir Columnas Laterales", value=True, key="include_lateral")
    with col3:
        st.info("Columnas Laterales se calculan: (Largo ÷ Distancia + 1) × Lados × Altura × Peso × 3.28")
    
    if st.button("🔧 Calcular Acero Estructural Completo", type="primary"):
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
                'tornillos_3_4': tornillos_3_4
            }
            
            st.success("✅ Cálculo de Acero Estructural Completado Exitosamente")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""d">
                    <div class="metric-title">Pórticos de Frenado</div>
                    <div class="metric-value">{perimetro:.1f}</div>
                    <div class="metric-subtitle">m perímetro</div>
                    <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                    <div class="metric-title">Tonelaje</div>
                    <div class="metric-value" style="font-size: 28px;">{ton_porticos:.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Columnas Frontales</div>
                    <div class="metric-value">{num_columnas_frontales:.0f}</div>
                    <div class="metric-subtitle">unidades</div>
                    <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                    <div class="metric-title">Tonelaje</div>
                    <div class="metric-value" style="font-size: 28px;">{ton_columnas_frontales:.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if incluir_laterales:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Columnas Laterales</div>
                        <div class="metric-value">{num_columnas_laterales:.0f}</div>
                        <div class="metric-subtitle">unidades ({num_lados} lado{'s' if num_lados > 1 else ''})</div>
                        <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                        <div class="metric-title">Tonelaje</div>
                        <div class="metric-value" style="font-size: 28px;">{ton_columnas_laterales:.2f}</div>
                        <div class="metric-subtitle">ton</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-title">Columnas Laterales</div>
                        <div class="metric-value">--</div>
                        <div class="metric-subtitle">no incluidas</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Conexiones (15%)</div>
                    <div class="metric-value">{libras_conexiones:,.0f}</div>
                    <div class="metric-subtitle">libras</div>
                    <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                    <div class="metric-title">Tonelaje</div>
                    <div class="metric-value" style="font-size: 28px;">{ton_conexiones:,.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Pernos</div>
                    <div class="metric-value">{cantidad_pernos:,.0f}</div>
                    <div class="metric-subtitle">unidades</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Tornillos 3/4"</div>
                    <div class="metric-value">{tornillos_3_4:,}</div>
                    <div class="metric-subtitle">unidades</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Total Libras</div>
                    <div class="metric-value" style="font-size: 20px;">{total_libras:,.0f}</div>
                    <div class="metric-subtitle">lb</div>
                </div>
                """, unsafe_allow_html=True)
            
            lateral_text = f" | Laterales: {ton_columnas_laterales:,.2f} ton" if incluir_laterales else ""
            st.markdown(f"""
            <div class="result-card">
                <div class="result-title">TOTAL ACERO ESTRUCTURAL</div>
                <div class="result-value">{total_ton:,.2f} TON</div>
                <div class="result-subtitle">
                    Columnas: {ton_columnas:,.2f} | Tijerillas: {ton_tijerillas:,.2f} | Pórticos: {ton_porticos:,.2f} | 
                    Frontales: {ton_columnas_frontales:,.2f}{lateral_text} | Conexiones: {ton_conexiones:,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
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
        mat_ancho = st.number_input("Ancho (m)", min_value=0.0, value=25.0, step=0.1, key="mat_width")
    with col2:
        mat_largo = st.number_input("Largo (m)", min_value=0.0, value=80.0, step=0.1, key="mat_length")
    with col3:
        mat_alt_lat = st.number_input("Altura Laterales (m)", min_value=0.0, value=9.0, step=0.1, key="mat_alt_lat")
    with col4:
        mat_alt_tech = st.number_input("Altura Techado (m)", min_value=0.0, value=7.0, step=0.1, key="mat_alt_tech")
    with col5:
        mat_dist = st.number_input("Distancia Ejes (m)", min_value=0.1, value=7.27, step=0.01, key="mat_dist")
    
    if st.button("📦 Calcular Materiales", type="primary"):
        try:
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
            
            # Save materials to session state for quotation import
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
                'area_total': area_total
            }
            
            st.success("✅ Cálculo de materiales completado exitosamente")
            
            materials_data = {
                'Material': [
                    'Aluzinc Techo', 'Aluzinc Paredes', 'Correas Techo', 'Correas Paredes',
                    'Tornillos', 'Tornillos 3/4"', 'Tillas', 'Tornillos 1/2"', 'Caños', 'Caballetes',
                    'Cubrefaltas', 'Bajantes', 'Boquillas', 'Pernos'
                ],
                'Cantidad': [
                    f"{aluzinc_techo:,.0f} pies", f"{aluzinc_paredes:,.0f} pies",
                    f"{correas_techo:,.0f} pies", f"{correas_paredes:,.0f} pies",
                    f"{tornillos_Techo:,.0f} unidades", f"{tornillos_3_4:,.0f} unidades",
                    f"{tillas:,.0f} unidades", f"{tornillos_media:,.0f} unidades",
                    f"{canos:,.0f} pies", f"{caballetes:,.0f} pies",
                    f"{cubrefaltas:,.0f} pies", f"{bajantes:,.0f} unidades",
                    f"{boquillas:,.0f} unidades", f"{pernos:,.0f} unidades"
                ],
                'Categoría': [
                    'Techado', 'Paredes', 'Estructura', 'Estructura',
                    'Fijación', 'Fijación', 'Estructura', 'Fijación', 'Estructura', 'Techado',
                    'Acabados', 'Drenaje', 'Drenaje', 'Fijación'
                ]
            }
            
            df_materials = pd.DataFrame(materials_data)
            st.dataframe(df_materials, hide_index=True, use_container_width=True, height=500)
            
            st.markdown(f"""
            <div class="result-card">
                <div class="result-title">ÁREA TOTAL DE LA NAVE</div>
                <div class="result-value">{area_total:,.2f} m²</div>
                <div class="result-subtitle">{area_total * 10.764:,.2f} pies²</div>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error en el cálculo de materiales: {str(e)}")

# TAB 3: DATABASE
with tab3:
    st.markdown('<div class="section-header">Base de Datos de Perfiles W</div>', unsafe_allow_html=True)
    
    search = st.text_input("🔍 Buscar perfil:", placeholder="Ej: W24, 120, W14 x 68...")
    
    df_profiles = pd.DataFrame(profiles, columns=['Serie', 'Peso (lb/ft)'])
    df_profiles['Perfil Completo'] = df_profiles.apply(lambda x: f"{x['Serie']} x {x['Peso (lb/ft)']}", axis=1)
    df_profiles = df_profiles[['Serie', 'Perfil Completo', 'Peso (lb/ft)']]
    
    if search:
        filtered_df = df_profiles[
            df_profiles['Perfil Completo'].str.contains(search, case=False) |
            df_profiles['Serie'].str.contains(search, case=False) |
            df_profiles['Peso (lb/ft)'].astype(str).str.contains(search, case=False)
        ]
    else:
        filtered_df = df_profiles
    
    st.dataframe(filtered_df, hide_index=True, use_container_width=True, height=600)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📊 **Total de perfiles:** {len(df_profiles)}")
    with col2:
        st.info(f"🔍 **Resultados filtrados:** {len(filtered_df)}")
    with col3:
        unique_series = df_profiles['Serie'].nunique()
        st.info(f"📋 **Series disponibles:** {unique_series}")

# TAB 4: QUOTATION - FIXED VERSION
with tab4:
    st.markdown('<div class="section-header">Generador de Cotizaciones</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Cliente", key="client_name", value="")
        project_name = st.text_input("Proyecto", key="project_name", value="")
    with col2:
        quote_date = st.date_input("Fecha", datetime.now())
        quote_validity = st.selectbox("Validez", ["15 días", "30 días", "45 días", "60 días"])
    
    notes = st.text_area("Notas/Observaciones", height=100, value="")
    
    st.markdown('<div class="section-header">Productos</div>', unsafe_allow_html=True)

    # Initialize session_state for products if not exists
    if "quote_products" not in st.session_state:
        st.session_state.quote_products = []

    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Los productos calculados se pueden importar automáticamente desde las pestañas de cálculo.")
    with col2:
        if st.button("🔄 Importar de Cálculos", type="secondary"):
            imported_products = []

            # Import from steel calculations
            if st.session_state.get('last_steel_calc'):
                calc = st.session_state.last_steel_calc
                imported_products.append({
                    "product_name": "Acero Estructural Total", 
                    "quantity": float(calc.get('total_ton', 0)), 
                    "unit_price": 0.0, 
                    "subtotal": 0.0
                })
                imported_products.append({
                    "product_name": f"Columnas Estructurales ({calc.get('num_columnas', 0):.0f} unidades)", 
                    "quantity": float(calc.get('ton_columnas', 0)), 
                    "unit_price": 0.0, 
                    "subtotal": 0.0
                })
                imported_products.append({
                    "product_name": f"Tijerillas ({calc.get('num_tijerillas', 0):.0f} elementos)", 
                    "quantity": float(calc.get('ton_tijerillas', 0)), 
                    "unit_price": 0.0, 
                    "subtotal": 0.0
                })

            # Import from materials calculations
            if st.session_state.get('last_materials_calc'):
                mat_calc = st.session_state.last_materials_calc
                imported_products.extend([
                    {"product_name": "Aluzinc para Techo", "quantity": float(mat_calc.get('aluzinc_techo', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Aluzinc para Paredes", "quantity": float(mat_calc.get('aluzinc_paredes', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Correas Techo", "quantity": float(mat_calc.get('correas_techo', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Correas Paredes", "quantity": float(mat_calc.get('correas_paredes', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Tornillos para Techo", "quantity": float(mat_calc.get('tornillos_techo', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Tornillos 3/4\"", "quantity": float(mat_calc.get('tornillos_3_4', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Tillas", "quantity": float(mat_calc.get('tillas', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Tornillos 1/2\"", "quantity": float(mat_calc.get('tornillos_media', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Caños", "quantity": float(mat_calc.get('canos', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Caballetes", "quantity": float(mat_calc.get('caballetes', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Cubrefaltas", "quantity": float(mat_calc.get('cubrefaltas', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Bajantes", "quantity": float(mat_calc.get('bajantes', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Boquillas", "quantity": float(mat_calc.get('boquillas', 0)), "unit_price": 0.0, "subtotal": 0.0},
                    {"product_name": "Pernos", "quantity": float(mat_calc.get('pernos', 0)), "unit_price": 0.0, "subtotal": 0.0},
                ])

            # Save imported products to session state
            st.session_state.quote_products = imported_products
            st.rerun()

    # Add button to manually add a product
    if st.button("➕ Agregar Producto Manual"):
        st.session_state.quote_products.append({
            "product_name": "",
            "quantity": 0.0,
            "unit_price": 0.0,
            "subtotal": 0.0
        })
        st.rerun()

    # Create DataFrame from session state
    if st.session_state.quote_products:
        products_df = pd.DataFrame(st.session_state.quote_products)
        
        # Ensure columns exist
        if 'product_name' not in products_df.columns:
            products_df['product_name'] = ''
        if 'quantity' not in products_df.columns:
            products_df['quantity'] = 0.0
        if 'unit_price' not in products_df.columns:
            products_df['unit_price'] = 0.0
        if 'subtotal' not in products_df.columns:
            products_df['subtotal'] = 0.0
        
        # Convert types
        products_df['product_name'] = products_df['product_name'].astype(str)
        products_df['quantity'] = pd.to_numeric(products_df['quantity'], errors='coerce').fillna(0)
        products_df['unit_price'] = pd.to_numeric(products_df['unit_price'], errors='coerce').fillna(0)
        products_df['subtotal'] = products_df['quantity'] * products_df['unit_price']

        # Show editable table
        edited_df = st.data_editor(
            products_df,
            column_config={
                "product_name": st.column_config.TextColumn("Producto", width="large"),
                "quantity": st.column_config.NumberColumn("Cantidad", format="%.2f"),
                "unit_price": st.column_config.NumberColumn("Precio Unit.", format="$%.2f"),
                "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.2f", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )

        # Recalculate subtotals
        edited_df['subtotal'] = edited_df['quantity'] * edited_df['unit_price']

        # Filter valid products and sync back to session state
        valid_products = edited_df[
            (edited_df['product_name'].notna()) & 
            (edited_df['product_name'] != '') &
            (edited_df['quantity'] > 0)
        ].to_dict('records')
        
        st.session_state.quote_products = valid_products

        # Calculate and display totals
        if valid_products:
            quotation = QuotationGenerator()
            totals = quotation.calculate_quote(valid_products)

            st.markdown('<div class="section-header">📊 Resumen de Costos</div>', unsafe_allow_html=True)

            # Display metrics in three columns
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
                    <div class="result-title">TOTAL GENERAL</div>
                    <div class="result-value">${totals['grand_total']:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # Action buttons
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # Add checkbox to toggle product inclusion in PDF
                show_products_pdf = st.checkbox("Incluir productos en PDF", value=True)
                
                if st.button("📄 Generar PDF", type="primary"):
                    try:
                        company_info = {
                            'client': client_name if client_name else "Cliente No Especificado",
                            'project': project_name if project_name else "Proyecto No Especificado",
                            'date': quote_date.strftime('%d/%m/%Y'),
                            'validity': quote_validity,
                            'notes': notes if notes else ""
                        }
                        
                        pdf_buffer = quotation.generate_pdf(
                            quote_data=company_info,
                            company_info=company_info,
                            products=valid_products if show_products_pdf else [],
                            totals=totals,
                            show_products=show_products_pdf
                        )
                        
                        st.download_button(
                            label="⬇️ Descargar PDF",
                            data=pdf_buffer,
                            file_name=f"cotizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
                        st.success("✅ PDF generado exitosamente")
                    except Exception as e:
                        st.error(f"Error al generar PDF: {str(e)}")

            with col2:
                if st.button("💾 Guardar Borrador"):
                    st.session_state.saved_quote = {
                        'products': valid_products,
                        'totals': totals,
                        'company_info': {
                            'client': client_name,
                            'project': project_name,
                            'validity': quote_validity,
                            'notes': notes
                        },
                        'timestamp': datetime.now()
                    }
                    st.success("✅ Borrador guardado exitosamente")

            with col3:
                if st.button("🔄 Reiniciar"):
                    st.session_state.quote_products = []
                    st.rerun()

            with col4:
                try:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        # Write products
                        products_export = pd.DataFrame(valid_products)
                        products_export.to_excel(writer, sheet_name='Productos', index=False)
                        
                        # Write totals
                        totals_df = pd.DataFrame([totals]).T.reset_index()
                        totals_df.columns = ['Concepto', 'Monto']
                        totals_df.to_excel(writer, sheet_name='Totales', index=False)
                    
                    excel_buffer.seek(0)
                    st.download_button(
                        label="📊 Exportar Excel",
                        data=excel_buffer,
                        file_name=f"cotizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Error al generar Excel: {str(e)}")

    else:
        st.info("No hay productos en la cotización. Use 'Importar de Cálculos' o 'Agregar Producto Manual' para comenzar.")

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
    🏗️ <strong>Calculadora de Nave Industrial 2030</strong><br>
    Sistema Avanzado de Cálculo Estructural + Cotización<br>
    © 2030 | Versión 2.0
</div>
""", unsafe_allow_html=True)
