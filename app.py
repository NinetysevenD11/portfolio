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

# --- 🎨 테마 커스텀 시스템 추가 ---
if 'main_color' not in st.session_state:
    st.session_state.main_color = '#10B981' # 기본값: 민트
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
    
    bt_df = bt_df.dropna()
    if bt_df.empty: return bt_df
    
    bt_df['Target'] = bt_df.apply(get_target_v45, axis=1)
    bt_df['Regime'] = apply_asymmetric_delay(bt_df['Target'])
    
    bt_df = bt_df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]
    return bt_df

REALTIME_TICKERS = ['QQQ','TQQQ','SMH','^VIX','HYG','IEF','UUP','GLD','SPY','SOXL','USD','QLD','SSO','USDKRW=X']

# 🚨 [수정사항] KST(한국 시간) 기반으로 타임스탬프 강제 보정 🚨
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

last_row = df.iloc[-1].copy()

rt_ok    = len(rt_injected) >= 3
rt_label = f"🟢 LIVE ({len(rt_injected)})" if rt_ok else "🟡 DELAYED"

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

# 차트 전역 색상
b_color = 'rgba(0,0,0,0)'
t_color = '#1E293B'
line_c = main_color
dash_c = '#94A3B8'
rsi_low_c = main_color
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
regime_info  = {1:("R1 BULL","풀 가동"),2:("R2 CORR","방어 진입"), 3:("R3 BEAR","대피"),4:("R4 PANIC","최대 방어")}

