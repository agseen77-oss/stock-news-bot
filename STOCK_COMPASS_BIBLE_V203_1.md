
Stock Compass Bible 변경 기록 — V203.1
기준 버전
기반: V203 VISIBILITY TOKEN FIX REAL
패치명: V203.1 TOKEN SINGLE SOURCE
변경 목적
V203에 V149, V201, V203 계열 토큰 캐시 흔적이 공존해 실제 토큰 원본이 혼란스러운 문제를 줄인다.
변경 내용
실제 토큰 원본을 `data/kis_token.json` 하나로 명시했다.
앱 상태 표시도 같은 파일을 확인하도록 수정했다.
앱 제목과 브라우저 페이지 제목을 V203.1로 통일했다.
추천 공식, 검증 공식, DB 스키마, 보유종목 데이터는 변경하지 않았다.
검증 상태
Python 문법 검사: 통과
파일 생성 및 ZIP 패키징: 통과
Streamlit Cloud 실제 배포: 사용자 GitHub 반영 후 확인 필요
KIS 실토큰 재사용/만료/신규발급: PC Master 실전 확인 필요
영향 범위
KIS 토큰 상태 표시와 버전 표기
추천·검증 엔진 공식에는 영향 없음
다음 작업
Streamlit 화면 회귀 확인
PC Master 토큰 재사용 확인
V203 다이어트: 중복 UI와 실험 기능의 안전 격리
Decision Engine 설계 전 Time Machine 공용화 준비
