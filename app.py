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
# 1. 대시보드 기본 설정 및 CSS 삽입
# ==========================================
st.set_page_config(page_title="RIMBERIO FINANCIAL GAZETTE", layout="wide", page_icon="📰")

st.markdown("""
<style>
    /* 전체 배경 및 기본 폰트 (모던하고 깔끔한 산세리프 적용) */
    .stApp {
        background-color: #F5F0E8;
        color: #1A1A1A;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    }
    
    /* 레이아웃 폭 고정 (1100px 가운데 정렬) */
    .main .block-container {
        max-width: 1100px;
        margin: 0 auto;
        padding-top: 2rem;
    }

    /* 제목 폰트 (신문 섹션 느낌은 유지하되 깔끔하게) */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Pretendard', sans-serif !important;
        color: #1A1A1A !important;
        letter-spacing: 0.5px;
        font-weight: 800 !important;
    }

    /* 알림 박스 (경보, 성공 등 - 플랫하고 얇은 테두리) */
    div[data-testid="stAlert"] {
        background-color: #FFFDF7;
        border: 1px solid #2C2C2C;
        border-radius: 4px;
        color: #1A1A1A;
        box-shadow: none;
    }
    /* 경고/에러 박스 (Breaking News 느낌의 붉은 테두리) */
    div[data-testid="stAlert"]:has(.stIcon-error), div[data-testid="stAlert"]:has(.stIcon-warning) {
        border: 2px solid #8B0000;
        background-color: #FFECEC;
        color: #8B0000;
    }

    /* 지표(Metric) 숫자 폰트 */
    div[data-testid="stMetricValue"] > div {
        font-family: 'Pretendard', sans-serif;
        font-weight: 900;
        color: #1A1A1A;
    }

    /* 버튼 */
    div[data-testid="stButton"] > button {
        background-color: #1A1A1A;
        color: #FFFDF7;
        border-radius: 4px;
        border: 2px solid #1A1A1A;
        font-family: 'Pretendard', sans-serif;
        font-weight: bold;
        transition: all 0.3s;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #8B0000;
        border-color: #8B0000;
        color: #FFFDF7;
    }

    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 3px solid #2C2C2C;
        gap: 25px; 
        padding-bottom: 5px; 
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Pretendard', sans-serif;
        color: #1A1A1A;
        font-weight: 700;
        font-size: 1.05rem; 
        border-radius: 4px 4px 0 0;
        border: 1px solid transparent;
        padding: 10px 15px; 
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFDF7;
        border: 2px solid #2C2C2C;
        border-bottom: 3px solid #FFFDF7; 
        margin-bottom: -3px;
        color: #8B0000; 
    }

    /* 구분선 */
    hr {
        border-top: 1px dashed #2C2C2C;
        background: transparent;
        margin: 2.5em 0;
    }

    /* 데이터 프레임/테이블 */
    [data-testid="stDataFrame"] {
        border: 2px solid #2C2C2C;
        background-color: #FFFDF7;
        border-radius: 4px;
    }
    
    /* 텍스트 인풋 등 */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        border-radius: 4px;
        border: 1px solid #2C2C2C;
        background-color: #FFFDF7;
        font-family: 'Pretendard', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# 📰 신문 헤더 (Masthead) 삽입
st.markdown("""
<div style="text-align: center; border-top: 4px solid #1A1A1A; border-bottom: 4px double #1A1A1A; padding: 20px 0; margin-bottom: 30px; background-color: transparent;">
    <h1 style="font-family: Georgia, serif; font-size: 3em; font-weight: bold; letter-spacing: 4px; margin: 0; color: #1A1A1A;">RIMBERIO FINANCIAL GAZETTE</h1>
    <p style="font-family: 'Pretendard', sans-serif; font-size: 1.1em; letter-spacing: 2px; margin: 12px 0; color: #1A1A1A; font-weight: 700;">
        주식 & 채권 &nbsp;✦&nbsp; 퀀트 전략 &nbsp;✦&nbsp; 매크로 뉴스
    </p>
    <div style="font-family: 'Pretendard', sans-serif; font-size: 0.95em; border-top: 1px solid #1A1A1A; padding-top: 8px; display: flex; justify-content: center; gap: 40px; color: #1A1A1A; font-weight: 700;">
        <span>제 45호</span>
        <span>AMLS V4.5 엔진</span>
        <span>2026년 발행</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 수집 및 지표 계산
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

with st.spinner('📰 최신 증시 지면을 인쇄 중입니다...'):
    df = load_data()

# ==========================================
# 3. AMLS v4.5 코어 엔진
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
    1: ("🟢 R1 (대세 강세장)", "풀 레버리지 가동"),
    2: ("🟡 R2 (경계/조정장)", "세윤's Rule (TQQQ 15% 방어 모드)"),
    3: ("🟠 R3 (대세 하락장)", "안전 자산 대피 (금/현금)"),
    4: ("🔴 R4 (패닉장)", "최대 방어 모드")
}

