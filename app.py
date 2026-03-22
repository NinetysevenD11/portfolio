import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import warnings, json, os
warnings.filterwarnings('ignore')

st.set_page_config(page_title="AMLS V4.5", layout="wide", page_icon="📈", initial_sidebar_state="expanded")
SECTOR_TICKERS = ['XLK','XLV','XLF','XLY','XLC','XLI','XLP','XLE','XLU','XLRE','XLB']
CORE_TICKERS = ['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD','^VIX','HYG','IEF','QQQE','UUP']
TICKERS = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST = ['TQQQ','SOXL','USD','QLD','SSO','SPY','QQQ','GLD','CASH']
PORTFOLIO_FILE = 'portfolio_autosave.json'

def sanitize_portfolio():
    for a in ASSET_LIST:
        val = st.session_state.portfolio.get(a)
        if isinstance(val,(int,float)) or val is None: st.session_state.portfolio[a]={'shares':float(val or 0.0),'avg_price':1.0 if a=='CASH' else 0.0,'fx':1350.0}
        elif isinstance(val,dict):
            if 'shares' not in val: val['shares']=0.0
            if 'avg_price' not in val: val['avg_price']=1.0 if a=='CASH' else 0.0
            if 'fx' not in val: val['fx']=1350.0
        else: st.session_state.portfolio[a]={'shares':0.0,'avg_price':0.0,'fx':1350.0}
if 'portfolio' not in st.session_state:
    st.session_state.portfolio={a:{'shares':0.0,'avg_price':0.0,'fx':1350.0} for a in ASSET_LIST}
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE,'r') as f:
                for k,v in json.load(f).items(): st.session_state.portfolio[k]=v
        except: pass
sanitize_portfolio()
def save_portfolio_to_disk():
    try:
        with open(PORTFOLIO_FILE,'w') as f: json.dump(st.session_state.portfolio,f)
    except: pass

@st.cache_data(ttl=3600)
def load_data():
    end_date=datetime.now(); start_date=end_date-timedelta(days=900)
    data=yf.download(TICKERS,start=start_date.strftime("%Y-%m-%d"),end=end_date.strftime("%Y-%m-%d"),progress=False,auto_adjust=True)['Close']
    df=pd.DataFrame(index=data.index)
    for t in TICKERS: df[t]=data[t]
    df=df.ffill().bfill()
    df['QQQ_MA20']=df['QQQ'].rolling(20).mean();df['QQQ_MA50']=df['QQQ'].rolling(50).mean();df['QQQ_MA200']=df['QQQ'].rolling(200).mean()
    df['TQQQ_MA200']=df['TQQQ'].rolling(200).mean();df['SMH_MA50']=df['SMH'].rolling(50).mean()
    df['VIX_MA5']=df['^VIX'].rolling(5).mean();df['VIX_MA20']=df['^VIX'].rolling(20).mean()
    df['SMH_3M_Ret']=df['SMH'].pct_change(63);df['SMH_1M_Ret']=df['SMH'].pct_change(21);df['SMH_RSI']=ta.rsi(df['SMH'],length=14)
    df['HYG_IEF_Ratio']=df['HYG']/df['IEF'];df['HYG_IEF_MA20']=df['HYG_IEF_Ratio'].rolling(20).mean();df['HYG_IEF_MA50']=df['HYG_IEF_Ratio'].rolling(50).mean()
    df['QQQ_20d_Ret']=df['QQQ'].pct_change(20);df['QQQE_20d_Ret']=df['QQQE'].pct_change(20);df['QQQ_RSI']=ta.rsi(df['QQQ'],length=14)
    df['GLD_SPY_Ratio']=df['GLD']/df['SPY'];df['GLD_SPY_MA50']=df['GLD_SPY_Ratio'].rolling(50).mean()
    df['QQQ_High52']=df['QQQ'].rolling(252).max();df['QQQ_DD']=(df['QQQ']/df['QQQ_High52'])-1;df['UUP_MA50']=df['UUP'].rolling(50).mean()
    for sec in SECTOR_TICKERS: df[f'{sec}_1M']=df[sec].pct_change(21)
    return df.dropna()

@st.cache_data(ttl=60)
def fetch_realtime_prices():
    prices={}
    for t in ['QQQ','TQQQ','SMH','^VIX','HYG','IEF','UUP','GLD','SPY','SOXL','USD','QLD','SSO','USDKRW=X']:
        try:
            info=yf.Ticker(t).fast_info;p=info.get('last_price') or info.get('lastPrice')
            if p and p>0: prices[t]=float(p)
        except: pass
    return prices

@st.cache_data(ttl=900)
def fetch_macro_news():
    hl,ni=[],[]
    try:
        url=f"https://news.google.com/rss/search?q={urllib.parse.quote('미국증시 OR 연준 OR 나스닥')}&hl=ko&gl=KR&ceid=KR:ko"
        root=ET.fromstring(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})).read())
        for item in root.findall('.//item')[:12]:
            t,l,d=item.find('title').text,item.find('link').text,item.find('pubDate').text
            hl.append(t);ni.append({"title":t,"link":l,"date":d[:-4]})
    except: pass
    return hl,ni

with st.spinner('데이터 수집 중...'): df=load_data(); rt_prices=fetch_realtime_prices()
if df is None or df.empty: st.error("🚨 데이터를 불러오지 못했습니다. 새로고침 해주세요."); st.stop()

last_row=df.iloc[-1].copy(); rt_injected=[]
for ticker,price in rt_prices.items():
    if ticker in last_row.index and price>0: last_row[ticker]=price; rt_injected.append(ticker)
