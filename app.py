import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import json
import os
import requests
from io import StringIO
import random

warnings.filterwarnings('ignore')

# =====================================================================
# [0] 시스템 설정 및 데이터 관리 (기존 코드 유지)
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 포트폴리오", layout="wide", initial_sidebar_state="expanded")

SETTINGS_FILE = "amls_settings_v12.json"
ACCOUNTS_FILE = "amls_multi_accounts.json"
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "SPY", "GLD", "CASH"]

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"theme": "애플 테마"}

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=4)

def load_accounts_data():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None
    return None

def save_accounts_data(data_dict):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)

if 'settings' not in st.session_state:
    st.session_state['settings'] = load_settings()

if 'accounts' not in st.session_state:
    loaded = load_accounts_data()
    if not loaded:
        loaded = {
            "AMLS v4.4": {  
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0,
                "layout_order": ["🎯 목표 달성률", "📊 계좌 요약", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
            }
        }
    st.session_state['accounts'] = loaded

# (생략: 계좌 이름 변경 로직 등 데이터 마이그레이션 코드 유지)
needs_save = False
# ... (기존 마이그레이션 코드) ...
if needs_save: save_accounts_data(st.session_state['accounts'])


# =====================================================================
# [2] 동적 테마 및 레이아웃 설정 (Glassmorphism 추가)
# =====================================================================
current_theme = st.session_state['settings'].get("theme", "애플 테마")
theme_list = ["애플 테마", "1930년대 타자기 테마", "월스트리트 저널 테마", "엑셀 테마"]

if current_theme not in theme_list:
    current_theme = "애플 테마"

if current_theme == "애플 테마":
    DEFAULT_TEXT_COLOR = "#1d1d1f"; TEXT_SUB = "#8e8e93"
    PANEL_BG = "rgba(255, 255, 255, 0.7)"; PANEL_BORDER = "1px solid rgba(200, 200, 200, 0.3)"; PANEL_RADIUS = "16px"
    WIDGET_THEME = "light"
    C_UP = "#34c759"; C_DOWN = "#ff3b30"; C_WARN = "#ff9500"; C_SAFE = "#007aff"
    BASE_CHART_COLORS = {'TQQQ':'#ff3b30', 'SOXL':'#af52de', 'USD':'#5856d6', 'QLD':'#ff9500', 'SSO':'#ffcc00', 'QQQ':'#007aff', 'SPY':'#34a853', 'GLD':'#34c759', 'BTC-USD':'#f7931a', 'CASH':'#8e8e93'}
# ... (생략: 다른 테마 설정 코드 유지) ...
else: # default 1930s or other
    DEFAULT_TEXT_COLOR = "#2c2a25"; TEXT_SUB = "#555555"
    PANEL_BG = "rgba(223, 215, 197, 0.85)"; PANEL_BORDER = "2px solid #2c2a25"; PANEL_RADIUS = "0px"
    WIDGET_THEME = "light"
    C_UP = "#000080"; C_DOWN = "#8b0000"; C_WARN = "#b8860b"; C_SAFE = "#006400"
    BASE_CHART_COLORS = {'TQQQ':'#8b0000', 'SOXL':'#556b2f', 'USD':'#8fbc8f', 'QLD':'#b8860b', 'SSO':'#cd853f', 'QQQ':'#000080', 'SPY':'#2e8b57', 'GLD':'#daa520', 'BTC-USD':'#f7931a', 'CASH':'#2f4f4f'}


if "last_theme" not in st.session_state['settings'] or st.session_state['settings']["last_theme"] != current_theme:
    st.session_state['settings']["text_color"] = DEFAULT_TEXT_COLOR
    st.session_state['settings']["last_theme"] = current_theme
    save_settings(st.session_state['settings'])

if "text_color" not in st.session_state['settings']: st.session_state['settings']["text_color"] = DEFAULT_TEXT_COLOR
if "chart_colors" not in st.session_state['settings']: st.session_state['settings']["chart_colors"] = BASE_CHART_COLORS.copy()
for tkr in REQUIRED_TICKERS + ['BTC-USD']:
    if tkr not in st.session_state['settings']["chart_colors"]:
        st.session_state['settings']["chart_colors"][tkr] = BASE_CHART_COLORS.get(tkr, "#888888")

TEXT_COLOR = st.session_state['settings']["text_color"]
COLOR_PALETTE = st.session_state['settings']["chart_colors"]

THEME_LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR, size=13), margin=dict(l=0, r=0, t=30, b=0))

