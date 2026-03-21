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
import google.generativeai as genai

warnings.filterwarnings('ignore')

# ==========================================
# 1. 설정 및 데이터
# ==========================================
st.set_page_config(page_title="AMLS V4.5 FINANCE STRATEGY", layout="wide", page_icon="📰", initial_sidebar_state="expanded")

SECTOR_TICKERS = ['XLK','XLV','XLF','XLY','XLC','XLI','XLP','XLE','XLU','XLRE','XLB']
CORE_TICKERS   = ['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD','^VIX','HYG','IEF','QQQE','UUP']
TICKERS        = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST     = ['TQQQ','SOXL','USD','QLD','SSO','SPY','QQQ','GLD','CASH']

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

REALTIME_TICKERS = ['QQQ','TQQQ','SMH','^VIX','HYG','IEF','UUP','GLD','SPY']
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
res = []; hist_curr = 3; pend = None; cnt = 0
for t in df['Target']:
    if t > hist_curr: hist_curr = t; pend = None; cnt = 0
    elif t < hist_curr:
        if t == pend:
            cnt += 1
            if cnt >= 5: hist_curr = t; pend = None; cnt = 0
        else: pend = t; cnt = 1
    else: pend = None; cnt = 0
    res.append(hist_curr)
df['Regime'] = pd.Series(res, index=df.index).shift(1).bfill()

# ── 핵심 수정: 실시간 가격 주입 후 레짐을 다시 계산 ──────────────
# curr_regime: 5일 확인 필터를 거친 '확정 레짐' (실제 매매 기준)
# live_regime: 실시간 가격 기준 '즉시 읽기' (하향은 즉시 반영)
live_regime   = get_target_v45(last_row)            # 실시간 재계산
hist_regime   = int(df.iloc[-1]['Regime'])           # 히스토리 확정값
# 하향(악화)은 즉시 반영, 상향(개선)은 히스토리 확정값 유지
curr_regime   = live_regime if live_regime > hist_regime else hist_regime
target_regime = live_regime

smh_c1 = smh_close > smh_ma50
smh_c2 = (smh_3m > 0.05 or smh_1m > 0.10)
smh_c3 = smh_rsi > 50
smh_cond = smh_c1 and smh_c2 and smh_c3

# ── v4.4 배분표 (Zero-Cash Optimization) ─────────────────────────
# R1: 현금 5% → SPY 5% 대체
# R2: 현금 10% → SPY 5% + GLD 5% 대체  (현금 5% 유지)
# R3/R4: 현금 유지 (약세장에서 현금은 실탄)
def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if smh_ok else 'USD'
    if reg == 1:
        # TQQQ 30, SOXL/USD 20, QLD 20, SSO 15, GLD 10, SPY 5 (현금 0)
        w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2:
        # TQQQ 15, QLD 30, SSO 25, USD 10, GLD 15, SPY 5 (현금 0)
        w['TQQQ'], w['QLD'], w['SSO'], w['USD'], w['GLD'], w['SPY'] = 0.15, 0.30, 0.25, 0.10, 0.15, 0.05
    elif reg == 3:
        # GLD 50, CASH 35, QQQ 15 — 현금 유지 (약세장 실탄)
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4:
        # GLD 50, CASH 40, QQQ 10 — 최대 방어
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w
target_weights = get_weights_v45(curr_regime, smh_cond)

# ==========================================
# 2. 사이드바
# ==========================================
sidebar_top = st.sidebar.container()
page = st.sidebar.radio("NAVIGATION MENU",
    ["📊 시장 분석관 (Home)","🍫 8-Pack 레이더망","📉 폭락장 아카이브","📰 매크로 뉴스룸"],
    label_visibility="collapsed")
st.sidebar.markdown("<br><hr><br>", unsafe_allow_html=True)
ui_style = st.sidebar.radio("🎨 UI 테마 선택",
    ["Light Mode (Neo-Tactile)", "Dark Mode (Elegant Theme)",
     "Liquid Glass Mode", "Transparent Mode (Acrylic)"])

is_neo_style         = ui_style == "Light Mode (Neo-Tactile)"
is_glass_style       = ui_style == "Liquid Glass Mode"
is_transparent_style = ui_style == "Transparent Mode (Acrylic)"

if is_neo_style:
    h_color="#3A2E28"; h_accent="#B26A47"; h_muted="#8A7668"
    h_border="rgba(139,94,60,0.1)"; h_shadow="2px 2px 4px rgba(255,255,255,0.8)"; h_sidebar_text="#3A2E28"
elif is_glass_style:
    h_color="#FFFFFF"; h_accent="#A8D4FF"; h_muted="rgba(255,255,255,0.65)"
    h_border="rgba(255,255,255,0.25)"; h_shadow="0 1px 6px rgba(0,0,0,0.30)"; h_sidebar_text="#FFFFFF"
elif is_transparent_style:
    h_color="#1C1C1E"; h_accent="#2563EB"; h_muted="#8E8E93"
    h_border="rgba(0,0,0,0.07)"; h_shadow="0 1px 2px rgba(0,0,0,0.08)"; h_sidebar_text="#1C1C1E"
else:
    h_color="#FFFFFF"; h_accent="#8B5CF6"; h_muted="#A0AEC0"
    h_border="rgba(255,255,255,0.05)"; h_shadow="2px 2px 4px rgba(0,0,0,0.5)"; h_sidebar_text="#FFFFFF"

sidebar_top.markdown(f"""
    <div style="text-align:center;margin-bottom:20px;padding-bottom:10px;border-bottom:2px solid {h_border};">
        <h2 style="font-family:Georgia,serif;margin:0;font-size:1.8rem;color:{h_color};">AMLS V4.5</h2>
        <h4 style="font-family:Georgia,serif;margin:0;font-size:1rem;color:{h_accent};">FINANCE STRATEGY</h4>
    </div>""", unsafe_allow_html=True)
st.sidebar.markdown(f"""
    <br><br><br>
    <div style="position:absolute;bottom:10px;text-align:center;width:100%;font-size:0.8em;color:{h_sidebar_text};">
        Powered by AMLS V4.5 Engine<br>&copy; 2026 SEYOON.</div>""", unsafe_allow_html=True)

# ==========================================
# 3. CSS
# ==========================================
neo_tactile_css = """<style>
    :root{--base-bg:#EBE5DF;--text-main:#3A2E28;--accent-primary:#B26A47;
          --shadow-dark:rgba(139,94,60,0.25);--shadow-light:rgba(255,255,255,0.85);
          --shadow-raised:6px 6px 12px var(--shadow-dark),-6px -6px 12px var(--shadow-light);
          --shadow-inset:inset 4px 4px 8px var(--shadow-dark),inset -4px -4px 8px var(--shadow-light);
          --border-color:rgba(139,94,60,0.1);}
    .stApp{background-color:var(--base-bg);color:var(--text-main);font-family:'Pretendard',sans-serif;}
    [data-testid="stSidebar"]{background-color:var(--base-bg);box-shadow:4px 0px 10px var(--shadow-dark);border:none;}
    [data-testid="stSidebar"] p{color:var(--text-main)!important;font-weight:bold;}
    div.row-widget.stRadio>div>label{background-color:var(--base-bg);border-radius:12px;box-shadow:var(--shadow-raised);transition:all 0.3s;}
    div.row-widget.stRadio>div>label:hover p{color:var(--accent-primary)!important;}
    div.row-widget.stRadio>div>label[data-baseweb="radio"]:has(input:checked){box-shadow:var(--shadow-inset)!important;}
    div.row-widget.stRadio>div>label[data-baseweb="radio"]:has(input:checked) p{color:var(--accent-primary)!important;}
    .neo-card{background-color:var(--base-bg);border-radius:20px;padding:25px;height:560px;overflow-y:auto;box-shadow:var(--shadow-raised);display:flex;flex-direction:column;margin-bottom:20px;}
    .neo-inset-box{background-color:var(--base-bg);border-radius:12px;padding:15px;box-shadow:var(--shadow-inset);text-align:center;margin-bottom:20px;}
    .check-row{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border-color);font-size:0.95em;color:var(--text-main);}
    .check-value{font-family:'Courier New',monospace;font-weight:bold;color:var(--accent-primary);}
</style>"""

