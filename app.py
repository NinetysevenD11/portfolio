import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import json
import os

warnings.filterwarnings('ignore')

# =====================================================================
# [0] 시스템 설정 및 동적 테마 엔진
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 포트폴리오", layout="wide", initial_sidebar_state="expanded")

SETTINGS_FILE = "amls_settings_v10.json"
# 테마 추가/삭제에 따른 충돌 방지를 위해 v11로 세팅 파일 업데이트
SETTINGS_FILE = "amls_settings_v11.json"
ACCOUNTS_FILE = "amls_multi_accounts.json"
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "GLD", "CASH"]

@@ -28,7 +29,7 @@
with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
return json.load(f)
except: pass
    return {"theme": "애플 테마"}
    return {"theme": "아이패드 테마"}

def save_settings(settings_data):
with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
@@ -94,63 +95,76 @@


# =====================================================================
# [2] 동적 테마 엔진 (7가지 통합)
# [2] 동적 테마 엔진 (신규 테마 반영)
# =====================================================================
current_theme = st.session_state['settings'].get("theme", "애플 테마")
current_theme = st.session_state['settings'].get("theme", "아이패드 테마")

if current_theme == "애플 테마":
BASE_TEXT_COLOR = "#1d1d1f"; TEXT_SUB = "#8e8e93"
PANEL_BG = "rgba(255,255,255,0.65)"; PANEL_BORDER = "1px solid rgba(255,255,255,0.5)"; PANEL_RADIUS = "16px"
WIDGET_THEME = "light"
C_UP = "#34c759"; C_DOWN = "#ff3b30"; C_WARN = "#ff9500"; C_SAFE = "#007aff"
BASE_CHART_COLORS = {'TQQQ':'#ff3b30', 'SOXL':'#af52de', 'USD':'#5856d6', 'QLD':'#ff9500', 'SSO':'#ffcc00', 'QQQ':'#007aff', 'GLD':'#34c759', 'CASH':'#8e8e93'}

elif current_theme == "아이패드 테마":
    BASE_TEXT_COLOR = "#1C1C1E"; TEXT_SUB = "#8E8E93"
    PANEL_BG = "#FFFFFF"; PANEL_BORDER = "none"; PANEL_RADIUS = "24px"
    WIDGET_THEME = "light"
    C_UP = "#34C759"; C_DOWN = "#FF3B30"; C_WARN = "#FF9500"; C_SAFE = "#007AFF"
    BASE_CHART_COLORS = {'TQQQ':'#FF3B30', 'SOXL':'#AF52DE', 'USD':'#5856D6', 'QLD':'#FF9500', 'SSO':'#FFCC00', 'QQQ':'#007AFF', 'GLD':'#34C759', 'CASH':'#8E8E93'}

elif current_theme == "갤럭시 탭 테마":
    BASE_TEXT_COLOR = "#FAFAFA"; TEXT_SUB = "#A0A0A0"
    PANEL_BG = "#1C1C1E"; PANEL_BORDER = "none"; PANEL_RADIUS = "28px"
    WIDGET_THEME = "dark"
    C_UP = "#23D079"; C_DOWN = "#E94C3D"; C_WARN = "#F4B33E"; C_SAFE = "#3E91FF"
    BASE_CHART_COLORS = {'TQQQ':'#E94C3D', 'SOXL':'#9D4EDD', 'USD':'#3E91FF', 'QLD':'#F4B33E', 'SSO':'#F39C12', 'QQQ':'#3E91FF', 'GLD':'#F1C40F', 'CASH':'#A0A0A0'}

elif current_theme == "엑셀 테마":
    BASE_TEXT_COLOR = "#333333"; TEXT_SUB = "#666666"
    PANEL_BG = "#FFFFFF"; PANEL_BORDER = "1px solid #D4D4D4"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#107C41"; C_DOWN = "#C00000"; C_WARN = "#FFB900"; C_SAFE = "#0078D4"
    BASE_CHART_COLORS = {'TQQQ':'#C00000', 'SOXL':'#800080', 'USD':'#0078D4', 'QLD':'#FFB900', 'SSO':'#E36C09', 'QQQ':'#0078D4', 'GLD':'#FFC000', 'CASH':'#7F7F7F'}

