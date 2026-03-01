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
st.markdown("현재 시장의 **AMLS 국면(Regime)**을 파악하고, 내 보유 종목의 **평균 단가 대비 수익률, 기술적 위치**, **자산 성장 추이**를 추적합니다.")

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
    smh, smh_ma50, smh_3m_ret, smh_rsi = today['SMH'], today['SMH_MA50'], today['SMH_3M_Ret'], today['SMH_RSI']

    # 레짐 판독
    if vix > 40: regime = 4
    elif qqq < ma200: regime = 3
    elif qqq >= ma200 and ma50 >= ma200 and vix < 25: regime = 1
    else: regime = 2

    # 반도체 스위칭 판독
    cond1 = smh > smh_ma50
    cond2 = smh_3m_ret > 0.05
    cond3 = smh_rsi > 50
    use_soxl = cond1 and cond2 and cond3
    
    semi_target = "SOXL (3배)" if use_soxl else "USD (2배)"
    if regime in [3, 4]: semi_target = "미보유 (안전 자산 대피)"
    elif regime == 2: semi_target = "USD (2배 - 레버리지 축소)"

    return {
        'regime': regime, 'vix': vix, 'qqq': qqq, 'ma200': ma200, 'ma50': ma50,
        'smh': smh, 'smh_ma50': smh_ma50, 'smh_3m_ret': smh_3m_ret, 'smh_rsi': smh_rsi,
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3,
        'semi_target': semi_target, 'date': today.name
    }

with st.spinner("시장 국면을 정밀 판독 중입니다..."):
    mr = get_market_regime()

st.subheader("🧭 0. AMLS v4 시장 레이더 (상세 지표)")
st.info(f"기준일: **{mr['date'].strftime('%Y년 %m월 %d일')} 종가**")

# 상단 요약 카드
r_col1, r_col2, r_col3, r_col4 = st.columns(4)
r_col1.metric("📌 오늘의 확정 국면", f"Regime {mr['regime']}")
r_col2.metric("📌 공포 지수 (VIX)", f"{mr['vix']:.2f}")
r_col3.metric("📌 QQQ 200일선 이격도", f"{(mr['qqq'] / mr['ma200'] - 1) * 100:.2f}%")
r_col4.metric("📌 반도체 스위칭 타겟", f"{mr['semi_target']}")

st.write("") # 간격 띄우기

# 하단 상세 지표 분석 (예쁜 상태 카드 형태)
col_ind1, col_ind2 = st.columns(2)

with col_ind1:
    st.markdown("##### 🎯 레짐 판단 3대 핵심 지표")
    
    # 1. VIX
    vix_status = "위험 (>40)" if mr['vix'] > 40 else ("경계 (25~40)" if mr['vix'] >= 25 else "안정 (<25)")
    vix_text = f"**1. 공포 지수 (VIX):** 현재 {mr['vix']:.2f} ➔ **{vix_status}**"
    if mr['vix'] > 40: st.error(vix_text, icon="🚨")
    elif mr['vix'] >= 25: st.warning(vix_text, icon="⚠️")
    else: st.success(vix_text, icon="✅")

    # 2. QQQ 추세
    qqq_trend = "상승 추세 (위에 있음)" if mr['qqq'] >= mr['ma200'] else "하락 추세 (아래에 있음)"
    qqq_text = f"**2. 장기 추세:** QQQ(${mr['qqq']:.2f})가 200일선(${mr['ma200']:.2f}) 대비 ➔ **{qqq_trend}**"
    if mr['qqq'] >= mr['ma200']: st.success(qqq_text, icon="✅")
    else: st.error(qqq_text, icon="🚨")

    # 3. QQQ 배열
    qqq_cross = "정배열 (골든 크로스)" if mr['ma50'] >= mr['ma200'] else "역배열 (데드 크로스)"
    cross_text = f"**3. 중기 배열:** 50일선(${mr['ma50']:.2f})이 200일선(${mr['ma200']:.2f}) 대비 ➔ **{qqq_cross}**"
    if mr['ma50'] >= mr['ma200']: st.success(cross_text, icon="✅")
    else: st.error(cross_text, icon="🚨")

