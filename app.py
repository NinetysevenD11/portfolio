# ------------------------------------------
# PAGE 1: 시장 분석관 (Home) - HTML 렌더링 오류 수정본
# ------------------------------------------
if page == "📊 시장 분석관 (Home)":
    st.subheader("I. 시장 분석관 (Market Intelligence)")

    # 3열 레이아웃 설정
    c1, c2, c3 = st.columns([1.3, 1.3, 1])

    # 1. 현재 시장 국면 카드
    with c1:
        r_color = "#856404" if curr_regime in [1, 2] else "#8B0000"
        r_bg = "#FFFAEB" if curr_regime in [1, 2] else "#FFECEC"
        r_border = "#FFC107" if curr_regime in [1, 2] else "#8B0000"
        
        regime_html = f"""
        <div style="border: 2px solid #2C2C2C; background-color: #FFFDF7; padding: 20px; border-radius: 8px; min-height: 520px; box-shadow: 4px 4px 0px rgba(0,0,0,0.1);">
            <div style="font-family: Georgia, serif; font-size: 1.4em; font-weight: bold; border-bottom: 2px solid #1A1A1A; padding-bottom: 10px; margin-bottom: 15px;">🏛️ 현재 시장 국면 (REGIME)</div>
            <div style="background-color: {r_bg}; border: 2px solid {r_border}; padding: 15px; border-radius: 6px; text-align: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: {r_color};">{regime_info[curr_regime][0]}</h2>
                <p style="margin: 5px 0 0 0; font-weight: 700; color: #1A1A1A;">전략: {regime_info[curr_regime][1]}</p>
            </div>
            <div style="font-weight: bold; margin-bottom: 5px;">🔍 알고리즘 해부</div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>① VIX 패닉 임계점 (< 40)</span>
                <span style="font-family: monospace; font-weight: bold;">{vix_close:.2f} <span style="color: green;">✅</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>② 장기 지지선 (QQQ > 200MA)</span>
                <span style="font-family: monospace; font-weight: bold;">${qqq_close:.0f} vs ${qqq_ma200:.0f} <span style="color: green;">✅</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>③ 추세 정배열 (50MA ≥ 200MA)</span>
                <span style="font-family: monospace; font-weight: bold;">${qqq_ma50:.0f} vs ${qqq_ma200:.0f} <span style="color: green;">✅</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>④ 노이즈 필터 (5일선 < 25)</span>
                <span style="font-family: monospace; font-weight: bold;">{vix_ma5:.2f} <span style="color: green;">✅</span></span>
            </div>
            <div style="margin-top: auto; background-color: #FFF3CD; padding: 12px; border-radius: 4px; font-size: 0.85em; border-left: 4px solid #FFC107;">
                💡 <b>위원회:</b> 시장이 R1 조건을 터치했으나, 5일 연속 충족 여부를 대기 중입니다.
            </div>
        </div>
        """
        st.markdown(regime_html, unsafe_allow_html=True)

    # 2. 반도체 판독관 카드
    with c2:
        s_color = "#006400" if smh_cond else "#8B0000"
        s_bg = "#F1F8E9" if smh_cond else "#FFF5F5"
        s_title = "🔥 승인: SOXL 편입" if smh_cond else "🛡️ 기각: USD 편입"
        
        soxl_html = f"""
        <div style="border: 2px solid #2C2C2C; background-color: #FFFDF7; padding: 20px; border-radius: 8px; min-height: 520px; box-shadow: 4px 4px 0px rgba(0,0,0,0.1);">
            <div style="font-family: Georgia, serif; font-size: 1.4em; font-weight: bold; border-bottom: 2px solid #1A1A1A; padding-bottom: 10px; margin-bottom: 15px;">💻 반도체(SOXL) 판독관</div>
            <div style="background-color: {s_bg}; border: 2px solid {s_color}; padding: 15px; border-radius: 6px; text-align: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: {s_color};">{s_title}</h2>
                <p style="margin: 5px 0 0 0; font-weight: 700; color: #1A1A1A;">전략: {"3배수 공격적 진입" if smh_cond else "변동성 방어용 2배수 편입"}</p>
            </div>
            <div style="font-weight: bold; margin-bottom: 5px;">🔍 3중 필터 해부</div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>① 정배열 추세 (SMH > 50MA)</span>
                <span style="font-family: monospace; font-weight: bold;">${smh_close:.1f} vs ${smh_ma50:.1f} <span style="color: red;">❌</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>② 모멘텀 (1M>10% or 3M>5%)</span>
                <span style="font-family: monospace; font-weight: bold;">3M {smh_3m*100:.1f}% <span style="color: green;">✅</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #CCC; padding: 12px 0;">
                <span>③ 매수 심리 강도 (RSI > 50)</span>
                <span style="font-family: monospace; font-weight: bold;">{smh_rsi:.1f} <span style="color: red;">❌</span></span>
            </div>
            <div style="margin-top: auto; padding: 12px; font-size: 0.85em; color: #666; border-left: 4px solid #CCC; font-style: italic; background-color: #F8F9FA;">
                ※ SOXL은 극단적 변동성을 수반하므로 위 필터를 모두 통과해야만 편입합니다.
            </div>
        </div>
        """
        st.markdown(soxl_html, unsafe_allow_html=True)

    # 3. 목표 포트폴리오 카드
    with c3:
        w_df = pd.DataFrame(list(target_weights.items()), columns=['ASSET', 'WEIGHT'])
        w_df = w_df[w_df['WEIGHT'] > 0].sort_values(by='WEIGHT', ascending=False)
        
        rows = "".join([f"""
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #EBE4D3; padding: 12px 0;">
                <strong style="color: #1A1A1A;">{r['ASSET']}</strong>
                <span style="font-family: monospace; font-weight: bold; color: #8B0000; font-size: 1.1em;">{r['WEIGHT']*100:.0f}%</span>
            </div>
        """ for _, r in w_df.iterrows()])

        port_html = f"""
        <div style="border: 2px solid #2C2C2C; background-color: #FFFDF7; padding: 20px; border-radius: 8px; min-height: 520px; box-shadow: 4px 4px 0px rgba(0,0,0,0.1);">
            <div style="font-family: Georgia, serif; font-size: 1.4em; font-weight: bold; border-bottom: 2px solid #1A1A1A; padding-bottom: 10px; margin-bottom: 15px;">🛒 V4.5 목표 비중</div>
            <div style="display: flex; justify-content: space-between; border-bottom: 2px solid #1A1A1A; padding-bottom: 5px; font-size: 0.8em; color: #666; font-weight: bold;">
                <span>자산 (TICKER)</span>
                <span>비중 (TARGET)</span>
            </div>
            {rows}
        </div>
        """
        st.markdown(port_html, unsafe_allow_html=True)
