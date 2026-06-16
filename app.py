
import json, re
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st
import requests
import xml.etree.ElementTree as ET

APP_TITLE = "🧭 스톡 컴퍼스 V91-2.3"
APP_SUBTITLE = "경규님 전용 개인용 AI 투자비서 · 온도계 연결 복구"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
HISTORY_FILE = DATA_DIR / "history.json"
SELL_FILE = DATA_DIR / "sell_records.json"
RECOMMEND_FILE = DATA_DIR / "recommend_history.json"
RECOMMEND_CACHE_FILE = DATA_DIR / "recommend_cache.json"

DEFAULT_DATA = {
    "profile": {
        "name": "경규님",
        "style": "균형형 성장투자자",
        "method": "장기 적립식",
        "principal": 5000000,
        "target_return": 15
    },
    "holdings": [
        {"name": "에스피시스템스", "qty": 4, "avg": 7520},
        {"name": "제룡전기", "qty": 8, "avg": 52463},
        {"name": "ACE AI반도체 TOP3", "qty": 22, "avg": 58561},
        {"name": "KODEX 미국S&P500", "qty": 6, "avg": 25680},
        {"name": "LG디스플레이", "qty": 16, "avg": 15113},
    ]
}

st.set_page_config(page_title="스톡 컴퍼스 V91-2.3", page_icon="🧭", layout="centered")

def sf(v, d=0):
    try:
        return float(v)
    except Exception:
        return d

def won(v):
    try:
        return f"{float(v):,.0f}원"
    except Exception:
        return "0원"

def save_data(data):
    DATA_DIR.mkdir(exist_ok=True)
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        if "holdings" in d:
            return d
    except Exception:
        pass
    return None

def migrate_old_files():
    for p in [
        Path("data/portfolio.json"),
        Path("../stock_compass_v75_4_single_action_rebalance/data/portfolio.json"),
        Path("../stock_compass_v75_3_action_engine/data/portfolio.json"),
        Path("../stock_compass_v75_2_replace_app_only/data/portfolio.json"),
        Path("../stock_compass_v75_1_personal_app/data/portfolio.json"),
    ]:
        if p.exists():
            d = load_json(p)
            if d and d.get("holdings"):
                return d
    return None

def load_data():
    if PORTFOLIO_FILE.exists():
        d = load_json(PORTFOLIO_FILE)
        if d:
            return normalize_profile(d)
    m = migrate_old_files()
    if m:
        save_data(m)
        return normalize_profile(m)
    save_data(DEFAULT_DATA)
    return DEFAULT_DATA.copy()

def normalize_profile(d):
    p = d.setdefault("profile", {})
    if "principal" not in p:
        p["principal"] = sf(p.get("monthly_cash", 5000000), 5000000)
    if "target_return" not in p:
        p["target_return"] = 15
    p.setdefault("name", "경규님")
    p.setdefault("style", "균형형 성장투자자")
    p.setdefault("method", "장기 적립식")
    d.setdefault("holdings", [])
    return d

def norm(name):
    n = str(name).strip()
    aliases = {
        "ACE 반도체 TOP3": "ACE AI반도체 TOP3",
        "KODEX 미국 S&P500": "KODEX 미국S&P500",
        "TIGER 미국 S&P500": "TIGER 미국S&P500",
        "NVDA": "엔비디아",
        "NVIDIA": "엔비디아",
        "nvidia": "엔비디아",
        "nvda": "엔비디아",
    }
    return aliases.get(n, n)

def code_map():
    return {
        # 기존 보유/관심
        "제룡전기": "033100",
        "에스피시스템스": "317830",
        "LG디스플레이": "034220",
        "ACE AI반도체 TOP3": "469150",
        "KODEX 미국S&P500": "379800",
        "TIGER 미국S&P500": "360750",

        # 반도체 / AI
        "삼성전자": "005930",
        "SK하이닉스": "000660",
        "한미반도체": "042700",
        "ISC": "095340",
        "하나마이크론": "067310",
        "이수페타시스": "007660",
        "리노공업": "058470",
        "동진쎄미켐": "005290",
        "솔브레인": "357780",
        "원익IPS": "240810",
        "HPSP": "403870",
        "DB하이텍": "000990",
        "테크윙": "089030",
        "심텍": "222800",
        "대덕전자": "353200",
        "주성엔지니어링": "036930",

        # 전력 / 전선 / 에너지
        "대한전선": "001440",
        "LS ELECTRIC": "010120",
        "HD현대일렉트릭": "267260",
        "효성중공업": "298040",
        "두산에너빌리티": "034020",
        "LS": "006260",
        "일진전기": "103590",
        "가온전선": "000500",
        "대원전선": "006340",
        "한전기술": "052690",
        "한국전력": "015760",
        "현대건설": "000720",

        # 2차전지
        "에코프로비엠": "247540",
        "에코프로": "086520",
        "포스코퓨처엠": "003670",
        "POSCO홀딩스": "005490",
        "LG에너지솔루션": "373220",
        "삼성SDI": "006400",
        "엘앤에프": "066970",
        "천보": "278280",
        "SK아이이테크놀로지": "361610",
        "코스모신소재": "005070",
        "나노신소재": "121600",

        # 방산 / 우주 / 조선
        "한화에어로스페이스": "012450",
        "LIG넥스원": "079550",
        "현대로템": "064350",
        "한국항공우주": "047810",
        "한화시스템": "272210",
        "HD현대중공업": "329180",
        "한화오션": "042660",
        "삼성중공업": "010140",

        # 로봇 / 자동화
        "레인보우로보틱스": "277810",
        "두산로보틱스": "454910",
        "로보티즈": "108490",
        "유진로봇": "056080",
        "로보스타": "090360",
        "에스비비테크": "389500",
        "뉴로메카": "348340",

        # 자동차 / 전장
        "현대차": "005380",
        "기아": "000270",
        "현대모비스": "012330",
        "HL만도": "204320",
        "성우하이텍": "015750",
        "에스엘": "005850",

        # 플랫폼 / 인터넷 / 게임
        "NAVER": "035420",
        "카카오": "035720",
        "크래프톤": "259960",
        "엔씨소프트": "036570",
        "넷마블": "251270",
        "펄어비스": "263750",

        # 바이오 / 헬스케어
        "셀트리온": "068270",
        "삼성바이오로직스": "207940",
        "알테오젠": "196170",
        "유한양행": "000100",
        "한미약품": "128940",
        "HLB": "028300",
        "리가켐바이오": "141080",
        "오스코텍": "039200",

        # 금융 / 배당
        "KB금융": "105560",
        "신한지주": "055550",
        "하나금융지주": "086790",
        "우리금융지주": "316140",
        "삼성화재": "000810",
        "메리츠금융지주": "138040",

        # 소비 / 화장품 / 음식료
        "아모레퍼시픽": "090430",
        "LG생활건강": "051900",
        "코스맥스": "192820",
        "한국콜마": "161890",
        "CJ제일제당": "097950",
        "농심": "004370",
        "삼양식품": "003230",

        # 미국 대형주 별칭
        "엔비디아": None,
        "브로드컴": None,
        "애플": None,
        "마이크로소프트": None,
        "테슬라": None,
        "아마존": None,
        "구글": None,
        "메타": None,
    }
def fallback_price(name):
    return {
        "제룡전기": 52500,
        "에스피시스템스": 6900,
        "LG디스플레이": 15110,
        "ACE AI반도체 TOP3": 58560,
        "KODEX 미국S&P500": 25680,
        "TIGER 미국S&P500": 20000,
        "엔비디아": 300000,
        "대한전선": 15000,
        "에코프로비엠": 150000,
        "에코프로": 80000,
        "LS ELECTRIC": 180000,
        "두산에너빌리티": 25000,
        "현대차": 250000,
        "기아": 110000,
        "NAVER": 200000,
        "카카오": 50000,
        "셀트리온": 180000,
        "삼성바이오로직스": 900000,
        "포스코퓨처엠": 250000,
        "HD현대일렉트릭": 300000,
        "효성중공업": 350000,
    }.get(norm(name))

def parse_price(s):
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


def parse_naver_number(html, label):
    try:
        # 네이버 금융 표 안에서 '거래량', '52주최고' 등 라벨 주변 숫자를 넓게 탐색
        pattern = rf'{label}[\s\S]{{0,250}}?<span class="blind">([\d,]+)</span>'
        m = re.search(pattern, html)
        if m:
            return parse_price(m.group(1))
    except Exception:
        pass
    return None

def fetch_market_data(name):
    name = norm(name)
    code = code_map().get(name)
    fallback = fallback_price(name)
    result = {
        "price": fallback,
        "change_rate": None,
        "volume": None,
        "high_52w": None,
        "low_52w": None,
        "src": "기본값",
        "is_live": False,
    }

    if not code:
        return result

    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3).text

        price = None
        for pat in [
            r'<p class="no_today">[\s\S]*?<span class="blind">([\d,]+)</span>',
            r'<div class="today">[\s\S]*?<span class="blind">([\d,]+)</span>',
        ]:
            m = re.search(pat, html)
            if m:
                price = parse_price(m.group(1))
                if price:
                    break

        # 등락률: em 태그나 blind 주변의 +- % 텍스트를 최대한 보수적으로 탐색
        change_rate = None
        m = re.search(r'([-+]?\d+(?:\.\d+)?)%', html)
        if m:
            try:
                change_rate = float(m.group(1))
            except Exception:
                change_rate = None

        volume = parse_naver_number(html, "거래량")
        high_52w = parse_naver_number(html, "52주최고")
        low_52w = parse_naver_number(html, "52주최저")

        result.update({
            "price": price or fallback,
            "change_rate": change_rate,
            "volume": volume,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "src": f"네이버 {code}" if price else "기본값",
            "is_live": True if price else False,
        })
        return result
    except Exception:
        return result

def position_52w(price, low_52w, high_52w):
    try:
        if not price or not low_52w or not high_52w or high_52w <= low_52w:
            return None
        return max(0, min(100, (price - low_52w) / (high_52w - low_52w) * 100))
    except Exception:
        return None


def fetch_price(name):
    md = fetch_market_data(name)
    return md.get("price"), md.get("src")


def sector(name):
    n = norm(name)

    if "S&P500" in n or "나스닥" in n or "미국배당" in n or "미국빅테크" in n:
        return "미국지수"

    if "반도체" in n or n in [
        "삼성전자", "SK하이닉스", "한미반도체", "엔비디아", "브로드컴",
        "ISC", "하나마이크론", "이수페타시스", "리노공업", "동진쎄미켐",
        "솔브레인", "원익IPS", "HPSP", "DB하이텍", "테크윙", "심텍",
        "대덕전자", "주성엔지니어링"
    ]:
        return "반도체"

    if n in [
        "제룡전기", "에스피시스템스", "대한전선", "LS ELECTRIC",
        "HD현대일렉트릭", "효성중공업", "두산에너빌리티", "LS",
        "일진전기", "가온전선", "대원전선", "한전기술", "한국전력"
    ] or "전기" in n or "전선" in n:
        return "전력/에너지"

    if n in [
        "에코프로비엠", "에코프로", "포스코퓨처엠", "POSCO홀딩스",
        "LG에너지솔루션", "삼성SDI", "엘앤에프", "천보",
        "SK아이이테크놀로지", "코스모신소재", "나노신소재"
    ] or "2차전지" in n or "전기차" in n:
        return "2차전지"

    if n in [
        "한화에어로스페이스", "LIG넥스원", "현대로템", "한국항공우주",
        "한화시스템", "HD현대중공업", "한화오션", "삼성중공업"
    ]:
        return "방산/조선"

    if n in [
        "레인보우로보틱스", "두산로보틱스", "로보티즈", "유진로봇",
        "로보스타", "에스비비테크", "뉴로메카"
    ] or "로봇" in n:
        return "로봇"

    if n in ["현대차", "기아", "현대모비스", "HL만도", "성우하이텍", "에스엘"]:
        return "자동차"

    if n in ["NAVER", "카카오", "크래프톤", "엔씨소프트", "넷마블", "펄어비스", "구글", "메타", "아마존"]:
        return "플랫폼"

    if n in ["셀트리온", "삼성바이오로직스", "알테오젠", "유한양행", "한미약품", "HLB", "리가켐바이오", "오스코텍"]:
        return "바이오"

    if n in ["KB금융", "신한지주", "하나금융지주", "우리금융지주", "삼성화재", "메리츠금융지주"]:
        return "금융/배당"

    if n in ["아모레퍼시픽", "LG생활건강", "코스맥스", "한국콜마", "CJ제일제당", "농심", "삼양식품"]:
        return "소비재"

    if "디스플레이" in n:
        return "디스플레이"

    return "기타"

def evaluate(name, qty, avg):
    md = fetch_market_data(name)
    price = md.get("price")
    src = md.get("src")
    qty = sf(qty)
    avg = sf(avg)
    if not price or qty <= 0 or avg <= 0:
        return None
    buy = qty * avg
    value = qty * price
    profit = value - buy
    rate = profit / buy * 100 if buy else 0
    pos52 = position_52w(price, md.get("low_52w"), md.get("high_52w"))
    return {
        "price": price,
        "src": src,
        "buy": buy,
        "value": value,
        "profit": profit,
        "rate": rate,
        "change_rate": md.get("change_rate"),
        "volume": md.get("volume"),
        "high_52w": md.get("high_52w"),
        "low_52w": md.get("low_52w"),
        "pos52": pos52,
        "is_live": md.get("is_live"),
    }


def metrics(data):
    total_buy = total_value = 0
    sec_values = {}
    rows = []
    for h in data.get("holdings", []):
        n = norm(h.get("name", ""))
        q = sf(h.get("qty"))
        a = sf(h.get("avg"))
        r = evaluate(n, q, a)
        buy = q * a
        value = r["value"] if r else buy
        total_buy += buy
        total_value += value
        sec_values[sector(n)] = sec_values.get(sector(n), 0) + value
        rows.append((n, q, a, r))
    profit = total_value - total_buy
    rate = profit / total_buy * 100 if total_buy else 0
    weights = {k: v / total_value * 100 for k, v in sec_values.items()} if total_value else {}
    return total_buy, total_value, profit, rate, weights, rows

def principal(data):
    return sf(data.get("profile", {}).get("principal", 5000000), 5000000)

def target_return(data):
    # V77-3-2: 목표수익률/투자기간 성향은 화면에서 제거.
    # 기존 매도/보유 판단 로직 호환용 내부 기준만 유지.
    return 15


def stock_score(name, qty, avg, r, weights, target):
    rate = r["rate"] if r else 0
    sec = sector(name)
    sw = weights.get(sec, 0)
    score = 60

    if rate >= target:
        score += 4
    elif rate >= 5:
        score += 8
    elif rate >= 0:
        score += 4
    elif rate <= -15:
        score -= 12
    elif rate <= -7:
        score -= 7

    if sec == "미국지수":
        score += 18 if sw < 25 else 8
    elif sec == "반도체":
        score -= 18 if sw >= 55 else (-8 if sw >= 45 else 5)
    elif sec == "디스플레이":
        score -= 8 if rate >= 8 else -2
    elif sec == "전력/자동화":
        score += 8 if sw < 25 else 2

    return max(0, min(100, int(score)))

def stock_signal(name, qty, avg, r, weights, target):
    score = stock_score(name, qty, avg, r, weights, target)
    rate = r["rate"] if r else 0
    sec = sector(name)
    sw = weights.get(sec, 0)

    if sec == "디스플레이" and rate >= max(6, target * 0.5):
        return score, "🔴 부분매도", "수익이 난 상태에서 업황 변동성이 있어 일부 현금화 후보입니다."
    if rate >= target and score < 70:
        return score, "🔴 부분매도", "투자기간 기준에 근접했지만 추가 상승 점수가 높지 않습니다."
    if sec == "반도체" and sw >= 55:
        return score, "🟡 추가매수 보류", "반도체 비중이 높아 신규 매수보다 분산이 우선입니다."
    if sec == "미국지수" and sw < 30:
        return score, "🔵 추가매수", "장기 적립식 기준으로 미국지수 비중 보강이 필요합니다."
    if score >= 72:
        return score, "🟢 보유", "점수와 비중이 양호해 보유 유지가 적합합니다."
    if score <= 50:
        return score, "🟠 관망", "점수가 낮아 신규 매수보다 관찰이 필요합니다."
    return score, "🟢 보유", "현재는 보유 유지가 적절합니다."