elif current_theme in ["1930년대 타자기 테마", "1920년대 타자기 테마"]:
BASE_TEXT_COLOR = "#2c2a25"; TEXT_SUB = "#555555"
PANEL_BG = "#dfd7c5"; PANEL_BORDER = "2px solid #2c2a25"; PANEL_RADIUS = "0px"
WIDGET_THEME = "light"
C_UP = "#000080"; C_DOWN = "#8b0000"; C_WARN = "#b8860b"; C_SAFE = "#006400"
BASE_CHART_COLORS = {'TQQQ':'#8b0000', 'SOXL':'#556b2f', 'USD':'#8fbc8f', 'QLD':'#b8860b', 'SSO':'#cd853f', 'QQQ':'#000080', 'GLD':'#daa520', 'CASH':'#2f4f4f'}
elif current_theme == "블룸버그 터미널 테마":
    BASE_TEXT_COLOR = "#00FF41"; TEXT_SUB = "#888888"
    PANEL_BG = "#050505"; PANEL_BORDER = "1px solid #333333"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "dark"
    C_UP = "#00FF41"; C_DOWN = "#FF003C"; C_WARN = "#FFB000"; C_SAFE = "#00FFFF"
    BASE_CHART_COLORS = {'TQQQ':'#FF003C', 'SOXL':'#B900FF', 'USD':'#00FFFF', 'QLD':'#FF8A00', 'SSO':'#FFFF00', 'QQQ':'#00FF41', 'GLD':'#FFB000', 'CASH':'#888888'}

elif current_theme == "카페 테마":
BASE_TEXT_COLOR = "#5D4A44"; TEXT_SUB = "#A89B96"
PANEL_BG = "#FFFFFF"; PANEL_BORDER = "2px solid #FFF0E5"; PANEL_RADIUS = "20px"
WIDGET_THEME = "light"
C_UP = "#FFB7B2"; C_DOWN = "#A1C9F1"; C_WARN = "#FFDAC1"; C_SAFE = "#B5EAD7"
BASE_CHART_COLORS = {'TQQQ':'#FF9AA2', 'SOXL':'#C7CEEA', 'USD':'#E2F0CB', 'QLD':'#FFDAC1', 'SSO':'#FFB7B2', 'QQQ':'#A1C9F1', 'GLD':'#FCEBB6', 'CASH':'#B5EAD7'}

elif current_theme == "2000년대 구글 감성 테마":
BASE_TEXT_COLOR = "#000000"; TEXT_SUB = "#666666"
PANEL_BG = "#F8F9FA"; PANEL_BORDER = "1px solid #CCCCCC"; PANEL_RADIUS = "0px"
WIDGET_THEME = "light"
C_UP = "#34A853"; C_DOWN = "#EA4335"; C_WARN = "#FBBC05"; C_SAFE = "#4285F4"
BASE_CHART_COLORS = {'TQQQ':'#EA4335', 'SOXL':'#990099', 'USD':'#660099', 'QLD':'#FBBC05', 'SSO':'#F68B1F', 'QQQ':'#4285F4', 'GLD':'#F4B400', 'CASH':'#34A853'}

elif current_theme == "월스트리트 저널 테마":
BASE_TEXT_COLOR = "#1A1A1A"; TEXT_SUB = "#555555"
PANEL_BG = "#FFFFFF"; PANEL_BORDER = "1px solid #1A1A1A"; PANEL_RADIUS = "0px"
WIDGET_THEME = "light"
C_UP = "#006400"; C_DOWN = "#8B0000"; C_WARN = "#B8860B"; C_SAFE = "#000080"
BASE_CHART_COLORS = {'TQQQ':'#8B0000', 'SOXL':'#556b2f', 'USD':'#2F4F4F', 'QLD':'#B8860B', 'SSO':'#DAA520', 'QQQ':'#000080', 'GLD':'#BDB76B', 'CASH':'#696969'}
elif current_theme == "Chat GPT 테마":
    BASE_TEXT_COLOR = "#ECECF1"; TEXT_SUB = "#8E8EA0"
    PANEL_BG = "#444654"; PANEL_BORDER = "1px solid #565869"; PANEL_RADIUS = "8px"
    WIDGET_THEME = "dark"
    C_UP = "#10A37F"; C_DOWN = "#EF4146"; C_WARN = "#F4AC36"; C_SAFE = "#2A85FF"
    BASE_CHART_COLORS = {'TQQQ':'#EF4146', 'SOXL':'#B582FF', 'USD':'#2A85FF', 'QLD':'#F4AC36', 'SSO':'#E8713A', 'QQQ':'#10A37F', 'GLD':'#F2C94C', 'CASH':'#565869'}