elegant_dark_css = """<style>
    :root{--base-bg:#121418;--card-bg:#1C1F28;--text-main:#FFFFFF;--text-muted:#A0AEC0;
          --accent-primary:#8B5CF6;--accent-glow:rgba(139,92,246,0.4);
          --border-color:rgba(255,255,255,0.05);--shadow-raised:0 10px 25px rgba(0,0,0,0.5);}
    .stApp{background-color:var(--base-bg);color:var(--text-main);font-family:'Pretendard',sans-serif;}
    [data-testid="stSidebar"]{background-color:var(--base-bg);border-right:1px solid var(--border-color);}
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label{color:#FFFFFF!important;font-weight:bold;}
    div.row-widget.stRadio>div>label{background-color:transparent;border-radius:12px;border:1px solid transparent;transition:all 0.3s;}
    div.row-widget.stRadio>div>label:hover{background-color:rgba(255,255,255,0.05);}
    div.row-widget.stRadio>div>label[data-baseweb="radio"]:has(input:checked){background-color:rgba(139,92,246,0.2)!important;border:1px solid var(--accent-primary);box-shadow:0 0 10px var(--accent-glow);}
    div.row-widget.stRadio>div>label[data-baseweb="radio"]:has(input:checked) p{color:var(--accent-primary)!important;}
    .neo-card{background-color:var(--card-bg);border:1px solid var(--border-color);border-radius:20px;padding:25px;height:560px;overflow-y:auto;box-shadow:var(--shadow-raised);display:flex;flex-direction:column;margin-bottom:20px;}
    .neo-inset-box{background:linear-gradient(145deg,rgba(139,92,246,0.1),rgba(0,0,0,0));border:1px solid var(--accent-primary);border-radius:12px;padding:15px;text-align:center;margin-bottom:20px;box-shadow:0 0 15px var(--accent-glow);}
    .check-row{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border-color);font-size:0.95em;color:var(--text-muted);}
    .check-value{font-family:'Courier New',monospace;font-weight:bold;color:var(--text-main);}
    [data-testid="stMetric"]{background-color:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;box-shadow:var(--shadow-raised);padding:15px;}
    div[data-testid="stMetricValue"]>div{color:var(--text-main)!important;}
    div[data-testid="stMetricDelta"]>div{color:var(--accent-primary)!important;}
</style>"""

# ── Liquid Glass CSS ────────────────────────────────────────
liquid_glass_css = """<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
    @keyframes shimmer {
        0%   { background-position: -300% 0; }
        100% { background-position:  300% 0; }
    }
    @keyframes prism-shift {
        0%   { opacity: 0.6; filter: hue-rotate(0deg); }
        50%  { opacity: 1.0; filter: hue-rotate(30deg); }
        100% { opacity: 0.6; filter: hue-rotate(0deg); }
    }
    :root {
        --lg-bg1: #B8C8F8;
        --lg-bg2: #F0C8E8;
        --lg-bg3: #C8E8FF;
        --text-main: #1C1C1E;
        --text-muted: #4A5270;
        --accent-blue: #3B5BDB;
    }
    /* ── 배경: 실버/크롬 톤 ── */
    .stApp {
        background:
            linear-gradient(135deg,
                rgba(255,255,255,0.30) 0%,
                rgba(200,210,220,0.20) 30%,
                rgba(180,190,205,0.25) 60%,
                rgba(210,215,225,0.20) 100%),
            url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1920&q=80")
            center/cover no-repeat fixed !important;
        color: var(--text-main);
        font-family: 'DM Sans', sans-serif;
    }
    /* ── 사이드바: 진짜 유리 패널 ── */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(40px) saturate(180%) brightness(1.10) !important;
        -webkit-backdrop-filter: blur(40px) saturate(180%) brightness(1.10) !important;
        border-right: 1px solid rgba(255,255,255,0.40) !important;
        box-shadow:
            4px 0 32px rgba(0,0,0,0.08),
            inset -1px 0 0 rgba(255,255,255,0.70) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label { color: rgba(255,255,255,0.92) !important; font-weight: 600; text-shadow: 0 1px 4px rgba(0,0,0,0.25); }
    /* ── 라디오 버튼: 액체 유리 pill ── */
    div.row-widget.stRadio > div > label {
        background: rgba(255,255,255,0.20);
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.65);
        box-shadow:
            0 4px 16px rgba(80,80,200,0.10),
            inset 0 1px 0 rgba(255,255,255,0.85),
            inset 0 -1px 0 rgba(180,190,255,0.20);
        transition: all 0.3s ease;
        margin-bottom: 5px !important;
        position: relative;
        overflow: hidden;
    }
    div.row-widget.stRadio > div > label::before {
        content: '';
        position: absolute;
        top: 0; left: -100%; right: -100%; height: 40%;
        background: linear-gradient(180deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0) 100%);
        border-radius: 14px 14px 0 0;
        pointer-events: none;
    }
    div.row-widget.stRadio > div > label:hover {
        background: rgba(255,255,255,0.35);
        box-shadow: 0 8px 28px rgba(80,80,200,0.18), inset 0 1px 0 rgba(255,255,255,0.95);
        transform: translateY(-1px);
    }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {
        background: rgba(91,111,232,0.18) !important;
        border: 1.5px solid rgba(120,140,255,0.70) !important;
        box-shadow: 0 0 0 2px rgba(91,111,232,0.25), 0 0 20px rgba(91,111,232,0.30) !important;
    }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) p {
        color: #3B4FC8 !important;
    }
    /* ── neo-card: 진짜 유리 투명 ── */
    .neo-card {
        position: relative;
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(36px) saturate(180%) brightness(1.12) !important;
        -webkit-backdrop-filter: blur(36px) saturate(180%) brightness(1.12) !important;
        border-radius: 28px !important;
        padding: 24px !important;
        height: 560px; overflow-y: auto;
        border: 1px solid rgba(255,255,255,0.45) !important;
        box-shadow:
            0 8px 40px rgba(0,0,0,0.12),
            0 2px 8px rgba(0,0,0,0.08),
            inset 0 1.5px 0 rgba(255,255,255,0.85),
            inset 0 -1px 0 rgba(255,255,255,0.10) !important;
        display: flex; flex-direction: column; margin-bottom: 20px;
    }
    /* ── Metric 카드 ── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(30px) saturate(180%) brightness(1.10) !important;
        -webkit-backdrop-filter: blur(30px) saturate(180%) brightness(1.10) !important;
        border: 1px solid rgba(255,255,255,0.40) !important;
        border-radius: 20px !important;
        box-shadow:
            0 4px 20px rgba(0,0,0,0.10),
            inset 0 1px 0 rgba(255,255,255,0.80) !important;
        padding: 16px !important;
        transition: transform 0.25s, box-shadow 0.25s;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 36px rgba(0,0,0,0.16), inset 0 1px 0 rgba(255,255,255,0.90) !important;
    }
    div[data-testid="stMetricValue"] > div { color: #FFFFFF !important; text-shadow: 0 1px 4px rgba(0,0,0,0.3); }
    div[data-testid="stMetricDelta"] > div { color: #A8D4FF !important; }
    /* ── 버튼 ── */
    .stButton > button {
        background: rgba(91,111,232,0.15) !important;
        backdrop-filter: blur(12px) !important;
        border: 1.5px solid rgba(120,140,255,0.55) !important;
        border-radius: 14px !important;
        color: #3B4FC8 !important;
        font-weight: 600 !important;
        box-shadow: 0 0 18px rgba(91,111,232,0.25) !important;
        transition: all 0.25s !important;
    }
    .stButton > button:hover {
        background: rgba(91,111,232,0.28) !important;
        box-shadow: 0 0 32px rgba(91,111,232,0.45) !important;
        transform: translateY(-1px) !important;
    }
    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.14) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255,255,255,0.55) !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 20px rgba(60,70,180,0.10), inset 0 1px 0 rgba(255,255,255,0.85) !important;
    }
    /* ── Alert ── */
    [data-testid="stAlert"] {
        backdrop-filter: blur(16px) !important;
        border-radius: 14px !important;
        border-left-width: 3px !important;
        background: rgba(255,255,255,0.22) !important;
    }
    /* ── Selectbox ── */
    [data-testid="stSelectbox"] > div > div {
        background: rgba(255,255,255,0.30) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255,255,255,0.60) !important;
        border-radius: 12px !important;
    }
    /* ── header text ── */
    h1,h2,h3,h4,h5 { color: #1C1C2E !important; }
    p, span, label { color: #2A2A3E; }
</style>"""

