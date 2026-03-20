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

# ==========================================
# 1. 대시보드 기본 설정 및 데이터 수집
# ==========================================
st.set_page_config(page_title="RIMBERIO FINANCIAL GAZETTE", layout="wide", page_icon="📰", initial_sidebar_state="expanded")

SECTOR_TICKERS = ['XLK', 'XLV', 'XLF', 'XLY', 'XLC', 'XLI', 'XLP', 'XLE', 'XLU', 'XLRE', 'XLB']
CORE_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'HYG', 'IEF', 'QQQE', 'UUP']
TICKERS = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST = ['TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'QQQ', 'GLD', 'CASH']

@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=600)
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close']
    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]
    df = df.ffill().bfill()
    df['QQQ_MA50'] = df['QQQ'].rolling(window=50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(window=200).mean()
    df['TQQQ_MA200'] = df['TQQQ'].rolling(window=200).mean() 
    df['SMH_MA50'] = df['SMH'].rolling(window=50).mean()
    df['VIX_MA5'] = df['^VIX'].rolling(window=5).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(periods=63)
    df['SMH_1M_Ret'] = df['SMH'].pct_change(periods=21)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    df['HYG_IEF_Ratio'] = df['HYG'] / df['IEF']
    df['HYG_IEF_MA50'] = df['HYG_IEF_Ratio'].rolling(window=50).mean()
    df['QQQ_20d_Ret'] = df['QQQ'].pct_change(periods=20)
    df['QQQE_20d_Ret'] = df['QQQE'].pct_change(periods=20)
    df['QQQ_RSI'] = ta.rsi(df['QQQ'], length=14)
    df['GLD_SPY_Ratio'] = df['GLD'] / df['SPY']
    df['GLD_SPY_MA50'] = df['GLD_SPY_Ratio'].rolling(window=50).mean()
    df['QQQ_High52'] = df['QQQ'].rolling(window=252).max() 
    df['QQQ_DD'] = (df['QQQ'] / df['QQQ_High52']) - 1 
    df['UUP_MA50'] = df['UUP'].rolling(window=50).mean() 
    for sec in SECTOR_TICKERS: df[f'{sec}_1M'] = df[sec].pct_change(periods=21)
    return df.dropna()

@st.cache_data(ttl=900)
def fetch_macro_news():
    headlines_for_ai, news_items = [], []
    try:
        search_query = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req).read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:12]
        for item in items:
            t, l, d = item.find('title').text, item.find('link').text, item.find('pubDate').text
            headlines_for_ai.append(t); news_items.append({"title": t, "link": l, "date": d[:-4]})
    except: pass
    return headlines_for_ai, news_items

with st.spinner('📰 데이터베이스 동기화 중...'):
    df = load_data()

# AMLS v4.5 코어 엔진 계산
last_row = df.iloc[-1]
vix_close, vix_ma5 = last_row['^VIX'], last_row['VIX_MA5']
qqq_close, qqq_ma50, qqq_ma200 = last_row['QQQ'], last_row['QQQ_MA50'], last_row['QQQ_MA200']
smh_close, smh_ma50, smh_3m, smh_1m, smh_rsi = last_row['SMH'], last_row['SMH_MA50'], last_row['SMH_3M_Ret'], last_row['SMH_1M_Ret'], last_row['SMH_RSI']

def get_target_v45(row):
    if row['^VIX'] > 40: return 4 
    if row['QQQ'] < row['QQQ_MA200']: return 3
    if row['QQQ'] >= row['QQQ_MA200'] and row['QQQ_MA50'] >= row['QQQ_MA200'] and row['VIX_MA5'] < 25: return 1 
    return 2

df['Target'] = df.apply(get_target_v45, axis=1)

res = []; curr = 3; pend = None; cnt = 0
for t in df['Target']:
    if t > curr: curr = t; pend = None; cnt = 0
    elif t < curr:
        if t == pend:
            cnt += 1; curr = t if cnt >= 5 else curr; pend = None if cnt >= 5 else pend; cnt = 0 if cnt >= 5 else cnt
        else: pend = t; cnt = 1
    else: pend = None; cnt = 0
    res.append(curr)
