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
    .main .block-container { max-width: 1300px; margin: 0 auto; padding-top: 2rem; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Pretendard', sans-serif !important; color: #1A1A1A !important; letter-spacing: 0.5px; font-weight: 800 !important; }
    
    /* 🚨 알림 박스 (초콜릿 모양으로 높이 고정하여 삐뚤어짐 방지) */
    div[data-testid="stAlert"] { 
        background-color: #FFFDF7; border: 1px solid #2C2C2C; border-radius: 4px; 
        color: #1A1A1A; box-shadow: none; padding: 10px; min-height: 65px; 
        display: flex; align-items: center; justify-content: flex-start; font-size: 0.9em;
    }
    div[data-testid="stAlert"]:has(.stIcon-error), div[data-testid="stAlert"]:has(.stIcon-warning) { 
        border: 2px solid #8B0000; background-color: #FFECEC; color: #8B0000; font-weight: bold;
    }
    
    div[data-testid="stMetricValue"] > div { font-family: 'Pretendard', sans-serif; font-weight: 900; color: #1A1A1A; }
    div[data-testid="stButton"] > button { background-color: #1A1A1A; color: #FFFDF7; border-radius: 4px; border: 2px solid #1A1A1A; font-family: 'Pretendard', sans-serif; font-weight: bold; transition: all 0.3s; }
    div[data-testid="stButton"] > button:hover { background-color: #8B0000; border-color: #8B0000; color: #FFFDF7; }
    .stTabs [data-baseweb="tab-list"] { border-bottom: 3px solid #2C2C2C; gap: 20px; padding-bottom: 5px; }
    .stTabs [data-baseweb="tab"] { font-family: 'Pretendard', sans-serif; color: #1A1A1A; font-weight: 700; font-size: 1.1rem; border-radius: 4px 4px 0 0; border: 1px solid transparent; padding: 10px 15px; }
    .stTabs [aria-selected="true"] { background-color: #FFFDF7; border: 2px solid #2C2C2C; border-bottom: 3px solid #FFFDF7; margin-bottom: -3px; color: #8B0000; }
    hr { border-top: 1px dashed #2C2C2C; background: transparent; margin: 2.5em 0; }
    [data-testid="stDataFrame"] { border: 2px solid #2C2C2C; background-color: #FFFDF7; border-radius: 4px; }
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
# 2. 데이터 수집
# ==========================================
SECTOR_TICKERS = ['XLK', 'XLV', 'XLF', 'XLY', 'XLC', 'XLI', 'XLP', 'XLE', 'XLU', 'XLRE', 'XLB']
CORE_TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX', 'HYG', 'IEF', 'QQQE', 'UUP']
TICKERS = CORE_TICKERS + SECTOR_TICKERS
ASSET_LIST = ['TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'QQQ', 'GLD', 'CASH']

@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.now()
    start_date = "2006-01-01"
    data = yf.download(TICKERS, start=start_date, end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close']
    
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
    
    for sec in SECTOR_TICKERS:
        df[f'{sec}_1M'] = df[sec].pct_change(periods=21)
        
    return df.dropna()

with st.spinner('📰 거시경제 데이터베이스를 동기화 중입니다...'):
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

# 공통 차트 레이아웃
chart_layout = dict(paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Pretendard", color="#1A1A1A"), margin=dict(l=0, r=0, t=40, b=0))
radar_layout = dict(height=200, margin=dict(l=10, r=10, t=15, b=15), paper_bgcolor='#FFFDF7', plot_bgcolor='#FFFDF7', font=dict(family="Pretendard", color="#1A1A1A"))
regime_colors = {1: 'rgba(0, 0, 0, 0.02)', 2: 'rgba(0, 0, 0, 0.08)', 3: 'rgba(139, 0, 0, 0.1)', 4: 'rgba(139, 0, 0, 0.2)'}

# ==========================================
# 4. 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["I. 시장 분석관", "II. 역사적 폭락장 아카이브", "III. 초콜릿 보드 (8-Pack 레이더)", "IV. 매크로 뉴스 & AI 브리핑"])

# ------------------------------------------
# 탭 1: MARKET ANALYSIS
# ------------------------------------------
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("현재 시장 국면 (REGIME)")
        st.info(f"### {regime_info[curr_regime][0]}\n**적용 로직:** {regime_info[curr_regime][1]}")
        if curr_regime != target_regime: st.warning(f"⏳ **상태 변경 대기 중:** 시장이 R{target_regime} 조건을 터치했습니다.")
        else: st.success("✅ **상태 양호:** 현재 국면이 안정적으로 유지되고 있습니다.")
    with c2:
        st.subheader("V4.5 목표 포트폴리오")
        w_df = pd.DataFrame(list(target_weights.items()), columns=['자산 (ASSET)', '비중 (WEIGHT)'])
        w_df = w_df[w_df['비중 (WEIGHT)'] > 0].sort_values(by='비중 (WEIGHT)', ascending=False)
        w_df['비중 (WEIGHT)'] = w_df['비중 (WEIGHT)'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(w_df, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("기술적 차트 모니터링 (QQQ & TQQQ)")
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
# 탭 2: 역사적 폭락장 시뮬레이터
# ------------------------------------------
with tab2:
    st.subheader("역사적 폭락장 시뮬레이터 (Crisis Archive)")
    st.write("하락장이 올 때마다 이 기록을 보며 멘탈을 통제하십시오. V4.5 시스템은 역사적 피바다 속에서 항상 안전 자산으로 도망쳐 있었습니다.")
    
    crises = {"2008 금융위기 (서브프라임)": ("2007-08-01", "2009-12-31"), "2020 코로나 팬데믹": ("2020-01-01", "2020-12-31"), "2022 인플레이션 쇼크": ("2021-11-01", "2023-03-31")}
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
            if df_crisis['Regime'].iloc[i] in [3, 4]: r3_r4_days += 1
                
        crisis_fig.update_layout(title=f"V4.5 백테스트 궤적: {selected_crisis}", height=450, **chart_layout)
        st.plotly_chart(crisis_fig, use_container_width=True)
        st.info(f"💡 **시뮬레이터 분석:** 이 위기 구간(총 {len(df_crisis)} 거래일) 동안, V4.5 시스템은 **{r3_r4_days}일({r3_r4_days/len(df_crisis)*100:.1f}%)** 동안 붉은색 영역(R3/R4)에 머물며 **계좌의 녹아내림을 완벽하게 방어**했습니다.")

# ------------------------------------------
# 탭 3: 8-PACK EARLY WARNING RADAR (ALL VISUALIZED)
# ------------------------------------------
with tab3:
    st.subheader("조기 경보 초콜릿 보드 (8-Pack 시각화 레이더)")
    st.write("모든 텍스트 지표를 차트로 변환하고 4x2 그리드 배열로 고정했습니다. 시장의 8가지 맥박을 한눈에 감시하십시오.")
    
    # 분석용 데이터 슬라이싱 (최근 120일)
    df_view = df.iloc[-120:]
    
    row1 = st.columns(4)
    row2 = st.columns(4)
    
    # ---------------- ROW 1 ----------------
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
        
        if fg_score < 30: st.success("🔥 극단적 공포: 저점 매집 찬스.")
        elif fg_score > 70: st.error("⚠️ 극단적 탐욕: 추격 매수 자제.")
        else: st.info("🟢 중립: 심리 상태 안정적.")
        
        # 글씨 잘림 방지를 위해 차트 안의 title 속성 제거하고 마진(여백) 최적화
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

    # ---------------- ROW 2 ----------------
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
        if last_row['QQQ_20d_Ret'] > 0 and last_row['QQQE_20d_Ret'] < 0: st.warning("⚠️ 가짜 상승: 대장주 쏠림 현상 심화.")
        else: st.success("✅ 건전한 상승: 시장 전반 고른 상승.")
        
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_20d_Ret'], name='QQQ', line=dict(color='#1A1A1A', width=2)))
        fig6.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQE_20d_Ret'], name='QQQE', line=dict(color='#8B0000', dash='dot')))
        fig6.update_layout(**radar_layout, showlegend=False, yaxis=dict(tickformat='.0%'))
        st.plotly_chart(fig6, use_container_width=True)

    with row2[2]:
        st.markdown("##### 7. 안전 자산 선호 (금/주식)")
        if last_row['GLD_SPY_Ratio'] > last_row['GLD_SPY_MA50']: st.warning("⚠️ 이탈: 금(GLD)으로 자금 피신 중.")
        else: st.success("✅ 정상: 주식(SPY) 선호도 우위.")
        
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_Ratio'], line=dict(color='#1A1A1A', width=2)))
        fig7.add_trace(go.Scatter(x=df_view.index, y=df_view['GLD_SPY_MA50'], line=dict(color='#8B0000', dash='dot')))
        fig7.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig7, use_container_width=True)

    with row2[3]:
        st.markdown("##### 8. 달러 유동성 (UUP)")
        if last_row['UUP'] > last_row['UUP_MA50']: st.error("🚨 유동성 축소: 강달러 압박 심화.")
        else: st.success("✅ 유동성 양호: 달러 강세 진정됨.")
        
        fig8 = go.Figure()
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP'], line=dict(color='#1A1A1A', width=2)))
        fig8.add_trace(go.Scatter(x=df_view.index, y=df_view['UUP_MA50'], line=dict(color='#8B0000', dash='dot')))
        fig8.update_layout(**radar_layout, showlegend=False)
        st.plotly_chart(fig8, use_container_width=True)

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
            if not api_key: st.warning("API Key가 필요합니다.")
            elif not headlines_for_ai: st.warning("분석할 전보 데이터가 없습니다.")
            else:
                try:
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
                            st.success(f"✅ 심층 추론 분석이 완료되었습니다. (사용 모델: {clean_model_name})")
                            st.info(f"**🤖 System-2 애널리스트 심층 리포트:**\n\n{response.text}")
                            with st.expander("📋 리포트 텍스트 복사하기"): st.code(response.text, language="markdown")
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
