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
# [0] 시스템 기본 설정 및 데이터 관리 & 1920s 빈티지 스타일 주입
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 관제탑", layout="wide", initial_sidebar_state="expanded")

def apply_vintage_style():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');

    /* 전체 배경 및 폰트 설정 (오래된 종이 질감과 잉크 색상) */
    html, body, [class*="css"] {
        font-family: 'Special Elite', 'Courier New', Courier, monospace !important;
        background-color: #e4dccc !important; 
        color: #2c2a25 !important;
    }

    /* 컨테이너 및 테두리 설정 (두꺼운 타자기 라인) */
    .st-emotion-cache-1104k38, .st-emotion-cache-16txtl3, div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #dfd7c5 !important;
        border: 2px solid #2c2a25 !important;
        border-radius: 0px !important;
        box-shadow: 4px 4px 0px #2c2a25 !important;
    }

    /* 버튼 스타일 (기계식 타자기 키 느낌) */
    .stButton>button {
        background-color: #d1c7b3 !important;
        color: #2c2a25 !important;
        border: 2px solid #2c2a25 !important;
        border-radius: 0px !important;
        box-shadow: 2px 2px 0px #2c2a25 !important;
        font-weight: bold;
        text-transform: uppercase;
        transition: all 0.1s ease-in-out;
    }
    .stButton>button:active {
        box-shadow: 0px 0px 0px #2c2a25 !important;
        transform: translateY(2px) translateX(2px);
    }

    /* 텍스트 입력창 및 선택창 */
    input, textarea, select, div[data-baseweb="select"] > div {
        background-color: #f0e9d8 !important;
        color: #2c2a25 !important;
        border: 1px dashed #2c2a25 !important;
        border-radius: 0px !important;
        font-family: 'Special Elite', 'Courier New', Courier, monospace !important;
    }

    /* 데이터프레임 (타자기 문서 느낌) */
    [data-testid="stDataFrame"] {
        border: 1px solid #2c2a25 !important;
        background-color: #f0e9d8 !important;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #d1c7b3 !important;
        border-right: 3px double #2c2a25 !important;
    }

    /* 제목선 (이중선 강조) */
    h1, h2, h3 {
        border-bottom: 3px double #2c2a25;
        padding-bottom: 8px;
        text-transform: uppercase;
    }
    
    /* 메트릭 값 */
    div[data-testid="stMetricValue"] {
        font-weight: bold !important;
        color: #1a1916 !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_vintage_style()

# Plotly 차트용 공통 빈티지 레이아웃 설정
VINTAGE_LAYOUT = dict(
    template="simple_white",
    paper_bgcolor="#e4dccc",
    plot_bgcolor="#dfd7c5",
    font=dict(family="'Special Elite', 'Courier New', Courier, monospace", color="#2c2a25"),
    margin=dict(l=0, r=0, t=30, b=0)
)
# 빈티지 색상 팔레트
C_UP = "#000080" # Navy
C_DOWN = "#8b0000" # Dark Red
C_WARN = "#b8860b" # Dark Goldenrod
C_SAFE = "#006400" # Dark Green

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
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0
            }
        }
    st.session_state['accounts'] = loaded

# 데이터 마이그레이션 및 자동 저장
needs_save = False
for acc_name, acc_data in st.session_state['accounts'].items():
    existing_tickers = [item["티커 (Ticker)"] for item in acc_data["portfolio"]]
    missing_tickers = [t for t in REQUIRED_TICKERS if t not in existing_tickers]
    if missing_tickers:
        port_dict = {item["티커 (Ticker)"]: item for item in acc_data["portfolio"]}
        new_port = []
        for req_t in REQUIRED_TICKERS:
            if req_t in port_dict: new_port.append(port_dict[req_t])
            else: new_port.append({"티커 (Ticker)": req_t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0})
        acc_data["portfolio"] = new_port
        needs_save = True
    for item in acc_data["portfolio"]:
        if "매입 환율" not in item:
            item["매입 환율"] = 0.0
            needs_save = True
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
    
    actual_regime_v4 = []
    actual_regime_v4_3 = []
    current_v4 = 3
    current_v4_3 = 3
    pend_v4 = None
    pend_v4_3 = None
    cnt_v4 = 0
    cnt_v4_3 = 0

    for i in range(len(df)):
        tr = df['Target_Regime'].iloc[i]
        
        if tr > current_v4: 
            current_v4 = tr; pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
        elif tr < current_v4:
            if tr == pend_v4:
                cnt_v4 += 1
                if cnt_v4 >= 5: current_v4 = tr; pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
                else: actual_regime_v4.append(current_v4)
            else: pend_v4 = tr; cnt_v4 = 1; actual_regime_v4.append(current_v4)
        else: pend_v4 = None; cnt_v4 = 0; actual_regime_v4.append(current_v4)
        
        if tr > current_v4_3: 
            current_v4_3 = tr; pend_v4_3 = None; cnt_v4_3 = 0; actual_regime_v4_3.append(current_v4_3)
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
        w = {t: 0.0 for t in data.columns}
        semi = 'SOXL' if use_soxl else 'USD'
        if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'] = 0.30, 0.20, 0.20, 0.15, 0.10
        elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['QQQ'], w['USD'] = 0.25, 0.20, 0.20, 0.15, 0.10
        elif regime == 3: w['GLD'], w['QQQ'], w['SPY'] = 0.35, 0.20, 0.10
        elif regime == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
        return w

    def get_v4_3_weights(regime, use_soxl):
        w = {t: 0.0 for t in data.columns}
        semi = 'SOXL' if use_soxl else 'USD'
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
        days_since_v4 += 1
        days_since_v4_3 += 1
        
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
        
        if rebal_v4:
            weights_v4 = get_v4_weights(sig_r_v4, use_soxl)
            days_since_v4 = 0

        sig_r_v4_3 = df['Signal_Regime_v4_3'].iloc[i]
        rebal_v4_3 = False
        if sig_r_v4_3 != df['Signal_Regime_v4_3'].iloc[i-1] or i == 1: rebal_v4_3 = True
        elif rebal_freq == "월 1회" and today.month != yesterday.month: rebal_v4_3 = True
        elif "주 1회" in rebal_freq and days_since_v4_3 >= 5: rebal_v4_3 = True
        elif "2주 1회" in rebal_freq and days_since_v4_3 >= 10: rebal_v4_3 = True
        elif "3주 1회" in rebal_freq and days_since_v4_3 >= 15: rebal_v4_3 = True
        
        if rebal_v4_3:
            weights_v4_3 = get_v4_3_weights(sig_r_v4_3, use_soxl)
            log_type = "TYPE: REGIME SHIFT" if sig_r_v4_3 != df['Signal_Regime_v4_3'].iloc[i-1] else f"TYPE: SCHEDULED ({rebal_freq.split(' ')[0]})"
            semi_target = "SOXL (3x)" if use_soxl and sig_r_v4_3 == 1 else ("USD (2x)" if sig_r_v4_3 in [1, 2] else "-")
            logs.append({"DATE": today.strftime('%Y-%m-%d'), "TYPE": log_type, "REGIME": f"R{int(sig_r_v4_3)}", "SEMI_SLOT": semi_target, "EQUITY": ports['AMLS v4.3']})
            days_since_v4_3 = 0

    for s in ports: df[f'{s}_Value'] = hists[s]
    
    inv_arr = [init_cap]
    curr_inv = init_cap
    for i in range(1, len(df)):
        if df.index[i].month != df.index[i-1].month: curr_inv += monthly_cont
        inv_arr.append(curr_inv)
    df['Invested'] = inv_arr
    
    return df, logs, data.columns


