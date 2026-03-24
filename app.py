#!/usr/bin/env python3
"""
AMLS V4.5 UI 개선 자동 패치 v3
================================
사용법: app.py와 같은 폴더에 넣고 실행
  python patch_v3.py

적용되는 개선 3가지:
  ① 포트폴리오 NaN 버그 수정
  ② 대시보드에 레짐 변천사 타임라인 추가
  ③ 백테스트에 월별 히트맵 추가
"""
import sys, os, shutil

APP_FILE = "app.py"
if not os.path.exists(APP_FILE):
    print(f"❌ {APP_FILE}을 찾을 수 없습니다.")
    sys.exit(1)

shutil.copy(APP_FILE, APP_FILE + ".backup_v3")
print(f"📦 백업 생성: {APP_FILE}.backup_v3")

with open(APP_FILE, 'r', encoding='utf-8') as f:
    code = f.read()

count = 0

# =====================================================
# PATCH 1: 포트폴리오 NaN 버그 수정
# =====================================================
old_prices = """    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH': current_prices[t] = 1.0
        elif t in rt_prices: current_prices[t] = rt_prices[t]
        elif t in df.columns: current_prices[t] = df[t].iloc[-1]
        else: current_prices[t] = 0.0"""

new_prices = """    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH':
            current_prices[t] = 1.0
        else:
            p = rt_prices.get(t)
            if p is not None and p == p and p > 0:
                current_prices[t] = float(p)
            elif t in df.columns:
                p2 = df[t].iloc[-1]
                current_prices[t] = float(p2) if (p2 is not None and p2 == p2 and p2 > 0) else 0.0
            else:
                current_prices[t] = 0.0"""

if old_prices in code:
    code = code.replace(old_prices, new_prices)
    count += 1
    print("✅ 패치 1 적용: current_prices NaN 방어")
else:
    print("⚠️ 패치 1: 대상 미발견 (이미 적용됨)")

old_vals = """    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}
    total_val_usd = sum(curr_vals.values())"""

new_vals = """    curr_vals = {}
    for a in ASSET_LIST:
        s = float(st.session_state.portfolio[a].get('shares', 0) or 0)
        p = float(current_prices.get(a, 0) or 0)
        v = s * p
        curr_vals[a] = v if v == v else 0.0
    total_val_usd = sum(curr_vals.values())"""

if old_vals in code:
    code = code.replace(old_vals, new_vals)
    count += 1
    print("✅ 패치 2 적용: curr_vals NaN 방어")
else:
    print("⚠️ 패치 2: 대상 미발견 (이미 적용됨)")

# =====================================================
# PATCH 3: 대시보드 - 레짐 변천사 타임라인 추가
# 차트 아래(fig_tqqq 다음)에 레짐 타임라인을 삽입
# =====================================================
# 기존 TQQQ 차트 컨테이너 닫는 부분 뒤에 타임라인 추가
old_tqqq_end = """        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.plotly_chart(fig_tqqq, use_container_width=True)"""

