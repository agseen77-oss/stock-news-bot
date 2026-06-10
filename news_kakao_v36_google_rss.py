# -*- coding: utf-8 -*-

import requests
import os
from dotenv import load_dotenv, set_key
from datetime import datetime
import json
import xml.etree.ElementTree as ET
from urllib.parse import quote

ENV_FILE = ".env"

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_TOKEN = os.getenv("KAKAO_TOKEN")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")


def refresh_kakao_token():
    global KAKAO_TOKEN, KAKAO_REFRESH_TOKEN

    url = "https://kauth.kakao.com/oauth/token"

    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }

    response = requests.post(url, data=data)
    result = response.json()

    if "access_token" not in result:
        print("토큰 갱신 실패")
        print(result)
        return False

    new_access_token = result["access_token"]
    KAKAO_TOKEN = new_access_token
    set_key(ENV_FILE, "KAKAO_TOKEN", new_access_token)

    if "refresh_token" in result:
        new_refresh_token = result["refresh_token"]
        KAKAO_REFRESH_TOKEN = new_refresh_token
        set_key(ENV_FILE, "KAKAO_REFRESH_TOKEN", new_refresh_token)

    print("카카오 토큰 자동 갱신 완료")
    return True


def get_news():
    """
    PythonAnywhere 무료 계정에서 네이버 뉴스 접속이 막힐 수 있어서
    구글뉴스 RSS 방식으로 뉴스 제목을 수집합니다.
    """
    keywords = [
        "미국 증시",
        "나스닥",
        "필라델피아 반도체",
        "엔비디아",
        "환율",
        "국제유가",
        "전쟁",
        "코스피",
        "삼성전자",
        "SK하이닉스",
        "전력설비",
        "AI 반도체"
    ]

    news_list = []

    for keyword in keywords:
        url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"

        try:
            res = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
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
            "뉴스 수집 실패: 구글뉴스 RSS 접속이 제한되었습니다.",
            "카카오 전송 기능 확인용 임시 뉴스입니다.",
            "PythonAnywhere 무료 계정의 외부 접속 제한 여부를 확인해야 합니다."
        ]

    return news_list[:15]


holdings = {
    "ACE 반도체 TOP3": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아"],
    "TIGER 반도체 TOP10": ["반도체", "AI", "삼성전자", "SK하이닉스", "한미반도체", "HBM", "엔비디아"],
    "TIGER 미국S&P500": ["미국", "S&P500", "나스닥", "엔비디아", "테슬라", "애플", "금리", "환율", "달러"],
    "제룡전기": ["전력", "전선", "변압기", "전력망", "송전", "전기"],
    "에스피시스템스": ["자동화", "로봇", "스마트팩토리", "공장", "설비", "2차전지"],
    "LG디스플레이": ["디스플레이", "OLED", "패널", "TV", "아이폰", "애플"],
}

positive_words = [
    "상승", "호재", "수주", "확대", "증가", "IPO", "목표가", "목표치",
    "돌파", "참여", "배정", "기대", "성장", "베팅", "강세", "상향",
    "협력", "계약", "투자", "개선", "최대", "흑자", "반등", "랠리",
    "신고가", "급등", "완화", "인하", "수혜"
]

negative_words = [
    "하락", "위기", "적자", "감소", "규제", "불공정", "우려", "충격",
    "리스크", "약세", "폭락", "둔화", "하향", "중단", "악재", "손실",
    "급락", "전쟁", "긴장", "침체", "불안", "고금리", "인상"
]


def score_news(news):
    score = 0

    for word in positive_words:
        if word in news:
            score += 2

    for word in negative_words:
        if word in news:
            score -= 2

    return score


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


def confidence(score, news_count):
    base = min(abs(score) * 10, 70)
    news_bonus = min(news_count * 5, 20)
    total = base + news_bonus

    if total < 30:
        total = 30

    if total > 95:
        total = 95

    return total


