import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="AMLS 내 포트폴리오 현황", layout="wide")
st.title("💼 AMLS v4 실전 포트폴리오 트래커")
st.markdown("현재 시장의 **AMLS 국면(Regime)**을 파악하고, 내 보유 종목의 **기술적 위치**, **자산 성장 추이**, 그리고 **수량 변경 히스토리**를 추적합니다.")

# --- 0. AMLS v4 현재 레짐 및 반도체 스위칭 파악 ---
@st.cache_data(ttl=1800)
def get_market_regime():
    tickers = ['QQQ', '^VIX', 'SMH']
    end_date = datetime.today()
    start_date = end_date - timedelta(days=400)
    
    data = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)['Close'].ffill()
    
    df = pd.DataFrame(index=data.index)
    df['QQQ'], df['VIX'], df['SMH'] = data['QQQ'], data['^VIX'], data['SMH']
    
    df['QQQ_MA50'] = df['QQQ'].rolling(50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(200).mean()
    df['SMH_MA50'] = df['SMH'].rolling(50).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(63)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    
    df = df.dropna()
    today = df.iloc[-1]
    
    vix, qqq, ma200, ma50 = today['VIX'], today['QQQ'], today['QQQ_MA200'], today['QQQ_MA50']
    
    if vix > 40: regime = 4
    elif qqq < ma200: regime = 3
    elif qqq >= ma200 and ma50 >= ma200 and vix < 25: regime = 1
    else: regime = 2
    
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
st.markdown("보유 중인 종목의 **티커(Ticker)**와 **수량(주)**을 입력하세요. 현금은 티커란에 **CASH** 라고 적고, 수량 란에 **달러($) 금액**을 적으시면 됩니다.")

if 'portfolio' not in st.session_state:
    initial_df = pd.DataFrame({
        "티커 (Ticker)": ["TQQQ", "QLD", "GLD", "CASH"],
        "수량 (주/달러)": [100.0, 50.0, 20.0, 1000.0]
    })
    st.session_state['portfolio'] = initial_df
    st.session_state['last_portfolio'] = initial_df.copy()
    st.session_state['portfolio_history'] = []

edited_df = st.data_editor(
    st.session_state['portfolio'],
    num_rows="dynamic",
    use_container_width=False,
    width=600
)

# 변경 사항 추적 로직
def get_dict_from_df(df):
    d = {}
    for _, row in df.iterrows():
        tkr = str(row["티커 (Ticker)"]).upper().strip()
        if tkr and tkr.lower() != 'nan' and tkr.lower() != 'none':
            try: val = float(row["수량 (주/달러)"])
            except: val = 0.0
            d[tkr] = d.get(tkr, 0.0) + val
    return d

old_dict = get_dict_from_df(st.session_state['last_portfolio'])
new_dict = get_dict_from_df(edited_df)
changes_made = False
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for tkr, old_val in old_dict.items():
    if tkr in new_dict:
        new_val = new_dict[tkr]
        if old_val != new_val:
            st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "수량 변경 🔄", "변경 전": f"{old_val:,.2f}", "변경 후": f"{new_val:,.2f}"})
            changes_made = True
    else:
        st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "항목 삭제 ❌", "변경 전": f"{old_val:,.2f}", "변경 후": "0.00"})
        changes_made = True

for tkr, new_val in new_dict.items():
    if tkr not in old_dict:
        st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "신규 추가 🟢", "변경 전": "0.00", "변경 후": f"{new_val:,.2f}"})
        changes_made = True

if changes_made:
    st.session_state['last_portfolio'] = edited_df.copy()
    st.session_state['portfolio'] = edited_df.copy()

st.divider()

raw_tickers = edited_df["티커 (Ticker)"].dropna().astype(str).str.upper().str.strip().tolist()
valid_stock_tickers = [t for t in raw_tickers if t != "" and t != "CASH"]

cash_amount = 0.0
for index, row in edited_df.iterrows():
    tkr = str(row["티커 (Ticker)"]).upper().strip()
    if tkr == "CASH":
        try: cash_amount += float(row["수량 (주/달러)"])
        except: pass