new_tqqq_end = """        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.plotly_chart(fig_tqqq, use_container_width=True)

        # ── 레짐 변천사 타임라인 ──────────────────────────
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        import plotly.express as px
        df_regime_vis = df_recent[['Regime']].copy()
        df_regime_vis['Regime'] = df_regime_vis['Regime'].astype(int)
        r_color_map = {1: main_color, 2: '#D97706', 3: '#DC2626', 4: '#7C3AED'}
        r_label_map = {1: 'R1 Bull', 2: 'R2 Corr', 3: 'R3 Bear', 4: 'R4 Panic'}

        # 구간 블록으로 변환
        blocks = []
        start_i = 0
        for i in range(1, len(df_regime_vis)):
            if df_regime_vis['Regime'].iloc[i] != df_regime_vis['Regime'].iloc[i-1] or i == len(df_regime_vis)-1:
                r = int(df_regime_vis['Regime'].iloc[start_i])
                blocks.append({
                    'Start': df_regime_vis.index[start_i],
                    'End': df_regime_vis.index[i],
                    'Regime': r_label_map.get(r, f'R{r}'),
                    'Color': r_color_map.get(r, '#888'),
                    'Days': (df_regime_vis.index[i] - df_regime_vis.index[start_i]).days
                })
                start_i = i

        if blocks:
            fig_timeline = go.Figure()
            for b in blocks:
                fig_timeline.add_trace(go.Bar(
                    x=[(b['End'] - b['Start']).days],
                    y=['Regime'],
                    orientation='h',
                    base=b['Start'],
                    marker=dict(color=b['Color'], line=dict(width=0)),
                    name=b['Regime'],
                    text=f"{b['Regime']} ({b['Days']}d)",
                    textposition='inside',
                    textfont=dict(family='DM Mono', size=10, color='#FFFFFF'),
                    hovertemplate=f"{b['Regime']}<br>{b['Start'].strftime('%Y-%m-%d')} → {b['End'].strftime('%Y-%m-%d')}<br>{b['Days']}일<extra></extra>",
                    showlegend=False
                ))
            fig_timeline.update_layout(
                height=70,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='DM Mono', color='#9494A0', size=10),
                margin=dict(l=0, r=0, t=0, b=0),
                barmode='stack',
                xaxis=dict(type='date', showgrid=False, showticklabels=True, tickfont=dict(size=9)),
                yaxis=dict(showticklabels=False, showgrid=False),
                bargap=0
            )
            with st.container(border=True):
                st.markdown('<div style="font-family:DM Mono,monospace;font-size:0.57em;color:#9494A0;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:4px;">Regime Timeline</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_timeline, use_container_width=True)"""

if old_tqqq_end in code:
    code = code.replace(old_tqqq_end, new_tqqq_end, 1)
    count += 1
    print("✅ 패치 3 적용: 레짐 변천사 타임라인 추가")
else:
    print("⚠️ 패치 3: 대상 미발견 (코드 구조가 다를 수 있음)")

# =====================================================
# PATCH 4: 백테스트 - 월별 히트맵 추가
# Drawdown 차트 다음에 히트맵 삽입
# =====================================================
old_bt_divider = """                st.divider()
            if st.button("✦ AI 추론 요약 실행", use_container_width=True):"""

new_bt_divider = """                # ── 월별 수익률 히트맵 ──────────────────────────
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                import plotly.express as px
                monthly_v45 = res_df['V4.5'].resample('M').last().pct_change().dropna() * 100
                if len(monthly_v45) > 3:
                    hm_data = pd.DataFrame({
                        'Year': monthly_v45.index.year,
                        'Month': monthly_v45.index.month,
                        'Return': monthly_v45.values
                    })
                    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                    hm_pivot = hm_data.pivot(index='Year', columns='Month', values='Return').fillna(0).round(1)
                    hm_pivot.columns = [month_names[int(c)-1] for c in hm_pivot.columns]

                    fig_hm = go.Figure(data=go.Heatmap(
                        z=hm_pivot.values,
                        x=hm_pivot.columns.tolist(),
                        y=[str(y) for y in hm_pivot.index],
                        text=[[f"{v:+.1f}" for v in row] for row in hm_pivot.values],
                        texttemplate="%{text}",
                        textfont=dict(size=10, family='DM Mono'),
                        colorscale=[[0,'#DC2626'],[0.5,'#FAFAF7'],[1,main_color]],
                        zmid=0, zmin=-15, zmax=15,
                        showscale=True,
                        colorbar=dict(
                            title=dict(text='%', font=dict(size=10, family='DM Mono')),
                            tickfont=dict(size=9, family='DM Mono'),
                            thickness=12, len=0.8
                        )
                    ))
                    fig_hm.update_layout(
                        title=dict(text="Monthly Returns Heatmap (%)", font=dict(family='DM Mono', size=13, color='#4A4A57')),
                        height=max(200, len(hm_pivot) * 36 + 60),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='DM Mono', color='#4A4A57'),
                        margin=dict(l=40, r=20, t=40, b=20),
                        xaxis=dict(side='top', tickfont=dict(size=10)),
                        yaxis=dict(autorange='reversed', tickfont=dict(size=10))
                    )
                    with st.container(border=True):
                        st.plotly_chart(fig_hm, use_container_width=True)

                st.divider()
            if st.button("✦ AI 추론 요약 실행", use_container_width=True):"""

if old_bt_divider in code:
    code = code.replace(old_bt_divider, new_bt_divider, 1)
    count += 1
    print("✅ 패치 4 적용: 백테스트 월별 히트맵 추가")
