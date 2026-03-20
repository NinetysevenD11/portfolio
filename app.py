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

# 🤖 Gemini API 연동을 위한 라이브러리
import google.generativeai as genai 

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
* 🚨 **TQQQ 200일선 경보:** QQQ보다 선행하는 레버리지 붕괴 조기 감지
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
tab1, tab2, tab3, tab4 = st.tabs(["📊 시스템 분석관", "🧮 리밸런싱 계산기", "🚨 실전 퀀트 무기", "📰 매크로 뉴스 & AI 요약"])

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
            
        if last_row['TQQQ'] < last_row['TQQQ_MA200'] and last_row['QQQ'] >= last_row['QQQ_MA200']:
            st.error("🚨 **[선행 경보 발동]** QQQ는 아직 200일선 위지만, **TQQQ가 200일선을 이탈했습니다.** 곧 R3로 강등될 위험이 높습니다!")
            
    with c2:
        st.subheader("V4.5 목표 비중")
        w_df = pd.DataFrame(list(target_weights.items()), columns=['자산', '비중'])
        w_df = w_df[w_df['비중'] > 0].sort_values(by='비중', ascending=False)
        w_df['비중'] = w_df['비중'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(w_df, hide_index=True, use_container_width=True)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("QQQ 종가 vs 200선", f"${last_row['QQQ']:.2f}", f"{(last_row['QQQ']/last_row['QQQ_MA200'] - 1)*100:+.2f}%")
    m2.metric("TQQQ 종가 vs 200선", f"${last_row['TQQQ']:.2f}", f"{(last_row['TQQQ']/last_row['TQQQ_MA200'] - 1)*100:+.2f}%", delta_color="inverse")
    m3.metric("VIX (5일 이평선)", f"{last_row['VIX_MA5']:.2f}", f"종가: {last_row['^VIX']:.2f}")
    m4.metric("반도체 1M 수익률", f"{last_row['SMH_1M_Ret']*100:+.2f}%", "SOXL 조건")
    m5.metric("반도체 3M 수익률", f"{last_row['SMH_3M_Ret']*100:+.2f}%", "")

    st.divider()
    st.subheader("📈 QQQ & TQQQ 200일선 모니터링 (조기 경보)")
    
    chart_col1, chart_col2 = st.columns(2)
    
    fig_qqq = go.Figure()
    fig_qqq.add_trace(go.Scatter(x=df.index, y=df['QQQ'], name='QQQ', line=dict(color='black', width=2)))
    fig_qqq.add_trace(go.Scatter(x=df.index, y=df['QQQ_MA200'], name='QQQ 200일선', line=dict(color='red', width=2, dash='dash')))
    
    fig_tqqq = go.Figure()
    fig_tqqq.add_trace(go.Scatter(x=df.index, y=df['TQQQ'], name='TQQQ', line=dict(color='blue', width=2)))
    fig_tqqq.add_trace(go.Scatter(x=df.index, y=df['TQQQ_MA200'], name='TQQQ 200일선', line=dict(color='orange', width=2, dash='dash')))
    
    colors = {1: 'rgba(0, 255, 0, 0.1)', 2: 'rgba(255, 255, 0, 0.1)', 3: 'rgba(255, 165, 0, 0.1)', 4: 'rgba(255, 0, 0, 0.1)'}
    for i in range(1, len(df)):
        if df['Regime'].iloc[i-1] != df['Regime'].iloc[i] or i == 1:
            start_idx = df.index[i]
            curr_r = df['Regime'].iloc[i]
        if i == len(df)-1 or df['Regime'].iloc[i] != df['Regime'].iloc[i+1]:
            fig_qqq.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=0.5, layer="below", line_width=0)
            fig_tqqq.add_vrect(x0=start_idx, x1=df.index[i], fillcolor=colors[curr_r], opacity=0.5, layer="below", line_width=0)
            
    fig_qqq.update_layout(title="[시스템 기준] QQQ vs 200일 이평선", height=350, template='plotly_white', margin=dict(l=0, r=0, t=40, b=0))
    fig_tqqq.update_layout(title="[조기 경보] TQQQ vs 200일 이평선", height=350, template='plotly_white', margin=dict(l=0, r=0, t=40, b=0))
    
    with chart_col1:
        st.plotly_chart(fig_qqq, use_container_width=True)
    with chart_col2:
        st.plotly_chart(fig_tqqq, use_container_width=True)

# ------------------------------------------
# 탭 2: 리밸런싱 계산기
# ------------------------------------------
with tab2:
    st.subheader("💼 내 포트폴리오 리밸런싱 계산기")
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        current_holdings = {}
        total_value = 0
        for asset in ASSET_LIST:
            val = st.number_input(f"{asset} 보유 금액 ($)", min_value=0.0, value=0.0, step=100.0)
            current_holdings[asset] = val
            total_value += val
        
        add_cash = st.number_input("추가 투입할 예수금 ($)", min_value=0.0, value=0.0, step=100.0)
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