if valid_stock_tickers or cash_amount > 0:
    with st.spinner("데이터를 분석 중입니다..."):
        start_5y = datetime.today() - timedelta(days=365*6)
        
        # 1. 기술적 지표 표
        indicator_data = []
        port_data = pd.DataFrame()
        
        if valid_stock_tickers:
            downloaded = yf.download(valid_stock_tickers, start=start_5y.strftime('%Y-%m-%d'), progress=False)['Close']
            if isinstance(downloaded, pd.Series): port_data = downloaded.to_frame(name=valid_stock_tickers[0])
            else: port_data = downloaded
            port_data = port_data.ffill()

            st.subheader("📊 2. 내 종목 기술적 지표 현황")
            for tkr in valid_stock_tickers:
                if tkr in port_data.columns:
                    series = port_data[tkr].dropna()
                    if len(series) < 150: continue
                    current_price = series.iloc[-1]
                    ma_30w = series.rolling(window=150).mean().iloc[-1]
                    trend_status = "🟢 위 (상승추세)" if current_price > ma_30w else "🔴 아래 (하락추세)"
                    rsi_14 = ta.rsi(series, length=14).iloc[-1]
                    indicator_data.append({"종목 (Ticker)": tkr, "현재가 ($)": f"${current_price:.2f}", "현재 RSI (14)": f"{rsi_14:.1f}", "30주 MA ($)": f"${ma_30w:.2f}", "30주 MA 돌파 여부": trend_status})
                    
            if indicator_data: st.dataframe(pd.DataFrame(indicator_data), hide_index=True, use_container_width=True)
            else: st.info("입력된 주식/ETF 종목이 없거나 데이터가 부족합니다.")

        st.divider()

        # 2. 자산 가치 시계열 계산 (기입일 필터링 추가)
        st.subheader("📈 3. 내 포트폴리오 가치 추이 및 변화량")
        
        # 사용자가 포트폴리오를 시작한 날짜 선택
        col_date, _ = st.columns([1, 2])
        with col_date:
            port_start_date = st.date_input("📅 포트폴리오 최초 기입일(매수일)", value=datetime.today() - timedelta(days=90))
            
        st.markdown(f"⚠️ **참고:** 설정하신 **{port_start_date.strftime('%Y년 %m월 %d일')}**부터 계산된 실제 내 계좌의 자산 가치 변화입니다.")
        
        benchmark_index = yf.download("QQQ", start=start_5y.strftime('%Y-%m-%d'), progress=False)['Close'].index
        portfolio_value_series = pd.Series(0.0, index=benchmark_index)
        
        for index, row in edited_df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            try: shares = float(row["수량 (주/달러)"])
            except: shares = 0.0
            
            if shares > 0 and tkr in port_data.columns:
                stock_series = port_data[tkr].reindex(benchmark_index).ffill().fillna(0)
                portfolio_value_series += stock_series * shares

        if cash_amount > 0:
            portfolio_value_series += cash_amount
            
        # 시간대(timezone) 제거 후 시작일 기준으로 필터링
        portfolio_value_series.index = portfolio_value_series.index.tz_localize(None)
        portfolio_value_series = portfolio_value_series.loc[pd.to_datetime(port_start_date):].dropna()
        
        if len(portfolio_value_series) > 0:
            val_today = portfolio_value_series.iloc[-1]
            val_start = portfolio_value_series.iloc[0] # 기입일(시작일) 당시의 가치
            
            # 메트릭스 출력 (수익률)
            v_col1, v_col2, v_col3 = st.columns(3)
            v_col1.metric("총 평가액 (현금 포함)", f"${val_today:,.2f}", f"기입일 대비 수익금: ${(val_today - val_start):+,.2f}")
            v_col2.metric("기입일 이후 총 수익률", f"{(val_today/val_start - 1)*100:+.2f}%")
            
            if len(portfolio_value_series) >= 2:
                val_1d = portfolio_value_series.iloc[-2]
                v_col3.metric("전일 대비 변화", f"${(val_today - val_1d):+,.2f}", f"{(val_today/val_1d - 1)*100:+.2f}%")
            else:
                v_col3.metric("전일 대비 변화", "-", "데이터 대기 중")

            # 기입일 기준 데이터로 차트 그리기
            tab1, tab2 = st.tabs(["📉 전체 기간 일별 추이", "📆 월별 수익금 추이"])

            with tab1:
                fig_daily = go.Figure()
                fig_daily.add_trace(go.Scatter(x=portfolio_value_series.index, y=portfolio_value_series.values, mode='lines', name='자산 가치', line=dict(color='#3498db', width=2.5), fill='tozeroy', fillcolor='rgba(52, 152, 219, 0.1)'))
                fig_daily.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)", hovermode="x unified")
                st.plotly_chart(fig_daily, use_container_width=True)

            with tab2:
                if len(portfolio_value_series) > 10:
                    monthly_df = portfolio_value_series.resample('ME').last()
                    fig_monthly = go.Figure()
                    fig_monthly.add_trace(go.Bar(x=monthly_df.index.strftime('%Y-%m'), y=monthly_df.values, name='자산 가치', marker_color='#8e44ad', text=[f"${v:,.0f}" for v in monthly_df.values], textposition='auto'))
                    fig_monthly.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)")
                    st.plotly_chart(fig_monthly, use_container_width=True)
                else:
                    st.info("월별 차트를 생성하기에는 아직 기간이 짧습니다.")
                
        else:
            st.warning("선택하신 기입일 이후의 데이터가 존재하지 않습니다.")
else:
    st.info("👆 위 표에 티커와 수량을 기입해 주세요.")

st.divider()

# --- 4. 포트폴리오 변경 히스토리 ---
st.subheader("🕰️ 4. 포트폴리오 변경 히스토리")
st.markdown("내가 직접 수정한 종목과 수량의 **변경 내역(로그)**이 시간순으로 기록됩니다. (※ 새로고침 시 초기화)")

if st.session_state['portfolio_history']:
    history_df = pd.DataFrame(st.session_state['portfolio_history'])[::-1]
    st.dataframe(history_df, hide_index=True, use_container_width=True)
else:
    st.info("아직 수량이 변경된 내역이 없습니다. 위 표의 숫자를 수정해 보세요!")