df['Regime'] = pd.Series(res, index=df.index).shift(1).bfill()

curr_regime = int(df.iloc[-1]['Regime'])
target_regime = int(df.iloc[-1]['Target'])
smh_c1, smh_c2, smh_c3 = smh_close > smh_ma50, (smh_3m > 0.05 or smh_1m > 0.10), smh_rsi > 50
smh_cond = smh_c1 and smh_c2 and smh_c3

def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if smh_ok else 'USD'
    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2: w['TQQQ'], w['QLD'], w['SSO'], w['GLD'], w['USD'], w['SPY'] = 0.15, 0.35, 0.20, 0.20, 0.10, 0.00
    elif reg == 3: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w

target_weights = get_weights_v45(curr_regime, smh_cond)

# ==========================================
# 2. 사이드바 (UI 스위치 통합)
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid rgba(139,94,60,0.1);">
            <h2 style="font-family: Georgia, serif; margin: 0; font-size: 1.8rem; color: #3A2E28; text-shadow: 1px 1px 0px #FFF;">RIMBERIO</h2>
            <h4 style="font-family: Georgia, serif; margin: 0; font-size: 1rem; color: #B26A47;">FINANCIAL GAZETTE</h4>
        </div>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "NAVIGATION MENU",
        ["📊 시장 분석관 (Home)", "🍫 8-Pack 레이더망", "📉 폭락장 아카이브", "📰 매크로 뉴스룸"],
        label_visibility="collapsed"
    )
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    
    ui_style = st.radio("🎨 UI 스타일 선택", ["Light Mode (Neo-Tactile)", "Dark Mode (Classic Finance)"])
    is_neo_style = ui_style == "Light Mode (Neo-Tactile)"
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="position: absolute; bottom: 10px; text-align: center; width: 100%; font-size: 0.8em; color: #8A7668;">
            Powered by AMLS V4.5 Engine<br>&copy; 2026 SEYOON.
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 통합 CSS 및 헤더 (조건부 스위칭)
# ==========================================
neo_tactile_css = """
<style>
    :root {
        --base-bg: #EBE5DF; --text-main: #3A2E28; --accent-primary: #B26A47;
        --shadow-dark: rgba(139, 94, 60, 0.25); --shadow-light: rgba(255, 255, 255, 0.85);
        --shadow-raised: 6px 6px 12px var(--shadow-dark), -6px -6px 12px var(--shadow-light);
        --shadow-inset: inset 4px 4px 8px var(--shadow-dark), inset -4px -4px 8px var(--shadow-light);
    }
    .stApp { background-color: var(--base-bg); color: var(--text-main); font-family: 'Pretendard', sans-serif; }
    [data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stSidebar"] { background-color: var(--base-bg); box-shadow: 4px 0px 10px var(--shadow-dark); border: none; }
    div.row-widget.stRadio > div > label { background-color: var(--base-bg); border-radius: 12px; box-shadow: var(--shadow-raised); transition: all 0.3s; }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) { box-shadow: var(--shadow-inset) !important; color: var(--accent-primary); }
    [data-testid="stMetric"] { background-color: var(--base-bg); border-radius: 12px; box-shadow: var(--shadow-raised); }
    div[data-testid="stMetricValue"] > div { color: var(--accent-primary); }
    div[data-testid="stButton"] > button { background: linear-gradient(145deg, #B26A47, #9A583A); color: #FFFDF7 !important; border-radius: 12px; box-shadow: 4px 4px 8px var(--shadow-dark), -4px -4px 8px var(--shadow-light); border:none; }
    div[data-testid="stAlert"] { background-color: var(--base-bg) !important; box-shadow: var(--shadow-inset); border: none; color: var(--text-main) !important;}
    .neo-card { background-color: var(--base-bg); border-radius: 20px; padding: 25px; min-height: 520px; box-shadow: var(--shadow-raised); display: flex; flex-direction: column; margin-bottom: 20px; }
    .neo-inset-box { background-color: var(--base-bg); border-radius: 12px; padding: 15px; box-shadow: var(--shadow-inset); text-align: center; margin-bottom: 20px;}
    .check-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(139,94,60,0.1); font-size: 0.95em; }
    .check-value { font-family: 'Courier New', monospace; font-weight: bold; color: var(--accent-primary); }
</style>
"""

