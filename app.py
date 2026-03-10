import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import json
import os
import requests
from io import StringIO
import copy
import time

warnings.filterwarnings('ignore')

# =====================================================================
# [0] 시스템 설정, 데이터 관리 및 커스텀 테마 주입
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 포트폴리오", layout="wide", initial_sidebar_state="expanded")

SETTINGS_FILE = "amls_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "text_color": "#1d1d1f",
        "chart_colors": {
            "TQQQ": "#ff3b30", "SOXL": "#af52de", "USD": "#5856d6",
            "QLD": "#ff9500", "SSO": "#ffcc00", "QQQ": "#007aff",
            "GLD": "#34c759", "CASH": "#8e8e93"
        }
    }

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=4)

if 'settings' not in st.session_state:
    st.session_state['settings'] = load_settings()

def apply_apple_glass_style():
    text_color = st.session_state['settings']['text_color']
    
    st.markdown(f"""
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

.stApp {{
    background: radial-gradient(circle at 15% 50%, rgba(240, 244, 255, 1), rgba(255, 255, 255, 0)), 
                radial-gradient(circle at 85% 30%, rgba(230, 240, 255, 1), rgba(255, 255, 255, 0)) !important;
    background-color: #f5f5f7 !important;
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    color: {text_color} !important;
    letter-spacing: -0.01em;
}}

div[data-testid="stMetricValue"] > div,
div[data-testid="stMetricDelta"] > div,
p, h1, h2, h3, h4, h5, h6, span, label, .stMarkdown {{
    white-space: normal !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {{
    background: rgba(255, 255, 255, 0.65) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    border-radius: 20px !important;
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.06) !important;
    padding: 1.5rem !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{
    box-shadow: 0 8px 32px -1px rgba(0, 0, 0, 0.1) !important;
}}

.stButton>button {{
    background-color: rgba(255, 255, 255, 0.8) !important;
    color: #007aff !important;
    border: 1px solid rgba(0, 122, 255, 0.3) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    backdrop-filter: blur(10px);
    transition: all 0.2s;
}}
.stButton>button:hover {{
    background-color: #007aff !important;
    color: #ffffff !important;
    transform: scale(1.02);
}}

input, textarea, select, div[data-baseweb="select"] > div {{
    background-color: rgba(255, 255, 255, 0.5) !important;
    backdrop-filter: blur(10px) !important;
    color: {text_color} !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    border-radius: 12px !important;
}}
input:focus, textarea:focus {{
    border-color: #007aff !important;
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2) !important;
}}

[data-testid="stDataFrame"] {{
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
    background: rgba(255, 255, 255, 0.5) !important;
}}

[data-testid="stSidebar"] {{
    background: rgba(245, 245, 247, 0.7) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid rgba(0,0,0,0.05) !important;
}}

button[data-baseweb="tab"] {{
    color: #8e8e93 !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    background-color: transparent !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: #1d1d1f !important;
    border-bottom-color: #1d1d1f !important;
    border-bottom-width: 2px !important;
}}

div[data-testid="stMetricValue"] {{
    font-weight: 700 !important;
    font-size: 2rem !important;
    color: {text_color} !important;
}}
div[data-testid="stMetricLabel"] {{
    color: #8e8e93 !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
}}

.sidebar-link {{
    display: flex;
    align-items: center;
    padding: 8px 12px;
    margin-bottom: 4px;
    border-radius: 10px;
    text-decoration: none !important;
    color: #1d1d1f !important;
    font-weight: 600;
    font-size: 0.95rem;
    background-color: transparent;
    transition: background-color 0.2s, transform 0.1s;
}}
.sidebar-link:hover {{
    background-color: rgba(0,0,0,0.05);
    transform: translateX(2px);
}}
.sidebar-link span {{
    margin-right: 10px;
    font-size: 1.1rem;
}}
</style>
    """, unsafe_allow_html=True)

apply_apple_glass_style()

GLASS_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'Pretendard', -apple-system, sans-serif", color=st.session_state['settings']['text_color'], size=13),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', zerolinecolor='rgba(0,0,0,0.1)'),
    yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', zerolinecolor='rgba(0,0,0,0.1)')
)

C_UP = "#34c759"
C_DOWN = "#ff3b30"
C_WARN = "#ff9500"
C_SAFE = "#007aff"

ACCOUNTS_FILE = "amls_multi_accounts.json"
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "GLD", "CASH"]

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

if 'accounts' not in st.session_state:
    loaded = load_accounts_data()
    if not loaded:
        loaded = {
            "AMLS v4.3": {  
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0
            }
        }
    st.session_state['accounts'] = loaded

needs_save = False
if "기본 계좌 (AMLS)" in st.session_state['accounts']:
    st.session_state['accounts']["AMLS v4.3"] = st.session_state['accounts'].pop("기본 계좌 (AMLS)")
    needs_save = True

