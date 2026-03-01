import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
import json
import os

warnings.filterwarnings('ignore')

# --- 데이터 영구 보존을 위한 파일 세팅 ---
DATA_FILE = "amls_portfolio_data.json"

def load_portfolio_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def save_portfolio_data(df, history, first_date):
    data = {
        "portfolio": df.to_dict(orient="records"),
        "history": history,
        "first_entry_date": first_date.isoformat() if first_date else None
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="AMLS 내 포트폴리오 현황", layout="wide")
st.title("💼 AMLS v4 실전 포트폴리오 트래커")
st.markdown("현재 시장의 **AMLS 국면(Regime)**을 파악하고, 내 보유 종목의 **비중, 기술적 위치**, **자산 성장 추이**, 그리고 **수량 변경 히스토리**를 추적합니다.")

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
st.info("기준일: **{} 종가**".format(last_date.strftime('%Y년 %m월 %d일')))

r_col1, r_col2, r_col3, r_col4 = st.columns(4)
r_col1.metric("오늘의 국면 (Regime)", "Regime {}".format(regime))
r_col2.metric("공포 지수 (VIX)", "{:.2f}".format(vix), "40 초과 시 위험 / 25 미만 시 안정", delta_color="off")
r_col3.metric("QQQ 200일선 이격도", "{:.2f}%".format((qqq / ma200 - 1) * 100), "양수(+)면 장기 상승 추세")
r_col4.metric("반도체 스위칭 타겟", "{}".format(semi_target))

st.divider()

# --- 1. 내 포트폴리오 직접 기입 및 시각화 ---
st.subheader("📝 1. 내 포트폴리오 기입란 & 비중")
st.markdown("티커와 수량을 수정하시면 **히스토리가 영구 저장**되며, 우측에 **현재 가치 기준 포트폴리오 비중**이 실시간으로 표시됩니다.")

# 세션 상태 초기화 및 데이터 로드
if 'portfolio' not in st.session_state:
    saved_data = load_portfolio_data()
    if saved_data:
        st.session_state['portfolio'] = pd.DataFrame(saved_data["portfolio"])
        st.session_state['portfolio_history'] = saved_data.get("history", [])
        fd = saved_data.get("first_entry_date")
        st.session_state['first_entry_date'] = datetime.fromisoformat(fd) if fd else None
    else:
        initial_df = pd.DataFrame({"티커 (Ticker)": ["TQQQ", "QLD", "GLD", "CASH"], "수량 (주/달러)": [100.0, 50.0, 20.0, 1000.0]})
        st.session_state['portfolio'] = initial_df
        st.session_state['portfolio_history'] = []
        st.session_state['first_entry_date'] = None

    st.session_state['last_portfolio'] = st.session_state['portfolio'].copy()

col_table, col_chart = st.columns([1, 1.5])

with col_table:
    edited_df = st.data_editor(
        st.session_state['portfolio'],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "티커 (Ticker)": st.column_config.TextColumn("티커 (Ticker)", help="예: TQQQ, QLD, GLD, CASH"),
            "수량 (주/달러)": st.column_config.NumberColumn("수량 (주/달러)", min_value=0, format="%.2f")
        }
    )

    # 변경 사항 추적 및 영구 저장 로직
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
                st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "수량 변경 🔄", "변경 전": "{:,.2f}".format(old_val), "변경 후": "{:,.2f}".format(new_val)})
                changes_made = True
        else:
            st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "항목 삭제 ❌", "변경 전": "{:,.2f}".format(old_val), "변경 후": "0.00"})
            changes_made = True

    for tkr, new_val in new_dict.items():
        if tkr not in old_dict:
            st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "신규 추가 🟢", "변경 전": "0.00", "변경 후": "{:,.2f}".format(new_val)})
            changes_made = True
            if st.session_state['first_entry_date'] is None:
                st.session_state['first_entry_date'] = datetime.now()

    if changes_made:
        st.session_state['last_portfolio'] = edited_df.copy()
        st.session_state['portfolio'] = edited_df.copy()
        save_portfolio_data(edited_df, st.session_state['portfolio_history'], st.session_state['first_entry_date'])