# ==========================================
# 2. CSS (사이드바 완벽 통일 + 버튼 디자인)
# ==========================================
css_block = f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;800&display=swap');
    
    :root {{
        --bg-main: #F8FAFC; 
        --text-main: #0F172A; 
        --text-muted: #64748B; 
        --accent-mint: #10B981; 
    }}

    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: var(--bg-main) !important;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 90% 80%, rgba(52, 211, 153, 0.06) 0%, transparent 40%) !important;
        color: var(--text-main) !important;
        font-family: 'Pretendard', sans-serif;
    }}
    
    [data-testid="stHeader"] {{ background-color: transparent !important; }}
    #MainMenu {{ visibility: hidden; }} footer {{ visibility: hidden; }}
    .main .block-container {{ max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem; }}

    [data-testid="stSidebar"] {{
        background: #f0f0e8 !important; 
        border-right: 2.5px solid #1a1a1a !important; 
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{ gap: 0px !important; padding: 0 15px !important; background: transparent !important; }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] {{
        display: flex !important; align-items: center !important; padding: 8px 12px !important; margin-bottom: 6px !important;
        border-radius: 10px !important; border: 2.5px solid transparent !important; background: rgba(0,0,0,0.04) !important;
        cursor: pointer !important; width: 100% !important; transition: all 0.2s !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] p {{
        color: #1a1a1a !important; font-weight: 800 !important; font-size: 0.95rem !important; margin: 0 !important; transform: none !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:hover,
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {{
        border: 2.5px solid #1a1a1a !important; background-color: #ffffff !important;
        transform: translateX(3px) !important; box-shadow: 2px 2px 0px #1a1a1a !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p {{ color: var(--accent-mint) !important; }}

    .sidebar-link {{ 
        display: flex; align-items: center; padding: 8px 12px; margin-bottom: 6px; 
        border-radius: 10px; border: 2.5px solid transparent; text-decoration: none !important; 
        color: #1a1a1a !important; font-weight: 800; font-size: 0.95rem; 
        transition: all 0.2s; background: rgba(0,0,0,0.04); 
    }}
    .sidebar-link:hover {{ 
        border: 2.5px solid #1a1a1a; background-color: #ffffff; 
        transform: translateX(3px); box-shadow: 2px 2px 0px #1a1a1a; 
    }}

    .radar-link {{ text-decoration: none !important; display: block; }}
    .radar-link-title {{ font-size: 0.85em; font-weight: 700; color: #64748B; transition: color 0.2s; }}
    .radar-link:hover .radar-link-title {{ color: var(--accent-mint) !important; }}

    .glass-card {{
        background: #FFFFFF !important; 
        border-top: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-left: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-bottom: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-right: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-radius: 24px !important;
        padding: 24px !important;
        box-shadow: 12px 12px 24px rgba(16, 185, 129, 0.15), -12px -12px 24px rgba(255, 255, 255, 0.9) !important; 
        height: 100%; display: flex; flex-direction: column; justify-content: space-between;
        transition: all 0.3s ease;
    }}
    .glass-card:hover {{
        transform: translateY(-5px); 
        border-bottom: 3.5px solid rgba(16, 185, 129, 0.8) !important; 
        border-right: 3.5px solid rgba(16, 185, 129, 0.8) !important; 
        box-shadow: 16px 16px 32px rgba(16, 185, 129, 0.18), -16px -16px 32px rgba(255, 255, 255, 1) !important;
    }}
    .glass-card h3 {{ font-family: 'Outfit', sans-serif; font-size: 1.15em !important; font-weight: 800 !important; color: var(--text-main); margin-bottom: 15px !important; letter-spacing: -0.5px; border-bottom: 2px solid rgba(16, 185, 129, 0.1); padding-bottom: 8px; }}
    
    .glass-inset {{
        background: #F8FAFC !important; 
        border-top: 1px solid rgba(16, 185, 129, 0.4) !important; border-left: 1px solid rgba(16, 185, 129, 0.4) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 1) !important; border-right: 1px solid rgba(255, 255, 255, 1) !important;
        border-radius: 16px !important; padding: 20px 10px 18px !important; text-align: center; margin-bottom: 16px;
        box-shadow: inset 6px 6px 12px rgba(16, 185, 129, 0.12), inset -6px -6px 12px rgba(255, 255, 255, 1) !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background: #FFFFFF !important; 
        border-top: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-left: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-bottom: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-right: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-radius: 24px !important;
        padding: 24px !important;
        box-shadow: 12px 12px 24px rgba(16, 185, 129, 0.15), -12px -12px 24px rgba(255, 255, 255, 0.9) !important; 
        transition: all 0.3s ease;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{
        transform: translateY(-5px); 
        border-bottom: 3.5px solid rgba(16, 185, 129, 0.8) !important; 
        border-right: 3.5px solid rgba(16, 185, 129, 0.8) !important; 
        box-shadow: 16px 16px 32px rgba(16, 185, 129, 0.18), -16px -16px 32px rgba(255, 255, 255, 1) !important;
    }}

    [data-testid="stMetric"] {{ 
        background: #FFFFFF !important; 
        border-top: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-left: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-bottom: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-right: 2.5px solid rgba(16, 185, 129, 0.6) !important;
        border-radius: 16px !important; 
        padding: 16px 20px !important; 
        box-shadow: 6px 6px 12px rgba(16, 185, 129, 0.1), -6px -6px 12px rgba(255, 255, 255, 0.9) !important;
        margin-bottom: 10px;
    }}
    [data-testid="stMetricLabel"] > div > div > p {{ font-size: 0.9em !important; font-weight: 700; color: var(--text-muted) !important; white-space: normal !important; }}
    [data-testid="stMetricValue"] > div {{ font-family: 'Outfit', sans-serif; font-size: 1.6em !important; font-weight: 800; color: var(--text-main) !important; }}
    div[data-testid="stMetricDelta"] > div {{ font-size: 0.9em !important; font-weight: 700; }}
    
    /* 🚨 새고로침 버튼 스타일 🚨 */
    [data-testid="stButton"] > button {{
        background-color: var(--bg-main) !important;
        border: 2px solid rgba(16, 185, 129, 0.8) !important;
        color: var(--text-main) !important;
        border-radius: 12px !important;
        padding: 4px 10px !important;
        font-weight: 800 !important;
        font-size: 0.85em !important;
        transition: all 0.2s ease !important;
    }}
    [data-testid="stButton"] > button:hover {{
        background-color: rgba(16, 185, 129, 0.1) !important;
        color: var(--accent-mint) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2) !important;
    }}

    h1 {{ font-family: 'Outfit', sans-serif; font-size: 2.6em !important; font-weight: 800 !important; letter-spacing: -1px; margin: 0 !important; color: var(--text-main) !important; }}
    .crow {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 0.9em; }}
    .clabel {{ color: var(--text-muted); font-weight: 600; }}
    .cval {{ font-family: 'Outfit', sans-serif; font-weight: 800; color: var(--accent-mint); }}
    
    .mint-table {{ width: 100%; border-collapse: separate; border-spacing: 0 8px; font-family: 'Pretendard', sans-serif; }}
    .mint-table th {{ padding: 10px 14px; font-weight: 700; color: #64748B; text-align: right; border-bottom: none; font-size: 0.9em; }}
    .mint-table td {{ padding: 14px; background: rgba(255, 255, 255, 0.8); color: #0F172A; text-align: right; border-top: 1px solid rgba(16, 185, 129, 0.1); border-bottom: 1px solid rgba(16, 185, 129, 0.1); }}
    .mint-table tr {{ transition: transform 0.2s; }}
    .mint-table tr:hover {{ transform: scale(1.01); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.05); }}
    .mint-table td:first-child {{ border-left: 1px solid rgba(16, 185, 129, 0.1); border-top-left-radius: 12px; border-bottom-left-radius: 12px; text-align: left; }}
    .mint-table td:last-child {{ border-right: 1px solid rgba(16, 185, 129, 0.1); border-top-right-radius: 12px; border-bottom-right-radius: 12px; text-align: center; }}

    [data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div {{ background: rgba(255,255,255,0.8) !important; border: 1px solid rgba(16,185,129,0.3) !important; border-radius: 12px !important; color: var(--text-main) !important; }}
</style>"""
st.markdown(apply_theme(css_block), unsafe_allow_html=True)

# ==========================================
# 3. 사이드바 UI
# ==========================================
sidebar_top = st.sidebar.container()
sidebar_top.markdown(apply_theme(f"""
<div style="padding: 10px 15px;">
    <div style="font-family: 'Outfit'; font-size: 1.8em; font-weight: 800; color: #1a1a1a; letter-spacing: -0.5px;">AMLS <span style="color:#10B981;">V4.5</span></div>
    <div style="font-family: 'Outfit'; font-size: 0.85em; font-weight: 800; color: #444444; margin-bottom: 10px;">QUANTITATIVE ENGINE</div>
    <div style="font-size: 0.75em; color: #1a1a1a; font-weight: 800; padding: 4px 10px; background: rgba(0,0,0,0.05); border-radius: 10px; display: inline-block; border: 2px solid #1a1a1a;">
        {rt_label}
    </div>
</div>"""), unsafe_allow_html=True)

st.sidebar.markdown("<div style='font-size:1.2rem; font-weight:900; color:#1a1a1a; margin-bottom:5px; padding: 0 15px;'>🧭 네비게이션</div>", unsafe_allow_html=True)
page = st.sidebar.radio("MENU",
    ["📊 Dashboard", "💼 Portfolio", "🍫 8-Pack Radar", "📈 Backtest Lab", "📰 Macro News"],
    label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-size:1.2rem; font-weight:900; color:#1a1a1a; margin-bottom:5px; padding: 0 15px;'>🎨 테마 색상 설정</div>", unsafe_allow_html=True)
col1, col2, col3 = st.sidebar.columns([0.1, 1, 0.1])
with col2:
    new_color = st.color_picker("메인 컬러를 지정하세요", st.session_state.main_color, label_visibility="collapsed")
    if new_color != st.session_state.main_color:
        st.session_state.main_color = new_color
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-size:1.2rem; font-weight:900; color:#1a1a1a; margin-bottom:10px; padding: 0 15px;'>⭐ 즐겨찾기</div>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="display:flex; flex-direction:column; gap:2px; padding: 0 15px;">
    <a href="https://www.youtube.com/@JB_Insight" target="_blank" class="sidebar-link"><span>📊</span> JB 인사이트</a>
    <a href="https://www.youtube.com/@odokgod" target="_blank" class="sidebar-link"><span>📻</span> 오독</a>
    <a href="https://www.youtube.com/@TQQQCRAZY" target="_blank" class="sidebar-link"><span>🔥</span> TQQQ 미친놈</a>
    <a href="https://www.youtube.com/@developmong" target="_blank" class="sidebar-link"><span>🐒</span> 디벨롭몽</a>
    <a href="https://kr.investing.com/" target="_blank" class="sidebar-link"><span>🌍</span> 인베스팅닷컴</a>
    <a href="https://kr.tradingview.com/" target="_blank" class="sidebar-link"><span>📉</span> 트레이딩뷰</a>
    <a href="https://claude.ai/" target="_blank" class="sidebar-link"><span>🧠</span> 클로드</a>
    <a href="https://gemini.google.com/" target="_blank" class="sidebar-link"><span>✨</span> 제미나이</a>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 🚨 [핵심 변경] 수동 새로고침 UI가 추가된 메인 타이틀 영역 🚨
c_title, c_info = st.columns([1.5, 1])
with c_title:
    st.markdown(apply_theme(f"""
    <div>
        <h1 style="margin:0; font-family:'Outfit'; font-size: 2.6em; font-weight: 800; letter-spacing: -1px; color: var(--text-main);">AMLS V4.5 ENGINE</h1>
        <p style="font-family:'Outfit'; font-size:1.05em; margin:4px 0 0 0; font-weight:700; color:#10B981; letter-spacing:0.5px;">THE WALL STREET QUANTITATIVE STRATEGY</p>
    </div>
    """), unsafe_allow_html=True)
    
with c_info:
    st.markdown(f"<div style='text-align:right; font-family:\"Outfit\"; font-size:1.1em; font-weight:800; color:#0F172A; margin-bottom:10px;'>CUSTOM THEME EDITION</div>", unsafe_allow_html=True)
    i1, i2 = st.columns([1.5, 1])
    with i1:
        st.markdown(f"<div style='text-align:right; font-size:0.8rem; font-weight:600; color:#64748B; margin-top:8px;'>⏱️ {last_update_time}</div>", unsafe_allow_html=True)
    with i2:
        if st.button("🔄 즉시 동기화", use_container_width=True):
            fetch_realtime_prices.clear()
            load_data.clear()
            st.rerun()

st.markdown(apply_theme(f'<div style="border-bottom: 2px solid rgba({r_c},{g_c},{b_c},0.1); padding-top: 10px; margin-bottom: 25px;"></div>'), unsafe_allow_html=True)


# ==========================================
# 5. 페이지 라우팅
# ==========================================
if page == "📊 Dashboard":
    
    def _lg_row(label, val, passed):
        icon = "🟢" if passed else "🔴"
        color = main_color if passed else "#EF4444"
        return f'<div class="crow"><span class="clabel">{label}</span><span class="cval" style="color:{color};">{val} {icon}</span></div>'

    soxl_title  = "SOXL 진입 승인" if smh_cond else "USD 방어 진입"
    soxl_strat  = "3x Leverage" if smh_cond else "2x Defense"
    soxl_color  = main_color if smh_cond else "#0F172A"
    
    weight_rows = "".join([f'<div class="crow"><span class="clabel">{k}</span><span class="cval" style="color:#10B981;">{v*100:.0f}%</span></div>'
                            for k,v in target_weights.items() if v > 0])

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.markdown(apply_theme(f"""<div class="glass-card">
            <h3>MARKET REGIME</h3>
            <div class="glass-inset">
                <div style="color:#10B981; font-family:'Outfit'; font-size:2em; font-weight:800;">{regime_info[curr_regime][0]}</div>
                <div style="font-weight:600; color:#64748B; font-size:0.95em; margin-top:4px;">{regime_info[curr_regime][1]}</div>
            </div>
            {_lg_row('VIX < 40', f'{vix_close:.2f}', vix_close<=40)}
            {_lg_row('QQQ > 200MA', f'${qqq_close:.0f}', qqq_close>=qqq_ma200)}
            {_lg_row('50MA ≥ 200MA', f'${qqq_ma50:.0f}', qqq_ma50>=qqq_ma200)}
            <div style="margin-top:auto; padding:12px; font-size:0.85em; text-align:center; border-radius:8px; background:rgba(16,185,129,0.1); color:#047857; font-weight:700;">{regime_committee_msg}</div>
        </div>"""), unsafe_allow_html=True)
    with c2:
        st.markdown(apply_theme(f"""<div class="glass-card">
            <h3>SEMI-CONDUCTOR (SOXL)</h3>
            <div class="glass-inset">
                <div style="color:{soxl_color}; font-family:'Outfit'; font-size:2em; font-weight:800;">{soxl_title}</div>
                <div style="font-weight:600; color:#64748B; font-size:0.95em; margin-top:4px;">{soxl_strat}</div>
            </div>
            {_lg_row('SMH > 50MA', f'${smh_close:.1f}', smh_c1)}
            {_lg_row('Mom (1M>10%)', f'{smh_1m*100:.1f}%', smh_c2)}
            {_lg_row('RSI > 50', f'{smh_rsi:.1f}', smh_c3)}
            <div style="margin-top:auto; padding:12px; font-size:0.85em; text-align:center; color:#64748B; font-weight:600; border-top:1px dashed rgba(16,185,129,0.3);">※ 3 filters required for SOXL</div>
        </div>"""), unsafe_allow_html=True)
    with c3:
        st.markdown(apply_theme(f"""<div class="glass-card">
            <h3>TARGET WEIGHTS</h3>
            <div style="display:flex; justify-content:space-between; font-size:0.8em; font-family:'Outfit'; font-weight:700; color:#94A3B8; border-bottom:2px solid rgba(16,185,129,0.15); padding-bottom:8px; margin-bottom:5px;"><span>ASSET</span><span>WEIGHT</span></div>
            {weight_rows}
        </div>"""), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("QQQ vs 200MA", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200MA", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (20D MA)", f"{last_row['VIX_MA20']:.2f}", f"NOW: {last_row['^VIX']:.2f}")
    m4.metric("SMH 1M", f"{last_row['SMH_1M_Ret']*100:+.1f}%", f"vs 50MA: {(last_row['SMH']/last_row['SMH_MA50']-1)*100:+.1f}%")
    m5.metric("SMH RSI", f"{last_row['SMH_RSI']:.1f}", "Target: > 50")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    df_recent = df.iloc[-500:]

    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color=line_c, width=2.5)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_qqq.update_layout(title=dict(text="QQQ vs 200MA", font=dict(family='Outfit', size=16, color="#0F172A")), height=350, **chart_layout)
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color=line_c, width=2.5)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_tqqq.update_layout(title=dict(text="TQQQ vs 200MA", font=dict(family='Outfit', size=16, color="#0F172A")), height=350, **chart_layout)

    with chart_col1:
        with st.container(border=True):
            st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2:
        with st.container(border=True):
            st.plotly_chart(fig_tqqq, use_container_width=True)

elif page == "💼 Portfolio":
    st.markdown("<h2 style='font-family:Outfit; font-size:1.8em; color:#0F172A;'>💼 Portfolio & Rebalancing</h2>", unsafe_allow_html=True)
    
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
            use_container_width=True
        )
    
    for _, row in edited_df.iterrows():
        asset = row["Asset"]
        st.session_state.portfolio[asset] = {
            'shares': float(row["Shares"]),
            'avg_price': float(row["Avg Price($)"]),
            'fx': float(row["FX Rate(₩)"])
        }
    save_portfolio_to_disk()
    
    st.markdown("<br><h3 style='font-family:Outfit; color:#0F172A;'>⚖️ Action Plan</h3>", unsafe_allow_html=True)
    
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
        c_green, c_red = main_color, "#EF4444"
        pie_layout = dict(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Pretendard", color="#0F172A", size=12))
        
        diff_vals = {a: (total_val_usd * target_weights.get(a, 0.0)) - curr_vals[a] for a in ASSET_LIST}
        chart_c1, chart_c2, chart_c3 = st.columns([1, 1, 1.5])
        
        labels_cur = [a for a in ASSET_LIST if curr_vals[a] > 0]
        vals_cur = [curr_vals[a] for a in labels_cur]
        if sum(vals_cur) > 0:
            fig_cur = go.Figure(data=[go.Pie(labels=labels_cur, values=vals_cur, hole=.4, textinfo='label+percent', marker=dict(colors=[line_c, dash_c, '#34D399', '#6EE7B7']))])
            fig_cur.update_layout(title=dict(text="Current", font=dict(family="Outfit", size=16, color="#0F172A")), **pie_layout)
            with chart_c1:
                with st.container(border=True):
                    st.plotly_chart(fig_cur, use_container_width=True)
        
        labels_tgt = [a for a in ASSET_LIST if target_weights.get(a, 0) > 0]
        vals_tgt = [target_weights.get(a, 0) for a in labels_tgt]
        fig_tgt = go.Figure(data=[go.Pie(labels=labels_tgt, values=vals_tgt, hole=.4, textinfo='label+percent', marker=dict(colors=[line_c, dash_c, '#34D399', '#6EE7B7']))])
        fig_tgt.update_layout(title=dict(text=f"Target (R{curr_regime})", font=dict(family="Outfit", size=16, color="#0F172A")), **pie_layout)
        with chart_c2:
            with st.container(border=True):
                st.plotly_chart(fig_tgt, use_container_width=True)
        
        diff_labels = [a for a in ASSET_LIST if abs(diff_vals[a]) >= 1.0]
        diff_values = [diff_vals[a] for a in diff_labels]
        diff_colors = [c_green if v > 0 else c_red for v in diff_values]
        if diff_labels:
            fig_bar = go.Figure(data=[go.Bar(x=diff_labels, y=diff_values, marker_color=diff_colors, text=[f"${v:,.0f}" for v in diff_values], textposition='auto')])
            fig_bar.update_layout(title=dict(text="Rebalancing Amounts ($)", font=dict(family="Outfit", size=16, color="#0F172A")), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#0F172A"), margin=dict(t=40, b=20, l=20, r=20))
            with chart_c3:
                with st.container(border=True):
                    st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown(f"<h4 style='color:#0F172A; margin-top: 20px; font-family:Outfit;'>📝 Quick Orders</h4>", unsafe_allow_html=True)
        summary_html = f"<div class='glass-card' style='height:auto !important; flex-direction:row; gap: 20px; padding: 20px !important;'>"
        
        sell_text = "<div style='flex: 1;'><strong style='color:#EF4444; font-family:Outfit; font-size:1.2em;'>🔴 SELL</strong><br><br>"
        buy_text = f"<div style='flex: 1;'><strong style='color:#10B981; font-family:Outfit; font-size:1.2em;'>🟢 BUY</strong><br><br>"
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff < -cur_p * 0.05:
                sell_text += f"<div style='margin-bottom: 8px; font-size: 0.95em;'><span style='color:#10B981; font-weight:800; font-family:Outfit;'>{asset}</span> : <span style='color:#EF4444; font-weight:700;'>{abs(diff)/cur_p:,.2f}주</span> 매도</div>"
            elif asset == 'CASH' and diff < -1.0:
                sell_text += f"<div style='margin-bottom: 8px; font-size: 0.95em;'><span style='color:#10B981; font-weight:800; font-family:Outfit;'>CASH</span> : <span style='color:#EF4444; font-weight:700;'>${abs(diff):,.0f}</span> 사용</div>"
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff > cur_p * 0.05:
                buy_text += f"<div style='margin-bottom: 8px; font-size: 0.95em;'><span style='color:#10B981; font-weight:800; font-family:Outfit;'>{asset}</span> : <span style='color:#10B981; font-weight:700;'>{diff/cur_p:,.2f}주</span> 매수</div>"
            elif asset == 'CASH' and diff > 1.0:
                buy_text += f"<div style='margin-bottom: 8px; font-size: 0.95em;'><span style='color:#10B981; font-weight:800; font-family:Outfit;'>CASH</span> : <span style='color:#10B981; font-weight:700;'>${diff:,.0f}</span> 확보</div>"
                
        summary_html += sell_text + "</div>" + buy_text + "</div></div>"
        st.markdown(apply_theme(summary_html), unsafe_allow_html=True)

        rebal_html = f"""<div style="overflow-x: auto; padding: 10px 0;">
<table class="mint-table">
<thead><tr>
<th>Asset</th><th>Avg &rarr; Cur</th><th>Ret (KRW)</th><th>Value ($)</th><th>Target %</th><th>Target ($)</th><th>Diff ($)</th><th style="text-align:center;">Action</th>
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
                avg_p_str = "-"
                ret_usd, ret_krw = 0.0, ((cur_fx / pur_fx) - 1) * 100 if pur_fx > 0 else 0.0
            else:
                avg_p_str = f"${avg_p:,.2f} &rarr; ${cur_p:,.2f}"
                ret_usd = (cur_p / avg_p - 1) * 100 if avg_p > 0 else 0.0
                ret_krw = ((cur_p * cur_fx) / (avg_p * pur_fx) - 1) * 100 if (avg_p > 0 and pur_fx > 0) else 0.0
                
            ret_usd_color = c_green if ret_usd >= 0 else c_red
            ret_usd_str = f"{ret_usd:+.2f}%" if asset != 'CASH' else "-"
            
            if abs(diff) < cur_p * 0.05 and asset != 'CASH': action = "<span style='color:#94A3B8; font-weight:700;'>HOLD</span>"; diff_str = "-"
            elif abs(diff) < 1.0 and asset == 'CASH': action = "<span style='color:#94A3B8; font-weight:700;'>HOLD</span>"; diff_str = "-"
            elif diff > 0: 
                action = f"<span style='color:#10B981; font-weight:700; background:rgba(16,185,129,0.1); padding:4px 10px; border-radius:6px;'>BUY</span>"
                diff_str = f"<span style='color:#10B981; font-weight:700;'>+${diff:,.0f}</span>"
            else: 
                action = f"<span style='color:#EF4444; font-weight:700; background:rgba(239,68,68,0.1); padding:4px 10px; border-radius:6px;'>SELL</span>"
                diff_str = f"<span style='color:#EF4444; font-weight:700;'>-${abs(diff):,.0f}</span>"
                
            if tgt_w > 0 or curr_v > 0 or shares > 0:
                rebal_html += f"""<tr>
<td style="font-weight:800; font-family:'Outfit'; color:#10B981; font-size:1.1em;">{asset}</td>
<td style="color:#64748B;">{avg_p_str}</td>
<td><span style="color:{ret_usd_color}; font-weight:700;">{ret_usd_str}</span></td>
<td style="font-weight:600;">{curr_v:,.0f}</td>
<td style="color:#10B981; font-weight:700;">{tgt_w*100:.0f}%</td>
<td style="font-weight:600;">{tgt_v:,.0f}</td>
<td>{diff_str}</td><td style="text-align:center;">{action}</td></tr>"""
        rebal_html += "</tbody></table></div>"
        
        with st.container(border=True):
            st.markdown(apply_theme(rebal_html), unsafe_allow_html=True)

elif page == "🍫 8-Pack Radar":

    df_view   = df.iloc[-120:]
    qqq_rsi   = last_row['QQQ_RSI']
    qqq_dd    = last_row['QQQ_DD']
    vix_score = max(0, min(100, 100-(last_row['^VIX']-12)/28*100))
    dd_score  = max(0, min(100, (qqq_dd+0.20)/0.20*100))
    rsi_score = max(0, min(100, qqq_rsi))
    fg_score  = (vix_score+dd_score+rsi_score)/3
    
    sec_names = {'XLK':'TECH','XLV':'HEALTH','XLF':'FIN','XLY':'CONS','XLC':'COMM',
                 'XLI':'IND','XLP':'STAPLE','XLE':'ENGY','XLU':'UTIL','XLRE':'REAL','XLB':'MAT'}
    sec_data  = [{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
    sec_df    = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
    top_sec, bot_sec = sec_df.iloc[-1]['섹터'], sec_df.iloc[0]['섹터']

    # 🚨 [새로운 기능] 레이더 종합 분석 판단 로직 🚨
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
        radar_status = "🔴 극단적 위험 구간 (Risk-Off)"
        radar_msg = "복수의 매크로 지표에서 강력한 하락 경고가 발생했습니다. 레버리지 비중을 축소하고 현금 및 달러/금 비중을 늘려 방어적으로 대응할 시기입니다."
        radar_color = "#EF4444"
        bg_color = "rgba(239,68,68,0.1)"
    elif warn_cnt >= 3 or risk_cnt == 1:
        radar_status = "🟡 변동성 주의 (Warning)"
        radar_msg = "시장의 균열 조짐이 감지되었습니다. 신규 매수를 보류하고 추세를 관망하며 포트폴리오 밸런스를 점검하십시오."
        radar_color = "#F59E0B"
        bg_color = "rgba(245,158,11,0.1)"
    else:
        radar_status = "🟢 안정적 순항 (Safe)"
        radar_msg = "매크로 지표들이 안정적인 추세를 지지하고 있습니다. 시스템 알고리즘이 제시하는 비중에 맞춰 추세 추종 전략을 전개하십시오."
        radar_color = main_color
        bg_color = f"rgba({r_c},{g_c},{b_c},0.1)"

    st.markdown('<h2 style="font-family:Outfit; font-size:1.8em; color:#0F172A; margin-bottom:15px;">🍫 8-Pack Radar</h2>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="glass-card" style="height:auto !important; margin-bottom: 25px; padding: 25px !important; border-left: 5px solid {radar_color} !important; background: {bg_color} !important;">
      <h3 style="color:{radar_color}; margin-bottom: 8px; font-size: 1.4em;">{radar_status}</h3>
      <div style="color:#0F172A; font-weight:700; font-size:1.1em; margin-bottom: 8px;">현재 상태: 위험 요소 {risk_cnt}개 / 경고 요소 {warn_cnt}개 / 안정 요소 {safe_cnt}개</div>
      <p style="color:#334155; font-weight:600; font-size:1.05em; margin:0; line-height: 1.5;">{radar_msg}</p>
    </div>
    """, unsafe_allow_html=True)

    def _badge(label, color, icon):
        p = {'green':(f'rgba({r_c},{g_c},{b_c},0.1)', main_color), 'orange':('rgba(245,158,11,0.1)','#F59E0B'),
             'red':('rgba(239,68,68,0.1)','#EF4444'), 'blue':('rgba(59,130,246,0.1)','#3B82F6')}
        bg,fg = p[color]
        return f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; border-radius:8px; padding:4px 10px; font-size:0.85em; font-weight:700; margin-left:8px;">{icon} {label}</span>'

    b1 = _badge("BUY","green","🔥") if qqq_rsi<40 else (_badge("OVER","red","⚠️") if qqq_rsi>70 else _badge("ACC","blue","🟢"))
    b2 = _badge("BEAR(-20%)","red","🚨") if qqq_dd<-0.20 else (_badge("CORR(-10%)","orange","⚠️") if qqq_dd<-0.10 else _badge("SAFE","green","✅"))
    b3 = _badge("FEAR","green","🔥") if fg_score<30 else (_badge("GREED","red","⚠️") if fg_score>70 else _badge("NEUTRAL","blue","🟢"))
    b4 = f'<span style="background:rgba({r_c},{g_c},{b_c},0.1); color:{main_color}; border:1px solid {main_color}; border-radius:8px; padding:4px 10px; font-size:0.85em; font-weight:700; margin-left:8px;">🏆 {top_sec} / 📉 {bot_sec}</span>'
    b5 = _badge("RISK OFF","red","🚨") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _badge("RISK ON","green","✅")
    b6 = _badge("NARROW","orange","⚠️") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0) else _badge("BROAD","green","✅")
    b7 = _badge("GOLD","orange","⚠️") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _badge("EQUITY","green","✅")
    b8 = _badge("STRONG USD","red","🚨") if last_row['UUP']>last_row['UUP_MA50'] else _badge("WEAK USD","green","✅")

    gauge_steps = [{'range':[0,25],'color':"rgba(239,68,68,0.5)"},{'range':[25,45],'color':"rgba(245,158,11,0.4)"},
                   {'range':[45,55],'color':"rgba(255,255,255,0.8)"},{'range':[55,75],'color':f"rgba({r_c},{g_c},{b_c},0.4)"},
                   {'range':[75,100],'color':f"rgba({r_c},{g_c},{b_c},0.6)"}]

    def r_head(title, badge, url, desc):
        return f'<a href="{url}" target="_blank" class="radar-link"><div class="radar-link-title" style="margin-bottom:4px;">{title} 🔗{badge}</div></a><div style="font-size:0.78em; color:var(--text-muted); margin-bottom:12px; line-height:1.3; letter-spacing:-0.3px;">{desc}</div>'

    u1 = "https://kr.tradingview.com/chart/?symbol=NASDAQ:QQQ"
    u2 = "https://kr.tradingview.com/chart/?symbol=NASDAQ:QQQ"
    u3 = "https://edition.cnn.com/markets/fear-and-greed"
    u4 = "https://finviz.com/map.ashx?t=sec"
    u5 = "https://fred.stlouisfed.org/series/BAMLH0A0HYM2"
    u6 = "https://kr.tradingview.com/chart/?symbol=NASDAQ:QQQE"
    u7 = "https://kr.tradingview.com/chart/?symbol=AMEX:GLD"
    u8 = "https://kr.tradingview.com/chart/?symbol=AMEX:UUP"

    row1 = st.columns(4)
    with row1[0]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("1. DCA (RSI)", b1, u1, "QQQ 단기 과열/침체. 30 이하 매수, 70 이상 분할 매도.")), unsafe_allow_html=True)
            fig1=go.Figure(); fig1.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_RSI'],line=dict(color=line_c,width=2.5)))
            fig1.add_hline(y=70,line_dash='dash',line_color=dash_c); fig1.add_hline(y=30,line_dash='dash',line_color=rsi_low_c)
            fig1.update_layout(**radar_layout,yaxis=dict(range=[10,90]),showlegend=False)
            st.plotly_chart(fig1,use_container_width=True)
    with row1[1]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("2. Drawdown", b2, u2, "고점 대비 하락률. -10%는 1차 지지선, -20% 약세장 의미.")), unsafe_allow_html=True)
            fig2=go.Figure(); fig2.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_DD'],fill='tozeroy',line=dict(color=dash_c,width=2.5)))
            fig2.update_layout(**radar_layout,yaxis=dict(tickformat='.0%'),showlegend=False)
            st.plotly_chart(fig2,use_container_width=True)
    with row1[2]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("3. Fear & Greed", b3, u3, "시장 심리 종합. 극단적 공포는 종종 훌륭한 매수 기회.")), unsafe_allow_html=True)
            fig3=go.Figure(go.Indicator(mode="gauge+number",value=fg_score,domain={'x':[0,1],'y':[0,1]},
                gauge={'axis':{'range':[0,100]},'bar':{'color':line_c},'steps':gauge_steps}))
            fig3.update_layout(height=200,margin=dict(l=15,r=15,t=10,b=10),paper_bgcolor=b_color,font=dict(family="Pretendard",color=t_color))
            st.plotly_chart(fig3,use_container_width=True)
    with row1[3]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("4. Sector (1M)", b4, u4, "자금 유입 주도 섹터 및 소외 섹터를 통한 흐름 파악.")), unsafe_allow_html=True)
            fig4=go.Figure(go.Bar(x=sec_df['수익률'],y=sec_df['섹터'],orientation='h', marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']]))
            fig4.update_layout(**radar_layout,showlegend=False)
            st.plotly_chart(fig4,use_container_width=True)

    row2 = st.columns(4)
    with row2[0]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("5. Credit Spread", b5, u5, "하이일드/국채 비율. 하락 시 스마트머니 자금 이탈 암시.")), unsafe_allow_html=True)
            fig5=go.Figure(); fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_Ratio'],line=dict(color=line_c,width=2.5)))
            fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_MA50'],line=dict(color=dash_c,dash='dot')))
            fig5.update_layout(**radar_layout,showlegend=False)
            st.plotly_chart(fig5,use_container_width=True)
    with row2[1]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("6. Market Breadth", b6, u6, "가중/동일가중 비교. 소수 대형주만의 가짜 반등 판별.")), unsafe_allow_html=True)
            fig6=go.Figure(); fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_20d_Ret'],name='QQQ',line=dict(color=line_c,width=2.5)))
            fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQE_20d_Ret'],name='QQQE',line=dict(color=dash_c,dash='dot')))
            fig6.update_layout(**radar_layout,showlegend=False,yaxis=dict(tickformat='.0%'))
            st.plotly_chart(fig6,use_container_width=True)
    with row2[2]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("7. Gold / Equity", b7, u7, "금/주식 상대 강도. 상승 시 안전 자산 선호도 증가.")), unsafe_allow_html=True)
            fig7=go.Figure(); fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_Ratio'],line=dict(color=line_c,width=2.5)))
            fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_MA50'],line=dict(color=dash_c,dash='dot')))
            fig7.update_layout(**radar_layout,showlegend=False)
            st.plotly_chart(fig7,use_container_width=True)
    with row2[3]:
        with st.container(border=True):
            st.markdown(apply_theme(r_head("8. USD (UUP)", b8, u8, "달러 강세 지표. 상승 시 유동성 축소 및 빅테크 악재.")), unsafe_allow_html=True)
            fig8=go.Figure(); fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP'],line=dict(color=line_c,width=2.5)))
            fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP_MA50'],line=dict(color=dash_c,dash='dot')))
            fig8.update_layout(**radar_layout,showlegend=False)
            st.plotly_chart(fig8,use_container_width=True)

elif page == "📈 Backtest Lab":
    st.markdown("<h2 style='font-family:Outfit; font-size:1.8em; color:#0F172A;'>📈 Backtest Lab</h2>", unsafe_allow_html=True)

    # 🚨 추가된 기간 설정 및 월 적립금 패널 🚨
    with st.container(border=True):
        st.markdown("<div style='font-size: 0.9em; font-weight: 700; color: #64748B; margin-bottom: 12px; text-transform:uppercase;'>⚙️ 백테스트 환경 설정</div>", unsafe_allow_html=True)
        
        col_s, col_e, col_m = st.columns(3)
        with col_s:
            bt_start = st.date_input("시작일 (Start Date)", datetime(2020, 1, 1))
        with col_e:
            bt_end = st.date_input("종료일 (End Date)", datetime.today())
        with col_m:
            monthly_cont = st.number_input("월 적립금 ($)", value=2000, step=500)

    with st.spinner("시뮬레이션 가동 중..."):
        bt_df = load_custom_backtest_data(bt_start, bt_end)
        
        if bt_df.empty:
            st.error("해당 기간의 데이터가 존재하지 않거나 부족합니다. 기간을 조정해주세요.")
        else:
            daily_ret = bt_df[['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD']].pct_change().fillna(0)
            w_orig = get_weights_v45(bt_df['Regime'].iloc[0], False)
            
            val_o, val_q, val_qld, val_tqqq = 10000, 10000, 10000, 10000
            hist_o, hist_q, hist_qld, hist_tqqq = [val_o], [val_q], [val_qld], [val_tqqq]
            invested = [10000]
            curr_inv = 10000
            
            for i in range(1, len(bt_df)):
                today = bt_df.index[i]
                yesterday = bt_df.index[i-1]

                ret_o = sum(w_orig.get(t,0) * daily_ret[t].iloc[i] for t in w_orig if t in daily_ret.columns)
                val_o *= (1 + ret_o); val_q *= (1 + daily_ret['QQQ'].iloc[i])
                val_qld *= (1 + daily_ret['QLD'].iloc[i]); val_tqqq *= (1 + daily_ret['TQQQ'].iloc[i])
                
                # 월 적립금 투입 로직
                if today.month != yesterday.month:
                    val_o += monthly_cont
                    val_q += monthly_cont
                    val_qld += monthly_cont
                    val_tqqq += monthly_cont
                    curr_inv += monthly_cont

                hist_o.append(val_o); hist_q.append(val_q); hist_qld.append(val_qld); hist_tqqq.append(val_tqqq)
                invested.append(curr_inv)
                
                smh_cond_i = (bt_df['SMH'].iloc[i] > bt_df['SMH_MA50'].iloc[i]) and (bt_df['SMH_3M_Ret'].iloc[i] > 0.05) and (bt_df['SMH_RSI'].iloc[i] > 50)
                w_orig = get_weights_v45(bt_df['Regime'].iloc[i], smh_cond_i)
                
            res_df = pd.DataFrame(index=bt_df.index)
            res_df['V4.5'], res_df['QQQ'], res_df['QLD'], res_df['TQQQ'] = hist_o, hist_q, hist_qld, hist_tqqq
            res_df['Invested'] = invested
            days = (res_df.index[-1] - res_df.index[0]).days
            
            def calc_metrics(series, inv_series):
                final_val = series.iloc[-1]
                total_inv = inv_series.iloc[-1]
                ret = (final_val / total_inv) - 1
                cagr = (final_val / total_inv) ** (365.25 / days) - 1 if days > 0 else 0
                mdd = ((series / series.cummax()) - 1).min()
                return ret, cagr, mdd
                
            ret_o, cagr_o, mdd_o       = calc_metrics(res_df['V4.5'], res_df['Invested'])
            ret_q, cagr_q, mdd_q       = calc_metrics(res_df['QQQ'], res_df['Invested'])
            ret_qld, cagr_qld, mdd_qld = calc_metrics(res_df['QLD'], res_df['Invested'])
            ret_t, cagr_t, mdd_t       = calc_metrics(res_df['TQQQ'], res_df['Invested'])
            
            mc1, mc2, mc3, mc4 = st.columns(4)
            def render_metric_card(title, ret, cagr, mdd, is_main=False):
                bg = f"background: rgba({r_c}, {g_c}, {b_c}, 0.1);" if is_main else ""
                bdr = f"border: 2px solid {main_color};" if is_main else ""
                return f"""<div class="glass-card" style="{bg} {bdr} height: auto !important; padding: 20px !important;">
    <div style="font-size: 0.9em; font-weight: 700; color: #64748B; margin-bottom: 8px;">{title}</div>
    <div style="font-family: 'Outfit'; font-size: 1.8em; font-weight: 800; color: #0F172A; margin-bottom: 10px;">CAGR {cagr*100:.1f}%</div>
    <div style="font-size: 0.9em; color: #64748B; font-weight:600;">누적: <span style="color: {main_color};">{ret*100:.1f}%</span> | MDD: <span style="color: #EF4444;">{mdd*100:.1f}%</span></div></div>"""
                
            mc1.markdown(apply_theme(render_metric_card("✨ AMLS V4.5", ret_o, cagr_o, mdd_o, True)), unsafe_allow_html=True)
            mc2.markdown(apply_theme(render_metric_card("QQQ", ret_q, cagr_q, mdd_q)), unsafe_allow_html=True)
            mc3.markdown(apply_theme(render_metric_card("QLD", ret_qld, cagr_qld, mdd_qld)), unsafe_allow_html=True)
            mc4.markdown(apply_theme(render_metric_card("TQQQ", ret_t, cagr_t, mdd_t)), unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QQQ'], name='QQQ', line=dict(color='#94A3B8', width=1.5, dash='dot')))
            fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QLD'], name='QLD', line=dict(color='#3B82F6', width=1.5, dash='dash')))
            fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['TQQQ'], name='TQQQ', line=dict(color='#EF4444', width=1.5, dash='dash')))
            fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['V4.5'], name='AMLS', line=dict(color=main_color, width=3.5)))
            fig_eq.update_layout(title=dict(text="Equity Curve (Log)", font=dict(family='Outfit', size=16, color="#0F172A")), height=400, yaxis_type='log', **chart_layout)
            
            with st.container(border=True):
                st.plotly_chart(fig_eq, use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            def get_dd_series(series): return (series / series.cummax()) - 1
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QQQ']), name='QQQ', line=dict(color='#94A3B8', width=1)))
            fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QLD']), name='QLD', line=dict(color='#3B82F6', width=1)))
            fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['TQQQ']), name='TQQQ', line=dict(color='#EF4444', width=1)))
            fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['V4.5']), name='AMLS', fill='tozeroy', line=dict(color=main_color, width=2.5)))
            fig_dd.update_layout(title=dict(text="Drawdown Curve", font=dict(family='Outfit', size=16, color="#0F172A")), height=300, yaxis=dict(tickformat='.0%'), **chart_layout)
            
            with st.container(border=True):
                st.plotly_chart(fig_dd, use_container_width=True)
            
            st.divider()
            if st.button("✨ AI 추론 요약 실행", use_container_width=True):
                try:
                    import google.generativeai as genai
                    api_key = st.secrets["GEMINI_API_KEY"]
                    genai.configure(api_key=api_key)
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(models[0].replace('models/',''))
                    prompt = f"""너는 최고 퀀트 애널리스트야. AMLS V4.5 전략 백테스트 결과를 분석해.
                    [AMLS] 누적수익률: {ret_o*100:.1f}%, CAGR: {cagr_o*100:.1f}%, MDD: {mdd_o*100:.1f}%
                    [TQQQ] 누적수익률: {ret_t*100:.1f}%, CAGR: {cagr_t*100:.1f}%, MDD: {mdd_t*100:.1f}%
                    AMLS 전략이 레버리지 MDD를 어떻게 회피하면서 수익을 냈는지 3단락으로 분석해."""
                    with st.spinner("AI 분석 중..."):
                        response = model.generate_content(prompt)
                        st.markdown(apply_theme(f"""<div class="glass-card" style="height: auto !important; padding: 30px !important; color:#0F172A; font-weight:500;">{response.text}</div>"""), unsafe_allow_html=True)
                except KeyError: st.error("🚨 GEMINI_API_KEY 누락")

elif page == "📰 Macro News":
    headlines_for_ai, news_items = fetch_macro_news()

    st.markdown(apply_theme(f"""
    <div class="glass-card" style="height:auto !important; display:flex; flex-direction:row; align-items:center; gap:20px; margin-bottom: 30px; padding: 25px 35px !important;">
      <div style="font-size:2.5em;">📰</div>
      <div>
          <h2 style="margin:0; color:#0F172A; font-size: 1.8em; font-family:'Outfit', sans-serif; font-weight:800; letter-spacing:-1px;">GLOBAL MACRO & AI BRIEFING</h2>
          <p style="margin:5px 0 0 0; color:#10B981; font-weight:700;">월스트리트 주요 속보와 AI 애널리스트의 심층 고찰</p>
      </div>
      <div style="margin-left:auto; background:rgba(255,255,255,0.8); padding:8px 20px; border-radius:50px; font-weight:800; color:#10B981; box-shadow: inset 0 2px 4px rgba(255,255,255,1), 0 4px 15px rgba(0,0,0,0.05);">{rt_label}</div>
    </div>
    """), unsafe_allow_html=True)

    with st.expander("✨ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("🚀 심층 추론 요약 실행", use_container_width=True):
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
                        st.markdown(apply_theme(f"""<div class="glass-card" style="height: auto !important; padding: 30px !important;">{response.text}</div>"""), unsafe_allow_html=True)
            except KeyError: st.error("🚨 GEMINI_API_KEY 누락")

    st.divider()

    if news_items:
        st.markdown("<div style='font-size: 1.4em; font-family: Outfit; font-weight: 800; color: #0F172A; margin-bottom: 20px;'>🖼️ LATEST HEADLINES</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx,item in enumerate(news_items):
            with cols[idx%3]:
                st.markdown(apply_theme(f"""<div class="glass-card" style="padding:20px !important; margin-bottom:15px; height:150px !important; display:flex; flex-direction:column; justify-content:space-between;">
                    <div style="font-weight:600; font-size:1em; line-height:1.4; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                        <a href="{item['link']}" target="_blank" style="color:#0F172A; text-decoration:none;">{item['title']}</a>
                    </div>
                    <div style="color:#10B981; font-family:Outfit; font-size:0.85em; font-weight:800; margin-top:10px;">{item['date']}</div>
                </div>"""), unsafe_allow_html=True)