rejected_dash_css = """
<style>
    :root {
        --bg-primary: #121418; --bg-secondary: #1C1F26; --accent-primary: #86A8E7; --accent-soxl: #E0E7FF;
        --text-main: #E5E7EB; --text-muted: #9CA3AF; --border-main: rgba(255, 255, 255, 0.08);
    }
    .stApp { background-color: var(--bg-primary); color: var(--text-main); }
    [data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stSidebar"] { background-color: var(--bg-secondary); border-right: 1px solid var(--border-main); }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) { background-color: rgba(134,168,231,0.1) !important; border: 1px solid var(--accent-primary); color: var(--accent-primary); }
    [data-testid="stMetric"] { background-color: var(--bg-secondary); border: 1px solid var(--border-main); border-radius: 8px; }
    div[data-testid="stMetricValue"] > div { color: var(--accent-primary); }
    div[data-testid="stButton"] > button { background-color: var(--accent-primary); color: #121418 !important; border-radius: 4px; border:none; }
    div[data-testid="stAlert"] { background-color: rgba(255,193,7,0.1) !important; border: 1px solid #FFC107; color: #FFC107 !important; }
    .metric-card { background-color: var(--bg-secondary); border: 1px solid var(--border-main); border-radius: 10px; padding: 25px; min-height: 520px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; flex-direction: column; margin-bottom: 20px;}
    .alert-panel { background-color: #121418; border: 1px solid var(--border-main); border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 25px; }
    .portfolio-card { background-color: var(--bg-secondary); border: 1px solid var(--border-main); border-radius: 10px; padding: 25px; min-height: 380px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .portfolio-rows { display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-main); padding: 12px 0; }
</style>
"""

if is_neo_style: st.markdown(neo_tactile_css, unsafe_allow_html=True)
else: st.markdown(rejected_dash_css, unsafe_allow_html=True)

