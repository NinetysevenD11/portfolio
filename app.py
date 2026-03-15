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
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "GLD", "CASH"]

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
            "AMLS v4.3": {  
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0,
                "layout_order": ["🎯 목표 달성률", "📊 실시간 요약", "⚡ 시스템 분석관", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
            }
        }
    st.session_state['accounts'] = loaded

needs_save = False
if "기본 계좌 (AMLS)" in st.session_state['accounts']:
    st.session_state['accounts']["AMLS v4.3"] = st.session_state['accounts'].pop("기본 계좌 (AMLS)")
    needs_save = True

for acc_name, acc_data in st.session_state['accounts'].items():
    if "seed_history" not in acc_data: acc_data["seed_history"] = {}; needs_save = True
    if "target_portfolio_value" not in acc_data: acc_data["target_portfolio_value"] = 100000.0; needs_save = True
    if "layout_order" not in acc_data: 
        acc_data["layout_order"] = ["🎯 목표 달성률", "📊 실시간 요약", "⚡ 시스템 분석관", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
        needs_save = True

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
    BASE_CHART_COLORS = {'TQQQ':'#ff3b30', 'SOXL':'#af52de', 'USD':'#5856d6', 'QLD':'#ff9500', 'SSO':'#ffcc00', 'QQQ':'#007aff', 'GLD':'#34c759', 'BTC-USD':'#f7931a', 'CASH':'#8e8e93'}

elif current_theme == "1930년대 타자기 테마":
    DEFAULT_TEXT_COLOR = "#2c2a25"; TEXT_SUB = "#555555"
    PANEL_BG = "rgba(223, 215, 197, 0.85)"; PANEL_BORDER = "2px solid #2c2a25"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#000080"; C_DOWN = "#8b0000"; C_WARN = "#b8860b"; C_SAFE = "#006400"
    BASE_CHART_COLORS = {'TQQQ':'#8b0000', 'SOXL':'#556b2f', 'USD':'#8fbc8f', 'QLD':'#b8860b', 'SSO':'#cd853f', 'QQQ':'#000080', 'GLD':'#daa520', 'BTC-USD':'#f7931a', 'CASH':'#2f4f4f'}

elif current_theme == "월스트리트 저널 테마":
    DEFAULT_TEXT_COLOR = "#1A1A1A"; TEXT_SUB = "#555555"
    PANEL_BG = "rgba(255, 255, 255, 0.95)"; PANEL_BORDER = "1px solid #000000"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#006400"; C_DOWN = "#8B0000"; C_WARN = "#B8860B"; C_SAFE = "#000080"
    BASE_CHART_COLORS = {'TQQQ':'#8B0000', 'SOXL':'#556b2f', 'USD':'#2F4F4F', 'QLD':'#B8860B', 'SSO':'#DAA520', 'QQQ':'#000080', 'GLD':'#BDB76B', 'BTC-USD':'#f7931a', 'CASH':'#696969'}

elif current_theme == "엑셀 테마":
    DEFAULT_TEXT_COLOR = "#333333"; TEXT_SUB = "#666666"
    PANEL_BG = "rgba(255, 255, 255, 0.95)"; PANEL_BORDER = "1px solid #D4D4D4"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#107C41"; C_DOWN = "#C00000"; C_WARN = "#FFB900"; C_SAFE = "#0078D4"
    BASE_CHART_COLORS = {'TQQQ':'#C00000', 'SOXL':'#800080', 'USD':'#0078D4', 'QLD':'#FFB900', 'SSO':'#E36C09', 'QQQ':'#0078D4', 'GLD':'#FFC000', 'BTC-USD':'#f7931a', 'CASH':'#7F7F7F'}


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
    css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.03); backdrop-filter: blur(10px); }}"
    
    if current_theme == "애플 테마":
        css_base = f"""
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        .stApp {{ background-color: #f5f5f7; background-image: radial-gradient(circle at top right, #e2e2e5 0%, #f5f5f7 40%, #e8e8ed 100%); font-family: 'Pretendard', -apple-system, sans-serif; color: {TEXT_COLOR}; letter-spacing: -0.01em; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background: {PANEL_BG}; backdrop-filter: blur(20px); border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.05); padding: 1.5rem; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none !important; color: {TEXT_COLOR}; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.05); transform: translateX(2px); }}
        """
    elif current_theme == "1930년대 타자기 테마":
        css_base = f"""
        @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp {{ font-family: 'Special Elite', 'Courier New', monospace !important; color: {TEXT_COLOR} !important; background-color: #e4dccc; background-image: url('https://www.transparenttextures.com/patterns/old-wall.png'); }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-radius: {PANEL_RADIUS} !important; box-shadow: 4px 4px 0px {TEXT_COLOR} !important; padding: 1.5rem !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 0px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: bold; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.1); border: 1px dashed {TEXT_COLOR}; }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: 4px 4px 0px {TEXT_COLOR}; }}"
    elif current_theme == "월스트리트 저널 테마":
        css_base = f"""
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap');
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp {{ font-family: 'Playfair Display', serif; color: {TEXT_COLOR}; background-color: #F4F4F0; background-image: repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.02) 2px, rgba(0,0,0,0.02) 4px); }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background-color: {PANEL_BG}; border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; padding: 1.5rem; box-shadow: 3px 3px 0px rgba(0,0,0,0.1); border-top: 4px solid #000000; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; text-decoration: none !important; color: #000000 !important; font-weight: bold; font-size: 0.95rem; border-bottom: 1px dotted #CCC; }}
        .sidebar-link:hover {{ background-color: #DDDDDD; }}
        """
    elif current_theme == "엑셀 테마":
        css_base = f"""
        .stApp {{ font-family: 'Calibri', 'Malgun Gothic', sans-serif; color: {TEXT_COLOR} !important; background-color: #F3F2F1; background-image: linear-gradient(#e1dfdd 1px, transparent 1px), linear-gradient(90deg, #e1dfdd 1px, transparent 1px); background-size: 20px 20px; }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background-color: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-top: 3px solid #107C41 !important; border-radius: {PANEL_RADIUS} !important; padding: 1.5rem !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px; text-decoration: none !important; color: #0078D4 !important; font-family: 'Calibri', sans-serif; font-size: 0.95rem; border-bottom: 1px solid transparent; }}
        .sidebar-link:hover {{ border-bottom: 1px solid #0078D4; background-color: rgba(0,0,0,0.05); }}
        """
        css_panel = f".info-panel {{ background: {PANEL_BG}; border: {PANEL_BORDER}; border-top: 3px solid #107C41 !important; border-radius: {PANEL_RADIUS}; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}"

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
# [3] 글로벌 백엔드 (백테스트 엔진 + 비트코인 옵션 적용)
# =====================================================================
@st.cache_data(ttl=3600)
def load_amls_backtest_data(start, end, init_cap, monthly_cont, rebal_freq="월 1회", btc_ratio=0):
    tickers = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'BTC-USD']
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
    
    actual_regime_v4_3 = []; current_v4_3 = 3; pend_v4_3 = None; cnt_v4_3 = 0
    for i in range(len(df)):
        tr = df['Target_Regime'].iloc[i]
        if tr > current_v4_3: 
            current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
        elif tr < current_v4_3: 
            if tr == pend_v4_3:
                cnt_v4_3 += 1
                if cnt_v4_3 >= 5: current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
                else: actual_regime_v4_3.append(current_v4_3 - 1)
            else: pend_v4_3 = tr; cnt_v4_3 = 1; actual_regime_v4_3.append(current_v4_3 - 1)
        else: pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)

    df['Signal_Regime_v4_3'] = pd.Series(actual_regime_v4_3, index=df.index).shift(1).bfill()

    def get_v4_3_weights(regime, use_soxl, b_ratio):
        w = {t: 0.0 for t in data.columns}; semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'] = 0.30, 0.20, 0.20, 0.15, 0.10
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'] = 0.30, 0.25, 0.20, 0.10, 0.05
        elif regime == 3: w['GLD'], w['QQQ'] = 0.50, 0.15
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        
        if b_ratio > 0 and w['GLD'] > 0:
            btc_amt = w['GLD'] * (b_ratio / 100.0)
            w['GLD'] = w['GLD'] - btc_amt
            w['BTC-USD'] = btc_amt
        return w

    strategies = ['AMLS v4.3', 'QQQ', 'QLD']
    ports = {s: init_cap for s in strategies}
    hists = {s: [init_cap] for s in ports.keys()}
    total_invested = init_cap
    weights_v4_3 = {t: 0.0 for t in data.columns}
    logs, days_since = [], 0

    for i in range(1, len(df)):
        today, yesterday = df.index[i], df.index[i-1]
        days_since += 1
        ret_v4_3 = sum(weights_v4_3[t] * daily_returns[t].iloc[i] for t in data.columns)
        
        ports['AMLS v4.3'] *= (1 + ret_v4_3)
        for s in ['QQQ', 'QLD']: ports[s] *= (1 + daily_returns[s].iloc[i])
        
        for t in data.columns:
            if ports['AMLS v4.3'] > 0: weights_v4_3[t] = weights_v4_3[t]*(1+daily_returns[t].iloc[i])/(1+ret_v4_3)
            
        if today.month != yesterday.month:
            for s in ports: ports[s] += monthly_cont
            total_invested += monthly_cont
        for s in ports: hists[s].append(ports[s])
        
        use_soxl = (df['SMH'].iloc[i-1] > df['SMH_MA50'].iloc[i-1]) and (df['SMH_3M_Ret'].iloc[i-1] > 0.05) and (df['SMH_RSI'].iloc[i-1] > 50)
        
        sig_r = df['Signal_Regime_v4_3'].iloc[i]
        rebal = False
        if sig_r != df['Signal_Regime_v4_3'].iloc[i-1] or i == 1: rebal = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal = True
        elif "주 1회" in rebal_freq and days_since >= 5: rebal = True
        elif "2주 1회" in rebal_freq and days_since >= 10: rebal = True
        elif "3주 1회" in rebal_freq and days_since >= 15: rebal = True
        
        if rebal:
            weights_v4_3 = get_v4_3_weights(sig_r, use_soxl, btc_ratio)
            log_type = "레짐 전환" if sig_r != df['Signal_Regime_v4_3'].iloc[i-1] else f"정기 ({rebal_freq.split(' ')[0]})"
            logs.append({"날짜": today.strftime('%Y-%m-%d'), "유형": log_type, "국면": f"R{int(sig_r)}", "평가액": ports['AMLS v4.3']})
            days_since = 0

    for s in ports: df[f'{s}_Value'] = hists[s]
    inv_arr = [init_cap]; curr_inv = init_cap
    for i in range(1, len(df)):
        if df.index[i].month != df.index[i-1].month: curr_inv += monthly_cont
        inv_arr.append(curr_inv)
    df['Invested'] = inv_arr
    return df, logs, data.columns


# =====================================================================
# [4] 페이지 구성: 글로벌 마켓 대시보드
# =====================================================================
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
            tickers = ['^GSPC', '^IXIC', '^VIX', 'USDKRW=X']
            indices_df = yf.download(tickers, start=datetime.today()-timedelta(days=365), progress=False)['Close'].ffill()
            
            if not indices_df.empty:
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
    
    def calc_metrics(series, invested_series):
        final_val = series.iloc[-1]; total_inv = invested_series.iloc[-1]
        total_ret = (final_val / total_inv) - 1
        days = (series.index[-1] - series.index[0]).days
        cagr = (final_val / invested_series.iloc[-1]) ** (365.25 / days) - 1 if days > 0 else 0
        mdd = ((series / series.cummax()) - 1).min()
        daily_ret = series.pct_change().dropna()
        sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252)) if daily_ret.std() != 0 else 0
        return final_val, total_ret, cagr, mdd, sharpe

    strats = ['AMLS v4.3', 'QQQ', 'QLD']
    metrics_data = []
    for s in strats:
        fv, tr, cagr, mdd, shp = calc_metrics(df[f'{s}_Value'], df['Invested'])
        metrics_data.append({"전략": s, "최종 금액": f"${fv:,.0f}", "수익률": f"{tr*100:+.1f}%", "CAGR": f"{cagr*100:.1f}%", "MDD": f"{mdd*100:.1f}%", "샤프": f"{shp:.2f}"})
    metrics_df = pd.DataFrame(metrics_data).set_index("전략")

    tab1, tab2, tab3 = st.tabs(["📊 성과 비교 및 차트", "🗓️ 월별 수익률 히트맵", "📝 시스템 로그"])

    with tab1:
        st.markdown("#### 🏆 성과 요약")
        st.info(f"투입 원금: ${df['Invested'].iloc[-1]:,.0f} (BTC 편입비중: {BTC_RATIO}%)")
        st.dataframe(metrics_df, use_container_width=True)

        st.markdown("#### 📈 자산 곡선 및 낙폭 (MDD)")
        fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        for s in strats:
            color = C_UP if 'AMLS' in s else (C_SAFE if 'QQQ' in s else C_WARN)
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

    with tab2:
        st.markdown("#### 🗓️ AMLS v4.3 월별 수익률 캘린더 (%)")
        monthly_df = df['AMLS v4.3_Value'].resample('M').last().pct_change() * 100
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
            st.dataframe(log_df, hide_index=True, use_container_width=True, height=500)


# =====================================================================
# [6] 페이지 구성: 내 포트폴리오 관리 
# =====================================================================
def make_portfolio_page(acc_name):
    def page_func():
        mobile_mode = st.sidebar.checkbox("📱 모바일 간편뷰 모드", value=False, help="작은 화면에서 텍스트와 핵심 지표만 크게 봅니다.")
        
        st.title(f"💼 {acc_name}")
        curr_acc_data = st.session_state['accounts'][acc_name]
        
        DEFAULT_LAYOUT = ["🎯 목표 달성률", "📊 실시간 요약", "⚡ 시스템 분석관", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
        current_layout = curr_acc_data.get("layout_order", DEFAULT_LAYOUT)
        
        with st.sidebar.expander(f"🛠️ 화면 레이아웃 편집", expanded=False):
            st.caption("위아래로 순서를 변경하세요.")
            for i, block_name in enumerate(current_layout):
                c_name, c_up, c_dn = st.columns([5, 1.5, 1.5])
                c_name.markdown(f"<div style='font-size:0.85rem; font-weight:bold; padding-top:5px;'>{i+1}. {block_name}</div>", unsafe_allow_html=True)
                if c_up.button("▲", key=f"up_{i}_{acc_name}") and i > 0:
                    current_layout[i], current_layout[i-1] = current_layout[i-1], current_layout[i]
                    curr_acc_data["layout_order"] = current_layout
                    save_accounts_data(st.session_state['accounts']); st.rerun()
                if c_dn.button("▼", key=f"dn_{i}_{acc_name}") and i < len(current_layout)-1:
                    current_layout[i], current_layout[i+1] = current_layout[i+1], current_layout[i]
                    curr_acc_data["layout_order"] = current_layout
                    save_accounts_data(st.session_state['accounts']); st.rerun()
        st.sidebar.markdown("---")

        pf_df = pd.DataFrame(curr_acc_data["portfolio"])
        for col in ["수량 (주/달러)", "평균 단가 ($)", "매입 환율"]:
            if col in pf_df.columns: pf_df[col] = pf_df[col].astype(float)
            else: pf_df[col] = 0.0

        @st.cache_data(ttl=1800)
        def get_market_status():
            TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']
            data = yf.download(TICKERS, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill()
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
                
            current_v4_3 = 3; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3 = []
            for tr in target_regimes:
                if tr > current_v4_3: 
                    current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
                elif tr < current_v4_3:
                    if tr == pend_v4_3:
                        cnt_v4_3 += 1
                        if cnt_v4_3 >= 5: current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
                        else: actual_regime_v4_3.append(current_v4_3 - 1)
                    else: 
                        pend_v4_3 = tr; cnt_v4_3 = 1; actual_regime_v4_3.append(current_v4_3 - 1)
                else: 
                    pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
                    
            applied_series = pd.Series(actual_regime_v4_3, index=data.index).shift(1).bfill()
            applied_reg = int(applied_series.iloc[-1])
            target_reg = int(target_regimes[-1])
            is_waiting = (pend_v4_3 is not None and target_reg < current_v4_3)

            current_reg = applied_series.iloc[-1]
            regime_duration = 0
            for i in range(len(applied_series)-1, -1, -1):
                if applied_series.iloc[i] == current_reg: regime_duration += 1
                else: break
            
            prev_reg = current_reg
            for i in range(len(applied_series)-regime_duration-1, -1, -1):
                prev_reg = applied_series.iloc[i]; break

            if current_reg < prev_reg: regime_direction = "ascending"
            elif current_reg > prev_reg: regime_direction = "descending"
            else: regime_direction = "stable"

            if regime_direction == "ascending": entry_grade = "최적 진입" if regime_duration <= 30 else "주의(전환)"
            elif regime_direction == "descending": entry_grade = "진입 보류" if regime_duration <= 20 else "바닥 탐색"
            else: entry_grade = "진입 적합"

            try:
                fx_data = yf.download('USDKRW=X', period='5d', progress=False)['Close'].ffill()
                current_usdkrw = float(fx_data.iloc[:, 0].iloc[-1] if isinstance(fx_data, pd.DataFrame) else fx_data.iloc[-1])
            except: current_usdkrw = 0.0

            return {
                'regime': applied_reg, 'target_regime': target_reg, 'is_waiting': is_waiting, 'wait_days': cnt_v4_3,
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
            if vix_rt > 40: rt_tgt = 4
            elif qqq_rt < ms['ma200']: rt_tgt = 3
            elif qqq_rt >= ms['ma200'] and ms['ma50'] >= ms['ma200'] and vix_rt < 25: rt_tgt = 1
            else: rt_tgt = 2
            
            ms['target_regime'] = rt_tgt
            if rt_tgt > ms['regime']:
                ms['regime'] = rt_tgt
                ms['is_waiting'] = False
            
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

        # 🔥 KeyError의 원인이었던 부분 완벽 복구
        def cy_krw(row):
            if row["수량 (주/달러)"] == 0 or row["평균 단가 ($)"] == 0 or row["티커 (Ticker)"] == "CASH": return 0.0
            if row.get("매입 환율", 0) <= 0 or current_usdkrw <= 0: return 0.0
            buy_krw = row["평균 단가 ($)"] * row["매입 환율"]
            now_krw = row["현재가 ($)"] * current_usdkrw
            return (now_krw - buy_krw) / buy_krw * 100
        disp_df["원화 수익률 (%)"] = disp_df.apply(cy_krw, axis=1)

        total_val_now = 0.0; total_val_yest = 0.0; auto_seed = 0.0
        best_ticker = "-"; best_ret = -999.0
        asset_vals = {}; weights_dict = {}
        
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

        if total_val_now > 0:
            for k, v in asset_vals.items(): weights_dict[k] = v / total_val_now

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


        # -------------------------------------------------------------
        # 동적 레이아웃 렌더링 루프
        # -------------------------------------------------------------
        for block in current_layout:
            
            if block == "🎯 목표 달성률":
                target_val = curr_acc_data.get("target_portfolio_value", 100000.0)
                progress_pct =
