
Stock Compass V203 VISIBILITY TOKEN FIX REAL

덮어써도 되는 실제 앱 업데이트입니다.

수정 1: 추천 글자색 문제
- 일반 추천/검증 카드는 검은 글씨 고정
- 검은/남색 배경 박스는 흰 글씨 고정
- Streamlit markdown 내부 span/b/strong까지 color와 -webkit-text-fill-color 강제
- 기존 V195~V202 글자색 충돌 재발 방지

수정 2: KIS 토큰 재사용 강화
- data/kis_token_v203.json 캐시 추가
- kis_access_token() 진입 시 캐시 우선 확인
- 23시간 내 기존 토큰 재사용
- 전문가 메뉴에 토큰 캐시 상태 표시

점검:
- app.py 내 token/oauth/access_token 관련 문자열 수: 12
- 이후에도 토큰 문자가 오면 별도 직접 발급 함수가 남아있는 것이므로 'tokenP' 검색 캡처 필요.
