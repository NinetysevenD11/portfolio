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
# 1. 데이터 수집 및 코어 엔진 (V4 vs V5 Apex)
# ==========================================
# 전문적인 UI 구현을 위해 타이틀과 아이콘 설정
st.set_page_config(page_title="SEYOON AMLS FINANCIAL STRATEGY", layout="wide", page_icon="⚖️", initial_sidebar_state="expanded")

TICKERS = ['QQQ', 'TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'SMH', 'GLD', '^VIX']
ASSET_LIST = ['TQQQ', 'SOXL', 'USD', 'QLD', 'SSO', 'SPY', 'QQQ', 'GLD', 'CASH']

@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=600)
    data = yf.download(TICKERS, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=False)['Close']
    df = pd.DataFrame(index=data.index)
    for t in TICKERS: df[t] = data[t]
    df = df.ffill().bfill()
    # 지표 계산
    df['QQQ_MA50'] = df['QQQ'].rolling(window=50).mean()
    df['QQQ_MA200'] = df['QQQ'].rolling(window=200).mean()
    df['SMH_MA50'] = df['SMH'].rolling(window=50).mean()
    df['SMH_3M_Ret'] = df['SMH'].pct_change(periods=63)
    df['SMH_1M_Ret'] = df['SMH'].pct_change(periods=21)
    df['SMH_RSI'] = ta.rsi(df['SMH'], length=14)
    # 8-Pack 레이더 지표
    df['QQQ_High52'] = df['QQQ'].rolling(window=252).max()
    df['QQQ_DD'] = (df['QQQ'] / df['QQQ_High52']) - 1
    df['QQQ_RSI'] = ta.rsi(df['QQQ'], length=14)
    return df.dropna()

# 비대칭 레짐 전환 함수 (상승 5일 확인, 하락 즉시)
def apply_asymmetric_delay(targets):
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

with st.spinner('📰 데이터 분석 엔진 가동 중...'):
    df = load_data()

# --- 코어 엔진 계산 (V4 vs V5 Apex) ---
last_row = df.iloc[-1]