transparent_acrylic_css = """<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
    :root{--base-bg:#E8E8ED;--card-bg:rgba(255,255,255,0.93);--text-main:#1C1C1E;--text-muted:#8E8E93;
          --accent-blue:#2563EB;--border-card:rgba(0,0,0,0.065);
          --shadow-card:0 2px 16px rgba(0,0,0,0.07),0 1px 4px rgba(0,0,0,0.04);
          --glow-blue:0 0 0 2px rgba(37,99,235,0.45),0 0 22px rgba(37,99,235,0.22);}
    .stApp{background-color:var(--base-bg)!important;color:var(--text-main);font-family:'DM Sans',sans-serif;}
    [data-testid="stSidebar"]{background-color:rgba(240,240,245,0.97)!important;border-right:1px solid var(--border-card)!important;box-shadow:2px 0 12px rgba(0,0,0,0.05)!important;}
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label{color:var(--text-main)!important;font-weight:600;}
    div.row-widget.stRadio>div>label{background:rgba(255,255,255,0.95);border-radius:14px;border:1px solid var(--border-card);box-shadow:var(--shadow-card);transition:all 0.2s;margin-bottom:5px!important;}
    div.row-widget.stRadio>div>label:hover{box-shadow:var(--glow-blue);transform:translateY(-1px);}
    div.row-widget.stRadio>div>label[data-baseweb="radio"]:has(input:checked){background:rgba(255,255,255,0.98)!important;border:1.5px solid rgba(37,99,235,0.5)!important;box-shadow:var(--glow-blue)!important;}
    div.row-widget.stRadio>div>label[data-baseweb="radio"]:has(input:checked) p{color:var(--accent-blue)!important;}
    .neo-card{background:var(--card-bg)!important;border:1px solid var(--border-card)!important;border-radius:22px!important;padding:24px!important;height:560px;overflow-y:auto;box-shadow:var(--shadow-card)!important;display:flex;flex-direction:column;margin-bottom:20px;transition:box-shadow 0.25s,transform 0.25s;}
    .neo-card:hover{box-shadow:0 8px 28px rgba(0,0,0,0.11)!important;transform:translateY(-1px);}
    .neo-inset-box{background:#FFFFFF!important;border:1px solid var(--border-card)!important;border-radius:16px!important;padding:18px!important;text-align:center;margin-bottom:18px;box-shadow:inset 0 1px 3px rgba(0,0,0,0.06)!important;}
    .check-row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid rgba(0,0,0,0.055);font-size:0.92em;color:var(--text-main);}
    .check-value{font-family:'DM Mono','Courier New',monospace;font-weight:700;color:var(--accent-blue);}
    [data-testid="stMetric"]{background:var(--card-bg)!important;border:1px solid var(--border-card)!important;border-radius:18px!important;box-shadow:var(--shadow-card)!important;padding:16px!important;transition:box-shadow 0.2s,transform 0.2s;}
    [data-testid="stMetric"]:hover{box-shadow:var(--glow-blue)!important;transform:translateY(-2px);}
    div[data-testid="stMetricValue"]>div{color:var(--text-main)!important;}
    div[data-testid="stMetricDelta"]>div{color:var(--accent-blue)!important;}
    .stButton>button{background:#FFFFFF!important;border:1.5px solid rgba(37,99,235,0.45)!important;border-radius:14px!important;color:var(--accent-blue)!important;font-weight:600!important;box-shadow:var(--glow-blue)!important;transition:all 0.2s!important;}
    .stButton>button:hover{box-shadow:0 0 0 2.5px rgba(37,99,235,0.65),0 0 32px rgba(37,99,235,0.32)!important;transform:translateY(-1px)!important;}
    [data-testid="stExpander"]{background:var(--card-bg)!important;border:1px solid var(--border-card)!important;border-radius:18px!important;box-shadow:var(--shadow-card)!important;}
    [data-testid="stSelectbox"]>div>div{background:#FFFFFF!important;border:1px solid var(--border-card)!important;border-radius:12px!important;}
    [data-testid="stAlert"]{background:rgba(255,255,255,0.95)!important;border-radius:14px!important;border-left-width:3px!important;box-shadow:var(--shadow-card)!important;}
</style>"""

if is_neo_style:         st.markdown(neo_tactile_css,        unsafe_allow_html=True)
elif is_glass_style:     st.markdown(liquid_glass_css,       unsafe_allow_html=True)
elif is_transparent_style: st.markdown(transparent_acrylic_css, unsafe_allow_html=True)
else:                    st.markdown(elegant_dark_css,       unsafe_allow_html=True)

st.markdown("""<style>
    [data-testid="stHeader"]{background-color:transparent!important;}
    #MainMenu{visibility:hidden;}footer{visibility:hidden;}
    .main .block-container{max-width:1300px;padding-top:0rem;padding-bottom:2rem;}
    h1,h2,h3,h4,h5,h6{font-family:'Pretendard',sans-serif!important;}
</style>""", unsafe_allow_html=True)

if is_neo_style:         edition_label = "Neo-Tactile"
elif is_glass_style:     edition_label = "Liquid Glass"
elif is_transparent_style: edition_label = "Acrylic"
else:                    edition_label = "Elegant Dark"

st.markdown(f"""
<div style="padding-bottom:15px;margin-bottom:30px;display:flex;justify-content:space-between;align-items:flex-end;margin-top:-20px;border-bottom:2px solid {h_border};">
    <div>
        <h1 style="font-family:Georgia,serif;font-size:2.8em;margin:0;color:{h_color};text-shadow:{h_shadow};">AMLS V4.5 FINANCE STRATEGY</h1>
        <p style="font-size:1.1em;letter-spacing:1px;margin:5px 0 0 0;font-weight:700;color:{h_accent};">THE WALL STREET QUANTITATIVE JOURNAL</p>
    </div>
    <div style="text-align:right;font-weight:bold;color:{h_color};">
        <div style="font-size:1.2em;">AMLS V4.5 ENGINE</div>
        <div style="font-size:0.9em;color:{h_muted};">{edition_label} Edition</div>
        <div style="font-size:0.8em;margin-top:4px;color:{h_muted};">{rt_label}</div>
    </div>
</div>""", unsafe_allow_html=True)

# ── 차트 색상 ──────────────────────────────────────────────
if is_neo_style:
    b_color='#EBE5DF'; t_color='#3A2E28'; line_c='#3A2E28'; dash_c='#B26A47'; rsi_low_c='#6B8E23'
    regime_colors={1:'rgba(0,0,0,0.0)',2:'rgba(139,94,60,0.05)',3:'rgba(178,106,71,0.10)',4:'rgba(178,106,71,0.20)'}
elif is_glass_style:
    b_color='rgba(0,0,0,0)'; t_color='#1C1C2E'; line_c='#3B5BDB'; dash_c='#E85D9A'; rsi_low_c='#10B981'
    regime_colors={1:'rgba(0,0,0,0.0)',2:'rgba(59,91,219,0.07)',3:'rgba(232,93,154,0.10)',4:'rgba(220,38,38,0.14)'}
elif is_transparent_style:
    b_color='rgba(0,0,0,0)'; t_color='#1C1C1E'; line_c='#2563EB'; dash_c='#F97316'; rsi_low_c='#16A34A'
    regime_colors={1:'rgba(0,0,0,0.0)',2:'rgba(37,99,235,0.04)',3:'rgba(249,115,22,0.07)',4:'rgba(220,38,38,0.10)'}
else:
    b_color='#1C1F28'; t_color='#A0AEC0'; line_c='#8B5CF6'; dash_c='#3B82F6'; rsi_low_c='#34D399'
    regime_colors={1:'rgba(0,0,0,0.0)',2:'rgba(139,92,246,0.05)',3:'rgba(248,113,113,0.10)',4:'rgba(248,113,113,0.20)'}

chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color,
                    font=dict(family="Pretendard", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15),
                    paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
regime_info  = {1:("🟢 R1 (강세장)","풀 가동"),2:("🟡 R2 (조정장)","TQQQ 15% 방어"),
                3:("🟠 R3 (하락장)","현금/금 대피"),4:("🔴 R4 (패닉장)","최대 방어")}

# 레짐 전환 안내 메시지 생성
if curr_regime == live_regime:
    regime_committee_msg = "모든 조건이 현재 국면에 부합합니다."
elif live_regime > curr_regime:
    # 하향 즉시 반영됨 — 이 경우는 curr_regime == live_regime이므로 도달 불가
    regime_committee_msg = f"R{live_regime} 하향 즉시 반영 중입니다."
else:
    # 상향(개선): 5일 확인 대기 중
    regime_committee_msg = f"R{live_regime} 신호 감지 — 5일 확인 대기 중 (현재 R{curr_regime} 배분 유지)"

# ==========================================
# Liquid Glass HTML 생성 헬퍼
# ==========================================
LG_BG = """
  background:
    linear-gradient(135deg,
        rgba(255,255,255,0.30) 0%,
        rgba(200,210,220,0.20) 30%,
        rgba(180,190,205,0.25) 60%,
        rgba(210,215,225,0.20) 100%),
    url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1920&q=80")
    center/cover no-repeat;"""