for acc_name, acc_data in st.session_state['accounts'].items():
    if "seed_history" not in acc_data:
        acc_data["seed_history"] = {}
        needs_save = True
    if "target_portfolio_value" not in acc_data:
        acc_data["target_portfolio_value"] = 100000.0
        needs_save = True

    existing_tickers = [item["티커 (Ticker)"] for item in acc_data["portfolio"]]
    port_dict = {item["티커 (Ticker)"]: item for item in acc_data["portfolio"]}
    new_port = []
    for req_t in REQUIRED_TICKERS:
        if req_t in port_dict: 
            item = port_dict[req_t]
            if "매입 환율" not in item: item["매입 환율"] = 0.0; needs_save = True
            if "태그" not in item: item["태그"] = "코어" if req_t != "CASH" else "현금"; needs_save = True
            new_port.append(item)
        else: 
            new_port.append({"티커 (Ticker)": req_t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어" if req_t != "CASH" else "현금"})
            needs_save = True
    acc_data["portfolio"] = new_port
if needs_save: save_accounts_data(st.session_state['accounts'])


# =====================================================================
# [1] 글로벌 백엔드 함수
# =====================================================================
@st.cache_data(ttl=3600)
def load_amls_backtest_data(start, end, init_cap, monthly_cont, rebal_freq="월 1회"):
    tickers = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']
    start_str = (start - timedelta(days=400)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    try: data = yf.download(tickers, start=start_str, end=end_str, progress=False, auto_adjust=True)['Close']
    except: data = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
    data = data.ffill().dropna(subset=['QQQ', '^VIX'])

    df = pd.DataFrame(index=data.index)
    for t in data.columns: df[t] = data[t]

    df['QQQ_MA50'] = df['QQQ'].rolling(window=50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(window=200).mean()
    df['QQQ_RSI'] = ta.rsi(df['QQQ'], length=14)
    df['SMH_MA50'] = df['SMH'].rolling(window=50).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(periods=63)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)

    df = df.dropna(subset=['QQQ_MA200', 'SMH_RSI']).loc[pd.to_datetime(start):]
    daily_returns = df[data.columns].pct_change().fillna(0)

    def get_target_regime(row):
        vix, qqq, ma200, ma50 = row['^VIX'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
        if vix > 40: return 4
        if qqq < ma200: return 3
        if qqq >= ma200 and ma50 >= ma200 and vix < 25: return 1
        return 2

    df['Target_Regime'] = df.apply(get_target_regime, axis=1)
    
    actual_regime_v4 = []; actual_regime_v4_3 = []
    current_v4 = 3; current_v4_3 = 3
    pend_v4 = None; pend_v4_3 = None
    cnt_v4 = 0; cnt_v4_3 = 0

    for i in range(len(df)):
        tr = df['Target_Regime'].iloc[i]
        if tr > current_v4: current_v4 = tr; pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
        elif tr < current_v4:
            if tr == pend_v4:
                cnt_v4 += 1
                if cnt_v4 >= 5: current_v4 = tr; pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
                else: actual_regime_v4.append(current_v4)
            else: pend_v4 = tr; cnt_v4 = 1; actual_regime_v4.append(current_v4)
        else: pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
        
        if tr > current_v4_3: current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
        elif tr < current_v4_3: 
            if tr == pend_v4_3:
                cnt_v4_3 += 1
                if cnt_v4_3 >= 5: current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
                else: actual_regime_v4_3.append(current_v4_3 - 1)
            else: pend_v4_3 = tr; cnt_v4_3 = 1; actual_regime_v4_3.append(current_v4_3 - 1)
        else: pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)

    df['Signal_Regime_v4'] = pd.Series(actual_regime_v4, index=df.index).shift(1).bfill()
    df['Signal_Regime_v4_3'] = pd.Series(actual_regime_v4_3, index=df.index).shift(1).bfill()

    def get_v4_weights(regime, use_soxl):
        w = {t: 0.0 for t in data.columns}; semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'] = 0.30, 0.20, 0.20, 0.15, 0.10
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['QQQ'], w['USD'] = 0.25, 0.20, 0.20, 0.15, 0.10
        elif regime == 3: w['GLD'], w['QQQ'], w['SPY'] = 0.35, 0.20, 0.10
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        return w

    def get_v4_3_weights(regime, use_soxl):
        w = {t: 0.0 for t in data.columns}; semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'] = 0.30, 0.20, 0.20, 0.15, 0.10
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'] = 0.30, 0.25, 0.20, 0.10, 0.05
        elif regime == 3: w['GLD'], w['QQQ'] = 0.50, 0.15
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        return w

    strategies = ['AMLS v4.3', 'AMLS v4', 'QQQ', 'QLD', 'TQQQ']
    ports = {s: init_cap for s in strategies}
    hists = {s: [init_cap] for s in ports.keys()}
    total_invested = init_cap
    weights_v4 = {t: 0.0 for t in data.columns}; weights_v4_3 = {t: 0.0 for t in data.columns}
    logs, days_since_v4, days_since_v4_3 = [], 0, 0

    for i in range(1, len(df)):
        today, yesterday = df.index[i], df.index[i-1]
        days_since_v4 += 1; days_since_v4_3 += 1
        ret_v4 = sum(weights_v4[t] * daily_returns[t].iloc[i] for t in data.columns)
        ret_v4_3 = sum(weights_v4_3[t] * daily_returns[t].iloc[i] for t in data.columns)
        
        ports['AMLS v4'] *= (1 + ret_v4); ports['AMLS v4.3'] *= (1 + ret_v4_3)
        for s in ['QQQ', 'QLD', 'TQQQ']: ports[s] *= (1 + daily_returns[s].iloc[i])
        
        for t in data.columns:
            if ports['AMLS v4'] > 0: weights_v4[t] = weights_v4[t]*(1+daily_returns[t].iloc[i])/(1+ret_v4)
            if ports['AMLS v4.3'] > 0: weights_v4_3[t] = weights_v4_3[t]*(1+daily_returns[t].iloc[i])/(1+ret_v4_3)
            
        if today.month != yesterday.month:
            for s in ports: ports[s] += monthly_cont
            total_invested += monthly_cont
        for s in ports: hists[s].append(ports[s])
        
        use_soxl = (df['SMH'].iloc[i-1] > df['SMH_MA50'].iloc[i-1]) and (df['SMH_3M_Ret'].iloc[i-1] > 0.05) and (df['SMH_RSI'].iloc[i-1] > 50)
        
        sig_r_v4 = df['Signal_Regime_v4'].iloc[i]
        rebal_v4 = False
        if sig_r_v4 != df['Signal_Regime_v4'].iloc[i-1] or i == 1: rebal_v4 = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal_v4 = True
        elif "주 1회" in rebal_freq and days_since_v4 >= 5: rebal_v4 = True
        elif "2주 1회" in rebal_freq and days_since_v4 >= 10: rebal_v4 = True
        elif "3주 1회" in rebal_freq and days_since_v4 >= 15: rebal_v4 = True
        if rebal_v4: weights_v4 = get_v4_weights(sig_r_v4, use_soxl); days_since_v4 = 0

        sig_r_v4_3 = df['Signal_Regime_v4_3'].iloc[i]
        rebal_v4_3 = False
        if sig_r_v4_3 != df['Signal_Regime_v4_3'].iloc[i-1] or i == 1: rebal_v4_3 = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal_v4_3 = True
        elif "주 1회" in rebal_freq and days_since_v4_3 >= 5: rebal_v4_3 = True
        elif "2주 1회" in rebal_freq and days_since_v4_3 >= 10: rebal_v4_3 = True
        elif "3주 1회" in rebal_freq and days_since_v4_3 >= 15: rebal_v4_3 = True
        if rebal_v4_3:
            weights_v4_3 = get_v4_3_weights(sig_r_v4_3, use_soxl)
            log_type = "🚨 레짐 전환" if sig_r_v4_3 != df['Signal_Regime_v4_3'].iloc[i-1] else f"🔄 정기 ({rebal_freq.split(' ')[0]})"
            semi_target = "SOXL (3x)" if use_soxl and sig_r_v4_3 == 1 else ("USD (2x)" if sig_r_v4_3 in [1, 2] else "-")
            logs.append({"날짜": today.strftime('%Y-%m-%d'), "유형": log_type, "국면": f"R{int(sig_r_v4_3)}", "반도체": semi_target, "평가액": ports['AMLS v4.3']})
            days_since_v4_3 = 0

    for s in ports: df[f'{s}_Value'] = hists[s]
    inv_arr = [init_cap]; curr_inv = init_cap
    for i in range(1, len(df)):
        if df.index[i].month != df.index[i-1].month: curr_inv += monthly_cont
        inv_arr.append(curr_inv)
    df['Invested'] = inv_arr
    return df, logs, data.columns


# =====================================================================
# [2] 페이지 구성: 글로벌 마켓 대시보드
# =====================================================================
def page_market_dashboard():
    st.title("🌐 글로벌 매크로 터미널")
    
    # 띄어쓰기 없이 HTML 삽입
    components.html("""<div class="tradingview-widget-container" style="border-radius: 16px; overflow: hidden; border: 1px solid rgba(0,0,0,0.05);">
<div class="tradingview-widget-container__widget"></div>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
{
"symbols": [
{"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"},
{"proName": "FOREXCOM:NSXUSD", "title": "NASDAQ 100"},
{"description": "TQQQ", "proName": "NASDAQ:TQQQ"},
{"description": "SOXL", "proName": "ARCA:SOXL"},
{"description": "USD/KRW", "proName": "FX_IDC:USDKRW"},
{"description": "GOLD", "proName": "OANDA:XAUUSD"}
],
"showSymbolLogo": true, "colorTheme": "light", "locale": "kr"
}
</script>
</div>""", height=70)

    col_left, col_right = st.columns([1, 1.8])
    with col_left:
        with st.container(border=True):
            st.markdown("##### 📈 주요 지수 현황판")
            tickers = ['^GSPC', '^IXIC', '^VIX', 'USDKRW=X']
            indices_df = yf.download(tickers, start=datetime.today()-timedelta(days=365), progress=False)['Close'].ffill()
            if not indices_df.empty:
                c1, c2 = st.columns(2); latest = indices_df.iloc[-1]; prev = indices_df.iloc[-2]
                c1.metric("S&P 500", f"{latest.get('^GSPC', 0):,.0f}", f"{(latest.get('^GSPC',0)/prev.get('^GSPC',1)-1)*100:+.2f}%")
                c2.metric("NASDAQ", f"{latest.get('^IXIC', 0):,.0f}", f"{(latest.get('^IXIC',0)/prev.get('^IXIC',1)-1)*100:+.2f}%")
                c3, c4 = st.columns(2)
                c3.metric("VIX (공포지수)", f"{latest.get('^VIX', 0):,.2f}", f"{(latest.get('^VIX',0)/prev.get('^VIX',1)-1)*100:+.2f}%", delta_color="inverse")
                c4.metric("USD/KRW 환율", f"₩{latest.get('USDKRW=X', 0):,.1f}", f"{(latest.get('USDKRW=X',0)/prev.get('USDKRW=X',1)-1)*100:+.2f}%", delta_color="inverse")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=indices_df.index, y=indices_df['^GSPC']/indices_df['^GSPC'].iloc[0]*100, name="S&P 500", line=dict(color=C_SAFE, width=3)))
                fig.add_trace(go.Scatter(x=indices_df.index, y=indices_df['^IXIC']/indices_df['^IXIC'].iloc[0]*100, name="NASDAQ", line=dict(color=C_UP, width=3)))
                custom_l = GLASS_LAYOUT.copy()
                custom_l.update(height=240, showlegend=False)
                fig.update_layout(**custom_l)
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.markdown("##### 🗺️ S&P 500 섹터 맵")
            components.html("""<div style="border-radius: 16px; overflow: hidden; height: 100%;">
<iframe src="https://www.tradingview.com/embed-widget-stock-heatmap/?locale=kr#%7B%22dataSource%22%3A%22SPX500%22%2C%22blockSize%22%3A%22market_cap_basic%22%2C%22blockColor%22%3A%22change%22%2C%22grouping%22%3A%22sector%22%2C%22colorTheme%22%3A%22light%22%7D" width="100%" height="450" frameborder="0"></iframe>
</div>""", height=460)


# =====================================================================
# [3] 페이지 구성: AMLS 백테스트
# =====================================================================
def page_amls_backtest():
    st.title("🦅 AMLS 백테스트 엔진")
    st.markdown("과거 데이터를 통해 다양한 시장 조건에서 전략의 퍼포먼스를 점검합니다.")

    st.sidebar.header("⚙️ 시뮬레이션 설정")
    BACKTEST_START = st.sidebar.date_input("시작일", datetime(2018, 1, 1))
    BACKTEST_END = st.sidebar.date_input("종료일", datetime.today())
    INITIAL_CAPITAL = st.sidebar.number_input("초기 자본금 ($)", value=10000, step=1000)
    MONTHLY_CONTRIBUTION = st.sidebar.number_input("매월 추가 적립금 ($)", value=2000, step=500)
    REBAL_FREQ = st.sidebar.selectbox("🔄 정기 리밸런싱 주기", ["월 1회", "주 1회 (5거래일)", "2주 1회 (10거래일)", "3주 1회 (15거래일)"], index=0)

    with st.spinner('방대한 시장 데이터를 연산 중입니다...'):
        df, logs, tickers = load_amls_backtest_data(BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL, MONTHLY_CONTRIBUTION, REBAL_FREQ)
    
    def calc_metrics(series, invested_series):
        final_val = series.iloc[-1]; total_inv = invested_series.iloc[-1]
        total_ret = (final_val / total_inv) - 1
        days = (series.index[-1] - series.index[0]).days
        cagr = (final_val / invested_series.iloc[-1]) ** (365.25 / days) - 1 if days > 0 else 0
        mdd = ((series / series.cummax()) - 1).min()
        daily_ret = series.pct_change().dropna()
        sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252)) if daily_ret.std() != 0 else 0
        return final_val, total_ret, cagr, mdd, sharpe

    strats = ['AMLS v4.3', 'QQQ', 'QLD', 'TQQQ']
    metrics_data = []
    for s in strats:
        fv, tr, cagr, mdd, shp = calc_metrics(df[f'{s}_Value'], df['Invested'])
        metrics_data.append({"전략/종목": s, "최종 평가금액": f"${fv:,.0f}", "수익률": f"{tr*100:+.1f}%", "연평균(CAGR)": f"{cagr*100:.1f}%", "최대 낙폭(MDD)": f"{mdd*100:.1f}%", "샤프 지수": f"{shp:.2f}"})
    metrics_df = pd.DataFrame(metrics_data).set_index("전략/종목")

    tab1, tab2, tab3 = st.tabs(["📊 성과 요약", "📈 자산 추이", "📝 매매 로그"])

    with tab1:
        st.markdown("#### 🏆 핵심 퍼포먼스")
        st.info(f"💡 **투입 원금 총합:** ${df['Invested'].iloc[-1]:,.0f} (초기 {INITIAL_CAPITAL} + 매월 {MONTHLY_CONTRIBUTION} 적립)")
        st.dataframe(metrics_df, use_container_width=True)

        st.markdown("#### 🥧 국면별 자산 배분 비중")
        c1, c2, c3, c4 = st.columns(4)
        def get_w(reg):
            if reg == 1: return {'TQQQ':30, 'SOXL/USD':20, 'QLD':20, 'SSO':15, 'GLD':10, 'CASH':5}
            elif reg == 2: return {'QLD':30, 'SSO':25, 'GLD':20, 'USD':10, 'QQQ':5, 'CASH':10}
            elif reg == 3: return {'GLD':50, 'CASH':35, 'QQQ':15}
            elif reg == 4: return {'GLD':50, 'CASH':40, 'QQQ':10}
        
        for i, col in enumerate([c1, c2, c3, c4]):
            r = i+1; w = {k:v for k,v in get_w(r).items() if v>0}
            fig_p = go.Figure(go.Pie(labels=list(w.keys()), values=list(w.values()), hole=0.5, marker=dict(colors=[st.session_state['settings']['chart_colors'].get(k.split('/')[0], '#d1d1d6') for k in w.keys()])))
            cust_p = GLASS_LAYOUT.copy(); cust_p.update(title=f"Regime {r}", title_x=0.5, height=250, margin=dict(t=40,b=10,l=10,r=10), showlegend=False)
            fig_p.update_layout(**cust_p)
            fig_p.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color='#1d1d1f', size=12))
            col.plotly_chart(fig_p, use_container_width=True)

    with tab2:
        st.markdown("#### 📈 자산 성장 곡선")
        use_log = st.checkbox("Y축 로그 스케일", value=False)
        fig_eq = go.Figure()
        
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['AMLS v4.3_Value'], name='AMLS v4.3', line=dict(color=C_UP, width=4)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['QQQ_Value'], name='QQQ', line=dict(color=C_SAFE, width=2)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['TQQQ_Value'], name='TQQQ', line=dict(color=C_DOWN, width=2)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['Invested'], name='원금', line=dict(color='#8e8e93', width=2, dash='dot')))
        
        if use_log: fig_eq.update_yaxes(type="log")
        cust_eq = GLASS_LAYOUT.copy(); cust_eq.update(height=450, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_eq.update_layout(**cust_eq)
        st.plotly_chart(fig_eq, use_container_width=True)

    with tab3:
        st.markdown("#### 📝 시스템 매매 로그")
        log_df = pd.DataFrame(logs)[::-1]
        if not log_df.empty:
            log_df['평가액'] = log_df['평가액'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(log_df, hide_index=True, use_container_width=True, height=400)


# =====================================================================
# [4] 페이지 구성: 내 포트폴리오 관리 (미니멀 분석관 요약 폼 적용)
# =====================================================================
def make_portfolio_page(acc_name):
    def page_func():
        st.title(f"💼 {acc_name}")
        st.markdown("나만의 포트폴리오를 스마트하게 관리하세요.")
        
        curr_acc_data = st.session_state['accounts'][acc_name]
        pf_df = pd.DataFrame(curr_acc_data["portfolio"])
        for col in ["수량 (주/달러)", "평균 단가 ($)", "매입 환율", "목표가 ($)"]:
            if col in pf_df.columns: pf_df[col] = pf_df[col].astype(float)

        @st.cache_data(ttl=1800)
        def get_market_status():
            TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']
            data = yf.download(TICKERS, start=datetime.today()-timedelta(days=400), progress=False)['Close'].ffill()
            today = data.iloc[-1]; yesterday = data.iloc[-2]
            ma200 = data['QQQ'].rolling(200).mean().iloc[-1]
            ma50 = data['QQQ'].rolling(50).mean().iloc[-1]
            smh_ma50 = data['SMH'].rolling(50).mean().iloc[-1]
            smh_3m_ret = (data['SMH'].iloc[-1] / data['SMH'].iloc[-63]) - 1
            smh_rsi = ta.rsi(data['SMH'], length=14).iloc[-1]
            
            if today['^VIX'] > 40: reg = 4
            elif today['QQQ'] < ma200: reg = 3
            elif today['QQQ'] >= ma200 and ma50 >= ma200 and today['^VIX'] < 25: reg = 1
            else: reg = 2

            try:
                fx_data = yf.download('USDKRW=X', period='5d', progress=False)['Close'].ffill()
                current_usdkrw = float(fx_data.iloc[:, 0].iloc[-1] if isinstance(fx_data, pd.DataFrame) else fx_data.iloc[-1])
            except: current_usdkrw = 0.0

            ma200_s = data['QQQ'].rolling(200).mean(); ma50_s = data['QQQ'].rolling(50).mean()
            regime_series = []
            for i in range(len(data)):
                v = data['^VIX'].iloc[i]; q = data['QQQ'].iloc[i]; m200 = ma200_s.iloc[i]; m50 = ma50_s.iloc[i]
                if pd.isna(m200): regime_series.append(2); continue
                if v > 40: regime_series.append(4)
                elif q < m200: regime_series.append(3)
                elif q >= m200 and m50 >= m200 and v < 25: regime_series.append(1)
                else: regime_series.append(2)

            current_reg = regime_series[-1]; regime_duration = 0
            for i in range(len(regime_series)-1, -1, -1):
                if regime_series[i] == current_reg: regime_duration += 1
                else: break

            prev_reg = current_reg
            for i in range(len(regime_series)-regime_duration-1, -1, -1):
                prev_reg = regime_series[i]; break

            if current_reg < prev_reg: regime_direction = "ascending"
            elif current_reg > prev_reg: regime_direction = "descending"
            else: regime_direction = "stable"

            if regime_direction == "ascending": entry_grade = "최적 진입" if regime_duration <= 30 else "주의(전환위험)"
            elif regime_direction == "descending": entry_grade = "진입 보류" if regime_duration <= 20 else "바닥 탐색"
            else: entry_grade = "진입 적합"

            return {
                'regime': reg, 'vix': today['^VIX'], 'qqq': today['QQQ'], 'ma200': ma200, 'ma50': ma50,
                'smh': today['SMH'], 'smh_ma50': smh_ma50, 'smh_3m_ret': smh_3m_ret, 'smh_rsi': smh_rsi,
                'prices': today.to_dict(), 'prev_prices': yesterday.to_dict(), 'date': data.index[-1],
                'usdkrw': current_usdkrw, 'regime_duration': regime_duration, 'prev_regime': prev_reg,
                'regime_direction': regime_direction, 'entry_grade': entry_grade
            }

        @st.cache_data(ttl=60)
        def get_realtime_prices():
            RT_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
            try:
                rt = yf.download(RT_TICKERS, period='1d', interval='5m', prepost=True, progress=False)['Close']
                if rt.empty: return None
                return rt.ffill().iloc[-1].to_dict()
            except: return None

        with st.spinner("AI 퀀트 엔진 동기화 중..."): 
            ms = get_market_status()
            rt_prices = get_realtime_prices()

        if rt_prices:
            for k, v in rt_prices.items():
                if k in ms['prices'] and pd.notna(v): ms['prices'][k] = v
            if pd.notna(rt_prices.get('^VIX', None)): ms['vix'] = rt_prices['^VIX']
            if pd.notna(rt_prices.get('QQQ', None)): ms['qqq'] = rt_prices['QQQ']
            if pd.notna(rt_prices.get('SMH', None)): ms['smh'] = rt_prices['SMH']
            if pd.notna(rt_prices.get('USDKRW=X', None)): ms['usdkrw'] = rt_prices['USDKRW=X']
            vix_rt, qqq_rt = ms['vix'], ms['qqq']
            if vix_rt > 40: ms['regime'] = 4
            elif qqq_rt < ms['ma200']: ms['regime'] = 3
            elif qqq_rt >= ms['ma200'] and ms['ma50'] >= ms['ma200'] and vix_rt < 25: ms['regime'] = 1
            else: ms['regime'] = 2
            
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            et_hour = (now_utc.hour - 5) % 24 
            if 4 <= et_hour < 9.5: price_label = "Pre-market"
            elif 9.5 <= et_hour < 16: price_label = "Live"
            elif 16 <= et_hour < 20: price_label = "After-hours"
            else: price_label = "Live"
        else: price_label = "종가"

        live_prices = {k: ms['prices'].get(k, 1.0) for k in REQUIRED_TICKERS}; live_prices['CASH'] = 1.0
        prev_prices = {k: ms['prev_prices'].get(k, live_prices[k]) for k in REQUIRED_TICKERS}; prev_prices['CASH'] = 1.0
        current_usdkrw = ms['usdkrw']
        
        disp_df = pf_df.copy()
        disp_df["현재가 ($)"] = disp_df["티커 (Ticker)"].apply(lambda x: live_prices.get(x, 0.0))
        disp_df["현재 환율"] = current_usdkrw
        
        def cy(row):
            if row["수량 (주/달러)"] == 0 or row["평균 단가 ($)"] == 0 or row["티커 (Ticker)"] == "CASH": return 0.0
            return (row["현재가 ($)"] - row["평균 단가 ($)"]) / row["평균 단가 ($)"] * 100
        disp_df["수익률 (%)"] = disp_df.apply(cy, axis=1)
        
        def cy_krw(row):
            if row["수량 (주/달러)"] == 0 or row["평균 단가 ($)"] == 0 or row["티커 (Ticker)"] == "CASH": return 0.0
            if row["매입 환율"] <= 0 or current_usdkrw <= 0: return 0.0
            buy_krw = row["평균 단가 ($)"] * row["매입 환율"]; now_krw = row["현재가 ($)"] * current_usdkrw
            return (now_krw - buy_krw) / buy_krw * 100
        disp_df["원화 수익률 (%)"] = disp_df.apply(cy_krw, axis=1)

        total_val_now = 0.0; total_val_yest = 0.0; auto_seed = 0.0
        best_ticker = "-"; best_ret = -999.0
        asset_vals = {}
        
        for _, row in disp_df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            qty = float(row["수량 (주/달러)"] if pd.notna(row["수량 (주/달러)"]) else 0)
            avg_p = float(row["평균 단가 ($)"] if pd.notna(row["평균 단가 ($)"]) else 0)
            
            v_now = qty * live_prices.get(tkr, 0.0) if tkr != "CASH" else qty
            v_yest = qty * prev_prices.get(tkr, 0.0) if tkr != "CASH" else qty
            
            if v_now > 0: asset_vals[tkr] = v_now
            if qty > 0:
                total_val_now += v_now
                total_val_yest += v_yest
                auto_seed += qty if tkr == "CASH" else qty * avg_p
                r_ret = row["수익률 (%)"]
                if tkr != "CASH" and r_ret > best_ret: best_ret = r_ret; best_ticker = tkr

        daily_diff = total_val_now - total_val_yest
        daily_diff_pct = (daily_diff / total_val_yest * 100) if total_val_yest > 0 else 0.0

        st.session_state['accounts'][acc_name]["target_seed"] = auto_seed
        rebal_base = total_val_now if total_val_now > 0 else auto_seed

        # 실제 자산 이력 자동 저장
        today_str = datetime.now().strftime("%Y-%m-%d")
        history_changed = False
        last_seed = curr_acc_data["seed_history"].get(today_str, {}).get("seed")
        last_equity = curr_acc_data["seed_history"].get(today_str, {}).get("equity")
        
        if total_val_now > 0 or auto_seed > 0:
            if last_seed != auto_seed or last_equity != total_val_now:
                curr_acc_data["seed_history"][today_str] = {"seed": auto_seed, "equity": total_val_now}
                history_changed = True
        if history_changed: save_accounts_data(st.session_state['accounts'])


        # ------------------- 0. 최상단 목표 자산 달성률 바 -------------------
        target_val = curr_acc_data.get("target_portfolio_value", 100000.0)
        progress_pct = (total_val_now / target_val) * 100 if target_val > 0 else 0.0
        
        st.markdown("#### 🎯 포트폴리오 목표 달성률")
        c_prog, c_set = st.columns([4, 1.2])
        with c_set:
            new_target = st.number_input("목표 금액 ($)", min_value=0.0, value=float(target_val), step=10000.0, format="%.0f")
            if new_target != target_val:
                st.session_state['accounts'][acc_name]["target_portfolio_value"] = new_target
                save_accounts_data(st.session_state['accounts'])
                target_val = new_target
                progress_pct = (total_val_now / target_val) * 100 if target_val > 0 else 0.0
                st.rerun()
                
        with c_prog:
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); padding:20px; border-radius:20px; border:1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>
<div style='display:flex; justify-content:space-between; margin-bottom:10px;'>
<span style='color:#1d1d1f; font-weight:700; font-size:1.05rem;'>현재: ${total_val_now:,.0f}</span>
<span style='color:#8e8e93; font-weight:600; font-size:1.05rem;'>목표: ${target_val:,.0f}</span>
</div>
<div style='background-color:rgba(0,0,0,0.05); border-radius:12px; height:18px; width:100%; position:relative; overflow:hidden;'>
<div style='background:linear-gradient(90deg, #34c759, #32d74b); width:{min(100.0, progress_pct)}%; height:100%; border-radius:12px; transition:width 0.8s ease;'></div>
</div>
<div style='text-align:right; margin-top:8px; font-size:0.95rem; font-weight:700; color:#007aff;'>
{progress_pct:.2f}%
</div>
</div>
""", unsafe_allow_html=True)
            
        st.write("")
        st.divider()

        # ------------------- 1. 상단 요약 대시보드 -------------------
        st.markdown(f"#### 📊 실시간 요약 (기준: {price_label})")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); border-radius:16px; padding:15px; border:1px solid rgba(255,255,255,0.5); text-align:center;'>
<div style='color:#8e8e93; font-size:0.85rem; font-weight:600;'>💰 총 평가액 (Total Equity)</div>
<div style='color:#1d1d1f; font-size:1.6rem; font-weight:700; margin-top:5px;'>${total_val_now:,.0f}</div>
</div>""", unsafe_allow_html=True)
        with m2:
            pn_col = C_UP if daily_diff > 0 else (C_DOWN if daily_diff < 0 else '#8e8e93')
            pn_ico = "▲" if daily_diff > 0 else ("▼" if daily_diff < 0 else "-")
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); border-radius:16px; padding:15px; border:1px solid rgba(255,255,255,0.5); text-align:center;'>
<div style='color:#8e8e93; font-size:0.85rem; font-weight:600;'>일간 손익 (Daily PnL)</div>
<div style='color:{pn_col}; font-size:1.6rem; font-weight:700; margin-top:5px;'>{pn_ico} {abs(daily_diff_pct):.2f}%</div>
<div style='color:{pn_col}; font-size:0.8rem;'>({daily_diff:+.0f} $)</div>
</div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); border-radius:16px; padding:15px; border:1px solid rgba(255,255,255,0.5); text-align:center;'>
<div style='color:#8e8e93; font-size:0.85rem; font-weight:600;'>👑 포트폴리오 MVP</div>
<div style='color:#1d1d1f; font-size:1.6rem; font-weight:700; margin-top:5px;'>{best_ticker}</div>
<div style='color:#007aff; font-size:0.8rem; font-weight:600;'>수익률 {best_ret:+.1f}%</div>
</div>""", unsafe_allow_html=True)
        with m4:
            app_reg = ms['regime']
            st.markdown(f"""
