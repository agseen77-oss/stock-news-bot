# -*- coding: utf-8 -*-
"""
V40 run_bot.py
경규님 전용 08시 투자판단 리포트
- 뉴스요약이 아니라 오늘 매수/스킵 판단
- 100점 만점 통일
- 기업점수 / 가격매력도 분리
- 종목별 DNA 반영
- 카카오톡 2개 발송
"""

import os
import json
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

KST = timezone(timedelta(hours=9))
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
KAKAO_TOKEN = os.getenv("KAKAO_TOKEN", "").strip().strip("'").strip('"')
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "").strip().strip("'").strip('"')

PORTFOLIO = {
    "에스피시스템스": {"qty": 4, "avg_price": 7520, "buy_rule": "추가매수 중지", "dna": "robotics"},
    "제룡전기": {"qty": 7, "avg_price": 53200, "buy_rule": "매일 1주", "dna": "power_infra"},
    "ACE AI반도체 TOP3": {"qty": 21, "avg_price": 57883, "buy_rule": "매일 1주", "dna": "semiconductor_etf"},
    "KODEX 미국S&P500": {"qty": 5, "avg_price": 25807, "buy_rule": "매일 1주", "dna": "sp500_etf"},
    "LG디스플레이": {"qty": 15, "avg_price": 15303, "buy_rule": "매일 1주", "dna": "display_turnaround"},
    "엔비디아": {"qty": 0.030428, "avg_price": 322236, "buy_rule": "매주 목요일 1만원", "dna": "global_ai"},
}

DNA = {
    "sp500_etf": {
        "label": "미국지수 장기 적립",
        "keywords": ["미국", "S&P500", "나스닥", "다우", "금리", "환율", "달러", "엔비디아"],
        "base_quality": 88,
        "weights": {"market": 45, "price": 20, "news": 15, "fx": 10, "quality": 10},
    },
    "semiconductor_etf": {
        "label": "AI 반도체 ETF",
        "keywords": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아", "SOXX"],
        "base_quality": 84,
        "weights": {"semiconductor": 35, "market": 20, "price": 20, "news": 15, "quality": 10},
    },
    "power_infra": {
        "label": "전력 인프라 성장주",
        "keywords": ["전력", "전선", "변압기", "전력망", "송전", "데이터센터", "AI 인프라", "제룡전기"],
        "base_quality": 78,
        "weights": {"power": 40, "price": 25, "news": 15, "market": 10, "quality": 10},
    },
    "robotics": {
        "label": "로봇/자동화 고변동 성장주",
        "keywords": ["로봇", "자동화", "스마트팩토리", "공장", "설비", "2차전지", "에스피시스템스"],
        "base_quality": 62,
        "weights": {"robotics": 35, "price": 25, "news": 15, "market": 10, "quality": 15},
    },
    "display_turnaround": {
        "label": "OLED 턴어라운드",
        "keywords": ["디스플레이", "OLED", "패널", "애플", "아이폰", "TV", "LG디스플레이"],
        "base_quality": 60,
        "weights": {"display": 35, "price": 25, "news": 15, "market": 10, "quality": 15},
    },
    "global_ai": {
        "label": "글로벌 AI 대표주",
        "keywords": ["엔비디아", "NVIDIA", "AI", "데이터센터", "GPU", "반도체", "HBM"],
        "base_quality": 96,
        "weights": {"ai": 40, "price": 20, "news": 15, "market": 15, "quality": 10},
    },
}

POSITIVE = ["상승", "강세", "급등", "반등", "호재", "수주", "확대", "증가", "성장", "기대", "투자", "협력", "계약", "최대", "흑자", "개선", "상향", "랠리", "수혜", "회복", "인하", "완화", "신고가", "돌파"]
NEGATIVE = ["하락", "약세", "급락", "폭락", "우려", "위기", "적자", "감소", "둔화", "하향", "규제", "충격", "리스크", "손실", "전쟁", "긴장", "침체", "불안", "고금리", "인상"]


def clamp(v, low=0, high=100):
    try:
        return max(low, min(high, int(round(v))))
    except Exception:
        return 50


def grade(score):
    if score >= 90:
        return "S"
    if score >= 75:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def score_text(score):
    label = {"S": "매우 좋음", "A": "좋음", "B": "보통", "C": "주의", "D": "위험"}[grade(score)]
    return f"{score}점 / {grade(score)}등급({label})"


