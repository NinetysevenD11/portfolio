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
import google.generativeai as genai

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="AMLS v4.5 | Quant Terminal",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
:root {
    --bg-base:        #F2ECE4;
    --bg-raised:      #F7F2EB;
    --bg-card:        #FAF6F0;
    --bg-inset:       #EAE4DB;
    --bg-pressed:     #E3DDD4;
    --copper-100:     #FDF0E8;
    --copper-200:     #F4D4BC;
    --copper-400:     #C98B62;
    --copper-500:     #B5724A;
    --copper-600:     #9A5C36;
    --copper-700:     #7D4826;
    --ink-900:        #2A2118;
    --ink-700:        #4A3D32;
    --ink-500:        #6B5E52;
    --ink-300:        #A8998C;
    --ink-100:        #D4C8BD;
    --success-bg:     #EBF5EB;
    --success-border: #5A9E5A;
    --success-text:   #2D6E2D;
    --warn-bg:        #FEF6E4;
    --warn-border:    #C9962A;
    --warn-text:      #7A5A10;
    --danger-bg:      #FCECEA;
    --danger-border:  #C0473A;
    --danger-text:    #8B1F16;
    --shadow-lv1: 0 1px 2px rgba(139,94,60,0.10), 0 2px 4px rgba(139,94,60,0.07);
    --shadow-lv2: 0 2px 6px rgba(139,94,60,0.12), 0 4px 12px rgba(139,94,60,0.09);
    --shadow-lv3: 0 4px 12px rgba(139,94,60,0.14), 0 8px 24px rgba(139,94,60,0.10);
    --shadow-inset: inset 0 1px 3px rgba(139,94,60,0.15), inset 0 2px 6px rgba(139,94,60,0.08);
    --r-sm:   6px;
    --r-md:   12px;
    --r-lg:   18px;
    --r-xl:   24px;
    --r-full: 9999px;
}

.stApp {
    background-color: var(--bg-base) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--ink-900) !important;
}

/* ── 사이드바 열기 버튼은 반드시 보이게 ── */
header { visibility: hidden; }
[data-testid="collapsedControl"] { visibility: visible !important; display: flex !important; }
#MainMenu, footer { visibility: hidden; }

.main .block-container { max-width: 1320px; padding: 1.5rem 2rem 3rem; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #EDE7DE 0%, #E6DFD5 100%) !important;
    border-right: 1px solid var(--ink-100) !important;
    box-shadow: var(--shadow-lv2) !important;
}
[data-testid="stSidebarNav"] { display: none; }

div.row-widget.stRadio > div { gap: 6px; flex-direction: column; }
div.row-widget.stRadio > div > label {
    background: var(--bg-card) !important;
    border: 1px solid var(--ink-100) !important;
    border-radius: var(--r-md) !important;
    padding: 12px 16px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    color: var(--ink-700) !important;
    box-shadow: var(--shadow-lv1) !important;
    transition: all 0.18s ease !important;
    cursor: pointer !important;
}
div.row-widget.stRadio > div > label:hover {
    background: var(--copper-100) !important;
    border-color: var(--copper-400) !important;
    box-shadow: var(--shadow-lv2) !important;
    transform: translateY(-1px) !important;
    color: var(--copper-600) !important;
}

h1, h2, h3 { font-family: 'DM Serif Display', serif !important; color: var(--ink-900) !important; letter-spacing: -0.3px !important; }
h4, h5, h6 { font-family: 'DM Sans', sans-serif !important; font-weight: 600 !important; color: var(--ink-700) !important; }

div[data-testid="stAlert"] {
    border-radius: var(--r-md) !important;
    border-width: 1px !important;
    box-shadow: var(--shadow-lv1) !important;
    padding: 14px 18px !important;
    font-family: 'DM Sans', sans-serif !important;
}

div[data-testid="stMetricValue"] > div {
    font-family: 'DM Serif Display', serif !important;
    font-size: 1.6rem !important;
    color: var(--ink-900) !important;
}
div[data-testid="stMetricLabel"] > div {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    color: var(--ink-500) !important;
}
div[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--ink-100) !important;
    border-radius: var(--r-lg) !important;
    padding: 18px 20px !important;
    box-shadow: var(--shadow-lv2) !important;
}

