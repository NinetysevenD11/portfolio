import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
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
st.set_page_config(page_title="AMLS V4.5 FINANCE STRATEGY", layout="wide", page_icon="🌿", initial_sidebar_state="expanded")

# --- 🎨 테마 커스텀 시스템 ---
if 'main_color' not in st.session_state:
    st.session_state.main_color = '#10B981'
main_color = st.session_state.main_color

def hex_to_rgb(hex_col):
    h = hex_col.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
r_c, g_c, b_c = hex_to_rgb(main_color)

def apply_theme(text):
    if not isinstance(text, str): return text
    text = text.replace("#10B981", main_color)
    text = text.replace("#10b981", main_color)
    text = text.replace("16, 185, 129", f"{r_c}, {g_c}, {b_c}")
    text = text.replace("16,185,129", f"{r_c},{g_c},{b_c}")
    return text

SECTOR_TICKERS = ['XLK','XLV','XLF','XLY','XLC','XLI','XLP','XLE','XLU','XLRE','XLB']
CORE_TICKERS   = ['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD','^VIX','HYG','IEF','QQQE','UUP','^TNX','BTC-USD','IWM']
TICKERS        = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST     = ['TQQQ','SOXL','USD','QLD','SSO','SPY','QQQ','GLD','CASH']

PORTFOLIO_FILE = 'portfolio_autosave.json'

def sanitize_portfolio():
    for a in ASSET_LIST:
        val = st.session_state.portfolio.get(a)
        if isinstance(val, (int, float)) or val is None:
            st.session_state.portfolio[a] = {'shares': float(val or 0.0), 'avg_price': 1.0 if a == 'CASH' else 0.0, 'fx': 1350.0}
        elif isinstance(val, dict):
            if 'shares' not in val: val['shares'] = 0.0
            if 'avg_price' not in val: val['avg_price'] = 1.0 if a == 'CASH' else 0.0
            if 'fx' not in val: val['fx'] = 1350.0
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
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"),
                       end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)['Close']
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
    df['VIX_MA50']      = df['^VIX'].rolling(50).mean()
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
    df['TNX_MA50']      = df['^TNX'].rolling(50).mean()
    df['BTC_MA50']      = df['BTC-USD'].rolling(50).mean()
    df['IWM_SPY_Ratio'] = df['IWM'] / df['SPY']
    df['IWM_SPY_MA50']  = df['IWM_SPY_Ratio'].rolling(50).mean()
    for sec in SECTOR_TICKERS: df[f'{sec}_1M'] = df[sec].pct_change(21)
    return df.dropna()

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

@st.cache_data(ttl=3600)
def load_custom_backtest_data(start_date, end_date):
    fetch_start = pd.to_datetime(start_date) - timedelta(days=400)
    f_start_str = fetch_start.strftime("%Y-%m-%d")
    f_end_str = (pd.to_datetime(end_date) + timedelta(days=1)).strftime("%Y-%m-%d")
    data = yf.download(TICKERS, start=f_start_str, end=f_end_str, progress=False, auto_adjust=True)['Close']
    bt_df = pd.DataFrame(index=data.index)
    for t in TICKERS: bt_df[t] = data[t]
    bt_df = bt_df.ffill().bfill()
    bt_df['QQQ_MA20']      = bt_df['QQQ'].rolling(20).mean()
    bt_df['QQQ_MA50']      = bt_df['QQQ'].rolling(50).mean()
    bt_df['QQQ_MA200']     = bt_df['QQQ'].rolling(200).mean()
    bt_df['TQQQ_MA200']    = bt_df['TQQQ'].rolling(200).mean()
    bt_df['SMH_MA50']      = bt_df['SMH'].rolling(50).mean()
    bt_df['VIX_MA5']       = bt_df['^VIX'].rolling(5).mean()
    bt_df['VIX_MA20']      = bt_df['^VIX'].rolling(20).mean()
    bt_df['VIX_MA50']      = bt_df['^VIX'].rolling(50).mean()
    bt_df['SMH_3M_Ret']    = bt_df['SMH'].pct_change(63)
    bt_df['SMH_1M_Ret']    = bt_df['SMH'].pct_change(21)
    bt_df['SMH_RSI']       = ta.rsi(bt_df['SMH'], length=14)
    bt_df['HYG_IEF_Ratio'] = bt_df['HYG'] / bt_df['IEF']
    bt_df['HYG_IEF_MA20']  = bt_df['HYG_IEF_Ratio'].rolling(20).mean()
    bt_df['HYG_IEF_MA50']  = bt_df['HYG_IEF_Ratio'].rolling(50).mean()
    bt_df['QQQ_20d_Ret']   = bt_df['QQQ'].pct_change(20)
    bt_df['QQQE_20d_Ret']  = bt_df['QQQE'].pct_change(20)
    bt_df['QQQ_RSI']       = ta.rsi(bt_df['QQQ'], length=14)
    bt_df['GLD_SPY_Ratio'] = bt_df['GLD'] / bt_df['SPY']
    bt_df['GLD_SPY_MA50']  = bt_df['GLD_SPY_Ratio'].rolling(50).mean()
    bt_df['QQQ_High52']    = bt_df['QQQ'].rolling(252).max()
    bt_df['QQQ_DD']        = (bt_df['QQQ'] / bt_df['QQQ_High52']) - 1
    bt_df['UUP_MA50']      = bt_df['UUP'].rolling(50).mean()
    bt_df['TNX_MA50']      = bt_df['^TNX'].rolling(50).mean()
    bt_df['BTC_MA50']      = bt_df['BTC-USD'].rolling(50).mean()
    bt_df['IWM_SPY_Ratio'] = bt_df['IWM'] / bt_df['SPY']
    bt_df['IWM_SPY_MA50']  = bt_df['IWM_SPY_Ratio'].rolling(50).mean()
    bt_df = bt_df.dropna()
    if bt_df.empty: return bt_df
    bt_df['Target'] = bt_df.apply(get_target_v45, axis=1)
    bt_df['Regime'] = apply_asymmetric_delay(bt_df['Target'])
    bt_df = bt_df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]
    return bt_df

REALTIME_TICKERS = ['QQQ','TQQQ','SMH','^VIX','HYG','IEF','UUP','GLD','SPY','SOXL','USD','QLD','SSO','USDKRW=X', '^TNX', 'BTC-USD', 'IWM']

@st.cache_data(ttl=60)
def fetch_realtime_prices():
    prices = {}
    for ticker in REALTIME_TICKERS:
        try:
            info  = yf.Ticker(ticker).fast_info
            price = info.get('last_price') or info.get('lastPrice')
            if price and price > 0: prices[ticker] = float(price)
        except: pass
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    fetch_time = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    return prices, fetch_time

@st.cache_data(ttl=1800)
def fetch_fear_and_greed():
    try:
        url = "https://production.api.cnn.io/data/ext/fear_and_greed/latest"
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        req = urllib.request.Request(url, headers=headers)
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode('utf-8'))
        return float(data['fear_and_greed']['score'])
    except: return None

@st.cache_data(ttl=900)
def fetch_macro_news():
    headlines_for_ai, news_items = [], []
    try:
        search_query = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url  = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
        req  = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(urllib.request.urlopen(req).read())
        for item in root.findall('.//item')[:12]:
            t, l, d = item.find('title').text, item.find('link').text, item.find('pubDate').text
            headlines_for_ai.append(t); news_items.append({"title":t,"link":l,"date":d[:-4]})
    except: pass
    return headlines_for_ai, news_items

with st.spinner('데이터 수집 중...'):
    df = load_data()
    rt_prices, last_update_time = fetch_realtime_prices()

if df is None or df.empty:
    st.error("🚨 야후 파이낸스(Yahoo Finance) 통신 지연. 잠시 후 새로고침 해주세요.")
    st.stop()

last_index = df.index[-1]
rt_injected = []
for ticker, price in rt_prices.items():
    if ticker in df.columns and price > 0:
        df.at[last_index, ticker] = price
        rt_injected.append(ticker)

if 'QQQ' in rt_injected:
    df.at[last_index, 'QQQ_DD'] = (df.at[last_index, 'QQQ'] / df['QQQ_High52'].iloc[-1]) - 1
if 'HYG' in rt_injected and 'IEF' in rt_injected:
    df.at[last_index, 'HYG_IEF_Ratio'] = df.at[last_index, 'HYG'] / df.at[last_index, 'IEF']
if 'IWM' in rt_injected and 'SPY' in rt_injected:
    df.at[last_index, 'IWM_SPY_Ratio'] = df.at[last_index, 'IWM'] / df.at[last_index, 'SPY']

last_row = df.iloc[-1].copy()

rt_ok    = len(rt_injected) >= 3
rt_label = f"⬤ LIVE  {len(rt_injected)} feeds" if rt_ok else "⬤ DELAYED"

vix_close, vix_ma5, vix_ma20 = last_row['^VIX'], last_row['VIX_MA5'], last_row['VIX_MA20']
qqq_close, qqq_ma50, qqq_ma200 = last_row['QQQ'], last_row['QQQ_MA50'], last_row['QQQ_MA200']
smh_close, smh_ma50, smh_3m, smh_1m, smh_rsi = (last_row['SMH'], last_row['SMH_MA50'],
    last_row['SMH_3M_Ret'], last_row['SMH_1M_Ret'], last_row['SMH_RSI'])

df['Target'] = df.apply(get_target_v45, axis=1)
df['Regime'] = apply_asymmetric_delay(df['Target'])

live_regime   = get_target_v45(last_row)
hist_regime   = int(df.iloc[-2]['Regime'])
curr_regime   = live_regime if live_regime > hist_regime else hist_regime
target_regime = live_regime

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

if curr_regime == live_regime: regime_committee_msg = "🟢 조건 부합 (안정)"
elif live_regime > curr_regime: regime_committee_msg = f"🔴 R{live_regime} 하향 즉시 반영"
else: regime_committee_msg = f"🟡 R{live_regime} 승급 대기 (5일)"

# ==========================================
# 2. 라이트 테마 색상 변수 (차트용)
# ==========================================
b_color   = 'rgba(0,0,0,0)'
t_color   = '#4A4A57'        # 차트 축 텍스트
line_c    = main_color
dash_c    = '#B0B0BE'
rsi_low_c = main_color

# ⚠️ xaxis/yaxis를 여기서 제외 → 각 차트에서 개별 지정 (중복 키 TypeError 방지)
chart_layout = dict(
    paper_bgcolor=b_color,
    plot_bgcolor=b_color,
    font=dict(family="DM Mono, DM Sans, monospace", color=t_color),
    margin=dict(l=0, r=0, t=40, b=0),
)
radar_layout = dict(
    height=200,
    margin=dict(l=10, r=10, t=15, b=15),
    paper_bgcolor=b_color,
    plot_bgcolor=b_color,
    font=dict(family="DM Mono, DM Sans, monospace", color=t_color),
)

# 공통 축 스타일 (라이트 테마)
_ax = dict(gridcolor='rgba(0,0,0,0.07)', linecolor='rgba(0,0,0,0.12)', showgrid=True, zeroline=False)
_ax_r = dict(gridcolor='rgba(0,0,0,0.07)', zeroline=False, showgrid=True)

regime_info = {1:("R1  BULL","풀 가동"),2:("R2  CORR","방어 진입"), 3:("R3  BEAR","대피"),4:("R4  PANIC","최대 방어")}

