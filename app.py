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

def save_portfolio_data(df, history, first_date, journal_text):
    data = {
        "portfolio": df.to_dict(orient="records"),
        "history": history,
        "first_entry_date": first_date.isoformat() if first_date else None,
        "journal_text": journal_text
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="AMLS 내 포트폴리오 현황", layout="wide")
st.title("💼 AMLS v4 실전 포트폴리오 트래커")
st.markdown("현재 시장의 **AMLS 국면(Regime)**을 파악하고, 내 보유 종목의 **평균 단가 대비 수익률, 리밸런싱 지침**, **자산 성장 추이**를 추적합니다.")

# --- 0. AMLS v4 현재 레짐 및 반도체 스위칭 파악 ---
TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']

def get_target_weights(regime, use_soxl):
    w = {t: 0.0 for t in TICKERS}
    semi = 'SOXL' if use_soxl else 'USD'
    if regime == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['CASH'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif regime == 2: w['QLD'], w['SSO'], w['GLD'], w['QQQ'], w['USD'], w['CASH'] = 0.25, 0.20, 0.20, 0.15, 0.10, 0.10
    elif regime == 3: w['GLD'], w['CASH'], w['QQQ'], w['SPY'] = 0.35, 0.35, 0.20, 0.10
    elif regime == 4: w['GLD'], w['CASH'], w['QQQ'] = 0.50, 0.40, 0.10
    return {k: v for k, v in w.items() if v > 0}

@st.cache_data(ttl=1800)
def get_market_regime():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=400)
    data = yf.download(TICKERS, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)['Close'].ffill()

    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]

    df['QQQ_MA50'] = df['QQQ'].rolling(50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(200).mean()
    df['SMH_MA50'] = df['SMH'].rolling(50).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(63)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)

    df = df.dropna()
    today = df.iloc[-1]

    vix, qqq, ma200, ma50 = today['^VIX'], today['QQQ'], today['QQQ_MA200'], today['QQQ_MA50']
    smh, smh_ma50, smh_3m_ret, smh_rsi = today['SMH'], today['SMH_MA50'], today['SMH_3M_Ret'], today['SMH_RSI']

    if vix > 40: regime = 4
    elif qqq < ma200: regime = 3
    elif qqq >= ma200 and ma50 >= ma200 and vix < 25: regime = 1
    else: regime = 2

    cond1, cond2, cond3 = smh > smh_ma50, smh_3m_ret > 0.05, smh_rsi > 50
    use_soxl = cond1 and cond2 and cond3
    
    target_w = get_target_weights(regime, use_soxl)
    semi_target = "SOXL (3배)" if use_soxl else "USD (2배)"
    if regime in [3, 4]: semi_target = "미보유 (대피)"
    elif regime == 2: semi_target = "USD (2배 - 축소)"

    return {
        'regime': regime, 'vix': vix, 'qqq': qqq, 'ma200': ma200, 'ma50': ma50,
        'smh': smh, 'smh_ma50': smh_ma50, 'smh_3m_ret': smh_3m_ret, 'smh_rsi': smh_rsi,
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3,
        'semi_target': semi_target, 'date': today.name, 'target_weights': target_w,
        'latest_prices': {t: today[t] for t in TICKERS if t != '^VIX'}
    }

with st.spinner("시장 국면을 정밀 판독 중입니다..."):
    mr = get_market_regime()

st.subheader("🧭 0. AMLS v4 시장 레이더 & 리밸런싱 지침")
st.info(f"기준일: **{mr['date'].strftime('%Y년 %m월 %d일')} 종가**")

r_col1, r_col2, r_col3, r_col4 = st.columns(4)
r_col1.metric("📌 오늘의 확정 국면", f"Regime {mr['regime']}")
r_col2.metric("📌 공포 지수 (VIX)", f"{mr['vix']:.2f}")
r_col3.metric("📌 QQQ 200일선 이격도", f"{(mr['qqq'] / mr['ma200'] - 1) * 100:.2f}%")
r_col4.metric("📌 반도체 스위칭 타겟", f"{mr['semi_target']}")

