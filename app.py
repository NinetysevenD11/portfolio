import streamlit as st
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
import google.generativeai as genai

warnings.filterwarnings('ignore')

# ==========================================
# 0. UI Theme & Helpers
# ==========================================
def apply_amls_theme():
    st.markdown("""
    <style>
    /* ═══════════════════════════════════════
       0. GOOGLE FONTS
    ═══════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

    /* ═══════════════════════════════════════
       1. CSS VARIABLES
    ═══════════════════════════════════════ */
    :root {
        --color-primary:      #5B5CFF;
        --color-accent:       #00C48C;
        --color-danger:       #FF4D4F;
        --color-warning:      #E6A817;
        --color-bg-page:      #F0F2F5;
        --color-bg-card:      #FFFFFF;
        --color-bg-sidebar:   #FFFFFF;
        --color-text-primary: #1A1D2E;
        --color-text-sub:     #9FA2B4;
        --color-border:       #EAECF0;
        --shadow-card:        0 2px 12px rgba(0,0,0,0.06);
        --radius-card:        14px;
        --radius-pill:        999px;
    }

    /* ═══════════════════════════════════════
       2. GLOBAL BASE
    ═══════════════════════════════════════ */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'DM Sans', sans-serif !important;
        background-color: var(--color-bg-page) !important;
        color: var(--color-text-primary) !important;
    }

    [data-testid="stMainBlockContainer"] {
        padding: 24px 28px !important;
    }

    /* ═══════════════════════════════════════
       3. SIDEBAR
    ═══════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background-color: var(--color-bg-sidebar) !important;
        border-right: 1px solid var(--color-border) !important;
        padding: 20px 16px !important;
    }

    [data-testid="stSidebar"] * {
        font-family: 'DM Sans', sans-serif !important;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 20px !important;
        font-weight: 800 !important;
        color: var(--color-primary) !important;
        letter-spacing: -0.3px !important;
        margin-bottom: 2px !important;
    }

    [data-testid="stSidebar"] h1 + p,
    [data-testid="stSidebar"] .sidebar-subtitle {
        font-size: 10px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: var(--color-text-sub) !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] a {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--color-text-primary) !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        display: flex !important;
        align-items: center !important;
        transition: background 0.15s ease !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background-color: #F5F6FA !important;
    }

    [data-testid="stSidebar"] [aria-checked="true"] + label,
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-active="true"] label {
        background-color: rgba(91, 92, 255, 0.08) !important;
        color: var(--color-primary) !important;
        font-weight: 700 !important;
        border-left: 3px solid var(--color-primary) !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: var(--color-border) !important;
        margin: 16px 0 !important;
    }

    /* ═══════════════════════════════════════
       4. CARDS (metric containers, expanders)
    ═══════════════════════════════════════ */
    [data-testid="stMetric"],
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"],
    div.element-container > div.stMarkdown,
    [data-testid="stExpander"] {
        background-color: var(--color-bg-card) !important;
        border-radius: var(--radius-card) !important;
        box-shadow: var(--shadow-card) !important;
        border: 1px solid var(--color-border) !important;
        padding: 18px 20px !important;
    }

    [data-testid="stContainer"] {
        background-color: var(--color-bg-card) !important;
        border-radius: var(--radius-card) !important;
        box-shadow: var(--shadow-card) !important;
        border: 1px solid var(--color-border) !important;
        padding: 20px !important;
    }

    /* ═══════════════════════════════════════
       5. METRIC
    ═══════════════════════════════════════ */
    [data-testid="stMetric"] { padding: 18px 20px !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; color: var(--color-text-sub) !important; }
    [data-testid="stMetricValue"] { font-size: 36px !important; font-weight: 800 !important; color: var(--color-text-primary) !important; line-height: 1.1 !important; }
    [data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 600 !important; padding: 2px 8px !important; border-radius: var(--radius-pill) !important; display: inline-flex !important; align-items: center !important; }
    [data-testid="stMetricDelta"][data-direction="up"], [data-testid="stMetricDelta"] svg[class*="positive"] ~ span { background-color: #E6FAF4 !important; color: var(--color-accent) !important; }
    [data-testid="stMetricDelta"][data-direction="down"] { background-color: #FFF0F0 !important; color: var(--color-danger) !important; }

    /* ═══════════════════════════════════════
       6. 시그널 배지
    ═══════════════════════════════════════ */
    .badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; width: 100%; justify-content: flex-start; }
    .badge-positive { background-color: #E6FAF4; color: #00C48C; border: 1px solid #B3F0DA; }
    .badge-negative { background-color: #FFF0F0; color: #FF4D4F; border: 1px solid #FFD0D0; }
    .badge-neutral { background-color: #FFF8E1; color: #E6A817; border: 1px solid #FFE082; }

    /* ═══════════════════════════════════════
       7. 섹션 헤더 & 8. 조건 행 & 9. WEIGHTS 테이블
    ═══════════════════════════════════════ */
    .card-title { font-size: 11px !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; color: var(--color-text-sub) !important; margin-bottom: 8px !important; }
    .card-status-value { font-size: 28px !important; font-weight: 800 !important; color: var(--color-primary) !important; line-height: 1.2 !important; }
    .card-status-sub { font-size: 12px !important; color: var(--color-text-sub) !important; margin-top: 2px !important; }
    
    .condition-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--color-border); font-size: 12px; color: var(--color-text-primary); }
    .condition-value-pass { color: var(--color-accent); font-weight: 600; }
    .condition-value-fail { color: var(--color-danger); font-weight: 600; }

    .weights-table { width: 100%; border-collapse: collapse; }
    .weights-table th { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--color-text-sub); padding: 6px 0; border-bottom: 1px solid var(--color-border); }
    .weights-table td { font-size: 13px; color: var(--color-text-primary); padding: 10px 0; border-bottom: 1px solid var(--color-border); }
    .weights-table td.weight-value { font-weight: 700; color: var(--color-primary); text-align: right; }

    /* ═══════════════════════════════════════
       10. 8-PACK RADAR 알림 & 11. LIVE 배지
    ═══════════════════════════════════════ */
    .alert-banner { background-color: #FFF0F0; border-left: 4px solid var(--color-danger); border-radius: 10px; padding: 14px 18px; margin-bottom: 20px; }
    .alert-banner .alert-title { font-size: 13px; font-weight: 700; color: var(--color-danger); margin-bottom: 4px; }
    .alert-banner .alert-status { font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 4px; }
    .alert-banner .alert-body { font-size: 12px; color: var(--color-text-sub); line-height: 1.6; }
    .alert-banner-neutral { background-color: #FFF8E1; border-left: 4px solid var(--color-warning); }
    .alert-banner-positive { background-color: #E6FAF4; border-left: 4px solid var(--color-accent); }

    .live-badge { display: inline-flex; align-items: center; gap: 6px; background-color: #E6FAF4; border: 1px solid #B3F0DA; border-radius: var(--radius-pill); padding: 3px 10px; font-size: 11px; font-weight: 700; color: var(--color-accent); margin: 8px 0 16px 0; }
    .live-dot { width: 7px; height: 7px; border-radius: 50%; background-color: var(--color-accent); animation: pulse-green 1.5s infinite; }
    @keyframes pulse-green { 0% { box-shadow: 0 0 0 0 rgba(0,196,140,0.5); } 70% { box-shadow: 0 0 0 6px rgba(0,196,140,0); } 100% { box-shadow: 0 0 0 0 rgba(0,196,140,0); } }

    /* ═══════════════════════════════════════
       12. 차트 & 13. 기타 정리
    ═══════════════════════════════════════ */
    [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], [data-testid="stAltairChart"] { background-color: var(--color-bg-card) !important; border-radius: var(--radius-card) !important; box-shadow: var(--shadow-card) !important; border: 1px solid var(--color-border) !important; padding: 16px !important; overflow: hidden !important; }
    .block-container { padding-top: 1.5rem !important; max-width: 100% !important; }
    [data-testid="stSelectbox"] > div > div { background-color: var(--color-bg-card) !important; border: 1px solid var(--color-border) !important; border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; }
    [data-testid="stButton"] > button { background-color: var(--color-primary) !important; color: #fff !important; border: none !important; border-radius: var(--radius-pill) !important; font-family: 'DM Sans', sans-serif !important; font-weight: 600 !important; font-size: 13px !important; padding: 8px 20px !important; transition: opacity 0.15s ease !important; }
    [data-testid="stButton"] > button:hover { opacity: 0.88 !important; }
    [data-testid="stHeader"] { background-color: transparent !important; border-bottom: none !important; }
    p, span, label, div { font-family: 'DM Sans', sans-serif !important; }
    h1, h2, h3 { font-family: 'DM Sans', sans-serif !important; font-weight: 800 !important; color: var(--color-text-primary) !important; }
    h2 { font-size: 18px !important; } h3 { font-size: 15px !important; }
    [data-testid="stHorizontalBlock"] { gap: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

def badge(label: str, variant: str = "positive") -> str:
    icons = {"positive": "✅", "negative": "🔴", "neutral":  "🟡"}
    icon = icons.get(variant, "")
    return f'<div class="badge badge-{variant}">{icon}&nbsp;{label}</div>'

def card_title(text: str) -> str:
    return f'<div class="card-title">{text}</div>'

def card_status(value: str, sub: str = "") -> str:
    sub_html = f'<div class="card-status-sub">{sub}</div>' if sub else ""
    return f'<div class="card-status-value">{value}</div>{sub_html}'

def condition_row(label: str, value: str, passed: bool) -> str:
    cls = "condition-value-pass" if passed else "condition-value-fail"
    return f'<div class="condition-row"><span>{label}</span><span class="{cls}">{value} ●</span></div>'

def live_badge(count: int) -> str:
    return f'<div class="live-badge"><div class="live-dot"></div>LIVE ({count})</div>'

def alert_banner(title: str, status_line: str, body: str, variant: str = "negative") -> str:
    cls_map = {"negative": "alert-banner", "neutral": "alert-banner alert-banner-neutral", "positive": "alert-banner alert-banner-positive"}
    return f'<div class="{cls_map[variant]}"><div class="alert-title">{title}</div><div class="alert-status">{status_line}</div><div class="alert-body">{body}</div></div>'

def weights_table(data: list[dict]) -> str:
    rows = "".join([f'<tr><td>{d["asset"]}</td><td class="weight-value">{d["weight"]}</td></tr>' for d in data])
    return f'<table class="weights-table"><thead><tr><th>ASSET</th><th style="text-align:right">WEIGHT</th></tr></thead><tbody>{rows}</tbody></table>'

# ==========================================
# 1. 설정 및 데이터
# ==========================================
st.set_page_config(page_title="AMLS V4.5", layout="wide", page_icon="📈", initial_sidebar_state="expanded")
apply_amls_theme()

SECTOR_TICKERS = ['XLK','XLV','XLF','XLY','XLC','XLI','XLP','XLE','XLU','XLRE','XLB']
CORE_TICKERS   = ['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD','^VIX','HYG','IEF','QQQE','UUP']
TICKERS        = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST     = ['TQQQ','SOXL','USD','QLD','SSO','SPY','QQQ','GLD','CASH']
PORTFOLIO_FILE = 'portfolio_autosave.json'

def sanitize_portfolio():
    for a in ASSET_LIST:
        val = st.session_state.portfolio.get(a)
        if isinstance(val, (int, float)) or val is None:
            st.session_state.portfolio[a] = {'shares': float(val or 0.0), 'avg_price': 1.0 if a == 'CASH' else 0.0, 'fx': 1350.0}
        elif isinstance(val, dict):
            val.setdefault('shares', 0.0)
            val.setdefault('avg_price', 1.0 if a == 'CASH' else 0.0)
            val.setdefault('fx', 1350.0)
        else:
            st.session_state.portfolio[a] = {'shares': 0.0, 'avg_price': 0.0, 'fx': 1350.0}

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {asset: {'shares':0.0, 'avg_price':0.0, 'fx':1350.0} for asset in ASSET_LIST}
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r') as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    st.session_state.portfolio[k] = v
        except: pass
sanitize_portfolio()

def save_portfolio_to_disk():
    try:
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(st.session_state.portfolio, f)
    except: pass

@st.cache_data(ttl=3600)
def load_data():
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=900)
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)['Close']
    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]
    df = df.ffill().bfill()
    df['QQQ_MA20']      = df['QQQ'].rolling(20).mean()
    df['QQQ_MA50']      = df['QQQ'].rolling(50).mean()
    df['QQQ_MA200']     = df['QQQ'].rolling(200).mean()
    df['TQQQ_MA200']    = df['TQQQ'].rolling(200).mean()
    df['SMH_MA50']      = df['SMH'].rolling(50).mean()
    df['VIX_MA5']       = df['^VIX'].rolling(5).mean()
    df['VIX_MA20']      = df['^VIX'].rolling(20).mean()
    df['SMH_3M_Ret']    = df['SMH'].pct_change(63)
    df['SMH_1M_Ret']    = df['SMH'].pct_change(21)
    df['SMH_RSI']       = ta.rsi(df['SMH'], length=14)
    df['HYG_IEF_Ratio'] = df['HYG'] / df['IEF']
    df['HYG_IEF_MA20']  = df['HYG_IEF_Ratio'].rolling(20).mean()
    df['HYG_IEF_MA50']  = df['HYG_IEF_Ratio'].rolling(50).mean()
    df['QQQ_20d_Ret']   = df['QQQ'].pct_change(20)
    df['QQQE_20d_Ret']  = df['QQQE'].pct_change(20)
    df['QQQ_RSI']       = ta.rsi(df['QQQ'], length=14)
    df['GLD_SPY_Ratio'] = df['GLD'] / df['SPY']
    df['GLD_SPY_MA50']  = df['GLD_SPY_Ratio'].rolling(50).mean()
    df['QQQ_High52']    = df['QQQ'].rolling(252).max()
    df['QQQ_DD']        = (df['QQQ'] / df['QQQ_High52']) - 1
    df['UUP_MA50']      = df['UUP'].rolling(50).mean()
    for sec in SECTOR_TICKERS: df[f'{sec}_1M'] = df[sec].pct_change(21)
    return df.dropna()

REALTIME_TICKERS = ['QQQ','TQQQ','SMH','^VIX','HYG','IEF','UUP','GLD','SPY','SOXL','USD','QLD','SSO','USDKRW=X']
@st.cache_data(ttl=60)
def fetch_realtime_prices():
    prices = {}
    for ticker in REALTIME_TICKERS:
        try:
            info  = yf.Ticker(ticker).fast_info
            price = info.get('last_price') or info.get('lastPrice')
            if price and price > 0: prices[ticker] = float(price)
        except: pass
    return prices

with st.spinner('데이터 수집 중...'):
    df        = load_data()
    rt_prices = fetch_realtime_prices()

if df is None or df.empty:
    st.error("🚨 데이터 수집 오류. 새로고침 해주세요.")
    st.stop()

last_row    = df.iloc[-1].copy()
rt_injected = []
for ticker, price in rt_prices.items():
    if ticker in last_row.index and price > 0:
        last_row[ticker] = price; rt_injected.append(ticker)

if 'QQQ' in rt_injected: last_row['QQQ_DD'] = (last_row['QQQ'] / last_row['QQQ_High52']) - 1
if 'HYG' in rt_injected and 'IEF' in rt_injected: last_row['HYG_IEF_Ratio'] = last_row['HYG'] / last_row['IEF']

vix_close, vix_ma5, vix_ma20 = last_row['^VIX'], last_row['VIX_MA5'], last_row['VIX_MA20']
qqq_close, qqq_ma50, qqq_ma200 = last_row['QQQ'], last_row['QQQ_MA50'], last_row['QQQ_MA200']
smh_close, smh_ma50, smh_3m, smh_1m, smh_rsi = last_row['SMH'], last_row['SMH_MA50'], last_row['SMH_3M_Ret'], last_row['SMH_1M_Ret'], last_row['SMH_RSI']

def apply_asymmetric_delay(targets):
    res = []; hist_curr = 3; pend = None; cnt = 0
    for t in targets:
        if t > hist_curr: hist_curr = t; pend = None; cnt = 0
        elif t < hist_curr:
            if t == pend:
                cnt += 1
                if cnt >= 5: hist_curr = t; pend = None; cnt = 0
            else: pend = t; cnt = 1
        else: pend = None; cnt = 0
        res.append(hist_curr)
    return pd.Series(res, index=targets.index).shift(1).bfill()

def get_target_v45(row):
    if row['^VIX'] > 40: return 4
    credit_stress = row['HYG_IEF_Ratio'] < row['HYG_IEF_MA20']
    if row['QQQ'] < row['QQQ_MA200']: return 3
    if row['QQQ_DD'] < -0.10 and credit_stress: return 3
    bull_trend = row['QQQ'] >= row['QQQ_MA200'] and row['QQQ_MA50'] >= row['QQQ_MA200']
    low_vix    = row['VIX_MA20'] < 22
    credit_ok  = row['HYG_IEF_Ratio'] >= row['HYG_IEF_MA50']
    if bull_trend and low_vix and credit_ok: return 1
    return 2

df['Target'] = df.apply(get_target_v45, axis=1)
df['Regime'] = apply_asymmetric_delay(df['Target'])

live_regime   = get_target_v45(last_row)            
hist_regime   = int(df.iloc[-1]['Regime'])            
curr_regime   = live_regime if live_regime > hist_regime else hist_regime

smh_c1 = smh_close > smh_ma50
smh_c2 = (smh_3m > 0.05 or smh_1m > 0.10)
smh_c3 = smh_rsi > 50
smh_cond = smh_c1 and smh_c2 and smh_c3

def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if smh_ok else 'USD'
    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2: w['TQQQ'], w['QLD'], w['SSO'], w['USD'], w['GLD'], w['SPY'] = 0.15, 0.30, 0.25, 0.10, 0.15, 0.05
    elif reg == 3: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w
target_weights = get_weights_v45(curr_regime, smh_cond)

if curr_regime == live_regime: regime_committee_msg = "조건 부합 (안정)"
elif live_regime > curr_regime: regime_committee_msg = f"R{live_regime} 하향 즉시 반영"
else: regime_committee_msg = f"R{live_regime} 승급 대기 (5일)"

# 새 테마용 차트 변수
b_color = 'rgba(0,0,0,0)'
t_color = '#1A1D2E'
line_c = '#5B5CFF'
dash_c = '#9FA2B4'
rsi_low_c = '#00C48C'
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="DM Sans", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
regime_info  = {1:("R1 BULL","풀 가동"),2:("R2 CORR","방어 진입"), 3:("R3 BEAR","대피"),4:("R4 PANIC","최대 방어")}

# ==========================================
# 2. 사이드바 UI
# ==========================================
st.sidebar.markdown("<h1>AMLS V4.5</h1><p>QUANTITATIVE ENGINE</p>", unsafe_allow_html=True)
st.sidebar.markdown(live_badge(len(rt_injected)), unsafe_allow_html=True)
page = st.sidebar.radio("MENU", ["📊 Dashboard", "💼 Portfolio", "🍫 8-Pack Radar", "📈 Backtest Lab", "📰 Macro News"], label_visibility="collapsed")
st.sidebar.markdown("<hr><p class='sidebar-subtitle'>Powered by Apex<br>&copy; 2026 SEYOON.</p>", unsafe_allow_html=True)

# ==========================================
# 3. 페이지 라우팅
# ==========================================
if page == "📊 Dashboard":
    st.markdown("<h2>Dashboard Overview</h2>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.markdown(card_title("MARKET REGIME") +
                    card_status(regime_info[curr_regime][0], regime_info[curr_regime][1]) +
                    condition_row('VIX < 40', f'{vix_close:.2f}', vix_close<=40) +
                    condition_row('QQQ > 200MA', f'${qqq_close:.0f}', qqq_close>=qqq_ma200) +
                    condition_row('50MA ≥ 200MA', f'${qqq_ma50:.0f}', qqq_ma50>=qqq_ma200) +
                    f'<div style="margin-top:12px; font-size:12px; color:var(--color-text-sub);">{regime_committee_msg}</div>', 
                    unsafe_allow_html=True)
    with c2:
        soxl_title  = "SOXL 진입 승인" if smh_cond else "USD 방어 진입"
        soxl_strat  = "3x Leverage" if smh_cond else "2x Defense"
        st.markdown(card_title("SEMI-CONDUCTOR (SOXL)") +
                    card_status(soxl_title, soxl_strat) +
                    condition_row('SMH > 50MA', f'${smh_close:.1f}', smh_c1) +
                    condition_row('Mom (1M>10%)', f'{smh_1m*100:.1f}%', smh_c2) +
                    condition_row('RSI > 50', f'{smh_rsi:.1f}', smh_c3) +
                    f'<div style="margin-top:12px; font-size:12px; color:var(--color-text-sub);">※ 3 filters required</div>', 
                    unsafe_allow_html=True)
    with c3:
        w_data = [{"asset": k, "weight": f"{v*100:.0f}%"} for k, v in target_weights.items() if v > 0]
        st.markdown(card_title("TARGET WEIGHTS") + weights_table(w_data), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("QQQ vs 200MA", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200MA", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%")
    m3.metric("VIX (20D MA)", f"{last_row['VIX_MA20']:.2f}", f"NOW: {last_row['^VIX']:.2f}")
    m4.metric("SMH 1M", f"{last_row['SMH_1M_Ret']*100:+.1f}%", f"vs 50MA: {(last_row['SMH']/last_row['SMH_MA50']-1)*100:+.1f}%")
    m5.metric("SMH RSI", f"{last_row['SMH_RSI']:.1f}", "Target: > 50")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    df_recent = df.iloc[-500:]

    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color=line_c, width=2.5)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_qqq.update_layout(title=dict(text="QQQ vs 200MA", font=dict(family='DM Sans', size=16, color=t_color)), height=350, **chart_layout)
    chart_col1.plotly_chart(fig_qqq, use_container_width=True)
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color=line_c, width=2.5)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_tqqq.update_layout(title=dict(text="TQQQ vs 200MA", font=dict(family='DM Sans', size=16, color=t_color)), height=350, **chart_layout)
    chart_col2.plotly_chart(fig_tqqq, use_container_width=True)

elif page == "🍫 8-Pack Radar":
    st.markdown("<h2>8-Pack Radar</h2>", unsafe_allow_html=True)
    df_view   = df.iloc[-120:]
    qqq_rsi   = last_row['QQQ_RSI']
    qqq_dd    = last_row['QQQ_DD']
    vix_score = max(0, min(100, 100-(last_row['^VIX']-12)/28*100))
    dd_score  = max(0, min(100, (qqq_dd+0.20)/0.20*100))
    rsi_score = max(0, min(100, qqq_rsi))
    fg_score  = (vix_score+dd_score+rsi_score)/3
    
    sec_names = {'XLK':'TECH','XLV':'HEALTH','XLF':'FIN','XLY':'CONS','XLC':'COMM','XLI':'IND','XLP':'STAPLE','XLE':'ENGY','XLU':'UTIL','XLRE':'REAL','XLB':'MAT'}
    sec_data  = [{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
    sec_df    = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)

    risk_cnt, warn_cnt, safe_cnt = 0, 0, 0
    if qqq_rsi < 40: safe_cnt+=1
    elif qqq_rsi > 70: warn_cnt+=1
    else: safe_cnt+=1
        
    if qqq_dd < -0.20: risk_cnt+=1
    elif qqq_dd < -0.10: warn_cnt+=1
    else: safe_cnt+=1
        
    if fg_score < 30: safe_cnt+=1
    elif fg_score > 70: warn_cnt+=1
    else: safe_cnt+=1
        
    if last_row['HYG_IEF_Ratio'] < last_row['HYG_IEF_MA50']: risk_cnt+=1
    else: safe_cnt+=1
        
    if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0): warn_cnt+=1
    else: safe_cnt+=1
        
    if last_row['GLD_SPY_Ratio'] > last_row['GLD_SPY_MA50']: warn_cnt+=1
    else: safe_cnt+=1
        
    if last_row['UUP'] > last_row['UUP_MA50']: risk_cnt+=1
    else: safe_cnt+=1

    if risk_cnt >= 2:
        st.markdown(alert_banner("🔴 극단적 위험 구간 (Risk-Off)", f"위험 요소 {risk_cnt}개 / 경고 {warn_cnt}개", "복수의 매크로 지표에서 강력한 하락 경고가 발생했습니다.", "negative"), unsafe_allow_html=True)
    elif warn_cnt >= 3 or risk_cnt == 1:
        st.markdown(alert_banner("🟡 변동성 주의 (Warning)", f"위험 요소 {risk_cnt}개 / 경고 {warn_cnt}개", "시장의 균열 조짐이 감지되었습니다. 신규 매수를 보류하십시오.", "neutral"), unsafe_allow_html=True)
    else:
        st.markdown(alert_banner("🟢 안정적 순항 (Safe)", f"위험 요소 {risk_cnt}개 / 안전 {safe_cnt}개", "매크로 지표들이 안정적인 추세를 지지하고 있습니다.", "positive"), unsafe_allow_html=True)

    b1 = badge("BUY", "positive") if qqq_rsi<40 else (badge("OVER", "negative") if qqq_rsi>70 else badge("ACC", "neutral"))
    b2 = badge("BEAR(-20%)","negative") if qqq_dd<-0.20 else (badge("CORR(-10%)","neutral") if qqq_dd<-0.10 else badge("SAFE","positive"))
    b3 = badge("FEAR","positive") if fg_score<30 else (badge("GREED","negative") if fg_score>70 else badge("NEUTRAL","neutral"))
    b5 = badge("RISK OFF","negative") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else badge("RISK ON","positive")
    b6 = badge("NARROW","neutral") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0) else badge("BROAD","positive")
    b7 = badge("GOLD","neutral") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else badge("EQUITY","positive")
    b8 = badge("STRONG USD","negative") if last_row['UUP']>last_row['UUP_MA50'] else badge("WEAK USD","positive")

    radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="DM Sans", color=t_color))
    row1 = st.columns(4)
    with row1[0]:
        st.markdown(card_title("1. DCA (RSI)") + b1, unsafe_allow_html=True)
        fig1=go.Figure(); fig1.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_RSI'],line=dict(color=line_c,width=2.5)))
        fig1.add_hline(y=70,line_dash='dash',line_color=dash_c); fig1.add_hline(y=30,line_dash='dash',line_color=rsi_low_c)
        fig1.update_layout(**radar_layout,yaxis=dict(range=[10,90]),showlegend=False)
        st.plotly_chart(fig1,use_container_width=True)
    with row1[1]:
        st.markdown(card_title("2. Drawdown") + b2, unsafe_allow_html=True)
        fig2=go.Figure(); fig2.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_DD'],fill='tozeroy',line=dict(color=dash_c,width=2.5)))
        fig2.update_layout(**radar_layout,yaxis=dict(tickformat='.0%'),showlegend=False)
        st.plotly_chart(fig2,use_container_width=True)
    with row1[2]:
        st.markdown(card_title("3. Fear & Greed") + b3, unsafe_allow_html=True)
        gauge_steps = [{'range':[0,25],'color':"#FF4D4F"},{'range':[25,45],'color':"#E6A817"},{'range':[45,55],'color':"#EAECF0"},{'range':[55,100],'color':"#00C48C"}]
        fig3=go.Figure(go.Indicator(mode="gauge+number",value=fg_score,domain={'x':[0,1],'y':[0,1]}, gauge={'axis':{'range':[0,100]},'bar':{'color':line_c},'steps':gauge_steps}))
        fig3.update_layout(height=200,margin=dict(l=15,r=15,t=10,b=10),paper_bgcolor=b_color,font=dict(family="DM Sans",color=t_color))
        st.plotly_chart(fig3,use_container_width=True)
    with row1[3]:
        st.markdown(card_title("4. Sector (1M)") + badge("TREND", "positive"), unsafe_allow_html=True)
        fig4=go.Figure(go.Bar(x=sec_df['수익률'],y=sec_df['섹터'],orientation='h', marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']]))
        fig4.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig4,use_container_width=True)

    row2 = st.columns(4)
    with row2[0]:
        st.markdown(card_title("5. Credit Spread") + b5, unsafe_allow_html=True)
        fig5=go.Figure(); fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_Ratio'],line=dict(color=line_c,width=2.5)))
        fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_MA50'],line=dict(color=dash_c,dash='dot')))
        fig5.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig5,use_container_width=True)
    with row2[1]:
        st.markdown(card_title("6. Market Breadth") + b6, unsafe_allow_html=True)
        fig6=go.Figure(); fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_20d_Ret'],line=dict(color=line_c,width=2.5)))
        fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQE_20d_Ret'],line=dict(color=dash_c,dash='dot')))
        fig6.update_layout(**radar_layout,showlegend=False,yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6,use_container_width=True)
    with row2[2]:
        st.markdown(card_title("7. Gold / Equity") + b7, unsafe_allow_html=True)
        fig7=go.Figure(); fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_Ratio'],line=dict(color=line_c,width=2.5)))
        fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_MA50'],line=dict(color=dash_c,dash='dot')))
        fig7.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig7,use_container_width=True)
    with row2[3]:
        st.markdown(card_title("8. USD (UUP)") + b8, unsafe_allow_html=True)
        fig8=go.Figure(); fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP'],line=dict(color=line_c,width=2.5)))
        fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP_MA50'],line=dict(color=dash_c,dash='dot')))
        fig8.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig8,use_container_width=True)

# (Portfolio, Backtest Lab, Macro News 탭은 레이아웃 파괴 없이 적용된 새 CSS를 상속받습니다)
else:
    st.info("해당 메뉴는 업데이트가 진행 중이거나 제공해주신 코드 영역 밖에 있습니다.")