# ==========================================
# 3. CSS  —  Refined Institutional  (2026)
#    Concept: Bloomberg × Swiss Grid × Monocle
#    → Ruled structure, tabular precision, zero decoration
# ==========================================
css_block = f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap');

    /* ── DESIGN TOKENS ──────────────────────────────── */
    :root {{
        /* Paper — warm ivory, not cold white */
        --paper:      #F7F6F2;
        --paper-2:    #EFEDE7;
        --paper-3:    #E8E5DD;
        --ink:        #111118;
        --ink-2:      #2C2C35;
        --ink-3:      #4A4A57;
        --ink-4:      #6B6B7A;
        --ink-5:      #9494A0;
        /* Rule lines */
        --rule:       rgba(0,0,0,0.10);
        --rule-strong:rgba(0,0,0,0.18);
        /* Accent — single color, surgical use */
        --acc:        #10B981;
        --acc-pale:   rgba(16,185,129,0.08);
        --acc-mid:    rgba(16,185,129,0.18);
        --acc-line:   rgba(16,185,129,0.40);
        /* State colors */
        --bull:       #059669;
        --bear:       #DC2626;
        --warn:       #D97706;
        /* Spacing unit */
        --u:          8px;
    }}

    /* ── RESET / BASE ───────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; }}

    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: var(--paper) !important;
        background-image:
            /* Subtle dot grid — institutional graph paper */
            radial-gradient(circle, rgba(0,0,0,0.055) 1px, transparent 1px),
            /* Accent corner wash */
            radial-gradient(ellipse 70% 40% at 5% 0%, rgba(16,185,129,0.055) 0%, transparent 55%) !important;
        background-size: 24px 24px, 100% 100% !important;
        color: var(--ink) !important;
        font-family: 'DM Sans', sans-serif;
        font-size: 14px;
    }}

    [data-testid="stHeader"] {{
        background: rgba(247,246,242,0.92) !important;
        backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--rule-strong);
    }}
    #MainMenu {{ visibility:hidden; }} footer {{ visibility:hidden; }}
    .main .block-container {{
        max-width: 1540px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }}

    /* ── SIDEBAR ────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: var(--paper-2) !important;
        border-right: 1px solid var(--rule-strong) !important;
        box-shadow: none !important;
    }}
    /* Vertical accent rule on right edge */
    [data-testid="stSidebar"]::after {{
        content:'';
        position:absolute; top:15%; right:0; width:2px; height:70%;
        background:linear-gradient(180deg, transparent, var(--acc-line), transparent);
        pointer-events:none;
    }}

    /* Sidebar radio → ruled nav rows */
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] > div:first-child {{ display:none !important; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
        gap:0px !important; padding:0 !important; background:transparent !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] {{
        display:flex !important; align-items:center !important;
        padding:10px 20px !important; margin:0 !important;
        border-radius:0 !important;
        border:none !important;
        border-bottom:1px solid var(--rule) !important;
        background:transparent !important;
        cursor:pointer !important; width:100% !important;
        transition:background 0.15s ease !important;
        position:relative;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] p {{
        color:var(--ink-3) !important; font-weight:500 !important;
        font-size:0.82rem !important; margin:0 !important;
        font-family:'DM Sans' !important; letter-spacing:0.01em !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:hover {{
        background:var(--paper-3) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {{
        background:var(--paper) !important;
        border-bottom:1px solid var(--rule) !important;
    }}
    /* Active indicator — left border bar */
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked)::before {{
        content:'';
        position:absolute; left:0; top:0; bottom:0; width:3px;
        background:var(--acc);
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p {{
        color:var(--ink) !important; font-weight:700 !important;
    }}

    .sidebar-link {{
        display:flex; align-items:center; gap:10px;
        padding:10px 20px; margin:0;
        border-bottom:1px solid var(--rule);
        text-decoration:none !important;
        color:var(--ink-3) !important;
        font-weight:500; font-size:0.82rem;
        transition:background 0.15s; background:transparent;
        font-family:'DM Sans';
        position:relative;
    }}
    .sidebar-link:hover {{
        background:var(--paper-3) !important;
        color:var(--ink) !important;
    }}

    /* ── INSTITUTIONAL PANEL (replaces glass-card) ──── */
    /* Ruled panels — no floating, no shadows, just structure */
    .glass-card {{
        background: #FAFAF7 !important;
        border: 1px solid var(--rule-strong) !important;
        border-top: 2px solid var(--ink-2) !important;
        border-radius: 0 !important;
        padding: 20px 22px !important;
        box-shadow: none !important;
        height: 100%; display:flex; flex-direction:column;
        justify-content:space-between;
        transition: border-top-color 0.2s ease;
        position:relative;
    }}
    .glass-card:hover {{
        border-top-color: var(--acc) !important;
        transform: none !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06) !important;
    }}
    .glass-card h3 {{
        font-family: 'DM Mono', monospace !important;
        font-size: 0.6em !important; font-weight: 400 !important;
        color: var(--ink-4) !important;
        margin-bottom: 14px !important;
        letter-spacing: 0.20em; text-transform: uppercase;
        border-bottom: 1px solid var(--rule); padding-bottom: 9px;
    }}

    /* Inset — subtle ruled box */
    .glass-inset {{
        background: var(--paper-2) !important;
        border: 1px solid var(--rule) !important;
        border-left: 3px solid var(--acc) !important;
        border-radius: 0 !important;
        padding: 14px 16px 12px !important;
        text-align: left; margin-bottom: 14px;
        box-shadow: none !important;
    }}

    /* Streamlit container(border=True) */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background: #FAFAF7 !important;
        border: 1px solid var(--rule-strong) !important;
        border-top: 2px solid var(--ink-2) !important;
        border-radius: 0 !important;
        padding: 20px 22px !important;
        box-shadow: none !important;
        transition: border-top-color 0.2s ease;
        position:relative;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{
        border-top-color: var(--acc) !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06) !important;
        transform: none !important;
    }}

    /* ── METRIC CARDS ───────────────────────────────── */
    [data-testid="stMetric"] {{
        background: #FAFAF7 !important;
        border: 1px solid var(--rule-strong) !important;
        border-top: 2px solid var(--ink-2) !important;
        border-radius: 0 !important;
        padding: 16px 18px !important;
        box-shadow: none !important;
        margin-bottom: 8px;
        transition: border-top-color 0.2s;
        position:relative;
    }}
    [data-testid="stMetric"]:hover {{
        border-top-color: var(--acc) !important;
        transform: none !important;
    }}
    [data-testid="stMetricLabel"] > div > div > p {{
        font-size: 0.65em !important; font-weight: 500; color: var(--ink-4) !important;
        white-space:normal !important; letter-spacing: 0.14em; text-transform:uppercase;
        font-family:'DM Mono', monospace !important;
    }}
    [data-testid="stMetricValue"] > div {{
        font-family:'DM Mono', monospace !important;
        font-size:1.4em !important; font-weight:400;
        color:var(--ink) !important;
        font-variant-numeric: tabular-nums;
    }}
    div[data-testid="stMetricDelta"] > div {{
        font-size:0.8em !important; font-weight:500;
        font-family:'DM Mono', monospace !important;
        font-variant-numeric: tabular-nums;
    }}

    /* ── BUTTONS ────────────────────────────────────── */
    [data-testid="stButton"] > button {{
        background: transparent !important;
        border: 1px solid var(--rule-strong) !important;
        color: var(--ink-2) !important;
        border-radius: 0 !important;
        padding: 7px 16px !important;
        font-weight: 500 !important; font-size: 0.78em !important;
        transition: all 0.15s ease !important;
        font-family:'DM Mono', monospace !important;
        letter-spacing: 0.06em; text-transform: uppercase;
    }}
    [data-testid="stButton"] > button:hover {{
        background: var(--acc-pale) !important;
        border-color: var(--acc-line) !important;
        color: var(--bull) !important;
    }}

    /* ── TYPOGRAPHY ─────────────────────────────────── */
    h1 {{
        font-family: 'Instrument Serif', serif !important;
        font-size: 2.4em !important; font-weight: 400 !important;
        letter-spacing: -0.5px; margin: 0 !important;
        color: var(--ink) !important; font-style: italic;
    }}
    h2 {{
        font-family: 'DM Sans', sans-serif !important;
        color: var(--ink) !important; font-weight: 700 !important;
        letter-spacing: -0.3px;
    }}
    h3 {{ font-family: 'DM Sans', sans-serif !important; color: var(--ink-2) !important; }}
    p  {{ color: var(--ink-3) !important; line-height: 1.65; }}
    strong {{ color: var(--ink) !important; }}

    /* All numbers — tabular figures */
    [data-testid="stMetricValue"],
    .cval, .mint-table td {{ font-variant-numeric: tabular-nums; }}

    /* ── DATA ROWS ──────────────────────────────────── */
    .crow {{
        display:flex; justify-content:space-between; align-items:center;
        padding: 8px 0;
        border-bottom: 1px solid var(--rule);
        font-size: 0.83em;
    }}
    .crow:last-child {{ border-bottom:none; }}
    .clabel {{
        color: var(--ink-3); font-weight:500;
        font-family:'DM Sans'; font-size:1em;
    }}
    .cval {{
        font-family:'DM Mono', monospace; font-weight:400;
        color:#10B981; font-size:0.9em;
        letter-spacing:0.02em; font-variant-numeric:tabular-nums;
    }}

    /* ── RADAR LINKS ────────────────────────────────── */
    .radar-link {{ text-decoration:none !important; display:block; }}
    .radar-link-title {{
        font-size:0.62em; font-weight:500; color:var(--ink-4);
        transition:color 0.15s; font-family:'DM Mono', monospace;
        letter-spacing:0.16em; text-transform:uppercase;
    }}
    .radar-link:hover .radar-link-title {{ color:var(--acc) !important; }}

    /* ── TABLES ─────────────────────────────────────── */
    .mint-table {{
        width:100%; border-collapse:collapse;
        font-family:'DM Mono', monospace;
    }}
    .mint-table th {{
        padding:8px 12px; font-weight:400; color:var(--ink-4);
        text-align:right; font-size:0.68em;
        letter-spacing:0.16em; text-transform:uppercase;
        border-bottom: 2px solid var(--ink-3);
        background: var(--paper-2);
    }}
    .mint-table td {{
        padding:10px 12px;
        background: #FAFAF7;
        color:var(--ink-2); text-align:right;
        border-bottom: 1px solid var(--rule);
        font-size:0.8em;
        font-variant-numeric:tabular-nums;
        transition:background 0.12s;
    }}
    .mint-table tr:hover td {{ background:var(--acc-pale); }}
    .mint-table td:first-child {{
        border-left:3px solid transparent;
        text-align:left; font-family:'DM Sans';
        font-weight:700; color:var(--bull);
        font-size:0.82em;
    }}
    .mint-table tr:hover td:first-child {{ border-left-color:var(--acc); }}
    .mint-table th:first-child {{ text-align:left; }}

    /* ── INPUTS ─────────────────────────────────────── */
    [data-testid="stNumberInput"] > div > div,
    [data-testid="stTextInput"] > div > div {{
        background:#FAFAF7 !important;
        border:1px solid var(--rule-strong) !important;
        border-radius:0 !important;
        color:var(--ink) !important;
    }}
    [data-testid="stDateInput"] > div > div {{
        background:#FAFAF7 !important;
        border:1px solid var(--rule-strong) !important;
        border-radius:0 !important;
        color:var(--ink) !important;
    }}
    [data-baseweb="select"] > div {{
        background:#FAFAF7 !important;
        border:1px solid var(--rule-strong) !important;
        border-radius:0 !important;
    }}

    /* ── FILE UPLOADER ──────────────────────────────── */
    [data-testid="stFileUploader"] {{
        background:var(--paper-2) !important;
        border:1px dashed var(--rule-strong) !important;
        border-radius:0 !important;
    }}

    /* ── EXPANDERS ──────────────────────────────────── */
    [data-testid="stExpander"] {{
        background:#FAFAF7 !important;
        border:1px solid var(--rule-strong) !important;
        border-radius:0 !important;
    }}

    /* ── DIVIDERS ───────────────────────────────────── */
    hr {{ border-color:var(--rule-strong) !important; }}

    /* ── SCROLLBAR ──────────────────────────────────── */
    ::-webkit-scrollbar {{ width:3px; height:3px; }}
    ::-webkit-scrollbar-track {{ background:var(--paper-2); }}
    ::-webkit-scrollbar-thumb {{ background:var(--ink-5); }}
    ::-webkit-scrollbar-thumb:hover {{ background:var(--ink-3); }}

    /* ── ANIMATIONS ─────────────────────────────────── */
    @keyframes pulseGlow {{
        0%,100% {{ opacity:1; }}
        50% {{ opacity:0.7; }}
    }}
    @keyframes fadeUp {{
        from {{ opacity:0; transform:translateY(10px); }}
        to   {{ opacity:1; transform:translateY(0); }}
    }}
    .live-pulse {{ animation:pulseGlow 2.8s ease-in-out infinite; }}

    .main .block-container > div > div:nth-child(1) {{ animation:fadeUp 0.35s ease 0.05s both; }}
    .main .block-container > div > div:nth-child(2) {{ animation:fadeUp 0.35s ease 0.10s both; }}
    .main .block-container > div > div:nth-child(3) {{ animation:fadeUp 0.35s ease 0.15s both; }}
    .main .block-container > div > div:nth-child(4) {{ animation:fadeUp 0.35s ease 0.20s both; }}
    .main .block-container > div > div:nth-child(5) {{ animation:fadeUp 0.35s ease 0.25s both; }}

    /* ── DATA EDITOR (portfolio table) ─────────────── */
    [data-testid="stDataEditor"] {{
        border:1px solid var(--rule-strong) !important;
        border-radius:0 !important;
    }}

    /* ── SIDEBAR TEXT OVERRIDES ─────────────────────── */
    [data-testid="stSidebar"] p      {{ color:var(--ink-3) !important; }}
    [data-testid="stSidebar"] strong {{ color:var(--ink)   !important; }}

    /* ── DATA TABLE (stDataFrame) ───────────────────── */
    [data-testid="stDataFrame"] {{
        border:1px solid var(--rule-strong) !important;
        border-radius:0 !important;
    }}
</style>"""


st.markdown(apply_theme(css_block), unsafe_allow_html=True)

# ==========================================
# 4. 사이드바 UI  —  Dark Glass Terminal
# ==========================================
sidebar_top = st.sidebar.container()
sidebar_top.markdown(apply_theme(f"""
<div style="padding:20px 20px 14px; border-bottom:1px solid rgba(0,0,0,0.10);">
    <div style="font-family:'DM Mono'; font-size:0.58em; color:#9494A0; letter-spacing:0.22em; text-transform:uppercase; margin-bottom:8px;">Quantitative Engine</div>
    <div style="font-family:'Instrument Serif',serif; font-size:1.7em; font-weight:400; font-style:italic; color:#111118; letter-spacing:-0.3px; line-height:1.1; margin-bottom:12px;">
        AMLS <span style="color:#10B981;">V4.5</span>
    </div>
    <div class="live-pulse" style="display:inline-flex; align-items:center; gap:5px; font-family:'DM Mono'; font-size:0.65em; color:#059669; padding:4px 10px; background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); letter-spacing:0.06em;">
        {rt_label}
    </div>
</div>
"""), unsafe_allow_html=True)

st.sidebar.markdown("""<div style="font-family:'DM Mono'; font-size:0.62em; font-weight:400; color:#4A5568; letter-spacing:0.2em; text-transform:uppercase; padding:14px 15px 6px;">Navigation</div>""", unsafe_allow_html=True)
page = st.sidebar.radio("MENU",
    ["📊 Dashboard", "💼 Portfolio", "🍫 12-Pack Radar", "📈 Backtest Lab", "📰 Macro News"],
    label_visibility="collapsed")

st.sidebar.markdown("""<div style="font-family:'DM Mono'; font-size:0.62em; font-weight:400; color:#4A5568; letter-spacing:0.2em; text-transform:uppercase; padding:6px 15px;">Theme Color</div>""", unsafe_allow_html=True)
col1, col2, col3 = st.sidebar.columns([0.1, 1, 0.1])
with col2:
    new_color = st.color_picker("메인 컬러", st.session_state.main_color, label_visibility="collapsed", key="cp_theme")
    if new_color != st.session_state.main_color:
        st.session_state.main_color = new_color
        st.rerun()

st.sidebar.markdown("""<div style="font-family:'DM Mono'; font-size:0.62em; font-weight:400; color:#4A5568; letter-spacing:0.2em; text-transform:uppercase; padding:6px 15px;">Bookmarks</div>""", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="display:flex; flex-direction:column; gap:0px; padding:0 12px;">
    <a href="https://www.youtube.com/@JB_Insight" target="_blank" class="sidebar-link">📊 JB 인사이트</a>
    <a href="https://www.youtube.com/@odokgod" target="_blank" class="sidebar-link">📻 오독</a>
    <a href="https://www.youtube.com/@TQQQCRAZY" target="_blank" class="sidebar-link">🔥 TQQQ 미친놈</a>
    <a href="https://www.youtube.com/@developmong" target="_blank" class="sidebar-link">🐒 디벨롭몽</a>
    <a href="https://kr.investing.com/" target="_blank" class="sidebar-link">🌍 인베스팅닷컴</a>
    <a href="https://kr.tradingview.com/" target="_blank" class="sidebar-link">📉 트레이딩뷰</a>
    <a href="https://claude.ai/" target="_blank" class="sidebar-link">🧠 클로드</a>
    <a href="https://gemini.google.com/" target="_blank" class="sidebar-link">✨ 제미나이</a>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 5. 메인 헤더  —  Editorial Bento Style
# ==========================================

# ① 풀 너비 상단 인트로 스트립 (타이틀 + 컨트롤 인라인)
_qqq_chg  = (last_row['QQQ'] / last_row['QQQ_MA200'] - 1) * 100
_vix_now  = last_row['^VIX']
_smh_chg  = last_row['SMH_1M_Ret'] * 100

def _pill(label, value, color):
    return (f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'padding:8px 18px;background:#FFFFFF;border:1px solid rgba(0,0,0,0.07);'
            f'border-top:2px solid {color};border-radius:12px;min-width:90px;">'
            f'<span style="font-family:\'DM Mono\';font-size:0.6em;color:#4A5568;letter-spacing:0.14em;text-transform:uppercase;">{label}</span>'
            f'<span style="font-family:\'DM Mono\';font-size:1.05em;font-weight:500;color:#0F172A;margin-top:2px;">{value}</span>'
            f'</div>')

_p_qqq  = _pill("QQQ/200MA", f"{_qqq_chg:+.1f}%", main_color if _qqq_chg >= 0 else "#EF4444")
_p_vix  = _pill("VIX", f"{_vix_now:.1f}", main_color if _vix_now < 20 else ("#F59E0B" if _vix_now < 30 else "#EF4444"))
_p_smh  = _pill("SMH 1M", f"{_smh_chg:+.1f}%", main_color if _smh_chg >= 0 else "#EF4444")
_p_reg  = _pill("REGIME", f"R{curr_regime}", main_color)

_hdr_left = apply_theme(f"""
<div style="display:flex;flex-direction:column;justify-content:center;">
    <div style="font-family:'Syne';font-size:2.5em;font-weight:800;letter-spacing:-2px;color:#0F172A;line-height:1;">
        AMLS <span style="color:#10B981;">V4.5</span>
    </div>
    <div style="font-family:'DM Mono';font-size:0.65em;color:#4A5568;letter-spacing:0.22em;text-transform:uppercase;margin-top:4px;">
        The Wall Street Quantitative Strategy
    </div>
</div>
""")

_hdr_right = apply_theme(f"""
<div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">
    <div style="display:flex;gap:6px;">
        {_p_qqq}{_p_vix}{_p_smh}{_p_reg}
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <div class="live-pulse" style="font-family:'DM Mono';font-size:0.68em;color:#059669;padding:4px 12px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);border-radius:6px;letter-spacing:0.06em;">{rt_label}</div>
        <div style="font-family:'DM Mono';font-size:0.68em;color:#4A5568;letter-spacing:0.04em;">⏱ {last_update_time}</div>
    </div>
</div>
""")

hdr_c1, hdr_c2 = st.columns([1, 1.6])
with hdr_c1:
    st.markdown(_hdr_left, unsafe_allow_html=True)
with hdr_c2:
    c_sync1, c_sync2 = st.columns([4, 1])
    with c_sync2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("↺ 동기화", use_container_width=True):
            fetch_realtime_prices.clear()
            load_data.clear()
            st.rerun()
    with c_sync1:
        st.markdown(_hdr_right, unsafe_allow_html=True)

st.markdown(apply_theme(f"""
<div style="position:relative;margin:14px 0 24px;height:1px;background:rgba(0,0,0,0.07);">
    <div style="position:absolute;left:0;top:0;width:100%;height:1px;background:rgba(0,0,0,0.12);"></div>
    <div style="position:absolute;left:0;top:-1px;width:80px;height:3px;background:var(--acc);"></div>
</div>
"""), unsafe_allow_html=True)

# ==========================================
# 6. 페이지 라우팅
# ==========================================
if page == "📊 Dashboard":

    def _lg_row(label, val, passed):
        icon  = "●" if passed else "○"
        color = main_color if passed else "#CBD5E1"
        if isinstance(val, (int, float)):
            val_str = f"${val:.2f}" if val > 5 else f"{val:.2f}"
        elif isinstance(val, str) and '%' in val:
            val_str = val
        else:
            val_str = str(val)
        return (f'<div class="crow">'
                f'<span class="clabel">{label}</span>'
                f'<span class="cval" style="color:{color};">{val_str} <span style="font-size:0.75em;">{icon}</span></span>'
                f'</div>')

    soxl_title = "SOXL  APPROVED" if smh_cond else "USD  DEFENSE"
    soxl_strat = "3× Leverage Active" if smh_cond else "2× Defense Mode"
    soxl_color = main_color if smh_cond else "#94A3B8"

    weight_rows = "".join([
        f'<div class="crow">'
        f'<span class="clabel" style="font-family:\'DM Mono\'; font-size:0.95em;">{k}</span>'
        f'<span class="cval">{v*100:.0f}%</span>'
        f'</div>'
        for k, v in target_weights.items() if v > 0
    ])

    # ── ① Mission Control  풀너비 배너 ──────────────────────────
    r_colors = {1: main_color, 2: "#F59E0B", 3: "#EF4444", 4: "#7C3AED"}
    r_labels = {1: "R1  BULL", 2: "R2  CORR", 3: "R3  BEAR", 4: "R4  PANIC"}
    regime_tabs_html = ""
    for r in [1, 2, 3, 4]:
        is_active = (r == curr_regime)
        bg   = f"rgba({r_c},{g_c},{b_c},0.12)" if is_active else "rgba(0,0,0,0.03)"
        bdr  = f"2px solid {r_colors[r]}" if is_active else "2px solid transparent"
        ftxt = r_colors[r] if is_active else "#CBD5E1"
        fw   = "700" if is_active else "400"
        regime_tabs_html += (
            f'<div style="flex:1;text-align:center;padding:10px 6px;border-radius:10px;'
            f'background:{bg};border:{bdr};transition:all 0.2s;">'
            f'<div style="font-family:\'Syne\';font-size:0.95em;font-weight:{fw};color:{ftxt};">{r_labels[r]}</div>'
            f'<div style="font-family:\'DM Mono\';font-size:0.6em;color:#4A5568;margin-top:2px;letter-spacing:0.1em;">'
            f'{regime_info[r][1]}</div></div>'
        )

    st.markdown(apply_theme(f"""
    <div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);border-top:2px solid #111118;
        border-radius:0;padding:16px 20px;margin-bottom:14px;
        box-shadow:none;">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px;">
            <span style="font-family:'DM Mono';font-size:0.62em;color:#4A5568;letter-spacing:0.2em;text-transform:uppercase;">Mission Control</span>
            <div style="flex:1;height:1px;background:rgba(0,0,0,0.05);"></div>
            <span style="font-family:'DM Mono';font-size:0.72em;padding:3px 10px;border-radius:6px;
                background:rgba(16,185,129,0.08);color:#059669;border:1px solid rgba(16,185,129,0.25);font-size:0.65em;letter-spacing:0.08em;padding:3px 10px;">
                {regime_committee_msg}
            </span>
        </div>
        <div style="display:flex;gap:8px;">{regime_tabs_html}</div>
    </div>
    """), unsafe_allow_html=True)

    # ── ② Bento Grid  비대칭 3칸 ────────────────────────────────
    c1, c2, c3 = st.columns([1.6, 1.4, 1])
    with c1:
        st.markdown(apply_theme(f"""<div class="glass-card">
            <h3>Market Regime  ·  Signal Conditions</h3>
            <div class="glass-inset" style="text-align:left;padding:16px 20px;">
                <div style="display:flex;align-items:baseline;gap:12px;">
                    <span style="color:#10B981;font-family:'Syne';font-size:2em;font-weight:800;letter-spacing:-1px;">{regime_info[curr_regime][0]}</span>
                    <span style="font-family:'DM Mono';font-size:0.72em;color:#344054;letter-spacing:0.12em;text-transform:uppercase;">{regime_info[curr_regime][1]}</span>
                </div>
            </div>
            {_lg_row('VIX < 40', f'{vix_close:.2f}', vix_close<=40)}
            {_lg_row('QQQ > 200MA', f'${qqq_close:.2f}', qqq_close>=qqq_ma200)}
            {_lg_row('50MA ≥ 200MA', f'${qqq_ma50:.2f}', qqq_ma50>=qqq_ma200)}
        </div>"""), unsafe_allow_html=True)

    with c2:
        st.markdown(apply_theme(f"""<div class="glass-card">
            <h3>Semi-Conductor  ·  SOXL Gate</h3>
            <div class="glass-inset" style="text-align:left;padding:16px 20px;">
                <div style="display:flex;align-items:baseline;gap:10px;">
                    <span style="color:{soxl_color};font-family:'Syne';font-size:1.3em;font-weight:800;">{soxl_title}</span>
                </div>
                <div style="font-family:'DM Mono';font-size:0.7em;color:#344054;margin-top:4px;letter-spacing:0.1em;text-transform:uppercase;">{soxl_strat}</div>
            </div>
            {_lg_row('SMH > 50MA', f'${smh_close:.2f}', smh_c1)}
            {_lg_row('Momentum 1M >10%', f'{smh_1m*100:.1f}%', smh_c2)}
            {_lg_row('RSI > 50', f'{smh_rsi:.1f}', smh_c3)}
            <div style="margin-top:auto;padding:8px 12px;font-size:0.73em;text-align:center;
                color:#4A5568;border-top:1px solid rgba(0,0,0,0.05);font-family:'DM Mono';">
                ※ 3 filters required for SOXL</div>
        </div>"""), unsafe_allow_html=True)

    with c3:
        st.markdown(apply_theme(f"""<div class="glass-card">
            <h3>Target Weights  ·  R{curr_regime}</h3>
            <div style="display:flex;justify-content:space-between;font-family:'DM Mono';
                font-size:0.62em;color:#4A5568;border-bottom:1px solid rgba(0,0,0,0.06);
                padding-bottom:8px;margin-bottom:4px;letter-spacing:0.15em;text-transform:uppercase;">
                <span>Asset</span><span>Weight</span>
            </div>
            {weight_rows}
        </div>"""), unsafe_allow_html=True)

    # ── ③ 메트릭 필 스트립 (가로 스크롤 카드 행) ────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    def _metric_pill(label, main_val, sub_val, delta_positive=True):
        sub_color = "#059669" if delta_positive else "#EF4444"
        return apply_theme(f"""
        <div style="flex:1;min-width:160px;background:#FFFFFF;border:1px solid rgba(0,0,0,0.07);
            border-top:2px solid rgba({r_c},{g_c},{b_c},0.35);border-radius:14px;padding:14px 18px;
            box-shadow:0 2px 12px rgba(0,0,0,0.05);transition:transform 0.2s;">
            <div style="font-family:'DM Mono';font-size:0.62em;color:#4A5568;letter-spacing:0.14em;
                text-transform:uppercase;margin-bottom:6px;">{label}</div>
            <div style="font-family:'DM Mono';font-size:1.3em;font-weight:400;color:#0F172A;">{main_val}</div>
            <div style="font-family:'DM Mono';font-size:0.72em;color:{sub_color};margin-top:3px;">{sub_val}</div>
        </div>""")

    _qqq_vs = (last_row['QQQ']/last_row['QQQ_MA200']-1)*100
    _tqqq_vs = (last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100
    _smh_vs = (last_row['SMH']/last_row['SMH_MA50']-1)*100
    pills_html = (
        _metric_pill("QQQ vs 200MA",    f"${last_row['QQQ']:.2f}",              f"{_qqq_vs:+.2f}%",          _qqq_vs>=0) +
        _metric_pill("TQQQ vs 200MA",   f"${last_row['TQQQ']:.2f}",             f"{_tqqq_vs:+.2f}%",         _tqqq_vs>=0) +
        _metric_pill("VIX · 20D MA",    f"{last_row['VIX_MA20']:.2f}",          f"NOW: {last_row['^VIX']:.2f}", last_row['^VIX']<20) +
        _metric_pill("SMH 1M Ret",      f"{last_row['SMH_1M_Ret']*100:+.1f}%",  f"vs 50MA: {_smh_vs:+.1f}%", last_row['SMH_1M_Ret']>=0) +
        _metric_pill("SMH RSI",         f"{last_row['SMH_RSI']:.1f}",           "Target > 50",               last_row['SMH_RSI']>50)
    )
    st.markdown(f'<div style="display:flex;gap:10px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:4px;">{pills_html}</div>', unsafe_allow_html=True)

    # ── ④ 차트  3:2 비대칭 분할 ─────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns([3, 2])
    df_recent = df.iloc[-500:]

    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color=line_c, width=2.5)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_qqq.update_layout(title=dict(text="QQQ  vs  200MA", font=dict(family='DM Mono', size=13, color=t_color)), height=360, **chart_layout)
    fig_qqq.update_xaxes(**_ax)
    fig_qqq.update_yaxes(**_ax)

    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color=line_c, width=2.5)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_tqqq.update_layout(title=dict(text="TQQQ  vs  200MA", font=dict(family='DM Mono', size=13, color=t_color)), height=360, **chart_layout)
    fig_tqqq.update_xaxes(**_ax)
    fig_tqqq.update_yaxes(**_ax)

    with chart_col1:
        with st.container(border=True):
            st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2:
        with st.container(border=True):
            st.plotly_chart(fig_tqqq, use_container_width=True)

# ──────────────────────────────────────────
elif page == "💼 Portfolio":
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
        <div>
            <h2 style="font-family:'Syne';font-size:1.7em;color:#0F172A;margin:0;">💼 Portfolio  &amp;  Rebalancing</h2>
            <div style="font-family:'DM Mono';font-size:0.65em;color:#4A5568;letter-spacing:0.16em;text-transform:uppercase;margin-top:3px;">Position Tracker  ·  Rebalancing Engine</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_up, col_down = st.columns(2)
    with col_up:
        uploaded_file = st.file_uploader("📂 Restore from JSON", type="json")
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                st.session_state.portfolio.update(data)
                sanitize_portfolio()
                save_portfolio_to_disk()
                st.success("포트폴리오 복구 완료")
                st.rerun()
            except:
                st.error("파일 형식 오류")
    with col_down:
        st.markdown("<br>", unsafe_allow_html=True)
        json_str = json.dumps(st.session_state.portfolio)
        st.download_button("💾 Backup to JSON", data=json_str, file_name="portfolio.json", mime="application/json", use_container_width=True)

    st.divider()

    editor_data = []
    for asset in ASSET_LIST:
        val = st.session_state.portfolio.get(asset, {})
        editor_data.append({
            "Asset": asset,
            "Shares": float(val.get('shares', 0.0)),
            "Avg Price($)": float(val.get('avg_price', 1.0 if asset == 'CASH' else 0.0)),
            "FX Rate(₩)": float(val.get('fx', 1350.0))
        })
    df_editor = pd.DataFrame(editor_data)

    with st.container(border=True):
        edited_df = st.data_editor(
            df_editor,
            disabled=["Asset"],
            hide_index=True,
            use_container_width=True,
            key="pf_editor",
            column_config={
                "Shares": st.column_config.NumberColumn("Shares", format="%.6f"),
                "Avg Price($)": st.column_config.NumberColumn("Avg Price($)", format="%.4f"),
                "FX Rate(₩)": st.column_config.NumberColumn("FX Rate(₩)", format="%.2f")
            }
        )

    if not edited_df.equals(df_editor):
        for _, row in edited_df.iterrows():
            asset = row["Asset"]
            st.session_state.portfolio[asset] = {
                'shares': float(row["Shares"]),
                'avg_price': float(row["Avg Price($)"]),
                'fx': float(row["FX Rate(₩)"])
            }
        save_portfolio_to_disk()
        st.rerun()

    st.markdown("""
    <div style="font-family:'DM Mono';font-size:0.62em;color:#4A5568;letter-spacing:0.2em;text-transform:uppercase;margin:16px 0 6px;">⚖  Action Plan</div>
    """, unsafe_allow_html=True)

    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': current_prices[t] = 1.0
        elif t in rt_prices: current_prices[t] = rt_prices[t]
        elif t in df.columns: current_prices[t] = df[t].iloc[-1]
        else: current_prices[t] = 0.0

    cur_fx = rt_prices.get('USDKRW=X', 1350.0)
    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}
    total_val_usd = sum(curr_vals.values())

    _nav_html = (
        f'<div style="display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap;">'
        f'<div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);border-top:2px solid #111118;'
        f'border-radius:0;padding:12px 20px;">'
        f'<div style="font-family:DM Mono,monospace;font-size:0.58em;color:#9494A0;'
        f'letter-spacing:0.16em;text-transform:uppercase;margin-bottom:4px;">Total NAV</div>'
        f'<div style="font-family:DM Mono,monospace;font-size:1.55em;font-weight:400;'
        f'color:#111118;font-variant-numeric:tabular-nums;">${total_val_usd:,.2f}</div>'
        f'</div>'
        f'<div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);border-top:2px solid rgba(0,0,0,0.25);'
        f'border-radius:0;padding:12px 20px;">'
        f'<div style="font-family:DM Mono,monospace;font-size:0.58em;color:#9494A0;'
        f'letter-spacing:0.16em;text-transform:uppercase;margin-bottom:4px;">USD/KRW</div>'
        f'<div style="font-family:DM Mono,monospace;font-size:1.55em;font-weight:400;'
        f'color:#111118;font-variant-numeric:tabular-nums;">₩{cur_fx:,.2f}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(_nav_html, unsafe_allow_html=True)

    if total_val_usd > 0:
        c_green, c_red = main_color, "#EF4444"
        pie_layout = dict(
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="DM Mono, DM Sans", color=t_color)
        )

        diff_vals = {a: (total_val_usd * target_weights.get(a, 0.0)) - curr_vals[a] for a in ASSET_LIST}
        chart_c1, chart_c2, chart_c3 = st.columns([1, 1, 1.5])

        labels_cur = [a for a in ASSET_LIST if curr_vals[a] > 0]
        vals_cur   = [curr_vals[a] for a in labels_cur]
        if sum(vals_cur) > 0:
            fig_cur = go.Figure(data=[go.Pie(labels=labels_cur, values=vals_cur, hole=.45, textinfo='label+percent',
                                              marker=dict(colors=[line_c, dash_c, '#34D399', '#6EE7B7', '#A7F3D0', '#059669', '#047857', '#065F46', '#D1FAE5']))])
            fig_cur.update_layout(title=dict(text="Current", font=dict(family="DM Mono", size=13, color=t_color)), **pie_layout)
            with chart_c1:
                with st.container(border=True):
                    st.plotly_chart(fig_cur, use_container_width=True)

        labels_tgt = [a for a in ASSET_LIST if target_weights.get(a, 0) > 0]
        vals_tgt   = [target_weights.get(a, 0) for a in labels_tgt]
        fig_tgt = go.Figure(data=[go.Pie(labels=labels_tgt, values=vals_tgt, hole=.45, textinfo='label+percent',
                                          marker=dict(colors=[line_c, dash_c, '#34D399', '#6EE7B7', '#A7F3D0', '#059669', '#047857', '#065F46', '#D1FAE5']))])
        fig_tgt.update_layout(title=dict(text=f"Target  ·  R{curr_regime}", font=dict(family="DM Mono", size=13, color=t_color)), **pie_layout)
        with chart_c2:
            with st.container(border=True):
                st.plotly_chart(fig_tgt, use_container_width=True)

        diff_labels = [a for a in ASSET_LIST if abs(diff_vals[a]) >= 1.0]
        diff_values = [diff_vals[a] for a in diff_labels]
        diff_colors = [c_green if v > 0 else c_red for v in diff_values]
        if diff_labels:
            fig_bar = go.Figure(data=[go.Bar(
                x=diff_labels, y=diff_values,
                marker_color=diff_colors,
                text=[f"${v:,.0f}" for v in diff_values],
                textposition='auto',
                marker_line_width=0
            )])
            fig_bar.update_layout(
                title=dict(text="Rebalancing  Δ($)", font=dict(family="DM Mono", size=13, color=t_color)),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=t_color, family="DM Mono"),
                margin=dict(t=40, b=20, l=20, r=20),
                xaxis=dict(gridcolor='rgba(0,0,0,0.05)', zeroline=False),
                yaxis=dict(gridcolor='rgba(0,0,0,0.05)', zeroline=False)
            )
            with chart_c3:
                with st.container(border=True):
                    st.plotly_chart(fig_bar, use_container_width=True)

        # ── Quick Orders ─────────────────────────────────────────
        st.markdown("""<div style="font-family:'DM Mono';font-size:0.6em;font-weight:500;color:#6B6B7A;letter-spacing:0.2em;text-transform:uppercase;margin:20px 0 10px;padding-bottom:6px;border-bottom:2px solid #111118;">📝  Quick Orders</div>""", unsafe_allow_html=True)

        sell_items, buy_items = [], []
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff  = diff_vals[asset]
            if asset != 'CASH' and diff < -cur_p * 0.05:
                sell_items.append((asset, f"{abs(diff)/cur_p:,.2f} 주 매도", "#EF4444"))
            elif asset == 'CASH' and diff < -1.0:
                sell_items.append(("CASH", f"${abs(diff):,.0f} 사용", "#EF4444"))
            if asset != 'CASH' and diff > cur_p * 0.05:
                buy_items.append((asset, f"{diff/cur_p:,.2f} 주 매수", "#059669"))
            elif asset == 'CASH' and diff > 1.0:
                buy_items.append(("CASH", f"${diff:,.0f} 확보", "#059669"))

        qo_col1, qo_col2 = st.columns(2)

        def _order_card(title, items, accent, col):
            rows_html = "".join([
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.06);">'
                f'<span style="font-family:DM Mono,monospace;font-size:0.82em;font-weight:600;color:#111118;">{a}</span>'
                f'<span style="font-family:DM Mono,monospace;font-size:0.82em;color:{c};font-variant-numeric:tabular-nums;">{v}</span>'
                f'</div>'
                for a, v, c in items
            ]) or f'<div style="font-family:DM Mono,monospace;font-size:0.78em;color:#9494A0;padding:8px 0;">— 해당 없음</div>'
            col.markdown(
                f'<div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);'
                f'border-top:3px solid {accent};padding:16px 18px;">'
                f'<div style="font-family:DM Sans,sans-serif;font-size:0.88em;font-weight:700;'
                f'color:{accent};letter-spacing:0.02em;margin-bottom:10px;">{title}</div>'
                f'{rows_html}</div>',
                unsafe_allow_html=True
            )

        _order_card("🔴  SELL", sell_items, "#EF4444", qo_col1)
        _order_card("🟢  BUY",  buy_items,  "#059669", qo_col2)

        rebal_html = f"""<div style="overflow-x:auto; padding:10px 0;">
<table class="mint-table">
<thead><tr>
<th>Asset</th><th>Avg → Cur</th><th>Ret (KRW)</th><th>Value ($)</th><th>Target %</th><th>Target ($)</th><th>Δ ($)</th><th style="text-align:center;">Action</th>
</tr></thead><tbody>"""

        for asset in ASSET_LIST:
            shares = st.session_state.portfolio[asset]['shares']
            avg_p  = st.session_state.portfolio[asset]['avg_price']
            pur_fx = st.session_state.portfolio[asset]['fx']
            cur_p  = current_prices[asset] if current_prices[asset] > 0 else 1.0
            curr_v = curr_vals[asset]
            tgt_w  = target_weights.get(asset, 0.0)
            tgt_v  = total_val_usd * tgt_w
            diff   = diff_vals[asset]

            if asset == 'CASH':
                avg_p_str = "—"
                ret_usd, ret_krw = 0.0, ((cur_fx / pur_fx) - 1) * 100 if pur_fx > 0 else 0.0
            else:
                avg_p_str = f"${avg_p:,.2f} → ${cur_p:,.2f}"
                ret_usd   = (cur_p / avg_p - 1) * 100 if avg_p > 0 else 0.0
                ret_krw   = ((cur_p * cur_fx) / (avg_p * pur_fx) - 1) * 100 if (avg_p > 0 and pur_fx > 0) else 0.0

            ret_usd_color = c_green if ret_usd >= 0 else c_red
            ret_usd_str   = f"{ret_usd:+.2f}%" if asset != 'CASH' else "—"

            if abs(diff) < cur_p * 0.05 and asset != 'CASH':
                action, diff_str = "<span style='color:#4A5568; font-weight:500;'>HOLD</span>", "—"
            elif abs(diff) < 1.0 and asset == 'CASH':
                action, diff_str = "<span style='color:#4A5568; font-weight:500;'>HOLD</span>", "—"
            elif diff > 0:
                action   = f"<span style='color:#10B981; font-weight:600; background:rgba(16,185,129,0.1); padding:3px 10px; border-radius:6px; border:1px solid rgba(16,185,129,0.2);'>BUY</span>"
                diff_str = f"<span style='color:#10B981; font-weight:500;'>+${diff:,.0f}</span>"
            else:
                action   = f"<span style='color:#EF4444; font-weight:600; background:rgba(239,68,68,0.1); padding:3px 10px; border-radius:6px; border:1px solid rgba(239,68,68,0.2);'>SELL</span>"
                diff_str = f"<span style='color:#EF4444; font-weight:500;'>-${abs(diff):,.0f}</span>"

            if tgt_w > 0 or curr_v > 0 or shares > 0:
                rebal_html += f"""<tr>
<td style="font-weight:700; font-family:'DM Sans'; color:#10B981;">{asset}</td>
<td style="color:#2D3A4A;">{avg_p_str}</td>
<td><span style="color:{ret_usd_color}; font-weight:500;">{ret_usd_str}</span></td>
<td>{curr_v:,.0f}</td>
<td style="color:#10B981;">{tgt_w*100:.0f}%</td>
<td>{tgt_v:,.0f}</td>
<td>{diff_str}</td>
<td style="text-align:center;">{action}</td></tr>"""

        rebal_html += "</tbody></table></div>"
        with st.container(border=True):
            st.markdown(apply_theme(rebal_html), unsafe_allow_html=True)

# ──────────────────────────────────────────
elif page == "🍫 12-Pack Radar":

    df_view  = df.iloc[-120:]
    qqq_rsi  = last_row['QQQ_RSI']
    qqq_dd   = last_row['QQQ_DD']
    cnn_fgi  = fetch_fear_and_greed()
    if cnn_fgi is not None:
        fg_score = cnn_fgi
    else:
        vix_score = max(0, min(100, 100-(last_row['^VIX']-12)/28*100))
        dd_score  = max(0, min(100, (qqq_dd+0.20)/0.20*100))
        rsi_score = max(0, min(100, qqq_rsi))
        fg_score  = (vix_score+dd_score+rsi_score)/3

    sec_names = {'XLK':'TECH','XLV':'HEALTH','XLF':'FIN','XLY':'CONS','XLC':'COMM',
                 'XLI':'IND','XLP':'STAPLE','XLE':'ENGY','XLU':'UTIL','XLRE':'REAL','XLB':'MAT'}
    sec_data  = [{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
    sec_df    = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
    top_sec, bot_sec = sec_df.iloc[-1]['섹터'], sec_df.iloc[0]['섹터']

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
    if last_row['^TNX'] > last_row['TNX_MA50']: warn_cnt+=1
    else: safe_cnt+=1
    if last_row['BTC-USD'] < last_row['BTC_MA50']: warn_cnt+=1
    else: safe_cnt+=1
    if last_row['IWM_SPY_Ratio'] < last_row['IWM_SPY_MA50']: warn_cnt+=1
    else: safe_cnt+=1
    if last_row['^VIX'] > last_row['VIX_MA50']: risk_cnt+=1
    else: safe_cnt+=1
    if top_sec not in ['UTIL', 'STAPLE', 'HEALTH']: safe_cnt+=1
    else: warn_cnt+=1

    if risk_cnt >= 3:
        radar_status = "🔴 극단적 위험 구간  (Risk-Off)"
        radar_msg    = "시장에 극단적인 공포가 덮쳤습니다. 현재 복수의 매크로 지표가 시스템 리스크를 강하게 경고하고 있습니다. 단순한 조정을 넘어선 투매 구간일 확률이 높으니, 모든 레버리지 포지션을 해제하고 현금과 달러, 금 등 안전 자산 비중을 최대로 늘려 폭풍우가 지나가기를 기다리셔야 합니다."
        radar_color  = "#EF4444"
    elif warn_cnt >= 4 or risk_cnt >= 1:
        radar_status = "🟡 변동성 주의  (Warning)"
        radar_msg    = "시장 곳곳에서 균열의 조짐이 감지되고 있습니다. 표면적인 지수는 버티고 있을지 몰라도 내부 자금 흐름이나 심리 지표가 점차 악화되고 있습니다. 신규 매수는 철저히 보류하시고, 포트폴리오의 리스크 노출도를 점검하며 보수적인 관망 자세를 유지하는 것이 좋습니다."
        radar_color  = "#F59E0B"
    else:
        radar_status = "🟢 안정적 순항  (Safe)"
        radar_msg    = "현재 글로벌 매크로 지표와 시장 심리가 모두 안정적인 궤도에 올라와 있습니다. 추세를 꺾을 만한 시스템 리스크가 보이지 않으니, AMLS 알고리즘이 제시하는 비중에 맞춰 자신감 있게 추세 추종 전략을 전개하시기 바랍니다. 수익을 극대화할 수 있는 구간입니다."
        radar_color  = main_color

    st.markdown(apply_theme(f"""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
        <div>
            <h2 style="font-family:'Syne';font-size:1.7em;color:#0F172A;margin:0;">🍫 12-Pack Radar</h2>
            <div style="font-family:'DM Mono';font-size:0.65em;color:#4A5568;letter-spacing:0.16em;text-transform:uppercase;margin-top:3px;">Global Macro Signal Dashboard</div>
        </div>
    </div>"""), unsafe_allow_html=True)

    # 상태 배너 — 좌(텍스트) + 우(카운터 3칸)
    _cnt_cards = ""
    for _lbl, _val, _c in [("RISK", risk_cnt, "#EF4444"), ("WARN", warn_cnt, "#F59E0B"), ("SAFE", safe_cnt, main_color)]:
        _cnt_cards += (f'<div style="flex:1;text-align:center;background:rgba(0,0,0,0.025);'
                       f'border:1px solid rgba(0,0,0,0.07);border-top:2px solid {_c};border-radius:12px;padding:12px 8px;">'
                       f'<div style="font-family:\'DM Mono\';font-size:1.8em;font-weight:400;color:{_c};">{_val}</div>'
                       f'<div style="font-family:\'DM Mono\';font-size:0.6em;color:#4A5568;letter-spacing:0.16em;text-transform:uppercase;margin-top:2px;">{_lbl}</div>'
                       f'</div>')

    st.markdown(apply_theme(f"""
    <div style="display:flex;gap:16px;margin-bottom:24px;align-items:stretch;">
        <div style="flex:3;background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);
            border-left:4px solid {radar_color};border-radius:0;padding:20px 22px;
            box-shadow:none;">
            <div style="font-family:'Syne';font-size:1.2em;font-weight:700;color:{radar_color};margin-bottom:10px;">{radar_status}</div>
            <p style="font-family:'DM Sans';color:#2D3A4A;font-size:0.92em;margin:0;line-height:1.75;">{radar_msg}</p>
        </div>
        <div style="flex:1;display:flex;flex-direction:column;gap:8px;min-width:160px;">
            {_cnt_cards}
        </div>
    </div>
    """), unsafe_allow_html=True)

    def _badge(label, color, icon):
        p = {
            'green':  (f'rgba({r_c},{g_c},{b_c},0.1)',  main_color),
            'orange': ('rgba(245,158,11,0.1)',           '#F59E0B'),
            'red':    ('rgba(239,68,68,0.1)',            '#EF4444'),
            'blue':   ('rgba(59,130,246,0.1)',           '#60A5FA')
        }
        bg, fg = p[color]
        return (f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; border-radius:6px; '
                f'padding:3px 9px; font-size:0.7em; font-weight:500; margin-left:6px; '
                f'font-family:\'DM Mono\'; letter-spacing:0.06em;">{icon} {label}</span>')

    b1  = _badge("BUY","green","▲") if qqq_rsi<40 else (_badge("OVER","red","▼") if qqq_rsi>70 else _badge("NEUTRAL","blue","—"))
    b2  = _badge("BEAR −20%","red","▼") if qqq_dd<-0.20 else (_badge("CORR −10%","orange","▼") if qqq_dd<-0.10 else _badge("SAFE","green","▲"))
    b3  = _badge("FEAR","green","▲") if fg_score<30 else (_badge("GREED","red","▼") if fg_score>70 else _badge("NEUTRAL","blue","—"))
    b4  = f'<span style="background:rgba({r_c},{g_c},{b_c},0.1); color:{main_color}; border:1px solid {main_color}; border-radius:6px; padding:3px 9px; font-size:0.7em; font-weight:500; margin-left:6px; font-family:\'DM Mono\';">▲ {top_sec} / ▼ {bot_sec}</span>'
    b5  = _badge("RISK OFF","red","▼") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _badge("RISK ON","green","▲")
    b6  = _badge("NARROW","orange","⚠") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0) else _badge("BROAD","green","▲")
    b7  = _badge("GOLD","orange","▲") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _badge("EQUITY","green","▲")
    b8  = _badge("USD STRONG","red","▼") if last_row['UUP']>last_row['UUP_MA50'] else _badge("USD WEAK","green","▲")
    b9  = _badge("YIELD UP","red","▼") if last_row['^TNX'] > last_row['TNX_MA50'] else _badge("YIELD DOWN","green","▲")
    b10 = _badge("RISK OFF","red","▼") if last_row['BTC-USD'] < last_row['BTC_MA50'] else _badge("RISK ON","green","▲")
    b11 = _badge("NARROW","orange","⚠") if last_row['IWM_SPY_Ratio'] < last_row['IWM_SPY_MA50'] else _badge("BROAD","green","▲")
    b12 = _badge("EXPAND","red","▼") if last_row['^VIX'] > last_row['VIX_MA50'] else _badge("SHRINK","green","▲")

    gauge_steps = [
        {'range':[0,25],  'color':"rgba(239,68,68,0.45)"},
        {'range':[25,45], 'color':"rgba(245,158,11,0.35)"},
        {'range':[45,55], 'color':"rgba(0,0,0,0.04)"},
        {'range':[55,75], 'color':f"rgba({r_c},{g_c},{b_c},0.35)"},
        {'range':[75,100],'color':f"rgba({r_c},{g_c},{b_c},0.55)"}
    ]

    desc1  = "나스닥 100(QQQ)의 단기 과열 및 침체를 나타내는 RSI 지표입니다. 30 밑으로 떨어지면 비이성적 투매가 진행 중이라는 뜻이니 훌륭한 분할 매수 기회로 삼고, 70을 넘어가면 환희에 취한 상태이니 신규 진입을 멈추고 현금을 확보하는 것이 좋습니다."
    desc2  = "QQQ의 52주 고점 대비 하락률을 보여줍니다. -10%는 통상적인 건전한 조정의 하단 지지선 역할을 하지만, -20%를 깨고 내려간다면 이는 단순 조정을 넘어선 본격적인 약세장(Bear Market) 진입을 의미하므로 즉각적인 방어 태세가 필요합니다."
    desc3  = "CNN에서 제공하는 시장 심리 종합 지표입니다. 대중이 극단적 공포(Extreme Fear)에 질려 주식을 집어 던질 때가 역사적으로 훌륭한 진입 시점이었습니다. 반대로 극단적 탐욕 구간에서는 수익을 실현하며 보수적으로 접근해야 합니다."
    desc4  = "최근 1개월간 글로벌 스마트머니가 어느 섹터로 흘러갔는지 보여줍니다. 유틸리티나 필수소비재 같은 방어주가 상위권을 차지한다면 시장이 경기 침체를 대비하고 있다는 시그널이므로 포트폴리오 경계감을 한 단계 높여야 합니다."
    desc5  = "안전한 국채 대신 위험한 하이일드 채권에 투자자들이 얼마나 자금을 넣고 있는지를 보여주는 척도입니다. 이 비율이 50일선 아래로 꺾인다면, 눈치 빠른 채권 시장의 스마트머니가 주식 시장보다 먼저 자금을 빼고 있다는 강력한 경고입니다."
    desc6  = "나스닥 시총 가중 지수(QQQ)와 동일 가중 지수(QQQE)를 비교합니다. 지수는 오르는데 QQQE가 하락한다면, 소수의 대형 기술주들만 지수를 멱살 잡고 끌어올리는 '가짜 상승'일 확률이 높으므로 곧 조정이 올 수 있음을 암시합니다."
    desc7  = "대표적 안전 자산인 금(GLD)과 위험 자산인 주식(SPY)의 상대 강도입니다. 이 비율이 50일선을 돌파해 상승 랠리를 펼친다면, 기관 투자자들이 주식 시장의 불확실성을 피해 금으로 대거 피신하고 있다는 구조적 리스크 오프 시그널입니다."
    desc8  = "미국 달러의 강세를 보여주는 지수입니다. 달러가 50일선을 뚫고 강세로 전환되면 글로벌 유동성이 미국으로 빨려 들어가며 기술주에 큰 하방 압력을 가하게 됩니다. 강달러 국면에서는 주식 비중을 줄이는 것이 정석입니다."
    desc9  = "모든 자산 밸류에이션의 중력 역할을 하는 미 10년물 국채금리입니다. 금리가 50일선을 뚫고 급등하면, 미래 실적을 당겨쓰는 나스닥 성장주들에게는 쥐약과도 같습니다. 금리 상승기에는 기술주 레버리지 투자를 극도로 조심해야 합니다."
    desc10 = "제도권에 편입된 비트코인은 글로벌 잉여 유동성과 위험 감수 의지를 가장 예민하게 반영하는 선행 지표입니다. 비트코인이 50일선을 깨고 무너진다면 주식 시장에도 곧 유동성 가뭄이 닥칠 수 있다는 경고벨로 받아들여야 합니다."
    desc11 = "대형주(SPY) 대비 중소형주(IWM)의 상대 강도입니다. 시장에 큰 호재 없이 러셀지수가 필요 이상으로 상승하고 채권시장을 살릴만한 뚜렷한 재료가 없을 때, 이 지표의 괴리를 활용해 러셀 숏 상품(TZA 등) 매수를 전략적으로 고려해 볼 수 있습니다."
    desc12 = "공포지수(VIX)의 추세입니다. 시장에서 유동성이 충분히 흡수되지 않으면 VIX 지수는 안정적인 하방 경직성을 가지게 됩니다. 반대로 이 선을 강하게 뚫고 올라온다면 평온했던 시장에 폭풍우가 몰아치기 시작했다는 시스템 패닉 시그널입니다."

    def r_head(title, badge, url, desc):
        return (f'<a href="{url}" target="_blank" class="radar-link">'
                f'<div class="radar-link-title" style="margin-bottom:5px;">{title} ↗{badge}</div>'
                f'</a>'
                f'<div style="font-size:0.76em; color:#344054; margin-bottom:12px; line-height:1.45; letter-spacing:-0.2px; word-break:keep-all;">{desc}</div>')

    u1  = "https://kr.tradingview.com/chart/?symbol=NASDAQ:QQQ"
    u2  = "https://kr.tradingview.com/chart/?symbol=NASDAQ:QQQ"
    u3  = "https://edition.cnn.com/markets/fear-and-greed"
    u4  = "https://finviz.com/map.ashx?t=sec"
    u5  = "https://fred.stlouisfed.org/series/BAMLH0A0HYM2"
    u6  = "https://kr.tradingview.com/chart/?symbol=NASDAQ:QQQE"
    u7  = "https://kr.tradingview.com/chart/?symbol=AMEX:GLD"
    u8  = "https://kr.tradingview.com/chart/?symbol=AMEX:UUP"
    u9  = "https://kr.tradingview.com/chart/?symbol=TVC:US10Y"
    u10 = "https://kr.tradingview.com/chart/?symbol=BINANCE:BTCUSD"
    u11 = "https://kr.tradingview.com/chart/?symbol=AMEX:IWM"
    u12 = "https://kr.tradingview.com/chart/?symbol=CBOE:VIX"

    row1 = st.columns(4)
    with row1[0]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("1. DCA  ·  RSI", b1, u1, desc1)), unsafe_allow_html=True)
            fig1=go.Figure()
            fig1.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_RSI'], line=dict(color=line_c, width=2)))
            fig1.add_hline(y=70, line_dash='dot', line_color='#CBD5E1', line_width=1)
            fig1.add_hline(y=30, line_dash='dot', line_color=rsi_low_c, line_width=1)
            fig1.update_layout(**radar_layout, showlegend=False)
            fig1.update_xaxes(**_ax_r)
            fig1.update_yaxes(range=[10,90], **_ax_r)
            st.plotly_chart(fig1, use_container_width=True)
    with row1[1]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("2. Drawdown", b2, u2, desc2)), unsafe_allow_html=True)
            fig2=go.Figure()
            fig2.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_DD'], fill='tozeroy', fillcolor='rgba(239,68,68,0.07)', line=dict(color='#EF4444', width=1.8)))
            fig2.update_layout(**radar_layout, showlegend=False)
            fig2.update_xaxes(**_ax_r)
            fig2.update_yaxes(tickformat='.0%', **_ax_r)
            st.plotly_chart(fig2, use_container_width=True)
    with row1[2]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("3. Fear & Greed", b3, u3, desc3)), unsafe_allow_html=True)
            fig3=go.Figure(go.Indicator(
                mode="gauge+number", value=fg_score, domain={'x':[0,1],'y':[0,1]},
                gauge={'axis':{'range':[0,100], 'tickcolor':t_color},'bar':{'color':line_c,'thickness':0.25},'steps':gauge_steps,'borderwidth':0}
            ))
            fig3.update_layout(height=200, margin=dict(l=15,r=15,t=10,b=10), paper_bgcolor=b_color, font=dict(family="DM Mono", color=t_color))
            st.plotly_chart(fig3, use_container_width=True)
    with row1[3]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("4. Sector  1M", b4, u4, desc4)), unsafe_allow_html=True)
            fig4=go.Figure(go.Bar(
                x=sec_df['수익률'], y=sec_df['섹터'], orientation='h',
                marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']],
                marker_line_width=0
            ))
            fig4.update_layout(**radar_layout, showlegend=False)
            fig4.update_xaxes(**_ax_r)
            fig4.update_yaxes(**_ax_r)
            st.plotly_chart(fig4, use_container_width=True)

    row2 = st.columns(4)
    with row2[0]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("5. Credit Spread", b5, u5, desc5)), unsafe_allow_html=True)
            fig5=go.Figure()
            fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_Ratio'], line=dict(color=line_c, width=2)))
            fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_MA50'],  line=dict(color=dash_c, dash='dot', width=1.2)))
            fig5.update_layout(**radar_layout, showlegend=False)
            fig5.update_xaxes(**_ax_r); fig5.update_yaxes(**_ax_r)
            st.plotly_chart(fig5, use_container_width=True)
    with row2[1]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("6. Market Breadth", b6, u6, desc6)), unsafe_allow_html=True)
            fig6=go.Figure()
            fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_20d_Ret'],  name='QQQ',  line=dict(color=line_c, width=2)))
            fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQE_20d_Ret'], name='QQQE', line=dict(color=dash_c, dash='dot', width=1.2)))
            fig6.update_layout(**radar_layout, showlegend=False)
            fig6.update_xaxes(**_ax_r)
            fig6.update_yaxes(tickformat='.0%', **_ax_r)
            st.plotly_chart(fig6, use_container_width=True)
    with row2[2]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("7. Gold / Equity", b7, u7, desc7)), unsafe_allow_html=True)
            fig7=go.Figure()
            fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_Ratio'], line=dict(color=line_c, width=2)))
            fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_MA50'],  line=dict(color=dash_c, dash='dot', width=1.2)))
            fig7.update_layout(**radar_layout, showlegend=False)
            fig7.update_xaxes(**_ax_r); fig7.update_yaxes(**_ax_r)
            st.plotly_chart(fig7, use_container_width=True)
    with row2[3]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("8. USD  (UUP)", b8, u8, desc8)), unsafe_allow_html=True)
            fig8=go.Figure()
            fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP'],       line=dict(color=line_c, width=2)))
            fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP_MA50'],  line=dict(color=dash_c, dash='dot', width=1.2)))
            fig8.update_layout(**radar_layout, showlegend=False)
            fig8.update_xaxes(**_ax_r); fig8.update_yaxes(**_ax_r)
            st.plotly_chart(fig8, use_container_width=True)

    row3 = st.columns(4)
    with row3[0]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("9. US 10Y Yield", b9, u9, desc9)), unsafe_allow_html=True)
            fig9=go.Figure()
            fig9.add_trace(go.Scatter(x=df_view.index, y=df_view['^TNX'],      line=dict(color=line_c, width=2)))
            fig9.add_trace(go.Scatter(x=df_view.index, y=df_view['TNX_MA50'],  line=dict(color=dash_c, dash='dot', width=1.2)))
            fig9.update_layout(**radar_layout, showlegend=False)
            fig9.update_xaxes(**_ax_r); fig9.update_yaxes(**_ax_r)
            st.plotly_chart(fig9, use_container_width=True)
    with row3[1]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("10. Bitcoin Trend", b10, u10, desc10)), unsafe_allow_html=True)
            fig10=go.Figure()
            fig10.add_trace(go.Scatter(x=df_view.index, y=df_view['BTC-USD'],  line=dict(color=line_c, width=2)))
            fig10.add_trace(go.Scatter(x=df_view.index, y=df_view['BTC_MA50'], line=dict(color=dash_c, dash='dot', width=1.2)))
            fig10.update_layout(**radar_layout, showlegend=False)
            fig10.update_xaxes(**_ax_r); fig10.update_yaxes(**_ax_r)
            st.plotly_chart(fig10, use_container_width=True)
    with row3[2]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("11. Russell / S&P 500", b11, u11, desc11)), unsafe_allow_html=True)
            fig11=go.Figure()
            fig11.add_trace(go.Scatter(x=df_view.index, y=df_view['IWM_SPY_Ratio'], line=dict(color=line_c, width=2)))
            fig11.add_trace(go.Scatter(x=df_view.index, y=df_view['IWM_SPY_MA50'],  line=dict(color=dash_c, dash='dot', width=1.2)))
            fig11.update_layout(**radar_layout, showlegend=False)
            fig11.update_xaxes(**_ax_r); fig11.update_yaxes(**_ax_r)
            st.plotly_chart(fig11, use_container_width=True)
    with row3[3]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("12. VIX Trend", b12, u12, desc12)), unsafe_allow_html=True)
            fig12=go.Figure()
            fig12.add_trace(go.Scatter(x=df_view.index, y=df_view['^VIX'],      line=dict(color=line_c, width=2)))
            fig12.add_trace(go.Scatter(x=df_view.index, y=df_view['VIX_MA50'],  line=dict(color=dash_c, dash='dot', width=1.2)))
            fig12.update_layout(**radar_layout, showlegend=False)
            fig12.update_xaxes(**_ax_r); fig12.update_yaxes(**_ax_r)
            st.plotly_chart(fig12, use_container_width=True)

# ──────────────────────────────────────────
elif page == "📈 Backtest Lab":
    st.markdown(apply_theme("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
        <div>
            <h2 style="font-family:'Syne';font-size:1.7em;color:#0F172A;margin:0;">📈 Backtest Lab</h2>
            <div style="font-family:'DM Mono';font-size:0.65em;color:#4A5568;letter-spacing:0.16em;text-transform:uppercase;margin-top:3px;">Strategy Simulator  ·  Historical Analysis</div>
        </div>
    </div>"""), unsafe_allow_html=True)

    # ── 2패널: 좌(설정) + 우(결과) ────────────────────────────
    panel_cfg, panel_res = st.columns([1, 2.8])

    with panel_cfg:
        with st.container(border=True):
            st.markdown("""<div style="font-family:'DM Mono';font-size:0.62em;color:#4A5568;margin-bottom:14px;letter-spacing:0.2em;text-transform:uppercase;">⚙  Config</div>""", unsafe_allow_html=True)
            bt_start = st.date_input("Start Date", datetime(2020, 1, 1), key="bt_start_input")
            bt_end   = st.date_input("End Date",   datetime.today(),     key="bt_end_input")
            monthly_cont = st.number_input("월 적립금 ($)", value=2000, step=500, key="bt_monthly_input")

    with panel_res:
        with st.spinner("시뮬레이션 가동 중..."):
            bt_df = load_custom_backtest_data(bt_start, bt_end)

            if bt_df.empty:
                st.error("해당 기간의 데이터가 존재하지 않거나 부족합니다. 기간을 조정해주세요.")
            else:
                daily_ret = bt_df[['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD']].pct_change().fillna(0)
                w_orig = get_weights_v45(bt_df['Regime'].iloc[0], False)

                val_o, val_q, val_qld, val_tqqq = 10000, 10000, 10000, 10000
                hist_o, hist_q, hist_qld, hist_tqqq = [val_o], [val_q], [val_qld], [val_tqqq]
                invested = [10000]; curr_inv = 10000

                for i in range(1, len(bt_df)):
                    today     = bt_df.index[i]
                    yesterday = bt_df.index[i-1]
                    ret_o = sum(w_orig.get(t,0) * daily_ret[t].iloc[i] for t in w_orig if t in daily_ret.columns)
                    val_o *= (1 + ret_o); val_q *= (1 + daily_ret['QQQ'].iloc[i])
                    val_qld *= (1 + daily_ret['QLD'].iloc[i]); val_tqqq *= (1 + daily_ret['TQQQ'].iloc[i])
                    if today.month != yesterday.month:
                        val_o += monthly_cont; val_q += monthly_cont
                        val_qld += monthly_cont; val_tqqq += monthly_cont
                        curr_inv += monthly_cont
                    hist_o.append(val_o); hist_q.append(val_q)
                    hist_qld.append(val_qld); hist_tqqq.append(val_tqqq)
                    invested.append(curr_inv)
                    smh_cond_i = (bt_df['SMH'].iloc[i] > bt_df['SMH_MA50'].iloc[i]) and (bt_df['SMH_3M_Ret'].iloc[i] > 0.05) and (bt_df['SMH_RSI'].iloc[i] > 50)
                    w_orig = get_weights_v45(bt_df['Regime'].iloc[i], smh_cond_i)

                res_df = pd.DataFrame(index=bt_df.index)
                res_df['V4.5'], res_df['QQQ'], res_df['QLD'], res_df['TQQQ'] = hist_o, hist_q, hist_qld, hist_tqqq
                res_df['Invested'] = invested
                days = (res_df.index[-1] - res_df.index[0]).days

                def calc_metrics(series, inv_series):
                    final_val = series.iloc[-1]; total_inv = inv_series.iloc[-1]
                    ret  = (final_val / total_inv) - 1
                    cagr = (final_val / total_inv) ** (365.25 / days) - 1 if days > 0 else 0
                    mdd  = ((series / series.cummax()) - 1).min()
                    return ret, cagr, mdd

                ret_o, cagr_o, mdd_o       = calc_metrics(res_df['V4.5'], res_df['Invested'])
                ret_q, cagr_q, mdd_q       = calc_metrics(res_df['QQQ'],  res_df['Invested'])
                ret_qld, cagr_qld, mdd_qld = calc_metrics(res_df['QLD'],  res_df['Invested'])
                ret_t, cagr_t, mdd_t       = calc_metrics(res_df['TQQQ'], res_df['Invested'])

                mc1, mc2, mc3, mc4 = st.columns(4)

                def _mc_html(title, ret, cagr, mdd, is_main=False):
                    """HTML 메트릭 카드 문자열 생성 (unsafe_allow_html 전용)"""
                    border_top = f"rgba({r_c},{g_c},{b_c},0.55)" if is_main else "rgba(0,0,0,0.12)"
                    bg        = f"rgba({r_c},{g_c},{b_c},0.06)" if is_main else "#FFFFFF"
                    tag_html  = (f'<span style="background:rgba({r_c},{g_c},{b_c},0.1);'
                                 f'color:{main_color};border-radius:5px;padding:2px 8px;'
                                 f'font-size:0.6em;font-family:DM Mono,monospace;'
                                 f'border:1px solid rgba({r_c},{g_c},{b_c},0.25);'
                                 f'letter-spacing:0.1em;">STRATEGY</span>') if is_main else ''
                    ret_c     = "#059669" if ret >= 0 else "#EF4444"
                    # display:flex을 쓰지 않고 inline-block으로 대체 (Streamlit 파서 안전)
                    return (
                        f'<div style="background:{bg};border:1px solid rgba(0,0,0,0.08);'
                        f'border-top:2px solid {border_top};border-radius:14px;'
                        f'padding:16px 18px;box-shadow:0 2px 12px rgba(0,0,0,0.05);'
                        f'min-height:100px;">'
                        f'<div style="font-family:DM Mono,monospace;font-size:0.62em;'
                        f'color:#4A5568;letter-spacing:0.14em;text-transform:uppercase;'
                        f'margin-bottom:6px;">{title}&nbsp;&nbsp;{tag_html}</div>'
                        f'<div style="font-family:DM Mono,monospace;font-size:1.6em;'
                        f'font-weight:400;color:#0F172A;letter-spacing:-0.5px;'
                        f'margin-bottom:6px;">CAGR {cagr*100:.1f}%</div>'
                        f'<div style="font-family:DM Mono,monospace;font-size:0.72em;'
                        f'color:#4A5568;">'
                        f'누적&nbsp;<b style="color:{ret_c};">{ret*100:.1f}%</b>'
                        f'&nbsp;&nbsp;MDD&nbsp;<b style="color:#EF4444;">{mdd*100:.1f}%</b>'
                        f'</div></div>'
                    )

                with mc1: st.markdown(_mc_html("✦ AMLS V4.5", ret_o,   cagr_o,   mdd_o,   True), unsafe_allow_html=True)
                with mc2: st.markdown(_mc_html("QQQ",          ret_q,   cagr_q,   mdd_q),         unsafe_allow_html=True)
                with mc3: st.markdown(_mc_html("QLD",          ret_qld, cagr_qld, mdd_qld),        unsafe_allow_html=True)
                with mc4: st.markdown(_mc_html("TQQQ",         ret_t,   cagr_t,   mdd_t),          unsafe_allow_html=True)

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QQQ'],  name='QQQ',  line=dict(color='#CBD5E1', width=1.2, dash='dot')))
                fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QLD'],  name='QLD',  line=dict(color='#3B82F6', width=1.2, dash='dash')))
                fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['TQQQ'], name='TQQQ', line=dict(color='#EF4444', width=1.2, dash='dash')))
                fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['V4.5'], name='AMLS', line=dict(color=main_color, width=3)))
                fig_eq.update_layout(
                    title=dict(text="Equity Curve  ·  Log Scale", font=dict(family='DM Mono', size=13, color=t_color)),
                    height=380, yaxis_type='log', **chart_layout
                )
                fig_eq.update_xaxes(**_ax)
                fig_eq.update_yaxes(**_ax)
                with st.container(border=True):
                    st.plotly_chart(fig_eq, use_container_width=True)

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

                def get_dd_series(s): return (s / s.cummax()) - 1
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QQQ']),  name='QQQ',  line=dict(color='#CBD5E1', width=1)))
                fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QLD']),  name='QLD',  line=dict(color='#3B82F6', width=1)))
                fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['TQQQ']), name='TQQQ', line=dict(color='#EF4444', width=1)))
                fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['V4.5']), name='AMLS',
                                             fill='tozeroy', fillcolor=f'rgba({r_c},{g_c},{b_c},0.1)',
                                             line=dict(color=main_color, width=2.2)))
                fig_dd.update_layout(
                    title=dict(text="Drawdown Curve", font=dict(family='DM Mono', size=13, color=t_color)),
                    height=260, **chart_layout
                )
                fig_dd.update_xaxes(**_ax)
                fig_dd.update_yaxes(tickformat='.0%', **_ax)
                with st.container(border=True):
                    st.plotly_chart(fig_dd, use_container_width=True)

                st.divider()
            if st.button("✦ AI 추론 요약 실행", use_container_width=True):
                try:
                    import google.generativeai as genai
                    api_key = st.secrets["GEMINI_API_KEY"]
                    genai.configure(api_key=api_key)
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model  = genai.GenerativeModel(models[0].replace('models/',''))
                    prompt = f"""너는 최고 퀀트 애널리스트야. AMLS V4.5 전략 백테스트 결과를 분석해.
[AMLS] 누적수익률: {ret_o*100:.1f}%, CAGR: {cagr_o*100:.1f}%, MDD: {mdd_o*100:.1f}%
[TQQQ] 누적수익률: {ret_t*100:.1f}%, CAGR: {cagr_t*100:.1f}%, MDD: {mdd_t*100:.1f}%
AMLS 전략이 레버리지 MDD를 어떻게 회피하면서 수익을 냈는지 3단락으로 분석해."""
                    with st.spinner("AI 분석 중..."):
                        response = model.generate_content(prompt)
                        st.markdown(apply_theme(f"""<div class="glass-card" style="height:auto !important; padding:28px !important; color:#CBD5E1; font-weight:400; line-height:1.75; font-size:0.95em;">{response.text}</div>"""), unsafe_allow_html=True)
                except KeyError:
                    st.error("🚨 GEMINI_API_KEY 누락")