<div style='background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); border-radius:16px; padding:15px; border:1px solid rgba(255,255,255,0.5); text-align:center;'>
<div style='color:#8e8e93; font-size:0.85rem; font-weight:600;'>AI 전략 국면</div>
<div style='color:#1d1d1f; font-size:1.6rem; font-weight:700; margin-top:5px;'>Regime {app_reg}</div>
<div style='color:#8e8e93; font-size:0.8rem; font-weight:600;'>{ms['entry_grade'].split('(')[0].strip()}</div>
</div>""", unsafe_allow_html=True)
            
        st.write("")
        
        # ------------------- 2, 3, 4번 '최소화 + 최소 시각화' 패널 (마크다운 버그 수정본) -------------------
        st.markdown("#### ⚡ 실시간 시스템 분석관 요약")
        
        c_s = "#34c759" if ms['smh'] > ms['smh_ma50'] else "#ff3b30"
        c_r = "#34c759" if ms['smh_3m_ret'] > 0.05 else "#ff3b30"
        c_rsi = "#34c759" if ms['smh_rsi'] > 50 else "#ff3b30"

        if app_reg == 1: badge_bg = "#34c759"; badge_txt = "R1 (강세)"; r_desc = "VIX 안정 & 정배열. 3배 레버리지 비중 확대 최적기."
        elif app_reg == 2: badge_bg = "#ff9500"; badge_txt = "R2 (조정)"; r_desc = "모멘텀 둔화. 2배수로 레버리지 축소 권장."
        elif app_reg == 3: badge_bg = "#ff3b30"; badge_txt = "R3 (약세)"; r_desc = "나스닥 200MA 붕괴. 레버리지 청산 & 금(GLD) 50% 방어."
        else: badge_bg = "#5856d6"; badge_txt = "R4 (위기)"; r_desc = "VIX 40 돌파 패닉. 즉시 주식 전량 매도 및 현금 대피."

        entry_txt = ms['entry_grade']
        if "최적" in entry_txt or "적합" in entry_txt: dot_c = "#34c759"
        elif "가능" in entry_txt or "탐색" in entry_txt: dot_c = "#ff9500"
        else: dot_c = "#ff3b30"
        dir_map = {"ascending": "상향", "descending": "하향", "stable": "유지"}
        direction_kr = dir_map.get(ms['regime_direction'], "알 수 없음")

        # 띄어쓰기 완전 제거하여 마크다운 버그 방지
        st.markdown(f"""<div style='display:flex; gap:15px; margin-bottom:20px; align-items:stretch;'>
