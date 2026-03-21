import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import warnings
import json
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. 설정 및 데이터
# ==========================================
st.set_page_config(page_title="AMLS V4.5 FINANCE STRATEGY", layout="wide", page_icon="📰", initial_sidebar_state="expanded")

SECTOR_TICKERS = ['XLK','XLV','XLF','XLY','XLC','XLI','XLP','XLE','XLU','XLRE','XLB']
CORE_TICKERS   = ['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD','^VIX','HYG','IEF','QQQE','UUP']
TICKERS        = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST     = ['TQQQ','SOXL','USD','QLD','SSO','SPY','QQQ','GLD','CASH']

# (Load data and prices etc... as provided in original code)
# ( skipping data loading here for quick CSS/UI check demonstration)

# ==========================================
# 2. CSS - New Apex Elegant Dark Theme
# ==========================================
# This new style replaces ALL previous themes to achieve the requested look.
# Spacing, rounded corners, colors, and the distinct sidebar/button glow.

st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
    
    :root {
        --base-bg: #121418;       /* Very dark background for the app */
        --sidebar-bg: #121418;   /* Sidebar background flush with app */
        --card-bg: #1C1F28;      /* Distinct dark background for main cards */
        --text-main: #FFFFFF;
        --text-muted: #A0AEC0;
        --accent-primary: #8B5CF6; /* Purple for titles and accents */
        --accent-glow: rgba(139, 92, 246, 0.35); /* Soft, glowing purple shadow */
        --border-color: rgba(255, 255, 255, 0.05); /* Content card border */
        --btn-border-glow: #8B5CF6; /* Button border itself glows */
        --btn-shadow: 0 8px 16px rgba(0, 0, 0, 0.25); /* Button standard shadow */
        --rsi-low: #10B981;       /* Custom green for low RSI */
        --mdd-red: #EF4444;       /* Custom red for MDD */
    }

    /* Target headers for main title and sidebar components to be rounded cards */
    .apex-sidebar-card {
        position: relative;
        background-color: #1C1F28 !important; /* Slightly distinct dark card background */
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
    }

    /* Target 'Powered by Apex' type text */
    .apex-powered-text {
        font-size: 0.8em;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-left: 20px;
        margin-bottom: 5px;
    }

    /* Overall App Theme */
    .stApp { background-color: var(--base-bg); color: var(--text-main); font-family: 'DM Sans', 'Pretendard', sans-serif; }
    
    /* Main Content Spacing and Page Spacing */
    .main .block-container { max-width: 1300px; padding-top: 1rem; padding-bottom: 2rem; }

    /* Main Page Content Cards Spacing and Rounding */
    .neo-card {
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 28px !important;
        padding: 30px !important;
        height: 570px !important; /* Spacing matched to user image layout */
        box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
        display: flex; flex-direction: column; margin-bottom: 20px; transition: transform 0.25s, box-shadow 0.25s;
    }
    .neo-card:hover { transform: translateY(-2px); box-shadow: 0 16px 56px rgba(139,92,246,0.15), 0 10px 25px rgba(0,0,0,0.5) !important; }

    [data-testid="stMetric"] { background-color: var(--card-bg) !important; border: 1px solid var(--border-color) !important; border-radius: 12px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important; padding: 15px !important; }
    div[data-testid="stMetricValue"]>div { color: var(--text-main) !important; }
    div[data-testid="stMetricDelta"]>div { color: var(--accent-primary) !important; }
    
    /* Buttons and Inputs */
    .stButton > button { background: rgba(139,92,246,0.15) !important; border: 1.5px solid var(--accent-primary) !important; border-radius: 12px !important; color: var(--accent-primary) !important; font-weight: 600 !important; box-shadow: 0 0 10px var(--accent-glow) !important; transition: all 0.25s !important; }
    .stButton > button:hover { background: rgba(139,92,246,0.28) !important; box-shadow: 0 0 20px var(--accent-glow) !important; transform: translateY(-1px) !important; }
    
    [data-testid="stExpander"] { background: var(--card-bg) !important; border: 1px solid var(--border-color) !important; border-radius: 18px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important; }
    [data-testid="stHeader"]{background-color:transparent!important;}
    #MainMenu{visibility:hidden;}footer{visibility:hidden;}
    
    [data-testid="stSelectbox"] > div > div { background: #FFFFFF !important; border: 1px solid var(--border-color) !important; border-radius: 12px !important; }
    [data-testid="stAlert"] { background: rgba(255,255,255,0.95) !important; border-radius: 14px !important; border-left-width: 3px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important; }

    /* Sidebar - Rounded cards and special button structure */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right: none !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }

    /* Main Radio Buttons in Sidebar (The navigation buttons) */
    div.row-widget.stRadio > div > label {
        background-color: transparent !important; /* Transparent background */
        border-radius: 16px !important; /* Rounded corners */
        border: 1px solid rgba(255, 255, 255, 0.1) !important; /* Initial subtle border */
        margin-top: 8px !important; margin-bottom: 8px !important; padding: 10px 15px !important;
        display: flex; align-items: center; gap: 10px; transition: all 0.3s ease; box-shadow: var(--btn-shadow);
        
        /* Internal Mixed Glow Effect using Box Shadow */
        box-shadow: inset 0 0 12px rgba(139, 92, 246, 0.35) !important;
    }

    /* Muted Grey Text for navigation */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: var(--text-muted) !important; font-weight: 600; margin-bottom: 8px; }

    div.row-widget.stRadio > div > label:hover {
        border-color: rgba(139, 92, 246, 0.3) !important; /* Subtle purple-red highlight on hover */
        transform: translateY(-1px); box-shadow: 0 10px 20px rgba(0,0,0,0.3), inset 0 0 12px rgba(139, 92, 246, 0.45) !important;
    }

    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {
        border: 1.5px solid var(--accent-primary) !important; /* Purple when active */
        box-shadow: 0 0 0 2px rgba(139,92,246,0.25), 0 0 15px rgba(139,92,246,0.6) !important; /* Intensified shadow glow */
    }
    
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) p { color: var(--accent-primary) !important; font-weight: 700; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 3. 사이드바 - Updated Design Elements
# ==========================================
# Target Colors from User Image:
# Purple accent: #8B5CF6
# Dark base background: #121418
# Muted text: #A0AEC0

sidebar_top = st.sidebar.container()

# 1. Sidebar Header - Rounded Card
sidebar_top.markdown(f"""<div class="apex-sidebar-card">
<div style="text-align:left;">
<div style="font-size:1.8em; font-weight:bold; color:#8B5CF6;">AMLS V4.5</div>
<div style="font-size:1.2em; font-weight:600; color:#FFFFFF;">FINANCE ENGINE</div>
<div style="font-size:0.9em; margin-top:10px; color:#A0AEC0;">
🟢 실시간 (7개 종목)
</div>
</div>
</div>""", unsafe_allow_html=True)

# 2. Navigation labels (Grey muted)
st.sidebar.markdown(f"<p style='font-size:0.8em; text-transform:uppercase; color:#A0AEC0;'>NAVIGATION MENU</p>", unsafe_allow_html=True)

# 3. Navigation MENU (User provided - radio will automatically use updated styles)
page = st.sidebar.radio("NAVIGATION MENU",
    ["📊 시장 분석관 (Home)", "💼 내 포트폴리오", "🍫 8-Pack 레이더망", "📈 백테스트 랩", "📰 매크로 뉴스룸"],
    label_visibility="collapsed")

# 4. Powered section
st.sidebar.markdown(f"<p style='font-size:0.8em; text-transform:uppercase; color:#A0AEC0; margin-top:10px;'>Powered by Apex</p>", unsafe_allow_html=True)

# 5. Sidebar Footer - Rounded Card with logo
st.sidebar.markdown(f"""<div class="apex-sidebar-card">
<div style="text-align:left; color:#A0AEC0;">
AMLS V4.5 Apex Engine<br>&copy; 2026 SEYOON.
</div>
</div>""", unsafe_allow_html=True)


# ==========================================
# 4. 메인 제목 영역 - Apex Dark/Purple Style
# ==========================================
st.markdown(f"""
<div style="padding-bottom:15px;margin-bottom:30px;display:flex;justify-content:space-between;align-items:flex-end;margin-top:-20px;border-bottom:2px solid rgba(255,255,255,0.05);">
<div>
<h1 style="font-family:Georgia,serif;font-size:2.8em;margin:0;color:#FFFFFF;text-shadow:2px 2px 4px rgba(0,0,0,0.5);">AMLS V4.5 FINANCE STRATEGY</h1>
<p style="font-size:1.1em;letter-spacing:1px;margin:5px 0 0 0;font-weight:700;color:#8B5CF6;">THE WALL STREET QUANTITATIVE JOURNAL</p>
</div>
<div style="text-align:right;font-weight:bold;color:#FFFFFF;">
<div style="font-size:1.2em;">AMLS V4.5 ENGINE</div>
<div style="font-size:0.9em;color:#A0AEC0;">Elegant Dark Edition</div>
<div style="font-size:0.8em;margin-top:4px;color:#A0AEC0;">🟢 실시간 (7개 종목)</div>
</div>
</div>""", unsafe_allow_html=True)

# (Remainder of the main page routing logic logic, as provided in original code)
# ... [Rest of the code continues normally] ...