# ──────────────────────────────────────────
elif page == "📰 Macro News":
    headlines_for_ai, news_items = fetch_macro_news()

    st.markdown(apply_theme(f"""
    <div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);border-top:2px solid #111118;display:flex;flex-direction:row;align-items:center;gap:20px;margin-bottom:24px;padding:20px 28px;">
        <div style="font-size:2.2em; line-height:1;">📰</div>
        <div>
            <h2 style="margin:0; font-family:'Syne'; font-size:1.65em; font-weight:800; letter-spacing:-1px; color:#0F172A;">Global Macro  ·  AI Briefing</h2>
            <p style="margin:5px 0 0; font-family:'DM Mono'; font-size:0.68em; color:#10B981; letter-spacing:0.18em; text-transform:uppercase;">Wall Street Analysis Engine</p>
        </div>
        <div style="margin-left:auto; background:rgba(16,185,129,0.1); padding:6px 18px; border-radius:50px; font-family:'DM Mono'; font-size:0.72em; font-weight:400; color:#10B981; border:1px solid rgba(16,185,129,0.3); letter-spacing:0.06em;">{rt_label}</div>
    </div>
    """), unsafe_allow_html=True)

    with st.expander("✦ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("↻ 심층 추론 요약 실행", use_container_width=True):
            try:
                import google.generativeai as genai
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai:
                    st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("AI 분석 중..."):
                        genai.configure(api_key=api_key)
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model  = genai.GenerativeModel(models[0].replace('models/',''))
                        prompt = "너는 퀀트 애널리스트야. 다음 뉴스를 섹터별, 리스크 요소, 최종 투자 스탠스로 나누어 3문단으로 요약해.\n" + "\n".join(headlines_for_ai)
                        response = model.generate_content(prompt)
                        st.markdown(apply_theme(f"""<div class="glass-card" style="height:auto !important; padding:28px !important; color:#CBD5E1; font-weight:400; line-height:1.75; font-size:0.95em;">{response.text}</div>"""), unsafe_allow_html=True)
            except KeyError:
                st.error("🚨 GEMINI_API_KEY 누락")

    st.divider()

    if news_items:
        st.markdown("""<div style="font-family:'Syne'; font-size:1.15em; font-weight:700; color:#0F172A; margin-bottom:18px; letter-spacing:-0.3px;">Latest Headlines</div>""", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, item in enumerate(news_items):
            with cols[idx % 3]:
                html_snippet = apply_theme(f"""
                <div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.10);border-top:2px solid rgba(0,0,0,0.18);padding:16px;margin-bottom:10px;height:138px;display:flex;flex-direction:column;justify-content:space-between;transition:border-top-color 0.15s;">
                    <div style="font-family:'DM Sans'; font-weight:400; font-size:0.9em; line-height:1.5; color:#4A5568; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                        <a href="{item['link']}" target="_blank" style="color:#4A5568; text-decoration:none; transition:color 0.2s;" onmouseover="this.style.color='#10B981'" onmouseout="this.style.color='#94A3B8'">{item['title']}</a>
                    </div>
                    <div style="font-family:'DM Mono'; font-size:0.68em; color:#4A5568; margin-top:8px; letter-spacing:0.06em;">{item['date']}</div>
                </div>
                """)
                st.markdown(html_snippet, unsafe_allow_html=True)
