# ------------------------------------------
# PAGE 4: 매크로 뉴스룸
# ------------------------------------------
elif page == "📰 매크로 뉴스룸":
    headlines_for_ai, news_items = fetch_macro_news()

    # 헤더 영역
    if is_glass_style:
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="lg-banner" style="display:flex;align-items:center;gap:12px;">
  <div style="font-size:1.5em;">📰</div>
  <h4 style="font-size:1.35em;margin-bottom:0;letter-spacing:-0.5px;">실시간 글로벌 매크로 뉴스 &amp; AI 브리핑</h4>
  <div class="badge-rt" style="margin-left:auto;">{rt_label}</div>
</div>
</body></html>""", height=85, scrolling=False)
    elif is_transparent_style:
        components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'DM Sans',sans-serif;background:#E8E8ED;padding:10px 6px 6px 6px;}}
.banner{{background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:20px;padding:16px 24px;box-shadow:0 2px 16px rgba(0,0,0,0.07);display:flex;align-items:center;gap:12px;}}
.banner h2{{font-size:1.35em;font-weight:700;color:#1C1C1E;letter-spacing:-0.5px;margin:0;}}
.badge-rt{{margin-left:auto;background:rgba(37,99,235,0.08);color:#2563EB;border:1px solid rgba(37,99,235,0.25);border-radius:8px;padding:4px 12px;font-size:0.85em;font-weight:600;white-space:nowrap;}}
</style></head><body>
<div class="banner"><div style="font-size:1.5em;">📰</div><h2>실시간 글로벌 매크로 뉴스 &amp; AI 브리핑</h2><div class="badge-rt">{rt_label}</div></div>
</body></html>""", height=85, scrolling=False)
    else:
        st.markdown(f"### 📰 실시간 글로벌 매크로 뉴스 & AI 브리핑")

    # ── AI 심층 분석 영역 (가독성 및 폰트 개선) ──
    with st.expander("✨ System-2 심층 추론 애널리스트 분석", expanded=True):
        if st.button("🚀 심층 추론 요약 실행", use_container_width=True):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                if not headlines_for_ai: 
                    st.warning("분석할 뉴스가 없습니다.")
                else:
                    with st.spinner("AI가 1920년대 퀀트 애널리스트의 시각으로 뉴스를 분석하고 있습니다..."):
                        genai.configure(api_key=api_key)
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model  = genai.GenerativeModel(models[0].replace('models/',''))
                        
                        prompt = """너는 1920년대 전설적인 월스트리트 퀀트 애널리스트야. 매우 냉철하고 전문적인 어조로 작성해.
                        다음 뉴스 헤드라인들을 분석해서 아래 3가지 목차로 요약해줘.
                        
                        ## 1. 주요 뉴스 분류 (섹터/테마별 묶음)
                        ## 2. 시장 잠재 리스크 (VIX 상승 요소)
                        ## 3. 애널리스트의 최종 고찰 (투자 스탠스)
                        
                        각 목차의 제목은 반드시 `##` 마크다운을 사용해서 크게 눈에 띄게 해주고, 내용은 글머리 기호(`*` 또는 `-`)를 사용해서 가독성 좋게 정리해.
                        
                        [뉴스 헤드라인]:
                        """ + "\n".join(headlines_for_ai)
                        
                        response = model.generate_content(prompt)
                        
                        ai_bg = 'rgba(255,255,255,0.05)' if is_dark else 'rgba(0,0,0,0.02)'
                        text_col = '#ECF0F1' if is_dark else '#2C3E50'
                        
                        st.markdown(f"""
                        <style>
                        .ai-report-box {{
                            background-color: {ai_bg};
                            border: 1px solid {h_border};
                            border-radius: 16px;
                            padding: 30px;
                            margin-top: 15px;
                            margin-bottom: 25px;
                            box-shadow: {h_shadow};
                        }}
                        .ai-report-box h2 {{
                            color: {h_accent};
                            font-size: 1.5em !important;
                            font-weight: 800;
                            border-bottom: 2px solid {h_border};
                            padding-bottom: 8px;
                            margin-top: 25px;
                            margin-bottom: 15px;
                        }}
                        .ai-report-box h2:first-child {{
                            margin-top: 0;
                        }}
                        .ai-report-box p, .ai-report-box li {{
                            color: {text_col};
                            font-size: 1.1em;
                            line-height: 1.7;
                            font-family: 'Pretendard', 'DM Sans', sans-serif;
                            font-weight: 500;
                        }}
                        .ai-report-box strong {{
                            color: {h_color};
                            font-weight: 700;
                            background-color: {'rgba(255,255,255,0.1)' if is_dark else 'rgba(0,0,0,0.05)'};
                            padding: 2px 6px;
                            border-radius: 4px;
                        }}
                        </style>
                        
                        <div class="ai-report-box">
                        """, unsafe_allow_html=True)
                        
                        st.markdown(response.text)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        with st.expander("📋 텍스트로 복사하기"): 
                            st.code(response.text, language="markdown")
            except KeyError: 
                st.error("🚨 Secrets에 'GEMINI_API_KEY'를 설정해주세요.")

    st.divider()

    # ── 최신 경제 헤드라인 갤러리 영역 ──
    if news_items:
        if is_glass_style:
            cards = "".join([f'<div class="ncard"><div class="ntitle"><a href="{i["link"]}" target="_blank">{i["title"].replace("&","&amp;")}</a></div><div class="ndate">{i["date"]}</div></div>'
                             for i in news_items])
            components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{LG_CSS_BASE}</head>