if 'QQQ' in rt_injected: last_row['QQQ_DD']=(last_row['QQQ']/last_row['QQQ_High52'])-1
if 'HYG' in rt_injected and 'IEF' in rt_injected: last_row['HYG_IEF_Ratio']=last_row['HYG']/last_row['IEF']
rt_ok=len(rt_injected)>=3; rt_label=f"LIVE ({len(rt_injected)})" if rt_ok else "DELAYED"
vix_close,vix_ma5,vix_ma20=last_row['^VIX'],last_row['VIX_MA5'],last_row['VIX_MA20']
qqq_close,qqq_ma50,qqq_ma200=last_row['QQQ'],last_row['QQQ_MA50'],last_row['QQQ_MA200']
smh_close,smh_ma50,smh_3m,smh_1m,smh_rsi=last_row['SMH'],last_row['SMH_MA50'],last_row['SMH_3M_Ret'],last_row['SMH_1M_Ret'],last_row['SMH_RSI']

def apply_asymmetric_delay(targets):
    res=[];c=3;p=None;n=0
    for t in targets:
        if t>c: c=t;p=None;n=0
        elif t<c:
            if t==p: n+=1
            else: p=t;n=1
            if n>=5: c=t;p=None;n=0
        else: p=None;n=0
        res.append(c)
    return pd.Series(res,index=targets.index).shift(1).bfill()
def get_target_v45(row):
    if row['^VIX']>40: return 4
    if row['QQQ']<row['QQQ_MA200']: return 3
    if row['QQQ_DD']<-0.10 and row['HYG_IEF_Ratio']<row['HYG_IEF_MA20']: return 3
    if row['QQQ']>=row['QQQ_MA200'] and row['QQQ_MA50']>=row['QQQ_MA200'] and row['VIX_MA20']<22 and row['HYG_IEF_Ratio']>=row['HYG_IEF_MA50']: return 1
    return 2
df['Target']=df.apply(get_target_v45,axis=1);df['Regime']=apply_asymmetric_delay(df['Target'])
live_regime=get_target_v45(last_row);hist_regime=int(df.iloc[-1]['Regime'])
curr_regime=live_regime if live_regime>hist_regime else hist_regime
smh_c1=smh_close>smh_ma50;smh_c2=(smh_3m>0.05 or smh_1m>0.10);smh_c3=smh_rsi>50;smh_cond=smh_c1 and smh_c2 and smh_c3
def get_weights_v45(reg,smh_ok):
    w={t:0.0 for t in ASSET_LIST};semi='SOXL' if smh_ok else 'USD'
    if reg==1: w['TQQQ'],w[semi],w['QLD'],w['SSO'],w['GLD'],w['SPY']=0.30,0.20,0.20,0.15,0.10,0.05
    elif reg==2: w['TQQQ'],w['QLD'],w['SSO'],w['USD'],w['GLD'],w['SPY']=0.15,0.30,0.25,0.10,0.15,0.05
    elif reg==3: w['GLD'],w['CASH'],w['QQQ']=0.50,0.35,0.15
    elif reg==4: w['GLD'],w['CASH'],w['QQQ']=0.50,0.40,0.10
    return w
target_weights=get_weights_v45(curr_regime,smh_cond)
regime_info={1:("🟢 R1 강세","풀 레버리지"),2:("🟡 R2 조정","TQQQ 15%"),3:("🟠 R3 하락","현금/금"),4:("🔴 R4 패닉","최대 방어")}
if curr_regime==live_regime: regime_msg="모든 조건이 현재 국면에 부합합니다."
elif live_regime>curr_regime: regime_msg=f"R{live_regime} 하향 즉시 반영 중"
else: regime_msg=f"R{live_regime} 신호 감지 — 5일 확인 대기 중"

# ==========================================
# CSS - Aether Dashboard (참고 이미지 재현)
# ==========================================
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap');
:root { --bg: #F3F1FA; --card: #FFFFFF; --text: #1A1A2E; --muted: #8E8EA0; --accent: #6C5CE7; --peach: #FDEBD0; --sky: #D6EAF8; --mint: #D5F5E3; --pink: #FADBD8; }

/* ── 배경: 연보라 메쉬 ── */
.stApp, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    background-image: radial-gradient(circle at 10% 20%, rgba(108,92,231,0.08) 0%, transparent 50%),
        radial-gradient(circle at 90% 80%, rgba(253,167,223,0.06) 0%, transparent 50%) !important;
    font-family: 'DM Sans', sans-serif !important; color: var(--text) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }
.main .block-container { max-width: 1400px; padding-top: 0.5rem; }