def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def get_yahoo_quote(symbol, name):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
    try:
        res = requests.get(url, params={"range": "5d", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res.raise_for_status()
        data = res.json()["chart"]["result"][0]
        meta = data.get("meta", {})
        closes = [c for c in data["indicators"]["quote"][0].get("close", []) if c is not None]
        if len(closes) >= 2:
            prev, curr = float(closes[-2]), float(closes[-1])
        else:
            curr, prev = float(meta.get("regularMarketPrice") or 0), float(meta.get("previousClose") or 0)
        if curr <= 0 or prev <= 0:
            raise ValueError("no price")
        pct = (curr - prev) / prev * 100
        arrow = "▲" if pct > 0 else "▼" if pct < 0 else "보합"
        return {"name": name, "pct": pct, "text": f"{name} {arrow} {pct:.2f}%", "ok": True}
    except Exception as e:
        print(f"[지표 수집 실패] {name}: {e}")
        return {"name": name, "pct": 0.0, "text": f"{name}: 수집 실패", "ok": False}


def get_indicators():
    targets = [
        ("^GSPC", "S&P500"), ("^IXIC", "나스닥"), ("^DJI", "다우"), ("SOXX", "미국 반도체 ETF"),
        ("NVDA", "엔비디아"), ("AMD", "AMD"), ("AVGO", "브로드컴"), ("CL=F", "WTI유가"), ("KRW=X", "원/달러 환율"),
    ]
    out = []
    for symbol, name in targets:
        out.append(get_yahoo_quote(symbol, name))
        time.sleep(0.15)
    return out


def get_news():
    queries = [
        "미국 증시 나스닥 반도체", "필라델피아 반도체 엔비디아 HBM", "원달러 환율 외국인 코스피",
        "국제유가 전쟁 중동", "삼성전자 SK하이닉스 반도체", "전력설비 변압기 전력망 데이터센터",
        "로봇 자동화 스마트팩토리", "LG디스플레이 OLED 애플", "엔비디아 AI 데이터센터 GPU",
    ]
    news = []
    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote(q)}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:2]:
                title = item.findtext("title", "").strip()
                if title and title not in news:
                    news.append(title)
        except Exception as e:
            print(f"[뉴스 수집 실패] {q}: {e}")
    return news[:14] or ["뉴스 수집 실패: 지표 기반 판단만 진행합니다."]


def sentiment(title):
    s = 0
    for w in POSITIVE:
        if w in title:
            s += 1
    for w in NEGATIVE:
        if w in title:
            s -= 1
    return s


def pct_map(indicators):
    return {x["name"]: x.get("pct", 0.0) for x in indicators}


def market_score(indicators):
    d = pct_map(indicators)
    score = 50
    plus, minus = [], []
    rules = [
        ("S&P500", 0.3, 8, "S&P500 상승으로 글로벌 투자심리 개선", "S&P500 하락으로 단기 변동성 주의"),
        ("나스닥", 0.5, 10, "나스닥 상승으로 성장주 분위기 긍정", "나스닥 하락으로 성장주 부담"),
        ("미국 반도체 ETF", 0.7, 12, "미국 반도체 강세로 국내 반도체에 긍정", "미국 반도체 약세로 국내 반도체 주의"),
        ("엔비디아", 1.0, 7, "엔비디아 강세로 AI/HBM 심리 개선", "엔비디아 약세로 AI 반도체 심리 약화"),
    ]
    for name, threshold, weight, pmsg, nmsg in rules:
        pct = d.get(name, 0)
        if pct > threshold:
            score += weight; plus.append(pmsg)
        elif pct < -threshold:
            score -= weight; minus.append(nmsg)
    oil = d.get("WTI유가", 0)
    fx = d.get("원/달러 환율", 0)
    if oil > 2:
        score -= 5; minus.append("유가 급등은 비용·물가 부담")
    elif oil < -2:
        score += 3; plus.append("유가 하락은 물가 부담 완화")
    if fx > 0.5:
        score -= 6; minus.append("원/달러 환율 상승은 외국인 수급 부담")
    elif fx < -0.5:
        score += 4; plus.append("원/달러 환율 하락은 외국인 수급에 우호적")
    return clamp(score), plus[:4], minus[:4]


def theme_score(theme, indicators, news):
    d = pct_map(indicators)
    score = 50
    plus, minus = [], []
    if theme in ["market", "ai", "semiconductor"]:
        nasdaq = d.get("나스닥", 0)
        if nasdaq > 0.5:
            score += 8; plus.append("나스닥 강세")
        elif nasdaq < -0.5:
            score -= 8; minus.append("나스닥 약세")
    if theme in ["semiconductor", "ai"]:
        soxx, nvda = d.get("미국 반도체 ETF", 0), d.get("엔비디아", 0)
        if soxx > 0.7:
            score += 12; plus.append("미국 반도체 ETF 강세")
        elif soxx < -0.7:
            score -= 12; minus.append("미국 반도체 ETF 약세")
        if nvda > 1:
            score += 10; plus.append("엔비디아 강세")
        elif nvda < -1:
            score -= 10; minus.append("엔비디아 약세")
    theme_words = {
        "power": ["전력", "변압기", "전력망", "전선", "데이터센터"],
        "robotics": ["로봇", "자동화", "스마트팩토리"],
        "display": ["디스플레이", "OLED", "애플", "패널"],
        "fx": ["환율", "달러", "원달러"],
    }.get(theme, [])
    for title in news:
        if any(w in title for w in theme_words):
            s = sentiment(title)
            if s > 0:
                score += min(5, s * 2); plus.append(title)
            elif s < 0:
                score -= min(5, abs(s) * 2); minus.append(title)
            else:
                score += 1; plus.append(title)
    return clamp(score), plus[:3], minus[:3]


