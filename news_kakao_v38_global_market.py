# -*- coding: utf-8 -*-
"""
V38: 글로벌 지표 + 구글뉴스 RSS + 경규님 전용 보유종목 브리핑
- GitHub Actions용
- .env 없이 GitHub Secrets 환경변수 사용 가능
- 카카오톡 2개 발송
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
    except Exception as e:
        print("로컬 .env access token 저장 생략:", e)

    if "refresh_token" in result:
        new_refresh_token = result["refresh_token"]
        KAKAO_REFRESH_TOKEN = new_refresh_token
        try:
            set_key(ENV_FILE, "KAKAO_REFRESH_TOKEN", new_refresh_token)
        except Exception as e:
            print("로컬 .env refresh token 저장 생략:", e)

    print("카카오 토큰 자동 갱신 완료")
    return True


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

        if change_pct > 0:
            arrow = "▲"
        elif change_pct < 0:
            arrow = "▼"
        else:
            arrow = "보합"

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
    indicators = [
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
    for symbol, name in indicators:
        results.append(get_yahoo_quote(symbol, name))
        time.sleep(0.2)

    return results


def score_indicators(indicators):
    score = 0
    reasons = []
    data = {x["name"]: x for x in indicators}

    def pct(name):
        return data.get(name, {}).get("change_pct", 0)

    nasdaq = pct("나스닥")
    sp500 = pct("S&P500")
    soxx = pct("미국 반도체 ETF")
    nvda = pct("엔비디아")
    oil = pct("WTI유가")
    fx = pct("원/달러 환율")

    if sp500 > 0.3:
        score += 2
        reasons.append("S&P500 상승으로 글로벌 위험자산 심리 개선")
    elif sp500 < -0.3:
        score -= 2
        reasons.append("S&P500 하락으로 투자심리 약화")

    if nasdaq > 0.5:
        score += 3
        reasons.append("나스닥 상승으로 성장주·기술주 분위기 긍정")
    elif nasdaq < -0.5:
        score -= 3
        reasons.append("나스닥 하락으로 성장주 부담")

    if soxx > 0.7:
        score += 4
        reasons.append("미국 반도체 강세로 국내 반도체 업종에 긍정")
    elif soxx < -0.7:
        score -= 4
        reasons.append("미국 반도체 약세로 국내 반도체 업종 부담")

    if nvda > 1:
        score += 2
        reasons.append("엔비디아 강세로 AI·HBM 관련주 관심")
    elif nvda < -1:
        score -= 2
        reasons.append("엔비디아 약세로 AI 반도체 투자심리 약화")

    if oil > 2:
        score -= 2
        reasons.append("유가 급등은 인플레이션·비용 부담 요인")
    elif oil < -2:
        score += 1
        reasons.append("유가 하락은 인플레이션 부담 완화 요인")

    if fx > 0.5:
        score -= 2
        reasons.append("원/달러 환율 상승은 외국인 수급 부담 가능성")
    elif fx < -0.5:
        score += 1
        reasons.append("원/달러 환율 하락은 외국인 수급에 비교적 우호적")

    return score, reasons


def get_news():
    keywords = [
        "미국 증시 나스닥 반도체",
        "필라델피아 반도체 엔비디아 HBM",
        "원달러 환율 외국인 코스피",
        "국제유가 전쟁 중동",
        "삼성전자 SK하이닉스 반도체",
        "전력설비 변압기 전력망",
        "로봇 자동화 스마트팩토리",
        "LG디스플레이 OLED 애플"
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

    if not news_list:
        news_list = [
            "뉴스 수집 실패: 구글뉴스 RSS 접속 제한 가능성",
            "지표 기반 브리핑은 계속 진행됩니다."
        ]

    return news_list[:12]


holdings = {
    "TIGER 미국S&P500": ["미국", "S&P500", "나스닥", "엔비디아", "애플", "금리", "환율", "달러"],
    "ACE 반도체 TOP3": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아"],
    "TIGER 반도체 TOP10": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아"],
    "제룡전기": ["전력", "전선", "변압기", "전력망", "송전", "전기"],
    "에스피시스템스": ["자동화", "로봇", "스마트팩토리", "공장", "설비", "2차전지"],
    "LG디스플레이": ["디스플레이", "OLED", "패널", "TV", "아이폰", "애플"],
}

positive_words = ["상승", "호재", "수주", "확대", "증가", "목표가", "돌파", "기대", "성장", "강세", "상향", "협력", "계약", "투자", "개선", "최대", "흑자", "반등", "랠리", "신고가", "급등", "완화", "인하", "수혜"]
negative_words = ["하락", "위기", "적자", "감소", "규제", "우려", "충격", "리스크", "약세", "폭락", "둔화", "하향", "중단", "악재", "손실", "급락", "전쟁", "긴장", "침체", "불안", "고금리", "인상"]


def score_news(news):
    score = 0
    for word in positive_words:
        if word in news:
            score += 2
    for word in negative_words:
        if word in news:
            score -= 2
    return score


def analyze_holdings(news_list, indicators):
    holding_scores = {name: 0 for name in holdings}
    holding_reasons = {name: [] for name in holdings}

    for news in news_list:
        score = score_news(news)
        for holding, keywords in holdings.items():
            for key in keywords:
                if key in news:
                    impact = score if score != 0 else 1
                    holding_scores[holding] += impact
                    holding_reasons[holding].append(news)
                    break

    data = {x["name"]: x for x in indicators}
    nasdaq = data.get("나스닥", {}).get("change_pct", 0)
    sp500 = data.get("S&P500", {}).get("change_pct", 0)
    soxx = data.get("미국 반도체 ETF", {}).get("change_pct", 0)
    nvda = data.get("엔비디아", {}).get("change_pct", 0)
    fx = data.get("원/달러 환율", {}).get("change_pct", 0)

    if sp500 > 0.3:
        holding_scores["TIGER 미국S&P500"] += 3
        holding_reasons["TIGER 미국S&P500"].append("S&P500 상승으로 장기 적립식 ETF에 우호적")
    elif sp500 < -0.3:
        holding_scores["TIGER 미국S&P500"] -= 2
        holding_reasons["TIGER 미국S&P500"].append("S&P500 하락으로 단기 변동성 주의")

    if soxx > 0.7 or nvda > 1:
        for h in ["ACE 반도체 TOP3", "TIGER 반도체 TOP10"]:
            holding_scores[h] += 4
            holding_reasons[h].append("미국 반도체·엔비디아 강세로 국내 반도체 수급 기대")
    elif soxx < -0.7 or nvda < -1:
        for h in ["ACE 반도체 TOP3", "TIGER 반도체 TOP10"]:
            holding_scores[h] -= 4
            holding_reasons[h].append("미국 반도체·엔비디아 약세로 국내 반도체 단기 부담")

    if nasdaq > 0.5:
        holding_scores["에스피시스템스"] += 1
        holding_reasons["에스피시스템스"].append("나스닥 강세는 성장·자동화 테마에 약한 긍정")
    elif nasdaq < -0.5:
        holding_scores["에스피시스템스"] -= 1
        holding_reasons["에스피시스템스"].append("나스닥 약세는 성장·자동화 테마에 부담")

    if fx > 0.5:
        holding_scores["LG디스플레이"] -= 1
        holding_reasons["LG디스플레이"].append("환율 상승은 시장 수급 부담 요인")
    elif fx < -0.5:
        holding_scores["LG디스플레이"] += 1
        holding_reasons["LG디스플레이"].append("환율 하락은 외국인 수급에 비교적 우호적")

    return holding_scores, holding_reasons


def star_rating(score):
    if score >= 7:
        return "⭐⭐⭐⭐⭐ 매우 긍정"
    elif score >= 4:
        return "⭐⭐⭐⭐ 긍정"
    elif score >= 1:
        return "⭐⭐⭐ 약긍정"
    elif score == 0:
        return "⭐⭐⭐ 중립"
    elif score >= -3:
        return "⭐⭐ 주의"
    else:
        return "⭐ 부정"


def market_view(score):
    if score >= 7:
        return "강세 예상"
    elif score >= 3:
        return "강보합 예상"
    elif score > -3:
        return "보합권 예상"
    elif score > -7:
        return "약세 주의"
    return "하락 위험"


def confidence(score, count):
    total = min(abs(score) * 8 + count * 3, 95)
    return max(int(total), 35)


def make_global_message(indicators, indicator_score, indicator_reasons, news_list):
    today = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    message = f"🌍 V38 밤사이 글로벌 증시 브리핑\n{today}\n\n"
    message += f"📌 오늘 한국장 예상: {market_view(indicator_score)}\n"
    message += f"시장 점수: {indicator_score}점 / 신뢰도 {confidence(indicator_score, len(indicator_reasons))}%\n\n"

    message += "📊 해외 주요 지표\n"
    for x in indicators:
        message += f"- {x['text']}\n"

    message += "\n🔎 판단 근거\n"
    if indicator_reasons:
        for r in indicator_reasons[:5]:
            message += f"- {r}\n"
    else:
        message += "- 뚜렷한 방향성은 약해 보합권 흐름 가능성\n"

    message += "\n📰 주요 뉴스\n"
    for n in news_list[:5]:
        message += f"- {n}\n"

    message += "\n※ Yahoo Finance 지표 + 구글뉴스 RSS 기반 자동 브리핑입니다."
    return message


def pick_best_holding(holding_scores):
    sorted_holdings = sorted(holding_scores.items(), key=lambda x: x[1], reverse=True)
    best_name, best_score = sorted_holdings[0]

    if best_score <= 0:
        return "TIGER 미국S&P500", "시장 방향성이 약하거나 불안할 때는 장기 분산형 ETF가 가장 안정적입니다."

    return best_name, f"오늘 지표·뉴스 기준 보유종목 중 점수가 가장 높습니다. 점수 {best_score}점."


def make_personal_message(indicator_score, holding_scores, holding_reasons):
    today = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    best_name, best_reason = pick_best_holding(holding_scores)

    message = f"📊 V38 경규님 전용 투자 브리핑\n{today}\n\n"
    message += "⭐ 오늘의 1순위 후보\n"
    message += f"{best_name}\n"
    message += f"이유: {best_reason}\n\n"

    message += "💼 보유종목 상황\n"
    sorted_holdings = sorted(holding_scores.items(), key=lambda x: x[1], reverse=True)

    for name, score in sorted_holdings:
        reasons = holding_reasons[name]
        message += f"\n{name}\n"
        message += f"{star_rating(score)} / 점수 {score}\n"
        if reasons:
            message += f"· {reasons[0]}\n"
        else:
            message += "· 관련 뉴스 없음\n"

    message += "\n🎯 오늘의 행동지침\n"
    if indicator_score >= 5:
        message += "분위기는 긍정적입니다. 보유 ETF 중심으로 소액 분할매수 가능. 단, 급등 출발 시 추격매수는 피하세요.\n"
    elif indicator_score <= -5:
        message += "시장 부담이 큽니다. 신규매수는 줄이고 현금 비중 유지, 보유종목 변동성 점검이 좋습니다.\n"
    else:
        message += "보합권입니다. 무리하지 말고 S&P500 또는 반도체 ETF 중심으로 천천히 접근하는 전략이 좋습니다.\n"

    message += "\n※ 자동 분석입니다. 최종 투자 판단은 직접 확인하세요."
    return message


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
    indicator_score, indicator_reasons = score_indicators(indicators)
    news = get_news()
    holding_scores, holding_reasons = analyze_holdings(news, indicators)

    global_message = make_global_message(indicators, indicator_score, indicator_reasons, news)
    personal_message = make_personal_message(indicator_score, holding_scores, holding_reasons)

    print(global_message)
    print("\n" + "=" * 50 + "\n")
    print(personal_message)

    print("\n[카카오톡 1번 발송: V38 글로벌 증시]")
    ok1 = send_kakao(global_message)

    print("\n[카카오톡 2번 발송: V38 경규님 전용]")
    ok2 = send_kakao(personal_message)

    if not (ok1 and ok2):
        raise SystemExit("카카오톡 발송 실패")
