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
# 1. 대시보드 기본 설정 및 빈티지 CSS 삽입
# ==========================================
st.set_page_config(page_title="RIMBERIO FINANCIAL GAZETTE", layout="wide", page_icon="📰")

st.markdown("""
<style>
    /* 전체 배경 및 기본 폰트 (타자기 느낌) */
    .stApp {
        background-color: #F5F0E8;
        color: #1A1A1A;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* 레이아웃 폭 고정 (1100px 가운데 정렬) */
    .main .block-container {
        max-width: 1100px;
        margin: 0 auto;
        padding-top: 2rem;
    }

    /* 제목 (Georgia, 대문자, 자간 넓게) */
    h1, h2, h3, h4, h5, h6 {
        font-family: Georgia, serif !important;
        color: #1A1A1A !important;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* 알림 박스 (경보, 성공 등 - 플랫하고 얇은 테두리) */
    div[data-testid="stAlert"] {
        background-color: #FFFDF7;
        border: 1px solid #2C2C2C;
        border-radius: 0px;
        color: #1A1A1A;
        box-shadow: none;
    }
    /* 경고/에러 박스 (Breaking News 느낌의 붉은 테두리) */
    div[data-testid="stAlert"]:has(.stIcon-error), div[data-testid="stAlert"]:has(.stIcon-warning) {
        border: 2px solid #8B0000;
        background-color: #FFECEC;
        color: #8B0000;
    }

    /* 지표(Metric) 숫자 폰트 (크고 굵은 Serif) */
    div[data-testid="stMetricValue"] > div {
        font-family: Georgia, serif;
        font-weight: bolder;
        color: #1A1A1A;
    }

    /* 버튼 (Sharp edges, Black & White) */
    div[data-testid="stButton"] > button {
        background-color: #1A1A1A;
        color: #FFFDF7;
        border-radius: 0px;
        border: 2px solid #1A1A1A;
        font-family: Georgia, serif;
        text-transform: uppercase;
        font-weight: bold;
        transition: all 0.3s;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #8B0000;
        border-color: #8B0000;
        color: #FFFDF7;
    }

    /* 탭 디자인 (신문 섹션 스타일) */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 4px double #2C2C2C;
        gap: 0px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: Georgia, serif;
        color: #1A1A1A;
        font-weight: bold;
        border-radius: 0;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFDF7;
        border: 2px solid #2C2C2C;
        border-bottom: 2px solid #FFFDF7;
        margin-bottom: -2px;
    }

    /* 구분선 (신문 느낌의 점선) */
    hr {
        border-top: 2px dashed #2C2C2C;
        background: transparent;
        margin: 2em 0;
    }

    /* 데이터 프레임/테이블 */
    [data-testid="stDataFrame"] {
        border: 2px solid #2C2C2C;
        background-color: #FFFDF7;
    }
    
    /* 텍스트 인풋 등 */
    .stTextInput>div>div>input {
        border-radius: 0;
        border: 1px solid #2C2C2C;
        background-color: #FFFDF7;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

# 📰 신문 헤더 (Masthead) 삽입
st.markdown("""
<div style="text-align: center; border-top: 4px solid #1A1A1A; border-bottom: 4px double #1A1A1A; padding: 20px 0; margin-bottom: 30px; background-color: transparent;">
    <h1 style="font-family: Georgia, serif; font-size: 3em; font-weight: bold; letter-spacing: 4px; margin: 0; color: #1A1A1A;">RIMBERIO FINANCIAL GAZETTE</h1>
    <p style="font-family: 'Courier New', monospace; font-size: 1em; letter-spacing: 2px; margin: 10px 0; color: #1A1A1A; font-weight: bold;">
        STOCKS & BONDS &nbsp;✦&nbsp; QUANT STRATEGY &nbsp;✦&nbsp; MACRO NEWS
    </p>
    <div style="font-family: Georgia, serif; font-size: 0.9em; border-top: 1px solid #1A1A1A; padding-top: 5px; display: flex; justify-content: center; gap: 40px; color: #1A1A1A; font-weight: bold;">
        <span>ISSUE NO. 45</span>
        <span>AMLS V4.5 ENGINE</span>
        <span>EST. 2026</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 수집 및 지표 계산 (로직 유지)
# ==========================================
TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'HYG', 'IEF', 'QQQE']
ASSET_LIST = ['TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'QQQ', 'GLD', 'CASH']

@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=500)
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close'].ffill()
    
    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]
    
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
    
    return df.dropna()

