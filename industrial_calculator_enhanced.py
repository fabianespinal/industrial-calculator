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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

# Page configuration - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="RIGC - ERP",
    page_icon="➕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize the database AFTER page config
import database
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
    # Accept a single dict
    length = dimensions.get('length', 20.0)
    width = dimensions.get('width', 15.0)
    wall_height = dimensions.get('wall_height', 4.0)
    roof_rise = dimensions.get('roof_height', 2.0)
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

# Steel profile weights (lbs/ft)
profile_weights = {
    # ... (keep all your profile_weights as-is – omitted here for brevity but must be included)
    "W12x136": 136, "W12x120": 120, "W12x106": 106, "W12x96": 96, "W12x87": 87,
    "W12x79": 79, "W12x72": 72, "W12x65": 65, "W12x58": 58, "W12x53": 53,
    "W12x50": 50, "W12x45": 45, "W12x40": 40, "W12x35": 35, "W12x30": 30,
    "W12x26": 26, "W12x22": 22, "W12x19": 19, "W12x16": 16, "W12x14": 14,
    "W14x159": 159, "W14x145": 145, "W14x132": 132, "W14x120": 120, "W14x109": 109,
    "W14x99": 99, "W14x90": 90, "W14x82": 82, "W14x74": 74, "W14x68": 68,
    "W14x61": 61, "W14x53": 53, "W14x48": 48, "W14x43": 43, "W14x38": 38,
    "W14x34": 34, "W14x30": 30, "W14x26": 26, "W14x22": 22,
    "W16x100": 100, "W16x89": 89, "W16x77": 77, "W16x67": 67, "W16x57": 57,
    "W16x50": 50, "W16x45": 45, "W16x40": 40, "W16x36": 36, "W16x31": 31,
    "W16x26": 26,
    "W18x119": 119, "W18x106": 106, "W18x97": 97, "W18x86": 86, "W18x76": 76,
    "W18x71": 71, "W18x65": 65, "W18x60": 60, "W18x55": 55, "W18x50": 50,
    "W18x46": 46, "W18x40": 40, "W18x35": 35,
    "W21x147": 147, "W21x132": 132, "W21x122": 122, "W21x111": 111, "W21x101": 101,
    "W21x93": 93, "W21x83": 83, "W21x73": 73, "W21x68": 68, "W21x62": 62,
    "W21x57": 57, "W21x50": 50, "W21x44": 44,
    "W24x192": 192, "W24x176": 176, "W24x162": 162, "W24x146": 146, "W24x131": 131,
    "W24x117": 117, "W24x104": 104, "W24x94": 94, "W24x84": 84, "W24x76": 76,
    "W24x68": 68, "W24x62": 62, "W24x55": 55,
    "W27x178": 178, "W27x161": 161, "W27x146": 146, "W27x114": 114, "W27x102": 102,
    "W27x94": 94, "W27x84": 84,
    "W30x211": 211, "W30x191": 191, "W30x173": 173, "W30x148": 148, "W30x132": 132,
    "W30x124": 124, "W30x116": 116, "W30x108": 108, "W30x99": 99, "W30x90": 90,
    "W33x241": 241, "W33x221": 221, "W33x201": 201, "W33x169": 169, "W33x152": 152,
    "W33x141": 141, "W33x130": 130, "W33x118": 118,
    "W36x302": 302, "W36x282": 282, "W36x262": 262, "W36x247": 247, "W36x232": 232,
    "W36x210": 210, "W36x194": 194, "W36x182": 182, "W36x170": 170, "W36x160": 160,
    "W36x150": 150, "W36x135": 135,
    "HSS8x8x1/2": 59.32, "HSS8x8x3/8": 45.34, "HSS8x8x5/16": 38.11, "HSS8x8x1/4": 30.84,
    "HSS6x6x1/2": 42.30, "HSS6x6x3/8": 32.58, "HSS6x6x5/16": 27.48, "HSS6x6x1/4": 22.37,
    "HSS5x5x1/2": 35.24, "HSS5x5x3/8": 27.04, "HSS5x5x5/16": 22.79, "HSS5x5x1/4": 18.54,
    "HSS4x4x1/2": 27.48, "HSS4x4x3/8": 21.21, "HSS4x4x5/16": 17.95, "HSS4x4x1/4": 14.62,
    "HSS3x3x3/8": 14.72, "HSS3x3x5/16": 12.51, "HSS3x3x1/4": 10.26, "HSS3x3x3/16": 7.90,
    "HSS8x6x1/2": 50.81, "HSS8x6x3/8": 38.96, "HSS8x6x5/16": 32.80, "HSS8x6x1/4": 26.60,
    "HSS8x4x1/2": 42.30, "HSS8x4x3/8": 32.58, "HSS8x4x5/16": 27.48, "HSS8x4x1/4": 22.37,
    "HSS6x4x1/2": 35.24, "HSS6x4x3/8": 27.04, "HSS6x4x5/16": 22.79, "HSS6x4x1/4": 18.54,
    "HSS5x3x1/2": 27.48, "HSS5x3x3/8": 21.21, "HSS5x3x5/16": 17.95, "HSS5x3x1/4": 14.62,
    "C15x50": 50, "C15x40": 40, "C15x33.9": 33.9,
    "C12x30": 30, "C12x25": 25, "C12x20.7": 20.7,
    "C10x30": 30, "C10x25": 25, "C10x20": 20, "C10x15.3": 15.3,
    "C8x18.75": 18.75, "C8x13.75": 13.75, "C8x11.5": 11.5,
    "C6x13": 13, "C6x10.5": 10.5, "C6x8.2": 8.2,
    "C4x7.25": 7.25, "C4x6.25": 6.25, "C4x5.4": 5.4,
    "C3x6": 6, "C3x5": 5, "C3x4.1": 4.1, "C3x3.5": 3.5,
    "MC18x58": 58, "MC18x51.9": 51.9, "MC18x45.8": 45.8, "MC18x42.7": 42.7,
    "MC12x50": 50, "MC12x45": 45, "MC12x40": 40, "MC12x35": 35, "MC12x31": 31,
    "MC12x14.3": 14.3, "MC12x10.6": 10.6,
    "MC10x41.1": 41.1, "MC10x33.6": 33.6, "MC10x28.5": 28.5, "MC10x25": 25, "MC10x22": 22,
    "MC10x8.4": 8.4, "MC10x6.5": 6.5,
    "L8x8x1": 51.0, "L8x8x3/4": 38.9, "L8x8x5/8": 32.7, "L8x8x1/2": 26.4,
    "L6x6x3/4": 28.7, "L6x6x5/8": 24.2, "L6x6x1/2": 19.6, "L6x6x3/8": 14.9, "L6x6x5/16": 12.4,
    "L5x5x3/4": 23.6, "L5x5x5/8": 20.0, "L5x5x1/2": 16.2, "L5x5x3/8": 12.3, "L5x5x5/16": 10.3,
    "L4x4x3/4": 18.5, "L4x4x5/8": 15.7, "L4x4x1/2": 12.8, "L4x4x3/8": 9.8, "L4x4x5/16": 8.2, "L4x4x1/4": 6.6,
    "L3.5x3.5x1/2": 11.1, "L3.5x3.5x3/8": 8.5, "L3.5x3.5x5/16": 7.2, "L3.5x3.5x1/4": 5.8,
    "L3x3x1/2": 9.4, "L3x3x3/8": 7.2, "L3x3x5/16": 6.1, "L3x3x1/4": 4.9, "L3x3x3/16": 3.71,
    "L8x6x1": 44.2, "L8x6x3/4": 33.8, "L8x6x5/8": 28.5, "L8x6x1/2": 23.0,
    "L8x4x1": 37.4, "L8x4x3/4": 28.7, "L8x4x5/8": 24.2, "L8x4x1/2": 19.6,
    "L6x4x3/4": 23.6, "L6x4x5/8": 20.0, "L6x4x1/2": 16.2, "L6x4x3/8": 12.3,
    "L5x3.5x3/4": 19.8, "L5x3.5x5/8": 16.8, "L5x3.5x1/2": 13.6, "L5x3.5x3/8": 10.4,
    "L5x3x1/2": 12.8, "L5x3x3/8": 9.7, "L5x3x5/16": 8.2, "L5x3x1/4": 6.6,
    "L4x3.5x1/2": 11.9, "L4x3.5x3/8": 9.1, "L4x3.5x5/16": 7.7, "L4x3.5x1/4": 6.2,
    "L4x3x5/8": 13.6, "L4x3x1/2": 11.1, "L4x3x3/8": 8.5, "L4x3x5/16": 7.2, "L4x3x1/4": 5.8,
    "S24x121": 121, "S24x106": 106, "S24x100": 100, "S24x90": 90, "S24x80": 80,
    "S20x96": 96, "S20x86": 86, "S20x75": 75, "S20x66": 66,
    "S18x70": 70, "S18x54.7": 54.7,
    "S15x50": 50, "S15x42.9": 42.9,
    "S12x50": 50, "S12x40.8": 40.8, "S12x35": 35, "S12x31.8": 31.8,
    "S10x35": 35, "S10x25.4": 25.4,
    "S8x23": 23, "S8x18.4": 18.4,
    "S6x17.25": 17.25, "S6x12.5": 12.5,
    "S4x9.5": 9.5, "S4x7.7": 7.7,
    "S3x7.5": 7.5, "S3x5.7": 5.7,
}

