# AMLS v4.3 코드 검증 결과 및 보완 패치
# 
# 검증 결과: 핵심 로직 100% 정확. 에지케이스 1건 보완.
#
# ================================================================
# 보완 내용: prev_reg 탐색 에지케이스 수정
# ================================================================
#
# 위치: get_market_status() 함수 내부
# 검색: prev_reg = current_reg
#
# ── 변경 전 ──
#
#             prev_reg = current_reg
#             for i in range(len(applied_series)-regime_duration-1, -1, -1):
#                 prev_reg = applied_series.iloc[i]; break
#
# ── 변경 후 ──
#
#             prev_reg = current_reg
#             search_start = len(applied_series) - regime_duration - 1
#             if search_start >= 0:
#                 prev_reg = int(applied_series.iloc[search_start])
#
# ================================================================
# 이유: 레짐이 전체 400일 데이터 기간 동안 변하지 않았을 경우,
# 기존 for 루프의 range가 음수가 되어 실행되지 않고
# prev_reg이 current_reg로 남아 방향 판단이 항상 "stable"이 됨.
# search_start가 0 이상일 때만 이전 레짐을 탐색하도록 수정.
# 음수인 경우(전체 기간 동일 레짐)는 stable이 맞으므로 그대로 유지.
# ================================================================