div[data-testid="stButton"] > button {
    background: var(--copper-500) !important;
    color: #FAF6F0 !important;
    border: none !important;
    border-radius: var(--r-md) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 10px 24px !important;
    box-shadow: var(--shadow-lv2) !important;
    transition: all 0.18s ease !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button:hover {
    background: var(--copper-600) !important;
    box-shadow: var(--shadow-lv3) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button:active {
    box-shadow: var(--shadow-inset) !important;
    transform: translateY(1px) !important;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--bg-inset) !important;
    border: 1px solid var(--ink-100) !important;
    border-radius: var(--r-md) !important;
    box-shadow: var(--shadow-inset) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--ink-900) !important;
    padding: 10px 14px !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--ink-100) !important;
    border-radius: var(--r-lg) !important;
    background: var(--bg-card) !important;
    box-shadow: var(--shadow-lv1) !important;
    overflow: hidden !important;
}

hr { border: none !important; border-top: 1px solid var(--ink-100) !important; margin: 2rem 0 !important; }

[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--ink-100) !important;
    border-radius: var(--r-lg) !important;
    box-shadow: var(--shadow-lv1) !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 헬퍼: Neo-Tactile 컴포넌트
# ==========================================
def nt_card(content_html, padding="20px 24px", bg="var(--bg-card)",
            border_color="var(--ink-100)", shadow="var(--shadow-lv2)",
            radius="var(--r-lg)", border_left=""):
    bl = f"border-left: 5px solid {border_left};" if border_left else ""
    return f"""
    <div style="background:{bg};border:1px solid {border_color};{bl}
                border-radius:{radius};padding:{padding};
                box-shadow:{shadow};margin-bottom:12px;">
        {content_html}
    </div>"""

def nt_section_title(icon, title, subtitle=""):
    sub = f'<div style="font-family:\'DM Sans\',sans-serif;font-size:0.82rem;font-weight:500;color:var(--ink-300);letter-spacing:0.8px;text-transform:uppercase;margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--ink-100);">
        <div style="background:var(--copper-100);border:1px solid var(--copper-200);border-radius:var(--r-sm);
                    width:36px;height:36px;display:flex;align-items:center;justify-content:center;
                    font-size:1.1rem;box-shadow:var(--shadow-lv1);">{icon}</div>
        <div>
            <div style="font-family:'DM Serif Display',serif;font-size:1.1rem;color:var(--ink-900);font-weight:400;">{title}</div>
            {sub}
        </div>
    </div>"""

def nt_badge(text, color="copper"):
    palette = {
        "copper":  ("var(--copper-100)", "var(--copper-500)", "var(--copper-200)"),
        "success": ("var(--success-bg)", "var(--success-text)", "#A8D5A8"),
        "danger":  ("var(--danger-bg)",  "var(--danger-text)",  "#E8B4B0"),
        "warn":    ("var(--warn-bg)",    "var(--warn-text)",    "#F0D090"),
        "ink":     ("#EAE4DB",           "var(--ink-700)",      "var(--ink-100)"),
    }
    bg, fg, bd = palette.get(color, palette["copper"])
    return f"""<span style="background:{bg};color:{fg};border:1px solid {bd};
               border-radius:var(--r-full);padding:2px 10px;font-size:0.78rem;
               font-weight:600;font-family:'DM Sans',sans-serif;letter-spacing:0.3px;">{text}</span>"""