st.write("")

# 상세 지표 카드
col_ind1, col_ind2 = st.columns(2)
with col_ind1:
    st.markdown("##### 🎯 레짐 판단 3대 핵심 지표")
    vix_text = f"**1. VIX:** 현재 {mr['vix']:.2f} ➔ **{'위험 (>40)' if mr['vix'] > 40 else ('경계 (>25)' if mr['vix'] >= 25 else '안정 (<25)')}**"
    if mr['vix'] > 40: st.error(vix_text, icon="🚨")
    elif mr['vix'] >= 25: st.warning(vix_text, icon="⚠️")
    else: st.success(vix_text, icon="✅")
    
    qqq_text = f"**2. 장기 추세:** QQQ(${mr['qqq']:.2f}) vs 200일선(${mr['ma200']:.2f})"
    if mr['qqq'] >= mr['ma200']: st.success(qqq_text + " ➔ **상승 (위)**", icon="✅")
    else: st.error(qqq_text + " ➔ **하락 (아래)**", icon="🚨")
    
    cross_text = f"**3. 배열:** 50일선(${mr['ma50']:.2f}) vs 200일선(${mr['ma200']:.2f})"
    if mr['ma50'] >= mr['ma200']: st.success(cross_text + " ➔ **정배열**", icon="✅")
    else: st.error(cross_text + " ➔ **역배열**", icon="🚨")

with col_ind2:
    st.markdown("##### ⚡ 반도체(SOXL) 진입 모멘텀 지표")
    if mr['cond1']: st.success(f"**1. 단기 추세:** SMH > 50일선 ➔ **합격**", icon="✅")
    else: st.error(f"**1. 단기 추세:** SMH < 50일선 ➔ **미달**", icon="❌")
    
    if mr['cond2']: st.success(f"**2. 수익률:** 최근 3개월 ({mr['smh_3m_ret']*100:.2f}%) ➔ **합격**", icon="✅")
    else: st.error(f"**2. 수익률:** 최근 3개월 ({mr['smh_3m_ret']*100:.2f}%) ➔ **미달**", icon="❌")
    
    if mr['cond3']: st.success(f"**3. 모멘텀:** RSI ({mr['smh_rsi']:.1f}) > 50 ➔ **합격**", icon="✅")
    else: st.error(f"**3. 모멘텀:** RSI ({mr['smh_rsi']:.1f}) < 50 ➔ **미달**", icon="❌")

st.divider()

# --- 1. 내 포트폴리오 직접 기입 및 시각화 ---
st.subheader("📝 1. 내 포트폴리오 기입란 & 수익률/리밸런싱 현황판")
st.markdown("💡 표 안의 숫자를 **더블 클릭**하여 수량과 평단가(소수점 2자리)를 입력하세요.")

if 'init_portfolio' not in st.session_state:
    saved_data = load_portfolio_data()
    if saved_data and len(saved_data.get("portfolio", [])) > 0:
        pf_df = pd.DataFrame(saved_data["portfolio"])
        pf_df["수량 (주/달러)"] = pf_df["수량 (주/달러)"].astype(float)
        pf_df["평균 단가 ($)"] = pf_df["평균 단가 ($)"].astype(float)
        st.session_state['init_portfolio'] = pf_df
        st.session_state['portfolio_history'] = saved_data.get("history", [])
        fd = saved_data.get("first_entry_date")
        st.session_state['first_entry_date'] = datetime.fromisoformat(fd) if fd else None
        st.session_state['journal_text'] = saved_data.get("journal_text", "")
    else:
        initial_df = pd.DataFrame({
            "티커 (Ticker)": ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "GLD", "CASH"],
            "수량 (주/달러)": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "평균 단가 ($)": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        })
        st.session_state['init_portfolio'] = initial_df
        st.session_state['portfolio_history'] = []
        st.session_state['first_entry_date'] = None
        st.session_state['journal_text'] = ""

    st.session_state['last_portfolio'] = st.session_state['init_portfolio'].copy()

col_table, col_chart = st.columns([1, 1.5])