<body>
<div class="section-title" style="font-size: 1.2em; margin-bottom: 15px;">🖼️ 최신 경제 헤드라인 갤러리</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;">{cards}</div>
</body></html>""", height=180+(len(news_items)//3)*160, scrolling=False)

        elif is_transparent_style:
            cards_tr = "".join([f"""<div style="background:rgba(255,255,255,0.93);border:1px solid rgba(0,0,0,0.065);border-radius:18px;padding:18px;height:140px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 2px 12px rgba(0,0,0,0.06);transition:transform 0.2s,box-shadow 0.2s;">
  <div style="font-size:0.95em;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;"><a href="{i['link']}" target="_blank" style="color:#1C1C1E;text-decoration:none;">{i['title'].replace('&','&amp;')}</a></div>
  <div style="font-size:0.8em;font-weight:600;color:#2563EB;margin-top:8px;">{i['date']}</div>
</div>""" for i in news_items])
            components.html(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'DM Sans',sans-serif;background:#E8E8ED;padding:10px 6px 10px 6px;}}
.title{{font-size:1.2em;font-weight:700;color:#1C1C1E;margin-bottom:15px;padding-left:4px;}}</style>
</head><body>
<div class="title">🖼️ 최신 경제 헤드라인 갤러리</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;">{cards_tr}</div>
</body></html>""", height=180+(len(news_items)//3)*160, scrolling=False)

        else:
            st.markdown("<div style='font-size: 1.2em; font-weight: 700; margin-bottom: 15px;'>🖼️ 최신 경제 헤드라인 갤러리</div>", unsafe_allow_html=True)
            cols = st.columns(3)
            c_bg  = '#FFFDF7' if is_neo_style else '#1C1F28'
            c_brd = '1px solid rgba(0,0,0,0.05)' if is_neo_style else '1px solid rgba(255,255,255,0.05)'
            c_shd = 'var(--shadow-raised)' if is_neo_style else '0 4px 15px rgba(0,0,0,0.3)'
            c_txt = 'var(--text-main)' if is_neo_style else '#ECF0F1'
            for idx,item in enumerate(news_items):
                with cols[idx%3]:
                    st.markdown(f"""<div style="background:{c_bg};border:{c_brd};padding:20px;margin-bottom:15px;border-radius:18px;height:150px;box-shadow:{c_shd};display:flex;flex-direction:column;justify-content:space-between; transition: transform 0.2s;">
                        <div style="font-weight:600;font-size:1.05em;line-height:1.45;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">
                            <a href="{item['link']}" target="_blank" style="color:{c_txt};text-decoration:none;">{item['title']}</a></div>
                        <div style="color:{h_accent};font-size:0.85em;margin-top:10px;font-weight:700;">{item['date']}</div>
                    </div>""", unsafe_allow_html=True)
    else:
        st.write("수신된 뉴스가 없습니다. (15분 후 갱신)")