def realistic_buy_qty(price, budget):
    if not price or price <= 0 or budget < price:
        return 0
    raw = int(budget // price)
    if price < 10000:
        return min(raw, 3)
    if price < 30000:
        return min(raw, 2)
    return 1

def best_buy(data, budget, exclude=None):
    _, _, _, _, weights, _ = metrics(data)
    candidates = ["KODEX 미국S&P500", "제룡전기", "ACE AI반도체 TOP3", "TIGER 미국S&P500"]
    result = []
    for n in candidates:
        if exclude and norm(n) == norm(exclude):
            continue
        price, src = fetch_price(n)
        if not price:
            continue
        sec = sector(n)
        sw = weights.get(sec, 0)
        score = 50
        if sec == "미국지수":
            score += 30 if sw < 30 else 12
        elif sec == "전력/자동화":
            score += 16 if sw < 25 else 8
        elif sec == "반도체":
            score += 6 if sw < 45 else -18
        shares = realistic_buy_qty(price, budget)
        score += 20 if shares >= 1 else -35
        result.append({"name": n, "price": price, "shares": shares, "score": score, "src": src, "raw_shares": int(budget // price) if price else 0})
    if not result:
        return None
    affordable = [x for x in result if x["shares"] >= 1]
    return sorted(affordable or result, key=lambda x: x["score"], reverse=True)[0]

def portfolio_health(data):
    """
    V91-2.1 긴급복구:
    데이터 일부가 없거나 계산 중 오류가 나도 앱이 멈추지 않도록 안전 계산.
    """
    try:
        total_buy, total_value, profit, rate, weights, rows = metrics(data)
    except Exception:
        total_buy, total_value, profit, rate, weights, rows = 0, 0, 0, 0, {}, []

    positives = []
    warnings = []

    try:
        rate = float(rate or 0)
    except Exception:
        rate = 0

    # 1) 수익상태 30점
    if rate >= 20:
        profit_score = 30
        positives.append("평가수익률이 높아 포트 흐름이 양호합니다.")
    elif rate >= 5:
        profit_score = 24
        positives.append("수익구간을 유지하고 있습니다.")
    elif rate >= 0:
        profit_score = 18
        positives.append("손실 없이 안정권을 유지 중입니다.")
    elif rate >= -5:
        profit_score = 12
        warnings.append("수익률이 약보합권이라 관찰이 필요합니다.")
    else:
        profit_score = 6
        warnings.append("평가손실 구간이라 추가매수보다 위험 점검이 우선입니다.")

    # 2) 분산/집중도 30점
    max_sector, max_weight = "-", 0.0
    try:
        if isinstance(weights, dict) and weights:
            max_sector, max_weight = max(weights.items(), key=lambda item: float(item[1] or 0))
            max_weight = float(max_weight or 0)
    except Exception:
        max_sector, max_weight = "-", 0.0

    if max_weight <= 35:
        div_score = 28
        positives.append("특정 섹터 집중도가 낮아 분산이 양호합니다.")
    elif max_weight <= 50:
        div_score = 21
        positives.append("집중도는 있으나 아직 관리 가능한 수준입니다.")
    elif max_weight <= 65:
        div_score = 13
        warnings.append(f"{max_sector} 비중이 {max_weight:.1f}%로 다소 높습니다.")
    else:
        div_score = 6
        warnings.append(f"{max_sector} 비중이 {max_weight:.1f}%로 집중 위험이 큽니다.")

    # 3) 손실/주의 종목 20점
    loss_count, danger_count = 0, 0
    try:
        for n, q, a, r in rows or []:
            if r and float(r.get("profit", 0) or 0) < 0:
                loss_count += 1
            if r:
                try:
                    grade, _ = risk_grade_simple(n, r)
                    if "위험" in str(grade) or "주의" in str(grade):
                        danger_count += 1
                except Exception:
                    pass
    except Exception:
        pass

    if danger_count == 0 and loss_count <= 1:
        risk_score = 20
        positives.append("위험 신호가 큰 종목은 제한적입니다.")
    elif danger_count <= 1:
        risk_score = 14
        warnings.append("일부 종목은 주의 관찰이 필요합니다.")
    else:
        risk_score = 7
        warnings.append("주의/위험 종목이 여러 개라 비중 조절이 필요합니다.")

    # 4) 미국지수/장기분산 20점
    us_weight = 0.0
    try:
        for sec, w in (weights or {}).items():
            if "미국지수" in str(sec):
                us_weight += float(w or 0)
    except Exception:
        us_weight = 0.0

    if us_weight >= 20:
        etf_score = 20
        positives.append("미국지수 비중이 있어 장기 안정성이 보강됩니다.")
    elif us_weight >= 8:
        etf_score = 15
        positives.append("미국지수 비중이 일부 있어 방어력이 있습니다.")
    else:
        etf_score = 8
        warnings.append("미국지수/장기 분산 비중이 부족합니다.")

    score = int(profit_score + div_score + risk_score + etf_score)
    score = max(0, min(100, score))

    if score >= 90:
        grade = "🟢 매우양호"
        action = "신규매수 가능 · 단, 과열 종목 추격매수는 피하세요."
    elif score >= 70:
        grade = "🟢 양호"
        action = "신규매수 가능 · 분할매수와 섹터 분산을 유지하세요."
    elif score >= 50:
        grade = "🟡 보통"
        action = "관망 우선 · 추가매수는 1순위 종목만 소액 분할 접근하세요."
    elif score >= 30:
        grade = "🟠 주의"
        action = "추가매수 보류 · 손실/집중 종목부터 점검하세요."
    else:
        grade = "🔴 위험"
        action = "매수 중지 · 비중축소와 리스크 관리가 우선입니다."

    return {
        "score": score,
        "grade": grade,
        "rate": rate,
        "max_sector": max_sector,
        "max_weight": max_weight,
        "loss_count": loss_count,
        "danger_count": danger_count,
        "us_weight": us_weight,
        "positives": positives[:3] or ["현재 포트폴리오 데이터를 기준으로 안정성을 점검했습니다."],
        "warnings": warnings[:3] or ["현재 큰 주의사항은 많지 않습니다."],
        "action": action,
    }

def render_portfolio_health(data):
    try:
        h = portfolio_health(data)
        positives = "<br>".join([f"✓ {x}" for x in h.get("positives", [])])
        warnings = "<br>".join([f"⚠ {x}" for x in h.get("warnings", [])])

        score = int(h.get("score", 50) or 50)
        score = max(0, min(100, score))

        st.markdown(f"""
        <div class="health-card">
            <div class="health-top">
                <div>
                    <div class="health-title">❤️ 포트폴리오 건강도</div>
                    <div class="health-sub">수익률 · 집중도 · 위험종목 · 미국지수 비중을 종합 판단</div>
                </div>
                <div class="health-score">
                    <div class="health-score-num">{score}</div>
                    <div class="health-grade">{h.get("grade", "🟡 보통")}</div>
                </div>
            </div>
            <div class="health-bar"><div class="health-fill" style="width:{score}%"></div></div>
            <div class="health-grid">
                <div class="health-box"><div class="health-label">평가수익률</div><div class="health-value">{float(h.get("rate", 0) or 0):.2f}%</div></div>
                <div class="health-box"><div class="health-label">최대 섹터비중</div><div class="health-value">{h.get("max_sector", "-")} {float(h.get("max_weight", 0) or 0):.1f}%</div></div>
                <div class="health-box"><div class="health-label">손실/주의 종목</div><div class="health-value">{h.get("loss_count", 0)}개 / {h.get("danger_count", 0)}개</div></div>
                <div class="health-box"><div class="health-label">미국지수 비중</div><div class="health-value">{float(h.get("us_weight", 0) or 0):.1f}%</div></div>
            </div>
            <div class="health-section"><b>현재상태</b><br>{positives}</div>
            <div class="health-section"><b>주의사항</b><br>{warnings}</div>
            <div class="health-action">오늘 행동: {h.get("action", "관망 우선 · 데이터 확인 후 판단하세요.")}</div>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        # 마지막 안전장치: 건강도 카드가 실패해도 앱 전체가 죽지 않게 함
        st.markdown(
            '<div class="health-card">'
            '<div class="health-title">❤️ 포트폴리오 건강도</div>'
            '<div class="health-section">건강도 계산 중 일부 데이터 오류가 있어 기본 상태로 표시합니다.</div>'
            '<div class="health-action">오늘 행동: 관망 우선 · 보유종목 데이터를 확인하세요.</div>'
            '</div>',
            unsafe_allow_html=True
        )


def one_action(data):
    total_buy, total_value, profit, rate, weights, rows = metrics(data)
    target = target_return(data)
    cash = 0

    sell_candidates = []
    for n, q, a, r in rows:
        if not r:
            continue
        score, sig, reason = stock_signal(n, q, a, r, weights, target)
        if "부분매도" in sig and q >= 4:
            sell_qty = max(1, int(q // 4))
            proceeds = sell_qty * r["price"]
            buy = best_buy(data, proceeds, exclude=n)
            sell_candidates.append({"name": n, "sell_qty": sell_qty, "proceeds": proceeds, "rate": r["rate"], "reason": reason, "buy": buy})

    if sell_candidates:
        c = sorted(sell_candidates, key=lambda x: x["rate"], reverse=True)[0]
        if c["buy"] and c["buy"]["shares"] >= 1:
            invest = c["buy"]["shares"] * c["buy"]["price"]
            remain = c["proceeds"] - invest
            return {
                "main": f'{c["name"]} {c["sell_qty"]}주 매도 → {c["buy"]["name"]} {c["buy"]["shares"]}주 매수',
                "sub": f'예상 확보금액 {won(c["proceeds"])} · 예상 재투자금 {won(invest)} · 참고금액 {won(remain)}<br>이유: {c["reason"]}',
                "badge": "자산 재배치",
                "conf": 82,
                "detail": f'{c["name"]} 수익률 {c["rate"]:.2f}% · {c["buy"]["name"]} 현재가 {won(c["buy"]["price"])} · 한 번에 몰아서 사지 않고 분할매수 기준으로 계산',
            }
        return {
            "main": f'{c["name"]} {c["sell_qty"]}주 부분매도 검토',
            "sub": f'예상 확보금액 {won(c["proceeds"])}<br>이유: {c["reason"]}',
            "badge": "현금화",
            "conf": 76,
            "detail": f'{c["name"]} 수익률 {c["rate"]:.2f}%',
        }

    if cash > 0:
        b = best_buy(data, cash)
        if b and b["shares"] >= 1:
            invest = b["shares"] * b["price"]
            return {
                "main": f'{b["name"]} {b["shares"]}주 매수 검토',
                "sub": f'현재 포트폴리오 기준으로는 {won(cash)}이지만, 한 번에 몰아 사지 않고 분할매수 기준으로 {b["shares"]}주만 제안합니다.<br>이유: 현재 포트폴리오에서 가장 보완 효과가 큰 단 하나의 후보입니다.',
                "badge": "분할매수",
                "conf": 78,
                "detail": f'예상 기준금액 {won(invest)} · 참고금액 {won(cash - invest)} · 원래 가능 수량 {b.get("raw_shares",0)}주 중 분할 기준 {b["shares"]}주',
            }

    return {
        "main": "오늘은 보유 유지",
        "sub": "부분매도 신호와 신규매수 여력이 뚜렷하지 않습니다.<br>무리한 매매보다 보유종목 점검이 우선입니다.",
        "badge": "관망",
        "conf": 72,
        "detail": f'현재 포트폴리오 평가수익률 {rate:.2f}% 기준',
    }

def related_keywords(data):
    keys = set()
    for h in data.get("holdings", []):
        n = norm(h.get("name", ""))
        keys.add(n)
        s = sector(n)
        if s == "반도체":
            keys.update(["반도체", "AI", "HBM", "삼성전자", "SK하이닉스"])
        elif s == "전력/자동화":
            keys.update(["전력", "전력망", "변압기", "전기", "자동화", "로봇"])
        elif s == "미국지수":
            keys.update(["미국", "S&P", "나스닥", "금리", "연준"])
        elif s == "디스플레이":
            keys.update(["디스플레이", "OLED", "패널", "LG디스플레이"])
    return [k for k in keys if k]


def now_label():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_key():
    return datetime.now().strftime("%Y-%m-%d")

def load_history():
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

def save_history(items):
    DATA_DIR.mkdir(exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def asset_summary(data):
    total_buy, total_value, unrealized_profit, unrealized_rate, weights, rows = metrics(data)

    # V77-3:
    # 별도 총 매입원금/사용안함을 사용하지 않음.
    # 보유종목의 수량 × 평단가 합계가 자동 매입원금.
    buy_principal = total_buy
    stock_value = total_value
    eval_profit = stock_value - buy_principal
    eval_rate = eval_profit / buy_principal * 100 if buy_principal else 0

    return {
        "buy_principal": buy_principal,
        "stock_value": stock_value,
        "total_asset": stock_value,
        "profit": eval_profit,
        "rate": eval_rate,
        "unrealized_profit": eval_profit,
        "unrealized_rate": eval_rate,
    }

def record_today_snapshot(data):
    s = asset_summary(data)
    items = load_history()
    key = today_key()
    row = {
        "date": key,
        "time": now_label(),
        "buy_principal": s["buy_principal"],
        "total_asset": s["total_asset"],
        "profit": s["profit"],
        "rate": s["rate"],
        "stock_value": s["stock_value"],
        "cash": 0,
    }
    done = False
    for i, old in enumerate(items):
        if old.get("date") == key:
            items[i] = row
            done = True
            break
    if not done:
        items.append(row)
    items = sorted(items, key=lambda x: x.get("date", ""))
    save_history(items)
    return row

def week_key(datestr):
    try:
        dt = datetime.strptime(datestr, "%Y-%m-%d")
        first_day = dt.replace(day=1)
        week_no = ((dt.day + first_day.weekday() - 1) // 7) + 1
        week_start = dt - timedelta(days=dt.weekday())
        week_end = week_start + timedelta(days=6)
        return f"{dt.year}년 {dt.month}월 {week_no}주차 ({week_start.strftime('%m/%d')}~{week_end.strftime('%m/%d')})"
    except Exception:
        return "주차 미상"


def month_key(datestr):
    try:
        dt = datetime.strptime(datestr, "%Y-%m-%d")
        return dt.strftime("%Y-%m")
    except Exception:
        return "월 미상"

def history_groups():
    items = load_history()
    daily = items[-14:]
    weekly_map = {}
    monthly_map = {}
    for r in items:
        weekly_map[week_key(r.get("date",""))] = r
        monthly_map[month_key(r.get("date",""))] = r
    weekly = [{"period": k, **v} for k, v in sorted(weekly_map.items())][-12:]
    monthly = [{"period": k, **v} for k, v in sorted(monthly_map.items())][-12:]
    return daily, weekly, monthly

def render_asset_top(data):
    s = asset_summary(data)
    cls = "profit" if s["profit"] >= 0 else "loss"
    st.markdown(
        f'<div class="card">'
        f'<div class="title">📅 {now_label()}</div>'
        f'<div class="body">'
        f'총 매입원금 {won(s["buy_principal"])}<br>'
        f'현재 평가금액 {won(s["stock_value"])}<br>'
        f'평가수익금 <span class="{cls}">{won(s["profit"])}</span> · 평가수익률 <span class="{cls}">{s["rate"]:.2f}%</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )
    record_today_snapshot(data)

def history_table_html(rows, label_key):
    if not rows:
        return "아직 기록이 없습니다."
    html = "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
    html += "<tr><th style='text-align:left;border-bottom:1px solid #e5e7eb;padding:6px;'>기간</th><th style='text-align:right;border-bottom:1px solid #e5e7eb;padding:6px;'>평가금액</th><th style='text-align:right;border-bottom:1px solid #e5e7eb;padding:6px;'>평가수익</th><th style='text-align:right;border-bottom:1px solid #e5e7eb;padding:6px;'>수익률</th></tr>"
    for r in reversed(rows):
        label = r.get(label_key) or r.get("period") or r.get("date","")
        profit = sf(r.get("profit"))
        color = "color:#dc2626;" if profit >= 0 else "color:#2563eb;"
        html += f"<tr><td style='padding:6px;border-bottom:1px solid #f1f5f9;'>{label}</td><td style='padding:6px;text-align:right;border-bottom:1px solid #f1f5f9;'>{won(r.get('total_asset'))}</td><td style='padding:6px;text-align:right;border-bottom:1px solid #f1f5f9;{color}'>{won(profit)}</td><td style='padding:6px;text-align:right;border-bottom:1px solid #f1f5f9;{color}'>{sf(r.get('rate')):.2f}%</td></tr>"
    html += "</table>"
    return html

def render_history_tables():
    daily, weekly, monthly = history_groups()
    st.markdown('<div class="card"><div class="title">기간별 평가수익 히스토리</div><div class="body">일간 / 주간 / 월간을 탭으로 확인합니다.</div></div>', unsafe_allow_html=True)
    tab_daily, tab_weekly, tab_monthly = st.tabs(["일간", "주간", "월간"])
    with tab_daily:
        st.markdown(history_table_html(daily, "date"), unsafe_allow_html=True)
    with tab_weekly:
        st.markdown(history_table_html(weekly, "period"), unsafe_allow_html=True)
    with tab_monthly:
        st.markdown(history_table_html(monthly, "period"), unsafe_allow_html=True)




def load_sell_records():
    try:
        if SELL_FILE.exists():
            with open(SELL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

def save_sell_records(items):
    DATA_DIR.mkdir(exist_ok=True)
    with open(SELL_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def add_sell_record(stock, qty, avg, sell_price, sell_date=None):
    sell_date = sell_date or today_key()
    qty = sf(qty)
    avg = sf(avg)
    sell_price = sf(sell_price)
    profit = (sell_price - avg) * qty
    rate = (sell_price - avg) / avg * 100 if avg else 0
    row = {
        "date": sell_date,
        "stock": norm(stock),
        "qty": qty,
        "avg": avg,
        "sell_price": sell_price,
        "profit": profit,
        "rate": rate,
        "type": "익절" if profit >= 0 else "손절",
        "created_at": now_label()
    }
    items = load_sell_records()
    items.append(row)
    save_sell_records(items)
    return row

def sell_period_groups():
    items = load_sell_records()
    daily_map = {}
    weekly_map = {}
    monthly_map = {}

    for r in items:
        d = r.get("date", "")
        profit = sf(r.get("profit"))
        daily_map[d] = daily_map.get(d, 0) + profit
        weekly_map[week_key(d)] = weekly_map.get(week_key(d), 0) + profit
        monthly_map[month_key(d)] = monthly_map.get(month_key(d), 0) + profit

    daily = [{"period": k, "profit": v} for k, v in sorted(daily_map.items())][-20:]
    weekly = [{"period": k, "profit": v} for k, v in sorted(weekly_map.items())][-12:]
    monthly = [{"period": k, "profit": v} for k, v in sorted(monthly_map.items())][-12:]
    return daily, weekly, monthly

def sell_table_html(rows):
    if not rows:
        return "아직 매도기록이 없습니다."
    html = "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
    html += "<tr><th style='text-align:left;border-bottom:1px solid #e5e7eb;padding:6px;'>기간</th><th style='text-align:right;border-bottom:1px solid #e5e7eb;padding:6px;'>실현손익</th></tr>"
    for r in reversed(rows):
        profit = sf(r.get("profit"))
        color = "color:#dc2626;" if profit >= 0 else "color:#2563eb;"
        html += f"<tr><td style='padding:6px;border-bottom:1px solid #f1f5f9;'>{r.get('period','')}</td><td style='padding:6px;text-align:right;border-bottom:1px solid #f1f5f9;{color}'>{won(profit)}</td></tr>"
    html += "</table>"
    return html

def render_sell_history():
    items = load_sell_records()
    total_profit = sum(sf(x.get("profit")) for x in items)
    cls = "profit" if total_profit >= 0 else "loss"
    st.markdown(
        f'<div class="card"><div class="title">실현손익 요약</div>'
        f'<div class="body">누적 실현손익 <span class="{cls}">{won(total_profit)}</span><br>'
        f'매도기록 {len(items)}건</div></div>',
        unsafe_allow_html=True
    )

    daily, weekly, monthly = sell_period_groups()
    tab_daily, tab_weekly, tab_monthly = st.tabs(["일간", "주간", "월간"])
    with tab_daily:
        st.markdown(sell_table_html(daily), unsafe_allow_html=True)
    with tab_weekly:
        st.markdown(sell_table_html(weekly), unsafe_allow_html=True)
    with tab_monthly:
        st.markdown(sell_table_html(monthly), unsafe_allow_html=True)

    if items:
        st.markdown('<div class="card"><div class="title">최근 매도기록</div><div class="body">최근 기록 10건</div></div>', unsafe_allow_html=True)
        for r in reversed(items[-10:]):
            cls = "profit" if sf(r.get("profit")) >= 0 else "loss"
            st.markdown(
                f'<div class="hold"><div class="hold-name">{r.get("stock","")}</div>'
                f'<div class="meta">{r.get("date","")} · {r.get("type","")} · {sf(r.get("qty")):g}주 매도</div>'
                f'<div class="eval">평단 {won(r.get("avg"))} · 매도가 {won(r.get("sell_price"))}<br>'
                f'실현손익 <span class="{cls}">{won(r.get("profit"))}</span> · 수익률 <span class="{cls}">{sf(r.get("rate")):.2f}%</span></div></div>',
                unsafe_allow_html=True
            )


def risk_grade_simple(name, r):
    rate = r["rate"] if r else 0
    if rate <= -20:
        return "🔴 위험", "수익률 -20% 이하입니다. 급락 또는 손실 확대 여부를 확인하세요."
    if rate <= -10:
        return "🟠 경고", "수익률 -10% 이하입니다. 추가 하락 여부 확인이 필요합니다."
    if rate <= -5:
        return "🟡 주의", "수익률 -5% 이하입니다. 관찰이 필요합니다."
    return "🟢 안전", "현재 단순 손익 기준 위험 신호는 크지 않습니다."

def render_risk_board(data):
    _, _, _, _, weights, rows = metrics(data)
    danger = []
    caution = []
    for n, q, a, r in rows:
        grade, reason = risk_grade_simple(n, r)
        if "🔴" in grade or "🟠" in grade:
            danger.append((n, grade, reason))
        elif "🟡" in grade:
            caution.append((n, grade, reason))
    if danger:
        n, grade, reason = danger[0]
        card("🚨 긴급상황판", f"위험종목 발견<br>{n} · {grade}<br>{reason}")
    elif caution:
        n, grade, reason = caution[0]
        card("🚨 긴급상황판", f"주의종목 있음<br>{n} · {grade}<br>{reason}")
    else:
        card("🚨 긴급상황판", "🟢 긴급상황 없음<br>현재 보유종목에서 큰 위험 신호는 보이지 않습니다.")


def css():
    st.markdown("""
    <style>
    .block-container{max-width:760px;padding-top:32px;padding-bottom:96px}
    .hero{background:#07111f;color:white;border-radius:24px;padding:22px;margin-bottom:14px}
    .hero h1{font-size:29px;margin:0 0 8px;font-weight:950}
    .hero p{margin:0;color:#cbd5e1;font-weight:800}
    .card{background:white;border:1px solid #e5e7eb;border-radius:18px;padding:16px;margin:10px 0;box-shadow:0 8px 22px rgba(15,23,42,.06)}
    .title{font-weight:950;font-size:19px;color:#0f172a;margin-bottom:8px}
    .body{font-weight:800;color:#475569;line-height:1.6;font-size:14px}
    .action{background:linear-gradient(180deg,#07111f,#0b1628);color:white;border-radius:22px;padding:18px;margin:12px 0}
    .action-k{font-size:13px;color:#cbd5e1;font-weight:900}
    .action-main{font-size:25px;font-weight:950;margin-top:4px}
    .action-sub{font-size:13px;color:#dbeafe;font-weight:800;margin-top:8px;line-height:1.5}
    .badge{display:inline-block;margin-top:8px;padding:5px 10px;border-radius:999px;background:#14532d;color:#bbf7d0;font-size:12px;font-weight:950}
    .hold{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:14px;margin:10px 0}
    .hold-name{font-size:19px;font-weight:950}
    .meta{font-size:13px;color:#475569;font-weight:850;margin-top:4px}
    .eval,.scorebox{background:#f8fafc;border:1px solid #e2e8f0;border-radius:15px;padding:11px;margin-top:8px;font-size:13px;color:#475569;font-weight:850}
    .profit{color:#dc2626;font-weight:950}.loss{color:#2563eb;font-weight:950}
    .nav{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);width:min(680px,92vw);background:#07111f;border-radius:999px;padding:8px;display:flex;gap:4px;z-index:999}
    .nav a{flex:1;text-align:center;color:white;text-decoration:none;font-weight:900;font-size:12px;padding:10px 4px;border-radius:999px}
    .nav a.active{background:#c6a15b}
    .notice{font-size:11px;color:#64748b;line-height:1.5;margin-top:10px}

    .thermo-wrap{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:16px;margin:10px 0;box-shadow:0 8px 22px rgba(15,23,42,.06)}
    .thermo-head{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;margin-bottom:10px}
    .thermo-title{font-weight:950;font-size:19px;color:#0f172a}
    .thermo-state{text-align:right;font-weight:950;color:#0f172a}
    .thermo-state .big{font-size:24px;line-height:1.1}
    .thermo-state .num{font-size:22px;color:#07111f}
    .thermo-box{position:relative;height:210px;border-radius:18px;background:linear-gradient(180deg,#e7f8ed 0%,#f8fafc 42%,#ffffff 50%,#fff7ed 75%,#fee2e2 100%);border:1px solid #e2e8f0;margin:10px 0;overflow:hidden}
    .thermo-center{position:absolute;left:8%;right:8%;top:50%;height:1px;background:#cbd5e1}
    .thermo-line{position:absolute;left:50%;top:14px;bottom:14px;width:5px;background:#cbd5e1;border-radius:999px;transform:translateX(-50%);box-shadow:0 0 0 4px rgba(203,213,225,.25)}
    .thermo-marker{position:absolute;left:50%;transform:translate(-50%,-50%);min-width:74px;height:34px;border-radius:999px;background:#07111f;color:white;font-weight:950;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 18px rgba(15,23,42,.25);padding:0 10px}
    .thermo-label{position:absolute;font-size:11px;font-weight:950;color:#334155;line-height:1.1}
    .thermo-label.safe100{top:10px;right:12px;color:#166534}
    .thermo-label.safe70{top:38px;right:12px;color:#15803d}
    .thermo-label.good40{top:66px;right:12px;color:#ca8a04}
    .thermo-label.mid{top:50%;right:12px;transform:translateY(-50%);color:#64748b}
    .thermo-label.warn40{bottom:66px;right:12px;color:#c2410c}
    .thermo-label.risk70{bottom:38px;right:12px;color:#b91c1c}
    .thermo-label.risk100{bottom:10px;right:12px;color:#991b1b}
    .thermo-note{font-size:13px;color:#475569;font-weight:850;line-height:1.6}


    .search-hint{font-size:12px;color:#64748b;font-weight:800;margin-top:-4px;margin-bottom:8px}
    .search-result-title{font-weight:950;font-size:18px;margin-top:8px;color:#0f172a}


    .grade-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:18px;padding:14px;margin:10px 0}
    .grade-top{display:flex;justify-content:space-between;align-items:center;gap:10px}
    .grade-name{font-size:20px;font-weight:950;color:#0f172a}
    .grade-pill{background:#07111f;color:#fff;border-radius:999px;padding:8px 12px;font-size:14px;font-weight:950}
    .grade-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
    .mini-box{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:10px;font-size:13px;font-weight:850;color:#475569}
    .mini-box b{font-size:18px;color:#0f172a}
    .horizon-row{display:flex;gap:6px;margin-top:8px}
    .horizon-chip{flex:1;text-align:center;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:8px 4px;font-size:12px;font-weight:900;color:#334155}
    .news-summary{background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;padding:12px;margin:8px 0;font-weight:850;color:#475569}


    .flow-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
    .flow-table th{background:#f8fafc;border-bottom:1px solid #e5e7eb;padding:7px;text-align:center;color:#334155}
    .flow-table td{border-bottom:1px solid #f1f5f9;padding:7px;text-align:center;font-weight:850;vertical-align:middle}
    .flow-buy{color:#dc2626;font-weight:950}
    .flow-sell{color:#2563eb;font-weight:950}
    .flow-flat{color:#64748b;font-weight:950}
    .flow-note{font-size:12px;color:#64748b;line-height:1.5;margin-top:6px;font-weight:800}


    .top-card{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:14px;margin:10px 0}
    .top-rank{display:inline-block;background:#07111f;color:white;border-radius:999px;padding:5px 10px;font-weight:950;font-size:12px;margin-bottom:6px}
    .top-name{font-size:18px;font-weight:950;color:#0f172a}
    .top-meta{font-size:13px;color:#475569;font-weight:850;line-height:1.5;margin-top:5px}


    .target-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
    .target-table th{background:#f8fafc;border-bottom:1px solid #e5e7eb;padding:7px;text-align:center;color:#334155}
    .target-table td{border-bottom:1px solid #f1f5f9;padding:7px;text-align:center;font-weight:850;vertical-align:middle}
    .target-buy{color:#dc2626;font-weight:950}
    .target-stop{color:#2563eb;font-weight:950}
    .target-note{font-size:12px;color:#64748b;line-height:1.5;margin-top:6px;font-weight:800}


    /* V80-9.2 모바일 가독성 긴급 패치 */
    .card, .scorebox, .top-card {
        background:#ffffff !important;
        color:#0f172a !important;
    }
    .card *, .scorebox *, .top-card * {
        color:inherit;
    }
    .title, .top-name {
        color:#020617 !important;
        font-weight:950 !important;
    }
    .body, .top-meta {
        color:#1e293b !important;
    }
    div[data-testid="stMarkdownContainer"] {
        color:#0f172a !important;
    }
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] span,
    div[data-testid="stMarkdownContainer"] div {
        color:inherit;
    }
    .holding-title, .stock-name, .holding-name {
        color:#020617 !important;
        font-weight:950 !important;
    }
    @media (max-width: 700px) {
        .card, .scorebox, .top-card {
            background:#ffffff !important;
            color:#0f172a !important;
        }
        .card h1, .card h2, .card h3,
        .card b, .scorebox b, .top-card b {
            color:#020617 !important;
        }
    }


    .timing-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}
    .timing-box{background:#f8fafc;border:1px solid #e5e7eb;border-radius:16px;padding:12px}
    .timing-label{font-size:12px;color:#64748b;font-weight:850}
    .timing-value{font-size:18px;color:#0f172a;font-weight:950;margin-top:4px}
    .timing-reason{font-size:12px;color:#334155;line-height:1.55;font-weight:800;margin-top:8px}
    @media (max-width:700px){.timing-grid{grid-template-columns:1fr}}


    /* V90-1.1 전체 밝은 테마 강제 패치 */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background:#f8fafc !important;
        color:#0f172a !important;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background:#f8fafc !important;
        color:#0f172a !important;
    }

    h1, h2, h3, h4, h5, h6,
    p, span, div, label, small, strong, b,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] * {
        color:#0f172a !important;
    }

    .card, .scorebox, .top-card, .timing-box {
        background:#ffffff !important;
        color:#0f172a !important;
        border-color:#e5e7eb !important;
    }

    .card *, .scorebox *, .top-card *, .timing-box * {
        color:#0f172a !important;
    }

    .title, .top-name, .timing-value {
        color:#020617 !important;
        font-weight:950 !important;
    }

    .body, .top-meta, .timing-reason, .timing-label {
        color:#1e293b !important;
    }

    /* 입력창/셀렉트박스/탭 다크모드 방지 */
    input, textarea, select,
    div[data-baseweb="input"],
    div[data-baseweb="input"] *,
    div[data-baseweb="select"],
    div[data-baseweb="select"] *,
    div[data-baseweb="textarea"],
    div[data-baseweb="textarea"] * {
        background:#ffffff !important;
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }

    div[data-baseweb="select"] svg,
    div[data-baseweb="input"] svg {
        color:#0f172a !important;
        fill:#0f172a !important;
    }

    [role="tab"], [role="tab"] *,
    button, button *,
    .stButton button, .stButton button * {
        color:#0f172a !important;
    }

    .stButton button {
        background:#ffffff !important;
        border:1px solid #cbd5e1 !important;
    }

    /* 하단 네비게이션은 기존 어두운 디자인 유지하되 글씨는 흰색 */
    .bottom-nav, .bottom-nav *,
    .nav, .nav * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    .bottom-nav .active, .nav .active,
    .bottom-nav .active *, .nav .active * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    /* 표 */
    table, th, td {
        color:#0f172a !important;
        background:#ffffff !important;
    }

    .flow-buy, .target-buy {
        color:#dc2626 !important;
        -webkit-text-fill-color:#dc2626 !important;
    }
    .flow-sell, .target-stop {
        color:#2563eb !important;
        -webkit-text-fill-color:#2563eb !important;
    }

    @media (prefers-color-scheme: dark) {
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:#f8fafc !important;
            color:#0f172a !important;
        }
        h1, h2, h3, h4, h5, h6, p, span, div, label, small, strong, b {
            color:#0f172a !important;
        }
        input, textarea, select {
            background:#ffffff !important;
            color:#0f172a !important;
            -webkit-text-fill-color:#0f172a !important;
        }
    }


    /* V90-1.2 대비색 최종 보정 */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background:#f8fafc !important;
    }

    h1, h2, h3, h4, h5, h6,
    p, label, small, strong, b,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] label {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }

    .card, .scorebox, .top-card, .timing-box {
        background:#ffffff !important;
        color:#0f172a !important;
        border-color:#e5e7eb !important;
    }
    .card *, .scorebox *, .top-card *, .timing-box * {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }

    .hero, .hero *,
    .app-hero, .app-hero *,
    .header, .header *,
    .banner, .banner *,
    .main-header, .main-header *,
    div[class*="hero"], div[class*="hero"] *,
    div[class*="header"], div[class*="header"] *,
    div[class*="banner"], div[class*="banner"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    div[style*="background:#07111f"], div[style*="background:#07111f"] *,
    div[style*="background: #07111f"], div[style*="background: #07111f"] *,
    div[style*="background:#020617"], div[style*="background:#020617"] *,
    div[style*="background: #020617"], div[style*="background: #020617"] *,
    div[style*="background:#0b1220"], div[style*="background:#0b1220"] *,
    div[style*="background: #0b1220"], div[style*="background: #0b1220"] *,
    div[style*="background:#0f172a"], div[style*="background:#0f172a"] *,
    div[style*="background: #0f172a"], div[style*="background: #0f172a"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    .bottom-nav, .bottom-nav *,
    .nav, .nav *,
    div[class*="bottom"], div[class*="bottom"] *,
    div[class*="nav"], div[class*="nav"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    .bottom-nav .active, .bottom-nav .active *,
    .nav .active, .nav .active *,
    div[class*="active"], div[class*="active"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    input, textarea, select,
    div[data-baseweb="input"],
    div[data-baseweb="input"] *,
    div[data-baseweb="select"],
    div[data-baseweb="select"] *,
    div[data-baseweb="textarea"],
    div[data-baseweb="textarea"] * {
        background:#ffffff !important;
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }

    .stButton button, .stButton button * {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }

    table, th, td {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
        background:#ffffff !important;
    }
    .flow-buy, .target-buy {
        color:#dc2626 !important;
        -webkit-text-fill-color:#dc2626 !important;
    }
    .flow-sell, .target-stop {
        color:#2563eb !important;
        -webkit-text-fill-color:#2563eb !important;
    }


    /* V90-1.3 프리미엄 고정 테마 */
    :root {
        --bg-main:#0b1020;
        --bg-soft:#111827;
        --card:#f8fafc;
        --card2:#ffffff;
        --text:#0f172a;
        --text-soft:#334155;
        --white:#ffffff;
        --gold:#c9a24f;
        --line:#e2e8f0;
        --nav:#050b18;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background:
            radial-gradient(circle at top left, rgba(201,162,79,0.14), transparent 28%),
            linear-gradient(180deg, #08101f 0%, #0b1020 40%, #111827 100%) !important;
        color:var(--white) !important;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background:transparent !important;
    }

    .block-container {
        padding-top:2rem !important;
        padding-bottom:7rem !important;
        max-width:920px !important;
    }

    /* 기본 텍스트 */
    h1, h2, h3, h4, h5, h6,
    p, label, small, strong, b,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] label {
        color:var(--white) !important;
        -webkit-text-fill-color:var(--white) !important;
    }

    /* 흰 카드 */
    .card, .scorebox, .top-card, .timing-box {
        background:linear-gradient(180deg, var(--card2) 0%, var(--card) 100%) !important;
        color:var(--text) !important;
        border:1px solid rgba(226,232,240,0.95) !important;
        border-radius:22px !important;
        box-shadow:0 18px 45px rgba(0,0,0,0.22) !important;
    }
    .card *, .scorebox *, .top-card *, .timing-box * {
        color:var(--text) !important;
        -webkit-text-fill-color:var(--text) !important;
    }

    .title, .top-name, .timing-value {
        color:#020617 !important;
        -webkit-text-fill-color:#020617 !important;
        font-weight:950 !important;
    }

    .body, .top-meta, .timing-reason, .timing-label {
        color:var(--text-soft) !important;
        -webkit-text-fill-color:var(--text-soft) !important;
    }

    /* 상단 히어로 */
    .hero, .hero *,
    .app-hero, .app-hero *,
    .header, .header *,
    .banner, .banner *,
    .main-header, .main-header *,
    div[class*="hero"], div[class*="hero"] *,
    div[class*="header"], div[class*="header"] *,
    div[class*="banner"], div[class*="banner"] *,
    div[style*="background:#07111f"], div[style*="background:#07111f"] *,
    div[style*="background: #07111f"], div[style*="background: #07111f"] *,
    div[style*="background:#020617"], div[style*="background:#020617"] *,
    div[style*="background: #020617"], div[style*="background: #020617"] *,
    div[style*="background:#0b1220"], div[style*="background:#0b1220"] *,
    div[style*="background: #0b1220"], div[style*="background: #0b1220"] *,
    div[style*="background:#0f172a"], div[style*="background:#0f172a"] *,
    div[style*="background: #0f172a"], div[style*="background: #0f172a"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    .hero, .app-hero, .header, .banner, .main-header {
        background:linear-gradient(135deg, #06101f 0%, #0b1220 55%, #141b2d 100%) !important;
        border:1px solid rgba(201,162,79,0.22) !important;
        box-shadow:0 20px 50px rgba(0,0,0,0.35) !important;
    }

    /* 입력창/셀렉트 */
    input, textarea, select,
    div[data-baseweb="input"],
    div[data-baseweb="input"] *,
    div[data-baseweb="select"],
    div[data-baseweb="select"] *,
    div[data-baseweb="textarea"],
    div[data-baseweb="textarea"] * {
        background:#ffffff !important;
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
        border-color:#cbd5e1 !important;
    }

    div[data-baseweb="select"] svg,
    div[data-baseweb="input"] svg {
        color:#0f172a !important;
        fill:#0f172a !important;
    }

    /* 일반 버튼 */
    .stButton button {
        background:linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
        border:1px solid #cbd5e1 !important;
        border-radius:14px !important;
        font-weight:850 !important;
    }
    .stButton button * {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }

    /* 하단 네비게이션 */
    .bottom-nav, .bottom-nav *,
    .nav, .nav *,
    div[class*="bottom"], div[class*="bottom"] *,
    div[class*="nav"], div[class*="nav"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    .bottom-nav, .nav {
        background:linear-gradient(135deg, #030712 0%, #06101f 100%) !important;
        border:1px solid rgba(201,162,79,0.25) !important;
        box-shadow:0 14px 40px rgba(0,0,0,0.45) !important;
    }

    .bottom-nav .active, .nav .active,
    .bottom-nav .active *, .nav .active *,
    div[class*="active"], div[class*="active"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    /* 표 */
    table {
        background:#ffffff !important;
        border-radius:14px !important;
        overflow:hidden !important;
    }
    table, th, td {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
        background:#ffffff !important;
        border-color:#e2e8f0 !important;
    }

    .flow-buy, .target-buy {
        color:#dc2626 !important;
        -webkit-text-fill-color:#dc2626 !important;
    }
    .flow-sell, .target-stop {
        color:#2563eb !important;
        -webkit-text-fill-color:#2563eb !important;
    }

    /* Streamlit 탭 */
    [role="tab"], [role="tab"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    /* 모바일 */
    @media (max-width:700px) {
        .block-container {
            padding-left:0.85rem !important;
            padding-right:0.85rem !important;
        }
        .card, .scorebox, .top-card, .timing-box {
            border-radius:20px !important;
        }
        h1 {font-size:1.65rem !important;}
        h2 {font-size:1.35rem !important;}
        h3 {font-size:1.15rem !important;}
    }


    /* V90-1.4-1 하단 메뉴 전용 색상 안정화 */
    .bottom-nav,
    .nav,
    div[class*="bottom-nav"],
    div[class*="bottom_nav"] {
        background:#050b18 !important;
        border:1px solid rgba(201,162,79,0.28) !important;
        box-shadow:0 14px 35px rgba(0,0,0,0.35) !important;
    }

    .bottom-nav *,
    .nav *,
    div[class*="bottom-nav"] *,
    div[class*="bottom_nav"] * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        opacity:1 !important;
    }

    .bottom-nav button,
    .nav button,
    div[class*="bottom-nav"] button,
    div[class*="bottom_nav"] button {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        background:transparent !important;
        border:0 !important;
    }

    .bottom-nav .active,
    .nav .active,
    div[class*="bottom-nav"] .active,
    div[class*="bottom_nav"] .active {
        background:#c9a24f !important;
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        border-radius:999px !important;
    }

    .bottom-nav .active *,
    .nav .active *,
    div[class*="bottom-nav"] .active *,
    div[class*="bottom_nav"] .active * {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        opacity:1 !important;
    }


    /* V90-1.4-2 보유종목 카드 전용 복구 */
    .holding-card,
    .holding-card *,
    .holding-price-card,
    .holding-price-card *,
    .portfolio-holding-card,
    .portfolio-holding-card *,
    .my-stock-card,
    .my-stock-card * {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
        opacity:1 !important;
    }

    .holding-card,
    .holding-price-card,
    .portfolio-holding-card,
    .my-stock-card {
        background:#ffffff !important;
        border:1px solid #e5e7eb !important;
        border-radius:20px !important;
    }

    .holding-card b,
    .holding-card strong,
    .holding-card h3,
    .holding-price-card b,
    .holding-price-card strong,
    .holding-price-card h3,
    .portfolio-holding-card b,
    .portfolio-holding-card strong,
    .portfolio-holding-card h3,
    .my-stock-card b,
    .my-stock-card strong,
    .my-stock-card h3 {
        color:#020617 !important;
        -webkit-text-fill-color:#020617 !important;
        font-weight:950 !important;
    }

    .holding-card .profit-plus,
    .holding-price-card .profit-plus,
    .portfolio-holding-card .profit-plus,
    .my-stock-card .profit-plus {
        color:#16a34a !important;
        -webkit-text-fill-color:#16a34a !important;
    }

    .holding-card .profit-minus,
    .holding-price-card .profit-minus,
    .portfolio-holding-card .profit-minus,
    .my-stock-card .profit-minus {
        color:#dc2626 !important;
        -webkit-text-fill-color:#dc2626 !important;
    }


    /* V91-1 고급형 보유종목 카드 UI */
    .premium-holding-card {
        background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%) !important;
        border:1px solid rgba(226,232,240,0.98) !important;
        border-radius:22px !important;
        padding:18px !important;
        margin:14px 0 !important;
        box-shadow:0 18px 45px rgba(0,0,0,0.22) !important;
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
    }
    .premium-holding-card * {
        color:#0f172a !important;
        -webkit-text-fill-color:#0f172a !important;
        opacity:1 !important;
    }
    .premium-stock-head {
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:10px;
        border-bottom:1px solid #e2e8f0;
        padding-bottom:12px;
        margin-bottom:12px;
    }
    .premium-stock-name {
        font-size:22px;
        line-height:1.25;
        font-weight:950;
        color:#020617 !important;
        -webkit-text-fill-color:#020617 !important;
    }
    .premium-stock-sub {
        font-size:13px;
        color:#64748b !important;
        -webkit-text-fill-color:#64748b !important;
        font-weight:800;
        margin-top:4px;
    }
    .premium-badge {
        display:inline-block;
        background:#07111f;
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        border-radius:999px;
        padding:6px 10px;
        font-size:12px;
        font-weight:900;
        white-space:nowrap;
    }
    .premium-badge.profit { background:#16a34a !important; }
    .premium-badge.loss { background:#dc2626 !important; }
    .premium-metrics {
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:10px;
    }
    .premium-metric {
        background:#f1f5f9;
        border:1px solid #e2e8f0;
        border-radius:16px;
        padding:10px 12px;
    }
    .premium-label {
        font-size:12px;
        color:#64748b !important;
        -webkit-text-fill-color:#64748b !important;
        font-weight:850;
        margin-bottom:5px;
    }
    .premium-value {
        font-size:16px;
        color:#020617 !important;
        -webkit-text-fill-color:#020617 !important;
        font-weight:950;
    }
    .premium-profit-plus {
        color:#16a34a !important;
        -webkit-text-fill-color:#16a34a !important;
    }
    .premium-profit-minus {
        color:#dc2626 !important;
        -webkit-text-fill-color:#dc2626 !important;
    }
    .premium-note {
        margin-top:10px;
        font-size:12px;
        color:#475569 !important;
        -webkit-text-fill-color:#475569 !important;
        font-weight:800;
        line-height:1.45;
    }
    @media (max-width:700px) {
        .premium-holding-card {padding:15px !important; border-radius:20px !important;}
        .premium-stock-name {font-size:20px;}
        .premium-metrics {grid-template-columns:1fr 1fr; gap:8px;}
        .premium-metric {padding:9px 10px;}
        .premium-value {font-size:14px;}
    }


    /* V91-2 포트폴리오 건강도 카드 */
    .health-card{background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:20px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.22)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .health-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .health-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px}
    .health-title{font-size:24px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1.25}
    .health-sub{font-size:13px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:4px}
    .health-score{text-align:right;min-width:92px}
    .health-score-num{font-size:34px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1}
    .health-grade{font-size:14px;font-weight:950;margin-top:5px}
    .health-bar{width:100%;height:16px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin:12px 0 16px}
    .health-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#dc2626 0%,#f59e0b 38%,#22c55e 100%)}
    .health-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
    .health-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:16px;padding:10px 12px}
    .health-label{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:5px}
    .health-value{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .health-section{margin-top:12px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:13px;font-weight:850;line-height:1.65;color:#334155!important;-webkit-text-fill-color:#334155!important}
    .health-action{margin-top:12px;background:#07111f;color:#fff!important;-webkit-text-fill-color:#fff!important;border-radius:16px;padding:12px 14px;font-size:14px;font-weight:950;line-height:1.5}
    .health-action *{color:#fff!important;-webkit-text-fill-color:#fff!important}
    @media(max-width:700px){.health-card{padding:16px!important;border-radius:21px!important}.health-title{font-size:21px}.health-score-num{font-size:30px}.health-grid{grid-template-columns:1fr 1fr;gap:8px}.health-box{padding:9px 10px}}
    /* V91-2 기존 투자온도계 숨김 후보 */
    .thermo-card,.temperature-card,.gauge-card,.temp-card{display:none!important}

    </style>
    """, unsafe_allow_html=True)

def header():
    st.markdown(f'<div class="hero"><h1>{APP_TITLE}</h1><p>{APP_SUBTITLE}</p></div>', unsafe_allow_html=True)

def card(title, body):
    st.markdown(f'<div class="card"><div class="title">{title}</div><div class="body">{body}</div></div>', unsafe_allow_html=True)

def html_card(title, body):
    st.markdown(
        f'<div class="card"><div class="title">{title}</div><div class="body">{body}</div></div>',
        unsafe_allow_html=True
    )


def nav(tab):
    items = [("home","🏠<br>홈"),("news","📰<br>뉴스"),("rec","🚀<br>추천"),("holdings","📦<br>내종목"),("profile","📈<br>투자기록")]
    html = '<div class="nav">'
    for key, label in items:
        html += f'<a class="{"active" if key == tab else ""}" href="?tab={key}">{label}</a>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def current_tab():
    try:
        return st.query_params.get("tab", "home")
    except Exception:
        return "home"

def render_action(data, show_detail=True):
    a = one_action(data)
    st.markdown(
        f'<div class="action">'
        f'<div class="action-k">🎯 오늘의 단 하나의 행동</div>'
        f'<div class="action-main">{a["main"]}</div>'
        f'<div class="action-sub">신뢰도 {a["conf"]}%<br>{a["sub"]}</div>'
        f'<span class="badge">{a["badge"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if show_detail and a.get("detail"):
        card("판단근거", a["detail"])

def investment_period_hint(data):
    _, _, _, _, weights, rows = metrics(data)
    semi = weights.get("반도체", 0)
    us = weights.get("미국지수", 0)
    power = weights.get("전력/자동화", 0)

    if us < 25:
        return "장기 적합", "미국지수 비중 보강은 장기 안정성에 도움이 됩니다."
    if semi >= 50:
        return "중기 관망", "반도체 비중이 높아 단기 추가매수보다 중기 관찰이 필요합니다."
    if power < 25:
        return "중기 적합", "전력/자동화 비중은 성장 테마 관점에서 중기 후보입니다."
    return "보유 유지", "현재는 특정 기간을 정해 공격적으로 움직이기보다 보유 점검이 적절합니다."



def emergency_items(data):
    """
    V91-2.2:
    portfolio_health()가 dict 구조로 바뀐 뒤에도 긴급상황판이 안전하게 동작하도록 연결 수정.
    """
    items = []

    try:
        h = portfolio_health(data)
    except Exception:
        h = {
            "score": 50,
            "grade": "🟡 보통",
            "warnings": ["건강도 계산 데이터 일부를 확인하지 못했습니다."],
            "action": "관망 우선 · 보유종목 데이터를 확인하세요.",
        }

    try:
        hs = int(h.get("score", 50) or 50)
    except Exception:
        hs = 50

    hg = h.get("grade", "🟡 보통")
    risk_reasons = h.get("warnings", []) or []
    risk_action = h.get("action", "관망 우선 · 보유종목 데이터를 확인하세요.")

    if hs < 30:
        items.append(("🔴", "위험 포트폴리오 건강도 낮음", f"건강도 {hs}점 · {hg}<br>{risk_action}"))
    elif hs < 50:
        items.append(("🟠", "경고 포트폴리오 점검 필요", f"건강도 {hs}점 · {hg}<br>{risk_action}"))
    elif hs < 70:
        items.append(("🟡", "주의 포트폴리오 보통권", f"건강도 {hs}점 · {hg}<br>{risk_action}"))

    for rr in risk_reasons[:2]:
        if "부족" in rr or "높" in rr or "위험" in rr or "손실" in rr:
            items.append(("🟡", "주의 " + rr[:28], rr))

    try:
        _, _, _, _, weights, rows = metrics(data)
        target = target_return(data)
        for n, q, a, r in rows:
            if not r:
                continue

            grade, reason = risk_grade_simple(n, r)
            if "위험" in grade:
                items.append(("🔴", f"위험 {n}", reason))
            elif "주의" in grade:
                items.append(("🟡", f"주의 {n}", reason))

            try:
                score, sig, stock_reason = stock_signal(n, q, a, r, weights, target)
                if score < 40:
                    items.append(("🟠", f"경고 {n} 종목점수 낮음", f"종목점수 {score}점 · {sig}<br>{stock_reason}"))
            except Exception:
                pass
    except Exception:
        pass

    clean = []
    seen = set()
    for icon, title, body in items:
        key = (title, body)
        if key not in seen:
            clean.append((icon, title, body))
            seen.add(key)

    return clean[:6]


def render_emergency_board(data):
    try:
        items = emergency_items(data)
    except Exception:
        items = []

    if not items:
        card("🚨 긴급상황판", "🟢 긴급상황 없음<br>현재 큰 위험 신호는 없습니다.")
        return

    body = ""
    counts = {"🔴": 0, "🟠": 0, "🟡": 0}
    for icon, title, detail in items:
        if icon in counts:
            counts[icon] += 1
        body += f"{icon} <b>{title}</b><br>{detail}<br><br>"

    summary = f"🔴 위험 {counts['🔴']}건 · 🟠 경고 {counts['🟠']}건 · 🟡 주의 {counts['🟡']}건<br><br>"
    card("🚨 긴급상황판", summary + body)


def render_investment_thermometer(data):
    """
    V91-2.3:
    기존 투자온도계 함수가 portfolio_health()를 예전 튜플 방식으로 호출하던 오류 수정.
    이제 온도계 대신 포트폴리오 건강도 카드를 표시합니다.
    """
    try:
        render_portfolio_health(data)
    except Exception:
        st.markdown(
            '<div class="health-card">'
            '<div class="health-title">❤️ 포트폴리오 건강도</div>'
            '<div class="health-section">건강도 계산 중 일부 데이터 오류가 있어 기본 상태로 표시합니다.</div>'
            '<div class="health-action">오늘 행동: 관망 우선 · 보유종목 데이터를 확인하세요.</div>'
            '</div>',
            unsafe_allow_html=True
        )


def stock_search_db():
    base = list(code_map().keys()) + [
        "TIGER 미국나스닥100",
        "KODEX 미국나스닥100",
        "TIGER 미국배당다우존스",
        "KODEX 200",
        "TIGER 2차전지테마",
        "KODEX 반도체",
        "TIGER 차이나전기차",
        "ACE 미국빅테크TOP7",
    ]
    try:
        for h in load_data().get("holdings", []):
            n = norm(h.get("name", ""))
            if n and n not in base:
                base.append(n)
    except Exception:
        pass
    return sorted(list(dict.fromkeys(base)))

def grade_from_score(score):
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C"
    return "D"

def horizon_scores(name, general_score, my_score):
    sec = sector(name)

    short = general_score - 5
    mid = general_score
    long = general_score

    if sec == "미국지수":
        short -= 22
        mid += 8
        long += 22
    elif sec == "반도체":
        short += 6
        mid += 10
        long += 4
    elif sec in ["전력/자동화", "전력/에너지"]:
        short -= 3
        mid += 14
        long += 7
    elif sec == "2차전지":
        short += 8
        mid += 3
        long -= 8
    elif sec == "방산/조선":
        short += 4
        mid += 12
        long += 3
    elif sec == "로봇":
        short += 8
        mid += 6
        long -= 5
    elif sec == "바이오":
        short += 10
        mid += 2
        long -= 8
    elif sec == "금융/배당":
        short -= 10
        mid += 5
        long += 15
    elif sec == "디스플레이":
        short += 3
        mid -= 2
        long -= 10
    elif sec == "자동차":
        short -= 2
        mid += 6
        long += 4

    # 경규님 기준 점수 보정: 경규님 점수가 낮으면 전체 기간 신뢰도를 낮춘다.
    personal_gap = my_score - general_score
    short += personal_gap * 0.3
    mid += personal_gap * 0.5
    long += personal_gap * 0.7

    return {
        "단기": max(0, min(100, int(short))),
        "중기": max(0, min(100, int(mid))),
        "장기": max(0, min(100, int(long))),
    }

def horizon_decision(name, horizons, my_score):
    best_name, best_score = sorted(horizons.items(), key=lambda x: x[1], reverse=True)[0]
    second_score = sorted(horizons.values(), reverse=True)[1] if len(horizons) > 1 else 0
    gap = best_score - second_score

    confidence = int(min(95, max(45, best_score * 0.75 + gap * 1.5)))
    if my_score < 55:
        confidence = max(40, confidence - 12)

    if best_name == "단기":
        period_text = "단기 적합"
        period_range = "1주~3개월"
        strategy = "빠른 변동성 확인이 필요합니다. 목표 수익 또는 손절 기준을 짧게 잡는 편이 좋습니다."
    elif best_name == "중기":
        period_text = "중기 적합"
        period_range = "3개월~1년"
        strategy = "테마와 실적 흐름을 함께 보면서 분할 접근하는 전략이 어울립니다."
    else:
        period_text = "장기 적합"
        period_range = "1년 이상"
        strategy = "단기 등락보다 적립식·분산 관점으로 길게 보는 전략이 어울립니다."

    if my_score >= 80 and best_score >= 75:
        action = "관심/편입 검토"
    elif my_score >= 65:
        action = "소액 분할 검토"
    elif my_score >= 55:
        action = "관망"
    else:
        action = "보류 또는 대체종목 검토"

    return {
        "best": best_name,
        "score": best_score,
        "confidence": confidence,
        "period_text": period_text,
        "period_range": period_range,
        "strategy": strategy,
        "action": action,
    }


def analyze_stock_for_search(name, data):
    n = norm(name)
    md = fetch_market_data(n)
    price, src = md.get("price"), md.get("src")
    sec = sector(n)
    _, _, _, _, weights, rows = metrics(data)

    general = 60
    reasons = []

    if price:
        general += 5
        live_tag = "실시간" if md.get("is_live") else "기본값"
        reasons.append(f"현재가 확인 가능: {won(price)} · {live_tag}")
    else:
        general -= 10
        reasons.append("현재가 확인이 제한적입니다.")

    if md.get("change_rate") is not None:
        cr = md.get("change_rate")
        if cr <= -3:
            general -= 5
            reasons.append(f"당일 등락률 {cr:.2f}%로 단기 변동성 주의가 필요합니다.")
        elif cr >= 3:
            general += 3
            reasons.append(f"당일 등락률 {cr:.2f}%로 단기 모멘텀이 있습니다.")

    pos52 = position_52w(price, md.get("low_52w"), md.get("high_52w"))
    if pos52 is not None:
        if pos52 >= 85:
            general -= 3
            reasons.append(f"52주 구간 상단부({pos52:.0f}%)에 가까워 추격매수는 신중합니다.")
        elif pos52 <= 25:
            general += 3
            reasons.append(f"52주 구간 하단부({pos52:.0f}%)로 가격 부담은 낮은 편입니다.")

    if sec == "미국지수":
        general += 18
        reasons.append("지수형 ETF는 장기 분산투자에 유리합니다.")
    elif sec == "반도체":
        general += 10
        reasons.append("AI/반도체 테마는 성장성은 있으나 변동성이 있습니다.")
    elif sec == "전력/자동화":
        general += 12
        reasons.append("전력/자동화 테마는 중기 성장 후보입니다.")
    elif sec == "디스플레이":
        general -= 3
        reasons.append("디스플레이 업황은 변동성 확인이 필요합니다.")
    elif sec == "2차전지":
        general += 6
        reasons.append("2차전지는 성장성은 있으나 변동성이 큰 테마입니다.")
    elif sec == "전력/에너지":
        general += 12
        reasons.append("전력/에너지 인프라 테마는 중기 성장 후보입니다.")
    elif sec == "자동차":
        general += 5
        reasons.append("자동차 업종은 실적과 환율 영향을 함께 봐야 합니다.")
    elif sec == "플랫폼":
        general += 2
        reasons.append("플랫폼 업종은 성장성보다 실적 회복 여부가 중요합니다.")
    elif sec == "바이오":
        general += 3
        reasons.append("바이오는 성장 가능성이 있지만 변동성과 뉴스 민감도가 큽니다.")
    elif sec == "방산/조선":
        general += 10
        reasons.append("방산/조선은 수주와 정책 모멘텀이 중요한 중기 테마입니다.")
    elif sec == "로봇":
        general += 8
        reasons.append("로봇 테마는 성장성은 크지만 변동성이 높은 편입니다.")
    elif sec == "금융/배당":
        general += 7
        reasons.append("금융/배당주는 방어와 배당 관점에서 볼 수 있습니다.")
    elif sec == "소비재":
        general += 3
        reasons.append("소비재는 경기와 실적 안정성을 함께 봐야 합니다.")

    my_score = general
    my_reasons = []
    current_weight = weights.get(sec, 0)

    if sec == "반도체" and current_weight >= 45:
        my_score -= 18
        my_reasons.append(f"경규님 포트에서 반도체 비중이 {current_weight:.1f}%로 높습니다.")
    elif sec == "미국지수" and current_weight < 30:
        my_score += 15
        my_reasons.append(f"미국지수 비중이 {current_weight:.1f}%라 장기 안정성 보강에 좋습니다.")
    elif sec == "전력/자동화" and current_weight < 25:
        my_score += 8
        my_reasons.append(f"전력/자동화 비중이 {current_weight:.1f}%라 중기 보강 후보입니다.")
    elif sec == "디스플레이":
        my_score -= 8
        my_reasons.append("현재 포트 기준 디스플레이는 보수적으로 보는 편이 좋습니다.")
    elif sec in ["2차전지", "바이오"]:
        my_score -= 4
        my_reasons.append("경규님 스타일 기준으로는 변동성이 있어 분할 접근이 좋습니다.")
    elif sec in ["전력/에너지"]:
        my_score += 6
        my_reasons.append("전력/에너지 테마는 기존 관심종목과 연결성이 있습니다.")
    elif sec in ["방산/조선", "로봇"]:
        my_score += 2
        my_reasons.append("성장 테마로 관심 가치는 있지만 분할 접근이 좋습니다.")
    elif sec in ["금융/배당"]:
        my_score += 5
        my_reasons.append("포트 안정성을 높이는 방어형 후보가 될 수 있습니다.")
    else:
        my_reasons.append("현재 포트와 큰 충돌은 없습니다.")

    general = max(0, min(100, int(general)))
    my_score = max(0, min(100, int(my_score)))
    horizons = horizon_scores(n, general, my_score)

    decision = horizon_decision(n, horizons, my_score)
    period_text = decision["period_text"]
    period_desc = f'{decision["period_range"]} · 신뢰도 {decision["confidence"]}% · {decision["strategy"]}' 

    return {
        "name": n,
        "price": price,
        "src": src,
        "sector": sec,
        "change_rate": md.get("change_rate"),
        "volume": md.get("volume"),
        "high_52w": md.get("high_52w"),
        "low_52w": md.get("low_52w"),
        "pos52": position_52w(price, md.get("low_52w"), md.get("high_52w")),
        "is_live": md.get("is_live"),
        "investor_flow": fetch_investor_flow(n),
        "general": general,
        "my_score": my_score,
        "general_grade": grade_from_score(general),
        "my_grade": grade_from_score(my_score),
        "horizons": horizons,
        "period_text": period_text,
        "period_desc": period_desc,
        "decision": decision,
        "reasons": reasons,
        "my_reasons": my_reasons,
    }

def render_stock_search(data):
    st.markdown(
        '<div class="card"><div class="title">🔎 종목검색</div>'
        '<div class="body">검색어를 입력하면 관련 종목 목록이 아래에 표시됩니다.</div></div>',
        unsafe_allow_html=True
    )

    options = stock_search_db()

    query = st.text_input(
        "종목 검색",
        placeholder="예: 에코, 대한전선, 삼성전자",
        key="home_stock_search_text"
    ).strip()

    matches = []
    if query:
        q = query.lower()
        matches = [x for x in options if q in x.lower()]
        if query not in matches:
            matches = [query] + matches

    if matches:
        st.markdown('<div class="search-hint">검색 결과에서 하나를 선택하세요.</div>', unsafe_allow_html=True)
        for i, item in enumerate(matches[:6]):
            if st.button(item, use_container_width=True, key=f"search_pick_{i}_{item}"):
                st.session_state["selected_search_stock"] = item

    selected = st.session_state.get("selected_search_stock", "")
    if selected:
        st.info(f"선택된 종목: {selected}")

    name = norm(selected or query)

    if st.button("종목 분석", use_container_width=True, key="analyze_stock_btn_v793"):
        if not name:
            st.warning("종목명을 입력하세요.")
            return

        result = analyze_stock_for_search(name, data)

        d = result.get("decision", {})
        live_line = f"현재가 {won(result['price']) if result['price'] else '확인 제한'} · {result['src']}"
        if result.get("change_rate") is not None:
            live_line += f"<br>등락률: {result['change_rate']:.2f}%"
        if result.get("volume"):
            live_line += f"<br>거래량: {result['volume']:,.0f}"
        if result.get("pos52") is not None:
            live_line += f"<br>52주 위치: {result['pos52']:.0f}%"

        card(
            f"{result['name']} 핵심 판단",
            f"<b>추천기간: {result['period_text']}</b><br>"
            f"예상기간: {d.get('period_range', '-')}<br>"
            f"신뢰도: {d.get('confidence', '-')}%<br>"
            f"현재 행동: {d.get('action', '-')}<br><br>"
            f"{d.get('strategy', '')}<br><br>"
            f"{live_line}<br>"
            f"섹터: {result['sector']}"
        )

        html = f"""
        <div class="grade-card">
            <div class="grade-top">
                <div class="grade-name">{result["name"]}</div>
                <div class="grade-pill">{result.get("decision", {}).get("period_text", "기간판정")}</div>
            </div>
            <div class="grade-grid">
                <div class="mini-box">일반 기준<br><b>{result["general"]}점</b> · {result["general_grade"]}</div>
                <div class="mini-box">경규님 기준<br><b>{result["my_score"]}점</b> · {result["my_grade"]}</div>
            </div>
            <div class="horizon-row">
                <div class="horizon-chip">단기<br>{result["horizons"]["단기"]}점</div>
                <div class="horizon-chip">중기<br>{result["horizons"]["중기"]}점</div>
                <div class="horizon-chip">장기<br>{result["horizons"]["장기"]}점</div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

        flow = result.get("investor_flow", {}) or {}
        html_card("외국인/기관 수급", investor_flow_table_html(flow))

        html_card("위치 / 진입타이밍 / 선반영", timing_engine_html(result["name"], result["price"], result))
        html_card("목표가 / 손절가 근거", target_plan_html(result["name"], result["price"], result))
        render_price_chart(result["name"], result["price"], result)

        card(
            "분석 근거",
            "<b>일반 기준</b><br>" + "<br>".join([f"① {x}" for x in result["reasons"][:3]]) +
            "<br><br><b>경규님 기준</b><br>" + "<br>".join([f"① {x}" for x in result["my_reasons"][:3]])
        )





def strip_html(s):
    try:
        s = re.sub(r"<script[\s\S]*?</script>", "", str(s))
        s = re.sub(r"<style[\s\S]*?</style>", "", s)
        s = re.sub(r"<[^>]+>", " ", s)
        s = s.replace("&nbsp;", " ").replace("\xa0", " ")
        return re.sub(r"\s+", " ", s).strip()
    except Exception:
        return ""

def parse_signed_number(v):
    try:
        s = str(v).strip()
        s = s.replace(",", "").replace("%", "").replace("+", "")
        s = re.sub(r"[^0-9\.\-]", "", s)
        if s in ["", "-", "."]:
            return None
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        return None


def flow_cell(v):
    try:
        v = float(v or 0)
        if v > 0:
            return f'<span class="flow-buy">▲ {v:,.0f}주</span>'
        if v < 0:
            return f'<span class="flow-sell">▼ {abs(v):,.0f}주</span>'
        return '<span class="flow-flat">-</span>'
    except Exception:
        return '<span class="flow-flat">-</span>'

def ratio_cell(v):
    try:
        if v is None:
            return "-"
        return f"{float(v):.2f}%"
    except Exception:
        return "-"

def investor_flow_table_html(flow):
    if not flow or not flow.get("is_live"):
        return "외국인/기관 수급 데이터 준비중"

    f5 = flow.get("foreign_5") or 0
    f20 = flow.get("foreign_20") or 0
    i5 = flow.get("institution_5") or 0
    i20 = flow.get("institution_20") or 0
    fr = flow.get("foreign_ratio")

    if f5 > 0 and i5 > 0:
        judge = "외국인·기관 동반 순매수"
    elif f5 > 0 and i5 < 0:
        judge = "외국인 매수 / 기관 매도"
    elif f5 < 0 and i5 > 0:
        judge = "외국인 매도 / 기관 매수"
    elif f5 < 0 and i5 < 0:
        judge = "외국인·기관 동반 순매도"
    else:
        judge = "수급 중립"

    return (
        '<table class="flow-table">'
        '<tr><th>구분</th><th>최근 5일</th><th>최근 20일</th><th>보유율</th></tr>'
        f'<tr><td>외국인</td><td>{flow_cell(f5)}</td><td>{flow_cell(f20)}</td><td>{ratio_cell(fr)}</td></tr>'
        f'<tr><td>기관</td><td>{flow_cell(i5)}</td><td>{flow_cell(i20)}</td><td>-</td></tr>'
        '</table>'
        f'<div class="flow-note"><b>종합판단: {judge}</b><br>'
        '▲ 빨강 = 순매수 / ▼ 파랑 = 순매도<br>'
        '5일·20일 수량은 총 보유수량이 아니라 해당 기간의 순매수·순매도 합계입니다.<br>'
        '외국인 보유율은 확인 가능한 경우에만 표시됩니다.</div>'
    )


def investor_flow_brief(flow):
    if not flow or not flow.get("is_live"):
        return "외국인/기관 수급 데이터 준비중"
    f5 = flow.get("foreign_5") or 0
    i5 = flow.get("institution_5") or 0

    f_txt = "순매수" if f5 > 0 else ("순매도" if f5 < 0 else "중립")
    i_txt = "순매수" if i5 > 0 else ("순매도" if i5 < 0 else "중립")
    return f"외국인 5일 {f_txt} · 기관 5일 {i_txt}"


def fetch_investor_flow(name):
    """
    V80-6 1차:
    네이버 금융 투자자별 매매동향 페이지를 시도.
    페이지 구조가 바뀌거나 ETF/해외주식처럼 데이터가 없으면 안전하게 준비중 처리.
    """
    name = norm(name)
    code = code_map().get(name)
    result = {
        "foreign_5": None,
        "foreign_20": None,
        "institution_5": None,
        "institution_20": None,
        "foreign_ratio": None,
        "src": "수급 데이터 준비중",
        "is_live": False,
    }

    if not code:
        return result

    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        try:
            res.encoding = "euc-kr"
        except Exception:
            pass
        html = res.text

        rows = re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", html)
        parsed = []

        for row in rows:
            txt = strip_html(row)
            if not re.search(r"\d{4}\.\d{2}\.\d{2}", txt):
                continue

            cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)
            vals = [strip_html(c) for c in cells]
            vals = [v for v in vals if v]

            # 예상 컬럼: 날짜, 종가, 전일비, 등락률, 거래량, 기관, 외국인, 보유주수, 보유율
            if len(vals) < 7:
                continue

            inst = parse_signed_number(vals[5]) if len(vals) > 5 else None
            foreign = parse_signed_number(vals[6]) if len(vals) > 6 else None
            ratio = parse_signed_number(vals[-1]) if vals else None

            if inst is None and foreign is None:
                continue

            parsed.append({
                "institution": inst or 0,
                "foreign": foreign or 0,
                "foreign_ratio": ratio,
            })

        if parsed:
            first20 = parsed[:20]
            first5 = parsed[:5]
            result.update({
                "foreign_5": sum(x["foreign"] for x in first5),
                "foreign_20": sum(x["foreign"] for x in first20),
                "institution_5": sum(x["institution"] for x in first5),
                "institution_20": sum(x["institution"] for x in first20),
                "foreign_ratio": next((x.get("foreign_ratio") for x in parsed if x.get("foreign_ratio") is not None), None),
                "src": f"네이버 수급 {code}",
                "is_live": True,
            })

    except Exception:
        pass

    return result

def investor_flow_summary(name):
    try:
        flow = fetch_investor_flow(name)
        return investor_flow_table_html(flow)
    except Exception:
        return "외국인/기관 수급 데이터 준비중"


def supply_profile_by_sector(sec):
    # V80-5 1차: 실제 외국인/기관 데이터 연결 전 섹터별 수급 민감도 기준
    if sec in ["반도체", "2차전지", "바이오", "로봇"]:
        return {"foreign": 35, "institution": 25, "volume": 30, "stability": 10}
    if sec in ["전력/에너지", "전력/자동화", "방산/조선"]:
        return {"foreign": 25, "institution": 35, "volume": 25, "stability": 15}
    if sec in ["미국지수", "금융/배당"]:
        return {"foreign": 20, "institution": 30, "volume": 10, "stability": 40}
    return {"foreign": 25, "institution": 25, "volume": 25, "stability": 25}

def estimate_supply_score(name, r):
    sec = sector(name)
    weights = supply_profile_by_sector(sec)
    try:
        flow = fetch_investor_flow(name)
    except Exception:
        flow = {"is_live": False}

    score = 60
    reasons = []

    cr = r.get("change_rate") if r else None
    pos52 = r.get("pos52") if r else None

    if cr is not None:
        if cr >= 3:
            score += 6
            reasons.append(f"등락률 {cr:.2f}%로 단기 수급 유입 가능성이 있습니다.")
        elif cr <= -3:
            score -= 6
            reasons.append(f"등락률 {cr:.2f}%로 단기 수급 이탈 주의가 필요합니다.")
        else:
            reasons.append(f"등락률 {cr:.2f}%로 가격 흐름은 중립권입니다.")
    else:
        reasons.append("등락률 데이터가 부족해 가격 흐름은 중립으로 봅니다.")

    if pos52 is not None:
        if pos52 >= 85:
            score -= 4
            reasons.append(f"52주 위치 {pos52:.0f}%로 과열 구간 접근 가능성이 있습니다.")
        elif pos52 <= 25:
            score += 4
            reasons.append(f"52주 위치 {pos52:.0f}%로 가격 부담은 낮은 편입니다.")

    if flow.get("is_live"):
        reasons.append(investor_flow_brief(flow))
        f5 = flow.get("foreign_5") or 0
        i5 = flow.get("institution_5") or 0
        f20 = flow.get("foreign_20") or 0
        i20 = flow.get("institution_20") or 0

        if f5 > 0:
            score += 7
            reasons.append(f"외국인 최근 5일 {f5:,.0f}주 순매수입니다.")
        elif f5 < 0:
            score -= 7
            reasons.append(f"외국인 최근 5일 {abs(f5):,.0f}주 순매도입니다.")

        if i5 > 0:
            score += 6
            reasons.append(f"기관 최근 5일 {i5:,.0f}주 순매수입니다.")
        elif i5 < 0:
            score -= 6
            reasons.append(f"기관 최근 5일 {abs(i5):,.0f}주 순매도입니다.")

        if f20 > 0 and i20 > 0:
            score += 6
            reasons.append("20일 기준 외국인과 기관이 함께 매수 우위입니다.")
        elif f20 < 0 and i20 < 0:
            score -= 8
            reasons.append("20일 기준 외국인과 기관이 함께 매도 우위입니다.")
    else:
        reasons.append("외국인/기관 실제 수급은 아직 확인되지 않아 추정 점수로 반영합니다.")

    if sec in ["미국지수", "금융/배당"]:
        score += 3
        reasons.append("장기 안정형 성격으로 급격한 수급 이탈 위험은 낮게 봅니다.")
    elif sec in ["바이오", "2차전지", "로봇"]:
        score -= 2
        reasons.append("테마 변동성이 있어 수급 변화에 민감합니다.")

    score = max(0, min(100, int(score)))

    if score >= 75:
        grade = "🟢 수급 양호"
    elif score >= 60:
        grade = "🟡 수급 보통"
    elif score >= 45:
        grade = "🟠 수급 주의"
    else:
        grade = "🔴 수급 위험"

    return {
        "score": score,
        "grade": grade,
        "weights": weights,
        "reasons": reasons,
        "flow": flow,
    }


def portfolio_supply_score(data):
    _, total_value, _, _, weights, rows = metrics(data)
    if not rows:
        return {"score": 50, "grade": "🟠 수급 데이터 부족", "reasons": ["보유종목이 없습니다."]}

    total_score = 0
    total_weight = 0
    reasons = []

    for n, q, a, r in rows:
        if not r:
            continue
        value = r.get("value", q * a)
        w = value / total_value if total_value else 0
        s = estimate_supply_score(n, r)
        total_score += s["score"] * w
        total_weight += w
        reasons.append(f"{n}: {s['grade']} · {s['score']}점")

    score = int(total_score / total_weight) if total_weight else 50

    if score >= 75:
        grade = "🟢 양호"
    elif score >= 60:
        grade = "🟡 보통"
    elif score >= 45:
        grade = "🟠 주의"
    else:
        grade = "🔴 위험"

    return {
        "score": score,
        "grade": grade,
        "reasons": reasons[:5],
    }

def render_supply_card(data):
    s = portfolio_supply_score(data)
    reason_html = "<br>".join([f"① {x}" for x in s["reasons"]]) if s["reasons"] else "수급 판단 데이터가 부족합니다."
    html_card(
        "💰 수급 점수",
        f"{s['score']}점 · {s['grade']}<br><br>{reason_html}<br><br>"
        f"※ 5일·20일 수량은 총 보유수량이 아니라 해당 기간 순매수/순매도 합계입니다. 외국인 보유율은 확인 가능한 경우 표시됩니다."
    )


def portfolio_health_score(data):
    h = portfolio_health(data)
    hs = h.get('score', 50)
    hg = h.get('grade', '🟡 보통')
    hr = h.get('rate', 0)
    risk_reasons = h.get('warnings', [])
    risk_action = h.get('action', '')
    _, _, _, _, weights, rows = metrics(data)

    comments = []
    semi = weights.get("반도체", 0)
    us = weights.get("미국지수", 0)
    power = weights.get("전력/에너지", 0) + weights.get("전력/자동화", 0)

    if semi >= 55:
        comments.append(f"반도체 비중 {semi:.1f}%로 집중도가 높습니다.")
    if us < 20:
        comments.append(f"미국지수 비중 {us:.1f}%로 방어 비중 보강이 필요합니다.")
    if power >= 25:
        comments.append(f"전력/에너지 비중 {power:.1f}%로 성장 테마 노출이 있습니다.")
    if not comments:
        comments.append("현재 포트폴리오 구성은 큰 쏠림 없이 관리되고 있습니다.")

    if hs >= 80:
        grade = "🟢 양호"
    elif hs >= 65:
        grade = "🟡 보통"
    elif hs >= 50:
        grade = "🟠 주의"
    else:
        grade = "🔴 위험"

    return {
        "score": hs,
        "grade": grade,
        "summary": hr,
        "comments": comments,
        "action": risk_action,
    }

def today_one_line(data):
    a = one_action(data)
    ph = portfolio_health_score(data)
    if ph["score"] >= 75:
        return f'{a["main"]}. 현재 포트 상태는 비교적 안정적입니다.'
    if ph["score"] >= 60:
        return f'{a["main"]}. 신규매수는 분산 중심으로 천천히 보는 것이 좋습니다.'
    return f'{a["main"]}. 지금은 공격보다 위험 관리가 우선입니다.'

def render_port_health_card(data):
    ph = portfolio_health_score(data)
    comment_html = "<br>".join([f"① {x}" for x in ph["comments"][:3]])
    card(
        "❤️ 포트 건강도",
        f"{ph['score']}점 · {ph['grade']}<br><br>"
        f"{ph['summary']}<br><br>"
        f"{comment_html}"
    )

def component_scores(data):
    ph = portfolio_health_score(data)
    _, _, _, rate, weights, rows = metrics(data)

    market_score = 70
    port_score = ph["score"]

    stock_scores = []
    target = target_return(data)
    for n, q, a, r in rows:
        if r:
            stock_scores.append(stock_score(n, q, a, r, weights, target))
    stock_avg = int(sum(stock_scores) / len(stock_scores)) if stock_scores else 60

    news_score_val = 70
    try:
        all_news = rss_items()
        pos = neg = 0
        keys = related_keywords(data)
        for source, title, link in all_news:
            if news_matches(title, keys):
                impact, _ = news_impact(title)
                if "긍정" in impact:
                    pos += 1
                elif "부정" in impact:
                    neg += 1
        news_score_val += min(10, pos * 2)
        news_score_val -= min(15, neg * 3)
    except Exception:
        pass
    news_score_val = max(0, min(100, int(news_score_val)))

    supply = portfolio_supply_score(data)
    supply_score_val = supply["score"]

    final = int(
        market_score * 0.18 +
        port_score * 0.30 +
        stock_avg * 0.25 +
        news_score_val * 0.12 +
        supply_score_val * 0.15
    )

    return {
        "시장점수": market_score,
        "포트점수": port_score,
        "종목점수": stock_avg,
        "뉴스점수": news_score_val,
        "수급점수": supply_score_val,
        "종합점수": final,
    }

def render_reason_process(data):
    a = one_action(data)
    scores = component_scores(data)
    ph = portfolio_health_score(data)
    period, period_reason = investment_period_hint(data)

    rows = "<br>".join([f"{k}: <b>{v}점</b>" for k, v in scores.items()])

    card(
        "최종결론",
        f"{a['main']}<br>"
        f"신뢰도 {a['conf']}%<br>"
        f"현재 행동: {a['badge']}<br><br>"
        f"{a['sub']}"
    )

    card("판단 점수", rows)
    card("추천 투자기간", f"{period}<br>{period_reason}")

    reason_html = "<br>".join([f"① {x}" for x in ph["comments"][:4]])
    card(
        "판단근거",
        f"{a.get('detail','')}<br><br>"
        f"<b>포트 근거</b><br>{reason_html}<br><br>"
        f"<b>포트 행동 기준</b><br>{ph['action']}"
    )


def home(data):
    header()
    render_asset_top(data)
    render_emergency_board(data)
    render_portfolio_health(data)
    render_investment_thermometer(data)
    render_action(data, show_detail=False)
    render_port_health_card(data)
    render_supply_card(data)
    card("오늘의 한줄요약", today_one_line(data))

    if st.button("🔄 새로고침 / 다시 판단하기", use_container_width=True):
        st.rerun()

def find_holding(data, name):
    n = norm(name)
    for idx, h in enumerate(data.get("holdings", [])):
        if norm(h.get("name", "")) == n:
            return idx, h
    return None, None

def render_trade_panel(data):
    st.subheader("➕ 매수/매도 입력")

    existing = [norm(h.get("name", "")) for h in data.get("holdings", []) if h.get("name")]
    options = ["+ 새 종목 직접입력"] + existing
    selected = st.selectbox("종목 선택", options, index=0, key="trade_selected_v2")

    if selected == "+ 새 종목 직접입력":
        name = st.text_input("새 종목명", placeholder="", key="trade_new_name")
    else:
        name = selected

    idx, holding = find_holding(data, name) if name else (None, None)

    if holding:
        st.info(f"현재 보유: {sf(holding.get('qty')):g}주 · 평단 {won(holding.get('avg'))}")
    elif name:
        st.caption("신규 종목입니다. 매수수량과 매수평단가를 입력하면 보유종목에 추가됩니다.")
    else:
        st.caption("새 종목은 종목명을 먼저 입력한 뒤 매수수량과 매수평단가를 저장하세요.")

    tab_buy, tab_sell = st.tabs(["매수", "매도"])

    with tab_buy:
        b1, b2 = st.columns(2)
        with b1:
            buy_qty = st.number_input("매수수량", min_value=0.0, value=0.0, step=1.0, key="buy_qty_v2")
        with b2:
            buy_avg = st.number_input("매수평단가", min_value=0.0, value=0.0, step=100.0, key="buy_avg_v2")
        if st.button("매수 저장", use_container_width=True, key="buy_save_v2"):
            if name and buy_qty > 0 and buy_avg > 0:
                n = norm(name)
                idx, h = find_holding(data, n)
                if h:
                    old_qty, old_avg = sf(h.get("qty")), sf(h.get("avg"))
                    new_qty = old_qty + buy_qty
                    new_avg = ((old_qty * old_avg) + (buy_qty * buy_avg)) / new_qty
                    h.update({"name": n, "qty": new_qty, "avg": new_avg})
                else:
                    data["holdings"].append({"name": n, "qty": buy_qty, "avg": buy_avg, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
                save_data(data)
                st.success("매수 저장 완료")
                st.rerun()
            else:
                st.warning("종목명, 매수수량, 매수평단가를 확인하세요.")

    with tab_sell:
        if not holding:
            st.info("매도는 기존 보유종목을 선택했을 때만 가능합니다.")
        s1, s2, s3 = st.columns([1, 1, 1])
        with s1:
            sell_date = st.date_input("매도일", value=datetime.now().date(), key="trade_sell_date_v2")
        with s2:
            sell_qty = st.number_input("매도수량", min_value=0.0, value=0.0, step=1.0, key="trade_sell_qty_v2")
        with s3:
            sell_price = st.number_input("매도가", min_value=0.0, value=0.0, step=100.0, key="trade_sell_price_v2")

        if st.button("매도 저장", use_container_width=True, key="sell_save_v2"):
            idx, h = find_holding(data, name) if name else (None, None)
            if not h:
                st.warning("매도할 보유종목을 선택하세요.")
            elif sell_qty <= 0 or sell_price <= 0:
                st.warning("매도수량과 매도가를 확인하세요.")
            elif sell_qty > sf(h.get("qty")):
                st.warning("매도수량이 현재 보유수량보다 많습니다.")
            else:
                add_sell_record(name, sell_qty, h.get("avg"), sell_price, sell_date.strftime("%Y-%m-%d"))
                remain_qty = sf(h.get("qty")) - sell_qty
                if remain_qty <= 0:
                    data["holdings"].pop(idx)
                else:
                    h.update({"name": norm(name), "qty": remain_qty, "avg": h.get("avg")})
                save_data(data)
                st.success("매도 저장 완료")
                st.rerun()



def premium_holding_card_html(name, qty, avg_price, result=None):
    q = sf(qty)
    a = sf(avg_price)
    buy_amt = q * a

    if result:
        cur = sf(result.get("price"))
        value = sf(result.get("value", q * cur))
        profit = sf(result.get("profit", value - buy_amt))
        rate = sf(result.get("rate", (profit / buy_amt * 100) if buy_amt else 0))
        change_rate = result.get("change_rate")
        volume = result.get("volume")
        src = result.get("src", "")
    else:
        cur, value, profit, rate, change_rate, volume, src = 0, 0, 0, 0, None, None, ""

    profit_cls = "premium-profit-plus" if profit >= 0 else "premium-profit-minus"
    badge_cls = "profit" if profit > 0 else ("loss" if profit < 0 else "")
    badge = "수익" if profit > 0 else ("손실" if profit < 0 else "보유")
    current_txt = won(cur) if cur else "확인 제한"
    change_txt = f"{change_rate:.2f}%" if change_rate is not None else "-"
    volume_txt = f"{volume:,.0f}" if volume else "-"
    qty_txt = f"{q:g}주"

    return f"""
    <div class="premium-holding-card">
        <div class="premium-stock-head">
            <div>
                <div class="premium-stock-name">{name}</div>
                <div class="premium-stock-sub">수량 {qty_txt} · 평단 {won(a)} · 매입 {won(buy_amt)}</div>
            </div>
            <div class="premium-badge {badge_cls}">{badge}</div>
        </div>
        <div class="premium-metrics">
            <div class="premium-metric">
                <div class="premium-label">현재가</div>
                <div class="premium-value">{current_txt}</div>
            </div>
            <div class="premium-metric">
                <div class="premium-label">등락률</div>
                <div class="premium-value">{change_txt}</div>
            </div>
            <div class="premium-metric">
                <div class="premium-label">평가금액</div>
                <div class="premium-value">{won(value) if value else "-"}</div>
            </div>
            <div class="premium-metric">
                <div class="premium-label">수익금 / 수익률</div>
                <div class="premium-value {profit_cls}">{won(profit) if cur else "-"} · {rate:.2f}%</div>
            </div>
        </div>
        <div class="premium-note">거래량 {volume_txt} · {src if src else "현재 보유 기준 자동평가"}</div>
    </div>
    """


def holdings(data):
    header()
    card("내종목 자동평가", "현재가, 수익률, 종목점수, 행동 시그널을 함께 표시합니다.")
    render_trade_panel(data)
    st.subheader("📋 보유종목 현황")

    _, _, _, _, weights, rows = metrics(data)
    target = target_return(data)

    if not rows:
        card("보유종목 없음", "매수/매도 입력에서 종목을 추가하면 이곳에 표시됩니다.")
        return

    for i, (n, q, a, r) in enumerate(rows):
        # V91-1: 기존 흰글씨 문제를 만들던 hold/eval div를 제거하고 고급형 카드로 통합
        st.markdown(premium_holding_card_html(n, q, a, r), unsafe_allow_html=True)

        if r:
            grade, risk_reason = risk_grade_simple(n, r)
            st.markdown(f'<div class="scorebox"><b>위험등급 {grade}</b><br>{risk_reason}</div>', unsafe_allow_html=True)

            score, sig, reason = stock_signal(n, q, a, r, weights, target)
            st.markdown(f'<div class="scorebox"><b>종목점수 {score}점 · {sig}</b><br>{reason}</div>', unsafe_allow_html=True)

            supply = estimate_supply_score(n, r)
            supply_reason = "<br>".join([f"· {x}" for x in supply["reasons"][:3]])
            flow_text = investor_flow_summary(n)
            st.markdown(
                f'<div class="scorebox"><b>수급점수 {supply["score"]}점 · {supply["grade"]}</b><br>{flow_text}<br>{supply_reason}</div>',
                unsafe_allow_html=True
            )

        c1, c2 = st.columns(2)
        with c1:
            new_qty = st.number_input("수량 수정", min_value=0.0, value=float(q), step=1.0, key=f"q{i}")
        with c2:
            new_avg = st.number_input("평단 수정", min_value=0.0, value=float(a), step=100.0, key=f"a{i}")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("수정 저장", use_container_width=True, key=f"u{i}"):
                if new_qty <= 0:
                    data["holdings"].pop(i)
                else:
                    data["holdings"][i].update({"name": n, "qty": new_qty, "avg": new_avg})
                save_data(data)
                st.rerun()
        with b2:
            if st.button("삭제", use_container_width=True, key=f"d{i}"):
                data["holdings"].pop(i)
                save_data(data)
                st.rerun()


def rss_items():
    items = []
    sources = [
        ("연합뉴스 경제", "https://www.yna.co.kr/rss/economy.xml"),
        ("한국경제", "https://www.hankyung.com/feed/economy"),
    ]
    for source, url in sources:
        try:
            root = ET.fromstring(requests.get(url, timeout=3, headers={"User-Agent":"Mozilla/5.0"}).content)
            for item in root.findall(".//item")[:12]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                if title:
                    items.append((source, title, link))
        except Exception:
            pass
    return items[:30]

def news_score(title, keys):
    t = str(title).lower()
    return sum(1 for k in keys if str(k).lower() in t)


def impact_words():
    positive = [
        "수주", "공급", "계약", "흑자", "증가", "성장", "확대", "호조",
        "상승", "투자", "실적 개선", "최대", "강세", "기대", "협력", "승인"
    ]
    negative = [
        "하락", "감소", "적자", "손실", "부진", "우려", "리콜", "조사",
        "소송", "급락", "약세", "축소", "취소", "위험", "경고", "부채", "파업"
    ]
    return positive, negative

def news_impact(title):
    positive, negative = impact_words()
    t = str(title)
    p = sum(1 for w in positive if w in t)
    n = sum(1 for w in negative if w in t)
    if p > n:
        return "🟢 긍정", p - n
    if n > p:
        return "🔴 부정", n - p
    return "⚪ 중립", 0

def holding_news_keywords(stock_name):
    n = norm(stock_name)
    keys = [n]
    s = sector(n)
    if s == "반도체":
        keys += ["반도체", "AI", "HBM", "삼성전자", "SK하이닉스", "한미반도체"]
    elif s == "전력/자동화":
        keys += ["전력", "전력망", "변압기", "전기", "자동화", "로봇", "설비"]
    elif s == "미국지수":
        keys += ["미국", "S&P", "나스닥", "금리", "연준", "뉴욕증시"]
    elif s == "디스플레이":
        keys += ["디스플레이", "OLED", "패널", "LG디스플레이"]
    return list(dict.fromkeys([k for k in keys if k]))

def news_matches(title, keys):
    t = str(title).lower()
    return sum(1 for k in keys if str(k).lower() in t)

def render_related_news_by_holding(data):
    all_news = rss_items()
    holdings = data.get("holdings", [])
    any_shown = False

    for h in holdings:
        stock = norm(h.get("name", ""))
        keys = holding_news_keywords(stock)
        matched = []
        for source, title, link in all_news:
            score = news_matches(title, keys)
            if score > 0:
                impact, impact_score = news_impact(title)
                matched.append((score + impact_score, impact, source, title, link))

        matched = sorted(matched, key=lambda x: x[0], reverse=True)[:5]
        if matched:
            any_shown = True
            pos = sum(1 for x in matched if "긍정" in x[1])
            neg = sum(1 for x in matched if "부정" in x[1])
            neu = len(matched) - pos - neg
            if neg > pos:
                summary = "🔴 부정 뉴스 비중이 있어 확인이 필요합니다."
            elif pos > neg:
                summary = "🟢 긍정 뉴스가 상대적으로 우세합니다."
            else:
                summary = "⚪ 중립 뉴스 중심입니다."

            card(f"{stock} 관련뉴스", f"{summary}<br>긍정 {pos}건 · 부정 {neg}건 · 중립 {neu}건")

            for score, impact, source, title, link in matched:
                card(
                    title,
                    f"영향: {impact}<br>출처: {source}<br><a href='{link}' target='_blank'>원문 보기</a>"
                )

    return any_shown


def news(data):
    header()
    card("뉴스", "보유종목과 연결되는 뉴스를 먼저 확인하고, 긍정/부정/중립 흐름을 요약합니다.")

    all_news = rss_items()
    holdings = data.get("holdings", [])
    shown_any = False

    for h in holdings:
        stock = norm(h.get("name", ""))
        keys = holding_news_keywords(stock)
        matched = []
        for source, title, link in all_news:
            score = news_matches(title, keys)
            if score > 0:
                impact, impact_score = news_impact(title)
                matched.append((score + impact_score, impact, source, title, link))

        matched = sorted(matched, key=lambda x: x[0], reverse=True)[:4]
        if matched:
            shown_any = True
            pos = sum(1 for x in matched if "긍정" in x[1])
            neg = sum(1 for x in matched if "부정" in x[1])
            neu = len(matched) - pos - neg

            if neg > pos:
                status = "🔴 부정 우세"
                guide = "확인이 필요한 뉴스 흐름입니다."
            elif pos > neg:
                status = "🟢 긍정 우세"
                guide = "긍정 흐름이 상대적으로 우세합니다."
            else:
                status = "⚪ 중립"
                guide = "큰 방향성은 아직 뚜렷하지 않습니다."

            st.markdown(
                f'<div class="news-summary"><b>{stock}</b><br>{status} · 긍정 {pos}건 / 부정 {neg}건 / 중립 {neu}건<br>{guide}</div>',
                unsafe_allow_html=True
            )

            for score, impact, source, title, link in matched[:2]:
                card(title, f"영향: {impact}<br>출처: {source}<br><a href='{link}' target='_blank'>원문 보기</a>")

    if not shown_any:
        card("관련 뉴스 없음", "현재 RSS 안에서는 보유종목과 직접 연결되는 뉴스가 적습니다. 일반 경제뉴스를 표시합니다.")
        for source, title, link in all_news[:8]:
            impact, _ = news_impact(title)
            card(title, f"영향: {impact}<br>출처: {source}<br><a href='{link}' target='_blank'>원문 보기</a>")



def load_recommend_history():
    try:
        if RECOMMEND_FILE.exists():
            with open(RECOMMEND_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

def save_recommend_history(items):
    DATA_DIR.mkdir(exist_ok=True)
    with open(RECOMMEND_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def save_recommend_snapshot(data, memo=""):
    a = one_action(data)
    cache, _ = get_one_pick_cache(data, force=False)
    pick = cache.get("pick") if cache else None

    if pick:
        stock_name = pick.get("name")
        rec_price = pick.get("price")
        action_text = f"오늘의 1순위: {stock_name}"
        conf = pick.get("confidence", a.get("conf", 0))
        detail = " / ".join(pick.get("reason", [])[:4])
        badge = pick.get("period", "신규발굴")
        target_info = target_plan(stock_name, rec_price, None) if rec_price else None
    else:
        stock_name = "포트폴리오 전체"
        rec_price = None
        action_text = a.get("main", "")
        conf = a.get("conf", 0)
        detail = a.get("detail", "")
        badge = a.get("badge", "")
        target_info = None

    row = {
        "date": today_key(),
        "time": now_label(),
        "action": action_text,
        "badge": badge,
        "confidence": conf,
        "detail": detail,
        "stock": stock_name,
        "recommend_price": rec_price,
        "target_plan": target_info,
        "status": "추적중",
        "memo": memo,
    }

    items = load_recommend_history()
    items.append(row)
    save_recommend_history(items)
    return row


def recommend_history_table_html():
    items = load_recommend_history()
    if not items:
        return "아직 저장된 추천 히스토리가 없습니다."

    html = "<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
    html += "<tr><th style='text-align:left;border-bottom:1px solid #e5e7eb;padding:6px;'>일시</th><th style='text-align:left;border-bottom:1px solid #e5e7eb;padding:6px;'>종목/대상</th><th style='text-align:left;border-bottom:1px solid #e5e7eb;padding:6px;'>추천</th><th style='text-align:right;border-bottom:1px solid #e5e7eb;padding:6px;'>신뢰도</th><th style='text-align:center;border-bottom:1px solid #e5e7eb;padding:6px;'>상태</th></tr>"
    for r in reversed(items[-20:]):
        price = won(r.get("recommend_price")) if r.get("recommend_price") else "-"
        html += (
            f"<tr>"
            f"<td style='padding:6px;border-bottom:1px solid #f1f5f9;'>{r.get('date','')}<br>{r.get('time','')[11:19]}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #f1f5f9;'>{r.get('stock','')}<br>{price}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #f1f5f9;'>{r.get('action','')}<br>{r.get('badge','')}</td>"
            f"<td style='padding:6px;text-align:right;border-bottom:1px solid #f1f5f9;'>{r.get('confidence',0)}%</td>"
            f"<td style='padding:6px;text-align:center;border-bottom:1px solid #f1f5f9;'>{r.get('status','추적중')}</td>"
            f"</tr>"
        )
    html += "</table>"
    return html



def fetch_price_history(name, days=60):
    """
    V80-9 1차:
    네이버 일별시세에서 최근 종가를 가져와 라인차트용으로 사용.
    실패하면 현재가 기준의 단순 기준 데이터로 대체해 앱이 멈추지 않게 한다.
    """
    name = norm(name)
    code = code_map().get(name)
    rows = []

    if code:
        try:
            for page in range(1, 6):
                url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"
                res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
                try:
                    res.encoding = "euc-kr"
                except Exception:
                    pass
                html = res.text
                trs = re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", html)

                for tr in trs:
                    tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr)
                    vals = [strip_html(x) for x in tds]
                    vals = [v for v in vals if v]
                    if len(vals) >= 6 and re.match(r"\d{4}\.\d{2}\.\d{2}", vals[0]):
                        close = parse_price(vals[1])
                        vol = parse_price(vals[-1])
                        if close:
                            rows.append({
                                "date": vals[0][5:].replace(".", "/"),
                                "close": close,
                                "volume": vol or 0
                            })

                if len(rows) >= days:
                    break
        except Exception:
            rows = []

    rows = rows[:days]
    rows = list(reversed(rows))

    if not rows:
        price, _ = fetch_price(name)
        if price:
            # 대체 데이터: 실제 차트가 없을 때 현재가 중심의 기준선 표시용
            rows = [
                {"date": "기준-4", "close": price * 0.96, "volume": 0},
                {"date": "기준-3", "close": price * 0.98, "volume": 0},
                {"date": "기준-2", "close": price * 0.97, "volume": 0},
                {"date": "기준-1", "close": price * 0.99, "volume": 0},
                {"date": "현재", "close": price, "volume": 0},
            ]
    return rows

def moving_average(values, window):
    out = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(sum(values[i+1-window:i+1]) / window)
    return out

def render_price_chart(name, price=None, result=None):
    history = fetch_price_history(name, days=60)
    if not history:
        card("실제 주가 차트", "차트 데이터를 가져오지 못했습니다.")
        return

    closes = [float(x["close"]) for x in history]
    ma5 = moving_average(closes, 5)
    ma20 = moving_average(closes, 20)

    chart_data = []
    for i, row in enumerate(history):
        chart_data.append({
            "일자": row["date"],
            "종가": round(float(row["close"]), 2),
            "5일선": round(ma5[i], 2) if ma5[i] is not None else None,
            "20일선": round(ma20[i], 2) if ma20[i] is not None else None,
        })

    st.markdown("### 📈 실제 주가 차트")
    st.caption("최근 종가 기준 1차 차트입니다. 캔들/거래량/수급선은 이후 단계에서 강화합니다.")
    st.line_chart(chart_data, x="일자", y=["종가", "5일선", "20일선"], use_container_width=True)

    p = price
    if not p:
        try:
            p = closes[-1]
        except Exception:
            p = None

    plan = target_plan(name, p, result) if p else None
    if plan:
        card(
            "차트 기준선",
            f"현재가 {won(plan['entry'])}<br>"
            f"손절가 {won(plan['stop'])}<br>"
            f"1차 목표가 {won(plan['target1'])}<br>"
            f"2차 목표가 {won(plan['target2'])}<br>"
            f"최종 목표가 {won(plan['target3'])}<br><br>"
            f"※ V80-9에서는 실제 종가 차트와 목표가 기준선을 함께 확인하는 1차 구조입니다."
        )


def round_price_unit(price):
    try:
        p = float(price or 0)
        if p <= 0:
            return None
        if p < 10000:
            unit = 10
        elif p < 50000:
            unit = 50
        elif p < 100000:
            unit = 100
        elif p < 500000:
            unit = 500
        else:
            unit = 1000
        return int(round(p / unit) * unit)
    except Exception:
        return None


def calc_recent_change(history, days):
    try:
        if not history or len(history) < max(2, days):
            return None
        now = float(history[-1]["close"])
        past = float(history[-days]["close"])
        if past == 0:
            return None
        return (now / past - 1) * 100
    except Exception:
        return None

def lifecycle_engine(name, price=None, result=None):
    """
    V90-1 1차:
    '소문에 사고 뉴스에 팔아라'를 수치화하기 위한 초기 엔진.
    위치: 초기/성장/후기/과열
    진입: 적극매수/분할매수/관망/매수금지
    선반영 위험: 0~100
    상승확률: 0~100
    """
    n = norm(name)
    p = price
    if not p:
        try:
            p, _ = fetch_price(n)
        except Exception:
            p = None

    history = fetch_price_history(n, days=60)
    closes = [float(x["close"]) for x in history if x.get("close")]
    chg20 = calc_recent_change(history, 20)
    chg60 = calc_recent_change(history, min(60, len(history))) if len(history) >= 10 else None

    pos52 = None
    change_rate = None
    score = 50
    reasons = []

    if result:
        pos52 = result.get("pos52")
        change_rate = result.get("change_rate")
        try:
            score = int(result.get("my_score") or result.get("score") or 50)
        except Exception:
            score = 50

    if pos52 is None and closes:
        try:
            lo, hi = min(closes), max(closes)
            if hi > lo:
                pos52 = (closes[-1] - lo) / (hi - lo) * 100
        except Exception:
            pos52 = None

    # 선반영 위험 계산
    rumor_risk = 40
    if pos52 is not None:
        if pos52 >= 90:
            rumor_risk += 28
            reasons.append(f"가격 위치가 상단부({pos52:.0f}%)라 뉴스 선반영 가능성이 큽니다.")
        elif pos52 >= 75:
            rumor_risk += 16
            reasons.append(f"가격 위치가 높은 편({pos52:.0f}%)이라 추격매수 주의가 필요합니다.")
        elif pos52 <= 30:
            rumor_risk -= 14
            reasons.append(f"가격 위치가 낮은 편({pos52:.0f}%)이라 선반영 부담은 낮습니다.")

    if chg20 is not None:
        if chg20 >= 25:
            rumor_risk += 24
            reasons.append(f"최근 20거래일 상승률 {chg20:.1f}%로 단기 급등 부담이 있습니다.")
        elif chg20 >= 12:
            rumor_risk += 12
            reasons.append(f"최근 20거래일 {chg20:.1f}% 상승해 일부 기대감이 반영됐습니다.")
        elif chg20 <= -8:
            rumor_risk -= 8
            reasons.append(f"최근 20거래일 {chg20:.1f}%로 과열 부담은 낮습니다.")

    if change_rate is not None:
        if change_rate >= 7:
            rumor_risk += 12
            reasons.append(f"당일 등락률 {change_rate:.1f}%로 뉴스 추격 위험을 반영합니다.")
        elif change_rate <= -5:
            rumor_risk -= 3
            reasons.append(f"당일 하락으로 단기 과열은 일부 해소됐습니다.")

    rumor_risk = max(0, min(100, int(rumor_risk)))

    # 현재 위치 판단
    if rumor_risk >= 82 or (pos52 is not None and pos52 >= 92):
        stage = "🔴 과열"
        stage_desc = "뉴스에 팔아라 구간일 가능성"
    elif rumor_risk >= 65 or (pos52 is not None and pos52 >= 75):
        stage = "🟠 후기"
        stage_desc = "좋은 재료가 상당 부분 반영된 구간"
    elif rumor_risk >= 38:
        stage = "🟡 성장"
        stage_desc = "추세는 살아있지만 진입은 분할이 적합"
    else:
        stage = "🟢 초기"
        stage_desc = "아직 선반영 부담이 낮은 구간"

    # 상승확률: 종합점수에서 선반영 위험을 차감하고, 낮은 위치/수급 여지를 가산
    upside = score
    upside -= int(rumor_risk * 0.35)
    if pos52 is not None and pos52 <= 35:
        upside += 10
    if chg20 is not None and -5 <= chg20 <= 12:
        upside += 8
    if change_rate is not None and change_rate >= 10:
        upside -= 8
    upside = max(5, min(95, int(upside)))

    # 진입 타이밍
    if upside >= 75 and rumor_risk <= 35:
        entry = "🟢 적극매수"
        entry_desc = "초기 신호와 상승여력이 함께 보이는 구간"
    elif upside >= 62 and rumor_risk <= 60:
        entry = "🟡 분할매수"
        entry_desc = "괜찮지만 한 번에 들어가기보다 나눠서 접근"
    elif upside >= 45 and rumor_risk <= 78:
        entry = "🟠 관망"
        entry_desc = "종목은 괜찮아도 진입 타이밍 확인 필요"
    else:
        entry = "🔴 매수금지"
        entry_desc = "선반영/과열 부담이 커서 추격매수 위험"

    if not reasons:
        reasons.append("현재 데이터 기준으로 위치·진입타이밍을 보수적으로 판단했습니다.")

    return {
        "stage": stage,
        "stage_desc": stage_desc,
        "entry": entry,
        "entry_desc": entry_desc,
        "rumor_risk": rumor_risk,
        "upside_prob": upside,
        "chg20": chg20,
        "chg60": chg60,
        "pos52": pos52,
        "reasons": reasons[:4],
    }

def timing_engine_html(name, price=None, result=None):
    e = lifecycle_engine(name, price, result)
    reason_html = "<br>".join([f"① {x}" for x in e["reasons"]])
    pos_text = "-" if e.get("pos52") is None else f"{e['pos52']:.0f}%"
    chg20_text = "-" if e.get("chg20") is None else f"{e['chg20']:.1f}%"

    return (
        '<div class="timing-grid">'
        f'<div class="timing-box"><div class="timing-label">현재 위치</div><div class="timing-value">{e["stage"]}</div><div class="timing-reason">{e["stage_desc"]}</div></div>'
        f'<div class="timing-box"><div class="timing-label">진입 타이밍</div><div class="timing-value">{e["entry"]}</div><div class="timing-reason">{e["entry_desc"]}</div></div>'
        f'<div class="timing-box"><div class="timing-label">선반영 위험</div><div class="timing-value">{e["rumor_risk"]}%</div><div class="timing-reason">높을수록 뒷북·추격매수 위험</div></div>'
        f'<div class="timing-box"><div class="timing-label">상승확률</div><div class="timing-value">{e["upside_prob"]}%</div><div class="timing-reason">현재 데이터 기준 가능성 추정</div></div>'
        '</div>'
        f'<div class="target-note"><b>판단 근거</b><br>{reason_html}<br>'
        f'52주/최근 위치: {pos_text} · 최근 20일 등락: {chg20_text}<br>'
        '※ V90-1은 1차 확률 엔진입니다. 실제 성과가 쌓이면 가중치를 조정합니다.</div>'
    )


def target_plan(name, price, result=None):
    """
    V80-8 목표가/손절가 1차 엔진.
    실제 고점/이평선 기반은 다음 단계에서 강화하고,
    지금은 종목 성격·투자기간·수급/가격위치에 따른 기본 전략을 만든다.
    """
    sec = sector(name)
    p = float(price or 0)
    if p <= 0:
        return None

    period = "-"
    confidence = 60
    pos52 = None
    reasons = []

    if result:
        period = result.get("period_text", "-")
        d = result.get("decision", {}) or {}
        confidence = d.get("confidence") or 60
        pos52 = result.get("pos52")

    # 기본 수익/손절 폭: 섹터와 투자기간별 차등
    if "단기" in period:
        t1, t2, t3, stop = 0.06, 0.12, 0.20, -0.06
        reasons.append("단기 적합 종목은 목표와 손절 폭을 짧게 잡습니다.")
    elif "장기" in period:
        t1, t2, t3, stop = 0.10, 0.22, 0.35, -0.10
        reasons.append("장기 적합 종목은 단기 등락보다 넓은 목표 구간을 둡니다.")
    else:
        t1, t2, t3, stop = 0.08, 0.16, 0.28, -0.08
        reasons.append("중기 적합 종목은 1차·2차 분할매도 기준이 적절합니다.")

    if sec in ["바이오", "2차전지", "로봇"]:
        stop -= 0.02
        t2 += 0.03
        t3 += 0.05
        reasons.append(f"{sec} 섹터는 변동성이 커서 손절 폭과 목표 폭을 함께 넓게 봅니다.")
    elif sec in ["미국지수", "금융/배당"]:
        stop += 0.02
        t2 -= 0.03
        t3 -= 0.05
        reasons.append(f"{sec} 성격은 급등 목표보다 안정적 누적 수익을 우선합니다.")
    elif sec in ["전력/에너지", "전력/자동화", "방산/조선", "반도체"]:
        t2 += 0.02
        t3 += 0.03
        reasons.append(f"{sec}는 성장 테마 모멘텀을 반영해 2차 목표를 조금 높게 둡니다.")

    if pos52 is not None:
        if pos52 >= 85:
            t1 -= 0.02
            t2 -= 0.03
            t3 -= 0.05
            reasons.append(f"52주 위치 {pos52:.0f}%로 상단부에 가까워 목표가를 보수적으로 조정합니다.")
        elif pos52 <= 25:
            t1 += 0.01
            t2 += 0.02
            t3 += 0.03
            reasons.append(f"52주 위치 {pos52:.0f}%로 가격 부담이 낮아 목표 여지를 조금 넓게 봅니다.")

    stop_price = round_price_unit(p * (1 + stop))
    t1_price = round_price_unit(p * (1 + t1))
    t2_price = round_price_unit(p * (1 + t2))
    t3_price = round_price_unit(p * (1 + t3))

    # 목표가별 신뢰도는 멀어질수록 낮아짐
    stop_conf = min(92, int(confidence + 8))
    t1_conf = min(90, int(confidence))
    t2_conf = max(45, int(confidence - 12))
    t3_conf = max(30, int(confidence - 28))

    return {
        "entry": round_price_unit(p),
        "stop": stop_price,
        "target1": t1_price,
        "target2": t2_price,
        "target3": t3_price,
        "stop_conf": stop_conf,
        "target1_conf": t1_conf,
        "target2_conf": t2_conf,
        "target3_conf": t3_conf,
        "reasons": reasons[:4],
    }

def target_plan_html(name, price, result=None):
    plan = target_plan(name, price, result)
    if not plan:
        return "현재가 확인이 제한되어 목표가를 계산하지 못했습니다."

    reason_html = "<br>".join([f"① {x}" for x in plan["reasons"]])
    return (
        '<table class="target-table">'
        '<tr><th>구분</th><th>가격</th><th>신뢰도</th><th>의미</th></tr>'
        f'<tr><td>매수가</td><td>{won(plan["entry"])}</td><td>-</td><td>현재 기준 진입가</td></tr>'
        f'<tr><td class="target-stop">손절가</td><td class="target-stop">{won(plan["stop"])}</td><td>{plan["stop_conf"]}%</td><td>위험관리 기준</td></tr>'
        f'<tr><td>1차 목표가</td><td class="target-buy">{won(plan["target1"])}</td><td>{plan["target1_conf"]}%</td><td>일부 매도 검토</td></tr>'
        f'<tr><td>2차 목표가</td><td class="target-buy">{won(plan["target2"])}</td><td>{plan["target2_conf"]}%</td><td>추세 지속 시</td></tr>'
        f'<tr><td>최종 목표가</td><td class="target-buy">{won(plan["target3"])}</td><td>{plan["target3_conf"]}%</td><td>강한 모멘텀 지속 시</td></tr>'
        '</table>'
        f'<div class="target-note"><b>목표가 근거</b><br>{reason_html}<br>'
        '※ V80-8 목표가는 1차 전략 기준입니다. 실제 차트 저항선·이평선·수급 변화가 붙으면 자동 조정됩니다.</div>'
    )



def cache_ttl_minutes():
    return 45

def parse_dt_safe(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def load_recommend_cache():
    try:
        if RECOMMEND_CACHE_FILE.exists():
            with open(RECOMMEND_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}

def save_recommend_cache(cache):
    DATA_DIR.mkdir(exist_ok=True)
    with open(RECOMMEND_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def cache_is_valid(cache):
    if not cache:
        return False
    if cache.get("date") != today_key():
        return False
    ts = parse_dt_safe(cache.get("created_at", ""))
    if not ts:
        return False
    age_min = (datetime.now() - ts).total_seconds() / 60
    return age_min <= cache_ttl_minutes()

def build_one_pick_cache(data):
    tops = discovery_candidates(data)
    pick = tops[0] if tops else None
    alt = tops[1:4] if len(tops) > 1 else []
    cache = {
        "date": today_key(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "ttl_minutes": cache_ttl_minutes(),
        "pick": pick,
        "alternatives": alt,
    }
    save_recommend_cache(cache)
    return cache

def get_one_pick_cache(data, force=False):
    if not force:
        cache = load_recommend_cache()
        if cache_is_valid(cache):
            return cache, False
    return build_one_pick_cache(data), True

def cache_status_text(cache):
    if not cache:
        return "추천 캐시 없음"
    ts = parse_dt_safe(cache.get("created_at", ""))
    if not ts:
        return "마지막 계산 시각 확인 불가"
    age_min = int((datetime.now() - ts).total_seconds() / 60)
    ttl = cache.get("ttl_minutes", cache_ttl_minutes())
    remain = max(0, int(ttl - age_min))
    return f"마지막 계산 {age_min}분 전 · 자동 재계산까지 약 {remain}분"


def priority_candidate_pool():
    # V80-7.1: 전체 DB 스캔 금지. 유망 섹터 대표 후보만 분석.
    return [
        "대한전선", "LS ELECTRIC", "HD현대일렉트릭", "효성중공업", "두산에너빌리티",
        "삼성전자", "SK하이닉스", "한미반도체", "리노공업", "이수페타시스",
        "한화에어로스페이스", "LIG넥스원", "현대로템", "한국항공우주",
        "레인보우로보틱스", "두산로보틱스", "에스피시스템스",
        "TIGER 미국S&P500", "KODEX 미국S&P500", "TIGER 미국나스닥100",
        "에코프로비엠", "포스코퓨처엠", "LG에너지솔루션",
    ]

def price_access_score(price):
    try:
        p = float(price or 0)
        if p <= 0:
            return -5, "현재가 확인 제한"
        if p <= 50000:
            return 10, "가격 부담 낮음"
        if p <= 100000:
            return 5, "가격 부담 보통"
        if p <= 200000:
            return 0, "가격 부담 다소 있음"
        return -10, "1주 가격이 높아 분할 접근 필요"
    except Exception:
        return -5, "가격 판단 제한"

def duplicate_penalty(sec, weights):
    current = weights.get(sec, 0)
    if current >= 50:
        return -12, f"{sec} 비중이 {current:.1f}%로 높아 중복 감점"
    if current >= 35:
        return -6, f"{sec} 비중이 {current:.1f}%로 다소 높음"
    if current <= 5:
        return 6, f"{sec} 비중이 낮아 분산 보강 효과"
    return 0, f"{sec} 비중은 무난"

def discovery_candidates(data):
    holding_names = {norm(h.get("name","")) for h in data.get("holdings", [])}
    _, _, _, _, weights, rows = metrics(data)
    candidates = []

    for name in priority_candidate_pool():
        n = norm(name)
        if not n or n in holding_names:
            continue

        try:
            result = analyze_stock_for_search(n, data)
            d = result.get("decision", {})
            price = result.get("price")
            sec = result.get("sector", "-")

            base = result.get("my_score", 0)
            price_adj, price_reason = price_access_score(price)
            dup_adj, dup_reason = duplicate_penalty(sec, weights)

            theme_bonus = 0
            if sec in ["전력/에너지", "전력/자동화", "방산/조선", "반도체", "미국지수", "로봇"]:
                theme_bonus = 6
            elif sec in ["2차전지", "바이오"]:
                theme_bonus = 2

            confidence = d.get("confidence") or 60
            timing = lifecycle_engine(n, price, result)
            timing_bonus = int(timing["upside_prob"] * 0.15) - int(timing["rumor_risk"] * 0.08)
            final_score = int(base + price_adj + dup_adj + theme_bonus + confidence * 0.08 + timing_bonus)
            final_score = max(0, min(100, final_score))

            reasons = []
            reasons.append((result.get("my_reasons") or result.get("reasons") or ["분석 근거 확인 필요"])[0])
            reasons.append(price_reason)
            reasons.append(dup_reason)
            reasons.append(f"위치 {timing['stage']} · 진입 {timing['entry']} · 상승확률 {timing['upside_prob']}%")

            candidates.append({
                "name": n,
                "score": final_score,
                "grade": result.get("my_grade", "-"),
                "period": result.get("period_text", "-"),
                "confidence": confidence,
                "sector": sec,
                "price": price,
                "reason": reasons,
                "why": f"성장섹터 + 가격접근성 + 포트중복도 기준으로 최종 {final_score}점",
            })
        except Exception:
            continue

    return sorted(candidates, key=lambda x: x["score"], reverse=True)


def render_discovery_top3(data):
    card(
        "🔥 오늘의 1순위",
        "추천 결과를 캐시에 저장해 추천탭 로딩을 빠르게 합니다. 뉴스·수급 변화가 의심되면 직접 다시 계산하세요."
    )

    force = False
    col1, col2 = st.columns(2)
    with col1:
        st.button("⚡ 저장된 추천 보기", use_container_width=True)
    with col2:
        if st.button("🔄 지금 다시 계산", use_container_width=True):
            force = True

    cache, refreshed = get_one_pick_cache(data, force=force)
    st.caption(cache_status_text(cache))

    x = cache.get("pick")
    if not x:
        card("오늘의 1순위 없음", "현재 후보군 기준으로 표시할 신규 후보가 없습니다.")
        return

    reason_html = "<br>".join([f"① {r}" for r in x.get("reason", [])[:4]])

    st.markdown(
        f'<div class="top-card">'
        f'<span class="top-rank">오늘의 1순위</span>'
        f'<div class="top-name">{x["name"]}</div>'
        f'<div class="top-meta">'
        f'종합점수 {x["score"]}점 · {x["grade"]}등급 · {x["period"]} · 신뢰도 {x["confidence"]}%<br>'
        f'섹터 {x["sector"]} · 현재가 {won(x["price"]) if x["price"] else "확인 제한"}<br><br>'
        f'<b>추천이유</b><br>{reason_html}<br><br>'
        f'<b>왜 이 종목인가?</b><br>{x["why"]}'
        f'</div></div>',
        unsafe_allow_html=True
    )

    try:
        result_for_timing = analyze_stock_for_search(x["name"], data)
    except Exception:
        result_for_timing = None
    html_card("위치 / 진입타이밍 / 선반영", timing_engine_html(x["name"], x["price"], result_for_timing))

    if st.button("📈 차트·목표가 자세히 보기", use_container_width=True):
        result_for_target = result_for_timing
        html_card("목표가 / 손절가 근거", target_plan_html(x["name"], x["price"], result_for_target))
        render_price_chart(x["name"], x["price"], result_for_target)

    alt = cache.get("alternatives", [])
    if alt:
        alt_txt = " · ".join([f"{y['name']} {y['score']}점" for y in alt[:3]])
        card("비교 후보", f"다음 후보: {alt_txt}<br>단, 오늘은 선택과 집중 기준으로 1개만 표시합니다.")


def rec(data):
    header()
    card("추천 분석", "홈에서 보여준 결론이 왜 나왔는지 점수와 근거를 확인하고, 새 종목도 검색합니다.")

    # V80-7: 종목검색은 홈이 아니라 추천 탭 최상단에 배치
    render_stock_search(data)

    render_discovery_top3(data)

    if st.button("💾 오늘 추천 히스토리 저장", use_container_width=True):
        save_recommend_snapshot(data)
        st.success("오늘 추천 내용을 히스토리에 저장했습니다.")
        st.rerun()

    if st.button("🔄 추천 다시 판단하기", use_container_width=True):
        st.rerun()

    render_reason_process(data)


def profile(data):
    header()
    st.subheader("📈 투자기록")
    s = asset_summary(data)
    cls = "profit" if s["profit"] >= 0 else "loss"

    st.markdown(
        f'<div class="card">'
        f'<div class="title">투자 요약</div>'
        f'<div class="body">'
        f'총 매입원금 {won(s["buy_principal"])}<br>'
        f'현재 평가금액 {won(s["stock_value"])}<br>'
        f'평가수익금 <span class="{cls}">{won(s["profit"])}</span> · 평가수익률 <span class="{cls}">{s["rate"]:.2f}%</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    st.markdown("### 평가수익 히스토리")
    render_history_tables()

    st.markdown("### 실현손익 히스토리")
    render_sell_history()

    st.markdown("### 추천 히스토리")
    st.markdown(
        '<div class="card"><div class="title">추천 히스토리 DB</div>'
        '<div class="body">오늘부터 추천 내용을 저장하고, 이후 수익률과 성공 여부를 추적합니다.</div></div>',
        unsafe_allow_html=True
    )
    st.markdown(recommend_history_table_html(), unsafe_allow_html=True)

    st.caption("평가수익은 현재 보유종목 기준이고, 실현손익은 매도기록 기준입니다.")

def main():
    css()
    data = load_data()
    tab = current_tab()
    if tab == "news":
        news(data)
    elif tab == "rec":
        rec(data)
    elif tab == "holdings":
        holdings(data)
    elif tab == "profile":
        profile(data)
    else:
        home(data)
    nav(tab)
    st.markdown('<div class="notice">※ 투자 판단 보조 도구입니다. 모든 투자 책임은 투자자 본인에게 있습니다.</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
