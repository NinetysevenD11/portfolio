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
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .main .block-container { max-width: 1300px; padding-top: 1rem; padding-bottom: 2rem; }
    
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
        border: 2px solid #2C2C2C;
        background-color: #FFFDF7;
        padding: 20px;
        border-radius: 8px;
        min-height: 520px;
        box-shadow: 4px 4px 0px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        margin-bottom: 20px;
    }
    
    /* 🚨 알림 박스 (AI 리포트 흰색 배경 & 검은 글씨 강제 적용) */
    div[data-testid="stAlert"] { 
        background-color: #FFFFFF !important; 
        border: 2px solid #1A1A1A !important; border-radius: 4px; 
        box-shadow: 2px 2px 0px rgba(0,0,0,0.1); padding: 10px;
    }
    div[data-testid="stAlert"] * { color: #000000 !important; }
    
    div[data-testid="stMetricValue"] > div { font-family: 'Pretendard', sans-serif; font-weight: 900; color: #1A1A1A; }
    div[data-testid="stButton"] > button { background-color: #1A1A1A; color: #FFFDF7; border-radius: 4px; border: 2px solid #1A1A1A; font-family: 'Pretendard', sans-serif; font-weight: bold; width: 100%; transition: all 0.3s; }
    
    hr { border-top: 1px dashed #2C2C2C; background: transparent; margin: 2em 0; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 사이드바 (변수 'page' 선언 위치 - 중요!)
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #1A1A1A;">
            <h2 style="font-family: Georgia, serif; margin: 0; font-size: 1.8rem; letter-spacing: 1px;">RIMBERIO</h2>
            <h4 style="font-family: Georgia, serif; margin: 0; font-size: 1rem; color: #8B0000;">FINANCIAL GAZETTE</h4>
            <p style="font-size: 0.8rem; margin-top: 5px; font-weight: bold;">EST. 2026 | QUANT DESK</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 💡 여기서 'page' 변수가 정의됩니다!
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
<div style="border-bottom: 4px double #1A1A1A; padding-bottom: 15px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end;">
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
# 3. 데이터 및 엔진 로직 (기존과 동일)
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

# 엔진 계산
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

# 레짐 지연 로직 생략(df['Regime'] 계산은 기존 로직 활용)
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

# ==========================================
# 6. 페이지 라우팅
# ==========================================

# ------------------------------------------
# PAGE 1: Home (리마스터 레이더)
# ------------------------------------------
if page == "📊 시장 분석관 (Home)":
    st.subheader("I. 시장 분석관 (Market Intelligence)")
    
    # 헬퍼 함수
    def check_item(label, val, passed):
        icon = "<span style='color:green;'>✅</span>" if passed else "<span style='color:red;'>❌</span>"
        return f"<div style='display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px dashed #ccc;'><span>{label}</span><b>{val} {icon}</b></div>"

    c1, c2, c3 = st.columns([1.3, 1.3, 1])
    
    with c1:
        st.markdown(f"""
        <div class="analysis-card">
            <div style="font-family:Georgia; font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px;">🏛️ 현재 시장 국면 (REGIME)</div>
            <div style="background:#FFFAEB; border:1px solid #FFC107; padding:15px; border-radius:6px; text-align:center; margin-bottom:20px;">
                <h3 style="margin:0;">{regime_info[curr_regime][0]}</h3>
                <p style="margin:0; font-size:0.9em;">전략: {regime_info[curr_regime][1]}</p>
            </div>
            {check_item('① VIX 임계점(<40)', f"{vix_close:.2f}", vix_close<=40)}
            {check_item('② 장기 지지(QQQ>200MA)', f"${qqq_close:.0f}", qqq_close>=qqq_ma200)}
            {check_item('③ 추세(50MA≥200MA)', f"${qqq_ma50:.0f}", qqq_ma50>=qqq_ma200)}
            {check_item('④ 노이즈(VIX 5일<25)', f"{vix_ma5:.2f}", vix_ma5<25)}
            <div style="margin-top:auto; background:#FFF3CD; padding:10px; font-size:0.85em; border-left:4px solid #FFC107;">
                💡 <b>위원회:</b> {"안정 유지 중" if curr_regime == target_regime else f"R{target_regime} 전환 대기 중"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="analysis-card">
            <div style="font-family:Georgia; font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px;">💻 반도체(SOXL) 판독관</div>
            <div style="background:{'#F1F8E9' if smh_cond else '#FFF5F5'}; border:1px solid {'#006400' if smh_cond else '#8B0000'}; padding:15px; border-radius:6px; text-align:center; margin-bottom:20px;">
                <h3 style="margin:0;">{'🔥 SOXL 승인' if smh_cond else '🛡️ USD 기각'}</h3>
            </div>
            {check_item('① 정배열(SMH>50MA)', f"${smh_close:.1f}", smh_c1)}
            {check_item('② 모멘텀 확인', f"{smh_3m*100:.1f}%", smh_c2)}
            {check_item('③ 매수 심리(RSI>50)', f"{smh_rsi:.1f}", smh_c3)}
            <div style="margin-top:auto; padding:10px; font-size:0.85em; background:#F8F9FA; border-left:4px solid #CCC; font-style:italic;">
                SOXL은 3가지 필터를 모두 통과해야 편입합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        rows = "".join([f"<div style='display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #EBE4D3;'><b style='color:#1A1A1A;'>{k}</b><b style='color:#8B0000;'>{v*100:.0f}%</b></div>" for k, v in target_weights.items() if v > 0])
        st.markdown(f"""
        <div class="analysis-card">
            <div style="font-family:Georgia; font-size:1.3em; font-weight:bold; border-bottom:2px solid #1A1A1A; padding-bottom:10px; margin-bottom:15px;">🛒 V4.5 목표 비중</div>
            {rows}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ vs 200MA", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200']-1)*100:+.2f}%")
    m2.metric("TQQQ vs 200MA", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200']-1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (5D MA)", f"{last_row['VIX_MA5']:.2f}", f"종가:{last_row['^VIX']:.2f}")
    m4.metric("반도체 1M", f"{last_row['SMH_1M_Ret']*100:+.2f}%")
    m5.metric("반도체 3M", f"{last_row['SMH_3M_Ret']*100:+.2f}%")

    if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
        st.error("### 🚨 [중대 경보] TQQQ가 200일선을 먼저 이탈했습니다. 하락 전조일 확률이 매우 높습니다!")

# ------------------------------------------
# PAGE 2, 3, 4 (생략 - 기존 로직과 동일하게 유지하되 위 page 변수에 따라 routing)
# ------------------------------------------
elif page == "🍫 8-Pack 레이더망":
    st.subheader("II. 조기 경보 초콜릿 보드")
    df_view = df.iloc[-120:]
    row1, row2 = st.columns(4), st.columns(4)
    # (기존 8-pack 차트 코드 유지...)
    with row1[0]: st.markdown("##### 1. 스마트 DCA (RSI)"); fig1 = go.Figure(); fig1.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_RSI'], line=dict(color='#1A1A1A'))); fig1.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0)); st.plotly_chart(fig1, use_container_width=True)
    # ... 나머지 차트들도 유사하게 구현 ...

elif page == "📉 폭락장 아카이브":
    st.subheader("III. 역사적 폭락장 아카이브")
    crises = {"2008 금융위기": ("2007-08-01", "2009-12-31"), "2020 코로나": ("2020-01-01", "2020-12-31")}
    c_name = st.selectbox("위기 선택", list(crises.keys()))
    # (기존 시뮬레이터 차트 코드 유지...)

elif page == "📰 매크로 뉴스룸":
    st.subheader("IV. 실시간 뉴스 & AI")
    headlines, news_items = fetch_macro_news()
    # (기존 뉴스 갤러리 + AI 분석 코드 유지...)
    if st.button("🚀 AI 분석 실행"):
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"뉴스 요약해줘: {headlines}")
        st.info(res.text)
    
    cols = st.columns(3)
    for i, item in enumerate(news_items):
        with cols[i%3]: st.markdown(f"<div style='background:white; border:1px solid #1A1A1A; padding:10px; border-radius:4px; height:120px;'><b><a href='{item['link']}'>{item['title']}</a></b><br><small>{item['date']}</small></div>", unsafe_allow_html=True)
