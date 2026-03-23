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
# 0. UI Theme & Helpers (SaaS + Connected Tabs)
# ==========================================
def apply_amls_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        --color-primary:      #5B5CFF;
        --color-accent:       #00C48C;
        --color-danger:       #FF4D4F;
        --color-warning:      #E6A817;
        --color-bg-page:      #F4F5F7; /* 약간 톤다운된 배경으로 카드 대비 강화 */
        --color-bg-card:      #FFFFFF;
        --color-bg-sidebar:   #FFFFFF;
        --color-text-primary: #1A1D2E;
        --color-text-sub:     #9FA2B4;
        --color-border:       #EAECF0;
        --shadow-card:        0 4px 20px rgba(0,0,0,0.04);
        --radius-card:        16px;
        --radius-pill:        999px;
    }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'DM Sans', sans-serif !important;
        background-color: var(--color-bg-page) !important;
        color: var(--color-text-primary) !important;
    }

    [data-testid="stMainBlockContainer"] { padding: 24px 32px !important; max-width: 1400px; }

    /* =========================================
       🔥 사이드바 집중 개편: 탭(Tab) 연결형 UI 복원 및 강화
       ========================================= */
    [data-testid="stSidebar"] {
        background-color: var(--color-bg-sidebar) !important;
        border-right: none !important;
        box-shadow: 2px 0 20px rgba(0,0,0,0.03) !important;
        padding: 24px 0px 24px 16px !important; /* 오른쪽 패딩을 0으로 만들어 탭이 끝까지 닿게 함 */
    }

    [data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif !important; }

    /* 로고 & 타이틀 영역 (여백 수동 조절) */
    .sidebar-header-custom { padding-right: 16px; margin-bottom: 30px; }
    .sidebar-header-custom h1 { font-size: 22px !important; font-weight: 800 !important; color: var(--color-primary) !important; letter-spacing: -0.5px !important; margin: 0 0 4px 0 !important; }
    .sidebar-header-custom p { font-size: 10px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.15em !important; color: var(--color-text-sub) !important; margin: 0 !important; }

    /* 1. 기본 라디오 버튼 동그라미 완전히 삭제 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child,
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] label[data-baseweb="radio"] svg { 
        display: none !important; opacity: 0 !important; width: 0px !important; height: 0px !important; margin: 0 !important; padding: 0 !important; 
    }
    
    /* 2. 메뉴 컨테이너 레이아웃 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] { gap: 6px; padding: 0 !important; background: transparent !important; }
    
    /* 3. 메뉴 아이템 기본 상태 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label {
        background: transparent !important;
        border: none !important;
        border-radius: 12px 0 0 12px !important;
        padding: 14px 20px !important;
        cursor: pointer; 
        width: 100%; 
        margin: 0 !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }
    
    /* 4. 메뉴 텍스트 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label p {
        font-size: 14px !important; font-weight: 600 !important; color: var(--color-text-sub) !important; margin: 0 !important; transition: all 0.2s ease !important;
    }
    
    /* 5. Hover 효과 (글씨 우측 이동 + 연한 보라색 스며들기) */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label:hover { background: rgba(91, 92, 255, 0.04) !important; }
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label:hover p { color: var(--color-primary) !important; transform: translateX(6px) !important; }
    
    /* 6. 🚨 Checked 상태 (오른쪽 메인화면과 하나로 연결되는 예쁜 탭 디자인) 🚨 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
        background: var(--color-bg-page) !important; /* 메인 배경색과 일치시켜 연결감 극대화 */
        border-left: 4px solid var(--color-primary) !important;
        box-shadow: -5px 5px 15px rgba(0,0,0,0.02) !important;
        margin-right: -10px !important; /* 오른쪽 끝을 화면 바깥으로 확장 */
        padding-right: 30px !important;
    }
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) p {
        color: var(--color-primary) !important; font-weight: 800 !important; transform: translateX(6px) !important;
    }

    .sidebar-footer { padding-right: 16px; margin-top: 40px; border-top: 1px solid var(--color-border); padding-top: 20px; }
    .sidebar-footer p { font-size: 10px !important; font-weight: 600 !important; color: var(--color-text-sub) !important; }

    /* =========================================
       Cards & Metrics
       ========================================= */
    .glass-card {
        background-color: var(--color-bg-card) !important; border-radius: var(--radius-card) !important;
        box-shadow: var(--shadow-card) !important; border: 1px solid var(--color-border) !important;
        padding: 24px !important; height: 100%; display: flex; flex-direction: column; justify-content: space-between;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.06) !important; }

    [data-testid="stMetric"] { background-color: var(--color-bg-card) !important; border-radius: var(--radius-card) !important; box-shadow: var(--shadow-card) !important; border: 1px solid var(--color-border) !important; padding: 20px !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; color: var(--color-text-sub) !important; }
    [data-testid="stMetricValue"] { font-size: 32px !important; font-weight: 800 !important; color: var(--color-text-primary) !important; line-height: 1.2 !important; }
    [data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 700 !important; padding: 4px 10px !important; border-radius: var(--radius-pill) !important; display: inline-flex !important; align-items: center !important; }
    [data-testid="stMetricDelta"][data-direction="up"], [data-testid="stMetricDelta"] svg[class*="positive"] ~ span { background-color: #E6FAF4 !important; color: var(--color-accent) !important; }
    [data-testid="stMetricDelta"][data-direction="down"] { background-color: #FFF0F0 !important; color: var(--color-danger) !important; }

    .card-title { font-size: 12px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; color: var(--color-text-sub) !important; margin-bottom: 12px !important; border-bottom: 1px solid var(--color-border); padding-bottom: 8px; }
    .card-status-value { font-size: 26px !important; font-weight: 800 !important; color: var(--color-primary) !important; line-height: 1.2 !important; }
    .card-status-sub { font-size: 13px !important; font-weight: 600 !important; color: var(--color-text-sub) !important; margin-top: 4px !important; margin-bottom: 16px !important; }
    
    .condition-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px dashed var(--color-border); font-size: 13px; font-weight: 500; color: var(--color-text-primary); }
    .condition-row:last-child { border-bottom: none; }
    .condition-value-pass { color: var(--color-accent); font-weight: 700; }
    .condition-value-fail { color: var(--color-danger); font-weight: 700; }

    .badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; justify-content: flex-start; }
    .badge-positive { background-color: rgba(0, 196, 140, 0.1); color: var(--color-accent); }
    .badge-negative { background-color: rgba(255, 77, 79, 0.1); color: var(--color-danger); }
    .badge-neutral { background-color: rgba(230, 168, 23, 0.1); color: var(--color-warning); }
    .badge-primary { background-color: rgba(91, 92, 255, 0.1); color: var(--color-primary); }

    .alert-banner { border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; display: flex; flex-direction: column; gap: 4px; }
    .alert-banner-negative { background-color: #FFF0F0; border-left: 5px solid var(--color-danger); }
    .alert-banner-neutral { background-color: #FFF8E1; border-left: 5px solid var(--color-warning); }
    .alert-banner-positive { background-color: #E6FAF4; border-left: 5px solid var(--color-accent); }
    .alert-title { font-size: 16px; font-weight: 800; }
    .alert-status { font-size: 13px; font-weight: 700; color: var(--color-text-primary); }
    .alert-body { font-size: 13px; font-weight: 500; color: var(--color-text-sub); line-height: 1.5; }

    .live-badge { display: inline-flex; align-items: center; gap: 6px; background-color: rgba(0, 196, 140, 0.1); border: 1px solid rgba(0, 196, 140, 0.3); border-radius: var(--radius-pill); padding: 4px 12px; font-size: 11px; font-weight: 800; color: var(--color-accent); margin-top: 12px; }
    .live-dot { width: 8px; height: 8px; border-radius: 50%; background-color: var(--color-accent); animation: pulse-green 1.5s infinite; }
    @keyframes pulse-green { 0% { box-shadow: 0 0 0 0 rgba(0,196,140,0.4); } 70% { box-shadow: 0 0 0 6px rgba(0,196,140,0); } 100% { box-shadow: 0 0 0 0 rgba(0,196,140,0); } }

    /* 데이터 테이블 (포트폴리오 등) */
    .data-table { width: 100%; border-collapse: separate; border-spacing: 0 8px; font-size: 13px; }
    .data-table th { font-weight: 700; color: var(--color-text-sub); border-bottom: none; padding: 8px 12px; text-align: right; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; }
    .data-table td { padding: 14px 12px; background: var(--color-bg-card); color: var(--color-text-primary); text-align: right; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); }
    .data-table tr { transition: transform 0.2s; }
    .data-table tr:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
    .data-table td:first-child { border-left: 1px solid var(--color-border); border-top-left-radius: 12px; border-bottom-left-radius: 12px; text-align: left; font-weight: 700; color: var(--color-primary); }
    .data-table td:last-child { border-right: 1px solid var(--color-border); border-top-right-radius: 12px; border-bottom-right-radius: 12px; text-align: center; }

    /* 기본 요소 정리 */
    h1, h2, h3 { font-family: 'DM Sans', sans-serif !important; font-weight: 800 !important; color: var(--color-text-primary) !important; letter-spacing: -0.5px; }
    h2 { font-size: 24px !important; margin-bottom: 24px !important; } 
    [data-testid="stPlotlyChart"] { background-color: var(--color-bg-card) !important; border-radius: var(--radius-card) !important; box-shadow: var(--shadow-card) !important; border: 1px solid var(--color-border) !important; padding: 16px !important; }
    [data-testid="stButton"] > button { background-color: var(--color-primary) !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-weight: 700 !important; font-size: 14px !important; padding: 10px 24px !important; transition: opacity 0.2s ease !important; }
    [data-testid="stButton"] > button:hover { opacity: 0.9 !important; }
    [data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div { background: var(--color-bg-card) !important; border: 1px solid var(--color-border) !important; border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

def badge(label: str, variant: str = "positive") -> str:
    icons = {"positive": "✅", "negative": "🔴", "neutral": "🟡", "primary": "🔵"}
    return f'<div class="badge badge-{variant}">{icons.get(variant, "")}&nbsp;{label}</div>'

def card_title(text: str) -> str: return f'<div class="card-title">{text}</div>'
def card_status(value: str, sub: str = "") -> str: return f'<div class="card-status-value">{value}</div><div class="card-status-sub">{sub}</div>'
def condition_row(label: str, value: str, passed: bool) -> str:
    cls = "condition-value-pass" if passed else "condition-value-fail"
    return f'<div class="condition-row"><span>{label}</span><span class="{cls}">{value} ●</span></div>'
def live_badge(count: int) -> str: return f'<div class="live-badge"><div class="live-dot"></div>LIVE ({count})</div>'
def alert_banner(title: str, status_line: str, body: str, variant: str = "negative") -> str:
    return f'<div class="alert-banner alert-banner-{variant}"><div class="alert-title" style="color:var(--color-{"accent" if variant=="positive" else "warning" if variant=="neutral" else "danger"});">{title}</div><div class="alert-status">{status_line}</div><div class="alert-body">{body}</div></div>'
def render_metric_card(title, ret, cagr, mdd, is_main=False):
    bg = "background: rgba(91, 92, 255, 0.03);" if is_main else ""
    bdr = "border: 2px solid var(--color-primary);" if is_main else ""
    return f"""<div class="glass-card" style="{bg} {bdr} height: auto !important; padding: 24px !important;">
    <div style="font-size: 12px; font-weight: 700; color: var(--color-text-sub); text-transform:uppercase; margin-bottom: 8px;">{title}</div>
    <div style="font-size: 28px; font-weight: 800; color: var(--color-text-primary); margin-bottom: 12px;">CAGR {cagr*100:.1f}%</div>
    <div style="font-size: 13px; font-weight: 600; color: var(--color-text-sub);">누적: <span style="color: var(--color-accent);">{ret*100:.1f}%</span> | MDD: <span style="color: var(--color-danger);">{mdd*100:.1f}%</span></div></div>"""

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
                st.session_state.portfolio.update(json.load(f))
        except: pass
sanitize_portfolio()

def save_portfolio_to_disk():
    try:
        with open(PORTFOLIO_FILE, 'w') as f: json.dump(st.session_state.portfolio, f)
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
                cnt += 1; 
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
live_regime  = get_target_v45(last_row)            
hist_regime  = int(df.iloc[-1]['Regime'])            
curr_regime  = live_regime if live_regime > hist_regime else hist_regime

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

# 차트 컬러 매핑
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
st.sidebar.markdown("""
<div class="sidebar-header-custom">
    <h1>AMLS V4.5</h1>
    <p>Quantitative Engine</p>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown(live_badge(len(rt_injected)), unsafe_allow_html=True)
page = st.sidebar.radio("MENU", ["📊 Dashboard", "💼 Portfolio", "🍫 8-Pack Radar", "📈 Backtest Lab", "📰 Macro News"], label_visibility="collapsed")
st.sidebar.markdown("<div class='sidebar-footer'><p>Powered by Apex<br>&copy; 2026 SEYOON.</p></div>", unsafe_allow_html=True)

# ==========================================
# 3. 페이지 라우팅
# ==========================================
if page == "📊 Dashboard":
    st.markdown("<h2>Dashboard Overview</h2>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.markdown(f"""<div class="glass-card">
            {card_title("MARKET REGIME")}
            {card_status(regime_info[curr_regime][0], regime_info[curr_regime][1])}
            {condition_row('VIX < 40', f'{vix_close:.2f}', vix_close<=40)}
            {condition_row('QQQ > 200MA', f'${qqq_close:.0f}', qqq_close>=qqq_ma200)}
            {condition_row('50MA ≥ 200MA', f'${qqq_ma50:.0f}', qqq_ma50>=qqq_ma200)}
            <div style="margin-top:auto; padding-top:16px; font-size:12px; font-weight:600; color:var(--color-primary); text-align:center;">{regime_committee_msg}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        soxl_title  = "SOXL 진입 승인" if smh_cond else "USD 방어 진입"
        soxl_strat  = "3x Leverage" if smh_cond else "2x Defense"
        st.markdown(f"""<div class="glass-card">
            {card_title("SEMI-CONDUCTOR (SOXL)")}
            {card_status(soxl_title, soxl_strat)}
            {condition_row('SMH > 50MA', f'${smh_close:.1f}', smh_c1)}
            {condition_row('Mom (1M>10%)', f'{smh_1m*100:.1f}%', smh_c2)}
            {condition_row('RSI > 50', f'{smh_rsi:.1f}', smh_c3)}
            <div style="margin-top:auto; padding-top:16px; font-size:12px; font-weight:600; color:var(--color-text-sub); text-align:center;">※ 3 filters required</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        w_rows = "".join([f'<div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--color-border); font-size:14px; font-weight:500;"><span>{k}</span><span style="color:var(--color-primary); font-weight:700;">{v*100:.0f}%</span></div>' for k,v in target_weights.items() if v > 0])
        st.markdown(f'<div class="glass-card">{card_title("TARGET WEIGHTS")}<div style="display:flex; justify-content:space-between; font-size:11px; font-weight:700; color:var(--color-text-sub); border-bottom:1px solid var(--color-border); padding-bottom:8px; margin-bottom:8px;"><span>ASSET</span><span>WEIGHT</span></div>{w_rows}</div>', unsafe_allow_html=True)

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

elif page == "💼 Portfolio":
    st.markdown("<h2>Portfolio & Rebalancing</h2>", unsafe_allow_html=True)
    
    col_up, col_down = st.columns(2)
    with col_up:
        uploaded_file = st.file_uploader("📂 Restore from JSON", type="json")
        if uploaded_file is not None:
            try:
                st.session_state.portfolio.update(json.load(uploaded_file))
                sanitize_portfolio() 
                save_portfolio_to_disk()
                st.success("포트폴리오 복구 완료")
            except: st.error("파일 형식 오류")
    with col_down:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("💾 Backup to JSON", data=json.dumps(st.session_state.portfolio), file_name="portfolio.json", mime="application/json", use_container_width=True)

    st.divider()
    
    editor_data = [{"Asset": a, "Shares": float(st.session_state.portfolio[a].get('shares',0.0)), "Avg Price($)": float(st.session_state.portfolio[a].get('avg_price',1.0 if a=='CASH' else 0.0)), "FX Rate(₩)": float(st.session_state.portfolio[a].get('fx',1350.0))} for a in ASSET_LIST]
    st.markdown('<div class="glass-card" style="padding: 16px !important;">', unsafe_allow_html=True)
    edited_df = st.data_editor(pd.DataFrame(editor_data), disabled=["Asset"], hide_index=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    for _, row in edited_df.iterrows():
        st.session_state.portfolio[row["Asset"]] = {'shares': float(row["Shares"]), 'avg_price': float(row["Avg Price($)"]), 'fx': float(row["FX Rate(₩)"])}
    save_portfolio_to_disk()
    
    st.markdown("<br><h3>Action Plan</h3>", unsafe_allow_html=True)
    
    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': current_prices[t] = 1.0
        elif t in rt_prices: current_prices[t] = rt_prices[t]
        elif t in df.columns: current_prices[t] = df[t].iloc[-1]
        else: current_prices[t] = 0.0
            
    cur_fx = rt_prices.get('USDKRW=X', 1350.0)
    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}
    total_val_usd = sum(curr_vals.values())
    
    st.metric("Total NAV", f"${total_val_usd:,.2f}", f"FX: ₩{cur_fx:,.2f}")
    
    if total_val_usd > 0:
        c_green, c_red = "#00C48C", "#FF4D4F"
        pie_layout = dict(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="DM Sans", color="#1A1D2E", size=12))
        diff_vals = {a: (total_val_usd * target_weights.get(a, 0.0)) - curr_vals[a] for a in ASSET_LIST}
        
        chart_c1, chart_c2, chart_c3 = st.columns([1, 1, 1.5])
        labels_cur = [a for a in ASSET_LIST if curr_vals[a] > 0]
        vals_cur = [curr_vals[a] for a in labels_cur]
        if sum(vals_cur) > 0:
            fig_cur = go.Figure(data=[go.Pie(labels=labels_cur, values=vals_cur, hole=.4, textinfo='label+percent', marker=dict(colors=[line_c, dash_c, '#8B8CFF', '#00E6A4']))])
            fig_cur.update_layout(title=dict(text="Current", font=dict(family="DM Sans", size=16, color="#1A1D2E")), **pie_layout)
            with chart_c1: st.plotly_chart(fig_cur, use_container_width=True)
        
        labels_tgt = [a for a in ASSET_LIST if target_weights.get(a, 0) > 0]
        vals_tgt = [target_weights.get(a, 0) for a in labels_tgt]
        fig_tgt = go.Figure(data=[go.Pie(labels=labels_tgt, values=vals_tgt, hole=.4, textinfo='label+percent', marker=dict(colors=[line_c, dash_c, '#8B8CFF', '#00E6A4']))])
        fig_tgt.update_layout(title=dict(text=f"Target (R{curr_regime})", font=dict(family="DM Sans", size=16, color="#1A1D2E")), **pie_layout)
        with chart_c2: st.plotly_chart(fig_tgt, use_container_width=True)
        
        diff_labels = [a for a in ASSET_LIST if abs(diff_vals[a]) >= 1.0]
        diff_values = [diff_vals[a] for a in diff_labels]
        diff_colors = [c_green if v > 0 else c_red for v in diff_values]
        if diff_labels:
            fig_bar = go.Figure(data=[go.Bar(x=diff_labels, y=diff_values, marker_color=diff_colors, text=[f"${v:,.0f}" for v in diff_values], textposition='auto')])
            fig_bar.update_layout(title=dict(text="Rebalancing Amounts ($)", font=dict(family="DM Sans", size=16, color="#1A1D2E")), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=20, l=20, r=20))
            with chart_c3: st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown(f"<h4 style='margin-top: 24px;'>Quick Orders</h4>", unsafe_allow_html=True)
        summary_html = f"<div class='glass-card' style='flex-direction:row; gap: 20px; padding: 24px !important;'>"
        sell_text = "<div style='flex: 1;'><strong style='color:var(--color-danger); font-size:16px;'>🔴 SELL</strong><br><br>"
        buy_text = "<div style='flex: 1;'><strong style='color:var(--color-accent); font-size:16px;'>🟢 BUY</strong><br><br>"
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff < -cur_p * 0.05: sell_text += f"<div style='margin-bottom:8px;'><span style='font-weight:700;'>{asset}</span> : <span style='color:var(--color-danger); font-weight:700;'>{abs(diff)/cur_p:,.2f}주</span> 매도</div>"
            elif asset == 'CASH' and diff < -1.0: sell_text += f"<div style='margin-bottom:8px;'><span style='font-weight:700;'>CASH</span> : <span style='color:var(--color-danger); font-weight:700;'>${abs(diff):,.0f}</span> 사용</div>"
            
            if asset != 'CASH' and diff > cur_p * 0.05: buy_text += f"<div style='margin-bottom:8px;'><span style='font-weight:700;'>{asset}</span> : <span style='color:var(--color-accent); font-weight:700;'>{diff/cur_p:,.2f}주</span> 매수</div>"
            elif asset == 'CASH' and diff > 1.0: buy_text += f"<div style='margin-bottom:8px;'><span style='font-weight:700;'>CASH</span> : <span style='color:var(--color-accent); font-weight:700;'>${diff:,.0f}</span> 확보</div>"
                
        summary_html += sell_text + "</div>" + buy_text + "</div></div><br>"
        st.markdown(summary_html, unsafe_allow_html=True)

        rebal_html = """<div style="overflow-x: auto;"><table class="data-table"><thead><tr><th>Asset</th><th>Avg &rarr; Cur</th><th>Ret (KRW)</th><th>Value ($)</th><th>Target %</th><th>Target ($)</th><th>Diff ($)</th><th style="text-align:center;">Action</th></tr></thead><tbody>"""
        for asset in ASSET_LIST:
            shares, avg_p, pur_fx = st.session_state.portfolio[asset]['shares'], st.session_state.portfolio[asset]['avg_price'], st.session_state.portfolio[asset]['fx']
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            curr_v, tgt_w = curr_vals[asset], target_weights.get(asset, 0.0)
            tgt_v, diff = total_val_usd * tgt_w, diff_vals[asset]
            
            if asset == 'CASH':
                avg_p_str, ret_usd, ret_krw = "-", 0.0, ((cur_fx / pur_fx) - 1) * 100 if pur_fx > 0 else 0.0
            else:
                avg_p_str = f"${avg_p:,.2f} &rarr; ${cur_p:,.2f}"
                ret_usd = (cur_p / avg_p - 1) * 100 if avg_p > 0 else 0.0
                ret_krw = ((cur_p * cur_fx) / (avg_p * pur_fx) - 1) * 100 if (avg_p > 0 and pur_fx > 0) else 0.0
                
            ret_usd_color = "var(--color-accent)" if ret_usd >= 0 else "var(--color-danger)"
            ret_usd_str = f"{ret_usd:+.2f}%" if asset != 'CASH' else "-"
            
            if abs(diff) < cur_p * 0.05 and asset != 'CASH': action = "<span style='color:var(--color-text-sub); font-weight:700;'>HOLD</span>"; diff_str = "-"
            elif abs(diff) < 1.0 and asset == 'CASH': action = "<span style='color:var(--color-text-sub); font-weight:700;'>HOLD</span>"; diff_str = "-"
            elif diff > 0: action = f"<span style='color:var(--color-accent); font-weight:700; background:rgba(0,196,140,0.1); padding:4px 10px; border-radius:6px;'>BUY</span>"; diff_str = f"<span style='color:var(--color-accent); font-weight:700;'>+${diff:,.0f}</span>"
            else: action = f"<span style='color:var(--color-danger); font-weight:700; background:rgba(255,77,79,0.1); padding:4px 10px; border-radius:6px;'>SELL</span>"; diff_str = f"<span style='color:var(--color-danger); font-weight:700;'>-${abs(diff):,.0f}</span>"
                
            if tgt_w > 0 or curr_v > 0 or shares > 0:
                rebal_html += f"""<tr><td>{asset}</td><td style="color:var(--color-text-sub);">{avg_p_str}</td><td><span style="color:{ret_usd_color}; font-weight:700;">{ret_usd_str}</span></td><td style="font-weight:600;">{curr_v:,.0f}</td><td style="color:var(--color-primary); font-weight:700;">{tgt_w*100:.0f}%</td><td style="font-weight:600;">{tgt_v:,.0f}</td><td>{diff_str}</td><td style="text-align:center;">{action}</td></tr>"""
        rebal_html += "</tbody></table></div>"
        st.markdown(f'<div class="glass-card" style="padding:16px !important;">{rebal_html}</div>', unsafe_allow_html=True)

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

    if risk_cnt >= 2: st.markdown(alert_banner("🔴 극단적 위험 구간 (Risk-Off)", f"위험 요소 {risk_cnt}개 / 경고 {warn_cnt}개", "복수의 매크로 지표에서 강력한 하락 경고가 발생했습니다.", "negative"), unsafe_allow_html=True)
    elif warn_cnt >= 3 or risk_cnt == 1: st.markdown(alert_banner("🟡 변동성 주의 (Warning)", f"위험 요소 {risk_cnt}개 / 경고 {warn_cnt}개", "시장의 균열 조짐이 감지되었습니다. 신규 매수를 보류하십시오.", "neutral"), unsafe_allow_html=True)
    else: st.markdown(alert_banner("🟢 안정적 순항 (Safe)", f"위험 요소 {risk_cnt}개 / 안전 {safe_cnt}개", "매크로 지표들이 안정적인 추세를 지지하고 있습니다.", "positive"), unsafe_allow_html=True)

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
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("1. DCA (RSI)")}{b1}</div>', unsafe_allow_html=True)
        fig1=go.Figure(); fig1.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_RSI'],line=dict(color=line_c,width=2.5)))
        fig1.add_hline(y=70,line_dash='dash',line_color=dash_c); fig1.add_hline(y=30,line_dash='dash',line_color=rsi_low_c)
        fig1.update_layout(**radar_layout,yaxis=dict(range=[10,90]),showlegend=False)
        st.plotly_chart(fig1,use_container_width=True)
    with row1[1]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("2. Drawdown")}{b2}</div>', unsafe_allow_html=True)
        fig2=go.Figure(); fig2.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_DD'],fill='tozeroy',line=dict(color=dash_c,width=2.5)))
        fig2.update_layout(**radar_layout,yaxis=dict(tickformat='.0%'),showlegend=False)
        st.plotly_chart(fig2,use_container_width=True)
    with row1[2]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("3. Fear & Greed")}{b3}</div>', unsafe_allow_html=True)
        gauge_steps = [{'range':[0,25],'color':"#FF4D4F"},{'range':[25,45],'color':"#E6A817"},{'range':[45,55],'color':"#EAECF0"},{'range':[55,100],'color':"#00C48C"}]
        fig3=go.Figure(go.Indicator(mode="gauge+number",value=fg_score,domain={'x':[0,1],'y':[0,1]}, gauge={'axis':{'range':[0,100]},'bar':{'color':line_c},'steps':gauge_steps}))
        fig3.update_layout(height=200,margin=dict(l=15,r=15,t=10,b=10),paper_bgcolor=b_color,font=dict(family="DM Sans",color=t_color))
        st.plotly_chart(fig3,use_container_width=True)
    with row1[3]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("4. Sector (1M)")}{badge("TREND", "primary")}</div>', unsafe_allow_html=True)
        fig4=go.Figure(go.Bar(x=sec_df['수익률'],y=sec_df['섹터'],orientation='h', marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']]))
        fig4.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig4,use_container_width=True)

    row2 = st.columns(4)
    with row2[0]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("5. Credit Spread")}{b5}</div>', unsafe_allow_html=True)
        fig5=go.Figure(); fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_Ratio'],line=dict(color=line_c,width=2.5)))
        fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_MA50'],line=dict(color=dash_c,dash='dot')))
        fig5.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig5,use_container_width=True)
    with row2[1]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("6. Market Breadth")}{b6}</div>', unsafe_allow_html=True)
        fig6=go.Figure(); fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_20d_Ret'],line=dict(color=line_c,width=2.5)))
        fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQE_20d_Ret'],line=dict(color=dash_c,dash='dot')))
        fig6.update_layout(**radar_layout,showlegend=False,yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6,use_container_width=True)
    with row2[2]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("7. Gold / Equity")}{b7}</div>', unsafe_allow_html=True)
        fig7=go.Figure(); fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_Ratio'],line=dict(color=line_c,width=2.5)))
        fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_MA50'],line=dict(color=dash_c,dash='dot')))
        fig7.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig7,use_container_width=True)
    with row2[3]:
        st.markdown(f'<div class="glass-card" style="padding:16px !important; margin-bottom:16px;">{card_title("8. USD (UUP)")}{b8}</div>', unsafe_allow_html=True)
        fig8=go.Figure(); fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP'],line=dict(color=line_c,width=2.5)))
        fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP_MA50'],line=dict(color=dash_c,dash='dot')))
        fig8.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig8,use_container_width=True)

elif page == "📈 Backtest Lab":
    st.markdown("<h2>Backtest Lab</h2>", unsafe_allow_html=True)

    with st.spinner("시뮬레이션 가동 중..."):
        daily_ret = df[['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD']].pct_change().fillna(0)
        w_orig = get_weights_v45(df['Regime'].iloc[0], False)
        
        val_o, val_q, val_qld, val_tqqq = 10000, 10000, 10000, 10000
        hist_o, hist_q, hist_qld, hist_tqqq = [val_o], [val_q], [val_qld], [val_tqqq]
        
        for i in range(1, len(df)):
            ret_o = sum(w_orig.get(t,0) * daily_ret[t].iloc[i] for t in w_orig if t in daily_ret.columns)
            val_o *= (1 + ret_o); val_q *= (1 + daily_ret['QQQ'].iloc[i])
            val_qld *= (1 + daily_ret['QLD'].iloc[i]); val_tqqq *= (1 + daily_ret['TQQQ'].iloc[i])
            hist_o.append(val_o); hist_q.append(val_q); hist_qld.append(val_qld); hist_tqqq.append(val_tqqq)
            
            smh_cond_i = (df['SMH'].iloc[i] > df['SMH_MA50'].iloc[i]) and (df['SMH_3M_Ret'].iloc[i] > 0.05) and (df['SMH_RSI'].iloc[i] > 50)
            w_orig = get_weights_v45(df['Regime'].iloc[i], smh_cond_i)
            
        res_df = pd.DataFrame(index=df.index)
        res_df['V4.5'], res_df['QQQ'], res_df['QLD'], res_df['TQQQ'] = hist_o, hist_q, hist_qld, hist_tqqq
        days = (res_df.index[-1] - res_df.index[0]).days
        
        def calc_metrics(series):
            ret = (series[-1]/series[0]) - 1
            cagr = (series[-1]/series[0]) ** (365.25 / days) - 1 if days > 0 else 0
            mdd = ((series / series.cummax()) - 1).min()
            return ret, cagr, mdd
            
        ret_o, cagr_o, mdd_o       = calc_metrics(res_df['V4.5'])
        ret_q, cagr_q, mdd_q       = calc_metrics(res_df['QQQ'])
        ret_qld, cagr_qld, mdd_qld = calc_metrics(res_df['QLD'])
        ret_t, cagr_t, mdd_t       = calc_metrics(res_df['TQQQ'])
        
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.markdown(render_metric_card("✨ AMLS V4.5", ret_o, cagr_o, mdd_o, True), unsafe_allow_html=True)
        mc2.markdown(render_metric_card("QQQ", ret_q, cagr_q, mdd_q), unsafe_allow_html=True)
        mc3.markdown(render_metric_card("QLD", ret_qld, cagr_qld, mdd_qld), unsafe_allow_html=True)
        mc4.markdown(render_metric_card("TQQQ", ret_t, cagr_t, mdd_t), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QQQ'], name='QQQ', line=dict(color=dash_c, width=1.5, dash='dot')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QLD'], name='QLD', line=dict(color='#8B8CFF', width=1.5, dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['TQQQ'], name='TQQQ', line=dict(color='#FF4D4F', width=1.5, dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['V4.5'], name='AMLS', line=dict(color=line_c, width=3.5)))
        fig_eq.update_layout(title=dict(text="Equity Curve (Log)", font=dict(family='DM Sans', size=16, color=t_color)), height=400, yaxis_type='log', **chart_layout)
        st.plotly_chart(fig_eq, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        def get_dd_series(series): return (series / series.cummax()) - 1
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QQQ']), name='QQQ', line=dict(color=dash_c, width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QLD']), name='QLD', line=dict(color='#8B8CFF', width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['TQQQ']), name='TQQQ', line=dict(color='#FF4D4F', width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['V4.5']), name='AMLS', fill='tozeroy', line=dict(color=line_c, width=2.5)))
        fig_dd.update_layout(title=dict(text="Drawdown Curve", font=dict(family='DM Sans', size=16, color=t_color)), height=300, yaxis=dict(tickformat='.0%'), **chart_layout)
        st.plotly_chart(fig_dd, use_container_width=True)
        
        st.divider()
        if st.button("✨ AI 추론 요약 실행", use_container_width=True):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model = genai.GenerativeModel(models[0].replace('models/',''))
                prompt = f"""너는 최고 퀀트 애널리스트야. AMLS V4.5 전략 백테스트 결과를 분석해.
                [AMLS] 누적수익률: {ret_o*100:.1f}%, CAGR: {cagr_o*100:.1f}%, MDD: {mdd_o*100:.1f}%
                [TQQQ] 누적수익률: {ret_t*100:.1f}%, CAGR: {cagr_t*100:.1f}%, MDD: {mdd_t*100:.1f}%
                AMLS 전략이 레버리지 MDD를 어떻게 회피하면서 수익을 냈는지 3단락으로 분석해."""
                with st.spinner("AI 분석 중..."):
                    st.markdown(f'<div class="glass-card" style="padding: 24px !important;">{model.generate_content(prompt).text}</div>', unsafe_allow_html=True)
            except KeyError: st.error("🚨 GEMINI_API_KEY 누락")

elif page == "📰 Macro News":
    headlines_for_ai, news_items = fetch_macro_news()

    st.markdown(f"""
    <div class="glass-card" style="flex-direction:row; align-items:center; gap:20px; margin-bottom: 24px; padding: 24px 32px !important;">
      <div style="font-size:32px;">📰</div>
      <div>
          <h2 style="margin:0; font-size: 20px;">GLOBAL MACRO & AI BRIEFING</h2>
          <p style="margin:4px 0 0 0; color:var(--color-text-sub); font-weight:600; font-size: 13px;">월스트리트 주요 속보와 AI 애널리스트의 심층 고찰</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("✨ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("🚀 심층 추론 요약 실행", use_container_width=True):
            try:
                if not headlines_for_ai: st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("AI 분석 중..."):
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model  = genai.GenerativeModel(models[0].replace('models/',''))
                        prompt = "너는 퀀트 애널리스트야. 다음 뉴스를 섹터별, 리스크 요소, 최종 투자 스탠스로 나누어 3문단으로 요약해.\n" + "\n".join(headlines_for_ai)
                        st.markdown(f'<div style="padding: 16px 0;">{model.generate_content(prompt).text}</div>', unsafe_allow_html=True)
            except KeyError: st.error("🚨 GEMINI_API_KEY 누락")

    st.divider()

    if news_items:
        st.markdown("<h3>Latest Headlines</h3>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx,item in enumerate(news_items):
            with cols[idx%3]:
                st.markdown(f"""<div class="glass-card" style="padding:20px !important; margin-bottom:16px; height:160px !important; display:flex; flex-direction:column; justify-content:space-between;">
                    <div style="font-weight:600; font-size:14px; line-height:1.5; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                        <a href="{item['link']}" target="_blank" style="color:var(--color-text-primary); text-decoration:none;">{item['title']}</a>
                    </div>
                    <div style="color:var(--color-text-sub); font-size:12px; font-weight:700; margin-top:12px;">{item['date']}</div>
                </div>""", unsafe_allow_html=True)