<div style='flex: 1.2; background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); padding:16px; border-radius:16px; border:1px solid rgba(255,255,255,0.5);'>
<div style='font-size:0.85rem; color:#8e8e93; font-weight:600; margin-bottom:10px;'>SOXL 진입 판독기</div>
<div style='display:flex; gap:8px;'>
<span style='background:{c_s}; color:#fff; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:12px;'>50MA</span>
<span style='background:{c_r}; color:#fff; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:12px;'>3M 수익</span>
<span style='background:{c_rsi}; color:#fff; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:12px;'>RSI 14</span>
</div>
</div>
<div style='flex: 2; background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); padding:16px; border-radius:16px; border:1px solid rgba(255,255,255,0.5);'>
<div style='font-size:0.85rem; color:#8e8e93; font-weight:600; margin-bottom:8px;'>AI 전략 분석관</div>
<div style='display:flex; align-items:center; gap:10px;'>
<span style='background:{badge_bg}; color:#fff; font-size:0.85rem; font-weight:700; padding:4px 12px; border-radius:8px;'>{badge_txt}</span>
<span style='font-size:0.95rem; color:#1d1d1f;'>{r_desc}</span>
</div>
</div>
<div style='flex: 1.2; background:rgba(255,255,255,0.6); backdrop-filter:blur(10px); padding:16px; border-radius:16px; border:1px solid rgba(255,255,255,0.5);'>
<div style='font-size:0.85rem; color:#8e8e93; font-weight:600; margin-bottom:8px;'>신규 자금 투입 가이드</div>
<div style='display:flex; align-items:center; gap:8px;'>
<div style='width:10px; height:10px; border-radius:50%; background-color:{dot_c};'></div>
<span style='font-size:1.0rem; font-weight:700; color:#1d1d1f;'>{entry_txt.split('(')[0].strip()}</span>
</div>
<div style='font-size:0.8rem; color:#8e8e93; margin-top:4px;'>
방향: <b>{direction_kr}</b> &nbsp;|&nbsp; 체류: <b>{ms['regime_duration']}일</b>
</div>
</div>
</div>""", unsafe_allow_html=True)

        st.divider()

        # ------------------- 데이터 테이블 -------------------
        st.markdown(f"#### 💼 포트폴리오 기입표")
        
        def color_y(val):
            if isinstance(val, (int, float)):
                if val > 0: return f'color: {C_UP}; font-weight: bold;'
                elif val < 0: return f'color: {C_DOWN}; font-weight: bold;'
            return ''

        ed_disp = st.data_editor(
            disp_df.style.map(color_y, subset=["수익률 (%)", "원화 수익률 (%)"]), 
            num_rows="dynamic", use_container_width=True, height=350,
            column_order=["태그", "티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "현재가 ($)", "수익률 (%)", "원화 수익률 (%)"],
            column_config={
                "태그": st.column_config.SelectboxColumn("태그", options=["코어", "위성", "헷지", "현금", "단기픽"], required=True),
                "티커 (Ticker)": st.column_config.TextColumn("종목명"),
                "현재가 ($)": st.column_config.NumberColumn("현재가 💵", disabled=True, format="$ %.2f"),
                "현재 환율": st.column_config.NumberColumn("현재 환율 💱", disabled=True, format="₩ %.1f"),
                "수익률 (%)": st.column_config.NumberColumn("수익률 📈", disabled=True, format="%.2f %%"),
                "원화 수익률 (%)": st.column_config.NumberColumn("원화 수익률 🇰🇷", disabled=True, format="%.2f %%"),
                "매입 환율": st.column_config.NumberColumn("매입 환율 💱", format="₩ %.1f"),
            }
        )
        base_cols = ["티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "태그"]
        if not ed_disp[base_cols].equals(pf_df[base_cols]):
            st.session_state['accounts'][acc_name]["portfolio"] = ed_disp[base_cols].to_dict(orient="records")
            save_accounts_data(st.session_state['accounts']); st.rerun()

        st.write("")

        # ------------------- 파이차트 & 리밸런싱 -------------------
        col_pie, col_act = st.columns([1, 1.3])
        
        with col_pie:
            st.markdown("#### 🍩 자산 배분 비중")
            with st.container(border=True):
                if total_val_now > 0:
                    fig = go.Figure(go.Pie(labels=list(asset_vals.keys()), values=list(asset_vals.values()), hole=0.6, marker=dict(colors=[st.session_state['settings']['chart_colors'].get(k, '#d1d1d6') for k in asset_vals.keys()])))
                    cust_p2 = GLASS_LAYOUT.copy()
                    cust_p2.update(height=300, showlegend=False, margin=dict(t=10, b=10, l=10, r=10), annotations=[dict(text=f"Total<br><b style='font-size:1.2rem; color:{st.session_state['settings']['text_color']};'>100%</b>", x=0.5, y=0.5, showarrow=False)])
                    fig.update_layout(**cust_p2)
                    fig.update_traces(textposition='inside', textinfo='percent+label', textfont_size=13, textfont_color=st.session_state['settings']['text_color'])
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown("<div style='height: 300px; display: flex; align-items: center; justify-content: center; color: #8e8e93;'>자산을 입력해 주세요.</div>", unsafe_allow_html=True)

        with col_act:
            st.markdown("#### ⚖️ AI 시스템 리밸런싱 지침")
            with st.container(border=True):
                status_d = []
                smh_cond = (ms['smh'] > ms['smh_ma50']) and (ms['smh_3m_ret'] > 0.05) and (ms['smh_rsi'] > 50)
                def get_w_local(reg, usx):
                    w = {t: 0.0 for t in REQUIRED_TICKERS}; semi = 'SOXL' if usx else 'USD'
                    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['CASH'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
                    elif reg == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'], w['CASH'] = 0.30, 0.25, 0.20, 0.10, 0.05, 0.10
                    elif reg == 3: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
                    elif reg == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
                    return {k: v for k, v in w.items() if v > 0}
                    
                target_w_dict = get_w_local(ms['regime'], smh_cond)
                all_tkrs = set([t for t in asset_vals.keys()] + list(target_w_dict.keys()))
                for tkr in all_tkrs:
                    tkr = tkr.upper()
                    my_v = asset_vals.get(tkr, 0.0); my_w = (my_v / total_val_now * 100) if total_val_now > 0 else 0.0
                    tw = target_w_dict.get(tkr, 0.0); tv = rebal_base * tw; diff = tv - my_v; cp = live_prices.get(tkr, 0.0)
                    
                    if tkr != "CASH" and cp > 0:
                        shares_to_trade = abs(diff) / cp
                        if shares_to_trade < 1.0: action = "✅ 적정 (유지)"
                        elif diff > 0: action = f"🟢 매수 ({shares_to_trade:.0f}주)"
                        else: action = f"🔴 매도 ({shares_to_trade:.0f}주)"
                    elif tkr == "CASH":
                        if abs(diff) < 50: action = "✅ 적정 (유지)"
                        elif diff > 0: action = f"🟢 추가 (${diff:,.0f})"
                        else: action = f"🔴 인출 (${abs(diff):,.0f})"
                    else: action = "✅ 적정 (유지)"
                    
                    if my_v > 0 or tw > 0: 
                        status_d.append({"종목": tkr, "목표비중": f"{tw*100:.1f}%", "현재비중": f"{my_w:.1f}%", "액션": action})
                        
                if status_d:
                    status_df = pd.DataFrame(status_d).sort_values("목표비중", ascending=False)
                    def color_act(val):
                        val_s = str(val)
                        if '매수' in val_s or '추가' in val_s: return f'color: {C_UP}; font-weight: 600;'
                        elif '매도' in val_s or '인출' in val_s: return f'color: {C_DOWN}; font-weight: 600;'
                        return 'color: #8e8e93;'
                    st.dataframe(status_df.style.map(color_act, subset=['액션']), use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("**[ 📈 내 실제 자산 성장 곡선 ]**")
        
        hist_dict = curr_acc_data.get("seed_history", {})
        if hist_dict:
            with st.container(border=True):
                hist_df = pd.DataFrame.from_dict(hist_dict, orient='index')
                hist_df.index = pd.to_datetime(hist_df.index)
                hist_df = hist_df.sort_index()

                fed_str = curr_acc_data.get("first_entry_date")
                col_date, _ = st.columns([1, 3])
                with col_date:
                    default_date = pd.to_datetime(fed_str).date() if fed_str else (datetime.today() - timedelta(days=90)).date()
                    u_date = st.date_input("최초 투자 시작일", value=default_date, key=f"date_{acc_name}")
                    if str(u_date) != str(fed_str)[:10]: 
                        st.session_state['accounts'][acc_name]["first_entry_date"] = str(u_date)
                        save_accounts_data(st.session_state['accounts'])
                
                try:
                    if fed_str:
                        fed_dt = pd.to_datetime(fed_str)
                        if fed_dt < hist_df.index[0]:
                            hist_df.loc[fed_dt] = {"seed": auto_seed, "equity": auto_seed}
                            hist_df = hist_df.sort_index()

                    hist_df = hist_df.resample('D').ffill()

                    fig_seed = go.Figure()
                    fig_seed.add_trace(go.Scatter(x=hist_df.index, y=hist_df['equity'], name="실제 총 평가액", line=dict(color=C_UP, width=3, shape='hv'), mode='lines', fill='tozeroy', fillcolor='rgba(52,199,89,0.1)'))
                    fig_seed.add_trace(go.Scatter(x=hist_df.index, y=hist_df['seed'], name="투입 시드 원금", line=dict(color='#8e8e93', width=2, dash='dot', shape='hv'), mode='lines'))
                    
                    cust_s = GLASS_LAYOUT.copy()
                    cust_s.update(
                        height=350, 
                        yaxis_title="자산 규모 ($)", 
                        hovermode="x unified",
                        yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', zerolinecolor='rgba(0,0,0,0.1)', autorange=True, rangemode="normal")
                    )
                    fig_seed.update_layout(**cust_s)
                    st.plotly_chart(fig_seed, use_container_width=True)
                except Exception as e: pass

        st.write("")
        col_log1, col_log2 = st.columns([1.5, 1])
        with col_log1:
            st.markdown("**[ 📝 매매 복기 일지 ]**")
            def save_j(): st.session_state['accounts'][acc_name]["journal_text"] = st.session_state[f"j_{acc_name}"]; save_accounts_data(st.session_state['accounts'])
            st.text_area("매매 감정과 이유를 기록하세요.", value=curr_acc_data.get('journal_text', ''), key=f"j_{acc_name}", height=300, on_change=save_j, label_visibility="collapsed")
        with col_log2:
            st.markdown("**[ 🔔 시스템 로그 ]**")
            history = curr_acc_data.get('history', [])
            if history: st.dataframe(pd.DataFrame(history)[::-1], hide_index=True, use_container_width=True, height=300)

    page_func.__name__ = f"pf_{abs(hash(acc_name))}"
    return page_func


# --- 페이지 구성: 계좌 관리 ---
def page_manage_accounts():
    st.title("⚙️ 포트폴리오 관리")
    new_acc = st.text_input("새로운 계좌 이름")
    if st.button("계좌 개설", type="primary") and new_acc:
        if new_acc not in st.session_state['accounts']:
            st.session_state['accounts'][new_acc] = {"portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어" if t != "CASH" else "현금"} for t in REQUIRED_TICKERS], "history": [{"Date": datetime.now().strftime("%Y-%m-%d"), "Log": "계좌 생성됨"}], "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0}
            save_accounts_data(st.session_state['accounts']); st.rerun()
    st.divider()
    for acc in list(st.session_state['accounts'].keys()):
        c1, c2 = st.columns([4, 1])
        c1.write(f"💼 **{acc}**")
        if c2.button("삭제", key=f"del_{acc}", disabled=len(st.session_state['accounts']) <=1):
            del st.session_state['accounts'][acc]; save_accounts_data(st.session_state['accounts']); st.rerun()

# --- 페이지 구성: 전략 명세서 ---
def page_strategy_specification():
    st.title("📜 AMLS 전략 명세서")
    st.markdown("""---""")

    with st.container():
        st.markdown("### 🏷️ 버전: v4.3")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.info("**요약**\n- **자산:** 나스닥 100 (QQQ)\n- **판단:** 200MA + VIX + 정배열\n- **규칙:** 하향 즉시 / 상향 5일 대기")
        with col_s2:
            st.success("**목표**\n- **MDD:** -35% 이하 방어\n- **가치:** 하락장 생존, 상승장 초입 극대화")

    st.markdown("### I. 레짐 판단 기준")
    st.table(pd.DataFrame({"우선순위": ["1", "2", "3", "4"], "조건": ["VIX > 40", "QQQ < 200일선", "정배열 & VIX < 25", "그 외 조건"], "레짐": ["R4 (위기)", "R3 (약세)", "R1 (강세)", "R2 (보통)"]}))

    st.markdown("### II. 레짐별 자산 배분표")
    tabs = st.tabs(["R1 (강세)", "R2 (보통)", "R3 (약세)", "R4 (위기)"])
    with tabs[0]: st.write("**실효 레버리지: 약 2.25배**"); st.table(pd.DataFrame({"종목": ["TQQQ", "SOXL/USD", "QLD", "SSO", "GLD", "현금"], "비중": ["30%", "20%", "20%", "15%", "10%", "5%"]}))
    with tabs[1]: st.write("**실효 레버리지: 약 1.75배**"); st.table(pd.DataFrame({"종목": ["QLD", "SSO", "GLD", "USD", "QQQ", "현금"], "비중": ["30%", "25%", "20%", "10%", "5%", "10%"]}))
    with tabs[2]: st.write("**실효 레버리지: 약 0.15배**"); st.table(pd.DataFrame({"종목": ["QQQ", "GLD", "현금"], "비중": ["15%", "50%", "35%"]}))
    with tabs[3]: st.write("**실효 레버리지: 약 0.10배**"); st.table(pd.DataFrame({"종목": ["GLD", "QQQ", "현금"], "비중": ["50%", "10%", "40%"]}))


# =====================================================================
# [5] 사이드바 설정 및 네비게이션 라우팅
# =====================================================================

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-size:1.1rem; font-weight:700; color:#1d1d1f; margin-bottom:10px;'>⭐ 즐겨찾기</div>", unsafe_allow_html=True)
st.sidebar.markdown("""<div style="display:flex; flex-direction:column; gap:2px;">
<div style="font-size:0.8rem; color:#8e8e93; font-weight:600; margin-top:5px;">유튜브</div>
<a href="https://www.youtube.com/@JB_Insight" target="_blank" class="sidebar-link"><span>📊</span> JB 인사이트</a>
<a href="https://www.youtube.com/@odokgod" target="_blank" class="sidebar-link"><span>📻</span> 오독</a>
<a href="https://www.youtube.com/@TQQQCRAZY" target="_blank" class="sidebar-link"><span>🔥</span> TQQQ 미친놈</a>
<a href="https://www.youtube.com/@developmong" target="_blank" class="sidebar-link"><span>🐒</span> 디벨롭몽</a>

