# -*- coding: utf-8 -*-
"""
Stock Compass V105-3
DB 동기화 검증/안정화 패치

목표
- PC와 휴대폰에서 매입원금/평가금액/수익률이 다르게 보이는 원인 추적
- portfolio.json을 단일 기준 데이터로 읽고, 모든 금액 계산을 같은 함수에서 처리
- DB 지문(파일 지문 + 정규화 데이터 지문 + 계산 지문)을 표시하여 기기별 불일치 확인

개발 원칙
- 기존 기능 삭제 금지
- 기능은 숨기거나 내부 엔진으로 활용
- 사용자는 결론을 본다
"""

import json
import os
import math
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st

APP_VERSION = "V105-3"
APP_TITLE = "Stock Compass"
BASE_DIR = Path(__file__).resolve().parent
PORTFOLIO_FILE = BASE_DIR / "portfolio.json"
DB_FILE = BASE_DIR / "stock_compass_db.json"

DEFAULT_HOLDINGS = [
    {"name": "에스피시스템스", "qty": 0, "avg_price": 0, "current_price": 0, "theme": "로봇/자동화", "leader_chain": "스마트팩토리·로봇 자동화"},
    {"name": "제룡전기", "qty": 0, "avg_price": 0, "current_price": 0, "theme": "전력기기", "leader_chain": "AI 데이터센터·전력 인프라"},
    {"name": "ACE AI반도체 TOP3", "qty": 0, "avg_price": 0, "current_price": 0, "theme": "AI반도체 ETF", "leader_chain": "삼성전자·SK하이닉스·한미반도체"},
    {"name": "KODEX 미국S&P500", "qty": 0, "avg_price": 0, "current_price": 0, "theme": "미국지수 ETF", "leader_chain": "미국 대형 성장주"},
    {"name": "LG디스플레이", "qty": 0, "avg_price": 0, "current_price": 0, "theme": "디스플레이", "leader_chain": "OLED·XR·전장 디스플레이"},
]

DISCOVERY_POOL = [
    {
        "name": "제룡전기",
        "theme": "전력기기 / 변압기",
        "supply_chain": "엔비디아·AI서버 → 데이터센터 증설 → 전력 사용량 증가 → 변압기/전력기기 수혜",
        "discovery_reason": "AI 서버가 늘수록 전력 인프라 병목이 커진다. 대장주보다 후방 전력기기 업체가 재평가될 수 있는 구조다.",
        "news_signal": "전력망 투자, 데이터센터 증설, 변압기 수출 뉴스에 민감",
        "chart_signal": "급등 후 눌림 구간에서는 분할 접근이 유리",
        "earnings_signal": "수주잔고와 수출 비중 확인 필요",
        "risk": "단기 급등 이후 변동성, 수주 공백, 환율 영향",
        "future_probability": 82,
        "action": "관망 후 눌림 매수",
        "score": 86,
    },
    {
        "name": "에스피시스템스",
        "theme": "로봇 / 스마트팩토리",
        "supply_chain": "자동차·2차전지·반도체 공장 자동화 → 물류/로봇 자동화 → 시스템 통합 수혜",
        "discovery_reason": "대기업 설비투자가 재개될 때 먼저 움직일 수 있는 자동화 후방주 성격이 있다. Stock Compass의 ‘다음 발굴주’ 기준에 가장 잘 맞는 후보군이다.",
        "news_signal": "로봇, 스마트팩토리, 공장 자동화 투자 뉴스에 반응",
        "chart_signal": "거래량 동반 반등 여부가 핵심",
        "earnings_signal": "수주성 매출 특성상 분기별 변동성 확인 필요",
        "risk": "소형주 변동성, 거래량 부족, 실적 확인 전 기대감 선반영",
        "future_probability": 80,
        "action": "소액 분할 추적",
        "score": 84,
    },
    {
        "name": "ISC",
        "theme": "반도체 테스트 소켓",
        "supply_chain": "SK하이닉스·엔비디아 HBM → 고성능 반도체 테스트 증가 → 테스트 소켓 수요 확대",
        "discovery_reason": "AI 반도체 대장주를 직접 사기 부담스러울 때, 테스트 공정의 핵심 부품주로 우회 접근할 수 있다.",
        "news_signal": "HBM, AI칩, 테스트 공정 투자 뉴스와 연결",
        "chart_signal": "고평가 부담이 있어 추격보다 조정 확인 필요",
        "earnings_signal": "AI/HBM 관련 매출 비중 확대 여부 확인",
        "risk": "이미 시장 관심이 높아 밸류에이션 부담 존재",
        "future_probability": 78,
        "action": "가격 부담 시 관망",
        "score": 81,
    },
    {
        "name": "이수페타시스",
        "theme": "AI 서버 PCB",
        "supply_chain": "엔비디아 GPU → AI 서버 → 고다층 PCB 수요 → 서버용 PCB 수혜",
        "discovery_reason": "AI 서버 확산의 직접 후방 공급망 후보. 대장주보다 서버 부품단에서 성장성을 찾는 방식에 맞다.",
        "news_signal": "AI 서버 증설, MLB/PCB 공급 부족 뉴스에 민감",
        "chart_signal": "테마 과열 시 변동성 확대 가능",
        "earnings_signal": "서버용 제품 비중과 마진 확인 필요",
        "risk": "테마 과열, 증설 비용, 고객사 집중도",
        "future_probability": 77,
        "action": "관심 유지",
        "score": 79,
    },
    {
        "name": "하나마이크론",
        "theme": "반도체 후공정",
        "supply_chain": "SK하이닉스·삼성전자 → 메모리/HBM 패키징 → 후공정 외주 수혜",
        "discovery_reason": "HBM과 메모리 사이클 회복 시 후공정 업체가 뒤따라 움직일 수 있다. 대장주의 공급망 수혜주 발굴 관점에 적합하다.",
        "news_signal": "HBM, 패키징, 후공정 투자 뉴스와 연결",
        "chart_signal": "업황 회복 기대와 실제 실적 사이의 간극 확인",
        "earnings_signal": "가동률과 수익성 개선 여부가 중요",
        "risk": "업황 둔화, 투자비 부담, 실적 지연",
        "future_probability": 74,
        "action": "분할 관심",
        "score": 76,
    },
]


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", "").replace("원", "").strip()
            if value == "":
                return default
        return float(value)
    except Exception:
        return default


