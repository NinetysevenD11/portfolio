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

st.set_page_config(page_title="AMLS V4.5 FINANCE STRATEGY", layout="wide", page_icon="📈", initial_sidebar_state="expanded")

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
                for k, v in loaded.items(): st.session_state.portfolio[k] = v
        except: pass
sanitize_portfolio()

def save_portfolio_to_disk():
    try:
        with open(PORTFOLIO_FILE, 'w') as f: json.dump(st.session_state.portfolio, f)
    except: pass

@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.now(); start_date = end_date - timedelta(days=900)
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)['Close']
    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]
    df = df.ffill().bfill()
    df['QQQ_MA20'] = df['QQQ'].rolling(20).mean(); df['QQQ_MA50'] = df['QQQ'].rolling(50).mean(); df['QQQ_MA200'] = df['QQQ'].rolling(200).mean()
    df['TQQQ_MA200'] = df['TQQQ'].rolling(200).mean(); df['SMH_MA50'] = df['SMH'].rolling(50).mean()
    df['VIX_MA5'] = df['^VIX'].rolling(5).mean(); df['VIX_MA20'] = df['^VIX'].rolling(20).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(63); df['SMH_1M_Ret'] = df['SMH'].pct_change(21); df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    df['HYG_IEF_Ratio'] = df['HYG'] / df['IEF']; df['HYG_IEF_MA20'] = df['HYG_IEF_Ratio'].rolling(20).mean(); df['HYG_IEF_MA50'] = df['HYG_IEF_Ratio'].rolling(50).mean()
    df['QQQ_20d_Ret'] = df['QQQ'].pct_change(20); df['QQQE_20d_Ret'] = df['QQQE'].pct_change(20); df['QQQ_RSI'] = ta.rsi(df['QQQ'], length=14)
    df['GLD_SPY_Ratio'] = df['GLD'] / df['SPY']; df['GLD_SPY_MA50'] = df['GLD_SPY_Ratio'].rolling(50).mean()
    df['QQQ_High52'] = df['QQQ'].rolling(252).max(); df['QQQ_DD'] = (df['QQQ'] / df['QQQ_High52']) - 1; df['UUP_MA50'] = df['UUP'].rolling(50).mean()
    for sec in SECTOR_TICKERS: df[f'{sec}_1M'] = df[sec].pct_change(21)
    return df.dropna()

REALTIME_TICKERS = ['QQQ','TQQQ','SMH','^VIX','HYG','IEF','UUP','GLD','SPY','SOXL','USD','QLD','SSO','USDKRW=X']
@st.cache_data(ttl=60)
def fetch_realtime_prices():
    prices = {}
    for ticker in REALTIME_TICKERS:
        try:
            info = yf.Ticker(ticker).fast_info; price = info.get('last_price') or info.get('lastPrice')
            if price and price > 0: prices[ticker] = float(price)
        except: pass
    return prices

@st.cache_data(ttl=900)
def fetch_macro_news():
    headlines_for_ai, news_items = [], []
    try:
        search_query = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(urllib.request.urlopen(req).read())
        for item in root.findall('.//item')[:12]:
            t, l, d = item.find('title').text, item.find('link').text, item.find('pubDate').text
            headlines_for_ai.append(t); news_items.append({"title":t,"link":l,"date":d[:-4]})
    except: pass
    return headlines_for_ai, news_items

with st.spinner('데이터 수집 중...'):
    df = load_data(); rt_prices = fetch_realtime_prices()

if df is None or df.empty:
    st.error("🚨 야후 파이낸스 서버 통신이 지연되어 데이터를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.")
    st.stop()

last_row = df.iloc[-1].copy(); rt_injected = []
for ticker, price in rt_prices.items():
    if ticker in last_row.index and price > 0: last_row[ticker] = price; rt_injected.append(ticker)
if 'QQQ' in rt_injected: last_row['QQQ_DD'] = (last_row['QQQ'] / last_row['QQQ_High52']) - 1
if 'HYG' in rt_injected and 'IEF' in rt_injected: last_row['HYG_IEF_Ratio'] = last_row['HYG'] / last_row['IEF']
rt_ok = len(rt_injected) >= 3; rt_label = f"LIVE ({len(rt_injected)})" if rt_ok else "DELAYED"

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
    low_vix = row['VIX_MA20'] < 22
    credit_ok = row['HYG_IEF_Ratio'] >= row['HYG_IEF_MA50']
    if bull_trend and low_vix and credit_ok: return 1
    return 2

df['Target'] = df.apply(get_target_v45, axis=1)
df['Regime'] = apply_asymmetric_delay(df['Target'])
live_regime = get_target_v45(last_row)
hist_regime = int(df.iloc[-1]['Regime'])
curr_regime = live_regime if live_regime > hist_regime else hist_regime
target_regime = live_regime

smh_c1 = smh_close > smh_ma50
smh_c2 = (smh_3m > 0.05 or smh_1m > 0.10)
smh_c3 = smh_rsi > 50
smh_cond = smh_c1 and smh_c2 and smh_c3

def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in ASSET_LIST}; semi = 'SOXL' if smh_ok else 'USD'
    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2: w['TQQQ'], w['QLD'], w['SSO'], w['USD'], w['GLD'], w['SPY'] = 0.15, 0.30, 0.25, 0.10, 0.15, 0.05
    elif reg == 3: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w
target_weights = get_weights_v45(curr_regime, smh_cond)

if curr_regime == live_regime: regime_committee_msg = "모든 조건이 현재 국면에 부합합니다."
elif live_regime > curr_regime: regime_committee_msg = f"R{live_regime} 하향 즉시 반영 중입니다."
else: regime_committee_msg = f"R{live_regime} 신호 감지 — 5일 확인 대기 중"