def price_attractiveness(info, news):
    dna = info["dna"]
    score = 50
    plus, minus = [], []
    rule = DNA[dna]
    related = [t for t in news if any(k in t for k in rule["keywords"])]
    for title in related:
        s = sentiment(title)
        if s < 0:
            score += 8; plus.append("관련 약세 뉴스 → 적립식 가격매력 상승")
        elif s > 0:
            score -= 4; minus.append("관련 강세 뉴스 → 단기 가격 부담")
    if dna in ["sp500_etf", "semiconductor_etf", "global_ai", "power_infra"]:
        score += 10; plus.append("장기 적립식 대상")
    if dna in ["robotics", "display_turnaround"]:
        score -= 5; minus.append("고변동/턴어라운드는 물타기 주의")
    return clamp(score), plus[:3], minus[:3]


def analyze_stock(name, info, indicators, news, market):
    rule = DNA[info["dna"]]
    quality = clamp(rule["base_quality"])
    price, pplus, pminus = price_attractiveness(info, news)
    related = [t for t in news if any(k in t for k in rule["keywords"])]
    news_score = 50
    nplus, nminus = [], []
    for title in related:
        s = sentiment(title)
        if s > 0:
            news_score += min(8, s * 3); nplus.append(title)
        elif s < 0:
            news_score -= min(8, abs(s) * 3); nminus.append(title)
        else:
            news_score += 1; nplus.append(title)
    component = {
        "market": market,
        "price": price,
        "news": clamp(news_score),
        "quality": quality,
        "fx": theme_score("fx", indicators, news)[0],
        "semiconductor": theme_score("semiconductor", indicators, news)[0],
        "power": theme_score("power", indicators, news)[0],
        "robotics": theme_score("robotics", indicators, news)[0],
        "display": theme_score("display", indicators, news)[0],
        "ai": theme_score("ai", indicators, news)[0],
    }
    total = 0
    for key, w in rule["weights"].items():
        total += component.get(key, 50) * w / 100
    total = clamp(total)
    decision, reason = decision_for(info, quality, price, total)
    plus = (pplus + nplus + [f"{rule['label']} 성격 유지"])[:3]
    minus = (pminus + nminus + ["특별한 감점 뉴스 없음"])[:3]
    return {"name": name, "total": total, "quality": quality, "price": price, "decision": decision, "reason": reason, "plus": plus, "minus": minus, "rule": info["buy_rule"]}


def decision_for(info, quality, price, total):
    rule = info["buy_rule"]
    if "중지" in rule:
        if total >= 85 and quality >= 75:
            return "관망 해제 검토", "중지 종목이지만 점수 개선이 커서 소액 재검토 가능"
        return "매수 중지 유지", "현재 원칙상 추가매수 중지 종목"
    if quality < 60:
        return "오늘은 스킵", "가격보다 기업/업황 확인이 우선"
    if quality >= 75 and price >= 75:
        return "매수 유지", "좋은 자산의 조정은 평단가 관리 기회"
    if quality >= 75 and price >= 55:
        return "계획대로 매수", "기업 매력은 유지되며 가격 부담도 과하지 않음"
    if quality >= 75 and price < 55:
        return "속도 조절", "좋은 자산이지만 단기 가격 부담"
    if total >= 60:
        return "보유/소액", "큰 문제는 없으나 확신은 보통"
    return "오늘은 스킵", "점수와 근거가 약함"


def portfolio_health(results):
    total_value, weighted = 0.0, 0.0
    for r in results:
        info = PORTFOLIO[r["name"]]
        value = float(info["qty"]) * float(info["avg_price"])
        total_value += value
        weighted += r["total"] * value
    return clamp(weighted / total_value) if total_value else 50


def split_message(msg, limit=900):
    if len(msg) <= limit:
        return [msg]
    parts, cur = [], ""
    for block in msg.split("\n\n"):
        if len(cur) + len(block) + 2 <= limit:
            cur += ("\n\n" if cur else "") + block
        else:
            if cur:
                parts.append(cur)
            cur = block
    if cur:
        parts.append(cur)
    return parts