with st.spinner('📰 최신 증시 인쇄 중...'):
    df = load_data()

# ==========================================
# 3. AMLS v4.5 코어 엔진 (로직 유지)
# ==========================================
def get_target_v45(row):
    v_close, v_ma5, q, m2, m5 = row['^VIX'], row['VIX_MA5'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
    if v_close > 40: return 4 
    if q < m2: return 3
    if q >= m2 and m5 >= m2 and v_ma5 < 25: return 1 
    return 2

df['Target'] = df.apply(get_target_v45, axis=1)

def apply_delay(targets):
    res = []; curr = 3; pend = None; cnt = 0
    for t in targets:
        if t > curr: curr = t; pend = None; cnt = 0
        elif t < curr:
            if t == pend:
                cnt += 1
                if cnt >= 5: curr = t; pend = None; cnt = 0
            else: pend = t; cnt = 1
        else: pend = None; cnt = 0
        res.append(curr)
    return pd.Series(res, index=targets.index).shift(1).bfill()

df['Regime'] = apply_delay(df['Target'])

def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if smh_ok else 'USD'
    if reg == 1: 
        w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2: 
        w['TQQQ'], w['QLD'], w['SSO'], w['GLD'], w['USD'], w['SPY'] = 0.15, 0.35, 0.20, 0.20, 0.10, 0.00
    elif reg == 3: 
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4: 
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w

last_row = df.iloc[-1]
curr_regime = int(last_row['Regime'])
target_regime = int(last_row['Target'])

smh_cond = (last_row['SMH'] > last_row['SMH_MA50']) and ((last_row['SMH_3M_Ret'] > 0.05) or (last_row['SMH_1M_Ret'] > 0.10)) and (last_row['SMH_RSI'] > 50)
target_weights = get_weights_v45(curr_regime, smh_cond)

regime_info = {
    1: ("R1 (BULL MARKET)", "FULL ALLOCATION"),
    2: ("R2 (CORRECTION)", "SEYOON'S RULE (15% DEFENSE)"),
    3: ("R3 (BEAR MARKET)", "SAFE HAVEN (GOLD/CASH)"),
    4: ("R4 (PANIC)", "MAXIMUM DEFENSE")
}

# ==========================================
# 4. 탭 구성 (섹션)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["I. MARKET ANALYSIS", "II. REBALANCING", "III. EARLY WARNING", "IV. MACRO NEWS"])

# ------------------------------------------
# 탭 1: MARKET ANALYSIS
# ------------------------------------------
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("CURRENT REGIME STATUS")
        st.info(f"### {regime_info[curr_regime][0]}\n**ACTION:** {regime_info[curr_regime][1]}")
        if curr_regime != target_regime:
            st.warning(f"WAITING FOR CONFIRMATION: Market touched R{target_regime} conditions.")
        else:
            st.success("STATUS CLEAR: Regime is stable.")
            
        if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
            st.error("BREAKING: TQQQ has broken the 200-day moving average. High risk of regime downgrade.")
            
    with c2:
        st.subheader("TARGET PORTFOLIO")
        w_df = pd.DataFrame(list(target_weights.items()), columns=['ASSET', 'WEIGHT'])
        w_df = w_df[w_df['WEIGHT'] > 0].sort_values(by='WEIGHT', ascending=False)
        w_df['WEIGHT'] = w_df['WEIGHT'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(w_df, hide_index=True, use_container_width=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ TO 200MA", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200'] - 1)*100:+.2f}%")
    m2.metric("TQQQ TO 200MA", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200'] - 1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (5D MA)", f"{last_row['VIX_MA5']:.2f}", f"CLOSE: {last_row['^VIX']:.2f}")
    m4.metric("SEMI 1M RET", f"{last_row['SMH_1M_Ret']*100:+.2f}%", "SOXL COND")
    m5.metric("SEMI 3M RET", f"{last_row['SMH_3M_Ret']*100:+.2f}%", "")

    st.divider()
    st.subheader("TECHNICAL CHARTS (QQQ & TQQQ)")
    
    chart_col1, chart_col2 = st.columns(2)
    
    # 빈티지 톤 차트 속성
    chart_layout = dict(
        paper_bgcolor='#FFFDF7',
        plot_bgcolor='#FFFDF7',
        font=dict(family="Georgia, serif", color="#1A1A1A"),
        height=350,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df.index, y=df['QQQ'], name='QQQ', line=dict(color='#1A1A1A', width=2)))
    fig_qqq.add_trace(go.Scatter(x=df.index, y=df['QQQ_MA200'], name='200 MA', line=dict(color='#8B0000', width=2, dash='dash')))
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df.index, y=df['TQQQ'], name='TQQQ', line=dict(color='#1A1A1A', width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df.index, y=df['TQQQ_MA200'], name='200 MA', line=dict(color='#8B0000', width=2, dash='dash')))
    
    # 흑백/빈티지 톤 레짐 컬러
    colors = {1: 'rgba(0, 0, 0, 0.03)', 2: 'rgba(0, 0, 0, 0.08)', 3: 'rgba(139, 0, 0, 0.1)', 4: 'rgba(139, 0, 0, 0.2)'}
    for i in range(1, len(df)):
        if df['Regime'].iloc[i-1] != df['Regime'].iloc[i] or i == 1:
            start_idx = df.index[i]
            curr_r = df['Regime'].iloc[i]
        if i == len(df)-1 or df['Regime'].iloc[i] != df['Regime'].iloc[i+1]:
            fig_qqq.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=1, layer="below", line_width=0)
            fig_tqqq.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=1, layer="below", line_width=0)
            
    fig_qqq.update_layout(title="QQQ SYSTEM BASELINE", **chart_layout)
    fig_tqqq.update_layout(title="TQQQ EARLY WARNING", **chart_layout)
    
    with chart_col1:
        st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2:
        st.plotly_chart(fig_tqqq, use_container_width=True)