else:
    print("⚠️ 패치 4: 대상 미발견 (코드 구조가 다를 수 있음)")

# =====================================================
# 저장
# =====================================================
with open(APP_FILE, 'w', encoding='utf-8') as f:
    f.write(code)

print(f"\n🎉 완료! {count}개 패치 적용됨.")
if count < 4:
    print("⚠️ 일부 패치가 적용되지 않았습니다. 코드 구조가 다를 수 있으니 수동으로 확인해주세요.")
else:
    print("✅ 모든 패치 정상 적용. GitHub에 push하세요!")
new_prices = """    current_prices = {}
    for t in ASSET_LIST:
        if t == 'CASH':
            current_prices[t] = 1.0
        else:
            p = rt_prices.get(t)
            if p is not None and p == p and p > 0:
                current_prices[t] = float(p)
            elif t in df.columns:
                p2 = df[t].iloc[-1]
                current_prices[t] = float(p2) if (p2 is not None and p2 == p2 and p2 > 0) else 0.0
            else:
                current_prices[t] = 0.0"""

if old_prices in code:
    code = code.replace(old_prices, new_prices)
    count += 1
    print("✅ 패치 1 적용: current_prices NaN 방어")
else:
    print("⚠️ 패치 1: 대상 미발견 (이미 적용됨)")

old_vals = """    curr_vals = {a: st.session_state.portfolio[a]['shares'] * current_prices[a] for a in ASSET_LIST}
    total_val_usd = sum(curr_vals.values())"""

new_vals = """    curr_vals = {}
    for a in ASSET_LIST:
        s = float(st.session_state.portfolio[a].get('shares', 0) or 0)
        p = float(current_prices.get(a, 0) or 0)
        v = s * p
        curr_vals[a] = v if v == v else 0.0
    total_val_usd = sum(curr_vals.values())"""

if old_vals in code:
    code = code.replace(old_vals, new_vals)
    count += 1
    print("✅ 패치 2 적용: curr_vals NaN 방어")
else:
    print("⚠️ 패치 2: 대상 미발견 (이미 적용됨)")

# =====================================================
# PATCH 3: 대시보드 - 레짐 변천사 타임라인 추가
# 차트 아래(fig_tqqq 다음)에 레짐 타임라인을 삽입
# =====================================================
# 기존 TQQQ 차트 컨테이너 닫는 부분 뒤에 타임라인 추가
old_tqqq_end = """        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.plotly_chart(fig_tqqq, use_container_width=True)"""

new_tqqq_end = """        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.plotly_chart(fig_tqqq, use_container_width=True)

        # ── 레짐 변천사 타임라인 ──────────────────────────
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        import plotly.express as px
        df_regime_vis = df_recent[['Regime']].copy()
        df_regime_vis['Regime'] = df_regime_vis['Regime'].astype(int)
        r_color_map = {1: main_color, 2: '#D97706', 3: '#DC2626', 4: '#7C3AED'}
        r_label_map = {1: 'R1 Bull', 2: 'R2 Corr', 3: 'R3 Bear', 4: 'R4 Panic'}

        # 구간 블록으로 변환
        blocks = []
        start_i = 0
        for i in range(1, len(df_regime_vis)):
            if df_regime_vis['Regime'].iloc[i] != df_regime_vis['Regime'].iloc[i-1] or i == len(df_regime_vis)-1:
                r = int(df_regime_vis['Regime'].iloc[start_i])
                blocks.append({
                    'Start': df_regime_vis.index[start_i],
                    'End': df_regime_vis.index[i],
                    'Regime': r_label_map.get(r, f'R{r}'),
                    'Color': r_color_map.get(r, '#888'),
                    'Days': (df_regime_vis.index[i] - df_regime_vis.index[start_i]).days
                })
                start_i = i

        if blocks:
            fig_timeline = go.Figure()
            for b in blocks:
                fig_timeline.add_trace(go.Bar(
                    x=[(b['End'] - b['Start']).days],
                    y=['Regime'],
                    orientation='h',
                    base=b['Start'],
                    marker=dict(color=b['Color'], line=dict(width=0)),
                    name=b['Regime'],
                    text=f"{b['Regime']} ({b['Days']}d)",
                    textposition='inside',
                    textfont=dict(family='DM Mono', size=10, color='#FFFFFF'),
                    hovertemplate=f"{b['Regime']}<br>{b['Start'].strftime('%Y-%m-%d')} → {b['End'].strftime('%Y-%m-%d')}<br>{b['Days']}일<extra></extra>",
                    showlegend=False
                ))
            fig_timeline.update_layout(
                height=70,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='DM Mono', color='#9494A0', size=10),
                margin=dict(l=0, r=0, t=0, b=0),
                barmode='stack',
                xaxis=dict(type='date', showgrid=False, showticklabels=True, tickfont=dict(size=9)),
                yaxis=dict(showticklabels=False, showgrid=False),
                bargap=0
            )
            with st.container(border=True):
                st.markdown('<div style="font-family:DM Mono,monospace;font-size:0.57em;color:#9494A0;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:4px;">Regime Timeline</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_timeline, use_container_width=True)"""