with col_chart:
    # 차트용 최신 가격 조회 및 비중 계산
    raw_tickers = edited_df["티커 (Ticker)"].dropna().astype(str).str.upper().str.strip().tolist()
    valid_stock_tickers = [t for t in raw_tickers if t != "" and t != "CASH" and t.lower() != 'nan']
    
    asset_values = {}
    total_value = 0.0
    
    if valid_stock_tickers:
        try:
            fast_data = yf.download(valid_stock_tickers, period="5d", progress=False)['Close']
            latest_prices = {}
            if isinstance(fast_data, pd.Series): latest_prices[valid_stock_tickers[0]] = fast_data.dropna().iloc[-1]
            else:
                for t in valid_stock_tickers:
                    if t in fast_data.columns: latest_prices[t] = fast_data[t].dropna().iloc[-1]
                    
            for _, row in edited_df.iterrows():
                tkr = str(row["티커 (Ticker)"]).upper().strip()
                try: shares = float(row["수량 (주/달러)"])
                except: shares = 0.0
                if shares > 0:
                    if tkr == "CASH":
                        asset_values[tkr] = asset_values.get(tkr, 0) + shares
                    elif tkr in latest_prices:
                        asset_values[tkr] = asset_values.get(tkr, 0) + (shares * latest_prices[tkr])
        except:
            pass
            
    # 현금만 있거나 예외 처리
    if not asset_values:
        for _, row in edited_df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            if tkr == "CASH":
                try: asset_values["CASH"] = asset_values.get("CASH", 0) + float(row["수량 (주/달러)"])
                except: pass

    if asset_values:
        total_value = sum(asset_values.values())
        fig_bar = go.Figure()
        
        # 색상 팔레트
        palette = ['#e74c3c', '#3498db', '#f1c40f', '#2ecc71', '#9b59b6', '#e67e22', '#1abc9c', '#34495e']
        sorted_assets = sorted(asset_values.items(), key=lambda x: x[1], reverse=True)
        
        for idx, (tkr, val) in enumerate(sorted_assets):
            weight = (val / total_value) * 100
            fig_bar.add_trace(go.Bar(
                y=['내 포트폴리오 비중'],
                x=[weight],
                name=tkr,
                orientation='h',
                text=f"<b>{tkr}</b><br>{weight:.1f}%",
                textposition='inside',
                insidetextanchor='middle',
                marker=dict(color=palette[idx % len(palette)], line=dict(color='white', width=1.5)),
                hoverinfo='text',
                hovertext=f"{tkr}: ${val:,.0f} ({weight:.1f}%)"
            ))

        fig_bar.update_layout(
            barmode='stack',
            height=200,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 100]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            showlegend=False,
            title=dict(text=f"총 자산 평가액: <b>${total_value:,.0f}</b>", font=dict(size=18), x=0.5, xanchor='center')
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("종목 수량을 입력하시면 비중 그래프가 나타납니다.")

st.divider()

# --- 2 & 3. 하단 데이터 연산부 ---
cash_amount = asset_values.get("CASH", 0.0)