def analyze(news_list):
    market_score = 0
    holding_scores = {name: 0 for name in holdings}
    holding_reasons = {name: [] for name in holdings}

    for news in news_list:
        score = score_news(news)
        market_score += score

        for holding, keywords in holdings.items():
            for key in keywords:
                if key in news:
                    impact = score if score != 0 else 1
                    holding_scores[holding] += impact
                    holding_reasons[holding].append(news)
                    break

    return market_score, holding_scores, holding_reasons


def make_global_message(news_list, market_score):
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"🌍 밤사이 글로벌 뉴스 브리핑\n{today}\n\n"

    message += "📊 오늘 시장 분위기\n"
    message += f"{star_rating(market_score)}\n"
    message += f"시장 점수 {market_score} / 신뢰도 {confidence(market_score, len(news_list))}%\n\n"

    message += "📰 주요 이슈\n"
    for n in news_list[:8]:
        message += f"- {n}\n"

    message += "\n📌 체크 포인트\n"
    message += "- 미국 증시, 나스닥, 반도체 지수 흐름 확인\n"
    message += "- 환율 상승 시 외국인 수급 주의\n"
    message += "- 유가 상승 시 항공·화학 부담, 정유·에너지 관심\n"
    message += "- 반도체 강세 뉴스는 국내 삼성전자·SK하이닉스·반도체 ETF에 영향\n"

    message += "\n\n※ 구글뉴스 RSS 기반 자동 요약입니다."
    return message


def pick_best_holding(holding_scores):
    sorted_holdings = sorted(holding_scores.items(), key=lambda x: x[1], reverse=True)
    best_name, best_score = sorted_holdings[0]

    if best_score <= 0:
        return "TIGER 미국S&P500", "개별 이슈가 약할 때는 장기 분산형 ETF가 가장 안정적입니다."

    reason = f"오늘 뉴스 키워드 기준으로 보유종목 중 관련 점수가 가장 높습니다. 점수 {best_score}점."
    return best_name, reason


def make_personal_message(news_list, market_score, holding_scores, holding_reasons):
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    best_name, best_reason = pick_best_holding(holding_scores)

    message = f"📊 경규님 전용 투자 브리핑\n{today}\n\n"

    message += "⭐ 오늘의 1순위 추천\n"
    message += f"{best_name}\n"
    message += f"이유: {best_reason}\n\n"

    message += "💼 보유종목 상황\n"

    sorted_holdings = sorted(holding_scores.items(), key=lambda x: x[1], reverse=True)

    for name, score in sorted_holdings:
        related_news = holding_reasons[name]
        message += f"\n{name}\n"
        message += f"{star_rating(score)}\n"
        message += f"점수 {score} / 신뢰도 {confidence(score, len(related_news))}%\n"

        if related_news:
            message += "관련 뉴스:\n"
            for r in related_news[:1]:
                message += f"· {r}\n"
        else:
            message += "관련 뉴스: 없음\n"

    message += "\n🎯 오늘의 행동지침\n"
    if market_score >= 5:
        message += "시장 분위기는 긍정적입니다. 무리한 추격매수보다는 보유 ETF 중심으로 1주 또는 소액 분할매수가 유리합니다.\n"
    elif market_score <= -5:
        message += "시장 분위기는 불안합니다. 신규매수는 줄이고 보유종목 점검과 현금 비중 유지가 좋습니다.\n"
    else:
        message += "시장은 중립권입니다. 급하게 움직이기보다 S&P500 또는 반도체 ETF 중심으로 천천히 접근하는 전략이 좋습니다.\n"

    message += "\n※ 자동 키워드 분석입니다. 최종 투자 판단은 직접 확인하세요."
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

    data = {
        "template_object": json.dumps(template_object, ensure_ascii=False)
    }

    response = requests.post(url, headers=headers, data=data)
    return response


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
    news = get_news()
    market_score, holding_scores, holding_reasons = analyze(news)

    global_message = make_global_message(news, market_score)
    personal_message = make_personal_message(news, market_score, holding_scores, holding_reasons)

    print(global_message)
    print("\n" + "=" * 50 + "\n")
    print(personal_message)

    print("\n[카카오톡 1번 발송: 글로벌 뉴스]")
    send_kakao(global_message)

    print("\n[카카오톡 2번 발송: 경규님 전용 투자 브리핑]")
    send_kakao(personal_message)