with col_table:
    edited_df = st.data_editor(
        st.session_state['init_portfolio'],
        num_rows="dynamic",
        key="portfolio_editor",
        use_container_width=True,
        column_config={
            "티커 (Ticker)": st.column_config.TextColumn("티커 (Ticker)"),
            "수량 (주/달러)": st.column_config.NumberColumn("수량", min_value=0.0, format="%.2f", step=0.1),
            "평균 단가 ($)": st.column_config.NumberColumn("평균 단가 ($)", min_value=0.0, format="%.2f", step=0.1)
        }
    )

    def get_portfolio_state(df):
        state = {}
        for _, row in df.iterrows():
            tkr = str(row["티커 (Ticker)"]).upper().strip()
            if tkr and tkr.lower() not in ['nan', 'none', '']:
                try: qty = float(row["수량 (주/달러)"])
                except: qty = 0.0
                try: avg_p = float(row["평균 단가 ($)"])
                except: avg_p = 0.0
                if tkr in state:
                    state[tkr]['qty'] += qty
                    state[tkr]['avg_p'] = avg_p
                else:
                    state[tkr] = {'qty': qty, 'avg_p': avg_p}
        return state

    old_state = get_portfolio_state(st.session_state['last_portfolio'])
    new_state = get_portfolio_state(edited_df)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changes_made = False

    if not edited_df.equals(st.session_state['last_portfolio']):
        for tkr, old_val in old_state.items():
            if tkr in new_state:
                new_val = new_state[tkr]
                if old_val['qty'] != new_val['qty']:
                    st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "수량 변경 🔄", "변경 전": f"{old_val['qty']:.2f}", "변경 후": f"{new_val['qty']:.2f}"})
                    changes_made = True
                if old_val['avg_p'] != new_val['avg_p']:
                    st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "평단가 변경 💰", "변경 전": f"${old_val['avg_p']:.2f}", "변경 후": f"${new_val['avg_p']:.2f}"})
                    changes_made = True
            else:
                st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "항목 삭제 ❌", "변경 전": f"{old_val['qty']:.2f}", "변경 후": "삭제됨"})
                changes_made = True

        for tkr, new_val in new_state.items():
            if tkr not in old_state:
                st.session_state['portfolio_history'].append({"변경 일시": now_str, "티커": tkr, "상태": "신규 추가 🟢", "변경 전": "없음", "변경 후": f"{new_val['qty']:.2f}"})
                changes_made = True
                if st.session_state['first_entry_date'] is None and new_val['qty'] > 0:
                    st.session_state['first_entry_date'] = datetime.now()

        if changes_made:
            st.session_state['last_portfolio'] = edited_df.copy()
            save_portfolio_data(edited_df, st.session_state['portfolio_history'], st.session_state['first_entry_date'], st.session_state['journal_text'])

with col_chart:
    asset_values = {}
    total_invested_principal = 0.0 
    
    for _, row in edited_df.iterrows():
        tkr = str(row["티커 (Ticker)"]).upper().strip()
        try: 
            shares = float(row["수량 (주/달러)"])
            avg_price = float(row.get("평균 단가 ($)", 0.0))
        except: 
            shares, avg_price = 0.0, 0.0
            
        if shares > 0:
            if tkr == "CASH":
                asset_values[tkr] = asset_values.get(tkr, 0) + shares
                total_invested_principal += shares
            else:
                curr_price = mr['latest_prices'].get(tkr, 0.0)
                if curr_price > 0:
                    asset_values[tkr] = asset_values.get(tkr, 0) + (shares * curr_price)
                if avg_price > 0:
                    total_invested_principal += (shares * avg_price)
                
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

st.write("")

# --- 리밸런싱 지시표 및 수익률 현황판 ---
st.markdown("##### 💵 종목별 수익률 & 리밸런싱 액션 지침")
st.markdown("현재 평가액과 오늘의 Regime 목표 비중을 비교하여 **부족한 것은 [매수], 넘치는 것은 [매도]**를 지시합니다.")

status_data = []
all_tickers = set([t for t in asset_values.keys()] + list(mr['target_weights'].keys()))