def sort_profiles(profiles):
    profile_types = ['W', 'S', 'HSS', 'MC', 'C', 'L']
    sorted_profiles = []
    for prefix in profile_types:
        type_profiles = [p for p in profiles if p.startswith(prefix)]
        type_profiles.sort(key=lambda x: profile_weights[x], reverse=True)
        sorted_profiles.extend(type_profiles)
    remaining = [p for p in profiles if p not in sorted_profiles]
    sorted_profiles.extend(remaining)
    return sorted_profiles

all_profiles = sort_profiles(list(profile_weights.keys()))

# --- AUTHENTICATION FUNCTIONS ---
def show_login_page():
    logo = next((p for p in ["logo.png", "assets/logo.png", "logo.jpg", "assets/logo.jpg"] 
                 if os.path.exists(p)), None)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if logo:
            st.image(logo, use_container_width=True)
        else:
            st.markdown('<div style="text-align:center; font-size:72px; margin:2rem 0;">🏗️</div>', 
                       unsafe_allow_html=True)
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
        if st.session_state.attempts >= MAX_ATTEMPTS:
            st.error("⚠️ Máximo de intentos alcanzado. Contacte al administrador.")
            return
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
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
    def generate_pdf(quote_data, company_info, products, totals, show_products=True, create_building_sketch=None):
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
        story.append(Paragraph("ESTIMADO", title_style))

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

        disclaimer_text = (
            "<b>Aviso legal:</b> <b>Esta cotización es solo un estimado.</b> "
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
    if st.sidebar.button("🚪 Cerrar Sesión", key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

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

    tab1, tab2, tab3, tab4 = st.tabs([
        "📐 CÁLCULO DE ACERO", 
        "🧱 MATERIALES DE CIERRE", 
        "🧮 COTIZACIÓN", 
        "💾 GUARDAR"
    ])

    # TAB 1: CÁLCULO DE ACERO
    with tab1:
        st.markdown('<div class="section-header">Cálculo de Acero Estructural</div>', unsafe_allow_html=True)
        if st.session_state.get('current_calculation'):
            calc_data = st.session_state.current_calculation
            default_largo = calc_data.get('warehouse_length', 80)
            default_ancho = calc_data.get('warehouse_width', 25)
            default_alto_lateral = calc_data.get('lateral_height', 9)
            default_alto_techado = calc_data.get('roof_height', 7)
            default_distancia = calc_data.get('axis_distance', 7.27)
        else:
            default_largo = 80
            default_ancho = 25
            default_alto_lateral = 9
            default_alto_techado = 7
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
            distancia = st.number_input("Distancia entre Ejes (m)", min_value=0.1, value=float(default_distancia), step=0.01, key="steel_distancia")

        if alto_techado < alto_lateral:
            st.warning("⚠️ La altura del techado debe ser mayor o igual a la altura lateral.")
            st.stop()

        st.markdown("### 🔧 Selección de Perfiles")
        default_columna = "W12x136"
        default_tijerilla = "W14x159"
        default_portico = "W16x100"
        default_correa = "C10x25"
        default_lateral = "W12x87"

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Perfiles Principales**")
            col1a, col1b = st.columns(2)
            with col1a:
                columnas = st.selectbox(
                    "Perfil Columnas", 
                    options=all_profiles, 
                    index=all_profiles.index(default_columna) if default_columna in all_profiles else 0,
                    key="col_profile"
                )
                tijerillas = st.selectbox(
                    "Perfil Tijerillas", 
                    options=all_profiles, 
                    index=all_profiles.index(default_tijerilla) if default_tijerilla in all_profiles else 0,
                    key="beam_profile"
                )
            with col1b:
                porticos = st.selectbox(
                    "Perfil Pórticos", 
                    options=all_profiles, 
                    index=all_profiles.index(default_portico) if default_portico in all_profiles else 0,
                    key="frame_profile"
                )
                correas = st.selectbox(
                    "Perfil Correas", 
                    options=all_profiles, 
                    index=all_profiles.index(default_correa) if default_correa in all_profiles else 0,
                    key="purlin_profile"
                )
        with col2:
            st.markdown("**Configuración Lateral**")
            col2a, col2b = st.columns(2)
            with col2a:
                columnas_laterales = st.selectbox(
                    "Perfil Columnas Laterales", 
                    options=all_profiles, 
                    index=all_profiles.index(default_lateral) if default_lateral in all_profiles else 0,
                    key="lat_profile"
                )
                num_lados = st.selectbox("Lados Laterales", options=[1, 2], index=1, key="lat_lados")
            with col2b:
                incluir_laterales = st.checkbox("Incluir Columnas Laterales", value=True, key="include_lateral")
                st.info("Columnas Laterales: (L÷D+1)×Lados×H×Peso×3.28")

        with st.expander("📊 Ver Pesos de Perfiles Seleccionados"):
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Columnas", f"{profile_weights[columnas]} lbs/ft")
            with col2:
                st.metric("Tijerillas", f"{profile_weights[tijerillas]} lbs/ft")
            with col3:
                st.metric("Pórticos", f"{profile_weights[porticos]} lbs/ft")
            with col4:
                st.metric("Correas", f"{profile_weights[correas]} lbs/ft")
            with col5:
                st.metric("Laterales", f"{profile_weights[columnas_laterales]} lbs/ft")

        if st.button("🔩 CALCULAR ESTRUCTURA COMPLETA", type="primary", key="calc_steel_btn"):
            try:
                peso_columnas = profile_weights[columnas]
                peso_tijerillas = profile_weights[tijerillas]
                peso_porticos = profile_weights[porticos]
                peso_laterales = profile_weights[columnas_laterales]
                peso_correas = profile_weights[correas]

                num_ejes = int((largo / distancia) + 1)
                num_columnas = num_ejes * 2
                libras_columnas = num_columnas * alto_lateral * peso_columnas * 3.28
                ton_columnas = libras_columnas / 2204.62

                num_tijerillas_calc = num_ejes * 2
                libras_tijerillas = num_tijerillas_calc * 1.1 * ancho * peso_tijerillas * 3.28
                ton_tijerillas = libras_tijerillas / 2204.62

                perimetro = (ancho * 2) + (largo * 2)
                libras_porticos = perimetro * peso_porticos * 3.28
                ton_porticos = libras_porticos / 2204.62

                num_columnas_frontales = int((ancho / distancia) + 1) * 2
                libras_columnas_frontales = num_columnas_frontales * alto_lateral * 1.1 * 3.28 * peso_columnas
                ton_columnas_frontales = libras_columnas_frontales / 2204.62

                if incluir_laterales:
                    num_columnas_laterales = int((largo / distancia) + 1) * num_lados
                    libras_columnas_laterales = num_columnas_laterales * alto_lateral * peso_laterales * 3.28
                    ton_columnas_laterales = libras_columnas_laterales / 2204.62
                else:
                    num_columnas_laterales = 0
                    libras_columnas_laterales = 0
                    ton_columnas_laterales = 0

                correas_techo = int((largo / 1.5) * (num_ejes * 2))
                correas_pared = int(((alto_lateral / 1.5) * num_ejes * 2) + ((alto_lateral / 1.5) * 4))
                total_correas = correas_techo + correas_pared
                libras_correas = total_correas * 6 * peso_correas * 3.28
                ton_correas = libras_correas / 2204.62

                total_libras = (libras_columnas + libras_tijerillas + libras_porticos + 
                               libras_columnas_frontales + libras_columnas_laterales + libras_correas)
                libras_conexiones = total_libras * 0.15
                ton_conexiones = libras_conexiones / 2204.62

                cantidad_pernos = num_ejes * 2
                tornillos_3_4 = int(libras_conexiones / 5)

                total_ton = (ton_columnas + ton_tijerillas + ton_porticos + 
                            ton_columnas_frontales + ton_columnas_laterales + 
                            ton_correas + ton_conexiones)

                st.session_state.last_steel_calc = {
                    'num_ejes': num_ejes,
                    'num_columnas': num_columnas,
                    'num_tijerillas': num_tijerillas_calc,
                    'num_porticos': perimetro,
                    'columnas_laterales': num_columnas_laterales,
                    'columnas_frontales': num_columnas_frontales,
                    'total_columnas': num_columnas + num_columnas_frontales + num_columnas_laterales,
                    'correas_techo': correas_techo,
                    'correas_pared': correas_pared,
                    'total_correas': total_correas,
                    'ton_columnas': ton_columnas,
                    'ton_tijerillas': ton_tijerillas,
                    'ton_porticos': ton_porticos,
                    'ton_frontales': ton_columnas_frontales,
                    'ton_laterales': ton_columnas_laterales,
                    'ton_correas': ton_correas,
                    'ton_conexiones': ton_conexiones,
                    'peso_total': total_ton,
                    'pernos': cantidad_pernos,
                    'tornillos_3_4': tornillos_3_4,
                    'largo': largo,
                    'ancho': ancho,
                    'alto_lateral': alto_lateral,
                    'alto_techado': alto_techado
                }

                st.success("✅ Cálculo de Acero Estructural Completado Exitosamente")
                st.markdown("### 📊 RESULTADOS DEL CÁLCULO ESTRUCTURAL")
                col1, col2, col3, col4 = st.columns(4)
                for i, (title, num, ton) in enumerate([
                    ("COLUMNAS PRINCIPALES", num_columnas, ton_columnas),
                    ("TIJERILLAS", num_tijerillas_calc, ton_tijerillas),
                    ("CORREAS", total_correas, ton_correas),
                    ("PÓRTICOS", perimetro, ton_porticos)
                ]):
                    unit = "unidades" if i != 3 else "m perímetro"
                    with [col1, col2, col3, col4][i]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8); margin-bottom: 12px;">{title}</div>
                            <div style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{num:.0f}</div>
                            <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">{unit}</div>
                            <hr style="margin: 20px 0; border: 1px solid rgba(0, 255, 255, 0.3);">
                            <div style="font-size: 14px; color: rgba(0, 255, 255, 0.8);">TONELAJE</div>
                            <div style="font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{ton:.2f}</div>
                            <div style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">ton</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("### ⚖️ RESUMEN DE PESOS (TONELADAS)")
                weights_df = pd.DataFrame({
                    'Componente': ['Columnas Principales', 'Columnas Frontales', 'Columnas Laterales', 
                                  'Tijerillas', 'Pórticos', 'Correas', 'Conexiones (15%)', 'TOTAL'],
                    'Cantidad': [num_columnas, num_columnas_frontales, num_columnas_laterales if incluir_laterales else 0,
                               num_tijerillas_calc, f"{perimetro:.1f}m", total_correas, '-', '-'],
                    'Peso (Ton)': [
                        f"{ton_columnas:.2f}",
                        f"{ton_columnas_frontales:.2f}",
                        f"{ton_columnas_laterales:.2f}" if incluir_laterales else "0.00",
                        f"{ton_tijerillas:.2f}",
                        f"{ton_porticos:.2f}",
                        f"{ton_correas:.2f}",
                        f"{ton_conexiones:.2f}",
                        f"{total_ton:.2f}"
                    ]
                })
                st.dataframe(weights_df, use_container_width=True, hide_index=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"🔩 **Pernos de Anclaje Requeridos:** {cantidad_pernos} unidades")
                with col2:
                    st.info(f"🔧 **Tornillos 3/4\" Estimados:** {tornillos_3_4:,} unidades")

                lateral_text = f" | Laterales: {ton_columnas_laterales:,.2f}" if incluir_laterales else ""
                st.markdown(f"""
                <div class="result-card">
                    <div style="font-size: 24px; font-weight: 800; color: rgba(0, 255, 255, 0.9); margin-bottom: 24px;">PESO TOTAL DE ACERO ESTRUCTURAL</div>
                    <div style="font-size: 64px; font-weight: 900; background: linear-gradient(135deg, #00ffff 0%, #0099ff 50%, #ff00ff 100%);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 24px 0;">{total_ton:,.2f} TON</div>
                    <div style="font-size: 16px; color: rgba(255, 255, 255, 0.7);">
                        Principales: {ton_columnas:,.2f} | Tijerillas: {ton_tijerillas:,.2f} | Pórticos: {ton_porticos:,.2f} | 
                        Frontales: {ton_columnas_frontales:,.2f}{lateral_text} | Correas: {ton_correas:,.2f} | Conexiones: {ton_conexiones:,.2f}
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background: rgba(0, 255, 255, 0.1); border-radius: 10px;">
                        <div style="font-size: 14px; color: rgba(255, 255, 255, 0.8);">
                            📐 Estructura: {largo}m × {ancho}m × {alto_lateral}m | 
                            🏗️ Ejes: {num_ejes} @ {distancia}m | 
                            🏠 Altura Techado: {alto_techado}m
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"❌ Error en el cálculo: {str(e)}")
                st.info("Verifica que todos los perfiles tengan pesos definidos en el diccionario profile_weights")

    # TAB 2: MATERIALES DE CIERRE
    with tab2:
        st.markdown("### 📏 Dimensiones de la Nave")
        col1, col2, col3, col4 = st.columns(4)
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
            area_total = largo_mat * ancho_mat
            st.markdown(f"""
            <div class="result-card">
                <h3 style="color: var(--primary-neon);">ÁREA TOTAL DE LA NAVE</h3>
                <h2 style="font-size: 36px; color: var(--accent-neon);">{area_total:,.0f} m²</h2>
            </div>
            """, unsafe_allow_html=True)

    # TAB 3: COTIZACIÓN
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

        st.markdown("### 📦 GESTIÓN DE PRODUCTOS")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Importar desde Cálculo de Acero", key="import_steel"):
                if st.session_state.last_steel_calc:
                    calc = st.session_state.last_steel_calc
                    steel_products = [
                        {"product_name": "Estructura de Acero - Columnas", 
                         "quantity": calc['ton_columnas'], "unit_price": 1200.0,
                         "subtotal": calc['ton_columnas'] * 1200.0},
                        {"product_name": "Estructura de Acero - Tijerillas", 
                         "quantity": calc['ton_tijerillas'], "unit_price": 1200.0,
                         "subtotal": calc['ton_tijerillas'] * 1200.0},
                        {"product_name": "Estructura de Acero - Correas", 
                         "quantity": calc['ton_correas'], "unit_price": 1200.0,
                         "subtotal": calc['ton_correas'] * 1200.0},
                        {"product_name": "Estructura de Acero - Pórticos", 
                         "quantity": calc['ton_porticos'], "unit_price": 1200.0,
                         "subtotal": calc['ton_porticos'] * 1200.0},
                        {"product_name": "Conexiones y Accesorios", 
                         "quantity": calc['ton_conexiones'], "unit_price": 1500.0,
                         "subtotal": calc['ton_conexiones'] * 1500.0}
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

        if st.session_state.quote_products:
            st.markdown("### Productos en la Cotización")
            products_df = pd.DataFrame(st.session_state.quote_products)
            for col in ['product_name', 'quantity', 'unit_price', 'subtotal']:
                if col not in products_df.columns:
                    products_df[col] = 0.0 if col != 'product_name' else ''
            products_df['quantity'] = pd.to_numeric(products_df['quantity'], errors='coerce').fillna(0)
            products_df['unit_price'] = pd.to_numeric(products_df['unit_price'], errors='coerce').fillna(0)
            products_df['subtotal'] = products_df['quantity'] * products_df['unit_price']

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

            if st.button("🔄 Limpiar Productos"):
                st.session_state.quote_products = []
                st.rerun()

            if st.session_state.quote_products:
                totals = QuotationGenerator.calculate_quote(st.session_state.quote_products)
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
                            sketch_buffer = create_building_sketch({
                                'length': calc.get('largo', 80),
                                'width': calc.get('ancho', 25),
                                'wall_height': calc.get('alto_lateral', 9),
                                'roof_height': calc.get('alto_techado', 12) - calc.get('alto_lateral', 9)
                            })

                        pdf_buffer = QuotationGenerator.generate_pdf(
                            quote_data={},
                            company_info=company_info,
                            products=st.session_state.quote_products,
                            totals=totals,
                            show_products=show_products_in_pdf,
                            create_building_sketch=sketch_buffer
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

    # TAB 4: GUARDAR CÁLCULO
    with tab4:
        st.markdown("### 💾 GUARDAR CÁLCULO")
        if st.session_state.current_client_id:
            client = database.get_client_by_id(st.session_state.current_client_id)
            st.info(f"**Cliente:** {client['company_name']}")
            has_steel = bool(st.session_state.get('last_steel_calc'))
            has_materials = bool(st.session_state.get('last_materials_calc'))
            if has_steel or has_materials:
                with st.form("save_calculation_form"):
                    project_save_name = st.text_input(
                        "Nombre del Proyecto",
                        value=st.session_state.get("project_name", "")
                    )
                    calc_type = st.selectbox(
                        "Tipo de Cálculo a Guardar",
                        ["Ambos (Acero + Materiales)", "Solo Acero", "Solo Materiales"]
                    )
                    total_amount = st.number_input("Monto Total (opcional)", value=0.0, min_value=0.0)
                    save_notes = st.text_area("Notas del Cálculo")
                    if st.form_submit_button("💾 Guardar en Base de Datos", type="primary"):
                        try:
                            if calc_type == "Ambos (Acero + Materiales)":
                                if has_steel and has_materials:
                                    steel = st.session_state.last_steel_calc
                                    materials = st.session_state.last_materials_calc
                                    combined_data = {"tipo": "completo", "acero": steel, "materiales": materials}
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
                        except Exception as e:
                            st.error(f"❌ Error al guardar: {str(e)}")
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