else:
    BASE_TEXT_COLOR = "#1d1d1f"; TEXT_SUB = "#8e8e93"
    PANEL_BG = "rgba(255,255,255,0.65)"; PANEL_BORDER = "1px solid rgba(255,255,255,0.5)"; PANEL_RADIUS = "16px"
    BASE_TEXT_COLOR = "#1C1C1E"; TEXT_SUB = "#8E8E93"
    PANEL_BG = "#FFFFFF"; PANEL_BORDER = "none"; PANEL_RADIUS = "24px"
WIDGET_THEME = "light"
    C_UP = "#34c759"; C_DOWN = "#ff3b30"; C_WARN = "#ff9500"; C_SAFE = "#007aff"
    BASE_CHART_COLORS = {'TQQQ':'#ff3b30', 'SOXL':'#af52de', 'USD':'#5856d6', 'QLD':'#ff9500', 'SSO':'#ffcc00', 'QQQ':'#007aff', 'GLD':'#34c759', 'CASH':'#8e8e93'}
    C_UP = "#34C759"; C_DOWN = "#FF3B30"; C_WARN = "#FF9500"; C_SAFE = "#007AFF"
    BASE_CHART_COLORS = {'TQQQ':'#FF3B30', 'SOXL':'#AF52DE', 'USD':'#5856D6', 'QLD':'#FF9500', 'SSO':'#FFCC00', 'QQQ':'#007AFF', 'GLD':'#34C759', 'CASH':'#8E8E93'}

if "text_color" not in st.session_state['settings']:
    st.session_state['settings']["text_color"] = BASE_TEXT_COLOR
if "chart_colors" not in st.session_state['settings']:
    st.session_state['settings']["chart_colors"] = BASE_CHART_COLORS.copy()
# 데이터 강제 주입 로직 (에러 방지)
if "text_color" not in st.session_state['settings']: st.session_state['settings']["text_color"] = BASE_TEXT_COLOR
if "chart_colors" not in st.session_state['settings']: st.session_state['settings']["chart_colors"] = BASE_CHART_COLORS.copy()
for tkr in REQUIRED_TICKERS:
if tkr not in st.session_state['settings']["chart_colors"]:
st.session_state['settings']["chart_colors"][tkr] = BASE_CHART_COLORS.get(tkr, "#888888")
@@ -159,10 +173,12 @@
COLOR_PALETTE = st.session_state['settings']["chart_colors"]

# --- Plotly 레이아웃 설정 ---
if current_theme == "1930년대 타자기 테마" or current_theme == "월스트리트 저널 테마":
if current_theme in ["1930년대 타자기 테마", "월스트리트 저널 테마"]:
THEME_LAYOUT = dict(template="simple_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0))
elif current_theme in ["블룸버그 터미널 테마", "Chat GPT 테마"]:
elif current_theme in ["갤럭시 탭 테마"]:
THEME_LAYOUT = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(showgrid=True, gridcolor='#333', zerolinecolor='#444'), yaxis=dict(showgrid=True, gridcolor='#333', zerolinecolor='#444'))
elif current_theme == "엑셀 테마":
    THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(showgrid=True, gridcolor='#E1DFDD', zerolinecolor='#8A8886'), yaxis=dict(showgrid=True, gridcolor='#E1DFDD', zerolinecolor='#8A8886'))
else:
THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)'))