# V4 타겟 레짐 판단
def get_target_v4(row):
    v, q, m2, m5 = row['^VIX'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
    if v > 40: return 4
    if q < m2: return 3
    if q >= m2 and m5 >= m2 and v < 25: return 1
    return 2
df['Target_V4'] = df.apply(get_target_v4, axis=1)

# V5 Apex 타겟 레짐 판단 (더 엄격한 강세장 기준)
def get_target_v5(row):
    v, q, m2, m5 = row['^VIX'], row['QQQ'], row['QQQ_MA200'], row['QQQ_MA50']
    if v > 40: return 4
    if q < m2: return 3
    # R1 조건 강화: VIX < 20
    if q >= m2 and m5 >= m2 and v < 20: return 1
    return 2
df['Target_V5'] = df.apply(get_target_v5, axis=1)

# 확정 레짐 계산
df['Sig_V4'] = apply_asymmetric_delay(df['Target_V4'])
df['Sig_V5'] = apply_asymmetric_delay(df['Target_V5'])

curr_regime_v4 = int(df.iloc[-1]['Sig_V4'])
curr_regime_v5 = int(df.iloc[-1]['Sig_V5'])

# SOXL 편입 조건 판단 (V5: 모멘텀 조건 OR 결합)
smh_c1 = last_row['SMH'] > last_row['SMH_MA50']
smh_c2_v4 = last_row['SMH_3M_Ret'] > 0.05
smh_c2_v5 = (last_row['SMH_3M_Ret'] > 0.05) or (last_row['SMH_1M_Ret'] > 0.10) # V자 반등 포착
smh_c3 = last_row['SMH_RSI'] > 50

smh_cond_v4 = smh_c1 and smh_c2_v4 and smh_c3
smh_cond_v5 = smh_c1 and smh_c2_v5 and smh_c3

# 비중 설정 함수 (V4 vs V5 Apex)
def get_w_v4(reg, soxl_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if soxl_ok else 'USD'
    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['SSO'], w['GLD'], w['SPY'] = 0.30, 0.20, 0.20, 0.15, 0.10, 0.05
    elif reg == 2: w['QLD'], w['SSO'], w['GLD'], w['USD'], w['QQQ'], w['SPY'] = 0.30, 0.25, 0.25, 0.10, 0.05, 0.05
    elif reg == 3: w['GLD'], w['QQQ'] = 0.50, 0.15 # Cash 생략
    elif reg == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
    return w

def get_w_v5(reg, soxl_ok):
    w = {t: 0.0 for t in ASSET_LIST}
    semi = 'SOXL' if soxl_ok else 'USD'
    # R1: 공격성 극대화 (TQQQ 40%)
    if reg == 1: w['TQQQ'], w[semi], w['QLD'], w['GLD'] = 0.40, 0.30, 0.20, 0.10
    # R2: 수비 강화 (레버리지 싹 제거)
    elif reg == 2: w['QLD'], w['SSO'], w['GLD'], w['QQQ'], w['SPY'] = 0.35, 0.25, 0.25, 0.10, 0.05
    elif reg == 3: w['GLD'], w['QQQ'] = 0.50, 0.15
    elif reg == 4: w['GLD'], w['QQQ'] = 0.50, 0.10
    return w

w_target_v4 = get_w_v4(curr_regime_v4, smh_cond_v4)
w_target_v5 = get_w_v5(curr_regime_v5, smh_cond_v5)

# ==========================================
# 2. 통합 CSS 시스템 (이미지 디자인 정확한 반영)
# ==========================================
sidebar_style = st.sidebar.radio("🎨 UI 테마 선택", ["Light Mode", "Dark Mode"])
is_dark = sidebar_style == "Dark Mode"

# 강조색 (보라색), 성공(초록), 경고(주황/빨강)
ACCENT = "#7C4DFF" if not is_dark else "#9D7BFF" 
GREEN = "#34D399"
RED = "#F87171"

if not is_dark:
    # --- Light Mode CSS ---
    st.markdown(f"""
    <style>
        /* 기본 배경 및 폰트 */
        .stApp {{
            background-color: #F7F8FA;
            color: #2C3E50;
            font-family: 'Pretendard', sans-serif !important;
        }}
        /* 헤더 정리 */
        [data-testid="stHeader"] {{ background-color: transparent !important; }}
        #MainMenu {{ visibility: hidden; }} footer {{ visibility: hidden; }}
        /* 사이드바 */
        [data-testid="stSidebar"] {{ background-color: #FFFFFF; box-shadow: 2px 0 15px rgba(0,0,0,0.03); border: none; }}
        
        /* 💡 이미지 UI 핵심: 디자인 카드 */
        .sc-card {{
            background-color: #FFFFFF;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.05);
            margin-bottom: 25px;
            border: 1px solid rgba(0,0,0,0.01);
        }}
        .sc-card-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding-bottom: 15px; margin-bottom: 20px;
            border-bottom: 1px solid #EEEEEE;
        }}
        .sc-card-title {{
            font-size: 1.25rem; font-weight: 700; color: #1A1A1A; display: flex; align-items: center; gap: 10px;
        }}
        
        /* 국면 상태 박스 */
        .sc-regime-box {{
            background-color: #F8F9FB;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid #EEEEEE;
            margin-bottom: 20px;
        }}
        .sc-regime-label {{ font-size: 0.9rem; color: #7F8C8D; margin-bottom: 5px; }}
        .sc-regime-value {{ font-size: 1.8rem; font-weight: 800; color: {ACCENT}; }}
        
        /* 데이터 행 (List Item) */
        .sc-data-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #F1F1F1;
        }}
        .sc-data-label {{ font-size: 1rem; color: #4F5E71; }}
        .sc-data-value {{ font-weight: 700; color: #1A1A1A; font-family: 'Roboto Mono', monospace; }}
        
        /* 비중 박스 */
        .sc-weight-box {{
            background-color: #F8F9FB;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 1px solid #EEEEEE;
        }}
        .sc-weight-ticker {{ font-size: 1.1rem; font-weight: 700; color: {ACCENT}; margin-bottom: 2px; }}
        .sc-weight-pct {{ font-size: 0.9rem; color: #7F8C8D; }}
        
        /* 성과 테이블 */
        .sc-perf-table {{ width: 100%; border-collapse: collapse; }}
        .sc-perf-th {{ text-align: left; font-size: 0.9rem; color: #7F8C8D; padding: 10px 5px; border-bottom: 1px solid #EEEEEE; }}
        .sc-perf-td {{ padding: 15px 5px; border-bottom: 1px solid #F1F1F1; font-weight: 600; }}
        
        /* 그라데이션 바 */
        .sc-bar-bg {{ background-color: #E0E0E0; border-radius: 10px; height: 10px; width: 100%; position: relative; overflow: hidden; }}
        .sc-bar-fill {{
            background: linear-gradient(90deg, #7C4DFF 0%, #B388FF 100%);
            border-radius: 10px; height: 10px; position: absolute; top: 0; left: 0;
        }}
        
        /* stRadio 커스터마이징 */
        div.row-widget.stRadio > div {{ flex-direction: row; gap: 10px; }}
        div.row-widget.stRadio > div > label {{
            background-color: #FFFFFF; border: 1px solid #DDDDDD; padding: 10px 20px; border-radius: 30px;
            transition: all 0.2s;
        }}
        div.row-widget.stRadio > div > label:hover {{ border-color: {ACCENT}; background-color: #F0EDFF; }}
        div.row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {{
            background-color: {ACCENT}; border-color: {ACCENT}; color: #FFFFFF !important;
            box-shadow: 0 4px 10px rgba(124,77,255,0.3);
        }}
        div.row-widget.stRadio > div > label p {{ margin: 0; font-weight: 600; }}
        
    </style>
    """, unsafe_allow_html=True)
else:
    # --- Dark Mode CSS ---
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: #121212;
            color: #ECF0F1;
            font-family: 'Pretendard', sans-serif !important;
        }}
        [data-testid="stHeader"] {{ background-color: transparent !important; }}
        #MainMenu {{ visibility: hidden; }} footer {{ visibility: hidden; }}
        [data-testid="stSidebar"] {{ background-color: #1E1E1E; box-shadow: 2px 0 15px rgba(0,0,0,0.2); border: none; }}
        
        .sc-card {{
            background-color: #1E1E1E;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.2);
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.01);
        }}
        .sc-card-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding-bottom: 15px; margin-bottom: 20px;
            border-bottom: 1px solid #333333;
        }}
        .sc-card-title {{
            font-size: 1.25rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 10px;
        }}
        
        .sc-regime-box {{
            background-color: #2C2C2C;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid #333333;
            margin-bottom: 20px;
        }}
        .sc-regime-label {{ font-size: 0.9rem; color: #AAAAAA; margin-bottom: 5px; }}
        .sc-regime-value {{ font-size: 1.8rem; font-weight: 800; color: {ACCENT}; }}
        
        .sc-data-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #2A2A2A;
        }}
        .sc-data-label {{ font-size: 1rem; color: #CCCCCC; }}
        .sc-data-value {{ font-weight: 700; color: #FFFFFF; font-family: 'Roboto Mono', monospace; }}
        
        .sc-weight-box {{
            background-color: #2C2C2C;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 1px solid #333333;
        }}
        .sc-weight-ticker {{ font-size: 1.1rem; font-weight: 700; color: {ACCENT}; margin-bottom: 2px; }}
        .sc-weight-pct {{ font-size: 0.9rem; color: #AAAAAA; }}
        
        .sc-perf-table {{ width: 100%; border-collapse: collapse; }}
        .sc-perf-th {{ text-align: left; font-size: 0.9rem; color: #AAAAAA; padding: 10px 5px; border-bottom: 1px solid #333333; }}
        .sc-perf-td {{ padding: 15px 5px; border-bottom: 1px solid #2A2A2A; font-weight: 600; }}
        
        .sc-bar-bg {{ background-color: #333333; border-radius: 10px; height: 10px; width: 100%; position: relative; overflow: hidden; }}
        .sc-bar-fill {{
            background: linear-gradient(90deg, #7C4DFF 0%, #B388FF 100%);
            border-radius: 10px; height: 10px; position: absolute; top: 0; left: 0;
        }}
        
        /* stRadio Dark */
        div.row-widget.stRadio > div > label {{
            background-color: #1E1E1E; border: 1px solid #444444; color: #ECF0F1;
        }}
        div.row-widget.stRadio > div > label:hover {{ border-color: {ACCENT}; background-color: #2C2C2C; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 메인 레이아웃 및 콘텐츠
# ==========================================
# 상단 헤더
st.markdown(f"""
<div style="padding: 10px 0; margin-bottom: 20px; display: flex; align-items: center; gap: 15px;">
    <div style="font-size: 2.5rem;">⚖️</div>
    <div>
        <h1 style="margin: 0; font-family: Georgia, serif; color: {h_color}; font-size: 2.2rem;">SEYOON AMLS FINANCIAL STRATEGY</h1>
        <p style="margin: 0; color: {h_accent}; font-weight: 700; letter-spacing: 1px;">QUANTITATIVE REGIME-SWITCHING JOURNAL</p>
    </div>
</div>
""", unsafe_allow_html=True)

vix_val, vix_ma_val = last_row['^VIX'], last_row['VIX_MA5']
qqq_val, qqq_ma_val = last_row['QQQ'], last_row['QQQ_MA200']
smh_val, smh_ma_val, smh_rsi_val = last_row['SMH'], last_row['SMH_MA50'], last_row['SMH_RSI']

regime_names = {1: "🟢 R1 강세", 2: "🟡 R2 조정", 3: "🟠 R3 하락", 4: "🔴 R4 패닉"}

# --- 1구역: 국면 분석 및 해부 (디자인 카드 적용) ---
c1, c2 = st.columns(2)

with c1:
    st.markdown(f"""
    <div class="sc-card">
        <div class="sc-card-header">
            <div class="sc-card-title">⚖️ 국면 분석 판독기 (V4)</div>
            <div style="font-size: 0.85rem; color: #7F8C8D;">AMLS V4.4 Engine</div>
        </div>
        <div class="sc-regime-box">
            <div class="sc-regime-label">현재 확정 레짐</div>
            <div class="sc-regime-value">{regime_names[curr_regime_v4]}</div>
        </div>
        <div style="font-weight: 700; color: {h_color}; margin-bottom: 10px;">🔍 알고리즘 해부 (V4)</div>
        <div class="sc-data-row">
            <span class="sc-data-label">VIX 지수 (vs 25)</span>
            <span class="sc-data-value">{vix_val:.2f} {"<span style='color:"+GREEN+";'>✔</span>" if vix_val<25 else "<span style='color:"+RED+";'>✕</span>"}</span>
        </div>
        <div class="sc-data-row">
            <span class="sc-data-label">QQQ vs 200일선</span>
            <span class="sc-data-value">${qqq_val:.0f} vs ${qqq_ma_val:.0f} {"<span style='color:"+GREEN+";'>✔</span>" if qqq_val>qqq_ma_val else "<span style='color:"+RED+";'>✕</span>"}</span>
        </div>
        <div class="sc-data-row">
            <span class="sc-data-label">반도체(SMH) RSI (vs 50)</span>
            <span class="sc-data-value">{smh_rsi_val:.1f} {"<span style='color:"+GREEN+";'>✔</span>" if smh_rsi_val>50 else "<span style='color:"+RED+";'>✕</span>"}</span>
        </div>
        <div style="margin-top: 15px; font-size: 0.9rem; color: #7F8C8D; text-align: center;">
            💡 반도체 편입 승인: {"<span style='color:"+GREEN+"; font-weight:700;'>승인</span>" if smh_cond_v4 else "<span style='color:"+RED+"; font-weight:700;'>기각(USD)</span>"}
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="sc-card">
        <div class="sc-card-header">
            <div class="sc-card-title">🚀 AMLS Apex 판독기 (V5)</div>
            <div style="font-size: 0.85rem; color: #7F8C8D;">Apex V5 Engine (Beta)</div>
        </div>
        <div class="sc-regime-box">
            <div class="sc-regime-label">Apex 확정 레짐</div>
            <div class="sc-regime-value" style="color: {RED if curr_regime_v5 >= 3 else ACCENT};">{regime_names[curr_regime_v5]}</div>
        </div>
        <div style="font-weight: 700; color: {h_color}; margin-bottom: 10px;">🔍 Apex 핵심 차별점</div>
        <div class="sc-data-row">
            <span class="sc-data-label">R1 진입 VIX 기준 (강화)</span>
            <span class="sc-data-value">{vix_val:.2f} {"<span style='color:"+GREEN+";'>✔ (<20)</span>" if vix_val<20 else "<span style='color:"+RED+";'>✕ (V4<25)</span>"}</span>
        </div>
        <div class="sc-data-row">
            <span class="sc-data-label">SOXL 모멘텀 조건 (OR결합)</span>
            <span class="sc-data-value">3M>5% {'OK' if smh_c2_v4 else '✕'} or 1M>10% {'OK' if last_row['SMH_1M_Ret']>0.1 else '✕'}</span>
        </div>
        <div class="sc-data-row">
            <span class="sc-data-label">R2 수비 전략 (V5 전용)</span>
            <span class="sc-data-value" style="color: {RED}; font-weight:700;">TQQQ 전량 제거</span>
        </div>
        <div style="margin-top: 15px; font-size: 0.9rem; color: #7F8C8D; text-align: center;">
            💡 Apex 반도체 편입: {"<span style='color:"+GREEN+"; font-weight:700;'>승인</span>" if smh_cond_v5 else "<span style='color:"+RED+"; font-weight:700;'>기각(USD)</span>"}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 2구역: 목표 비중 비교 (이미지 스타일 비중 박스) ---
st.markdown("<h3 style='margin-bottom: 20px;'>⚖️ 목표 비중 비교 (V4 vs V5 Apex)</h3>", unsafe_allow_html=True)

w_col1, w_col2 = st.columns(2)

def render_weights(weights, title, subtitle):
    sorted_w = sorted([item for item in weights.items() if item[1] > 0], key=lambda x: x[1], reverse=True)
    cols_html = ""
    # 4열 배치
    for i in range(0, len(sorted_w), 4):
        cols_html += "<div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px;'>"
        for j in range(4):
            if i + j < len(sorted_w):
                ticker, pct = sorted_w[i+j]
                cols_html += f"""
                <div class="sc-weight-box">
                    <div class="sc-weight-ticker">{ticker}</div>
                    <div class="sc-weight-pct">{pct*100:.0f}%</div>
                </div>
                """
            else:
                cols_html += "<div></div>" # 빈칸 채우기
        cols_html += "</div>"
        
    return f"""
    <div class="sc-card">
        <div class="sc-card-header">
            <div class="sc-card-title">🛒 {title}</div>
            <div style="font-size: 0.85rem; color: #7F8C8D;">{subtitle}</div>
        </div>
        {cols_html}
    </div>
    """

with w_col1:
    st.markdown(render_weights(w_target_v4, "V4 목표 비중", f"AMLS V4 (Regime {curr_regime_v4})"), unsafe_allow_html=True)

with w_col2:
    st.markdown(render_weights(w_target_v5, "Apex V5 목표 비중", f"Apex V5 (Regime {curr_regime_v5})"), unsafe_allow_html=True)

# --- 3구역: 백테스트 성과 요약 (이미지 스타일 테이블 & 그라데이션 바) ---
st.markdown("<h3 style='margin-bottom: 20px;'>📈 백테스트 핵심 성과 요약</h3>", unsafe_allow_html=True)

# 그라데이션 바 HTML 생성 함수
def get_bar_html(value, max_value):
    pct = (value / max_value) * 100
    return f"""
    <div style="display: flex; align-items: center; gap: 10px;">
        <div class="sc-bar-bg"><div class="sc-bar-fill" style="width: {pct}%;"></div></div>
        <div style="font-size: 0.9rem; color: #7F8C8D; width: 40px; text-align: right;">{value}x</div>
    </div>
    """

st.markdown(f"""
<div class="sc-card">
    <div class="sc-card-header">
        <div class="sc-card-title">📊 기간 성과 비교</div>
        <div style="font-size: 0.85rem; color: #7F8C8D;">2018.01 ~ Current</div>
    </div>
    <table class="sc-perf-table">
        <thead>
            <tr>
                <th class="sc-perf-th">전략명</th>
                <th class="sc-perf-th">최종 수익률 (배수)</th>
                <th class="sc-perf-th">CAGR</th>
                <th class="sc-perf-th">MDD (최대낙폭)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="sc-perf-td" style="color: {ACCENT}; font-weight:700;">AMLS Apex (V5)</td>
                <td class="sc-perf-td">{get_bar_html(8.41, 10)}</td> <td class="sc-perf-td" style="color: {GREEN};">35.2%</td>
                <td class="sc-perf-td" style="color: {RED};">-33.1%</td>
            </tr>
            <tr>
                <td class="sc-perf-td">기존 V4.4</td>
                <td class="sc-perf-td">{get_bar_html(5.82, 10)}</td> <td class="sc-perf-td">28.7%</td>
                <td class="sc-perf-td">-31.5%</td>
            </tr>
            <tr>
                <td class="sc-perf-td" style="color: #7F8C8D;">QQQ (Buy&Hold)</td>
                <td class="sc-perf-td">{get_bar_html(2.71, 10)}</td> <td class="sc-perf-td">17.1%</td>
                <td class="sc-perf-td">-35.1%</td>
            </tr>
        </tbody>
    </table>
    <div style="margin-top: 20px; font-size: 0.85rem; color: #7F8C8D; text-align: center;">
        ※ 성과 데이터는 예시이며, 실제 백테스트 엔진 가동 시 업데이트됩니다.
    </div>
</div>
""", unsafe_allow_html=True)


# --- 4구역: 8-Pack 레이더 (Home에는 요약만 배치) ---
st.markdown("<h3 style='margin-bottom: 20px;'>🍫 8-Pack 시장 심리 레이더 (요약)</h3>", unsafe_allow_html=True)

df_view = df.iloc[-120:]

radar_layout = dict(height=180, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=text_main))

r_col1, r_col2, r_col3, r_col4 = st.columns(4)

with r_col1:
    st.markdown("##### 1. 스마트 DCA (RSI)")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_RSI'], line=dict(color=ACCENT, width=2)))
    fig1.add_hline(y=70, line_dash='dash', line_color=RED)
    fig1.add_hline(y=30, line_dash='dash', line_color=GREEN)
    fig1.update_layout(**radar_layout, yaxis=dict(range=[10, 90], showticklabels=False), xaxis=dict(showticklabels=False))
    st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

with r_col2:
    st.markdown("##### 2. 멘탈 방어 ( Drawdown)")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_view.index, y=df_view['QQQ_DD'], fill='tozeroy', line=dict(color=RED, width=1)))
    fig2.update_layout(**radar_layout, yaxis=dict(tickformat='.0%', showticklabels=False), xaxis=dict(showticklabels=False))
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
    
with r_col3:
    st.markdown("##### 3. 변동성 (VIX선)")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df_view.index, y=df_view['^VIX'], line=dict(color=text_main, width=2)))
    fig3.update_layout(**radar_layout, yaxis=dict(showticklabels=False), xaxis=dict(showticklabels=False))
    st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

with r_col4:
    st.markdown("##### 4. 공포탐욕지수 (추정)")
    # 간단 추정 모델
    fg_score = 100 - vix_val * 2
    st.metric("", f"{fg_score:.0f}", " Neutral")

# 사이드바 하단 정보
gen_headlines, _ = fetch_macro_news()
if st.sidebar.button("🤖 AI 매크로 브리핑 생성"):
    st.sidebar.markdown("---")
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"너는 월스트리트의 헤지펀드 매니저야. 다음 뉴스 헤드라인을 바탕으로 현재 시장의 핵심 위험 요소와 기회 요소를 아주 냉철하게 3줄 요약해.\n\n" + "\n".join(gen_headlines)
        response = model.generate_content(prompt)
        st.sidebar.info(f"📋 **AI 분석 결과:**\n\n{response.text}")
    except:
        st.sidebar.error("Secrets에 API Key를 설정하거나, 뉴스 수신 상태를 확인하세요.")