# ------------------------------------------
# 탭 3: 실전 퀀트 무기 (선행 지표)
# ------------------------------------------
with tab3:
    st.subheader("🚨 조기 경보 레이더 (선행 지표)")
    r1, r2 = st.columns(2)
    
    with r1:
        st.markdown("#### 1. 채권 스프레드 (HYG/IEF)")
        curr_ratio = last_row['HYG_IEF_Ratio']
        ma50_ratio = last_row['HYG_IEF_MA50']
        
        if curr_ratio < ma50_ratio:
            st.error("🚨 **위험 (Risk-Off):** 스마트머니 이탈 중.")
        else:
            st.success("✅ **안전 (Risk-On):** 자금 흐름 건전.")
            
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_Ratio'].iloc[-200:], name='HYG/IEF 비율', line=dict(color='blue')))
        fig2.add_trace(go.Scatter(x=df.index[-200:], y=df['HYG_IEF_MA50'].iloc[-200:], name='50일 이평선', line=dict(color='orange', dash='dot')))
        fig2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    with r2:
        st.markdown("#### 2. 시장 폭 (가짜 상승 판별)")
        qqq_ret = last_row['QQQ_20d_Ret']
        qqqe_ret = last_row['QQQE_20d_Ret']
        
        if qqq_ret > 0 and qqqe_ret < 0:
            st.warning("⚠️ **가짜 상승 (Divergence):** 소수 대장주만 오르는 중.")
        else:
            st.success("✅ **건전한 상승:** 시장 전체가 오르는 중.")
            
        st.metric("QQQ (시총가중) 20일 수익률", f"{qqq_ret*100:+.2f}%")
        st.metric("QQQE (동일가중) 20일 수익률", f"{qqqe_ret*100:+.2f}%")

# ------------------------------------------
# 탭 4: 매크로 뉴스 & AI 요약 (신규 추가)
# ------------------------------------------
with tab4:
    st.subheader("📰 실시간 뉴스 및 🤖 AI 시장 분위기 요약")
    st.write("구글 뉴스 헤드라인을 바탕으로 현재 시장의 핵심 쟁점을 AI가 요약합니다.")
    
    # 1. 뉴스 데이터 가져오기
    headlines_for_ai = []
    try:
        search_query = urllib.parse.quote("미국증시 OR 연준 OR 나스닥 OR 금리")
        url = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req).read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:15] # 최신 15개
        
        if items:
            for item in items:
                title = item.find('title').text
                headlines_for_ai.append(title)
    except Exception as e:
        st.error(f"뉴스 데이터를 가져오는 중 오류가 발생했습니다: {e}")

    # 2. AI 요약 기능 (Gemini API)
    with st.expander("✨ AI에게 현재 시장 요약 시키기 (클릭하여 열기)", expanded=True):
        st.markdown("**1. 무료 API Key 발급받기:** [Google AI Studio](https://aistudio.google.com/app/apikey)에 접속하여 'Create API key' 버튼을 눌러 키를 복사하세요.")
        
        api_key = st.text_input("🔑 발급받은 Gemini API Key를 입력하세요:", type="password")
        
        if st.button("🚀 헤드라인 요약 실행"):
            if not api_key:
                st.warning("API Key를 먼저 입력해 주세요!")
            elif not headlines_for_ai:
                st.warning("분석할 뉴스 데이터가 없습니다.")
            else:
                try:
                    with st.spinner("AI가 최신 뉴스 15개를 분석 중입니다... 잠시만 기다려주세요."):
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = (
                            "너는 월스트리트의 날카로운 퀀트 애널리스트야. "
                            "다음은 방금 수집된 미국의 증시, 나스닥, 연준, 금리 관련 최신 뉴스 헤드라인 15개야. "
                            "이 헤드라인들을 바탕으로 현재 주식 시장의 전반적인 분위기와 가장 주의해야 할 리스크를 3~4줄로 아주 명확하고 객관적으로 요약해 줘.\n\n"
                            "[뉴스 헤드라인]\n" + "\n".join(headlines_for_ai)
                        )
                        
                        response = model.generate_content(prompt)
                        st.success("✅ AI 분석 완료!")
                        st.info(f"**🤖 AI 애널리스트 요약 리포트:**\n\n{response.text}")
                except Exception as e:
                    st.error(f"AI 분석 중 오류가 발생했습니다. API Key가 정확한지 확인해 주세요. 상세 에러: {e}")

    # 3. 뉴스 원문 리스트 출력
    st.divider()
    st.markdown("#### 📝 최신 뉴스 헤드라인 원문")
    if items:
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            clean_date = pubDate[:-4] if pubDate else ""
            st.markdown(f"- [{title}]({link}) <span style='color:gray; font-size:0.8em;'>({clean_date})</span>", unsafe_allow_html=True)
    else:
        st.write("표시할 뉴스가 없습니다.")