with col_ind2:
    st.markdown("##### ⚡ 반도체(SOXL) 진입 3대 모멘텀 지표")
    
    # 1. SMH 단기 추세
    c1_mark = "합격" if mr['cond1'] else "미달"
    c1_text = f"**1. 단기 추세:** SMH(${mr['smh']:.2f}) > 50일선(${mr['smh_ma50']:.2f}) ➔ **{c1_mark}**"
    if mr['cond1']: st.success(c1_text, icon="✅")
    else: st.error(c1_text, icon="❌")

    # 2. SMH 중기 수익률
    c2_mark = "합격" if mr['cond2'] else "미달"
    c2_text = f"**2. 중기 수익률:** 최근 3개월 수익률 ({mr['smh_3m_ret']*100:.2f}%) > +5% ➔ **{c2_mark}**"
    if mr['cond2']: st.success(c2_text, icon="✅")
    else: st.error(c2_text, icon="❌")

    # 3. SMH 모멘텀 강도
    c3_mark = "합격" if mr['cond3'] else "미달"
    c3_text = f"**3. 모멘텀 (RSI):** RSI 14 지수 ({mr['smh_rsi']:.1f}) > 50 ➔ **{c3_mark}**"
    if mr['cond3']: st.success(c3_text, icon="✅")
    else: st.error(c3_text, icon="❌")

st.divider()

# --- 1. 내 포트폴리오 직접 기입 및 시각화 ---
st.subheader("📝 1. 내 포트폴리오 기입란 & 평단가 대비 수익률")
st.markdown("수량과 **평균 단가**를 입력하시면 우측에 비중이, 하단에 **실시간 수익률 현황판**이 표시됩니다. (내역 영구 저장)")

if 'portfolio' not in st.session_state:
    saved_data = load_portfolio_data()
    if saved_data and len(saved_data.get("portfolio", [])) > 0:
        pf_df = pd.DataFrame(saved_data["portfolio"])
        if "평균 단가 ($)" not in pf_df.columns:
            pf_df["평균 단가 ($)"] = 0.0
        st.session_state['portfolio'] = pf_df
        st.session_state['portfolio_history'] = saved_data.get("history", [])
        fd = saved_data.get("first_entry_date")
        st.session_state['first_entry_date'] = datetime.fromisoformat(fd) if fd else None
    else:
        initial_df = pd.DataFrame({
            "티커 (Ticker)": ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "GLD", "CASH"],
            "수량 (주/달러)": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "평균 단가 ($)": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        })
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
            "티커 (Ticker)": st.column_config.TextColumn("티커 (Ticker)"),
            "수량 (주/달러)": st.column_config.NumberColumn("수량", min_value=0.0, format="%.2f"),
            "평균 단가 ($)": st.column_config.NumberColumn("평균 단가 ($)", min_value=0.0, format="%.2f")
        }
    )

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

    if not edited_df.equals(st.session_state['last_portfolio']):
        changes_made = True

    for tkr, old_val in old_dict.items():
        if tkr in new_dict:
            new_val = new_dict[tkr]
            if old_val != new_val:
                st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "수량 변경 🔄", "변경 전": f"{old_val:,.2f}", "변경 후": f"{new_val:,.2f}"})
        else:
            st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "항목 삭제 ❌", "변경 전": f"{old_val:,.2f}", "변경 후": "0.00"})

    for tkr, new_val in new_dict.items():
        if tkr not in old_dict:
            st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "신규 추가 🟢", "변경 전": "0.00", "변경 후": f"{new_val:,.2f}"})
            if st.session_state['first_entry_date'] is None and new_val > 0:
                st.session_state['first_entry_date'] = datetime.now()

    if changes_made:
        st.session_state['last_portfolio'] = edited_df.copy()
        st.session_state['portfolio'] = edited_df.copy()
        save_portfolio_data(edited_df, st.session_state['portfolio_history'], st.session_state['first_entry_date'])

raw_tickers = edited_df["티커 (Ticker)"].dropna().astype(str).str.upper().str.strip().tolist()
valid_stock_tickers = [t for t in raw_tickers if t != "" and t != "CASH" and t.lower() != 'nan']

