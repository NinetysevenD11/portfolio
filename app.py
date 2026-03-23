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
st.set_page_config(page_title="AMLS V4.5 FINANCE STRATEGY", layout="wide", page_icon="🌿", initial_sidebar_state="expanded")

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
    st.error("🚨 야후 파이낸스(Yahoo Finance) 통신 지연. 잠시 후 새로고침 해주세요.")
    st.stop()

last_row    = df.iloc[-1].copy()
rt_injected = []
for ticker, price in rt_prices.items():
    if ticker in last_row.index and price > 0:
        last_row[ticker] = price; rt_injected.append(ticker)
if 'QQQ' in rt_injected:
    last_row['QQQ_DD'] = (last_row['QQQ'] / last_row['QQQ_High52']) - 1
if 'HYG' in rt_injected and 'IEF' in rt_injected:
    last_row['HYG_IEF_Ratio'] = last_row['HYG'] / last_row['IEF']
rt_ok    = len(rt_injected) >= 3
rt_label = f"🟢 LIVE ({len(rt_injected)})" if rt_ok else "🟡 DELAYED"

vix_close, vix_ma5, vix_ma20 = last_row['^VIX'], last_row['VIX_MA5'], last_row['VIX_MA20']
qqq_close, qqq_ma50, qqq_ma200 = last_row['QQQ'], last_row['QQQ_MA50'], last_row['QQQ_MA200']
smh_close, smh_ma50, smh_3m, smh_1m, smh_rsi = (last_row['SMH'], last_row['SMH_MA50'],
    last_row['SMH_3M_Ret'], last_row['SMH_1M_Ret'], last_row['SMH_RSI'])

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
target_regime = live_regime

# 반도체 진입 조건
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

# 차트 전역 색상 변수 (Light Mint Theme)
b_color = 'rgba(0,0,0,0)'
t_color = '#1E293B'
line_c = '#10B981'
dash_c = '#94A3B8'
rsi_low_c = '#10B981'
regime_colors={1:'rgba(0,0,0,0.0)', 2:'rgba(16, 185, 129, 0.05)', 3:'rgba(245, 158, 11, 0.08)', 4:'rgba(239, 68, 68, 0.1)'}
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
regime_info  = {1:("R1 BULL","풀 가동"),2:("R2 CORR","방어 진입"), 3:("R3 BEAR","대피"),4:("R4 PANIC","최대 방어")}

