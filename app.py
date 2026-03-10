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
# [0] 시스템 기본 설정 및 데이터 관리 & 부드러운 UI 렌더링
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 관제탑", layout="wide", initial_sidebar_state="expanded")

def apply_cafe_style_professional():
    st.markdown("""
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

    /* 배경은 포근한 크림 아이보리, 텍스트는 부드러운 코코아 브라운 */
    html, body, [class*="css"] {
        font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif !important;
        background-color: #FFFBF0 !important; 
        color: #5D4A44 !important; 
        letter-spacing: -0.01em;
    }

    /* 글씨 잘림 방지 */
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div,
    p, h1, h2, h3, h4, h5, h6, span, label, .stMarkdown {
        white-space: normal !important;
        word-break: keep-all !important;
        overflow-wrap: break-word !important;
    }

    /* 컨테이너 및 카드: 동글동글한 모서리와 푹신한 그림자 */
    div[data-testid="stVerticalBlockBorderWrapper"] > div, .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3 {
        background-color: #FFFFFF !important;
        border: 2px solid #FFF0E5 !important;
        border-radius: 24px !important;
        box-shadow: 0 8px 20px rgba(210, 190, 175, 0.15) !important;
        padding: 1.5rem !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 28px rgba(210, 190, 175, 0.25) !important;
    }

    /* 버튼: 말랑말랑한 젤리 느낌의 파스텔 톤 */
    .stButton>button {
        background-color: #FFB7B2 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        box-shadow: 0 4px 0 #F29F9A !important;
    }
    .stButton>button:hover {
        background-color: #FFC4C0 !important;
        transform: translateY(2px) !important;
        box-shadow: 0 2px 0 #F29F9A !important;
    }
    .stButton>button:active {
        transform: translateY(4px) !important;
        box-shadow: 0 0 0 #F29F9A !important;
    }

    /* 텍스트 입력창 */
    input, textarea, select, div[data-baseweb="select"] > div {
        background-color: #FAFAFA !important;
        color: #5D4A44 !important;
        border: 2px solid #EAE3D9 !important;
        border-radius: 12px !important;
    }
    input:focus, textarea:focus {
        border-color: #FFB7B2 !important;
        box-shadow: 0 0 0 3px rgba(255, 183, 178, 0.2) !important;
    }

    /* 데이터프레임 둥글게 */
    [data-testid="stDataFrame"] {
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 2px solid #FFF0E5 !important;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #FFF6EC !important;
        border-right: 2px dashed #EAE3D9 !important;
    }

    /* 탭 스타일 */
    button[data-baseweb="tab"] {
        color: #A89B96 !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        background-color: transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FF9B94 !important;
        border-bottom-color: #FF9B94 !important;
        border-bottom-width: 3px !important;
    }
    
    /* 이모지 및 메트릭 강조 */
    div[data-testid="stMetricValue"] {
        font-weight: 800 !important;
        font-size: 2rem !important;
        color: #5D4A44 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #A89B96 !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_cafe_style_professional()

# 파스텔톤 차트 레이아웃
CUTE_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'Pretendard', sans-serif", color="#8B7D77", size=13),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=True, gridcolor='#F5F0EA', zerolinecolor='#EAE3D9'),
    yaxis=dict(showgrid=True, gridcolor='#F5F0EA', zerolinecolor='#EAE3D9')
)

# 부드러운 컬러 팔레트
C_UP = "#FFB7B2"     # 상승/매수 톤
C_DOWN = "#A1C9F1"   # 하락/매도 톤
C_WARN = "#FFDAC1"   
C_SAFE = "#B5EAD7"   

COLOR_PALETTE = {
    'TQQQ': '#FF9AA2',      
    'SOXL/USD': '#C7CEEA',  
    'USD': '#E2F0CB',       
    'QLD': '#FFDAC1',       
    'SSO': '#FFB7B2',       
    'QQQ': '#A1C9F1',       
    'GLD': '#FCEBB6',       
    'CASH': '#B5EAD7'       
}

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
            "기본 계좌 (AMLS)": {
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "목표가 ($)": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0
            }
        }
    st.session_state['accounts'] = loaded

# [마이그레이션] 새로운 필드 유지
needs_save = False
for acc_name, acc_data in st.session_state['accounts'].items():
    existing_tickers = [item["티커 (Ticker)"] for item in acc_data["portfolio"]]
    missing_tickers = [t for t in REQUIRED_TICKERS if t not in existing_tickers]
    
    port_dict = {item["티커 (Ticker)"]: item for item in acc_data["portfolio"]}
    new_port = []
    
    for req_t in REQUIRED_TICKERS:
        if req_t in port_dict: 
            item = port_dict[req_t]
            if "매입 환율" not in item: item["매입 환율"] = 0.0; needs_save = True
            if "목표가 ($)" not in item: item["목표가 ($)"] = 0.0; needs_save = True
            if "태그" not in item: item["태그"] = "코어" if req_t != "CASH" else "현금"; needs_save = True
            new_port.append(item)
        else: 
            new_port.append({"티커 (Ticker)": req_t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "목표가 ($)": 0.0, "태그": "코어" if req_t != "CASH" else "현금"})
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
    components.html("""
    <div class="tradingview-widget-container" style="border-radius: 16px; overflow: hidden; border: 2px solid #FFF0E5;">
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
    </div>
    """, height=70)

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
                custom_l = CUTE_LAYOUT.copy()
                custom_l.update(height=240, showlegend=False)
                fig.update_layout(**custom_l)
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.markdown("##### 🗺️ S&P 500 섹터 맵")
            components.html("""
            <div style="border-radius: 16px; overflow: hidden; height: 100%;">
            <iframe src="https://www.tradingview.com/embed-widget-stock-heatmap/?locale=kr#%7B%22dataSource%22%3A%22SPX500%22%2C%22blockSize%22%3A%22market_cap_basic%22%2C%22blockColor%22%3A%22change%22%2C%22grouping%22%3A%22sector%22%2C%22colorTheme%22%3A%22light%22%7D" width="100%" height="450" frameborder="0"></iframe>
            </div>
            """, height=460)


# =====================================================================
# [3] 페이지 구성: AMLS 백테스트
# =====================================================================
def page_amls_backtest():
    st.title("🦅 AMLS 백테스트 엔진 (Tearsheet)")
    st.markdown("다양한 시장 조건과 벤치마크를 비교 분석하는 전문가용 시뮬레이터입니다.")

    st.sidebar.header("⚙️ 백테스트 파라미터")
    BACKTEST_START = st.sidebar.date_input("시작일", datetime(2018, 1, 1))
    BACKTEST_END = st.sidebar.date_input("종료일", datetime.today())
    INITIAL_CAPITAL = st.sidebar.number_input("초기 자본금 ($)", value=10000, step=1000)
    MONTHLY_CONTRIBUTION = st.sidebar.number_input("매월 추가 적립금 ($)", value=2000, step=500)
    REBAL_FREQ = st.sidebar.selectbox("🔄 정기 리밸런싱 주기", ["월 1회", "주 1회 (5거래일)", "2주 1회 (10거래일)", "3주 1회 (15거래일)"], index=0)

    with st.spinner('방대한 시장 데이터를 연산 중입니다. 잠시만 기다려주세요...'):
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

    tab1, tab2, tab3 = st.tabs(["📊 성과 비교 요약", "📈 자산 추이 및 낙폭", "📝 시스템 매매 로그"])

    with tab1:
        st.markdown("#### 🏆 핵심 퍼포먼스 비교표")
        st.info(f"💡 **투입 원금 총합:** ${df['Invested'].iloc[-1]:,.0f} (초기 {INITIAL_CAPITAL} + 매월 {MONTHLY_CONTRIBUTION} 적립)")
        st.dataframe(metrics_df, use_container_width=True)

        st.markdown("#### 🥧 AMLS v4.3 국면별 자산 배분 비중")
        c1, c2, c3, c4 = st.columns(4)
        def get_w(reg):
            if reg == 1: return {'TQQQ':30, 'SOXL/USD':20, 'QLD':20, 'SSO':15, 'GLD':10, 'CASH':5}
            elif reg == 2: return {'QLD':30, 'SSO':25, 'GLD':20, 'USD':10, 'QQQ':5, 'CASH':10}
            elif reg == 3: return {'GLD':50, 'CASH':35, 'QQQ':15}
            elif reg == 4: return {'GLD':50, 'CASH':40, 'QQQ':10}
        
        for i, col in enumerate([c1, c2, c3, c4]):
            r = i+1; w = {k:v for k,v in get_w(r).items() if v>0}
            fig_p = go.Figure(go.Pie(labels=list(w.keys()), values=list(w.values()), hole=0.5, marker=dict(colors=[COLOR_PALETTE.get(k.split('/')[0], '#EAE3D9') for k in w.keys()])))
            cust_p = CUTE_LAYOUT.copy(); cust_p.update(title=f"Regime {r}", title_x=0.5, height=250, margin=dict(t=40,b=10,l=10,r=10), showlegend=False)
            fig_p.update_layout(**cust_p)
            fig_p.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color='#5D4A44', size=12))
            col.plotly_chart(fig_p, use_container_width=True)

    with tab2:
        st.markdown("#### 📈 자산 성장 곡선")
        use_log = st.checkbox("Y축 로그 스케일 적용", value=False)
        fig_eq = go.Figure()
        
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['AMLS v4.3_Value'], name='AMLS v4.3', line=dict(color=C_UP, width=4)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['QQQ_Value'], name='QQQ (1배)', line=dict(color=C_DOWN, width=2)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['TQQQ_Value'], name='TQQQ (3배)', line=dict(color=C_WARN, width=2)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['Invested'], name='원금 (Invested)', line=dict(color='#A89B96', width=2, dash='dot')))
        
        if use_log: fig_eq.update_yaxes(type="log")
        cust_eq = CUTE_LAYOUT.copy(); cust_eq.update(height=450, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_eq.update_layout(**cust_eq)
        st.plotly_chart(fig_eq, use_container_width=True)

    with tab3:
        st.markdown("#### 📝 시스템 매매 로그")
        st.caption(f"적용된 리밸런싱 주기: **{REBAL_FREQ}**")
        log_df = pd.DataFrame(logs)[::-1]
        if not log_df.empty:
            log_df['평가액'] = log_df['평가액'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(log_df, hide_index=True, use_container_width=True)


# =====================================================================
# [4] 페이지 구성: 내 포트폴리오 관리
# =====================================================================
def make_portfolio_page(acc_name):
    def page_func():
        st.title(f"🏦 {acc_name} 포트폴리오 관제탑")
        st.markdown("포트폴리오 자산을 기입하고 실시간 AI 리밸런싱 신호를 확인하세요.")
        
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

            if regime_direction == "ascending":
                if regime_duration <= 10: entry_grade = "최적 진입 구간"
                elif regime_duration <= 30: entry_grade = "진입 적합"
                elif regime_duration <= 60: entry_grade = "진입 가능 (장기 체류)"
                else: entry_grade = "진입 주의 — 전환 리스크"
            elif regime_direction == "descending":
                if regime_duration <= 5: entry_grade = "진입 보류 — 하락 전환 직후"
                elif regime_duration <= 20: entry_grade = "진입 주의 — 추가 하락 가능"
                else: entry_grade = "바닥 탐색 — 상향 전환 대기"
            else:
                if regime_duration <= 30: entry_grade = "진입 적합"
                elif regime_duration <= 60: entry_grade = "진입 가능 (장기 체류)"
                else: entry_grade = "진입 주의 — 전환 리스크"

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

        with st.spinner("시장 데이터 동기화 및 AI 분석 중..."): 
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
            if 4 <= et_hour < 9.5: price_label = "프리마켓"
            elif 9.5 <= et_hour < 16: price_label = "장중 실시간"
            elif 16 <= et_hour < 20: price_label = "애프터마켓"
            else: price_label = "실시간"
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

        def target_prog(row):
            if row["목표가 ($)"] <= 0 or row["티커 (Ticker)"] == "CASH": return 0.0
            p = (row["현재가 ($)"] / row["목표가 ($)"]) * 100
            return min(p, 100.0) 
        disp_df["달성률 (%)"] = disp_df.apply(target_prog, axis=1)

        total_val_now = 0.0; total_val_yest = 0.0; auto_seed = 0.0
        best_ticker = "데이터 없음"; best_ret = -999.0
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

        # ------------------- 상단 요약 대시보드 -------------------
        st.markdown(f"#### 📊 실시간 시장 인텔리전스 (기준: {price_label})")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div style='background:#FFFFFF; border-radius:20px; padding:15px; border:2px solid #FFF0E5; text-align:center;'>
                <div style='color:#A89B96; font-size:0.9rem; font-weight:700;'>💰 총 평가액 (Total Equity)</div>
                <div style='color:#5D4A44; font-size:1.8rem; font-weight:800; margin-top:5px;'>${total_val_now:,.0f}</div>
            </div>""", unsafe_allow_html=True)
        with m2:
            pn_col = C_UP if daily_diff > 0 else (C_DOWN if daily_diff < 0 else '#A89B96')
            pn_ico = "📈" if daily_diff > 0 else ("📉" if daily_diff < 0 else "➖")
            st.markdown(f"""
            <div style='background:#FFFFFF; border-radius:20px; padding:15px; border:2px solid #FFF0E5; text-align:center;'>
                <div style='color:#A89B96; font-size:0.9rem; font-weight:700;'>{pn_ico} 일간 손익 (Daily PnL)</div>
                <div style='color:{pn_col}; font-size:1.8rem; font-weight:800; margin-top:5px;'>{daily_diff_pct:+.2f}%</div>
                <div style='color:{pn_col}; font-size:0.85rem;'>({daily_diff:+.0f} USD)</div>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div style='background:#FFFFFF; border-radius:20px; padding:15px; border:2px solid #FFF0E5; text-align:center;'>
                <div style='color:#A89B96; font-size:0.9rem; font-weight:700;'>👑 포트폴리오 MVP</div>
                <div style='color:#FFB7B2; font-size:1.8rem; font-weight:800; margin-top:5px;'>{best_ticker}</div>
                <div style='color:#A89B96; font-size:0.85rem;'>수익률: {best_ret:+.1f}%</div>
            </div>""", unsafe_allow_html=True)
        with m4:
            app_reg = ms['regime']
            ico_r = "🔥" if app_reg==1 else "🛡️" if app_reg==2 else "⚠️" if app_reg==3 else "🚨"
            st.markdown(f"""
            <div style='background:#FFFFFF; border-radius:20px; padding:15px; border:2px solid #FFF0E5; text-align:center;'>
                <div style='color:#A89B96; font-size:0.9rem; font-weight:700;'>{ico_r} AI 전략 분석관</div>
                <div style='color:#5D4A44; font-size:1.8rem; font-weight:800; margin-top:5px;'>Regime {app_reg}</div>
                <div style='color:#8B7D77; font-size:0.85rem;'>{ms['entry_grade']}</div>
            </div>""", unsafe_allow_html=True)
            
        st.write("")
        st.divider()

        # ------------------- 데이터 테이블 & 목표가 게이지 -------------------
        st.markdown(f"#### 💼 포트폴리오 기입표 (더블클릭하여 수정하세요)")
        
        def color_y(val):
            if isinstance(val, (int, float)):
                if val > 0: return f'color: {C_UP}; font-weight: bold;'
                elif val < 0: return f'color: {C_DOWN}; font-weight: bold;'
            return ''

        ed_disp = st.data_editor(
            disp_df.style.map(color_y, subset=["수익률 (%)", "원화 수익률 (%)"]), 
            num_rows="dynamic", use_container_width=True, height=380,
            column_order=["태그", "티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "현재가 ($)", "수익률 (%)", "원화 수익률 (%)", "목표가 ($)", "달성률 (%)"],
            column_config={
                "태그": st.column_config.SelectboxColumn("태그 🏷️", help="포지션의 성격을 선택하세요.", options=["코어", "위성", "헷지", "현금", "단기픽"], required=True),
                "티커 (Ticker)": st.column_config.TextColumn("종목명 🏷️"),
                "현재가 ($)": st.column_config.NumberColumn("현재가 💵", disabled=True, format="$ %.2f"),
                "현재 환율": st.column_config.NumberColumn("현재 환율 💱", disabled=True, format="₩ %.1f"),
                "수익률 (%)": st.column_config.NumberColumn("수익률 📈", disabled=True, format="%.2f %%"),
                "원화 수익률 (%)": st.column_config.NumberColumn("원화 수익률 🇰🇷", disabled=True, format="%.2f %%"),
                "목표가 ($)": st.column_config.NumberColumn("목표가 🎯", format="$ %.2f", help="매도 목표가를 입력하세요."),
                "달성률 (%)": st.column_config.ProgressColumn("목표 달성률 (%)", help="현재가가 목표가에 얼마나 도달했는지 나타냅니다.", min_value=0, max_value=100, format="%f%%"),
                "매입 환율": st.column_config.NumberColumn("매입 환율 💱", format="₩ %.1f"),
            }
        )
        base_cols = ["티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율", "목표가 ($)", "태그"]
        if not ed_disp[base_cols].equals(pf_df[base_cols]):
            st.session_state['accounts'][acc_name]["portfolio"] = ed_disp[base_cols].to_dict(orient="records")
            save_accounts_data(st.session_state['accounts']); st.rerun()

        st.write("")

        # ------------------- 파이차트 & 리밸런싱 -------------------
        col_pie, col_act = st.columns([1, 1.3])
        
        with col_pie:
            st.markdown("#### 🍩 자산 배분 비중 (Allocation)")
            with st.container(border=True):
                if total_val_now > 0:
                    fig = go.Figure(go.Pie(labels=list(asset_vals.keys()), values=list(asset_vals.values()), hole=0.6, marker=dict(colors=[COLOR_PALETTE.get(k, '#EAE3D9') for k in asset_vals.keys()])))
                    cust_p2 = CUTE_LAYOUT.copy()
                    cust_p2.update(height=300, showlegend=False, margin=dict(t=10, b=10, l=10, r=10), annotations=[dict(text=f"Total<br><b style='font-size:1.2rem; color:#5D4A44;'>100%</b>", x=0.5, y=0.5, showarrow=False)])
                    fig.update_layout(**cust_p2)
                    fig.update_traces(textposition='inside', textinfo='percent+label', textfont_size=13, textfont_color='#5D4A44')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown("<div style='height: 300px; display: flex; align-items: center; justify-content: center; color: #A89B96;'>자산 데이터를 입력하면 차트가 표시됩니다.</div>", unsafe_allow_html=True)

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
                        status_d.append({"종목": tkr, "목표비중": f"{tw*100:.1f}%", "현재비중": f"{my_w:.1f}%", "액션 (Action)": action})
                        
                if status_d:
                    status_df = pd.DataFrame(status_d).sort_values("목표비중", ascending=False)
                    def color_act(val):
                        val_s = str(val)
                        if '매수' in val_s or '추가' in val_s: return f'color: {C_UP}; font-weight: 700;'
                        elif '매도' in val_s or '인출' in val_s: return f'color: {C_DOWN}; font-weight: 700;'
                        return 'color: #A89B96;'
                    st.dataframe(status_df.style.map(color_act, subset=['액션 (Action)']), use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("**[ 📈 운용 시드(Target Seed) 성장 곡선 ]**")
        
        if auto_seed > 0:
            with st.container(border=True):
                fed_str = curr_acc_data.get("first_entry_date")
                default_date = pd.to_datetime(fed_str).date() if fed_str else (datetime.today() - timedelta(days=90)).date()
                col_date, _ = st.columns([1, 3])
                with col_date:
                    u_date = st.date_input("투자 시작일", value=default_date, key=f"date_{acc_name}")
                    if str(u_date) != str(fed_str)[:10]: 
                        st.session_state['accounts'][acc_name]["first_entry_date"] = str(u_date)
                        save_accounts_data(st.session_state['accounts'])
                
                try:
                    chart_start_ts = pd.Timestamp(u_date)
                    bench_data = yf.download("QQQ", start=(chart_start_ts - timedelta(days=5)).strftime('%Y-%m-%d'), progress=False)['Close'].ffill()
                    if not bench_data.empty:
                        bench_series = bench_data.iloc[:, 0] if isinstance(bench_data, pd.DataFrame) else bench_data
                        bench_series = bench_series[bench_series.index >= chart_start_ts]
                        seed_curve = (bench_series / bench_series.iloc[0]) * auto_seed
                        
                        fig_seed = go.Figure()
                        fig_seed.add_trace(go.Scatter(x=seed_curve.index, y=seed_curve.values, name="운용 시드 궤적", line=dict(color=C_SAFE, width=3), fill='tozeroy', fillcolor='rgba(181, 234, 215, 0.2)'))
                        fig_seed.add_trace(go.Scatter(x=seed_curve.index, y=[auto_seed]*len(seed_curve), name="현재 시드 원금", line=dict(color=C_UP, width=2, dash='dot')))
                        cust_s = CUTE_LAYOUT.copy()
                        cust_s.update(height=300, yaxis_title="자산 규모 ($)", hovermode="x unified")
                        fig_seed.update_layout(**cust_s)
                        st.plotly_chart(fig_seed, use_container_width=True)
                except Exception as e: pass

        st.write("")
        col_log1, col_log2 = st.columns([1.5, 1])
        with col_log1:
            st.markdown("**[ 📝 매매 복기 일지 ]**")
            def save_j(): st.session_state['accounts'][acc_name]["journal_text"] = st.session_state[f"j_{acc_name}"]; save_accounts_data(st.session_state['accounts'])
            st.text_area("시장의 주요 이슈와 매매 감정을 자유롭게 기록하세요.", value=curr_acc_data.get('journal_text', ''), key=f"j_{acc_name}", height=150, on_change=save_j, label_visibility="collapsed")
        with col_log2:
            st.markdown("**[ 🔔 시스템 로그 ]**")
            history = curr_acc_data.get('history', [])
            if history: st.dataframe(pd.DataFrame(history)[::-1], hide_index=True, use_container_width=True, height=150)

    page_func.__name__ = f"pf_{abs(hash(acc_name))}"
    return page_func


# --- 페이지 구성: 계좌 관리 ---
def page_manage_accounts():
    st.title("⚙️ 포트폴리오 계좌 관리")
    new_acc = st.text_input("신규 계좌 이름")
    if st.button("🚀 계좌 개설", type="primary") and new_acc:
        if new_acc not in st.session_state['accounts']:
            st.session_state['accounts'][new_acc] = {"portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "목표가 ($)": 0.0, "태그": "코어" if t != "CASH" else "현금"} for t in REQUIRED_TICKERS], "history": [{"Date": datetime.now().strftime("%Y-%m-%d"), "Log": "✨ 계좌 개설"}], "target_seed": 10000.0}
            save_accounts_data(st.session_state['accounts']); st.rerun()
    st.divider()
    for acc in list(st.session_state['accounts'].keys()):
        c1, c2 = st.columns([4, 1])
        c1.write(f"📁 **{acc}**")
        if c2.button("삭제", key=f"del_{acc}", disabled=len(st.session_state['accounts']) <=1):
            del st.session_state['accounts'][acc]; save_accounts_data(st.session_state['accounts']); st.rerun()

# --- 페이지 구성: 전략 명세서 ---
def page_strategy_specification():
    st.title("📜 AMLS 전략 명세서")
    st.markdown("""---""")

    with st.container():
        st.markdown("### 🏷️ 버전: v4.3 (단계적 진입 로직 적용)")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.info("**문서 요약**\n- **기준 자산:** 나스닥 100\n- **레짐 판단:** 이동평균선과 공포지수(VIX)\n- **전환 규칙:** 하향 즉시 대응 / 상향 5일 확인 대기")
        with col_s2:
            st.success("**목표 지표**\n- **목표 MDD:** -35% 이하로 방어\n- **핵심 가치:** 하락장에서는 보수적, 상승장 초입에는 과감하게 포지셔닝")

    st.markdown("### I. 레짐 판단 기준")
    st.table(pd.DataFrame({"우선순위": ["1", "2", "3", "4"], "조건": ["VIX > 40", "QQQ < 200일선", "정배열 & VIX < 25", "그 외 조건"], "목표 레짐": ["R4 (위기)", "R3 (약세)", "R1 (강세)", "R2 (보통)"]}))

    st.markdown("### II. 레짐별 자산 배분표")
    tabs = st.tabs(["R1 (강세)", "R2 (보통)", "R3 (약세)", "R4 (위기)"])
    with tabs[0]: st.write("**실효 레버리지: 약 2.25배**"); st.table(pd.DataFrame({"종목": ["TQQQ", "SOXL/USD", "QLD", "SSO", "GLD", "현금"], "비중": ["30%", "20%", "20%", "15%", "10%", "5%"]}))
    with tabs[1]: st.write("**실효 레버리지: 약 1.75배**"); st.table(pd.DataFrame({"종목": ["QLD", "SSO", "GLD", "USD", "QQQ", "현금"], "비중": ["30%", "25%", "20%", "10%", "5%", "10%"]}))
    with tabs[2]: st.write("**실효 레버리지: 약 0.15배**"); st.table(pd.DataFrame({"종목": ["QQQ", "GLD", "현금"], "비중": ["15%", "50%", "35%"]}))
    with tabs[3]: st.write("**실효 레버리지: 약 0.10배**"); st.table(pd.DataFrame({"종목": ["GLD", "QQQ", "현금"], "비중": ["50%", "10%", "40%"]}))


# =====================================================================
# [5] 네비게이션 라우팅
# =====================================================================
pages = {
    "메인 뷰": [st.Page(page_market_dashboard, title="마켓 터미널", icon="🌐"), st.Page(page_amls_backtest, title="백테스트 시뮬레이터", icon="🦅")],
    "나의 포트폴리오": [],
    "설정 및 문서": [st.Page(page_strategy_specification, title="전략 명세서", icon="📜")]
}

for name in st.session_state['accounts'].keys():
    pages["나의 포트폴리오"].append(st.Page(make_portfolio_page(name), title=name, icon="💼"))

pages["설정 및 문서"].append(st.Page(page_manage_accounts, title="계좌 관리", icon="⚙️"))

with st.sidebar.expander("💾 백업 및 복구"):
    st.download_button("📥 백업 파일 다운로드", data=json.dumps(st.session_state['accounts']), file_name="amls_backup.json")
    up_f = st.file_uploader("📤 백업 파일 불러오기", type=['json'])
    if up_f and st.button("⚠️ 현재 데이터에 덮어쓰기"):
        st.session_state['accounts'] = json.load(up_f)
        save_accounts_data(st.session_state['accounts']); st.rerun()

pg = st.navigation(pages)
pg.run()