# ------------------------------------------
# 탭 2: REBALANCING
# ------------------------------------------
with tab2:
    st.subheader("LEDGER & REBALANCING CALCULATOR")
    st.write("Enter your current holdings to calculate exact orders required for the target regime.")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        current_holdings = {}
        total_value = 0
        for asset in ASSET_LIST:
            val = st.number_input(f"{asset} ($)", min_value=0.0, value=0.0, step=100.0)
            current_holdings[asset] = val
            total_value += val
        
        add_cash = st.number_input("NEW CASH ENTRY ($)", min_value=0.0, value=0.0, step=100.0)
        total_value += add_cash

    with col_result:
        if total_value > 0:
            st.markdown(f"### TOTAL ASSETS: **${total_value:,.2f}**")
            
            rebal_data = []
            for asset in ASSET_LIST:
                target_ratio = target_weights[asset]
                target_amt = total_value * target_ratio
                curr_amt = current_holdings[asset]
                if asset == 'CASH': curr_amt += add_cash
                
                diff = target_amt - curr_amt
                action = "BUY" if diff > 0 else ("SELL" if diff < 0 else "HOLD")
                if abs(diff) < 1: action = "HOLD"
                
                rebal_data.append({
                    "ASSET": asset,
                    "TARGET %": f"{target_ratio*100:.0f}%",
                    "TARGET AMT": f"${target_amt:,.2f}",
                    "CURRENT AMT": f"${curr_amt:,.2f}",
                    "ACTION": action,
                    "ORDER AMT": f"${abs(diff):,.2f}"
                })
            
            rebal_df = pd.DataFrame(rebal_data)
            st.dataframe(rebal_df, hide_index=True, use_container_width=True)
        else:
            st.info("Awaiting input in the ledger...")

