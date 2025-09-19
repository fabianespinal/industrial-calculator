import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Calculadora de Nave Industrial 2030",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Styling
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
.stTextInput > div > div > input {
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
.stTextInput > div > div > input:focus {
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

.stSelectbox > div > div > div[role="button"]:hover {
    border-color: var(--primary-neon) !important;
    box-shadow: 0 0 25px rgba(0, 255, 255, 0.4) !important;
    transform: translateY(-2px) !important;
}

.stSelectbox [data-baseweb="select"] [role="listbox"] {
    background: var(--card-bg) !important;
    border: 2px solid rgba(0, 255, 255, 0.4) !important;
    border-radius: 20px !important;
    backdrop-filter: blur(25px) !important;
    box-shadow: var(--shadow-glow) !important;
    max-height: 400px !important;
    margin-top: 8px !important;
}

.stSelectbox [role="option"] {
    background: transparent !important;
    color: rgba(255, 255, 255, 0.9) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 18px 28px !important;
    min-height: 56px !important;
    border-bottom: 1px solid rgba(0, 255, 255, 0.1) !important;
    transition: all 0.3s ease !important;
}

.stSelectbox [role="option"]:hover {
    background: linear-gradient(90deg, rgba(0, 255, 255, 0.1), rgba(255, 0, 255, 0.1)) !important;
    color: #ffffff !important;
    border-left: 4px solid var(--primary-neon) !important;
    padding-left: 24px !important;
    transform: translateX(8px) !important;
}

.stSelectbox [role="option"][aria-selected="true"] {
    background: var(--gradient-primary) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    border-left: 6px solid var(--accent-neon) !important;
    padding-left: 22px !important;
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
    <div class="main-subtitle">Sistema RIGC. Cálculo Estructural 2030</div>
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

# Initialize data
profiles = get_steel_profiles()
profile_options = [f"{p[0]} x {p[1]} ({p[1]} lb/ft)" for p in profiles]
profile_weights = {f"{p[0]} x {p[1]} ({p[1]} lb/ft)": p[1] for p in profiles}

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Cálculo de Acero", 
    "📦 Materiales", 
    "📚 Base de Datos", 
    "💰 DR Gravamen + ITBIS"
])

# TAB 1: STEEL CALCULATION
with tab1:
    st.markdown('<div class="section-header">Cálculo de Acero Estructural</div>', unsafe_allow_html=True)
    
    # Input dimensions
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        largo = st.number_input("Largo (m)", min_value=0.0, value=80.0, step=0.1)
    with col2:
        ancho = st.number_input("Ancho (m)", min_value=0.0, value=25.0, step=0.1)
    with col3:
        alto_lateral = st.number_input("Altura Lateral (m)", min_value=0.0, value=9.0, step=0.1)
    with col4:
        distancia = st.number_input("Distancia entre Ejes (m)", min_value=0.1, value=7.27, step=0.01)
    
    # Profile selection
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
    
    # Additional configuration
    st.markdown('<div class="section-header">Configuración Adicional</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        num_lados = st.selectbox("Lados Laterales", options=[1, 2], index=1, key="lat_lados")
    with col2:
        incluir_laterales = st.checkbox("Incluir Columnas Laterales", value=True, key="include_lateral")
    with col3:
        st.markdown("**Columnas Laterales:** Se calculan con la fórmula (Largo ÷ Distancia + 1) × Lados × Altura × Peso × 3.28")
    
    # Calculate button
    if st.button("🔧 Calcular Acero Estructural Completo", type="primary"):
        try:
            # Get weights
            peso_columnas = profile_weights[columnas]
            peso_tijerillas = profile_weights[tijerillas]
            peso_porticos = profile_weights[porticos]
            peso_laterales = profile_weights[columnas_laterales]
            
            # 1. Columnas: (Largo / distancia + 1) × 2 × altura lateral × peso × 3.28
            num_columnas = ((largo / distancia) + 1) * 2
            libras_columnas = num_columnas * alto_lateral * peso_columnas * 3.28
            ton_columnas = libras_columnas / 2204.62
            
            # 2. Tijerillas: (Largo / distancia + 1) × 2 × 1.1 × ancho × peso × 3.28
            num_tijerillas_calc = ((largo / distancia) + 1) * 2
            libras_tijerillas = num_tijerillas_calc * 1.1 * ancho * peso_tijerillas * 3.28
            ton_tijerillas = libras_tijerillas / 2204.62
            
            # 3. Pórticos: Perímetro × peso × 3.28
            perimetro = (ancho * 2) + (largo * 2)
            libras_porticos = perimetro * peso_porticos * 3.28
            ton_porticos = libras_porticos / 2204.62
            
            # 4. Columnas frontales: (Ancho / distancia + 1) × 2 × altura × 1.1 × 3.28 × peso
            num_columnas_frontales = ((ancho / distancia) + 1) * 2
            libras_columnas_frontales = num_columnas_frontales * alto_lateral * 1.1 * 3.28 * peso_columnas
            ton_columnas_frontales = libras_columnas_frontales / 2204.62
            
            # 5. Columnas laterales (opcional)
            if incluir_laterales:
                num_columnas_laterales = ((largo / distancia) + 1) * num_lados
                libras_columnas_laterales = num_columnas_laterales * alto_lateral * peso_laterales * 3.28
                ton_columnas_laterales = libras_columnas_laterales / 2204.62
            else:
                num_columnas_laterales = 0
                libras_columnas_laterales = 0
                ton_columnas_laterales = 0
            
            # 6. Conexiones: 15% del total
            total_libras = (libras_columnas + libras_tijerillas + libras_porticos + 
                           libras_columnas_frontales + libras_columnas_laterales)
            libras_conexiones = total_libras * 0.15
            ton_conexiones = libras_conexiones / 2204.62
            
            # 7. Elementos de fijación
            cantidad_pernos = ((largo / distancia) + 1) * 2
            tornillos_3_4 = int(libras_conexiones / 5)
            
            # Total
            total_ton = (ton_columnas + ton_tijerillas + ton_porticos + 
                        ton_columnas_frontales + ton_columnas_laterales + ton_conexiones)
            
            # Success message
            st.success("✅ Cálculo de Acero Estructural Completado Exitosamente")
            
            # Display results - First row
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Columnas</div>
                    <div class="metric-value">{num_columnas:.0f}</div>
                    <div class="metric-subtitle">unidades</div>
                    <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                    <div class="metric-title">Tonelaje</div>
                    <div class="metric-value" style="font-size: 28px;">{ton_columnas:.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Tijerillas</div>
                    <div class="metric-value">{num_tijerillas_calc:.0f}</div>
                    <div class="metric-subtitle">elementos</div>
                    <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                    <div class="metric-title">Tonelaje</div>
                    <div class="metric-value" style="font-size: 28px;">{ton_tijerillas:.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Pórticos de Frenado</div>
                    <div class="metric-value">{perimetro:.1f}</div>
                    <div class="metric-subtitle">m perímetro</div>
                    <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                    <div class="metric-title">Tonelaje</div>
                    <div class="metric-value" style="font-size: 28px;">{ton_porticos:.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Second row
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
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Columnas Laterales</div>
                        <div class="metric-value">--</div>
                        <div class="metric-subtitle">no incluidas</div>
                        <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                        <div class="metric-title">Tonelaje</div>
                        <div class="metric-value" style="font-size: 28px;">0.00</div>
                        <div class="metric-subtitle">ton</div>
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
                    <div class="metric-value" style="font-size: 28px;">{ton_conexiones:.2f}</div>
                    <div class="metric-subtitle">ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Third row - Additional elements
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Pernos</div>
                    <div class="metric-value">{cantidad_pernos:.0f}</div>
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
            
            # Total result
            lateral_text = f" | Laterales: {ton_columnas_laterales:.2f} ton" if incluir_laterales else ""
            st.markdown(f"""
            <div class="result-card">
                <div class="result-title">TOTAL ACERO ESTRUCTURAL</div>
                <div class="result-value">{total_ton:.2f} TON</div>
                <div class="result-subtitle">
                    Columnas: {ton_columnas:.2f} | Tijerillas: {ton_tijerillas:.2f} | Pórticos: {ton_porticos:.2f} | 
                    Frontales: {ton_columnas_frontales:.2f}{lateral_text} | Conexiones: {ton_conexiones:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Visualization
            fig = go.Figure()
            
            components = ['Columnas', 'Tijerillas', 'Pórticos', 'Col. Frontales']
            tonnages = [ton_columnas, ton_tijerillas, ton_porticos, ton_columnas_frontales]
            colors = ['rgba(0, 255, 255, 0.8)', 'rgba(255, 0, 255, 0.8)', 'rgba(255, 255, 0, 0.8)', 'rgba(0, 255, 0, 0.8)']
            
            if incluir_laterales:
                components.append('Col. Laterales')
                tonnages.append(ton_columnas_laterales)
                colors.append('rgba(255, 150, 0, 0.8)')
            
            components.append('Conexiones')
            tonnages.append(ton_conexiones)
            colors.append('rgba(150, 0, 255, 0.8)')
            
            for i, (component, tonnage, color) in enumerate(zip(components, tonnages, colors)):
                fig.add_trace(go.Bar(
                    name=component,
                    x=[component],
                    y=[tonnage],
                    marker=dict(
                        color=color,
                        line=dict(color=color.replace('0.8', '1'), width=2)
                    ),
                    hovertemplate=f'<b>{component}</b><br>Tonelaje: %{{y:.2f}} ton<extra></extra>'
                ))
            
            fig.update_layout(
                title=dict(
                    text='Distribución Completa de Tonelaje de Acero',
                    font=dict(size=24, color='white', family='Space Grotesk')
                ),
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
            
            st.success("✅ Cálculo de materiales completado exitosamente")
            
            # Materials dataframe
            materials_data = {
                'Material': [
                    'Aluzinc Techo', 'Aluzinc Paredes', 'Correas Techo', 'Correas Paredes',
                    'Tornillos', 'Tornillos 3/4"', 'Tillas', 'Tornillos 1/2"', 'Caños', 'Caballetes',
                    'Cubrefaltas', 'Bajantes', 'Boquillas', 'Pernos'
                ],
                'Cantidad': [
                    f"{aluzinc_techo:,.0f} pies",
                    f"{aluzinc_paredes:,.0f} pies",
                    f"{correas_techo:,.0f} pies",
                    f"{correas_paredes:,.0f} pies",
                    f"{tornillos_Techo:,.0f} unidades",
                    f"{tornillos_3_4:,.0f} unidades",
                    f"{tillas:,.0f} unidades",
                    f"{tornillos_media:,.0f} unidades",
                    f"{canos:,.0f} pies",
                    f"{caballetes:,.0f} pies",
                    f"{cubrefaltas:,.0f} pies",
                    f"{bajantes:,.0f} unidades",
                    f"{boquillas:,.0f} unidades",
                    f"{pernos:,.0f} unidades"
                ],
                'Categoría': [
                    'Techado', 'Paredes', 'Estructura', 'Estructura',
                    'Fijación', 'Fijación', 'Estructura', 'Fijación', 'Estructura', 'Techado',
                    'Acabados', 'Drenaje', 'Drenaje', 'Fijación'
                ]
            }
            
            df_materials = pd.DataFrame(materials_data)
            
            # Display table
            st.dataframe(
                df_materials,
                hide_index=True,
                use_container_width=True,
                height=500,
                column_config={
                    "Material": st.column_config.TextColumn("Material", width="medium"),
                    "Cantidad": st.column_config.TextColumn("Cantidad", width="medium"),
                    "Categoría": st.column_config.TextColumn("Categoría", width="small")
                }
            )
            
            # Area total
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
    
    # Search
    search = st.text_input("🔍 Buscar perfil:", placeholder="Ej: W24, 120, W14 x 68...")
    
    # Create dataframe
    df_profiles = pd.DataFrame(profiles, columns=['Serie', 'Peso (lb/ft)'])
    df_profiles['Perfil Completo'] = df_profiles.apply(lambda x: f"{x['Serie']} x {x['Peso (lb/ft)']}", axis=1)
    df_profiles = df_profiles[['Serie', 'Perfil Completo', 'Peso (lb/ft)']]
    
    # Filter
    if search:
        filtered_df = df_profiles[
            df_profiles['Perfil Completo'].str.contains(search, case=False) |
            df_profiles['Serie'].str.contains(search, case=False) |
            df_profiles['Peso (lb/ft)'].astype(str).str.contains(search, case=False)
        ]
    else:
        filtered_df = df_profiles
    
    # Display
    st.dataframe(
        filtered_df,
        hide_index=True,
        use_container_width=True,
        height=600,
        column_config={
            "Serie": st.column_config.TextColumn("Serie", width="small"),
            "Perfil Completo": st.column_config.TextColumn("Perfil Completo", width="medium"),
            "Peso (lb/ft)": st.column_config.NumberColumn("Peso (lb/ft)", width="small")
        }
    )
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📊 **Total de perfiles:** {len(df_profiles)}")
    with col2:
        st.info(f"🔍 **Resultados filtrados:** {len(filtered_df)}")
    with col3:
        unique_series = df_profiles['Serie'].nunique()
        st.info(f"📋 **Series disponibles:** {unique_series}")

# TAB 4: DR TAX CALCULATOR
with tab4:
    st.markdown('<div class="section-header">Calculadora DR Gravamen + ITBIS</div>', unsafe_allow_html=True)
    st.markdown("Cálculo de impuestos de importación para República Dominicana")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subtotal = st.number_input("SubTotal Importado (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    with col2:
        flete = st.number_input("Total Flete (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    with col3:
        base = st.number_input("Grand Total Base (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    
    # Tax calculations
    suma = subtotal + flete
    gravamen = suma * 0.14
    itbis = suma * 0.18
    total_final = base + gravamen + itbis
    
    # Display results
    if suma > 0 or base > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Suma Base</div>
                <div class="metric-value">${suma:,.2f}</div>
                <div class="metric-subtitle">SubTotal + Flete</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Gravamen (14%)</div>
                <div class="metric-value">${gravamen:,.2f}</div>
                <div class="metric-subtitle">Impuesto aduanal</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">ITBIS (18%)</div>
                <div class="metric-value">${itbis:,.2f}</div>
                <div class="metric-subtitle">Impuesto al valor</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Final total
        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">GRAN TOTAL FINAL</div>
            <div class="result-value">${total_final:,.2f}</div>
            <div class="result-subtitle">Base + Gravamen (14%) + ITBIS (18%)</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tax pie chart
        if total_final > 0:
            fig = go.Figure(data=[
                go.Pie(
                    labels=['Base', 'Gravamen (14%)', 'ITBIS (18%)'],
                    values=[base, gravamen, itbis],
                    hole=.4,
                    marker=dict(
                        colors=['#00ffff', '#ff00ff', '#ffff00'],
                        line=dict(color='#ffffff', width=3)
                    ),
                    textfont=dict(color='white', size=14, family='JetBrains Mono'),
                    hovertemplate='<b>%{label}</b><br>Monto: $%{value:,.2f}<br>Porcentaje: %{percent}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title=dict(
                    text='Desglose de Impuestos',
                    font=dict(size=24, color='white', family='Space Grotesk')
                ),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='white', family='JetBrains Mono'),
                height=500,
                showlegend=True,
                legend=dict(bgcolor='rgba(0, 0, 0, 0)', font=dict(color='white'))
            )
            
            st.plotly_chart(fig, use_container_width=True)

# SIDEBAR
with st.sidebar:
    st.markdown("""
    <div style="background: var(--card-bg); 
                border: 2px solid rgba(0, 255, 255, 0.4);
                padding: 24px; border-radius: 20px; margin-bottom: 2rem;
                backdrop-filter: blur(20px);
                box-shadow: var(--shadow-glow);">
        <h2 style="color: var(--primary-neon); margin-bottom: 16px; font-family: 'Space Grotesk', sans-serif;">📖 Guía de Uso</h2>
        <p style="color: rgba(255,255,255,0.8); margin-bottom: 0;">
            Sistema completo para cálculo de naves industriales
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔧 **Cálculo de Acero**")
    st.markdown("""
    • Dimensiones de la nave industrial
    • Selección de 4 tipos de perfiles W
    • **Incluye columnas laterales opcionales**
    • Cálculos automáticos de hasta 7 componentes
    • Visualización completa integrada
    """)
    
    st.markdown("### 📦 **Cálculo de Materiales**")
    st.markdown("""
    • Lista completa de materiales
    • Cantidades exactas calculadas
    • Incluye tornillos 3/4" nuevos
    • Área total automática
    """)
    
    st.markdown("### 📚 **Base de Datos**")
    st.markdown("""
    • Más de 150 perfiles W
    • Búsqueda avanzada
    • 13 series disponibles
    • Información completa
    """)
    
    st.markdown("### 💰 **Calculadora DR**")
    st.markdown("""
    • Gravamen 14% automático
    • ITBIS 18% calculado
    • Visualización en tiempo real
    • Desglose completo
    """)
    
    st.markdown("---")
    
    st.markdown("### 📐 **Fórmulas Técnicas**")
    
    with st.expander("🏛️ **Columnas**"):
        st.code("""
Cantidad = (Largo ÷ Distancia + 1) × 2
Libras = Cantidad × Altura × Peso × 3.28
Toneladas = Libras ÷ 2204.62
        """)
    
    with st.expander("🔗 **Tijerillas**"):
        st.code("""
Elementos = (Largo ÷ Distancia + 1) × 2
Libras = Elementos × 1.1 × Ancho × Peso × 3.28
Toneladas = Libras ÷ 2204.62
        """)
    
    with st.expander("🏗️ **Pórticos**"):
        st.code("""
Perímetro = (Ancho + Largo) × 2
Libras = Perímetro × Peso × 3.28
Toneladas = Libras ÷ 2204.62
        """)
    
    with st.expander("🏛️ **Columnas Laterales**"):
        st.code("""
Cantidad = (Largo ÷ Distancia + 1) × Lados
Libras = Cantidad × Altura × Peso × 3.28
Toneladas = Libras ÷ 2204.62
        """)
    
    with st.expander("⚙️ **Conexiones y Fijación**"):
        st.code("""
Conexiones = Total_Libras × 15%
Pernos = (Largo ÷ Distancia + 1) × 2
Tornillos 3/4" = Conexiones ÷ 5
        """)
    
    st.markdown("---")
    
    # Statistics
    st.markdown("### 📊 **Estadísticas**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Perfiles", len(profiles))
    with col2:
        st.metric("Series", len(set([p[0] for p in profiles])))
    
    st.markdown("---")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(255, 0, 255, 0.1)); 
                padding: 20px; border-radius: 15px; border: 2px solid rgba(0, 255, 255, 0.3);">
        <h4 style="color: var(--primary-neon);">💡 Consejo Técnico</h4>
        <p style="color: rgba(255, 255, 255, 0.9); font-size: 13px; margin: 0;">
            Las columnas laterales son opcionales y se pueden activar/desactivar según el diseño.
            Todos los cálculos usan fórmulas ingenieriles estándar.
        </p>
    </div>
    """, unsafe_allow_html=True)

# FOOTER
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem 0; 
            background: var(--card-bg); border-radius: 20px; 
            border: 1px solid rgba(0, 255, 255, 0.3);
            backdrop-filter: blur(15px);">
    <p style="margin: 0; font-size: 16px; color: rgba(255, 255, 255, 0.8);">
        🏗️ <strong>Calculadora de Nave Industrial 2030</strong> | 
        Sistema Avanzado de Cálculo Estructural | 
        © 2030 | Versión 2.0
    </p>
</div>
""", unsafe_allow_html=True)