# ★ Aether 테마 색상
b_color, t_color = 'rgba(0,0,0,0)', '#2D3436'
line_c, dash_c = '#6C5CE7', '#FDA7DF'
rsi_low_c = '#00B894'
regime_colors = {1:'rgba(0,0,0,0.0)', 2:'rgba(108,92,231,0.04)', 3:'rgba(253,167,223,0.06)', 4:'rgba(255,118,117,0.08)'}
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color), margin=dict(l=0,r=0,t=40,b=0))
radar_layout = dict(height=200, margin=dict(l=10,r=10,t=15,b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
regime_info = {1:("🟢 R1 (강세장)","풀 가동"), 2:("🟡 R2 (조정장)","TQQQ 15% 방어"), 3:("🟠 R3 (하락장)","현금/금 대피"), 4:("🔴 R4 (패닉장)","최대 방어")}

# ==========================================
# 2. Aether CSS
# ==========================================
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&family=Outfit:wght@400;600;800&display=swap');
    :root { --text-main: #2D3436; --text-muted: #636E72; --accent: #6C5CE7; }
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #F0EEFF !important;
        background-image: radial-gradient(circle at 15% 25%, rgba(108,92,231,0.12) 0%, transparent 50%),
            radial-gradient(circle at 85% 75%, rgba(253,167,223,0.10) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(116,185,255,0.06) 0%, transparent 60%) !important;
        background-attachment: fixed !important; color: var(--text-main) !important; font-family: 'Pretendard', sans-serif;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; }
    .main .block-container { max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem; }
    [data-testid="stSidebar"] { background: rgba(255,255,255,0.75) !important; backdrop-filter: blur(30px) !important; border-right: 1px solid rgba(108,92,231,0.08) !important; }
    div.row-widget.stRadio > div { gap: 6px; }
    div.row-widget.stRadio > div > label { background: transparent !important; border: none !important; border-radius: 12px !important; padding: 10px 16px !important; box-shadow: none !important; transition: all 0.2s ease !important; }
    div.row-widget.stRadio > div > label p { font-size: 0.88em !important; font-weight: 600 !important; color: var(--text-muted) !important; }
    div.row-widget.stRadio > div > label:hover { background: rgba(108,92,231,0.06) !important; }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) { background: #2D3436 !important; border-radius: 12px !important; box-shadow: 0 2px 8px rgba(45,52,54,0.15) !important; border: none !important; }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) p { color: #FFFFFF !important; font-weight: 700 !important; }
    .glass-card { position: relative; background: #FFFFFF !important; backdrop-filter: none !important; border: 1px solid rgba(108,92,231,0.06) !important; border-radius: 24px !important; padding: 25px !important; box-shadow: 0 4px 24px rgba(108,92,231,0.06), 0 1px 4px rgba(0,0,0,0.02) !important; overflow: hidden; transition: all 0.25s ease; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .glass-card:hover { transform: translateY(-2px); box-shadow: 0 12px 36px rgba(108,92,231,0.10), 0 2px 8px rgba(0,0,0,0.03) !important; }
    .glass-card h3 { font-size: 1em !important; font-weight: 700 !important; margin-bottom: 14px !important; color: var(--text-muted); letter-spacing: -0.3px; border-bottom: none; padding-bottom: 0; }
    .glass-inset { background: linear-gradient(135deg, #FFF5EE 0%, #FFF0E6 100%) !important; border-radius: 16px !important; padding: 18px; text-align: center; box-shadow: none !important; border: 1px solid rgba(253,167,121,0.12); }
    h1 { font-family: 'Outfit'; font-size: 2.4em !important; letter-spacing: -1.5px; margin: 0 !important; color: #2D3436; }
    .crow { display: flex; justify-content: space-between; padding: 11px 0; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 0.88em; }
    .clabel { color: #636E72; font-weight: 600; } .cval { font-family: 'Outfit'; font-weight: 800; color: #6C5CE7; }
    [data-testid="stMetric"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 10px 5px !important; }
    [data-testid="stMetricLabel"] > div > div > p { font-size: 0.85em !important; font-weight: 700; color: #636E72 !important; }
    [data-testid="stMetricValue"] > div { font-size: 1.3em !important; font-weight: 800; color: #2D3436 !important; }
    div[data-testid="stMetricDelta"] > div { font-size: 0.85em !important; font-weight: 700; }
    .stButton > button { background: #6C5CE7 !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; font-weight: 700 !important; padding: 8px 24px !important; box-shadow: 0 4px 12px rgba(108,92,231,0.25) !important; transition: all 0.2s !important; }
    .stButton > button:hover { background: #5A4BD1 !important; box-shadow: 0 6px 20px rgba(108,92,231,0.35) !important; transform: translateY(-1px) !important; }
    [data-testid="stExpander"] { background: #FFFFFF !important; border: 1px solid rgba(108,92,231,0.06) !important; border-radius: 20px !important; box-shadow: 0 4px 24px rgba(108,92,231,0.06) !important; }
</style>""", unsafe_allow_html=True)

LG_CSS_BASE = """<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&family=Outfit:wght@400;600;800&display=swap');
* { margin:0; padding:0; box-sizing:border-box; }
body { background: transparent; font-family: 'Pretendard', 'Outfit', sans-serif; color: #2D3436; padding: 10px; }
.glass-card { background: #FFFFFF; border: 1px solid rgba(108,92,231,0.06); border-radius: 24px; padding: 28px; box-shadow: 0 4px 24px rgba(108,92,231,0.06); height: 580px; display: flex; flex-direction: column; transition: transform 0.25s, box-shadow 0.25s; }
.glass-card:hover { transform: translateY(-2px); box-shadow: 0 12px 36px rgba(108,92,231,0.10); }
.glass-inset { background: linear-gradient(135deg, #FFF5EE 0%, #FFF0E6 100%); border-radius: 16px; box-shadow: none; padding: 20px; margin-bottom: 20px; text-align: center; border: 1px solid rgba(253,167,121,0.10); }
h2, h3, h4 { color: #2D3436; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; font-family: 'Outfit'; }
.crow { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 0.92em; }
.clabel { color: #636E72; font-weight: 600; } .cval { font-family: 'Outfit', monospace; font-weight: 800; color: #6C5CE7; font-size: 1.05em; }
.weight-header { display: flex; justify-content: space-between; font-size: 0.78em; font-weight: 800; color: #B2BEC3; border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 10px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
.footer-msg { margin-top: auto; padding: 14px; font-size: 0.88em; text-align: center; border-radius: 14px; background: rgba(108,92,231,0.05); color: #6C5CE7; font-weight: 700; }
</style>"""

# ==========================================
# 3. 사이드바
# ==========================================
sidebar_top = st.sidebar.container()
sidebar_top.markdown(f"""
<div style="padding: 10px 10px 20px 10px;">
    <div style="font-family: 'Outfit'; font-size: 1.8em; font-weight: 800; background: linear-gradient(135deg, #6C5CE7 0%, #FDA7DF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AMLS V4.5</div>
    <div style="font-family: 'Outfit'; font-size: 0.85em; font-weight: 700; color: #2D3436; margin-bottom: 12px; letter-spacing: 0.5px;">FINANCE ENGINE</div>
    <div style="font-size: 0.75em; color: #6C5CE7; font-weight: 800; padding: 4px 10px; background: rgba(108,92,231,0.08); border-radius: 50px; display: inline-block; border: 1px solid rgba(108,92,231,0.15);">{rt_label}</div>
</div>""", unsafe_allow_html=True)

page = st.sidebar.radio("MENU",
    ["📊 시장 분석관 (Home)", "💼 내 포트폴리오", "🍫 8-Pack 레이더망", "📈 백테스트 랩", "📰 매크로 뉴스룸"],
    label_visibility="collapsed")

st.sidebar.markdown(f"""
<div style="margin-top: 30px; padding: 15px; border-radius: 18px; background: rgba(255,255,255,0.5); border: 1px solid rgba(108,92,231,0.06);">
    <div style="font-family: 'Outfit'; font-size:0.7em; font-weight:800; color:#6C5CE7; text-transform: uppercase;">Powered by Apex</div>
    <div style="font-size:0.75em; font-weight:700; color:#636E72; margin-top: 4px;">Aether Edition v4.5<br>&copy; 2026 SEYOON.</div>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="padding-bottom:15px; margin-bottom:30px; display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 1px solid rgba(108,92,231,0.08);">
    <div>
        <h1 style="color:#2D3436;">AMLS V4.5 ENGINE</h1>
        <p style="font-size:1em; letter-spacing:0.5px; margin:4px 0 0 0; font-weight:800; color:#6C5CE7;">THE WALL STREET QUANTITATIVE STRATEGY</p>
    </div>
    <div style="text-align:right; font-weight:bold;">
        <div style="font-family:'Outfit'; font-size:1em; color:#2D3436;">AETHER EDITION</div>
        <div style="font-size:0.8em; margin-top:6px; color:#6C5CE7; background: rgba(108,92,231,0.08); padding: 5px 12px; border-radius: 50px; display: inline-block;">{rt_label}</div>
    </div>
</div>""", unsafe_allow_html=True)

# ==========================================
# 5. 페이지 라우팅
# ==========================================
if page == "📊 시장 분석관 (Home)":
    def _lg_row(label, val, passed):
        icon = "✔" if passed else "✕"; color = "#00B894" if passed else "#EF4444"
        return f'<div class="crow"><span class="clabel">{label}</span><span class="cval" style="color:{color};">{val} {icon}</span></div>'

    soxl_title = "🔥 승인: SOXL" if smh_cond else "🛡️ 기각: USD"
    soxl_strat = "3배수 공격적 진입" if smh_cond else "변동성 방어용 2배수"
    soxl_color = "#00B894" if smh_cond else "#6C5CE7"
    weight_rows = "".join([f'<div class="crow"><span class="clabel">{k}</span><span class="cval" style="color:#6C5CE7;">{v*100:.0f}%</span></div>' for k,v in target_weights.items() if v > 0])

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.markdown(f"""<div class="glass-card">
            <h3>🏛️ 시장 국면 분석</h3>
            <div class="glass-inset">
                <div style="color:#6C5CE7; font-size:1.6em; font-weight:800;">{regime_info[curr_regime][0]}</div>
                <div style="font-weight:700; color:#636E72; font-size:0.9em; margin-top:4px;">{regime_info[curr_regime][1]}</div>
            </div>
            {_lg_row('① VIX 임계점 (< 40)', f'{vix_close:.2f}', vix_close<=40)}
            {_lg_row('② 지지선 (QQQ > 200MA)', f'${qqq_close:.0f}', qqq_close>=qqq_ma200)}
            {_lg_row('③ 추세 (50MA ≥ 200MA)', f'${qqq_ma50:.0f}', qqq_ma50>=qqq_ma200)}
            <div style="margin-top:auto; padding:10px; font-size:0.8em; text-align:center; border-radius:12px; background:rgba(108,92,231,0.05); color:#6C5CE7; font-weight:700;">💡 {regime_committee_msg}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="glass-card">
            <h3>💻 반도체(SOXL) 판독관</h3>
            <div class="glass-inset">
                <div style="color:{soxl_color}; font-size:1.6em; font-weight:800;">{soxl_title}</div>
                <div style="font-weight:700; color:#636E72; font-size:0.9em; margin-top:4px;">{soxl_strat}</div>
            </div>
            {_lg_row('① 추세 (SMH > 50MA)', f'${smh_close:.1f}', smh_c1)}
            {_lg_row('② 모멘텀 (1M > 10%)', f'{smh_1m*100:.1f}%', smh_c2)}
            {_lg_row('③ 매수심리 (RSI > 50)', f'{smh_rsi:.1f}', smh_c3)}
            <div style="margin-top:auto; padding:10px; font-size:0.8em; text-align:center; color:#636E72; font-weight:600; border-top:1px dashed rgba(0,0,0,0.05);">※ 필터 통과 시에만 SOXL 편입</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="glass-card">
            <h3>🛒 포트폴리오 비중</h3>
            <div style="display:flex; justify-content:space-between; font-size:0.75em; font-weight:800; color:#B2BEC3; border-bottom:1px solid rgba(0,0,0,0.05); padding-bottom:8px; margin-bottom:5px;"><span>ASSET</span><span>WEIGHT</span></div>
            {weight_rows}
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("QQQ vs 200MA", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200MA", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (20D MA)", f"{last_row['VIX_MA20']:.2f}", f"NOW:{last_row['^VIX']:.2f}")
    m4.metric("반도체 1M", f"{last_row['SMH_1M_Ret']*100:+.1f}%", f"vs MA50: {(last_row['SMH']/last_row['SMH_MA50']-1)*100:+.1f}%")
    m5.metric("반도체 RSI", f"{last_row['SMH_RSI']:.1f}", "Condition: 50")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    df_recent = df.iloc[-500:]
    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color=line_c, width=2)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_qqq.update_layout(title=dict(text="[시스템 기준] QQQ vs 200일선", font=dict(size=16, color="#2D3436")), height=350, **chart_layout)
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color=line_c, width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200MA', line=dict(color=dash_c, width=1.5, dash='dash')))
    fig_tqqq.update_layout(title=dict(text="[조기 경보] TQQQ vs 200일선", font=dict(size=16, color="#2D3436")), height=350, **chart_layout)
    with chart_col1:
        st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
        st.plotly_chart(fig_qqq, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
    with chart_col2:
        st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
        st.plotly_chart(fig_tqqq, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

elif page == "💼 내 포트폴리오":
    st.markdown("<h2 style='font-family:Outfit; font-size:2em;'>💼 내 포트폴리오</h2>", unsafe_allow_html=True)
    col_up, col_down = st.columns(2)
    with col_up:
        uploaded_file = st.file_uploader("📂 포트폴리오 복구 (JSON)", type="json")
        if uploaded_file is not None:
            try: data = json.load(uploaded_file); st.session_state.portfolio.update(data); sanitize_portfolio(); save_portfolio_to_disk(); st.success("복구 완료!")
            except: st.error("파일 형식 오류")
    with col_down:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("💾 백업 다운로드", data=json.dumps(st.session_state.portfolio), file_name="portfolio_backup.json", mime="application/json", use_container_width=True)
    st.divider()
    st.markdown("#### 📥 포트폴리오 자산 입력")
    editor_data = []
    for asset in ASSET_LIST:
        val = st.session_state.portfolio.get(asset, {})
        editor_data.append({"자산": asset, "수량": float(val.get('shares', 0.0)), "매수단가($)": float(val.get('avg_price', 1.0 if asset == 'CASH' else 0.0)), "매입환율(₩)": float(val.get('fx', 1350.0))})
    df_editor = pd.DataFrame(editor_data)
    st.markdown('<div class="glass-card" style="height: auto !important; padding: 25px !important;">', unsafe_allow_html=True)
    edited_df = st.data_editor(df_editor, disabled=["자산"], hide_index=True, use_container_width=True,
        column_config={"수량": st.column_config.NumberColumn("보유 수량", min_value=0.0, format="%.4f"), "매수단가($)": st.column_config.NumberColumn("매수단가 ($)", min_value=0.0, format="%.2f"), "매입환율(₩)": st.column_config.NumberColumn("매입환율 (₩)", min_value=0.0, format="%.2f")})
    st.markdown('</div>', unsafe_allow_html=True)
    for _, row in edited_df.iterrows():
        st.session_state.portfolio[row["자산"]] = {'shares': float(row["수량"]), 'avg_price': float(row["매수단가($)"]), 'fx': float(row["매입환율(₩)"])}
    save_portfolio_to_disk()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### ⚖️ 포트폴리오 현황 및 리밸런싱 액션")

    # ★ NaN 방어 패치 적용
    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH':
            current_prices[t] = 1.0
        else:
            p = rt_prices.get(t)
            if p is not None and p == p and p > 0:
                current_prices[t] = float(p)
            elif t in df.columns:
                p2 = df[t].iloc[-1]
                current_prices[t] = float(p2) if (p2 is not None and p2 == p2 and p2 > 0) else 0.0
            else:
                current_prices[t] = 0.0

    cur_fx = rt_prices.get('USDKRW=X', 1350.0)
    if cur_fx is None or cur_fx != cur_fx or cur_fx <= 0: cur_fx = 1350.0

    curr_vals = {}
    for a in ASSET_LIST:
        shares = float(st.session_state.portfolio[a].get('shares', 0) or 0)
        price = float(current_prices.get(a, 0) or 0)
        val = shares * price
        curr_vals[a] = val if val == val else 0.0
    total_val_usd = sum(curr_vals.values())

    st.metric("총 자산 규모", f"${total_val_usd:,.2f}", f"환율: ₩{cur_fx:,.2f}")

    if total_val_usd > 0:
        c_green, c_red = "#00B894", "#EF4444"
        pie_layout = dict(margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit, Pretendard", color="#2D3436", size=14))
        diff_vals = {a: (total_val_usd * target_weights.get(a, 0.0)) - curr_vals[a] for a in ASSET_LIST}

        chart_c1, chart_c2, chart_c3 = st.columns([1, 1, 1.5])
        labels_cur = [a for a in ASSET_LIST if curr_vals[a] > 0]; vals_cur = [curr_vals[a] for a in labels_cur]
        if sum(vals_cur) > 0:
            fig_cur = go.Figure(data=[go.Pie(labels=labels_cur, values=vals_cur, hole=.4, textinfo='label+percent')])
            fig_cur.update_layout(title=dict(text="현재 비중", font=dict(size=18, color="#2D3436")), **pie_layout)
            with chart_c1:
                st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
                st.plotly_chart(fig_cur, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

        labels_tgt = [a for a in ASSET_LIST if target_weights.get(a, 0) > 0]; vals_tgt = [target_weights.get(a, 0) for a in labels_tgt]
        fig_tgt = go.Figure(data=[go.Pie(labels=labels_tgt, values=vals_tgt, hole=.4, textinfo='label+percent')])
        fig_tgt.update_layout(title=dict(text=f"목표 비중 (R{curr_regime})", font=dict(size=18, color="#2D3436")), **pie_layout)
        with chart_c2:
            st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
            st.plotly_chart(fig_tgt, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

        diff_labels = [a for a in ASSET_LIST if abs(diff_vals[a]) >= 1.0]; diff_values = [diff_vals[a] for a in diff_labels]
        if diff_labels:
            diff_colors = [c_green if v > 0 else c_red for v in diff_values]
            fig_bar = go.Figure(data=[go.Bar(x=diff_labels, y=diff_values, marker_color=diff_colors, text=[f"${v:,.0f}" for v in diff_values], textposition='auto')])
            fig_bar.update_layout(title=dict(text="리밸런싱 필요 금액 ($)", font=dict(size=18, color="#2D3436")), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit", color="#2D3436"), margin=dict(t=50,b=20,l=20,r=20))
            with chart_c3:
                st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<h4 style='color:#2D3436; margin-top:20px;'>📝 요약 주문서</h4>", unsafe_allow_html=True)
        summary_html = "<div class='glass-card' style='height:auto !important; flex-direction:row; gap:30px; color:#2D3436; padding:30px !important;'>"
        sell_text = "<div style='flex:1;'><strong style='font-size:1.3em; font-family:Outfit; color:#EF4444;'>🔴 SELL ORDER</strong><br><br>"
        buy_text = "<div style='flex:1;'><strong style='font-size:1.3em; font-family:Outfit; color:#00B894;'>🟢 BUY ORDER</strong><br><br>"
        has_sell, has_buy = False, False
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0; diff = diff_vals[asset]
            if asset != 'CASH' and diff < -cur_p * 0.05:
                sell_text += f"<div style='margin-bottom:12px; font-size:1.15em;'><span style='display:inline-block; width:70px; font-weight:800; color:#6C5CE7;'>{asset}</span> <span style='color:#EF4444; font-weight:800; background:rgba(255,255,255,0.6); padding:4px 12px; border-radius:8px;'>{abs(diff)/cur_p:,.2f}주</span> 매도 <span style='color:#636E72; font-size:0.85em;'>(약 ${abs(diff):,.0f})</span></div>"; has_sell = True
            elif asset == 'CASH' and diff < -1.0:
                sell_text += f"<div style='margin-bottom:12px; font-size:1.15em;'><span style='display:inline-block; width:70px; font-weight:800; color:#6C5CE7;'>현금</span> <span style='color:#EF4444; font-weight:800;'>${abs(diff):,.0f}</span> 투자에 사용</div>"; has_sell = True
        for asset in ASSET_LIST:
            cur_p = current_prices[asset] if current_prices[asset] > 0 else 1.0; diff = diff_vals[asset]
            if asset != 'CASH' and diff > cur_p * 0.05:
                buy_text += f"<div style='margin-bottom:12px; font-size:1.15em;'><span style='display:inline-block; width:70px; font-weight:800; color:#6C5CE7;'>{asset}</span> <span style='color:#00B894; font-weight:800; background:rgba(255,255,255,0.6); padding:4px 12px; border-radius:8px;'>{diff/cur_p:,.2f}주</span> 매수 <span style='color:#636E72; font-size:0.85em;'>(약 ${diff:,.0f})</span></div>"; has_buy = True
            elif asset == 'CASH' and diff > 1.0:
                buy_text += f"<div style='margin-bottom:12px; font-size:1.15em;'><span style='display:inline-block; width:70px; font-weight:800; color:#6C5CE7;'>현금</span> <span style='color:#00B894; font-weight:800;'>${diff:,.0f}</span> 현금 확보</div>"; has_buy = True
        if not has_sell: sell_text += "<span style='color:#636E72; font-weight:600;'>필요한 매도 주문이 없습니다.</span>"
        if not has_buy: buy_text += "<span style='color:#636E72; font-weight:600;'>필요한 매수 주문이 없습니다.</span>"
        summary_html += sell_text + "</div>" + buy_text + "</div></div>"
        st.markdown(summary_html, unsafe_allow_html=True)
    else:
        st.info("👈 위 표에 보유 중인 자산의 수량과 단가를 1개 이상 입력하시면, 시각화 차트와 상세 리밸런싱 지침이 이 자리에 나타납니다.")

elif page == "🍫 8-Pack 레이더망":
    df_view = df.iloc[-120:]; qqq_rsi = last_row['QQQ_RSI']; qqq_dd = last_row['QQQ_DD']
    vix_score = max(0, min(100, 100-(last_row['^VIX']-12)/28*100)); dd_score = max(0, min(100, (qqq_dd+0.20)/0.20*100)); rsi_score = max(0, min(100, qqq_rsi))
    fg_score = (vix_score+dd_score+rsi_score)/3
    sec_names = {'XLK':'기술','XLV':'헬스','XLF':'금융','XLY':'소비','XLC':'통신','XLI':'산업','XLP':'필수','XLE':'에너지','XLU':'유틸','XLRE':'부동산','XLB':'소재'}
    sec_data = [{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
    sec_df = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
    top_sec, bot_sec = sec_df.iloc[-1]['섹터'], sec_df.iloc[0]['섹터']

    def _badge(label, color, icon):
        p = {'green':('rgba(0,184,148,0.12)','#00B894'), 'orange':('rgba(253,167,223,0.15)','#E17055'), 'red':('rgba(239,68,68,0.12)','#EF4444'), 'blue':('rgba(108,92,231,0.12)','#6C5CE7')}
        bg,fg = p[color]
        return f'<div style="background:{bg}; color:{fg}; border:1px solid rgba(255,255,255,0.9); border-radius:50px; padding:8px 18px; font-size:0.9em; font-weight:800; display:inline-flex; align-items:center; justify-content:center; width:100%;">{icon} {label}</div>'

    b1 = _badge("매수","green","🔥") if qqq_rsi<40 else (_badge("과열","red","⚠️") if qqq_rsi>70 else _badge("적립","blue","🟢"))
    b2 = _badge("약세(-20%)","red","🚨") if qqq_dd<-0.20 else (_badge("조정(-10%)","orange","⚠️") if qqq_dd<-0.10 else _badge("고점 순항","green","✅"))
    b3 = _badge("극단 공포","green","🔥") if fg_score<30 else (_badge("극단 탐욕","red","⚠️") if fg_score>70 else _badge("중립","blue","🟢"))
    b4 = f'<div style="background:rgba(108,92,231,0.12); color:#6C5CE7; border-radius:50px; padding:8px 18px; font-size:0.9em; font-weight:800; display:inline-flex; align-items:center; justify-content:center; width:100%;">🏆 {top_sec} / 📉 {bot_sec}</div>'
    b5 = _badge("국채 피신","red","🚨") if last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'] else _badge("회사채 선호","green","✅")
    b6 = _badge("쏠림 심화","orange","⚠️") if (last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0) else _badge("고른 상승","green","✅")
    b7 = _badge("금 피신","orange","⚠️") if last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'] else _badge("주식 선호","green","✅")
    b8 = _badge("강달러 압박","red","🚨") if last_row['UUP']>last_row['UUP_MA50'] else _badge("달러 진정","green","✅")
    gauge_steps = [{'range':[0,25],'color':"rgba(239,68,68,0.5)"}, {'range':[25,45],'color':"rgba(253,167,223,0.3)"}, {'range':[45,55],'color':"rgba(255,255,255,0.4)"}, {'range':[55,75],'color':"rgba(0,184,148,0.3)"}, {'range':[75,100],'color':"rgba(0,184,148,0.5)"}]

    st.markdown(f"""<div class="glass-card" style="height:auto !important; margin-bottom:25px; padding:30px !important;">
      <h3 style="color:#6C5CE7; margin-bottom:8px;">"감정을 배제하고, 진실에 집중하십시오."</h3>
      <p style="color:#2D3436; font-weight:600; font-size:1.1em; margin:0;">'8-Pack 정밀 렌즈'를 통해 겉으로 평온해 보이는 시장을 3차원으로 해부합니다.</p>
    </div>""", unsafe_allow_html=True)

    row1 = st.columns(4)
    items_r1 = [("1. 스마트 DCA (RSI)", b1, 'QQQ_RSI', 'line', [70,30]),
                ("2. 멘탈 방어 (DD)", b2, 'QQQ_DD', 'fill', None),
                ("3. 시장 심리 (F&G)", b3, None, 'gauge', None),
                ("4. 섹터 순환 (1M)", b4, None, 'bar', None)]
    for idx, (title, badge, col_name, chart_type, hlines) in enumerate(items_r1):
        with row1[idx]:
            st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:20px;"><div class="glass-inset" style="margin-bottom:10px; padding:15px;"><div style="font-size:0.85em; font-weight:800; color:#2D3436; margin-bottom:10px;">{title}</div>{badge}</div>', unsafe_allow_html=True)
            if chart_type == 'line':
                fig = go.Figure(); fig.add_trace(go.Scatter(x=df_view.index, y=df_view[col_name], line=dict(color=line_c, width=2)))
                if hlines:
                    fig.add_hline(y=hlines[0], line_dash='dash', line_color=dash_c); fig.add_hline(y=hlines[1], line_dash='dash', line_color=rsi_low_c)
                fig.update_layout(**radar_layout, yaxis=dict(range=[10,90]), showlegend=False)
            elif chart_type == 'fill':
                fig = go.Figure(); fig.add_trace(go.Scatter(x=df_view.index, y=df_view[col_name], fill='tozeroy', line=dict(color=dash_c, width=2)))
                fig.update_layout(**radar_layout, yaxis=dict(tickformat='.0%'), showlegend=False)
            elif chart_type == 'gauge':
                fig = go.Figure(go.Indicator(mode="gauge+number", value=fg_score, domain={'x':[0,1],'y':[0,1]}, gauge={'axis':{'range':[0,100]}, 'bar':{'color':line_c}, 'steps':gauge_steps}))
                fig.update_layout(height=200, margin=dict(l=15,r=15,t=10,b=10), paper_bgcolor=b_color, font=dict(family="Outfit", color=t_color))
            elif chart_type == 'bar':
                fig = go.Figure(go.Bar(x=sec_df['수익률'], y=sec_df['섹터'], orientation='h', marker_color=[dash_c if v<0 else line_c for v in sec_df['수익률']]))
                fig.update_layout(**radar_layout, showlegend=False)
            st.plotly_chart(fig, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

    row2 = st.columns(4)
    items_r2 = [("5. 채권 스프레드", b5, [('HYG_IEF_Ratio',line_c,None),('HYG_IEF_MA50',dash_c,'dot')]),
                ("6. 시장 폭 (Breadth)", b6, [('QQQ_20d_Ret',line_c,None),('QQQE_20d_Ret',dash_c,'dot')]),
                ("7. 안전 자산 (금/주식)", b7, [('GLD_SPY_Ratio',line_c,None),('GLD_SPY_MA50',dash_c,'dot')]),
                ("8. 달러 (UUP)", b8, [('UUP',line_c,None),('UUP_MA50',dash_c,'dot')])]
    for idx, (title, badge, traces) in enumerate(items_r2):
        with row2[idx]:
            st.markdown(f'<div class="glass-card" style="height:auto !important; padding:15px !important; margin-bottom:20px;"><div class="glass-inset" style="margin-bottom:10px; padding:15px;"><div style="font-size:0.85em; font-weight:800; color:#2D3436; margin-bottom:10px;">{title}</div>{badge}</div>', unsafe_allow_html=True)
            fig = go.Figure()
            for col_name, color, dash in traces:
                fig.add_trace(go.Scatter(x=df_view.index, y=df_view[col_name], line=dict(color=color, width=2, dash=dash)))
            extra = dict(yaxis=dict(tickformat='.0%')) if 'Ret' in traces[0][0] else {}
            fig.update_layout(**radar_layout, showlegend=False, **extra)
            st.plotly_chart(fig, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

elif page == "📈 백테스트 랩":
    st.markdown("<h2 style='font-family:Outfit; color:#2D3436;'>📈 백테스트 랩</h2>", unsafe_allow_html=True)
    st.markdown("<span style='color:#636E72; font-weight:600; font-size:1.1em;'>AMLS V4.5 성과를 나스닥(QQQ) 및 레버리지 장기투자와 비교합니다.</span><br><br>", unsafe_allow_html=True)
    with st.spinner("시뮬레이션 가동 중..."):
        daily_ret = df[['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD']].pct_change().fillna(0)
        w_orig = get_weights_v45(df['Regime'].iloc[0], False)
        val_o, val_q, val_qld, val_tqqq = 10000, 10000, 10000, 10000
        hist_o, hist_q, hist_qld, hist_tqqq = [val_o], [val_q], [val_qld], [val_tqqq]
        for i in range(1, len(df)):
            ret_o = sum(w_orig.get(t,0) * daily_ret[t].iloc[i] for t in w_orig if t in daily_ret.columns)
            val_o *= (1+ret_o); val_q *= (1+daily_ret['QQQ'].iloc[i]); val_qld *= (1+daily_ret['QLD'].iloc[i]); val_tqqq *= (1+daily_ret['TQQQ'].iloc[i])
            hist_o.append(val_o); hist_q.append(val_q); hist_qld.append(val_qld); hist_tqqq.append(val_tqqq)
            smh_cond_i = (df['SMH'].iloc[i] > df['SMH_MA50'].iloc[i]) and (df['SMH_3M_Ret'].iloc[i] > 0.05) and (df['SMH_RSI'].iloc[i] > 50)
            w_orig = get_weights_v45(df['Regime'].iloc[i], smh_cond_i)
        res_df = pd.DataFrame(index=df.index); res_df['V4.5']=hist_o; res_df['QQQ']=hist_q; res_df['QLD']=hist_qld; res_df['TQQQ']=hist_tqqq
        days = (res_df.index[-1] - res_df.index[0]).days
        def calc_metrics(series):
            ret=(series[-1]/series[0])-1; cagr=(series[-1]/series[0])**(365.25/days)-1 if days>0 else 0; mdd=((series/series.cummax())-1).min()
            return ret, cagr, mdd
        ret_o,cagr_o,mdd_o = calc_metrics(res_df['V4.5']); ret_q,cagr_q,mdd_q = calc_metrics(res_df['QQQ'])
        ret_qld,cagr_qld,mdd_qld = calc_metrics(res_df['QLD']); ret_t,cagr_t,mdd_t = calc_metrics(res_df['TQQQ'])

        st.markdown(f"<h4 style='color:#2D3436;'>📊 핵심 성과 ({days}일)</h4>", unsafe_allow_html=True)
        mc1,mc2,mc3,mc4 = st.columns(4)
        def render_mc(title, ret, cagr, mdd, is_main=False):
            bg = "background: rgba(108,92,231,0.08);" if is_main else ""
            bdr = "border: 2px solid #6C5CE7;" if is_main else "border: 1px solid rgba(108,92,231,0.06);"
            return f"""<div class="glass-card" style="{bg} {bdr} height:auto !important; padding:25px !important;">
<div style="font-size:1.05em; font-weight:800; color:#636E72; margin-bottom:12px;">{title}</div>
<div style="font-family:'Outfit'; font-size:2.2em; font-weight:800; color:#2D3436; margin-bottom:15px;">CAGR {cagr*100:.1f}%</div>
<div style="font-size:1em; color:#2D3436; font-weight:700;">누적: <span style="color:#00B894; font-weight:800;">{ret*100:.1f}%</span></div>
<div style="font-size:1em; color:#2D3436; font-weight:700;">MDD: <span style="color:#EF4444; font-weight:800;">{mdd*100:.1f}%</span></div></div>"""
        mc1.markdown(render_mc("✨ AMLS V4.5",ret_o,cagr_o,mdd_o,True), unsafe_allow_html=True)
        mc2.markdown(render_mc("QQQ (1x)",ret_q,cagr_q,mdd_q), unsafe_allow_html=True)
        mc3.markdown(render_mc("QLD (2x)",ret_qld,cagr_qld,mdd_qld), unsafe_allow_html=True)
        mc4.markdown(render_mc("TQQQ (3x)",ret_t,cagr_t,mdd_t), unsafe_allow_html=True)

        st.markdown("<br><h4 style='color:#2D3436;'>📈 자산 성장 곡선</h4>", unsafe_allow_html=True)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=res_df.index,y=res_df['QQQ'],name='QQQ',line=dict(color='#B2BEC3',width=1.5,dash='dot')))
        fig_eq.add_trace(go.Scatter(x=res_df.index,y=res_df['QLD'],name='QLD',line=dict(color='#FDA7DF',width=2,dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index,y=res_df['TQQQ'],name='TQQQ',line=dict(color='#EF4444',width=2,dash='dash')))
        fig_eq.add_trace(go.Scatter(x=res_df.index,y=res_df['V4.5'],name='AMLS V4.5',line=dict(color='#6C5CE7',width=3.5)))
        fig_eq.update_layout(height=450,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family="Outfit",color='#2D3436'),yaxis_type='log',margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
        st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
        st.plotly_chart(fig_eq, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br><h4 style='color:#2D3436;'>📉 수중 차트 (Drawdown)</h4>", unsafe_allow_html=True)
        def get_dd(s): return (s/s.cummax())-1
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=res_df.index,y=get_dd(res_df['QQQ']),name='QQQ',line=dict(color='#B2BEC3',width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index,y=get_dd(res_df['QLD']),name='QLD',line=dict(color='#FDA7DF',width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index,y=get_dd(res_df['TQQQ']),name='TQQQ',line=dict(color='#EF4444',width=1)))
        fig_dd.add_trace(go.Scatter(x=res_df.index,y=get_dd(res_df['V4.5']),name='V4.5',fill='tozeroy',line=dict(color='#6C5CE7',width=2.5)))
        fig_dd.update_layout(height=300,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family="Outfit",color='#2D3436'),yaxis=dict(tickformat='.0%'),margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
        st.markdown('<div class="glass-card" style="height:auto !important; padding:15px !important;">', unsafe_allow_html=True)
        st.plotly_chart(fig_dd, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

elif page == "📰 매크로 뉴스룸":
    headlines_for_ai, news_items = fetch_macro_news()
    st.markdown(f"""
    <div class="glass-card" style="height:auto !important; display:flex; flex-direction:row; align-items:center; gap:20px; margin-bottom:30px; padding:25px 35px !important;">
      <div style="font-size:2.5em;">📰</div>
      <div>
          <h2 style="margin:0; color:#2D3436; font-size:1.8em; font-family:'Outfit'; font-weight:800; letter-spacing:-1px;">GLOBAL MACRO & AI BRIEFING</h2>
          <p style="margin:5px 0 0 0; color:#6C5CE7; font-weight:700;">월스트리트 주요 속보와 AI 애널리스트의 심층 고찰</p>
      </div>
      <div style="margin-left:auto; background:rgba(108,92,231,0.08); padding:8px 20px; border-radius:50px; font-weight:800; color:#6C5CE7;">{rt_label}</div>
    </div>""", unsafe_allow_html=True)

    with st.expander("✨ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("🚀 심층 추론 요약 실행", use_container_width=True):
            try:
                import google.generativeai as genai
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("AI가 뉴스를 분석하고 있습니다..."):
                        genai.configure(api_key=api_key)
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model = genai.GenerativeModel(models[0].replace('models/',''))
                        prompt = """너는 1920년대 전설적인 월스트리트 퀀트 애널리스트야. 매우 냉철하고 전문적인 어조로 작성해.
                        다음 뉴스 헤드라인들을 분석해서 아래 3가지 목차로 요약해줘.
                        ## 1. 주요 뉴스 분류 (섹터/테마별 묶음)
                        ## 2. 시장 잠재 리스크 (VIX 상승 요소)
                        ## 3. 애널리스트의 최종 고찰 (투자 스탠스)
                        각 목차는 `##` 마크다운, 내용은 글머리 기호로 정리해.
                        [뉴스 헤드라인]:
                        """ + "\n".join(headlines_for_ai)
                        response = model.generate_content(prompt)
                        st.markdown(f"""<style>
.ai-report-box h2 {{ color: #6C5CE7 !important; font-size: 1.6em !important; font-weight: 800; border-bottom: 2px solid rgba(108,92,231,0.1); padding-bottom: 12px; margin-top: 30px; margin-bottom: 15px; }}
.ai-report-box h2:first-child {{ margin-top: 0; }}
.ai-report-box p, .ai-report-box li {{ color: #2D3436; font-size: 1.15em; line-height: 1.8; font-weight: 500; }}
.ai-report-box strong {{ color: #2D3436; font-weight: 800; background-color: rgba(108,92,231,0.06); padding: 2px 8px; border-radius: 8px; }}
</style><div class="glass-card ai-report-box" style="height:auto !important; padding:40px !important;">{response.text}</div>""", unsafe_allow_html=True)
                        with st.expander("📋 텍스트로 복사하기"): st.code(response.text, language="markdown")
            except KeyError: st.error("🚨 Secrets에 'GEMINI_API_KEY'를 설정해주세요.")
            except Exception as e: st.error(f"API 오류: {e}")

    st.divider()
    if news_items:
        st.markdown("<div style='font-size:1.4em; font-family:Outfit; font-weight:800; color:#2D3436; margin-bottom:20px; letter-spacing:-0.5px;'>🖼️ LATEST HEADLINES</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, item in enumerate(news_items):
            with cols[idx%3]:
                st.markdown(f"""
                <div class="glass-card" style="padding:25px !important; margin-bottom:20px; height:160px !important; display:flex; flex-direction:column; justify-content:space-between;">
                    <div style="font-weight:700; font-size:1.1em; line-height:1.5; color:#2D3436; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                        <a href="{item['link']}" target="_blank" style="color:#2D3436; text-decoration:none;">{item['title'].replace('&','&amp;')}</a>
                    </div>
                    <div style="color:#6C5CE7; font-size:0.9em; margin-top:10px; font-weight:800; font-family:'Outfit';">{item['date']}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다. (15분 후 갱신)")
