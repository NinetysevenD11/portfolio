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

SETTINGS_FILE = "amls_settings_v5.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"theme": "애플 테마"}

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=4)

if 'settings' not in st.session_state:
    st.session_state['settings'] = load_settings()

current_theme = st.session_state['settings'].get("theme", "애플 테마")

# --- 테마별 변수 세팅 ---
if current_theme == "애플 테마":
    TEXT_COLOR = "#1d1d1f"
    C_UP = "#34c759"; C_DOWN = "#ff3b30"; C_WARN = "#ff9500"; C_SAFE = "#007aff"
    COLOR_PALETTE = {'TQQQ':'#ff3b30', 'SOXL':'#af52de', 'USD':'#5856d6', 'QLD':'#ff9500', 'SSO':'#ffcc00', 'QQQ':'#007aff', 'GLD':'#34c759', 'CASH':'#8e8e93'}
    THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="'Pretendard', sans-serif", color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', zerolinecolor='rgba(0,0,0,0.1)'), yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', zerolinecolor='rgba(0,0,0,0.1)'))
    
elif current_theme == "1920년대 타자기 테마":
    TEXT_COLOR = "#2c2a25"
    C_UP = "#000080"; C_DOWN = "#8b0000"; C_WARN = "#b8860b"; C_SAFE = "#006400"
    COLOR_PALETTE = {'TQQQ':'#8b0000', 'SOXL':'#556b2f', 'USD':'#8fbc8f', 'QLD':'#b8860b', 'SSO':'#cd853f', 'QQQ':'#000080', 'GLD':'#daa520', 'CASH':'#2f4f4f'}
    THEME_LAYOUT = dict(template="simple_white", paper_bgcolor="#e4dccc", plot_bgcolor="#dfd7c5", font=dict(family="'Special Elite', 'Courier New', monospace", color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0))

elif current_theme == "카페 테마":
    TEXT_COLOR = "#5D4A44"
    C_UP = "#FFB7B2"; C_DOWN = "#A1C9F1"; C_WARN = "#FFDAC1"; C_SAFE = "#B5EAD7"
    COLOR_PALETTE = {'TQQQ':'#FF9AA2', 'SOXL':'#C7CEEA', 'USD':'#E2F0CB', 'QLD':'#FFDAC1', 'SSO':'#FFB7B2', 'QQQ':'#A1C9F1', 'GLD':'#FCEBB6', 'CASH':'#B5EAD7'}
    THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="'Pretendard', sans-serif", color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(showgrid=True, gridcolor='#F5F0EA', zerolinecolor='#EAE3D9'), yaxis=dict(showgrid=True, gridcolor='#F5F0EA', zerolinecolor='#EAE3D9'))

elif current_theme == "2000년대 구글 감성 테마":
    TEXT_COLOR = "#000000"
    C_UP = "#34A853"; C_DOWN = "#EA4335"; C_WARN = "#FBBC05"; C_SAFE = "#4285F4"
    COLOR_PALETTE = {'TQQQ':'#EA4335', 'SOXL':'#990099', 'USD':'#660099', 'QLD':'#FBBC05', 'SSO':'#F68B1F', 'QQQ':'#4285F4', 'GLD':'#F4B400', 'CASH':'#34A853'}
    THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(family="Arial, Tahoma, sans-serif", color=TEXT_COLOR, size=12), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(showgrid=True, gridcolor='#E0E0E0', zerolinecolor='#CCCCCC'), yaxis=dict(showgrid=True, gridcolor='#E0E0E0', zerolinecolor='#CCCCCC'))