latest_prices = {}
if valid_stock_tickers:
    try:
        fast_data = yf.download(valid_stock_tickers, period="5d", progress=False)['Close']
        if isinstance(fast_data, pd.Series): latest_prices[valid_stock_tickers[0]] = fast_data.dropna().iloc[-1]
        else:
            for t in valid_stock_tickers:
                if t in fast_data.columns: latest_prices[t] = fast_data[t].dropna().iloc[-1]
    except:
        pass

with col_chart:
    asset_values = {}
    for _, row in edited_df.iterrows():
        tkr = str(row["티커 (Ticker)"]).upper().strip()
        try: shares = float(row["수량 (주/달러)"])
        except: shares = 0.0
        if shares > 0:
            if tkr == "CASH":
                asset_values[tkr] = asset_values.get(tkr, 0) + shares
            elif tkr in latest_prices:
                asset_values[tkr] = asset_values.get(tkr, 0) + (shares * latest_prices[tkr])
                
    total_value = sum(asset_values.values()) if asset_values else 0.0

    if total_value > 0:
        fig_bar = go.Figure()
        palette = ['#e74c3c', '#3498db', '#f1c40f', '#2ecc71', '#9b59b6', '#e67e22', '#1abc9c', '#34495e']
        sorted_assets = sorted(asset_values.items(), key=lambda x: x[1], reverse=True)
        
        for idx, (tkr, val) in enumerate(sorted_assets):
            weight = (val / total_value) * 100
            fig_bar.add_trace(go.Bar(
                y=['내 포트폴리오 비중'], x=[weight], name=tkr, orientation='h',
                text=f"<b>{tkr}</b><br>{weight:.1f}%", textposition='inside', insidetextanchor='middle',
                marker=dict(color=palette[idx % len(palette)], line=dict(color='white', width=1.5)),
                hoverinfo='text', hovertext=f"{tkr}: ${val:,.0f} ({weight:.1f}%)"
            ))

        fig_bar.update_layout(
            barmode='stack', height=200, margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 100]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            showlegend=False,
            title=dict(text=f"총 자산 평가액: <b>${total_value:,.0f}</b>", font=dict(size=18), x=0.5, xanchor='center')
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("수량을 기입하시면 비중 그래프가 나타납니다.")

st.markdown("##### 💵 내 종목별 실시간 수익률 현황")
status_data = []
for _, row in edited_df.iterrows():
    tkr = str(row["티커 (Ticker)"]).upper().strip()
    try: 
        shares = float(row["수량 (주/달러)"])
        avg_price = float(row.get("평균 단가 ($)", 0.0))
    except: 
        shares, avg_price = 0.0, 0.0
        
    if shares > 0:
        if tkr == "CASH":
            status_data.append({"종목": tkr, "보유 수량": f"${shares:,.2f}", "평균 단가": "-", "현재 시장가": "-", "평가액": f"${shares:,.2f}", "수익률 (%)": "0.00%", "수익금 ($)": "$0.00"})
        elif tkr in latest_prices:
            curr_price = latest_prices[tkr]
            total_val = shares * curr_price
            if avg_price > 0:
                ret_pct = ((curr_price - avg_price) / avg_price) * 100
                ret_amt = (curr_price - avg_price) * shares
            else:
                ret_pct, ret_amt = 0.0, 0.0
                
            status_data.append({
                "종목": tkr,
                "보유 수량": f"{shares:,.2f} 주",
                "평균 단가": f"${avg_price:,.2f}",
                "현재 시장가": f"${curr_price:,.2f}",
                "평가액": f"${total_val:,.2f}",
                "수익률 (%)": f"{ret_pct:+.2f}%",
                "수익금 ($)": f"${ret_amt:+,.2f}"
            })

if status_data:
    status_df = pd.DataFrame(status_data)
    def color_returns(val):
        if type(val) == str and ('%' in val or '$+' in val or '$-' in val):
            if '+' in val: return 'color: #2ecc71; font-weight: bold;'
            elif '-' in val and val != '-': return 'color: #e74c3c; font-weight: bold;'
        return ''
    
    st.dataframe(status_df.style.map(color_returns, subset=['수익률 (%)', '수익금 ($)']), hide_index=True, use_container_width=True)

