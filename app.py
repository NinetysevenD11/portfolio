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
st.set_page_config(page_title="AMLS V4.5 FINANCE STRATEGY", layout="wide", page_icon="🌌", initial_sidebar_state="expanded")

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

with st.spinner('위성 데이터 동기화 중...'):
    df        = load_data()
    rt_prices = fetch_realtime_prices()

if df is None or df.empty:
    st.error("🚨 야후 파이낸스(Yahoo Finance) 서버 통신 지연. 잠시 후 새로고침 해주세요.")
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

# 차트 전역 색상 (다크 테마용 네온 컬러)
b_color, t_color = 'rgba(0,0,0,0)', '#94A3B8'
line_c, dash_c = '#8B5CF6', '#3B82F6'  # 퍼플 & 네온블루
rsi_low_c = '#10B981'
regime_colors={1:'rgba(0,0,0,0.0)', 2:'rgba(139,92,246,0.1)', 3:'rgba(249,115,22,0.1)', 4:'rgba(239,68,68,0.2)'}
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
regime_info  = {1:("R1 BULL","풀 가동"),2:("R2 CORR","방어 진입"), 3:("R3 BEAR","대피"),4:("R4 PANIC","최대 방어")}

# ==========================================
# 2. Deep Dark Glass UI CSS + 사이드바 초정밀 튜닝
# ==========================================
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;800&display=swap');
    
    :root {
        --bg-deep: #020617; /* 심해 같은 딥 다크 네이비/블랙 */
        --bg-panel: rgba(15, 23, 42, 0.6); /* 투명한 다크 패널 */
        --text-main: #F8FAFC; /* 쨍한 화이트 */
        --text-muted: #94A3B8; /* 차분한 슬레이트 그레이 */
        --accent-purple: #8B5CF6; /* 네온 퍼플 */
        --accent-blue: #3B82F6; /* 네온 블루 */
        --border-glass: rgba(255, 255, 255, 0.08); /* 매우 얇고 투명한 테두리 */
    }

    /* [배경] 심해 다크 그라데이션 */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-deep) !important;
        background-image: 
            radial-gradient(circle at 15% 50%, rgba(139, 92, 246, 0.05), transparent 25%),
            radial-gradient(circle at 85% 30%, rgba(59, 130, 246, 0.05), transparent 25%) !important;
        color: var(--text-main) !important;
        font-family: 'Pretendard', sans-serif;
    }
    
    [data-testid="stHeader"] { background-color: transparent !important; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; }
    .main .block-container { max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem; }

    /* =========================================
       ✨ 사이드바 완벽 개편 (2026 트렌드 반영)
       ========================================= */
    [data-testid="stSidebar"] {
        background: rgba(2, 6, 23, 0.65) !important; /* 딥 다크 배경을 투명하게 */
        backdrop-filter: blur(40px) !important;
        -webkit-backdrop-filter: blur(40px) !important;
        border-right: 1px solid var(--border-glass) !important;
    }
    
    /* 1. 라디오 버튼의 기본 동그라미(Bullet)를 완전히 삭제 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] label[data-baseweb="radio"] div:first-child { 
        display: none !important; 
        width: 0 !important; margin: 0 !important; padding: 0 !important;
    }
    
    /* 2. 메뉴 컨테이너 여백 큼직하게 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] { 
        gap: 12px; padding: 20px 15px; 
    }
    
    /* 3. 각 메뉴 항목(Label) 기본 상태 - 큼직한 패딩과 모서리 둥글기 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label {
        background: transparent !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        cursor: pointer; width: 100%; margin: 0 !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }
    
    /* 4. 메뉴 텍스트 - 더 큼직하게 (1.25em) */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label p {
        font-family: 'Outfit', 'Pretendard', sans-serif !important;
        font-size: 1.25em !important; 
        font-weight: 500 !important; 
        color: #94A3B8 !important; 
        margin: 0 !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        transform-origin: left center !important;
    }
    
    /* 5. 🚨 Hover 효과 (마우스 올렸을 때) 🚨 */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        background: rgba(139, 92, 246, 0.08) !important; /* 연한 퍼플 배경 오버레이 */
    }
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label:hover p { 
        color: #F8FAFC !important; /* 텍스트 밝아짐 */
        transform: scale(1.08) translateX(5px) !important; /* 글씨 살짝 확대 + 우측 밀림 */
        font-weight: 600 !important;
    }
    
    /* 6. Checked 효과 (선택된 메뉴) */
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
        background: rgba(139, 92, 246, 0.15) !important;
        box-shadow: inset 4px 0 0 #8B5CF6 !important; /* 좌측에 네온 퍼플 엣지 라인 */
        border-radius: 12px !important;
    }
    [data-testid="stSidebar"] div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) p {
        color: #FFFFFF !important; 
        font-weight: 800 !important;
        transform: scale(1.08) translateX(5px) !important; /* 선택 상태에서도 확대 유지 */
    }

    /* =========================================
       메인 패널 및 기타 UI
       ========================================= */
    .glass-card {
        background: var(--bg-panel) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05) !important;
        height: 100%; display: flex; flex-direction: column; justify-content: space-between;
    }
    .glass-card h3 { font-size: 1.1em !important; font-weight: 600 !important; color: var(--text-main); margin-bottom: 15px !important; letter-spacing: 0.5px; }

    .glass-inset {
        background: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 12px !important; padding: 16px; text-align: center; margin-bottom: 16px;
    }
    
    h1 { font-size: 2.2em !important; font-weight: 700 !important; letter-spacing: -0.5px; margin: 0 !important; color: var(--text-main) !important; }

    .crow { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9em; }
    .clabel { color: var(--text-muted); font-weight: 400; }
    .cval { font-weight: 600; color: var(--text-main); }

    [data-testid="stMetric"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 5px !important; }
    [data-testid="stMetricLabel"] > div > div > p { font-size: 0.85em !important; font-weight: 500; color: var(--text-muted) !important; }
    [data-testid="stMetricValue"] > div { font-size: 1.4em !important; font-weight: 700; color: var(--text-main) !important; font-family: 'Inter', 'Pretendard', sans-serif; }
    div[data-testid="stMetricDelta"] > div { font-size: 0.8em !important; font-weight: 600; }
    
    [data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div { background: rgba(0,0,0,0.5) !important; border: 1px solid var(--border-glass) !important; border-radius: 8px !important; color: var(--text-main) !important; }
</style>""", unsafe_allow_html=True)

# iframe 용 CSS (HTML Components)
LG_CSS_BASE = """<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
* { margin:0; padding:0; box-sizing:border-box; }
body { background: transparent; font-family: 'Pretendard', sans-serif; color: #F8FAFC; padding: 10px; }
.glass-card { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05); height: 580px; display: flex; flex-direction: column; }
.glass-inset { background: rgba(0, 0, 0, 0.3); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); padding: 16px; margin-bottom: 16px; text-align: center; }
h2, h3, h4 { color: #F8FAFC; font-weight: 600; margin-bottom: 8px; font-size: 1.1em; letter-spacing: 0.5px; }
.crow { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9em; }
.clabel { color: #94A3B8; font-weight: 400; } .cval { font-weight: 600; color: #F8FAFC; font-size: 1.05em; }
.weight-header { display: flex; justify-content: space-between; font-size: 0.8em; font-weight: 600; color: #94A3B8; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 8px; text-transform: uppercase; }
.footer-msg { margin-top: auto; padding: 12px; font-size: 0.85em; text-align: center; border-radius: 8px; background: rgba(139,92,246,0.1); color: #C4B5FD; font-weight: 500; border: 1px solid rgba(139,92,246,0.2); }
</style>"""

# ==========================================
# 3. 사이드바 UI (다크 앤 클린)
# ==========================================
sidebar_top = st.sidebar.container()
sidebar_top.markdown(f"""
<div style="padding: 20px 15px;">
    <div style="font-family: 'Outfit', sans-serif; font-size: 2.2em; font-weight: 800; color: #F8FAFC; letter-spacing: -1px;">AMLS <span style="color:#8B5CF6;">V4.5</span></div>
    <div style="font-size: 0.85em; font-weight: 600; color: #94A3B8; margin-bottom: 15px; letter-spacing: 1px;">QUANTITATIVE ENGINE</div>
    <div style="font-size: 0.75em; color: #34D399; font-weight: 600; padding: 4px 10px; background: rgba(16,185,129,0.1); border-radius: 4px; display: inline-block; border: 1px solid rgba(16,185,129,0.2);">
        {rt_label}
    </div>
</div>""", unsafe_allow_html=True)

page = st.sidebar.radio("MENU",
    ["📊 Dashboard", "💼 Portfolio", "🍫 8-Pack Radar", "📈 Backtest Lab", "📰 Macro News"],
    label_visibility="collapsed")

st.sidebar.markdown(f"""
<div style="margin-top: 50px; padding: 20px 15px; border-top: 1px solid rgba(255,255,255,0.05);">
    <div style="font-size:0.7em; font-weight:600; color:#8B5CF6; letter-spacing: 1px;">POWERED BY APEX</div>
    <div style="font-size:0.7em; font-weight:400; color:#64748B; margin-top: 4px;">Deep Space Edition v4.5<br>&copy; 2026 SEYOON.</div>
</div>""", unsafe_allow_html=True)

# 메인 타이틀 영역
st.markdown(f"""
<div style="padding-bottom:15px; margin-bottom:25px; display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 1px solid rgba(255,255,255,0.08);">
    <div>
        <h1>AMLS V4.5 ENGINE</h1>
        <p style="font-size:0.95em; margin:4px 0 0 0; font-weight:500; color:#94A3B8;">Quantitative Asset Allocation System</p>
    </div>
    <div style="text-align:right;">
        <div style="font-size:0.8em; font-weight:500; color:#8B5CF6; border: 1px solid rgba(139,92,246,0.3); padding: 4px 12px; border-radius: 50px;">{rt_label} STATUS</div>
    </div>
</div>""", unsafe_allow_html=True)

# ==========================================
# 5. 페이지 라우팅
# ==========================================
if page == "📊 Dashboard":
    
    def _lg_row(label, val, passed):
        icon = "🟢" if passed else "🔴"
        color = "#F8FAFC" if passed else "#EF4444"
        return f'<div class="crow"><span class="clabel">{label}</span><span class="cval" style="color:{color};">{val} {icon}</span></div>'

    soxl_title  = "SOXL 진입 승인" if smh_cond else "USD 방어 진입"
    soxl_strat  = "3x Leverage" if smh_cond else "2x Defense"
    soxl_color  = "#34D399" if smh_cond else "#8B5CF6"
    
    weight_rows = "".join([f'<div class="crow"><span class="clabel">{k}</span><span class="cval" style="color:#8B5CF6;">{v*100:.0f}%</span></div>'
                            for k,v in target_weights.items() if v > 0])

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.markdown(f"""<div class="glass-card">
            <h3>MARKET REGIME</h3>
            <div class="glass-inset">
                <div style="color:#8B5CF6; font-size:1.8em; font-weight:700;">{regime_info[curr_regime][0]}</div>
                <div style="font-weight:400; color:#94A3B8; font-size:0.9em; margin-top:4px;">{regime_info[curr_regime][1]}</div>
            </div>
            {_lg_row('VIX < 40', f'{vix_close:.2f}', vix_close<=40)}
            {_lg_row('QQQ > 200MA', f'${qqq_close:.0f}', qqq_close>=qqq_ma200)}
            {_lg_row('50MA ≥ 200MA', f'${qqq_ma50:.0f}', qqq_ma50>=qqq_ma200)}
            <div class="footer-msg">{regime_committee_msg}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="glass-card">
            <h3>SEMI-CONDUCTOR (SOXL)</h3>
            <div class="glass-inset">
                <div style="color:{soxl_color}; font-size:1.8em; font-weight:700;">{soxl_title}</div>
                <div style="font-weight:400; color:#94A3B8; font-size:0.9em; margin-top:4px;">{soxl_strat}</div>
            </div>
            {_lg_row('SMH > 50MA', f'${smh_close:.1f}', smh_c1)}
            {_lg_row('Mom (1M>10%)', f'{smh_1m*100:.1f}%', smh_c2)}
            {_lg_row('RSI > 50', f'{smh_rsi:.1f}', smh_c3)}
            <div class="footer-msg" style="background:rgba(255,255,255,0.03); color:#94A3B8; border-color:rgba(255,255,255,0.05);">※ 3 filters required for SOXL</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="glass-card">
            <h3>TARGET WEIGHTS</h3>
            <div style="display:flex; justify-content:space-between; font-size:0.8em; font-weight:600; color:#94A3B8; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:8px; margin-bottom:5px;"><span>ASSET</span><span>WEIGHT</span></div>
            {weight_rows}
        </div>""", unsafe_allow_html=True)

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
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color=line_c, width=2)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_qqq.update_layout(title=dict(text="QQQ vs 200MA", font=dict(size=14, color="#F8FAFC")), height=300, **chart_layout)
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color=line_c, width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_tqqq.update_layout(title=dict(text="TQQQ vs 200MA", font=dict(size=14, color="#F8FAFC")), height=300, **chart_layout)

    with chart_col1:
        st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
        st.plotly_chart(fig_qqq, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with chart_col2:
        st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
        st.plotly_chart(fig_tqqq, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "💼 Portfolio":
    st.markdown("<h2 style='font-size:1.5em;'>💼 Portfolio & Rebalancing</h2>", unsafe_allow_html=True)
    
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
    
    st.markdown('<div class="glass-card" style="height: auto !important; padding: 20px !important;">', unsafe_allow_html=True)
    edited_df = st.data_editor(
        df_editor,
        disabled=["Asset"],
        hide_index=True,
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    for _, row in edited_df.iterrows():
        asset = row["Asset"]
        st.session_state.portfolio[asset] = {
            'shares': float(row["Shares"]),
            'avg_price': float(row["Avg Price($)"]),
            'fx': float(row["FX Rate(₩)"])
        }
    save_portfolio_to_disk()
    
    st.markdown("<br><h3 style='color:#F8FAFC;'>⚖️ Action Plan</h3>", unsafe_allow_html=True)
    
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
        c_green, c_red = "#34D399", "#EF4444"
        pie_layout = dict(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Pretendard", color="#F8FAFC", size=12))
        
        diff_vals = {a: (total_val_usd * target_weights.get(a, 0.0)) - curr_vals[a] for a in ASSET_LIST}
        chart_c1, chart_c2, chart_c3 = st.columns([1, 1, 1.5])
        
        labels_cur = [a for a in ASSET_LIST if curr_vals[a] > 0]
        vals_cur = [curr_vals[a] for a in labels_cur]
        if sum(vals_cur) > 0:
            fig_cur = go.Figure(data=[go.Pie(labels=labels_cur, values=vals_cur, hole=.4, textinfo='label+percent')])
            fig_cur.update_layout(title=dict(text="Current", font=dict(size=14, color="#F8FAFC")), **pie_layout)
            with chart_c1:
                st.markdown('<div class="glass-card" style="height: auto !important; padding: 10px !important;">', unsafe_allow_html=True)
                st.plotly_chart(fig_cur, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        labels_tgt = [a for a in ASSET_LIST if target_weights.get(a, 0) > 0]
        vals_tgt = [target_weights.get(a, 0) for a in labels_tgt]
        fig_tgt = go.Figure(data=[go.Pie(labels=labels_tgt, values=vals_tgt, hole=.4, textinfo='label+percent')])
        fig_tgt.update_layout(title=dict(text=f"Target (R{curr_regime})", font=dict(size=14, color="#F8FAFC")), **pie_layout)
        with chart_c2:
            st.markdown('<div class="glass-card" style="height: auto !important; padding: 10px !important;">', unsafe_allow_html=True)
            st.plotly_chart(fig_tgt, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        diff_labels = [a for a in ASSET_LIST if abs(diff_vals[a]) >= 1.0]
        diff_values = [diff_vals[a] for a in diff_labels]
        diff_colors = [c_green if v > 0 else c_red for v in diff_values]
        if diff_labels:
            fig_bar = go.Figure(data=[go.Bar(x=diff_labels, y=diff_values, marker_color=diff_colors, text=[f"${v:,.0f}" for v in diff_values], textposition='auto')])
            fig_bar.update_layout(title=dict(text="Rebalancing Amounts ($)", font=dict(size=14, color="#F8FAFC")), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#F8FAFC"), margin=dict(t=40, b=20, l=20, r=20))
            with chart_c3:
                st.markdown('<div class="glass-card" style="height: auto !important; padding: 10px !important;">', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"<h4 style='color:#F8FAFC; margin-top: 20px;'>📝 Quick Orders</h4>", unsafe_allow_html=True)
        summary_html = f"<div class='glass-card' style='height:auto !important; flex-direction:row; gap: 20px; padding: 20px !important;'>"
        
        sell_text = "<div style='flex: 1;'><strong style='color:#EF4444;'>🔴 SELL</strong><br><br>"
        buy_text = "<div style='flex: 1;'><strong style='color:#10B981;'>🟢 BUY</strong><br><br>"
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff < -cur_p * 0.05:
                sell_text += f"<div style='margin-bottom: 8px; font-size: 0.9em;'><span style='color:#8B5CF6; font-weight:600;'>{asset}</span> : <span style='color:#EF4444;'>{abs(diff)/cur_p:,.2f}주</span> 매도</div>"
            elif asset == 'CASH' and diff < -1.0:
                sell_text += f"<div style='margin-bottom: 8px; font-size: 0.9em;'><span style='color:#8B5CF6; font-weight:600;'>CASH</span> : <span style='color:#EF4444;'>${abs(diff):,.0f}</span> 사용</div>"
        
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0
            diff = diff_vals[asset]
            if asset != 'CASH' and diff > cur_p * 0.05:
                buy_text += f"<div style='margin-bottom: 8px; font-size: 0.9em;'><span style='color:#8B5CF6; font-weight:600;'>{asset}</span> : <span style='color:#10B981;'>{diff/cur_p:,.2f}주</span> 매수</div>"
            elif asset == 'CASH' and diff > 1.0:
                buy_text += f"<div style='margin-bottom: 8px; font-size: 0.9em;'><span style='color:#8B5CF6; font-weight:600;'>CASH</span> : <span style='color:#10B981;'>${diff:,.0f}</span> 확보</div>"
                
        summary_html += sell_text + "</div>" + buy_text + "</div></div>"
        st.markdown(summary_html, unsafe_allow_html=True)

        rebal_html = f"""<div style="overflow-x: auto; padding: 10px 0;">
<table style="width: 100%; border-collapse: collapse; text-align: right; color: #F8FAFC; font-size: 0.9em;">
<thead><tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: #94A3B8;">
<th style="padding: 10px; text-align:left;">Asset</th><th>Avg &rarr; Cur</th><th>Ret (KRW)</th><th>Value ($)</th><th>Target %</th><th>Target ($)</th><th>Diff ($)</th><th style="text-align:center;">Action</th>
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
            
            if abs(diff) < cur_p * 0.05 and asset != 'CASH': action = "<span style='color:#64748B;'>HOLD</span>"; diff_str = "-"
            elif abs(diff) < 1.0 and asset == 'CASH': action = "<span style='color:#64748B;'>HOLD</span>"; diff_str = "-"
            elif diff > 0: 
                action = f"<span style='color:#10B981;'>BUY</span>"
                diff_str = f"<span style='color:#10B981;'>+${diff:,.0f}</span>"
            else: 
                action = f"<span style='color:#EF4444;'>SELL</span>"
                diff_str = f"<span style='color:#EF4444;'>-${abs(diff):,.0f}</span>"
                
            if tgt_w > 0 or curr_v > 0 or shares > 0:
                rebal_html += f"""<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
<td style="text-align:left; padding: 12px 10px; font-weight:600; color:#8B5CF6;">{asset}</td>
<td style="padding: 12px 10px; color:#94A3B8;">{avg_p_str}</td>
<td style="padding: 12px 10px;"><span style="color:{ret_usd_color};">{ret_usd_str}</span></td>
<td style="padding: 12px 10px;">{curr_v:,.0f}</td>
<td style="padding: 12px 10px; color:#8B5CF6;">{tgt_w*100:.0f}%</td>
<td style="padding: 12px 10px;">{tgt_v:,.0f}</td>
<td>{diff_str}</td><td style="text-align:center;">{action}</td></tr>"""
        rebal_html += "</tbody></table></div>"
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important;">{rebal_html}</div>', unsafe_allow_html=True)

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

    def _badge(label, color, icon):
        p = {'green':('rgba(16,185,129,0.1)','#34D399'), 'orange':('rgba(249,115,22,0.1)','#FB923C'),
             'red':('rgba(239,68,68,0.1)','#F87171'), 'blue':('rgba(139,92,246,0.1)','#A78BFA')}
        bg,fg = p[color]
        return f'<div style="background:{bg}; color:{fg}; border:1px solid {fg}; border-radius:4px; padding:4px 10px; font-size:0.8em; font-weight:600; display:inline-block; margin-top:5px;">{icon} {label}</div>'

    b1 = _badge("BUY","green","🔥") if qqq_rsi<40 else (_badge("OVER","red","⚠️") if qqq_rsi>70 else _badge("ACC","blue","🟢"))
    b2 = (_badge("BEAR(-20%)","red","🚨") if qqq_dd<-0.20 else (_badge("CORR(-10%)","orange","⚠️") if qqq_dd<-0.10 else _badge("SAFE","green","✅")))
    b3 = (_badge("FEAR","green","🔥") if fg_score<30 else (_badge("GREED","red","⚠️") if fg_score>70 else _badge("NEUTRAL","blue","🟢")))
    b4 = f'<div style="background:rgba(139,92,246,0.1); color:#A78BFA; border:1px solid #A78BFA; border-radius:4px; padding:4px 10px; font-size:0.8em; font-weight:600; display:inline-block; margin-top:5px;">🏆 {top_sec} / 📉 {bot_sec}</div>'
    b5 = _badge("RISK OFF","red","🚨") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _badge("RISK ON","green","✅")
    b6 = (_badge("NARROW","orange","⚠️") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0) else _badge("BROAD","green","✅"))
    b7 = _badge("GOLD","orange","⚠️") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _badge("EQUITY","green","✅")
    b8 = _badge("STRONG USD","red","🚨") if last_row['UUP']>last_row['UUP_MA50'] else _badge("WEAK USD","green","✅")

    gauge_steps = [{'range':[0,25],'color':"rgba(239,68,68,0.5)"},{'range':[25,45],'color':"rgba(249,115,22,0.3)"},
                   {'range':[45,55],'color':"rgba(255,255,255,0.1)"},{'range':[55,75],'color':"rgba(16,185,129,0.3)"},
                   {'range':[75,100],'color':"rgba(16,185,129,0.5)"}]

    st.markdown('<h2 style="font-size:1.5em; margin-bottom:15px;">🍫 8-Pack Radar</h2>', unsafe_allow_html=True)

    row1 = st.columns(4)
    with row1[0]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">1. DCA (RSI)</div>{b1}</div>', unsafe_allow_html=True)
        fig1=go.Figure(); fig1.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_RSI'],line=dict(color=line_c,width=2)))
        fig1.add_hline(y=70,line_dash='dash',line_color=dash_c); fig1.add_hline(y=30,line_dash='dash',line_color=rsi_low_c)
        fig1.update_layout(**radar_layout,yaxis=dict(range=[10,90]),showlegend=False)
        st.plotly_chart(fig1,use_container_width=True)
    with row1[1]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">2. Drawdown</div>{b2}</div>', unsafe_allow_html=True)
        fig2=go.Figure(); fig2.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_DD'],fill='tozeroy',line=dict(color=dash_c,width=2)))
        fig2.update_layout(**radar_layout,yaxis=dict(tickformat='.0%'),showlegend=False)
        st.plotly_chart(fig2,use_container_width=True)
    with row1[2]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">3. Fear & Greed</div>{b3}</div>', unsafe_allow_html=True)
        fig3=go.Figure(go.Indicator(mode="gauge+number",value=fg_score,domain={'x':[0,1],'y':[0,1]},
            gauge={'axis':{'range':[0,100]},'bar':{'color':line_c},'steps':gauge_steps}))
        fig3.update_layout(height=200,margin=dict(l=15,r=15,t=10,b=10),paper_bgcolor=b_color,font=dict(family="Pretendard",color=t_color))
        st.plotly_chart(fig3,use_container_width=True)
    with row1[3]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">4. Sector (1M)</div>{b4}</div>', unsafe_allow_html=True)
        fig4=go.Figure(go.Bar(x=sec_df['수익률'],y=sec_df['섹터'],orientation='h', marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']]))
        fig4.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig4,use_container_width=True)

    row2 = st.columns(4)
    with row2[0]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">5. Credit Spread</div>{b5}</div>', unsafe_allow_html=True)
        fig5=go.Figure(); fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_Ratio'],line=dict(color=line_c,width=2)))
        fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_MA50'],line=dict(color=dash_c,dash='dot')))
        fig5.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig5,use_container_width=True)
    with row2[1]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">6. Market Breadth</div>{b6}</div>', unsafe_allow_html=True)
        fig6=go.Figure(); fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_20d_Ret'],name='QQQ',line=dict(color=line_c,width=2)))
        fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQE_20d_Ret'],name='QQQE',line=dict(color=dash_c,dash='dot')))
        fig6.update_layout(**radar_layout,showlegend=False,yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6,use_container_width=True)
    with row2[2]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">7. Gold / Equity</div>{b7}</div>', unsafe_allow_html=True)
        fig7=go.Figure(); fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_Ratio'],line=dict(color=line_c,width=2)))
        fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_MA50'],line=dict(color=dash_c,dash='dot')))
        fig7.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig7,use_container_width=True)
    with row2[3]:
        st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:15px;"><div style="font-size:0.85em; font-weight:600; color:#94A3B8;">8. USD (UUP)</div>{b8}</div>', unsafe_allow_html=True)
        fig8=go.Figure(); fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP'],line=dict(color=line_c,width=2)))
        fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP_MA50'],line=dict(color=dash_c,dash='dot')))
        fig8.update_layout(**radar_layout,showlegend=False)
        st.plotly_chart(fig8,use_container_width=True)

elif page == "📈 Backtest Lab":
    st.markdown("<h2 style='font-size:1.5em;'>📈 Backtest Lab</h2>", unsafe_allow_html=True)

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
        def render_metric_card(title, ret, cagr, mdd, is_main=False):
            bg = f"background: rgba(139, 92, 246, 0.1);" if is_main else ""
            bdr = f"border: 1px solid #8B5CF6;" if is_main else ""
            return f"""<div class="glass-card" style="{bg} {bdr} height: auto !important; padding: 20px !important;">
<div style="font-size: 0.9em; font-weight: 600; color: #94A3B8; margin-bottom: 8px;">{title}</div>
<div style="font-size: 1.8em; font-weight: 700; color: #F8FAFC; margin-bottom: 10px;">CAGR {cagr*100:.1f}%</div>
<div style="font-size: 0.9em; color: #94A3B8;">누적: <span style="color: #34D399; font-weight: 600;">{ret*100:.1f}%</span> | MDD: <span style="color: #EF4444; font-weight: 600;">{mdd*100:.1f}%</span></div></div>"""
            
        mc1.markdown(render_metric_card("✨ AMLS V4.5", ret_o, cagr_o, mdd_o, True), unsafe_allow_html=True)
        mc2.markdown(render_metric_card("QQQ", ret_q, cagr_q, mdd_q), unsafe_allow_html=True)
        mc3.markdown(render_metric_card("QLD", ret_qld, cagr_qld, mdd_qld), unsafe_allow_html=True)
        mc4.markdown(render_metric_card("TQQQ", ret_t, cagr_t, mdd_t), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QQQ'], name='QQQ', line=dict(color='#64748B', width=1)))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['QLD'], name='QLD', line=dict(color='#3B82F6', width=1.5, dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['TQQQ'], name='TQQQ', line=dict(color='#EF4444', width=1.5, dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index, y=res_df['V4.5'], name='AMLS', line=dict(color='#8B5CF6', width=3)))
        fig_eq.update_layout(title="Equity Curve (Log)", height=400, yaxis_type='log', margin=dict(l=0,r=0,t=30,b=0), **chart_layout)
        st.plotly_chart(fig_eq, use_container_width=True)

elif page == "📰 Macro News":
    headlines_for_ai, news_items = fetch_macro_news()
    st.markdown("<h2 style='font-size:1.5em; margin-bottom: 20px;'>📰 Macro News</h2>", unsafe_allow_html=True)

    if st.button("✨ AI 추론 요약 실행", use_container_width=True):
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            if headlines_for_ai:
                with st.spinner("AI 분석 중..."):
                    genai.configure(api_key=api_key)
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model  = genai.GenerativeModel(models[0].replace('models/',''))
                    prompt = "너는 퀀트 애널리스트야. 다음 뉴스를 섹터별, 리스크 요소, 최종 투자 스탠스로 나누어 3문단으로 요약해.\n" + "\n".join(headlines_for_ai)
                    response = model.generate_content(prompt)
                    st.markdown(f"""<div class="glass-card" style="height: auto !important; padding: 30px !important;">{response.text}</div>""", unsafe_allow_html=True)
        except KeyError: st.error("🚨 GEMINI_API_KEY 누락")

    if news_items:
        cols = st.columns(3)
        for idx,item in enumerate(news_items):
            with cols[idx%3]:
                st.markdown(f"""<div class="glass-card" style="padding:20px !important; margin-bottom:15px; height:140px !important; display:flex; flex-direction:column; justify-content:space-between;">
                    <div style="font-weight:500; font-size:0.95em; line-height:1.4; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                        <a href="{item['link']}" target="_blank" style="color:#F8FAFC; text-decoration:none;">{item['title']}</a>
                    </div>
                    <div style="color:#8B5CF6; font-size:0.8em; margin-top:10px;">{item['date']}</div>
                </div>""", unsafe_allow_html=True)
