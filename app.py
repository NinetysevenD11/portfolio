import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import json
import os
import requests
from io import StringIO
import random

warnings.filterwarnings('ignore')

# =====================================================================
# [0] 시스템 설정 및 데이터 관리
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 포트폴리오", layout="wide", initial_sidebar_state="expanded")

SETTINGS_FILE = "amls_settings_v12.json"
ACCOUNTS_FILE = "amls_multi_accounts.json"
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "SPY", "GLD", "CASH"]

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

if 'settings' not in st.session_state:
    st.session_state['settings'] = load_settings()

if 'accounts' not in st.session_state:
    loaded = load_accounts_data()
    if not loaded:
        loaded = {
            "AMLS v4.4": {  
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0,
                "layout_order": ["🎯 목표 달성률", "📊 계좌 요약", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
            }
        }
    st.session_state['accounts'] = loaded

needs_save = False
if "기본 계좌 (AMLS)" in st.session_state['accounts']:
    st.session_state['accounts']["AMLS v4.4"] = st.session_state['accounts'].pop("기본 계좌 (AMLS)")
    needs_save = True
if "AMLS v4.3" in st.session_state['accounts']:
    st.session_state['accounts']["AMLS v4.4"] = st.session_state['accounts'].pop("AMLS v4.3")
    needs_save = True

for acc_name, acc_data in st.session_state['accounts'].items():
    if "seed_history" not in acc_data: acc_data["seed_history"] = {}; needs_save = True
    if "target_portfolio_value" not in acc_data: acc_data["target_portfolio_value"] = 100000.0; needs_save = True
    
    curr_layout = acc_data.get("layout_order", [])
    for old_item in ["⚡ 시스템 분석관", "🔍 레짐 판단 근거"]:
        if old_item in curr_layout: curr_layout.remove(old_item); needs_save = True
    if "📊 실시간 요약" in curr_layout: 
        curr_layout[curr_layout.index("📊 실시간 요약")] = "📊 계좌 요약"; needs_save = True
    
    if not curr_layout:
        acc_data["layout_order"] = ["🎯 목표 달성률", "📊 계좌 요약", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
        needs_save = True
    else:
        acc_data["layout_order"] = curr_layout

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
# [2] 동적 테마 및 레이아웃 설정
# =====================================================================
current_theme = st.session_state['settings'].get("theme", "애플 테마")
theme_list = ["애플 테마", "1930년대 타자기 테마", "월스트리트 저널 테마", "엑셀 테마"]

if current_theme not in theme_list:
    current_theme = "애플 테마"

if current_theme == "애플 테마":
    DEFAULT_TEXT_COLOR = "#1d1d1f"; TEXT_SUB = "#8e8e93"
    PANEL_BG = "rgba(255, 255, 255, 0.7)"; PANEL_BORDER = "1px solid rgba(200, 200, 200, 0.3)"; PANEL_RADIUS = "16px"
    WIDGET_THEME = "light"
    C_UP = "#34c759"; C_DOWN = "#ff3b30"; C_WARN = "#ff9500"; C_SAFE = "#007aff"
    BASE_CHART_COLORS = {'TQQQ':'#ff3b30', 'SOXL':'#af52de', 'USD':'#5856d6', 'QLD':'#ff9500', 'SSO':'#ffcc00', 'QQQ':'#007aff', 'SPY':'#34a853', 'GLD':'#34c759', 'BTC-USD':'#f7931a', 'CASH':'#8e8e93'}

elif current_theme == "1930년대 타자기 테마":
    DEFAULT_TEXT_COLOR = "#2c2a25"; TEXT_SUB = "#555555"
    PANEL_BG = "rgba(223, 215, 197, 0.85)"; PANEL_BORDER = "2px solid #2c2a25"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#000080"; C_DOWN = "#8b0000"; C_WARN = "#b8860b"; C_SAFE = "#006400"
    BASE_CHART_COLORS = {'TQQQ':'#8b0000', 'SOXL':'#556b2f', 'USD':'#8fbc8f', 'QLD':'#b8860b', 'SSO':'#cd853f', 'QQQ':'#000080', 'SPY':'#2e8b57', 'GLD':'#daa520', 'BTC-USD':'#f7931a', 'CASH':'#2f4f4f'}

elif current_theme == "월스트리트 저널 테마":
    DEFAULT_TEXT_COLOR = "#1A1A1A"; TEXT_SUB = "#555555"
    PANEL_BG = "rgba(255, 255, 255, 0.95)"; PANEL_BORDER = "1px solid #000000"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#006400"; C_DOWN = "#8B0000"; C_WARN = "#B8860B"; C_SAFE = "#000080"
    BASE_CHART_COLORS = {'TQQQ':'#8B0000', 'SOXL':'#556b2f', 'USD':'#2F4F4F', 'QLD':'#B8860B', 'SSO':'#DAA520', 'QQQ':'#000080', 'SPY':'#4682B4', 'GLD':'#BDB76B', 'BTC-USD':'#f7931a', 'CASH':'#696969'}

elif current_theme == "엑셀 테마":
    DEFAULT_TEXT_COLOR = "#333333"; TEXT_SUB = "#666666"
    PANEL_BG = "rgba(255, 255, 255, 0.95)"; PANEL_BORDER = "1px solid #D4D4D4"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#107C41"; C_DOWN = "#C00000"; C_WARN = "#FFB900"; C_SAFE = "#0078D4"
    BASE_CHART_COLORS = {'TQQQ':'#C00000', 'SOXL':'#800080', 'USD':'#0078D4', 'QLD':'#FFB900', 'SSO':'#E36C09', 'QQQ':'#0078D4', 'SPY':'#107C41', 'GLD':'#FFC000', 'BTC-USD':'#f7931a', 'CASH':'#7F7F7F'}


if "last_theme" not in st.session_state['settings'] or st.session_state['settings']["last_theme"] != current_theme:
    st.session_state['settings']["text_color"] = DEFAULT_TEXT_COLOR
    st.session_state['settings']["last_theme"] = current_theme
    save_settings(st.session_state['settings'])

if "text_color" not in st.session_state['settings']: st.session_state['settings']["text_color"] = DEFAULT_TEXT_COLOR
if "chart_colors" not in st.session_state['settings']: st.session_state['settings']["chart_colors"] = BASE_CHART_COLORS.copy()
for tkr in REQUIRED_TICKERS + ['BTC-USD']:
    if tkr not in st.session_state['settings']["chart_colors"]:
        st.session_state['settings']["chart_colors"][tkr] = BASE_CHART_COLORS.get(tkr, "#888888")

TEXT_COLOR = st.session_state['settings']["text_color"]
COLOR_PALETTE = st.session_state['settings']["chart_colors"]

THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0))