def safe_load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.session_state["last_json_error"] = f"{path.name}: {e}"
    return default


def safe_save_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_holdings_payload(data: Any) -> List[Dict[str, Any]]:
    """여러 저장 구조를 받아도 holdings 리스트만 추출한다."""
    if isinstance(data, dict):
        for key in ["holdings", "portfolio", "stocks", "items", "data"]:
            if isinstance(data.get(key), list):
                return data[key]
        # 종목명이 key로 저장된 dict 구조도 허용
        if data and all(isinstance(v, dict) for v in data.values()):
            out = []
            for name, item in data.items():
                row = dict(item)
                row.setdefault("name", name)
                out.append(row)
            return out
    if isinstance(data, list):
        return data
    return []


def normalize_holdings(data: Any) -> List[Dict[str, Any]]:
    raw = extract_holdings_payload(data)
    if not raw:
        return DEFAULT_HOLDINGS

    normalized = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("종목명") or item.get("stock_name") or item.get("ticker") or item.get("code") or "미지정"
        qty = to_float(item.get("qty", item.get("수량", item.get("quantity", 0))))
        avg = to_float(item.get("avg_price", item.get("평단", item.get("평단가", item.get("average_price", 0)))))
        cur = to_float(item.get("current_price", item.get("현재가", item.get("price", item.get("last_price", 0)))))

        normalized.append({
            "name": str(name).strip(),
            "qty": qty,
            "avg_price": avg,
            "current_price": cur,
            "theme": item.get("theme", item.get("테마", "")),
            "leader_chain": item.get("leader_chain", item.get("공급망", "")),
        })

    # 이름 기준 정렬로 PC/모바일의 JSON 순서 차이에도 같은 지문 생성
    normalized = [x for x in normalized if x["name"] and x["name"] != "미지정"] or DEFAULT_HOLDINGS
    normalized.sort(key=lambda x: x["name"])
    return normalized


def load_holdings() -> Tuple[List[Dict[str, Any]], str]:
    """단일 기준: portfolio.json 우선, 없으면 stock_compass_db.json, 그것도 없으면 기본 보유종목."""
    if PORTFOLIO_FILE.exists():
        return normalize_holdings(safe_load_json(PORTFOLIO_FILE, DEFAULT_HOLDINGS)), "portfolio.json"
    if DB_FILE.exists():
        return normalize_holdings(safe_load_json(DB_FILE, DEFAULT_HOLDINGS)), "stock_compass_db.json"
    return normalize_holdings(DEFAULT_HOLDINGS), "DEFAULT_HOLDINGS"