if valid_stock_tickers or cash_amount > 0:
    with st.spinner("과거 궤적과 기술적 지표를 분석 중입니다..."):
        if st.session_state.get('first_entry_date'):
            chart_start = st.session_state['first_entry_date'] - timedelta(days=1)
        else:
            chart_start = datetime.today() - timedelta(days=365 * 6)

        data_fetch_start = min(chart_start, datetime.today() - timedelta(days=365 * 6))
        indicator_data = []
        port_data = pd.DataFrame()

        if valid_stock_tickers:
            downloaded = yf.download(valid_stock_tickers, start=data_fetch_start.strftime('%Y-%m-%d'), progress=False)['Close']
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

                    indicator_data.append({
                        "종목 (Ticker)": tkr,
                        "현재가 ($)": "${:.2f}".format(current_price),
                        "현재 RSI (14)": "{:.1f}".format(rsi_14),
                        "30주 MA ($)": "${:.2f}".format(ma_30w),
                        "30주 MA 돌파 여부": trend_status
                    })

            if indicator_data: st.dataframe(pd.DataFrame(indicator_data), hide_index=True, use_container_width=True)
            else: st.info("입력된 주식/ETF 종목이 없거나 데이터가 부족합니다.")

        st.divider()

        st.subheader("📈 3. 내 포트폴리오 가치 추이 및 변화량")
        benchmark_index = yf.download("QQQ", start=data_fetch_start.strftime('%Y-%m-%d'), progress=False)['Close'].index
        portfolio_value_series = pd.Series(0.0, index=benchmark_index)

        for _, row in edited_df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            try: shares = float(row["수량 (주/달러)"])
            except: shares = 0.0
            if shares > 0 and tkr in port_data.columns:
                stock_series = port_data[tkr].reindex(benchmark_index).ffill().fillna(0)
                portfolio_value_series += stock_series * shares

        if cash_amount > 0:
            portfolio_value_series += cash_amount

        portfolio_value_series = portfolio_value_series.dropna()

        if st.session_state.get('first_entry_date'):
            chart_start_ts = pd.Timestamp(st.session_state['first_entry_date'].date())
            portfolio_value_series = portfolio_value_series[portfolio_value_series.index >= chart_start_ts]

        if not portfolio_value_series.empty:
            val_today = portfolio_value_series.iloc[-1]
            val_1d = portfolio_value_series.iloc[-2] if len(portfolio_value_series) >= 2 else val_today
            val_1w = portfolio_value_series.iloc[-6] if len(portfolio_value_series) >= 6 else val_today
            val_1m = portfolio_value_series.iloc[-22] if len(portfolio_value_series) >= 22 else val_today

            v_col1, v_col2, v_col3 = st.columns(3)
            v_col1.metric("총 평가액 (현금 포함)", "${:,.2f}".format(val_today), "전일 대비: ${:+,.2f}".format(val_today - val_1d))
            v_col2.metric("1주일 전 대비 변화", "${:+,.2f}".format(val_today - val_1w), "{:+.2f}%".format((val_today / val_1w - 1) * 100))
            v_col3.metric("1개월 전 대비 변화", "${:+,.2f}".format(val_today - val_1m), "{:+.2f}%".format((val_today / val_1m - 1) * 100))

            daily_df = portfolio_value_series.last('90D')
            monthly_df = portfolio_value_series.resample('ME').last().last('1095D')
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
                fig_yearly.add_trace(go.Bar(x=yearly_df.index.strftime('%Y'), y=yearly_df.values, name='자산 가치', marker_color='#e74c3c', text=["${:,.0f}".format(v) for v in yearly_df.values], textposition='auto'))
                fig_yearly.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)")
                st.plotly_chart(fig_yearly, use_container_width=True)
        else:
            st.info("선택한 기간에 데이터가 부족합니다.")

st.divider()

# --- 4. 포트폴리오 변경 히스토리 (영구 보존) ---
st.subheader("🕰️ 4. 포트폴리오 변경 히스토리")
st.markdown("내가 직접 수정한 종목과 수량의 **변경 내역(로그)**이 시간순으로 영구 기록됩니다.")

if st.session_state['portfolio_history']:
    history_df = pd.DataFrame(st.session_state['portfolio_history'])[::-1]
    st.dataframe(history_df, hide_index=True, use_container_width=True)
else:
    st.info("아직 수량이 변경된 내역이 없습니다. 위 표에 종목을 추가해 보세요!")