# =====================================================================
# [2] 페이지 구성: 글로벌 마켓 대시보드
# =====================================================================
def page_market_dashboard():
    st.title("🌐 TELEGRAPH: GLOBAL MACRO")
    components.html("""
    <div class="tradingview-widget-container">
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
      "showSymbolLogo": false, "colorTheme": "light", "locale": "kr"
    }
      </script>
    </div>
    """, height=70)

    col_left, col_right = st.columns([1, 1.8])
    with col_left:
        with st.container(border=True):
            st.markdown("##### 📈 TELEGRAM: INDEX STATUS")
            tickers = ['^GSPC', '^IXIC', '^VIX', 'USDKRW=X']
            indices_df = yf.download(tickers, start=datetime.today()-timedelta(days=365), progress=False)['Close'].ffill()
            if not indices_df.empty:
                c1, c2 = st.columns(2); latest = indices_df.iloc[-1]; prev = indices_df.iloc[-2]
                c1.metric("S&P 500", f"{latest.get('^GSPC', 0):,.0f}", f"{(latest.get('^GSPC',0)/prev.get('^GSPC',1)-1)*100:+.2f}%")
                c2.metric("NASDAQ", f"{latest.get('^IXIC', 0):,.0f}", f"{(latest.get('^IXIC',0)/prev.get('^IXIC',1)-1)*100:+.2f}%")
                c3, c4 = st.columns(2)
                c3.metric("VIX (FEAR INDEX)", f"{latest.get('^VIX', 0):,.2f}", f"{(latest.get('^VIX',0)/prev.get('^VIX',1)-1)*100:+.2f}%", delta_color="inverse")
                c4.metric("USD/KRW RATE", f"₩{latest.get('USDKRW=X', 0):,.1f}", f"{(latest.get('USDKRW=X',0)/prev.get('USDKRW=X',1)-1)*100:+.2f}%", delta_color="inverse")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=indices_df.index, y=indices_df['^GSPC']/indices_df['^GSPC'].iloc[0]*100, name="S&P 500", line=dict(color=C_UP)))
                fig.add_trace(go.Scatter(x=indices_df.index, y=indices_df['^IXIC']/indices_df['^IXIC'].iloc[0]*100, name="NASDAQ", line=dict(color=C_DOWN)))
                
                custom_layout = VINTAGE_LAYOUT.copy()
                custom_layout.update(height=240, showlegend=False)
                fig.update_layout(**custom_layout)
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.markdown("##### 🗺️ S&P 500 SECTOR MAP")
            components.html("""
            <iframe src="https://www.tradingview.com/embed-widget-stock-heatmap/?locale=kr#%7B%22dataSource%22%3A%22SPX500%22%2C%22blockSize%22%3A%22market_cap_basic%22%2C%22blockColor%22%3A%22change%22%2C%22grouping%22%3A%22sector%22%2C%22colorTheme%22%3A%22light%22%7D" width="100%" height="450" frameborder="0"></iframe>
            """, height=460)