for tkr in all_tickers:
    tkr = tkr.upper()
    my_val = asset_values.get(tkr, 0.0)
    my_weight = (my_val / total_value) * 100 if total_value > 0 else 0.0
    
    shares, avg_price = 0.0, 0.0
    for _, row in edited_df.iterrows():
        if str(row["티커 (Ticker)"]).upper().strip() == tkr:
            try: 
                shares += float(row["수량 (주/달러)"])
                avg_price = float(row.get("평균 단가 ($)", 0.0))
            except: pass
            
    target_w_dec = mr['target_weights'].get(tkr, 0.0)
    target_val = total_value * target_w_dec if total_value > 0 else 0.0
    
    diff_val = target_val - my_val
    if abs(diff_val) < 50: action = "적정 (유지)"
    elif diff_val > 0: action = f"🟢 약 ${diff_val:,.0f} 매수"
    else: action = f"🔴 약 ${abs(diff_val):,.0f} 매도"

    if shares > 0:
        if tkr == "CASH":
            ret_pct, ret_amt = 0.0, 0.0
        else:
            curr_price = mr['latest_prices'].get(tkr, 0.0)
            if avg_price > 0:
                ret_pct = ((curr_price - avg_price) / avg_price) * 100
                ret_amt = (curr_price - avg_price) * shares
            else:
                ret_pct, ret_amt = 0.0, 0.0
    else:
        ret_pct, ret_amt = 0.0, 0.0

    if my_val > 0 or target_w_dec > 0:
        status_data.append({
            "종목": tkr,
            "현재 비중": f"{my_weight:.1f}%",
            "목표 비중": f"{target_w_dec*100:.1f}%",
            "평가액": f"${my_val:,.0f}",
            "목표액": f"${target_val:,.0f}",
            "리밸런싱 액션": action,
            "수익률": f"{ret_pct:+.2f}%" if shares > 0 and tkr != "CASH" else "-",
            "수익금": f"${ret_amt:+,.0f}" if shares > 0 and tkr != "CASH" else "-"
        })

if status_data:
    status_df = pd.DataFrame(status_data).sort_values(by="목표 비중", ascending=False)
    
    def color_status(val):
        if type(val) == str:
            if '매수' in val or '+' in val: return 'color: #2ecc71; font-weight: bold;'
            elif '매도' in val or ('-' in val and val != '-'): return 'color: #e74c3c; font-weight: bold;'
            elif '유지' in val: return 'color: #95a5a6;'
        return ''
    
    st.dataframe(status_df.style.map(color_status, subset=['리밸런싱 액션', '수익률', '수익금']), hide_index=True, use_container_width=True)

st.divider()

