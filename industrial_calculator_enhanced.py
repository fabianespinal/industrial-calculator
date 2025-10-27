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

# CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #5e64ff;
    --text-color: #333333;
    --text-muted: #6c757d;
    --bg-color: #ffffff;
    --card-bg: #f8f9fa;
    --border-color: #dee2e6;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.main, .stApp {
    background: var(--bg-color);
    color: var(--text-color);
    font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
    min-height: 100vh;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.login-container {
    max-width: 500px;
    margin: 5rem auto;
    padding: 3rem;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: var(--shadow);
}

.login-title {
    text-align: center;
    font-size: 32px;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* --- Text input --- */
.stTextInput > div > div > input {
    background: #d9d9d9 !important;
    color: #1023c9 !important;
    border: 1px solid #999 !important;
    border-radius: 6px !important;
    padding: 10px 15px !important;
    font-size: 16px !important;
    font-weight: bold !important;
    transition: all 0.3s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(94, 100, 255, 0.1) !important;
}

/* --- Button --- */
.stButton > button {
    background-color: var(--primary) !important;
    color: white !important;
    border: none !important;
    font-weight: 500 !important;
    padding: 8px 24px !important;
    border-radius: 4px !important;
    font-size: 14px !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    box-shadow: none !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    background-color: #4a50e6 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 2px 5px rgba(94, 100, 255, 0.2) !important;
}

/* --- Tabs --- */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 4px;
    gap: 8px;
    justify-content: center;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--text-muted);
    border: 1px solid transparent;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.3s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(94, 100, 255, 0.05);
    border-color: var(--border-color);
    color: var(--primary);
}
.stTabs [aria-selected="true"] {
    background: rgba(94, 100, 255, 0.1) !important;
    border: 1px solid var(--primary) !important;
    color: var(--primary) !important;
}

/* --- Cards --- */
.result-card, .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: var(--shadow);
    text-align: center;
}

/* --- Selectbox --- */
div[data-baseweb="select"] > div {
    background-color: #d9d9d9 !important;
    border: 1px solid #999 !important;
    border-radius: 6px !important;
    font-size: 16px !important;
    font-weight: bold !important;
    color: #1023c9 !important;
}
div[data-baseweb="select"] * {
    color: #1023c9 !important;
    font-weight: bold !important;
}

/* --- Number input --- */
input[type="number"] {
    background-color: #d9d9d9 !important;
    color: #1023c9 !important;
    font-size: 16px !important;
    font-weight: bold !important;
    border: 1px solid #999 !important;
    border-radius: 6px !important;
}

/* --- DataFrame --- */
.stDataFrame {
    background-color: #e6e6e6 !important;
    border: 1px solid #999 !important;
    border-radius: 8px !important;
    padding: 8px !important;
}