# ==========================================
# 4. 탭 구성 (섹션)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["I. 시장 분석관", "II. 리밸런싱 장부", "III. 조기 경보 레이더", "IV. 매크로 뉴스룸"])

# ------------------------------------------
# 탭 1: MARKET ANALYSIS
# ------------------------------------------
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("현재 시장 국면 (REGIME)")
        st.info(f"### {regime_info[curr_regime][0]}\n**적용 로직:** {regime_info[curr_regime][1]}")
        if curr_regime != target_regime:
            st.warning(f"⏳ **상태 변경 대기 중:** 시장이 R{target_regime} 조건을 터치했습니다.")
        else:
            st.success("✅ **상태 양호:** 현재 국면이 안정적으로 유지되고 있습니다.")
            
        if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
            st.error("🚨 **[선행 경보 발동]** QQQ는 아직 200일선 위지만, **TQQQ가 200일선을 이탈했습니다.** 곧 R3로 강등될 위험이 높습니다!")
            
    with c2:
        st.subheader("V4.5 목표 포트폴리오")
        w_df = pd.DataFrame(list(target_weights.items()), columns=['자산 (ASSET)', '비중 (WEIGHT)'])
        w_df = w_df[w_df['비중 (WEIGHT)'] > 0].sort_values(by='비중 (WEIGHT)', ascending=False)
        w_df['비중 (WEIGHT)'] = w_df['비중 (WEIGHT)'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(w_df, hide_index=True, use_container_width=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ 종가 vs 200일선", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200'] - 1)*100:+.2f}%")
    m2.metric("TQQQ 종가 vs 200일선", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200'] - 1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (5일 이평선)", f"{last_row['VIX_MA5']:.2f}", f"종가: {last_row['^VIX']:.2f}")
    m4.metric("반도체 1M 수익률", f"{last_row['SMH_1M_Ret']*100:+.2f}%", "SOXL 조건")
    m5.metric("반도체 3M 수익률", f"{last_row['SMH_3M_Ret']*100:+.2f}%", "")

    st.divider()
    st.subheader("기술적 차트 모니터링 (QQQ & TQQQ)")
    
    chart_col1, chart_col2 = st.columns(2)
    
    chart_layout = dict(
        paper_bgcolor='#FFFDF7',
        plot_bgcolor='#FFFDF7',
        font=dict(family="Pretendard, sans-serif", color="#1A1A1A"),
        height=350,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df.index, y=df['QQQ'], name='QQQ', line=dict(color='#1A1A1A', width=2)))
    fig_qqq.add_trace(go.Scatter(x=df.index, y=df['QQQ_MA200'], name='200일선', line=dict(color='#8B0000', width=2, dash='dash')))
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df.index, y=df['TQQQ'], name='TQQQ', line=dict(color='#1A1A1A', width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df.index, y=df['TQQQ_MA200'], name='200일선', line=dict(color='#8B0000', width=2, dash='dash')))
    
    colors = {1: 'rgba(0, 0, 0, 0.03)', 2: 'rgba(0, 0, 0, 0.08)', 3: 'rgba(139, 0, 0, 0.1)', 4: 'rgba(139, 0, 0, 0.2)'}
    for i in range(1, len(df)):
        if df['Regime'].iloc[i-1] != df['Regime'].iloc[i] or i == 1:
            start_idx = df.index[i]
            curr_r = df['Regime'].iloc[i]
        if i == len(df)-1 or df['Regime'].iloc[i] != df['Regime'].iloc[i+1]:
            fig_qqq.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=1, layer="below", line_width=0)
            fig_tqqq.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=1, layer="below", line_width=0)
            
    fig_qqq.update_layout(title="[시스템 기준] QQQ vs 200일 이평선", **chart_layout)
    fig_tqqq.update_layout(title="[조기 경보] TQQQ vs 200일 이평선", **chart_layout)
    
    with chart_col1:
        st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2:
        st.plotly_chart(fig_tqqq, use_container_width=True)