<div style="font-size:0.8rem; color:#8e8e93; font-weight:600; margin-top:15px;">차트 분석</div>
<a href="https://kr.investing.com/" target="_blank" class="sidebar-link"><span>🌍</span> 인베스팅닷컴</a>
<a href="https://kr.tradingview.com/" target="_blank" class="sidebar-link"><span>📉</span> 트레이딩뷰</a>

<div style="font-size:0.8rem; color:#8e8e93; font-weight:600; margin-top:15px;">AI 도우미</div>
<a href="https://claude.ai/" target="_blank" class="sidebar-link"><span>🧠</span> 클로드</a>
<a href="https://gemini.google.com/" target="_blank" class="sidebar-link"><span>✨</span> 제미나이</a>
</div>""", unsafe_allow_html=True)
st.sidebar.markdown("---")

with st.sidebar.expander("🎨 테마 색상 설정"):
    st.markdown("**기본 텍스트**")
    new_text_color = st.color_picker("색상", st.session_state['settings']['text_color'])
    if new_text_color != st.session_state['settings']['text_color']:
        st.session_state['settings']['text_color'] = new_text_color
        save_settings(st.session_state['settings']); st.rerun()
        
    st.markdown("---")
    st.markdown("📈 **파이 차트 조각**")
    for tkr in st.session_state['settings']['chart_colors']:
        new_c = st.color_picker(f"{tkr}", st.session_state['settings']['chart_colors'][tkr])
        if new_c != st.session_state['settings']['chart_colors'][tkr]:
            st.session_state['settings']['chart_colors'][tkr] = new_c
            save_settings(st.session_state['settings']); st.rerun()

with st.sidebar.expander("💾 백업 및 복구"):
    st.download_button("📥 백업 다운로드", data=json.dumps(st.session_state['accounts']), file_name="amls_backup.json")
    up_f = st.file_uploader("📤 복구 파일 업로드", type=['json'])
    if up_f and st.button("⚠️ 복구 실행"):
        st.session_state['accounts'] = json.load(up_f)
        save_accounts_data(st.session_state['accounts']); st.rerun()

pages = {
    "관제탑": [st.Page(page_market_dashboard, title="마켓 터미널", icon="🌐"), st.Page(page_amls_backtest, title="백테스트 엔진", icon="🦅")],
    "포트폴리오": [],
    "설정": [st.Page(page_strategy_specification, title="전략 명세서", icon="📜"), st.Page(page_manage_accounts, title="계좌 관리", icon="⚙️")]
}

for name in st.session_state['accounts'].keys():
    pages["포트폴리오"].append(st.Page(make_portfolio_page(name), title=name, icon="💼"))

pg = st.navigation(pages)
pg.run()