# ==========================================
# 2. Light Mint Glass UI CSS (+ 탭 연결형 사이드바)
# ==========================================
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;800&display=swap');
    
    :root {
        --bg-main: #F8FAFC; 
        --text-main: #0F172A; 
        --text-muted: #64748B; 
        --accent-mint: #10B981; 
        --accent-dark: #047857;
    }

    /* [배경] 밝고 깨끗한 화이트 & 민트 메쉬 그라데이션 */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-main) !important;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 90% 80%, rgba(52, 211, 153, 0.06) 0%, transparent 40%) !important;
        color: var(--text-main) !important;
        font-family: 'Pretendard', sans-serif;
    }
    
    [data-testid="stHeader"] { background-color: transparent !important; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; }
    .main .block-container { max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem; }

    /* =========================================
       🔥 사이드바 집중 개편: 둥근 알약(Pill) 형태 디자인 🔥
       ========================================= */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: blur(40px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(40px) saturate(150%) !important;
        border-right: 1px solid rgba(0,0,0,0.05) !important; 
    }
    
    /* 1. 기본 라디오 버튼 동그라미 완전히 삭제 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child,
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] label[data-baseweb="radio"] svg,
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label > div:first-child { 
        display: none !important; 
        opacity: 0 !important; 
        visibility: hidden !important; 
        width: 0px !important; 
        height: 0px !important; 
        margin: 0 !important; 
        padding: 0 !important; 
    }
    
    /* 2. 메뉴 컨테이너 레이아웃 - 간격 넓히기 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] { 
        gap: 12px; 
        padding: 10px 20px; 
        background: transparent !important; 
    }
    
    /* 3. 메뉴 아이템 기본 상태 (선택 안됨) */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label {
        background: transparent !important;
        border: none !important;
        border-radius: 50px !important; /* 사방을 완벽히 둥글게 */
        padding: 14px 20px !important;
        cursor: pointer; 
        width: 100%; 
        margin: 0 !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    
    /* 4. 기본 텍스트 디자인 (연한 회색) */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label p {
        font-size: 1.1em !important; 
        font-weight: 500 !important; 
        color: #64748B !important; 
        margin: 0 !important; 
        padding-left: 0 !important;
        transition: all 0.2s ease !important;
    }
    
    /* 5. Hover 효과 (마우스 올렸을 때 살짝 커지며 진해짐) */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        background: rgba(0, 0, 0, 0.03) !important; 
    }
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label:hover p { 
        color: #0F172A !important; 
        transform: scale(1.05) translateX(4px) !important; 
        font-weight: 600 !important;
    }
    
    /* 6. 🚨 Checked 상태 (레퍼런스 사진처럼 까만 배경에 흰 글씨!) 🚨 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
        background: #1E1E24 !important; /* 다크 그레이/블랙 */
        border-radius: 50px !important; /* 사방이 둥근 알약 모양 */
        border: none !important;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15) !important; /* 살짝 떠보이는 그림자 */
        padding-right: 20px !important;
        margin-right: 0 !important; 
        width: 100% !important;
    }
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) p {
        color: #FFFFFF !important; /* 완전한 흰색 글씨 */
        font-weight: 600 !important;
        transform: scale(1.05) translateX(4px) !important; /* 호버와 동일하게 텍스트 확대 유지 */
    }
    /* ========================================= */

    /* 🚨 카드 UI (완벽한 양각 Neumorphism) 🚨 */
    .glass-card {
        background: #FFFFFF !important; 
        border-top: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-left: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-bottom: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-right: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-radius: 24px !important;
        padding: 24px !important;
        box-shadow: 
            12px 12px 24px rgba(16, 185, 129, 0.15),   
            -12px -12px 24px rgba(255, 255, 255, 0.9) !important; 
        height: 100%; display: flex; flex-direction: column; justify-content: space-between;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .glass-card:hover {
        transform: translateY(-5px); 
        border-bottom: 3.5px solid rgba(16, 185, 129, 0.8) !important; 
        border-right: 3.5px solid rgba(16, 185, 129, 0.8) !important; 
        box-shadow: 16px 16px 32px rgba(16, 185, 129, 0.18), -16px -16px 32px rgba(255, 255, 255, 1) !important;
    }
    .glass-card h3 { font-family: 'Outfit', sans-serif; font-size: 1.15em !important; font-weight: 800 !important; color: var(--text-main); margin-bottom: 15px !important; letter-spacing: -0.5px; border-bottom: 2px solid rgba(16, 185, 129, 0.1); padding-bottom: 8px; }

    .glass-inset {
        background: #F8FAFC !important;
        border-top: 1px solid rgba(16, 185, 129, 0.4) !important;
        border-left: 1px solid rgba(16, 185, 129, 0.4) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 1) !important;
        border-right: 1px solid rgba(255, 255, 255, 1) !important;
        border-radius: 16px !important; padding: 18px; text-align: center; margin-bottom: 16px;
        box-shadow: inset 6px 6px 12px rgba(16, 185, 129, 0.12), inset -6px -6px 12px rgba(255, 255, 255, 1) !important;
    }
    
    h1 { font-family: 'Outfit', sans-serif; font-size: 2.6em !important; font-weight: 800 !important; letter-spacing: -1px; margin: 0 !important; color: var(--text-main) !important; }

    .crow { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 0.9em; }
    .clabel { color: var(--text-muted); font-weight: 600; }
    .cval { font-family: 'Outfit', sans-serif; font-weight: 800; color: var(--accent-mint); }

    [data-testid="stMetric"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 5px !important; }
    [data-testid="stMetricLabel"] > div > div > p { font-size: 0.85em !important; font-weight: 600; color: var(--text-muted) !important; }
    [data-testid="stMetricValue"] > div { font-family: 'Outfit', sans-serif; font-size: 1.5em !important; font-weight: 800; color: var(--text-main) !important; }
    div[data-testid="stMetricDelta"] > div { font-size: 0.85em !important; font-weight: 700; }
    
    .mint-table { width: 100%; border-collapse: separate; border-spacing: 0 8px; font-family: 'Pretendard', sans-serif; }
    .mint-table th { padding: 10px 14px; font-weight: 700; color: #64748B; text-align: right; border-bottom: none; font-size: 0.9em; }
    .mint-table td { padding: 14px; background: rgba(255, 255, 255, 0.8); color: #0F172A; text-align: right; border-top: 1px solid rgba(16, 185, 129, 0.1); border-bottom: 1px solid rgba(16, 185, 129, 0.1); }
    .mint-table tr { transition: transform 0.2s; }
    .mint-table tr:hover { transform: scale(1.01); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.05); }
    .mint-table td:first-child { border-left: 1px solid rgba(16, 185, 129, 0.1); border-top-left-radius: 12px; border-bottom-left-radius: 12px; text-align: left; }
    .mint-table td:last-child { border-right: 1px solid rgba(16, 185, 129, 0.1); border-top-right-radius: 12px; border-bottom-right-radius: 12px; text-align: center; }

    [data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div { background: rgba(255,255,255,0.8) !important; border: 1px solid var(--border-glass) !important; border-radius: 12px !important; color: var(--text-main) !important; }
</style>""", unsafe_allow_html=True)