# ------------------------------------------
# 탭 3: EARLY WARNING
# ------------------------------------------
with tab3:
    st.subheader("EARLY WARNING RADAR (SMART MONEY)")
    r1, r2 = st.columns(2)
    
    with r1:
        st.markdown("#### I. CREDIT SPREAD (HYG/IEF)")
        curr_ratio = last_row['HYG_IEF_Ratio']
        ma50_ratio = last_row['HYG_IEF_MA50']
        
        if curr_ratio < ma50_ratio:
            st.error("ALERT: Risk-Off sentiment detected. Capital is fleeing to safety.")
        else:
            st.success("STABLE: Credit markets show normal appetite for risk.")
            
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_Ratio'].iloc[-200:], name='HYG/IEF', line=dict(color='#1A1A1A')))
        fig2.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_MA50'].iloc[-200:], name='50 MA', line=dict(color='#8B0000', dash='dot')))
        fig2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Georgia, serif", color="#1A1A1A"))
        st.plotly_chart(fig2, use_container_width=True)

    with r2:
        st.markdown("#### II. MARKET BREADTH DIVERGENCE")
        qqq_ret = last_row['QQQ_20d_Ret']
        qqqe_ret = last_row['QQQE_20d_Ret']
        
        if qqq_ret > 0 and qqqe_ret < 0:
            st.warning("ALERT: Divergence detected. Market driven by few heavyweights.")
        else:
            st.success("STABLE: Broad market participation observed.")
            
        st.metric("QQQ (CAP-WEIGHTED) 20D", f"{qqq_ret*100:+.2f}%")
        st.metric("QQQE (EQUAL-WEIGHTED) 20D", f"{qqqe_ret*100:+.2f}%")

# ------------------------------------------
# 탭 4: MACRO NEWS
# ------------------------------------------
with tab4:
    st.subheader("TELEGRAPH & AI INTELLIGENCE BUREAU")
    st.warning("DISCLAIMER: Headlines are for observational purposes only. Stick to the mathematical rules.")
    
    headlines_for_ai = []
    try:
        search_query = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        xml_data = urllib.request.urlopen(req).read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:15]
        
        if items:
            for item in items:
                title = item.find('title').text
                headlines_for_ai.append(title)
    except Exception as e:
        st.error(f"Telegraph connection failed: {e}")

    with st.expander("REQUEST AI ANALYST SUMMARY", expanded=True):
        st.markdown("Provide your API Key to command the intelligence bureau.")
        api_key = st.text_input("API KEY:", type="password")
        
        if st.button("GENERATE REPORT"):
            if not api_key:
                st.warning("API Key required.")
            elif not headlines_for_ai:
                st.warning("No telegrams available for analysis.")
            else:
                try:
                    with st.spinner("Decoding telegrams..."):
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = (
                            "너는 1920년대 월스트리트의 날카로운 퀀트 애널리스트야. 말투도 딱딱하고 고전적인 비즈니스 신문 칼럼니스트처럼 해줘. "
                            "다음은 수집된 미국의 증시 최신 뉴스 헤드라인 15개야. "
                            "이걸 바탕으로 현재 시장 분위기와 리스크를 3~4줄로 명확하게 요약해 줘.\n\n"
                            "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                        )
                        
                        response = model.generate_content(prompt)
                        st.success("ANALYSIS COMPLETE.")
                        st.info(f"**INTELLIGENCE REPORT:**\n\n{response.text}")
                except Exception as e:
                    st.error(f"Analysis failed. Verify credentials. Error: {e}")

    st.divider()
    st.markdown("#### 📰 LATEST TELEGRAMS")
    if items:
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            clean_date = pubDate[:-4] if pubDate else ""
            st.markdown(f"- [{title}]({link}) <span style='color:#8B0000; font-family:Georgia; font-size:0.8em;'>({clean_date})</span>", unsafe_allow_html=True)
    else:
        st.write("No news received.")