if old_tqqq_end in code:
    code = code.replace(old_tqqq_end, new_tqqq_end, 1)
    count += 1
    print("✅ 패치 3 적용: 레짐 변천사 타임라인 추가")
else:
    print("⚠️ 패치 3: 대상 미발견 (코드 구조가 다를 수 있음)")

# =====================================================
# PATCH 4: 백테스트 - 월별 히트맵 추가
# Drawdown 차트 다음에 히트맵 삽입
# =====================================================
old_bt_divider = """                st.divider()
            if st.button("✦ AI 추론 요약 실행", use_container_width=True):"""

new_bt_divider = """                # ── 월별 수익률 히트맵 ──────────────────────────
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                import plotly.express as px
                monthly_v45 = res_df['V4.5'].resample('M').last().pct_change().dropna() * 100
                if len(monthly_v45) > 3:
                    hm_data = pd.DataFrame({
                        'Year': monthly_v45.index.year,
                        'Month': monthly_v45.index.month,
                        'Return': monthly_v45.values
                    })
                    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                    hm_pivot = hm_data.pivot(index='Year', columns='Month', values='Return').fillna(0).round(1)
                    hm_pivot.columns = [month_names[int(c)-1] for c in hm_pivot.columns]

                    fig_hm = go.Figure(data=go.Heatmap(
                        z=hm_pivot.values,
                        x=hm_pivot.columns.tolist(),
                        y=[str(y) for y in hm_pivot.index],
                        text=[[f"{v:+.1f}" for v in row] for row in hm_pivot.values],
                        texttemplate="%{text}",
                        textfont=dict(size=10, family='DM Mono'),
                        colorscale=[[0,'#DC2626'],[0.5,'#FAFAF7'],[1,main_color]],
                        zmid=0, zmin=-15, zmax=15,
                        showscale=True,
                        colorbar=dict(
                            title=dict(text='%', font=dict(size=10, family='DM Mono')),
                            tickfont=dict(size=9, family='DM Mono'),
                            thickness=12, len=0.8
                        )
                    ))
                    fig_hm.update_layout(
                        title=dict(text="Monthly Returns Heatmap (%)", font=dict(family='DM Mono', size=13, color='#4A4A57')),
                        height=max(200, len(hm_pivot) * 36 + 60),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='DM Mono', color='#4A4A57'),
                        margin=dict(l=40, r=20, t=40, b=20),
                        xaxis=dict(side='top', tickfont=dict(size=10)),
                        yaxis=dict(autorange='reversed', tickfont=dict(size=10))
                    )
                    with st.container(border=True):
                        st.plotly_chart(fig_hm, use_container_width=True)

                st.divider()
            if st.button("✦ AI 추론 요약 실행", use_container_width=True):"""

if old_bt_divider in code:
    code = code.replace(old_bt_divider, new_bt_divider, 1)
    count += 1
    print("✅ 패치 4 적용: 백테스트 월별 히트맵 추가")
else:
    print("⚠️ 패치 4: 대상 미발견 (코드 구조가 다를 수 있음)")

# =====================================================
# 저장
# =====================================================
with open(APP_FILE, 'w', encoding='utf-8') as f:
    f.write(code)

print(f"\n🎉 완료! {count}개 패치 적용됨.")
if count < 4:
    print("⚠️ 일부 패치가 적용되지 않았습니다. 코드 구조가 다를 수 있으니 수동으로 확인해주세요.")
else:
    print("✅ 모든 패치 정상 적용. GitHub에 push하세요!")