def apply_custom_css():
    if current_theme == "애플 테마":
        css = f"""
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        .stApp {{ background: radial-gradient(circle at 15% 50%, rgba(240, 244, 255, 1), rgba(255, 255, 255, 0)), radial-gradient(circle at 85% 30%, rgba(230, 240, 255, 1), rgba(255, 255, 255, 0)); background-color: #f5f5f7; font-family: 'Pretendard', sans-serif; color: {TEXT_COLOR}; letter-spacing: -0.01em; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background: rgba(255, 255, 255, 0.65); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.5); border-radius: 20px; box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.06); padding: 1.5rem; transition: transform 0.2s ease, box-shadow 0.2s ease; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{ box-shadow: 0 8px 32px -1px rgba(0, 0, 0, 0.1); }}
        .stButton>button {{ background-color: rgba(255, 255, 255, 0.8); color: #007aff; border: 1px solid rgba(0, 122, 255, 0.3); border-radius: 12px; font-weight: 600; padding: 0.5rem 1rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); backdrop-filter: blur(10px); transition: all 0.2s; }}
        .stButton>button:hover {{ background-color: #007aff; color: #ffffff; transform: scale(1.02); }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: rgba(255, 255, 255, 0.5); backdrop-filter: blur(10px); color: {TEXT_COLOR}; border: 1px solid rgba(0,0,0,0.1); border-radius: 12px; }}
        [data-testid="stDataFrame"] {{ border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); background: rgba(255, 255, 255, 0.5); }}
        [data-testid="stSidebar"] {{ background: rgba(245, 245, 247, 0.7); backdrop-filter: blur(20px); border-right: 1px solid rgba(0,0,0,0.05); }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #1d1d1f; border-bottom-color: #1d1d1f; border-bottom-width: 2px; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none; color: #1d1d1f; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.05); transform: translateX(2px); }}
        """
    elif current_theme == "1920년대 타자기 테마":
        css = f"""
        @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
        .stApp, html, body {{ font-family: 'Special Elite', 'Courier New', monospace; background-color: #e4dccc; color: {TEXT_COLOR}; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: #dfd7c5; border: 2px solid {TEXT_COLOR}; border-radius: 0px; box-shadow: 4px 4px 0px {TEXT_COLOR}; padding: 1.5rem; }}
        .stButton>button {{ background-color: #d1c7b3; color: {TEXT_COLOR}; border: 2px solid {TEXT_COLOR}; border-radius: 0px; box-shadow: 2px 2px 0px {TEXT_COLOR}; font-weight: bold; text-transform: uppercase; transition: all 0.1s; }}
        .stButton>button:active {{ box-shadow: 0px 0px 0px {TEXT_COLOR}; transform: translateY(2px) translateX(2px); }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #f0e9d8; color: {TEXT_COLOR}; border: 1px dashed {TEXT_COLOR}; border-radius: 0px; font-family: 'Special Elite', monospace; }}
        [data-testid="stDataFrame"] {{ border: 1px solid {TEXT_COLOR}; background-color: #f0e9d8; border-radius: 0px; }}
        [data-testid="stSidebar"] {{ background-color: #d1c7b3; border-right: 3px double {TEXT_COLOR}; }}
        h1, h2, h3, h4 {{ text-transform: uppercase; border-bottom: 2px solid {TEXT_COLOR}; padding-bottom: 5px; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: {TEXT_COLOR}; border-bottom-color: {TEXT_COLOR}; border-bottom-width: 3px; font-weight: bold; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border: 1px solid transparent; border-radius: 0px; text-decoration: none; color: {TEXT_COLOR}; font-weight: bold; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.1); border: 1px dashed {TEXT_COLOR}; }}
        """
    elif current_theme == "카페 테마":
        css = f"""
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        .stApp, html, body {{ font-family: 'Pretendard', sans-serif; background-color: #FFFBF0; color: {TEXT_COLOR}; letter-spacing: -0.01em; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: #FFFFFF; border: 2px solid #FFF0E5; border-radius: 24px; box-shadow: 0 8px 20px rgba(210, 190, 175, 0.15); padding: 1.5rem; transition: transform 0.2s ease, box-shadow 0.2s ease; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{ transform: translateY(-2px); box-shadow: 0 12px 28px rgba(210, 190, 175, 0.25); }}
        .stButton>button {{ background-color: #FFB7B2; color: #FFFFFF; border: none; border-radius: 16px; font-weight: 700; padding: 0.6rem 1.2rem; box-shadow: 0 4px 0 #F29F9A; transition: all 0.2s; }}
        .stButton>button:hover {{ background-color: #FFC4C0; transform: translateY(2px); box-shadow: 0 2px 0 #F29F9A; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #FAFAFA; color: {TEXT_COLOR}; border: 2px solid #EAE3D9; border-radius: 12px; }}
        [data-testid="stDataFrame"] {{ border-radius: 16px; border: 2px solid #FFF0E5; }}
        [data-testid="stSidebar"] {{ background-color: #FFF6EC; border-right: 2px dashed #EAE3D9; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #FF9B94; border-bottom-color: #FF9B94; border-bottom-width: 3px; font-weight: bold; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none; color: {TEXT_COLOR}; font-weight: 700; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link:hover {{ background-color: #FFF0E5; transform: translateX(4px); }}
        """
    else: # 2000년대 구글 감성 테마
        css = f"""
        .stApp, html, body {{ font-family: Arial, Tahoma, sans-serif; background-color: #FFFFFF; color: {TEXT_COLOR}; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{ background-color: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 0px; box-shadow: none; padding: 1.5rem; }}
        .stButton>button {{ background-color: #F0F0F0; color: #000000; border: 1px solid #707070; border-radius: 2px; font-weight: normal; padding: 0.3rem 0.8rem; }}
        .stButton>button:hover {{ background-color: #E0E0E0; border: 1px solid #333333; }}
        input, textarea, select, div[data-baseweb="select"] > div {{ background-color: #FFFFFF; color: #000000; border: 1px solid #999999; border-radius: 0px; font-family: Arial, sans-serif; }}
        [data-testid="stDataFrame"] {{ border-radius: 0px; border: 1px solid #999999; }}
        [data-testid="stSidebar"] {{ background-color: #F8F9FA; border-right: 1px solid #CCCCCC; }}
        h1, h2, h3, h4 {{ color: #000000; border-bottom: 1px solid #EEEEEE; padding-bottom: 5px; }}
        button[data-baseweb="tab"] {{ color: #0000EE; text-decoration: underline; font-weight: normal; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #000000; text-decoration: none; border-bottom: none; font-weight: bold; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px; text-decoration: underline; color: #0000EE; font-family: Arial, sans-serif; font-size: 0.9rem; }}
        .sidebar-link:hover {{ color: #FF0000; }}
        .sidebar-link span {{ display: none; }} /* 이모티콘 숨기기 (구글 감성) */
        """
    
    # 공통: 텍스트 잘림 방지 처리
    st.markdown(f"""
    <style>
    {css}
    div[data-testid="stMetricValue"] > div, div[data-testid="stMetricDelta"] > div, p, span, label, .stMarkdown {{ white-space: normal !important; word-break: keep-all !important; overflow-wrap: break-word !important; }}
    div[data-testid="stMetricValue"] {{ font-weight: bold; font-size: 1.8rem; color: {TEXT_COLOR}; }}
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

ACCOUNTS_FILE = "amls_multi_accounts.json"
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "GLD", "CASH"]

def load_accounts_data():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None
    return None

def save_accounts_data(data_dict):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)

if 'accounts' not in st.session_state:
    loaded = load_accounts_data()
    if not loaded:
        loaded = {
            "AMLS v4.3": {  
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0
            }
        }
    st.session_state['accounts'] = loaded

# 마이그레이션 로직
needs_save = False
for acc_name, acc_data in st.session_state['accounts'].items():
    if "seed_history" not in acc_data: acc_data["seed_history"] = {}; needs_save = True
    if "target_portfolio_value" not in acc_data: acc_data["target_portfolio_value"] = 100000.0; needs_save = True

    existing_tickers = [item["티커 (Ticker)"] for item in acc_data["portfolio"]]
    port_dict = {item["티커 (Ticker)"]: item for item in acc_data["portfolio"]}
    new_port = []
    for req_t in REQUIRED_TICKERS:
        if req_t in port_dict: 
            item = port_dict[req_t]
            if "매입 환율" not in item: item["매입 환율"] = 0.0; needs_save = True
            if "태그" not in item: item["태그"] = "코어" if req_t != "CASH" else "현금"; needs_save = True
            new_port.append(item)
        else: 
            new_port.append({"티커 (Ticker)": req_t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어" if req_t != "CASH" else "현금"})
            needs_save = True
    acc_data["portfolio"] = new_port
if needs_save: save_accounts_data(st.session_state['accounts'])


# =====================================================================
# [1] 글로벌 백엔드 함수
# =====================================================================
@st.cache_data(ttl=3600)
def load_amls_backtest_data(start, end, init_cap, monthly_cont, rebal_freq="월 1회"):
    tickers = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']
    start_str = (start - timedelta(days=400)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    try: data = yf.download(tickers, start=start_str, end=end_str, progress=False, auto_adjust=True)['Close']
    except: data = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
    data = data.ffill().dropna(subset=['QQQ', '^VIX'])

    df = pd.DataFrame(index=data.index)
    for t in data.columns: df[t] = data[t]

    df['QQQ_MA50'] = df['QQQ'].rolling(window=50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(window=200).mean()
    df['QQQ_RSI'] = ta.rsi(df['QQQ'], length=14)
    df['SMH_MA50'] = df['SMH'].rolling(window=50).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(periods=63)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)

    df = df.dropna(subset=['QQQ_MA200', 'SMH_RSI']).loc[pd.to_datetime(start):]
    daily_returns = df[data.columns].pct_change().fillna(0)

    def get_target_regime(row):
        vix, qqq, ma200, ma50 = row['^VIX'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
        if vix > 40: return 4
        if qqq < ma200: return 3
        if qqq >= ma200 and ma50 >= ma200 and vix < 25: return 1
        return 2

    df['Target_Regime'] = df.apply(get_target_regime, axis=1)
    
    actual_regime_v4 = []; actual_regime_v4_3 = []
    current_v4 = 3; current_v4_3 = 3
    pend_v4 = None; pend_v4_3 = None
    cnt_v4 = 0; cnt_v4_3 = 0

    for i in range(len(df)):
        tr = df['Target_Regime'].iloc[i]
        if tr > current_v4: current_v4 = tr; pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
        elif tr < current_v4:
            if tr == pend_v4:
                cnt_v4 += 1
                if cnt_v4 >= 5: current_v4 = tr; pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
                else: actual_regime_v4.append(current_v4)
            else: pend_v4 = tr; cnt_v4 = 1; actual_regime_v4.append(current_v4)
        else: pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
        
        if tr > current_v4_3: current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
        elif tr < current_v4_3: 
            if tr == pend_v4_3:
                cnt_v4_3 += 1
                if cnt_v4_3 >= 5: current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
                else: actual_regime_v4_3.append(current_v4_3 - 1)
            else: pend_v4_3 = tr; cnt_v4_3 = 1; actual_regime_v4_3.append(current_v4_3 - 1)
        else: pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)

    df['Signal_Regime_v4'] = pd.Series(actual_regime_v4, index=df.index).shift(1).bfill()
    df['Signal_Regime_v4_3'] = pd.Series(actual_regime_v4_3, index=df.index).shift(1).bfill()

    def get_v4_weights(regime, use_soxl):
        w = {t: 0.0 for t in data.columns}; semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'] = 0.30, 0.20, 0.20, 0.15, 0.10
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['QQQ'], w['USD'] = 0.25, 0.20, 0.20, 0.15, 0.10
        elif regime == 3: w['GLD'], w['QQQ'], w['SPY'] = 0.35, 0.20, 0.10
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        return w

    def get_v4_3_weights(regime, use_soxl):
        w = {t: 0.0 for t in data.columns}; semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'] = 0.30, 0.20, 0.20, 0.15, 0.10
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'] = 0.30, 0.25, 0.20, 0.10, 0.05
        elif regime == 3: w['GLD'], w['QQQ'] = 0.50, 0.15
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        return w

    strategies = ['AMLS v4.3', 'AMLS v4', 'QQQ', 'QLD', 'TQQQ']
    ports = {s: init_cap for s in strategies}
    hists = {s: [init_cap] for s in ports.keys()}
    total_invested = init_cap
    weights_v4 = {t: 0.0 for t in data.columns}; weights_v4_3 = {t: 0.0 for t in data.columns}
    logs, days_since_v4, days_since_v4_3 = [], 0, 0

    for i in range(1, len(df)):
        today, yesterday = df.index[i], df.index[i-1]
        days_since_v4 += 1; days_since_v4_3 += 1
        ret_v4 = sum(weights_v4[t] * daily_returns[t].iloc[i] for t in data.columns)
        ret_v4_3 = sum(weights_v4_3[t] * daily_returns[t].iloc[i] for t in data.columns)
        
        ports['AMLS v4'] *= (1 + ret_v4); ports['AMLS v4.3'] *= (1 + ret_v4_3)
        for s in ['QQQ', 'QLD', 'TQQQ']: ports[s] *= (1 + daily_returns[s].iloc[i])
        
        for t in data.columns:
            if ports['AMLS v4'] > 0: weights_v4[t] = weights_v4[t]*(1+daily_returns[t].iloc[i])/(1+ret_v4)
            if ports['AMLS v4.3'] > 0: weights_v4_3[t] = weights_v4_3[t]*(1+daily_returns[t].iloc[i])/(1+ret_v4_3)
            
        if today.month != yesterday.month:
            for s in ports: ports[s] += monthly_cont
            total_invested += monthly_cont
        for s in ports: hists[s].append(ports[s])
        
        use_soxl = (df['SMH'].iloc[i-1] > df['SMH_MA50'].iloc[i-1]) and (df['SMH_3M_Ret'].iloc[i-1] > 0.05) and (df['SMH_RSI'].iloc[i-1] > 50)
        
        sig_r_v4 = df['Signal_Regime_v4'].iloc[i]
        rebal_v4 = False
        if sig_r_v4 != df['Signal_Regime_v4'].iloc[i-1] or i == 1: rebal_v4 = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal_v4 = True
        elif "주 1회" in rebal_freq and days_since_v4 >= 5: rebal_v4 = True
        elif "2주 1회" in rebal_freq and days_since_v4 >= 10: rebal_v4 = True
        elif "3주 1회" in rebal_freq and days_since_v4 >= 15: rebal_v4 = True
        if rebal_v4: weights_v4 = get_v4_weights(sig_r_v4, use_soxl); days_since_v4 = 0

        sig_r_v4_3 = df['Signal_Regime_v4_3'].iloc[i]
        rebal_v4_3 = False
        if sig_r_v4_3 != df['Signal_Regime_v4_3'].iloc[i-1] or i == 1: rebal_v4_3 = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal_v4_3 = True
        elif "주 1회" in rebal_freq and days_since_v4_3 >= 5: rebal_v4_3 = True
        elif "2주 1회" in rebal_freq and days_since_v4_3 >= 10: rebal_v4_3 = True
        elif "3주 1회" in rebal_freq and days_since_v4_3 >= 15: rebal_v4_3 = True
        if rebal_v4_3:
            weights_v4_3 = get_v4_3_weights(sig_r_v4_3, use_soxl)
            log_type = "레짐 전환" if sig_r_v4_3 != df['Signal_Regime_v4_3'].iloc[i-1] else f"정기 ({rebal_freq.split(' ')[0]})"
            semi_target = "SOXL" if use_soxl and sig_r_v4_3 == 1 else ("USD" if sig_r_v4_3 in [1, 2] else "-")
            logs.append({"날짜": today.strftime('%Y-%m-%d'), "유형": log_type, "국면": f"R{int(sig_r_v4_3)}", "반도체": semi_target, "평가액": ports['AMLS v4.3']})
            days_since_v4_3 = 0

    for s in ports: df[f'{s}_Value'] = hists[s]
    inv_arr = [init_cap]; curr_inv = init_cap
    for i in range(1, len(df)):
        if df.index[i].month != df.index[i-1].month: curr_inv += monthly_cont
        inv_arr.append(curr_inv)
    df['Invested'] = inv_arr
    return df, logs, data.columns


# =====================================================================
# [2] 페이지 구성: 글로벌 마켓 대시보드
# =====================================================================
def page_market_dashboard():
    st.title("🌐 매크로 터미널")
    
    components.html("""<div class="tradingview-widget-container" style="border-radius: 8px; overflow: hidden; border: 1px solid rgba(0,0,0,0.1);">
<div class="tradingview-widget-container__widget"></div>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
{
"symbols": [
{"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"},
{"proName": "FOREXCOM:NSXUSD", "title": "NASDAQ 100"},
{"description": "TQQQ", "proName": "NASDAQ:TQQQ"},
{"description": "SOXL", "proName": "ARCA:SOXL"},
{"description": "USD/KRW", "proName": "FX_IDC:USDKRW"},
{"description": "GOLD", "proName": "OANDA:XAUUSD"}
],
"showSymbolLogo": true, "colorTheme": "light", "locale": "kr"
}
</script>
</div>""", height=70)

    col_left, col_right = st.columns([1, 1.8])
    with col_left:
        with st.container(border=True):
            st.markdown("##### 📈 주요 지수")
            tickers = ['^GSPC', '^IXIC', '^VIX', 'USDKRW=X']
            indices_df = yf.download(tickers, start=datetime.today()-timedelta(days=365), progress=False)['Close'].ffill()
            if not indices_df.empty:
                c1, c2 = st.columns(2); latest = indices_df.iloc[-1]; prev = indices_df.iloc[-2]
                c1.metric("S&P 500", f"{latest.get('^GSPC', 0):,.0f}", f"{(latest.get('^GSPC',0)/prev.get('^GSPC',1)-1)*100:+.2f}%")
                c2.metric("NASDAQ", f"{latest.get('^IXIC', 0):,.0f}", f"{(latest.get('^IXIC',0)/prev.get('^IXIC',1)-1)*100:+.2f}%")
                c3, c4 = st.columns(2)
                c3.metric("VIX", f"{latest.get('^VIX', 0):,.2f}", f"{(latest.get('^VIX',0)/prev.get('^VIX',1)-1)*100:+.2f}%", delta_color="inverse")
                c4.metric("USD/KRW", f"₩{latest.get('USDKRW=X', 0):,.1f}", f"{(latest.get('USDKRW=X',0)/prev.get('USDKRW=X',1)-1)*100:+.2f}%", delta_color="inverse")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=indices_df.index, y=indices_df['^GSPC']/indices_df['^GSPC'].iloc[0]*100, name="S&P 500", line=dict(color=C_SAFE, width=2)))
                fig.add_trace(go.Scatter(x=indices_df.index, y=indices_df['^IXIC']/indices_df['^IXIC'].iloc[0]*100, name="NASDAQ", line=dict(color=C_UP, width=2)))
                custom_l = THEME_LAYOUT.copy(); custom_l.update(height=240, showlegend=False)
                fig.update_layout(**custom_l)
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.markdown("##### 🗺️ S&P 500 히트맵")
            components.html("""<div style="border-radius: 8px; overflow: hidden; height: 100%;">
<iframe src="https://www.tradingview.com/embed-widget-stock-heatmap/?locale=kr#%7B%22dataSource%22%3A%22SPX500%22%2C%22blockSize%22%3A%22market_cap_basic%22%2C%22blockColor%22%3A%22change%22%2C%22grouping%22%3A%22sector%22%2C%22colorTheme%22%3A%22light%22%7D" width="100%" height="450" frameborder="0"></iframe>
</div>""", height=460)


# =====================================================================
# [3] 페이지 구성: AMLS 백테스트
# =====================================================================
def page_amls_backtest():
    st.title("🦅 전략 시뮬레이터")

    st.sidebar.header("⚙️ 시뮬레이션 설정")
    BACKTEST_START = st.sidebar.date_input("시작일", datetime(2018, 1, 1))
    BACKTEST_END = st.sidebar.date_input("종료일", datetime.today())
    INITIAL_CAPITAL = st.sidebar.number_input("초기 자본금 ($)", value=10000, step=1000)
    MONTHLY_CONTRIBUTION = st.sidebar.number_input("월 적립금 ($)", value=2000, step=500)
    REBAL_FREQ = st.sidebar.selectbox("🔄 리밸런싱 주기", ["월 1회", "주 1회 (5거래일)", "2주 1회 (10거래일)", "3주 1회 (15거래일)"], index=0)

    with st.spinner('과거 데이터를 분석 중입니다...'):
        df, logs, tickers = load_amls_backtest_data(BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL, MONTHLY_CONTRIBUTION, REBAL_FREQ)
    
    def calc_metrics(series, invested_series):
        final_val = series.iloc[-1]; total_inv = invested_series.iloc[-1]
        total_ret = (final_val / total_inv) - 1
        days = (series.index[-1] - series.index[0]).days
        cagr = (final_val / invested_series.iloc[-1]) ** (365.25 / days) - 1 if days > 0 else 0
        mdd = ((series / series.cummax()) - 1).min()
        daily_ret = series.pct_change().dropna()
        sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252)) if daily_ret.std() != 0 else 0
        return final_val, total_ret, cagr, mdd, sharpe

    strats = ['AMLS v4.3', 'QQQ', 'QLD', 'TQQQ']
    metrics_data = []
    for s in strats:
        fv, tr, cagr, mdd, shp = calc_metrics(df[f'{s}_Value'], df['Invested'])
        metrics_data.append({"전략": s, "최종 금액": f"${fv:,.0f}", "수익률": f"{tr*100:+.1f}%", "CAGR": f"{cagr*100:.1f}%", "MDD": f"{mdd*100:.1f}%", "샤프": f"{shp:.2f}"})
    metrics_df = pd.DataFrame(metrics_data).set_index("전략")

    tab1, tab2, tab3 = st.tabs(["📊 요약", "📈 성장 곡선", "📝 매매 로그"])

    with tab1:
        st.markdown("#### 🏆 성과 요약")
        st.info(f"투입 원금: ${df['Invested'].iloc[-1]:,.0f}")
        st.dataframe(metrics_df, use_container_width=True)

        st.markdown("#### 🥧 국면별 비중")
        c1, c2, c3, c4 = st.columns(4)
        def get_w(reg):
            if reg == 1: return {'TQQQ':30, 'SOXL/USD':20, 'QLD':20, 'SSO':15, 'GLD':10, 'CASH':5}
            elif reg == 2: return {'QLD':30, 'SSO':25, 'GLD':20, 'USD':10, 'QQQ':5, 'CASH':10}
            elif reg == 3: return {'GLD':50, 'CASH':35, 'QQQ':15}
            elif reg == 4: return {'GLD':50, 'CASH':40, 'QQQ':10}
        
        for i, col in enumerate([c1, c2, c3, c4]):
            r = i+1; w = {k:v for k,v in get_w(r).items() if v>0}
            fig_p = go.Figure(go.Pie(labels=list(w.keys()), values=list(w.values()), hole=0.5, marker=dict(colors=[COLOR_PALETTE.get(k.split('/')[0], '#888') for k in w.keys()])))
            cust_p = THEME_LAYOUT.copy(); cust_p.update(title=f"R{r}", title_x=0.5, height=250, margin=dict(t=40,b=10,l=10,r=10), showlegend=False)
            fig_p.update_layout(**cust_p)
            fig_p.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color=TEXT_COLOR, size=11))
            col.plotly_chart(fig_p, use_container_width=True)

    with tab2:
        st.markdown("#### 📈 자산 곡선")
        use_log = st.checkbox("Y축 로그 스케일", value=False)
        fig_eq = go.Figure()
        
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['AMLS v4.3_Value'], name='AMLS v4.3', line=dict(color=C_UP, width=3)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['QQQ_Value'], name='QQQ', line=dict(color=C_SAFE, width=1.5)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['TQQQ_Value'], name='TQQQ', line=dict(color=C_DOWN, width=1.5)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['Invested'], name='원금', line=dict(color='#888', width=1.5, dash='dot')))
        
        if use_log: fig_eq.update_yaxes(type="log")
        cust_eq = THEME_LAYOUT.copy(); cust_eq.update(height=450, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_eq.update_layout(**cust_eq)
        st.plotly_chart(fig_eq, use_container_width=True)

    with tab3:
        st.markdown("#### 📝 매매 로그")
        log_df = pd.DataFrame(logs)[::-1]
        if not log_df.empty:
            log_df['평가액'] = log_df['평가액'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(log_df, hide_index=True, use_container_width=True, height=400)


# =====================================================================
# [4] 페이지 구성: 내 포트폴리오 관리 (요약 패널 + HTML 띄어쓰기 완전 제거)
# =====================================================================
def make_portfolio_page(acc_name):
    def page_func():
        st.title(f"💼 {acc_name}")
        
        curr_acc_data = st.session_state['accounts'][acc_name]
        pf_df = pd.DataFrame(curr_acc_data["portfolio"])
        for col in ["수량 (주/달러)", "평균 단가 ($)", "매입 환율"]:
            if col in pf_df.columns: pf_df[col] = pf_df[col].astype(float)

        @st.cache_data(ttl=1800)
        def get_market_status():
            TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']
            data = yf.download(TICKERS, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill()
            today = data.iloc[-1]; yesterday = data.iloc[-2]
            ma200 = data['QQQ'].rolling(200).mean().iloc[-1]
            ma50 = data['QQQ'].rolling(50).mean().iloc[-1]
            smh_ma50 = data['SMH'].rolling(50).mean().iloc[-1]
            smh_3m_ret = (data['SMH'].iloc[-1] / data['SMH'].iloc[-63]) - 1
            smh_rsi = ta.rsi(data['SMH'], length=14).iloc[-1]
            
            if today['^VIX'] > 40: reg = 4
            elif today['QQQ'] < ma200: reg = 3
            elif today['QQQ'] >= ma200 and ma50 >= ma200 and today['^VIX'] < 25: reg = 1
            else: reg = 2

            try:
                fx_data = yf.download('USDKRW=X', period='5d', progress=False)['Close'].ffill()
                current_usdkrw = float(fx_data.iloc[:, 0].iloc[-1] if isinstance(fx_data, pd.DataFrame) else fx_data.iloc[-1])
            except: current_usdkrw = 0.0

            ma200_s = data['QQQ'].rolling(200).mean(); ma50_s = data['QQQ'].rolling(50).mean()
            regime_series = []
            for i in range(len(data)):
                v = data['^VIX'].iloc[i]; q = data['QQQ'].iloc[i]; m200 = ma200_s.iloc[i]; m50 = ma50_s.iloc[i]
                if pd.isna(m200): regime_series.append(2); continue
                if v > 40: regime_series.append(4)
                elif q < m200: regime_series.append(3)
                elif q >= m200 and m50 >= m200 and v < 25: regime_series.append(1)
                else: regime_series.append(2)

            current_reg = regime_series[-1]; regime_duration = 0
            for i in range(len(regime_series)-1, -1, -1):
                if regime_series[i] == current_reg: regime_duration += 1
                else: break

            prev_reg = current_reg
            for i in range(len(regime_series)-regime_duration-1, -1, -1):
                prev_reg = regime_series[i]; break

            if current_reg < prev_reg: regime_direction = "ASCENDING"
            elif current_reg > prev_reg: regime_direction = "DESCENDING"
            else: regime_direction = "STABLE"

            if regime_direction == "ASCENDING": entry_grade = "최적 진입" if regime_duration <= 30 else "주의(전환)"
            elif regime_direction == "DESCENDING": entry_grade = "진입 보류" if regime_duration <= 20 else "바닥 탐색"
            else: entry_grade = "진입 적합"

            return {
                'regime': reg, 'vix': today['^VIX'], 'qqq': today['QQQ'], 'ma200': ma200, 'ma50': ma50,
                'smh': today['SMH'], 'smh_ma50': smh_ma50, 'smh_3m_ret': smh_3m_ret, 'smh_rsi': smh_rsi,
                'prices': today.to_dict(), 'prev_prices': yesterday.to_dict(), 'date': data.index[-1],
                'usdkrw': current_usdkrw, 'regime_duration': regime_duration, 'prev_regime': prev_reg,
                'regime_direction': regime_direction, 'entry_grade': entry_grade
            }

        @st.cache_data(ttl=60)
        def get_realtime_prices():
            RT_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
            try:
                rt = yf.download(RT_TICKERS, period='1d', interval='5m', prepost=True, progress=False)['Close']
                if rt.empty: return None
                return rt.ffill().iloc[-1].to_dict()
            except: return None

        with st.spinner("AI 엔진 동기화 중..."): 
            ms = get_market_status()
            rt_prices = get_realtime_prices()

        if rt_prices:
            for k, v in rt_prices.items():
                if k in ms['prices'] and pd.notna(v): ms['prices'][k] = v
            if pd.notna(rt_prices.get('^VIX', None)): ms['vix'] = rt_prices['^VIX']
            if pd.notna(rt_prices.get('QQQ', None)): ms['qqq'] = rt_prices['QQQ']
            if pd.notna(rt_prices.get('SMH', None)): ms['smh'] = rt_prices['SMH']
            if pd.notna(rt_prices.get('USDKRW=X', None)): ms['usdkrw'] = rt_prices['USDKRW=X']
            vix_rt, qqq_rt = ms['vix'], ms['qqq']
            if vix_rt > 40: ms['regime'] = 4
            elif qqq_rt < ms['ma200']: ms['regime'] = 3
            elif qqq_rt >= ms['ma200'] and ms['ma50'] >= ms['ma200'] and vix_rt < 25: ms['regime'] = 1
            else: ms['regime'] = 2
            
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            et_hour = (now_utc.hour - 5) % 24 
            if 4 <= et_hour < 9.5: price_label = "Pre"
            elif 9.5 <= et_hour < 16: price_label = "Live"
            elif 16 <= et_hour < 20: price_label = "After"
            else: price_label = "Live"
        else: price_label = "Close"

        live_prices = {k: ms['prices'].get(k, 1.0) for k in REQUIRED_TICKERS}; live_prices['CASH'] = 1.0
        prev_prices = {k: ms['prev_prices'].get(k, live_prices[k]) for k in REQUIRED_TICKERS}; prev_prices['CASH'] = 1.0
        current_usdkrw = ms['usdkrw']
        
        disp_df = pf_df.copy()
        disp_df["현재가 ($)"] = disp_df["티커 (Ticker)"].apply(lambda x: live_prices.get(x, 0.0))
        disp_df["현재 환율"] = current_usdkrw
        
        def cy(row):
            if row["수량 (주/달러)"] == 0 or row["평균 단가 ($)"] == 0 or row["티커 (Ticker)"] == "CASH": return 0.0
            return (row["현재가 ($)"] - row["평균 단가 ($)"]) / row["평균 단가 ($)"] * 100
        disp_df["수익률 (%)"] = disp_df.apply(cy, axis=1)
        
        def cy_krw(row):
            if row["수량 (주/달러)"] == 0 or row["평균 단가 ($)"] == 0 or row["티커 (Ticker)"] == "CASH": return 0.0
            if row["매입 환율"] <= 0 or current_usdkrw <= 0: return 0.0
            buy_krw = row["평균 단가 ($)"] * row["매입 환율"]; now_krw = row["현재가 ($)"] * current_usdkrw
            return (now_krw - buy_krw) / buy_krw * 100
        disp_df["원화 수익률 (%)"] = disp_df.apply(cy_krw, axis=1)

        total_val_now = 0.0; total_val_yest = 0.0; auto_seed = 0.0
        best_ticker = "-"; best_ret = -999.0
        asset_vals = {}
        
        for _, row in disp_df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            qty = float(row["수량 (주/달러)"] if pd.notna(row["수량 (주/달러)"]) else 0)
            avg_p = float(row["평균 단가 ($)"] if pd.notna(row["평균 단가 ($)"]) else 0)
            
            v_now = qty * live_prices.get(tkr, 0.0) if tkr != "CASH" else qty
            v_yest = qty * prev_prices.get(tkr, 0.0) if tkr != "CASH" else qty
            
            if v_now > 0: asset_vals[tkr] = v_now
            if qty > 0:
                total_val_now += v_now
                total_val_yest += v_yest
                auto_seed += qty if tkr == "CASH" else qty * avg_p
                r_ret = row["수익률 (%)"]
                if tkr != "CASH" and r_ret > best_ret: best_ret = r_ret; best_ticker = tkr

        daily_diff = total_val_now - total_val_yest
        daily_diff_pct = (daily_diff / total_val_yest * 100) if total_val_yest > 0 else 0.0

        st.session_state['accounts'][acc_name]["target_seed"] = auto_seed
        rebal_base = total_val_now if total_val_now > 0 else auto_seed

        today_str = datetime.now().strftime("%Y-%m-%d")
        history_changed = False
        last_seed = curr_acc_data["seed_history"].get(today_str, {}).get("seed")
        last_equity = curr_acc_data["seed_history"].get(today_str, {}).get("equity")
        if total_val_now > 0 or auto_seed > 0:
            if last_seed != auto_seed or last_equity != total_val_now:
                curr_acc_data["seed_history"][today_str] = {"seed": auto_seed, "equity": total_val_now}
                history_changed = True
        if history_changed: save_accounts_data(st.session_state['accounts'])


        # ------------------- 0. 달성률 바 -------------------
        target_val = curr_acc_data.get("target_portfolio_value", 100000.0)
        progress_pct = (total_val_now / target_val) * 100 if target_val > 0 else 0.0
        
        c_prog, c_set = st.columns([4, 1.2])
        with c_set:
            new_target = st.number_input("목표 금액 설정", min_value=0.0, value=float(target_val), step=10000.0, format="%.0f")
            if new_target != target_val:
                st.session_state['accounts'][acc_name]["target_portfolio_value"] = new_target
                save_accounts_data(st.session_state['accounts'])
                st.rerun()
                
        with c_prog:
            st.markdown(f"""<div style='background:rgba(255,255,255,0.1); padding:15px; border-radius:12px; border:1px solid rgba(150,150,150,0.2);'>
<div style='display:flex; justify-content:space-between; margin-bottom:8px; font-weight:bold; font-size:1.05rem;'>
<span>현재: ${total_val_now:,.0f}</span>
<span style='color:{C_DOWN};'>목표: ${target_val:,.0f}</span>
</div>
<div style='background-color:rgba(0,0,0,0.1); border-radius:8px; height:16px; width:100%; position:relative; overflow:hidden;'>
<div style='background-color:{C_UP}; width:{min(100.0, progress_pct)}%; height:100%; border-radius:8px;'></div>
</div>
<div style='text-align:right; margin-top:5px; font-weight:bold;'>{progress_pct:.2f}%</div>
</div>""", unsafe_allow_html=True)
            
        st.write("")

        # ------------------- 1. 상단 요약 (검은색 텍스트 강제 적용) -------------------
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div style='background:rgba(255,255,255,0.2); border-radius:12px; padding:15px; border:1px solid rgba(150,150,150,0.2); text-align:center;'>
<div style='color:#000000; font-size:0.85rem; font-weight:bold;'>💰 총 평가액 (Total)</div>
<div style='color:#000000; font-size:1.6rem; font-weight:bold; margin-top:5px;'>${total_val_now:,.0f}</div>
</div>""", unsafe_allow_html=True)
        with m2:
            pn_col = "#000000"
            pn_ico = "▲" if daily_diff > 0 else ("▼" if daily_diff < 0 else "-")
            st.markdown(f"""<div style='background:rgba(255,255,255,0.2); border-radius:12px; padding:15px; border:1px solid rgba(150,150,150,0.2); text-align:center;'>
<div style='color:#000000; font-size:0.85rem; font-weight:bold;'>일간 손익 (Daily)</div>
<div style='color:#000000; font-size:1.6rem; font-weight:bold; margin-top:5px;'>{pn_ico} {abs(daily_diff_pct):.2f}%</div>
<div style='color:#000000; font-size:0.8rem;'>({daily_diff:+.0f} $)</div>
</div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div style='background:rgba(255,255,255,0.2); border-radius:12px; padding:15px; border:1px solid rgba(150,150,150,0.2); text-align:center;'>
<div style='color:#000000; font-size:0.85rem; font-weight:bold;'>👑 포트폴리오 MVP</div>
<div style='color:#000000; font-size:1.6rem; font-weight:bold; margin-top:5px;'>{best_ticker}</div>
<div style='color:#000000; font-size:0.8rem; font-weight:bold;'>수익률 {best_ret:+.1f}%</div>
</div>""", unsafe_allow_html=True)
        with m4:
            app_reg = ms['regime']
            st.markdown(f"""<div style='background:rgba(255,255,255,0.2); border-radius:12px; padding:15px; border:1px solid rgba(150,150,150,0.2); text-align:center;'>
<div style='color:#000000; font-size:0.85rem; font-weight:bold;'>AI 전략 국면</div>
<div style='color:#000000; font-size:1.6rem; font-weight:bold; margin-top:5px;'>Regime {app_reg}</div>
<div style='color:#000000; font-size:0.8rem; font-weight:bold;'>{ms['entry_grade'].split('(')[0].strip()}</div>
</div>""", unsafe_allow_html=True)
            
        st.write("")
        
        # ------------------- 2. 공간 절약형 슬림 패널 (판독기+분석관+가이드) -------------------
        c_s = C_UP if ms['smh'] > ms['smh_ma50'] else C_DOWN
        c_r = C_UP if ms['smh_3m_ret'] > 0.05 else C_DOWN
        c_rsi = C_UP if ms['smh_rsi'] > 50 else C_DOWN
        
        if app_reg == 1: badge_bg = C_UP; badge_txt = "R1 (강세)"; r_desc = f"VIX({ms['vix']:.1f}) & 정배열. 3X 확대."
        elif app_reg == 2: badge_bg = C_WARN; badge_txt = "R2 (조정)"; r_desc = f"모멘텀 약화. 2X 축소."
        elif app_reg == 3: badge_bg = C_DOWN; badge_txt = "R3 (약세)"; r_desc = f"QQQ 200MA 붕괴. 방어(GLD 50%)."
        else: badge_bg = C_DOWN; badge_txt = "R4 (위기)"; r_desc = f"VIX({ms['vix']:.1f}) 패닉. 즉시 현금화."

        entry_txt = ms['entry_grade']
        dot_c = C_UP if "최적" in entry_txt or "적합" in entry_txt else (C_WARN if "주의" in entry_txt or "탐색" in entry_txt else C_DOWN)
        dir_map = {"ascending": "상향", "descending": "하향", "stable": "유지"}
        direction_kr = dir_map.get(ms['regime_direction'], "-")

        # HTML 블록 띄어쓰기 전부 제거 (마크다운 버그 원천 차단)
        st.markdown(f"""<div style='display:flex; gap:10px; margin-bottom:20px; align-items:stretch;'>
<div style='flex:1; background:rgba(255,255,255,0.2); padding:12px; border-radius:12px; border:1px solid rgba(150,150,150,0.2);'>
<div style='font-size:0.8rem; font-weight:bold; color:#000000; margin-bottom:8px;'>⚡ SOXL 판독기</div>
<div style='display:flex; gap:6px;'>
<span style='background:{c_s}; color:#fff; font-size:0.7rem; font-weight:bold; padding:2px 6px; border-radius:4px;'>50MA</span>
<span style='background:{c_r}; color:#fff; font-size:0.7rem; font-weight:bold; padding:2px 6px; border-radius:4px;'>3M</span>
<span style='background:{c_rsi}; color:#fff; font-size:0.7rem; font-weight:bold; padding:2px 6px; border-radius:4px;'>RSI</span>
</div>
</div>
<div style='flex:2; background:rgba(255,255,255,0.2); padding:12px; border-radius:12px; border:1px solid rgba(150,150,150,0.2);'>
<div style='font-size:0.8rem; font-weight:bold; color:#000000; margin-bottom:8px;'>🤖 AI 전략 분석관</div>
<div style='display:flex; align-items:center; gap:8px;'>
<span style='background:{badge_bg}; color:#fff; font-size:0.8rem; font-weight:bold; padding:2px 8px; border-radius:4px;'>{badge_txt}</span>
<span style='font-size:0.9rem; color:#000000;'>{r_desc}</span>
</div>
</div>
<div style='flex:1; background:rgba(255,255,255,0.2); padding:12px; border-radius:12px; border:1px solid rgba(150,150,150,0.2);'>
<div style='font-size:0.8rem; font-weight:bold; color:#000000; margin-bottom:8px;'>🌱 투입 가이드</div>
<div style='display:flex; align-items:center; gap:6px;'>
<div style='width:8px; height:8px; border-radius:50%; background-color:{dot_c};'></div>
<span style='font-size:0.95rem; font-weight:bold; color:#000000;'>{entry_txt.split('(')[0].strip()}</span>
</div>
<div style='font-size:0.75rem; color:#000000; margin-top:4px;'>방향: {direction_kr} | 체류: {ms['regime_duration']}일</div>
</div>
</div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ------------------- 데이터 테이블 -------------------
        st.markdown(f"#### 💼 포트폴리오 기입표")
        
        def color_y(val):
            if isinstance(val, (int, float)):
                if val > 0: return f'color: {C_UP}; font-weight: bold;'
                elif val < 0: return f'color: {C_DOWN}; font-weight: bold;'
            return ''

        ed_disp = st.data_editor(
            disp_df.style.map(color_y, subset=["수익률 (%)", "원화 수익률 (%)"]), 
            num_rows="dynamic", use_container_width=True, height=350,
            column_order=["태그", "티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "현재가 ($)", "수익률 (%)", "원화 수익률 (%)"],
            column_config={
                "태그": st.column_config.SelectboxColumn("CLASS", options=["코어", "위성", "헷지", "현금", "단기픽"], required=True),
                "티커 (Ticker)": st.column_config.TextColumn("TICKER"),
                "현재가 ($)": st.column_config.NumberColumn("PRICE", disabled=True, format="$ %.2f"),
                "현재 환율": st.column_config.NumberColumn("FX", disabled=True, format="₩ %.1f"),
                "수익률 (%)": st.column_config.NumberColumn("RET", disabled=True, format="%.2f %%"),
                "원화 수익률 (%)": st.column_config.NumberColumn("KRW RET", disabled=True, format="%.2f %%"),
                "매입 환율": st.column_config.NumberColumn("BUY FX", format="₩ %.1f"),
            }
        )
        base_cols = ["티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "태그"]
        if not ed_disp[base_cols].equals(pf_df[base_cols]):
            st.session_state['accounts'][acc_name]["portfolio"] = ed_disp[base_cols].to_dict(orient="records")
            save_accounts_data(st.session_state['accounts']); st.rerun()

        st.write("")

        # ------------------- 파이차트 & 리밸런싱 -------------------
        col_pie, col_act = st.columns([1, 1.3])
        
        with col_pie:
            st.markdown("#### 🍩 자산 배분 비중")
            with st.container(border=True):
                if total_val_now > 0:
                    fig = go.Figure(go.Pie(labels=list(asset_vals.keys()), values=list(asset_vals.values()), hole=0.6, marker=dict(colors=[COLOR_PALETTE.get(k, '#888') for k in asset_vals.keys()])))
                    cust_p2 = THEME_LAYOUT.copy()
                    cust_p2.update(height=300, showlegend=False, margin=dict(t=10, b=10, l=10, r=10), annotations=[dict(text=f"100%", x=0.5, y=0.5, showarrow=False, font=dict(color=TEXT_COLOR, size=16))])
                    fig.update_layout(**cust_p2)
                    fig.update_traces(textposition='inside', textinfo='percent+label', textfont_size=13, textfont_color="#fff" if current_theme=="1920년대 타자기 테마" else TEXT_COLOR)
                    st.plotly_chart(fig, use_container_width=True)

        with col_act:
            st.markdown("#### ⚖️ 리밸런싱 지침")
            with st.container(border=True):
                status_d = []
                smh_cond = (ms['smh'] > ms['smh_ma50']) and (ms['smh_3m_ret'] > 0.05) and (ms['smh_rsi'] > 50)
                def get_w_local(reg, usx):
                    w = {t: 0.0 for t in REQUIRED_TICKERS}; semi = 'SOXL' if usx else 'USD'
                    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['CASH'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
                    elif reg == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'], w['CASH'] = 0.30, 0.25, 0.20, 0.10, 0.05, 0.10
                    elif reg == 3: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
                    elif reg == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
                    return {k: v for k, v in w.items() if v > 0}
                    
                target_w_dict = get_w_local(ms['regime'], smh_cond)
                all_tkrs = set([t for t in asset_vals.keys()] + list(target_w_dict.keys()))
                for tkr in all_tkrs:
                    tkr = tkr.upper()
                    my_v = asset_vals.get(tkr, 0.0); my_w = (my_v / total_val_now * 100) if total_val_now > 0 else 0.0
                    tw = target_w_dict.get(tkr, 0.0); tv = rebal_base * tw; diff = tv - my_v; cp = live_prices.get(tkr, 0.0)
                    
                    if tkr != "CASH" and cp > 0:
                        shares_to_trade = abs(diff) / cp
                        if shares_to_trade < 1.0: action = "HOLD"
                        elif diff > 0: action = f"BUY {shares_to_trade:.0f}"
                        else: action = f"SELL {shares_to_trade:.0f}"
                    elif tkr == "CASH":
                        if abs(diff) < 50: action = "HOLD"
                        elif diff > 0: action = f"ADD ${diff:,.0f}"
                        else: action = f"WITHDRAW ${abs(diff):,.0f}"
                    else: action = "HOLD"
                    
                    if my_v > 0 or tw > 0: 
                        status_d.append({"TICKER": tkr, "TARGET": f"{tw*100:.1f}%", "ACTUAL": f"{my_w:.1f}%", "ACTION": action})
                        
                if status_d:
                    status_df = pd.DataFrame(status_d).sort_values("TARGET", ascending=False)
                    def color_act(val):
                        val_s = str(val)
                        if 'BUY' in val_s or 'ADD' in val_s: return f'color: {C_UP}; font-weight:bold;'
                        elif 'SELL' in val_s or 'WITHDRAW' in val_s: return f'color: {C_DOWN}; font-weight:bold;'
                        return ''
                    st.dataframe(status_df.style.map(color_act, subset=['ACTION']), use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("**📈 자산 성장 곡선**")
        
        hist_dict = curr_acc_data.get("seed_history", {})
        if hist_dict:
            with st.container(border=True):
                hist_df = pd.DataFrame.from_dict(hist_dict, orient='index')
                hist_df.index = pd.to_datetime(hist_df.index)
                hist_df = hist_df.sort_index()

                fed_str = curr_acc_data.get("first_entry_date")
                col_date, _ = st.columns([1, 3])
                with col_date:
                    default_date = pd.to_datetime(fed_str).date() if fed_str else (datetime.today() - timedelta(days=90)).date()
                    u_date = st.date_input("기준일 설정", value=default_date, key=f"date_{acc_name}")
                    if str(u_date) != str(fed_str)[:10]: 
                        st.session_state['accounts'][acc_name]["first_entry_date"] = str(u_date)
                        save_accounts_data(st.session_state['accounts'])
                
                try:
                    if fed_str:
                        fed_dt = pd.to_datetime(fed_str)
                        if fed_dt < hist_df.index[0]:
                            hist_df.loc[fed_dt] = {"seed": auto_seed, "equity": auto_seed}
                            hist_df = hist_df.sort_index()

                    hist_df = hist_df.resample('D').ffill()

                    fig_seed = go.Figure()
                    fig_seed.add_trace(go.Scatter(x=hist_df.index, y=hist_df['equity'], name="TOTAL EQUITY", line=dict(color=C_UP, width=3, shape='hv'), mode='lines'))
                    fig_seed.add_trace(go.Scatter(x=hist_df.index, y=hist_df['seed'], name="SEED", line=dict(color=C_DOWN, width=2, dash='dot', shape='hv'), mode='lines'))
                    
                    cust_s = THEME_LAYOUT.copy()
                    cust_s.update(height=350, hovermode="x unified", yaxis=dict(showgrid=True, autorange=True, rangemode="normal"))
                    fig_seed.update_layout(**cust_s)
                    st.plotly_chart(fig_seed, use_container_width=True)
                except Exception as e: pass

        st.write("")
        col_log1, col_log2 = st.columns([1.5, 1])
        with col_log1:
            st.markdown("**📝 매매 일지**")
            def save_j(): st.session_state['accounts'][acc_name]["journal_text"] = st.session_state[f"j_{acc_name}"]; save_accounts_data(st.session_state['accounts'])
            st.text_area("LOG...", value=curr_acc_data.get('journal_text', ''), key=f"j_{acc_name}", height=300, on_change=save_j, label_visibility="collapsed")
        with col_log2:
            st.markdown("**🔔 시스템 로그**")
            history = curr_acc_data.get('history', [])
            if history: st.dataframe(pd.DataFrame(history)[::-1], hide_index=True, use_container_width=True, height=300)

    page_func.__name__ = f"pf_{abs(hash(acc_name))}"
    return page_func


# --- 페이지 구성: 계좌 관리 ---
def page_manage_accounts():
    st.title("⚙️ 계좌 관리")
    new_acc = st.text_input("새 계좌명")
    if st.button("개설", type="primary") and new_acc:
        if new_acc not in st.session_state['accounts']:
            st.session_state['accounts'][new_acc] = {"portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS], "history": [{"Date": datetime.now().strftime("%Y-%m-%d"), "Log": "계좌 개설"}], "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0}
            save_accounts_data(st.session_state['accounts']); st.rerun()
    st.divider()
    for acc in list(st.session_state['accounts'].keys()):
        c1, c2 = st.columns([4, 1])
        c1.write(f"📁 **{acc}**")
        if c2.button("삭제", key=f"del_{acc}", disabled=len(st.session_state['accounts']) <=1):
            del st.session_state['accounts'][acc]; save_accounts_data(st.session_state['accounts']); st.rerun()

# --- 페이지 구성: 전략 명세서 ---
def page_strategy_specification():
    st.title("📜 전략 명세서")
    st.markdown("### 🏷️ 버전: v4.3")
    st.table(pd.DataFrame({"우선순위": ["1", "2", "3", "4"], "조건": ["VIX > 40", "QQQ < 200일선", "정배열 & VIX < 25", "그 외 조건"], "레짐": ["R4 (위기)", "R3 (약세)", "R1 (강세)", "R2 (보통)"]}))


# =====================================================================
# [5] 사이드바 (테마 변경 및 링크 - HTML 버그 완전 수정)
# =====================================================================

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 테마 설정")
theme_list = ["애플 테마", "1920년대 타자기 테마", "카페 테마", "2000년대 구글 감성 테마"]
selected_theme = st.sidebar.selectbox("테마를 선택하세요", theme_list, index=theme_list.index(current_theme))
if selected_theme != current_theme:
    st.session_state['settings']['theme'] = selected_theme
    save_settings(st.session_state['settings']); st.rerun()

st.sidebar.markdown("---")

# 띄어쓰기 전부 삭제하여 마크다운 버그 원천 차단
st.sidebar.markdown(f"<div style='font-size:1.1rem; font-weight:700; color:{TEXT_COLOR}; margin-bottom:10px;'>⭐ 즐겨찾기</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"""<div style="display:flex; flex-direction:column; gap:2px;">
<div style="font-size:0.8rem; font-weight:bold; margin-top:5px;">유튜브</div>
<a href="https://www.youtube.com/@JB_Insight" target="_blank" class="sidebar-link"><span>📊</span> JB 인사이트</a>
<a href="https://www.youtube.com/@odokgod" target="_blank" class="sidebar-link"><span>📻</span> 오독</a>
<a href="https://www.youtube.com/@TQQQCRAZY" target="_blank" class="sidebar-link"><span>🔥</span> TQQQ 미친놈</a>
<a href="https://www.youtube.com/@developmong" target="_blank" class="sidebar-link"><span>🐒</span> 디벨롭몽</a>
<div style="font-size:0.8rem; font-weight:bold; margin-top:15px;">차트 분석</div>
<a href="https://kr.investing.com/" target="_blank" class="sidebar-link"><span>🌍</span> 인베스팅닷컴</a>
<a href="https://kr.tradingview.com/" target="_blank" class="sidebar-link"><span>📉</span> 트레이딩뷰</a>
<div style="font-size:0.8rem; font-weight:bold; margin-top:15px;">AI 도우미</div>
<a href="https://claude.ai/" target="_blank" class="sidebar-link"><span>🧠</span> 클로드</a>
<a href="https://gemini.google.com/" target="_blank" class="sidebar-link"><span>✨</span> 제미나이</a>
</div>""", unsafe_allow_html=True)
st.sidebar.markdown("---")

with st.sidebar.expander("💾 백업 및 복구"):
    st.download_button("📥 백업 다운로드", data=json.dumps(st.session_state['accounts']), file_name="amls_backup.json")
    up_f = st.file_uploader("📤 복구 업로드", type=['json'])
    if up_f and st.button("⚠️ 복구 실행"):
        st.session_state['accounts'] = json.load(up_f)
        save_accounts_data(st.session_state['accounts']); st.rerun()

pages = {
    "시스템": [st.Page(page_market_dashboard, title="마켓 터미널", icon="🌐"), st.Page(page_amls_backtest, title="백테스트 엔진", icon="🦅")],
    "포트폴리오": [],
    "설정": [st.Page(page_strategy_specification, title="전략 명세서", icon="📜"), st.Page(page_manage_accounts, title="계좌 관리", icon="⚙️")]
}

for name in st.session_state['accounts'].keys():
    pages["포트폴리오"].append(st.Page(make_portfolio_page(name), title=name, icon="💼"))

pg = st.navigation(pages)
pg.run()