/* ── 사이드바: 깨끗한 흰색, 섹션 헤더 ── */
[data-testid="stSidebar"] { background: #FFFFFF !important; border-right: 1px solid #F0EDF6 !important; box-shadow: none !important; }
[data-testid="stSidebar"] [data-testid="stMarkdown"] p { color: var(--text) !important; }
div.row-widget.stRadio > div { gap: 2px !important; }
div.row-widget.stRadio > div > label {
    background: transparent !important; border: none !important; border-radius: 10px !important;
    padding: 8px 14px !important; margin: 0 4px !important; transition: all 0.15s !important;
}
div.row-widget.stRadio > div > label p { font-size: 0.85em !important; font-weight: 500 !important; color: #6B6B80 !important; }
div.row-widget.stRadio > div > label:hover { background: #F8F7FC !important; }
div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {
    background: #1A1A2E !important; border-radius: 10px !important;
}
div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) p { color: #FFFFFF !important; font-weight: 600 !important; }

/* ── 메트릭 숨기기 (커스텀 카드 사용) ── */
[data-testid="stMetric"] { display: none !important; }

/* ── 버튼 ── */
.stButton > button {
    background: var(--accent) !important; color: #FFF !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important; font-size: 0.9em !important;
    box-shadow: 0 4px 12px rgba(108,92,231,0.2) !important; transition: all 0.2s !important;
}
.stButton > button:hover { background: #5A4BD1 !important; transform: translateY(-1px) !important; }

/* ── Expander ── */
[data-testid="stExpander"] { background: var(--card) !important; border: 1px solid #F0EDF6 !important; border-radius: 16px !important; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 사이드바 UI
# ==========================================
sidebar_top = st.sidebar.container()
sidebar_top.markdown("""
<div style="padding: 8px 12px 16px 12px;">
    <div style="font-family:'Outfit'; font-size:1.5em; font-weight:800; color:#1A1A2E; letter-spacing:-1px;">⚡ AMLS</div>
    <div style="font-size:0.72em; font-weight:600; color:#8E8EA0; letter-spacing:1px; text-transform:uppercase;">V4.5 Finance Engine</div>
</div>""", unsafe_allow_html=True)
st.sidebar.markdown(f"<div style='font-size:0.7em; font-weight:700; color:#8E8EA0; padding:4px 16px; text-transform:uppercase; letter-spacing:1.5px;'>Main</div>", unsafe_allow_html=True)
page = st.sidebar.radio("MENU",
    ["📊 시장 분석관", "💼 포트폴리오", "🍫 8-Pack", "📈 백테스트", "📰 뉴스룸"],
    label_visibility="collapsed")
st.sidebar.markdown(f"""<div style='font-size:0.7em; font-weight:700; color:#8E8EA0; padding:12px 16px 4px 16px; text-transform:uppercase; letter-spacing:1.5px;'>Tools</div>
<div style='padding:4px 16px; font-size:0.82em; color:#6B6B80; font-weight:500;'>
    <div style='padding:6px 0;'>⏱ Data: {rt_label}</div>
    <div style='padding:6px 0;'>📅 {datetime.now().strftime('%Y.%m.%d')}</div>
</div>""", unsafe_allow_html=True)

# ==========================================
# 헬퍼: Aether 메트릭 카드 (파스텔 헤더 스트립 + 화살표 뱃지)
# ==========================================
def metric_card(title, subtitle, value, change, change_color, header_color):
    arrow_bg = "#E8F8F0" if change_color == "#00B894" else "#FDECEA"
    arrow_icon = "↗" if change_color == "#00B894" else "↘"
    return f"""<div style="background:#FFF; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6; transition:transform 0.2s; height:100%;">
    <div style="background:{header_color}; padding:14px 18px;">
        <div style="font-size:0.78em; font-weight:700; color:#1A1A2E;">{title}</div>
        <div style="font-size:0.68em; font-weight:500; color:#6B6B80; margin-top:2px;">{subtitle}</div>
    </div>
    <div style="padding:16px 18px; display:flex; justify-content:space-between; align-items:flex-end;">
        <div>
            <div style="font-family:'Outfit'; font-size:1.8em; font-weight:800; color:#1A1A2E; letter-spacing:-1px;">{value}</div>
            <div style="font-size:0.75em; font-weight:600; color:{change_color}; margin-top:4px;">{change}</div>
        </div>
        <div style="width:32px; height:32px; border-radius:50%; background:{arrow_bg}; display:flex; align-items:center; justify-content:center; font-size:1em; color:{change_color}; font-weight:800;">{arrow_icon}</div>
    </div></div>"""

# 헬퍼: 체크 행 (알고리즘 해부)
def check_row(label, val, passed):
    icon = "✔" if passed else "✕"; color = "#00B894" if passed else "#E74C3C"
    return f'<div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #F8F7FC; font-size:0.85em;"><span style="color:#6B6B80; font-weight:500;">{label}</span><span style="font-family:Outfit; font-weight:700; color:{color};">{val} {icon}</span></div>'

# 헬퍼: 상태 뱃지 (테이블용)
def status_badge(text, color):
    bg_map = {"#00B894":"#E8F8F0", "#E74C3C":"#FDECEA", "#F39C12":"#FEF5E7"}
    return f'<span style="background:{bg_map.get(color,"#F0EDF6")}; color:{color}; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:700;">● {text}</span>'

# ==========================================
# PAGE: 시장 분석관 (Home) - Aether 레이아웃
# ==========================================
if page == "📊 시장 분석관":
    # ── 인사 헤더 (이미지의 "Hello Moni" 영역) ──
    st.markdown(f"""<div style="margin-bottom:24px;">
        <div style="font-family:'Outfit'; font-size:2.2em; font-weight:800; color:#1A1A2E; letter-spacing:-1px;">AMLS V4.5 Dashboard</div>
        <div style="font-size:0.95em; color:#8E8EA0; font-weight:500;">시장 상태를 실시간으로 모니터링하고, AI 시스템이 최적의 전략을 제시합니다.</div>
    </div>""", unsafe_allow_html=True)

    # ── 상단: 메트릭 카드 3개 + AI 인사이트 패널 (이미지의 3카드+사이드패널 구조) ──
    gap_pct = float((qqq_close/qqq_ma200 - 1)*100)
    qqq_chg = f"{gap_pct:+.1f}% vs 200MA"
    qqq_chg_c = "#00B894" if gap_pct > 0 else "#E74C3C"
    vix_chg = f"20D MA: {float(vix_ma20):.1f}"
    vix_chg_c = "#00B894" if float(vix_ma20) < 25 else "#E74C3C"
    smh_chg = f"RSI: {float(smh_rsi):.0f}"
    smh_chg_c = "#00B894" if float(smh_rsi) > 50 else "#E74C3C"

    top_left, top_right = st.columns([2.5, 1])
    with top_left:
        mc1, mc2, mc3 = st.columns(3)
        with mc1: st.markdown(metric_card("QQQ 현재가", "나스닥 100 추종", f"${float(qqq_close):,.0f}", qqq_chg, qqq_chg_c, "#FDEBD0"), unsafe_allow_html=True)
        with mc2: st.markdown(metric_card("VIX 공포지수", "시장 변동성", f"{float(vix_close):.1f}", vix_chg, vix_chg_c, "#D6EAF8"), unsafe_allow_html=True)
        with mc3: st.markdown(metric_card("반도체 모멘텀", "SMH 3개월 수익률", f"{float(smh_3m)*100:+.1f}%", smh_chg, smh_chg_c, "#D5F5E3"), unsafe_allow_html=True)

    with top_right:
        # AI 인사이트 패널 (이미지 오른쪽의 둥근 카드)
        soxl_label = "SOXL 승인" if smh_cond else "USD 방어"
        soxl_icon = "🔥" if smh_cond else "🛡️"
        st.markdown(f"""<div style="background:#FFF; border-radius:16px; padding:20px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6; height:100%;">
            <div style="font-family:'Outfit'; font-size:1.05em; font-weight:700; color:#1A1A2E; margin-bottom:16px;">AI Insights</div>
            <div style="background:#F8F7FC; border-radius:12px; padding:12px 14px; margin-bottom:10px;">
                <div style="font-size:0.82em; font-weight:700; color:#6C5CE7;">🏛️ 현재 국면</div>
                <div style="font-size:0.9em; font-weight:600; color:#1A1A2E; margin-top:4px;">{regime_info[curr_regime][0]}</div>
                <div style="font-size:0.75em; color:#8E8EA0; margin-top:2px;">{regime_msg}</div>
            </div>
            <div style="background:#F8F7FC; border-radius:12px; padding:12px 14px; margin-bottom:10px;">
                <div style="font-size:0.82em; font-weight:700; color:#6C5CE7;">{soxl_icon} 반도체 판정</div>
                <div style="font-size:0.9em; font-weight:600; color:#1A1A2E; margin-top:4px;">{soxl_label}</div>
            </div>
            <div style="background:#F8F7FC; border-radius:12px; padding:12px 14px;">
                <div style="font-size:0.82em; font-weight:700; color:#6C5CE7;">📋 전략 배분</div>
                <div style="font-size:0.9em; font-weight:600; color:#1A1A2E; margin-top:4px;">{regime_info[curr_regime][1]}</div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── 중단: 비중 바 차트 + 알고리즘 해부 테이블 (이미지의 차트+테이블 구조) ──
    mid_left, mid_right = st.columns([1.5, 1])
    with mid_left:
        st.markdown("""<div style="background:#FFF; border-radius:16px; padding:20px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;">
            <div style="font-family:'Outfit'; font-size:1.05em; font-weight:700; color:#1A1A2E; margin-bottom:4px;">Portfolio Allocation</div>
            <div style="font-size:0.8em; color:#8E8EA0; font-weight:500; margin-bottom:12px;">V4.5 목표 비중</div>""", unsafe_allow_html=True)
        active = {k:v for k,v in target_weights.items() if v > 0}
        fig_bar = go.Figure()
        bar_colors = {'TQQQ':'#6C5CE7','SOXL':'#A29BFE','USD':'#B8B5FF','QLD':'#6C5CE7','SSO':'#A29BFE','GLD':'#FFEAA7','SPY':'#81ECEC','QQQ':'#74B9FF','CASH':'#DFE6E9'}
        fig_bar.add_trace(go.Bar(
            x=list(active.keys()), y=[v*100 for v in active.values()],
            marker=dict(color=[bar_colors.get(k,'#6C5CE7') for k in active.keys()], cornerradius=8),
            text=[f"{v*100:.0f}%" for v in active.values()], textposition='outside',
            textfont=dict(family='Outfit', size=13, color='#1A1A2E')
        ))
        fig_bar.update_layout(height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='DM Sans', color='#8E8EA0'), margin=dict(l=0,r=0,t=10,b=30),
            yaxis=dict(showgrid=True, gridcolor='#F8F7FC', showticklabels=False, range=[0, max(active.values())*100*1.3]),
            xaxis=dict(tickfont=dict(family='Outfit', size=12, color='#1A1A2E')), showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with mid_right:
        # 알고리즘 해부 테이블 (이미지의 Performance Analytics 테이블 스타일)
        st.markdown(f"""<div style="background:#FFF; border-radius:16px; padding:20px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;">
            <div style="font-family:'Outfit'; font-size:1.05em; font-weight:700; color:#1A1A2E; margin-bottom:12px;">Algorithm Status</div>
            <table style="width:100%; border-collapse:collapse; font-size:0.82em;">
                <thead><tr style="border-bottom:2px solid #F0EDF6;">
                    <th style="text-align:left; padding:8px 4px; color:#8E8EA0; font-weight:600;">Check</th>
                    <th style="text-align:right; padding:8px 4px; color:#8E8EA0; font-weight:600;">Value</th>
                    <th style="text-align:center; padding:8px 4px; color:#8E8EA0; font-weight:600;">Status</th>
                </tr></thead>
                <tbody>
                    <tr style="border-bottom:1px solid #F8F7FC;">
                        <td style="padding:10px 4px; font-weight:500; color:#1A1A2E;">VIX &lt; 40</td>
                        <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">{float(vix_close):.1f}</td>
                        <td style="text-align:center;">{status_badge("Pass","#00B894") if float(vix_close)<=40 else status_badge("Fail","#E74C3C")}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F8F7FC;">
                        <td style="padding:10px 4px; font-weight:500; color:#1A1A2E;">QQQ &gt; 200MA</td>
                        <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">${float(qqq_close):,.0f}</td>
                        <td style="text-align:center;">{status_badge("Pass","#00B894") if float(qqq_close)>=float(qqq_ma200) else status_badge("Fail","#E74C3C")}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F8F7FC;">
                        <td style="padding:10px 4px; font-weight:500; color:#1A1A2E;">50MA ≥ 200MA</td>
                        <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">${float(qqq_ma50):,.0f}</td>
                        <td style="text-align:center;">{status_badge("Pass","#00B894") if float(qqq_ma50)>=float(qqq_ma200) else status_badge("Fail","#E74C3C")}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F8F7FC;">
                        <td style="padding:10px 4px; font-weight:500; color:#1A1A2E;">VIX 20MA &lt; 22</td>
                        <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">{float(vix_ma20):.1f}</td>
                        <td style="text-align:center;">{status_badge("Pass","#00B894") if float(vix_ma20)<22 else status_badge("Warn","#F39C12")}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F8F7FC;">
                        <td style="padding:10px 4px; font-weight:500; color:#1A1A2E;">SMH &gt; 50MA</td>
                        <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">${float(smh_close):,.0f}</td>
                        <td style="text-align:center;">{status_badge("Pass","#00B894") if smh_c1 else status_badge("Fail","#E74C3C")}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px 4px; font-weight:500; color:#1A1A2E;">SMH RSI &gt; 50</td>
                        <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">{float(smh_rsi):.0f}</td>
                        <td style="text-align:center;">{status_badge("Pass","#00B894") if smh_c3 else status_badge("Fail","#E74C3C")}</td>
                    </tr>
                </tbody>
            </table>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── 하단: QQQ/TQQQ 차트 ──
    ch1, ch2 = st.columns(2)
    df_recent = df.iloc[-300:]
    for col_st, ticker, ma_col, title in [(ch1,'QQQ','QQQ_MA200','QQQ vs 200일선'), (ch2,'TQQQ','TQQQ_MA200','TQQQ vs 200일선')]:
        with col_st:
            st.markdown(f"""<div style="background:#FFF; border-radius:16px; padding:16px 18px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;">
                <div style="font-family:'Outfit'; font-size:0.95em; font-weight:700; color:#1A1A2E; margin-bottom:8px;">{title}</div>""", unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_recent.index, y=df_recent[ticker], name=ticker, line=dict(color='#6C5CE7', width=2.5), fill='tozeroy', fillcolor='rgba(108,92,231,0.06)'))
            fig.add_trace(go.Scatter(x=df_recent.index, y=df_recent[ma_col], name='200MA', line=dict(color='#FDA7DF', width=1.5, dash='dash')))
            fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='DM Sans', color='#8E8EA0', size=11), margin=dict(l=0,r=0,t=5,b=0),
                yaxis=dict(showgrid=True, gridcolor='#F8F7FC'), xaxis=dict(showgrid=False),
                legend=dict(orientation="h", yanchor="top", y=1.12, font=dict(size=11)), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "💼 포트폴리오":
    st.markdown("<div style='font-family:Outfit; font-size:2em; font-weight:800; color:#1A1A2E; letter-spacing:-1px; margin-bottom:16px;'>💼 내 포트폴리오</div>", unsafe_allow_html=True)
    col_up, col_down = st.columns(2)
    with col_up:
        uf = st.file_uploader("📂 JSON 복구", type="json")
        if uf:
            try: st.session_state.portfolio.update(json.load(uf)); sanitize_portfolio(); save_portfolio_to_disk(); st.success("복구 완료!")
            except: st.error("파일 오류")
    with col_down:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("💾 백업", data=json.dumps(st.session_state.portfolio), file_name="portfolio_backup.json", mime="application/json", use_container_width=True)
    st.divider()

    ed_data = [{"자산":a,"수량":float(st.session_state.portfolio[a].get('shares',0)),"매수단가($)":float(st.session_state.portfolio[a].get('avg_price',1.0 if a=='CASH' else 0)),"매입환율(₩)":float(st.session_state.portfolio[a].get('fx',1350))} for a in ASSET_LIST]
    edited_df = st.data_editor(pd.DataFrame(ed_data), disabled=["자산"], hide_index=True, use_container_width=True,
        column_config={"수량":st.column_config.NumberColumn("보유 수량",min_value=0.0,format="%.4f"),"매수단가($)":st.column_config.NumberColumn("매수단가",min_value=0.0,format="%.2f"),"매입환율(₩)":st.column_config.NumberColumn("환율",min_value=0.0,format="%.0f")})
    for _,row in edited_df.iterrows():
        st.session_state.portfolio[row["자산"]]={'shares':float(row["수량"]),'avg_price':float(row["매수단가($)"]),'fx':float(row["매입환율(₩)"])}
    save_portfolio_to_disk()

    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': current_prices[t] = 1.0
        else:
            p = rt_prices.get(t)
            if p is not None and p == p and p > 0: current_prices[t] = float(p)
            elif t in df.columns:
                p2 = df[t].iloc[-1]; current_prices[t] = float(p2) if (p2 is not None and p2 == p2 and p2 > 0) else 0.0
            else: current_prices[t] = 0.0
    cur_fx = rt_prices.get('USDKRW=X', 1350.0)
    if cur_fx is None or cur_fx != cur_fx or cur_fx <= 0: cur_fx = 1350.0
    curr_vals = {}
    for a in ASSET_LIST:
        s=float(st.session_state.portfolio[a].get('shares',0) or 0); p=float(current_prices.get(a,0) or 0); v=s*p
        curr_vals[a]=v if v==v else 0.0
    total_val_usd = sum(curr_vals.values())

    tc1,tc2,tc3 = st.columns(3)
    with tc1: st.markdown(metric_card("총 평가액","Total Value",f"${total_val_usd:,.0f}",f"₩{total_val_usd*cur_fx:,.0f}","#6C5CE7","#FDEBD0"), unsafe_allow_html=True)
    with tc2: st.markdown(metric_card("적용 환율","USD/KRW",f"₩{cur_fx:,.0f}","현재 시세","#00B894","#D6EAF8"), unsafe_allow_html=True)
    with tc3: st.markdown(metric_card("현재 레짐","System Regime",f"R{curr_regime}",regime_info[curr_regime][1],"#6C5CE7","#D5F5E3"), unsafe_allow_html=True)

    if total_val_usd > 0:
        diff_vals = {a:(total_val_usd*target_weights.get(a,0))-curr_vals[a] for a in ASSET_LIST}
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        # 리밸런싱 테이블 (이미지의 Performance Analytics 스타일)
        st.markdown(f"""<div style="background:#FFF; border-radius:16px; padding:20px 24px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;">
            <div style="font-family:'Outfit'; font-size:1.05em; font-weight:700; color:#1A1A2E; margin-bottom:14px;">Rebalancing Orders</div>
            <table style="width:100%; border-collapse:collapse; font-size:0.85em;">
                <thead><tr style="border-bottom:2px solid #F0EDF6;">
                    <th style="text-align:left; padding:10px 6px; color:#8E8EA0; font-weight:600;">Asset</th>
                    <th style="text-align:right; padding:10px 6px; color:#8E8EA0; font-weight:600;">보유</th>
                    <th style="text-align:right; padding:10px 6px; color:#8E8EA0; font-weight:600;">목표비중</th>
                    <th style="text-align:right; padding:10px 6px; color:#8E8EA0; font-weight:600;">차액</th>
                    <th style="text-align:center; padding:10px 6px; color:#8E8EA0; font-weight:600;">Action</th>
                </tr></thead><tbody>""", unsafe_allow_html=True)
        rows_html = ""
        for a in ASSET_LIST:
            tw=target_weights.get(a,0); cv=curr_vals[a]; d=diff_vals[a]; cp=current_prices[a] if current_prices[a]>0 else 1
            if tw > 0 or cv > 0:
                if abs(d) < cp*0.05 and a != 'CASH': badge = status_badge("Hold","#00B894")
                elif d > 0:
                    sh = f"{d/cp:.1f}주" if a != 'CASH' else f"${d:,.0f}"
                    badge = status_badge(f"Buy {sh}","#00B894")
                else:
                    sh = f"{abs(d)/cp:.1f}주" if a != 'CASH' else f"${abs(d):,.0f}"
                    badge = status_badge(f"Sell {sh}","#E74C3C")
                rows_html += f"""<tr style="border-bottom:1px solid #F8F7FC;">
                    <td style="padding:10px 6px; font-weight:700; color:#6C5CE7;">{a}</td>
                    <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">${cv:,.0f}</td>
                    <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:#1A1A2E;">{tw*100:.0f}%</td>
                    <td style="text-align:right; font-family:'Outfit'; font-weight:700; color:{'#00B894' if d>=0 else '#E74C3C'};">{'+' if d>=0 else ''}${d:,.0f}</td>
                    <td style="text-align:center;">{badge}</td></tr>"""
        st.markdown(rows_html + "</tbody></table></div>", unsafe_allow_html=True)
    else:
        st.info("자산을 1개 이상 입력하면 리밸런싱 지침이 나타납니다.")

elif page == "🍫 8-Pack":
    df_view=df.iloc[-120:]; qqq_rsi=last_row['QQQ_RSI']; qqq_dd=last_row['QQQ_DD']
    vix_sc=max(0,min(100,100-(last_row['^VIX']-12)/28*100)); dd_sc=max(0,min(100,(qqq_dd+0.20)/0.20*100)); rsi_sc=max(0,min(100,qqq_rsi))
    fg_score=(vix_sc+dd_sc+rsi_sc)/3
    sec_names={'XLK':'기술','XLV':'헬스','XLF':'금융','XLY':'소비','XLC':'통신','XLI':'산업','XLP':'필수','XLE':'에너지','XLU':'유틸','XLRE':'부동산','XLB':'소재'}
    sec_data=[{'섹터':sec_names[s],'수익률':last_row[f'{s}_1M']*100} for s in SECTOR_TICKERS]
    sec_df=pd.DataFrame(sec_data).sort_values(by='수익률',ascending=True)
    top_sec,bot_sec=sec_df.iloc[-1]['섹터'],sec_df.iloc[0]['섹터']

    st.markdown(f"""<div style="font-family:'Outfit'; font-size:2em; font-weight:800; color:#1A1A2E; letter-spacing:-1px; margin-bottom:4px;">8-Pack 레이더망</div>
        <div style="font-size:0.95em; color:#8E8EA0; font-weight:500; margin-bottom:24px;">8개 렌즈로 시장을 입체 분석합니다.</div>""", unsafe_allow_html=True)

    def pack_card(title, val_text, val_color, header_color):
        return f"""<div style="background:#FFF; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6; margin-bottom:16px;">
            <div style="background:{header_color}; padding:12px 16px;">
                <div style="font-size:0.82em; font-weight:700; color:#1A1A2E;">{title}</div>
            </div>
            <div style="padding:14px 16px; text-align:center;">
                {status_badge(val_text, val_color)}
            </div>"""

    r1 = st.columns(4)
    items = [
        ("1. RSI (DCA)", "매수 구간" if qqq_rsi<40 else ("과열" if qqq_rsi>70 else "적립 유지"), "#00B894" if qqq_rsi<40 else ("#E74C3C" if qqq_rsi>70 else "#6C5CE7"), "#FDEBD0", 'QQQ_RSI', dict(range=[10,90])),
        ("2. Drawdown", f"{float(qqq_dd)*100:.1f}%", "#E74C3C" if qqq_dd<-0.10 else "#00B894", "#D6EAF8", 'QQQ_DD', dict(tickformat='.0%')),
        ("3. Fear & Greed", f"Score: {fg_score:.0f}", "#00B894" if fg_score<30 else ("#E74C3C" if fg_score>70 else "#6C5CE7"), "#D5F5E3", None, None),
        ("4. Sector Rotation", f"🏆{top_sec} 📉{bot_sec}", "#6C5CE7", "#FADBD8", None, None),
    ]
    for idx,(title,val,vc,hc,col_name,yax) in enumerate(items):
        with r1[idx]:
            st.markdown(pack_card(title,val,vc,hc), unsafe_allow_html=True)
            if col_name:
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=df_view.index,y=df_view[col_name],line=dict(color='#6C5CE7',width=2),fill='tozeroy',fillcolor='rgba(108,92,231,0.06)'))
                if col_name=='QQQ_RSI': fig.add_hline(y=70,line_dash='dash',line_color='#FDA7DF'); fig.add_hline(y=30,line_dash='dash',line_color='#00B894')
                fig.update_layout(height=150,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=0,b=0),yaxis=yax or {},xaxis=dict(showticklabels=False),showlegend=False,font=dict(size=10,color='#8E8EA0'))
                st.plotly_chart(fig,use_container_width=True)
            elif title.startswith("3"):
                fig=go.Figure(go.Indicator(mode="gauge+number",value=fg_score,domain={'x':[0,1],'y':[0,1]},gauge={'axis':{'range':[0,100]},'bar':{'color':'#6C5CE7'},
                    'steps':[{'range':[0,25],'color':'rgba(231,76,60,0.2)'},{'range':[25,50],'color':'rgba(253,167,223,0.15)'},{'range':[50,75],'color':'rgba(108,92,231,0.1)'},{'range':[75,100],'color':'rgba(0,184,148,0.2)'}]}))
                fig.update_layout(height=150,paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=15,r=15,t=0,b=0),font=dict(family='Outfit',color='#1A1A2E',size=12))
                st.plotly_chart(fig,use_container_width=True)
            elif title.startswith("4"):
                fig=go.Figure(go.Bar(x=sec_df['수익률'],y=sec_df['섹터'],orientation='h',marker=dict(color=['#FDA7DF' if v<0 else '#6C5CE7' for v in sec_df['수익률']],cornerradius=4)))
                fig.update_layout(height=150,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=0,b=0),showlegend=False,font=dict(size=10,color='#8E8EA0'),yaxis=dict(tickfont=dict(size=9)))
                st.plotly_chart(fig,use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    r2 = st.columns(4)
    line_items = [
        ("5. Credit Spread", last_row['HYG_IEF_Ratio']<last_row['HYG_IEF_MA50'], [('HYG_IEF_Ratio','#6C5CE7'),('HYG_IEF_MA50','#FDA7DF')], "#FDEBD0", {}),
        ("6. Breadth", last_row['QQQ_20d_Ret']>0 and last_row['QQQE_20d_Ret']<0, [('QQQ_20d_Ret','#6C5CE7'),('QQQE_20d_Ret','#FDA7DF')], "#D6EAF8", dict(tickformat='.0%')),
        ("7. Gold/Equity", last_row['GLD_SPY_Ratio']>last_row['GLD_SPY_MA50'], [('GLD_SPY_Ratio','#6C5CE7'),('GLD_SPY_MA50','#FDA7DF')], "#D5F5E3", {}),
        ("8. Dollar (UUP)", last_row['UUP']>last_row['UUP_MA50'], [('UUP','#6C5CE7'),('UUP_MA50','#FDA7DF')], "#FADBD8", {}),
    ]
    risk_labels = ["국채 피신","쏠림 심화","금 피신","강달러 압박"]
    safe_labels = ["회사채 선호","고른 상승","주식 선호","달러 진정"]
    for idx,(title,is_risk,traces,hc,yax) in enumerate(line_items):
        with r2[idx]:
            vl = risk_labels[idx] if is_risk else safe_labels[idx]; vc = "#E74C3C" if is_risk else "#00B894"
            st.markdown(pack_card(title,vl,vc,hc), unsafe_allow_html=True)
            fig=go.Figure()
            for col,color in traces: fig.add_trace(go.Scatter(x=df_view.index,y=df_view[col],line=dict(color=color,width=2 if color=='#6C5CE7' else 1.5,dash=None if color=='#6C5CE7' else 'dash')))
            fig.update_layout(height=150,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=0,b=0),yaxis=yax,xaxis=dict(showticklabels=False),showlegend=False,font=dict(size=10,color='#8E8EA0'))
            st.plotly_chart(fig,use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "📈 백테스트":
    st.markdown("<div style='font-family:Outfit; font-size:2em; font-weight:800; color:#1A1A2E; letter-spacing:-1px;'>📈 백테스트 랩</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.95em; color:#8E8EA0; margin-bottom:20px;'>AMLS V4.5 vs 나스닥 레버리지 장기투자</div>", unsafe_allow_html=True)
    with st.spinner("시뮬레이션 중..."):
        daily_ret=df[['QQQ','TQQQ','SOXL','USD','QLD','SSO','SPY','SMH','GLD']].pct_change().fillna(0)
        w=get_weights_v45(df['Regime'].iloc[0],False)
        vo,vq,vl,vt=10000,10000,10000,10000; ho,hq,hl,ht=[vo],[vq],[vl],[vt]
        for i in range(1,len(df)):
            r=sum(w.get(t,0)*daily_ret[t].iloc[i] for t in w if t in daily_ret.columns)
            vo*=(1+r);vq*=(1+daily_ret['QQQ'].iloc[i]);vl*=(1+daily_ret['QLD'].iloc[i]);vt*=(1+daily_ret['TQQQ'].iloc[i])
            ho.append(vo);hq.append(vq);hl.append(vl);ht.append(vt)
            sc=(df['SMH'].iloc[i]>df['SMH_MA50'].iloc[i]) and (df['SMH_3M_Ret'].iloc[i]>0.05) and (df['SMH_RSI'].iloc[i]>50)
            w=get_weights_v45(df['Regime'].iloc[i],sc)
        res=pd.DataFrame(index=df.index);res['V4.5']=ho;res['QQQ']=hq;res['QLD']=hl;res['TQQQ']=ht
        days=(res.index[-1]-res.index[0]).days
        def cm(s): return (s[-1]/s[0]-1),(s[-1]/s[0])**(365.25/days)-1 if days>0 else 0,((s/s.cummax())-1).min()
        ro,co,mo=cm(res['V4.5']);rq,cq,mq=cm(res['QQQ']);rl,cl,ml=cm(res['QLD']);rt,ct,mt=cm(res['TQQQ'])

    mc1,mc2,mc3,mc4=st.columns(4)
    with mc1: st.markdown(metric_card("✨ AMLS V4.5",f"CAGR {co*100:.1f}%",f"${vo:,.0f}",f"MDD {mo*100:.1f}%","#00B894" if mo>-0.30 else "#E74C3C","#FDEBD0"), unsafe_allow_html=True)
    with mc2: st.markdown(metric_card("QQQ (1x)",f"CAGR {cq*100:.1f}%",f"${vq:,.0f}",f"MDD {mq*100:.1f}%","#E74C3C","#D6EAF8"), unsafe_allow_html=True)
    with mc3: st.markdown(metric_card("QLD (2x)",f"CAGR {cl*100:.1f}%",f"${vl:,.0f}",f"MDD {ml*100:.1f}%","#E74C3C","#D5F5E3"), unsafe_allow_html=True)
    with mc4: st.markdown(metric_card("TQQQ (3x)",f"CAGR {ct*100:.1f}%",f"${vt:,.0f}",f"MDD {mt*100:.1f}%","#E74C3C","#FADBD8"), unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # 자산 곡선 (둥근 영역 차트)
    st.markdown("<div style='background:#FFF; border-radius:16px; padding:18px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;'><div style='font-family:Outfit; font-size:1em; font-weight:700; color:#1A1A2E; margin-bottom:8px;'>Equity Curve (Log)</div>", unsafe_allow_html=True)
    fig_eq=go.Figure()
    fig_eq.add_trace(go.Scatter(x=res.index,y=res['QQQ'],name='QQQ',line=dict(color='#B2BEC3',width=1.5,dash='dot')))
    fig_eq.add_trace(go.Scatter(x=res.index,y=res['QLD'],name='QLD',line=dict(color='#FDA7DF',width=2,dash='dash')))
    fig_eq.add_trace(go.Scatter(x=res.index,y=res['TQQQ'],name='TQQQ',line=dict(color='#E74C3C',width=2,dash='dash')))
    fig_eq.add_trace(go.Scatter(x=res.index,y=res['V4.5'],name='V4.5',line=dict(color='#6C5CE7',width=3),fill='tozeroy',fillcolor='rgba(108,92,231,0.06)'))
    fig_eq.update_layout(height=400,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='DM Sans',color='#8E8EA0'),yaxis_type='log',yaxis=dict(showgrid=True,gridcolor='#F8F7FC'),margin=dict(l=0,r=0,t=5,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
    st.plotly_chart(fig_eq,use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Drawdown 차트
    st.markdown("<div style='background:#FFF; border-radius:16px; padding:18px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;'><div style='font-family:Outfit; font-size:1em; font-weight:700; color:#1A1A2E; margin-bottom:8px;'>Drawdown</div>", unsafe_allow_html=True)
    def dd(s): return (s/s.cummax())-1
    fig_dd=go.Figure()
    fig_dd.add_trace(go.Scatter(x=res.index,y=dd(res['QQQ']),name='QQQ',line=dict(color='#B2BEC3',width=1)))
    fig_dd.add_trace(go.Scatter(x=res.index,y=dd(res['TQQQ']),name='TQQQ',line=dict(color='#E74C3C',width=1)))
    fig_dd.add_trace(go.Scatter(x=res.index,y=dd(res['V4.5']),name='V4.5',fill='tozeroy',fillcolor='rgba(108,92,231,0.08)',line=dict(color='#6C5CE7',width=2.5)))
    fig_dd.update_layout(height=250,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='DM Sans',color='#8E8EA0'),yaxis=dict(tickformat='.0%',showgrid=True,gridcolor='#F8F7FC'),margin=dict(l=0,r=0,t=5,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
    st.plotly_chart(fig_dd,use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "📰 뉴스룸":
    headlines_for_ai, news_items = fetch_macro_news()
    st.markdown("""<div style="font-family:'Outfit'; font-size:2em; font-weight:800; color:#1A1A2E; letter-spacing:-1px;">📰 매크로 뉴스룸</div>
        <div style="font-size:0.95em; color:#8E8EA0; margin-bottom:24px;">글로벌 매크로 뉴스와 AI 브리핑</div>""", unsafe_allow_html=True)

    with st.expander("✨ AI 심층 분석", expanded=True):
        if st.button("🚀 AI 분석 실행", use_container_width=True):
            try:
                import google.generativeai as genai
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: st.warning("뉴스 없음")
                else:
                    with st.spinner("분석 중..."):
                        genai.configure(api_key=api_key)
                        models=[m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model=genai.GenerativeModel(models[0].replace('models/',''))
                        prompt="너는 월스트리트 퀀트 애널리스트야. 뉴스를 ## 1. 주요 분류 ## 2. 리스크 ## 3. 최종 고찰 3가지로 요약해.\n[뉴스]:\n"+"\n".join(headlines_for_ai)
                        resp=model.generate_content(prompt)
                        st.markdown(f"""<div style="background:#FFF; border-radius:16px; padding:28px; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6;">
                        <style>.ai-box h2{{color:#6C5CE7!important;font-size:1.4em!important;font-weight:800;border-bottom:2px solid #F0EDF6;padding-bottom:10px;margin-top:24px;}}.ai-box h2:first-child{{margin-top:0;}}.ai-box p,.ai-box li{{color:#1A1A2E;font-size:1.05em;line-height:1.8;}}.ai-box strong{{color:#1A1A2E;background:rgba(108,92,231,0.06);padding:2px 6px;border-radius:6px;}}</style>
                        <div class="ai-box">{resp.text}</div></div>""", unsafe_allow_html=True)
            except KeyError: st.error("GEMINI_API_KEY가 필요합니다.")
            except Exception as e: st.error(f"오류: {e}")

    st.divider()
    if news_items:
        st.markdown("<div style='font-family:Outfit; font-size:1.2em; font-weight:700; color:#1A1A2E; margin-bottom:16px;'>Latest Headlines</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, item in enumerate(news_items):
            with cols[idx%3]:
                st.markdown(f"""<div style="background:#FFF; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.04); border:1px solid #F0EDF6; margin-bottom:14px;">
                    <div style="background:{'#FDEBD0' if idx%3==0 else '#D6EAF8' if idx%3==1 else '#D5F5E3'}; height:4px;"></div>
                    <div style="padding:16px 18px; min-height:120px; display:flex; flex-direction:column; justify-content:space-between;">
                        <div style="font-weight:600; font-size:0.92em; line-height:1.5; color:#1A1A2E; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                            <a href="{item['link']}" target="_blank" style="color:#1A1A2E; text-decoration:none;">{item['title'].replace('&','&amp;')}</a>
                        </div>
                        <div style="color:#6C5CE7; font-size:0.78em; font-weight:700; font-family:'Outfit'; margin-top:10px;">{item['date']}</div>
                    </div></div>""", unsafe_allow_html=True)
    else: st.info("뉴스가 없습니다.")