def apply_custom_css():
    css_base = ""
    # 네이티브 컨테이너를 쓰기 위해 강제 높이, CSS 그리드는 모두 뺌 (글씨 잘림 방지 핵심)
    
    if current_theme == "애플 테마":
        css_base = f"""
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        .stApp {{ background-color: #f5f5f7; background-image: radial-gradient(circle at top right, #e2e2e5 0%, #f5f5f7 40%, #e8e8ed 100%); font-family: 'Pretendard', -apple-system, sans-serif; color: {TEXT_COLOR}; letter-spacing: -0.01em; }}
        /* 패널 디자인 (Glassmorphism) */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background: {PANEL_BG}; backdrop-filter: blur(20px); border: {PANEL_BORDER}; border-radius: {PANEL_RADIUS}; box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.05); padding: 1.5rem; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border-radius: 10px; text-decoration: none !important; color: {TEXT_COLOR}; font-weight: 600; font-size: 0.95rem; transition: background-color 0.2s, transform 0.1s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.05); transform: translateX(2px); }}
        """
    # ... (생략: 다른 테마 CSS 유지) ...
    elif current_theme == "1930년대 타자기 테마":
        css_base = f"""
        @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: transparent !important; }}
        .stApp {{ font-family: 'Special Elite', 'Courier New', monospace !important; color: {TEXT_COLOR} !important; background-color: #e4dccc; background-image: url('https://www.transparenttextures.com/patterns/old-wall.png'); }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{ background: {PANEL_BG} !important; border: {PANEL_BORDER} !important; border-radius: {PANEL_RADIUS} !important; box-shadow: 4px 4px 0px {TEXT_COLOR} !important; padding: 1.5rem !important; }}
        .sidebar-link {{ display: flex; align-items: center; padding: 8px 12px; margin-bottom: 4px; border: 1px solid transparent; border-radius: 0px; text-decoration: none !important; color: {TEXT_COLOR} !important; font-weight: bold; font-size: 0.95rem; transition: background-color 0.2s; }}
        .sidebar-link:hover {{ background-color: rgba(0,0,0,0.1); border: 1px dashed {TEXT_COLOR}; }}
        """

    st.markdown(f"""
    <style>
    {css_base}
    /* 메트릭 및 텍스트 자동 줄바꿈 (글씨 잘림 방지) */
    div[data-testid="stMetricValue"] > div, div[data-testid="stMetricDelta"] > div, p, span, label, .stMarkdown {{ white-space: normal !important; word-break: keep-all !important; overflow-wrap: break-word !important; }}
    div[data-testid="stMetricValue"] {{ font-weight: bold; font-size: 1.8rem; color: {TEXT_COLOR}; }}
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()


# =====================================================================
# [3] 글로벌 백엔드 데이터 함수 (기존 유지)
# =====================================================================
@st.cache_data(ttl=1800)
def get_market_status():
    TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
    try:
        data = yf.download(TICKERS, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill()
        if data.empty or len(data) < 200: raise ValueError
    except:
        return {
            'regime': 2, 'target_regime': 2, 'is_waiting': False, 'wait_days': 0,
            'regime_duration': 0, 'regime_direction': 'stable', 'entry_grade': '서버 점검중',
            'vix': 20.0, 'qqq': 400.0, 'ma200': 400.0, 'ma50': 400.0,
            'smh': 200.0, 'smh_ma50': 200.0, 'smh_3m_ret': 0.05, 'smh_rsi': 55.0,
            'prices': {t: 100.0 for t in TICKERS}, 'prev_prices': {t: 100.0 for t in TICKERS},
            'date': datetime.today(), 'usdkrw': 1350.0
        }

    today = data.iloc[-1]; yesterday = data.iloc[-2]
    
    ma200_s = data['QQQ'].rolling(200).mean()
    ma50_s = data['QQQ'].rolling(50).mean()
    smh_ma50_s = data['SMH'].rolling(50).mean()
    smh_3m_ret_s = data['SMH'].pct_change(63)
    smh_rsi_s = ta.rsi(data['SMH'], length=14)
    
    target_regimes = []
    for i in range(len(data)):
        v = data['^VIX'].iloc[i]; q = data['QQQ'].iloc[i]; m200 = ma200_s.iloc[i]; m50 = ma50_s.iloc[i]
        if pd.isna(m200): target_regimes.append(2); continue
        if v > 40: target_regimes.append(4)
        elif q < m200: target_regimes.append(3)
        elif q >= m200 and m50 >= m200 and vix < 25: target_regimes.append(1)
        else: target_regimes.append(2)
        
    current_v4_4 = 3; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4 = []
    for tr in target_regimes:
        if tr > current_v4_4: 
            current_v4_4 = tr; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
        elif tr < current_v4_4:
            if tr == pend_v4_4:
                cnt_v4_4 += 1
                if cnt_v4_4 >= 5: current_v4_4 = tr; pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
                else: actual_regime_v4_4.append(current_v4_4 - 1)
            else: 
                pend_v4_4 = tr; cnt_v4_4 = 1; actual_regime_v4_4.append(current_v4_4 - 1)
        else: 
            pend_v4_4 = None; cnt_v4_4 = 0; actual_regime_v4_4.append(current_v4_4)
            
    applied_series = pd.Series(actual_regime_v4_4, index=data.index).shift(1).bfill()
    applied_reg = int(applied_series.iloc[-1])
    target_reg = int(target_regimes[-1])
    is_waiting = (pend_v4_4 is not None and target_reg < current_v4_4)

    current_reg = applied_series.iloc[-1]
    regime_duration = 0
    for i in range(len(applied_series)-1, -1, -1):
        if applied_series.iloc[i] == current_reg: regime_duration += 1
        else: break
    
    prev_reg = current_reg
    search_start = len(applied_series) - regime_duration - 1
    if search_start >= 0:
        prev_reg = int(applied_series.iloc[search_start])

    if current_reg < prev_reg: regime_direction = "ascending"
    elif current_reg > prev_reg: regime_direction = "descending"
    else: regime_direction = "stable"

    if regime_direction == "ascending": entry_grade = "최적 진입" if regime_duration <= 30 else "주의(전환)"
    elif regime_direction == "descending": entry_grade = "진입 보류" if regime_duration <= 20 else "바닥 탐색"
    else: entry_grade = "진입 적합"

    try:
        current_usdkrw = float(today['USDKRW=X']) if pd.notna(today.get('USDKRW=X')) else 0.0
    except: current_usdkrw = 0.0

    return {
        'regime': applied_reg, 'target_regime': target_reg, 'is_waiting': is_waiting, 'wait_days': cnt_v4_4,
        'regime_duration': regime_duration, 'regime_direction': regime_direction, 'entry_grade': entry_grade,
        'vix': today['^VIX'], 'qqq': today['QQQ'], 'ma200': ma200_s.iloc[-1], 'ma50': ma50_s.iloc[-1],
        'smh': today['SMH'], 'smh_ma50': smh_ma50_s.iloc[-1], 'smh_3m_ret': smh_3m_ret_s.iloc[-1], 'smh_rsi': smh_rsi_s.iloc[-1],
        'prices': today.to_dict(), 'prev_prices': yesterday.to_dict(), 'date': data.index[-1], 'usdkrw': current_usdkrw
    }

@st.cache_data(ttl=60)
def get_realtime_prices():
    RT_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
    try:
        rt = yf.download(RT_TICKERS, period='1d', interval='5m', prepost=True, progress=False)['Close']
        if rt.empty: return None
        return rt.ffill().iloc[-1].to_dict()
    except: return None
    
@st.cache_data(ttl=3600)
def get_regime_chart_data():
    tkrs = ['QQQ', '^VIX']
    try:
        c_df = yf.download(tkrs, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill().dropna()
        c_df['MA50'] = c_df['QQQ'].rolling(50).mean()
        c_df['MA200'] = c_df['QQQ'].rolling(200).mean()
        return c_df.dropna().tail(252)
    except:
        return pd.DataFrame()

# (생략: 백테스트 데이터 로드 함수 유지)
@st.cache_data(ttl=3600)
def load_amls_backtest_data(start, end, init_cap, monthly_cont, rebal_freq="월 1회", btc_ratio=0):
    # ... (기존 백테스트 로직 함수 코드 유지) ...
    pass


# =====================================================================
# [4] 페이지 구성: 글로벌 마켓 대시보드
# =====================================================================
@st.cache_data(ttl=3600)
def get_dashboard_data():
    tickers = ['^GSPC', '^IXIC', '^VIX', 'USDKRW=X']
    try:
        df = yf.download(tickers, start=datetime.today()-timedelta(days=365), progress=False)['Close'].ffill()
        if df.empty: raise ValueError
        return df
    except:
        return pd.DataFrame()

def page_market_dashboard():
    st.title("🌐 매크로 터미널")
    
    # 🔥 트레이딩뷰 위젯 테마 적용
    components.html(f"""<div class="tradingview-widget-container" style="border-radius: {PANEL_RADIUS}; overflow: hidden; border: {PANEL_BORDER};">
<div class="tradingview-widget-container__widget"></div>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
{{
"symbols": [
{{"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"}},
{{"proName": "FOREXCOM:NSXUSD", "title": "NASDAQ 100"}},
{{"description": "TQQQ", "proName": "NASDAQ:TQQQ"}},
{{"description": "SOXL", "proName": "ARCA:SOXL"}},
{{"description": "USD/KRW", "proName": "FX_IDC:USDKRW"}},
{{"description": "GOLD", "proName": "OANDA:XAUUSD"}},
{{"description": "BITCOIN", "proName": "BINANCE:BTCUSD"}}
],
"showSymbolLogo": true, "colorTheme": "{WIDGET_THEME}", "locale": "kr"
}}
</script>
</div>""", height=70)

    col_left, col_right = st.columns([1, 1.8])
    with col_left:
        with st.container(border=True):
            st.markdown("##### 📈 주요 지수 및 시장 심리")
            indices_df = get_dashboard_data()
            
            if not indices_df.empty and len(indices_df) >= 2:
                c1, c2 = st.columns(2); latest = indices_df.iloc[-1]; prev = indices_df.iloc[-2]
                # 🔥 세련된 메트릭 위젯 도입
                c1.metric("S&P 500", f"{latest.get('^GSPC', 0):,.0f}", f"{(latest.get('^GSPC',0)/prev.get('^GSPC',1)-1)*100:+.2f}%")
                c2.metric("NASDAQ", f"{latest.get('^IXIC', 0):,.0f}", f"{(latest.get('^IXIC',0)/prev.get('^IXIC',1)-1)*100:+.2f}%")
                c3, c4 = st.columns(2)
                c3.metric("VIX", f"{latest.get('^VIX', 0):,.2f}", f"{(latest.get('^VIX',0)/prev.get('^VIX',1)-1)*100:+.2f}%", delta_color="inverse")
                c4.metric("USD/KRW", f"₩{latest.get('USDKRW=X', 0):,.1f}", f"{(latest.get('USDKRW=X',0)/prev.get('USDKRW=X',1)-1)*100:+.2f}%", delta_color="inverse")
                
                # 공포와 탐욕 지수 (Progress Bar로 트렌디하게 변경)
                vix_val = latest.get('^VIX', 20)
                fg_score = max(0, min(100, 100 - (vix_val - 10) * 2.5)) # 간단 예시식
                st.markdown(f"**🧠 시장 공포 & 탐욕 지수:** `{'극심한 공포' if fg_score<25 else '공포' if fg_score<45 else '중립' if fg_score<55 else '탐욕' if fg_score<75 else '극심한 탐욕'}`")
                st.progress(fg_score / 100.0)
            else:
                st.warning("⚠️ 야후 파이낸스 서버 혼잡(Rate Limit)으로 지표를 불러오지 못했습니다. 잠시 후 다시 접속해 주세요.")

    with col_right:
        with st.container(border=True):
            st.markdown("##### 📉 장단기 금리차 (10Y - 2Y Yield Curve)")
            @st.cache_data(ttl=86400)
            def fetch_yield_curve():
                try:
                    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y"
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    res = requests.get(url, headers=headers, timeout=5)
                    if "<html" not in res.text[:100].lower():
                        return pd.read_csv(StringIO(res.text), parse_dates=['DATE'], index_col='DATE').replace('.', np.nan).astype(float).dropna()
                except: return None
            
            yc_data = fetch_yield_curve()
            if yc_data is not None and not yc_data.empty:
                yc_data = yc_data[yc_data.index > (datetime.today() - timedelta(days=365*5))]
                fig_yc = go.Figure()
                fig_yc.add_trace(go.Scatter(x=yc_data.index, y=yc_data['T10Y2Y'], fill='tozeroy', name="장단기 금리차", line=dict(color=C_WARN)))
                fig_yc.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="역전 기준선 (Recession Warning)")
                
                custom_yc = THEME_LAYOUT.copy()
                custom_yc.update(height=220)
                fig_yc.update_layout(**custom_yc)
                st.plotly_chart(fig_yc, use_container_width=True)
            else:
                st.info("장단기 금리차 데이터를 불러오는 중 오류가 발생했습니다. (FRED API 차단)")


# =====================================================================
# [5] 페이지 구성: AMLS 백테스트 (기존 유지)
# =====================================================================
def page_amls_backtest():
    st.title("🦅 전략 시뮬레이터 (Tearsheet)")
    # ... (기존 백테스트 페이지 코드 유지) ...
    pass


# =====================================================================
# [6] 페이지 구성: AI 시스템 분석관 (글씨 잘림 해결 및 트렌디 UI)
# =====================================================================
def page_ai_analyst():
    st.title("⚡ AI 시스템 분석관")
    
    with st.spinner("AI 엔진 동기화 중..."): 
        ms = get_market_status()
        rt_prices = get_realtime_prices()

    if rt_prices:
        for k, v in rt_prices.items():
            if k in ms['prices'] and pd.notna(v): ms['prices'][k] = v
        if pd.notna(rt_prices.get('^VIX', None)): ms['vix'] = rt_prices['^VIX']
        if pd.notna(rt_prices.get('QQQ', None)): ms['qqq'] = rt_prices['QQQ']
        if pd.notna(rt_prices.get('SMH', None)): ms['smh'] = rt_prices['SMH']
        
        # 실시간 레짐 재계산
        vix_rt, qqq_rt = ms['vix'], ms['qqq']
        if vix_rt > 40: rt_tgt = 4
        elif qqq_rt < ms['ma200']: rt_tgt = 3
        elif qqq_rt >= ms['ma200'] and ms['ma50'] >= ms['ma200'] and vix_rt < 25: rt_tgt = 1
        else: rt_tgt = 2
        
        ms['target_regime'] = rt_tgt
        if rt_tgt > ms['regime']:
            ms['regime'] = rt_tgt
            ms['is_waiting'] = False

    app_reg = ms['regime']; tgt_reg = ms['target_regime']; is_wait = ms['is_waiting']; wait_d = ms['wait_days']; dur = ms['regime_duration']
    entry_g = ms['entry_grade']; direction = ms['regime_direction']
    vix_c = ms['vix']; qqq_c = ms['qqq']; ma200_c = ms['ma200']; smh_c = ms['smh']; smh_ma50_c = ms['smh_ma50']
    
    s_stat = "돌파" if smh_c > smh_ma50_c else "붕괴"
    r_stat = "통과" if ms['smh_3m_ret'] > 0.05 else "미달"
    rsi_stat = "통과" if ms['smh_rsi'] > 50 else "미달"
    soxl_res = "승인" if (smh_c > smh_ma50_c and ms['smh_3m_ret'] > 0.05 and ms['smh_rsi'] > 50) else "보류"

    # 레짐별 설명/조언 (기존 유지)
    if app_reg == 1:
        reg_t = "[R1: 완벽 강세장]"
        reg_d = f"VIX({vix_c:.1f}) 안정권 및 나스닥({qqq_c:.0f}) 정배열 유지. 하방 리스크가 제한적이므로 3배 레버리지를 가동해 상승분을 캡처하십시오."
    elif app_reg == 2:
        reg_t = "[R2: 조정/경계]"
        reg_d = f"장기 추세는 유효하나 VIX({vix_c:.1f})가 상승했거나 단기 모멘텀이 약화되었습니다. 과도한 레버리지를 2배수 이하로 축소하십시오."
    elif app_reg == 3:
        reg_t = "[R3: 장기 하락장]"
        reg_d = f"나스닥({qqq_c:.0f})이 200일선({ma200_c:.0f})을 하향 이탈했습니다. 하락 추세가 컨펌되었으니 레버리지 청산 후 GLD로 방어하십시오."
    else:
        reg_t = "[R4: 시스템 패닉]"
        reg_d = f"VIX({vix_c:.1f}) 40 돌파. 시장이 이성을 상실한 시스템 리스크 구간입니다. 주식을 전량 매도하고 안전자산으로 대피하십시오."

    # 🌱 신규 자금 조언 (기존 유지)
    dir_map = {"ascending": "상향 전환", "descending": "하향 전환", "stable": "현재 상태 유지"}
    dir_kr = dir_map.get(direction, "-")
    
    if direction == 'ascending' and dur <= 10: summ = "상향 전환 직후 골든타임. 진입 비중 확대를 적극 권장합니다."
    elif direction == 'ascending': summ = "상승 추세 안정화. 계획된 비중대로 편안하게 분할 매수하십시오."
    elif direction == 'descending' and dur <= 20: summ = "하향 전환 발생. 추가 하락 우려가 있으므로 신규 매수를 전면 보류하십시오."
    elif direction == 'descending': summ = "장기 하락 중. 완벽한 상승 신호가 뜰 때까지 현금을 대기하십시오."
    elif dur > 60: summ = "레짐 장기화로 추세 반전 리스크 누적. 보수적인 분할 진입을 추천합니다."
    else: summ = "레짐 안정적. 시스템 룰에 맞춰 평소처럼 자금을 정상 운용하십시오."

    # 거물의 속삭임 (기존 유지)
    quotes_r1 = ["강세장은 비관 속에서 태어나, 회의 속에서 자라며, 낙관 속에서 성숙하고, 행복 속에서 죽는다. - 존 템플턴", "10년 이상 볼 것이 아니면 단 10분도 그 주식을 갖고 있지 마라. - 워런 버핏"]
    quotes_r2 = ["위험은 자신이 무엇을 하는지 모르는 데서 온다. - 워런 버핏", "투자의 가장 큰 적은 바로 자기 자신이다. - 벤저민 그레이엄"]
    quotes_r3 = ["떨어지는 칼날을 맨손으로 잡지 마라. - 피터 린치", "성공적인 투자는 영원히 기다리는 것이다. - 찰리 멍거"]
    quotes_r4 = ["남들이 겁을 먹고 있을 때 욕심을 부려라. - 워런 버핏", "공포가 절정에 달했을 때가 가장 안전한 매수 시점이다. - 존 템플턴"]
    q_list = quotes_r1 if ms['regime']==1 else (quotes_r2 if ms['regime']==2 else (quotes_r3 if ms['regime']==3 else quotes_r4))

    # 🔥 [개편] 투박한 게이지를 없애고 세련된 메트릭 위젯 도입 (글씨 잘림 방지)
    st.markdown("#### 📊 시장 핵심 지표 판독기")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.metric(label="시장 공포지수 (VIX)", value=f"{vix_c:.2f}", delta="안정권" if vix_c < 25 else "위험권", delta_color="inverse")
    with col2:
        with st.container(border=True):
            gap_pct = (qqq_c / ma200_c - 1) * 100
            st.metric(label="나스닥 200일선 이격도", value=f"{gap_pct:+.2f}%", delta="추세 상회" if gap_pct > 0 else "추세 하회", delta_color="normal")
    with col3:
        with st.container(border=True):
            rsi_val = ms['smh_rsi']
            rsi_status = "과열" if rsi_val > 70 else ("침체" if rsi_val < 30 else "보통")
            st.metric(label="반도체(SMH) 단기 RSI", value=f"{rsi_val:.1f}", delta=rsi_status, delta_color="off")
            
    st.write("")

    # 🔥 [개편] HTML 박스를 없애고 네이티브 컨테이너 기반의 유연한 리포트 (글씨 잘림 완벽 방지)
    st.markdown("#### 🤖 AI 전략 분석관 Report")
    with st.container(border=True):
        st.markdown(f"### 현재 국면: {reg_t}")
        st.markdown(f"**진단:** {reg_d}")
        st.markdown(f"**⏱️ 상태 유지 기간:** 현재 R{app_reg} 체류 {dur}일째")
        
        # 하락장 경고창 트렌디하게 변경
        if is_wait and tgt_reg < app_reg:
            st.warning(f"**⏳ 상향 전환 검증 진행 중 ({wait_d}/5일차)**\n\n현재 시장 지표는 **[R{tgt_reg}]** 조건을 충족했으나, 휩쏘(속임수)를 피하기 위해 5일 연속 체류를 확인 중입니다. 대기 기간 동안은 보수적으로 비중을 유지합니다.")
        elif tgt_reg > app_reg:
            st.error(f"**🚨 하락 전환 주의 발동**\n\n현재 시장 지표가 **[R{tgt_reg}]** 악화 조건을 터치했습니다. 오늘 종가가 이대로 마감되면 내일 아침 즉시 시스템이 하향 전환됩니다.")
        else:
            st.success("✅ **특이사항 없음:** 시스템 지표가 안정적인 상태를 가리키고 있습니다.")
            
        st.info(f"📜 **거물의 속삭임:** {random.choice(q_list)}")

    st.write("")
    
    # 🔥 [개편] 투박한 HTML 박스를 없애고 유연한 컨테이너 기반 2분할 (글씨 잘림 방지)
    col_soxl, col_entry = st.columns(2)
    with col_soxl:
        with st.container(border=True):
            st.markdown("#### ⚡ SOXL 진입 판독기")
            st.write(f"- **50MA 추세:** {s_stat} (기준: ${smh_ma50_c:.1f})")
            st.write(f"- **3M 모멘텀:** {r_stat} (누적 {ms['smh_3m_ret']*100:+.1f}%)")
            st.write(f"- **RSI 지수:** {rsi_stat} (기준: 50 초과)")
            st.divider()
            if soxl_res == "승인": st.success("**결론: SOXL 편입 승인 완료**")
            else: st.warning("**결론: USD(2X) 방어 모드 유지**")
            
    with col_entry:
        with st.container(border=True):
            st.markdown("#### 🌱 신규 자금 투입 가이드")
            st.write(f"- **진입 적합도:** {entry_g}")
            st.write(f"- **추세 방향:** {dir_kr}")
            st.write(f"- **AI 조언:** {summ}")
            st.divider()
            st.info("💡 위 조언은 'AMLS v4.4'의 기계적 룰과 궤를 같이합니다.")

    st.write("")
    
    # 레짐 판단 근거 차트 (기존 유지)
    st.markdown("#### 🔍 레짐 판단 근거 시각화")
    c_df = get_regime_chart_data()
    if not c_df.empty:
        fig_rc = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.08, subplot_titles=("나스닥 (QQQ) 장단기 추세", "시장 공포지수 (VIX)"))
        
        fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['QQQ'], name="QQQ (Price)", line=dict(color=C_SAFE, width=2)), row=1, col=1)
        fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['MA50'], name="50MA", line=dict(color=C_WARN, width=1.5, dash='dot')), row=1, col=1)
        fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['MA200'], name="200MA", line=dict(color=C_DOWN, width=2)), row=1, col=1)
        
        fig_rc.add_trace(go.Scatter(x=c_df.index, y=c_df['^VIX'], name="VIX", line=dict(color='#9b59b6', width=1.5), fill='tozeroy'), row=2, col=1)
        fig_rc.add_hline(y=40, line_dash="dash", line_color="red", row=2, col=1, annotation_text="패닉 (40)")
        fig_rc.add_hline(y=25, line_dash="dash", line_color="orange", row=2, col=1, annotation_text="경계 (25)")
        
        cust_rc = THEME_LAYOUT.copy()
        cust_rc.update(height=500, hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
        fig_rc.update_layout(**cust_rc)
        
        with st.container(border=True):
            st.plotly_chart(fig_rc, use_container_width=True)
            st.caption("💡 **레짐 판단의 핵심 지표:** 나스닥(QQQ)이 200일 이동평균선(빨간선) 위에 있는지, 공포지수(VIX)가 25나 40을 넘었는지가 전략의 핵심입니다.")
    else:
        st.error("데이터를 불러오지 못했습니다.")


# =====================================================================
# [7] 페이지 구성: 내 포트폴리오 관리 (기존 유지)
# =====================================================================
def make_portfolio_page(acc_name):
    # ... (기존 포트폴리오 페이지 함수 코드 유지) ...
    pass


# =====================================================================
# [8] 네비게이션 및 메인 실행
# =====================================================================
st.sidebar.markdown("---")
# (생략: 테마 커스텀, 백업 복구 등의 사이드바 기능 코드 유지)

pages = {
    "시스템": [
        st.Page(page_market_dashboard, title="마켓 터미널", icon="🌐"), 
        st.Page(page_amls_backtest, title="백테스트 엔진", icon="🦅"),
        st.Page(page_ai_analyst, title="AI 시스템 분석관", icon="⚡") # 🔥 분석관 정상 등록
    ],
    "포트폴리오": [],
    "설정": [
        # (생략: 전략 명세서, 계좌 관리 등 기존 설정 페이지 등록 코드 유지)
    ]
}

# (생략: 포트폴리오 페이지 자동 등록 및 네비게이션 실행 코드 유지)
pg = st.navigation(pages)
pg.run()
