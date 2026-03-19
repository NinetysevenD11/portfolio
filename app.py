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
st.set_page_config(page_title="AMLS v4.5 Ultimate", layout="wide", page_icon="🚀")
st.title("🚀 AMLS v4.5 (세윤's Ultimate Edition)")
st.markdown("""
**휩쏘를 방어하고 멘탈을 지키는 진화형 퀀트 대시보드입니다.**
* 🛡️ **VIX 5일 이평선:** 단기 노이즈 필터링 (불필요한 잦은 매매 차단)
* 📉 **세윤's Rule (R2):** TQQQ 15% + QLD 35% (충격 흡수 및 멘탈 방어)
* ⚡ **반도체 모멘텀:** 1개월 10% 급반등 조건 추가 (V자 반등 초입 포착)
""")

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
    
    # 기본 이평선
    df['QQQ_MA50'] = df['QQQ'].rolling(window=50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(window=200).mean()
    df['SMH_MA50'] = df['SMH'].rolling(window=50).mean()
    
    # V4.5 개선 지표
    df['VIX_MA5'] = df['^VIX'].rolling(window=5).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(periods=63)
    df['SMH_1M_Ret'] = df['SMH'].pct_change(periods=21)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    
    # 조기 경보 지표
    df['HYG_IEF_Ratio'] = df['HYG'] / df['IEF']
    df['HYG_IEF_MA50'] = df['HYG_IEF_Ratio'].rolling(window=50).mean()
    df['QQQ_20d_Ret'] = df['QQQ'].pct_change(periods=20)
    df['QQQE_20d_Ret'] = df['QQQE'].pct_change(periods=20)
    
    return df.dropna()

with st.spinner('해외 증시 데이터를 불러오고 V4.5 엔진을 구동 중입니다...'):
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
    1: ("🟢 R1 (대세 강세장)", "풀 배분 가동"),
    2: ("🟡 R2 (경계/조정장)", "세윤's Rule (TQQQ 15% 방어 모드)"),
    3: ("🟠 R3 (대세 하락장)", "안전 자산 대피"),
    4: ("🔴 R4 (패닉장)", "최대 방어")
}

# ==========================================
# 4. 탭 구성
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 시스템 분석관", "🧮 리밸런싱 계산기", "🚨 실전 퀀트 무기"])

# ------------------------------------------
# 탭 1: 시스템 분석관
# ------------------------------------------
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("현재 시장 국면")
        st.info(f"### {regime_info[curr_regime][0]}\n**적용 로직:** {regime_info[curr_regime][1]}")
        if curr_regime != target_regime:
            st.warning(f"⏳ **상태 변경 대기 중:** 시장이 R{target_regime} 조건을 터치했습니다.")
        else:
            st.success("✅ 현재 국면이 안정적으로 유지되고 있습니다.")
            
    with c2:
        st.subheader("V4.5 목표 비중")
        w_df = pd.DataFrame(list(target_weights.items()), columns=['자산', '비중'])
        w_df = w_df[w_df['비중'] > 0].sort_values(by='비중', ascending=False)
        w_df['비중'] = w_df['비중'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(w_df, hide_index=True, use_container_width=True)

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("QQQ 종가 vs 200일선", f"${last_row['QQQ']:.2f}", f"