def nt_cond_row(label, value, ok):
    badge = nt_badge("PASS ✓", "success") if ok else nt_badge("FAIL ✗", "danger")
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                background:var(--bg-raised);border:1px solid var(--ink-100);border-radius:var(--r-md);
                padding:10px 14px;margin-bottom:8px;box-shadow:var(--shadow-lv1);">
        <div>
            <div style="font-family:'DM Sans',sans-serif;font-weight:600;font-size:0.88rem;color:var(--ink-700);">{label}</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.8rem;color:var(--ink-300);margin-top:2px;">{value}</div>
        </div>
        {badge}
    </div>"""

def nt_bar_item(label, pct, max_pct):
    bar_w = pct / max_pct * 100
    return f"""
    <div style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px;">
            <span style="font-family:'DM Sans',sans-serif;font-weight:600;font-size:0.92rem;color:var(--ink-700);">{label}</span>
            <span style="font-family:'DM Serif Display',serif;font-size:1.1rem;color:var(--copper-500);">{pct:.0f}%</span>
        </div>
        <div style="background:var(--bg-inset);border-radius:var(--r-full);height:7px;box-shadow:var(--shadow-inset);">
            <div style="background:linear-gradient(90deg,var(--copper-400),var(--copper-600));
                        width:{bar_w}%;height:7px;border-radius:var(--r-full);
                        box-shadow:0 1px 4px rgba(181,114,74,0.4);"></div>
        </div>
    </div>"""

# ==========================================
# 사이드바
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:20px 10px 16px;border-bottom:1px solid var(--ink-100);margin-bottom:20px;">
        <div style="font-family:'DM Serif Display',serif;font-size:2rem;color:var(--ink-900);letter-spacing:-0.5px;line-height:1;">AMLS</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.72rem;font-weight:700;letter-spacing:2px;color:var(--copper-500);text-transform:uppercase;margin-top:4px;">Quant Terminal v4.5</div>
        <div style="margin-top:12px;display:inline-block;background:var(--copper-100);border:1px solid var(--copper-200);border-radius:var(--r-full);padding:3px 12px;">
            <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--copper-600);font-weight:500;">EST. 2026 | SEYOON</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "NAV",
        ["📊  시장 분석관", "🎯  8-Pack 레이더", "📉  폭락장 아카이브", "📰  매크로 뉴스룸"],
        label_visibility="collapsed"
    )

    st.markdown("""
    <div style="position:fixed;bottom:20px;left:0;width:260px;text-align:center;
                font-family:'DM Sans',sans-serif;font-size:0.75rem;color:var(--ink-300);">
        Powered by AMLS V4.5 Engine<br>© 2026 SEYOON
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 글로벌 헤더
# ==========================================
today_str = datetime.now().strftime("%b %d, %Y")
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:20px 28px;margin-bottom:28px;
            background:var(--bg-card);border:1px solid var(--ink-100);
            border-radius:var(--r-xl);box-shadow:var(--shadow-lv2);">
    <div>
        <div style="font-family:'DM Serif Display',serif;font-size:1.9rem;color:var(--ink-900);letter-spacing:-0.5px;line-height:1.1;">
            RIMBERIO <span style="color:var(--copper-500);">Financial</span> Gazette
        </div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.78rem;font-weight:700;
                    letter-spacing:2px;text-transform:uppercase;color:var(--ink-300);margin-top:5px;">
            The Wall Street Quantitative Journal &nbsp;·&nbsp; Real-Time Macro Terminal
        </div>
    </div>
    <div style="text-align:right;">
        <div style="font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink-500);">{today_str}</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.72rem;font-weight:700;
                    letter-spacing:1.5px;text-transform:uppercase;color:var(--copper-500);margin-top:4px;">AMLS V4.5 ENGINE</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 데이터 수집 & 지표 계산
# ==========================================
SECTOR_TICKERS = ['XLK','XLV','XLF','XLY','XLC','XLI','XLP','XLE','XLU','XLRE','XLB']
CORE_TICKERS   = ['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD','^VIX','HYG','IEF','QQQE','UUP']
TICKERS        = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST     = ['TQQQ','SOXL','USD','QLD','SSO','SPY','QQQ','GLD','CASH']

@st.cache_data(ttl=3600)
def load_data():
    end_date   = datetime.now()
    start_date = "2006-01-01"
    data = yf.download(TICKERS, start=start_date, end=end_date.strftime("%Y-%m-%d"),
                       progress=False, auto_adjust=False)['Close']
    df = pd.DataFrame(index=data.index)
    for t in TICKERS:
        df[t] = data[t]
    df = df.ffill().bfill()
    df['QQQ_MA50']      = df['QQQ'].rolling(50).mean()
    df['QQQ_MA200']     = df['QQQ'].rolling(200).mean()
    df['TQQQ_MA200']    = df['TQQQ'].rolling(200).mean()
    df['SMH_MA50']      = df['SMH'].rolling(50).mean()
    df['VIX_MA5']       = df['^VIX'].rolling(5).mean()
    df['SMH_3M_Ret']    = df['SMH'].pct_change(63)
    df['SMH_1M_Ret']    = df['SMH'].pct_change(21)
    df['SMH_RSI']       = ta.rsi(df['SMH'], length=14)
    df['HYG_IEF_Ratio'] = df['HYG'] / df['IEF']
    df['HYG_IEF_MA50']  = df['HYG_IEF_Ratio'].rolling(50).mean()
    df['QQQ_20d_Ret']   = df['QQQ'].pct_change(20)
    df['QQQE_20d_Ret']  = df['QQQE'].pct_change(20)
    df['QQQ_RSI']       = ta.rsi(df['QQQ'], length=14)
    df['GLD_SPY_Ratio'] = df['GLD'] / df['SPY']
    df['GLD_SPY_MA50']  = df['GLD_SPY_Ratio'].rolling(50).mean()
    df['QQQ_High52']    = df['QQQ'].rolling(252).max()
    df['QQQ_DD']        = (df['QQQ'] / df['QQQ_High52']) - 1
    df['UUP_MA50']      = df['UUP'].rolling(50).mean()
    for sec in SECTOR_TICKERS:
        df[f'{sec}_1M'] = df[sec].pct_change(21)
    return df.dropna()

with st.spinner('데이터베이스 동기화 중…'):
    df = load_data()

