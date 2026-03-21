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

with st.spinner('📰 데이터베이스 동기화 중...'):
    df        = load_data()
    rt_prices = fetch_realtime_prices()

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
rt_label = f"🟢 실시간 ({len(rt_injected)}개 종목)" if rt_ok else "🟡 지연 데이터 (장외/캐시)"

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

smh_c1 = smh_close > smh_ma50
smh_c2 = (smh_3m > 0.05 or smh_1m > 0.10)
smh_c3 = smh_rsi > 50
smh_cond = smh_c1 and smh_c2 and smh_c3

def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if smh_ok else 'USD'
    if reg == 1:
        w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2:
        w['TQQQ'], w['QLD'], w['SSO'], w['USD'], w['GLD'], w['SPY'] = 0.15, 0.30, 0.25, 0.10, 0.15, 0.05
    elif reg == 3:
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4:
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w
target_weights = get_weights_v45(curr_regime, smh_cond)

# ==========================================
# 2. 사이드바 & CSS (Apple Lead UI Engineer Spec)
# ==========================================
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    
    :root {
        --text-main: #1C1C1E;
        --text-body: #3A3A3A;
        --text-muted: #5A5A5A;
        --accent: #3B5BDB;
    }

    /* [배경] */
    .stApp, [data-testid="stAppViewContainer"] {
        background: 
            repeating-linear-gradient(105deg, rgba(255,255,255,0.0) 0px, rgba(255,255,255,0.12) 1px, rgba(255,255,255,0.0) 2px, rgba(255,255,255,0.0) 18px),
            linear-gradient(160deg, #E8E9EC 0%, #F4F5F7 8%, #C8CACD 18%, #EAECEE 28%, #F0F1F3 48%, #D0D2D5 56%, #FFFFFF 63%, #E6E8EA 80%, #DCDEE0 100%) !important;
        color: var(--text-body) !important;
        font-family: 'DM Sans', 'Pretendard', sans-serif;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; }
    .main .block-container { max-width: 1300px; padding-top: 1rem; padding-bottom: 2rem; }

    /* [사이드바] */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.15) !important;
        backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
        -webkit-backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
        border-right: 1px solid rgba(255,255,255,0.55) !important;
        box-shadow: 4px 0 40px rgba(0,0,0,0.05) !important;
    }
    
    /* 텍스트 강제 색상 지정 */
    h1, h2, h3, h4, h5, h6 { color: var(--text-main) !important; font-weight: 700 !important; }
    p, span, label, div { color: var(--text-body); font-weight: 500; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: var(--text-muted) !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

    /* [카드 (모든 컨테이너)] */
    .neo-card, [data-testid="stMetric"], .ai-report-box, [data-testid="stExpander"] {
        position: relative;
        background: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
        -webkit-backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.55) !important;
        border-radius: 24px !important;
        box-shadow: 
            0 8px 40px rgba(0,0,0,0.10),
            inset 0 1.5px 0 rgba(255,255,255,0.90),
            inset 0 -1px 0 rgba(200,210,230,0.20) !important;
        overflow: hidden !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
    }
    .neo-card { padding: 25px !important; height: 570px !important; display: flex; flex-direction: column; margin-bottom: 20px; }
    [data-testid="stMetric"] { padding: 18px !important; text-align: center; }
    
    /* 카드 ::before 광택 */
    .neo-card::before, [data-testid="stMetric"]::before, .ai-report-box::before, [data-testid="stExpander"]::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 40%;
        background: linear-gradient(180deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 50%, transparent 100%);
        border-radius: 24px 24px 50% 50%; pointer-events: none; z-index: 0;
    }
    .neo-card > *, [data-testid="stMetric"] > *, .ai-report-box > *, [data-testid="stExpander"] > * { position: relative; z-index: 1; }

    /* [hover 효과] */
    .neo-card:hover, [data-testid="stMetric"]:hover, .ai-report-box:hover, [data-testid="stExpander"]:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 16px 56px rgba(60,70,200,0.18),
            inset 0 1.5px 0 rgba(255,255,255,0.90),
            inset 0 -1px 0 rgba(200,210,230,0.20) !important;
    }

    /* [카드 안의 inset 박스] */
    .neo-inset-box {
        position: relative;
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(20px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
        border: 1px solid rgba(255, 255, 255, 0.50) !important;
        border-radius: 20px !important;
        box-shadow: inset 0 1.5px 0 rgba(255,255,255,0.75), 0 4px 16px rgba(0,0,0,0.06) !important;
        overflow: hidden !important;
        padding: 15px; margin-bottom: 20px; text-align: center;
    }
    .neo-inset-box::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 40%;
        background: linear-gradient(180deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 50%, transparent 100%);
        border-radius: 20px 20px 50% 50%; pointer-events: none; z-index: 0;
    }
    .neo-inset-box > * { position: relative; z-index: 1; }

    /* [버튼] */
    .stButton > button, div.row-widget.stRadio > div > label {
        position: relative;
        background: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
        -webkit-backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.55) !important;
        border-radius: 50px !important; /* 알약 모양 */
        box-shadow: 0 4px 12px rgba(0,0,0,0.10), inset 0 1.5px 0 rgba(255,255,255,0.90) !important;
        overflow: hidden !important;
        color: var(--accent) !important;
        font-weight: 700 !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        margin-bottom: 5px !important;
    }
    .stButton > button::before, div.row-widget.stRadio > div > label::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 45%;
        background: linear-gradient(180deg, rgba(255,255,255,0.4) 0%, transparent 100%);
        border-radius: 50px 50px 0 0; pointer-events: none; z-index: 0;
    }
    .stButton > button > *, div.row-widget.stRadio > div > label > * { position: relative; z-index: 1; }
    
    .stButton > button:hover, div.row-widget.stRadio > div > label:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(59,91,219,0.25), inset 0 1.5px 0 rgba(255,255,255,0.95) !important;
    }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {
        background: linear-gradient(135deg, rgba(59,91,219,0.15), rgba(59,91,219,0.05)) !important;
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(59,91,219,0.3), 0 8px 24px rgba(59,91,219,0.25), inset 0 1.5px 0 rgba(255,255,255,0.9) !important;
    }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) p { color: var(--accent) !important; font-weight: 800 !important; }

    /* 리스트 표 UI */
    .check-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.4); font-size: 0.95em; color: var(--text-body); }
    .check-value { font-family: 'DM Mono', monospace; font-weight: 800; color: var(--accent); }
    
    /* 입력창 및 데이터에디터 투명화 */
    [data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div { background: rgba(255,255,255,0.25) !important; border: 1px solid rgba(255,255,255,0.55) !important; border-radius: 12px !important; color: var(--text-main) !important; }
    [data-testid="stFileUploader"] { background: rgba(255,255,255,0.15) !important; border: 1px dashed rgba(255,255,255,0.55) !important; border-radius: 16px !important; }
    
    div[data-testid="stMetricValue"]>div { color: var(--text-main) !important; font-weight: 800; }
    div[data-testid="stMetricDelta"]>div { color: var(--accent) !important; font-weight: 700; }
</style>""", unsafe_allow_html=True)

# CSS for HTML Components (iframe)
LG_BG = """background: repeating-linear-gradient(105deg, rgba(255,255,255,0.0) 0px, rgba(255,255,255,0.12) 1px, rgba(255,255,255,0.0) 2px, rgba(255,255,255,0.0) 18px), linear-gradient(160deg, #E8E9EC 0%, #F4F5F7 8%, #C8CACD 18%, #EAECEE 28%, #F0F1F3 48%, #D0D2D5 56%, #FFFFFF 63%, #E6E8EA 80%, #DCDEE0 100%) !important;"""
LG_CSS_BASE = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ {LG_BG} font-family: 'DM Sans', sans-serif; color: #3A3A3A; padding: 12px; min-height: 100vh; }}
.glass-card, .glass-inset, .banner, .ncard {{ position: relative; background: rgba(255, 255, 255, 0.25); backdrop-filter: blur(36px) saturate(160%) brightness(1.05); -webkit-backdrop-filter: blur(36px) saturate(160%) brightness(1.05); border: 1px solid rgba(255, 255, 255, 0.55); overflow: hidden; transition: transform 0.3s ease, box-shadow 0.3s ease; }}
.glass-card {{ border-radius: 24px; box-shadow: 0 8px 40px rgba(0,0,0,0.10), inset 0 1.5px 0 rgba(255,255,255,0.90), inset 0 -1px 0 rgba(200,210,230,0.20); padding: 24px; height: 570px; display: flex; flex-direction: column; }}
.glass-card:hover, .ncard:hover {{ transform: translateY(-2px); box-shadow: 0 16px 56px rgba(60,70,200,0.18), inset 0 1.5px 0 rgba(255,255,255,0.90), inset 0 -1px 0 rgba(200,210,230,0.20); }}
.glass-inset {{ background: rgba(255, 255, 255, 0.15); border-radius: 20px; box-shadow: inset 0 1.5px 0 rgba(255,255,255,0.75), 0 4px 16px rgba(0,0,0,0.06); padding: 16px; margin-bottom: 20px; text-align: center; height: auto; }}
.glass-card::before, .glass-inset::before, .banner::before, .ncard::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 40%; background: linear-gradient(180deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 50%, transparent 100%); pointer-events: none; z-index: 0; }}
.glass-card::before {{ border-radius: 24px 24px 50% 50%; }}
.glass-inset::before {{ border-radius: 20px 20px 50% 50%; }}
.glass-card > *, .glass-inset > *, .banner > *, .ncard > * {{ position: relative; z-index: 1; }}
h1, h2, h3, h4, h5, h6 {{ color: #1C1C1E; font-weight: 700; margin-bottom: 8px; }}
p, span, div {{ color: #3A3A3A; font-weight: 500; }}
.crow {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.4); font-size: 0.9em; }}
.clabel {{ color: #5A5A5A; }} .cval {{ font-family: 'DM Mono', monospace; font-weight: 800; color: #3B5BDB; }}
.weight-header {{ display: flex; justify-content: space-between; font-size: 0.8em; font-weight: 700; color: #5A5A5A; border-bottom: 2px solid rgba(255,255,255,0.5); padding-bottom: 8px; margin-bottom: 4px; text-transform: uppercase; }}
.footer-msg {{ margin-top: auto; padding: 12px; font-size: 0.85em; text-align: center; border-radius: 14px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.4); color: #5A5A5A; }}
.banner {{ border-radius: 22px; padding: 16px 24px; margin-bottom: 15px; box-shadow: 0 4px 16px rgba(0,0,0,0.08), inset 0 1.5px 0 rgba(255,255,255,0.9); }}
.ncard {{ border-radius: 20px; padding: 15px; height: 140px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 4px 16px rgba(0,0,0,0.08), inset 0 1.5px 0 rgba(255,255,255,0.9); }}
.ncard::before {{ border-radius: 20px 20px 50% 50%; }}
.ntitle a {{ color: #1C1C1E; text-decoration: none; font-weight: 700; font-size: 0.95em; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
.ndate {{ font-size: 0.8em; color: #3B5BDB; margin-top: 8px; font-weight: 700; }}
</style>"""

sidebar_top = st.sidebar.container()
sidebar_top.markdown(f"""
<div class="neo-inset-box" style="margin-bottom: 10px; padding: 20px; border-radius: 20px; text-align: left;">
    <div style="font-size:1.8em; font-weight:800; color:#3B5BDB;">AMLS V4.5</div>
    <div style="font-size:1.1em; font-weight:700; color:#1C1C1E; margin-bottom: 8px;">FINANCE ENGINE</div>
    <div style="font-size:0.85em; color:#5A5A5A; font-weight: 600; padding: 4px 8px; background: rgba(255,255,255,0.3); border-radius: 8px; display: inline-block;">
        {rt_label}
    </div>
</div>""", unsafe_allow_html=True)

page = st.sidebar.radio("NAVIGATION MENU",
    ["📊 시장 분석관 (Home)", "💼 내 포트폴리오", "🍫 8-Pack 레이더망", "📈 백테스트 랩", "📰 매크로 뉴스룸"],
    label_visibility="collapsed")

st.sidebar.markdown(f"""
<div class="neo-inset-box" style="margin-top: 20px; padding: 15px; border-radius: 16px; text-align: left;">
    <div style="font-size:0.8em; font-weight:700; color:#5A5A5A; text-transform: uppercase;">Powered by Apex</div>
    <div style="font-size:0.8em; font-weight:600; color:#3A3A3A; margin-top: 4px;">Liquid Glass Edition<br>&copy; 2026 SEYOON.</div>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="padding-bottom:15px;margin-bottom:30px;display:flex;justify-content:space-between;align-items:flex-end;margin-top:-20px;border-bottom:2px solid rgba(255,255,255,0.4);">
    <div>
        <h1 style="font-family:Georgia,serif;font-size:2.8em;margin:0;color:#1C1C1E;">AMLS V4.5 FINANCE STRATEGY</h1>
        <p style="font-size:1.1em;letter-spacing:1px;margin:5px 0 0 0;font-weight:800;color:#3B5BDB;">THE WALL STREET QUANTITATIVE JOURNAL</p>
    </div>
    <div style="text-align:right;font-weight:bold;">
        <div style="font-size:1.2em; color:#1C1C1E;">AMLS V4.5 ENGINE</div>
        <div style="font-size:0.9em;color:#5A5A5A;">Liquid Glass Edition</div>
        <div style="font-size:0.8em;margin-top:4px;color:#5A5A5A; background: rgba(255,255,255,0.3); padding: 2px 8px; border-radius: 6px; display: inline-block;">{rt_label}</div>
    </div>
</div>""", unsafe_allow_html=True)

# 차트용 변수
b_color = 'rgba(0,0,0,0)'
t_color = '#3A3A3A'
line_c = '#3B5BDB'
dash_c = '#F97316'
rsi_low_c = '#10B981'
regime_colors={1:'rgba(0,0,0,0.0)',2:'rgba(59,91,219,0.05)',3:'rgba(249,115,22,0.10)',4:'rgba(239,68,68,0.15)'}
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="DM Sans", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="DM Sans", color=t_color))
regime_info  = {1:("🟢 R1 (강세장)","풀 가동"),2:("🟡 R2 (조정장)","TQQQ 15% 방어"), 3:("🟠 R3 (하락장)","현금/금 대피"),4:("🔴 R4 (패닉장)","최대 방어")}

# ==========================================
# 5. 페이지 라우팅
# ==========================================
if page == "📊 시장 분석관 (Home)":
    
    def _lg_ck(label, val, passed):
        icon  = "✔" if passed else "✕"
        color = "#10B981" if passed else "#EF4444"
        return f'<div class="crow"><span class="clabel">{label}</span><span class="cval" style="color:{color};">{val} {icon}</span></div>'

    regime_msg  = regime_committee_msg
    soxl_title  = "🔥 승인: SOXL 편입" if smh_cond else "🛡️ 기각: USD 편입"
    soxl_strat  = "3배수 공격적 진입" if smh_cond else "변동성 방어용 2배수"
    soxl_color  = "#10B981" if smh_cond else "#3B5BDB"
    weight_rows = "".join([f'<div class="crow"><span class="clabel">{k}</span><span class="cval" style="color:#3B5BDB;">{v*100:.0f}%</span></div>'
                            for k,v in target_weights.items() if v > 0])
    
    ck_r = (_lg_ck('① VIX 패닉 임계점 (&lt; 40)',      f'{vix_close:.2f}',                      vix_close<=40) +
            _lg_ck('② 장기 지지선 (QQQ &gt; 200MA)',    f'${qqq_close:.0f} vs ${qqq_ma200:.0f}', qqq_close>=qqq_ma200) +
            _lg_ck('③ 추세 정배열 (50MA ≥ 200MA)',       f'${qqq_ma50:.0f} vs ${qqq_ma200:.0f}',  qqq_ma50>=qqq_ma200) +
            _lg_ck('④ 노이즈 필터 (20일선 &lt; 22)',      f'{vix_ma20:.2f}',                       vix_ma20<22))
    
    ck_s = (_lg_ck('① 정배열 추세 (SMH &gt; 50MA)',      f'${smh_close:.1f} vs ${smh_ma50:.1f}', smh_c1) +
            _lg_ck('② 모멘텀 (1M&gt;10% or 3M&gt;5%)',  f'3M {smh_3m*100:.1f}%',                smh_c2) +
            _lg_ck('③ 매수 심리 강도 (RSI &gt; 50)',      f'{smh_rsi:.1f}',                        smh_c3))

    tr_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head><body>
    <div style="display:grid;grid-template-columns:1.2fr 1.2fr 1fr;gap:20px;align-items:start;">
      <div class="glass-card">
        <h2 style="border-bottom:2px solid rgba(255,255,255,0.4); padding-bottom:8px;">🏛️ 현재 시장 국면</h2>
        <div class="glass-inset">
          <h2 style="color:#3B5BDB; font-size:1.8em;">{regime_info[curr_regime][0]}</h2>
          <p style="font-weight:700;">전략: {regime_info[curr_regime][1]}</p>
        </div>
        <div style="font-weight:800; margin-bottom:8px;">🔍 알고리즘 해부</div>
        {ck_r}
        <div class="footer-msg">💡 위원회: {regime_msg}</div>
      </div>
      <div class="glass-card">
        <h2 style="border-bottom:2px solid rgba(255,255,255,0.4); padding-bottom:8px;">💻 반도체(SOXL) 판독관</h2>
        <div class="glass-inset">
          <h2 style="color:{soxl_color}; font-size:1.8em;">{soxl_title}</h2>
          <p style="font-weight:700;">전략: {soxl_strat}</p>
        </div>
        <div style="font-weight:800; margin-bottom:8px;">🔍 3중 필터 해부</div>
        {ck_s}
        <div class="footer-msg">※ SOXL은 극단적 변동성을 수반하므로 필터 모두 통과 필수.</div>
      </div>
      <div class="glass-card">
        <h2 style="border-bottom:2px solid rgba(255,255,255,0.4); padding-bottom:8px;">🛒 V4.5 목표 비중</h2>
        <div class="weight-header"><span>자산 (ASSET)</span><span>비중 (WEIGHT)</span></div>
        {weight_rows}
      </div>
    </div></body></html>"""
    components.html(tr_html, height=620, scrolling=False)

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("QQQ vs 200MA",  f"${last_row['QQQ']:.2f}",   f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200MA", f"${last_row['TQQQ']:.2f}",  f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (20D MA)",  f"{last_row['VIX_MA20']:.2f}", f"종가:{last_row['^VIX']:.2f}")
    m4.metric("반도체 1M",      f"{last_row['SMH_1M_Ret']*100:+.2f}%", f"vs MA50: {(last_row['SMH']/last_row['SMH_MA50']-1)*100:+.2f}%")
    m5.metric("반도체 3M",      f"{last_row['SMH_3M_Ret']*100:+.2f}%", f"RSI: {last_row['SMH_RSI']:.1f}")

    if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
        st.warning("⚠️ **[선행 경보]** TQQQ가 200일선을 이탈했습니다. 하락 전조 주의.")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    df_recent = df.iloc[-500:]

    fig_qqq  = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'],      name='QQQ',   line=dict(color=line_c, width=2)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'],name='200일선',line=dict(color=dash_c, width=2, dash='dash')))
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'],      name='TQQQ', line=dict(color=line_c, width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'],name='200일선',line=dict(color=dash_c, width=2, dash='dash')))

    for i in range(1, len(df_recent)):
        if df_recent['Regime'].iloc[i-1] != df_recent['Regime'].iloc[i] or i==1:
            start_idx = df_recent.index[i]; curr_r = df_recent['Regime'].iloc[i]
        if i==len(df_recent)-1 or df_recent['Regime'].iloc[i] != df_recent['Regime'].iloc[i+1]:
            fig_qqq.add_vrect(x0=start_idx, x1=df_recent.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)
            fig_tqqq.add_vrect(x0=start_idx,x1=df_recent.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)

    fig_qqq.update_layout(title="[시스템 기준] QQQ vs 200일 이평선",  height=350, **chart_layout)
    fig_tqqq.update_layout(title="[조기 경보] TQQQ vs 200일 이평선", height=350, **chart_layout)
    with chart_col1: st.plotly_chart(fig_qqq,  use_container_width=True)
    with chart_col2: st.plotly_chart(fig_tqqq, use_container_width=True)

# ------------------------------------------
# PAGE 1.5: 💼 내 포트폴리오
# ------------------------------------------
elif page == "💼 내 포트폴리오":
    st.subheader("💼 내 포트폴리오 & 리밸런싱 지침")
    st.markdown("자산별 **보유 수량, 매수 단가, 매입 환율**을 표에 입력하면 증권사 앱에 바로 입력할 수 있는 **정확한 매수/매도 수량**을 계산해 줍니다.")
    
    col_up, col_down = st.columns(2)
    with col_up:
        uploaded_file = st.file_uploader("📂 포트폴리오 수동 복구 (기기 변경 시 JSON 업로드)", type="json")
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                st.session_state.portfolio.update(data)
                sanitize_portfolio() 
                save_portfolio_to_disk()
                st.success("포트폴리오가 성공적으로 복구되었습니다!")
            except:
                st.error("파일 형식이 올바르지 않습니다.")
    with col_down:
        st.markdown("<br>", unsafe_allow_html=True)
        json_str = json.dumps(st.session_state.portfolio)
        st.download_button(label="💾 현재 포트폴리오 수동 백업 (JSON 다운로드)", 
                           data=json_str, file_name="portfolio_backup.json", 
                           mime="application/json", use_container_width=True)

    st.divider()
    
    st.markdown("#### 📥 포트폴리오 자산 입력")
    st.markdown("<span style='color:#5A5A5A; font-weight:600;'>아래 표를 클릭하여 직접 타이핑하거나 엑셀에서 복사/붙여넣기 하세요. (CASH는 달러 총액을 수량에 입력)</span>", unsafe_allow_html=True)
    
    editor_data = []
    for asset in ASSET_LIST:
        val = st.session_state.portfolio.get(asset, {})
        editor_data.append({
            "자산": asset,
            "수량": float(val.get('shares', 0.0)),
            "매수단가($)": float(val.get('avg_price', 1.0 if asset == 'CASH' else 0.0)),
            "매입환율(₩)": float(val.get('fx', 1350.0))
        })
    df_editor = pd.DataFrame(editor_data)
    
    edited_df = st.data_editor(
        df_editor,
        disabled=["자산"],
        hide_index=True,
        use_container_width=True,
        column_config={
            "수량": st.column_config.NumberColumn("보유 수량", min_value=0.0, format="%.4f"),
            "매수단가($)": st.column_config.NumberColumn("매수단가 ($)", min_value=0.0, format="%.2f"),
            "매입환율(₩)": st.column_config.NumberColumn("매입환율 (₩)", min_value=0.0, format="%.2f")
        }
    )
    
    for _, row in edited_df.iterrows():
        asset = row["자산"]
        st.session_state.portfolio[asset] = {
            'shares': float(row["수량"]),
            'avg_price': float(row["매수단가($)"]),
            'fx': float(row["매입환율(₩)"])
        }
    save_portfolio_to_disk()
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### ⚖️ 포트폴리오 현황 및 리밸런싱 액션")
    
    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': current_prices[t] = 1.0
        elif t in rt_prices: current_prices[t] = rt_prices[t]
        elif t in df.columns: current_prices[t] = df[t].iloc[-1]
        else: current_prices[t] = 0.0
            
    cur_fx = rt_prices.get('USDKRW=X', 1350.0)
    
    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}
    total_val_usd = sum(curr_vals.values())
    
    st.metric("총 자산 규모 (Total Portfolio Value)", f"${total_val_usd:,.2f}", f"현재 적용 환율: ₩{cur_fx:,.2f}")
    
    if total_val_usd > 0:
        c_green = "#10B981"
        c_red = "#EF4444"
        pie_layout = dict(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#1C1C1E', family="DM Sans"))
        
        diff_vals = {a: (total_val_usd * target_weights.get(a, 0.0)) - curr_vals[a] for a in ASSET_LIST}
        
        st.markdown("##### 📊 비중 현황 및 리밸런싱 필요 금액")
        chart_c1, chart_c2, chart_c3 = st.columns([1, 1, 1.5])
        
        labels_cur = [a for a in ASSET_LIST if curr_vals[a] > 0]
        vals_cur = [curr_vals[a] for a in labels_cur]
        if sum(vals_cur) > 0:
            fig_cur = go.Figure(data=[go.Pie(labels=labels_cur, values=vals_cur, hole=.4, textinfo='label+percent')])
            fig_cur.update_layout(title_text="현재 포트폴리오 비중", **pie_layout)
            chart_c1.plotly_chart(fig_cur, use_container_width=True)
        
        labels_tgt = [a for a in ASSET_LIST if target_weights.get(a, 0) > 0]
        vals_tgt = [target_weights.get(a, 0) for a in labels_tgt]
        fig_tgt = go.Figure(data=[go.Pie(labels=labels_tgt, values=vals_tgt, hole=.4, textinfo='label+percent')])
        fig_tgt.update_layout(title_text=f"목표 포트폴리오 비중 (R{curr_regime})", **pie_layout)
        chart_c2.plotly_chart(fig_tgt, use_container_width=True)
        
        diff_labels = [a for a in ASSET_LIST if abs(diff_vals[a]) >= 1.0]
        diff_values = [diff_vals[a] for a in diff_labels]
        diff_colors = [c_green if v > 0 else c_red for v in diff_values]
        if diff_labels:
            fig_bar = go.Figure(data=[go.Bar(x=diff_labels, y=diff_values, marker_color=diff_colors, text=[f"${v:,.0f}" for v in diff_values], textposition='auto')])
            fig_bar.update_layout(title_text="리밸런싱 필요 금액 ($)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#1C1C1E', family="DM Sans"), margin=dict(t=40, b=10, l=10, r=10))
            chart_c3.plotly_chart(fig_bar, use_container_width=True)

        st.markdown(f"<h5 style='margin-top: 10px;'>📝 요약 주문서 (증권사 앱 입력용)</h5>", unsafe_allow_html=True)
        summary_html = f"<div class='neo-card' style='height:auto !important; flex-direction:row; gap: 20px; color: #1C1C1E;'>"
        
        sell_text = "<div style='flex: 1;'><strong>🔴 매도(SELL) 주문</strong><br><br>"
        buy_text = "<div style='flex: 1;'><strong>🟢 매수(BUY) 주문</strong><br><br>"
        
        has_sell = False
        has_buy = False
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff < -cur_p * 0.05:
                sell_text += f"<div style='margin-bottom: 8px; font-size: 1.1em;'><span style='display:inline-block; width: 60px; font-weight:bold; color:#3B5BDB;'>{asset}</span> : <span style='color:{c_red}; font-weight:bold;'>{abs(diff)/cur_p:,.2f}주</span> 매도 (약 ${abs(diff):,.0f})</div>"
                has_sell = True
            elif asset == 'CASH' and diff < -1.0:
                sell_text += f"<div style='margin-bottom: 8px; font-size: 1.1em;'><span style='display:inline-block; width: 60px; font-weight:bold; color:#3B5BDB;'>현금</span> : <span style='color:{c_red}; font-weight:bold;'>${abs(diff):,.0f}</span> 투자에 사용</div>"
                has_sell = True
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff > cur_p * 0.05:
                buy_text += f"<div style='margin-bottom: 8px; font-size: 1.1em;'><span style='display:inline-block; width: 60px; font-weight:bold; color:#3B5BDB;'>{asset}</span> : <span style='color:{c_green}; font-weight:bold;'>{diff/cur_p:,.2f}주</span> 매수 (약 ${diff:,.0f})</div>"
                has_buy = True
            elif asset == 'CASH' and diff > 1.0:
                buy_text += f"<div style='margin-bottom: 8px; font-size: 1.1em;'><span style='display:inline-block; width: 60px; font-weight:bold; color:#3B5BDB;'>현금</span> : <span style='color:{c_green}; font-weight:bold;'>${diff:,.0f}</span> 현금 확보</div>"
                has_buy = True
                
        if not has_sell: sell_text += f"<span style='color:#5A5A5A;'>필요한 매도 주문이 없습니다.</span>"
        if not has_buy: buy_text += f"<span style='color:#5A5A5A;'>필요한 매수 주문이 없습니다.</span>"
        
        sell_text += "</div>"
        buy_text += "</div>"
        summary_html += sell_text + buy_text + "</div>"
        st.markdown(summary_html, unsafe_allow_html=True)

        rebal_html = f"""<div class='neo-card' style="height:auto !important; overflow-x: auto; padding: 20px !important;">
<table style="width:100%; border-collapse: collapse; text-align:right; color: #1C1C1E; font-family: 'DM Sans', 'Pretendard', sans-serif; white-space: nowrap;">
<thead>
<tr style="border-bottom: 2px solid rgba(255,255,255,0.5);">
<th style="text-align:left; padding: 12px 10px; color: #5A5A5A;">자산</th>
<th style="padding: 12px 10px; color: #5A5A5A;">매수단가 &rarr; 현재가</th>
<th style="padding: 12px 10px; color: #5A5A5A;">수익률 (KRW)</th>
<th style="padding: 12px 10px; color: #5A5A5A;">평가금액 ($)</th>
<th style="padding: 12px 10px; color: #5A5A5A;">목표비중</th>
<th style="padding: 12px 10px; color: #5A5A5A;">목표금액 ($)</th>
<th style="padding: 12px 10px; color: #5A5A5A;">리밸런싱 ($)</th>
<th style="text-align:center; padding: 12px 10px; color: #5A5A5A;">액션 지침</th>
</tr>
</thead>
<tbody>"""
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
                ret_usd = 0.0
                ret_krw = ((cur_fx / pur_fx) - 1) * 100 if pur_fx > 0 else 0.0
            else:
                avg_p_str = f"${avg_p:,.2f} &rarr; ${cur_p:,.2f}"
                ret_usd = (cur_p / avg_p - 1) * 100 if avg_p > 0 else 0.0
                ret_krw = ((cur_p * cur_fx) / (avg_p * pur_fx) - 1) * 100 if (avg_p > 0 and pur_fx > 0) else 0.0
                
            ret_usd_color = c_green if ret_usd >= 0 else c_red
            ret_krw_color = c_green if ret_krw >= 0 else c_red
            ret_usd_str = f"{ret_usd:+.2f}%" if asset != 'CASH' else "-"
            ret_krw_str = f"₩ {ret_krw:+.2f}%"
            
            if abs(diff) < cur_p * 0.05 and asset != 'CASH': 
                action = f"<span style='color: #5A5A5A; font-weight:bold;'>HOLD</span>"
                diff_str = "-"
            elif abs(diff) < 1.0 and asset == 'CASH':
                action = f"<span style='color: #5A5A5A; font-weight:bold;'>HOLD</span>"
                diff_str = "-"
            elif diff > 0: 
                if asset == 'CASH':
                    action = f"<div style='background: linear-gradient(135deg, rgba(59,91,219,0.2), rgba(0,198,255,0.2)); color: #3B5BDB; border: 1px solid rgba(59,91,219,0.5); box-shadow: 0 4px 16px rgba(59,91,219,0.2), inset 0 1px 0 rgba(255,255,255,0.8); border-radius: 50px; padding: 6px 16px; font-weight: 700; display: inline-block;'>현금 +${diff:,.0f} 확보</div>"
                else:
                    action = f"<div style='background: linear-gradient(135deg, rgba(59,91,219,0.2), rgba(0,198,255,0.2)); color: #3B5BDB; border: 1px solid rgba(59,91,219,0.5); box-shadow: 0 4px 16px rgba(59,91,219,0.2), inset 0 1px 0 rgba(255,255,255,0.8); border-radius: 50px; padding: 6px 16px; font-weight: 700; display: inline-block;'>{diff/cur_p:,.2f}주 매수</div>"
                diff_str = f"<span style='color: {c_green}; font-weight: 800;'>+${diff:,.2f}</span>"
            else: 
                if asset == 'CASH':
                    action = f"<div style='background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(249,115,22,0.2)); color: #DC2626; border: 1px solid rgba(239,68,68,0.5); box-shadow: 0 4px 16px rgba(239,68,68,0.2), inset 0 1px 0 rgba(255,255,255,0.8); border-radius: 50px; padding: 6px 16px; font-weight: 700; display: inline-block;'>현금 -${abs(diff):,.0f} 사용</div>"
                else:
                    action = f"<div style='background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(249,115,22,0.2)); color: #DC2626; border: 1px solid rgba(239,68,68,0.5); box-shadow: 0 4px 16px rgba(239,68,68,0.2), inset 0 1px 0 rgba(255,255,255,0.8); border-radius: 50px; padding: 6px 16px; font-weight: 700; display: inline-block;'>{abs(diff)/cur_p:,.2f}주 매도</div>"
                diff_str = f"<span style='color: {c_red}; font-weight: 800;'>-${abs(diff):,.2f}</span>"
                
            if tgt_w > 0 or curr_v > 0 or shares > 0:
                rebal_html += f"""<tr style="border-bottom: 1px solid rgba(255,255,255,0.3);">
<td style="text-align:left; padding: 15px 10px; font-weight:800; color:#3B5BDB;">{asset}</td>
<td style="padding: 15px 10px; font-weight:600;">{avg_p_str}</td>
<td style="padding: 15px 10px; line-height:1.4;"><span style="color: {ret_usd_color}; font-weight:800;">{ret_usd_str}</span><br><span style="font-size: 0.85em; color: {ret_krw_color}; font-weight:700;">{ret_krw_str}</span></td>
<td style="padding: 15px 10px; font-weight:700;">{curr_v:,.2f}</td>
<td style="padding: 15px 10px; font-weight:800; color:#1C1C1E;">{tgt_w*100:.0f}%</td>
<td style="padding: 15px 10px; font-weight:600;">{tgt_v:,.2f}</td>
<td style="padding: 15px 10px;">{diff_str}</td>
<td style="text-align:center; padding: 15px 10px;">{action}</td>
</tr>"""
        rebal_html += "</tbody></table></div>"
        st.markdown(rebal_html, unsafe_allow_html=True)
    else:
        st.info("👈 위 표에 보유 중인 자산의 수량과 단가를 1개 이상 입력하시면, 시각화 차트와 상세 리밸런싱 지침이 이 자리에 나타납니다.")

# ------------------------------------------
# PAGE 2: 8-PACK
# ------------------------------------------
elif page == "🍫 8-Pack 레이더망":

    df_view   = df.iloc[-120:]
    qqq_rsi   = last_row['QQQ_RSI']
    qqq_dd    = last_row['QQQ_DD']
    vix_score = max(0, min(100, 100-(last_row['^VIX']-12)/28*100))
    dd_score  = max(0, min(100, (qqq_dd+0.20)/0.20*100))
    rsi_score = max(0, min(100, qqq_rsi))
    fg_score  = (vix_score+dd_score+rsi_score)/3
    sec_names = {'XLK':'기술','XLV':'헬스','XLF':'금융','XLY':'소비','XLC':'통신',
                 'XLI':'산업','XLP':'필수','XLE':'에너지','XLU':'유틸','XLRE':'부동산','XLB':'소재'}
    sec_data  = [{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
    sec_df    = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
    top_sec, bot_sec = sec_df.iloc[-1]['섹터'], sec_df.iloc[0]['섹터']

    def _badge(label, color, icon):
        p = {'green':('rgba(16,185,129,0.15)','#10B981'),
             'orange':('rgba(249,115,22,0.15)','#F97316'),
             'red':('rgba(239,68,68,0.15)','#EF4444'),
             'blue':('rgba(59,91,219,0.15)','#3B5BDB')}
        bg,fg = p[color]
        return f'<div class="badge" style="background:{bg};color:{fg};border:1px solid rgba(255,255,255,0.6);">{icon} {label}</div>'

    b1 = _badge("매수","green","🔥") if qqq_rsi<40 else (_badge("과열","red","⚠️") if qqq_rsi>70 else _badge("적립","blue","🟢"))
    b2 = (_badge("약세(-20%)","red","🚨") if qqq_dd<-0.20 else
          (_badge("조정(-10%)","orange","⚠️") if qqq_dd<-0.10 else _badge("고점 순항","green","✅")))
    b3 = (_badge("극단 공포","green","🔥") if fg_score<30 else
          (_badge("극단 탐욕","red","⚠️") if fg_score>70 else _badge("중립","blue","🟢")))
    b4 = f'<div class="badge" style="background:rgba(59,91,219,0.15);color:#3B5BDB;border:1px solid rgba(255,255,255,0.6);">🏆 {top_sec} &nbsp;/&nbsp; 📉 {bot_sec}</div>'
    b5 = _badge("국채 피신","red","🚨") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _badge("회사채 선호","green","✅")
    b6 = (_badge("쏠림 심화","orange","⚠️") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0)
          else _badge("고른 상승","green","✅"))
    b7 = _badge("금 피신","orange","⚠️") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _badge("주식 선호","green","✅")
    b8 = _badge("강달러 압박","red","🚨") if last_row['UUP']>last_row['UUP_MA50'] else _badge("달러 진정","green","✅")

    gauge_steps = [{'range':[0,25],'color':"rgba(239,68,68,0.55)"},
                   {'range':[25,45],'color':"rgba(249,115,22,0.30)"},
                   {'range':[45,55],'color':"rgba(255,255,255,0.15)"},
                   {'range':[55,75],'color':"rgba(16,185,129,0.30)"},
                   {'range':[75,100],'color':"rgba(16,185,129,0.55)"}]

    cells_tr = "".join([f'<div class="glass-inset"><div style="font-size:0.81em;font-weight:700;color:#1C1C1E;margin-bottom:8px;">{t}</div>{b}</div>'
                        for t,b in [("1. 스마트 DCA (RSI)",b1),("2. 멘탈 방어 (Drawdown)",b2),
                                    ("3. 시장 심리 (F&amp;G)",b3),("4. 섹터 순환 (1M)",b4),
                                    ("5. 채권 스프레드",b5),("6. 시장 폭 (Breadth)",b6),
                                    ("7. 안전 자산 (금/주식)",b7),("8. 달러 (UUP)",b8)]])
    components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="glass-card" style="height:auto; margin-bottom: 20px;">
  <h4 style="color:#3B5BDB; margin-bottom: 5px;">"감정을 배제하고, 진실에 집중하십시오."</h4>
  <p>단순한 보조 지표가 아닙니다. <strong>'8-Pack 정밀 렌즈'</strong>를 통해 겉으로 평온해 보이는 시장을 3차원으로 해부합니다.</p>
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;">{cells_tr}</div>
</body></html>""", height=400, scrolling=False)

# ------------------------------------------
# PAGE 3: 📈 백테스트 랩
# ------------------------------------------
elif page == "📈 백테스트 랩":
    st.subheader("📈 AMLS V4.5 공식 백테스트 랩")
    st.markdown("현재 로드된 데이터 기간 동안의 AMLS V4.5 성과를 **나스닥(QQQ) 및 2배/3배 레버리지 장기투자** 성과와 비교 검증합니다.")

    with st.spinner("과거 데이터 기반 정밀 시뮬레이션 가동 중..."):
        daily_ret = df[['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD']].pct_change().fillna(0)
        w_orig = get_weights_v45(df['Regime'].iloc[0], False)
        
        val_o, val_q, val_qld, val_tqqq = 10000, 10000, 10000, 10000
        hist_o, hist_q, hist_qld, hist_tqqq = [val_o], [val_q], [val_qld], [val_tqqq]
        
        for i in range(1, len(df)):
            ret_o = sum(w_orig.get(t,0) * daily_ret[t].iloc[i] for t in w_orig if t in daily_ret.columns)
            
            val_o    *= (1 + ret_o)
            val_q    *= (1 + daily_ret['QQQ'].iloc[i])
            val_qld  *= (1 + daily_ret['QLD'].iloc[i])
            val_tqqq *= (1 + daily_ret['TQQQ'].iloc[i])
            
            hist_o.append(val_o)
            hist_q.append(val_q)
            hist_qld.append(val_qld)
            hist_tqqq.append(val_tqqq)
            
            smh_cond_i = (df['SMH'].iloc[i] > df['SMH_MA50'].iloc[i]) and (df['SMH_3M_Ret'].iloc[i] > 0.05) and (df['SMH_RSI'].iloc[i] > 50)
            w_orig = get_weights_v45(df['Regime'].iloc[i], smh_cond_i)
            
        res_df = pd.DataFrame(index=df.index)
        res_df['V4.5'] = hist_o
        res_df['QQQ']  = hist_q
        res_df['QLD']  = hist_qld
        res_df['TQQQ'] = hist_tqqq
        
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
        
        st.markdown(f"#### 📊 핵심 성과 지표 (최근 {days}일)")
        mc1, mc2, mc3, mc4 = st.columns(4)
        
        def render_metric_card(title, ret, cagr, mdd, is_main=False):
            bg = f"background: rgba(139,92,246,0.15);" if is_main else ""
            bdr = f"border: 2px solid #8B5CF6;" if is_main else f"border: 1px solid rgba(255,255,255,0.55);"
            mdd_col = '#EF4444'
            ret_col = '#10B981'
            
            return f"""<div class="neo-card" style="{bg} {bdr} height: auto !important; padding: 20px !important;">
<div style="font-size: 0.95em; font-weight: 700; color: #5A5A5A; margin-bottom: 8px;">{title}</div>
<div style="font-size: 1.6em; font-weight: 800; color: #1C1C1E; margin-bottom: 8px;">CAGR {cagr*100:.1f}%</div>
<div style="font-size: 0.9em; color: #3A3A3A; font-weight: 600;">누적수익: <span style="color: {ret_col}; font-weight: 800;">{ret*100:.1f}%</span></div>
<div style="font-size: 0.9em; color: #3A3A3A; font-weight: 600;">최대낙폭: <span style="color: {mdd_col}; font-weight: 800;">{mdd*100:.1f}%</span></div>
</div>"""
            
        mc1.markdown(render_metric_card("✨ AMLS V4.5", ret_o, cagr_o, mdd_o, is_main=True), unsafe_allow_html=True)
        mc2.markdown(render_metric_card("QQQ (1배수)", ret_q, cagr_q, mdd_q), unsafe_allow_html=True)
        mc3.markdown(render_metric_card("QLD (2배수)", ret_qld, cagr_qld, mdd_qld), unsafe_allow_html=True)
        mc4.markdown(render_metric_card("TQQQ (3배수)", ret_t, cagr_t, mdd_t), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### 📈 자산 성장 곡선 (Equity Curve)", unsafe_allow_html=True)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QQQ'], name='QQQ (1x)', line=dict(color='#A0AEC0', width=1.5, dash='dot')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QLD'], name='QLD (2x)', line=dict(color='#3B82F6', width=1.5, dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['TQQQ'], name='TQQQ (3x)', line=dict(color='#EF4444', width=1.5, dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['V4.5'], name='AMLS V4.5', line=dict(color=line_c, width=3)))
        
        fig_eq.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                             font=dict(family="DM Sans", color=t_color), yaxis_type='log', margin=dict(l=0,r=0,t=10,b=0),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_eq, use_container_width=True)
        
        st.markdown("#### 📉 수중 차트 (Drawdown - 멘탈 스트레스 지수)", unsafe_allow_html=True)
        def get_dd_series(series): return (series / series.cummax()) - 1
        
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QQQ']), name='QQQ (1x)', line=dict(color='#A0AEC0', width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['QLD']), name='QLD (2x)', line=dict(color='#3B82F6', width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['TQQQ']), name='TQQQ (3x)', line=dict(color='#EF4444', width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index, y=get_dd_series(res_df['V4.5']), name='AMLS V4.5', fill='tozeroy', line=dict(color=line_c, width=2)))
        
        fig_dd.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                             font=dict(family="DM Sans", color=t_color), yaxis=dict(tickformat='.0%'), margin=dict(l=0,r=0,t=10,b=0),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_dd, use_container_width=True)
        
        st.divider()
        st.markdown("#### 🤖 AI 전략 성과 브리핑 리포트")
        st.markdown("제미나이(Gemini) 모델이 위 백테스트의 수익률(Return)과 낙폭(Drawdown)을 비교 분석하여 전략의 우위성을 해설합니다.")
        
        if st.button("✨ 백테스트 결과 AI 분석 실행", use_container_width=True):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model = genai.GenerativeModel(models[0].replace('models/',''))
                
                prompt = f"""너는 월스트리트의 최고 퀀트 애널리스트야. 다음은 지난 {days}일 간의 AMLS V4.5 전략과 주요 나스닥 추종 ETF들의 백테스트 결과야.
                [AMLS V4.5 (동적 자산배분)] 누적수익률: {ret_o*100:.1f}%, 연평균수익률(CAGR): {cagr_o*100:.1f}%, 최대낙폭(MDD): {mdd_o*100:.1f}%
                [QQQ (나스닥 1배수)] 누적수익률: {ret_q*100:.1f}%, 연평균수익률(CAGR): {cagr_q*100:.1f}%, 최대낙폭(MDD): {mdd_q*100:.1f}%
                [QLD (나스닥 2배수)] 누적수익률: {ret_qld*100:.1f}%, 연평균수익률(CAGR): {cagr_qld*100:.1f}%, 최대낙폭(MDD): {mdd_qld*100:.1f}%
                [TQQQ (나스닥 3배수)] 누적수익률: {ret_t*100:.1f}%, 연평균수익률(CAGR): {cagr_t*100:.1f}%, 최대낙폭(MDD): {mdd_t*100:.1f}%
                
                이 데이터를 바탕으로 AMLS V4.5 전략이 '단순 레버리지 존버(QLD, TQQQ)'의 파멸적 MDD 위험을 어떻게 회피하면서도 '1배수(QQQ)' 이상의 수익을 창출해 냈는지 아주 냉철하고 전문적인 3단락 브리핑 리포트를 작성해. 
                숫자를 직접 인용하면서 설명하고, 변동성 끌림(Volatility Decay)을 극복한 이 전략의 가치를 명확히 짚어줘. 마크다운으로 예쁘게 서식을 넣어줘."""
                
                with st.spinner("AI가 성과를 분석 중입니다..."):
                    response = model.generate_content(prompt)
                    st.markdown(f"""<div class="neo-card" style="height: auto !important;">{response.text}</div>""", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"API 호출 오류 (Secrets에 GEMINI_API_KEY가 등록되어 있는지 확인하세요): {e}")

# ------------------------------------------
# PAGE 4: 매크로 뉴스룸
# ------------------------------------------
elif page == "📰 매크로 뉴스룸":
    headlines_for_ai, news_items = fetch_macro_news()

    components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="glass-card" style="height:auto; display:flex; flex-direction:row; align-items:center; gap:15px; margin-bottom: 20px;">
  <div style="font-size:2em;">📰</div>
  <h2 style="margin:0; color:#1C1C1E; font-size: 1.5em;">실시간 글로벌 매크로 뉴스 &amp; AI 브리핑</h2>
  <div style="margin-left:auto; background:rgba(255,255,255,0.4); padding:6px 16px; border-radius:50px; font-weight:700; color:#3B5BDB; border:1px solid rgba(255,255,255,0.8); box-shadow: 0 4px 12px rgba(0,0,0,0.05);">{rt_label}</div>
</div>
</body></html>""", height=120, scrolling=False)

    with st.expander("✨ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("🚀 심층 추론 요약 실행", use_container_width=True):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: 
                    st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("AI가 1920년대 퀀트 애널리스트의 시각으로 뉴스를 분석하고 있습니다..."):
                        genai.configure(api_key=api_key)
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model  = genai.GenerativeModel(models[0].replace('models/',''))
                        
                        prompt = """너는 1920년대 전설적인 월스트리트 퀀트 애널리스트야. 매우 냉철하고 전문적인 어조로 작성해.
                        다음 뉴스 헤드라인들을 분석해서 아래 3가지 목차로 요약해줘.
                        
                        ## 1. 주요 뉴스 분류 (섹터/테마별 묶음)
                        ## 2. 시장 잠재 리스크 (VIX 상승 요소)
                        ## 3. 애널리스트의 최종 고찰 (투자 스탠스)
                        
                        각 목차의 제목은 반드시 `##` 마크다운을 사용해서 크게 눈에 띄게 해주고, 내용은 글머리 기호(`*` 또는 `-`)를 사용해서 가독성 좋게 정리해.
                        
                        [뉴스 헤드라인]:
                        """ + "\n".join(headlines_for_ai)
                        
                        response = model.generate_content(prompt)
                        
                        st.markdown(f"""<style>
.ai-report-box h2 {{ color: #3B5BDB !important; font-size: 1.5em !important; font-weight: 800; border-bottom: 2px solid rgba(255,255,255,0.5); padding-bottom: 8px; margin-top: 25px; margin-bottom: 15px; }}
.ai-report-box h2:first-child {{ margin-top: 0; }}
.ai-report-box p, .ai-report-box li {{ color: #3A3A3A; font-size: 1.1em; line-height: 1.7; font-family: 'DM Sans', 'Pretendard', sans-serif; font-weight: 500; }}
.ai-report-box strong {{ color: #1C1C1E; font-weight: 800; background-color: rgba(255,255,255,0.4); padding: 2px 6px; border-radius: 6px; }}
</style>
<div class="neo-card ai-report-box" style="height: auto !important;">
{response.text}
</div>""", unsafe_allow_html=True)
                        
                        with st.expander("📋 텍스트로 복사하기"): 
                            st.code(response.text, language="markdown")
            except KeyError: 
                st.error("🚨 Secrets에 'GEMINI_API_KEY'를 설정해주세요.")

    st.divider()

    if news_items:
        cards_tr = "".join([f"""<div class="ncard">
  <div style="font-size:1.05em; font-weight:700; line-height:1.45; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;"><a href="{i['link']}" target="_blank" style="color:#1C1C1E; text-decoration:none;">{i['title'].replace('&','&amp;')}</a></div>
  <div style="font-size:0.85em; font-weight:800; color:#3B5BDB; margin-top:8px;">{i['date']}</div>
</div>""" for i in news_items])
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div style="font-size:1.3em; font-weight:800; color:#1C1C1E; margin-bottom:15px; padding-left:4px;">🖼️ 최신 경제 헤드라인 갤러리</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;">{cards_tr}</div>
</body></html>""", height=180+(len(news_items)//3)*165, scrolling=False)
    else:
        st.write("수신된 뉴스가 없습니다. (15분 후 갱신)")
