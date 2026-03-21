#!/usr/bin/env python3
"""
AMLS V4.5 포트폴리오 NaN 버그 자동 패치
사용법: 이 파일을 app.py와 같은 폴더에 넣고 실행하세요.
  python patch_portfolio.py
자동으로 app.py를 읽어서 패치하고 저장합니다.
"""
import sys, os, shutil

APP_FILE = "app.py"

if not os.path.exists(APP_FILE):
    print(f"❌ {APP_FILE}을 찾을 수 없습니다. 같은 폴더에 넣어주세요.")
    sys.exit(1)

# 백업
shutil.copy(APP_FILE, APP_FILE + ".backup")
print(f"📦 백업 생성: {APP_FILE}.backup")

with open(APP_FILE, 'r', encoding='utf-8') as f:
    code = f.read()

count = 0

# PATCH 1: current_prices NaN fix
old1 = """    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': current_prices[t] = 1.0
        elif t in rt_prices: current_prices[t] = rt_prices[t]
        elif t in df.columns: current_prices[t] = df[t].iloc[-1]
        else: current_prices[t] = 0.0"""

new1 = """    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': 
            current_prices[t] = 1.0
        elif t in rt_prices and rt_prices[t] and not np.isnan(rt_prices[t]): 
            current_prices[t] = float(rt_prices[t])
        elif t in df.columns and not np.isnan(df[t].iloc[-1]): 
            current_prices[t] = float(df[t].iloc[-1])
        else: 
            current_prices[t] = 0.0"""

if old1 in code:
    code = code.replace(old1, new1)
    count += 1
    print("✅ 패치 1 적용: current_prices NaN 방어")
else:
    print("⚠️ 패치 1 대상을 찾지 못했습니다 (이미 적용되었거나 코드가 다름)")

# PATCH 2: curr_vals NaN fix
old2 = """    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}
    total_val_usd = sum(curr_vals.values())"""

new2 = """    curr_vals = {}
    for a in ASSET_LIST:
        shares = float(st.session_state.portfolio[a].get('shares', 0) or 0)
        price = float(current_prices.get(a, 0) or 0)
        val = shares * price
        curr_vals[a] = val if not np.isnan(val) else 0.0
    total_val_usd = sum(curr_vals.values())"""

if old2 in code:
    code = code.replace(old2, new2)
    count += 1
    print("✅ 패치 2 적용: curr_vals NaN 방어")
else:
    print("⚠️ 패치 2 대상을 찾지 못했습니다 (이미 적용되었거나 코드가 다름)")

with open(APP_FILE, 'w', encoding='utf-8') as f:
    f.write(code)

print(f"\n🎉 완료! {count}개 패치 적용됨. {APP_FILE} 저장 완료.")
if count < 2:
    print("⚠️ 일부 패치가 적용되지 않았습니다. 코드를 직접 확인해주세요.")
