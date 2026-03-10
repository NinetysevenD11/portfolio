# 📅 월별 수익률 히트맵 추가 패치
# 현재 app.py에 2곳만 수정하면 됩니다.

# ================================================================
# 변경 1: DEFAULT_LAYOUT에 "📅 월별 히트맵" 추가
# ================================================================
# 
# 찾을 코드 (Ctrl+F로 검색):
#   DEFAULT_LAYOUT = ["🎯 목표 달성률", "📊 실시간 요약", "⚡ 시스템 분석관", "💼 포트폴리오 & 리밸런싱", "📈 성장 곡선", "📝 매매 일지"]
#
# 바꿀 코드:
#   DEFAULT_LAYOUT = ["🎯 목표 달성률", "📊 실시간 요약", "⚡ 시스템 분석관", "💼 포트폴리오 & 리밸런싱", "📈 성장 곡선", "📅 월별 히트맵", "📝 매매 일지"]
#
# (변경점: "📈 성장 곡선" 뒤에 "📅 월별 히트맵" 추가)


# ================================================================
# 변경 2: 렌더링 루프에 히트맵 블록 삽입
# ================================================================
#
# 찾을 위치: elif block == "📝 매매 일지": 바로 위에 아래 코드를 삽입
# (즉, elif block == "📈 성장 곡선": 블록의 st.write("") 다음 줄)
#
# 아래 코드를 그대로 복사해서 붙여넣으세요:

            elif block == "📅 월별 히트맵":
                st.markdown("**📅 월별 수익률 히트맵**")
                hist_dict = curr_acc_data.get("seed_history", {})
                if hist_dict and len(hist_dict) >= 2:
                    with st.container(border=True):
                        try:
                            hist_df = pd.DataFrame.from_dict(hist_dict, orient='index')
                            hist_df.index = pd.to_datetime(hist_df.index)
                            hist_df = hist_df.sort_index()
                            
                            monthly_equity = hist_df['equity'].resample('ME').last().dropna()
                            monthly_returns = monthly_equity.pct_change().dropna() * 100
                            
                            if len(monthly_returns) > 0:
                                years = sorted(monthly_returns.index.year.unique())
                                month_labels = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']
                                
                                z_data = []; text_data = []
                                for y in years:
                                    row = []; text_row = []
                                    for m in range(1, 13):
                                        mask = (monthly_returns.index.year == y) & (monthly_returns.index.month == m)
                                        vals = monthly_returns[mask]
                                        if len(vals) > 0:
                                            v = vals.iloc[0]; row.append(v); text_row.append(f"{v:+.1f}%")
                                        else:
                                            row.append(None); text_row.append("")
                                    z_data.append(row); text_data.append(text_row)
                                
                                if current_theme in ["갤럭시 탭 테마"]:
                                    cs = [[0, '#E94C3D'], [0.5, '#1C1C1E'], [1, '#23D079']]
                                else:
                                    cs = [[0, C_DOWN], [0.5, '#F5F5F5'], [1, C_UP]]
                                
                                fig_hm = go.Figure(data=go.Heatmap(
                                    z=z_data, x=month_labels, y=[str(y) for y in years],
                                    text=text_data, texttemplate="%{text}",
                                    textfont={"size": 13, "color": TEXT_COLOR},
                                    colorscale=cs, zmid=0, zmin=-15, zmax=15,
                                    hovertemplate='%{y}년 %{x}: %{text}<extra></extra>',
                                    showscale=True,
                                    colorbar=dict(title="(%)", titlefont=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR))
                                ))
                                cust_hm = THEME_LAYOUT.copy()
                                cust_hm.update(height=max(200, len(years)*60+80), xaxis=dict(side='top', tickfont=dict(size=13)), yaxis=dict(autorange='reversed', tickfont=dict(size=13)))
                                fig_hm.update_layout(**cust_hm)
                                st.plotly_chart(fig_hm, use_container_width=True)
                                
                                pos_m = sum(1 for r in monthly_returns if r > 0)
                                neg_m = sum(1 for r in monthly_returns if r < 0)
                                tot_m = len(monthly_returns)
                                wr = (pos_m / tot_m * 100) if tot_m > 0 else 0
                                
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("월간 승률", f"{wr:.0f}%", f"{pos_m}승 {neg_m}패")
                                c2.metric("월 평균 수익률", f"{monthly_returns.mean():+.2f}%")
                                c3.metric("최고의 달", f"{monthly_returns.idxmax().strftime('%Y-%m')}", f"{monthly_returns.max():+.1f}%")
                                c4.metric("최악의 달", f"{monthly_returns.idxmin().strftime('%Y-%m')}", f"{monthly_returns.min():+.1f}%", delta_color="inverse")
                            else:
                                st.info("수익률 계산을 위해 최소 2개월 이상의 데이터가 필요합니다.")
                        except Exception as e:
                            st.warning(f"히트맵 생성 중 오류: {e}")
                else:
                    st.info("히트맵을 표시하려면 며칠간 포트폴리오 데이터가 누적되어야 합니다.")
                st.write("")
