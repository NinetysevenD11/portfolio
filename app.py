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
    .stApp { background-color: #F5F0E8; color: #1A1A1A; font-family: 'Pretendard', sans-serif; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding-top: 2rem; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Pretendard', sans-serif !important; color: #1A1A1A !important; letter-spacing: 0.5px; font-weight: 800 !important; }
    div[data-testid="stAlert"] { background-color: #FFFDF7; border: 1px solid #2C2C2C; border-radius: 4px; color: #1A1A1A; box-shadow: none; padding: 10px 15px; }
    div[data-testid="stAlert"]:has(.stIcon-error), div[data-testid="stAlert"]:has(.stIcon-warning) { border: 2px solid #8B0000; background-color: #FFECEC; color: #8B0000; }
    div[data-testid="stMetricValue"] > div { font-family: 'Pretendard', sans-serif; font-weight: 900; color: #1A1A1A; }
    div[data-testid="stButton"] > button { background-color: #1A1A1A; color: #FFFDF7; border-radius: 4px; border: 2px solid #1A1A1A; font-family: 'Pretendard', sans-serif; font-weight: bold; transition: all 0.3s; }
    div[data-testid="stButton"] > button:hover { background-color: #8B0000; border-color: #8B0000; color: #FFFDF7; }
    .stTabs [data-baseweb="tab-list"] { border-bottom: 3px solid #2C2C2C; gap: 20px; padding-bottom: 5px; }
    .stTabs [data-baseweb="tab"] { font-family: 'Pretendard', sans-serif; color: #1A1A1A; font-weight: 700; font-size: 1.1rem; border-radius: 4px 4px 0 0; border: 1px solid transparent; padding: 10px 15px; }
    .stTabs [aria-selected="true"] { background-color: #FFFDF7; border: 2px solid #2C2C2C; border-bottom: 3px solid #FFFDF7; margin-bottom: -3px; color: #8B0000; }
    hr { border-top: 1px dashed #2C2C2C; background: transparent; margin: 2.5em 0; }
    [data-testid="stDataFrame"] { border: 2px solid #2C2C2C; background-color: #FFFDF7; border-radius: 4px; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { border-radius: 4px; border: 1px solid #2C2C2C; background-color: #FFFDF7; font-family: 'Pretendard', sans-serif; }
</style>
""", unsafe_allow_html=True)

# 📰 신문 헤더
st.markdown("""
<div style="text-align: center; border-top: 4px solid #1A1A1A; border-bottom: 4px double #1A1A1A; padding: 20px 0; margin-bottom: 30px;">
    <h1 style="font-family: Georgia, serif; font-size: 3.5em; font-weight: bold; letter-spacing: 4px; margin: 0; color: #1A1A1A;">RIMBERIO FINANCIAL GAZETTE</h1>
    <p style="font-size: 1.1em; letter-spacing: 2px; margin: 12px 0; font-weight: 700;">주식 & 채권 &nbsp;✦&nbsp; 퀀트 전략 &nbsp;✦&nbsp; 매크로 뉴스</p>
    <div style="font-size: 0.95em; border-top: 1px solid #1A1A1A; padding-top: 8px; display: flex; justify-content: center; gap: 40px; font-weight: 700;">
        <span>제 45호</span><span>AMLS V4.5 엔진</span><span>2026년 발행</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 수집 (2006년부터 수집하여 2008 폭락장 커버)
# ==========================================
# 섹터 ETF 11개 추가
SECTOR_TICKERS = ['XLK', 'XLV', 'XLF', 'XLY', 'XLC', 'XLI', 'XLP', 'XLE', 'XLU', 'XLRE', 'XLB']
CORE_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'HYG', 'IEF', 'QQQE', 'UUP']
TICKERS = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST = ['TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'QQQ', 'GLD', 'CASH']

@st.cache_data(ttl=3600)
def load_data():
    # 2008년 금융위기 시뮬레이션을 위해 2006년부터 데이터 수집
    end_date = datetime.now()
    start_date = "2006-01-01"
    data = yf.download(TICKERS, start=start_date, end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close']
    
    # 상장 전 데이터(NaN)로 인해 2008년 데이터가 날아가지 않도록 ffill/bfill 적용
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
    
    # 11개 섹터 1개월 수익률
    for sec in SECTOR_TICKERS:
        df[f'{sec}_1M'] = df[sec].pct_change(periods=21)
        
    return df.dropna()

with st.spinner('📰 거시경제 데이터베이스를 동기화 중입니다 (2006~현재)...'):
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
chart_layout = dict(paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Pretendard", color="#1A1A1A"), margin=dict(l=0, r=0, t=40, b=0))
regime_colors = {1: 'rgba(0, 0, 0, 0.02)', 2: 'rgba(0, 0, 0, 0.08)', 3: 'rgba(139, 0, 0, 0.1)', 4: 'rgba(139, 0, 0, 0.2)'}

# ==========================================
# 4. 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["I. 시장 분석관", "II. 역사적 폭락장 아카이브", "III. 8-Pack 레이더망", "IV. 매크로 뉴스 & AI 브리핑"])

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
    # 최근 2년 데이터만 그려서 최적화
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
# 탭 2: 역사적 폭락장 시뮬레이터 (신규)
# ------------------------------------------
with tab2:
    st.subheader("역사적 폭락장 시뮬레이터 (Crisis Archive)")
    st.write("피바다가 되었던 역사적 위기 구간에서, AMLS V4.5 시스템이 어떻게 현금/금(R3, R4)으로 도망쳐 자산을 수호했는지 확인하십시오. 하락장이 올 때마다 이 기록을 보며 멘탈을 통제하십시오.")
    
    crises = {
        "2008 금융위기 (서브프라임 모기지 사태)": ("2007-08-01", "2009-12-31"),
        "2020 코로나 팬데믹 (블랙 스완)": ("2020-01-01", "2020-12-31"),
        "2022 인플레이션 & 공격적 금리인상": ("2021-11-01", "2023-03-31")
    }
    
    selected_crisis = st.selectbox("조회할 역사적 위기를 선택하십시오:", list(crises.keys()))
    s_date, e_date = crises[selected_crisis]
    
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
            if df_crisis['Regime'].iloc[i] in [3, 4]:
                r3_r4_days += 1
                
        crisis_fig.update_layout(title=f"V4.5 백테스트 궤적: {selected_crisis}", height=450, **chart_layout)
        st.plotly_chart(crisis_fig, use_container_width=True)
        
        st.info(f"💡 **시뮬레이터 분석:** 이 위기 구간(총 {len(df_crisis)} 거래일) 동안, V4.5 시스템은 **{r3_r4_days}일({r3_r4_days/len(df_crisis)*100:.1f}%)** 동안 붉은색 영역(R3 하락장, R4 패닉장)에 머물며 **안전 자산(금/현금)으로 대피해 계좌의 녹아내림을 완벽하게 방어**했습니다.")

# ------------------------------------------
# 탭 3: 8-PACK EARLY WARNING RADAR
# ------------------------------------------
with tab3:
    st.subheader("조기 경보 8-Pack 레이더망 (종합 스마트머니 모니터링)")
    st.write("시스템이 붕괴를 공식화하기 전, 이면의 흐름을 읽어내고 자금 투입의 강약을 조절하는 월스트리트 프랍 데스크의 엑스레이입니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. 스마트 DCA
        st.markdown("#### 1. 스마트 DCA (자금 투입 페이스메이커)")
        qqq_rsi = last_row['QQQ_RSI']
        qqq_close = last_row['QQQ']
        qqq_ma200 = last_row['QQQ_MA200']
        if qqq_rsi < 40 and qqq_close < qqq_ma200: st.success("🔥 **적극 매수:** 시장이 공포에 질렸습니다. 비축한 현금을 투입할 시기입니다.")
        elif qqq_rsi > 70: st.error("⚠️ **투입 보류:** 시장 단기 과열. 적립금을 아끼고 현금을 비축하십시오.")
        else: st.info("🟢 **정상 적립:** 평시 상태입니다. 기계적인 월 적립 투자를 유지하십시오.")
        st.metric("QQQ 현재 RSI (14일)", f"{qqq_rsi:.1f}", "과열(70) / 침체(40)")
        st.divider()
        
        # 3. 인간 심리 계기판 (Fear & Greed)
        st.markdown("#### 3. 극단적 인간 심리 계기판")
        # 심리 점수 합성 (VIX, Drawdown, RSI 조합)
        vix_score = max(0, min(100, 100 - (last_row['^VIX'] - 12) / 28 * 100))
        dd_score = max(0, min(100, (last_row['QQQ_DD'] + 0.20) / 0.20 * 100))
        rsi_score = max(0, min(100, qqq_rsi))
        fg_score = (vix_score + dd_score + rsi_score) / 3
        
        fg_fig = go.Figure(go.Indicator(
            mode="gauge+number", value=fg_score, domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Fear & Greed Index", 'font': {'size': 18}},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#1A1A1A"},
                   'steps': [{'range': [0, 25], 'color': "rgba(139,0,0,0.7)"}, {'range': [25, 45], 'color': "rgba(139,0,0,0.3)"},
                             {'range': [45, 55], 'color': "rgba(0,0,0,0.1)"}, {'range': [55, 75], 'color': "rgba(0,100,0,0.3)"},
                             {'range': [75, 100], 'color': "rgba(0,100,0,0.7)"}]}
        ))
        fg_fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='#FFFDF7')
        st.plotly_chart(fg_fig, use_container_width=True)
        st.divider()

        # 5. 하이일드 채권 스프레드
        st.markdown("#### 5. 채권 스프레드 (스마트머니 이탈)")
        curr_ratio = last_row['HYG_IEF_Ratio']
        ma50_ratio = last_row['HYG_IEF_MA50']
        if curr_ratio < ma50_ratio: st.error("🚨 **위험 (Risk-Off):** 거대 자본이 위험 자산을 버리고 국채로 피신 중입니다.")
        else: st.success("✅ **안전 (Risk-On):** 채권 시장의 자금 흐름이 건전합니다.")
        fig_hyg = go.Figure()
        fig_hyg.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_Ratio'].iloc[-200:], name='비율', line=dict(color='#1A1A1A')))
        fig_hyg.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_MA50'].iloc[-200:], name='50일선', line=dict(color='#8B0000', dash='dot')))
        fig_hyg.update_layout(height=200, **chart_layout)
        st.plotly_chart(fig_hyg, use_container_width=True)
        st.divider()

        # 7. 안전자산 선호도 (금/주식)
        st.markdown("#### 7. 안전 자산 선호도 (금 vs 주식)")
        gld_spy_ratio = last_row['GLD_SPY_Ratio']
        gld_spy_ma50 = last_row['GLD_SPY_MA50']
        if gld_spy_ratio > gld_spy_ma50: st.warning("⚠️ **은밀한 이탈:** 스마트머니가 몰래 주식을 팔고 금을 매집 중입니다.")
        else: st.success("✅ **정상 흐름:** 주식이 금 대비 굳건한 우위를 점하고 있습니다.")
        fig_gld = go.Figure()
        fig_gld.add_trace(go.Scatter(x=df.index[-200:], y=df['GLD_SPY_Ratio'].iloc[-200:], name='GLD/SPY', line=dict(color='#1A1A1A')))
        fig_gld.add_trace(go.Scatter(x=df.index[-200:], y=df['GLD_SPY_MA50'].iloc[-200:], name='50일선', line=dict(color='#8B0000', dash='dot')))
        fig_gld.update_layout(height=200, **chart_layout)
        st.plotly_chart(fig_gld, use_container_width=True)

    with col2:
        # 2. 고점 대비 하락률 (Drawdown)
        st.markdown("#### 2. 멘탈 방어 온도계 (Drawdown)")
        qqq_dd = last_row['QQQ_DD']
        if qqq_dd < -0.20: st.error("🚨 **약세장 (Bear Market):** 고점 대비 -20% 이상 폭락. 시스템 규칙을 맹신하십시오.")
        elif qqq_dd < -0.10: st.warning("⚠️ **조정장 (Correction):** -10% 이상 하락. 과도한 공포를 경계하십시오.")
        else: st.success("✅ **안전 (Healthy):** 건전한 추세 내의 잔파도입니다. 흔들리지 마십시오.")
        st.metric("QQQ 52주 고점 대비 하락률", f"{qqq_dd*100:.2f}%", f"고점: ${last_row['QQQ_High52']:.2f} (현재: ${last_row['QQQ']:.2f})", delta_color="inverse")
        st.divider()

        # 4. 11개 섹터 자금 순환 지도
        st.markdown("#### 4. 섹터 자금 순환 지도 (1개월 수익률)")
        sec_names = {'XLK': '기술', 'XLV': '헬스케어', 'XLF': '금융', 'XLY': '자유소비재', 'XLC': '통신', 'XLI': '산업재', 'XLP': '필수소비재', 'XLE': '에너지', 'XLU': '유틸리티', 'XLRE': '부동산', 'XLB': '소재'}
        sec_data = [{'섹터': sec_names[s], '수익률': last_row[f'{s}_1M'] * 100} for s in SECTOR_TICKERS]
        sec_df = pd.DataFrame(sec_data).sort_values(by='수익률', ascending=True)
        
        fig_sec = go.Figure(go.Bar(
            x=sec_df['수익률'], y=sec_df['섹터'], orientation='h',
            marker_color=['#8B0000' if val < 0 else '#1A1A1A' for val in sec_df['수익률']]
        ))
        fig_sec.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7')
        st.plotly_chart(fig_sec, use_container_width=True)
        st.divider()

        # 6. 시장 폭 (Breadth)
        st.markdown("#### 6. 시장 폭 (가짜 상승 판별)")
        qqq_ret = last_row['QQQ_20d_Ret']
        qqqe_ret = last_row['QQQE_20d_Ret']
        if qqq_ret > 0 and qqqe_ret < 0: st.warning("⚠️ **가짜 상승 (Divergence):** 소수 대장주만 오르며 대다수는 하락 중입니다. 고점 징후입니다.")
        else: st.success("✅ **건전한 상승:** 시장 전반의 기업들이 고르게 상승에 참여하고 있습니다.")
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("QQQ (시총가중) 20D", f"{qqq_ret*100:+.2f}%")
        c_m2.metric("QQQE (동일가중) 20D", f"{qqqe_ret*100:+.2f}%")
        st.divider()

        # 8. 달러 유동성
        st.markdown("#### 8. 달러 유동성 진공청소기 (UUP)")
        uup_close = last_row['UUP']
        uup_ma50 = last_row['UUP_MA50']
        if uup_close > uup_ma50: st.error("🚨 **유동성 축소:** 달러가 강력하게 상승하며 글로벌 자금을 블랙홀처럼 빨아들이고 있습니다.")
        else: st.success("✅ **유동성 양호:** 달러 강세가 진정되어 위험 자산 투자에 우호적입니다.")
        fig_uup = go.Figure()
        fig_uup.add_trace(go.Scatter(x=df.index[-200:], y=df['UUP'].iloc[-200:], name='UUP', line=dict(color='#1A1A1A')))
        fig_uup.add_trace(go.Scatter(x=df.index[-200:], y=df['UUP_MA50'].iloc[-200:], name='50일선', line=dict(color='#8B0000', dash='dot')))
        fig_uup.update_layout(height=200, **chart_layout)
        st.plotly_chart(fig_uup, use_container_width=True)

# ------------------------------------------
# 탭 4: MACRO NEWS & AI
# ------------------------------------------
with tab4:
    st.subheader("실시간 글로벌 매크로 뉴스 및 심층 추론 브리핑")
    st.warning("⚠️ **[멘탈 주의보]** 쏟아지는 뉴스는 단순 참고용입니다. 자극적인 헤드라인에 흔들리지 마시고, 오직 시스템의 숫자에만 의존하십시오.")
    
    headlines_for_ai = []
    try:
        search_query = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req).read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:15]
        
        if items:
            for item in items:
                headlines_for_ai.append(item.find('title').text)
    except Exception as e:
        st.error(f"통신망 연결에 실패했습니다: {e}")

    with st.expander("✨ System-2 심층 추론 애널리스트에게 시장 분석 지시 (클릭하여 열기)", expanded=True):
        api_key = st.text_input("🔑 API KEY 입력:", type="password")
        
        if st.button("🚀 심층 추론 요약 실행"):
            if not api_key:
                st.warning("API Key가 필요합니다.")
            elif not headlines_for_ai:
                st.warning("분석할 전보 데이터가 없습니다.")
            else:
                try:
                    with st.spinner("최신 전보를 해독하며, 다각도 검증 및 심층 추론을 진행 중입니다..."):
                        genai.configure(api_key=api_key)
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        if not available_models:
                            st.error("사용 가능한 AI 모델이 없습니다.")
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
                                "위의 심층 추론(Deep-thinking) 과정은 너의 내부 논리로만 사용하고, 최종 출력되는 답변에는 다음 3가지 목차만 정확히 포함해서 작성해. 개별 뉴스에 대한 세세한 분석 및 검증 과정은 절대 화면에 출력하지 마.\n"
                                "1. 주요 뉴스 헤드라인 분류 및 초기 분석\n"
                                "2. 현재 주식 시장의 핵심 쟁점 및 잠재적 리스크 도출\n"
                                "3. 최종 고찰 (Reconsideration from Scratch)\n\n"
                                "[Task]\n"
                                "다음은 방금 수집된 미국의 증시, 나스닥, 연준 관련 최신 뉴스 헤드라인 15개야. "
                                "이 헤드라인들을 철저하게 분석하고, 숨겨진 논리적 허점을 찾아내 검증한 뒤, 지시된 3가지 목차로만 결과물을 도출해 줘.\n\n"
                                "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                            )
                            
                            response = model.generate_content(prompt)
                            st.success(f"✅ 심층 추론 분석이 완료되었습니다. (사용 모델: {clean_model_name})")
                            st.info(f"**🤖 System-2 애널리스트 심층 리포트:**\n\n{response.text}")
                            
                            with st.expander("📋 리포트 텍스트 복사하기 (클릭하여 열기)"):
                                st.code(response.text, language="markdown")
                                
                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다. 상세 에러: {e}")

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