st.markdown("""
<style>
    #MainMenu { visibility: hidden; } footer { visibility: hidden; }
    .main .block-container { max-width: 1300px; padding-top: 0rem; padding-bottom: 2rem; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Pretendard', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

h_color = "#3A2E28" if is_neo_style else "#E5E7EB"
h_accent = "#B26A47" if is_neo_style else "#86A8E7"
h_muted = "#8A7668" if is_neo_style else "#9CA3AF"
h_shadow = "2px 2px 4px rgba(255,255,255,0.8)" if is_neo_style else "2px 2px 4px rgba(0,0,0,0.5)"

st.markdown(f"""
<div style="padding-bottom: 15px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; margin-top: -20px; border-bottom: 2px solid rgba(139,94,60,0.1);">
    <div>
        <h1 style="font-family: Georgia, serif; font-size: 2.8em; margin: 0; color: {h_color}; text-shadow: {h_shadow};">RIMBERIO FINANCIAL GAZETTE</h1>
        <p style="font-size: 1.1em; letter-spacing: 1px; margin: 5px 0 0 0; font-weight: 700; color: {h_accent};">THE WALL STREET QUANTITATIVE JOURNAL</p>
    </div>
    <div style="text-align: right; font-weight: bold; color: {h_color};">
        <div style="font-size: 1.2em;">AMLS V4.5 ENGINE</div>
        <div style="font-size: 0.9em; color: {h_muted};">실시간 매크로 판독 터미널</div>
    </div>
</div>
""", unsafe_allow_html=True)

b_color = '#EBE5DF' if is_neo_style else '#121418'
t_color = '#3A2E28' if is_neo_style else '#E5E7EB'
chart_layout = dict(paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color), margin=dict(l=0, r=0, t=40, b=0))
radar_layout = dict(height=200, margin=dict(l=10, r=10, t=15, b=15), paper_bgcolor=b_color, plot_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
regime_colors = {1: 'rgba(0, 0, 0, 0.0)', 2: 'rgba(139, 94, 60, 0.05)' if is_neo_style else 'rgba(134, 168, 231, 0.03)', 3: 'rgba(178, 106, 71, 0.1)', 4: 'rgba(178, 106, 71, 0.2)'}
regime_info = {1: ("🟢 R1 (강세장)", "풀 가동"), 2: ("🟡 R2 (조정장)", "TQQQ 15% 방어"), 3: ("🟠 R3 (하락장)", "현금/금 대피"), 4: ("🔴 R4 (패닉장)", "최대 방어")}

# ==========================================
# 5. 페이지 라우팅
# ==========================================

# ------------------------------------------
# PAGE 1: 시장 분석관 (Home)
# ------------------------------------------
if page == "📊 시장 분석관 (Home)":
    st.subheader("I. 시장 분석관 (Market Intelligence)")

    if is_neo_style:
        def check_item(label, val, passed):
            icon = "<span style='color:#6B8E23;'>✔</span>" if passed else "<span style='color:#B26A47;'>✕</span>"
            return f"<div class='check-row'><span>{label}</span><span class='check-value'>{val} {icon}</span></div>"

        c1, c2, c3 = st.columns([1.2, 1.2, 1])
        with c1:
            st.markdown(f"""
            <div class="neo-card">
                <div style="font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px; color:#3A2E28;">🏛️ 현재 시장 국면</div>
                <div class="neo-inset-box"><h2 style="margin:0; color:#B26A47;">{regime_info[curr_regime][0]}</h2><p style="margin:0;">전략: {regime_info[curr_regime][1]}</p></div>
                {check_item('① VIX 임계점(<40)', f"{vix_close:.2f}", vix_close<=40)}
                {check_item('② 장기 지지(QQQ>200MA)', f"${qqq_close:.0f}", qqq_close>=qqq_ma200)}
                {check_item('③ 추세(50MA≥200MA)', f"${qqq_ma50:.0f}", qqq_ma50>=qqq_ma200)}
                {check_item('④ 노이즈(VIX 5일<25)', f"{vix_ma5:.2f}", vix_ma5<25)}
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="neo-card">
                <div style="font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px; color:#3A2E28;">💻 반도체(SOXL) 판독관</div>
                <div class="neo-inset-box"><h2 style="margin:0; color:#6B8E23;">{'🔥 SOXL 승인' if smh_cond else '🛡️ USD 기각'}</h2></div>
                {check_item('① 정배열(SMH>50MA)', f"${smh_close:.1f}", smh_c1)}
                {check_item('② 모멘텀 확인', f"{smh_3m*100:.1f}%", smh_c2)}
                {check_item('③ 심리(RSI>50)', f"{smh_rsi:.1f}", smh_c3)}
            </div>
            """, unsafe_allow_html=True)
        with c3:
            rows = "".join([f"<div class='check-row'><span>{k}</span><span class='check-value'>{v*100:.0f}%</span></div>" for k, v in target_weights.items() if v > 0])
            st.markdown(f"""<div class="neo-card"><div style="font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px; color:#3A2E28;">🛒 목표 비중</div>{rows}</div>""", unsafe_allow_html=True)

    else:
        c1, c2, c3 = st.columns([1.2, 1.2, 1])
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-end;"><h3>🏛️ 시장 국면</h3></div>
                <div class="alert-panel"><h1 style="color:var(--accent-primary); margin:0;">{regime_info[curr_regime][0]}</h1></div>
                <ul>
                    <li>① VIX 임계점: {vix_close:.2f} {'✅' if vix_close<=40 else '❌'}</li>
                    <li>② 장기 지지선: ${qqq_close:.0f} {'✅' if qqq_close>=qqq_ma200 else '❌'}</li>
                    <li>③ 추세 정배열: ${qqq_ma50:.0f} {'✅' if qqq_ma50>=qqq_ma200 else '❌'}</li>
                    <li>④ 노이즈 필터: {vix_ma5:.2f} {'✅' if vix_ma5<25 else '❌'}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            status = '🔥 SOXL 승인' if smh_cond else '🛡️ USD 기각'
            color = 'var(--accent-soxl)' if smh_cond else 'var(--accent-primary)'
            st.markdown(f"""
            <div class="metric-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-end;"><h3>💻 SOXL 판독관</h3></div>
                <div class="alert-panel"><h1 style="color:{color}; margin:0;">{status}</h1></div>
                <ul>
                    <li>① 정배열 추세: ${smh_close:.1f} {'✅' if smh_c1 else '❌'}</li>
                    <li>② 상승 모멘텀: {smh_3m*100:.1f}% {'✅' if smh_c2 else '❌'}</li>
                    <li>③ 심리 강도: {smh_rsi:.1f} {'✅' if smh_c3 else '❌'}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            rows = "".join([f"<div class='portfolio-rows'><strong>{k}</strong><b style='color:var(--accent-primary);'>{v*100:.0f}%</b></div>" for k, v in target_weights.items() if v > 0])
            st.markdown(f"<div class='portfolio-card'><h3>🛒 목표 포트폴리오</h3>{rows}</div>", unsafe_allow_html=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ vs 200MA", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200MA", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (5D MA)", f"{last_row['VIX_MA5']:.2f}", f"종가:{last_row['^VIX']:.2f}")
    m4.metric("반도체 1M", f"{last_row['SMH_1M_Ret']*100:+.2f}%")
    m5.metric("반도체 3M", f"{last_row['SMH_3M_Ret']*100:+.2f}%")

    if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
        st.warning("⚠️ **[선행 경보]** TQQQ가 200일선을 이탈했습니다. 하락 전조 주의.")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    df_recent = df.iloc[-500:]
    
    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color=t_color, width=2)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200일선', line=dict(color='#B26A47' if is_neo_style else '#86A8E7', width=2, dash='dash')))
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color=t_color, width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200일선', line=dict(color='#B26A47' if is_neo_style else '#86A8E7', width=2, dash='dash')))
    
    for i in range(1, len(df_recent)):
        if df_recent['Regime'].iloc[i-1] != df_recent['Regime'].iloc[i] or i == 1: start_idx = df_recent.index[i]; curr_r = df_recent['Regime'].iloc[i]
        if i == len(df_recent)-1 or df_recent['Regime'].iloc[i] != df_recent['Regime'].iloc[i+1]:
            fig_qqq.add_vrect(x0=start_idx, x1=df_recent.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)
            fig_tqqq.add_vrect(x0=start_idx, x1=df_recent.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)
            
    fig_qqq.update_layout(title="[시스템 기준] QQQ vs 200일 이평선", height=350, **chart_layout)
    fig_tqqq.update_layout(title="[조기 경보] TQQQ vs 200일 이평선", height=350, **chart_layout)
    
    with chart_col1: st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2: st.plotly_chart(fig_tqqq, use_container_width=True)

# ------------------------------------------
# PAGE 2: 8-PACK 레이더망 (오류 완벽 해결본)
# ------------------------------------------
elif page == "🍫 8-Pack 레이더망":
    
    # 상단 안내 문구
    if is_neo_style:
        st.markdown("""
        <div class="neo-inset-box" style="text-align: left; padding: 20px;">
            <h4 style="margin-top: 0; color: var(--accent-primary);">"감정을 배제하고, 냉혹한 진실에만 집중하십시오."</h4>
            <p style="font-size: 1.05em; line-height: 1.6; margin-bottom: 0;">겉으로 평온해 보이는 시장을 정밀 분석합니다. 군중의 환희를 신뢰하지 마십시오.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-main); padding: 20px; border-radius: 8px; margin-bottom: 25px;">
            <h4 style="margin-top: 0; color: var(--accent-primary);">"자본의 도피처를 찾으십시오."</h4>
            <p style="font-size: 1.05em; line-height: 1.6; margin-bottom: 0;">8-Pack 카드는 시장의 변심을 가장 먼저 감지하는 안테나입니다. 숫자의 진실에 집중하십시오.</p>
        </div>
        """, unsafe_allow_html=True)
    
    df_view = df.iloc[-120:]
    row1 = st.columns(4)
    row2 = st.columns(4)
    line_c = '#3A2E28' if is_neo_style else '#86A8E7'
    dash_c = '#B26A47' if is_neo_style else '#E5E7EB'
    
    # 1. 스마트 DCA
    with row1[0]:
        st.markdown("##### 1. 스마트 DCA (RSI)")
        qqq_rsi = last_row['QQQ_RSI'] 
        
        # 🚨 에러가 났던 삼항 연산자를 안전한 if-elif-else 구조로 완전히 분리했습니다!
        if qqq_rsi < 40:
            st.success("🔥 공포 매수 구간")
        elif qqq_rsi > 70:
            st.error("⚠️ 단기 과열 보류")
        else:
            st.info("🟢 정상 적립 유지")
            
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_RSI'], line=dict(color=line_c, width=2)))
        fig1.add_hline(y=70, line_dash='dash', line_color=dash_c)
        fig1.add_hline(y=30, line_dash='dash', line_color='#6B8E23')
        fig1.update_layout(**radar_layout, yaxis=dict(range=[10, 90]), showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    # 2. 멘탈 방어
    with row1[1]:
        st.markdown("##### 2. 멘탈 방어 (Drawdown)")
        qqq_dd = last_row['QQQ_DD']
        
        if qqq_dd < -0.20:
            st.error("🚨 약세장 (-20%)")
        elif qqq_dd < -0.10:
            st.warning("⚠️ 조정장 (-10%)")
        else:
            st.success("✅ 고점 순항 중")
            
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_DD'], fill='tozeroy', line=dict(color=dash_c, width=2)))
        fig2.update_layout(**radar_layout, yaxis=dict(tickformat='.0%'), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # 3. 시장 심리
    with row1[2]:
        st.markdown("##### 3. 시장 심리 (F&G)")
        vix_score = max(0, min(100, 100 - (last_row['^VIX'] - 12) / 28 * 100))
        dd_score = max(0, min(100, (qqq_dd + 0.20) / 0.20 * 100))
        rsi_score = max(0, min(100, qqq_rsi))
        fg_score = (vix_score + dd_score + rsi_score) / 3
        
        if fg_score < 30:
            st.success("🔥 극단적 공포")
        elif fg_score > 70:
            st.error("⚠️ 극단적 탐욕")
        else:
            st.info("🟢 중립 심리")
            
        fig3 = go.Figure(go.Indicator(
            mode="gauge+number", value=fg_score, domain={'x': [0, 1], 'y': [0, 1]},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': line_c},
                   'steps': [{'range': [0, 25], 'color': "rgba(178,106,71,0.7)"}, {'range': [25, 45], 'color': "rgba(178,106,71,0.3)"},
                             {'range': [45, 55], 'color': "rgba(139,94,60,0.1)"}, {'range': [55, 75], 'color': "rgba(107,142,35,0.3)"},
                             {'range': [75, 100], 'color': "rgba(107,142,35,0.7)"}]}
        ))
        fig3.update_layout(height=200, margin=dict(l=15, r=15, t=10, b=10), paper_bgcolor=b_color, font=dict(family="Pretendard", color=t_color))
        st.plotly_chart(fig3, use_container_width=True)

    # 4. 섹터 순환
    with row1[3]:
        st.markdown("##### 4. 섹터 순환 (1M)")
        sec_names = {'XLK': '기술', 'XLV': '헬스', 'XLF': '금융', 'XLY': '소비', 'XLC': '통신', 'XLI': '산업', 'XLP': '필수', 'XLE': '에너지', 'XLU': '유틸', 'XLRE': '부동산', 'XLB': '소재'}
        sec_data = [{'섹터': sec_names[s], '수익률': last_row[f'{s}_1M'] * 100} for s in SECTOR_TICKERS]
        sec_df = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
        top_sec, bot_sec = sec_df.iloc[-1]['섹터'], sec_df.iloc[0]['섹터']
        
        st.info(f"🏆 {top_sec} / 📉 {bot_sec}")
        
        fig4 = go.Figure(go.Bar(x=sec_df['수익률'], y=sec_df['섹터'], orientation='h', marker_color=[dash_c if val < 0 else line_c for val in sec_df['수익률']]))
        fig4.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    # 5. 채권 스프레드
    with row2[0]:
        st.markdown("##### 5. 채권 스프레드")
        if last_row['HYG_IEF_Ratio'] < last_row['HYG_IEF_MA50']:
            st.error("🚨 국채로 자본 도피")
        else:
            st.success("✅ 회사채 선호")
            
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_Ratio'], line=dict(color=line_c, width=2)))
        fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_MA50'], line=dict(color=dash_c, dash='dot')))
        fig5.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

    # 6. 시장 폭
    with row2[1]:
        st.markdown("##### 6. 시장 폭 (Breadth)")
        if last_row['QQQ_20d_Ret'] > 0 and last_row['QQQE_20d_Ret'] < 0:
            st.warning("⚠️ 대장주 쏠림 심화")
        else:
            st.success("✅ 고른 시장 상승")
            
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_20d_Ret'], name='QQQ', line=dict(color=line_c, width=2)))
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQE_20d_Ret'], name='QQQE', line=dict(color=dash_c, dash='dot')))
        fig6.update_layout(**radar_layout, showlegend=False, yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6, use_container_width=True)

    # 7. 안전 자산
    with row2[2]:
        st.markdown("##### 7. 안전 자산 (금/주식)")
        if last_row['GLD_SPY_Ratio'] > last_row['GLD_SPY_MA50']:
            st.warning("⚠️ 금으로 자금 피신")
        else:
            st.success("✅ 주식 선호도 우위")
            
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_Ratio'], line=dict(color=line_c, width=2)))
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_MA50'], line=dict(color=dash_c, dash='dot')))
        fig7.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig7, use_container_width=True)

    # 8. 달러 유동성
    with row2[3]:
        st.markdown("##### 8. 달러 유동성 (UUP)")
        if last_row['UUP'] > last_row['UUP_MA50']:
            st.error("🚨 강달러 압박 심화")
        else:
            st.success("✅ 달러 강세 진정")
            
        fig8 = go.Figure()
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP'], line=dict(color=line_c, width=2)))
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP_MA50'], line=dict(color=dash_c, dash='dot')))
        fig8.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig8, use_container_width=True)

