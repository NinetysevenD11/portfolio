import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="AMLS 내 포트폴리오 현황", layout="wide")
st.title("💼 AMLS v4 실전 포트폴리오 트래커")
st.markdown("현재 시장의 **AMLS 국면(Regime)**을 파악하고, 내 보유 종목의 **기술적 위치**와 **자산 성장 추이**를 추적합니다.")

# --- 0. AMLS v4 현재 레짐 및 반도체 스위칭 파악 ---
@st.cache_data(ttl=1800) # 30분마다 갱신
def get_market_regime():
    tickers = ['QQQ', '^VIX', 'SMH']
    end_date = datetime.today()
    start_date = end_date - timedelta(days=400) # 200일 이평선 계산을 위해 넉넉히 수집
    
    data = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)['Close'].ffill()
    
    # 지표 계산
    df = pd.DataFrame(index=data.index)
    df['QQQ'] = data['QQQ']
    df['VIX'] = data['^VIX']
    df['SMH'] = data['SMH']
    
    df['QQQ_MA50'] = df['QQQ'].rolling(50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(200).mean()
    
    df['SMH_MA50'] = df['SMH'].rolling(50).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(63)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    
    df = df.dropna()
    today = df.iloc[-1]
    
    # 레짐 판독
    vix, qqq, ma200, ma50 = today['VIX'], today['QQQ'], today['QQQ_MA200'], today['QQQ_MA50']
    
    if vix > 40: regime = 4
    elif qqq < ma200: regime = 3
    elif qqq >= ma200 and ma50 >= ma200 and vix < 25: regime = 1
    else: regime = 2
    
    # 반도체 스위칭 판독
    use_soxl = (today['SMH'] > today['SMH_MA50']) and (today['SMH_3M_Ret'] > 0.05) and (today['SMH_RSI'] > 50)
    semi_target = "SOXL (3배)" if use_soxl else "USD (2배)"
    if regime in [3, 4]: semi_target = "미보유 (안전 자산 대피)"
    elif regime == 2: semi_target = "USD (2배 - 레버리지 축소)"
        
    return regime, vix, qqq, ma200, semi_target, today.name

with st.spinner("시장 국면을 판독 중입니다..."):
    regime, vix, qqq, ma200, semi_target, last_date = get_market_regime()

st.subheader("🧭 0. AMLS v4 시장 레이더")
st.info(f"기준일: **{last_date.strftime('%Y년 %m월 %d일')} 종가**")

r_col1, r_col2, r_col3, r_col4 = st.columns(4)
r_col1.metric("오늘의 국면 (Regime)", f"Regime {regime}")
r_col2.metric("공포 지수 (VIX)", f"{vix:.2f}", "40 초과 시 위험 / 25 미만 시 안정", delta_color="off")
r_col3.metric("QQQ 200일선 이격도", f"{(qqq/ma200 - 1)*100:.2f}%", "양수(+)면 장기 상승 추세")
r_col4.metric("반도체 스위칭 타겟", f"{semi_target}")

st.divider()

# --- 1. 내 포트폴리오 직접 기입 ---
st.subheader("📝 1. 내 포트폴리오 기입란")
st.markdown("보유 중인 종목의 **티커(Ticker)**와 **수량(주)**을 입력하세요. 행을 추가하거나 삭제할 수 있습니다.")

# 기본 세팅값
if 'portfolio' not in st.session_state:
    st.session_state['portfolio'] = pd.DataFrame({
        "티커 (Ticker)": ["TQQQ", "QLD", "QQQ", "GLD"],
        "수량 (Shares)": [100, 50, 0, 20]
    })

# 동적 테이블 (사용자 직접 수정 가능)
edited_df = st.data_editor(
    st.session_state['portfolio'],
    num_rows="dynamic",
    use_container_width=False,
    width=600
)

st.divider()

# 데이터 처리를 위한 티커 추출
raw_tickers = edited_df["티커 (Ticker)"].dropna().str.upper().tolist()
valid_tickers = [t.strip() for t in raw_tickers if t.strip() != ""]

if valid_tickers:
    with st.spinner("내 종목들의 실시간 기술적 지표와 과거 데이터를 불러오고 있습니다..."):
        # 최근 5년치 데이터 수집 (연별 그래프를 위해)
        start_5y = datetime.today() - timedelta(days=365*6)
        port_data = yf.download(valid_tickers, start=start_5y.strftime('%Y-%m-%d'), progress=False)['Close']
        
        # 티커가 1개일 경우 Series로 반환되는 것을 DataFrame으로 변환
        if isinstance(port_data, pd.Series):
            port_data = port_data.to_frame(name=valid_tickers[0])
            
        port_data = port_data.ffill()

        # --- 2. 종목별 기술적 지표 표 ---
        st.subheader("📊 2. 내 종목 기술적 지표 현황")
        st.markdown("AMLS 전략 참고용으로, 각 종목의 **현재가, RSI(14), 30주 이평선(약 150일선) 상회 여부**를 나타냅니다.")
        
        indicator_data = []
        
        for tkr in valid_tickers:
            if tkr in port_data.columns:
                series = port_data[tkr].dropna()
                if len(series) < 150:
                    continue # 상장된지 얼마 안된 종목 스킵
                
                current_price = series.iloc[-1]
                
                # 30주 MA (1주일=5거래일 -> 150일 MA)
                ma_30w = series.rolling(window=150).mean().iloc[-1]
                trend_status = "🟢 위 (상승추세)" if current_price > ma_30w else "🔴 아래 (하락추세)"
                
                # RSI 14
                rsi_14 = ta.rsi(series, length=14).iloc[-1]
                
                indicator_data.append({
                    "종목 (Ticker)": tkr,
                    "현재가 ($)": f"${current_price:.2f}",
                    "현재 RSI (14)": f"{rsi_14:.1f}",
                    "30주 MA ($)": f"${ma_30w:.2f}",
                    "30주 MA 돌파 여부": trend_status
                })
                
        if indicator_data:
            ind_df = pd.DataFrame(indicator_data)
            st.dataframe(ind_df, hide_index=True, use_container_width=True)
        else:
            st.warning("데이터를 충분히 불러올 수 없거나 유효하지 않은 티커입니다.")

        st.divider()

        # --- 3. 자산 변화 수치 그래프 (일별/월별/연별) ---
        st.subheader("📈 3. 내 포트폴리오 가치 추이")
        st.markdown("⚠️ **참고:** 현재 기입한 포트폴리오 수량을 과거에도 *그대로 보유했다고 가정*했을 때의 자산 가치 변화입니다.")

        # 포트폴리오 시계열 가치 계산
        portfolio_value_series = pd.Series(0.0, index=port_data.index)
        current_total_value = 0.0
        
        for index, row in edited_df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            shares = float(row["수량 (Shares)"])
            if tkr in port_data.columns and shares > 0:
                portfolio_value_series += port_data[tkr] * shares
                current_total_value += port_data[tkr].iloc[-1] * shares
                
        portfolio_value_series = portfolio_value_series.dropna()
        
        if current_total_value > 0:
            st.metric("현재 내 포트폴리오 총 평가액", f"${current_total_value:,.2f}")
            
            # 리샘플링 (일별, 월별, 연별)
            # 1) 일별 (최근 3개월)
            daily_df = portfolio_value_series.last('90D')
            
            # 2) 월별 (최근 3년, 월말 기준)
            monthly_df = portfolio_value_series.resample('ME').last().last('1095D')
            
            # 3) 연별 (최근 5년, 연말 기준)
            yearly_df = portfolio_value_series.resample('YE').last()

            tab1, tab2, tab3 = st.tabs(["📉 일별 추이 (최근 3개월)", "📆 월별 추이 (최근 3년)", "📅 연별 추이 (최근 5년)"])

            with tab1:
                fig_daily = go.Figure()
                fig_daily.add_trace(go.Scatter(x=daily_df.index, y=daily_df.values, mode='lines+markers', name='자산 가치', line=dict(color='#3498db', width=2)))
                fig_daily.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)", hovermode="x unified")
                st.plotly_chart(fig_daily, use_container_width=True)

            with tab2:
                fig_monthly = go.Figure()
                fig_monthly.add_trace(go.Bar(x=monthly_df.index.strftime('%Y-%m'), y=monthly_df.values, name='자산 가치', marker_color='#8e44ad'))
                fig_monthly.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)", hovermode="x unified")
                st.plotly_chart(fig_monthly, use_container_width=True)

            with tab3:
                fig_yearly = go.Figure()
                fig_yearly.add_trace(go.Bar(x=yearly_df.index.strftime('%Y'), y=yearly_df.values, name='자산 가치', marker_color='#e74c3c', text=[f"${v:,.0f}" for v in yearly_df.values], textposition='auto'))
                fig_yearly.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)")
                st.plotly_chart(fig_yearly, use_container_width=True)
                
        else:
            st.warning("수량이 입력되지 않았거나 유효하지 않은 포트폴리오입니다.")
else:
    st.info("👆 위 표에 티커와 수량을 기입해 주세요.")