@@ -182,9 +198,58 @@
       [data-testid="stDataFrame"] {{ border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); background: rgba(255, 255, 255, 0.5); }}
       [data-testid="stSidebar"] {{ background: rgba(245, 245, 247, 0.7); backdrop-filter: blur(20px); border-right: 1px solid rgba(0,0,0,0.05); }}
       button[data-baseweb="tab"][aria-selected="true"] {{ color: #1d1d1f; border-bottom-color: #1d1d1f; border-bottom-width: 2px; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none; color: #1d1d1f; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none !important; color: {TEXT_COLOR}; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
       .sidebar-link:hover {{ background-color: rgba(0,0,0,0.05); transform: translateX(2px); }}
       """
        
    elif current_theme == "아이패드 테마":
        css_base = f"""
        .stApp, html, body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #F2F2F7 !important; color: {TEXT_COLOR} !important; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-radius: {PANEL_RADIUS} !important; box-shadow: 0 4px 20px rgba(0,0,0,0.05) !important; padding: 1.5rem !important; }}
        .stButton>button {{ background-color: #F2F2F7 !important; color: #007aff !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; padding: 0.5rem 1rem !important; transition: all 0.2s; }}
        .stButton>button:hover {{ background-color: #007aff !important; color: #ffffff !important; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #F2F2F7 !important; color: {TEXT_COLOR} !important; border: none !important; border-radius: 10px !important; }}
        [data-testid="stDataFrame"] {{ border-radius: 16px !important; border: 1px solid #E5E5EA !important; }}
        [data-testid="stSidebar"] {{ background-color: #FFFFFF !important; border-right: 1px solid #E5E5EA !important; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #1d1d1f !important; border-bottom-color: #1d1d1f !important; border-bottom-width: 2px !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: #F2F2F7; }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}"

    elif current_theme == "갤럭시 탭 테마":
        css_base = f"""
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp, html, body {{ font-family: 'Pretendard', sans-serif; background-color: #000000 !important; color: {TEXT_COLOR} !important; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-radius: {PANEL_RADIUS} !important; padding: 1.5rem !important; box-shadow: none !important; }}
        .stButton>button {{ background-color: #333333 !important; color: #FAFAFA !important; border: none !important; border-radius: 20px !important; font-weight: 600 !important; padding: 0.5rem 1rem !important; transition: all 0.2s; }}
        .stButton>button:hover {{ background-color: #3E91FF !important; color: #ffffff !important; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #2C2C2E !important; color: {TEXT_COLOR} !important; border: none !important; border-radius: 14px !important; }}
        [data-testid="stDataFrame"] {{ border-radius: 20px !important; border: none !important; background-color: #1C1C1E !important; }}
        [data-testid="stSidebar"] {{ background-color: #151515 !important; border-right: 1px solid #333333 !important; }}
        button[data-baseweb="tab"] {{ color: #A0A0A0 !important; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #3E91FF !important; border-bottom-color: #3E91FF !important; border-bottom-width: 2px !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 14px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: #333333; }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: none; }}"

    elif current_theme == "엑셀 테마":
        css_base = f"""
        .stApp, html, body {{ font-family: 'Calibri', 'Malgun Gothic', sans-serif; background-color: #F3F2F1 !important; color: {TEXT_COLOR} !important; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-top: 3px solid #107C41 !important; border-radius: {PANEL_RADIUS} !important; padding: 1.5rem !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; }}
        .stButton>button {{ background-color: #E1DFDD !important; color: #333333 !important; border: 1px solid #8A8886 !important; border-radius: 2px !important; font-weight: normal !important; padding: 0.3rem 0.8rem !important; }}
        .stButton>button:hover {{ background-color: #C8C6C4 !important; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #FFFFFF !important; color: {TEXT_COLOR} !important; border: 1px solid #8A8886 !important; border-radius: 0px !important; }}
        [data-testid="stDataFrame"] {{ border-radius: 0px !important; border: 1px solid #D4D4D4 !important; }}
        [data-testid="stSidebar"] {{ background-color: #FFFFFF !important; border-right: 1px solid #D4D4D4 !important; }}
        button[data-baseweb="tab"] {{ color: #666666 !important; font-weight: normal !important; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #107C41 !important; border-bottom-color: #107C41 !important; border-bottom-width: 2px !important; font-weight: bold !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px; text-decoration: none !important; color: #0078D4 !important; font-family: 'Calibri', sans-serif; font-size: 0.95rem; border-bottom: 1px solid transparent; }}
        .sidebar-link:hover {{ border-bottom: 1px solid #0078D4; background-color: #F3F2F1; }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-top: 3px solid #107C41 !important; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}"

elif current_theme in ["1930년대 타자기 테마", "1920년대 타자기 테마"]:
css_base = f"""
       @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
@@ -201,22 +266,7 @@
       .sidebar-link:hover {{ background-color: rgba(0,0,0,0.1); border: 1px dashed {TEXT_COLOR}; }}
       """
css_panel = f".info-panel {{ background: #dfd7c5; border: 2px solid {TEXT_COLOR}; border-radius: 0px; padding: 16px; height: 100%; box-shadow: 4px 4px 0px {TEXT_COLOR}; }}"
    elif current_theme == "블룸버그 터미널 테마":
        css_base = f"""
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        [data-testid="stAppViewContainer"], [data-testid="stHeader"], .stApp {{ background-color: #000000 !important; background-image: none !important; }}
        html, body {{ font-family: 'Share Tech Mono', monospace !important; background-color: #000000 !important; color: {TEXT_COLOR} !important; letter-spacing: 0.05em; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: #050505 !important; border: 1px solid #333333 !important; border-radius: 0px !important; box-shadow: none !important; padding: 1.5rem !important; }}
        .stButton>button {{ background-color: #000000 !important; color: {TEXT_COLOR} !important; border: 1px solid {TEXT_COLOR} !important; border-radius: 0px !important; font-weight: normal !important; text-transform: uppercase; transition: all 0.1s; }}
        .stButton>button:hover {{ background-color: {TEXT_COLOR} !important; color: #000000 !important; box-shadow: 0 0 8px {TEXT_COLOR} !important; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #000000 !important; color: {TEXT_COLOR} !important; border: 1px solid #444444 !important; border-radius: 0px !important; font-family: 'Share Tech Mono', monospace !important; }}
        [data-testid="stDataFrame"] {{ border-radius: 0px !important; border: 1px solid #333333 !important; background: #000000 !important; }}
        [data-testid="stSidebar"] {{ background-color: #050505 !important; border-right: 1px solid #333333 !important; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: {TEXT_COLOR} !important; border-bottom-color: {TEXT_COLOR} !important; border-bottom-width: 2px !important; text-shadow: 0 0 5px {TEXT_COLOR}; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border: 1px solid transparent; border-radius: 0px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-size: 0.95rem; transition: background-color 0.1s; }}
        .sidebar-link:hover {{ background-color: rgba(0, 255, 65, 0.1); border: 1px dashed {TEXT_COLOR}; }}
        """
        css_panel = f".info-panel {{ background: #050505; border: 1px solid #333333; border-radius: 0px; padding: 16px; height: 100%; box-shadow: none; }}"
    
elif current_theme == "카페 테마":
css_base = f"""
       @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
@@ -228,9 +278,11 @@
       [data-testid="stDataFrame"] {{ border-radius: 16px; border: 2px solid #FFF0E5; }}
       [data-testid="stSidebar"] {{ background-color: #FFF6EC; border-right: 2px dashed #EAE3D9; }}
       button[data-baseweb="tab"][aria-selected="true"] {{ color: #FF9B94; border-bottom-color: #FF9B94; border-bottom-width: 3px; font-weight: bold; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none; color: {TEXT_COLOR}; font-weight: 700; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: 700; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
       .sidebar-link:hover {{ background-color: #FFF0E5; transform: translateX(4px); }}
       """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: 0 4px 12px rgba(210,190,175,0.1); }}"
    
elif current_theme == "2000년대 구글 감성 테마":
css_base = f"""
       .stApp, html, body {{ font-family: Arial, Tahoma, sans-serif; background-color: #FFFFFF; color: {TEXT_COLOR}; }}
@@ -242,10 +294,12 @@
       [data-testid="stSidebar"] {{ background-color: #F8F9FA; border-right: 1px solid #CCCCCC; }}
       button[data-baseweb="tab"] {{ color: #0000EE; text-decoration: underline; font-weight: normal; }}
       button[data-baseweb="tab"][aria-selected="true"] {{ color: {TEXT_COLOR}; text-decoration: none; border-bottom: none; font-weight: bold; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px; text-decoration: underline; color: #0000EE; font-family: Arial, sans-serif; font-size: 0.9rem; }}
        .sidebar-link:hover {{ color: #FF0000; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px; text-decoration: underline !important; color: #0000EE !important; font-family: Arial, sans-serif; font-size: 0.9rem; }}
        .sidebar-link:hover {{ color: #FF0000 !important; }}
       .sidebar-link span {{ display: none; }}
       """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; }}"
    
elif current_theme == "월스트리트 저널 테마":
css_base = f"""
       @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap');
@@ -258,27 +312,9 @@
       [data-testid="stDataFrame"] {{ border-radius: 0px; border: 1px solid #000000; }}
       [data-testid="stSidebar"] {{ background-color: #EBEBEB; border-right: 2px solid #000000; }}
       button[data-baseweb="tab"][aria-selected="true"] {{ color: #000000; border-bottom: 3px solid #000000; font-weight: bold; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; text-decoration: none; color: #000000; font-weight: bold; font-size: 0.95rem; border-bottom: 1px dotted #CCC; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; text-decoration: none !important; color: #000000 !important; font-weight: bold; font-size: 0.95rem; border-bottom: 1px dotted #CCC; }}
       .sidebar-link:hover {{ background-color: #DDDDDD; }}
       """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; border-top: 3px solid #000; font-family: 'Arial', sans-serif; }}"
    elif current_theme == "Chat GPT 테마":
        css_base = f"""
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp, html, body {{ font-family: 'Pretendard', sans-serif; background-color: #343541 !important; color: {TEXT_COLOR} !important; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: #444654 !important; border: 1px solid #565869 !important; border-radius: 8px !important; padding: 1.5rem !important; }}
        .stButton>button {{ background-color: #10A37F !important; color: #FFFFFF !important; border: none !important; border-radius: 6px !important; font-weight: 600 !important; transition: background-color 0.2s; }}
        .stButton>button:hover {{ background-color: #1A7F64 !important; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #40414F !important; color: {TEXT_COLOR} !important; border: 1px solid #565869 !important; border-radius: 6px !important; }}
        input:focus, textarea:focus {{ border-color: #10A37F !important; box-shadow: 0 0 0 1px #10A37F !important; }}
        [data-testid="stDataFrame"] {{ border-radius: 8px !important; border: 1px solid #565869 !important; background: #40414F !important; }}
        [data-testid="stSidebar"] {{ background-color: #202123 !important; border-right: 1px solid #4D4D4F !important; }}
        button[data-baseweb="tab"] {{ color: #8E8EA0 !important; font-weight: normal !important; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: {TEXT_COLOR} !important; border-bottom-color: #10A37F !important; border-bottom-width: 2px !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 6px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: 500; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: #2A2B32; }}
        """

st.markdown(f"""
   <style>
@@ -536,7 +572,7 @@
fig_p = go.Figure(go.Pie(labels=list(w.keys()), values=list(w.values()), hole=0.5, marker=dict(colors=[COLOR_PALETTE.get(k.split('/')[0], '#888') for k in w.keys()])))
cust_p = THEME_LAYOUT.copy(); cust_p.update(title=f"R{r}", title_x=0.5, height=250, margin=dict(t=40,b=10,l=10,r=10), showlegend=False)
fig_p.update_layout(**cust_p)
            fig_p.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color=TEXT_COLOR if current_theme not in ["1930년대 타자기 테마", "월스트리트 저널 테마", "블룸버그 터미널 테마", "Chat GPT 테마"] else "#ffffff", size=11))
            fig_p.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color="#ffffff" if current_theme in ["1930년대 타자기 테마", "월스트리트 저널 테마", "블룸버그 터미널 테마"] else TEXT_COLOR, size=11))
col.plotly_chart(fig_p, use_container_width=True)

with tab2:
@@ -571,17 +607,12 @@

curr_acc_data = st.session_state['accounts'][acc_name]

        # 기입표와 리밸런싱을 통합한 새로운 기본 레이아웃 구성
DEFAULT_LAYOUT = ["🎯 목표 달성률", "📊 실시간 요약", "⚡ 시스템 분석관", "💼 포트폴리오 & 리밸런싱", "📈 성장 곡선", "📝 매매 일지"]
current_layout = curr_acc_data.get("layout_order", [])

        # 구버전 레이아웃 블록 마이그레이션 처리
        if "💼 기입표" in current_layout:
            current_layout[current_layout.index("💼 기입표")] = "💼 포트폴리오 & 리밸런싱"
        if "🍩 자산 배분 & 지침" in current_layout:
            current_layout.remove("🍩 자산 배분 & 지침")
        if "🍩 배분 및 지침" in current_layout:
            current_layout.remove("🍩 배분 및 지침")
        if "💼 기입표" in current_layout: current_layout[current_layout.index("💼 기입표")] = "💼 포트폴리오 & 리밸런싱"
        if "🍩 자산 배분 & 지침" in current_layout: current_layout.remove("🍩 자산 배분 & 지침")
        if "🍩 배분 및 지침" in current_layout: current_layout.remove("🍩 배분 및 지침")

for item in DEFAULT_LAYOUT:
if item not in current_layout: current_layout.append(item)
@@ -744,7 +775,7 @@


# -------------------------------------------------------------
        # 레이아 편집기 UI
        # 레이아웃 편집기 UI
# -------------------------------------------------------------
with st.expander("🛠️ 화면 레이아웃 편집 (위아래로 순서 변경)"):
for i, block_name in enumerate(current_layout):
@@ -914,11 +945,11 @@
column_config={
"태그": st.column_config.SelectboxColumn("태그", options=["코어", "위성", "헷지", "현금", "단기픽"], required=True),
"티커 (Ticker)": st.column_config.TextColumn("종목명"),
                            "현재가 ($)": st.column_config.NumberColumn("현재가", disabled=True, format="$ %.2f"),
                            "현재 환율": st.column_config.NumberColumn("현재 환율", disabled=True, format="₩ %.1f"),
                            "수익률 (%)": st.column_config.NumberColumn("수익률", disabled=True, format="%.2f %%"),
                            "원화 수익률 (%)": st.column_config.NumberColumn("원화 수익", disabled=True, format="%.2f %%"),
                            "매입 환율": st.column_config.NumberColumn("매입 환율", format="₩ %.1f"),
                            "현재가 ($)": st.column_config.NumberColumn("현재가 💵", disabled=True, format="$ %.2f"),
                            "현재 환율": st.column_config.NumberColumn("현재 환율 💱", disabled=True, format="₩ %.1f"),
                            "수익률 (%)": st.column_config.NumberColumn("수익률 📈", disabled=True, format="%.2f %%"),
                            "원화 수익률 (%)": st.column_config.NumberColumn("원화 수익 🇰🇷", disabled=True, format="%.2f %%"),
                            "매입 환율": st.column_config.NumberColumn("매입 환율 💱", format="₩ %.1f"),
}
)
base_cols = ["티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "태그"]
@@ -1064,7 +1095,7 @@

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 테마 설정")
theme_list = ["애플 테마", "1930년대 타자기 테마", "블룸버그 터미널 테마", "카페 테마", "2000년대 구글 감성 테마", "월스트리트 저널 테마", "Chat GPT 테마"]
theme_list = ["애플 테마", "아이패드 테마", "갤럭시 탭 테마", "1930년대 타자기 테마", "카페 테마", "2000년대 구글 감성 테마", "월스트리트 저널 테마", "엑셀 테마"]
selected_theme = st.sidebar.selectbox("테마를 선택하세요", theme_list, index=theme_list.index(current_theme))
if selected_theme != current_theme:
st.session_state['settings']['theme'] = selected_theme