# ------------------------------------------
# PAGE 3: 역사적 폭락장 아카이브
# ------------------------------------------
elif page == "📉 폭락장 아카이브":
    st.subheader("III. 역사적 폭락장 아카이브 (Crisis Archive)")
    st.write("하락장이 올 때마다 이 기록을 보며 멘탈을 통제하십시오. V4.5 시스템은 역사적 피바다 속에서 항상 안전 자산으로 도망쳐 있었습니다.")
    
    crises = {"2008 금융위기 (서브프라임)": ("2007-08-01", "2009-12-31"), "2020 코로나 팬데믹": ("2020-01-01", "2020-12-31"), "2022 인플레이션 쇼크": ("2021-11-01", "2023-03-31")}
    selected_crisis = st.selectbox("조회할 역사적 위기를 선택하십시오:", list(crises.keys()))
    s_date, e_date = crises[selected_crisis]
    
    try:
        df_crisis = df.loc[s_date:e_date]
        if len(df_crisis) > 0:
            crisis_fig = go.Figure()
            crisis_fig.add_trace(go.Scatter(x=df_crisis.index, y=df_crisis['QQQ'], name='QQQ (나스닥)', line=dict(color=t_color, width=2)))
            crisis_fig.add_trace(go.Scatter(x=df_crisis.index, y=df_crisis['QQQ_MA200'], name='200일선', line=dict(color='#B26A47' if is_neo_style else '#86A8E7', width=2, dash='dash')))
            
            r3_r4_days = 0
            for i in range(1, len(df_crisis)):
                if df_crisis['Regime'].iloc[i-1] != df_crisis['Regime'].iloc[i] or i == 1:
                    start_idx = df_crisis.index[i]
                    curr_r = df_crisis['Regime'].iloc[i]
                if i == len(df_crisis)-1 or df_crisis['Regime'].iloc[i] != df_crisis['Regime'].iloc[i+1]:
                    crisis_fig.add_vrect(x0=start_idx, x1=df_crisis.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)
                if df_crisis['Regime'].iloc[i] in [3, 4]: r3_r4_days += 1
                    
            crisis_fig.update_layout(title=f"V4.5 백테스트 궤적: {selected_crisis}", height=500, **chart_layout)
            st.plotly_chart(crisis_fig, use_container_width=True)
            st.info(f"💡 **분석:** 총 {len(df_crisis)} 거래일 중, V4.5 시스템은 **{r3_r4_days}일({r3_r4_days/len(df_crisis)*100:.1f}%)** 동안 안전 자산으로 방어했습니다.")
    except Exception as e:
        st.error("데이터 범위 오류: 데이터를 불러오지 못했습니다.")