LG_CSS_BASE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
@keyframes shimmer {
  0%   { background-position: -300% 50%; }
  100% { background-position:  300% 50%; }
}
@keyframes prism {
  0%,100% { opacity:0.7; }
  50%      { opacity:1.0; }
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: 'DM Sans', sans-serif;
  """ + LG_BG + """
  padding: 12px 6px 4px 6px;
  min-height: 100vh;
}
/* ── Liquid Glass 카드 공통 ── */
.lg-card {
  position: relative;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(36px) saturate(180%) brightness(1.12);
  -webkit-backdrop-filter: blur(36px) saturate(180%) brightness(1.12);
  border-radius: 28px;
  border: 1px solid rgba(255,255,255,0.42);
  box-shadow:
    0 8px 40px rgba(0,0,0,0.14),
    0 2px 8px  rgba(0,0,0,0.08),
    inset 0 1.5px 0 rgba(255,255,255,0.82),
    inset 0 -1px 0 rgba(255,255,255,0.08),
    inset 1px 0 0 rgba(255,255,255,0.30),
    inset -1px 0 0 rgba(255,255,255,0.15);
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}
.lg-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 16px 56px rgba(60,70,200,0.22),
    0 4px 16px rgba(0,0,0,0.12),
    inset 0 1.5px 0 rgba(255,255,255,0.98),
    inset 0 -1px 0 rgba(160,170,255,0.22);
}
/* 상단 하이라이트 리플렉션 */
.lg-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 42%;
  background: linear-gradient(180deg,
    rgba(255,255,255,0.38) 0%,
    rgba(255,255,255,0.10) 60%,
    rgba(255,255,255,0.00) 100%);
  border-radius: 28px 28px 60% 60%;
  pointer-events: none;
  z-index: 1;
}
/* 프리즘 엣지 shimmer */
.lg-card::after {
  content: '';
  position: absolute;
  top: -1px; left: -1px; right: -1px; bottom: -1px;
  border-radius: 29px;
  background: linear-gradient(135deg,
    rgba(180,200,255,0.55) 0%,
    rgba(255,180,220,0.35) 20%,
    rgba(180,255,220,0.30) 40%,
    rgba(255,220,120,0.20) 60%,
    rgba(180,180,255,0.40) 80%,
    rgba(255,255,255,0.55) 100%);
  background-size: 300% 300%;
  animation: shimmer 5s linear infinite, prism 4s ease-in-out infinite;
  z-index: -1;
  pointer-events: none;
}
.lg-card-inner {
  position: relative;
  z-index: 2;
  padding: 22px 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
/* ── 카드 제목 ── */
.lg-title {
  font-size: 1.12em;
  font-weight: 700;
  color: rgba(255,255,255,0.95);
  border-bottom: 1px solid rgba(255,255,255,0.22);
  padding-bottom: 11px;
  margin-bottom: 14px;
  text-shadow: 0 1px 4px rgba(0,0,0,0.25);
}
/* ── 인셋 박스 (내부 glass) ── */
.lg-inset {
  position: relative;
  background: rgba(255,255,255,0.16);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid rgba(255,255,255,0.55);
  border-radius: 20px;
  padding: 16px 14px;
  text-align: center;
  margin-bottom: 16px;
  box-shadow:
    inset 0 1.5px 0 rgba(255,255,255,0.80),
    0 4px 20px rgba(0,0,0,0.08);
  overflow: hidden;
}
.lg-inset::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 45%;
  background: linear-gradient(180deg, rgba(255,255,255,0.45) 0%, transparent 100%);
  border-radius: 20px 20px 50% 50%;
  pointer-events: none;
}
.lg-inset h2 {
  font-size: 1.4em; font-weight: 700; margin-bottom: 4px;
  position: relative; z-index: 1;
  text-shadow: 0 1px 6px rgba(0,0,0,0.30);
}
.lg-inset p {
  font-size: 0.87em; color: rgba(255,255,255,0.78); font-weight: 500;
  position: relative; z-index: 1;
  text-shadow: 0 1px 3px rgba(0,0,0,0.20);
}
/* ── 체크 행 ── */
.crow {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.18);
  font-size: 0.875em;
}
.clabel { color: rgba(255,255,255,0.85); font-weight: 500; text-shadow: 0 1px 3px rgba(0,0,0,0.20); }
.cval   { font-family: 'DM Mono', monospace; font-weight: 600; font-size: 0.95em; }
/* ── 하단 메시지 ── */
.footer-msg {
  margin-top: auto;
  padding: 11px 14px;
  font-size: 0.81em; color: rgba(255,255,255,0.80);
  text-align: center;
  background: rgba(255,255,255,0.10);
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.22);
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0,0,0,0.20);
}
.footer-dashed {
  margin-top: auto;
  padding: 11px 14px;
  font-size: 0.81em; color: rgba(255,255,255,0.70);
  text-align: center;
  border-top: 1px dashed rgba(255,255,255,0.30);
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0,0,0,0.20);
}
/* ── 비중 헤더 ── */
.weight-header {
  display: flex; justify-content: space-between;
  font-size: 0.77em; font-weight: 700; color: rgba(255,255,255,0.55);
  border-bottom: 1.5px solid rgba(255,255,255,0.22);
  padding-bottom: 7px; margin-bottom: 2px; letter-spacing: 0.4px;
}
/* ── 뱃지 (8-Pack용) ── */
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 13px; border-radius: 12px;
  font-size: 0.88em; font-weight: 600;
  width: 100%; justify-content: center;
  backdrop-filter: blur(8px);
  text-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
/* ── 8-Pack 셀 ── */
.pack-cell {
  position: relative;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(28px) saturate(180%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.42);
  border-radius: 20px;
  padding: 13px 13px 11px 13px;
  box-shadow:
    0 4px 20px rgba(0,0,0,0.10),
    inset 0 1.5px 0 rgba(255,255,255,0.75);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}