# =====================================================================
# [3] 페이지 구성: AMLS 백테스트 (티어시트)
# =====================================================================
def page_amls_backtest():
    st.title("🦅 AMLS QUANT SIMULATOR (TEARSHEET)")
    st.markdown("PAPER TAPE SIMULATION OF HISTORICAL DATA.")

    st.sidebar.header("⚙️ PAPER PUNCH PARAMETERS")
    BACKTEST_START = st.sidebar.date_input("START DATE", datetime(2018, 1, 1))
    BACKTEST_END = st.sidebar.date_input("END DATE", datetime.today())
    INITIAL_CAPITAL = st.sidebar.number_input("INITIAL CAPITAL ($)", value=10000, step=1000)
    MONTHLY_CONTRIBUTION = st.sidebar.number_input("MONTHLY ADD ($)", value=2000, step=500)
    REBAL_FREQ = st.sidebar.selectbox("🔄 REBALANCING FREQ", ["월 1회", "주 1회 (5거래일)", "2주 1회 (10거래일)", "3주 1회 (15거래일)"], index=0)

    with st.spinner('PUNCHING CARDS. PLEASE WAIT...'):
        df, logs, tickers = load_amls_backtest_data(BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL, MONTHLY_CONTRIBUTION, REBAL_FREQ)
    
    def calc_metrics(series, invested_series):
        final_val = series.iloc[-1]
        total_inv = invested_series.iloc[-1]
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
        metrics_data.append({
            "STRATEGY": s,
            "FINAL EQUITY": f"${fv:,.0f}",
            "TOTAL RETURN": f"{tr*100:+.1f}%",
            "CAGR": f"{cagr*100:.1f}%",
            "MAX DRAWDOWN": f"{mdd*100:.1f}%",
            "SHARPE RATIO": f"{shp:.2f}"
        })
    metrics_df = pd.DataFrame(metrics_data).set_index("STRATEGY")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 METRICS", "📈 EQUITY CURVE", "🗓️ YEARLY", "📝 PUNCH LOG"])

    with tab1:
        st.markdown("#### 🏆 CORE PERFORMANCE LEDGER")
        st.info(f"**TOTAL INVESTED:** ${df['Invested'].iloc[-1]:,.0f} (INIT {INITIAL_CAPITAL} + {MONTHLY_CONTRIBUTION}/mo)")
        st.dataframe(metrics_df, use_container_width=True)

        st.markdown("#### 🥧 AMLS v4.3 ALLOCATION RULEBOOK")
        c1, c2, c3, c4 = st.columns(4)
        def get_w(reg):
            if reg == 1: return {'TQQQ':30, 'SOXL/USD':20, 'QLD':20, 'SSO':15, 'GLD':10, 'CASH':5}
            elif reg == 2: return {'QLD':30, 'SSO':25, 'GLD':20, 'USD':10, 'QQQ':5, 'CASH':10}
            elif reg == 3: return {'GLD':50, 'CASH':35, 'QQQ':15}
            elif reg == 4: return {'GLD':50, 'CASH':40, 'QQQ':10}
        colors = {'TQQQ':'#8b0000', 'SOXL/USD':'#556b2f', 'USD':'#8fbc8f', 'QLD':'#b8860b', 'SSO':'#cd853f', 'QQQ':'#000080', 'GLD':'#daa520', 'CASH':'#2f4f4f'}
        
        for i, col in enumerate([c1, c2, c3, c4]):
            r = i+1; w = {k:v for k,v in get_w(r).items() if v>0}
            fig_p = go.Figure(go.Pie(labels=list(w.keys()), values=list(w.values()), hole=0.5, marker=dict(colors=[colors.get(k, '#000') for k in w.keys()])))
            custom_layout = VINTAGE_LAYOUT.copy()
            custom_layout.update(title=f"REGIME {r}", title_x=0.5, height=250, showlegend=False)
            fig_p.update_layout(**custom_layout)
            fig_p.update_traces(textinfo='label+percent', textposition='inside')
            col.plotly_chart(fig_p, use_container_width=True)

    with tab2:
        st.markdown("#### 📈 EQUITY GROWTH")
        use_log = st.checkbox("LOGARITHMIC SCALE", value=False)
        fig_eq = go.Figure()
        colors_line = {'AMLS v4.3': '#006400', 'QQQ': '#000080', 'QLD': '#b8860b', 'TQQQ': '#8b0000'}
        for s in strats:
            fig_eq.add_trace(go.Scatter(x=df.index, y=df[f'{s}_Value'], name=s, line=dict(color=colors_line[s], width=3 if 'AMLS' in s else 1.5)))
        fig_eq.add_trace(go.Scatter(x=df.index, y=df['Invested'], name='INVESTED', line=dict(color='#555555', width=2, dash='dot')))
        if use_log: fig_eq.update_yaxes(type="log")
        custom_layout = VINTAGE_LAYOUT.copy()
        custom_layout.update(height=450, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_eq.update_layout(**custom_layout)
        st.plotly_chart(fig_eq, use_container_width=True)

        st.markdown("#### 📉 DRAWDOWN ANALYSIS")
        fig_dd = go.Figure()
        for s in strats:
            dd = (df[f'{s}_Value'] / df[f'{s}_Value'].cummax() - 1) * 100
            fig_dd.add_trace(go.Scatter(x=df.index, y=dd, name=f'{s} DD', line=dict(color=colors_line[s], width=2 if 'AMLS' in s else 1)))
        fig_dd.add_hline(y=-30, line_dash="dash", line_color="#8b0000", annotation_text="DANGER LINE -30%")
        custom_layout_dd = VINTAGE_LAYOUT.copy()
        custom_layout_dd.update(height=300, hovermode="x unified")
        fig_dd.update_layout(**custom_layout_dd)
        st.plotly_chart(fig_dd, use_container_width=True)

    with tab3:
        st.markdown("#### 🗓️ YEARLY RETURNS LEDGER")
        years = df.index.year.unique()
        yr_data = []
        for y in years:
            y_df = df[df.index.year == y]
            if len(y_df) > 0:
                row = {"Year": str(y)}
                for s in strats:
                    ret = (y_df[f'{s}_Value'].iloc[-1] / y_df[f'{s}_Value'].iloc[0] - 1) * 100
                    row[s] = ret
                yr_data.append(row)
        yr_df = pd.DataFrame(yr_data).set_index("Year")
        
        fig_yr = go.Figure()
        for s in strats:
            fig_yr.add_trace(go.Bar(name=s, x=yr_df.index, y=yr_df[s], marker_color=colors_line[s]))
        custom_layout_yr = VINTAGE_LAYOUT.copy()
        custom_layout_yr.update(barmode='group', height=400, yaxis_title="RETURN (%)")
        fig_yr.update_layout(**custom_layout_yr)
        st.plotly_chart(fig_yr, use_container_width=True)
        
        st.dataframe(yr_df.style.format("{:.1f}%"), use_container_width=True)

    with tab4:
        st.markdown("#### 📝 TYPEWRITER REBALANCING LOG")
        st.caption(f"FREQ APPLIED: **{REBAL_FREQ}**")
        log_df = pd.DataFrame(logs)[::-1]
        if not log_df.empty:
            log_df['EQUITY'] = log_df['EQUITY'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(log_df, hide_index=True, use_container_width=True)


# =====================================================================
# [4] 페이지 구성: 내 포트폴리오 관리 (UI 최적화 및 액션 지침 복구)
# =====================================================================
def make_portfolio_page(acc_name):
    def page_func():
        st.title(f"🏦 LEDGER: {acc_name}")
        curr_acc_data = st.session_state['accounts'][acc_name]
        pf_df = pd.DataFrame(curr_acc_data["portfolio"])
        pf_df["수량 (주/달러)"] = pf_df["수량 (주/달러)"].astype(float)
        pf_df["평균 단가 ($)"] = pf_df["평균 단가 ($)"].astype(float)
        pf_df["매입 환율"] = pf_df["매입 환율"].astype(float)

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
                if isinstance(fx_data, pd.DataFrame): fx_data = fx_data.iloc[:, 0]
                current_usdkrw = float(fx_data.iloc[-1])
            except:
                current_usdkrw = 0.0

            ma200_s = data['QQQ'].rolling(200).mean()
            ma50_s = data['QQQ'].rolling(50).mean()
            regime_series = []
            for i in range(len(data)):
                v = data['^VIX'].iloc[i]; q = data['QQQ'].iloc[i]
                m200 = ma200_s.iloc[i]; m50 = ma50_s.iloc[i]
                if pd.isna(m200): regime_series.append(2); continue
                if v > 40: regime_series.append(4)
                elif q < m200: regime_series.append(3)
                elif q >= m200 and m50 >= m200 and v < 25: regime_series.append(1)
                else: regime_series.append(2)

            current_reg = regime_series[-1]
            regime_duration = 0
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
                if regime_duration <= 10: entry_grade = "OPTIMAL ENTRY"
                elif regime_duration <= 30: entry_grade = "GOOD ENTRY"
                elif regime_duration <= 60: entry_grade = "OKAY (LONG DURATION)"
                else: entry_grade = "CAUTION: REVERSAL RISK"
            elif regime_direction == "descending":
                if regime_duration <= 5: entry_grade = "HOLD: FRESH DOWNTURN"
                elif regime_duration <= 20: entry_grade = "CAUTION: MORE DOWN"
                else: entry_grade = "BOTTOM FISHING"
            else:
                if regime_duration <= 30: entry_grade = "GOOD ENTRY"
                elif regime_duration <= 60: entry_grade = "OKAY (LONG DURATION)"
                else: entry_grade = "CAUTION: REVERSAL RISK"

            return {
                'regime': reg, 'vix': today['^VIX'], 'qqq': today['QQQ'], 'ma200': ma200, 'ma50': ma50,
                'smh': today['SMH'], 'smh_ma50': smh_ma50, 'smh_3m_ret': smh_3m_ret, 'smh_rsi': smh_rsi,
                'prices': today.to_dict(), 'prev_prices': yesterday.to_dict(), 'date': data.index[-1],
                'usdkrw': current_usdkrw,
                'regime_duration': regime_duration, 'prev_regime': prev_reg,
                'regime_direction': regime_direction, 'entry_grade': entry_grade
            }

        @st.cache_data(ttl=60)
        def get_realtime_prices():
            RT_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'USDKRW=X']
            try:
                rt = yf.download(RT_TICKERS, period='1d', interval='5m', prepost=True, progress=False)['Close']
                if rt.empty: return None
                return rt.ffill().iloc[-1].to_dict()
            except:
                return None

        with st.spinner("TRANSMITTING TELEGRAPH SIGNALS..."): 
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
            if 4 <= et_hour < 9.5: price_label = "PRE-MARKET"
            elif 9.5 <= et_hour < 16: price_label = "LIVE TRADING"
            elif 16 <= et_hour < 20: price_label = "AFTER-HOURS"
            else: price_label = "LIVE"
        else:
            price_label = "CLOSED"

        st.markdown("### 📡 MARKET INTELLIGENCE TICKER")
        with st.container(border=True):
            st.markdown(f"**DATE:** {ms['date'].strftime('%Y-%m-%d')} | 💹 **{price_label}** QUOTES")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                vix_val = ms['vix']
                fig_vix = go.Figure(go.Indicator(
                    mode = "gauge+number", value = vix_val, title = {'text': "VIX (FEAR INDEX)", 'font': {'size': 14, 'color': '#2c2a25'}},
                    number = {'font': {'color': '#2c2a25'}},
                    gauge = {
                        'axis': {'range': [0, 80], 'tickwidth': 1, 'tickcolor': "#2c2a25"},
                        'bar': {'color': "#2c2a25", 'thickness': 0.2},
                        'steps': [{'range': [0, 25], 'color': "#8fbc8f"}, {'range': [25, 40], 'color': "#daa520"}, {'range': [40, 80], 'color': "#8b0000"}],
                        'threshold': {'line': {'color': "#2c2a25", 'width': 4}, 'thickness': 0.75, 'value': 40}
                    }))
                cust_l = VINTAGE_LAYOUT.copy()
                cust_l.update(height=240, margin=dict(l=30, r=30, t=50, b=20))
                fig_vix.update_layout(**cust_l)
                st.plotly_chart(fig_vix, use_container_width=True)

            with col2:
                q_dist = (ms['qqq'] / ms['ma200'] - 1) * 100
                fig_qqq = go.Figure(go.Indicator(
                    mode = "gauge+number", value = q_dist, number={'suffix': "%", 'valueformat': "+.1f", 'font': {'color': '#2c2a25'}},
                    title = {'text': "QQQ 200MA DISTANCE", 'font': {'size': 14, 'color': '#2c2a25'}},
                    gauge = {
                        'axis': {'range': [-30, 30], 'tickwidth': 1, 'tickcolor': "#2c2a25"},
                        'bar': {'color': "#2c2a25", 'thickness': 0.2},
                        'steps': [{'range': [-30, 0], 'color': "#8b0000"}, {'range': [0, 30], 'color': "#8fbc8f"}],
                        'threshold': {'line': {'color': "#2c2a25", 'width': 4}, 'thickness': 0.75, 'value': 0}
                    }))
                fig_qqq.update_layout(**cust_l)
                st.plotly_chart(fig_qqq, use_container_width=True)

            with col3:
                rsi_val = ms['smh_rsi']
                fig_rsi = go.Figure(go.Indicator(
                    mode = "gauge+number", value = rsi_val, title = {'text': "SEMI (SMH) RSI", 'font': {'size': 14, 'color': '#2c2a25'}},
                    number = {'font': {'color': '#2c2a25'}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#2c2a25"},
                        'bar': {'color': "#2c2a25", 'thickness': 0.2},
                        'steps': [{'range': [0, 30], 'color': "#8b0000"}, {'range': [30, 50], 'color': "#daa520"}, {'range': [50, 100], 'color': "#000080"}],
                        'threshold': {'line': {'color': "#2c2a25", 'width': 4}, 'thickness': 0.75, 'value': 50}
                    }))
                fig_rsi.update_layout(**cust_l)
                st.plotly_chart(fig_rsi, use_container_width=True)

            st.divider()

            st.markdown("#### ⚡ SEMI 3X (SOXL) ENTRY LOGIC")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                s_icon = "[Y]" if ms['smh'] > ms['smh_ma50'] else "[N]"
                st.info(f"**{s_icon} SHORT TREND (50MA)**\n\n`{'BROKEN UP' if ms['smh'] > ms['smh_ma50'] else 'BROKEN DOWN'}`")
            with col_s2:
                ret_val = ms['smh_3m_ret'] * 100
                r_icon = "[Y]" if ret_val > 5.0 else "[N]"
                st.info(f"**{r_icon} 3M CUMULATIVE RET**\n\n`{ret_val:+.2f}%` (REQ: > 5%)")
            with col_s3:
                rsi_icon = "[Y]" if rsi_val > 50 else "[N]"
                st.info(f"**{rsi_icon} RELATIVE STRENGTH (RSI)**\n\n`{rsi_val:.1f}` (REQ: > 50)")

            st.divider()

            st.markdown("##### 🤖 AMLS QUANT ANALYST REPORT")
            app_reg = ms['regime']
            
            col_a1, col_a2 = st.columns([1, 4])
            with col_a1:
                bg_color = "#8b0000" if app_reg >= 3 else "#8fbc8f"
                border_color = "#2c2a25"
                st.markdown(f"<div style='text-align: center; padding: 20px; border-radius: 0px; background-color: {bg_color}; border: 3px double {border_color};'><h1 style='color: white; margin:0;'>R{app_reg}</h1><p style='color: white; margin:0;'>CURRENT REGIME</p></div>", unsafe_allow_html=True)
            with col_a2:
                if app_reg == 4:
                    st.error("🚨 **[PANIC] DANGER LEVEL MAX.** VIX > 40. LIQUIDATE EQUITY. MOVE TO GLD & CASH IMMEDIATELY.")
                elif app_reg == 3:
                    st.warning("⚠️ **[WARNING] BEAR MARKET CONFIRMED.** NASDAQ < 200MA. MAINTAIN DEFENSIVE POSTURE (GLD 50%).")
                elif app_reg == 1:
                    st.success("🔥 **[BULL] GOLDILOCKS ASCENT.** VIX STABLE. MA ALIGNED. DEPLOY 3X LEVERAGE FOR MAXIMUM VELOCITY.")
                else:
                    st.info("🛡️ **[CORRECTION] SECURE MARGIN.** TREND ALIVE BUT VOLATILE. REDUCE TO 2X LEVERAGE.")

            st.divider()
            st.markdown("##### 🚦 NEW CAPITAL ENTRY SIGNAL")
            entry_g = ms['entry_grade']
            dur = ms['regime_duration']
            direction = ms['regime_direction']
            prev_r = ms['prev_regime']
            reg_names = {1: 'R1 BULL', 2: 'R2 NORM', 3: 'R3 BEAR', 4: 'R4 CRASH'}
            dir_arrows = {'ascending': 'UP', 'descending': 'DOWN', 'stable': 'FLAT'}

            sig_color = '#2c2a25' # 빈티지니까 색상보다는 선 굵기와 배경으로
            sig_bg = "#dfd7c5"

            col_sig, col_detail = st.columns([1, 2.5])
            with col_sig:
                st.markdown(f"""
                <div style="text-align:center; padding:16px; border:3px double {sig_color}; background:{sig_bg};">
                    <div style="font-size:13px; font-weight:bold;">ENTRY SIGNAL TAPE</div>
                    <div style="font-size:22px; font-weight:bold; margin:6px 0;">{entry_g}</div>
                    <div style="font-size:12px;">DUR: {dur} DAYS | {reg_names.get(prev_r,'')} -> {reg_names.get(app_reg,'')}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_detail:
                st.markdown(f"**SHIFT DIR:** {dir_arrows.get(direction, '')} &nbsp; | &nbsp; **STAY DUR:** {dur} DAYS")
                st.info("ANALYST NOTE: READ TAPE CAREFULLY BEFORE INJECTING FRESH CAPITAL.")

        st.write("")
        c_h1, c_h2 = st.columns([5, 1])
        with c_h1: st.markdown(f"**[ 💼 PORTFOLIO LEDGER ]**")
        with c_h2:
            if st.button("🔄 CLEAR TAPE", use_container_width=True):
                st.session_state['accounts'][acc_name]["portfolio"] = [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0} for t in REQUIRED_TICKERS]
                save_accounts_data(st.session_state['accounts']); st.rerun()

        live_prices = {k: ms['prices'].get(k, 1.0) for k in REQUIRED_TICKERS}
        live_prices['CASH'] = 1.0
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
            buy_krw = row["평균 단가 ($)"] * row["매입 환율"]
            now_krw = row["현재가 ($)"] * current_usdkrw
            return (now_krw - buy_krw) / buy_krw * 100
        disp_df["원화 수익률 (%)"] = disp_df.apply(cy_krw, axis=1)

        def color_y(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #000080; font-weight: bold;'
                elif val < 0: return 'color: #8b0000; font-weight: bold;'
            return ''

        c_t, c_c = st.columns([1.2, 1])
        with c_t:
            st.caption(f"💡 DOUBLE CLICK TO TYPE. (LIVE QT: {price_label})")
            ed_disp = st.data_editor(
                disp_df.style.map(color_y, subset=["수익률 (%)", "원화 수익률 (%)"]), 
                num_rows="dynamic", use_container_width=True, height=350,
                column_config={
                    "현재가 ($)": st.column_config.NumberColumn(disabled=True, format="$ %.2f"),
                    "현재 환율": st.column_config.NumberColumn(disabled=True, format="₩ %.1f"),
                    "수익률 (%)": st.column_config.NumberColumn(disabled=True, format="%.2f %%"),
                    "원화 수익률 (%)": st.column_config.NumberColumn(disabled=True, format="%.2f %%"),
                    "매입 환율": st.column_config.NumberColumn(format="₩ %.1f"),
                }
            )
            base_cols = ["티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율"]
            if not ed_disp[base_cols].equals(pf_df[["티커 (Ticker)", "수량 (주/달러)", "평균 단가 ($)", "매입 환율"]]):
                st.session_state['accounts'][acc_name]["portfolio"] = ed_disp[base_cols].to_dict(orient="records")
                save_accounts_data(st.session_state['accounts']); st.rerun()

        with c_c:
            st.markdown("<div style='margin-top: 45px;'></div>", unsafe_allow_html=True)
            asset_vals = {}
            for _, r in ed_disp.iterrows():
                v = r["수량 (주/달러)"] * r["현재가 ($)"] if r["티커 (Ticker)"] != "CASH" else r["수량 (주/달러)"]
                if v > 0: asset_vals[r["티커 (Ticker)"]] = v
            
            total_val = sum(asset_vals.values())
            if total_val > 0:
                fig = go.Figure(go.Pie(labels=list(asset_vals.keys()), values=list(asset_vals.values()), hole=0.6, marker=dict(colors=['#556b2f','#8b0000','#b8860b','#000080','#daa520'])))
                cust_p = VINTAGE_LAYOUT.copy()
                cust_p.update(height=320, showlegend=False, annotations=[dict(text=f"TOTAL EQUITY<br><b>${total_val:,.0f}</b>", x=0.5, y=0.5, font_size=16, font=dict(family="'Special Elite', Courier", color="#2c2a25"), showarrow=False)])
                fig.update_layout(**cust_p)
                st.plotly_chart(fig, use_container_width=True)

        st.write("")
        st.markdown("**[ 🎯 REBALANCING DIRECTIVE ]**")
        auto_seed = 0.0
        for _, row in ed_disp.iterrows():
            qty = float(row["수량 (주/달러)"] if pd.notna(row["수량 (주/달러)"]) else 0)
            avg_p = float(row["평균 단가 ($)"] if pd.notna(row["평균 단가 ($)"]) else 0)
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            if qty > 0:
                if tkr == "CASH": auto_seed += qty
                else: auto_seed += qty * avg_p
        st.session_state['accounts'][acc_name]["target_seed"] = auto_seed

        rebal_base = total_val if total_val > 0 else auto_seed
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("💰 BOOK COST", f"${auto_seed:,.2f}")
        col_m2.metric("📊 TARGET BASE (LIVE)", f"${rebal_base:,.2f}")

        status_d = []
        smh_cond = (ms['smh'] > ms['smh_ma50']) and (ms['smh_3m_ret'] > 0.05) and (ms['smh_rsi'] > 50)
        
        def get_w_local(reg, usx):
            w = {t: 0.0 for t in REQUIRED_TICKERS}
            semi = 'SOXL' if usx else 'USD'
            if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['CASH'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
            elif reg == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'], w['CASH'] = 0.30, 0.25, 0.20, 0.10, 0.05, 0.10
            elif reg == 3: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
            elif reg == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
            return {k: v for k, v in w.items() if v > 0}
            
        target_w_dict = get_w_local(ms['regime'], smh_cond)

        all_tkrs = set([t for t in asset_vals.keys()] + list(target_w_dict.keys()))
        for tkr in all_tkrs:
            tkr = tkr.upper()
            my_v = asset_vals.get(tkr, 0.0)
            my_w = (my_v / total_val * 100) if total_val > 0 else 0.0
            tw = target_w_dict.get(tkr, 0.0)
            tv = rebal_base * tw
            diff = tv - my_v
            cp = live_prices.get(tkr, 0.0)
            
            if tkr != "CASH" and cp > 0:
                shares_to_trade = abs(diff) / cp
                krw_amt = abs(diff) * current_usdkrw if current_usdkrw > 0 else 0
                if shares_to_trade < 1.0:
                    action = "HOLD"
                elif diff > 0:
                    action = f"BUY {shares_to_trade:.0f} SHS (${diff:,.0f})"
                else:
                    action = f"SELL {shares_to_trade:.0f} SHS (${abs(diff):,.0f})"
            elif tkr == "CASH":
                if abs(diff) < 50: action = "HOLD"
                elif diff > 0: action = f"ADD ${diff:,.0f}"
                else: action = f"WITHDRAW ${abs(diff):,.0f}"
            else:
                action = "HOLD"
            
            if my_v > 0 or tw > 0: 
                status_d.append({"TICKER": tkr, "TARGET %": f"{tw*100:.1f}%", "ACTUAL %": f"{my_w:.1f}%", "TARGET $": f"${tv:,.0f}", "ACTUAL $": f"${my_v:,.0f}", "ACTION": action})
                
        if status_d:
            status_df = pd.DataFrame(status_d).sort_values("TARGET %", ascending=False)
            fig_comp = go.Figure(data=[
                go.Bar(name='ACTUAL', x=list(status_df['TICKER']), y=[float(str(x).replace('%','')) for x in status_df['ACTUAL %']], marker_color='#8b0000'),
                go.Bar(name='TARGET', x=list(status_df['TICKER']), y=[float(str(x).replace('%','')) for x in status_df['TARGET %']], marker_color='#000080')
            ])
            cust_b = VINTAGE_LAYOUT.copy()
            cust_b.update(barmode='group', height=250, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_comp.update_layout(**cust_b)
            st.plotly_chart(fig_comp, use_container_width=True)

            def color_act(val):
                val_s = str(val)
                if 'BUY' in val_s or 'ADD' in val_s: return 'color: #000080; font-weight: bold;'
                elif 'SELL' in val_s or 'WITHDRAW' in val_s: return 'color: #8b0000; font-weight: bold;'
                return ''
            st.dataframe(status_df.style.map(color_act, subset=['ACTION']), use_container_width=True, hide_index=True)


        st.write("")
        st.markdown("**[ 📈 BOOK VALUE TRAJECTORY ]**")
        
        if auto_seed > 0:
            with st.container(border=True):
                fed_str = curr_acc_data.get("first_entry_date")
                default_date = pd.to_datetime(fed_str).date() if fed_str else (datetime.today() - timedelta(days=90)).date()
                col_date, _ = st.columns([1, 3])
                with col_date:
                    u_date = st.date_input("INCEPTION DATE", value=default_date, key=f"date_{acc_name}")
                    if str(u_date) != str(fed_str)[:10]: 
                        st.session_state['accounts'][acc_name]["first_entry_date"] = str(u_date)
                        save_accounts_data(st.session_state['accounts'])
                
                try:
                    chart_start_ts = pd.Timestamp(u_date)
                    fetch_start = (chart_start_ts - timedelta(days=5)).strftime('%Y-%m-%d')
                    bench_data = yf.download("QQQ", start=fetch_start, progress=False)['Close'].ffill()
                    
                    if not bench_data.empty:
                        if isinstance(bench_data, pd.DataFrame): bench_series = bench_data.iloc[:, 0]
                        else: bench_series = bench_data
                        
                        bench_series = bench_series[bench_series.index >= chart_start_ts]
                        seed_curve = (bench_series / bench_series.iloc[0]) * auto_seed
                        
                        fig_seed = go.Figure()
                        fig_seed.add_trace(go.Scatter(x=seed_curve.index, y=seed_curve.values, name="SEED TRAJECTORY", line=dict(color='#000080', width=3), fill='tozeroy', fillcolor='rgba(0, 0, 128, 0.1)'))
                        fig_seed.add_trace(go.Scatter(x=seed_curve.index, y=[auto_seed]*len(seed_curve), name="ORIGINAL SEED", line=dict(color='#8b0000', width=2, dash='dot')))
                        cust_s = VINTAGE_LAYOUT.copy()
                        cust_s.update(height=350, yaxis_title="EQUITY ($)", hovermode="x unified")
                        fig_seed.update_layout(**cust_s)
                        st.plotly_chart(fig_seed, use_container_width=True)
                except Exception as e: pass

        st.write("")
        col_log1, col_log2 = st.columns([1.5, 1])
        with col_log1:
            st.markdown("**[ TRADER'S DIARY ]**")
            def save_j(): st.session_state['accounts'][acc_name]["journal_text"] = st.session_state[f"j_{acc_name}"]; save_accounts_data(st.session_state['accounts'])
            st.text_area("TYPE YOUR MARKET THOUGHTS HERE...", value=curr_acc_data.get('journal_text', ''), key=f"j_{acc_name}", height=150, on_change=save_j, label_visibility="collapsed")
        with col_log2:
            st.markdown("**[ SYSTEM LOGS ]**")
            history = curr_acc_data.get('history', [])
            if history: st.dataframe(pd.DataFrame(history)[::-1], hide_index=True, use_container_width=True, height=150)

    page_func.__name__ = f"pf_{abs(hash(acc_name))}"
    return page_func


# --- 페이지 구성: 계좌 관리 ---
def page_manage_accounts():
    st.title("⚙️ MANAGE LEDGERS")
    new_acc = st.text_input("NEW LEDGER NAME")
    if st.button("🚀 OPEN ACCOUNT", type="primary") and new_acc:
        if new_acc not in st.session_state['accounts']:
            st.session_state['accounts'][new_acc] = {"portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0} for t in REQUIRED_TICKERS], "history": [{"Date": datetime.now().strftime("%Y-%m-%d"), "Log": "✨ LEDGER CREATED"}], "target_seed": 10000.0}
            save_accounts_data(st.session_state['accounts']); st.rerun()
    st.divider()
    for acc in list(st.session_state['accounts'].keys()):
        c1, c2 = st.columns([4, 1])
        c1.write(f"💼 **{acc}**")
        if c2.button("DELETE", key=f"del_{acc}", disabled=len(st.session_state['accounts']) <=1):
            del st.session_state['accounts'][acc]; save_accounts_data(st.session_state['accounts']); st.rerun()

# --- 페이지 구성: 전략 명세서 ---
def page_strategy_specification():
    st.title("📜 AMLS STRATEGY MANIFESTO")
    st.caption("DEPARTMENT OF QUANTITATIVE STRATEGY | CONFIDENTIAL")
    st.markdown("""---""")

    with st.container():
        st.markdown("### 🏷️ VERSION: v4.3 (PHASED ENTRY)")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.info("**SUMMARY**\n- **BASE ASSET:** QQQ (NASDAQ 100 ETF)\n- **REGIME DETECTOR:** QQQ vs 200MA + VIX + MA CROSS\n- **RULE:** IMMEDIATE DOWN, 5-DAY VERIFY UP\n- **CORE ETF:** TQQQ, SOXL, USD, QLD, SSO, QQQ, SPY, GLD")
        with col_s2:
            st.success("**TARGETS**\n- **TARGET MDD:** UNDER -35%\n- **EVOLUTION:** v4 -> v4.2 -> v4.3\n- **CORE VALUE:** SURVIVE BEARS, EXPLOIT BULLS")

    st.markdown("### I. EVOLUTION LOG")
    st.markdown("- **v4:** 4-STAGE REGIMES (R1~R4) AND ASYMMETRIC RULES ESTABLISHED.\n- **v4.2:** R2 LEVERAGE TO 1.75X. R3 GLD TO 50% FOR HEAVY CRASHES.\n- **v4.3:** PHASED ENTRY IMPLEMENTED. PREVENTS GAIN LOSS DURING 5-DAY DELAY.")

    st.markdown("### II. REGIME DETECTION MATRIX")
    st.table(pd.DataFrame({"PRIORITY": ["1", "2", "3", "4"], "CONDITION": ["VIX > 40", "QQQ < 200MA", "QQQ > MA200 & MA50 > MA200 & VIX < 25", "OTHERWISE"], "TARGET": ["R4 (CRASH)", "R3 (BEAR)", "R1 (BULL)", "R2 (NORM)"]}))

    st.markdown("### III. ALLOCATION DIRECTIVE (v4.3)")
    tabs = st.tabs(["Regime 1", "Regime 2", "Regime 3", "Regime 4"])
    with tabs[0]: st.write("**EFFECTIVE LEVERAGE: ~2.25x**"); st.table(pd.DataFrame({"ASSET": ["TQQQ", "SOXL/USD", "QLD", "SSO", "GLD", "CASH"], "WEIGHT": ["30%", "20%", "20%", "15%", "10%", "5%"]}))
    with tabs[1]: st.write("**EFFECTIVE LEVERAGE: ~1.75x**"); st.table(pd.DataFrame({"ASSET": ["QLD", "SSO", "GLD", "USD", "QQQ", "CASH"], "WEIGHT": ["30%", "25%", "20%", "10%", "5%", "10%"]}))
    with tabs[2]: st.write("**EFFECTIVE LEVERAGE: ~0.15x**"); st.table(pd.DataFrame({"ASSET": ["QQQ", "GLD", "CASH"], "WEIGHT": ["15%", "50%", "35%"]}))
    with tabs[3]: st.write("**EFFECTIVE LEVERAGE: ~0.10x**"); st.table(pd.DataFrame({"ASSET": ["GLD", "QQQ", "CASH"], "WEIGHT": ["50%", "10%", "40%"]}))


# =====================================================================
# [5] 네비게이션 라우팅
# =====================================================================
pages = {
    "🌐 GLOBAL MACRO": [st.Page(page_market_dashboard, title="MARKET TICKER", icon="🗺️")],
    "📊 SIMULATIONS": [st.Page(page_amls_backtest, title="AMLS TEARSHEET", icon="🦅")],
    "🏦 MY LEDGERS": [],
    "📜 DIRECTIVES": [st.Page(page_strategy_specification, title="MANIFESTO v4.3", icon="📄")]
}

for name in st.session_state['accounts'].keys():
    pages["🏦 MY LEDGERS"].append(st.Page(make_portfolio_page(name), title=name, icon="💼"))

pages["🏦 MY LEDGERS"].append(st.Page(page_manage_accounts, title="⚙️ SETTINGS", icon="⚙️"))

# 사이드바 데이터 백업
with st.sidebar.expander("💾 ARCHIVE / RESTORE"):
    st.download_button("📥 PUNCH TAPE OUT", data=json.dumps(st.session_state['accounts']), file_name="amls_archive.json")
    up_f = st.file_uploader("📤 READ TAPE IN", type=['json'])
    if up_f and st.button("⚠️ OVERWRITE"):
        st.session_state['accounts'] = json.load(up_f)
        save_accounts_data(st.session_state['accounts'])
        st.rerun()

pg = st.navigation(pages)
pg.run()