# ------------------------------------------
# PAGE 4: MACRO NEWS & AI
# ------------------------------------------
elif page == "📰 매크로 뉴스룸":
    st.subheader("IV. 실시간 글로벌 매크로 뉴스 & AI 브리핑")
    
    headlines_for_ai, news_items = fetch_macro_news()

    with st.expander("✨ System-2 심층 추론 애널리스트 분석 (클릭하여 열기)", expanded=True):
        st.markdown("**(주의)** Streamlit Cloud의 `Secrets` 설정에 `GEMINI_API_KEY`를 먼저 등록해주십시오.")
        
        if st.button("🚀 심층 추론 요약 실행"):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("심층 추론 진행 중..."):
                        genai.configure(api_key=api_key)
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        if not available_models: st.error("AI 모델이 없습니다.")
                        else:
                            target_model = next((m for m in available_models if 'flash' in m.lower() or 'pro' in m.lower()), available_models[0])
                            clean_model_name = target_model.replace('models/', '')
                            model = genai.GenerativeModel(clean_model_name)
                            
                            prompt = (
                                "너는 1920년대 월스트리트의 날카롭고 이성적인 퀀트 애널리스트야. 고전적이고 단호한 비즈니스 신문 칼럼니스트의 말투를 사용해.\n"
                                "답변은 반드시 다음 3가지 목차만 포함해서 작성해. 1. 주요 뉴스 헤드라인 분류 및 초기 분석\n2. 현재 주식 시장의 핵심 쟁점 및 잠재적 리스크 도출\n3. 최종 고찰\n"
                                "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                            )
                            response = model.generate_content(prompt)
                            
                            # 순백색 배경 + 칠흑색 글씨 강제 적용 (다크모드에서도 흰색 유지)
                            st.markdown(f"""
                            <div style="background-color: #FFFFFF; border-radius: 12px; padding: 20px; box-shadow: inset 4px 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                                <h3 style="color: #1A1A1A; border-bottom: 2px solid #1A1A1A; padding-bottom: 10px; margin-top: 0;">✅ 심층 추론 분석 완료 ({clean_model_name})</h3>
                                <div style="font-size: 1.05em; line-height: 1.6; color: #000000;">
                                    {response.text.replace(chr(10), '<br>')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander("📋 텍스트 복사하기"): st.code(response.text, language="markdown")
            except KeyError:
                st.error("🚨 Streamlit Secrets에 'GEMINI_API_KEY'를 설정해주세요.")
            except Exception as e:
                st.error(f"오류: {e}")

    st.divider()
    st.markdown("#### 🖼️ 최신 경제 헤드라인 갤러리")
    if news_items:
        cols = st.columns(3)
        c_bg = '#FFFFFF' if not is_neo_style else '#FFFDF7' 
        c_brd = '1px solid var(--border-main)' if not is_neo_style else 'none'
        c_shd = 'none' if not is_neo_style else 'var(--shadow-raised)'
        
        for idx, item in enumerate(news_items):
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color: {c_bg}; border: {c_brd}; padding: 15px; margin-bottom: 15px; border-radius: 12px; height: 140px; box-shadow: {c_shd}; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-weight: bold; font-size: 1.05em; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">
                        <a href="{item['link']}" target="_blank" style="color: var(--text-main); text-decoration: none;">{item['title']}</a>
                    </div>
                    <div style="color: var(--accent-primary); font-size: 0.85em; margin-top: 10px; font-weight: bold;">
                        {item['date']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다. (15분 후 갱신)")
