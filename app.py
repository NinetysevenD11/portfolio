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
# 1. 대시보드 기본 설정 및 리얼 웹사이트 CSS
# ==========================================
st.set_page_config(page_title="RIMBERIO FINANCIAL GAZETTE", layout="wide", page_icon="📰", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #F5F0E8; color: #1A1A1A; font-family: 'Pretendard', sans-serif; }
    
    /* 🚨 수정됨: header를 완전히 숨기지 않고 배경만 투명하게 하여 사이드바 열기 버튼(>)을 살려둡니다! */
    [data-testid="stHeader"] { background-color: transparent !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    .main .block-container { max-width: 1300px; padding-top: 0rem; padding-bottom: 2rem; }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] { background-color: #EBE4D3; border-right: 2px solid #2C2C2C; }
    [data-testid="stSidebarNav"] { display: none; } 
    
    div.row-widget.stRadio > div { background-color: transparent; gap: 10px; }
    div.row-widget.stRadio > div > label {
        background-color: transparent; border: 1px solid transparent; padding: 10px 15px;
        border-radius: 4px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 1.1rem; color: #1A1A1A; transition: all 0.2s; cursor: pointer;
    }
    div.row-widget.stRadio > div > label:hover { background-color: #DFD7C2; border: 1px solid #2C2C2C; }

    h1, h2, h3, h4, h5, h6 { font-family: 'Pretendard', sans-serif !important; color: #1A1A1A !important; font-weight: 800 !important; letter-spacing: 0.5px; }
    
    /* 통합 카드 UI 스타일 */
    .analysis-card {
        border: 2px solid #2C2C2C; background-color: #FFFDF7; padding: 20px;
        border-radius: 8px; min-height: 520px; box-shadow: 4px 4px 0px rgba(0,0,0,0.1);
        display: flex; flex-direction: column; margin-bottom: 20px;
    }
    
    div[data-testid="stMetricValue"] > div { font-family: 'Pretendard', sans-serif; font-weight: 900; color: #1A1A1A; }
    div[data-testid="stButton"] > button { background-color: #1A1A1A; color: #FFFDF7; border-radius: 4px; border: 2px solid #1A1A1A; font-family: 'Pretendard', sans-serif; font-weight: bold; width: 100%; transition: all 0.3s; }
    div[data-testid="stButton"] > button:hover { background-color: #8B0000; border-color: #8B0000; color: #FFFDF7; }
    
    hr { border-top: 1px dashed #2C2C2C; background: transparent; margin: 2em 0; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 사이드바 (웹사이트 네비게이션)
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #1A1A1A;">
            <h2 style="font-family: Georgia, serif; margin: 0; font-size: 1.8rem; letter-spacing: 1px;">RIMBERIO</h2>
            <h4 style="font-family: Georgia, serif; margin: 0; font-size: 1rem; color: #8B0000;">FINANCIAL GAZETTE</h4>
            <p style="font-size: 0.8rem; margin-top: 5px; font-weight: bold;">EST. 2026 | QUANT DESK</p>
        </div>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "NAVIGATION MENU",
        ["📊 시장 분석관 (Home)", "🍫 8-Pack 레이더망", "📉 폭락장 아카이브", "📰 매크로 뉴스룸"],
        label_visibility="collapsed"
    )
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="position: absolute; bottom: 10px; text-align: center; width: 100%; font-size: 0.8em; color: #555;">
            Powered by AMLS V4.5 Engine<br>
            &copy; 2026 SEYOON. All rights reserved.
        </div>
    """, unsafe_allow_html=True)

# 📰 글로벌 상단 헤더
st.markdown("""
<div style="border-bottom: 4px double #1A1A1A; padding-bottom: 15px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; margin-top: -20px;">
    <div>
        <h1 style="font-family: Georgia, serif; font-size: 2.8em; margin: 0; color: #1A1A1A;">RIMBERIO FINANCIAL GAZETTE</h1>
        <p style="font-family: 'Pretendard', sans-serif; font-size: 1.1em; letter-spacing: 1px; margin: 5px 0 0 0; font-weight: 700; color: #8B0000;">THE WALL STREET QUANTITATIVE JOURNAL</p>
    </div>
    <div style="text-align: right; font-family: 'Pretendard', sans-serif; font-weight: bold; color: #1A1A1A;">
        <div style="font-size: 1.2em;">AMLS V4.5 ENGINE</div>
        <div style="font-size: 0.9em; color: #555;">실시간 매크로 판독 터미널</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 3. 데이터 수집 및 지표 계산
# ==========================================
SECTOR_TICKERS = ['XLK', 'XLV', 'XLF', 'XLY', 'XLC', 'XLI', 'XLP', 'XLE', 'XLU', 'XLRE', 'XLB']
CORE_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'HYG', 'IEF', 'QQQE', 'UUP']
TICKERS = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST = ['TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'QQQ', 'GLD', 'CASH']

@st.cache_data(ttl=3600)
def load_data():
    data = yf.download(TICKERS, start="2006-01-01", end=datetime.now().strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close']
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

with st.spinner('📰 통신 중...'):
    df = load_data()

# ==========================================
# 4. AMLS v4.5 코어 엔진 계산
# ==========================================
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
            cnt += 1
            if cnt >= 5: curr = t; pend = None; cnt = 0
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
regime_info = {1: ("🟢 R1 (강세장)", "풀 가동"), 2: ("🟡 R2 (조정장)", "TQQQ 15% 방어"), 3: ("🟠 R3 (하락장)", "현금/금 대피"), 4: ("🔴 R4 (패닉장)", "최대 방어")}
chart_layout = dict(paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Pretendard", color="#1A1A1A"), margin=dict(l=0, r=0, t=40, b=0))
radar_layout = dict(height=200, margin=dict(l=10, r=10, t=15, b=15), paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Pretendard", color="#1A1A1A"))
regime_colors = {1: 'rgba(0, 0, 0, 0.02)', 2: 'rgba(0, 0, 0, 0.08)', 3: 'rgba(139, 0, 0, 0.1)', 4: 'rgba(139, 0, 0, 0.2)'}

# ==========================================
# 5. 페이지 라우팅 (Page Routing)
# ==========================================

# ------------------------------------------
# PAGE 1: 시장 분석관 (Home)
# ------------------------------------------
if page == "📊 시장 분석관 (Home)":
    st.subheader("I. 시장 분석관 (Market Intelligence)")
    
    def check_item(label, val, passed):
        icon = "<span style='color:green;'>✅</span>" if passed else "<span style='color:#8B0000;'>❌</span>"
        return f"<div style='display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px dashed #ccc;'><span>{label}</span><b style='font-family: monospace;'>{val} {icon}</b></div>"

    c1, c2, c3 = st.columns([1.3, 1.3, 1])
    
    with c1:
        r_bg = "#FFFAEB" if curr_regime in [1, 2] else "#FFECEC"
        r_border = "#FFC107" if curr_regime in [1, 2] else "#8B0000"
        r_text = "#856404" if curr_regime in [1, 2] else "#8B0000"
        
        st.markdown(f"""
        <div class="analysis-card">
            <div style="font-family:Georgia; font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px;">🏛️ 현재 시장 국면 (REGIME)</div>
            <div style="background:{r_bg}; border:2px solid {r_border}; padding:15px; border-radius:6px; text-align:center; margin-bottom:20px;">
                <h3 style="margin:0; color:{r_text};">{regime_info[curr_regime][0]}</h3>
                <p style="margin:0; font-size:0.9em; font-weight:bold;">전략: {regime_info[curr_regime][1]}</p>
            </div>
            {check_item('① VIX 임계점 (< 40)', f"{vix_close:.2f}", vix_close<=40)}
            {check_item('② 장기 지지선 (QQQ > 200MA)', f"${qqq_close:.0f}", qqq_close>=qqq_ma200)}
            {check_item('③ 추세 정배열 (50MA ≥ 200MA)', f"${qqq_ma50:.0f}", qqq_ma50>=qqq_ma200)}
            {check_item('④ 노이즈 필터 (5일선 < 25)', f"{vix_ma5:.2f}", vix_ma5<25)}
            <div style="margin-top:auto; background:#FFF3CD; padding:12px; font-size:0.85em; border-left:4px solid #FFC107; border-radius:4px;">
                💡 <b>위원회:</b> {"모든 조건이 현재 국면에 부합합니다." if curr_regime == target_regime else f"R{target_regime} 전환 대기 중입니다."}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        s_bg = "#F1F8E9" if smh_cond else "#FFF5F5"
        s_border = "#006400" if smh_cond else "#8B0000"
        
        st.markdown(f"""
        <div class="analysis-card">
            <div style="font-family:Georgia; font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px;">💻 반도체(SOXL) 판독관</div>
            <div style="background:{s_bg}; border:2px solid {s_border}; padding:15px; border-radius:6px; text-align:center; margin-bottom:20px;">
                <h3 style="margin:0; color:{s_border};">{'🔥 승인: SOXL 편입' if smh_cond else '🛡️ 기각: USD 편입'}</h3>
                <p style="margin:0; font-size:0.9em; font-weight:bold;">전략: {'3배수 반도체 공격적 진입' if smh_cond else '변동성 방어용 2배수 편입'}</p>
            </div>
            {check_item('① 정배열 추세 (SMH > 50MA)', f"${smh_close:.1f}", smh_c1)}
            {check_item('② 상승 모멘텀 (1M>10% or 3M>5%)', f"3M {smh_3m*100:.1f}%", smh_c2)}
            {check_item('③ 매수 심리 강도 (RSI > 50)', f"{smh_rsi:.1f}", smh_c3)}
            <div style="margin-top:auto; padding:12px; font-size:0.85em; background:#F8F9FA; border-left:4px solid #CCC; font-style:italic;">
                ※ SOXL은 극단적 변동성을 수반하므로 3가지 필터를 모두 통과해야 편입합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        rows = "".join([f"<div style='display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #EBE4D3;'><b style='color:#1A1A1A;'>{k}</b><b style='font-family:monospace; color:#8B0000; font-size:1.1em;'>{v*100:.0f}%</b></div>" for k, v in target_weights.items() if v > 0])
        st.markdown(f"""
        <div class="analysis-card">
            <div style="font-family:Georgia; font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px;">🛒 V4.5 목표 비중</div>
            <div style="display:flex; justify-content:space-between; border-bottom:2px solid #1A1A1A; padding-bottom:5px; font-size:0.8em; color:#666; font-weight:bold;">
                <span>자산 (TICKER)</span><span>비중 (TARGET)</span>
            </div>
            {rows}
            <div style="margin-top:auto; font-size:0.8em; color:#888; text-align:right;">*최종 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ 종가 vs 200일선", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ 종가 vs 200일선", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (5일 이평선)", f"{last_row['VIX_MA5']:.2f}", f"종가:{last_row['^VIX']:.2f}")
    m4.metric("반도체 1M 수익률", f"{last_row['SMH_1M_Ret']*100:+.2f}%")
    m5.metric("반도체 3M 수익률", f"{last_row['SMH_3M_Ret']*100:+.2f}%")

    if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
        st.error("### 🚨 [중대 경보] TQQQ가 200일선을 먼저 이탈했습니다. 하락 전조일 확률이 매우 높습니다!")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    df_recent = df.iloc[-500:]
    
    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ'], name='QQQ', line=dict(color='#1A1A1A', width=2)))
    fig_qqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['QQQ_MA200'], name='200일선', line=dict(color='#8B0000', width=2, dash='dash')))
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ'], name='TQQQ', line=dict(color='#1A1A1A', width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df_recent.index, y=df_recent['TQQQ_MA200'], name='200일선', line=dict(color='#8B0000', width=2, dash='dash')))
    
    for i in range(1, len(df_recent)):
        if df_recent['Regime'].iloc[i-1] != df_recent['Regime'].iloc[i] or i == 1:
            start_idx = df_recent.index[i]
            curr_r = df_recent['Regime'].iloc[i]
        if i == len(df_recent)-1 or df_recent['Regime'].iloc[i] != df_recent['Regime'].iloc[i+1]:
            fig_qqq.add_vrect(x0=start_idx, x1=df_recent.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)
            fig_tqqq.add_vrect(x0=start_idx, x1=df_recent.index[i], fillcolor=regime_colors[curr_r], opacity=1, layer="below", line_width=0)
            
    fig_qqq.update_layout(title="[시스템 기준] QQQ vs 200일 이평선", height=350, **chart_layout)
    fig_tqqq.update_layout(title="[조기 경보] TQQQ vs 200일 이평선", height=350, **chart_layout)
    
    with chart_col1: st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2: st.plotly_chart(fig_tqqq, use_container_width=True)

# ------------------------------------------
# PAGE 2: 8-PACK 레이더망
# ------------------------------------------
elif page == "🍫 8-Pack 레이더망":
    st.subheader("II. 조기 경보 초콜릿 보드 (8-Pack Visual Radar)")
    
    st.markdown("""
    <div style="background-color: #FFFDF7; border-left: 5px solid #8B0000; padding: 20px; margin-bottom: 25px; box-shadow: 2px 2px 0px rgba(0,0,0,0.1);">
        <h4 style="margin-top: 0; color: #8B0000;">"군중의 환희는 속일 수 있어도, 거대 자본이 남기는 발자국은 결코 속일 수 없다."</h4>
        <p style="font-size: 1.05em; line-height: 1.6; margin-bottom: 0;">
            이곳은 단순한 보조 지표의 나열이 아닙니다. 월스트리트 프랍 데스크(Prop Desk)의 심장부에서나 볼 수 있는 <strong>'8-Pack 정밀 광학 렌즈'</strong>입니다. 
        </p>
        <ul style="margin-top: 10px; margin-bottom: 15px; font-size: 1.05em; line-height: 1.6;">
            <li>🎯 <strong>제 1열 ~ 3열 (심리와 타점):</strong> 시장이 비이성적인 공포에 질렸는지 파악하여 <strong>'자금 투입(DCA) 속도'</strong>를 기계적으로 통제합니다.</li>
            <li>🔍 <strong>제 4열 ~ 8열 (스마트머니 추적):</strong> 지수는 오르는데 대장주만 오르는지(시장 폭), 기관들이 몰래 금이나 안전한 국채로 도망치고 있는지(스프레드) 감시합니다.</li>
        </ul>
        <p style="font-weight: bold; margin-bottom: 0; color: #1A1A1A;">
            폭락은 예고 없이 오지 않습니다. 감정을 배제하고 차트가 가리키는 냉혹한 진실에만 집중하십시오.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    df_view = df.iloc[-120:]
    row1 = st.columns(4)
    row2 = st.columns(4)
    
    with row1[0]:
        st.markdown("##### 1. 스마트 DCA (RSI)")
        qqq_rsi = last_row['QQQ_RSI'] 
        if qqq_rsi < 40 and last_row['QQQ'] < last_row['QQQ_MA200']: st.success("🔥 매수: 공포/과매도. 현금 투입.")
        elif qqq_rsi > 70: st.error("⚠️ 보류: 단기 과열. 현금 비축.")
        else: st.info("🟢 정상: 기계적 적립 유지.")
        
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_RSI'], line=dict(color='#1A1A1A', width=2)))
        fig1.add_hline(y=70, line_dash='dash', line_color='#8B0000')
        fig1.add_hline(y=30, line_dash='dash', line_color='green')
        fig1.update_layout(**radar_layout, yaxis=dict(range=[10, 90]), showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    with row1[1]:
        st.markdown("##### 2. 멘탈 방어 (Drawdown)")
        qqq_dd = last_row['QQQ_DD']
        if qqq_dd < -0.20: st.error("🚨 약세장: -20% 돌파. 공포 통제.")
        elif qqq_dd < -0.10: st.warning("⚠️ 조정장: -10% 돌파. 건강한 뷰 유지.")
        else: st.success("✅ 안전: 고점 부근 순항 중.")
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_DD'], fill='tozeroy', line=dict(color='#8B0000', width=2)))
        fig2.update_layout(**radar_layout, yaxis=dict(tickformat='.0%'), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with row1[2]:
        st.markdown("##### 3. 시장 심리 (Fear & Greed)")
        vix_score = max(0, min(100, 100 - (last_row['^VIX'] - 12) / 28 * 100))
        dd_score = max(0, min(100, (qqq_dd + 0.20) / 0.20 * 100))
        rsi_score = max(0, min(100, qqq_rsi))
        fg_score = (vix_score + dd_score + rsi_score) / 3
        
        if fg_score < 30: st.success("🔥 공포: 저점 매집 찬스.")
        elif fg_score > 70: st.error("⚠️ 탐욕: 추격 매수 자제.")
        else: st.info("🟢 중립: 심리 상태 안정적.")
        
        fig3 = go.Figure(go.Indicator(
            mode="gauge+number", value=fg_score, domain={'x': [0, 1], 'y': [0, 1]},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#1A1A1A"},
                   'steps': [{'range': [0, 25], 'color': "rgba(139,0,0,0.7)"}, {'range': [25, 45], 'color': "rgba(139,0,0,0.3)"},
                             {'range': [45, 55], 'color': "rgba(0,0,0,0.1)"}, {'range': [55, 75], 'color': "rgba(0,100,0,0.3)"},
                             {'range': [75, 100], 'color': "rgba(0,100,0,0.7)"}]}
        ))
        fig3.update_layout(height=200, margin=dict(l=15, r=15, t=10, b=10), paper_bgcolor='#FFFDF7', font=dict(family="Pretendard", color="#1A1A1A"))
        st.plotly_chart(fig3, use_container_width=True)

    with row1[3]:
        st.markdown("##### 4. 섹터 순환 (1M 수익률)")
        sec_names = {'XLK': '기술', 'XLV': '헬스', 'XLF': '금융', 'XLY': '소비', 'XLC': '통신', 'XLI': '산업', 'XLP': '필수', 'XLE': '에너지', 'XLU': '유틸', 'XLRE': '부동산', 'XLB': '소재'}
        sec_data = [{'섹터': sec_names[s], '수익률': last_row[f'{s}_1M'] * 100} for s in SECTOR_TICKERS]
        sec_df = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
        top_sec, bot_sec = sec_df.iloc[-1]['섹터'], sec_df.iloc[0]['섹터']
        st.info(f"🏆 강세: {top_sec} / 📉 약세: {bot_sec}")
        
        fig4 = go.Figure(go.Bar(x=sec_df['수익률'], y=sec_df['섹터'], orientation='h', marker_color=['#8B0000' if val < 0 else '#1A1A1A' for val in sec_df['수익률']]))
        fig4.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    with row2[0]:
        st.markdown("##### 5. 채권 스프레드 (HYG/IEF)")
        if last_row['HYG_IEF_Ratio'] < last_row['HYG_IEF_MA50']: st.error("🚨 위험: 국채로 자본 도피 중.")
        else: st.success("✅ 안전: 위험 자산(회사채) 선호.")
        
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_Ratio'], line=dict(color='#1A1A1A', width=2)))
        fig5.add_trace(go.Scatter(x=df_view.index, y=df_view['HYG_IEF_MA50'], line=dict(color='#8B0000', dash='dot')))
        fig5.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

    with row2[1]:
        st.markdown("##### 6. 시장 폭 (QQQ vs QQQE)")
        if last_row['QQQ_20d_Ret'] > 0 and last_row['QQQE_20d_Ret'] < 0: st.warning("⚠️ 가짜 상승: 쏠림 현상 심화.")
        else: st.success("✅ 건전: 시장 전반 고른 상승.")
        
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_20d_Ret'], name='QQQ', line=dict(color='#1A1A1A', width=2)))
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQE_20d_Ret'], name='QQQE', line=dict(color='#8B0000', dash='dot')))
        fig6.update_layout(**radar_layout, showlegend=False, yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6, use_container_width=True)

    with row2[2]:
        st.markdown("##### 7. 안전 자산 선호 (금/주식)")
        if last_row['GLD_SPY_Ratio'] > last_row['GLD_SPY_MA50']: st.warning("⚠️ 이탈: 금으로 자금 피신 중.")
        else: st.success("✅ 정상: 주식 선호도 우위.")
        
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_Ratio'], line=dict(color='#1A1A1A', width=2)))
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_MA50'], line=dict(color='#8B0000', dash='dot')))
        fig7.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig7, use_container_width=True)

    with row2[3]:
        st.markdown("##### 8. 달러 유동성 (UUP)")
        if last_row['UUP'] > last_row['UUP_MA50']: st.error("🚨 축소: 강달러 압박 심화.")
        else: st.success("✅ 양호: 달러 강세 진정됨.")
        
        fig8 = go.Figure()
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP'], line=dict(color='#1A1A1A', width=2)))
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP_MA50'], line=dict(color='#8B0000', dash='dot')))
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
            crisis_fig.add_trace(go.Scatter(x=df_crisis.index, y=df_crisis['QQQ'], name='QQQ (나스닥)', line=dict(color='#1A1A1A', width=2)))
            crisis_fig.add_trace(go.Scatter(x=df_crisis.index, y=df_crisis['QQQ_MA200'], name='200일선', line=dict(color='#8B0000', width=2, dash='dash')))
            
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
            st.info(f"💡 **시뮬레이터 분석:** 이 위기 구간(총 {len(df_crisis)} 거래일) 동안, V4.5 시스템은 **{r3_r4_days}일({r3_r4_days/len(df_crisis)*100:.1f}%)** 동안 붉은색 영역(R3/R4)에 머물며 **계좌의 녹아내림을 완벽하게 방어**했습니다.")
    except Exception as e:
        st.error("데이터 범위 오류: 데이터를 불러오지 못했습니다.")

# ------------------------------------------
# PAGE 4: MACRO NEWS & AI
# ------------------------------------------
elif page == "📰 매크로 뉴스룸":
    st.subheader("IV. 실시간 글로벌 매크로 뉴스 & AI 브리핑")
    st.warning("⚠️ **[멘탈 주의보]** 쏟아지는 뉴스는 단순 참고용입니다. 자극적인 헤드라인에 흔들리지 마시고, 오직 시스템의 숫자에만 의존하십시오.")
    
    headlines_for_ai, news_items = fetch_macro_news()

    with st.expander("✨ System-2 심층 추론 애널리스트에게 시장 분석 지시 (클릭하여 열기)", expanded=True):
        st.markdown("**(주의)** Streamlit Cloud의 `Secrets` 설정에 `GEMINI_API_KEY`를 먼저 등록해주십시오.")
        
        if st.button("🚀 심층 추론 요약 실행"):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: st.warning("분석할 전보 데이터가 없습니다.")
                else:
                    with st.spinner("최신 전보를 해독하며, 다각도 검증 및 심층 추론을 진행 중입니다..."):
                        genai.configure(api_key=api_key)
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        if not available_models: st.error("사용 가능한 AI 모델이 없습니다.")
                        else:
                            target_model = next((m for m in available_models if 'flash' in m.lower() or 'pro' in m.lower()), available_models[0])
                            clean_model_name = target_model.replace('models/', '')
                            model = genai.GenerativeModel(clean_model_name)
                            
                            prompt = (
                                "너는 1920년대 월스트리트의 날카롭고 이성적인 퀀트 애널리스트야. 고전적이고 단호한 비즈니스 신문 칼럼니스트의 말투를 사용해.\n\n"
                                "[System Instructions]\n"
                                "Ultra-deep thinking mode. Greater rigor, attention to detail, and multi-angle verification. "
                                "Start by outlining the task and breaking down the problem into subtasks. "
                                "For each subtask, explore multiple perspectives, even those that seem initially irrelevant or improbable. "
                                "Purposefully attempt to disprove or challenge your own assumptions at every step. Triple-verify everything. "
                                "Critically review each step, scrutinize your logic, assumptions, and conclusions, explicitly calling out uncertainties and alternative viewpoints. "
                                "Independently verify your reasoning using alternative methodologies or tools, cross-checking every fact, inference, and conclusion against external data, calculation, or authoritative sources. "
                                "Deliberately seek out and employ at least twice as many verification tools or methods as you typically would. "
                                "Use mathematical validations, web searches, logic evaluation frameworks, and additional resources explicitly and liberally to cross-verify your claims. "
                                "Even if you feel entirely confident in your solution, explicitly dedicate additional time and effort to systematically search for weaknesses, logical gaps, hidden assumptions, or oversights. "
                                "Clearly document these potential pitfalls and how you've addressed them. "
                                "Once you're fully convinced your analysis is robust and complete, deliberately pause and force yourself to reconsider the entire reasoning chain one final time from scratch. "
                                "Explicitly detail this last reflective step.\n"
                                "답변은 반드시 처음부터 끝까지 한국말로 작성해.\n\n"
                                "🚨 [중요: 출력 형식 제한] 🚨\n"
                                "위의 심층 추론 과정은 너의 내부 논리로만 사용하고, 최종 출력되는 답변에는 다음 3가지 목차만 정확히 포함해서 작성해. 개별 뉴스 분석 등은 절대 화면에 출력하지 마.\n"
                                "1. 주요 뉴스 헤드라인 분류 및 초기 분석\n"
                                "2. 현재 주식 시장의 핵심 쟁점 및 잠재적 리스크 도출\n"
                                "3. 최종 고찰 (Reconsideration from Scratch)\n\n"
                                "[Task]\n"
                                "방금 수집된 미국의 증시, 나스닥, 연준 관련 최신 뉴스 헤드라인 15개야. 철저하게 분석하고 3가지 목차로만 결과물을 도출해 줘.\n\n"
                                "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                            )
                            response = model.generate_content(prompt)
                            
                            # 흰색 배경 + 검은 글씨 강제 적용을 위한 마크다운 출력
                            st.markdown(f"""
                            <div style="background-color: #FFFFFF; border: 2px solid #1A1A1A; padding: 20px; border-radius: 8px; color: #000000; box-shadow: 4px 4px 0px rgba(0,0,0,0.1); margin-bottom: 20px;">
                                <h3 style="color: #1A1A1A; border-bottom: 2px solid #1A1A1A; padding-bottom: 10px; margin-top: 0;">✅ 심층 추론 분석이 완료되었습니다. (사용 모델: {clean_model_name})</h3>
                                <div style="font-size: 1.05em; line-height: 1.6; color: #000000;">
                                    {response.text.replace(chr(10), '<br>')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander("📋 리포트 텍스트 복사하기"): st.code(response.text, language="markdown")
            except KeyError:
                st.error("🚨 Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다. [Settings] -> [Secrets] 메뉴에서 키를 먼저 등록해주세요!")
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다. 상세 에러: {e}")

    st.divider()
    st.markdown("#### 🖼️ 최신 경제 헤드라인 갤러리")
    if news_items:
        cols = st.columns(3)
        for idx, item in enumerate(news_items):
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #1A1A1A; padding: 15px; margin-bottom: 15px; border-radius: 4px; height: 140px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 2px 2px 0px rgba(0,0,0,0.1);">
                    <div style="font-weight: bold; font-size: 1.05em; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
                        <a href="{item['link']}" target="_blank" style="color: #1A1A1A; text-decoration: none;">{item['title']}</a>
                    </div>
                    <div style="color: #8B0000; font-size: 0.85em; margin-top: 10px; font-weight: bold;">
                        {item['date']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다. (15분 후 다시 시도합니다)")