def calc_portfolio_summary(holdings: List[Dict[str, Any]]) -> Dict[str, float]:
    principal = 0.0
    valuation = 0.0
    for h in holdings:
        qty = to_float(h.get("qty"))
        avg = to_float(h.get("avg_price"))
        cur = to_float(h.get("current_price"))
        # 현재가가 없으면 평가금액은 평단 기준으로 잡아 기기별 계산 차이를 막는다.
        effective_price = cur if cur > 0 else avg
        principal += qty * avg
        valuation += qty * effective_price
    profit = valuation - principal
    profit_rate = (profit / principal * 100) if principal else 0.0
    return {
        "principal": round(principal, 2),
        "valuation": round(valuation, 2),
        "profit": round(profit, 2),
        "profit_rate": round(profit_rate, 4),
        "count": len(holdings),
    }


def short_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length].upper()


def json_fingerprint(data: Any) -> str:
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return short_hash(canonical)


def file_fingerprint(path: Path) -> str:
    if not path.exists():
        return "파일없음"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12].upper()
    except Exception:
        return "읽기실패"


def build_db_diagnostic(holdings: List[Dict[str, Any]], source_name: str) -> Dict[str, Any]:
    summary = calc_portfolio_summary(holdings)
    normalized_hash = json_fingerprint(holdings)
    calc_hash = json_fingerprint(summary)
    return {
        "app_version": APP_VERSION,
        "base_dir": str(BASE_DIR),
        "source": source_name,
        "portfolio_file_path": str(PORTFOLIO_FILE),
        "portfolio_file_exists": PORTFOLIO_FILE.exists(),
        "portfolio_file_hash": file_fingerprint(PORTFOLIO_FILE),
        "db_file_path": str(DB_FILE),
        "db_file_exists": DB_FILE.exists(),
        "db_file_hash": file_fingerprint(DB_FILE),
        "normalized_holdings_hash": normalized_hash,
        "calculation_hash": calc_hash,
        "summary": summary,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def action_badge(action: str) -> str:
    if "매수" in action or "추적" in action:
        return "🟢"
    if "관망" in action:
        return "🟡"
    if "축소" in action or "주의" in action:
        return "🟠"
    return "🔵"


def future_bar(prob: int) -> str:
    prob = max(0, min(100, int(prob)))
    filled = math.floor(prob / 10)
    return "█" * filled + "░" * (10 - filled)


def render_metric_card(title: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div style='padding:14px 16px;border:1px solid #e7e7e7;border-radius:16px;background:#ffffff;margin-bottom:10px;'>
            <div style='font-size:13px;color:#666;margin-bottom:4px;'>{title}</div>
            <div style='font-size:22px;font-weight:800;color:#111;'>{value}</div>
            <div style='font-size:12px;color:#777;margin-top:6px;'>{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_discovery_card(item: Dict[str, Any], rank: int | None = None) -> None:
    prefix = f"TOP {rank} · " if rank else ""
    badge = action_badge(item["action"])
    st.markdown(f"### {badge} {prefix}{item['name']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("발굴점수", f"{item['score']}점")
    c2.metric("미래확률", f"{item['future_probability']}%")
    c3.metric("최종행동", item["action"])

    st.markdown(f"**발굴 이유**  \n{item['discovery_reason']}")
    st.markdown(f"**공급망 연결**  \n{item['supply_chain']}")

    with st.expander("내부 판단 근거 보기", expanded=False):
        st.write("**뉴스 신호:**", item["news_signal"])
        st.write("**차트 신호:**", item["chart_signal"])
        st.write("**실적 신호:**", item["earnings_signal"])
        st.write("**리스크:**", item["risk"])
        st.write("**미래확률 바:**", future_bar(item["future_probability"]))


def render_home(holdings: List[Dict[str, Any]], source_name: str) -> None:
    st.subheader("🏠 홈")
    st.caption("사용자는 결론만 본다: 오늘 뭐 사? 오늘 뭐 팔아? 오늘 뭐 하지?")

    summary = calc_portfolio_summary(holdings)
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("시장판단", "중립~선별", "전체 매수보다 발굴형 선별 접근")
    with c2:
        render_metric_card("내 포트 매입원금", f"{summary['principal']:,.0f}원", f"단일 계산 함수 기준 · source={source_name}")
    with c3:
        render_metric_card("내 포트 평가금액", f"{summary['valuation']:,.0f}원", f"수익률 {summary['profit_rate']:.2f}%")

    st.markdown("## 오늘의 행동")
    top = sorted(DISCOVERY_POOL, key=lambda x: x["score"], reverse=True)[0]
    st.success(f"오늘은 **{top['name']}** 중심으로 확인: {top['action']}")

    st.markdown("## 오늘의 발굴 TOP3")
    for idx, item in enumerate(sorted(DISCOVERY_POOL, key=lambda x: x["score"], reverse=True)[:3], start=1):
        with st.container(border=True):
            st.markdown(f"**TOP {idx}. {item['name']}** — {item['theme']}")
            st.write(item["discovery_reason"])
            st.caption(f"공급망: {item['supply_chain']}")

    st.markdown("## AI 소장 의견")
    st.info("V105-3은 새 기능보다 DB 신뢰성 확보가 목표입니다. 홈/내종목/DB확인이 모두 같은 계산 함수를 사용하도록 통일했습니다.")


def render_search() -> None:
    st.subheader("🔎 검색")
    keyword = st.text_input("종목명 또는 테마 검색", placeholder="예: 제룡전기, 에스피시스템스, HBM, AI서버")
    pool = DISCOVERY_POOL
    if keyword:
        pool = [x for x in DISCOVERY_POOL if keyword.lower() in (x['name'] + x['theme'] + x['supply_chain']).lower()]
        if not pool:
            st.warning("검색 결과가 없습니다. 현재 내장 발굴 후보군 기준입니다.")
            return

    for item in pool:
        with st.expander(f"{item['name']} · {item['theme']}", expanded=False):
            st.write("### 기업개요")
            st.write(item["theme"])
            st.write("### 공급망")
            st.write(item["supply_chain"])
            st.write("### 뉴스분석")
            st.write(item["news_signal"])
            st.write("### 실적분석")
            st.write(item["earnings_signal"])
            st.write("### 차트분석")
            st.write(item["chart_signal"])
            st.write("### 미래확률")
            st.write(f"{item['future_probability']}% · {future_bar(item['future_probability'])}")
            st.write("### 리스크")
            st.write(item["risk"])
            st.write("### AI소장 의견")
            st.write(item["discovery_reason"])


def render_recommendation() -> None:
    st.subheader("🧭 추천 · 발굴형 구조 유지")
    st.caption("V106에서 본격 개편 예정. V105-3에서는 DB 안정화를 우선하고 발굴형 구조는 유지합니다.")

    mode = st.radio("보기 방식", ["오늘의 발굴 TOP3", "공급망별 보기", "행동별 보기"], horizontal=True)
    sorted_pool = sorted(DISCOVERY_POOL, key=lambda x: x["score"], reverse=True)

    if mode == "오늘의 발굴 TOP3":
        st.markdown("## 오늘의 발굴 TOP3")
        for idx, item in enumerate(sorted_pool[:3], start=1):
            with st.container(border=True):
                render_discovery_card(item, idx)
    elif mode == "공급망별 보기":
        for item in sorted_pool:
            with st.container(border=True):
                st.markdown(f"### 🔗 {item['theme']} · {item['name']}")
                st.write(item["supply_chain"])
                st.write("**발굴 이유:**", item["discovery_reason"])
                st.caption(f"미래확률 {item['future_probability']}% / 행동 {item['action']}")
    else:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in sorted_pool:
            groups.setdefault(item["action"], []).append(item)
        for action, items in groups.items():
            st.markdown(f"## {action_badge(action)} {action}")
            for item in items:
                st.write(f"- **{item['name']}**: {item['discovery_reason']}")


def render_my_stocks(holdings: List[Dict[str, Any]]) -> None:
    st.subheader("📌 내종목")
    st.caption("모든 금액은 DB 안정화용 단일 계산 함수와 같은 기준으로 표시합니다.")

    summary = calc_portfolio_summary(holdings)
    c1, c2, c3 = st.columns(3)
    c1.metric("총 매입원금", f"{summary['principal']:,.0f}원")
    c2.metric("총 평가금액", f"{summary['valuation']:,.0f}원")
    c3.metric("총 수익률", f"{summary['profit_rate']:.2f}%")

    for h in holdings:
        name = h.get("name", "미지정")
        qty = to_float(h.get("qty"))
        avg = to_float(h.get("avg_price"))
        cur = to_float(h.get("current_price"))
        effective_price = cur if cur > 0 else avg
        principal = qty * avg
        valuation = qty * effective_price
        rate = ((valuation - principal) / principal * 100) if principal else 0.0
        price_caption = "현재가 기준" if cur > 0 else "현재가 없음: 평단 기준"

        with st.expander(f"{name}", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("수량", f"{qty:g}")
            c2.metric("평단", f"{avg:,.0f}원")
            c3.metric("현재가", f"{effective_price:,.0f}원", help=price_caption)
            c4, c5, c6 = st.columns(3)
            c4.metric("매입원금", f"{principal:,.0f}원")
            c5.metric("평가금액", f"{valuation:,.0f}원")
            c6.metric("수익률", f"{rate:.2f}%")

            matched = next((x for x in DISCOVERY_POOL if x["name"] == name), None)
            if matched:
                st.write("종합점수:", f"{matched['score']}점")
                st.write("미래확률:", f"{matched['future_probability']}%")
                st.write("행동지침:", matched["action"])
                st.write("공급망:", matched["supply_chain"])
                st.write("AI소장 의견:", matched["discovery_reason"])
            else:
                st.info("V107에서 상세 분석 연결 예정")


def render_db_status(holdings: List[Dict[str, Any]], source_name: str) -> None:
    st.subheader("🗄️ DB 상태 확인 · V105-3")
    st.caption("PC와 휴대폰의 금액 차이 원인 확인용. 아래 지문이 같으면 같은 데이터/계산 기준입니다.")

    diagnostic = build_db_diagnostic(holdings, source_name)
    summary = diagnostic["summary"]

    c1, c2, c3 = st.columns(3)
    c1.metric("매입원금", f"{summary['principal']:,.0f}원")
    c2.metric("평가금액", f"{summary['valuation']:,.0f}원")
    c3.metric("수익률", f"{summary['profit_rate']:.2f}%")

    st.markdown("### 핵심 지문")
    st.code(
        f"""앱버전: {diagnostic['app_version']}
읽은 데이터: {diagnostic['source']}
정규화 보유종목 지문: {diagnostic['normalized_holdings_hash']}
계산결과 지문: {diagnostic['calculation_hash']}
portfolio.json 파일 지문: {diagnostic['portfolio_file_hash']}
stock_compass_db.json 파일 지문: {diagnostic['db_file_hash']}
기준 폴더: {diagnostic['base_dir']}"""
    )

    st.markdown("### 파일 상태")
    for path in [PORTFOLIO_FILE, DB_FILE]:
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if exists else "없음"
        st.write(f"**{path.name}**")
        st.code(f"경로: {path}\n존재: {exists}\n크기: {size} bytes\n수정시간: {mtime}\n파일지문: {file_fingerprint(path)}")

    with st.expander("현재 읽힌 보유종목 보기", expanded=False):
        st.json(holdings)

    with st.expander("진단 전체 JSON 보기", expanded=False):
        st.json(diagnostic)

    st.warning("PC와 휴대폰에서 정규화 보유종목 지문 또는 계산결과 지문이 다르면, 같은 코드를 쓰더라도 서로 다른 DB/세션/파일을 읽고 있는 것입니다.")


def render_footer() -> None:
    st.divider()
    st.caption("Stock Compass는 주식 관리 앱이 아니다. 주식 발굴기다. 목표는 다음 에스피시스템스를 남들보다 먼저 찾는 것.")


def main() -> None:
    st.set_page_config(page_title=f"{APP_TITLE} {APP_VERSION}", page_icon="🧭", layout="wide")
    st.title(f"🧭 {APP_TITLE} {APP_VERSION}")
    st.caption("DB 동기화 검증/안정화 패치 · PC/휴대폰 수익률 불일치 확인")

    holdings, source_name = load_holdings()

    tabs = st.tabs(["홈", "검색", "추천", "내종목", "DB확인"])
    with tabs[0]:
        render_home(holdings, source_name)
    with tabs[1]:
        render_search()
    with tabs[2]:
        render_recommendation()
    with tabs[3]:
        render_my_stocks(holdings)
    with tabs[4]:
        render_db_status(holdings, source_name)

    render_footer()


if __name__ == "__main__":
    main()
