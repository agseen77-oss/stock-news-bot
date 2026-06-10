print("🚀 RUN_BOT 실행중")
# -*- coding: utf-8 -*-

print("🚀 RUN_BOT 실행중")

"""
V39: 경규님 투자 스타일 반영 버전
"""
- GitHub Actions 자동 실행용
- 구글뉴스 RSS + Yahoo Finance 지표
- 카카오톡 2개 발송
- 장기 적립식 / 하루 1주 매수 스타일 반영
"""

import os
import json
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv, set_key

ENV_FILE = ".env"
load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_TOKEN = os.getenv("KAKAO_TOKEN")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")

KST = timezone(timedelta(hours=9))


# =========================
# 카카오 토큰
# =========================
def refresh_kakao_token():
    global KAKAO_TOKEN, KAKAO_REFRESH_TOKEN

    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        print("토큰 갱신 실패: KAKAO_REST_API_KEY 또는 KAKAO_REFRESH_TOKEN 없음")
        return False

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }

    response = requests.post(url, data=data, timeout=15)
    result = response.json()

    if "access_token" not in result:
        print("토큰 갱신 실패")
        print(result)
        return False

    new_access_token = result["access_token"]
    KAKAO_TOKEN = new_access_token

    try:
        set_key(ENV_FILE, "KAKAO_TOKEN", new_access_token)
    except Exception:
        pass

    if "refresh_token" in result:
        KAKAO_REFRESH_TOKEN = result["refresh_token"]
        try:
            set_key(ENV_FILE, "KAKAO_REFRESH_TOKEN", KAKAO_REFRESH_TOKEN)
        except Exception:
            pass

    print("카카오 토큰 자동 갱신 완료")
    return True


# =========================
# 지표 수집
# =========================
def get_yahoo_quote(symbol, name):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
    params = {"range": "5d", "interval": "1d"}

    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res.raise_for_status()
        data = res.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]

        if len(closes) >= 2:
            prev = closes[-2]
            curr = closes[-1]
        else:
            curr = meta.get("regularMarketPrice")
            prev = meta.get("previousClose")

        if not curr or not prev:
            return {"name": name, "symbol": symbol, "ok": False, "change_pct": 0, "text": f"{name}: 수집 실패"}

        change_pct = (curr - prev) / prev * 100
        arrow = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "보합"

        return {
            "name": name,
            "symbol": symbol,
            "ok": True,
            "price": curr,
            "prev": prev,
            "change_pct": change_pct,
            "text": f"{name} {arrow} {change_pct:.2f}%"
        }

    except Exception as e:
        print(f"[지표 수집 실패] {name} {symbol}: {e}")
        return {"name": name, "symbol": symbol, "ok": False, "change_pct": 0, "text": f"{name}: 수집 실패"}


def get_global_indicators():
    targets = [
        ("^GSPC", "S&P500"),
        ("^IXIC", "나스닥"),
        ("^DJI", "다우"),
        ("SOXX", "미국 반도체 ETF"),
        ("NVDA", "엔비디아"),
        ("AMD", "AMD"),
        ("AVGO", "브로드컴"),
        ("CL=F", "WTI유가"),
        ("KRW=X", "원/달러 환율"),
    ]

    results = []
    for symbol, name in targets:
        results.append(get_yahoo_quote(symbol, name))
        time.sleep(0.2)

    return results


# =========================
# 뉴스 수집
# =========================
def get_news():
    keywords = [
        "미국 증시 나스닥 반도체",
        "필라델피아 반도체 엔비디아 HBM",
        "원달러 환율 외국인 코스피",
        "국제유가 전쟁 중동",
        "삼성전자 SK하이닉스 반도체",
        "전력설비 변압기 전력망",
        "로봇 자동화 스마트팩토리",
        "LG디스플레이 OLED 애플",
        "AI 인프라 데이터센터 전력"
    ]

    news_list = []

    for keyword in keywords:
        url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"

        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            items = root.findall(".//item")

            for item in items[:2]:
                title_tag = item.find("title")
                if title_tag is not None and title_tag.text:
                    title = title_tag.text.strip()
                    if title not in news_list:
                        news_list.append(title)

        except Exception as e:
            print(f"[뉴스 수집 실패] {keyword}: {e}")

    return news_list[:14] if news_list else ["뉴스 수집 실패: 지표 기반 브리핑만 진행합니다."]


# =========================
# 점수 로직
# =========================
holdings = {
    "TIGER 미국S&P500": {
        "keywords": ["미국", "S&P500", "나스닥", "엔비디아", "애플", "금리", "환율", "달러"],
        "base": 3,
        "style": "장기 적립 핵심"
    },
    "ACE 반도체 TOP3": {
        "keywords": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아"],
        "base": 2,
        "style": "반도체 핵심"
    },
    "TIGER 반도체 TOP10": {
        "keywords": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아"],
        "base": 1,
        "style": "반도체 분산"
    },
    "제룡전기": {
        "keywords": ["전력", "전선", "변압기", "전력망", "송전", "전기", "데이터센터"],
        "base": 1,
        "style": "전력 인프라"
    },
    "에스피시스템스": {
        "keywords": ["자동화", "로봇", "스마트팩토리", "공장", "설비", "2차전지"],
        "base": -1,
        "style": "변동성 주의"
    },
    "LG디스플레이": {
        "keywords": ["디스플레이", "OLED", "패널", "TV", "아이폰", "애플"],
        "base": -1,
        "style": "실적 확인 필요"
    },
}

positive_words = ["상승", "호재", "수주", "확대", "증가", "목표가", "돌파", "기대", "성장", "강세", "상향", "협력", "계약", "투자", "개선", "최대", "흑자", "반등", "랠리", "신고가", "급등", "완화", "인하", "수혜", "회복"]
negative_words = ["하락", "위기", "적자", "감소", "규제", "우려", "충격", "리스크", "약세", "폭락", "둔화", "하향", "중단", "악재", "손실", "급락", "전쟁", "긴장", "침체", "불안", "고금리", "인상"]


def score_news(title):
    score = 0
    for word in positive_words:
        if word in title:
            score += 1
    for word in negative_words:
        if word in title:
            score -= 1
    return score


def score_market(indicators):
    score = 0
    reasons = []
    data = {x["name"]: x for x in indicators}

    def pct(name):
        return data.get(name, {}).get("change_pct", 0)

    sp500 = pct("S&P500")
    nasdaq = pct("나스닥")
    soxx = pct("미국 반도체 ETF")
    nvda = pct("엔비디아")
    oil = pct("WTI유가")
    fx = pct("원/달러 환율")

    if sp500 > 0.3:
        score += 2
        reasons.append("S&P500 상승 → 글로벌 투자심리 긍정")
    elif sp500 < -0.3:
        score -= 2
        reasons.append("S&P500 하락 → 단기 변동성 주의")

    if nasdaq > 0.5:
        score += 3
        reasons.append("나스닥 상승 → 기술주·성장주에 긍정")
    elif nasdaq < -0.5:
        score -= 3
        reasons.append("나스닥 하락 → 기술주·성장주 부담")

    if soxx > 0.7:
        score += 4
        reasons.append("미국 반도체 ETF 강세 → 국내 반도체 긍정")
    elif soxx < -0.7:
        score -= 4
        reasons.append("미국 반도체 ETF 약세 → 국내 반도체 주의")

    if nvda > 1:
        score += 2
        reasons.append("엔비디아 강세 → AI/HBM 투자심리 개선")
    elif nvda < -1:
        score -= 2
        reasons.append("엔비디아 약세 → AI 반도체 심리 약화")

    if oil > 2:
        score -= 2
        reasons.append("유가 급등 → 인플레이션·비용 부담")
    elif oil < -2:
        score += 1
        reasons.append("유가 하락 → 물가 부담 완화")

    if fx > 0.5:
        score -= 2
        reasons.append("원/달러 환율 상승 → 외국인 수급 부담")
    elif fx < -0.5:
        score += 1
        reasons.append("원/달러 환율 하락 → 외국인 수급 우호")

    return score, reasons


def analyze_holdings(news_list, indicators):
    scores = {name: data["base"] for name, data in holdings.items()}
    reasons = {name: [f"기본 성격: {data['style']}"] for name, data in holdings.items()}

    for title in news_list:
        news_score = score_news(title)
        for name, data in holdings.items():
            for key in data["keywords"]:
                if key in title:
                    impact = news_score if news_score != 0 else 1
                    scores[name] += impact
                    reasons[name].append(title)
                    break

    data = {x["name"]: x for x in indicators}
    sp500 = data.get("S&P500", {}).get("change_pct", 0)
    nasdaq = data.get("나스닥", {}).get("change_pct", 0)
    soxx = data.get("미국 반도체 ETF", {}).get("change_pct", 0)
    nvda = data.get("엔비디아", {}).get("change_pct", 0)
    fx = data.get("원/달러 환율", {}).get("change_pct", 0)

    if sp500 > 0.3:
        scores["TIGER 미국S&P500"] += 3
        reasons["TIGER 미국S&P500"].append("S&P500 상승으로 매일 적립 전략 유지 가능")
    elif sp500 < -0.3:
        scores["TIGER 미국S&P500"] -= 1
        reasons["TIGER 미국S&P500"].append("S&P500 하락이지만 장기 적립 관점에서는 분할매수 가능")

    if soxx > 0.7 or nvda > 1:
        for h in ["ACE 반도체 TOP3", "TIGER 반도체 TOP10"]:
            scores[h] += 4
            reasons[h].append("미국 반도체/엔비디아 강세로 반도체 ETF 우호적")
    elif soxx < -0.7 or nvda < -1:
        for h in ["ACE 반도체 TOP3", "TIGER 반도체 TOP10"]:
            scores[h] -= 3
            reasons[h].append("미국 반도체/엔비디아 약세로 오늘은 추가매수 신중")

    if nasdaq > 0.5:
        scores["에스피시스템스"] += 1
        reasons["에스피시스템스"].append("나스닥 강세는 자동화·성장주 심리에 약한 긍정")
    elif nasdaq < -0.5:
        scores["에스피시스템스"] -= 1
        reasons["에스피시스템스"].append("나스닥 약세는 자동화·성장주에 부담")

    if fx > 0.5:
        scores["LG디스플레이"] -= 1
        reasons["LG디스플레이"].append("환율 상승은 시장 수급 부담")
    elif fx < -0.5:
        scores["LG디스플레이"] += 1
        reasons["LG디스플레이"].append("환율 하락은 수급에 비교적 우호적")

    return scores, reasons


# =========================
# 메시지 생성
# =========================
def star(score):
    if score >= 7:
        return "⭐⭐⭐⭐⭐ 매우 긍정"
    if score >= 4:
        return "⭐⭐⭐⭐ 긍정"
    if score >= 1:
        return "⭐⭐⭐ 보통"
    if score >= -2:
        return "⭐⭐ 주의"
    return "⭐ 부정"


def action_for(name, score, market_score):
    if name == "TIGER 미국S&P500":
        if market_score <= -5:
            return "1주 매수 유지 또는 금액 줄여 적립"
        return "1주 매수 유지"

    if score >= 5:
        return "소액 추가매수 가능"
    if score >= 1:
        return "보유 유지"
    if score >= -2:
        return "관망"
    return "추가매수 보류"


def market_view(score):
    if score >= 7:
        return "강세 예상"
    if score >= 3:
        return "강보합 예상"
    if score > -3:
        return "보합권 예상"
    if score > -7:
        return "약세 주의"
    return "하락 위험"


def make_global_message(indicators, market_score, market_reasons, news):
    today = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    msg = f"🌍 V39 밤사이 글로벌 브리핑\n{today}\n\n"
    msg += f"📌 오늘 한국장 예상: {market_view(market_score)}\n"
    msg += f"시장 점수: {market_score}점\n\n"

    msg += "📊 핵심 해외 지표\n"
    for x in indicators:
        msg += f"- {x['text']}\n"

    msg += "\n🔎 핵심 판단\n"
    if market_reasons:
        for r in market_reasons[:5]:
            msg += f"- {r}\n"
    else:
        msg += "- 뚜렷한 방향성은 약해 보합권 가능성\n"

    msg += "\n📰 밤사이 주요 뉴스\n"
    for n in news[:5]:
        msg += f"- {n}\n"

    msg += "\n※ 지표+뉴스 자동 분석입니다."
    return msg


def make_personal_message(market_score, scores, reasons):
    today = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best, best_score = ranked[0]

    msg = f"📊 V39 경규님 전용 투자비서\n{today}\n\n"
    msg += "⭐ 오늘의 1순위 후보\n"
    msg += f"{best}\n"
    msg += f"판단: {action_for(best, best_score, market_score)}\n"
    msg += f"이유: {reasons[best][-1] if reasons[best] else '점수 우위'}\n\n"

    msg += "💼 보유종목별 행동지침\n"
    for name, score in ranked:
        msg += f"\n{name}\n"
        msg += f"{star(score)} / 점수 {score}\n"
        msg += f"행동: {action_for(name, score, market_score)}\n"
        if reasons[name]:
            msg += f"근거: {reasons[name][-1]}\n"

    msg += "\n🎯 경규님 스타일 기준 결론\n"
    if market_score <= -5:
        msg += "오늘은 시장 부담이 큽니다. 그래도 장기 적립식인 TIGER 미국S&P500은 무리 없는 범위에서 유지하고, 반도체·개별주는 관망이 좋습니다.\n"
    elif market_score >= 5:
        msg += "오늘은 분위기가 좋습니다. S&P500 적립은 유지하고, 반도체 ETF는 소액 추가매수 후보로 볼 수 있습니다.\n"
    else:
        msg += "오늘은 중립권입니다. S&P500 1주 적립은 유지, 반도체와 개별주는 급하게 늘리지 않는 전략이 좋습니다.\n"

    msg += "\n※ 자동 분석이며 최종 판단은 직접 확인하세요."
    return msg


# =========================
# 카카오 전송
# =========================
def send_kakao_once(message):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {KAKAO_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    template_object = {
        "object_type": "text",
        "text": message[:950],
        "link": {
            "web_url": "https://finance.naver.com",
            "mobile_web_url": "https://finance.naver.com"
        }
    }

    data = {"template_object": json.dumps(template_object, ensure_ascii=False)}
    return requests.post(url, headers=headers, data=data, timeout=15)


def send_kakao(message):
    response = send_kakao_once(message)

    if response.status_code == 200:
        print(200)
        print(response.text)
        return True

    print(response.status_code)
    print(response.text)

    try:
        result = response.json()
    except Exception:
        result = {}

    if response.status_code == 401 or result.get("code") == -401:
        print("access_token 만료 감지 → 자동 갱신 시도")
        if refresh_kakao_token():
            response = send_kakao_once(message)
            print(response.status_code)
            print(response.text)
            return response.status_code == 200

    return False


if __name__ == "__main__":
    indicators = get_global_indicators()
    market_score, market_reasons = score_market(indicators)
    news = get_news()
    scores, reasons = analyze_holdings(news, indicators)

    global_msg = make_global_message(indicators, market_score, market_reasons, news)
    personal_msg = make_personal_message(market_score, scores, reasons)

    print(global_msg)
    print("\n" + "=" * 50 + "\n")
    print(personal_msg)

    print("\n[카카오톡 1번 발송: V39 글로벌]")
    ok1 = send_kakao(global_msg)

    print("\n[카카오톡 2번 발송: V39 경규님 전용]")
    ok2 = send_kakao(personal_msg)

    if not (ok1 and ok2):
        raise SystemExit("카카오톡 발송 실패")        
