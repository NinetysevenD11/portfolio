#!/usr/bin/env python3
"""
AMLS V4.5 — 목표 달성률 + NaN 수정 패치
=========================================
app.py와 같은 폴더에서 실행: python patch_goal.py
"""
import shutil, os, sys

FILE = "app.py"
if not os.path.exists(FILE):
    print(f"❌ {FILE} 없음"); sys.exit(1)

shutil.copy(FILE, FILE + ".bak_goal")
print(f"📦 백업: {FILE}.bak_goal")

with open(FILE, "r", encoding="utf-8") as f:
    code = f.read()

n = 0

# ── PATCH 1: NaN 방어 (current_prices) ──
old1 = (
    "    current_prices = {}\n"
    "    for t in ASSET_LIST:\n"
    "        if t == 'CASH': current_prices[t] = 1.0\n"
    "        elif t in rt_prices: current_prices[t] = rt_prices[t]\n"
    "        elif t in df.columns: current_prices[t] = df[t].iloc[-1]\n"
    "        else: current_prices[t] = 0.0"
)
new1 = (
    "    current_prices = {}\n"
    "    for t in ASSET_LIST:\n"
    "        if t == 'CASH':\n"
    "            current_prices[t] = 1.0\n"
    "        else:\n"
    "            _p = rt_prices.get(t)\n"
    "            if _p is not None and _p == _p and _p > 0:\n"
    "                current_prices[t] = float(_p)\n"
    "            elif t in df.columns:\n"
    "                _p2 = df[t].iloc[-1]\n"
    "                current_prices[t] = float(_p2) if (_p2 is not None and _p2 == _p2 and _p2 > 0) else 0.0\n"
    "            else:\n"
    "                current_prices[t] = 0.0"
)
if old1 in code:
    code = code.replace(old1, new1); n += 1; print("✅ 1/4: current_prices NaN 방어")
else:
    print("⚠️ 1/4: 이미 적용됨")

# ── PATCH 2: NaN 방어 (curr_vals) ──
old2 = "    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}\n    total_val_usd = sum(curr_vals.values())"
new2 = (
    "    curr_vals = {}\n"
    "    for a in ASSET_LIST:\n"
    "        _s = float(st.session_state.portfolio[a].get('shares', 0) or 0)\n"
    "        _pr = float(current_prices.get(a, 0) or 0)\n"
    "        _v = _s * _pr\n"
    "        curr_vals[a] = _v if _v == _v else 0.0\n"
    "    total_val_usd = sum(curr_vals.values())"
)
if old2 in code:
    code = code.replace(old2, new2); n += 1; print("✅ 2/4: curr_vals NaN 방어")
else:
    print("⚠️ 2/4: 이미 적용됨")

# ── PATCH 3: goal_amount 초기화 ──
old3 = "sanitize_portfolio()\n\ndef save_portfolio_to_disk():"
new3 = "sanitize_portfolio()\n\nif 'goal_amount' not in st.session_state:\n    st.session_state.goal_amount = 50000.0\n\ndef save_portfolio_to_disk():"
if old3 in code and "'goal_amount'" not in code:
    code = code.replace(old3, new3); n += 1; print("✅ 3/4: goal_amount 초기화")
elif "'goal_amount'" in code:
    print("⚠️ 3/4: 이미 적용됨")
else:
    print("❌ 3/4: 대상 미발견")

# ── PATCH 4: 목표 달성률 UI ──
old4 = '    st.markdown("</div></div>", unsafe_allow_html=True)\n\n    # ── 메인 2패널: 좌(포지션 입력+Quick Orders) + 우(차트+리밸런싱) ─\n    left_pf, right_pf = st.columns([1.1, 2])'

# Build the goal tracker HTML as a proper Python code block
goal_code = r'''    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── 🎯 목표 달성률 시각화 ─────────────────────────────────────
    _goal_col1, _goal_col2 = st.columns([3.5, 1])
    with _goal_col2:
        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        _new_goal = st.number_input(
            "🎯 목표 금액 ($)", value=float(st.session_state.goal_amount),
            min_value=1000.0, step=5000.0, key="goal_input", format="%.0f"
        )
        if _new_goal != st.session_state.goal_amount:
            st.session_state.goal_amount = _new_goal
            st.rerun()

    with _goal_col1:
        _goal = st.session_state.goal_amount
        _pct = min((total_val_usd / _goal) * 100, 100) if _goal > 0 else 0
        _pct_raw = (total_val_usd / _goal) * 100 if _goal > 0 else 0
        _remaining = max(0, _goal - total_val_usd)
        if _pct_raw >= 100:
            _bar_color = "#059669"; _status_text = "🎉 목표 달성!"
        elif _pct_raw >= 75:
            _bar_color = main_color; _status_text = "거의 다 왔습니다"
        elif _pct_raw >= 50:
            _bar_color = "#3B82F6"; _status_text = "절반을 넘었습니다"
        elif _pct_raw >= 25:
            _bar_color = "#D97706"; _status_text = "꾸준히 성장 중"
        else:
            _bar_color = "#9494A0"; _status_text = "여정의 시작"

        _goal_html = (
            f'<div style="background:#FAFAF7;border:1px solid rgba(0,0,0,0.12);border-top:3px solid {_bar_color};padding:18px 22px 16px;margin-bottom:14px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;">'
            f'<div>'
            f'<div style="font-family:DM Mono,monospace;font-size:0.57em;color:#9494A0;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:4px;">Portfolio Goal Tracker</div>'
            f'<div style="font-family:Instrument Serif,serif;font-size:2.2em;font-weight:400;font-style:italic;color:{_bar_color};line-height:1;letter-spacing:-0.5px;">{_pct_raw:.1f}%</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-family:DM Mono,monospace;font-size:0.9em;color:#111118;font-variant-numeric:tabular-nums;">${total_val_usd:,.0f} <span style="color:#9494A0;font-size:0.8em;">/ ${_goal:,.0f}</span></div>'
            f'<div style="font-family:DM Mono,monospace;font-size:0.72em;color:#9494A0;margin-top:2px;">잔여: ${_remaining:,.0f}</div>'
            f'</div></div>'
            f'<div style="position:relative;height:20px;background:rgba(0,0,0,0.06);overflow:hidden;margin-bottom:10px;">'
            f'<div style="height:100%;width:{_pct:.1f}%;background:linear-gradient(90deg,{_bar_color},{_bar_color}99);transition:width 0.6s ease;"></div>'
            f'<div style="position:absolute;left:25%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.12);"></div>'
            f'<div style="position:absolute;left:50%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.15);"></div>'
            f'<div style="position:absolute;left:75%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.12);"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;font-family:DM Mono,monospace;font-size:0.58em;color:#9494A0;margin-bottom:10px;">'
            f'<span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>'
            f'<div style="background:rgba(0,0,0,0.03);border-left:2px solid {_bar_color};padding:6px 12px;font-family:DM Sans,sans-serif;font-size:0.82em;color:#4A4A57;">'
            f'{_status_text}</div></div>'
        )
        st.markdown(apply_theme(_goal_html), unsafe_allow_html=True)

    # ── 메인 2패널: 좌(포지션 입력+Quick Orders) + 우(차트+리밸런싱) ─
    left_pf, right_pf = st.columns([1.1, 2])'''

if old4 in code:
    code = code.replace(old4, goal_code, 1); n += 1; print("✅ 4/4: 목표 달성률 UI 추가")
else:
    print("❌ 4/4: 포트폴리오 패치 대상 미발견")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(code)

print(f"\n{'🎉' if n==4 else '⚠️'} 완료: {n}/4 패치 적용됨")