/* --- Metrics --- */
[data-testid="stMetricValue"] {
    color: #1023c9 !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #666 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
</style>
""", unsafe_allow_html=True)

# Steel profile weights (lbs/ft)
profile_weights = {
    "W4x13": 13, "W5x16": 16, "W5x19": 19,
    "W6x9": 9, "W6x12": 12, "W6x15": 15, "W6x16": 16, "W6x20": 20, "W6x25": 25,
    "W8x10": 10, "W8x13": 13, "W8x15": 15, "W8x18": 18, "W8x21": 21, "W8x24": 24,
    "W8x28": 28, "W8x31": 31, "W8x35": 35, "W8x40": 40, "W8x48": 48, "W8x58": 58, "W8x67": 67,
    "W10x12": 12, "W10x15": 15, "W10x17": 17, "W10x19": 19, "W10x22": 22, "W10x26": 26,
    "W10x30": 30, "W10x33": 33, "W10x39": 39, "W10x45": 45, "W10x49": 49, "W10x54": 54,
    "W10x60": 60, "W10x68": 68, "W10x77": 77, "W10x88": 88, "W10x100": 100, "W10x112": 112,
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
    "C9x20": 20, "C9x15": 15, "C9x13.4": 13.4,
    "C8x18.75": 18.75, "C8x13.75": 13.75, "C8x11.5": 11.5,
    "C7x14.75": 14.75, "C7x12.25": 12.25, "C7x9.8": 9.8,
    "C6x13": 13, "C6x10.5": 10.5, "C6x8.2": 8.2,
    "C5x9": 9, "C5x6.7": 6.7,
    "C4x7.25": 7.25, "C4x6.25": 6.25, "C4x5.4": 5.4,
    "C3x6": 6, "C3x5": 5, "C3x4.1": 4.1, "C3x3.5": 3.5,
    "MC18x58": 58, "MC18x51.9": 51.9, "MC18x45.8": 45.8, "MC18x42.7": 42.7,
    "MC13x50": 50, "MC13x40": 40, "MC13x35": 35, "MC13x31.8": 31.8,
    "MC12x50": 50, "MC12x45": 45, "MC12x40": 40, "MC12x35": 35, "MC12x31": 31,
    "MC12x14.3": 14.3, "MC12x10.6": 10.6,
    "MC10x41.1": 41.1, "MC10x33.6": 33.6, "MC10x28.5": 28.5, "MC10x25": 25, "MC10x22": 22,
    "MC10x8.4": 8.4, "MC10x6.5": 6.5,
    "MC9x25.4": 25.4, "MC9x23.9": 23.9,
    "MC8x22.8": 22.8, "MC8x21.4": 21.4, "MC8x20": 20, "MC8x18.7": 18.7, "MC8x8.5": 8.5,
    "MC7x22.7": 22.7, "MC7x19.1": 19.1, "MC7x17.6": 17.6,
    "MC6x18": 18, "MC6x16.3": 16.3, "MC6x15.3": 15.3, "MC6x15.1": 15.1, "MC6x12": 12,
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

def parse_fraction(s):
    if '/' in s:
        num, den = map(int, s.split('/'))
        return num / den
    return float(s)

def sort_key(profile):
    # Extract prefix (e.g., 'W', 'HSS')
    match = re.match(r'([A-Z]+)', profile)
    if not match:
        return (99, 0, 0, 0)
    prefix = match.group(1)
    
    # Type order matching your list, but closer to AISC (W, S, C, MC, L, HSS)
    types_order = {'W': 0, 'S': 1, 'C': 2, 'MC': 3, 'L': 4, 'HSS': 5}
    type_idx = types_order.get(prefix, 99)
    
    # Parse dimensions based on type
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

# Your profile_weights dict goes here
all_profiles = better_sort(list(profile_weights.keys()))

# --- AUTHENTICATION FUNCTIONS ---

def show_login_page():
    st.set_page_config(layout="centered")
    st.markdown("""
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
    """, unsafe_allow_html=True)

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
        st.markdown('</div>', unsafe_allow_html=True)
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

    st.markdown('</div>', unsafe_allow_html=True)

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

# --- MAIN APPLICATION (SINGLE PAGE, NO TABS) ---
def show_main_app():
    # === SIDEBAR: CLIENT MANAGEMENT (UNCHANGED) ===
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

    # === MAIN HEADER ===

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

            /* Subtle text shadow glow */
            .main-title, .subtitle {
                text-shadow: 0px 0px 20px rgba(0, 100, 255, 0.15);
            }

            /* Animation */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Responsive */
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

        <div class="header-container">
            <h1 class="main-title">RIGC 2030</h1>
            <p class="subtitle">Sistema de Cálculo Industrial</p>
        </div>
    """, unsafe_allow_html=True)



    # === CLIENT CONTEXT ===
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

    # ===================================================================================
    # SECTION 1: CÁLCULO COMPLETO (ACERO + MATERIALES)
    # ===================================================================================
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

            /* Subtle text shadow glow */
            .main-title, .subtitle {
                text-shadow: 0px 0px 20px rgba(0, 100, 255, 0.15);
            }

            /* Animation */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Responsive */
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

        <div class="header-container">
            <h1 class="main-title">CÁLCULO COMPLETO</h1>
            <p class="subtitle">ESTRUCTURA ➕ MATERIALES</p>
        </div>
    """, unsafe_allow_html=True)

    # --- Load defaults ---
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

    # --- Inputs ---
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

    # --- Profile selection ---
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

    # --- Profile weights ---
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

    # --- CALCULATE BUTTON ---
    if st.button("🟥 CALCULAR ESTRUCTURA COMPLETA + MATERIALES", type="primary", key="calc_full_btn", use_container_width=True):
        try:
            # ===== STEEL =====
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

            # ===== MATERIALS =====
            def calculate_materials(largo, ancho, alto_lateral, alto_techado):
                aluzinc_techo = largo * ancho * 1.1 * 3.28
                perimetro = 2 * (largo + ancho)
                aluzinc_pared = perimetro * alto_lateral * 3.28
                correa_techo = (ancho + 2) * largo * 3.28
                correa_pared = perimetro * (alto_lateral / 2 + 1) * 3.28
                tornillos_techo = aluzinc_techo * 5
                cubrefaltas = (ancho * 2 + alto_lateral * 4) * 1.1 * 3.28
                canaletas = largo * 2 * 1.1 * 3.28
                bajantes = int(largo / 7) + 1
                caballetes = largo * 1.1 * 3.28
                return {k: v for k, v in locals().items() if k != 'perimetro'}

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

            # ===== COMBINE & SAVE =====
            df_combined = pd.concat([df_steel, df_materials], ignore_index=True)
            st.session_state.full_calculation_result = df_combined

            # ===== DISPLAY RESULTS =====
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

            # --- Steel breakdown ---
            st.markdown("#### 🔹 Acero Estructural")
            peso_acero = df_combined[df_combined["tipo"] == "Acero Estructural"]
            if not peso_acero.empty:
                res = peso_acero.groupby("funcion")["peso_total"].sum().reset_index()
                res.columns = ["Elemento", "Peso (kg)"]
                res["Peso (kg)"] = res["Peso (kg)"].map("{:,.2f}".format)
                st.dataframe(res, use_container_width=True, hide_index=True)

            # --- Materials list ---
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

    # ===================================================================================
    # SECTION 2: COTIZACIÓN
    # ===================================================================================
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

            /* Subtle text shadow glow */
            .main-title, .subtitle {
                text-shadow: 0px 0px 20px rgba(0, 100, 255, 0.15);
            }

            /* Animation */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Responsive */
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

        <div class="header-container">
            <h1 class="main-title">COTIZACION</h1>
            <p class="subtitle">ESTRUCTURA ➕ MATERIALES</p>
        </div>
    """, unsafe_allow_html=True)

    # --- Company & Client Info ---
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

    # --- Import Button ---
    if st.button("🟥 Importar Cálculo Completo", type="primary", key="import_full", use_container_width=True):
        if 'full_calculation_result' in st.session_state and not st.session_state.full_calculation_result.empty:
            df = st.session_state.full_calculation_result.copy()
            steel_df = df[df["tipo"] == "Acero Estructural"].copy()
            steel_df["toneladas"] = steel_df["peso_total"] / 1000
            ton_columnas = steel_df[steel_df["funcion"] == "Columnas centrales"]["toneladas"].sum()
            ton_laterales = steel_df[steel_df["funcion"] == "Columnas laterales"]["toneladas"].sum()
            ton_tijerillas = steel_df[steel_df["funcion"] == "Tijerillas"]["toneladas"].sum()
            ton_porticos = steel_df[steel_df["funcion"] == "Pórticos de frenado"]["toneladas"].sum()
            ton_bracing = steel_df[steel_df["funcion"] == "Bracing (arriostramiento)"]["toneladas"].sum()
            ton_sagrods = steel_df[steel_df["funcion"] == "Sag Rods (tensores)"]["toneladas"].sum()
            ton_estructura = ton_columnas + ton_laterales + ton_tijerillas + ton_porticos + ton_bracing + ton_sagrods
            ton_conexiones = ton_estructura * 0.08

            materials_df = df[df["tipo"] == "Material de Cierre"].copy()
            mat_dict = dict(zip(materials_df["perfil"], materials_df["cantidad"]))

            products = [
                {"product_name": "Estructura de Acero - Columnas", "quantity": round(ton_columnas + ton_laterales, 2), "unit_price": 1200.0},
                {"product_name": "Estructura de Acero - Tijerillas", "quantity": round(ton_tijerillas, 2), "unit_price": 1200.0},
                {"product_name": "Estructura de Acero - Pórticos", "quantity": round(ton_porticos, 2), "unit_price": 1200.0},
                {"product_name": "Estructura de Acero - Correas", "quantity": round(ton_bracing + ton_sagrods, 2), "unit_price": 1200.0},
                {"product_name": "Conexiones y Accesorios", "quantity": round(ton_conexiones, 2), "unit_price": 1500.0},
                {"product_name": "Aluzinc Techo", "quantity": round(mat_dict.get("Aluzinc Techo", 0), 2), "unit_price": 3.5},
                {"product_name": "Aluzinc Pared", "quantity": round(mat_dict.get("Aluzinc Pared", 0), 2), "unit_price": 3.5},
                {"product_name": "Tornillos de Techo", "quantity": round(mat_dict.get("Tornillos", 0), 0), "unit_price": 0.15},
                {"product_name": "Canaletas", "quantity": round(mat_dict.get("Canaletas", 0), 2), "unit_price": 12.0},
                {"product_name": "Bajantes", "quantity": round(mat_dict.get("Bajantes", 0), 0), "unit_price": 85.0},
            ]
            for p in products:
                p["subtotal"] = p["quantity"] * p["unit_price"]
            st.session_state.quote_products = products
            st.success("✅ Productos importados desde Cálculo Completo")
            st.rerun()
        else:
            st.warning("⚠️ Ejecute primero el cálculo en la sección superior.")

    # --- Manual Add & Quote Table ---
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

    # --- Quote Table & Totals ---
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
            <div style="background: #f2f2f2; padding: 1rem; border-radius: 12px; text-align: center;">
                <div style="font-size: 20px; font-weight: bold; color: #1023c9;">TOTAL GENERAL</div>
                <div style="font-size: 36px; font-weight: bold; color: #1023c9;">${totals['grand_total']:,.2f}</div>
            </div>
                """, unsafe_allow_html=True)

        # --- Generate PDF ---
        col1, col2 = st.columns(2)
        with col1:
            show_products_in_pdf = st.checkbox("Mostrar productos en PDF", value=True)
        with col2:
            include_sketch = st.checkbox("Incluir diagrama 2D", value=True)
        if st.button("🟥Generar PDF", type="primary", use_container_width=True):
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
                pdf = QuotationGenerator.generate_pdf(
                    quote_data={},
                    company_info=company_info,
                    products=st.session_state.quote_products,
                    totals=totals,
                    show_products=show_products_in_pdf,
                    create_building_sketch=sketch
                )
                st.download_button(
                    "🟥 Descargar Cotización PDF ⏬",
                    pdf.getvalue(),
                    f"cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
    else:
        st.info("👆 Importe productos desde el cálculo o agréguelos manualmente para generar una cotización.")

    st.divider()

    # ===================================================================================
    # SECTION 3: GUARDAR CÁLCULO
    # ===================================================================================
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

            /* Subtle text shadow glow */
            .main-title, .subtitle {
                text-shadow: 0px 0px 20px rgba(0, 100, 255, 0.15);
            }

            /* Animation */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Responsive */
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

   # === FOOTER ===
    st.markdown("""
        <style>
            .footer {
                text-align: center;
                padding: 3rem 0 2rem 0;
                color: #a6a6a6;
                font-size: 15px;
                position: relative;
                margin-top: 4rem;
                animation: fadeIn 1.2s ease;
            }

            .footer-title {
                background: linear-gradient(120deg, #00d4ff 0%, #007bff 45%, #9b00ff 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 700;
                font-size: 18px;
                letter-spacing: 2px;
                text-transform: uppercase;
                text-shadow: 0px 0px 16px rgba(0, 100, 255, 0.12);
                margin-bottom: 0.5rem;
                display: inline-block;
            }

            .footer::before {
                content: "";
                display: block;
                width: 140px;
                height: 3px;
                margin: 0 auto 1.2rem auto;
                background: linear-gradient(90deg, rgba(0,212,255,0.8), rgba(155,0,255,0.8));
                border-radius: 3px;
                box-shadow: 0px 0px 10px rgba(0, 100, 255, 0.25);
            }

            .footer small {
                display: block;
                margin-top: 0.5rem;
                font-size: 13px;
                color: #8a8a8a;
                letter-spacing: 1px;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @media (max-width: 768px) {
                .footer {
                    font-size: 14px;
                    padding: 2rem 1rem;
                }
                .footer-title {
                    font-size: 16px;
                    letter-spacing: 1px;
                }
            }
        </style>

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




