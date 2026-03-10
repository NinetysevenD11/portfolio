# 수정 사항 2개 (기존 코드에서 찾아 바꾸기)

## 수정 1: 도넛 차트 중앙 텍스트 (100% → 총 평가액)

찾기:
annotations=[dict(text=f"100%", x=0.5, y=0.5, showarrow=False, font=dict(color=TEXT_COLOR, size=16))]

바꾸기:
annotations=[dict(text=f"<b>${total_val_now:,.0f}</b>", x=0.5, y=0.5, showarrow=False, font=dict(color=TEXT_COLOR, size=15))]


## 수정 2: 리밸런싱 액션 (간소화 → 상세 버전)

찾기: (전체 블록)
                        if tkr != "CASH" and cp > 0:
                            shares_to_trade = abs(diff) / cp
                            if shares_to_trade < 1.0: action = "HOLD"
                            elif diff > 0: action = f"BUY {shares_to_trade:.0f}"
                            else: action = f"SELL {shares_to_trade:.0f}"
                        elif tkr == "CASH":
                            if abs(diff) < 50: action = "HOLD"
                            elif diff > 0: action = f"ADD ${diff:,.0f}"
                            else: action = f"WITHDRAW ${abs(diff):,.0f}"
                        else: action = "HOLD"
                        
                        if my_v > 0 or tw > 0: 
                            status_d.append({"TICKER": tkr, "TARGET": f"{tw*100:.1f}%", "ACTUAL": f"{my_w:.1f}%", "ACTION": action})

바꾸기:
                        if tkr != "CASH" and cp > 0:
                            shares_to_trade = abs(diff) / cp
                            krw_amt = abs(diff) * current_usdkrw if current_usdkrw > 0 else 0
                            if shares_to_trade < 1.0:
                                action = "✅ HOLD"
                            elif diff > 0:
                                action = f"🟢 {shares_to_trade:.0f}주 매수 (${diff:,.0f}, ₩{krw_amt:,.0f})"
                            else:
                                action = f"🔴 {shares_to_trade:.0f}주 매도 (${abs(diff):,.0f}, ₩{krw_amt:,.0f})"
                        elif tkr == "CASH":
                            krw_amt = abs(diff) * current_usdkrw if current_usdkrw > 0 else 0
                            if abs(diff) < 50: action = "✅ HOLD"
                            elif diff > 0: action = f"🟢 ${diff:,.0f} 추가 (₩{krw_amt:,.0f})"
                            else: action = f"🔴 ${abs(diff):,.0f} 인출 (₩{krw_amt:,.0f})"
                        else: action = "✅ HOLD"
                        
                        if my_v > 0 or tw > 0: 
                            status_d.append({"TICKER": tkr, "TARGET": f"{tw*100:.1f}%", "ACTUAL": f"{my_w:.1f}%", "TARGET$": f"${tv:,.0f}", "ACTUAL$": f"${my_v:,.0f}", "ACTION": action})


## 수정 3: 리밸런싱 테이블 위에 바 차트 추가

찾기:
                    if status_d:
                        status_df = pd.DataFrame(status_d).sort_values("TARGET", ascending=False)
                        def color_act(val):
                            val_s = str(val)
                            if 'BUY' in val_s or 'ADD' in val_s: return f'color: {C_UP}; font-weight:bold;'
                            elif 'SELL' in val_s or 'WITHDRAW' in val_s: return f'color: {C_DOWN}; font-weight:bold;'
                            return ''
                        st.dataframe(status_df.style.map(color_act, subset=['ACTION']), use_container_width=True, hide_index=True)

바꾸기:
                    if status_d:
                        status_df = pd.DataFrame(status_d).sort_values("TARGET", ascending=False)
                        
                        fig_comp = go.Figure(data=[
                            go.Bar(name='현재 (Actual)', x=list(status_df['TICKER']), y=[float(str(x).replace('%','')) for x in status_df['ACTUAL']], marker_color=C_SAFE),
                            go.Bar(name='목표 (Target)', x=list(status_df['TICKER']), y=[float(str(x).replace('%','')) for x in status_df['TARGET']], marker_color=C_UP)
                        ])
                        cust_bar = THEME_LAYOUT.copy()
                        cust_bar.update(barmode='group', height=220, margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        fig_comp.update_layout(**cust_bar)
                        st.plotly_chart(fig_comp, use_container_width=True)
                        
                        def color_act(val):
                            val_s = str(val)
                            if '매수' in val_s or '추가' in val_s: return f'color: {C_UP}; font-weight:bold;'
                            elif '매도' in val_s or '인출' in val_s: return f'color: {C_DOWN}; font-weight:bold;'
                            return ''
                        st.dataframe(status_df.style.map(color_act, subset=['ACTION']), use_container_width=True, hide_index=True)