# ------------------------------------------
# 탭 2: REBALANCING
# ------------------------------------------
with tab2:
    st.subheader("내 포트폴리오 리밸런싱 장부")
    st.write("현재 보유 중인 자산의 평가 금액을 입력하면, V4.5 목표 비중에 맞춘 정확한 주문 금액을 계산합니다.")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        current_holdings = {}
        total_value = 0
        for asset in ASSET_LIST:
            val = st.number_input(f"{asset} 보유 금액 ($)", min_value=0.0, value=0.0, step=100.0)
            current_holdings[asset] = val
            total_value += val
        
        add_cash = st.number_input("신규 투입 예수금 ($)", min_value=0.0, value=0.0, step=100.0)
        total_value += add_cash

    with col_result:
        if total_value > 0:
            st.markdown(f"### 총 운용 자산: **${total_value:,.2f}**")
            
            rebal_data = []
            for asset in ASSET_LIST:
                target_ratio = target_weights[asset]
                target_amt = total_value * target_ratio
                curr_amt = current_holdings[asset]
                if asset == 'CASH': curr_amt += add_cash
                
                diff = target_amt - curr_amt
                action = "매수 🟢" if diff > 0 else ("매도 🔴" if diff < 0 else "유지 ⚪")
                if abs(diff) < 1: action = "유지 ⚪"
                
                rebal_data.append({
                    "자산": asset,
                    "목표 비중": f"{target_ratio*100:.0f}%",
                    "목표 금액": f"${target_amt:,.2f}",
                    "현재 금액": f"${curr_amt:,.2f}",
                    "액션": action,
                    "주문 금액": f"${abs(diff):,.2f}"
                })
            
            rebal_df = pd.DataFrame(rebal_data)
            st.dataframe(rebal_df, hide_index=True, use_container_width=True)
            st.info("💡 **지침:** 매도(🔴) 주문을 먼저 실행하여 장부상 현금을 확보한 뒤, 매수(🟢)를 진행하십시오.")
        else:
            st.info("장부에 현재 보유 자산 금액을 입력해 주십시오.")

# ------------------------------------------
# 탭 3: EARLY WARNING
# ------------------------------------------
with tab3:
    st.subheader("조기 경보 레이더 (스마트머니 동향)")
    st.write("시스템이 폭락을 공식화하기 전에 자금 시장의 이면을 감지하는 지표입니다.")
    r1, r2 = st.columns(2)
    
    with r1:
        st.markdown("#### 1. 하이일드 채권 스프레드 (HYG/IEF)")
        curr_ratio = last_row['HYG_IEF_Ratio']
        ma50_ratio = last_row['HYG_IEF_MA50']
        
        if curr_ratio < ma50_ratio:
            st.error("🚨 **위험 (Risk-Off):** 거대 자본이 위험 자산을 버리고 안전 자산(국채)으로 피신하고 있습니다.")
        else:
            st.success("✅ **안전 (Risk-On):** 채권 시장의 자금 흐름이 건전합니다.")
            
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_Ratio'].iloc[-200:], name='HYG/IEF 비율', line=dict(color='#1A1A1A')))
        fig2.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_MA50'].iloc[-200:], name='50일선', line=dict(color='#8B0000', dash='dot')))
        fig2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Pretendard, sans-serif", color="#1A1A1A"))
        st.plotly_chart(fig2, use_container_width=True)

    with r2:
        st.markdown("#### 2. 시장 폭 (가짜 상승 판별)")
        qqq_ret = last_row['QQQ_20d_Ret']
        qqqe_ret = last_row['QQQE_20d_Ret']
        
        if qqq_ret > 0 and qqqe_ret < 0:
            st.warning("⚠️ **가짜 상승 (Divergence):** 소수의 대장주만 지수를 끌어올리고 있으며, 대다수 기업은 하락 중입니다.")
        else:
            st.success("✅ **건전한 상승:** 시장 전반의 기업들이 고르게 상승에 참여하고 있습니다.")
            
        st.metric("QQQ (시총가중) 20일 수익률", f"{qqq_ret*100:+.2f}%")
        st.metric("QQQE (동일가중) 20일 수익률", f"{qqqe_ret*100:+.2f}%")