# --- 2 & 3. 하단 데이터 연산부 (원금/순수익 분리 차트 및 날짜 선택) ---
if total_value > 0:
    with st.spinner("자산 가치 추이를 계산 중입니다..."):
        st.subheader("📈 2. 포트폴리오 가치 추이 및 순수익")
        
        # 사용자가 추적 시작일(매수일)을 맘대로 수정할 수 있도록 달력 복구
        default_date = st.session_state.get('first_entry_date')
        if default_date is None:
            default_date = datetime.today() - timedelta(days=90)
            
        col_date, _ = st.columns([1, 2])
        with col_date:
            user_start_date = st.date_input("📅 포트폴리오 매수 시작일 (이 날짜부터 차트 생성)", value=default_date)
            # 날짜를 선택하면 그 날짜를 세션 및 JSON에 덮어쓰기
            st.session_state['first_entry_date'] = datetime.combine(user_start_date, datetime.min.time())
            save_portfolio_data(st.session_state['init_portfolio'], st.session_state['portfolio_history'], st.session_state['first_entry_date'], st.session_state['journal_text'])

        v_col1, v_col2, v_col3 = st.columns(3)
        pure_profit = total_value - total_invested_principal
        profit_pct = (pure_profit / total_invested_principal * 100) if total_invested_principal > 0 else 0.0
        
        v_col1.metric("내 평가액 총합", f"${total_value:,.2f}")
        v_col2.metric("내가 넣은 원금 총합", f"${total_invested_principal:,.2f}")
        v_col3.metric("누적 순수익금", f"${pure_profit:+,.2f}", f"{profit_pct:+.2f}% 수익률")

        # 시계열 차트 생성 로직
        chart_start_ts = pd.Timestamp(user_start_date)
        fetch_start = (chart_start_ts - timedelta(days=10)).strftime('%Y-%m-%d') # 여유분 다운로드
        
        try:
            benchmark_index = yf.download("QQQ", start=fetch_start, progress=False)['Close'].index
            portfolio_value_series = pd.Series(0.0, index=benchmark_index)
            principal_series = pd.Series(0.0, index=benchmark_index)

            for _, row in edited_df.iterrows():
                tkr = str(row["티커 (Ticker)"]).upper().strip()
                try: 
                    shares = float(row["수량 (주/달러)"])
                    avg_p = float(row.get("평균 단가 ($)", 0.0))
                except: 
                    shares, avg_p = 0.0, 0.0
                    
                if shares > 0:
                    if tkr == "CASH":
                        portfolio_value_series += shares
                        principal_series += shares
                    else:
                        try:
                            stock_series = yf.download(tkr, start=fetch_start, progress=False)['Close']
                            if not stock_series.empty:
                                if isinstance(stock_series, pd.DataFrame): stock_series = stock_series.iloc[:, 0]
                                stock_series = stock_series.reindex(benchmark_index).ffill().fillna(0)
                                portfolio_value_series += stock_series * shares
                                principal_series += (shares * avg_p)
                        except: pass

            portfolio_value_series = portfolio_value_series.dropna()
            principal_series = principal_series.dropna()
            
            # 선택한 날짜 이후 데이터만 자르기
            portfolio_value_series = portfolio_value_series[portfolio_value_series.index >= chart_start_ts]
            principal_series = principal_series[principal_series.index >= chart_start_ts]

            if len(portfolio_value_series) > 0:
                fig_perf = go.Figure()
                fig_perf.add_trace(go.Scatter(x=portfolio_value_series.index, y=portfolio_value_series.values, mode='lines', name='내 총 자산 (평가액)', line=dict(color='#8e44ad', width=3), fill='tozeroy', fillcolor='rgba(142, 68, 173, 0.1)'))
                fig_perf.add_trace(go.Scatter(x=principal_series.index, y=principal_series.values, mode='lines', name='투입 원금', line=dict(color='#e74c3c', width=2, dash='dash')))
                
                fig_perf.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="달러 ($)", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_perf, use_container_width=True)
            else:
                st.info("선택하신 시작일 이후의 거래 데이터가 없습니다. 날짜를 조금 더 과거로 설정해 보세요.")
        except Exception as e:
            st.error("차트 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
else:
    st.info("👆 위 표에 종목과 평단가를 기입하시면 자산 추이와 순수익이 분석됩니다.")

st.divider()

# --- 4. 매매 일지 및 히스토리 (최하단) ---
st.subheader("📓 3. 나만의 매매 복기 일지 & 히스토리")

col_jnl, col_hist = st.columns([1.5, 1])

with col_jnl:
    st.markdown("오늘 시장을 보며 느낀 점이나 원칙을 어긴 이유, 다짐 등을 자유롭게 기록하세요. (자동 저장됨)")
    def save_journal():
        save_portfolio_data(st.session_state['init_portfolio'], st.session_state['portfolio_history'], st.session_state['first_entry_date'], st.session_state['journal_text'])
        
    st.session_state['journal_text'] = st.text_area("매매 일지 입력란", value=st.session_state.get('journal_text', ''), height=300, on_change=save_journal)

with col_hist:
    st.markdown("자동 수량 변경 내역 (Log)")
    if st.session_state['portfolio_history']:
        history_df = pd.DataFrame(st.session_state['portfolio_history'])[::-1]
        st.dataframe(history_df, hide_index=True, use_container_width=True, height=300)
    else:
        st.info("변경 내역이 없습니다.")