st.divider()

# --- 2 & 3. 하단 데이터 연산부 ---
cash_amount = asset_values.get("CASH", 0.0)
active_stock_tickers = [t for t in valid_stock_tickers if asset_values.get(t, 0) > 0]

if active_stock_tickers or cash_amount > 0:
    with st.spinner("과거 궤적과 기술적 지표를 분석 중입니다..."):
        if st.session_state.get('first_entry_date'):
            chart_start = st.session_state['first_entry_date'] - timedelta(days=1)
        else:
            chart_start = datetime.today() - timedelta(days=365 * 6)

        data_fetch_start = min(chart_start, datetime.today() - timedelta(days=365 * 6))
        indicator_data = []
        port_data = pd.DataFrame()

        if active_stock_tickers:
            downloaded = yf.download(active_stock_tickers, start=data_fetch_start.strftime('%Y-%m-%d'), progress=False)['Close']
            if isinstance(downloaded, pd.Series): port_data = downloaded.to_frame(name=active_stock_tickers[0])
            else: port_data = downloaded
            port_data = port_data.ffill()

            st.subheader("📊 2. 내 종목 장기 기술적 지표 현황")
            for tkr in active_stock_tickers:
                if tkr in port_data.columns:
                    series = port_data[tkr].dropna()
                    if len(series) < 150: continue
                    current_price = series.iloc[-1]
                    ma_30w = series.rolling(window=150).mean().iloc[-1]
                    trend_status = "🟢 위 (장기 상승추세)" if current_price > ma_30w else "🔴 아래 (장기 하락추세)"
                    rsi_14 = ta.rsi(series, length=14).iloc[-1]

                    indicator_data.append({
                        "종목 (Ticker)": tkr,
                        "현재가 ($)": f"${current_price:.2f}",
                        "현재 RSI (14)": f"{rsi_14:.1f}",
                        "30주 MA ($)": f"${ma_30w:.2f}",
                        "30주 MA 돌파 여부": trend_status
                    })

            if indicator_data: st.dataframe(pd.DataFrame(indicator_data), hide_index=True, use_container_width=True)

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

        if not portfolio_value_series.empty and len(portfolio_value_series) > 1:
            val_today = portfolio_value_series.iloc[-1]
            val_1d = portfolio_value_series.iloc[-2] if len(portfolio_value_series) >= 2 else val_today
            val_1w = portfolio_value_series.iloc[-6] if len(portfolio_value_series) >= 6 else val_today
            val_1m = portfolio_value_series.iloc[-22] if len(portfolio_value_series) >= 22 else val_today

            v_col1, v_col2, v_col3 = st.columns(3)
            v_col1.metric("총 평가액 (현금 포함)", f"${val_today:,.2f}", f"전일 대비: ${(val_today - val_1d):+,.2f}")
            v_col2.metric("1주일 전 대비 변화", f"${(val_today - val_1w):+,.2f}", f"{(val_today / val_1w - 1) * 100:+.2f}%" if val_1w else "0.00%")
            v_col3.metric("1개월 전 대비 변화", f"${(val_today - val_1m):+,.2f}", f"{(val_today / val_1m - 1) * 100:+.2f}%" if val_1m else "0.00%")

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
                fig_yearly.add_trace(go.Bar(
                    x=yearly_df.index.strftime('%Y'), y=yearly_df.values,
                    name='자산 가치', marker_color='#e74c3c',
                    text=[f"${v:,.0f}" for v in yearly_df.values], textposition='auto'
                ))
                fig_yearly.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)")
                st.plotly_chart(fig_yearly, use_container_width=True)

st.divider()

# --- 4. 포트폴리오 변경 히스토리 (영구 보존) ---
st.subheader("🕰️ 4. 포트폴리오 변경 히스토리")
if st.session_state['portfolio_history']:
    history_df = pd.DataFrame(st.session_state['portfolio_history'])[::-1]
    st.dataframe(history_df, hide_index=True, use_container_width=True)
else:
    st.info("아직 수량이 변경된 내역이 없습니다. 위 표에서 수량을 수정해 보세요!")