# ------------------------------------------
# 탭 4: MACRO NEWS
# ------------------------------------------
with tab4:
    st.subheader("실시간 글로벌 매크로 뉴스 및 심층 추론(Deep-Thought) 브리핑")
    st.warning("⚠️ **[멘탈 주의보]** 쏟아지는 뉴스는 단순 참고용입니다. 자극적인 헤드라인에 흔들리지 마시고, 오직 시스템의 숫자에만 의존하십시오.")
    
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
        st.error(f"통신망 연결에 실패했습니다: {e}")

    with st.expander("✨ System-2 심층 추론 애널리스트에게 시장 분석 지시 (클릭하여 열기)", expanded=True):
        st.markdown("발급받은 API Key를 입력하여 전보(Telegram)의 내용을 **초정밀 심층 분석(Ultra-deep thinking mode)** 하십시오. *(분석에 시간이 다소 소요될 수 있습니다)*")
        api_key = st.text_input("🔑 API KEY 입력:", type="password")
        
        if st.button("🚀 심층 추론 요약 실행"):
            if not api_key:
                st.warning("API Key가 필요합니다.")
            elif not headlines_for_ai:
                st.warning("분석할 전보 데이터가 없습니다.")
            else:
                try:
                    with st.spinner("최신 전보를 해독하며, 다각도 검증 및 심층 추론을 진행 중입니다. 잠시만 기다려주세요..."):
                        genai.configure(api_key=api_key)
                        
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        if not available_models:
                            st.error("API Key에 접근 가능한 AI 모델이 없습니다. 설정을 확인해 주세요.")
                        else:
                            target_model = next((m for m in available_models if 'flash' in m.lower() or 'pro' in m.lower()), available_models[0])
                            clean_model_name = target_model.replace('models/', '')
                            model = genai.GenerativeModel(clean_model_name)
                            
                            # 세윤님이 요청하신 Ultra-deep thinking mode 프롬프트 완벽 이식
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
                                "[Task]\n"
                                "다음은 방금 수집된 미국의 증시, 나스닥, 연준 관련 최신 뉴스 헤드라인 15개야. "
                                "위의 지침에 따라 이 헤드라인들을 철저하게 분석하고, 숨겨진 논리적 허점을 찾아내 검증한 뒤, 현재 주식 시장의 핵심 쟁점과 잠재적 리스크를 도출해 줘.\n\n"
                                "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                            )
                            
                            response = model.generate_content(prompt)
                            st.success(f"✅ 심층 추론 분석이 완료되었습니다. (사용 모델: {clean_model_name})")
                            st.info(f"**🤖 System-2 애널리스트 심층 리포트:**\n\n{response.text}")
                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다. 키 값을 확인하십시오. 상세 에러: {e}")

    st.divider()
    st.markdown("#### 📝 최신 경제 헤드라인 원문")
    if items:
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            clean_date = pubDate[:-4] if pubDate else ""
            st.markdown(f"- [{title}]({link}) <span style='color:#8B0000; font-family:Pretendard, sans-serif; font-size:0.8em;'>({clean_date})</span>", unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다.")