def apply_custom_css():
    css_base = ""
    # height: 100% 제거하고 min-height 적용 (글씨 잘림 방지)
    css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; min-height: 100%; height: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.03); backdrop-filter: blur(10px); word-wrap: break-word; }}"
    
    if current_theme == "애플 테마":
        css_base = f"""
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        .stApp {{ background-color: #f5f5f7; background-image: radial-gradient(circle at top right, #e2e2e5 0%, #f5f5f7 40%, #e8e8ed 100%); font-family: 'Pretendard', -apple-system, sans-serif; color: {TEXT_COLOR}; letter-spacing: -0.01em; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background: {PANEL_BG}; backdrop-filter: blur(20px); border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.05); padding: 1.5rem; height: 100%; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none !important; color: {TEXT_COLOR}; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.05); transform: translateX(2px); }}
        """
    elif current_theme == "1930년대 타자기 테마":
        css_base = f"""
        @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp {{ font-family: 'Special Elite', 'Courier New', monospace !important; color: {TEXT_COLOR} !important; background-color: #e4dccc; background-image: url('https://www.transparenttextures.com/patterns/old-wall.png'); }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-radius: {PANEL_RADIUS} !important; box-shadow: 4px 4px 0px {TEXT_COLOR} !important; padding: 1.5rem !important; height: 100%; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 0px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: bold; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.1); border: 1px dashed {TEXT_COLOR}; }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; min-height: 100%; height: auto; box-shadow: 4px 4px 0px {TEXT_COLOR}; }}"
    elif current_theme == "월스트리트 저널 테마":
        css_base = f"""
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap');
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp {{ font-family: 'Playfair Display', serif; color: {TEXT_COLOR}; background-color: #F4F4F0; background-image: repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.02) 2px, rgba(0,0,0,0.02) 4px); }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background-color: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 1.5rem; box-shadow: 3px 3px 0px rgba(0,0,0,0.1); border-top: 4px solid #000000; height: 100%; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; text-decoration: none !important; color: #000000 !important; font-weight: bold; font-size: 0.95rem; border-bottom: 1px dotted #CCC; }}
        .sidebar-link:hover {{ background-color: #DDDDDD; }}
        """
    elif current_theme == "엑셀 테마":
        css_base = f"""
        .stApp {{ font-family: 'Calibri', 'Malgun Gothic', sans-serif; color: {TEXT_COLOR} !important; background-color: #F3F2F1; background-image: linear-gradient(#e1dfdd 1px, transparent 1px), linear-gradient(90deg, #e1dfdd 1px, transparent 1px); background-size: 20px 20px; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background-color: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-top: 3px solid #107C41 !important; border-radius: {PANEL_RADIUS} !important; padding: 1.5rem !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; height: 100%; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px; text-decoration: none !important; color: #0078D4 !important; font-family: 'Calibri', sans-serif; font-size: 0.95rem; border-bottom: 1px solid transparent; }}
        .sidebar-link:hover {{ border-bottom: 1px solid #0078D4; background-color: rgba(0,0,0,0.05); }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-top: 3px solid #107C41 !important; border-radius: {PANEL_RADIUS}; padding: 16px; min-height: 100%; height: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}"

    st.markdown(f"""
    <style>
    {css_base}
    div[data-testid="stMetricValue"] > div, div[data-testid="stMetricDelta"] > div, p, span, label, .stMarkdown {{ white-space: normal !important; word-break: keep-all !important; overflow-wrap: break-word !important; }}
    div[data-testid="stMetricValue"] {{ font-weight: bold; font-size: 1.8rem; color: {TEXT_COLOR}; }}
    .info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }}
    @media (max-width: 800px) {{ .info-grid {{ grid-template-columns: 1fr; }} }}
    {css_panel}
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()


# =====================================================================
# [3] 글로벌 백엔드 (AMLS v4.4 백테스트 엔진 + 무한매수 비교군 추가)
# =====================================================================
@st.cache_data(ttl=3600)
def load_amls_backtest_data(start, end, init_cap, monthly_cont, rebal_freq="월 1회", btc_ratio=0):
    tickers = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'BTC-USD']
    start_str = (start - timedelta(days=400)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    try: 
        data = yf.download(tickers, start=start_str, end=end_str, progress=False, auto_adjust=True)['Close']
        if data.empty: raise ValueError
    except: 
        try:
            data = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
            if data.empty: raise ValueError
        except:
            return pd.DataFrame(), [], []

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
    
    actual_regime_v4_4 = []; current_v4_4 = 3; pend_v4_4 = None; cnt_v4_4 = 0
    for i in range(len(df)):
        tr = df['Target_Regime'].iloc[i]
        if tr > current_v4_4: 
            current_v4_4 = tr; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
        elif tr < current_v4_4: 
            if tr == pend_v4_4:
                cnt_v4_4 += 1
                if cnt_v4_4 >= 5: current_v4_4 = tr; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
                else: actual_regime_v4_4.append(current_v4_4 - 1)
            else: pend_v4_4 = tr; cnt_v4_4 = 1; actual_regime_v4_4.append(current_v4_4 - 1)
        else: pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)

    df['Signal_Regime_v4_4'] = pd.Series(actual_regime_v4_4, index=df.index).shift(1).bfill()

    def get_v4_4_weights(regime, use_soxl, b_ratio):
        w = {t: 0.0 for t in data.columns}; semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'], w['SPY'] = 0.30, 0.25, 0.25, 0.10, 0.05, 0.05
        elif regime == 3: w['GLD'], w['QQQ'] = 0.50, 0.15
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        
        if b_ratio > 0 and w['GLD'] > 0:
            btc_amt = w['GLD'] * (b_ratio / 100.0)
            w['GLD'] = w['GLD'] - btc_amt
            w['BTC-USD'] = btc_amt
        return w

    strategies = ['AMLS v4.4', 'QQQ', 'QLD', 'TQQQ', '무한매수(TQQQ)']
    ports = {s: init_cap for s in strategies if s != '무한매수(TQQQ)'}
    hists = {s: [init_cap] for s in ports.keys()}
    total_invested = init_cap
    weights_v4_4 = {t: 0.0 for t in data.columns}
    logs, days_since = [], 0

    inf_cash = init_cap
    inf_shares = 0.0
    inf_avg = 0.0
    inf_days = 0
    inf_chunk = init_cap / 40.0
    hists['무한매수(TQQQ)'] = [init_cap]

    for i in range(1, len(df)):
        today, yesterday = df.index[i], df.index[i-1]
        days_since += 1
        
        ret_v4_4 = sum(weights_v4_4[t] * daily_returns[t].iloc[i] for t in data.columns)
        ports['AMLS v4.4'] *= (1 + ret_v4_4)
        for s in ['QQQ', 'QLD', 'TQQQ']: ports[s] *= (1 + daily_returns[s].iloc[i])
        
        for t in data.columns:
            if ports['AMLS v4.4'] > 0: weights_v4_4[t] = weights_v4_4[t]*(1+daily_returns[t].iloc[i])/(1+ret_v4_4)
            
        if today.month != yesterday.month:
            for s in ports: ports[s] += monthly_cont
            total_invested += monthly_cont
            inf_cash += monthly_cont

        for s in ports: hists[s].append(ports[s])
        
        p_tqqq = data['TQQQ'].iloc[i]
        if inf_shares > 0:
            if p_tqqq >= inf_avg * 1.10:
                inf_cash += inf_shares * p_tqqq
                inf_shares, inf_days = 0.0, 0
            elif inf_days >= 40:
                inf_cash += inf_shares * p_tqqq
                inf_shares, inf_days = 0.0, 0
                
        if inf_shares == 0:
            inf_chunk = (inf_cash) / 40.0
            if inf_chunk <= 0: inf_chunk = 0.0
            
        if inf_cash > 0:
            spend = inf_chunk if p_tqqq < inf_avg else inf_chunk * 0.5
            if inf_shares == 0: spend = inf_chunk
            if spend > inf_cash: spend = inf_cash
            
            buy_sh = spend / p_tqqq
            if inf_shares + buy_sh > 0:
                inf_avg = ((inf_shares * inf_avg) + spend) / (inf_shares + buy_sh)
            inf_shares += buy_sh
            inf_cash -= spend
            inf_days += 1
            
        hists['무한매수(TQQQ)'].append(inf_cash + inf_shares * p_tqqq)
        
        use_soxl = (df['SMH'].iloc[i-1] > df['SMH_MA50'].iloc[i-1]) and (df['SMH_3M_Ret'].iloc[i-1] > 0.05) and (df['SMH_RSI'].iloc[i-1] > 50)
        
        sig_r = df['Signal_Regime_v4_4'].iloc[i]
        rebal = False
        if sig_r != df['Signal_Regime_v4_4'].iloc[i-1] or i == 1: rebal = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal = True
        elif "주 1회" in rebal_freq and days_since >= 5: rebal = True
        elif "2주 1회" in rebal_freq and days_since >= 10: rebal = True
        elif "3주 1회" in rebal_freq and days_since >= 15: rebal = True
        
        if rebal:
            weights_v4_4 = get_v4_4_weights(sig_r, use_soxl, btc_ratio)
            log_type = "레짐 전환" if sig_r != df['Signal_Regime_v4_4'].iloc[i-1] else f"정기 ({rebal_freq.split(' ')[0]})"
            logs.append({"날짜": today.strftime('%Y-%m-%d'), "유형": log_type, "국면": f"R{int(sig_r)}", "평가액": ports['AMLS v4.4']})
            days_since = 0

    for s in strategies: df[f'{s}_Value'] = hists[s]
    inv_arr = [init_cap]; curr_inv = init_cap
    for i in range(1, len(df)):
        if df.index[i].month != df.index[i-1].month: curr_inv += monthly_cont
        inv_arr.append(curr_inv)
    df['Invested'] = inv_arr
    return df, logs, data.columns


# =====================================================================
# [4] 페이지 구성: 글로벌 마켓 대시보드
# =====================================================================
@st.cache_data(ttl=3600)
def get_dashboard_data():
    tickers = ['^GSPC', '^IXIC', '^VIX', 'USDKRW=X']
    try:
        df = yf.download(tickers, start=datetime.today()-timedelta(days=365), progress=False)['Close'].ffill()
        if df.empty: raise ValueError
        return df
    except:
        return pd.DataFrame()

def page_market_dashboard():
    st.title("🌐 매크로 터미널")
    
    components.html(f"""<div class="tradingview-widget-container" style="border-radius: {PANEL_RADIUS}; overflow: hidden; border: {PANEL_BORDER};">
<div class="tradingview-widget-container__widget"></div>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
{{
"symbols": [
{{"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"}},
{{"proName": "FOREXCOM:NSXUSD", "title": "NASDAQ 100"}},
{{"description": "TQQQ", "proName": "NASDAQ:TQQQ"}},
{{"description": "SOXL", "proName": "ARCA:SOXL"}},
{{"description": "USD/KRW", "proName": "FX_IDC:USDKRW"}},
{{"description": "GOLD", "proName": "OANDA:XAUUSD"}},
{{"description": "BITCOIN", "proName": "BINANCE:BTCUSD"}}
],
"showSymbolLogo": true, "colorTheme": "{WIDGET_THEME}", "locale": "kr"
}}
</script>
</div>""", height=70)

    col_left, col_right = st.columns([1, 1.8])
    with col_left:
        with st.container(border=True):
            st.markdown("##### 📈 주요 지수 및 시장 심리")
            indices_df = get_dashboard_data()
            
            if not indices_df.empty and len(indices_df) >= 2:
                c1, c2 = st.columns(2); latest = indices_df.iloc[-1]; prev = indices_df.iloc[-2]
                c1.metric("S&P 500", f"{latest.get('^GSPC', 0):,.0f}", f"{(latest.get('^GSPC',0)/prev.get('^GSPC',1)-1)*100:+.2f}%")
                c2.metric("NASDAQ", f"{latest.get('^IXIC', 0):,.0f}", f"{(latest.get('^IXIC',0)/prev.get('^IXIC',1)-1)*100:+.2f}%")
                c3, c4 = st.columns(2)
                c3.metric("VIX", f"{latest.get('^VIX', 0):,.2f}", f"{(latest.get('^VIX',0)/prev.get('^VIX',1)-1)*100:+.2f}%", delta_color="inverse")
                c4.metric("USD/KRW", f"₩{latest.get('USDKRW=X', 0):,.1f}", f"{(latest.get('USDKRW=X',0)/prev.get('USDKRW=X',1)-1)*100:+.2f}%", delta_color="inverse")
                
                vix_val = latest.get('^VIX', 20)
                fg_score = max(0, min(100, 100 - (vix_val - 10) * 2.5))
                st.markdown(f"**🧠 시장 공포 & 탐욕 지수:** `{'극심한 공포' if fg_score<25 else '공포' if fg_score<45 else '중립' if fg_score<55 else '탐욕' if fg_score<75 else '극심한 탐욕'}`")
                st.progress(fg_score / 100.0)
            else:
                st.warning("⚠️ 야후 파이낸스 서버 혼잡(Rate Limit)으로 지표를 불러오지 못했습니다. 잠시 후 다시 접속해 주세요.")

    with col_right:
        with st.container(border=True):
            st.markdown("##### 📉 장단기 금리차 (10Y - 2Y Yield Curve)")
            @st.cache_data(ttl=86400)
            def fetch_yield_curve():
                try:
                    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y"
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    res = requests.get(url, headers=headers, timeout=5)
                    if "<html" not in res.text[:100].lower():
                        return pd.read_csv(StringIO(res.text), parse_dates=['DATE'], index_col='DATE').replace('.', np.nan).astype(float).dropna()
                except: return None
            
            yc_data = fetch_yield_curve()
            if yc_data is not None and not yc_data.empty:
                yc_data = yc_data[yc_data.index > (datetime.today() - timedelta(days=365*5))]
                fig_yc = go.Figure()
                fig_yc.add_trace(go.Scatter(x=yc_data.index, y=yc_data['T10Y2Y'], fill='tozeroy', name="장단기 금리차", line=dict(color=C_WARN)))
                fig_yc.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="역전 기준선 (Recession Warning)")
                
                custom_yc = THEME_LAYOUT.copy()
                custom_yc.update(height=220)
                fig_yc.update_layout(**custom_yc)
                st.plotly_chart(fig_yc, use_container_width=True)
            else:
                st.info("장단기 금리차 데이터를 불러오는 중 오류가 발생했습니다. (FRED API 차단)")


# =====================================================================
# [5] 페이지 구성: AMLS 백테스트 (티어시트 + 월별 캘린더)
# =====================================================================
def page_amls_backtest():
    st.title("🦅 전략 시뮬레이터 (Tearsheet)")

    st.sidebar.header("⚙️ 시뮬레이션 설정")
    BACKTEST_START = st.sidebar.date_input("시작일", datetime(2018, 1, 1))
    BACKTEST_END = st.sidebar.date_input("종료일", datetime.today())
    INITIAL_CAPITAL = st.sidebar.number_input("초기 자본금 ($)", value=10000, step=1000)
    MONTHLY_CONTRIBUTION = st.sidebar.number_input("월 적립금 ($)", value=2000, step=500)
    REBAL_FREQ = st.sidebar.selectbox("🔄 리밸런싱 주기", ["월 1회", "주 1회 (5거래일)", "2주 1회 (10거래일)", "3주 1회 (15거래일)"], index=0)
    BTC_RATIO = st.sidebar.slider("🪙 비트코인 디지털 골드 편입비중 (금속 비중 내)", min_value=0, max_value=100, value=0, step=5, help="안전자산인 금(GLD) 비중 중 몇 %를 비트코인으로 대체할지 결정합니다.")

    with st.spinner('과거 데이터를 분석 중입니다...'):
        df, logs, tickers = load_amls_backtest_data(BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL, MONTHLY_CONTRIBUTION, REBAL_FREQ, BTC_RATIO)
    
    if df.empty:
        st.error("⚠️ 야후 파이낸스 서버 혼잡(Rate Limit)으로 시뮬레이션 데이터를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.")
        return

    def calc_metrics(series, invested_series):
        final_val = series.iloc[-1]; total_inv = invested_series.iloc[-1]
        total_ret = (final_val / total_inv) - 1
        days = (series.index[-1] - series.index[0]).days
        cagr = (final_val / invested_series.iloc[-1]) ** (365.25 / days) - 1 if days > 0 else 0
        mdd = ((series / series.cummax()) - 1).min()
        daily_ret = series.pct_change().dropna()
        sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252)) if daily_ret.std() != 0 else 0
        return final_val, total_ret, cagr, mdd, sharpe

    strats = ['AMLS v4.4', 'QQQ', 'QLD', 'TQQQ', '무한매수(TQQQ)']
    metrics_data = []
    for s in strats:
        fv, tr, cagr, mdd, shp = calc_metrics(df[f'{s}_Value'], df['Invested'])
        metrics_data.append({"전략": s, "최종 금액": f"${fv:,.0f}", "수익률": f"{tr*100:+.1f}%", "CAGR": f"{cagr*100:.1f}%", "MDD": f"{mdd*100:.1f}%", "샤프": f"{shp:.2f}"})
    metrics_df = pd.DataFrame(metrics_data).set_index("전략")

    tab1, tab2, tab3 = st.tabs(["📊 성과 비교 및 차트", "🗓️ 월별 수익률 히트맵", "📝 시스템 로그"])

    with tab1:
        st.markdown("#### 🏆 성과 요약")
        st.info(f"투입 원금: ${df['Invested'].iloc[-1]:,.0f} (BTC 편입비중: {BTC_RATIO}%)")
        st.dataframe(metrics_df, width="stretch")

        st.markdown("#### 📈 자산 곡선 및 낙폭 (MDD)")
        fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        for s in strats:
            color = C_UP if 'AMLS' in s else (C_SAFE if 'QQQ' in s else (C_WARN if 'QLD' in s else ('#8e44ad' if '무한매수' in s else C_DOWN)))
            fig_eq.add_trace(go.Scatter(x=df.index, y=df[f'{s}_Value'], name=s, line=dict(color=color, width=3 if 'AMLS' in s else 1.5)), row=1, col=1)
            dd = (df[f'{s}_Value'] / df[f'{s}_Value'].cummax() - 1) * 100
            fig_eq.add_trace(go.Scatter(x=df.index, y=dd, name=f'{s} DD', line=dict(color=color, width=1.5)), row=2, col=1)
        
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['Invested'], name='원금', line=dict(color='#888', dash='dot')), row=1, col=1)
        fig_eq.add_hline(y=-30, line_dash="dash", line_color="red", row=2, col=1)
        
        cust_eq = THEME_LAYOUT.copy()
        cust_eq.update(height=600, hovermode="x unified", margin=dict(l=0,r=0,t=20,b=0))
        fig_eq.update_layout(**cust_eq)
        fig_eq.update_yaxes(type="log", row=1, col=1)
        st.plotly_chart(fig_eq, use_container_width=True)

        st.markdown("#### 🥧 국면별 비중 (AMLS v4.4 기준)")
        c1, c2, c3, c4 = st.columns(4)
        def get_w(reg):
            if reg == 1: return {'TQQQ':30, 'SOXL/USD':20, 'QLD':20, 'SSO':15, 'GLD':10, 'SPY':5}
            elif reg == 2: return {'QLD':30, 'SSO':25, 'GLD':25, 'USD':10, 'QQQ':5, 'SPY':5}
            elif reg == 3: return {'GLD':50, 'CASH':35, 'QQQ':15}
            elif reg == 4: return {'GLD':50, 'CASH':40, 'QQQ':10}
        
        for i, col in enumerate([c1, c2, c3, c4]):
            r = i+1; w = {k:v for k,v in get_w(r).items() if v>0}
            fig_p = go.Figure(go.Pie(labels=list(w.keys()), values=list(w.values()), hole=0.5, marker=dict(colors=[COLOR_PALETTE.get(k.split('/')[0], '#888') for k in w.keys()])))
            cust_p = THEME_LAYOUT.copy(); cust_p.update(title=f"R{r}", title_x=0.5, height=250, margin=dict(t=40,b=10,l=10,r=10), showlegend=False)
            fig_p.update_layout(**cust_p)
            fig_p.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color="#ffffff" if current_theme in ["1930년대 타자기 테마", "월스트리트 저널 테마", "블룸버그 터미널 테마"] else TEXT_COLOR, size=11))
            col.plotly_chart(fig_p, use_container_width=True)


    with tab2:
        st.markdown("#### 🗓️ AMLS v4.4 월별 수익률 캘린더 (%)")
        monthly_df = df['AMLS v4.4_Value'].resample('M').last().pct_change() * 100
        monthly_df = monthly_df.dropna()
        
        heatmap_data = pd.DataFrame({'Year': monthly_df.index.year, 'Month': monthly_df.index.month, 'Return': monthly_df.values})
        pivot_data = heatmap_data.pivot(index='Year', columns='Month', values='Return').fillna(0).round(1)
        pivot_data.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot_data.columns)]
        
        fig_hm = px.imshow(pivot_data, text_auto=True, color_continuous_scale='RdYlGn', zmin=-15, zmax=15, aspect="auto")
        custom_hm = THEME_LAYOUT.copy()
        custom_hm.update(height=400)
        fig_hm.update_layout(**custom_hm)
        st.plotly_chart(fig_hm, use_container_width=True)

    with tab3:
        st.markdown("#### 📝 매매 로그")
        log_df = pd.DataFrame(logs)[::-1]
        if not log_df.empty:
            log_df['평가액'] = log_df['평가액'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(log_df, hide_index=True, width="stretch", height=500)


# =====================================================================
# [6] 페이지 구성: AI 시스템 분석관 (분리된 독립 페이지 + 트렌디 UI)
# =====================================================================
def page_ai_analyst():
    st.title("⚡ AI 시스템 분석관")
    mobile_mode = st.sidebar.checkbox("📱 모바일 간편뷰 모드", value=False, help="작은 화면에서 텍스트와 핵심 지표만 크게 봅니다.")
    
    @st.cache_data(ttl=1800)
    def get_market_status():
        TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
        try:
            data = yf.download(TICKERS, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill()
            if data.empty or len(data) < 200: raise ValueError
        except:
            return {
                'regime': 2, 'target_regime': 2, 'is_waiting': False, 'wait_days': 0,
                'regime_duration': 0, 'regime_direction': 'stable', 'entry_grade': '서버 점검중',
                'vix': 20.0, 'qqq': 400.0, 'ma200': 400.0, 'ma50': 400.0,
                'smh': 200.0, 'smh_ma50': 200.0, 'smh_3m_ret': 0.05, 'smh_rsi': 55.0,
                'prices': {t: 100.0 for t in TICKERS}, 'prev_prices': {t: 100.0 for t in TICKERS},
                'date': datetime.today(), 'usdkrw': 1350.0
            }

        today = data.iloc[-1]; yesterday = data.iloc[-2]
        
        ma200_s = data['QQQ'].rolling(200).mean()
        ma50_s = data['QQQ'].rolling(50).mean()
        smh_ma50_s = data['SMH'].rolling(50).mean()
        smh_3m_ret_s = data['SMH'].pct_change(63)
        smh_rsi_s = ta.rsi(data['SMH'], length=14)
        
        target_regimes = []
        for i in range(len(data)):
            v = data['^VIX'].iloc[i]; q = data['QQQ'].iloc[i]; m200 = ma200_s.iloc[i]; m50 = ma50_s.iloc[i]
            if pd.isna(m200): target_regimes.append(2); continue
            if v > 40: target_regimes.append(4)
            elif q < m200: target_regimes.append(3)
            elif q >= m200 and m50 >= m200 and v < 25: target_regimes.append(1)
            else: target_regimes.append(2)
            
        current_v4_4 = 3; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4 = []
        for tr in target_regimes:
            if tr > current_v4_4: 
                current_v4_4 = tr; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
            elif tr < current_v4_4:
                if tr == pend_v4_4:
                    cnt_v4_4 += 1
                    if cnt_v4_4 >= 5: current_v4_4 = tr; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
                    else: actual_regime_v4_4.append(current_v4_4 - 1)
                else: 
                    pend_v4_4 = tr; cnt_v4_4 = 1; actual_regime_v4_4.append(current_v4_4 - 1)
            else: 
                pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
                
        applied_series = pd.Series(actual_regime_v4_4, index=data.index).shift(1).bfill()
        applied_reg = int(applied_series.iloc[-1])
        target_reg = int(target_regimes[-1])
        is_waiting = (pend_v4_4 is not None and target_reg < current_v4_4)

        current_reg = applied_series.iloc[-1]
        regime_duration = 0
        for i in range(len(applied_series)-1, -1, -1):
            if applied_series.iloc[i] == current_reg: regime_duration += 1
            else: break
        
        prev_reg = current_reg
        search_start = len(applied_series) - regime_duration - 1
        if search_start >= 0:
            prev_reg = int(applied_series.iloc[search_start])

        if current_reg < prev_reg: regime_direction = "ascending"
        elif current_reg > prev_reg: regime_direction = "descending"
        else: regime_direction = "stable"

        if regime_direction == "ascending": entry_grade = "최적 진입" if regime_duration <= 30 else "주의(전환)"
        elif regime_direction == "descending": entry_grade = "진입 보류" if regime_duration <= 20 else "바닥 탐색"
        else: entry_grade = "진입 적합"

        try:
            current_usdkrw = float(today['USDKRW=X']) if pd.notna(today.get('USDKRW=X')) else 0.0
        except: current_usdkrw = 0.0

        return {
            'regime': applied_reg, 'target_regime': target_reg, 'is_waiting': is_waiting, 'wait_days': cnt_v4_4,
            'regime_duration': regime_duration, 'regime_direction': regime_direction, 'entry_grade': entry_grade,
            'vix': today['^VIX'], 'qqq': today['QQQ'], 'ma200': ma200_s.iloc[-1], 'ma50': ma50_s.iloc[-1],
            'smh': today['SMH'], 'smh_ma50': smh_ma50_s.iloc[-1], 'smh_3m_ret': smh_3m_ret_s.iloc[-1], 'smh_rsi': smh_rsi_s.iloc[-1],
            'prices': today.to_dict(), 'prev_prices': yesterday.to_dict(), 'date': data.index[-1], 'usdkrw': current_usdkrw
        }

    @st.cache_data(ttl=60)
    def get_realtime_prices():
        RT_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
        try:
            rt = yf.download(RT_TICKERS, period='1d', interval='5m', prepost=True, progress=False)['Close']
            if rt.empty: return None
            return rt.ffill().iloc[-1].to_dict()
        except: return None
        
    @st.cache_data(ttl=3600)
    def get_regime_chart_data():
        tkrs = ['QQQ', '^VIX']
        try:
            c_df = yf.download(tkrs, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill().dropna()
            c_df['MA50'] = c_df['QQQ'].rolling(50).mean()
            c_df['MA200'] = c_df['QQQ'].rolling(200).mean()
            return c_df.dropna().tail(252)
        except:
            return pd.DataFrame()

    with st.spinner("AI 엔진 동기화 중..."): 
        ms = get_market_status()
        rt_prices = get_realtime_prices()

    if rt_prices:
        for k, v in rt_prices.items():
            if k in ms['prices'] and pd.notna(v): ms['prices'][k] = v
        if pd.notna(rt_prices.get('^VIX', None)): ms['vix'] = rt_prices['^VIX']
        if pd.notna(rt_prices.get('QQQ', None)): ms['qqq'] = rt_prices['QQQ']
        if pd.notna(rt_prices.get('SMH', None)): ms['smh'] = rt_prices['SMH']
        
        vix_rt, qqq_rt = ms['vix'], ms['qqq']
        if vix_rt > 40: rt_tgt = 4
        elif qqq_rt < ms['ma200']: rt_tgt = 3
        elif qqq_rt >= ms['ma200'] and ms['ma50'] >= ms['ma200'] and vix_rt < 25: rt_tgt = 1
        else: rt_tgt = 2
        
        ms['target_regime'] = rt_tgt
        if rt_tgt > ms['regime']:
            ms['regime'] = rt_tgt
            ms['is_waiting'] = False

    app_reg = ms['regime']; tgt_reg = ms['target_regime']; is_wait = ms['is_waiting']; wait_d = ms['wait_days']; dur = ms['regime_duration']
    entry_g = ms['entry_grade']; direction = ms['regime_direction']
    vix_c = ms['vix']; qqq_c = ms['qqq']; ma200_c = ms['ma200']; smh_c = ms['smh']; smh_ma50_c = ms['smh_ma50']
    
    s_stat = "돌파" if smh_c > smh_ma50_c else "붕괴"
    r_stat = "통과" if ms['smh_3m_ret'] > 0.05 else "미달"
    rsi_stat = "통과" if ms['smh_rsi'] > 50 else "미달"
    soxl_res = "SOXL 편입 승인" if (smh_c > smh_ma50_c and ms['smh_3m_ret'] > 0.05 and ms['smh_rsi'] > 50) else "USD(2X) 방어 유지"

    if app_reg == 1:
        reg_t = "[R1: 완벽 강세장]"
        reg_d = f"VIX({vix_c:.1f}) 안정권 및 나스닥({qqq_c:.0f}) 정배열 유지. 하방 리스크가 제한적이므로 3배 레버리지를 가동해 상승분을 캡처하십시오."
    elif app_reg == 2:
        reg_t = "[R2: 조정/경계]"
        reg_d = f"장기 추세는 유효하나 VIX({vix_c:.1f})가 상승했거나 단기 모멘텀이 약화되었습니다. 과도한 레버리지를 2배수 이하로 축소하십시오."
    elif app_reg == 3:
        reg_t = "[R3: 장기 하락장]"
        reg_d = f"나스닥({qqq_c:.0f})이 200일선({ma200_c:.0f})을 하향 이탈했습니다. 하락 추세가 컨펌되었으니 레버리지 청산 후 GLD로 방어하십시오."
    else:
        reg_t = "[R4: 시스템 패닉]"
        reg_d = f"VIX({vix_c:.1f}) 40 돌파. 시장이 이성을 상실한 시스템 리스크 구간입니다. 주식을 전량 매도하고 안전자산으로 대피하십시오."

    dir_map = {"ascending": "상향 전환", "descending": "하향 전환", "stable": "현재 상태 유지"}
    dir_kr = dir_map.get(direction, "-")
    
    if direction == 'ascending' and dur <= 10: summ = "상향 전환 직후 골든타임. 진입 비중 확대를 적극 권장합니다."
    elif direction == 'ascending': summ = "상승 추세 안정화. 계획된 비중대로 편안하게 분할 매수하십시오."
    elif direction == 'descending' and dur <= 20: summ = "하향 전환 발생. 추가 하락 우려가 있으므로 신규 매수를 전면 보류하십시오."
    elif direction == 'descending': summ = "장기 하락 중. 완벽한 상승 신호가 뜰 때까지 현금을 대기하십시오."
    elif dur > 60: summ = "레짐 장기화로 추세 반전 리스크 누적. 보수적인 분할 진입을 추천합니다."
    else: summ = "레짐 안정적. 시스템 룰에 맞춰 평소처럼 자금을 정상 운용하십시오."

    quotes_r1 = ["강세장은 비관 속에서 태어나, 회의 속에서 자라며, 낙관 속에서 성숙하고, 행복 속에서 죽는다. - 존 템플턴", "10년 이상 볼 것이 아니면 단 10분도 그 주식을 갖고 있지 마라. - 워런 버핏"]
    quotes_r2 = ["위험은 자신이 무엇을 하는지 모르는 데서 온다. - 워런 버핏", "투자의 가장 큰 적은 바로 자기 자신이다. - 벤저민 그레이엄"]
    quotes_r3 = ["떨어지는 칼날을 맨손으로 잡지 마라. - 피터 린치", "성공적인 투자는 영원히 기다리는 것이다. - 찰리 멍거"]
    quotes_r4 = ["남들이 겁을 먹고 있을 때 욕심을 부려라. - 워런 버핏", "공포가 절정에 달했을 때가 가장 안전한 매수 시점이다. - 존 템플턴"]
    q_list = quotes_r1 if ms['regime']==1 else (quotes_r2 if ms['regime']==2 else (quotes_r3 if ms['regime']==3 else quotes_r4))

    # 🔥 트렌디한 네이티브 UI (Container + Metric 활용)
    if mobile_mode:
        st.success(f"**🤖 AI 전략 분석관 (Regime {app_reg})**\n\n{reg_t} {reg_d}\n\n⏱️ 현재 R{app_reg} 체류 기간: {dur}일째")
        if is_wait and tgt_reg < app_reg: st.warning(f"⏳ 상향 전환 검증 진행 중 ({wait_d}/5일차)")
        elif tgt_reg > app_reg: st.error("🚨 하락 전환 주의 발동")
        
        st.info(f"**⚡ 반도체 판독기:** {soxl_res} (추세 {s_stat}, 수익률 {r_stat}, RSI {rsi_stat})")
        st.warning(f"**🌱 신규 투입 조언:** {entry_g} ({summ})")
    else:
        # 상단 3개 게이지 차트
        c1, c2, c3 = st.columns(3)
        with c1:
            fig_vix = go.Figure(go.Indicator(mode="gauge+number", value=ms['vix'], title={'text':"VIX"}, gauge={'axis':{'range':[0,80]}, 'steps':[{'range':[0,25],'color':"#2ecc71"},{'range':[25,40],'color':"#f39c12"},{'range':[40,80],'color':"#e74c3c"}], 'threshold':{'line':{'color':"red",'width':4}, 'value':40}}))
            fig_vix.update_layout(height=200, margin=dict(l=20,r=20,t=40,b=10), template="plotly_dark" if WIDGET_THEME=="dark" else "plotly_white")
            st.plotly_chart(fig_vix, use_container_width=True)
        with c2:
            fig_qqq = go.Figure(go.Indicator(mode="gauge+number", value=(ms['qqq']/ms['ma200']-1)*100, title={'text':"QQQ 200일 이격도(%)"}, gauge={'axis':{'range':[-30,30]}, 'steps':[{'range':[-30,0],'color':"#e74c3c"},{'range':[0,30],'color':"#2ecc71"}], 'threshold':{'line':{'color':"yellow",'width':4}, 'value':0}}))
            fig_qqq.update_layout(height=200, margin=dict(l=20,r=20,t=40,b=10), template="plotly_dark" if WIDGET_THEME=="dark" else "plotly_white")
            st.plotly_chart(fig_qqq, use_container_width=True)
        with c3:
            fig_rsi = go.Figure(go.Indicator(mode="gauge+number", value=ms['smh_rsi'], title={'text':"SMH RSI(14)"}, gauge={'axis':{'range':[0,100]}, 'steps':[{'range':[0,30],'color':"#e74c3c"},{'range':[30,50],'color':"#f39c12"},{'range':[50,100],'color':"#3498db"}], 'threshold':{'line':{'color':"green",'width':4}, 'value':50}}))
            fig_rsi.update_layout(height=200, margin=dict(l=20,r=20,t=40,b=10), template="plotly_dark" if WIDGET_THEME=="dark" else "plotly_white")
            st.plotly_chart(fig_rsi, use_container_width=True)
            
        st.write("")
        
        # 메인 브리핑 컨테이너 (트렌디한 네이티브 UI)
        with st.container(border=True):
            st.markdown(f"### 🤖 AI 전략 분석관 Report")
            t_col = C_UP if app_reg==1 else (C_WARN if app_reg==2 else C_DOWN)
            st.markdown(f"<h4 style='color:{t_col};'>{reg_t}</h4>", unsafe_allow_html=True)
            st.markdown(f"**{reg_d}**")
            st.markdown(f"<span style='color:{C_SAFE}; font-weight:bold; font-size:1.1rem;'>⏱️ 현재 R{app_reg} 체류 기간: {dur}일째</span>", unsafe_allow_html=True)
            
            if is_wait and tgt_reg < app_reg:
                st.warning(f"**⏳ 상향 전환 검증 진행 중 ({wait_d}/5일차)**\n\n현재 시장 지표는 **[R{tgt_reg}]** 조건을 충족했으나, 휩쏘를 피하기 위해 5일 연속 체류를 확인 중입니다. (보수적 비중 유지)")
            elif tgt_reg > app_reg:
                st.error(f"**🚨 하락 전환 주의 발동**\n\n현재 시장 지표가 **[R{tgt_reg}]** 악화 조건을 터치했습니다. 오늘 종가가 이대로 마감되면 내일 아침 즉시 하향 전환됩니다.")
                
            st.info(f"📜 **거물의 속삭임:** {random.choice(q_list)}")

        st.write("")
        
        # 하단 2개 분할 컨테이너 (SOXL / 신규 자금)
        sub1, sub2 = st.columns(2)
        with sub1:
            with st.container(border=True):
                st.markdown("#### ⚡ SOXL 진입 판독기")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("50MA 추세", s_stat, f"현재 ${smh_c:.1f}", delta_color="normal" if smh_c > smh_ma50_c else "inverse")
                mc2.metric("3M 모멘텀", r_stat, f"누적 {ms['smh_3m_ret']*100:+.1f}%", delta_color="normal" if ms['smh_3m_ret'] > 0.05 else "inverse")
                mc3.metric("RSI(14)", rsi_stat, f"현재 {ms['smh_rsi']:.1f}", delta_color="normal" if ms['smh_rsi'] > 50 else "inverse")
                
                bg_color = "rgba(46, 204, 113, 0.15)" if "승인" in soxl_res else "rgba(243, 156, 18, 0.15)"
                s_color = C_UP if "승인" in soxl_res else C_WARN
                st.markdown(f"<div style='padding:12px; border-radius:8px; background:{bg_color}; text-align:center; font-weight:bold; color:{s_color}; font-size:1.1rem;'>결론: {soxl_res}</div>", unsafe_allow_html=True)
                
        with sub2:
            with st.container(border=True):
                st.markdown("#### 🌱 신규 자금 투입 가이드")
                mc4, mc5 = st.columns(2)
                mc4.metric("진입 적합도", entry_g)
                mc5.metric("추세 방향", dir_kr)
                st.markdown(f"<div style='padding:12px; border-radius:8px; background:rgba(150,150,150,0.1); text-align:center; font-weight:bold; font-size:1.0rem;'>💡 조언: {summ}</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("#### 🔍 레짐 판단 근거 시각화")
    if mobile_mode:
        st.info("📱 모바일 간편뷰 모드에서는 복잡한 차트가 생략됩니다.")
    else:
        c_df = get_regime_chart_data()
        if not c_df.empty:
            fig_rc = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.08, subplot_titles=("나스닥 (QQQ) 장단기 추세", "시장 공포지수 (VIX)"))
            
            fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['QQQ'], name="QQQ (Price)", line=dict(color=C_SAFE, width=2)), row=1, col=1)
            fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['MA50'], name="50MA", line=dict(color=C_WARN, width=1.5, dash='dot')), row=1, col=1)
            fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['MA200'], name="200MA", line=dict(color=C_DOWN, width=2)), row=1, col=1)
            
            fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['^VIX'], name="VIX", line=dict(color='#9b59b6', width=1.5), fill='tozeroy'), row=2, col=1)
            fig_rc.add_hline(y=40, line_dash="dash", line_color="red", row=2, col=1, annotation_text="패닉 (40)")
            fig_rc.add_hline(y=25, line_dash="dash", line_color="orange", row=2, col=1, annotation_text="경계 (25)")
            
            cust_rc = THEME_LAYOUT.copy()
            cust_rc.update(height=500, hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
            fig_rc.update_layout(**cust_rc)
            
            with st.container(border=True):
                st.plotly_chart(fig_rc, use_container_width=True)
                st.markdown(f"<div style='font-size:0.85rem; color:{TEXT_SUB}; text-align:center;'>💡 <b>레짐 판단의 핵심 지표:</b> 나스닥(QQQ)이 200일 이동평균선(빨간선) 위에 있는지, 공포지수(VIX)가 25나 40을 넘었는지가 전략의 핵심입니다.</div>", unsafe_allow_html=True)
        else:
            st.info("데이터를 불러오지 못했습니다.")


# =====================================================================
# [7] 사이드바 설정 및 네비게이션
# =====================================================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 테마 설정")
theme_list = ["애플 테마", "1930년대 타자기 테마", "월스트리트 저널 테마", "엑셀 테마"]
selected_theme = st.sidebar.selectbox("테마를 선택하세요", theme_list, index=theme_list.index(current_theme))
if selected_theme != current_theme:
    st.session_state['settings']['theme'] = selected_theme
    save_settings(st.session_state['settings']); st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("⭐ 즐겨찾기 링크", expanded=False):
    st.markdown(f"""<div style="display:flex; flex-direction:column; gap:2px;">
    <div style="font-size:0.8rem; font-weight:bold; margin-top:5px; color:{TEXT_SUB};">유튜브</div>
    <a href="https://www.youtube.com/@JB_Insight" target="_blank" class="sidebar-link"><span>📊</span> JB 인사이트</a>
    <a href="https://www.youtube.com/@odokgod" target="_blank" class="sidebar-link"><span>📻</span> 오독</a>
    <a href="https://www.youtube.com/@TQQQCRAZY" target="_blank" class="sidebar-link"><span>🔥</span> TQQQ 미친놈</a>
    <a href="https://www.youtube.com/@developmong" target="_blank" class="sidebar-link"><span>🐒</span> 디벨롭몽</a>
    <div style="font-size:0.8rem; font-weight:bold; margin-top:15px; color:{TEXT_SUB};">차트 분석</div>
    <a href="https://kr.investing.com/" target="_blank" class="sidebar-link"><span>🌍</span> 인베스팅닷컴</a>
    <a href="https://kr.tradingview.com/" target="_blank" class="sidebar-link"><span>📉</span> 트레이딩뷰</a>
    <div style="font-size:0.8rem; font-weight:bold; margin-top:15px; color:{TEXT_SUB};">AI 도우미</div>
    <a href="https://claude.ai/" target="_blank" class="sidebar-link"><span>🧠</span> 클로드</a>
    <a href="https://gemini.google.com/" target="_blank" class="sidebar-link"><span>✨</span> 제미나이</a>
    </div>""", unsafe_allow_html=True)

st.sidebar.markdown("---")
with st.sidebar.expander("🎨 테마 색상 커스텀"):
    st.markdown("**기본 텍스트**")
    new_text_color = st.color_picker("색상", st.session_state['settings']['text_color'])
    if new_text_color != st.session_state['settings']['text_color']:
        st.session_state['settings']['text_color'] = new_text_color
        save_settings(st.session_state['settings']); st.rerun()
        
    st.markdown("---")
    st.markdown("📈 **파이 차트 조각**")
    for tkr in st.session_state['settings']['chart_colors']:
        new_c = st.color_picker(f"{tkr}", st.session_state['settings']['chart_colors'][tkr])
        if new_c != st.session_state['settings']['chart_colors'][tkr]:
            st.session_state['settings']['chart_colors'][tkr] = new_c
            save_settings(st.session_state['settings']); st.rerun()

with st.sidebar.expander("💾 백업 및 복구"):
    st.download_button("📥 백업 다운로드", data=json.dumps(st.session_state['accounts']), file_name="amls_backup.json")
    up_f = st.file_uploader("📤 복구 업로드", type=['json'])
    if up_f and st.button("⚠️ 복구 실행"):
        st.session_state['accounts'] = json.load(up_f)
        save_accounts_data(st.session_state['accounts']); st.rerun()

# 🔥 좌측 카테고리 (AI 시스템 분석관 분리 적용)
pages = {
    "시스템": [
        st.Page(page_market_dashboard, title="마켓 터미널", icon="🌐"), 
        st.Page(page_amls_backtest, title="백테스트 엔진", icon="🦅"),
        st.Page(page_ai_analyst, title="AI 시스템 분석관", icon="⚡")
    ],
    "포트폴리오": [],
    "설정": [
        st.Page(page_strategy_specification, title="전략 명세서", icon="📜"), 
        st.Page(page_manage_accounts, title="계좌 관리", icon="⚙️")
    ]
}

for name in st.session_state['accounts'].keys(): 
    pages["포트폴리오"].append(st.Page(make_portfolio_page(name), title=name, icon="💼"))

pg = st.navigation(pages)
pg.run()
