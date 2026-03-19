import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 대시보드 기본 설정
# ==========================================
st.set_page_config(page_title="AMLS v4.5 Dashboard", layout="wide", page_icon="🚀")
st.title("🚀 AMLS v4.5 대시보드 (세윤's Ultimate Edition)")
st.markdown("""
**구조적 결함을 완벽히 개선한 진화형 퀀트 엔진입니다.**
* 🛡️ **문제 1 해결:** VIX 5일 이동평균선 적용 (단기 지정학적 노이즈 완벽 필터링)
* 📉 **문제 2 해결 (세윤's Rule):** R2 강등 시 TQQQ 15% 잔류 + QLD 전환 (충격 스무딩 및 멘탈 보호)
* ⚡ **문제 3 해결:** 반도체(SOXL) 1개월 10% 급반등 조건 추가 (V자 반등 초입 포착)
""")
st.divider()

# ==========================================
# 2. 데이터 수집 및 지표 계산
# ==========================================
TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']

@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def load_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=500)
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close'].ffill()
    
    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]
    
    # 기본 이평선
    df['QQQ_MA50'] = df['QQQ'].rolling(window=50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(window=200).mean()
    df['SMH_MA50'] = df['SMH'].rolling(window=50).mean()
    
    # v4.5 핵심 추가 지표
    df['VIX_MA5'] = df['^VIX'].rolling(window=5).mean() # 🛡️ VIX 노이즈 필터
    df['SMH_3M_Ret'] = df['SMH'].pct_change(periods=63)
    df['SMH_1M_Ret'] = df['SMH'].pct_change(periods=21) # ⚡ SOXL 급반등 포착용
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    
    return df.dropna()

with st.spinner('해외 증시 데이터를 불러오고 시스템을 구동 중입니다...'):
    df = load_data()

# ==========================================
# 3. AMLS v4.5 코어 엔진 (레짐 및 비중)
# ==========================================
# 1) 레짐 판단 (VIX 5일선 적용)
def get_target_v45(row):
    v_close, v_ma5, q, m2, m5 = row['^VIX'], row['VIX_MA5'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
    if v_close > 40: return 4  # 패닉은 즉시 대피
    if q < m2: return 3
    if q >= m2 and m5 >= m2 and v_ma5 < 25: return 1 # R1 진입/유지는 5일 평균선 기준!
    return 2

df['Target'] = df.apply(get_target_v45, axis=1)

# 2) 5일 비대칭 딜레이 (상승만 5일 대기)
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

# 3) 세윤's Rule 비중 산출 로직
def get_weights_v45(reg, smh_ok):
    w = {t: 0.0 for t in TICKERS}; w['CASH'] = 0.0
    semi = 'SOXL' if smh_ok else 'USD'
    
    if reg == 1: 
        w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2: 
        # 📉 세윤's Rule: TQQQ 15% 남기고 QLD로 방어!
        w['TQQQ'], w['QLD'], w['SSO'], w['GLD'], w['USD'], w['SPY'] = 0.15, 0.35, 0.20, 0.20, 0.10, 0.00
    elif reg == 3: 
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.35, 0.15
    elif reg == 4: 
        w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return w

# ==========================================
# 4. 오늘의 액션 플랜 계산
# ==========================================
last_row = df.iloc[-1]
prev_row = df.iloc[-2]

curr_regime = int(last_row['Regime'])
target_regime = int(last_row['Target'])

# SOXL 진입 조건 (3개월 5% OR 1개월 10%)
smh_momentum = (last_row['SMH_3M_Ret'] > 0.05) or (last_row['SMH_1M_Ret'] > 0.10)
smh_cond = (last_row['SMH'] > last_row['SMH_MA50']) and smh_momentum and (last_row['SMH_RSI'] > 50)

current_weights = get_weights_v45(curr_regime, smh_cond)

# 상태 정의
regime_info = {
    1: ("🟢 R1 (대세 강세장)", "풀 레버리지 가동"),
    2: ("🟡 R2 (경계/조정장)", "세윤's Rule 가동: 1.5배수 스무딩 방어"),
    3: ("🟠 R3 (대세 하락장)", "현금 및 1배수 안전 대피소"),
    4: ("🔴 R4 (패닉장)", "최대 방어 모드")
}

# ==========================================
# 5. UI 화면 구성
# ==========================================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 현재 시장 국면 (Regime)")
    st.info(f"### {regime_info[curr_regime][0]}\n**전략:** {regime_info[curr_regime][1]}")
    
    if curr_regime != target_regime:
        st.warning(f"⏳ **상태 변경 대기 중:** 시장이 R{target_regime}의 조건을 터치했습니다. 5일 연속 유지 시 레짐이 변경됩니다.")
    else:
        st.success("✅ 현재 국면이 안정적으로 유지되고 있습니다.")

with col2:
    st.subheader("🛒 V4.5 목표 비중 (Target Weights)")
    
    # 비중 표 데이터화
    w_df = pd.DataFrame(list(current_weights.items()), columns=['자산', '비중'])
    w_df = w_df[w_df['비중'] > 0].sort_values(by='비중', ascending=False)
    w_df['비중'] = w_df['비중'].apply(lambda x: f"{x*100:.0f}%")
    
    st.dataframe(w_df, hide_index=True, use_container_width=True)

st.divider()

# 주요 지표 모니터링
st.subheader("🔍 V4.5 핵심 지표 모니터링")
c1, c2, c3, c4 = st.columns(4)
c1.metric("QQQ 종가 vs 200일선", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200'] - 1)*100:+.2f}%")
# VIX는 종가와 5일선을 같이 보여줍니다.
c2.metric("VIX (5일 이평선)", f"{last_row['VIX_MA5']:.2f}", f"종가: {last_row['^VIX']:.2f}")
c3.metric("반도체(SMH) 1개월 수익률", f"{last_row['SMH_1M_Ret']*100:.2f}%", "SOXL 스위칭 조건")
c4.metric("반도체(SMH) RSI", f"{last_row['SMH_RSI']:.1f}", "")

st.divider()

# 차트 그리기
st.subheader("📈 나스닥(QQQ) 200일선 및 레짐 시각화")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ'], name='QQQ (나스닥)', line=dict(color='black', width=2)))
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ_MA200'], name='200일 이평선', line=dict(color='red', width=2, dash='dash')))

# 레짐 백그라운드 컬러
colors = {1: 'rgba(0, 255, 0, 0.1)', 2: 'rgba(255, 255, 0, 0.1)', 3: 'rgba(255, 165, 0, 0.1)', 4: 'rgba(255, 0, 0, 0.1)'}
for i in range(1, len(df)):
    if df['Regime'].iloc[i-1] != df['Regime'].iloc[i] or i == 1:
        start_idx = df.index[i]
        curr_r = df['Regime'].iloc[i]
    if i == len(df)-1 or df['Regime'].iloc[i] != df['Regime'].iloc[i+1]:
        fig.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=0.5, layer="below", line_width=0)

fig.update_layout(height=400, template='plotly_white', hovermode='x unified', margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)

st.caption("💡 VIX 5일 평균선을 적용하여 과거 휩쏘 구간이 어떻게 평탄화(Smoothing)되었는지 확인해 보세요!")
