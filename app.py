import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import json
import os
import requests
from io import StringIO
import random

warnings.filterwarnings('ignore')

# =====================================================================
# [0] 시스템 설정 및 데이터 관리 (기존 코드 유지)
# =====================================================================
st.set_page_config(page_title="AMLS 퀀트 포트폴리오", layout="wide", initial_sidebar_state="expanded")

SETTINGS_FILE = "amls_settings_v12.json"
ACCOUNTS_FILE = "amls_multi_accounts.json"
REQUIRED_TICKERS = ["TQQQ", "QLD", "QQQ", "SOXL", "USD", "SSO", "SPY", "GLD", "CASH"]

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"theme": "애플 테마"}

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=4)

def load_accounts_data():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None
    return None

def save_accounts_data(data_dict):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)

if 'settings' not in st.session_state:
    st.session_state['settings'] = load_settings()

if 'accounts' not in st.session_state:
    loaded = load_accounts_data()
    if not loaded:
        loaded = {
            "AMLS v4.4": {  
                "portfolio": [{"티커 (Ticker)": t, "수량 (주/달러)": 0.0, "평균 단가 ($)": 0.0, "매입 환율": 0.0, "태그": "코어"} for t in REQUIRED_TICKERS],
                "history": [], "first_entry_date": None, "journal_text": "", "target_seed": 10000.0, "seed_history": {}, "target_portfolio_value": 100000.0,
                "layout_order": ["🎯 목표 달성률", "📊 계좌 요약", "💼 포트폴리오 & 리밸런싱", "📈 목표 달성률 추이", "📝 매매 일지"]
            }
        }
    st.session_state['accounts'] = loaded

# --- 사이드바 및 네비게이션 설정 ---
st.sidebar.markdown("---")
# (생략: 즐겨찾기 링크, 테마 색상 커스텀, 백업 및 복구 등의 사이드바 기능 코드)

# 🔥 좌측 카테고리
pages = {
    "시스템": [
        st.Page(lambda: st.title("🌐 마켓 터미널"), title="마켓 터미널", icon="🌐"), 
        st.Page(lambda: st.title("🦅 백테스트 엔진"), title="백테스트 엔진", icon="🦅"),
        st.Page(page_ai_analyst, title="AI 시스템 분석관", icon="⚡") # 🔥 핵심: 분석관 독립
    ],
    "설정": [
        st.Page(lambda: st.title("⚙️ 계좌 관리"), title="계좌 관리", icon="⚙️")
    ]
}
pg = st.navigation(pages)
pg.run()