.pack-cell:hover { transform: translateY(-2px); box-shadow: 0 10px 32px rgba(0,0,0,0.16), inset 0 1.5px 0 rgba(255,255,255,0.88); }
.pack-cell::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 40%;
  background: linear-gradient(180deg, rgba(255,255,255,0.28) 0%, transparent 100%);
  border-radius: 20px 20px 50% 50%;
  pointer-events: none;
}
.pack-title { font-size: 0.81em; font-weight: 700; color: rgba(255,255,255,0.90); margin-bottom: 8px; position: relative; z-index: 1; text-shadow: 0 1px 4px rgba(0,0,0,0.25); }
/* ── 배너 (8-Pack / 뉴스) ── */
.lg-banner {
  position: relative;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(32px) saturate(180%);
  -webkit-backdrop-filter: blur(32px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.42);
  border-radius: 22px;
  padding: 16px 22px;
  margin-bottom: 14px;
  box-shadow: 0 6px 28px rgba(0,0,0,0.10), inset 0 1.5px 0 rgba(255,255,255,0.78);
  overflow: hidden;
}
.lg-banner::before {
  content: '';
  position: absolute; top:0; left:0; right:0; height:45%;
  background: linear-gradient(180deg, rgba(255,255,255,0.28) 0%, transparent 100%);
  border-radius: 22px 22px 50% 50%;
  pointer-events: none;
}
.lg-banner h4 { color: rgba(255,255,255,0.95); font-size: 1.03em; margin-bottom: 5px; font-weight: 700; position: relative; z-index:1; text-shadow: 0 1px 6px rgba(0,0,0,0.30); }
.lg-banner p  { color: rgba(255,255,255,0.80); font-size: 0.91em; line-height: 1.6; position: relative; z-index:1; text-shadow: 0 1px 3px rgba(0,0,0,0.20); }
/* ── 뉴스 카드 ── */
.ncard {
  position: relative;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(28px) saturate(180%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.42);
  border-radius: 20px;
  padding: 15px 15px 13px 15px;
  height: 140px;
  display: flex; flex-direction: column; justify-content: space-between;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12), inset 0 1.5px 0 rgba(255,255,255,0.70);
  overflow: hidden;
  transition: transform 0.22s, box-shadow 0.22s;
}
.ncard:hover { transform: translateY(-3px); box-shadow: 0 12px 36px rgba(0,0,0,0.20), inset 0 1.5px 0 rgba(255,255,255,0.85); }
.ncard::before {
  content: '';
  position: absolute; top:0; left:0; right:0; height: 40%;
  background: linear-gradient(180deg, rgba(255,255,255,0.25) 0%, transparent 100%);
  border-radius: 20px 20px 50% 50%;
  pointer-events: none;
}
.ntitle { font-size:0.89em; font-weight:600; line-height:1.44; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; color:rgba(255,255,255,0.92); position:relative; z-index:1; text-shadow:0 1px 4px rgba(0,0,0,0.25); }
.ntitle a { color:rgba(255,255,255,0.92); text-decoration:none; }
.ntitle a:hover { color:#A8D4FF; }
.ndate { font-size:0.77em; font-weight:600; color:#A8D4FF; margin-top:8px; flex-shrink:0; position:relative; z-index:1; }
.section-title { font-size:1.03em; font-weight:700; color:rgba(255,255,255,0.95); margin-bottom:12px; padding-left:2px; text-shadow:0 1px 4px rgba(0,0,0,0.20); }
.badge-rt {
  margin-left:auto;
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.90);
  border: 1px solid rgba(255,255,255,0.40);
  border-radius: 10px;
  padding: 4px 12px;
  font-size: 0.8em; font-weight:600; white-space:nowrap;
  backdrop-filter: blur(8px);
  text-shadow: 0 1px 3px rgba(0,0,0,0.20);
}
</style>
"""

def _lg_ck(label, val, passed):
    icon  = "✔" if passed else "✕"
    color = "#16A34A" if passed else "#DC2626"
    return f'<div class="crow"><span class="clabel">{label}</span><span class="cval" style="color:{color};">{val} {icon}</span></div>'

def lg_cards_html(regime_title, regime_strat, regime_msg, soxl_title, soxl_strat, soxl_color,
                  weight_rows, ck_rows_regime, ck_rows_soxl):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div style="display:grid;grid-template-columns:1.2fr 1.2fr 1fr;gap:14px;align-items:start;">

  <div class="lg-card" style="height:570px;">
    <div class="lg-card-inner">
      <div class="lg-title">🏛️ 현재 시장 국면</div>
      <div class="lg-inset">
        <h2 style="color:#3B4FC8;">{regime_title}</h2>
        <p>전략: {regime_strat}</p>
      </div>
      <div style="font-size:0.82em;font-weight:700;color:#2A2A4A;margin-bottom:4px;">🔍 알고리즘 해부</div>
      {ck_rows_regime}
      <div class="footer-msg">💡 위원회: {regime_msg}</div>
    </div>
  </div>

  <div class="lg-card" style="height:570px;">
    <div class="lg-card-inner">
      <div class="lg-title">💻 반도체(SOXL) 판독관</div>
      <div class="lg-inset">
        <h2 style="color:{soxl_color};">{soxl_title}</h2>
        <p>전략: {soxl_strat}</p>
      </div>
      <div style="font-size:0.82em;font-weight:700;color:#2A2A4A;margin-bottom:4px;">🔍 3중 필터 해부</div>
      {ck_rows_soxl}
      <div class="footer-dashed">※ SOXL은 극단적 변동성을 수반하므로 필터 모두 통과 필수.</div>
    </div>
  </div>

  <div class="lg-card" style="height:570px;">
    <div class="lg-card-inner">
      <div class="lg-title">🛒 V4.5 목표 비중</div>
      <div class="weight-header"><span>자산 (ASSET)</span><span>비중 (WEIGHT)</span></div>
      {weight_rows}
    </div>
  </div>

</div>
</body></html>"""

# ==========================================
# 5. 페이지 라우팅
# ==========================================
if page == "📊 시장 분석관 (Home)":

    def render_row_std(label, val, passed):
        if is_neo_style:
            icon = f"<span style='color:#6B8E23;'>✔</span>" if passed else f"<span style='color:#B26A47;'>✕</span>"
        elif is_transparent_style:
            icon = f"<span style='color:#16A34A;'>✔</span>" if passed else f"<span style='color:#DC2626;'>✕</span>"
        else:
            icon = f"<span style='color:#34D399;'>✔</span>" if passed else f"<span style='color:#F87171;'>✕</span>"
        return f"<div class='check-row'><span>{label}</span><span class='check-value'>{val} {icon}</span></div>"

    c1, c2, c3 = st.columns([1.2, 1.2, 1])

    if is_glass_style:
        # ── Liquid Glass: components.html ──────────────────
        regime_msg  = regime_committee_msg
        soxl_title  = "🔥 승인: SOXL 편입" if smh_cond else "🛡️ 기각: USD 편입"
        soxl_strat  = "3배수 공격적 진입" if smh_cond else "변동성 방어용 2배수"
        soxl_color  = "#16A34A" if smh_cond else "#3B4FC8"
        weight_rows = "".join([f'<div class="crow"><span class="clabel">{k}</span><span class="cval" style="color:#3B4FC8;">{v*100:.0f}%</span></div>'
                                for k,v in target_weights.items() if v > 0])
        ck_r = (_lg_ck('① VIX 패닉 임계점 (&lt; 40)',       f'{vix_close:.2f}',                      vix_close<=40) +
                _lg_ck('② 장기 지지선 (QQQ &gt; 200MA)',     f'${qqq_close:.0f} vs ${qqq_ma200:.0f}', qqq_close>=qqq_ma200) +
                _lg_ck('③ 추세 정배열 (50MA ≥ 200MA)',       f'${qqq_ma50:.0f} vs ${qqq_ma200:.0f}',  qqq_ma50>=qqq_ma200) +
                _lg_ck('④ 노이즈 필터 (20일선 &lt; 22)',      f'{vix_ma20:.2f}',                       vix_ma20<22))
        ck_s = (_lg_ck('① 정배열 추세 (SMH &gt; 50MA)',      f'${smh_close:.1f} vs ${smh_ma50:.1f}', smh_c1) +
                _lg_ck('② 모멘텀 (1M&gt;10% or 3M&gt;5%)',  f'3M {smh_3m*100:.1f}%',                smh_c2) +
                _lg_ck('③ 매수 심리 강도 (RSI &gt; 50)',      f'{smh_rsi:.1f}',                        smh_c3))
        components.html(lg_cards_html(regime_info[curr_regime][0], regime_info[curr_regime][1],
                                      regime_msg, soxl_title, soxl_strat, soxl_color,
                                      weight_rows, ck_r, ck_s), height=620, scrolling=False)

    elif is_transparent_style:
        # ── Transparent: components.html ───────────────────
        def ck_tr(label, val, passed):
            icon  = "✔" if passed else "✕"
            color = "#16A34A" if passed else "#DC2626"
            return f'<div class="crow"><span class="clabel">{label}</span><span class="cval" style="color:{color};">{val} {icon}</span></div>'

        regime_msg  = regime_committee_msg
        soxl_title  = "🔥 승인: SOXL 편입" if smh_cond else "🛡️ 기각: USD 편입"
        soxl_strat  = "3배수 공격적 진입" if smh_cond else "변동성 방어용 2배수"
        soxl_color  = "#16A34A" if smh_cond else "#2563EB"

        regime_glow = {1:"0 0 0 2px rgba(37,99,235,0.50),0 0 28px rgba(37,99,235,0.25)",
                       2:"0 0 0 2px rgba(249,115,22,0.50),0 0 28px rgba(249,115,22,0.25)",
                       3:"0 0 0 2px rgba(220,38,38,0.45),0 0 28px rgba(220,38,38,0.22)",
                       4:"0 0 0 2px rgba(220,38,38,0.65),0 0 36px rgba(220,38,38,0.35)"}[curr_regime]
        soxl_glow   = ("0 0 0 2px rgba(22,163,74,0.48),0 0 24px rgba(22,163,74,0.22)" if smh_cond
                       else "0 0 0 2px rgba(249,115,22,0.48),0 0 24px rgba(249,115,22,0.22)")

        wr = "".join([f'<div class="crow"><span class="clabel">{k}</span><span class="cval" style="color:#2563EB;">{v*100:.0f}%</span></div>'
                      for k,v in target_weights.items() if v > 0])
        ck_r = (ck_tr('① VIX 패닉 임계점 (&lt; 40)',      f'{vix_close:.2f}',                      vix_close<=40) +
                ck_tr('② 장기 지지선 (QQQ &gt; 200MA)',    f'${qqq_close:.0f} vs ${qqq_ma200:.0f}', qqq_close>=qqq_ma200) +
                ck_tr('③ 추세 정배열 (50MA ≥ 200MA)',      f'${qqq_ma50:.0f} vs ${qqq_ma200:.0f}',  qqq_ma50>=qqq_ma200) +
                ck_tr('④ 노이즈 필터 (20일선 &lt; 22)',     f'{vix_ma20:.2f}',                       vix_ma20<22))
        ck_s = (ck_tr('① 정배열 추세 (SMH &gt; 50MA)',     f'${smh_close:.1f} vs ${smh_ma50:.1f}', smh_c1) +
                ck_tr('② 모멘텀 (1M&gt;10% or 3M&gt;5%)', f'3M {smh_3m*100:.1f}%',                smh_c2) +
                ck_tr('③ 매수 심리 강도 (RSI &gt; 50)',    f'{smh_rsi:.1f}',                        smh_c3))

        tr_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'DM Sans',sans-serif;background:#E8E8ED;padding:12px 6px 4px 6px;}}
.grid{{display:grid;grid-template-columns:1.2fr 1.2fr 1fr;gap:14px;}}
.card{{background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:22px;padding:22px 20px;height:570px;display:flex;flex-direction:column;box-shadow:0 2px 16px rgba(0,0,0,0.07);transition:transform 0.25s,box-shadow 0.25s;overflow:hidden;}}
.card:hover{{transform:translateY(-1px);box-shadow:0 8px 28px rgba(0,0,0,0.11);}}
.card-title{{font-size:1.12em;font-weight:700;color:#1C1C1E;border-bottom:1.5px solid rgba(0,0,0,0.06);padding-bottom:11px;margin-bottom:14px;}}
.inset{{background:#FFFFFF;border:1px solid rgba(0,0,0,0.06);border-radius:16px;padding:17px 14px;text-align:center;margin-bottom:16px;}}
.inset-glow-regime{{background:#FFFFFF;border:1px solid rgba(0,0,0,0.06);border-radius:16px;padding:17px 14px;text-align:center;margin-bottom:16px;box-shadow:{regime_glow};}}
.inset-glow-soxl{{background:#FFFFFF;border:1px solid rgba(0,0,0,0.06);border-radius:16px;padding:17px 14px;text-align:center;margin-bottom:16px;box-shadow:{soxl_glow};}}
.inset h2,.inset-glow-regime h2,.inset-glow-soxl h2{{font-size:1.4em;font-weight:700;margin-bottom:4px;}}
.inset p,.inset-glow-regime p,.inset-glow-soxl p{{font-size:0.87em;color:#6B7280;font-weight:500;}}
.section-label{{font-size:0.82em;font-weight:700;color:#1C1C1E;margin-bottom:4px;}}
.crow{{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(0,0,0,0.055);font-size:0.875em;}}
.clabel{{color:#374151;font-weight:500;}}.cval{{font-family:'DM Mono','Courier New',monospace;font-weight:700;font-size:0.95em;}}
.footer-msg{{margin-top:auto;padding:11px 14px;font-size:0.81em;color:#6B7280;text-align:center;background:rgba(37,99,235,0.05);border-radius:12px;border:1px solid rgba(37,99,235,0.10);font-weight:500;}}
.footer-dashed{{margin-top:auto;padding:11px 14px;font-size:0.81em;color:#6B7280;text-align:center;border-top:1.5px dashed rgba(0,0,0,0.10);font-weight:500;}}
.weight-header{{display:flex;justify-content:space-between;font-size:0.77em;font-weight:700;color:#9CA3AF;border-bottom:1.5px solid rgba(0,0,0,0.08);padding-bottom:7px;margin-bottom:2px;letter-spacing:0.4px;}}
</style></head><body>
<div class="grid">
  <div class="card">
    <div class="card-title">🏛️ 현재 시장 국면</div>
    <div class="inset-glow-regime"><h2 style="color:#2563EB;">{regime_info[curr_regime][0]}</h2><p>전략: {regime_info[curr_regime][1]}</p></div>
    <div class="section-label">🔍 알고리즘 해부</div>
    {ck_r}
    <div class="footer-msg">💡 위원회: {regime_msg}</div>
  </div>
  <div class="card">
    <div class="card-title">💻 반도체(SOXL) 판독관</div>
    <div class="inset-glow-soxl"><h2 style="color:{soxl_color};">{soxl_title}</h2><p>전략: {soxl_strat}</p></div>
    <div class="section-label">🔍 3중 필터 해부</div>
    {ck_s}
    <div class="footer-dashed">※ SOXL은 극단적 변동성을 수반하므로 필터 모두 통과 필수.</div>
  </div>
  <div class="card">
    <div class="card-title">🛒 V4.5 목표 비중</div>
    <div class="weight-header"><span>자산 (ASSET)</span><span>비중 (WEIGHT)</span></div>
    {wr}
  </div>
</div>
</body></html>"""
        components.html(tr_html, height=620, scrolling=False)

    else:
        # ── Neo / Dark ──────────────────────────────────────
        with c1:
            msg_bg = 'transparent' if is_neo_style else 'rgba(139,92,246,0.1)'
            st.markdown(f"""
            <div class="neo-card">
                <div style="font-size:1.4em;font-weight:bold;color:{h_color};border-bottom:2px solid {h_border};padding-bottom:10px;margin-bottom:15px;">🏛️ 현재 시장 국면</div>
                <div class="neo-inset-box">
                    <h2 style="margin:0;color:{h_accent};">{regime_info[curr_regime][0]}</h2>
                    <p style="margin:5px 0 0 0;font-weight:bold;color:{h_muted};">전략: {regime_info[curr_regime][1]}</p>
                </div>
                <div style="font-weight:800;margin-bottom:5px;color:{h_color};">🔍 알고리즘 해부</div>
                {render_row_std('① VIX 패닉 임계점 (< 40)',      f"{vix_close:.2f}",                      vix_close<=40)}
                {render_row_std('② 장기 지지선 (QQQ > 200MA)',    f"${qqq_close:.0f} vs ${qqq_ma200:.0f}", qqq_close>=qqq_ma200)}
                {render_row_std('③ 추세 정배열 (50MA ≥ 200MA)',   f"${qqq_ma50:.0f} vs ${qqq_ma200:.0f}",  qqq_ma50>=qqq_ma200)}
                {render_row_std('④ 노이즈 필터 (20일선 < 22)',     f"{vix_ma20:.2f}",                       vix_ma20<22)}
                <div style="margin-top:auto;padding:15px;font-size:0.85em;color:{h_muted};text-align:center;background-color:{msg_bg};border-radius:8px;">
                    💡 위원회: {regime_committee_msg}
                </div>
            </div>""", unsafe_allow_html=True)
        with c2:
            s_title = '🔥 승인: SOXL 편입' if smh_cond else '🛡️ 기각: USD 편입'
            ok_col  = '#34D399'
            st.markdown(f"""
            <div class="neo-card">
                <div style="font-size:1.4em;font-weight:bold;color:{h_color};border-bottom:2px solid {h_border};padding-bottom:10px;margin-bottom:15px;">💻 반도체(SOXL) 판독관</div>
                <div class="neo-inset-box">
                    <h2 style="margin:0;color:{ok_col if smh_cond else h_accent};">{s_title}</h2>
                    <p style="margin:5px 0 0 0;font-weight:bold;color:{h_muted};">전략: {'3배수 공격적 진입' if smh_cond else '변동성 방어용 2배수'}</p>
                </div>
                <div style="font-weight:800;margin-bottom:5px;color:{h_color};">🔍 3중 필터 해부</div>
                {render_row_std('① 정배열 추세 (SMH > 50MA)',     f"${smh_close:.1f} vs ${smh_ma50:.1f}", smh_c1)}
                {render_row_std('② 모멘텀 (1M>10% or 3M>5%)',    f"3M {smh_3m*100:.1f}%",               smh_c2)}
                {render_row_std('③ 매수 심리 강도 (RSI > 50)',    f"{smh_rsi:.1f}",                       smh_c3)}
                <div style="margin-top:auto;padding:15px;font-size:0.85em;color:{h_muted};text-align:center;border-top:1px dashed {h_border};">
                    ※ SOXL은 극단적 변동성을 수반하므로 필터 모두 통과 필수.
                </div>
            </div>""", unsafe_allow_html=True)
        with c3:
            rows = "".join([f"<div class='check-row'><span>{k}</span><span class='check-value'>{v*100:.0f}%</span></div>"
                            for k,v in target_weights.items() if v > 0])
            st.markdown(f"""
            <div class="neo-card">
                <div style="font-size:1.4em;font-weight:bold;color:{h_color};border-bottom:2px solid {h_border};padding-bottom:10px;margin-bottom:15px;">🛒 V4.5 목표 비중</div>
                <div style="display:flex;justify-content:space-between;border-bottom:1px solid {h_border};padding-bottom:5px;font-size:0.8em;font-weight:bold;color:{h_muted};">
                    <span>자산 (ASSET)</span><span>비중 (WEIGHT)</span>
                </div>
                {rows}
            </div>""", unsafe_allow_html=True)

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
        p = {'green':('rgba(16,185,129,0.15)','#059669','rgba(16,185,129,0.35)'),
             'orange':('rgba(249,115,22,0.15)','#D97706','rgba(249,115,22,0.35)'),
             'red':('rgba(239,68,68,0.15)','#DC2626','rgba(239,68,68,0.35)'),
             'blue':('rgba(37,99,235,0.12)','#2563EB','rgba(37,99,235,0.30)')}
        bg,fg,bdr = p[color]
        return f'<div class="badge" style="background:{bg};color:{fg};border:1px solid {bdr};">{icon} {label}</div>'

    b1 = _badge("매수","green","🔥") if qqq_rsi<40 else (_badge("과열","red","⚠️") if qqq_rsi>70 else _badge("적립","blue","🟢"))
    b2 = (_badge("약세(-20%)","red","🚨") if qqq_dd<-0.20 else
          (_badge("조정(-10%)","orange","⚠️") if qqq_dd<-0.10 else _badge("고점 순항","green","✅")))
    b3 = (_badge("극단 공포","green","🔥") if fg_score<30 else
          (_badge("극단 탐욕","red","⚠️") if fg_score>70 else _badge("중립","blue","🟢")))
    b4 = f'<div class="badge" style="background:rgba(37,99,235,0.12);color:#2563EB;border:1px solid rgba(37,99,235,0.3);">🏆 {top_sec} &nbsp;/&nbsp; 📉 {bot_sec}</div>'
    b5 = _badge("국채 피신","red","🚨") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _badge("회사채 선호","green","✅")
    b6 = (_badge("쏠림 심화","orange","⚠️") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0)
          else _badge("고른 상승","green","✅"))
    b7 = _badge("금 피신","orange","⚠️") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _badge("주식 선호","green","✅")
    b8 = _badge("강달러 압박","red","🚨") if last_row['UUP']>last_row['UUP_MA50'] else _badge("달러 진정","green","✅")

    gauge_steps = ([{'range':[0,25],'color':"rgba(239,68,68,0.55)"},
                    {'range':[25,45],'color':"rgba(249,115,22,0.30)"},
                    {'range':[45,55],'color':"rgba(200,210,255,0.15)"},
                    {'range':[55,75],'color':"rgba(16,185,129,0.30)"},
                    {'range':[75,100],'color':"rgba(16,185,129,0.55)"}]
                   if (is_glass_style or is_transparent_style) else
                   ([{'range':[0,25],'color':"rgba(178,106,71,0.7)"},
                     {'range':[25,45],'color':"rgba(178,106,71,0.3)"},
                     {'range':[45,55],'color':"rgba(139,94,60,0.1)"},
                     {'range':[55,75],'color':"rgba(107,142,35,0.3)"},
                     {'range':[75,100],'color':"rgba(107,142,35,0.7)"}]
                    if is_neo_style else
                    [{'range':[0,25],'color':"rgba(248,113,113,0.7)"},
                     {'range':[25,45],'color':"rgba(248,113,113,0.3)"},
                     {'range':[45,55],'color':"rgba(255,255,255,0.05)"},
                     {'range':[55,75],'color':"rgba(52,211,153,0.3)"},
                     {'range':[75,100],'color':"rgba(52,211,153,0.7)"}]))

    # Glass / Transparent: components.html 배너+뱃지
    if is_glass_style:
        cells = "".join([f'<div class="pack-cell"><div class="pack-title">{t}</div><div style="position:relative;z-index:1;">{b}</div></div>'
                         for t,b in [("1. 스마트 DCA (RSI)",b1),("2. 멘탈 방어 (Drawdown)",b2),
                                     ("3. 시장 심리 (F&amp;G)",b3),("4. 섹터 순환 (1M)",b4),
                                     ("5. 채권 스프레드",b5),("6. 시장 폭 (Breadth)",b6),
                                     ("7. 안전 자산 (금/주식)",b7),("8. 달러 (UUP)",b8)]])
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="lg-banner">
  <h4>"감정을 배제하고, 진실에 집중하십시오."</h4>
  <p>단순한 보조 지표가 아닙니다. <strong>'8-Pack 정밀 렌즈'</strong>를 통해 겉으로 평온해 보이는 시장을 3차원으로 해부합니다.</p>
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">{cells}</div>
</body></html>""", height=360, scrolling=False)

    elif is_transparent_style:
        def _tr_badge(label, color, icon):
            p = {'green':('rgba(16,185,129,0.12)','#16A34A','rgba(22,163,74,0.30)'),
                 'orange':('rgba(249,115,22,0.12)','#D97706','rgba(249,115,22,0.32)'),
                 'red':('rgba(239,68,68,0.12)','#DC2626','rgba(220,38,38,0.30)'),
                 'blue':('rgba(37,99,235,0.10)','#2563EB','rgba(37,99,235,0.28)')}
            bg,fg,bdr = p[color]
            return f'<div style="display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:10px;font-size:0.88em;font-weight:600;width:100%;justify-content:center;background:{bg};color:{fg};border:1px solid {bdr};">{icon} {label}</div>'

        tb1 = _tr_badge("매수","green","🔥") if qqq_rsi<40 else (_tr_badge("과열","red","⚠️") if qqq_rsi>70 else _tr_badge("적립","blue","🟢"))
        tb2 = (_tr_badge("약세(-20%)","red","🚨") if qqq_dd<-0.20 else (_tr_badge("조정(-10%)","orange","⚠️") if qqq_dd<-0.10 else _tr_badge("고점 순항","green","✅")))
        tb3 = (_tr_badge("극단 공포","green","🔥") if fg_score<30 else (_tr_badge("극단 탐욕","red","⚠️") if fg_score>70 else _tr_badge("중립","blue","🟢")))
        tb4 = f'<div style="display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:10px;font-size:0.88em;font-weight:600;width:100%;justify-content:center;background:rgba(37,99,235,0.10);color:#2563EB;border:1px solid rgba(37,99,235,0.28);">🏆 {top_sec} / 📉 {bot_sec}</div>'
        tb5 = _tr_badge("국채 피신","red","🚨") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _tr_badge("회사채 선호","green","✅")
        tb6 = (_tr_badge("쏠림 심화","orange","⚠️") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0) else _tr_badge("고른 상승","green","✅"))
        tb7 = _tr_badge("금 피신","orange","⚠️") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _tr_badge("주식 선호","green","✅")
        tb8 = _tr_badge("강달러 압박","red","🚨") if last_row['UUP']>last_row['UUP_MA50'] else _tr_badge("달러 진정","green","✅")
        cells_tr = "".join([f'<div style="background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:18px;padding:13px;box-shadow:0 2px 12px rgba(0,0,0,0.06);"><div style="font-size:0.81em;font-weight:700;color:#374151;margin-bottom:8px;">{t}</div>{b}</div>'
                            for t,b in [("1. 스마트 DCA (RSI)",tb1),("2. 멘탈 방어 (Drawdown)",tb2),
                                        ("3. 시장 심리 (F&amp;G)",tb3),("4. 섹터 순환 (1M)",tb4),
                                        ("5. 채권 스프레드",tb5),("6. 시장 폭 (Breadth)",tb6),
                                        ("7. 안전 자산 (금/주식)",tb7),("8. 달러 (UUP)",tb8)]])
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'DM Sans',sans-serif;background:#E8E8ED;padding:10px 6px 6px 6px;}}.banner{{background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:20px;padding:16px 22px;margin-bottom:14px;box-shadow:0 2px 16px rgba(0,0,0,0.07);}}.banner h4{{color:#2563EB;font-size:1.03em;margin-bottom:5px;font-weight:700;}}.banner p{{color:#374151;font-size:0.91em;line-height:1.6;}}</style>
</head><body>
<div class="banner"><h4>"감정을 배제하고, 진실에 집중하십시오."</h4><p>단순한 보조 지표가 아닙니다. <strong>'8-Pack 정밀 렌즈'</strong>를 통해 겉으로 평온해 보이는 시장을 3차원으로 해부합니다.</p></div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">{cells_tr}</div>
</body></html>""", height=360, scrolling=False)

    else:
        st.markdown(f"""<div class="neo-inset-box" style="text-align:left;padding:20px;">
            <h4 style="margin-top:0;color:{h_accent};">"감정을 배제하고, 진실에 집중하십시오."</h4>
            <p style="font-size:1.05em;color:{h_color};line-height:1.6;margin-bottom:0;">
                단순한 보조 지표가 아닙니다. <strong>'8-Pack 정밀 렌즈'</strong>를 통해 겉으로 평온해 보이는 시장을 3차원으로 해부합니다.</p>
        </div>""", unsafe_allow_html=True)

    # ── 차트 8개 (Glass/Transparent: 타이틀·뱃지 생략) ──────
    show_st_labels = not is_glass_style and not is_transparent_style
    row1 = st.columns(4); row2 = st.columns(4)

    with row1[0]:
        if show_st_labels:
            st.markdown("##### 1. 스마트 DCA (RSI)")
            if qqq_rsi<40: st.success("🔥 매수")
            elif qqq_rsi>70: st.error("⚠️ 과열")
            else: st.info("🟢 적립")
        fig1=go.Figure(); fig1.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_RSI'],line=dict(color=line_c,width=2)))
        fig1.add_hline(y=70,line_dash='dash',line_color=dash_c); fig1.add_hline(y=30,line_dash='dash',line_color=rsi_low_c)
        fig1.update_layout(**radar_layout,yaxis=dict(range=[10,90]),showlegend=False)
        st.plotly_chart(fig1,use_container_width=True)
    with row1[1]:
        if show_st_labels:
            st.markdown("##### 2. 멘탈 방어 (Drawdown)")
            if qqq_dd<-0.20: st.error("🚨 약세 (-20%)")
            elif qqq_dd<-0.10: st.warning("⚠️ 조정 (-10%)")
            else: st.success("✅ 고점 순항")
        fig2=go.Figure(); fig2.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_DD'],fill='tozeroy',line=dict(color=dash_c,width=2)))
        fig2.update_layout(**radar_layout,yaxis=dict(tickformat='.0%'),showlegend=False); st.plotly_chart(fig2,use_container_width=True)
    with row1[2]:
        if show_st_labels:
            st.markdown("##### 3. 시장 심리 (F&G)")
            if fg_score<30: st.success("🔥 극단 공포")
            elif fg_score>70: st.error("⚠️ 극단 탐욕")
            else: st.info("🟢 중립")
        fig3=go.Figure(go.Indicator(mode="gauge+number",value=fg_score,domain={'x':[0,1],'y':[0,1]},
            gauge={'axis':{'range':[0,100]},'bar':{'color':line_c},'steps':gauge_steps}))
        fig3.update_layout(height=200,margin=dict(l=15,r=15,t=10,b=10),paper_bgcolor=b_color,font=dict(family="Pretendard",color=t_color))
        st.plotly_chart(fig3,use_container_width=True)
    with row1[3]:
        if show_st_labels:
            st.markdown("##### 4. 섹터 순환 (1M)"); st.info(f"🏆 {top_sec} / 📉 {bot_sec}")
        fig4=go.Figure(go.Bar(x=sec_df['수익률'],y=sec_df['섹터'],orientation='h',
            marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']]))
        fig4.update_layout(**radar_layout,showlegend=False); st.plotly_chart(fig4,use_container_width=True)
    with row2[0]:
        if show_st_labels:
            st.markdown("##### 5. 채권 스프레드")
            if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50']: st.error("🚨 국채 피신")
            else: st.success("✅ 회사채 선호")
        fig5=go.Figure(); fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_Ratio'],line=dict(color=line_c,width=2)))
        fig5.add_trace(go.Scatter(x=df_view.index,y=df_view['HYG_IEF_MA50'],line=dict(color=dash_c,dash='dot')))
        fig5.update_layout(**radar_layout,showlegend=False); st.plotly_chart(fig5,use_container_width=True)
    with row2[1]:
        if show_st_labels:
            st.markdown("##### 6. 시장 폭 (Breadth)")
            if last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0: st.warning("⚠️ 쏠림 심화")
            else: st.success("✅ 고른 상승")
        fig6=go.Figure(); fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQ_20d_Ret'],name='QQQ',line=dict(color=line_c,width=2)))
        fig6.add_trace(go.Scatter(x=df_view.index,y=df_view['QQQE_20d_Ret'],name='QQQE',line=dict(color=dash_c,dash='dot')))
        fig6.update_layout(**radar_layout,showlegend=False,yaxis=dict(tickformat='.0%')); st.plotly_chart(fig6,use_container_width=True)
    with row2[2]:
        if show_st_labels:
            st.markdown("##### 7. 안전 자산 (금/주식)")
            if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50']: st.warning("⚠️ 금 피신")
            else: st.success("✅ 주식 선호")
        fig7=go.Figure(); fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_Ratio'],line=dict(color=line_c,width=2)))
        fig7.add_trace(go.Scatter(x=df_view.index,y=df_view['GLD_SPY_MA50'],line=dict(color=dash_c,dash='dot')))
        fig7.update_layout(**radar_layout,showlegend=False); st.plotly_chart(fig7,use_container_width=True)
    with row2[3]:
        if show_st_labels:
            st.markdown("##### 8. 달러 (UUP)")
            if last_row['UUP']>last_row['UUP_MA50']: st.error("🚨 강달러 압박")
            else: st.success("✅ 달러 진정")
        fig8=go.Figure(); fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP'],line=dict(color=line_c,width=2)))
        fig8.add_trace(go.Scatter(x=df_view.index,y=df_view['UUP_MA50'],line=dict(color=dash_c,dash='dot')))
        fig8.update_layout(**radar_layout,showlegend=False); st.plotly_chart(fig8,use_container_width=True)

# ------------------------------------------
# PAGE 3: 폭락장 아카이브
# ------------------------------------------
elif page == "📉 폭락장 아카이브":
    st.subheader("III. 역사적 폭락장 아카이브")
    crises = {"2008 금융위기":("2007-08-01","2009-12-31"),"2020 코로나":("2020-01-01","2020-12-31"),"2022 인플레이션":("2021-11-01","2023-03-31")}
    selected_crisis = st.selectbox("조회할 역사적 위기를 선택하십시오:", list(crises.keys()))
    s_date, e_date = crises[selected_crisis]
    try:
        df_crisis = df.loc[s_date:e_date]
        if len(df_crisis) > 0:
            crisis_fig = go.Figure()
            crisis_fig.add_trace(go.Scatter(x=df_crisis.index,y=df_crisis['QQQ'],name='QQQ',line=dict(color=t_color,width=2)))
            crisis_fig.add_trace(go.Scatter(x=df_crisis.index,y=df_crisis['QQQ_MA200'],name='200MA',line=dict(color=dash_c,width=2,dash='dash')))
            r3r4 = 0
            for i in range(1,len(df_crisis)):
                if df_crisis['Regime'].iloc[i-1]!=df_crisis['Regime'].iloc[i] or i==1:
                    start_idx=df_crisis.index[i]; curr_r=df_crisis['Regime'].iloc[i]
                if i==len(df_crisis)-1 or df_crisis['Regime'].iloc[i]!=df_crisis['Regime'].iloc[i+1]:
                    crisis_fig.add_vrect(x0=start_idx,x1=df_crisis.index[i],fillcolor=regime_colors[curr_r],opacity=1,layer="below",line_width=0)
                if df_crisis['Regime'].iloc[i] in [3,4]: r3r4+=1
            crisis_fig.update_layout(title=f"V4.5 백테스트 궤적: {selected_crisis}", height=500, **chart_layout)
            st.plotly_chart(crisis_fig, use_container_width=True)
            st.info(f"💡 총 {len(df_crisis)} 거래일 중, **{r3r4}일({r3r4/len(df_crisis)*100:.1f}%)** 동안 안전 자산으로 방어했습니다.")
    except: st.error("데이터를 불러오지 못했습니다.")

# ------------------------------------------
# PAGE 4: 매크로 뉴스룸
# ------------------------------------------
elif page == "📰 매크로 뉴스룸":
    headlines_for_ai, news_items = fetch_macro_news()

    # 헤더
    if is_glass_style:
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="lg-banner" style="display:flex;align-items:center;gap:12px;">
  <div>📰</div>
  <h4 style="font-size:1.25em;margin-bottom:0;">실시간 글로벌 매크로 뉴스 &amp; AI 브리핑</h4>
  <div class="badge-rt" style="margin-left:auto;">{rt_label}</div>
</div>
</body></html>""", height=85, scrolling=False)
    elif is_transparent_style:
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'DM Sans',sans-serif;background:#E8E8ED;padding:10px 6px 6px 6px;}}
.banner{{background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:20px;padding:16px 24px;box-shadow:0 2px 16px rgba(0,0,0,0.07);display:flex;align-items:center;gap:12px;}}
.banner h2{{font-size:1.25em;font-weight:700;color:#1C1C1E;}}
.badge-rt{{margin-left:auto;background:rgba(37,99,235,0.08);color:#2563EB;border:1px solid rgba(37,99,235,0.25);border-radius:8px;padding:4px 12px;font-size:0.8em;font-weight:600;white-space:nowrap;}}
</style></head><body>
<div class="banner"><div>📰</div><h2>실시간 글로벌 매크로 뉴스 &amp; AI 브리핑</h2><div class="badge-rt">{rt_label}</div></div>
</body></html>""", height=85, scrolling=False)
    else:
        st.subheader("IV. 실시간 글로벌 매크로 뉴스 & AI 브리핑")

    with st.expander("✨ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("🚀 심층 추론 요약 실행"):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("심층 추론 진행 중..."):
                        genai.configure(api_key=api_key)
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model  = genai.GenerativeModel(models[0].replace('models/',''))
                        prompt = "너는 1920년대 퀀트 애널리스트야. 1. 주요 뉴스 분류\n2. 잠재 리스크\n3. 최종 고찰 목차로 요약해.\n" + "\n".join(headlines_for_ai)
                        response = model.generate_content(prompt)
                        st.markdown(f"""<div style="background-color:#FFFFFF;border-radius:12px;padding:20px;box-shadow:inset 4px 4px 8px rgba(0,0,0,0.1);margin-bottom:20px;">
                            <h3 style="color:#1A1A1A;border-bottom:2px solid #1A1A1A;padding-bottom:10px;margin-top:0;">✅ 분석 완료</h3>
                            <div style="font-size:1.05em;color:#000000;">{response.text.replace(chr(10),'<br>')}</div>
                        </div>""", unsafe_allow_html=True)
                        with st.expander("📋 텍스트 복사하기"): st.code(response.text, language="markdown")
            except KeyError: st.error("🚨 Secrets에 'GEMINI_API_KEY'를 설정해주세요.")

    st.divider()

    if news_items:
        if is_glass_style:
            cards = "".join([f'<div class="ncard"><div class="ntitle"><a href="{i["link"]}" target="_blank">{i["title"].replace("&","&amp;")}</a></div><div class="ndate">{i["date"]}</div></div>'
                             for i in news_items])
            components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="section-title">🖼️ 최신 경제 헤드라인 갤러리</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">{cards}</div>
</body></html>""", height=160+(len(news_items)//3)*155, scrolling=False)

        elif is_transparent_style:
            cards_tr = "".join([f"""<div style="background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:18px;padding:15px;height:140px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 2px 12px rgba(0,0,0,0.06);transition:transform 0.2s,box-shadow 0.2s;">
  <div style="font-size:0.89em;font-weight:600;line-height:1.44;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;"><a href="{i['link']}" target="_blank" style="color:#1C1C1E;text-decoration:none;">{i['title'].replace('&','&amp;')}</a></div>
  <div style="font-size:0.77em;font-weight:600;color:#2563EB;margin-top:8px;">{i['date']}</div>
</div>""" for i in news_items])
            components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'DM Sans',sans-serif;background:#E8E8ED;padding:10px 6px 10px 6px;}}
.title{{font-size:1.03em;font-weight:700;color:#1C1C1E;margin-bottom:12px;padding-left:2px;}}</style>
</head><body>
<div class="title">🖼️ 최신 경제 헤드라인 갤러리</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">{cards_tr}</div>
</body></html>""", height=160+(len(news_items)//3)*155, scrolling=False)

        else:
            st.markdown("#### 🖼️ 최신 경제 헤드라인 갤러리")
            cols = st.columns(3)
            c_bg  = '#FFFDF7' if is_neo_style else '#1C1F28'
            c_brd = 'none'    if is_neo_style else '1px solid rgba(255,255,255,0.05)'
            c_shd = 'var(--shadow-raised)' if is_neo_style else 'none'
            c_txt = 'var(--text-main)'     if is_neo_style else '#A0AEC0'
            for idx,item in enumerate(news_items):
                with cols[idx%3]:
                    st.markdown(f"""<div style="background:{c_bg};border:{c_brd};padding:15px;margin-bottom:15px;border-radius:16px;height:140px;box-shadow:{c_shd};display:flex;flex-direction:column;justify-content:space-between;">
                        <div style="font-weight:bold;font-size:1.05em;line-height:1.4;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">
                            <a href="{item['link']}" target="_blank" style="color:{c_txt};text-decoration:none;">{item['title']}</a></div>
                        <div style="color:{h_accent};font-size:0.85em;margin-top:10px;font-weight:bold;">{item['date']}</div>
                    </div>""", unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다. (15분 후 갱신)")