@st.cache_data(ttl=900)
def fetch_macro_news():
    headlines, items = [], []
    try:
        q   = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(urllib.request.urlopen(req).read())
        for item in root.findall('.//item')[:12]:
            t = item.find('title').text
            l = item.find('link').text
            d = (item.find('pubDate').text or "")[:-4]
            headlines.append(t)
            items.append({"title": t, "link": l, "date": d})
    except Exception:
        pass
    return headlines, items

# ==========================================
# AMLS v4.5 코어 엔진
# ==========================================
def get_target_v45(row):
    v, vm, q, m2, m5 = row['^VIX'], row['VIX_MA5'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
    if v > 40:                           return 4
    if q < m2:                           return 3
    if q >= m2 and m5 >= m2 and vm < 25: return 1
    return 2

df['Target'] = df.apply(get_target_v45, axis=1)

def apply_delay(targets):
    res=[]; curr=3; pend=None; cnt=0
    for t in targets:
        if t > curr:   curr=t; pend=None; cnt=0
        elif t < curr:
            if t == pend:
                cnt += 1
                if cnt >= 5: curr=t; pend=None; cnt=0
            else: pend=t; cnt=1
        else: pend=None; cnt=0
        res.append(curr)
    return pd.Series(res, index=targets.index).shift(1).bfill()

df['Regime'] = apply_delay(df['Target'])

def get_weights_v45(reg, smh_ok):
    w    = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if smh_ok else 'USD'
    if   reg == 1: w['TQQQ'],w[semi],w['QLD'],w['SSO'],w['GLD'],w['SPY'] = .30,.20,.20,.15,.10,.05
    elif reg == 2: w['TQQQ'],w['QLD'],w['SSO'],w['GLD'],w['USD']         = .15,.35,.20,.20,.10
    elif reg == 3: w['GLD'],w['CASH'],w['QQQ']                            = .50,.35,.15
    elif reg == 4: w['GLD'],w['CASH'],w['QQQ']                            = .50,.40,.10
    return w

last_row      = df.iloc[-1]
curr_regime   = int(last_row['Regime'])
target_regime = int(last_row['Target'])

vix_close = last_row['^VIX'];  vix_ma5   = last_row['VIX_MA5']
qqq_close = last_row['QQQ'];   qqq_ma50  = last_row['QQQ_MA50'];  qqq_ma200 = last_row['QQQ_MA200']
smh_close = last_row['SMH'];   smh_ma50  = last_row['SMH_MA50']
smh_3m    = last_row['SMH_3M_Ret']; smh_1m = last_row['SMH_1M_Ret']; smh_rsi = last_row['SMH_RSI']

smh_c1   = smh_close > smh_ma50
smh_c2   = (smh_3m > .05) or (smh_1m > .10)
smh_c3   = smh_rsi > 50
smh_cond = smh_c1 and smh_c2 and smh_c3
target_weights = get_weights_v45(curr_regime, smh_cond)

regime_info = {
    1: ("🟢  R1 — 대세 강세장",   "풀 레버리지 가동",           "#2D6E2D","#EBF5EB","#5A9E5A"),
    2: ("🟡  R2 — 경계 / 조정장", "세윤's Rule (TQQQ 15% 방어)","#7A5A10","#FEF6E4","#C9962A"),
    3: ("🟠  R3 — 대세 하락장",   "안전 자산 대피",             "#9A3A10","#FEF0E8","#D0703A"),
    4: ("🔴  R4 — 패닉장",        "최대 방어 모드",             "#8B1F16","#FCECEA","#C0473A"),
}

chart_layout = dict(
    paper_bgcolor='#FAF6F0', plot_bgcolor='#F7F2EB',
    font=dict(family="DM Sans", color="#4A3D32"),
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(gridcolor="#EAE4DB", linecolor="#D4C8BD"),
    yaxis=dict(gridcolor="#EAE4DB", linecolor="#D4C8BD"),
)
radar_layout = dict(
    height=210, margin=dict(l=10, r=10, t=15, b=15),
    paper_bgcolor='#FAF6F0', plot_bgcolor='#F7F2EB',
    font=dict(family="DM Sans", color="#4A3D32"),
    xaxis=dict(gridcolor="#EAE4DB"), yaxis=dict(gridcolor="#EAE4DB"),
)
regime_colors = {
    1:'rgba(90,158,90,0.08)', 2:'rgba(201,150,42,0.10)',
    3:'rgba(154,58,16,0.12)', 4:'rgba(139,31,22,0.18)'
}

# ==========================================
# 페이지 라우팅
# ==========================================

# ─── PAGE 1: 시장 분석관 ───────────────────────────────────────
if page == "📊  시장 분석관":

    rname, rstrat, rfg, rbg, rbd = regime_info[curr_regime]

    st.markdown(f"""
    <div style="background:{rbg};border:1px solid {rbd};border-left:6px solid {rfg};
                border-radius:var(--r-lg);padding:18px 24px;margin-bottom:20px;
                box-shadow:var(--shadow-lv2);display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div style="font-family:'DM Serif Display',serif;font-size:1.5rem;color:{rfg};line-height:1.2;">{rname}</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:0.9rem;color:{rfg};opacity:0.85;margin-top:4px;font-weight:500;">전략: {rstrat}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-family:'DM Mono',monospace;font-size:0.75rem;color:{rfg};opacity:0.6;text-transform:uppercase;letter-spacing:1px;">Current Regime</div>
            <div style="font-family:'DM Serif Display',serif;font-size:2.4rem;color:{rfg};line-height:1;">R{curr_regime}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if curr_regime != target_regime:
        st.warning(f"⏳ **위원회 대기:** 시장이 R{target_regime} 조건을 터치했으나, 5일 연속 확인 중입니다.")
    else:
        st.success("✅ **위원회:** 모든 조건이 현재 국면에 부합합니다.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1], gap="large")

    with col_left:
        algo_col, semi_col = st.columns(2, gap="medium")

        with algo_col:
            st.markdown(nt_section_title("🏛", "REGIME 알고리즘", "4-Factor Engine"), unsafe_allow_html=True)
            for lbl, val, ok in [
                ("VIX 패닉 임계점 &lt; 40", f"{vix_close:.2f}", vix_close <= 40),
                ("QQQ &gt; 200MA", f"${qqq_close:.0f} / ${qqq_ma200:.0f}", qqq_close >= qqq_ma200),
                ("50MA ≥ 200MA",   f"${qqq_ma50:.0f} / ${qqq_ma200:.0f}", qqq_ma50 >= qqq_ma200),
                ("VIX 5일선 &lt; 25", f"{vix_ma5:.2f}", vix_ma5 < 25),
            ]:
                st.markdown(nt_cond_row(lbl, val, ok), unsafe_allow_html=True)

        with semi_col:
            st.markdown(nt_section_title("💻", "SOXL 3중 필터", "Semiconductor Gate"), unsafe_allow_html=True)
            for lbl, val, ok in [
                ("정배열 추세 SMH > 50MA",      f"${smh_close:.1f} / ${smh_ma50:.1f}", smh_c1),
                ("상승 모멘텀 1M>10% or 3M>5%", f"1M {smh_1m*100:.1f}% / 3M {smh_3m*100:.1f}%", smh_c2),
                ("매수 심리 RSI > 50",           f"RSI {smh_rsi:.1f}", smh_c3),
            ]:
                st.markdown(nt_cond_row(lbl, val, ok), unsafe_allow_html=True)

            vbg  = "var(--success-bg)" if smh_cond else "var(--danger-bg)"
            vbd  = "var(--success-border)" if smh_cond else "var(--danger-border)"
            vfg  = "var(--success-text)"   if smh_cond else "var(--danger-text)"
            vtxt = "🔥 SOXL 편입 승인" if smh_cond else "🛡️ USD 편입 (SOXL 기각)"
            st.markdown(f"""
            <div style="background:{vbg};border:1px solid {vbd};border-radius:var(--r-md);
                        padding:12px 16px;text-align:center;font-family:'DM Sans',sans-serif;
                        font-weight:700;color:{vfg};font-size:0.95rem;margin-top:4px;
                        box-shadow:var(--shadow-lv1);">{vtxt}</div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown(nt_section_title("🛒", "V4.5 목표 포트폴리오", "Target Allocation"), unsafe_allow_html=True)
        w_items = sorted([(a, w) for a, w in target_weights.items() if w > 0], key=lambda x: -x[1])
        max_w   = max(w for _, w in w_items)
        bars    = "".join(nt_bar_item(a, w*100, max_w*100) for a, w in w_items)
        st.markdown(f"""
        <div style="background:var(--bg-card);border:1px solid var(--ink-100);
                    border-radius:var(--r-lg);padding:20px 22px;box-shadow:var(--shadow-lv2);">
            {bars}
        </div>""", unsafe_allow_html=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ vs 200일선",   f"${last_row['QQQ']:.2f}",  f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200일선",  f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX 5일 이평선",   f"{last_row['VIX_MA5']:.2f}", f"종가 {last_row['^VIX']:.2f}")
    m4.metric("반도체 1M 수익률", f"{last_row['SMH_1M_Ret']*100:+.2f}%", "SOXL 조건")
    m5.metric("반도체 3M 수익률", f"{last_row['SMH_3M_Ret']*100:+.2f}%", "")

    st.divider()
    st.markdown(nt_section_title("📈", "기술적 차트 모니터링", "QQQ & TQQQ 200일선"), unsafe_allow_html=True)
    if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
        st.error("🚨 **[선행 경보]** QQQ는 200일선 위지만 TQQQ가 이탈 — R3 강등 위험!")

    df_recent = df.iloc[-500:]
    cc1, cc2  = st.columns(2)

    def build_chart(series, ma_series, title):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_recent.index, y=series,    name=title.split()[0], line=dict(color='#7D4826', width=2)))
        fig.add_trace(go.Scatter(x=df_recent.index, y=ma_series, name='200일선',         line=dict(color='#C98B62', width=1.5, dash='dash')))
        for i in range(1, len(df_recent)):
            if df_recent['Regime'].iloc[i-1] != df_recent['Regime'].iloc[i] or i == 1:
                si = df_recent.index[i]; cr = int(df_recent['Regime'].iloc[i])
            if i == len(df_recent)-1 or df_recent['Regime'].iloc[i] != df_recent['Regime'].iloc[i+1]:
                fig.add_vrect(x0=si, x1=df_recent.index[i], fillcolor=regime_colors[cr], opacity=1, layer="below", line_width=0)
        fig.update_layout(title=title, height=320, **chart_layout)
        return fig

    with cc1: st.plotly_chart(build_chart(df_recent['QQQ'],  df_recent['QQQ_MA200'],  "[시스템] QQQ vs 200일"), use_container_width=True)
    with cc2: st.plotly_chart(build_chart(df_recent['TQQQ'], df_recent['TQQQ_MA200'], "[조기 경보] TQQQ vs 200일"), use_container_width=True)

# ─── PAGE 2: 8-Pack 레이더 ────────────────────────────────────
elif page == "🎯  8-Pack 레이더":
    st.markdown(nt_section_title("🎯", "조기 경보 8-Pack 레이더", "Smart Money Tracking System"), unsafe_allow_html=True)
    st.markdown(nt_card("""
    <div style="font-family:'DM Serif Display',serif;font-size:1.05rem;font-style:italic;color:var(--copper-600);margin-bottom:10px;">
        "군중의 환희는 속일 수 있어도, 거대 자본이 남기는 발자국은 결코 속일 수 없다."
    </div>
    <div style="font-family:'DM Sans',sans-serif;font-size:0.9rem;line-height:1.65;color:var(--ink-700);">
        월스트리트 Prop Desk 수준의 <strong>8개 선행 지표</strong>. 감정을 배제하고 숫자에만 집중하십시오.
    </div>
    """, border_left="var(--copper-400)"), unsafe_allow_html=True)

    df_view = df.iloc[-120:]
    qqq_rsi = last_row['QQQ_RSI']
    qqq_dd  = last_row['QQQ_DD']
    row1 = st.columns(4)
    row2 = st.columns(4)

    with row1[0]:
        st.markdown("##### 1. 스마트 DCA (RSI)")
        if qqq_rsi < 40 and last_row['QQQ'] < last_row['QQQ_MA200']: st.success("🔥 매수: 공포/과매도")
        elif qqq_rsi > 70: st.error("⚠️ 보류: 단기 과열")
        else: st.info("🟢 정상: 기계적 적립")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_RSI'], line=dict(color='#9A5C36', width=2)))
        fig1.add_hline(y=70, line_dash='dash', line_color='#C0473A', line_width=1)
        fig1.add_hline(y=30, line_dash='dash', line_color='#5A9E5A', line_width=1)
        fig1.update_layout(**radar_layout, yaxis=dict(range=[10,90]), showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    with row1[1]:
        st.markdown("##### 2. 멘탈 방어 (Drawdown)")
        if qqq_dd < -0.20: st.error("🚨 약세장: -20% 돌파")
        elif qqq_dd < -0.10: st.warning("⚠️ 조정장: -10% 돌파")
        else: st.success("✅ 안전: 고점 순항")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_DD'], fill='tozeroy',
                                  line=dict(color='#C07B54', width=2), fillcolor='rgba(192,123,84,0.15)'))
        fig2.update_layout(**radar_layout, yaxis=dict(tickformat='.0%'), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with row1[2]:
        st.markdown("##### 3. 시장 심리 (F&G)")
        vix_score = max(0, min(100, 100-(last_row['^VIX']-12)/28*100))
        dd_score  = max(0, min(100, (qqq_dd+.20)/.20*100))
        fg_score  = (vix_score+dd_score+max(0, min(100, qqq_rsi)))/3
        if fg_score < 30: st.success("🔥 공포: 저점 매집")
        elif fg_score > 70: st.error("⚠️ 탐욕: 추격 자제")
        else: st.info("🟢 중립")
        fig3 = go.Figure(go.Indicator(
            mode="gauge+number", value=fg_score,
            gauge={'axis':{'range':[0,100]}, 'bar':{'color':'#9A5C36'}, 'bgcolor':'#F7F2EB',
                   'steps':[{'range':[0,25],'color':'rgba(192,71,58,0.6)'},
                             {'range':[25,45],'color':'rgba(201,150,42,0.3)'},
                             {'range':[45,55],'color':'rgba(0,0,0,0.05)'},
                             {'range':[55,75],'color':'rgba(90,158,90,0.3)'},
                             {'range':[75,100],'color':'rgba(90,158,90,0.6)'}]}
        ))
        fig3.update_layout(height=210, margin=dict(l=15,r=15,t=10,b=10),
                           paper_bgcolor='#FAF6F0', font=dict(family="DM Sans",color="#4A3D32"))
        st.plotly_chart(fig3, use_container_width=True)

    with row1[3]:
        st.markdown("##### 4. 섹터 순환 (1M)")
        sec_names = {'XLK':'기술','XLV':'헬스','XLF':'금융','XLY':'소비','XLC':'통신',
                     'XLI':'산업','XLP':'필수','XLE':'에너지','XLU':'유틸','XLRE':'부동산','XLB':'소재'}
        sec_data  = [{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
        sec_df    = pd.DataFrame(sec_data).sort_values('수익률', ascending=True)
        st.info(f"🏆 {sec_df.iloc[-1]['섹터']} / 📉 {sec_df.iloc[0]['섹터']}")
        fig4 = go.Figure(go.Bar(x=sec_df['수익률'], y=sec_df['섹터'], orientation='h',
                                marker_color=['#C0473A' if v<0 else '#7D4826' for v in sec_df['수익률']]))
        fig4.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    with row2[0]:
        st.markdown("##### 5. 채권 스프레드")
        if last_row['HYG_IEF_Ratio'] < last_row['HYG_IEF_MA50']: st.error("🚨 위험: 국채 도피")
        else: st.success("✅ 안전: 위험 자산 선호")
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_Ratio'], line=dict(color='#9A5C36', width=2)))
        fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_MA50'],  line=dict(color='#C98B62', dash='dot')))
        fig5.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

    with row2[1]:
        st.markdown("##### 6. 시장 폭")
        if last_row['QQQ_20d_Ret'] > 0 and last_row['QQQE_20d_Ret'] < 0: st.warning("⚠️ 가짜 상승: 쏠림")
        else: st.success("✅ 건전: 고른 상승")
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_20d_Ret'],  name='QQQ',  line=dict(color='#7D4826', width=2)))
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQE_20d_Ret'], name='QQQE', line=dict(color='#C98B62', dash='dot')))
        fig6.update_layout(**radar_layout, showlegend=False, yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6, use_container_width=True)

    with row2[2]:
        st.markdown("##### 7. 안전 자산 (금/주식)")
        if last_row['GLD_SPY_Ratio'] > last_row['GLD_SPY_MA50']: st.warning("⚠️ 이탈: 금 피신")
        else: st.success("✅ 정상: 주식 선호")
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_Ratio'], line=dict(color='#9A5C36', width=2)))
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_MA50'],  line=dict(color='#C98B62', dash='dot')))
        fig7.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig7, use_container_width=True)

    with row2[3]:
        st.markdown("##### 8. 달러 유동성")
        if last_row['UUP'] > last_row['UUP_MA50']: st.error("🚨 강달러 압박")
        else: st.success("✅ 달러 강세 진정")
        fig8 = go.Figure()
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP'],      line=dict(color='#9A5C36', width=2)))
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP_MA50'], line=dict(color='#C98B62', dash='dot')))
        fig8.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig8, use_container_width=True)

# ─── PAGE 3: 폭락장 아카이브 ──────────────────────────────────
elif page == "📉  폭락장 아카이브":
    st.markdown(nt_section_title("📉", "역사적 폭락장 아카이브", "Crisis Archive"), unsafe_allow_html=True)
    st.write("하락장이 올 때마다 이 기록을 보며 멘탈을 통제하십시오.")

    crises = {
        "2008 금융위기 (서브프라임)": ("2007-08-01","2009-12-31"),
        "2020 코로나 팬데믹":         ("2020-01-01","2020-12-31"),
        "2022 인플레이션 쇼크":       ("2021-11-01","2023-03-31"),
    }
    selected = st.selectbox("위기 구간 선택:", list(crises.keys()))
    s_date, e_date = crises[selected]
    try:
        df_c = df.loc[s_date:e_date]
        if len(df_c) > 0:
            fig_c = go.Figure()
            fig_c.add_trace(go.Scatter(x=df_c.index, y=df_c['QQQ'],       name='QQQ',    line=dict(color='#7D4826', width=2)))
            fig_c.add_trace(go.Scatter(x=df_c.index, y=df_c['QQQ_MA200'], name='200일선', line=dict(color='#C98B62', width=2, dash='dash')))
            r3r4 = 0
            for i in range(1, len(df_c)):
                if df_c['Regime'].iloc[i-1] != df_c['Regime'].iloc[i] or i == 1:
                    si = df_c.index[i]; cr = int(df_c['Regime'].iloc[i])
                if i == len(df_c)-1 or df_c['Regime'].iloc[i] != df_c['Regime'].iloc[i+1]:
                    fig_c.add_vrect(x0=si, x1=df_c.index[i], fillcolor=regime_colors[cr], opacity=1, layer="below", line_width=0)
                if df_c['Regime'].iloc[i] in [3,4]: r3r4 += 1
            fig_c.update_layout(title=f"V4.5 백테스트: {selected}", height=480, **chart_layout)
            st.plotly_chart(fig_c, use_container_width=True)
            st.info(f"💡 총 {len(df_c)} 거래일 중 **{r3r4}일 ({r3r4/len(df_c)*100:.1f}%)** R3/R4 방어 완료.")
    except Exception:
        st.error("데이터 범위 오류.")

# ─── PAGE 4: 매크로 뉴스룸 ────────────────────────────────────
elif page == "📰  매크로 뉴스룸":
    st.markdown(nt_section_title("📰", "실시간 매크로 뉴스 & AI 브리핑", "Global Macro Intelligence"), unsafe_allow_html=True)
    st.warning("⚠️ **[멘탈 주의보]** 뉴스는 참고용입니다. 오직 시스템 숫자에만 의존하십시오.")

    headlines_for_ai, news_items = fetch_macro_news()

    with st.expander("✨ System-2 심층 추론 애널리스트 (클릭하여 열기)", expanded=True):
        st.markdown("**(주의)** Streamlit Cloud `Secrets`에 `GEMINI_API_KEY`를 먼저 등록하십시오.")
        if st.button("🚀 심층 추론 요약 실행"):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai:
                    st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("다각도 검증 및 심층 추론 중…"):
                        genai.configure(api_key=api_key)
                        models_avail = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        if not models_avail:
                            st.error("사용 가능한 모델이 없습니다.")
                        else:
                            tgt   = next((m for m in models_avail if 'flash' in m.lower() or 'pro' in m.lower()), models_avail[0])
                            clean = tgt.replace('models/', '')
                            model = genai.GenerativeModel(clean)
                            prompt = (
                                "너는 1920년대 월스트리트의 날카롭고 이성적인 퀀트 애널리스트야.\n\n"
                                "답변은 반드시 한국어. 다음 3가지 목차만 출력:\n"
                                "1. 주요 뉴스 분류 및 초기 분석\n"
                                "2. 핵심 쟁점 및 잠재 리스크\n"
                                "3. 최종 고찰 (Reconsideration from Scratch)\n\n"
                                "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                            )
                            resp = model.generate_content(prompt)
                            st.success(f"✅ 분석 완료 (모델: {clean})")
                            st.info(f"**🤖 System-2 심층 리포트:**\n\n{resp.text}")
                            with st.expander("📋 복사하기"):
                                st.code(resp.text, language="markdown")
            except KeyError:
                st.error("🚨 Streamlit Secrets에 'GEMINI_API_KEY'가 없습니다.")
            except Exception as e:
                st.error(f"오류: {e}")

    st.divider()
    st.markdown("#### 🖼️ 최신 헤드라인 갤러리")
    if news_items:
        cols = st.columns(3)
        for idx, item in enumerate(news_items):
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background:var(--bg-card);border:1px solid var(--ink-100);
                            border-radius:var(--r-lg);padding:16px 18px;margin-bottom:14px;
                            height:140px;display:flex;flex-direction:column;justify-content:space-between;
                            box-shadow:var(--shadow-lv2);">
                    <div style="font-family:'DM Sans',sans-serif;font-weight:600;font-size:0.9rem;
                                line-height:1.45;color:var(--ink-700);
                                overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;">
                        <a href="{item['link']}" target="_blank"
                           style="color:var(--ink-700);text-decoration:none;">{item['title']}</a>
                    </div>
                    <div style="font-family:'DM Mono',monospace;font-size:0.72rem;
                                color:var(--copper-500);margin-top:10px;">{item['date']}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다.")