def make_global_message(indicators, market, plus, minus, news):
    msg = f"🌍 V40 장전 시장판단 리포트\n{now_kst()}\n\n"
    msg += f"📊 시장점수: {score_text(market)}\n\n"
    msg += "📌 해외 핵심 지표\n" + "\n".join(f"- {x['text']}" for x in indicators)
    msg += "\n\n✅ 긍정요인\n" + "\n".join(f"- {x}" for x in (plus or ["뚜렷한 긍정요인 제한"]))
    msg += "\n\n⚠️ 부담요인\n" + "\n".join(f"- {x}" for x in (minus or ["뚜렷한 부담요인 제한"]))
    msg += "\n\n📰 주요 뉴스\n" + "\n".join(f"- {x}" for x in news[:4])
    msg += "\n\n※ 자동 분석입니다. 최종 판단은 직접 결정하세요."
    return msg


def make_personal_message(results, health):
    ranked = sorted(results, key=lambda x: x["total"], reverse=True)
    top = ranked[0]
    msg = f"📊 V40 경규님 08시 투자판단\n{now_kst()}\n\n"
    msg += f"💼 포트폴리오 건강점수: {score_text(health)}\n\n"
    msg += f"🔥 오늘 1순위\n{top['name']} → {top['decision']}\n종합 {top['total']}점 / 기업 {top['quality']}점 / 가격 {top['price']}점\n이유: {top['reason']}\n"
    msg += "\n✅ 오늘의 행동표"
    for r in ranked:
        msg += f"\n\n{r['name']}\n- 판단: {r['decision']}\n- 종합: {r['total']}점 / {grade(r['total'])}등급\n- 기업: {r['quality']}점, 가격: {r['price']}점\n- 원칙: {r['rule']}\n- 이유: {r['reason']}"
    msg += "\n\n🎯 핵심 원칙\n좋은 자산이 하락한 날은 평단가를 낮출 기회입니다. 단, 기업점수가 낮은 종목은 싸 보여도 무리한 물타기를 피합니다."
    return msg


def refresh_kakao_token():
    global KAKAO_TOKEN, KAKAO_REFRESH_TOKEN
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        print("토큰 갱신 실패: REST API KEY 또는 REFRESH TOKEN 없음")
        return False
    try:
        res = requests.post("https://kauth.kakao.com/oauth/token", data={"grant_type": "refresh_token", "client_id": KAKAO_REST_API_KEY, "refresh_token": KAKAO_REFRESH_TOKEN}, timeout=15)
        data = res.json()
    except Exception as e:
        print("토큰 갱신 요청 실패:", e)
        return False
    if "access_token" not in data:
        print("토큰 갱신 실패", data)
        return False
    KAKAO_TOKEN = data["access_token"]
    KAKAO_REFRESH_TOKEN = data.get("refresh_token", KAKAO_REFRESH_TOKEN)
    print("카카오 토큰 자동 갱신 완료")
    return True


def send_kakao_once(text):
    template = {"object_type": "text", "text": text, "link": {"web_url": "https://finance.naver.com", "mobile_web_url": "https://finance.naver.com"}}
    return requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send", headers={"Authorization": f"Bearer {KAKAO_TOKEN}", "Content-Type": "application/x-www-form-urlencoded"}, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=15)


def send_kakao(msg):
    ok = True
    for i, part in enumerate(split_message(msg), 1):
        res = send_kakao_once(part)
        if res.status_code == 200:
            print(f"카카오 발송 성공 part {i}")
            continue
        print(f"카카오 발송 실패 part {i}: {res.status_code}", res.text)
        try:
            err = res.json()
        except Exception:
            err = {}
        if res.status_code == 401 or err.get("code") == -401:
            print("access_token 만료 감지 → 자동 갱신 시도")
            if refresh_kakao_token():
                res = send_kakao_once(part)
                print(res.status_code, res.text)
                if res.status_code == 200:
                    continue
        ok = False
    return ok


def main():
    print("🚀 V40 RUN_BOT 실행중")
    indicators = get_indicators()
    news = get_news()
    market, mplus, mminus = market_score(indicators)
    results = [analyze_stock(name, info, indicators, news, market) for name, info in PORTFOLIO.items()]
    health = portfolio_health(results)
    global_msg = make_global_message(indicators, market, mplus, mminus, news)
    personal_msg = make_personal_message(results, health)
    print(global_msg)
    print("\n" + "=" * 60 + "\n")
    print(personal_msg)
    ok1 = send_kakao(global_msg)
    ok2 = send_kakao(personal_msg)
    if not (ok1 and ok2):
        raise SystemExit("카카오톡 발송 실패")
    print("✅ V40 전체 완료")


if __name__ == "__main__":
    main()
