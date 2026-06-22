
import json, re, hashlib, os, io, zipfile
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st

# V112-3: 시작부에는 실행문이 아닌 import/변수 선언/주석만 둡니다.
# 한국어 설명은 반드시 # 주석 또는 문자열 내부에만 작성합니다.
import requests
import xml.etree.ElementTree as ET

APP_TITLE = "🧭 스톡 컴퍼스 V124-13 COMBO VALIDATION LAB"
APP_SUBTITLE = "경규님 전용 개인용 AI 투자비서 · 5,000건 표본 성공/실패 패턴 해부"

# V112-2-1 HOTFIX
# CLOUD_DB_ROOT는 DATA_DIR보다 반드시 먼저 선언되어야 합니다.
# 값이 없으면 기존처럼 앱 폴더의 data/portfolio.json을 사용합니다.
CLOUD_DB_ROOT = os.environ.get("STOCK_COMPASS_CLOUD_DB_PATH", "").strip()
DEVICE_ROLE_SETTING = os.environ.get("STOCK_COMPASS_DEVICE_ROLE", "auto").strip().lower()

DATA_DIR = Path(CLOUD_DB_ROOT) if CLOUD_DB_ROOT else Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_SCHEMA_VERSION = "V121-4"
DB_MODE = "SMART_MONEY_LIVE_V1"
DB_ROLE = "PC Master / GitHub JSON 배포 / 모바일 조회"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
HISTORY_FILE = DATA_DIR / "history.json"
SELL_FILE = DATA_DIR / "sell_records.json"
DB_FILES = {
    "portfolio": PORTFOLIO_FILE,
    "history": HISTORY_FILE,
    "sell_records": SELL_FILE,
}

def db_path(name):
    return DB_FILES.get(name, DATA_DIR / f"{name}.json")

def backup_file(path):
    try:
        path = Path(path)
        if not path.exists():
            return None
        bdir = DATA_DIR / "backup"
        bdir.mkdir(exist_ok=True)
        stamp = kst_now().strftime("%Y%m%d_%H%M%S") if "kst_now" in globals() else datetime.now().strftime("%Y%m%d_%H%M%S")
        bpath = bdir / f"{path.stem}_{stamp}{path.suffix}"
        bpath.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        return bpath
    except Exception:
        return None

def read_db_json(name, default=None):
    p = db_path(name)
    try:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def write_db_json(name, data, backup=True):
    # V112-3A: 검증 전용 단계. MASTER 환경에서만 DB를 저장하고 VIEWER에서는 쓰기를 막습니다.
    if not can_write_db():
        return None
    DATA_DIR.mkdir(exist_ok=True)
    p = db_path(name)
    if backup:
        backup_file(p)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


def device_role():
    """V112-2: PC는 수정권한, Cloud/모바일은 조회전용으로 구분합니다.
    환경변수 STOCK_COMPASS_DEVICE_ROLE=master/viewer 로 강제 지정 가능.
    """
    if DEVICE_ROLE_SETTING in ["master", "pc", "write"]:
        return "MASTER"
    if DEVICE_ROLE_SETTING in ["viewer", "mobile", "read"]:
        return "VIEWER"
    return "MASTER" if app_env_label() == "PC/Local" else "VIEWER"

def can_write_db():
    return device_role() == "MASTER"

def db_role_label():
    if can_write_db():
        return "🖥️ PC 모체 · 수정 가능"
    return "📱 모바일/Cloud 조회전용 · 수정 잠금"

def read_only_notice():
    st.markdown(
        '<div class="db-card"><div class="db-title">🔒 조회전용 모드</div>'
        '<div class="db-sub">현재 환경은 모바일/Cloud 조회전용으로 판단되어 매수·매도·수량·평단 수정 기능을 잠갔습니다.</div>'
        '<div class="db-action">수정은 PC 모체에서만 진행하세요. 휴대폰은 판단 결과 확인용으로 사용합니다.</div></div>',
        unsafe_allow_html=True
    )

DEFAULT_DATA = {
    "profile": {
        "name": "경규님",
        "style": "균형형 성장투자자",
        "method": "장기 적립식",
        "principal": 5000000,
        "target_return": 15
    },
    "holdings": [
        {"name": "에스피시스템스", "qty": 60, "avg": 7520},
        {"name": "제룡전기", "qty": 14, "avg": 52463},
        {"name": "ACE AI반도체 TOP3", "qty": 23, "avg": 58561},
        {"name": "KODEX 미국S&P500", "qty": 42, "avg": 25513},
        {"name": "LG디스플레이", "qty": 20, "avg": 15113},
    ]
}

st.set_page_config(page_title="스톡 컴퍼스 V121-4", page_icon="🧭", layout="centered")

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

def volume_text(v):
    try:
        v = int(float(v or 0))
        if v <= 0:
            return "확인불가"
        if v >= 100000000:
            return f"{v/100000000:.1f}억주"
        if v >= 10000:
            return f"{v/10000:.1f}만주"
        return f"{v:,}주"
    except Exception:
        return "확인불가"

def kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def app_env_label():
    try:
        cwd = str(Path.cwd().resolve()).replace("\\", "/")
        # Streamlit Cloud 배포 경로는 /mount/src 입니다.
        # 로컬 PC에서 streamlit을 실행해도 STREAMLIT_SERVER_PORT가 생길 수 있어 그 값만으로는 Cloud로 보지 않습니다.
        if "/mount/src" in cwd:
            return "Streamlit Cloud/휴대폰"
        return "PC/Local"
    except Exception:
        return "확인불가"

def save_data(data):
    # V112-1: 모든 포트폴리오 저장은 이 함수 하나로만 통과시킵니다.
    # 다음 V112-2 Cloud DB 전환 시 이 함수 내부만 바꾸면 PC/모바일 동기화 구조로 확장 가능합니다.
    DATA_DIR.mkdir(exist_ok=True)
    try:
        data.setdefault("_meta", {})
        data["_meta"].update({
            "last_saved_kst": kst_now().strftime("%Y-%m-%d %H:%M:%S"),
            "saved_env": app_env_label(),
            "db_schema": DB_SCHEMA_VERSION,
            "db_mode": DB_MODE,
            "db_role": DB_ROLE,
            "device_role": device_role(),
            "write_allowed": can_write_db(),
            "cloud_db_root": CLOUD_DB_ROOT or "local data",
            "storage_file": str(PORTFOLIO_FILE),
        })
    except Exception:
        pass
    write_db_json("portfolio", data, backup=True)

def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        if "holdings" in d:
            d.setdefault("_meta", {})
            d["_meta"].setdefault("db_schema", DB_SCHEMA_VERSION)
            d["_meta"].setdefault("db_mode", DB_MODE)
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
        "제룡전기": "033100",
        "에스피시스템스": "317830",
        "LG디스플레이": "034220",
        "ACE AI반도체 TOP3": "469150",
        "KODEX 미국S&P500": "379800",
        "TIGER 미국S&P500": "360750",
        "삼성전자": "005930",
        "SK하이닉스": "000660",
        "한미반도체": "042700",
        "대한전선": "001440",
        "하나마이크론": "067310",
        "ISC": "095340",
        "이수페타시스": "007660",
        "LS ELECTRIC": "010120",
        "효성중공업": "298040",
        "레인보우로보틱스": "277810",
        "두산로보틱스": "454910",
        "비에이치아이": "083650",
        "우진": "105840",
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
        "하나마이크론": 12000,
        "ISC": 70000,
        "이수페타시스": 45000,
        "LS ELECTRIC": 180000,
        "효성중공업": 420000,
        "레인보우로보틱스": 160000,
        "두산로보틱스": 65000,
        "비에이치아이": 18000,
        "우진": 8000,
    }.get(norm(name))

def parse_price(s):
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_detail(name):
    """
    V108-5: 실제 현재가 + 당일 등락률을 함께 가져옵니다.
    실패해도 기존 fallback 현재가는 유지합니다.
    """
    name = norm(name)
    code = code_map().get(name)
    fallback = fallback_price(name)
    if not code:
        return {"price": fallback, "src": "기본값", "change_rate": None, "change_text": "등락률 확인불가", "volume": None, "volume_text": "확인불가"}
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4).text
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

        change_rate = None
        change_text = "등락률 확인불가"
        m = re.search(r'<p class="no_exday">([\s\S]*?)</p>', html)
        if m:
            block = m.group(1)
            blinds = [x.strip() for x in re.findall(r'<span class="blind">([^<]+)</span>', block) if x.strip()]
            sign = 1
            if any("하락" in x or "마이너스" in x for x in blinds):
                sign = -1
            elif any("상승" in x or "플러스" in x for x in blinds):
                sign = 1
            nums = []
            for x in blinds:
                y = str(x).replace(",", "").replace("%", "").strip()
                try:
                    nums.append(float(y))
                except Exception:
                    pass
            if nums:
                # 보통 마지막 숫자가 등락률(%)입니다.
                change_rate = sign * float(nums[-1])
                change_text = f"{change_rate:+.2f}%"

        return {"price": price or fallback, "src": f"네이버 {code}", "change_rate": change_rate, "change_text": change_text}
    except Exception:
        return {"price": fallback, "src": "기본값", "change_rate": None, "change_text": "등락률 확인불가", "volume": None, "volume_text": "확인불가"}

def fetch_price(name):
    d = fetch_price_detail(name)
    return d.get("price"), d.get("src", "기본값")

def sector(name):
    n = norm(name)
    if "반도체" in n or n in ["삼성전자", "SK하이닉스", "한미반도체", "엔비디아"]:
        return "반도체"
    if n in ["제룡전기", "에스피시스템스"] or "전기" in n:
        return "전력/자동화"
    if "S&P500" in n or "나스닥" in n:
        return "미국지수"
    if "디스플레이" in n:
        return "디스플레이"
    return "기타"

def evaluate(name, qty, avg):
    detail = fetch_price_detail(name)
    price = detail.get("price")
    src = detail.get("src", "기본값")
    qty = sf(qty)
    avg = sf(avg)
    if not price or qty <= 0 or avg <= 0:
        return None
    buy = qty * avg
    value = qty * price
    profit = value - buy
    rate = profit / buy * 100 if buy else 0
    return {
        "price": price,
        "src": src,
        "buy": buy,
        "value": value,
        "profit": profit,
        "rate": rate,
        "change_rate": detail.get("change_rate"),
        "change_text": detail.get("change_text", "등락률 확인불가"),
        "volume": detail.get("volume"),
        "volume_text": detail.get("volume_text", "확인불가"),
        "fetched_at": detail.get("fetched_at", now_label()),
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
    total_buy, total_value, profit, rate, weights, rows = metrics(data)

    score = 100
    reasons = []

    semi = weights.get("반도체", 0)
    us = weights.get("미국지수", 0)
    display = weights.get("디스플레이", 0)

    # 1. 반도체 비중 위험
    if semi >= 60:
        score -= 25
        reasons.append(f"반도체 비중이 {semi:.1f}%로 매우 높습니다.")
    elif semi >= 45:
        score -= 15
        reasons.append(f"반도체 비중이 {semi:.1f}%로 다소 높습니다.")

    # 2. 미국지수 방어 비중 부족
    if us < 15:
        score -= 20
        reasons.append(f"미국지수 비중이 {us:.1f}%로 낮아 방어력이 부족합니다.")
    elif us < 30:
        score -= 10
        reasons.append(f"미국지수 비중이 {us:.1f}%로 조금 더 보강이 필요합니다.")

    # 3. 디스플레이 비중 위험
    if display >= 20:
        score -= 10
        reasons.append(f"디스플레이 비중이 {display:.1f}%로 변동성 관리가 필요합니다.")

    # 4. 손실 종목 개수 위험
    loss_count = 0
    danger_items = []
    for n, q, a, r in rows:
        if r and r["rate"] <= -5:
            loss_count += 1
            danger_items.append(f"{n} {r['rate']:.2f}%")

    if loss_count >= 3:
        score -= 20
        reasons.append(f"손실 종목이 {loss_count}개입니다: {', '.join(danger_items)}")
    elif loss_count >= 1:
        score -= 10
        reasons.append(f"손실 관리가 필요한 종목이 있습니다: {', '.join(danger_items)}")

    # 5. 전체 수익률 반영
    if rate >= 8:
        score += 5
        reasons.append(f"전체 수익률이 {rate:.2f}%로 양호합니다.")
    elif rate <= -5:
        score -= 10
        reasons.append(f"전체 수익률이 {rate:.2f}%로 방어가 필요합니다.")

    score = max(0, min(100, int(score)))

    if score >= 85:
        grade = "🟢 안전"
        action = "현재 포트폴리오는 안정적입니다. 적립식 매수를 유지해도 좋습니다."
    elif score >= 70:
        grade = "🟡 보통"
        action = "무리한 개별주 추가매수보다 S&P500 같은 지수형 ETF 보강이 좋습니다."
    elif score >= 55:
        grade = "🟠 주의"
        action = "신규 매수보다 비중 조정과 손실 종목 점검이 우선입니다."
    else:
        grade = "🔴 위험"
        action = "추가매수는 멈추고, 손실 확대 종목과 특정 섹터 집중도를 먼저 줄여야 합니다."

    summary = f"반도체 {semi:.1f}% · 미국지수 {us:.1f}% · 디스플레이 {display:.1f}% · 평가수익률 {rate:.2f}%"

    return score, grade, summary, reasons, action

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
    return kst_now().strftime("%Y-%m-%d %H:%M:%S")

def today_key():
    return kst_now().strftime("%Y-%m-%d")

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
    # V112-1: 히스토리 저장도 공통 DB writer를 사용합니다.
    write_db_json("history", items, backup=True)

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
    # V112-1: 매도기록 저장도 공통 DB writer를 사용합니다.
    write_db_json("sell_records", items, backup=True)

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
    .thermo-title{font-weight:950;font-size:19px;color:#0f172a;margin-bottom:10px}
    .thermo-box{position:relative;height:320px;border-radius:18px;background:linear-gradient(180deg,#dcfce7 0%,#f8fafc 48%,#f8fafc 52%,#fee2e2 100%);border:1px solid #e2e8f0;margin:10px 0;overflow:hidden}
    .thermo-center{position:absolute;left:0;right:0;top:50%;height:2px;background:#64748b}
    .thermo-line{position:absolute;left:50%;top:16px;bottom:16px;width:4px;background:#cbd5e1;border-radius:999px;transform:translateX(-50%)}
    .thermo-marker{position:absolute;left:50%;transform:translate(-50%,-50%);width:72px;height:34px;border-radius:999px;background:#07111f;color:white;font-weight:950;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 18px rgba(15,23,42,.25)}
    .thermo-label{position:absolute;right:14px;font-size:12px;font-weight:950;color:#334155}
    .thermo-label.top{top:12px;color:#166534}
    .thermo-label.mid{top:50%;transform:translateY(-50%);color:#475569}
    .thermo-label.bot{bottom:12px;color:#991b1b}
    .thermo-note{font-size:13px;color:#475569;font-weight:850;line-height:1.6}


    /* V94-2.1 매수타이밍 긴급복구 CSS */
    .buytiming-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.20)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .buytiming-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .buytiming-top{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #e2e8f0;padding-bottom:12px;margin-bottom:12px}
    .buytiming-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .buytiming-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:4px}
    .buytiming-score{text-align:right;min-width:76px}.buytiming-score .num{font-size:31px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1}.buytiming-score .txt{font-size:12px;font-weight:900;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:4px}
    .buytiming-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.45;margin:10px 0}
    .buytiming-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.buytiming-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px}.buytiming-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}.buytiming-value{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .buytiming-bar{width:100%;height:12px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin:8px 0 4px}.buytiming-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#ef4444 0%,#f59e0b 45%,#22c55e 100%)}
    .buytiming-reason{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}
    .buytiming-list{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}.buytiming-list-head{display:flex;justify-content:space-between;gap:8px}.buytiming-list-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}.buytiming-list-score{font-size:18px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}.buytiming-list-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:5px;line-height:1.45}


    /* V95-1 저평가·배당·성장성 카드 */
    .value-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .value-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .value-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .value-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .value-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
    .value-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px}
    .value-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}
    .value-num{font-size:18px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .value-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.45;margin:10px 0}
    .value-reason{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}
    .value-row{display:flex;justify-content:space-between;gap:8px;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .value-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .value-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:4px;line-height:1.45}
    .value-score{font-size:18px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}


    /* V96-1 리밸런싱 엔진 */
    .rebalance-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .rebalance-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .rebalance-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .rebalance-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .rebalance-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .rebalance-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
    .rebalance-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px}
    .rebalance-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}
    .rebalance-value{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1.35}
    .rebalance-reason{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}
    .rebalance-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .rebalance-row-head{display:flex;justify-content:space-between;gap:8px}
    .rebalance-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .rebalance-score{font-size:16px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}
    .rebalance-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:5px;line-height:1.45}


    /* V97-1 목표가·손절가·매수구간 엔진 */
    .target-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .target-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .target-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .target-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .target-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .target-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
    .target-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px}
    .target-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}
    .target-value{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1.35}
    .target-reason{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}
    .target-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .target-row-head{display:flex;justify-content:space-between;gap:8px}
    .target-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .target-score{font-size:16px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}
    .target-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:5px;line-height:1.45}


    /* V98-1 미래확률 엔진 */
    .future-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .future-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .future-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .future-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .future-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .future-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:10px 0}
    .future-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px;text-align:center}
    .future-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}
    .future-value{font-size:20px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1.35}
    .future-reason{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}
    .future-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .future-row-head{display:flex;justify-content:space-between;gap:8px}
    .future-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .future-score{font-size:16px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}
    .future-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:5px;line-height:1.45}


    /* V99-1 종목 브리핑 엔진 */
    .brief-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .brief-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .brief-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .brief-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .brief-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.55;margin:10px 0}
    .brief-action *{color:#fff!important;-webkit-text-fill-color:#fff!important}
    .brief-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
    .brief-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px}
    .brief-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}
    .brief-value{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1.35}
    .brief-reason{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}
    .brief-search{background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:14px;margin:12px 0}
    div[data-testid="stExpander"]{background:#ffffff!important;border:1px solid #e2e8f0!important;border-radius:18px!important;margin:10px 0!important;overflow:hidden!important}
    div[data-testid="stExpander"] *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}


    /* V100-1 AI 소장 의견 */
    .boss-card{background:linear-gradient(180deg,#07111f 0%,#111827 100%)!important;border:1px solid rgba(255,255,255,.18)!important;border-radius:26px!important;padding:20px!important;margin:16px 0!important;box-shadow:0 22px 55px rgba(0,0,0,.35)!important;color:#fff!important;-webkit-text-fill-color:#fff!important}
    .boss-card *{color:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important}
    .boss-kicker{font-size:12px;font-weight:950;color:#93c5fd!important;-webkit-text-fill-color:#93c5fd!important;margin-bottom:8px}
    .boss-title{font-size:23px;font-weight:950;color:#fff!important;-webkit-text-fill-color:#fff!important;margin-bottom:8px;line-height:1.3}
    .boss-summary{font-size:14px;font-weight:900;line-height:1.65;color:#e5e7eb!important;-webkit-text-fill-color:#e5e7eb!important;margin:10px 0}
    .boss-action{background:#ffffff!important;border-radius:16px;padding:13px;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;font-size:15px;font-weight:950;line-height:1.5;margin:12px 0}
    .boss-action *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .boss-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
    .boss-box{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.15);border-radius:15px;padding:10px}
    .boss-label{font-size:11px;font-weight:850;color:#cbd5e1!important;-webkit-text-fill-color:#cbd5e1!important;margin-bottom:4px}
    .boss-value{font-size:15px;font-weight:950;color:#fff!important;-webkit-text-fill-color:#fff!important;line-height:1.35}
    .boss-reason{font-size:12px;font-weight:850;line-height:1.65;color:#cbd5e1!important;-webkit-text-fill-color:#cbd5e1!important;margin-top:10px}
    .boss-warning{background:rgba(239,68,68,.18);border:1px solid rgba(239,68,68,.35);border-radius:14px;padding:10px;margin-top:10px;font-size:12px;font-weight:850;line-height:1.5}


    /* V101-1 투자금 배분 엔진 */
    .alloc-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .alloc-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .alloc-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .alloc-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .alloc-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .alloc-action *{color:#fff!important;-webkit-text-fill-color:#fff!important}
    .alloc-row{display:flex;justify-content:space-between;gap:10px;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .alloc-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .alloc-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:5px;line-height:1.45}
    .alloc-money{text-align:right;font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}
    .alloc-bar{height:9px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin-top:7px}
    .alloc-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#60a5fa 0%,#22c55e 100%)}
    .alloc-note{font-size:12px;font-weight:850;line-height:1.6;color:#334155!important;-webkit-text-fill-color:#334155!important;margin-top:10px}


    /* V102-1 뉴스 결론화 */
    .newscon-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .newscon-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .newscon-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .newscon-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .newscon-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .newscon-head{font-size:14px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .newscon-body{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.5;margin-top:4px}
    .newscon-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}


    /* V103-1 토스 포트 자동갱신 */
    .toss-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .toss-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .toss-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .toss-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .toss-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .toss-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .toss-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .toss-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:4px;line-height:1.45}


    /* V104-1 공급망 발굴 DB */
    .supply-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .supply-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .supply-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .supply-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .supply-action{background:#07111f;border-radius:15px;padding:12px;color:#fff!important;-webkit-text-fill-color:#fff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .supply-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .supply-head{display:flex;justify-content:space-between;gap:8px}
    .supply-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .supply-score{font-size:17px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap}
    .supply-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:5px;line-height:1.5}
    .supply-tag{display:inline-block;background:#e0f2fe;border-radius:999px;padding:3px 8px;margin:2px;font-size:11px;font-weight:900;color:#0369a1!important;-webkit-text-fill-color:#0369a1!important}


    /* V105-2 DB 상태 확인 */
    .db-card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%)!important;border:1px solid #e2e8f0!important;border-radius:24px!important;padding:18px!important;margin:16px 0!important;box-shadow:0 18px 45px rgba(0,0,0,.18)!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .db-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .db-title{font-size:21px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .db-sub{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;line-height:1.45;margin-bottom:12px}
    .db-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
    .db-box{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:14px;padding:10px}
    .db-label{font-size:11px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-bottom:4px}
    .db-value{font-size:14px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;line-height:1.35;word-break:break-all}
    .db-action{background:#07111f!important;border-radius:15px;padding:12px;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .db-action, .db-action *{color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;opacity:1!important}
    .db-dark-text{background:#07111f!important;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;border-radius:15px;padding:12px;font-size:14px;font-weight:950;line-height:1.5;margin:10px 0}
    .db-dark-text *{color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;opacity:1!important}
    .db-row{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:11px 12px;margin:8px 0}
    .db-name{font-size:15px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important}
    .db-meta{font-size:12px;font-weight:850;color:#64748b!important;-webkit-text-fill-color:#64748b!important;margin-top:4px;line-height:1.45}


    /* V107-5 THEME FIX: Streamlit 다크/라이트 모드 영향 차단 */
    :root{color-scheme:light!important;}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"]{background:#f8fafc!important;color:#0f172a!important;}

    /* 흰 카드 영역은 무조건 검은 글씨 */
    .card,.hold,.eval,.scorebox,.db-card,.brief-card,.brief-search,.newscon-card,.supply-card,.target-card,.future-card,.value-card,.rebalance-card,.alloc-card,.toss-card,.buytiming-card,.thermo-wrap,
    div[data-testid="stExpander"], div[data-testid="stExpander"] details, div[data-testid="stExpander"] summary{
        background:#ffffff!important;
        color:#0f172a!important;
        -webkit-text-fill-color:#0f172a!important;
    }
    .card *,.hold *,.eval *,.scorebox *,.db-card *,.brief-card *,.brief-search *,.newscon-card *,.supply-card *,.target-card *,.future-card *,.value-card *,.rebalance-card *,.alloc-card *,.toss-card *,.buytiming-card *,.thermo-wrap *,
    div[data-testid="stExpander"] *, div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li, div[data-testid="stMarkdownContainer"] span{
        color:#0f172a!important;
        -webkit-text-fill-color:#0f172a!important;
        opacity:1!important;
    }

    /* 검은 박스/결론 박스는 무조건 흰 글씨 */
    .hero,.hero *,.action,.action *,.boss-card,.boss-card *,.nav,.nav *,
    .db-action,.db-action *,.brief-action,.brief-action *,.newscon-action,.newscon-action *,.supply-action,.supply-action *,
    .target-action,.target-action *,.future-action,.future-action *,.value-action,.value-action *,.rebalance-action,.rebalance-action *,
    .alloc-action,.alloc-action *,.toss-action,.toss-action *,.buytiming-action,.buytiming-action *{
        color:#ffffff!important;
        -webkit-text-fill-color:#ffffff!important;
        opacity:1!important;
    }

    /* 입력/선택 영역도 테마 영향 차단 */
    input, textarea, select, div[data-baseweb="input"] *, div[data-baseweb="textarea"] *, div[data-baseweb="select"] *{
        color:#0f172a!important;
        -webkit-text-fill-color:#0f172a!important;
        background:#ffffff!important;
    }

    /* 보조 텍스트는 회색 유지하되 안 보이지 않게 고정 */
    .body,.meta,.db-sub,.brief-sub,.newscon-sub,.supply-sub,.target-sub,.future-sub,.value-sub,.rebalance-sub,.alloc-sub,.toss-sub,.buytiming-sub,.notice{
        color:#475569!important;
        -webkit-text-fill-color:#475569!important;
    }


    /* V108-2 VERIFIED: 컴파스/전략/TOP3 + 강제 글자색 안정화 */
    .hero,.hero *{color:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important}
    .card,.hold,.eval,.scorebox,.search-card,.search-card *,.card *,.hold *,.eval *,.scorebox *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .body,.meta,.scorebox,.eval{color:#475569!important;-webkit-text-fill-color:#475569!important}
    .action,.action *{color:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important}
    .action-sub{color:#dbeafe!important;-webkit-text-fill-color:#dbeafe!important}
    .badge{color:#bbf7d0!important;-webkit-text-fill-color:#bbf7d0!important}
    div[data-testid="stExpander"]{background:#ffffff!important;border:1px solid #e2e8f0!important;border-radius:18px!important;margin:10px 0!important;overflow:hidden!important}
    div[data-testid="stExpander"] *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    div[data-testid="stExpander"] .action, div[data-testid="stExpander"] .action *,
    div[data-testid="stExpander"] .boss-card, div[data-testid="stExpander"] .boss-card *,
    div[data-testid="stExpander"] .db-action, div[data-testid="stExpander"] .db-action *,
    div[data-testid="stExpander"] .supply-action, div[data-testid="stExpander"] .supply-action *,
    div[data-testid="stExpander"] .brief-action, div[data-testid="stExpander"] .brief-action *,
    div[data-testid="stExpander"] .target-action, div[data-testid="stExpander"] .target-action *,
    div[data-testid="stExpander"] .future-action, div[data-testid="stExpander"] .future-action *,
    div[data-testid="stExpander"] .rebalance-action, div[data-testid="stExpander"] .rebalance-action *,
    div[data-testid="stExpander"] .value-action, div[data-testid="stExpander"] .value-action *,
    div[data-testid="stExpander"] .buytiming-action, div[data-testid="stExpander"] .buytiming-action *,
    div[data-testid="stExpander"] .newscon-action, div[data-testid="stExpander"] .newscon-action *{color:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important}
    .compass-card{background:linear-gradient(180deg,#07111f 0%,#0b1628 100%)!important;color:#fff!important;-webkit-text-fill-color:#fff!important;border-radius:26px;padding:20px;margin:14px 0;box-shadow:0 18px 45px rgba(15,23,42,.24)}
    .compass-card *{color:#fff!important;-webkit-text-fill-color:#fff!important;opacity:1!important}
    .compass-k{font-size:13px;font-weight:950;color:#93c5fd!important;-webkit-text-fill-color:#93c5fd!important;margin-bottom:8px}
    .compass-main{font-size:30px;font-weight:950;line-height:1.18;margin:4px 0}
    .compass-score{font-size:54px;font-weight:950;line-height:1;margin:10px 0}
    .compass-sub{font-size:14px;font-weight:850;line-height:1.6;color:#dbeafe!important;-webkit-text-fill-color:#dbeafe!important}
    .compass-pill{display:inline-block;margin-top:10px;padding:7px 12px;border-radius:999px;background:#14532d;color:#bbf7d0!important;-webkit-text-fill-color:#bbf7d0!important;font-weight:950;font-size:12px}
    .strategy-card{background:#fff!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;border:1px solid #e2e8f0;border-radius:22px;padding:17px;margin:12px 0;box-shadow:0 10px 25px rgba(15,23,42,.08)}
    .strategy-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .strategy-title{font-size:21px;font-weight:950;margin-bottom:8px}
    .strategy-line{font-size:14px;font-weight:850;line-height:1.65;color:#475569!important;-webkit-text-fill-color:#475569!important}
    .top3-card{background:#fff!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;border:1px solid #e2e8f0;border-radius:18px;padding:14px;margin:9px 0;box-shadow:0 8px 18px rgba(15,23,42,.06)}
    .top3-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .top3-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
    .top3-name{font-size:18px;font-weight:950}
    .top3-score{font-size:20px;font-weight:950;white-space:nowrap}
    .top3-meta{font-size:13px;font-weight:850;line-height:1.55;color:#475569!important;-webkit-text-fill-color:#475569!important;margin-top:6px}

    

    /* V108-3 HEADER FIX: 5개 탭 공통 상단 헤더 글자색 강제 */
    .hero{
        background:#07111f!important;
        color:#ffffff!important;
        -webkit-text-fill-color:#ffffff!important;
        border-radius:24px!important;
    }
    .hero, .hero div, .hero span, .hero h1, .hero p, .hero strong{
        color:#ffffff!important;
        -webkit-text-fill-color:#ffffff!important;
        opacity:1!important;
        text-shadow:none!important;
    }
    .hero-title{
        display:block!important;
        color:#ffffff!important;
        -webkit-text-fill-color:#ffffff!important;
        font-size:29px!important;
        font-weight:950!important;
        line-height:1.25!important;
        margin:0 0 8px 0!important;
    }
    .hero-subtitle{
        display:block!important;
        color:#dbeafe!important;
        -webkit-text-fill-color:#dbeafe!important;
        font-size:14px!important;
        font-weight:850!important;
        line-height:1.45!important;
        margin:0!important;
    }


    /* V110 SEARCH REPORT */
    .search-report{background:linear-gradient(180deg,#07111f,#0b1628)!important;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;border-radius:26px;padding:20px;margin:14px 0;box-shadow:0 22px 55px rgba(0,0,0,.30)}
    .search-report *{color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;opacity:1!important}
    .search-kicker{font-size:12px;font-weight:950;color:#bfdbfe!important;-webkit-text-fill-color:#bfdbfe!important;margin-bottom:7px}
    .search-name{font-size:25px;font-weight:950;line-height:1.25;margin-bottom:8px}
    .search-verdict{font-size:18px;font-weight:950;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:12px;margin:10px 0;line-height:1.5}
    .search-score-big{font-size:42px;font-weight:950;line-height:1;margin:8px 0}
    .search-report-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
    .search-report-box{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.15);border-radius:15px;padding:10px}
    .search-report-label{font-size:11px;font-weight:850;color:#cbd5e1!important;-webkit-text-fill-color:#cbd5e1!important;margin-bottom:4px}
    .search-report-value{font-size:15px;font-weight:950;line-height:1.35}
    .search-point-card{background:#ffffff!important;border:1px solid #e2e8f0!important;border-radius:20px!important;padding:15px!important;margin:12px 0!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;font-size:13px;font-weight:850;line-height:1.65}
    .search-point-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .search-point-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}
    .search-point-good{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:15px;padding:11px}
    .search-point-bad{background:#fff7ed;border:1px solid #fed7aa;border-radius:15px;padding:11px}
    .search-card{background:#ffffff!important;border:1px solid #e2e8f0!important;border-radius:20px!important;padding:15px!important;margin:12px 0!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important}
    .search-card *{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;opacity:1!important}
    .search-title{font-size:20px;font-weight:950;color:#020617!important;-webkit-text-fill-color:#020617!important;margin-bottom:6px}
    .search-sub,.search-mini{font-size:13px;font-weight:850;color:#475569!important;-webkit-text-fill-color:#475569!important;line-height:1.6}
    .search-final{background:#07111f!important;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;border-radius:15px;padding:12px;margin-top:10px;font-size:14px;font-weight:950;line-height:1.5}
    .search-final *{color:#ffffff!important;-webkit-text-fill-color:#ffffff!important}

    </style>
    """, unsafe_allow_html=True)

def header():
    st.markdown(
        f'''<div class="hero" style="background:#07111f!important;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;border-radius:24px!important;padding:22px!important;margin-bottom:14px!important;">
                <div class="hero-title" style="color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;font-size:29px!important;font-weight:950!important;line-height:1.25!important;margin:0 0 8px 0!important;">{APP_TITLE}</div>
                <div class="hero-subtitle" style="color:#dbeafe!important;-webkit-text-fill-color:#dbeafe!important;font-size:14px!important;font-weight:850!important;line-height:1.45!important;margin:0!important;">{APP_SUBTITLE}</div>
            </div>''',
        unsafe_allow_html=True
    )

def card(title, body):
    st.markdown(f'<div class="card"><div class="title">{title}</div><div class="body">{body}</div></div>', unsafe_allow_html=True)

def nav(tab):
    items = [("home","🏠<br>홈"),("search","🔎<br>검색"),("rec","🚀<br>추천"),("holdings","📦<br>내종목"),("profile","📈<br>투자기록")]
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
    items = []

    # 1) 포트폴리오 위험도 기반
    hs, hg, hr, risk_reasons, risk_action = portfolio_health(data)
    if hs < 55:
        items.append({
            "level": "🔴 위험",
            "title": "포트폴리오 위험도 높음",
            "body": f"{hs}점 · {hg}<br>{risk_action}"
        })
    elif hs < 70:
        items.append({
            "level": "🟠 경고",
            "title": "포트폴리오 주의 필요",
            "body": f"{hs}점 · {hg}<br>{risk_action}"
        })

    # 2) 섹터 비중 위험
    _, _, _, _, weights, rows = metrics(data)
    semi = weights.get("반도체", 0)
    us = weights.get("미국지수", 0)
    display = weights.get("디스플레이", 0)

    if semi >= 60:
        items.append({
            "level": "🔴 위험",
            "title": "반도체 비중 과다",
            "body": f"반도체 비중 {semi:.1f}%입니다. 추가매수보다 분산 점검이 우선입니다."
        })
    elif semi >= 45:
        items.append({
            "level": "🟠 경고",
            "title": "반도체 비중 높음",
            "body": f"반도체 비중 {semi:.1f}%입니다. 신규 반도체 매수는 신중하게 보는 것이 좋습니다."
        })

    if us < 15:
        items.append({
            "level": "🟡 주의",
            "title": "미국지수 방어비중 부족",
            "body": f"미국지수 비중 {us:.1f}%입니다. 장기 안정성 보강 후보입니다."
        })

    if display >= 20:
        items.append({
            "level": "🟡 주의",
            "title": "디스플레이 비중 확인",
            "body": f"디스플레이 비중 {display:.1f}%입니다. 업황 변동성 확인이 필요합니다."
        })

    # 3) 개별 종목 손실 위험
    for n, q, a, r in rows:
        if not r:
            continue
        rate = r.get("rate", 0)
        if rate <= -30:
            items.append({
                "level": "⚫ 긴급",
                "title": f"{n} 급락 위험",
                "body": f"수익률 {rate:.2f}%입니다. 손실 확대 여부를 즉시 확인하세요."
            })
        elif rate <= -20:
            items.append({
                "level": "🔴 위험",
                "title": f"{n} 손실 확대",
                "body": f"수익률 {rate:.2f}%입니다. 추가 하락 여부 확인이 필요합니다."
            })
        elif rate <= -10:
            items.append({
                "level": "🟠 경고",
                "title": f"{n} 경고 구간",
                "body": f"수익률 {rate:.2f}%입니다. 관찰이 필요합니다."
            })

    # 4) 뉴스 부정 영향
    try:
        all_news = rss_items()
        for h in data.get("holdings", []):
            stock = norm(h.get("name", ""))
            keys = holding_news_keywords(stock) if "holding_news_keywords" in globals() else [stock]
            neg_count = 0
            neg_titles = []
            for source, title, link in all_news:
                if news_matches(title, keys) if "news_matches" in globals() else (stock.lower() in str(title).lower()):
                    impact, _ = news_impact(title) if "news_impact" in globals() else ("⚪ 중립", 0)
                    if "부정" in impact:
                        neg_count += 1
                        neg_titles.append(title)
            if neg_count >= 2:
                items.append({
                    "level": "🔴 위험",
                    "title": f"{stock} 부정뉴스 증가",
                    "body": f"부정 뉴스 {neg_count}건 감지<br>{neg_titles[0] if neg_titles else ''}"
                })
            elif neg_count == 1:
                items.append({
                    "level": "🟡 주의",
                    "title": f"{stock} 부정뉴스 확인",
                    "body": f"부정 뉴스 1건 감지<br>{neg_titles[0] if neg_titles else ''}"
                })
    except Exception:
        pass

    rank = {"⚫ 긴급": 0, "🔴 위험": 1, "🟠 경고": 2, "🟡 주의": 3, "🟢 안전": 4}
    return sorted(items, key=lambda x: rank.get(x["level"], 9))

def render_emergency_board(data):
    items = emergency_items(data)
    if not items:
        card("🚨 긴급상황판", "🟢 긴급상황 없음<br>현재 큰 위험 신호는 없습니다.")
        return

    counts = {}
    for x in items:
        counts[x["level"]] = counts.get(x["level"], 0) + 1

    summary = " · ".join([f"{k} {v}건" for k, v in counts.items()])
    detail = "<br><br>".join([
        f"<b>{x['level']} {x['title']}</b><br>{x['body']}"
        for x in items[:8]
    ])

    more = ""
    if len(items) > 8:
        more = f"<br><br>외 {len(items)-8}건 추가 경고가 있습니다."

    card("🚨 긴급상황판", f"{summary}<br><br>{detail}{more}")



def render_investment_thermometer(data):
    score, grade, summary, reasons, action = portfolio_health(data)

    # 기존 안전도 점수(0~100)를 투자온도계(-100~+100)로 변환
    # +100 = 매우 안전 / 0 = 중립 / -100 = 매우 위험
    temp = int((score - 50) * 2)
    temp = max(-100, min(100, temp))
    marker_top = (100 - temp) / 200 * 100

    if temp >= 50:
        state = "🟢 안전권"
        guide = "현재는 비교적 안정적입니다."
    elif temp >= 15:
        state = "🟡 양호"
        guide = "크게 위험하지는 않지만 비중 점검은 필요합니다."
    elif temp > -15:
        state = "⚪ 중립"
        guide = "방향성이 애매합니다. 무리한 매매보다 관찰이 좋습니다."
    elif temp > -50:
        state = "🟠 주의"
        guide = "위험 쪽으로 기울고 있습니다. 신규매수는 신중하게 보세요."
    else:
        state = "🔴 위험권"
        guide = "위험 신호가 강합니다. 손실 확대와 비중 집중을 먼저 확인하세요."

    html = f"""
    <div class="thermo-wrap">
        <div class="thermo-title">📈 투자온도계</div>
        <div class="thermo-box">
            <div class="thermo-line"></div>
            <div class="thermo-center"></div>
            <div class="thermo-label top">+100 안전</div>
            <div class="thermo-label mid">0 중립</div>
            <div class="thermo-label bot">-100 위험</div>
            <div class="thermo-marker" style="top:{marker_top}%;">{temp:+d}</div>
        </div>
        <div class="thermo-note">
            상태 : <b>{state}</b><br>
            {guide}<br>
            기준 : {summary}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)



# V94-2.1 긴급복구: 매수타이밍 함수 누락 방지
def safe_timing_score(name, result=None):
    n = norm(name)
    sec = sector(n)
    score = 55
    reasons = []

    if sec == "미국지수":
        score += 10
        stage = "🟢 안정 성장"
        reasons.append("미국지수형 자산은 장기 적립식 관점에서 안정성이 있습니다.")
    elif sec == "전력/자동화":
        score += 8
        stage = "🟢 성장 초중기"
        reasons.append("전력/자동화 테마는 성장성 관점에서 관심 유지.")
    elif sec == "반도체":
        score += 4
        stage = "🟡 성장"
        reasons.append("반도체는 성장성은 있으나 과열 여부 확인 필요.")
    elif sec == "디스플레이":
        score -= 4
        stage = "🟠 회복 확인"
        reasons.append("디스플레이는 업황 회복 확인 필요.")
    else:
        stage = "🟡 중립"
        reasons.append("섹터 기준 보수 판단.")

    try:
        rate = float(result.get("rate", 0) or 0) if result else 0
        if rate <= -10:
            score -= 8
            reasons.append("손실폭이 커서 추가매수는 신중.")
        elif -5 <= rate <= 5:
            score += 4
            reasons.append("손익이 과열/급락 구간은 아님.")
        elif rate >= 15:
            score -= 6
            reasons.append("수익구간이 높아 추격매수보다 관리 우선.")
    except Exception:
        rate = 0

    score = max(0, min(100, int(score)))
    if score >= 75:
        level = "🟢 분할매수 가능"
        action = "1주 또는 소액 분할매수 가능"
    elif score >= 60:
        level = "🟡 소액 가능"
        action = "무리하지 말고 소액 분할"
    elif score >= 45:
        level = "🟠 관망"
        action = "추가매수 보류"
    else:
        level = "🔴 매수금지"
        action = "비중 확대 금지"

    return {
        "name": n,
        "score": score,
        "stage": stage,
        "level": level,
        "action": action,
        "upside": score,
        "risk": max(10, min(90, 100 - score)),
        "reasons": reasons[:4],
        "rate": rate,
    }

def render_buy_timing_card_safe(item, title="⏱️ 매수타이밍"):
    reasons = "<br>".join([f"① {x}" for x in item.get("reasons", [])])
    html = (
        '<div class="buytiming-card">'
        '<div class="buytiming-top">'
        '<div>'
        f'<div class="buytiming-title">{title} · {item.get("name","-")}</div>'
        f'<div class="buytiming-sub">{item.get("level","🟠 관망")}</div>'
        '</div>'
        '<div class="buytiming-score">'
        f'<div class="num">{item.get("score",50)}</div>'
        '<div class="txt">매수적합도</div>'
        '</div>'
        '</div>'
        f'<div class="buytiming-action">오늘 행동: {item.get("action","관망")}</div>'
        f'<div class="buytiming-bar"><div class="buytiming-fill" style="width:{item.get("score",50)}%"></div></div>'
        '<div class="buytiming-grid">'
        f'<div class="buytiming-box"><div class="buytiming-label">현재위치</div><div class="buytiming-value">{item.get("stage","-")}</div></div>'
        f'<div class="buytiming-box"><div class="buytiming-label">상승확률</div><div class="buytiming-value">{item.get("upside",50)}%</div></div>'
        f'<div class="buytiming-box"><div class="buytiming-label">선반영위험</div><div class="buytiming-value">{item.get("risk",50)}%</div></div>'
        f'<div class="buytiming-box"><div class="buytiming-label">현재수익률</div><div class="buytiming-value">{item.get("rate",0):.2f}%</div></div>'
        '</div>'
        f'<div class="buytiming-reason"><b>판단근거</b><br>{reasons}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def holding_buy_timing_list(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    items = []
    for n, q, a, r in rows:
        try:
            items.append(safe_timing_score(n, r))
        except Exception:
            pass
    return sorted(items, key=lambda x: x.get("score", 0), reverse=True)

def render_buy_timing_summary(data):
    items = holding_buy_timing_list(data)
    if not items:
        card("⏱️ 매수타이밍", "보유종목 데이터가 없어 매수타이밍을 계산하지 못했습니다.")
        return
    render_buy_timing_card_safe(items[0], "⏱️ 보유종목 매수타이밍 1순위")

def render_buy_timing_ranking(data):
    items = holding_buy_timing_list(data)
    if not items:
        return
    st.markdown('<div class="buytiming-card"><div class="buytiming-title">⏱️ 보유종목 매수타이밍 전체 순위</div>', unsafe_allow_html=True)
    for idx, x in enumerate(items, start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        row = (
            '<div class="buytiming-list">'
            '<div class="buytiming-list-head">'
            f'<div class="buytiming-list-name">{medal} {x.get("name","-")}</div>'
            f'<div class="buytiming-list-score">{x.get("score",50)}점</div>'
            '</div>'
            f'<div class="buytiming-list-meta">{x.get("level","🟠 관망")} · {x.get("action","관망")}<br>현재위치 {x.get("stage","-")} · 상승확률 {x.get("upside",50)}% · 선반영위험 {x.get("risk",50)}%</div>'
            '</div>'
        )
        st.markdown(row, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



# V95-1: 저평가·배당·성장성 1차 엔진
def value_profile(name):
    n = norm(name)
    sec = sector(n)
    if sec == "미국지수":
        return {"value": 65, "dividend": 55, "growth": 72, "quality": 78, "label": "장기 안정형"}
    if sec == "반도체":
        return {"value": 52, "dividend": 25, "growth": 82, "quality": 70, "label": "성장형"}
    if sec == "전력/자동화":
        return {"value": 60, "dividend": 35, "growth": 78, "quality": 66, "label": "성장·인프라형"}
    if sec == "디스플레이":
        return {"value": 58, "dividend": 20, "growth": 48, "quality": 45, "label": "회복 확인형"}
    return {"value": 50, "dividend": 30, "growth": 55, "quality": 50, "label": "중립형"}

def value_dividend_score(name, result=None):
    n = norm(name)
    p = value_profile(n)
    value = int(p["value"])
    dividend = int(p["dividend"])
    growth = int(p["growth"])
    quality = int(p["quality"])
    score = int(value * 0.30 + dividend * 0.15 + growth * 0.35 + quality * 0.20)
    reasons = []

    try:
        rate = float(result.get("rate", 0) or 0) if result else 0
        if rate <= -10 and growth >= 65:
            score += 5
            reasons.append("성장성 대비 손실구간이라 저가 관심 후보입니다.")
        elif rate >= 15:
            score -= 5
            reasons.append("수익구간이 높아 저평가 매력은 일부 낮아졌습니다.")
    except Exception:
        rate = 0

    if value >= 60:
        reasons.append("가격·섹터 기준 저평가 매력이 있습니다.")
    elif value <= 50:
        reasons.append("저평가보다는 성장 기대 중심으로 봐야 합니다.")

    if dividend >= 50:
        reasons.append("배당/안정성 보강 역할이 가능합니다.")
    elif dividend <= 30:
        reasons.append("배당 매력은 낮아 시세차익 중심입니다.")

    if growth >= 75:
        reasons.append("성장성 점수가 높아 중장기 관심을 유지할 만합니다.")
    elif growth <= 50:
        reasons.append("성장성 확인이 필요합니다.")

    score = max(0, min(100, int(score)))
    if score >= 75:
        action = "🟢 가치·성장 우수"
    elif score >= 62:
        action = "🟡 보유 적합"
    elif score >= 50:
        action = "🟠 확인 필요"
    else:
        action = "🔴 가치매력 낮음"

    return {"name": n, "score": score, "action": action, "value": value, "dividend": dividend,
            "growth": growth, "quality": quality, "label": p["label"], "rate": rate, "reasons": reasons[:4]}

def value_dividend_list(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    out = []
    for n, q, a, r in rows:
        try:
            out.append(value_dividend_score(n, r))
        except Exception:
            pass
    return sorted(out, key=lambda x: x.get("score", 0), reverse=True)

def render_value_dividend_summary(data):
    items = value_dividend_list(data)
    if not items:
        return
    top = items[0]
    reasons = "<br>".join([f"① {x}" for x in top.get("reasons", [])])
    html = (
        '<div class="value-card">'
        f'<div class="value-title">💎 저평가·배당·성장성 1순위 · {top["name"]}</div>'
        f'<div class="value-sub">{top["label"]} · {top["action"]}</div>'
        f'<div class="value-action">판단: {top["score"]}점 · 매수 판단 보조지표로 확인</div>'
        '<div class="value-grid">'
        f'<div class="value-box"><div class="value-label">저평가</div><div class="value-num">{top["value"]}점</div></div>'
        f'<div class="value-box"><div class="value-label">배당/안정</div><div class="value-num">{top["dividend"]}점</div></div>'
        f'<div class="value-box"><div class="value-label">성장성</div><div class="value-num">{top["growth"]}점</div></div>'
        f'<div class="value-box"><div class="value-label">기업품질</div><div class="value-num">{top["quality"]}점</div></div>'
        '</div>'
        f'<div class="value-reason"><b>판단근거</b><br>{reasons}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_value_dividend_ranking(data):
    items = value_dividend_list(data)
    if not items:
        return
    st.markdown('<div class="value-card"><div class="value-title">💎 저평가·배당·성장성 전체 순위</div>', unsafe_allow_html=True)
    for idx, x in enumerate(items, start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        row = (
            '<div class="value-row">'
            f'<div><div class="value-name">{medal} {x["name"]}</div>'
            f'<div class="value-meta">{x["label"]} · {x["action"]}<br>저평가 {x["value"]} · 배당 {x["dividend"]} · 성장 {x["growth"]}</div></div>'
            f'<div class="value-score">{x["score"]}점</div>'
            '</div>'
        )
        st.markdown(row, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



# V96-1: 리밸런싱 엔진 1차
def target_sector_weights():
    return {"미국지수": 30, "반도체": 25, "전력/자동화": 25, "디스플레이": 8, "기타": 12}

def rebalance_analysis(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return None
    targets = target_sector_weights()
    gaps = {}
    for sec in set(list(targets.keys()) + list(weights.keys())):
        now = float(weights.get(sec, 0) or 0)
        tgt = float(targets.get(sec, 10) or 10)
        gaps[sec] = {"now": now, "target": tgt, "gap": now - tgt}

    reduce_stocks, add_stocks = [], []
    for n, q, a, r in rows:
        if not r:
            continue
        sec = sector(n)
        now_w = weights.get(sec, 0)
        tgt_w = targets.get(sec, 10)
        rate_v = float(r.get("rate", 0) or 0)
        try:
            st_score = int(stock_score(n, q, a, r, weights, target_return(data)))
        except Exception:
            st_score = 50

        rs, rr = 0, []
        if now_w > tgt_w + 8:
            rs += 30; rr.append(f"{sec} 비중 과다")
        if rate_v >= 15:
            rs += 18; rr.append("수익구간 일부 관리")
        if rate_v <= -12:
            rs += 12; rr.append("손실 확대 점검")
        if st_score <= 52:
            rs += 15; rr.append("종목점수 낮음")
        if rs:
            reduce_stocks.append({"name": n, "score": rs, "rate": rate_v, "sector": sec, "reason": " · ".join(rr)})

        ads, ar = 0, []
        if now_w < tgt_w - 8:
            ads += 30; ar.append(f"{sec} 비중 부족")
        if st_score >= 68:
            ads += 18; ar.append("종목점수 양호")
        if -7 <= rate_v <= 7:
            ads += 8; ar.append("과열/급락 아님")
        if sec == "미국지수":
            ads += 12; ar.append("장기 안정성 보강")
        if ads:
            add_stocks.append({"name": n, "score": ads, "rate": rate_v, "sector": sec, "reason": " · ".join(ar)})

    reduce_stocks = sorted(reduce_stocks, key=lambda x: x["score"], reverse=True)
    add_stocks = sorted(add_stocks, key=lambda x: x["score"], reverse=True)
    reduce_top = reduce_stocks[0] if reduce_stocks else None
    add_top = add_stocks[0] if add_stocks else None

    if reduce_top and add_top and reduce_top["name"] != add_top["name"]:
        action = f'{reduce_top["name"]} 비중 점검 → {add_top["name"]} 보강 후보'
        summary = "비중 과다 후보와 부족 후보를 함께 점검합니다."
    elif add_top:
        action = f'{add_top["name"]} 보강 후보'
        summary = "줄일 후보보다 부족 비중 보강이 우선입니다."
    elif reduce_top:
        action = f'{reduce_top["name"]} 비중 점검'
        summary = "늘릴 후보보다 줄일 후보 점검이 우선입니다."
    else:
        action = "현재는 리밸런싱 필요 낮음"
        summary = "섹터 비중이 크게 벗어나지 않았습니다."

    return {"weights": weights, "targets": targets, "gaps": gaps, "reduce_stocks": reduce_stocks, "add_stocks": add_stocks, "reduce_top": reduce_top, "add_top": add_top, "action": action, "summary": summary}

def render_rebalance_summary(data):
    rb = rebalance_analysis(data)
    if not rb:
        card("🔄 리밸런싱", "리밸런싱 계산 데이터가 부족합니다.")
        return
    rt, at = rb.get("reduce_top"), rb.get("add_top")
    reduce_name = rt["name"] if rt else "없음"
    add_name = at["name"] if at else "없음"
    reduce_reason = rt["reason"] if rt else "비중 축소 후보가 뚜렷하지 않습니다."
    add_reason = at["reason"] if at else "보강 후보가 뚜렷하지 않습니다."

    sector_lines = []
    for sec, g in rb["gaps"].items():
        if abs(g["gap"]) >= 5:
            mark = "과다" if g["gap"] > 0 else "부족"
            sector_lines.append(f'{sec}: 현재 {g["now"]:.1f}% / 목표 {g["target"]:.1f}% → {mark} {abs(g["gap"]):.1f}%p')
    sector_html = "<br>".join(sector_lines[:5]) if sector_lines else "현재 섹터 비중은 큰 이탈이 없습니다."

    html = (
        '<div class="rebalance-card">'
        '<div class="rebalance-title">🔄 오늘의 리밸런싱 제안</div>'
        f'<div class="rebalance-sub">{rb["summary"]}</div>'
        f'<div class="rebalance-action">오늘 행동: {rb["action"]}<br>※ 실제 매도 지시가 아니라 비중 점검 후보입니다.</div>'
        '<div class="rebalance-grid">'
        f'<div class="rebalance-box"><div class="rebalance-label">줄일 후보</div><div class="rebalance-value">{reduce_name}</div></div>'
        f'<div class="rebalance-box"><div class="rebalance-label">늘릴 후보</div><div class="rebalance-value">{add_name}</div></div>'
        f'<div class="rebalance-box"><div class="rebalance-label">줄일 이유</div><div class="rebalance-value">{reduce_reason}</div></div>'
        f'<div class="rebalance-box"><div class="rebalance-label">늘릴 이유</div><div class="rebalance-value">{add_reason}</div></div>'
        '</div>'
        f'<div class="rebalance-reason"><b>섹터 비중 점검</b><br>{sector_html}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_rebalance_detail(data):
    rb = rebalance_analysis(data)
    if not rb:
        return
    st.markdown('<div class="rebalance-card"><div class="rebalance-title">🔄 리밸런싱 상세 후보</div>', unsafe_allow_html=True)
    for title, key in [("줄일 후보", "reduce_stocks"), ("늘릴 후보", "add_stocks")]:
        st.markdown(f'<div class="rebalance-sub">{title}</div>', unsafe_allow_html=True)
        items = rb.get(key, [])
        if items:
            for x in items[:5]:
                row = (
                    '<div class="rebalance-row">'
                    '<div class="rebalance-row-head">'
                    f'<div class="rebalance-name">{x["name"]}</div>'
                    f'<div class="rebalance-score">{x["score"]}점</div>'
                    '</div>'
                    f'<div class="rebalance-meta">{x["sector"]} · 수익률 {x["rate"]:.2f}%<br>{x["reason"]}</div>'
                    '</div>'
                )
                st.markdown(row, unsafe_allow_html=True)
        else:
            st.markdown('<div class="rebalance-row"><div class="rebalance-meta">후보가 뚜렷하지 않습니다.</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



# V97-1: 목표가·손절가·매수구간 엔진 1차
def round_price_unit(price):
    try:
        p = float(price or 0)
        if p <= 0:
            return 0
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
        return 0

def target_price_plan(name, result=None, data=None):
    n = norm(name)
    sec = sector(n)
    price = None
    rate = 0
    if result:
        price = result.get("price")
        try:
            rate = float(result.get("rate", 0) or 0)
        except Exception:
            rate = 0
    if not price:
        try:
            price, _ = fetch_price(n)
        except Exception:
            price = fallback_price(n)

    try:
        price = float(price or 0)
    except Exception:
        price = 0

    if price <= 0:
        return None

    # 섹터별 목표/손절 폭
    if sec == "미국지수":
        t1, t2, stop = 0.06, 0.12, -0.07
        confidence = 72
        stage = "장기 안정형"
        reason = "미국지수는 단기 급등보다 장기 적립식 기준으로 목표폭을 보수적으로 설정합니다."
    elif sec == "반도체":
        t1, t2, stop = 0.10, 0.22, -0.10
        confidence = 66
        stage = "성장 변동형"
        reason = "반도체는 성장성은 높지만 변동성이 커 목표와 손절 폭을 넓게 둡니다."
    elif sec == "전력/자동화":
        t1, t2, stop = 0.09, 0.20, -0.09
        confidence = 70
        stage = "성장 인프라형"
        reason = "전력/자동화는 성장 테마와 수급 흐름을 반영해 중기 목표폭을 적용합니다."
    elif sec == "디스플레이":
        t1, t2, stop = 0.07, 0.15, -0.08
        confidence = 60
        stage = "회복 확인형"
        reason = "디스플레이는 업황 회복 확인이 필요해 목표를 보수적으로 잡습니다."
    else:
        t1, t2, stop = 0.08, 0.16, -0.08
        confidence = 60
        stage = "중립형"
        reason = "섹터 특성이 명확하지 않아 기본 목표폭을 적용합니다."

    # 현재 손익 상태 보정
    if rate >= 15:
        t1 *= 0.8
        t2 *= 0.85
        confidence -= 5
        extra = "현재 수익구간이 높아 신규 추격보다 분할매도/관리 기준을 우선합니다."
    elif rate <= -10:
        t1 *= 0.9
        t2 *= 0.9
        stop *= 0.85
        confidence -= 4
        extra = "현재 손실구간이라 목표보다 손실 확대 방어 기준을 함께 봐야 합니다."
    else:
        extra = "현재 손익이 과열/급락 극단은 아니어서 기본 목표 기준을 적용합니다."

    buy_low = round_price_unit(price * 0.96)
    buy_high = round_price_unit(price * 1.02)
    target1 = round_price_unit(price * (1 + t1))
    target2 = round_price_unit(price * (1 + t2))
    stop_price = round_price_unit(price * (1 + stop))

    exp1 = (target1 / price - 1) * 100 if price else 0
    exp2 = (target2 / price - 1) * 100 if price else 0
    loss = (stop_price / price - 1) * 100 if price else 0

    # 현재 매수구간 판단
    if buy_low <= price <= buy_high:
        zone = "🟢 매수구간"
        zone_action = "분할매수 가능"
    elif price > buy_high:
        zone = "🟠 상단 접근"
        zone_action = "추격매수 신중"
        confidence -= 3
    else:
        zone = "🟡 하단 대기"
        zone_action = "관심 유지"

    confidence = max(40, min(90, int(confidence)))

    return {
        "name": n,
        "price": round_price_unit(price),
        "buy_low": buy_low,
        "buy_high": buy_high,
        "target1": target1,
        "target2": target2,
        "stop": stop_price,
        "exp1": exp1,
        "exp2": exp2,
        "loss": loss,
        "confidence": confidence,
        "stage": stage,
        "zone": zone,
        "zone_action": zone_action,
        "reason": reason,
        "extra": extra,
        "sector": sec,
        "rate": rate,
    }

def target_price_list(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    items = []
    for n, q, a, r in rows:
        try:
            plan = target_price_plan(n, r, data)
            if plan:
                items.append(plan)
        except Exception:
            pass
    return sorted(items, key=lambda x: (x.get("confidence", 0), x.get("exp2", 0)), reverse=True)

def render_target_price_card(plan, title="🎯 목표가 엔진"):
    if not plan:
        return
    html = (
        '<div class="target-card">'
        f'<div class="target-title">{title} · {plan["name"]}</div>'
        f'<div class="target-sub">{plan["stage"]} · {plan["zone"]} · 신뢰도 {plan["confidence"]}%</div>'
        f'<div class="target-action">오늘 행동: {plan["zone_action"]}<br>현재가 {won(plan["price"])} 기준</div>'
        '<div class="target-grid">'
        f'<div class="target-box"><div class="target-label">매수 적정구간</div><div class="target-value">{won(plan["buy_low"])} ~ {won(plan["buy_high"])}</div></div>'
        f'<div class="target-box"><div class="target-label">손절선</div><div class="target-value">{won(plan["stop"])} ({plan["loss"]:.1f}%)</div></div>'
        f'<div class="target-box"><div class="target-label">1차 목표가</div><div class="target-value">{won(plan["target1"])} ({plan["exp1"]:.1f}%)</div></div>'
        f'<div class="target-box"><div class="target-label">2차 목표가</div><div class="target-value">{won(plan["target2"])} ({plan["exp2"]:.1f}%)</div></div>'
        '</div>'
        f'<div class="target-reason"><b>근거</b><br>① {plan["reason"]}<br>② {plan["extra"]}<br>③ 목표가는 확정 예측이 아니라 분할매수·분할매도 기준선입니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_target_price_summary(data):
    items = target_price_list(data)
    if not items:
        card("🎯 목표가 엔진", "목표가 계산 데이터가 부족합니다.")
        return
    render_target_price_card(items[0], "🎯 목표가 1순위")

def render_target_price_ranking(data):
    items = target_price_list(data)
    if not items:
        return
    st.markdown('<div class="target-card"><div class="target-title">🎯 보유종목 목표가 전체</div>', unsafe_allow_html=True)
    for idx, x in enumerate(items, start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        row = (
            '<div class="target-row">'
            '<div class="target-row-head">'
            f'<div class="target-name">{medal} {x["name"]}</div>'
            f'<div class="target-score">{x["confidence"]}%</div>'
            '</div>'
            f'<div class="target-meta">현재가 {won(x["price"])} · 매수구간 {won(x["buy_low"])}~{won(x["buy_high"])}<br>'
            f'1차 {won(x["target1"])} · 2차 {won(x["target2"])} · 손절 {won(x["stop"])}<br>'
            f'{x["zone"]} · {x["zone_action"]}</div>'
            '</div>'
        )
        st.markdown(row, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



# V98-1: 미래확률 엔진 1차
def future_probability_score(name, result=None, data=None):
    n = norm(name)
    sec = sector(n)
    reasons = []

    if sec == "미국지수":
        base = 62
        reasons.append("미국지수는 장기 우상향 기대와 분산효과를 반영합니다.")
    elif sec == "반도체":
        base = 64
        reasons.append("반도체는 AI/첨단산업 성장 기대를 반영합니다.")
    elif sec == "전력/자동화":
        base = 66
        reasons.append("전력/자동화는 전력망·로봇·자동화 투자 기대를 반영합니다.")
    elif sec == "디스플레이":
        base = 50
        reasons.append("디스플레이는 업황 회복 확인이 필요해 보수적으로 판단합니다.")
    else:
        base = 55
        reasons.append("섹터 기준 중립 기대값으로 시작합니다.")

    try:
        if data:
            _, _, _, _, weights, rows = metrics(data)
            for rn, q, a, r in rows:
                if norm(rn) == n:
                    st_s = int(stock_score(n, q, a, r, weights, target_return(data)))
                    base += int((st_s - 60) * 0.35)
                    reasons.append(f"종목점수 {st_s}점을 미래확률에 반영했습니다.")
                    result = result or r
                    break
    except Exception:
        pass

    try:
        if "safe_timing_score" in globals():
            t = safe_timing_score(n, result)
            timing_score = int(t.get("score", 55))
        elif "buy_timing_analysis" in globals():
            t = buy_timing_analysis(n, result, data)
            timing_score = int(t.get("score", 55))
        else:
            timing_score = 55
        base += int((timing_score - 55) * 0.25)
        reasons.append(f"매수타이밍 {timing_score}점을 반영했습니다.")
    except Exception:
        timing_score = 55

    try:
        if "value_dividend_score" in globals():
            v = value_dividend_score(n, result)
            vg = int(v.get("growth", 55))
            vv = int(v.get("value", 55))
            base += int((vg - 55) * 0.18)
            base += int((vv - 55) * 0.08)
            reasons.append(f"성장성 {vg}점, 저평가 {vv}점을 반영했습니다.")
    except Exception:
        pass

    try:
        rate = float(result.get("rate", 0) or 0) if result else 0
        if rate >= 20:
            base -= 8
            reasons.append("현재 수익률이 높아 단기 선반영 가능성을 감점했습니다.")
        elif rate <= -12:
            base -= 5
            reasons.append("손실폭이 커서 단기 회복확률은 보수적으로 봅니다.")
        elif -5 <= rate <= 5:
            base += 3
            reasons.append("손익이 과열/급락 구간은 아니라 기대값을 소폭 보강했습니다.")
    except Exception:
        rate = 0

    try:
        if data:
            _, _, _, _, weights, _ = metrics(data)
            sw = weights.get(sec, 0)
            if sw >= 55:
                base -= 6
                reasons.append(f"{sec} 비중이 높아 포트 관점 기대값을 낮췄습니다.")
            elif sw <= 18:
                base += 3
                reasons.append(f"{sec} 비중이 낮아 분산 보강 기대를 반영했습니다.")
    except Exception:
        pass

    p6 = max(20, min(88, int(base)))
    p3 = max(15, min(85, int(p6 - 5)))
    p12 = max(25, min(90, int(p6 + 6)))

    confidence = 62
    if len(reasons) >= 4:
        confidence += 8
    if result:
        confidence += 4
    confidence = max(45, min(82, confidence))

    if p6 >= 75:
        action = "🟢 상승 기대값 우위"
    elif p6 >= 62:
        action = "🟡 긍정 우세"
    elif p6 >= 50:
        action = "🟠 중립 관찰"
    else:
        action = "🔴 기대값 낮음"

    return {"name": n, "p3": p3, "p6": p6, "p12": p12, "confidence": confidence, "action": action, "sector": sec, "rate": rate, "reasons": reasons[:5]}

def future_probability_list(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    items = []
    for n, q, a, r in rows:
        try:
            items.append(future_probability_score(n, r, data))
        except Exception:
            pass
    return sorted(items, key=lambda x: (x.get("p12", 0), x.get("p6", 0)), reverse=True)

def render_future_probability_card(item, title="🔮 미래확률 엔진"):
    reasons = "<br>".join([f"① {x}" for x in item.get("reasons", [])])
    html = (
        '<div class="future-card">'
        f'<div class="future-title">{title} · {item["name"]}</div>'
        f'<div class="future-sub">{item["sector"]} · {item["action"]} · 신뢰도 {item["confidence"]}%</div>'
        f'<div class="future-action">현재 판단: {item["action"]}<br>※ 확정 예측이 아니라 기대값 우위 판단입니다.</div>'
        '<div class="future-grid">'
        f'<div class="future-box"><div class="future-label">3개월</div><div class="future-value">{item["p3"]}%</div></div>'
        f'<div class="future-box"><div class="future-label">6개월</div><div class="future-value">{item["p6"]}%</div></div>'
        f'<div class="future-box"><div class="future-label">12개월</div><div class="future-value">{item["p12"]}%</div></div>'
        '</div>'
        f'<div class="future-reason"><b>판단근거</b><br>{reasons}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_future_probability_summary(data):
    items = future_probability_list(data)
    if not items:
        card("🔮 미래확률", "미래확률 계산 데이터가 부족합니다.")
        return
    render_future_probability_card(items[0], "🔮 미래확률 1순위")

def render_future_probability_ranking(data):
    items = future_probability_list(data)
    if not items:
        return
    st.markdown('<div class="future-card"><div class="future-title">🔮 보유종목 미래확률 전체</div>', unsafe_allow_html=True)
    for idx, x in enumerate(items, start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        row = (
            '<div class="future-row">'
            '<div class="future-row-head">'
            f'<div class="future-name">{medal} {x["name"]}</div>'
            f'<div class="future-score">12개월 {x["p12"]}%</div>'
            '</div>'
            f'<div class="future-meta">3개월 {x["p3"]}% · 6개월 {x["p6"]}% · 신뢰도 {x["confidence"]}%<br>{x["action"]}</div>'
            '</div>'
        )
        st.markdown(row, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



# V99-1: 종목 브리핑 엔진 + 종목검색 복귀
def stock_briefing_data(name, result=None, data=None):
    n = norm(name)
    if result is None:
        result = None
        try:
            p, src = fetch_price(n)
            result = {"price": p, "src": src, "rate": 0, "change_rate": None}
        except Exception:
            result = {"price": fallback_price(n), "src": "기본값", "rate": 0, "change_rate": None}

    sec = sector(n)
    price = result.get("price") if result else None
    rate = float(result.get("rate", 0) or 0) if result else 0

    stock_s = 50
    supply_s = 50
    timing_s = 50
    future_12 = 50
    target = None
    value_s = 50
    now_weight = 0
    target_weight = target_sector_weights().get(sec, 10) if "target_sector_weights" in globals() else 10

    try:
        if data:
            _, _, _, _, weights, rows = metrics(data)
            now_weight = float(weights.get(sec, 0) or 0)
            for rn, q, a, r in rows:
                if norm(rn) == n:
                    result = result or r
                    stock_s = int(stock_score(n, q, a, r, weights, target_return(data)))
                    try:
                        sp = estimate_supply_score(n, r)
                        supply_s = int(sp.get("score", 50))
                    except Exception:
                        pass
                    break
    except Exception:
        pass

    try:
        if "safe_timing_score" in globals():
            t = safe_timing_score(n, result)
            timing_s = int(t.get("score", 50))
            timing_level = t.get("level", "🟠 관망")
        elif "buy_timing_analysis" in globals():
            t = buy_timing_analysis(n, result, data)
            timing_s = int(t.get("score", 50))
            timing_level = t.get("level", "🟠 관망")
        else:
            timing_level = "🟠 관망"
    except Exception:
        timing_level = "🟠 관망"

    try:
        if "future_probability_score" in globals():
            f = future_probability_score(n, result, data)
            future_12 = int(f.get("p12", 50))
            future_6 = int(f.get("p6", 50))
        else:
            future_6 = 50
    except Exception:
        future_6 = 50

    try:
        if "target_price_plan" in globals():
            target = target_price_plan(n, result, data)
    except Exception:
        target = None

    try:
        if "value_dividend_score" in globals():
            v = value_dividend_score(n, result)
            value_s = int(v.get("score", 50))
    except Exception:
        pass

    total = int(stock_s * 0.22 + supply_s * 0.15 + timing_s * 0.23 + future_12 * 0.25 + value_s * 0.15)

    reasons = []
    if stock_s >= 68:
        reasons.append(f"종목점수 {stock_s}점으로 기본 체력은 양호합니다.")
    elif stock_s <= 52:
        reasons.append(f"종목점수 {stock_s}점으로 단독 매수 근거는 약합니다.")
    else:
        reasons.append(f"종목점수 {stock_s}점으로 보유 관찰권입니다.")

    if timing_s >= 70:
        reasons.append(f"매수타이밍 {timing_s}점으로 분할 접근 가능권입니다.")
    elif timing_s <= 50:
        reasons.append(f"매수타이밍 {timing_s}점으로 추매는 신중합니다.")

    if future_12 >= 70:
        reasons.append(f"12개월 기대확률 {future_12}%로 중장기 기대값이 우세합니다.")
    elif future_12 <= 55:
        reasons.append(f"12개월 기대확률 {future_12}%로 기대값 확인이 필요합니다.")

    if now_weight > target_weight + 8:
        reasons.append(f"현재 {sec} 비중 {now_weight:.1f}%로 권장 {target_weight:.1f}%보다 높습니다.")
        balance_msg = "비중 과다 · 추가매수보다 유지/분산 우선"
    elif now_weight < target_weight - 8:
        reasons.append(f"현재 {sec} 비중 {now_weight:.1f}%로 권장 {target_weight:.1f}%보다 낮습니다.")
        balance_msg = "비중 부족 · 보강 후보"
    else:
        balance_msg = "비중 적정권"

    if total >= 75 and now_weight <= target_weight + 8:
        decision = "🟢 분할매수 가능"
        one_line = "점수와 기대값이 우세하고 비중 부담도 크지 않아 분할매수 후보입니다."
    elif total >= 65:
        decision = "🟡 보유 우선"
        one_line = "좋은 후보지만 지금은 무리한 추매보다 보유와 분할 확인이 적절합니다."
    elif total >= 52:
        decision = "🟠 관망"
        one_line = "확실한 매수 우위는 부족해 관망하면서 추가 근거를 확인합니다."
    else:
        decision = "🔴 추매 보류"
        one_line = "현재 기준에서는 추가매수보다 리스크 점검이 우선입니다."

    if now_weight > target_weight + 10 and "매수" in decision:
        decision = "🟡 보유 우선"
        one_line = "종목 자체는 나쁘지 않지만 포트 비중이 높아 추가매수는 신중합니다."

    return {
        "name": n, "sector": sec, "price": price, "rate": rate,
        "stock_s": stock_s, "supply_s": supply_s, "timing_s": timing_s,
        "future_6": future_6, "future_12": future_12, "value_s": value_s,
        "total": total, "decision": decision, "one_line": one_line,
        "balance_msg": balance_msg, "now_weight": now_weight, "target_weight": target_weight,
        "target": target, "reasons": reasons[:5],
    }

def render_stock_briefing(name, result=None, data=None, title_prefix="📌 종목 브리핑"):
    b = stock_briefing_data(name, result, data)
    target = b.get("target")
    if target:
        target_txt = f'매수구간 {won(target["buy_low"])}~{won(target["buy_high"])}<br>1차 {won(target["target1"])} · 2차 {won(target["target2"])} · 손절 {won(target["stop"])}'
    else:
        target_txt = "목표가 데이터 준비중"

    reasons = "<br>".join([f"① {x}" for x in b.get("reasons", [])])
    price_txt = won(b["price"]) if b.get("price") else "확인중"

    html = (
        '<div class="brief-card">'
        f'<div class="brief-title">{title_prefix} · {b["name"]}</div>'
        f'<div class="brief-sub">{b["sector"]} · 종합 {b["total"]}점 · {b["decision"]}</div>'
        f'<div class="brief-action">한줄요약: {b["one_line"]}<br>밸런스 판단: {b["balance_msg"]}</div>'
        '<div class="brief-grid">'
        f'<div class="brief-box"><div class="brief-label">현재가</div><div class="brief-value">{price_txt}</div></div>'
        f'<div class="brief-box"><div class="brief-label">현재/권장 비중</div><div class="brief-value">{b["now_weight"]:.1f}% / {b["target_weight"]:.1f}%</div></div>'
        f'<div class="brief-box"><div class="brief-label">종목·수급</div><div class="brief-value">종목 {b["stock_s"]}점 · 수급 {b["supply_s"]}점</div></div>'
        f'<div class="brief-box"><div class="brief-label">타이밍·미래확률</div><div class="brief-value">타이밍 {b["timing_s"]}점 · 12개월 {b["future_12"]}%</div></div>'
        f'<div class="brief-box"><div class="brief-label">가치점수</div><div class="brief-value">{b["value_s"]}점</div></div>'
        f'<div class="brief-box"><div class="brief-label">목표/손절</div><div class="brief-value">{target_txt}</div></div>'
        '</div>'
        f'<div class="brief-reason"><b>판단근거</b><br>{reasons}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_holdings_briefing_accordion(data):
    st.markdown('<div class="brief-card"><div class="brief-title">📌 내 종목 상세 브리핑</div><div class="brief-sub">종목명을 눌러 사야 할지, 보유할지, 비중이 적절한지 확인합니다.</div></div>', unsafe_allow_html=True)
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        rows = []
    for n, q, a, r in rows:
        with st.expander(f"📌 {n} 브리핑 보기", expanded=False):
            render_stock_briefing(n, r, data, title_prefix="내 종목 판단")

def render_stock_search_briefing(data):
    st.markdown('<div class="brief-card"><div class="brief-title">🔎 종목 검색 브리핑</div><div class="brief-sub">보유종목이 아니어도 검색해서 매수타이밍·목표가·미래확률을 한 번에 확인합니다.</div></div>', unsafe_allow_html=True)

    candidates = []
    try:
        for h in data.get("holdings", []):
            n = norm(h.get("name", ""))
            if n and n not in candidates:
                candidates.append(n)
    except Exception:
        pass

    base_names = ["대한전선", "제룡전기", "에스피시스템스", "ACE AI반도체 TOP3", "KODEX 미국S&P500", "TIGER 미국S&P500", "LG디스플레이", "엔비디아", "QQQ", "SOXX"]
    for n in base_names:
        if n not in candidates:
            candidates.append(n)

    c1, c2 = st.columns([2, 1])
    with c1:
        typed = st.text_input("종목명 직접 입력", value="", placeholder="예: 대한전선, 엔비디아, QQQ")
    with c2:
        selected = st.selectbox("빠른 선택", ["선택안함"] + candidates)

    target_name = norm(typed.strip()) if typed.strip() else (selected if selected != "선택안함" else "")
    if target_name:
        render_stock_briefing(target_name, None, data, title_prefix="검색 종목 판단")



def render_home_best_briefing(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
        best = None
        best_score = -1
        for n, q, a, r in rows:
            b = stock_briefing_data(n, r, data)
            if b["total"] > best_score:
                best = (n, r)
                best_score = b["total"]
        if best:
            render_stock_briefing(best[0], best[1], data, title_prefix="오늘 핵심 종목")
    except Exception:
        pass



# V100-1: AI 소장 의견 엔진
def ai_boss_opinion_data(data):
    try:
        total_buy, total_value, profit, rate, weights, rows = metrics(data)
    except Exception:
        return None

    warnings = []
    opinions = []

    try:
        targets = target_sector_weights() if "target_sector_weights" in globals() else {"미국지수":30, "반도체":25, "전력/자동화":25, "디스플레이":8, "기타":12}
    except Exception:
        targets = {"미국지수":30, "반도체":25, "전력/자동화":25, "디스플레이":8, "기타":12}

    overweight = []
    underweight = []
    for sec, now in weights.items():
        tgt = targets.get(sec, 10)
        gap = float(now or 0) - float(tgt or 0)
        if gap >= 8:
            overweight.append((sec, now, tgt, gap))
        elif gap <= -8:
            underweight.append((sec, now, tgt, gap))

    overweight = sorted(overweight, key=lambda x: x[3], reverse=True)
    underweight = sorted(underweight, key=lambda x: x[3])

    if overweight:
        sec, now, tgt, gap = overweight[0]
        warnings.append(f"{sec} 비중이 {now:.1f}%로 권장 {tgt:.1f}%보다 높습니다.")
    if underweight:
        sec, now, tgt, gap = underweight[0]
        opinions.append(f"{sec} 비중이 부족해 보강 후보를 우선 확인합니다.")

    briefs = []
    for n, q, a, r in rows:
        try:
            if "stock_briefing_data" in globals():
                b = stock_briefing_data(n, r, data)
            else:
                st_s = int(stock_score(n, q, a, r, weights, target_return(data)))
                b = {"name": n, "total": st_s, "decision": "🟡 보유", "one_line": "보유 관찰", "sector": sector(n), "now_weight": weights.get(sector(n), 0), "target_weight": targets.get(sector(n), 10)}
            briefs.append(b)
        except Exception:
            pass

    briefs = sorted(briefs, key=lambda x: x.get("total", 0), reverse=True)

    rb = None
    try:
        if "rebalance_analysis" in globals():
            rb = rebalance_analysis(data)
    except Exception:
        rb = None

    add_candidate = None
    hold_candidate = None
    caution_candidate = None

    for b in briefs:
        nw = float(b.get("now_weight", 0) or 0)
        tw = float(b.get("target_weight", 10) or 10)
        if not add_candidate and b.get("total", 0) >= 65 and nw <= tw + 8:
            add_candidate = b
        if not hold_candidate and b.get("total", 0) >= 55:
            hold_candidate = b
        if not caution_candidate and (b.get("total", 0) < 55 or nw > tw + 10):
            caution_candidate = b

    if rb and rb.get("add_top"):
        rb_add_name = rb["add_top"]["name"]
        for b in briefs:
            if norm(b["name"]) == norm(rb_add_name):
                add_candidate = b
                break

    if add_candidate:
        today_action = f'{add_candidate["name"]} 소액/분할매수 후보'
        action_reason = add_candidate.get("one_line", "포트 기준 보강 후보입니다.")
    elif hold_candidate:
        today_action = f'{hold_candidate["name"]} 보유 유지'
        action_reason = "뚜렷한 추가매수 후보보다 보유 관찰이 적절합니다."
    else:
        today_action = "오늘은 관망 우선"
        action_reason = "강한 매수 우위 후보가 뚜렷하지 않습니다."

    health = 60
    try:
        if float(rate or 0) >= 0:
            health += 6
    except Exception:
        pass
    if overweight:
        health -= min(15, int(overweight[0][3]))
    if underweight:
        health -= 3
    if briefs:
        health += max(0, int((briefs[0].get("total", 60) - 60) * 0.25))
    health = max(0, min(100, int(health)))

    if health >= 75:
        status = "🟢 양호"
    elif health >= 60:
        status = "🟡 보통"
    elif health >= 45:
        status = "🟠 주의"
    else:
        status = "🔴 위험"

    summary_lines = [
        f"현재 포트 상태는 {health}점, {status}입니다.",
        f"오늘 핵심 행동은 {today_action}입니다."
    ]
    if warnings:
        summary_lines.insert(1, warnings[0])
    if opinions:
        summary_lines.insert(1, opinions[0])

    return {
        "health": health,
        "status": status,
        "today_action": today_action,
        "action_reason": action_reason,
        "add": add_candidate,
        "hold": hold_candidate,
        "caution": caution_candidate,
        "warnings": warnings,
        "summary": summary_lines,
    }

def render_ai_boss_opinion(data):
    d = ai_boss_opinion_data(data)
    if not d:
        card("👷 AI 소장 의견", "포트폴리오 데이터를 확인하지 못했습니다.")
        return

    add = d.get("add")
    hold = d.get("hold")
    caution = d.get("caution")

    add_txt = add["name"] if add else "없음"
    hold_txt = hold["name"] if hold else "없음"
    caution_txt = caution["name"] if caution else "없음"

    summary_html = "<br>".join([f"• {x}" for x in d.get("summary", [])])
    warning_html = ""
    if d.get("warnings"):
        warning_html = '<div class="boss-warning">' + "<br>".join([f"⚠️ {x}" for x in d["warnings"][:3]]) + "</div>"

    html = (
        '<div class="boss-card">'
        '<div class="boss-kicker">👷 AI 소장 의견</div>'
        f'<div class="boss-title">오늘은 “{d["today_action"]}” 쪽으로 보는 게 좋겠습니다.</div>'
        f'<div class="boss-summary">{summary_html}</div>'
        f'<div class="boss-action">최종 행동: {d["today_action"]}<br>이유: {d["action_reason"]}</div>'
        '<div class="boss-grid">'
        f'<div class="boss-box"><div class="boss-label">포트 상태</div><div class="boss-value">{d["health"]}점 · {d["status"]}</div></div>'
        f'<div class="boss-box"><div class="boss-label">추가매수 후보</div><div class="boss-value">{add_txt}</div></div>'
        f'<div class="boss-box"><div class="boss-label">보유 후보</div><div class="boss-value">{hold_txt}</div></div>'
        f'<div class="boss-box"><div class="boss-label">주의 후보</div><div class="boss-value">{caution_txt}</div></div>'
        '</div>'
        '<div class="boss-reason">※ AI 소장 의견은 종목점수, 매수타이밍, 미래확률, 목표가, 리밸런싱 결과를 종합한 행동 요약입니다.</div>'
        f'{warning_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)



# V101-1: 투자금 배분 엔진
def allocation_candidates(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []

    items = []
    try:
        targets = target_sector_weights()
    except Exception:
        targets = {"미국지수":30, "반도체":25, "전력/자동화":25, "디스플레이":8, "기타":12}

    for n, q, a, r in rows:
        try:
            if "stock_briefing_data" in globals():
                b = stock_briefing_data(n, r, data)
                score = int(b.get("total", 50))
                reason = b.get("one_line", "")
                now_w = float(b.get("now_weight", 0) or 0)
                tgt_w = float(b.get("target_weight", 10) or 10)
            else:
                sec0 = sector(n)
                score = int(stock_score(n, q, a, r, weights, target_return(data)))
                reason = "종목점수 기준 배분 후보"
                now_w = float(weights.get(sec0, 0) or 0)
                tgt_w = float(targets.get(sec0, 10) or 10)

            sec = sector(n)
            bonus = 0
            if now_w < tgt_w - 8:
                bonus += 18
            elif now_w > tgt_w + 8:
                bonus -= 18

            rate_v = float(r.get("rate", 0) or 0) if r else 0
            if rate_v >= 20:
                bonus -= 8
            elif -7 <= rate_v <= 7:
                bonus += 5

            if sec == "미국지수":
                bonus += 10

            final = max(0, min(100, int(score + bonus)))
            if final >= 45:
                items.append({"name": norm(n), "score": final, "base_score": score, "sector": sec,
                              "now_weight": now_w, "target_weight": tgt_w, "rate": rate_v, "reason": reason})
        except Exception:
            pass

    return sorted(items, key=lambda x: x.get("score", 0), reverse=True)

def allocation_plan(data, amount):
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0

    if amount <= 0:
        return {"amount": 0, "items": [], "cash": 0, "message": "투자 가능금액을 입력하세요."}

    candidates = allocation_candidates(data)
    if not candidates:
        return {"amount": amount, "items": [], "cash": amount, "message": "배분 후보가 없습니다."}

    selected = candidates[:4]
    total_score = sum(max(1, x["score"]) for x in selected)

    raw = []
    for x in selected:
        pct = max(5, int(round(x["score"] / total_score * 90)))
        y = dict(x)
        y["pct"] = pct
        raw.append(y)

    pct_sum = sum(x["pct"] for x in raw)
    if pct_sum > 0:
        for x in raw:
            x["pct"] = int(round(x["pct"] / pct_sum * 90))

    diff = 90 - sum(x["pct"] for x in raw)
    if raw:
        raw[0]["pct"] += diff

    items = []
    for x in raw:
        money = int(amount * x["pct"] / 100)
        money = int(money // 1000 * 1000)
        y = dict(x)
        y["money"] = money
        items.append(y)

    used = sum(x["money"] for x in items)
    cash = max(0, amount - used)

    return {"amount": amount, "items": items, "cash": cash, "message": "수량이 아니라 금액/비중 기준 배분입니다."}

def render_investment_allocation(data):
    st.markdown(
        '<div class="alloc-card"><div class="alloc-title">💰 투자금 배분 엔진</div><div class="alloc-sub">이번에 넣을 금액을 입력하면, 현재 포트 기준으로 어디에 몇 % 넣을지 제안합니다.</div></div>',
        unsafe_allow_html=True
    )

    amount = st.number_input("이번 투자 가능금액", min_value=0, max_value=100000000, value=300000, step=10000, format="%d", key="alloc_amount_v101")
    plan = allocation_plan(data, amount)

    if not plan["items"]:
        card("💰 배분 결과", plan.get("message", "배분 후보가 없습니다."))
        return

    top = plan["items"][0]
    top_html = (
        '<div class="alloc-card">'
        '<div class="alloc-title">💰 이번 투자금 배분 제안</div>'
        f'<div class="alloc-sub">총 투자금 {won(plan["amount"])} 기준</div>'
        f'<div class="alloc-action">1순위: {top["name"]} · {top["pct"]}% · {won(top["money"])}<br>현금 유지: {won(plan["cash"])}</div>'
    )
    st.markdown(top_html, unsafe_allow_html=True)

    for x in plan["items"]:
        row = (
            '<div class="alloc-row">'
            '<div style="flex:1">'
            f'<div class="alloc-name">{x["name"]}</div>'
            f'<div class="alloc-meta">{x["sector"]} · 배분점수 {x["score"]}점<br>현재/권장 비중 {x["now_weight"]:.1f}% / {x["target_weight"]:.1f}%<br>{x["reason"]}</div>'
            f'<div class="alloc-bar"><div class="alloc-fill" style="width:{x["pct"]}%"></div></div>'
            '</div>'
            f'<div class="alloc-money">{x["pct"]}%<br>{won(x["money"])}</div>'
            '</div>'
        )
        st.markdown(row, unsafe_allow_html=True)

    st.markdown(f'<div class="alloc-note">※ {plan["message"]}<br>※ 실제 주문 전 현재가와 계좌 상황을 다시 확인하세요.</div></div>', unsafe_allow_html=True)



# V102-1: 뉴스 결론화 안전버전
def news_conclusion_items(data=None):
    items = []
    raw_text = ""
    try:
        if isinstance(data, dict):
            for key in ["news", "news_items", "market_news", "rss_news", "cached_news"]:
                vals = data.get(key)
                if isinstance(vals, list):
                    for v in vals[:30]:
                        if isinstance(v, dict):
                            raw_text += " " + str(v.get("title", "")) + " " + str(v.get("summary", ""))
                        else:
                            raw_text += " " + str(v)
                elif isinstance(vals, str):
                    raw_text += " " + vals
    except Exception:
        raw_text = ""

    positive_terms = ["AI", "HBM", "반도체", "데이터센터", "전력", "전력망", "변압기", "로봇", "자동화", "수주", "실적", "증설"]
    caution_terms = ["금리", "환율", "유가", "전쟁", "과열", "차익", "급락", "인플레이션", "매파"]

    pos_hit = [t for t in positive_terms if t.lower() in raw_text.lower()]
    cau_hit = [t for t in caution_terms if t.lower() in raw_text.lower()]

    if pos_hit:
        main = " · ".join(pos_hit[:3])
        items.append(("🟢 긍정", f"{main} 관련 흐름 감지", "성장 테마는 우호적이지만 추격매수보다 종목별 타이밍 확인이 필요합니다."))
    if cau_hit:
        main = " · ".join(cau_hit[:3])
        items.append(("🟠 주의", f"{main} 변수 감지", "시장 전체 비중 확대보다 분할 접근이 유리합니다."))

    if len(items) < 3:
        try:
            _, _, _, _, weights, rows = metrics(data)
            top_secs = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            if top_secs:
                sec, w = top_secs[0]
                items.append(("🧭 포트 기준", f"{sec} 비중 {w:.1f}%", "뉴스보다 현재 포트 비중과 AI 소장 의견을 우선합니다."))
        except Exception:
            pass

    defaults = [
        ("🔎 발굴 관점", "대장주 뉴스보다 핵심부품·협력사·저평가 수혜주 추적", "앞으로 숨은 수혜주 엔진의 핵심 데이터로 사용합니다."),
        ("⚠️ 원칙", "뉴스가 많이 나온 종목은 이미 선반영됐을 수 있음", "좋은 회사보다 좋은 진입시점을 우선합니다."),
        ("📰 결론", "뉴스 원문은 숨기고 결론만 사용", "오늘 행동 판단에 필요한 핵심만 남깁니다."),
    ]
    for d in defaults:
        if len(items) >= 3:
            break
        items.append(d)
    return items[:3]

def render_news_conclusion(data):
    items = news_conclusion_items(data)
    html = (
        '<div class="newscon-card">'
        '<div class="newscon-title">📰 AI 시장결론</div>'
        '<div class="newscon-sub">뉴스 원문은 내부 판단 재료로만 사용하고, 화면에는 결론만 짧게 표시합니다.</div>'
        '<div class="newscon-action">오늘 기준: 뉴스보다 행동 결론 우선 · 추격매수 금지 · 포트 기준 판단</div>'
    )
    for head, body, detail in items:
        html += (
            '<div class="newscon-row">'
            f'<div class="newscon-head">{head} · {body}</div>'
            f'<div class="newscon-body">{detail}</div>'
            '</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)



# V103-1: 토스 포트 수량 자동갱신 1차
def toss_known_names():
    return [
        "에스피시스템스",
        "제룡전기",
        "ACE AI반도체TOP3+",
        "ACE AI반도체 TOP3+",
        "ACE AI반도체 TOP3",
        "ACE 반도체 TOP3",
        "KODEX 미국S&P500",
        "KODEX 미국 S&P500",
        "TIGER 미국S&P500",
        "TIGER 미국 S&P500",
        "LG디스플레이",
    ]

def normalize_toss_name(name):
    n = str(name).strip()
    mapping = {
        "ACE AI반도체TOP3+": "ACE AI반도체 TOP3",
        "ACE AI반도체 TOP3+": "ACE AI반도체 TOP3",
        "ACE 반도체 TOP3": "ACE AI반도체 TOP3",
        "KODEX 미국 S&P500": "KODEX 미국S&P500",
        "TIGER 미국 S&P500": "TIGER 미국S&P500",
    }
    return norm(mapping.get(n, n))

def parse_toss_portfolio_text(raw):
    raw = str(raw or "")
    if not raw.strip():
        return []

    lines = [x.strip() for x in raw.replace("\t", " ").splitlines() if x.strip()]
    joined = "\n".join(lines)
    results = []

    for name in toss_known_names():
        idx = joined.find(name)
        if idx == -1:
            continue
        segment = joined[idx: idx + 160]
        m = re.search(r"(\d+(?:\.\d+)?)\s*주", segment)
        if m:
            qty = float(m.group(1))
            results.append({"name": normalize_toss_name(name), "qty": qty, "source": "토스 텍스트"})

    if not results:
        for name in toss_known_names():
            pat = re.escape(name) + r"[\s\S]{0,100}?(\d+(?:\.\d+)?)\s*주"
            m = re.search(pat, raw)
            if m:
                results.append({"name": normalize_toss_name(name), "qty": float(m.group(1)), "source": "토스 텍스트"})

    unique = {}
    for r in results:
        unique[r["name"]] = r
    return list(unique.values())

def apply_toss_sync(data, parsed):
    if not parsed:
        return []

    data.setdefault("holdings", [])
    data.setdefault("sync_history", [])

    changes = []
    for item in parsed:
        name = norm(item.get("name", ""))
        qty = float(item.get("qty", 0) or 0)
        if not name or qty < 0:
            continue

        found = False
        for h in data["holdings"]:
            if norm(h.get("name", "")) == name:
                old_qty = float(h.get("qty", 0) or 0)
                old_avg = float(h.get("avg", 0) or 0)
                h["name"] = name
                h["qty"] = qty
                h["avg"] = old_avg
                changes.append({"name": name, "old_qty": old_qty, "new_qty": qty, "avg": old_avg, "type": "update"})
                found = True
                break

        if not found:
            try:
                price, src = fetch_price(name)
                avg = float(price or 0)
            except Exception:
                avg = float(fallback_price(name) or 0)
            data["holdings"].append({"name": name, "qty": qty, "avg": avg})
            changes.append({"name": name, "old_qty": 0, "new_qty": qty, "avg": avg, "type": "new"})

    if changes:
        data["sync_history"].append({
            "type": "toss_portfolio_sync",
            "count": len(changes),
            "changes": changes[-20:],
        })
        save_data(data)

    return changes

def render_toss_portfolio_sync(data):
    if not can_write_db():
        read_only_notice()
        return
    st.markdown(
        '<div class="toss-card"><div class="toss-title">📷 토스 포트 총 보유수량 맞추기</div><div class="toss-sub">토스 보유화면의 종목명·현재 총 보유수량을 붙여넣으면 기존 보유수량을 그 숫자로 맞춥니다. 평단은 기존 값을 보존합니다.</div><div class="toss-action">주의: 입력값은 오늘 매수수량이 아니라 현재 총 보유수량입니다.</div></div>',
        unsafe_allow_html=True
    )

    up = st.file_uploader("토스 화면 캡처 업로드(참고용)", type=["png", "jpg", "jpeg"], key="toss_capture_v103")
    if up is not None:
        st.image(up, caption="업로드한 토스 화면", use_container_width=True)
        st.caption("현재 버전은 이미지 자동 OCR 대신 아래 텍스트 붙여넣기를 사용합니다. 다음 단계에서 OCR/PDF 인식으로 확장합니다.")

    sample = "에스피시스템스 60주\n제룡전기 13주\nACE AI반도체TOP3+ 22주\nKODEX 미국S&P500 41주\nLG디스플레이 20주"
    raw = st.text_area("토스 보유 텍스트 붙여넣기", value="", placeholder=sample, height=140, key="toss_text_v103")

    parsed = parse_toss_portfolio_text(raw)
    if parsed:
        st.markdown('<div class="toss-card"><div class="toss-title">🔎 인식 결과</div>', unsafe_allow_html=True)
        for p in parsed:
            st.markdown(
                f'<div class="toss-row"><div class="toss-name">{p["name"]}</div><div class="toss-meta">수량 {p["qty"]:g}주</div></div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("토스 현재 총 보유수량으로 맞추기", use_container_width=True, key="apply_toss_sync_v103"):
        changes = apply_toss_sync(data, parsed)
        if changes:
            st.success(f"{len(changes)}개 종목을 현재 총 보유수량 기준으로 맞췄습니다. 평단은 기존 값을 유지했습니다.")
            st.rerun()
        else:
            st.warning("인식된 종목이 없습니다. 예시처럼 '종목명 00주' 형태로 붙여넣어 주세요.")



# V104-1: 공급망 발굴 DB 1차
def supply_chain_db():
    return {
        "AI/HBM": {
            "leaders": ["엔비디아", "SK하이닉스", "삼성전자", "AMD", "브로드컴"],
            "theme_reason": "AI 연산 수요와 HBM 메모리 수요 증가",
            "beneficiaries": [
                {"name": "하나마이크론", "role": "HBM/반도체 후공정", "link": 92, "growth": 82, "price": 72, "note": "하이닉스·삼성 HBM 확대 시 후공정 수혜 후보"},
                {"name": "ISC", "role": "반도체 테스트 소켓", "link": 88, "growth": 80, "price": 66, "note": "AI 반도체 검사 수요 증가 수혜 후보"},
                {"name": "한미반도체", "role": "HBM 장비", "link": 95, "growth": 84, "price": 55, "note": "HBM 장비 대장급이나 가격 부담 확인 필요"},
                {"name": "이수페타시스", "role": "AI 서버 PCB", "link": 86, "growth": 78, "price": 62, "note": "AI 서버 확대 시 고다층 PCB 수혜 후보"},
            ],
        },
        "AI 데이터센터 전력": {
            "leaders": ["엔비디아", "마이크로소프트", "아마존", "구글", "메타"],
            "theme_reason": "AI 데이터센터 증설에 따른 전력·변압기·전력망 투자 증가",
            "beneficiaries": [
                {"name": "제룡전기", "role": "변압기/전력설비", "link": 90, "growth": 83, "price": 68, "note": "데이터센터 전력 수요 증가 간접 수혜 후보"},
                {"name": "대한전선", "role": "전력 케이블", "link": 84, "growth": 75, "price": 70, "note": "전력망 투자 확대 수혜 후보"},
                {"name": "LS ELECTRIC", "role": "전력기기/자동화", "link": 88, "growth": 80, "price": 58, "note": "전력 인프라 대형 수혜주이나 가격 부담 확인"},
                {"name": "효성중공업", "role": "초고압 변압기", "link": 87, "growth": 79, "price": 55, "note": "전력망 투자 수혜이나 이미 선반영 여부 확인"},
            ],
        },
        "로봇/자동화": {
            "leaders": ["테슬라", "현대차", "삼성전자", "두산"],
            "theme_reason": "휴머노이드·스마트팩토리·자동화 투자 확대",
            "beneficiaries": [
                {"name": "에스피시스템스", "role": "자동화/로봇 시스템", "link": 84, "growth": 76, "price": 74, "note": "스마트팩토리·자동화 확대 수혜 후보"},
                {"name": "레인보우로보틱스", "role": "로봇 플랫폼", "link": 86, "growth": 82, "price": 52, "note": "로봇 대표주이나 가격 부담 확인"},
                {"name": "두산로보틱스", "role": "협동로봇", "link": 82, "growth": 78, "price": 55, "note": "협동로봇 성장 수혜 후보"},
            ],
        },
        "원전/전력안보": {
            "leaders": ["두산에너빌리티", "한전KPS", "한국전력"],
            "theme_reason": "AI 전력수요와 에너지 안보에 따른 원전·전력 인프라 관심 증가",
            "beneficiaries": [
                {"name": "비에이치아이", "role": "발전설비", "link": 78, "growth": 72, "price": 68, "note": "원전·발전설비 투자 수혜 후보"},
                {"name": "우진", "role": "원전 계측", "link": 74, "growth": 70, "price": 70, "note": "원전 가동·정비 관련 수혜 후보"},
            ],
        },
    }

def supply_discovery_score(item, theme_name="", data=None):
    link = int(item.get("link", 50))
    growth = int(item.get("growth", 50))
    price = int(item.get("price", 50))
    timing_bonus = 0
    future_bonus = 0
    owned_bonus = 0

    try:
        if data and "stock_briefing_data" in globals():
            b = stock_briefing_data(item["name"], None, data)
            timing_bonus = int((b.get("timing_s", 50) - 50) * 0.15)
            future_bonus = int((b.get("future_12", 50) - 50) * 0.18)
            if b.get("now_weight", 0) > 0:
                owned_bonus = 3
    except Exception:
        pass

    score = int(link * 0.35 + growth * 0.30 + price * 0.20 + 60 * 0.15 + timing_bonus + future_bonus + owned_bonus)
    return max(0, min(100, score))

def supply_discovery_candidates(data=None):
    db = supply_chain_db()
    out = []
    for theme, info in db.items():
        for item in info.get("beneficiaries", []):
            score = supply_discovery_score(item, theme, data)
            x = dict(item)
            x["theme"] = theme
            x["leaders"] = info.get("leaders", [])
            x["theme_reason"] = info.get("theme_reason", "")
            x["score"] = score
            out.append(x)
    return sorted(out, key=lambda x: x.get("score", 0), reverse=True)

def render_supply_chain_discovery(data):
    items = supply_discovery_candidates(data)
    if not items:
        return

    top = items[0]
    leader_txt = " · ".join(top.get("leaders", [])[:3])
    html = (
        '<div class="supply-card">'
        '<div class="supply-title">🔥 오늘의 공급망 발굴 후보</div>'
        '<div class="supply-sub">대장주를 직접 사는 대신, 그 뒤에 있는 핵심부품·협력사·저평가 수혜주를 찾는 1차 엔진입니다.</div>'
        f'<div class="supply-action">1순위: {top["name"]} · 발굴점수 {top["score"]}점<br>대장주 체인: {leader_txt}<br>수혜 논리: {top["role"]}</div>'
    )

    for idx, x in enumerate(items[:5], start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        leaders = " · ".join(x.get("leaders", [])[:3])
        tags = (
            f'<span class="supply-tag">연결 {x.get("link",0)}점</span>'
            f'<span class="supply-tag">성장 {x.get("growth",0)}점</span>'
            f'<span class="supply-tag">가격 {x.get("price",0)}점</span>'
        )
        html += (
            '<div class="supply-row">'
            '<div class="supply-head">'
            f'<div class="supply-name">{medal} {x["name"]}</div>'
            f'<div class="supply-score">{x["score"]}점</div>'
            '</div>'
            f'<div class="supply-meta">테마: {x["theme"]}<br>대장주: {leaders}<br>역할: {x["role"]}<br>{x["note"]}<br>{tags}</div>'
            '</div>'
        )

    html += '<div class="supply-sub">※ V104-1은 공급망 DB 1차 버전입니다. 다음 단계에서 뉴스·수주·실적 데이터를 더 강하게 연결합니다.</div></div>'
    st.markdown(html, unsafe_allow_html=True)



# V105-2: DB 상태 확인 / 동기화 점검판
# V105-3: DB 안정화 / 지문 강화 / PC-휴대폰 비교판
def short_hash(text, length=10):
    try:
        return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:length].upper()
    except Exception:
        return "HASHERR"

def stable_holdings_raw(data):
    try:
        rows = []
        for h in data.get("holdings", []):
            rows.append({
                "name": norm(h.get("name", "")),
                "qty": float(sf(h.get("qty"))),
                "avg": float(sf(h.get("avg"))),
            })
        rows = sorted(rows, key=lambda x: x["name"])
        return json.dumps(rows, ensure_ascii=False, sort_keys=True)
    except Exception:
        return "[]"

def db_file_info():
    info = {}
    p = PORTFOLIO_FILE
    try:
        resolved = p.resolve()
        info["portfolio_path"] = str(resolved)
        info["portfolio_exists"] = p.exists()
        info["portfolio_size"] = p.stat().st_size if p.exists() else 0
        if p.exists():
            mt_kst = datetime.utcfromtimestamp(p.stat().st_mtime) + timedelta(hours=9)
            info["portfolio_mtime"] = mt_kst.strftime("%Y-%m-%d %H:%M:%S")
            raw = p.read_text(encoding="utf-8")
            info["file_hash"] = short_hash(raw, 12)
        else:
            info["portfolio_mtime"] = "없음"
            info["file_hash"] = "파일없음"
    except Exception as e:
        info["portfolio_path"] = str(p)
        info["portfolio_exists"] = False
        info["portfolio_size"] = 0
        info["portfolio_mtime"] = "확인불가"
        info["file_hash"] = f"ERR-{short_hash(e, 6)}"
    try:
        info["cwd"] = str(Path.cwd().resolve())
    except Exception:
        info["cwd"] = str(Path.cwd())
    info["env"] = app_env_label()
    return info

def db_fingerprint(data):
    try:
        s = asset_summary(data)
        holdings = data.get("holdings", [])
        holdings_raw = stable_holdings_raw(data)
        calc_raw = json.dumps({
            "buy_principal": round(float(s.get("buy_principal", 0)), 2),
            "stock_value": round(float(s.get("stock_value", 0)), 2),
            "profit": round(float(s.get("profit", 0)), 2),
            "rate": round(float(s.get("rate", 0)), 4),
            "count": len(holdings),
        }, ensure_ascii=False, sort_keys=True)
        legacy_checksum = sum(ord(c) for c in holdings_raw) % 1000000
        return {
            "holdings_count": len(holdings),
            "buy_principal": s.get("buy_principal", s.get("principal", 0)),
            "stock_value": s.get("stock_value", 0),
            "profit": s.get("profit", 0),
            "rate": s.get("rate", 0),
            "checksum": legacy_checksum,
            "holdings_hash": short_hash(holdings_raw, 12),
            "calc_hash": short_hash(calc_raw, 12),
            "full_hash": short_hash(holdings_raw + "|" + calc_raw, 12),
        }
    except Exception as e:
        return {
            "holdings_count": 0,
            "buy_principal": 0,
            "stock_value": 0,
            "profit": 0,
            "rate": 0,
            "checksum": 0,
            "holdings_hash": f"ERR-{short_hash(e, 6)}",
            "calc_hash": "ERR",
            "full_hash": "ERR",
        }

def export_portfolio_text(data):
    try:
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        return ""

def apply_imported_portfolio(raw):
    if not can_write_db():
        return False, "현재 환경은 조회전용입니다. DB 가져오기는 PC 모체에서만 가능합니다."
    try:
        incoming = json.loads(str(raw or "").strip())
        if not isinstance(incoming, dict) or "holdings" not in incoming:
            return False, "holdings가 있는 portfolio JSON이 아닙니다."
        incoming = normalize_profile(incoming)
        save_data(incoming)
        return True, "가져오기 완료"
    except Exception as e:
        return False, f"가져오기 실패: {e}"


def read_text_if_exists(path):
    try:
        path = Path(path)
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""

def github_json_sync_package(data):
    """PC Master DB를 GitHub data 폴더에 그대로 올릴 수 있는 zip으로 만듭니다."""
    try:
        history_text = read_text_if_exists(HISTORY_FILE) or "[]"
        sell_text = read_text_if_exists(SELL_FILE) or "[]"
        portfolio_text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        readme = (
            "Stock Compass V112-3 GitHub JSON Sync\n"
            "======================================\n\n"
            "목적: PC Master DB를 GitHub 저장소의 data 폴더에 반영하여 "
            "Streamlit Cloud/휴대폰이 같은 JSON을 읽게 만드는 업로드용 패키지입니다.\n\n"
            "사용 순서:\n"
            "1) 이 zip을 PC에서 다운로드합니다.\n"
            "2) 압축을 풀면 data/portfolio.json, data/history.json, data/sell_records.json 이 있습니다.\n"
            "3) GitHub 저장소 stock-news-bot 의 data 폴더에 같은 이름으로 덮어씁니다.\n"
            "4) commit 후 Streamlit Cloud가 재배포되면 휴대폰은 같은 Cloud JSON을 읽습니다.\n\n"
            "주의: 휴대폰/Cloud에서는 수정하지 않고 조회 전용으로 사용합니다.\n"
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("data/portfolio.json", portfolio_text)
            z.writestr("data/history.json", history_text)
            z.writestr("data/sell_records.json", sell_text)
            z.writestr("README_GITHUB_JSON_SYNC.txt", readme)
        bio.seek(0)
        return bio.getvalue()
    except Exception:
        return b""

def render_github_json_sync_panel(data):
    info = db_file_info()
    fp = db_fingerprint(data)
    is_master = can_write_db()
    status = "🖥️ PC Master 업로드 준비 가능" if is_master else "📱 모바일/Cloud 조회전용 · 업로드 패키지 생성 잠금"
    action_text = (
        "PC에서 DB를 수정한 뒤 이 패키지를 받아 GitHub 저장소의 data 폴더에 덮어쓰면 됩니다. "
        "휴대폰은 GitHub/Streamlit Cloud에 올라간 JSON을 조회합니다."
        if is_master else
        "현재 환경은 조회전용입니다. DB 수정과 GitHub 업로드 패키지 생성은 PC Master에서만 진행하세요."
    )
    st.markdown(
        f'<div class="db-card"><div class="db-title">🔗 V112-3 GitHub JSON Sync</div>'
        f'<div class="db-sub">PC를 원본 DB로 고정하고, GitHub 저장소의 <b>data/*.json</b>을 모바일 조회용 Cloud DB처럼 사용하는 방식입니다.</div>'
        f'<div class="db-action">현재상태: {status}<br>{action_text}</div>'
        f'<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">원본 기준</div><div class="db-value">PC Master</div></div>'
        f'<div class="db-box"><div class="db-label">모바일 기준</div><div class="db-value">GitHub data JSON 조회</div></div>'
        f'<div class="db-box"><div class="db-label">보유종목 수</div><div class="db-value">{fp.get("holdings_count", 0)}개</div></div>'
        f'<div class="db-box"><div class="db-label">총 매입원금</div><div class="db-value">{won(fp.get("buy_principal", 0))}</div></div>'
        f'<div class="db-box"><div class="db-label">통합지문</div><div class="db-value">{fp.get("full_hash", "-")}</div></div>'
        f'<div class="db-box"><div class="db-label">파일지문</div><div class="db-value">{info.get("file_hash", "-")}</div></div>'
        f'</div>'
        f'<div class="db-sub"><b>업로드 위치</b><br>GitHub 저장소 <b>stock-news-bot/data/</b><br><br>'
        f'<b>덮어쓸 파일</b><br>portfolio.json / history.json / sell_records.json</div></div>',
        unsafe_allow_html=True
    )
    if is_master:
        pkg = github_json_sync_package(data)
        st.download_button(
            "📦 GitHub 업로드용 DB 패키지 다운로드",
            data=pkg,
            file_name="StockCompass_GitHub_JSON_DB_package.zip",
            mime="application/zip",
            use_container_width=True,
            key="github_json_sync_package_download_v1123",
        )
        with st.expander("📋 GitHub에 올릴 portfolio.json 미리보기", expanded=False):
            st.text_area("portfolio.json", value=export_portfolio_text(data), height=260, key="github_json_portfolio_preview_v1123")
    else:
        st.info("모바일/Cloud에서는 DB를 수정하지 않습니다. PC에서 패키지를 만들어 GitHub에 반영하세요.")

def render_db_sync_panel(data):
    info = db_file_info()
    fp = db_fingerprint(data)
    st.markdown(
        f'<div class="db-card"><div class="db-title">🔁 PC ↔ 휴대폰 DB 맞추기</div>'
        f'<div class="db-sub">현재 실행환경: <b>{info.get("env", "-")}</b><br>'
        f'현재 기준시간(KST): {now_label()}<br>'
        f'통합지문: <b>{fp.get("full_hash", "-")}</b><br>'
        f'파일지문: <b>{info.get("file_hash", "-")}</b></div>'
        f'<div class="db-action">컴퓨터가 맞으면 컴퓨터의 아래 DB 내용을 복사해서 휴대폰 프로필 탭의 가져오기에 붙여넣으면 됩니다.</div></div>',
        unsafe_allow_html=True
    )
    with st.expander("📤 현재 DB 내보내기 / 📥 다른 기기 DB 가져오기", expanded=False):
        st.text_area("현재 DB 복사용", value=export_portfolio_text(data), height=220, key="db_export_v10542")
        raw = st.text_area("여기에 맞는 기기의 DB를 붙여넣기", value="", height=160, key="db_import_v10542")
        if st.button("📥 붙여넣은 DB로 현재 기기 맞추기", use_container_width=True, key="db_import_btn_v10542"):
            ok, msg = apply_imported_portfolio(raw)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def render_db_structure_panel(data):
    info = db_file_info()
    meta = data.get("_meta", {}) if isinstance(data, dict) else {}
    html = (
        '<div class="db-card">'
        '<div class="db-title">🏗️ DB 구조 정리 V112-3A</div>'
        '<div class="db-sub">이번 버전은 Cloud DB 전환 전 PC/모바일 DB 진실 확인 단계입니다.</div>'
        '<div class="db-action">현재 단계: DB VERIFY ONLY · PC/모바일 실제 경로와 지문 확인</div>'
        '<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">저장 통로</div><div class="db-value">save_data → write_db_json</div></div>'
        f'<div class="db-box"><div class="db-label">읽기 통로</div><div class="db-value">load_data → load_json</div></div>'
        f'<div class="db-box"><div class="db-label">자동 백업</div><div class="db-value">data/backup 폴더</div></div>'
        f'<div class="db-box"><div class="db-label">현재 DB 모드</div><div class="db-value">{DB_MODE}</div></div>'
        f'<div class="db-box"><div class="db-label">현재 권한</div><div class="db-value">{db_role_label()}</div></div>'
        f'<div class="db-box"><div class="db-label">Cloud 경로</div><div class="db-value">{CLOUD_DB_ROOT or "미설정"}</div></div>'
        f'<div class="db-box"><div class="db-label">마지막 저장환경</div><div class="db-value">{meta.get("saved_env", "아직 저장기록 없음")}</div></div>'
        f'<div class="db-box"><div class="db-label">마지막 저장시간</div><div class="db-value">{meta.get("last_saved_kst", info.get("portfolio_mtime", "-"))}</div></div>'
        '</div>'
        '<div class="db-sub">※ V112-3A는 자동 동기화가 아니라 진단 전용입니다. PC/휴대폰 지문이 다른지 먼저 확인합니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def db_diagnostic_text(data):
    info = db_file_info()
    fp = db_fingerprint(data)
    lines = [
        f"앱버전: {APP_TITLE}",
        f"DB스키마: {DB_SCHEMA_VERSION}",
        f"실행환경: {info.get('env','-')}",
        f"현재권한: {db_role_label()}",
        f"실제 DB경로: {info.get('portfolio_path','-')}",
        f"현재 실행위치: {info.get('cwd','-')}",
        f"보유종목수: {fp.get('holdings_count','-')}",
        f"총매입원금: {won(fp.get('buy_principal',0))}",
        f"평가금액: {won(fp.get('stock_value',0))}",
        f"평가수익률: {fp.get('rate',0):.2f}%",
        f"보유종목지문: {fp.get('holdings_hash','-')}",
        f"계산결과지문: {fp.get('calc_hash','-')}",
        f"통합지문: {fp.get('full_hash','-')}",
        f"파일지문: {info.get('file_hash','-')}",
        f"마지막저장시간(KST): {info.get('portfolio_mtime','-')}",
        f"파일크기: {info.get('portfolio_size',0):,} byte",
        "동기화판정: V112-3은 PC Master DB를 GitHub JSON으로 배포하기 위한 준비 단계입니다.",
    ]
    return "\n".join(lines)


def render_db_truth_panel(data):
    info = db_file_info()
    fp = db_fingerprint(data)
    env = info.get("env", "-")
    if env == "PC/Local":
        location_judge = "🖥️ PC 로컬 DB를 읽는 중"
        truth_msg = "현재 화면은 PC 폴더의 data/portfolio.json 기준입니다. 휴대폰과 자동 동기화된 상태가 아닙니다."
    elif "Cloud" in env:
        location_judge = "☁️ Streamlit Cloud 서버 DB를 읽는 중"
        truth_msg = "현재 화면은 Streamlit Cloud 서버의 data/portfolio.json 기준입니다. PC Z드라이브 DB와 자동 동기화된 상태가 아닙니다."
    else:
        location_judge = "❓ 실행환경 확인 필요"
        truth_msg = "실행환경을 확정하지 못했습니다. 실제 DB 경로와 지문을 비교하세요."

    html = (
        '<div class="db-card">'
        '<div class="db-title">🧪 DB 진실 확인 V112-3A</div>'
        '<div class="db-sub">이 패널의 목적은 Cloud DB 전환 전, PC와 휴대폰이 실제로 어느 DB를 읽는지 확인하는 것입니다.</div>'
        f'<div class="db-action">판정: {location_judge}<br>{truth_msg}</div>'
        '<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">실행환경</div><div class="db-value">{env}</div></div>'
        f'<div class="db-box"><div class="db-label">현재권한</div><div class="db-value">{db_role_label()}</div></div>'
        f'<div class="db-box"><div class="db-label">보유종목 수</div><div class="db-value">{fp.get("holdings_count",0)}개</div></div>'
        f'<div class="db-box"><div class="db-label">총 매입원금</div><div class="db-value">{won(fp.get("buy_principal",0))}</div></div>'
        f'<div class="db-box"><div class="db-label">통합지문</div><div class="db-value">{fp.get("full_hash","-")}</div></div>'
        f'<div class="db-box"><div class="db-label">파일지문</div><div class="db-value">{info.get("file_hash","-")}</div></div>'
        f'<div class="db-box"><div class="db-label">마지막 저장시간</div><div class="db-value">{info.get("portfolio_mtime","-")}</div></div>'
        f'<div class="db-box"><div class="db-label">DB 파일크기</div><div class="db-value">{info.get("portfolio_size",0):,} byte</div></div>'
        '</div>'
        f'<div class="db-sub"><b>실제 읽은 DB 경로</b><br>{info.get("portfolio_path","-")}<br><br><b>비교 방법</b><br>PC와 휴대폰에서 통합지문·파일지문·총매입원금이 같으면 같은 DB입니다. 하나라도 다르면 서로 다른 DB입니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    with st.expander("📋 진단값 복사용", expanded=False):
        st.text_area("PC/휴대폰 비교용 진단값", value=db_diagnostic_text(data), height=300, key="db_truth_copy_v1123a")

def render_db_status(data, compact=False):
    info = db_file_info()
    fp = db_fingerprint(data)

    if compact:
        st.markdown(
            f'<div class="db-card">'
            f'<div class="db-title">🧩 DB 간단 지문</div>'
            f'<div class="db-sub">PC와 휴대폰에서 아래 3개가 같으면 같은 DB를 보고 있는 것입니다.</div>'
            f'<div class="db-dark-text">보유 {fp["holdings_count"]}개 · 매입 {won(fp["buy_principal"])} · 통합지문 {fp["full_hash"]}</div>'
            f'<div class="db-sub">스키마 {DB_SCHEMA_VERSION} · 환경 {info.get("env", "-")} · 권한 {db_role_label()}<br>현재(KST) {now_label()}<br>저장시간(KST) {info["portfolio_mtime"]} · 파일지문 {info["file_hash"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        return

    html = (
        '<div class="db-card">'
        '<div class="db-title">🧩 DB 상태 확인 V112-3A</div>'
        '<div class="db-sub">PC와 휴대폰 수익률이 다르면 아래 값이 같은지 비교하세요. 총 매입원금은 현재가와 무관하므로 이 값이 다르면 수량/평단 DB가 다른 것입니다.</div>'
        '<div class="db-action">비교 기준: 실제 읽은 경로 · 보유종목 수 · 총 매입원금 · 보유종목 지문 · 계산결과 지문 · 파일 지문</div>'
        '<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">앱 버전</div><div class="db-value">{APP_TITLE}</div></div>'
        f'<div class="db-box"><div class="db-label">DB 스키마</div><div class="db-value">{DB_SCHEMA_VERSION}</div></div>'
        f'<div class="db-box"><div class="db-label">DB 모드</div><div class="db-value">{DB_MODE}</div></div>'
        f'<div class="db-box"><div class="db-label">DB 역할</div><div class="db-value">{DB_ROLE}</div></div>'
        f'<div class="db-box"><div class="db-label">현재 권한</div><div class="db-value">{db_role_label()}</div></div>'
        f'<div class="db-box"><div class="db-label">실행환경</div><div class="db-value">{info.get("env", "-")}</div></div>'
        f'<div class="db-box"><div class="db-label">현재시간(KST)</div><div class="db-value">{now_label()}</div></div>'
        f'<div class="db-box"><div class="db-label">portfolio.json 존재</div><div class="db-value">{"있음" if info["portfolio_exists"] else "없음"}</div></div>'
        f'<div class="db-box"><div class="db-label">보유종목 수</div><div class="db-value">{fp["holdings_count"]}개</div></div>'
        f'<div class="db-box"><div class="db-label">총 매입원금</div><div class="db-value">{won(fp["buy_principal"])}</div></div>'
        f'<div class="db-box"><div class="db-label">현재 평가금액</div><div class="db-value">{won(fp["stock_value"])}</div></div>'
        f'<div class="db-box"><div class="db-label">평가수익률</div><div class="db-value">{fp["rate"]:.2f}%</div></div>'
        f'<div class="db-box"><div class="db-label">보유종목 지문</div><div class="db-value">{fp["holdings_hash"]}</div></div>'
        f'<div class="db-box"><div class="db-label">계산결과 지문</div><div class="db-value">{fp["calc_hash"]}</div></div>'
        f'<div class="db-box"><div class="db-label">통합 지문</div><div class="db-value">{fp["full_hash"]}</div></div>'
        f'<div class="db-box"><div class="db-label">파일 지문</div><div class="db-value">{info["file_hash"]}</div></div>'
        f'<div class="db-box"><div class="db-label">마지막 저장시간</div><div class="db-value">{info["portfolio_mtime"]}</div></div>'
        f'<div class="db-box"><div class="db-label">DB 파일크기</div><div class="db-value">{info["portfolio_size"]:,} byte</div></div>'
        '</div>'
        f'<div class="db-sub"><b>실제 읽은 DB 경로</b><br>{info["portfolio_path"]}<br><br><b>현재 실행 위치</b><br>{info["cwd"]}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    st.markdown('<div class="db-card"><div class="db-title">📦 보유종목 DB 내용</div><div class="db-sub">PC/휴대폰에서 아래 수량과 평단이 같은지 비교하세요.</div>', unsafe_allow_html=True)
    try:
        for h in data.get("holdings", []):
            n = norm(h.get("name", ""))
            q = sf(h.get("qty"))
            a = sf(h.get("avg"))
            st.markdown(
                f'<div class="db-row"><div class="db-name">{n}</div><div class="db-meta">수량 {q:g}주 · 평단 {won(a)} · 매입금액 {won(q*a)}</div></div>',
                unsafe_allow_html=True
            )
    except Exception:
        st.markdown('<div class="db-row"><div class="db-meta">보유종목 정보를 읽지 못했습니다.</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    render_db_sync_panel(data)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 DB 새로고침", use_container_width=True, key="db_refresh_v1053"):
            st.rerun()
    with c2:
        if st.button("💾 현재 DB 강제저장", use_container_width=True, key="db_save_v1053"):
            save_data(data)
            st.success("현재 보유종목 DB를 강제 저장했습니다.")
            st.rerun()

    with st.expander("🧪 원인 판단법", expanded=False):
        st.markdown("""
- PC와 휴대폰의 **앱 버전은 같은데 총 매입원금이 다르면 DB가 다릅니다.**
- **보유종목 지문**이 다르면 종목명/수량/평단 중 하나가 다릅니다.
- **계산결과 지문**이 다르면 매입원금/평가금액/수익률 계산 결과가 다릅니다.
- **파일 지문**과 **마지막 저장시간**이 다르면 실제 저장파일 자체가 다릅니다.
- 같은 Streamlit Cloud 주소인데도 다르면, 브라우저 캐시/세션 또는 배포 인스턴스 저장소 차이 가능성이 있습니다.
""")

def search_stock_options(data=None):
    names = []
    try:
        for h in (data or {}).get("holdings", []):
            n = norm(h.get("name", ""))
            if n and n not in names:
                names.append(n)
    except Exception:
        pass
    extra = [
        "하나마이크론", "ISC", "한미반도체", "이수페타시스",
        "제룡전기", "대한전선", "LS ELECTRIC", "효성중공업",
        "에스피시스템스", "레인보우로보틱스", "두산로보틱스",
        "삼성전자", "SK하이닉스", "엔비디아",
        "ACE AI반도체 TOP3", "KODEX 미국S&P500", "TIGER 미국S&P500", "LG디스플레이"
    ]
    for n in extra:
        nn = norm(n)
        if nn not in names:
            names.append(nn)
    return names

def company_summary_text(name):
    n = norm(name)
    mapping = {
        "하나마이크론": "반도체 후공정/패키징 관련 기업으로, HBM·AI 반도체 확대 시 후공정 수요 증가 관점에서 확인할 후보입니다.",
        "ISC": "반도체 테스트 소켓 관련 기업으로, AI 반도체와 고성능 칩 검사 수요 증가와 연결됩니다.",
        "한미반도체": "HBM 장비 대표 기업군입니다. 성장성은 강하지만 이미 선반영된 가격 부담 여부를 함께 봐야 합니다.",
        "이수페타시스": "AI 서버용 고다층 PCB 수요와 연결되는 기업으로, 데이터센터 투자 확대의 간접 수혜 후보입니다.",
        "제룡전기": "변압기/전력설비 관련 기업으로, AI 데이터센터 전력 수요 증가와 연결됩니다.",
        "대한전선": "전력 케이블 관련 기업으로, 전력망 투자 확대와 데이터센터 전력 인프라 수혜 후보입니다.",
        "LS ELECTRIC": "전력기기·자동화 대표 기업군입니다. 전력 인프라 확대 수혜는 있으나 가격 부담도 함께 봐야 합니다.",
        "효성중공업": "초고압 변압기와 전력 인프라 관련 기업으로, 글로벌 전력망 투자와 연결됩니다.",
        "에스피시스템스": "자동화/로봇 시스템 관련 기업으로, 스마트팩토리·로봇 자동화 확대 수혜 후보입니다.",
        "LG디스플레이": "디스플레이 패널 기업으로, OLED 업황 회복과 수익성 개선 여부 확인이 중요합니다.",
        "SK하이닉스": "HBM 대장주입니다. 직접 투자보다는 후공정·장비·소재 협력사 발굴의 기준점으로도 활용됩니다.",
        "삼성전자": "반도체·AI·메모리·파운드리의 대형 축입니다. 공급망 발굴의 기준점으로 활용됩니다.",
        "엔비디아": "AI 반도체 대장주입니다. 직접 매수보다 AI 서버·PCB·전력·냉각·메모리 공급망 발굴의 기준점입니다.",
    }
    if n in mapping:
        return mapping[n]
    if "S&P500" in n:
        return "미국 대표지수 ETF입니다. 개별 종목 발굴보다 장기 방어력과 분산 안정성 역할을 합니다."
    if "반도체" in n:
        return "반도체 테마 ETF/종목입니다. AI·HBM 성장성과 반도체 비중 과다 여부를 함께 봐야 합니다."
    return "기업 개요 데이터는 1차 기본값입니다. 다음 버전에서 실제 데이터와 연결할 예정입니다."

def supply_chain_summary_for_stock(name):
    n = norm(name)
    try:
        db = supply_chain_db()
    except Exception:
        db = {}
    hits = []
    for theme, info in db.items():
        for item in info.get("beneficiaries", []):
            if norm(item.get("name", "")) == n:
                leaders = " · ".join(info.get("leaders", [])[:4])
                chain = f'{leaders} → {theme} → {item.get("role","수혜")}'
                hits.append((theme, chain, item.get("note", ""), item.get("link", 0), item.get("growth", 0), item.get("price", 0)))
    if hits:
        html = ""
        for theme, chain, note, link, growth, price in hits:
            html += f"테마: <b>{theme}</b><br>수혜체인: {chain}<br>근거: {note}<br>연결강도 {link}점 · 성장성 {growth}점 · 가격매력 {price}점<br><br>"
        return html.strip()
    if n in ["SK하이닉스", "삼성전자", "엔비디아"]:
        return f"{n}은 대장주 성격입니다. 이 종목 자체보다 후공정·PCB·전력·장비·소재 협력사를 발굴하는 기준점으로 사용합니다."
    return "공급망 DB에 직접 연결된 항목은 아직 없습니다. 다음 버전에서 2500종목 필터링과 함께 확장합니다."

def search_news_summary_for_stock(name, data=None):
    n = norm(name)
    try:
        all_news = rss_items()
        keys = holding_news_keywords(n) if "holding_news_keywords" in globals() else [n]
        matched = []
        for source, title, link in all_news:
            score = news_matches(title, keys) if "news_matches" in globals() else (1 if n.lower() in str(title).lower() else 0)
            if score:
                impact, _ = news_impact(title) if "news_impact" in globals() else ("⚪ 중립", 0)
                matched.append((impact, source, title, link))
        if matched:
            pos = sum(1 for x in matched if "긍정" in x[0])
            neg = sum(1 for x in matched if "부정" in x[0])
            neu = len(matched) - pos - neg
            mood = "🟢 긍정 우세" if pos > neg else ("🔴 부정 확인" if neg > pos else "⚪ 중립")
            return f"{mood}<br>관련 뉴스 {len(matched)}건 · 긍정 {pos}건 · 부정 {neg}건 · 중립 {neu}건<br>뉴스 원문은 숨기고 결론만 판단 재료로 사용합니다."
    except Exception:
        pass
    return "현재 RSS 기준 직접 관련 뉴스는 많지 않습니다. 뉴스보다 공급망·차트·포트 비중을 함께 봅니다."

def search_ai_final_comment(name, data=None):
    try:
        b = stock_briefing_data(name, None, data)
        return f'{b["decision"]}<br>{b["one_line"]}<br>현재/권장 비중 {b["now_weight"]:.1f}% / {b["target_weight"]:.1f}%'
    except Exception:
        sec = sector(name)
        if sec == "반도체":
            return "반도체 성장성은 좋지만 선반영과 포트 비중을 함께 확인해야 합니다."
        if sec == "전력/자동화":
            return "AI 데이터센터·전력 인프라 수혜 관점에서 관심 유지 후보입니다."
        if sec == "미국지수":
            return "장기 적립식 기준 안정성 보강 후보입니다."
        return "아직 명확한 최종 의견 데이터가 부족합니다. 관망 기준으로 확인합니다."


# V108-4: 검색 즉시판정 엔진
# 검색탭의 목표를 "이 종목 지금 사도 돼?"에 답하는 화면으로 바꿉니다.
def search_decision_data(name, data=None):
    n = norm(name)
    now = now_label()
    try:
        b = stock_briefing_data(n, None, data)
    except Exception:
        b = {"name": n, "sector": sector(n), "price": fallback_price(n), "total": 50, "decision": "🟠 관망", "one_line": "기본 데이터 기준 관찰이 필요합니다.", "future_12": 50, "timing_s": 50, "stock_s": 50, "value_s": 50, "now_weight": 0, "target_weight": 10}

    detail = fetch_price_detail(n)
    price = detail.get("price") or b.get("price") or fallback_price(n) or 0
    change_rate = detail.get("change_rate")
    change_text = detail.get("change_text", "등락률 확인불가")
    volume = detail.get("volume")
    volume_txt = detail.get("volume_text", "확인불가")
    data_src = detail.get("src", "기본값")
    fetched_at = detail.get("fetched_at", now)
    total = int(max(0, min(100, b.get("total", 50))))
    upside = int(max(5, min(90, b.get("future_12", 50))))
    downside = int(max(10, min(90, 100 - total)))
    timing = int(max(0, min(100, b.get("timing_s", 50))))
    sec = b.get("sector", sector(n))

    try:
        mq = move_quality_judgement(n, {"price": price, "rate": 0}, data)
        mq_label = mq.get("label", "⚪ 중립 흐름")
        mq_action = mq.get("action", "보유 점검")
    except Exception:
        mq_label, mq_action = "⚪ 중립 흐름", "보유 점검"

    # 발굴엔진 후보 여부 확인
    discovery_rank = "후보권 밖"
    discovery_score = 0
    try:
        for idx, x in enumerate(supply_discovery_candidates(data), start=1):
            if norm(x.get("name", "")) == n:
                discovery_rank = f"TOP{idx} 후보" if idx <= 10 else f"{idx}위 후보"
                discovery_score = int(x.get("score", 0))
                break
    except Exception:
        pass

    good = []
    bad = []
    if sec == "미국지수":
        good.append("장기 분산·방어 자산 역할")
        bad.append("단기 급등 수익률은 제한적일 수 있음")
    elif sec == "반도체":
        good.append("AI/HBM 성장 테마 연결")
        bad.append("선반영·대장주 조정 동조 위험")
    elif sec == "전력/자동화":
        good.append("AI 데이터센터 전력·자동화 수혜 체인")
        bad.append("수주 기대 선반영 여부 확인 필요")
    elif sec == "디스플레이":
        good.append("업황 회복 시 반등 여지")
        bad.append("회복 확인 전 변동성 큼")
    else:
        good.append("관심 후보로 기본 분석 가능")
        bad.append("아직 내부 데이터 연결이 부족함")

    if discovery_score >= 70:
        good.append(f"발굴엔진 {discovery_score}점 · {discovery_rank}")
    elif discovery_score:
        bad.append(f"발굴엔진 {discovery_score}점으로 TOP권은 아님")

    try:
        nw = float(b.get("now_weight", 0) or 0)
        tw = float(b.get("target_weight", 10) or 10)
        if nw > tw + 8:
            bad.append(f"현재 포트 비중 {nw:.1f}%로 권장 {tw:.1f}%보다 높음")
        elif nw < tw - 8:
            good.append(f"현재 포트 비중 {nw:.1f}%로 보강 여지")
    except Exception:
        pass

    if change_rate is not None:
        if change_rate >= 3:
            bad.append(f"오늘 {change_text} 상승으로 단기 추격 위험 확인")
        elif change_rate <= -3:
            good.append(f"오늘 {change_text} 하락 · 좋은하락 여부 확인 구간")
        else:
            good.append(f"오늘 등락률 {change_text} · 과열/급락 극단은 아님")
    else:
        bad.append("실시간 등락률 확인불가 · 장중 데이터 재확인 필요")

    if volume:
        good.append(f"거래량 {volume_txt} 확인")
    else:
        bad.append("거래량 확인불가 · 수급 판단 제한")

    if total >= 75:
        verdict = "🟢 분할매수 가능"
        today = "소액·분할 접근 가능"
    elif total >= 65:
        verdict = "🟡 보유/관심 우선"
        today = "무리한 추격보다 눌림 확인"
    elif total >= 52:
        verdict = "🟠 관망"
        today = "지금은 확인 후 접근"
    else:
        verdict = "🔴 매수 보류"
        today = "추가매수 금지 · 원인 확인"

    return {
        "name": n, "time": now, "price": price, "sector": sec,
        "change_rate": change_rate, "change_text": change_text, "volume": volume, "volume_text": volume_txt, "data_src": data_src, "fetched_at": fetched_at,
        "total": total, "verdict": verdict, "today": today,
        "upside": upside, "downside": downside, "timing": timing,
        "summary": b.get("one_line", "검색 즉시판정 결과입니다."),
        "mq_label": mq_label, "mq_action": mq_action,
        "discovery_rank": discovery_rank, "discovery_score": discovery_score,
        "good": good[:4], "bad": bad[:4]
    }

def search_report_grade(total, discovery_score=0):
    try:
        total = int(total or 0)
        discovery_score = int(discovery_score or 0)
    except Exception:
        total, discovery_score = 50, 0
    blended = int(total * 0.75 + discovery_score * 0.25) if discovery_score else total
    if blended >= 82:
        return "S", "강한 후보"
    if blended >= 72:
        return "A", "우선 검토"
    if blended >= 62:
        return "B", "관심 유지"
    if blended >= 50:
        return "C", "관망"
    return "D", "보류"

def render_search_decision_panel(name, data=None):
    d = search_decision_data(name, data)
    grade, grade_text = search_report_grade(d.get("total"), d.get("discovery_score"))
    confidence = max(45, min(92, int(d.get("total", 50) * 0.55 + d.get("timing", 50) * 0.20 + d.get("upside", 50) * 0.25)))

    st.markdown(
        f'<div class="search-report">'
        f'<div class="search-kicker">🔎 V111 실시간 데이터 리포트 · {d["time"]}</div>'
        f'<div class="search-name">{d["name"]}</div>'
        f'<div class="search-score-big">{d["total"]}점</div>'
        f'<div class="search-verdict">최종행동: {d["verdict"]}<br>{d["today"]}</div>'
        f'<div class="search-report-grid">'
        f'<div class="search-report-box"><div class="search-report-label">현재가</div><div class="search-report-value">{won(d["price"])}</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">오늘 등락률</div><div class="search-report-value">{d["change_text"]}</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">거래량</div><div class="search-report-value">{d["volume_text"]}</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">데이터 출처</div><div class="search-report-value">{d["data_src"]}</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">신뢰도</div><div class="search-report-value">{confidence}%</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">발굴등급</div><div class="search-report-value">{grade} · {grade_text}</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">발굴엔진</div><div class="search-report-value">{d["discovery_rank"]}</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">상승 기대</div><div class="search-report-value">{d["upside"]}%</div></div>'
        f'<div class="search-report-box"><div class="search-report-label">하락/선반영 위험</div><div class="search-report-value">{d["downside"]}%</div></div>'
        f'</div>'
        f'<div class="search-verdict">흐름판정: {d["mq_label"]}<br>흐름행동: {d["mq_action"]}<br>{d["summary"]}<br>실데이터 기준시각: {d["fetched_at"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    good = "<br>".join([f"✅ {x}" for x in d.get("good", [])]) or "✅ 특별한 강점 데이터는 추가 확인이 필요합니다."
    bad = "<br>".join([f"⚠️ {x}" for x in d.get("bad", [])]) or "⚠️ 뚜렷한 위험은 아직 크지 않습니다."
    st.markdown(
        f'<div class="search-point-card"><div class="search-point-grid"><div class="search-point-good"><b>좋은 점</b><br>{good}</div><div class="search-point-bad"><b>주의점</b><br>{bad}</div></div></div>',
        unsafe_allow_html=True
    )

def render_search_stock_detail(name, data):
    n = norm(name)
    if not n:
        return
    render_search_decision_panel(n, data)
    try:
        gd = good_bad_drop_engine(n, None, data)
        render_good_bad_drop_card(gd, "검색 종목 하락판단")
    except Exception:
        pass
    try:
        b = stock_briefing_data(n, None, data)
        final_line = f'{b["decision"]} · 종합 {b["total"]}점<br>{b["one_line"]}'
    except Exception:
        final_line = f'{n} 분석 준비중<br>기본 데이터 기준으로 확인합니다.'
    st.markdown(
        f'<div class="search-card"><div class="search-title">📂 {n} 상세 근거</div>'
        f'<div class="search-sub">위 결론의 세부 근거입니다. 필요한 항목만 펼쳐 확인합니다.</div>'
        f'<div class="search-final">AI 최종결론: {final_line}</div></div>',
        unsafe_allow_html=True
    )
    with st.expander("🏢 기업 개요", expanded=True):
        st.markdown(f'<div class="search-mini">{company_summary_text(n)}</div>', unsafe_allow_html=True)
    with st.expander("🔗 공급망 / 대장주 연결", expanded=False):
        st.markdown(f'<div class="search-mini">{supply_chain_summary_for_stock(n)}</div>', unsafe_allow_html=True)
    with st.expander("📰 뉴스 분석 결과", expanded=False):
        st.markdown(f'<div class="search-mini">{search_news_summary_for_stock(n, data)}</div>', unsafe_allow_html=True)
    with st.expander("📈 차트·매수타이밍", expanded=False):
        try:
            item = safe_timing_score(n, None)
            render_buy_timing_card_safe(item, "검색 종목 매수타이밍")
        except Exception:
            st.markdown('<div class="search-mini">차트/매수타이밍 데이터 준비중입니다.</div>', unsafe_allow_html=True)
    with st.expander("🎯 목표가 / 손절가", expanded=False):
        try:
            plan = target_price_plan(n, None, data)
            if plan:
                render_target_price_card(plan, "검색 종목 목표가")
            else:
                st.markdown('<div class="search-mini">목표가 데이터 준비중입니다.</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div class="search-mini">목표가 데이터 준비중입니다.</div>', unsafe_allow_html=True)
    with st.expander("🔮 미래 성장성", expanded=False):
        try:
            item = future_probability_score(n, None, data)
            render_future_probability_card(item, "검색 종목 미래확률")
        except Exception:
            st.markdown('<div class="search-mini">미래확률 데이터 준비중입니다.</div>', unsafe_allow_html=True)
    with st.expander("⚠️ 리스크 / 주의사항", expanded=False):
        sec = sector(n)
        risk = "뉴스가 많이 나온 종목은 이미 선반영됐을 수 있습니다. 추격매수보다 진입시점과 비중을 우선 확인하세요."
        if sec == "반도체":
            risk += "<br>반도체는 사이클과 대장주 조정에 같이 흔들릴 수 있습니다."
        elif sec == "전력/자동화":
            risk += "<br>전력/자동화는 수주 기대가 선반영됐는지 확인이 필요합니다."
        elif sec == "디스플레이":
            risk += "<br>디스플레이는 업황 회복 확인 전까지 변동성이 큽니다."
        st.markdown(f'<div class="search-mini">{risk}</div>', unsafe_allow_html=True)
    with st.expander("👷 AI 소장 최종 의견", expanded=True):
        st.markdown(f'<div class="search-mini">{search_ai_final_comment(n, data)}</div>', unsafe_allow_html=True)

def search(data):
    header()
    st.markdown(
        '<div class="search-card"><div class="search-title">🔎 이 종목 지금 사도 돼?</div>'
        '<div class="search-sub">실제 현재가·오늘 등락률·거래량·종합점수·최종행동을 리포트형으로 먼저 보여줍니다.</div></div>',
        unsafe_allow_html=True
    )
    options = search_stock_options(data)
    default_from_home = ""
    try:
        default_from_home = st.query_params.get("stock", "")
    except Exception:
        default_from_home = ""

    with st.form("search_form_v1054", clear_on_submit=False):
        q = st.text_input(
            "종목명 입력",
            value=str(default_from_home or ""),
            placeholder="예: 하나마이크론, 제룡전기, 대한전선",
            key="search_tab_input_v1054"
        ).strip()
        qlow = q.lower()
        if q:
            matches = [x for x in options if qlow in x.lower()]
            if norm(q) not in matches:
                matches = [norm(q)] + matches
        else:
            matches = options[:8]
        selected = st.selectbox("빠른 선택", ["직접입력/첫번째 결과"] + matches[:20], key="search_tab_select_v1054")
        submitted = st.form_submit_button("🔍 분석하기", use_container_width=True)

    target = ""
    if submitted or default_from_home:
        target = norm(q) if selected == "직접입력/첫번째 결과" else norm(selected)
        if not target and matches:
            target = norm(matches[0])

    if target:
        render_search_stock_detail(target, data)
    else:
        st.info("종목명을 입력한 뒤 엔터 또는 🔍 분석하기를 누르세요.")




# V106-2: 행동/위험/발굴 중심 + 가격흐름 판정
# 기존 엔진은 삭제하지 않고 결론 생성용 내부 엔진으로 유지합니다.
def render_v106_action_board(data):
    try:
        a = one_action(data)
        main = a.get("main", "오늘은 보유 유지")
        sub = str(a.get("sub", "무리한 매매보다 보유종목 점검이 우선입니다.")).replace("<br>", " · ")
        badge = a.get("badge", "관망")
        conf = a.get("conf", 70)
    except Exception:
        main, sub, badge, conf = "오늘은 보유 유지", "무리한 매매보다 보유종목 점검이 우선입니다.", "관망", 70

    st.markdown(
        f'<div class="action">'
        f'<div class="action-k">🎯 오늘의 행동</div>'
        f'<div class="action-main">{main}</div>'
        f'<div class="action-sub">신뢰도 {conf}%<br>{sub}</div>'
        f'<span class="badge">{badge}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("왜 이렇게 판단했나", expanded=False):
        try:
            if a.get("detail"):
                st.markdown(a.get("detail"), unsafe_allow_html=True)
        except Exception:
            pass
        try:
            d = ai_boss_opinion_data(data)
            if d:
                st.markdown(f'**AI 소장 판단:** {d.get("today_action", "관망")}')
                st.caption(d.get("action_reason", ""))
        except Exception:
            pass


def render_v106_risk_radar(data):
    """V107-1 위험레이더: 정상 종목은 숨기고, 지금 확인할 위험/주의만 보여줍니다."""
    try:
        items = emergency_items(data)
    except Exception:
        items = []

    rank = {"⚫ 긴급": 0, "🔴 위험": 1, "🟠 경고": 2, "🟡 주의": 3}
    show = []
    for x in items:
        level = str(x.get("level", ""))
        if level in rank:
            show.append(x)
    show = sorted(show, key=lambda x: rank.get(str(x.get("level", "")), 9))

    if not show:
        card("🚨 위험 레이더", "현재 바로 확인할 위험 종목은 없습니다.")
        return

    grouped = {"⚫ 긴급": [], "🔴 위험": [], "🟠 경고": [], "🟡 주의": []}
    for x in show:
        grouped[str(x.get("level", ""))].append(x)

    parts = []
    for level in ["⚫ 긴급", "🔴 위험", "🟠 경고", "🟡 주의"]:
        arr = grouped.get(level, [])
        if not arr:
            continue
        parts.append(f"<b>{level} {len(arr)}건</b>")
        for x in arr[:3]:
            parts.append(f'{x.get("title", "")}<br>{x.get("body", "")}')

    if len(show) > 8:
        parts.append(f"외 {len(show)-8}건은 투자기록 탭/고급분석에서 확인하세요.")

    card("🚨 위험 레이더", "<br><br>".join(parts))





# V109-2: 위험레이더 2.0 - 위험 원인 분류 + 최종행동 연결
# 정상 종목은 숨기고, 위험/주의가 있는 종목만 보여줍니다.
def risk_radar_v2_items(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        weights, rows = {}, []

    out = []
    top_names = discovery_top_names(data, 3) if "discovery_top_names" in globals() else []

    for n, q, a, r in rows:
        if not r:
            continue
        n = norm(n)
        sec = sector(n)
        rate = float(r.get("rate", 0) or 0)
        today = r.get("change_rate", None)
        sec_w = float((weights or {}).get(sec, 0) or 0)
        causes = []
        level_score = 0

        # 1) 손실경고
        if rate <= -20:
            causes.append(("🔴 손실확대", f"보유수익률 {rate:.2f}%로 손실 확대 구간입니다."))
            level_score += 35
        elif rate <= -10:
            causes.append(("🟠 손실경고", f"보유수익률 {rate:.2f}%로 경고 구간입니다."))
            level_score += 24
        elif rate <= -5:
            causes.append(("🟡 손실주의", f"보유수익률 {rate:.2f}%로 관찰이 필요합니다."))
            level_score += 12

        # 2) 오늘 급락
        try:
            if today is not None:
                today = float(today)
                if today <= -5:
                    causes.append(("🔴 오늘급락", f"오늘 등락률 {today:+.2f}%로 급락 신호입니다."))
                    level_score += 30
                elif today <= -3:
                    causes.append(("🟠 오늘하락", f"오늘 등락률 {today:+.2f}%로 하락 압력이 있습니다."))
                    level_score += 18
        except Exception:
            pass

        # 3) 섹터 비중 위험
        if sec_w >= 60:
            causes.append(("🔴 비중과다", f"{sec} 비중 {sec_w:.1f}%로 집중 위험이 큽니다."))
            level_score += 28
        elif sec_w >= 45:
            causes.append(("🟠 비중주의", f"{sec} 비중 {sec_w:.1f}%로 추가매수는 신중해야 합니다."))
            level_score += 14

        # 4) 좋은하락/나쁜하락 엔진 연결
        try:
            gd = good_bad_drop_engine(n, r, data, weights)
        except Exception:
            gd = {"label":"⚪ 흐름확인", "final_action":"보유", "drop_score":50, "confidence":60, "action_detail":"판단 데이터가 부족합니다.", "future12":50, "in_discovery": n in top_names}

        label = str(gd.get("label", ""))
        final_action = gd.get("final_action", "보유")
        if "나쁜하락" in label:
            causes.append(("🔴 나쁜하락", f"좋은하락 점수 {gd.get('drop_score', 0)}점 · {gd.get('action_detail', '')}"))
            level_score += 26
        elif "좋은하락" in label:
            causes.append(("🟢 좋은하락", f"위험은 있지만 최종행동은 {final_action} 후보입니다."))
            level_score -= 10
        elif "애매" in label:
            causes.append(("🟡 애매한하락", f"좋은하락 점수 {gd.get('drop_score', 0)}점 · 추매보다 확인이 필요합니다."))
            level_score += 8

        # 5) 미래확률 / 발굴등급
        future12 = int(gd.get("future12", 50) or 50)
        if future12 <= 52:
            causes.append(("🟠 미래확률저하", f"12개월 미래확률 {future12}%로 기대값이 약합니다."))
            level_score += 16
        if n not in top_names and final_action in ["관망", "비중축소"]:
            causes.append(("🟡 발굴등급제외", "발굴 TOP3에 포함되지 않아 추매 근거가 약합니다."))
            level_score += 7

        # 위험 원인이 없으면 숨김
        if not causes:
            continue

        if final_action == "추가매수":
            action_line = "추가매수 가능 · 단, 정해둔 금액 안에서만"
        elif final_action == "분할매수":
            action_line = "분할매수 후보 · 손실경고와 좋은하락을 함께 확인"
        elif final_action == "보유":
            action_line = "보유 유지 · 추매는 신호 확인 후"
        elif final_action == "관망":
            action_line = "관망 · 원인 확인 전 추매 금지"
        else:
            action_line = "비중축소 검토 · 손실 확대 방어 우선"

        # 좋은하락이 있으면 손실경고라도 '추매금지'로 단정하지 않음
        has_good_drop = any("좋은하락" in c[0] for c in causes)
        if has_good_drop and final_action in ["추가매수", "분할매수"]:
            level = "🟡 주의"
            title = f"{n} · 위험이지만 추매후보"
        elif level_score >= 55 or final_action == "비중축소":
            level = "🔴 위험"
            title = f"{n} · 위험 확인"
        elif level_score >= 30 or final_action == "관망":
            level = "🟠 경고"
            title = f"{n} · 경고 구간"
        else:
            level = "🟡 주의"
            title = f"{n} · 주의 구간"

        out.append({
            "name": n,
            "level": level,
            "title": title,
            "causes": causes[:6],
            "final_action": final_action,
            "action_line": action_line,
            "good_bad": gd,
            "score": max(0, min(100, int(level_score))),
        })

    rank = {"🔴 위험": 0, "🟠 경고": 1, "🟡 주의": 2}
    return sorted(out, key=lambda x: (rank.get(x.get("level", ""), 9), -x.get("score", 0)))


def render_v106_risk_radar(data):
    """V109-2 위험레이더 2.0: 위험 원인을 종류별로 보여주고 좋은하락이면 추매후보로 구분합니다."""
    items = risk_radar_v2_items(data)
    if not items:
        card("🚨 위험 레이더 2.0", "🟢 현재 바로 확인할 위험 종목은 없습니다.<br>정상 종목은 숨김 처리합니다.")
        return

    body = []
    for x in items[:5]:
        cause_html = "<br>".join([f"{tag} · {txt}" for tag, txt in x.get("causes", [])[:4]])
        gd = x.get("good_bad", {})
        body.append(
            f'<b>{x.get("level", "")} {x.get("name", "")}</b><br>'
            f'최종행동: <b>{x.get("action_line", "보유 점검")}</b><br>'
            f'하락판정: {gd.get("label", "흐름확인")} {gd.get("drop_score", 0)}점 · 신뢰도 {gd.get("confidence", 0)}%<br>'
            f'{cause_html}'
        )

    if len(items) > 5:
        body.append(f"외 {len(items)-5}건은 추천탭/내종목 상세에서 확인하세요.")
    card("🚨 위험 레이더 2.0", "<br><br>".join(body))

    with st.expander("위험 원인 상세보기", expanded=False):
        for x in items:
            gd = x.get("good_bad", {})
            st.markdown(f'**{x.get("name", "")} · {x.get("level", "")} · 최종행동 {x.get("final_action", "보유")}**')
            st.markdown(f'- 하락판정: {gd.get("label", "흐름확인")} {gd.get("drop_score", 0)}점 · 신뢰도 {gd.get("confidence", 0)}%')
            for tag, txt in x.get("causes", []):
                st.markdown(f'- {tag}: {txt}')
            st.markdown('---')


def render_risk_radar_v2_detail(data):
    items = risk_radar_v2_items(data)
    if not items:
        card("🚨 위험레이더 2.0", "현재 위험/주의 종목은 없습니다.")
        return
    st.markdown('<div class="brief-card"><div class="brief-title">🚨 위험레이더 2.0 상세</div><div class="brief-sub">경고 한 단어가 아니라 손실·비중·미래확률·좋은하락 여부를 분리해서 보여줍니다.</div></div>', unsafe_allow_html=True)
    for x in items:
        cause_html = "<br>".join([f"{tag} · {txt}" for tag, txt in x.get("causes", [])])
        gd = x.get("good_bad", {})
        st.markdown(
            f'<div class="brief-card">'
            f'<div class="brief-title">{x.get("level", "")} {x.get("name", "")}</div>'
            f'<div class="brief-sub">하락판정 {gd.get("label", "흐름확인")} · 좋은하락 점수 {gd.get("drop_score", 0)}점 · 신뢰도 {gd.get("confidence", 0)}%</div>'
            f'<div class="brief-action">최종행동: {x.get("action_line", "보유 점검")}</div>'
            f'<div class="brief-reason"><b>위험 원인</b><br>{cause_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# V107-2: 좋은 하락 / 나쁜 하락 판정 엔진 2차
# 가격 움직임만 보지 않고 내부 체력(품질/타이밍/미래확률/가치/뉴스/섹터)을 함께 봅니다.
def move_quality_judgement(name, r=None, data=None, weights=None):
    n = norm(name)
    sec = sector(n)
    rate = 0
    try:
        rate = float((r or {}).get("rate", 0) or 0)
    except Exception:
        rate = 0
    try:
        today_rate = (r or {}).get("change_rate", None)
        today_rate = None if today_rate is None else float(today_rate)
    except Exception:
        today_rate = None
    # V108-5: 오늘 등락률이 있으면 '오늘 하락/상승' 판단에 우선 사용합니다.
    # 없으면 기존처럼 보유수익률을 대용으로 사용합니다.
    signal_rate = today_rate if today_rate is not None else rate

    quality = 55
    timing = 55
    future12 = 55
    value_score = 55
    news_bias = 0
    news_label = "⚪ 뉴스 중립"
    reasons = []

    try:
        if data and weights is None:
            _, _, _, _, weights, _ = metrics(data)
    except Exception:
        weights = weights or {}

    try:
        if data and weights is not None:
            for rn, q, a, rr in metrics(data)[5]:
                if norm(rn) == n:
                    quality = int(stock_score(n, q, a, rr, weights, target_return(data)))
                    break
    except Exception:
        pass

    try:
        timing = int(safe_timing_score(n, r).get("score", timing))
    except Exception:
        pass

    try:
        future12 = int(future_probability_score(n, r, data).get("p12", future12))
    except Exception:
        pass

    try:
        value_score = int(value_dividend_score(n, r).get("score", value_score))
    except Exception:
        pass

    # 뉴스는 1차적으로 제목 키워드만 반영합니다. 실제 실적/수급 연결은 후속 버전에서 강화합니다.
    try:
        all_news = rss_items()
        keys = holding_news_keywords(n) if "holding_news_keywords" in globals() else [n]
        pos = neg = 0
        for source, title, link in all_news:
            if news_matches(title, keys) if "news_matches" in globals() else (n.lower() in str(title).lower()):
                impact, _ = news_impact(title) if "news_impact" in globals() else ("⚪ 중립", 0)
                if "긍정" in impact:
                    pos += 1
                elif "부정" in impact:
                    neg += 1
        if pos > neg:
            news_bias = min(8, (pos - neg) * 3)
            news_label = f"🟢 뉴스 긍정 {pos}건"
        elif neg > pos:
            news_bias = -min(10, (neg - pos) * 4)
            news_label = f"🔴 뉴스 부정 {neg}건"
        elif pos or neg:
            news_label = "⚪ 뉴스 혼조"
    except Exception:
        pass

    core = int(quality * 0.32 + timing * 0.23 + future12 * 0.25 + value_score * 0.15 + 55 * 0.05 + news_bias)

    if core >= 70:
        reasons.append("내부 체력이 양호해 단순 가격 하락을 곧바로 위험으로 보지 않습니다.")
    elif core <= 52:
        reasons.append("내부 체력이 약해 하락 시 방어와 원인 확인이 우선입니다.")
    else:
        reasons.append("내부 체력은 중립권이라 섣부른 추가매수보다 확인이 필요합니다.")

    if sec == "디스플레이":
        core -= 6
        reasons.append("디스플레이 업황 변동성을 보수적으로 반영했습니다.")
    elif sec == "미국지수":
        core += 6
        reasons.append("미국지수형 자산은 장기 적립식 안정성을 반영했습니다.")
    elif sec == "전력/자동화":
        core += 4
        reasons.append("전력/자동화 성장 테마를 일부 반영했습니다.")
    elif sec == "반도체":
        reasons.append("반도체는 성장성은 크지만 선반영/비중 부담을 함께 봅니다.")

    try:
        sw = float((weights or {}).get(sec, 0) or 0)
        if sw >= 55:
            core -= 6
            reasons.append(f"{sec} 비중이 {sw:.1f}%로 높아 추가매수 판단은 보수적으로 봅니다.")
        elif sw <= 18:
            core += 3
            reasons.append(f"{sec} 비중이 낮아 분산 보강 관점은 일부 긍정입니다.")
    except Exception:
        pass

    if news_bias > 0:
        reasons.append("관련 뉴스 흐름은 긍정 쪽이 우세합니다.")
    elif news_bias < 0:
        reasons.append("관련 뉴스에 부정 신호가 있어 하락 시 더 보수적으로 봅니다.")

    core = max(0, min(100, int(core)))
    confidence = max(45, min(90, int(core * 0.55 + 35)))

    # V108-5: 실제 당일 등락률이 있으면 그것을 우선 사용합니다.
    if signal_rate <= -3:
        if core >= 66:
            label = "🟢 좋은 하락"
            action = "분할매수 검토"
            summary = "하락했지만 내부 체력이 살아 있어 공포매도보다 분할매수 후보로 볼 수 있습니다."
        elif core >= 56:
            label = "🟡 애매한 하락"
            action = "관망 후 확인"
            summary = "하락했지만 근거가 완전히 무너지지는 않았습니다. 추가매수는 보류하고 원인을 확인합니다."
        else:
            label = "🔴 나쁜 하락"
            action = "추매금지 · 위험 확인"
            summary = "하락과 내부 체력 약화가 겹쳤습니다. 추가매수보다 손실 확대 원인 확인이 우선입니다."
    elif signal_rate >= 3:
        if core >= 66:
            label = "🟢 좋은 상승"
            action = "보유 유지"
            summary = "수익구간이면서 내부 체력도 양호합니다. 성급한 매도보다 보유 관리가 우선입니다."
        elif core >= 56:
            label = "🟡 관리 필요한 상승"
            action = "일부 수익관리"
            summary = "수익은 났지만 내부 점수가 아주 강하지 않습니다. 추격매수보다 수익관리 관점입니다."
        else:
            label = "🟠 나쁜 상승"
            action = "비중축소 검토"
            summary = "수익은 났지만 내부 체력이 약합니다. 선반영/일시 반등 가능성을 점검합니다."
    else:
        if core >= 72:
            label = "🟡 조용한 강세"
            action = "관심 유지"
            summary = "큰 손익 변화는 없지만 내부 체력이 좋아 관심 유지 구간입니다."
        elif core <= 50:
            label = "🟠 약한 흐름"
            action = "관망"
            summary = "가격은 크게 무너지지 않았지만 내부 체력이 약해 신규매수는 보류합니다."
        else:
            label = "⚪ 중립 흐름"
            action = "보유 점검"
            summary = "좋은 하락/나쁜 하락으로 단정할 만큼 신호가 강하지 않습니다."

    return {
        "name": n,
        "label": label,
        "action": action,
        "summary": summary,
        "core": core,
        "confidence": confidence,
        "rate": rate,
        "today_rate": today_rate,
        "signal_rate": signal_rate,
        "quality": quality,
        "timing": timing,
        "future12": future12,
        "value_score": value_score,
        "news_label": news_label,
        "news_bias": news_bias,
        "reasons": reasons[:6],
    }



# V109-1: 좋은하락 / 나쁜하락 최종행동 엔진
def discovery_top_names(data, limit=3):
    try:
        return [norm(x.get("name", "")) for x in supply_discovery_candidates(data)[:limit]]
    except Exception:
        return []

def risk_titles_for_stock(data, name):
    n = norm(name)
    hits = []
    try:
        for x in emergency_items(data):
            title = str(x.get("title", ""))
            body = str(x.get("body", ""))
            if n in title or n in body:
                hits.append(x)
    except Exception:
        pass
    return hits

def good_bad_drop_engine(name, r=None, data=None, weights=None):
    """하락을 단순 손실이 아니라 좋은하락/나쁜하락/중립으로 재분류하고 최종행동을 5단계로 정합니다."""
    n = norm(name)
    try:
        if data and weights is None:
            _, _, _, _, weights, _ = metrics(data)
    except Exception:
        weights = weights or {}

    try:
        mq = move_quality_judgement(n, r, data, weights)
    except Exception:
        mq = {"core": 50, "confidence": 60, "rate": 0, "today_rate": None, "signal_rate": 0, "quality": 50, "timing": 50, "future12": 50, "value_score": 50, "label": "⚪ 흐름 확인", "summary": "판단 데이터가 부족합니다.", "reasons": []}

    rate = float(mq.get("rate", 0) or 0)
    today_rate = mq.get("today_rate", None)
    signal_rate = mq.get("signal_rate", rate)
    core = int(mq.get("core", 50) or 50)
    future12 = int(mq.get("future12", 50) or 50)

    top_names = discovery_top_names(data, 3)
    in_discovery = n in top_names
    risk_hits = risk_titles_for_stock(data, n)
    risk_count = len(risk_hits)

    sec = sector(n)
    sec_weight = 0
    try:
        sec_weight = float((weights or {}).get(sec, 0) or 0)
    except Exception:
        sec_weight = 0

    drop_score = core
    reasons = []

    if in_discovery:
        drop_score += 8
        reasons.append("발굴 TOP3 후보에 포함되어 성장/공급망 관점이 살아 있습니다.")
    else:
        reasons.append("발굴 TOP3에는 포함되지 않아 추매 근거는 한 단계 낮게 봅니다.")

    if future12 >= 70:
        drop_score += 6
        reasons.append(f"12개월 미래확률 {future12}%로 중장기 기대값이 우세합니다.")
    elif future12 <= 55:
        drop_score -= 6
        reasons.append(f"12개월 미래확률 {future12}%로 기대값 확인이 필요합니다.")

    if risk_count >= 2:
        drop_score -= 12
        reasons.append(f"위험레이더 신호가 {risk_count}건 있어 하락 판단을 보수적으로 봅니다.")
    elif risk_count == 1:
        drop_score -= 6
        reasons.append("위험레이더 신호가 1건 있어 무리한 추매는 제한합니다.")
    else:
        reasons.append("종목별 위험레이더 신호는 크지 않습니다.")

    if sec_weight >= 55:
        drop_score -= 8
        reasons.append(f"{sec} 비중이 {sec_weight:.1f}%로 높아 좋은 하락이어도 추매 규모를 줄입니다.")
    elif sec_weight <= 18:
        drop_score += 3
        reasons.append(f"{sec} 비중이 낮아 분산 보강 관점은 일부 긍정입니다.")

    is_drop = (signal_rate is not None and signal_rate <= -3) or rate <= -5
    if is_drop:
        if drop_score >= 82:
            label = "🟢 좋은하락"
            final_action = "추가매수"
            action_detail = "단, 한 번에 몰아서가 아니라 정해둔 금액 안에서만 추가매수합니다."
        elif drop_score >= 68:
            label = "🟢 좋은하락"
            final_action = "분할매수"
            action_detail = "손실 경고는 있지만 내부 체력이 살아 있어 소액 분할추매 후보입니다."
        elif drop_score >= 52:
            label = "🟡 애매한 하락"
            final_action = "보유"
            action_detail = "버릴 종목은 아니지만 추매 근거가 충분히 강하지 않아 보유 우선입니다."
        elif drop_score >= 35:
            label = "🟠 나쁜하락 의심"
            final_action = "관망"
            action_detail = "하락 원인을 더 확인할 때까지 신규매수는 보류합니다."
        else:
            label = "🔴 나쁜하락"
            final_action = "비중축소"
            action_detail = "하락과 내부 점수 약화가 겹쳐 손실 확대 방어가 우선입니다."
    else:
        if drop_score >= 72:
            label = "🟡 좋은 흐름"
            final_action = "보유"
            action_detail = "하락 신호는 약하지만 내부 체력이 양호해 보유 관리가 적절합니다."
        elif drop_score >= 52:
            label = "⚪ 중립 흐름"
            final_action = "보유"
            action_detail = "좋은하락/나쁜하락으로 단정할 만큼 신호가 강하지 않습니다."
        else:
            label = "🟠 약한 흐름"
            final_action = "관망"
            action_detail = "신규매수보다 추가 데이터 확인이 우선입니다."

    drop_score = max(0, min(100, int(drop_score)))
    confidence = max(45, min(92, int((int(mq.get("confidence", 60)) + drop_score) / 2)))

    base_reasons = mq.get("reasons", [])[:3]
    reasons = reasons + [x for x in base_reasons if x not in reasons]
    today_txt = "오늘등락 확인불가" if today_rate is None else f"오늘 {today_rate:+.2f}%"
    return {
        "name": n,
        "label": label,
        "final_action": final_action,
        "action_detail": action_detail,
        "drop_score": drop_score,
        "confidence": confidence,
        "rate": rate,
        "today_rate": today_rate,
        "today_txt": today_txt,
        "core": core,
        "quality": int(mq.get("quality", 50) or 50),
        "timing": int(mq.get("timing", 50) or 50),
        "future12": future12,
        "value_score": int(mq.get("value_score", 50) or 50),
        "in_discovery": in_discovery,
        "risk_count": risk_count,
        "summary": f"{label} {drop_score}점 · 최종행동: {final_action}",
        "reasons": reasons[:7],
    }

def good_bad_drop_list(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    out = []
    for n, q, a, r in rows:
        try:
            out.append(good_bad_drop_engine(n, r, data, weights))
        except Exception:
            pass
    rank = {"추가매수": 0, "분할매수": 1, "보유": 2, "관망": 3, "비중축소": 4}
    return sorted(out, key=lambda x: (rank.get(x.get("final_action", ""), 9), -x.get("drop_score", 0)))

def render_good_bad_drop_card(item, title_prefix="🎯 좋은하락/나쁜하락"):
    rs = "<br>".join([f"① {x}" for x in item.get("reasons", [])])
    st.markdown(
        f'<div class="brief-card">'
        f'<div class="brief-title">{title_prefix} · {item["name"]}</div>'
        f'<div class="brief-sub">{item["label"]} · 신뢰도 {item["confidence"]}% · {item["today_txt"]} · 보유수익률 {item["rate"]:.2f}%</div>'
        f'<div class="brief-action">최종행동: {item["final_action"]}<br>{item["action_detail"]}</div>'
        f'<div class="brief-grid">'
        f'<div class="brief-box"><div class="brief-label">좋은하락 점수</div><div class="brief-value">{item["drop_score"]}점</div></div>'
        f'<div class="brief-box"><div class="brief-label">내부체력</div><div class="brief-value">{item["core"]}점</div></div>'
        f'<div class="brief-box"><div class="brief-label">미래확률</div><div class="brief-value">12개월 {item["future12"]}%</div></div>'
        f'<div class="brief-box"><div class="brief-label">발굴TOP3</div><div class="brief-value">{"포함" if item["in_discovery"] else "미포함"}</div></div>'
        f'<div class="brief-box"><div class="brief-label">위험신호</div><div class="brief-value">{item["risk_count"]}건</div></div>'
        f'<div class="brief-box"><div class="brief-label">타이밍/가치</div><div class="brief-value">{item["timing"]}점 / {item["value_score"]}점</div></div>'
        f'</div>'
        f'<div class="brief-reason"><b>판단근거</b><br>{rs}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

def render_good_bad_drop_summary(data):
    items = good_bad_drop_list(data)
    if not items:
        card("🎯 좋은하락/나쁜하락", "판단할 보유종목 데이터가 없습니다.")
        return
    focus = []
    for x in items:
        if x.get("final_action") in ["추가매수", "분할매수", "관망", "비중축소"]:
            focus.append(x)
    focus = focus[:3] or items[:3]
    st.markdown('<div class="brief-card"><div class="brief-title">🎯 좋은하락/나쁜하락 최종판단</div><div class="brief-sub">손실 경고와 발굴 후보가 충돌할 때, 최종행동을 하나로 정리합니다.</div></div>', unsafe_allow_html=True)
    for x in focus:
        render_good_bad_drop_card(x, "판단")


def render_move_quality_home(data):
    items = good_bad_drop_list(data)
    if not items:
        return

    focus = []
    for x in items:
        if x.get("final_action") in ["추가매수", "분할매수", "관망", "비중축소"]:
            focus.append(x)
    focus = focus[:4] or items[:3]

    body = []
    for x in focus:
        body.append(f'<b>{x["label"]} · {x["name"]}</b><br>최종행동: {x["final_action"]}<br>좋은하락 점수 {x["drop_score"]}점 · 신뢰도 {x["confidence"]}%<br>{x["action_detail"]}')
    card("🎯 좋은하락 / 나쁜하락 최종판단", "<br><br>".join(body))

    with st.expander("좋은하락/나쁜하락 상세근거", expanded=False):
        for x in focus:
            rs = "  \n".join([f'- {r}' for r in x.get("reasons", [])])
            st.markdown(
                f'**{x["name"]} · {x["label"]} · {x["final_action"]}**  \n'
                f'- 좋은하락 점수: {x["drop_score"]}점 · 신뢰도 {x["confidence"]}%  \n'
                f'- {x["today_txt"]} · 보유수익률 {x["rate"]:.2f}%  \n'
                f'- 내부체력 {x["core"]} · 품질 {x["quality"]} · 타이밍 {x["timing"]} · 12개월 {x["future12"]}% · 가치 {x["value_score"]}  \n'
                f'{rs}'
            )


def render_v106_discovery_top3(data):
    try:
        items = supply_discovery_candidates(data)[:3]
    except Exception:
        items = []
    if not items:
        card("🔥 오늘의 발굴 TOP3", "발굴 후보를 계산하지 못했습니다.")
        return

    body = []
    for i, x in enumerate(items, 1):
        body.append(f'{i}. <b>{x.get("name", "-")}</b> · {x.get("theme", "")} · {x.get("score", 0)}점')
    card("🔥 오늘의 발굴 TOP3", "<br>".join(body))

    with st.expander("발굴 근거 보기", expanded=False):
        for i, x in enumerate(items, 1):
            leaders = " · ".join(x.get("leaders", [])[:3])
            st.markdown(
                f'**{i}. {x.get("name", "-")}**  \n'
                f'- 테마: {x.get("theme", "")}  \n'
                f'- 대장주 체인: {leaders}  \n'
                f'- 역할: {x.get("role", "")}  \n'
                f'- 근거: {x.get("note", "")}  \n'
                f'- 발굴점수: {x.get("score", 0)}점'
            )


def render_turbo_home(data):
    header()
    # V107-1: 홈은 결론 3개만 먼저 보여줍니다.
    render_v106_action_board(data)
    render_v106_risk_radar(data)
    render_v106_discovery_top3(data)

    with st.expander("🎯 좋은 하락/나쁜 하락 판정 보기", expanded=False):
        render_move_quality_home(data)

    with st.expander("고급 분석 엔진 보기", expanded=False):
        st.caption("기존 기능은 삭제하지 않았고, 결론 생성용 내부 엔진으로 유지합니다.")
        try:
            render_news_conclusion(data)
            render_supply_chain_discovery(data)
            render_rebalance_summary(data)
            render_target_price_summary(data)
            render_future_probability_summary(data)
            render_core_engine_summary(data)
        except Exception as e:
            st.caption(f"고급 분석 일부를 불러오지 못했습니다: {e}")

    # V107-3: DB 지문은 홈에서 숨기고 투자기록 탭의 전문가 메뉴로 이동했습니다.
    if st.button("🔄 새로고침 / 다시 판단하기", use_container_width=True):
        st.rerun()



# V108-2 VERIFIED: 행동 컴파스 / 실행전략 / 발굴 TOP3 카드
# 기준 파일: V107-5_THEME_FIX. 기존 기능은 삭제하지 않고 홈/추천의 노출 방식만 강화합니다.
def compass_decision(data):
    try:
        hs, hg, hr, risk_reasons, risk_action = portfolio_health(data)
        total_buy, total_value, profit, rate, weights, rows = metrics(data)
        a = one_action(data)
        action_text = str(a.get("main", "오늘은 보유 유지"))
    except Exception:
        hs, hg, hr, risk_action, rate, weights, action_text = 60, "🟡 보통", "", "보유 점검", 0, {}, "오늘은 보유 유지"
    score = int(max(0, min(100, hs)))
    semi = float(weights.get("반도체", 0) or 0)
    us = float(weights.get("미국지수", 0) or 0)
    if score >= 85 and rate >= 0:
        mode, headline = "🟢 공격 가능", "분할매수 가능권"
    elif score >= 72:
        mode, headline = "🔵 보유 우위", "오늘은 보유 중심"
    elif score >= 60:
        mode, headline = "🟡 선별 매수", "무리하지 말고 한 종목만"
    elif score >= 45:
        mode, headline = "🟠 경계", "신규매수보다 점검 우선"
    else:
        mode, headline = "🔴 위험", "매수 중지 · 방어 우선"
    if semi >= 50:
        key_reason = f"반도체 비중 {semi:.1f}%로 높아 추격매수보다 분산이 우선입니다."
    elif us < 25:
        key_reason = f"미국지수 비중 {us:.1f}%로 낮아 장기 안정성 보강 여지가 있습니다."
    elif rate >= 3:
        key_reason = f"평가수익률 {rate:.2f}% 수익권입니다. 성급한 매도보다 보유 관리가 우선입니다."
    else:
        key_reason = f"평가수익률 {rate:.2f}% 기준으로 큰 방향 전환 신호는 아직 약합니다."
    return {"score":score,"mode":mode,"headline":headline,"key_reason":key_reason,"risk_action":risk_action,"action_text":action_text,"summary":hr}

def render_compass_gauge(data, title="🧭 오늘의 컴파스"):
    d = compass_decision(data)
    st.markdown(
        f'<div class="compass-card"><div class="compass-k">{title}</div>'
        f'<div class="compass-main">{d["headline"]}</div>'
        f'<div class="compass-score">{d["score"]}점</div>'
        f'<div class="compass-sub"><b>{d["mode"]}</b><br>{d["key_reason"]}<br>오늘 행동: {d["action_text"]}</div>'
        f'<span class="compass-pill">{d["mode"]}</span></div>',
        unsafe_allow_html=True)

def render_execution_strategy(data):
    d = compass_decision(data)
    try:
        period, period_reason = investment_period_hint(data)
    except Exception:
        period, period_reason = "보유 점검", "투자기간 판단 데이터가 부족합니다."
    try:
        hs, hg, hr, risk_reasons, risk_action = portfolio_health(data)
    except Exception:
        hs, hg, hr, risk_reasons, risk_action = d["score"], d["mode"], d["summary"], [], d["risk_action"]
    reasons = "<br>".join([f"- {x}" for x in (risk_reasons or [])[:4]]) or "- 현재는 큰 위험 신호보다 보유 점검이 우선입니다."
    st.markdown(
        f'<div class="strategy-card"><div class="strategy-title">📌 오늘 실행전략</div>'
        f'<div class="strategy-line"><b>결론</b>: {d["headline"]}<br>'
        f'<b>행동</b>: {d["action_text"]}<br>'
        f'<b>투자기간</b>: {period} · {period_reason}<br>'
        f'<b>포트 상태</b>: {hs}점 · {hg}<br>'
        f'<b>근거</b><br>{reasons}<br><br><b>실행 기준</b>: {risk_action}</div></div>',
        unsafe_allow_html=True)

def render_discovery_top3_cards(data):
    try:
        items = supply_discovery_candidates(data)[:3]
    except Exception:
        items = []
    if not items:
        card("🔥 오늘의 발굴 TOP3", "발굴 후보를 계산하지 못했습니다.")
        return
    st.markdown('<div class="strategy-card"><div class="strategy-title">🔥 오늘의 발굴 TOP3</div><div class="strategy-line">대장주가 아니라 대장주의 공급망 수혜 후보를 카드로 보여줍니다.</div></div>', unsafe_allow_html=True)
    for i, x in enumerate(items, 1):
        leaders = " · ".join(x.get("leaders", [])[:3])
        st.markdown(
            f'<div class="top3-card"><div class="top3-head"><div class="top3-name">{i}. {x.get("name", "-")}</div><div class="top3-score">{x.get("score",0)}점</div></div>'
            f'<div class="top3-meta">테마: {x.get("theme", "")}<br>수혜체인: {leaders} → {x.get("role", "")}<br>이유: {x.get("note", "")}</div></div>',
            unsafe_allow_html=True)

def render_real_drop_defense(data):
    """V108-5: 수익률 하락 대응용 실시간 방어판."""
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        rows, weights = [], {}
    items = []
    for n, q, a, r in rows:
        if not r:
            continue
        try:
            gd = good_bad_drop_engine(n, r, data, weights)
            today = gd.get("today_rate", None)
            hold_rate = gd.get("rate", 0)
            priority = 0
            if today is not None and today <= -3:
                priority += 30
            if hold_rate <= -5:
                priority += 20
            if gd.get("final_action") in ["추가매수", "분할매수"]:
                priority += 30
            elif gd.get("final_action") in ["관망", "비중축소"]:
                priority += 25
            items.append({"name": n, "today": today, "hold_rate": hold_rate, "label": gd.get("label", "⚪ 흐름 확인"), "action": gd.get("final_action", "보유"), "summary": gd.get("action_detail", ""), "priority": priority, "confidence": gd.get("confidence", 70), "drop_score": gd.get("drop_score", 0)})
        except Exception:
            pass
    if not items:
        return
    items = sorted(items, key=lambda x: x.get("priority", 0), reverse=True)
    focus = [x for x in items if x.get("priority", 0) > 0][:3] or items[:2]
    body = []
    for x in focus:
        today_txt = "오늘등락 확인불가" if x.get("today") is None else f"오늘 {x['today']:+.2f}%"
        body.append(f'<b>{x["name"]}</b><br>{today_txt} · 보유수익률 {x["hold_rate"]:.2f}%<br>{x["label"]} {x.get("drop_score",0)}점 · 최종행동 {x["action"]} · 신뢰도 {x["confidence"]}%<br>{x["summary"]}')
    card("🛡️ 실시간 하락 방어판", "<br><br>".join(body))



# V114~V116 CORE ENGINE: 뉴스점수 + 차트점수 + 발굴엔진 V1
POSITIVE_NEWS_WORDS_V114 = ["수주", "계약", "공급", "흑자", "증가", "성장", "확대", "호조", "상승", "투자", "실적", "개선", "최대", "강세", "협력", "승인", "증설", "수혜", "목표가 상향"]
NEGATIVE_NEWS_WORDS_V114 = ["하락", "감소", "적자", "손실", "부진", "우려", "리콜", "조사", "소송", "급락", "약세", "축소", "취소", "위험", "경고", "부채", "파업", "목표가 하향"]

def stock_news_score_v114(name):
    """종목/섹터 관련 RSS 제목을 1차 점수화합니다. 실패하면 중립으로 반환합니다."""
    n = norm(name)
    try:
        keys = holding_news_keywords(n) if "holding_news_keywords" in globals() else [n, sector(n)]
    except Exception:
        keys = [n]
    score = 0
    pos_hits, neg_hits, matched_titles = [], [], []
    try:
        for source, title, link in rss_items():
            title_s = str(title or "")
            if not any(str(k).lower() in title_s.lower() for k in keys):
                continue
            matched_titles.append(title_s)
            p = sum(1 for w in POSITIVE_NEWS_WORDS_V114 if w in title_s)
            ng = sum(1 for w in NEGATIVE_NEWS_WORDS_V114 if w in title_s)
            if p:
                pos_hits.append(title_s)
            if ng:
                neg_hits.append(title_s)
            score += min(18, p * 6) - min(18, ng * 7)
    except Exception:
        pass
    score = max(-50, min(50, int(score)))
    if score >= 20:
        label = "🟢 뉴스 우호"
    elif score >= 5:
        label = "🟡 뉴스 약우호"
    elif score <= -20:
        label = "🔴 뉴스 위험"
    elif score <= -5:
        label = "🟠 뉴스 주의"
    else:
        label = "⚪ 뉴스 중립"
    reasons = []
    if pos_hits:
        reasons.append(f"긍정 키워드 뉴스 {len(pos_hits)}건")
    if neg_hits:
        reasons.append(f"부정 키워드 뉴스 {len(neg_hits)}건")
    if matched_titles:
        reasons.append(f"관련 뉴스 {len(matched_titles)}건 감지")
    if not reasons:
        reasons.append("직접 관련 뉴스가 적어 중립 처리")
    return {"name": n, "score": score, "label": label, "reasons": reasons[:3], "sample": matched_titles[:2]}

def chart_score_v115(name, result=None):
    """현재 보유수익률/당일등락률/거래량 기반 1차 차트 점수. RSI/MACD는 후속 실제 차트데이터 연결 시 확장."""
    n = norm(name)
    r = result or {}
    price = sf(r.get("price"), fallback_price(n) or 0)
    rate = sf(r.get("rate"), 0)
    today = r.get("change_rate")
    today = None if today is None else sf(today)
    vol = sf(r.get("volume"), 0)
    score = 50
    reasons = []
    if rate <= -15:
        score -= 12; reasons.append("보유수익률 -15% 이하로 손실추세 주의")
    elif rate <= -7:
        score -= 6; reasons.append("보유수익률 -7% 이하로 조정구간")
    elif -5 <= rate <= 5:
        score += 4; reasons.append("과열/급락이 아닌 중립권")
    elif rate >= 20:
        score -= 5; reasons.append("수익률이 높아 단기 차익매물 가능성")
    elif rate >= 8:
        score += 5; reasons.append("수익권 유지로 추세 양호")
    if today is not None:
        if today <= -4:
            score -= 12; reasons.append(f"오늘 {today:+.2f}% 급락")
        elif today <= -2:
            score -= 6; reasons.append(f"오늘 {today:+.2f}% 하락")
        elif today >= 4:
            score += 8; reasons.append(f"오늘 {today:+.2f}% 강세")
        elif today >= 2:
            score += 4; reasons.append(f"오늘 {today:+.2f}% 상승")
    else:
        reasons.append("당일 등락률 확인불가")
    if vol and vol >= 1000000:
        score += 4; reasons.append("거래량 100만주 이상")
    score = max(0, min(100, int(score)))
    if score >= 72:
        label = "🟢 차트 우호"
    elif score >= 58:
        label = "🟡 차트 보통+"
    elif score >= 45:
        label = "⚪ 차트 중립"
    elif score >= 32:
        label = "🟠 차트 주의"
    else:
        label = "🔴 차트 위험"
    return {"name": n, "score": score, "label": label, "reasons": reasons[:4], "price": price, "rate": rate, "today": today}

def core_engine_score_v116(name, result=None, data=None):
    n = norm(name)
    news = stock_news_score_v114(n)
    chart = chart_score_v115(n, result)
    future = 55
    supply = 50
    try:
        if "future_probability_score" in globals():
            future = int(future_probability_score(n, result, data).get("p12", 55))
    except Exception:
        pass
    try:
        for item in supply_discovery_candidates(data)[:20]:
            if norm(item.get("name", "")) == n:
                supply = int(item.get("score", 50)); break
    except Exception:
        pass
    news_norm = 50 + news.get("score", 0)
    total = int(news_norm * 0.25 + chart.get("score", 50) * 0.30 + future * 0.25 + supply * 0.20)
    total = max(0, min(100, total))
    if total >= 78:
        action = "🟢 발굴/분할매수 후보"
    elif total >= 66:
        action = "🟡 관심·보유 우위"
    elif total >= 52:
        action = "⚪ 관찰"
    elif total >= 38:
        action = "🟠 주의"
    else:
        action = "🔴 제외/비중축소 검토"
    return {"name": n, "total": total, "action": action, "news": news, "chart": chart, "future": future, "supply": supply}

def discovery_engine_v116(data):
    """보유종목 + 공급망 DB 후보를 합쳐 오늘의 발굴 후보를 만듭니다."""
    candidates = []
    seen = set()
    try:
        for h in data.get("holdings", []):
            n = norm(h.get("name", ""))
            if n:
                seen.add(n)
                r = evaluate(n, sf(h.get("qty")), sf(h.get("avg")))
                x = core_engine_score_v116(n, r, data)
                x["source"] = "보유종목"
                candidates.append(x)
    except Exception:
        pass
    try:
        for item in supply_discovery_candidates(data):
            n = norm(item.get("name", ""))
            if not n or n in seen:
                continue
            seen.add(n)
            r = {"price": fallback_price(n), "rate": 0, "change_rate": None, "volume": None}
            x = core_engine_score_v116(n, r, data)
            x["source"] = f"발굴DB · {item.get('theme','')}"
            x["role"] = item.get("role", "")
            candidates.append(x)
    except Exception:
        pass
    return sorted(candidates, key=lambda x: x.get("total", 0), reverse=True)


# V117 GOOD/BAD DROP ENGINE: V114 뉴스 + V115 차트 + V116 발굴 점수를 행동판단에 연결
# 개발용 엔진 점수는 화면에 직접 노출하지 않고, 최종판단과 핵심근거만 보여줍니다.
def good_bad_drop_engine_v117(name, r=None, data=None):
    n = norm(name)
    base = {}
    core = {}
    try:
        base = good_bad_drop_engine(n, r, data)
    except Exception:
        base = {"name": n, "label": "⚪ 중립 흐름", "final_action": "보유", "drop_score": 55, "confidence": 60, "reasons": []}
    try:
        core = core_engine_score_v116(n, r, data)
    except Exception:
        core = {"total": 55, "news": {"score": 0, "label": "⚪ 뉴스 중립", "reasons": []}, "chart": {"score": 50, "label": "⚪ 차트 중립", "reasons": []}, "future": 55, "supply": 50}

    news_score = int(core.get("news", {}).get("score", 0) or 0)
    chart_score = int(core.get("chart", {}).get("score", 50) or 50)
    discovery_score = int(core.get("total", 55) or 55)
    base_score = int(base.get("drop_score", 55) or 55)
    today_rate = base.get("today_rate")
    rate = float(base.get("rate", 0) or 0)

    v117_score = int(base_score * 0.45 + (50 + news_score) * 0.20 + chart_score * 0.20 + discovery_score * 0.15)
    v117_score = max(0, min(100, v117_score))

    is_drop = False
    try:
        is_drop = today_rate is not None and float(today_rate) <= -2
    except Exception:
        is_drop = rate <= -5

    if is_drop:
        if v117_score >= 70:
            label = "🟢 좋은하락"
            action = "분할매수 검토"
            summary = "하락했지만 뉴스·차트·발굴 점수가 무너지지 않아 공포매도보다 분할매수 후보로 봅니다."
        elif v117_score >= 55:
            label = "🟡 애매한 하락"
            action = "보유·관찰"
            summary = "추가매수 근거가 강하지 않습니다. 보유는 가능하지만 원인 확인이 우선입니다."
        else:
            label = "🔴 나쁜하락"
            action = "추매금지"
            summary = "하락과 내부점수 약화가 겹쳤습니다. 신규매수보다 방어가 우선입니다."
    else:
        if v117_score >= 74:
            label = "🟢 좋은 흐름"
            action = "보유 우위"
            summary = "하락 신호는 약하고 내부 점수가 양호합니다. 성급한 매도보다 보유 관리가 우선입니다."
        elif v117_score >= 58:
            label = "🟡 관찰 흐름"
            action = "보유·관찰"
            summary = "크게 무너진 흐름은 아니지만 추가매수는 선별적으로 판단합니다."
        else:
            label = "🟠 약한 흐름"
            action = "관망"
            summary = "뉴스·차트·발굴 점수가 약해 신규매수보다 관망이 우선입니다."

    reasons = []
    reasons.append(core.get("news", {}).get("label", "⚪ 뉴스 중립"))
    reasons.append(core.get("chart", {}).get("label", "⚪ 차트 중립"))
    if discovery_score >= 70:
        reasons.append(f"발굴점수 {discovery_score}점으로 후보권")
    else:
        reasons.append(f"발굴점수 {discovery_score}점")
    for rr in core.get("news", {}).get("reasons", [])[:1]:
        reasons.append(rr)
    for rr in core.get("chart", {}).get("reasons", [])[:1]:
        reasons.append(rr)
    for rr in base.get("reasons", [])[:2]:
        if rr not in reasons:
            reasons.append(rr)

    return {
        "name": n,
        "label": label,
        "action": action,
        "summary": summary,
        "score": v117_score,
        "confidence": max(50, min(92, int((base.get("confidence", 60) + v117_score) / 2))),
        "rate": rate,
        "today_rate": today_rate,
        "today_txt": base.get("today_txt", "오늘등락 확인불가"),
        "news_score": news_score,
        "chart_score": chart_score,
        "discovery_score": discovery_score,
        "future": core.get("future", 55),
        "supply": core.get("supply", 50),
        "reasons": reasons[:6],
    }


def good_bad_drop_list_v117(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    out = []
    for n, q, a, r in rows:
        try:
            out.append(good_bad_drop_engine_v117(n, r, data))
        except Exception:
            pass
    rank = {"분할매수 검토": 0, "보유 우위": 1, "보유·관찰": 2, "관망": 3, "추매금지": 4}
    return sorted(out, key=lambda x: (rank.get(x.get("action", ""), 9), -x.get("score", 0)))


def render_v117_good_bad_summary(data, compact=False):
    items = good_bad_drop_list_v117(data)
    if not items:
        card("🎯 좋은하락/나쁜하락", "판단할 보유종목 데이터가 없습니다.")
        return
    focus = items[:3] if compact else items[:5]
    title = "🎯 좋은하락/나쁜하락 엔진 V117"
    sub = "뉴스점수·차트점수·발굴점수를 합쳐 오늘 행동을 하나로 정리합니다."
    st.markdown(f'<div class="brief-card"><div class="brief-title">{title}</div><div class="brief-sub">{sub}</div></div>', unsafe_allow_html=True)
    for x in focus:
        reason = " / ".join(x.get("reasons", [])[:3])
        st.markdown(
            f'<div class="top3-card"><div class="top3-head"><div class="top3-name">{x["label"]} · {x["name"]}</div><div class="top3-score">{x["score"]}점</div></div>'
            f'<div class="top3-meta">최종행동: <b>{x["action"]}</b> · 신뢰도 {x["confidence"]}%<br>{x["summary"]}<br>근거: {reason}</div></div>',
            unsafe_allow_html=True
        )
    with st.expander("전문가용 엔진 점수 보기", expanded=False):
        st.caption("사용자 화면에서는 숨기고, 검증용으로만 확인합니다.")
        for x in items:
            st.markdown(
                f'**{x["name"]} · {x["label"]} · {x["action"]}**  \n'
                f'- V117 점수: {x["score"]}점 · 신뢰도 {x["confidence"]}%  \n'
                f'- 뉴스점수: {x["news_score"]:+d} · 차트점수: {x["chart_score"]} · 발굴점수: {x["discovery_score"]} · 미래확률: {x["future"]}% · 공급망: {x["supply"]}  \n'
                f'- {" / ".join(x.get("reasons", []))}'
            )



# V117-1: 내 보유종목 자동판정 엔진
# 목적: 사용자가 점수표를 보지 않아도 각 보유종목별로 "오늘 뭘 해야 하는지"를 한눈에 보여줍니다.
def portfolio_auto_judge_v1171(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        return []
    out = []
    for n, q, a, r in rows:
        try:
            gd = good_bad_drop_engine_v117(n, r, data)
            rate = float(r.get("rate", 0) or 0) if r else 0
            today = r.get("change_rate") if r else None
            sec = sector(n)
            label = gd.get("label", "⚪ 관찰")
            action = gd.get("action", "보유·관찰")
            score = int(gd.get("score", 55) or 55)
            confidence = int(gd.get("confidence", 60) or 60)
            summary = gd.get("summary", "판단 데이터가 부족합니다.")

            # 장기 ETF는 단기 하락판정보다 적립 원칙을 우선합니다.
            if sec == "미국지수":
                if score >= 58:
                    label = "🟢 장기적립 유지"
                    action = "적립 유지"
                    summary = "미국지수형 ETF는 단기 흔들림보다 장기 적립 원칙을 우선합니다."
                else:
                    label = "🟡 적립 관찰"
                    action = "소액 유지"
                    summary = "장기 적립 대상이지만 시장 변동성이 커서 무리한 증액은 보류합니다."

            # 높은 수익권 종목은 무조건 추매보다 강세보유/일부관리로 표현합니다.
            if rate >= 25 and sec != "미국지수":
                label = "🟢 강세보유"
                action = "보유·일부관리"
                summary = "수익권이 크므로 무리한 추매보다 보유 유지와 일부 수익관리 기준을 함께 봅니다."
            elif rate >= 12 and "분할매수" in action:
                action = "보유 우선"
                summary = "수익권에 있으므로 신규 추매보다 보유 유지가 우선입니다."

            # 손실권인데 내부 점수가 낮으면 주의로 끌어올림
            if rate <= -8 and score < 58:
                label = "🟠 주의"
                action = "추매 보류"
                summary = "손실구간에서 내부 점수가 강하지 않아 추가매수보다 원인 확인이 우선입니다."

            # 화면용 최종 등급
            if "좋은하락" in label or "장기적립" in label or "강세보유" in label:
                level = "🟢"
            elif "나쁜" in label or "주의" in label or "약한" in label:
                level = "🟠"
            elif "추매금지" in action:
                level = "🔴"
            else:
                level = "🟡"

            reasons = gd.get("reasons", [])[:3]
            if not reasons:
                reasons = ["뉴스·차트·발굴 점수를 종합한 자동판정"]

            out.append({
                "name": n,
                "sector": sec,
                "level": level,
                "label": label,
                "action": action,
                "score": score,
                "confidence": confidence,
                "rate": rate,
                "today": today,
                "today_txt": r.get("change_text", "등락률 확인불가") if r else "등락률 확인불가",
                "summary": summary,
                "reasons": reasons,
            })
        except Exception:
            pass
    priority = {"🔴":0, "🟠":1, "🟡":2, "🟢":3}
    return sorted(out, key=lambda x: (priority.get(x.get("level", "🟡"), 9), -x.get("score", 0)))


def render_portfolio_auto_judge_v1171(data, compact=False):
    items = portfolio_auto_judge_v1171(data)
    if not items:
        card("🧭 내 보유종목 자동판정", "보유종목 판정 데이터가 없습니다.")
        return
    title = "🧭 내 보유종목 자동판정 V117-1"
    sub = "보유종목별로 오늘 해야 할 행동을 한 줄로 정리합니다. 점수표는 숨기고 최종판정만 먼저 보여줍니다."
    st.markdown(f'<div class="brief-card"><div class="brief-title">{title}</div><div class="brief-sub">{sub}</div></div>', unsafe_allow_html=True)
    show = items[:3] if compact else items
    for x in show:
        reason = " / ".join(x.get("reasons", [])[:3])
        today_line = f'오늘 {x.get("today_txt", "등락률 확인불가")} · 보유수익률 {x.get("rate",0):.2f}%'
        st.markdown(
            f'<div class="top3-card"><div class="top3-head"><div class="top3-name">{x["level"]} {x["name"]}</div><div class="top3-score">{x["action"]}</div></div>'
            f'<div class="top3-meta"><b>판정:</b> {x["label"]}<br>{today_line}<br>{x["summary"]}<br>근거: {reason}</div></div>',
            unsafe_allow_html=True
        )
    with st.expander("전문가용 자동판정 점수 보기", expanded=False):
        for x in items:
            st.markdown(
                f'**{x["name"]}**  \n'
                f'- 판정: {x["label"]} / 행동: {x["action"]}  \n'
                f'- 점수: {x["score"]}점 · 신뢰도 {x["confidence"]}% · 보유수익률 {x["rate"]:.2f}%  \n'
                f'- {" / ".join(x.get("reasons", []))}'
            )


def render_core_engine_summary(data):
    items = discovery_engine_v116(data)[:5]
    if not items:
        card("🧠 핵심 엔진", "뉴스/차트/발굴 후보를 계산하지 못했습니다.")
        return
    top = items[0]
    st.markdown(
        f'<div class="strategy-card"><div class="strategy-title">🧠 V114~V116 핵심 엔진</div>'
        f'<div class="strategy-line"><b>1순위</b>: {top["name"]} · {top["total"]}점 · {top["action"]}<br>'
        f'뉴스: {top["news"]["label"]} ({top["news"]["score"]:+d}) · 차트: {top["chart"]["label"]} ({top["chart"]["score"]}점)<br>'
        f'미래확률: {top["future"]}% · 공급망: {top["supply"]}점<br>'
        f'<b>의미</b>: 뉴스점수와 차트점수를 발굴엔진에 연결한 1차 버전입니다.</div></div>',
        unsafe_allow_html=True
    )
    for i, x in enumerate(items[:5], 1):
        nr = " / ".join(x.get("news", {}).get("reasons", [])[:2])
        cr = " / ".join(x.get("chart", {}).get("reasons", [])[:2])
        st.markdown(
            f'<div class="top3-card"><div class="top3-head"><div class="top3-name">{i}. {x["name"]}</div><div class="top3-score">{x["total"]}점</div></div>'
            f'<div class="top3-meta">{x["action"]}<br>출처: {x.get("source", "-")}<br>뉴스근거: {nr}<br>차트근거: {cr}</div></div>',
            unsafe_allow_html=True
        )



# V121-1: Smart Money Data Layer / 실시간 거래량·거래대금 1차 연결
# 목적: 뉴스보다 먼저 움직이는 거래량/거래대금/차트 이상징후를 잡기 위한 데이터 계층입니다.
def env_or_secret_exists(*names):
    """API 키 존재 여부만 확인합니다. 값은 화면에 절대 노출하지 않습니다."""
    for name in names:
        try:
            if os.environ.get(name):
                return True
        except Exception:
            pass
        try:
            if hasattr(st, "secrets") and name in st.secrets and st.secrets.get(name):
                return True
        except Exception:
            pass
    return False

def get_secret_value(*names, default=""):
    """환경변수 또는 Streamlit secrets에서 키 값을 읽습니다. 값은 화면에 노출하지 않습니다."""
    for name in names:
        try:
            v = os.environ.get(name)
            if v:
                return str(v).strip()
        except Exception:
            pass
        try:
            if hasattr(st, "secrets"):
                if name in st.secrets and st.secrets.get(name):
                    return str(st.secrets.get(name)).strip()
                # [kis] 섹션 지원
                if "kis" in st.secrets and name in st.secrets["kis"] and st.secrets["kis"].get(name):
                    return str(st.secrets["kis"].get(name)).strip()
        except Exception:
            pass
    return default


def kis_credentials():
    app_key = get_secret_value("KIS_APP_KEY", "KIS_APPKEY", "KOREA_INVESTMENT_APP_KEY", "APP_KEY")
    app_secret = get_secret_value("KIS_APP_SECRET", "KIS_APPSECRET", "KOREA_INVESTMENT_APP_SECRET", "APP_SECRET")
    # paper=true면 모의투자 도메인, 아니면 실전 도메인
    paper = get_secret_value("KIS_PAPER", "KOREA_INVESTMENT_PAPER", default="false").lower() in ["1", "true", "yes", "y"]
    return app_key, app_secret, paper


def kis_base_url():
    _, _, paper = kis_credentials()
    return "https://openapivts.koreainvestment.com:29443" if paper else "https://openapi.koreainvestment.com:9443"


@st.cache_data(ttl=60*60*6, show_spinner=False)
def kis_access_token_cached(app_key_hash, app_secret_hash, paper=False):
    """실제 키 값은 cache key에 넣지 않고 해시만 사용합니다. 내부에서 다시 secrets를 읽습니다."""
    app_key, app_secret, _ = kis_credentials()
    if not app_key or not app_secret:
        return ""
    try:
        url = f"{kis_base_url()}/oauth2/tokenP"
        payload = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code == 200:
            return r.json().get("access_token", "")
    except Exception:
        pass
    return ""


def kis_access_token():
    app_key, app_secret, paper = kis_credentials()
    if not app_key or not app_secret:
        return ""
    return kis_access_token_cached(short_hash(app_key, 8), short_hash(app_secret, 8), paper)


def kis_ready():
    app_key, app_secret, _ = kis_credentials()
    return bool(app_key and app_secret)


@st.cache_data(ttl=60, show_spinner=False)
def kis_inquire_price_cached(name):
    """한국투자 Open API 국내주식 현재가. 현재가/거래량/거래대금을 Smart Money 데이터로 사용합니다."""
    n = norm(name)
    code = code_map().get(n)
    if not code or not kis_ready():
        return None
    token = kis_access_token()
    if not token:
        return None
    app_key, app_secret, _ = kis_credentials()
    try:
        url = f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST01010100",
        }
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        r = requests.get(url, headers=headers, params=params, timeout=6)
        if r.status_code != 200:
            return {"ok": False, "src": "KIS", "error": f"HTTP {r.status_code}"}
        js = r.json()
        out = js.get("output", {}) if isinstance(js, dict) else {}
        if not out:
            return {"ok": False, "src": "KIS", "error": str(js)[:120]}
        price = parse_price(out.get("stck_prpr"))
        volume = parse_price(out.get("acml_vol"))
        amount = parse_price(out.get("acml_tr_pbmn"))
        change_rate = None
        try:
            change_rate = float(str(out.get("prdy_ctrt", "")).replace(",", ""))
        except Exception:
            change_rate = None
        return {
            "ok": True,
            "name": n,
            "code": code,
            "price": price,
            "volume": volume,
            "amount": amount,
            "change_rate": change_rate,
            "src": f"KIS {code}",
            "raw_time": now_label(),
        }
    except Exception as e:
        return {"ok": False, "src": "KIS", "error": str(e)[:120]}


def kis_inquire_price(name):
    try:
        return kis_inquire_price_cached(norm(name))
    except Exception:
        return None



# V121-2: KIS REAL TEST PANEL / 한국투자 실데이터 진단패널
# 목적: APP KEY 인식 → 토큰 발급 → 현재가/거래량/거래대금 조회 성공 여부를 화면에서 바로 확인합니다.
def mask_secret_status(value):
    return "✅ 인식됨" if bool(str(value or "").strip()) else "❌ 없음"


def kis_account_info():
    account_no = get_secret_value("KIS_ACCOUNT_NO", "KIS_ACCT_NO", "KOREA_INVESTMENT_ACCOUNT_NO", default="")
    product_code = get_secret_value("KIS_PRODUCT_CODE", "KIS_ACCOUNT_PRODUCT_CODE", "KIS_ACCT_PRDT_CD", default="01")
    return account_no, product_code


@st.cache_data(ttl=60*60*23, show_spinner=False)
def kis_direct_token_test_cached(app_key_hash, app_secret_hash, paper=False):
    """V121-4: 토큰은 24시간 원칙을 고려해 23시간 캐시합니다. 새로고침 때마다 재발급하지 않습니다."""
    app_key, app_secret, _ = kis_credentials()
    if not app_key or not app_secret:
        return {"ok": False, "status": "키 없음", "error": "KIS_APP_KEY 또는 KIS_APP_SECRET이 없습니다.", "token": "", "cached": False}
    try:
        url = f"{kis_base_url()}/oauth2/tokenP"
        payload = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
        r = requests.post(url, json=payload, timeout=8)
        try:
            js = r.json()
        except Exception:
            js = {"raw": r.text[:200]}
        token = js.get("access_token", "") if isinstance(js, dict) else ""
        if r.status_code == 200 and token:
            return {"ok": True, "status": f"HTTP {r.status_code}", "error": "", "token": token, "cached": True}
        return {"ok": False, "status": f"HTTP {r.status_code}", "error": str(js)[:220], "token": "", "cached": False}
    except Exception as e:
        return {"ok": False, "status": "요청 실패", "error": str(e)[:220], "token": "", "cached": False}


def kis_direct_token_test():
    """V121-4: 화면 진단용 토큰 테스트. 키 값은 절대 화면에 노출하지 않습니다."""
    app_key, app_secret, paper = kis_credentials()
    if not app_key or not app_secret:
        return {"ok": False, "status": "키 없음", "error": "KIS_APP_KEY 또는 KIS_APP_SECRET이 없습니다.", "token": "", "cached": False}
    return kis_direct_token_test_cached(short_hash(app_key, 8), short_hash(app_secret, 8), paper)


def kis_direct_price_test(name="삼성전자"):
    """캐시를 우회해서 국내주식 현재가 API를 직접 호출합니다."""
    n = norm(name)
    code = code_map().get(n)
    if not code:
        return {"ok": False, "name": n, "code": "", "error": "종목코드 없음"}
    token_test = kis_direct_token_test()
    if not token_test.get("ok"):
        return {"ok": False, "name": n, "code": code, "error": f"토큰 실패: {token_test.get('status')} / {token_test.get('error', '')}"}
    app_key, app_secret, _ = kis_credentials()
    try:
        url = f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token_test.get('token')}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST01010100",
        }
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        r = requests.get(url, headers=headers, params=params, timeout=8)
        try:
            js = r.json()
        except Exception:
            js = {"raw": r.text[:200]}
        out = js.get("output", {}) if isinstance(js, dict) else {}
        if r.status_code != 200 or not out:
            return {"ok": False, "name": n, "code": code, "status": f"HTTP {r.status_code}", "error": str(js)[:240]}
        return {
            "ok": True,
            "name": n,
            "code": code,
            "status": f"HTTP {r.status_code}",
            "price": parse_price(out.get("stck_prpr")),
            "volume": parse_price(out.get("acml_vol")),
            "amount": parse_price(out.get("acml_tr_pbmn")),
            "change_rate": out.get("prdy_ctrt", ""),
            "src": f"KIS {code}",
            "checked_at": now_label(),
        }
    except Exception as e:
        return {"ok": False, "name": n, "code": code, "status": "요청 실패", "error": str(e)[:240]}


def amount_text(v):
    try:
        v = float(v or 0)
        if v <= 0:
            return "확인불가"
        if v >= 1000000000000:
            return f"{v/1000000000000:.1f}조원"
        if v >= 100000000:
            return f"{v/100000000:.1f}억원"
        return f"{v:,.0f}원"
    except Exception:
        return "확인불가"


def render_kis_real_test_panel(data=None):
    app_key, app_secret, paper = kis_credentials()
    account_no, product_code = kis_account_info()
    mode = "모의투자" if paper else "실전투자"
    base = kis_base_url()
    token_test = kis_direct_token_test()

    samsung = kis_direct_price_test("삼성전자")
    jeryong = kis_direct_price_test("제룡전기")

    token_label = "✅ 성공" if token_test.get("ok") else "❌ 실패"
    samsung_label = "✅ 성공" if samsung.get("ok") else "❌ 실패"
    jeryong_label = "✅ 성공" if jeryong.get("ok") else "❌ 실패"
    account_label = "입력됨" if account_no else "미입력"

    def price_row(x):
        if x.get("ok"):
            return (
                f'<div class="db-row"><div class="db-name">{x.get("name")} · {x.get("code")} · {x.get("src")}</div>'
                f'<div class="db-meta">현재가 {won(x.get("price"))} · 등락률 {x.get("change_rate", "-")}%<br>'
                f'거래량 {volume_text(x.get("volume"))} · 거래대금 {amount_text(x.get("amount"))}<br>'
                f'확인시간 {x.get("checked_at", now_label())}</div></div>'
            )
        return (
            f'<div class="db-row"><div class="db-name">{x.get("name", "테스트")} · {x.get("code", "-")}</div>'
            f'<div class="db-meta">조회 실패 · {x.get("status", "-")}<br>{x.get("error", "오류 확인불가")}</div></div>'
        )

    action = "KIS 실데이터 연결 성공" if token_test.get("ok") and samsung.get("ok") else "KIS 연결 확인 필요"
    html = (
        '<div class="db-card">'
        '<div class="db-title">📡 V121-4 KIS 실데이터 진단</div>'
        '<div class="db-sub">키 인식 → 토큰 캐시 → 실제 현재가/거래량/거래대금 조회까지 한 번에 확인합니다. 키 값은 화면에 표시하지 않습니다.</div>'
        f'<div class="db-action">판정: {action}<br>토큰 발급: {token_label} · 삼성전자 조회: {samsung_label} · 제룡전기 조회: {jeryong_label}</div>'
        '<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">APP KEY</div><div class="db-value">{mask_secret_status(app_key)}</div></div>'
        f'<div class="db-box"><div class="db-label">APP SECRET</div><div class="db-value">{mask_secret_status(app_secret)}</div></div>'
        f'<div class="db-box"><div class="db-label">투자 구분</div><div class="db-value">{mode}</div></div>'
        f'<div class="db-box"><div class="db-label">도메인</div><div class="db-value">{base.replace("https://", "")}</div></div>'
        f'<div class="db-box"><div class="db-label">계좌번호</div><div class="db-value">{account_label}</div></div>'
        f'<div class="db-box"><div class="db-label">상품코드</div><div class="db-value">{product_code or "01"}</div></div>'
        f'<div class="db-box"><div class="db-label">토큰 상태</div><div class="db-value">{token_test.get("status", "-")}</div></div>'
        f'<div class="db-box"><div class="db-label">확인시간</div><div class="db-value">{now_label()}</div></div>'
        '</div>'
    )
    if not token_test.get("ok"):
        html += f'<div class="db-sub"><b>토큰 오류</b><br>{token_test.get("error", "오류 없음")}</div>'
    html += price_row(samsung) + price_row(jeryong)
    html += '<div class="db-sub">※ 장 시작 전/장마감이어도 마지막 현재가와 누적 거래량 조회는 보통 가능해야 합니다. 여기서 실패하면 장 시간 문제가 아니라 화면 연결·키·토큰·권한·도메인 문제입니다.</div></div>'
    st.markdown(html, unsafe_allow_html=True)


def render_kis_live_quote_strip(data=None, title="📡 KIS 실시간 데이터 바로보기"):
    """V121-4: 조회 결과가 화면에 안 보이는 문제를 막기 위해 홈/추천 상단에 직접 노출합니다."""
    app_key, app_secret, paper = kis_credentials()
    mode = "모의" if paper else "실전"
    names = ["삼성전자", "제룡전기"]
    try:
        for h in (data or {}).get("holdings", [])[:3]:
            n = norm(h.get("name", ""))
            if n and n not in names and code_map().get(n):
                names.append(n)
    except Exception:
        pass

    token = kis_direct_token_test()
    rows = []
    ok_count = 0
    for n in names[:5]:
        q = kis_direct_price_test(n)
        if q.get("ok"):
            ok_count += 1
            rows.append(
                f'<div class="db-row"><div class="db-name">{q.get("name")} · {q.get("code")} · {q.get("src")}</div>'
                f'<div class="db-meta">현재가 {won(q.get("price"))} · 거래량 {volume_text(q.get("volume"))} · 거래대금 {amount_text(q.get("amount"))}<br>'
                f'등락률 {q.get("change_rate", "-")}% · 확인 {q.get("checked_at", now_label())}</div></div>'
            )
        else:
            rows.append(
                f'<div class="db-row"><div class="db-name">{q.get("name", n)} · {q.get("code", "-")}</div>'
                f'<div class="db-meta">조회 실패 · {q.get("status", "-")}<br>{q.get("error", "오류 확인불가")}</div></div>'
            )

    token_label = "✅ 토큰 확인" if token.get("ok") else "❌ 토큰 실패"
    ready_label = "✅ 키 인식" if app_key and app_secret else "❌ 키 없음"
    action = "실데이터 화면 표시 성공" if ok_count else "실데이터 화면 표시 실패"
    html = (
        '<div class="db-card">'
        f'<div class="db-title">{title}</div>'
        f'<div class="db-action">판정: {action}<br>{ready_label} · {token_label} · 구분 {mode} · 조회성공 {ok_count}/{len(names[:5])}</div>'
        '<div class="db-sub">이 카드는 V121-4에서 홈/추천 상단에 강제로 노출한 실제 조회 결과입니다. 여기 값이 보이면 “화면 연결”은 성공입니다.</div>'
        + ''.join(rows) +
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# V122: SMART MONEY LIVE / 거래량·거래대금 기반 세력 유입 1차 탐지
# 원칙: 현재가보다 거래량·거래대금 변화를 우선 봅니다. 기준선은 V122-1 임시 기준값이며, 다음 버전에서 5일/20일 평균으로 자동화합니다.
def smart_money_baseline(name):
    n = norm(name)
    base = {
        "삼성전자": {"volume": 18000000, "amount": 1400000000000},
        "SK하이닉스": {"volume": 4500000, "amount": 1000000000000},
        "제룡전기": {"volume": 550000, "amount": 30000000000},
        "에스피시스템스": {"volume": 300000, "amount": 2500000000},
        "ACE AI반도체 TOP3": {"volume": 120000, "amount": 8000000000},
        "KODEX 미국S&P500": {"volume": 250000, "amount": 6500000000},
        "LG디스플레이": {"volume": 1800000, "amount": 18000000000},
        "대한전선": {"volume": 6500000, "amount": 90000000000},
        "하나마이크론": {"volume": 700000, "amount": 9000000000},
        "이수페타시스": {"volume": 1500000, "amount": 65000000000},
        "LS ELECTRIC": {"volume": 350000, "amount": 70000000000},
        "한미반도체": {"volume": 1100000, "amount": 120000000000},
    }
    return base.get(n, {"volume": 300000, "amount": 5000000000})


# V122-2: REAL VOLUME ENGINE / 장중 시간보정 기준선
# 09:01처럼 장 초반에는 하루 평균거래량과 단순 비교하면 대부분 낮게 보입니다.
# 그래서 정규장 390분 중 현재 경과분을 반영한 "현재 시각 기준 기대 거래량"과 비교합니다.
def market_progress_ratio_now():
    try:
        now = kst_now()
        start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        end = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if now < start:
            return 0.0, "장전"
        if now >= end:
            return 1.0, "장마감"
        elapsed = (now - start).total_seconds() / 60
        return max(1/390, min(1.0, elapsed / 390)), f"장중 {elapsed:.0f}분 경과"
    except Exception:
        return 1.0, "시간확인불가"


def smart_money_expected_by_now(name):
    base = smart_money_baseline(name)
    progress, label = market_progress_ratio_now()
    # 장 초반 1~5분은 거래가 몰리는 시간이므로 너무 과민하게 뜨지 않도록 최소 기대치를 둡니다.
    adj_progress = max(progress, 0.012)
    return {
        "avg_volume": max(1, parse_float_safe(base.get("volume"), 1)),
        "avg_amount": max(1, parse_float_safe(base.get("amount"), 1)),
        "expected_volume": max(1, parse_float_safe(base.get("volume"), 1) * adj_progress),
        "expected_amount": max(1, parse_float_safe(base.get("amount"), 1) * adj_progress),
        "progress": progress,
        "progress_label": label,
    }


def smart_money_watchlist(data=None):
    names = []
    try:
        for h in (data or {}).get("holdings", []):
            n = norm(h.get("name", ""))
            if n and n not in names and code_map().get(n):
                names.append(n)
    except Exception:
        pass
    extra = ["삼성전자", "SK하이닉스", "대한전선", "하나마이크론", "이수페타시스", "LS ELECTRIC", "한미반도체", "에스피시스템스", "제룡전기"]
    for n in extra:
        if n not in names and code_map().get(n):
            names.append(n)
    return names[:12]


def parse_float_safe(v, default=0):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except Exception:
        return default


def smart_money_live_item(name):
    n = norm(name)
    q = kis_direct_price_test(n) if "kis_direct_price_test" in globals() else {"ok": False, "error": "KIS 함수 없음"}
    base = smart_money_baseline(n)
    expected = smart_money_expected_by_now(n)
    if not q.get("ok"):
        return {
            "ok": False, "name": n, "code": code_map().get(n, ""), "score": 0,
            "verdict": "조회 실패", "action": "연결 확인", "reason": q.get("error", "조회 실패"),
            "raw": q,
        }

    price = parse_float_safe(q.get("price"), 0)
    volume = parse_float_safe(q.get("volume"), 0)
    amount = parse_float_safe(q.get("amount"), 0)
    change = parse_float_safe(q.get("change_rate"), 0)
    if amount <= 0 and price > 0 and volume > 0:
        amount = price * volume

    base_vol = max(1, parse_float_safe(base.get("volume"), 1))
    base_amt = max(1, parse_float_safe(base.get("amount"), 1))
    expected_vol = max(1, parse_float_safe(expected.get("expected_volume"), 1))
    expected_amt = max(1, parse_float_safe(expected.get("expected_amount"), 1))
    # day_ratio = 하루 평균 대비 진행률, live_ratio = 현재 시각 기대치 대비 진행률
    day_vol_ratio = volume / base_vol * 100 if volume else 0
    day_amt_ratio = amount / base_amt * 100 if amount else 0
    vol_ratio = volume / expected_vol * 100 if volume else 0
    amt_ratio = amount / expected_amt * 100 if amount else 0

    score = 35
    reasons = []
    if vol_ratio >= 300:
        score += 28; reasons.append(f"시간보정 거래량 {vol_ratio:.0f}% 급증")
    elif vol_ratio >= 180:
        score += 18; reasons.append(f"시간보정 거래량 {vol_ratio:.0f}% 증가")
    elif vol_ratio >= 100:
        score += 8; reasons.append(f"시간보정 거래량 기준 근접 {vol_ratio:.0f}%")
    else:
        reasons.append(f"시간보정 거래량 {vol_ratio:.0f}%")

    if amt_ratio >= 300:
        score += 30; reasons.append(f"시간보정 거래대금 {amt_ratio:.0f}% 급증")
    elif amt_ratio >= 180:
        score += 20; reasons.append(f"시간보정 거래대금 {amt_ratio:.0f}% 증가")
    elif amt_ratio >= 100:
        score += 8; reasons.append(f"시간보정 거래대금 기준 근접 {amt_ratio:.0f}%")
    else:
        reasons.append(f"시간보정 거래대금 {amt_ratio:.0f}%")

    if change >= 5:
        score += 12; reasons.append(f"주가 강세 {change:+.2f}%")
    elif change >= 2:
        score += 7; reasons.append(f"주가 상승 {change:+.2f}%")
    elif change <= -5 and (vol_ratio >= 160 or amt_ratio >= 160):
        score -= 18; reasons.append(f"하락 중 거래 동반 {change:+.2f}% → 이탈/분산 주의")
    elif change < 0:
        score -= 5; reasons.append(f"주가 약세 {change:+.2f}%")
    else:
        reasons.append(f"등락률 {change:+.2f}%")

    score = max(0, min(100, int(score)))
    exit_risk = 0
    if change <= -3 and vol_ratio >= 160:
        exit_risk += 35
    if change <= -5 and amt_ratio >= 160:
        exit_risk += 35
    if vol_ratio >= 250 and amount <= base_amt:
        exit_risk += 15
    exit_risk = max(0, min(100, int(exit_risk)))

    if score >= 78 and exit_risk < 45:
        verdict = "🔥 스마트머니 유입 강함"
        action = "관심/추적 강화"
    elif score >= 65 and exit_risk < 50:
        verdict = "🟢 유입 후보"
        action = "분할 관심"
    elif exit_risk >= 60:
        verdict = "🔴 이탈 의심"
        action = "추격금지/위험확인"
    elif exit_risk >= 40:
        verdict = "🟠 분산 주의"
        action = "관망"
    else:
        verdict = "⚪ 보통"
        action = "관찰"

    return {
        "ok": True, "name": n, "code": q.get("code", code_map().get(n, "")), "price": price,
        "volume": volume, "amount": amount, "change": change,
        "vol_ratio": vol_ratio, "amt_ratio": amt_ratio,
        "day_vol_ratio": day_vol_ratio, "day_amt_ratio": day_amt_ratio,
        "avg_volume": base_vol, "avg_amount": base_amt,
        "expected_volume": expected_vol, "expected_amount": expected_amt,
        "progress_label": expected.get("progress_label", "-"),
        "score": score, "exit_risk": exit_risk,
        "verdict": verdict, "action": action, "reasons": reasons[:5], "checked_at": q.get("checked_at", now_label()),
        "src": q.get("src", "KIS"),
    }


def smart_money_live_scan(data=None):
    items = []
    for n in smart_money_watchlist(data):
        try:
            items.append(smart_money_live_item(n))
        except Exception as e:
            items.append({"ok": False, "name": n, "score": 0, "verdict": "오류", "action": "확인", "reason": str(e)[:120]})
    return sorted(items, key=lambda x: (x.get("ok", False), x.get("score", 0), -x.get("exit_risk", 0)), reverse=True)


def render_smart_money_live_v122(data=None, compact=False):
    items = smart_money_live_scan(data)
    ok_items = [x for x in items if x.get("ok")]
    top = ok_items[0] if ok_items else None
    if top:
        headline = f'{top["name"]} · {top["verdict"]}'
        score_line = f'스마트머니 {top["score"]}점 · 이탈위험 {top.get("exit_risk",0)}점'
        sub = f'시간보정 거래량 {top.get("vol_ratio",0):.0f}% · 거래대금 {top.get("amt_ratio",0):.0f}% · 등락 {top.get("change",0):+.2f}%' 
    else:
        headline = "조회 성공 종목 없음"
        score_line = "KIS 키/토큰/종목코드 확인 필요"
        sub = "V121-4 현재가 조회가 성공했는지 먼저 확인하세요."

    html = (
        '<div class="db-card">'
        '<div class="db-title">🔥 V122-2 Real Volume Engine</div>'
        '<div class="db-sub">현재가보다 거래량·거래대금을 먼저 보고, 장중 시간보정 기준으로 세력 유입/분산/이탈 가능성을 1차 판정합니다.</div>'
        f'<div class="db-action">1순위: {headline}<br>{score_line}<br>{sub}</div>'
    )
    show_items = ok_items[:3] if compact else ok_items[:8]
    for idx, x in enumerate(show_items, start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        reasons = " · ".join(x.get("reasons", []))
        html += (
            '<div class="db-row">'
            f'<div class="db-name">{medal} {x.get("name")} · {x.get("code")} · {x.get("verdict")}</div>'
            f'<div class="db-meta">현재가 {won(x.get("price"))} · 등락 {x.get("change",0):+.2f}% · 행동 {x.get("action")}<br>'
            f'현재 거래량 {volume_text(x.get("volume"))} · 기대 {volume_text(x.get("expected_volume"))} · 시간보정 {x.get("vol_ratio",0):.0f}%<br>'
            f'현재 거래대금 {amount_text(x.get("amount"))} · 기대 {amount_text(x.get("expected_amount"))} · 시간보정 {x.get("amt_ratio",0):.0f}%<br>'
            f'하루평균 대비 거래량 {x.get("day_vol_ratio",0):.1f}% · 거래대금 {x.get("day_amt_ratio",0):.1f}% · {x.get("progress_label", "-")}<br>'
            f'스마트머니 {x.get("score",0)}점 · 이탈위험 {x.get("exit_risk",0)}점 · {reasons}<br>확인 {x.get("checked_at", now_label())}</div>'
            '</div>'
        )
    failed = [x for x in items if not x.get("ok")]
    if failed and not compact:
        html += '<div class="db-sub"><b>조회 실패 종목</b><br>' + '<br>'.join([f'{x.get("name")}: {x.get("reason", x.get("verdict", "실패"))}' for x in failed[:5]]) + '</div>'
    html += '<div class="db-sub">※ V122-2는 하루 평균 기준선을 현재 장중 경과시간으로 보정합니다. 다음 단계에서 5일/20일 평균과 체결강도까지 강화합니다.</div></div>'
    st.markdown(html, unsafe_allow_html=True)


# V122-1: KIS TOKEN CACHE HOTFIX
# 목적: 앱 새로고침/화면 이동 때마다 한국투자 접근토큰이 새로 발급되어 카톡 문자가 반복되는 문제를 막습니다.
# 원칙: 24시간 유효 토큰은 로컬 런타임 파일에 저장하고, 만료 전에는 반드시 재사용합니다.
KIS_TOKEN_CACHE_FILE = Path(".kis_token_cache.json")


def _kis_token_cache_key(app_key, app_secret, paper):
    return short_hash(f"{app_key}|{app_secret}|{paper}", 16)


def _read_kis_token_cache():
    try:
        if KIS_TOKEN_CACHE_FILE.exists():
            with open(KIS_TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def _write_kis_token_cache(data):
    try:
        with open(KIS_TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _utc_now_dt():
    return datetime.utcnow()


def _parse_cache_expire(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcfromtimestamp(0)


def kis_stable_token_info(force_new=False):
    app_key, app_secret, paper = kis_credentials()
    if not app_key or not app_secret:
        return {"ok": False, "status": "키 없음", "error": "KIS_APP_KEY 또는 KIS_APP_SECRET이 없습니다.", "token": "", "cached": False, "source": "none"}

    cache_key = _kis_token_cache_key(app_key, app_secret, paper)
    cache = _read_kis_token_cache()
    now = _utc_now_dt()

    if not force_new:
        exp = _parse_cache_expire(cache.get("expires_at_utc", ""))
        token = str(cache.get("access_token", "") or "")
        # 만료 10분 전까지는 기존 토큰 재사용
        if token and cache.get("cache_key") == cache_key and exp > now + timedelta(minutes=10):
            return {
                "ok": True,
                "status": "재사용",
                "error": "",
                "token": token,
                "cached": True,
                "source": "file_cache",
                "expires_at_utc": cache.get("expires_at_utc", ""),
                "issued_at_utc": cache.get("issued_at_utc", ""),
            }

    try:
        url = f"{kis_base_url()}/oauth2/tokenP"
        payload = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
        r = requests.post(url, json=payload, timeout=8)
        try:
            js = r.json()
        except Exception:
            js = {"raw": r.text[:200]}
        token = js.get("access_token", "") if isinstance(js, dict) else ""
        if r.status_code == 200 and token:
            # 한국투자 안내 기준 24시간. 안전하게 23시간 30분만 사용.
            issued = now
            expires = now + timedelta(hours=23, minutes=30)
            cache_data = {
                "cache_key": cache_key,
                "paper": bool(paper),
                "access_token": token,
                "issued_at_utc": issued.strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at_utc": expires.strftime("%Y-%m-%d %H:%M:%S"),
                "last_status": f"HTTP {r.status_code}",
            }
            _write_kis_token_cache(cache_data)
            return {"ok": True, "status": "신규발급", "error": "", "token": token, "cached": False, "source": "new_issue", **cache_data}
        return {"ok": False, "status": f"HTTP {r.status_code}", "error": str(js)[:220], "token": "", "cached": False, "source": "issue_failed"}
    except Exception as e:
        return {"ok": False, "status": "요청 실패", "error": str(e)[:220], "token": "", "cached": False, "source": "exception"}


# 기존 함수명 override: 앱 전체가 같은 토큰 캐시를 사용하게 고정합니다.
def kis_access_token():
    info = kis_stable_token_info(force_new=False)
    return info.get("token", "") if info.get("ok") else ""


def kis_direct_token_test():
    return kis_stable_token_info(force_new=False)


def kis_direct_price_test(name="삼성전자"):
    """V122-1: 토큰 재발급 없이 캐시 토큰으로 현재가/거래량/거래대금 조회."""
    n = norm(name)
    code = code_map().get(n)
    if not code:
        return {"ok": False, "name": n, "code": "", "error": "종목코드 없음"}
    token_info = kis_stable_token_info(force_new=False)
    if not token_info.get("ok"):
        return {"ok": False, "name": n, "code": code, "status": token_info.get("status", "토큰 실패"), "error": f"토큰 실패: {token_info.get('status')} / {token_info.get('error', '')}"}
    app_key, app_secret, _ = kis_credentials()
    try:
        url = f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token_info.get('token')}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST01010100",
        }
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        r = requests.get(url, headers=headers, params=params, timeout=7)
        try:
            js = r.json()
        except Exception:
            js = {"raw": r.text[:200]}
        if r.status_code != 200:
            return {"ok": False, "name": n, "code": code, "status": f"HTTP {r.status_code}", "error": str(js)[:220]}
        out = js.get("output", {}) if isinstance(js, dict) else {}
        if not out:
            return {"ok": False, "name": n, "code": code, "status": "응답 없음", "error": str(js)[:220]}
        price = parse_price(out.get("stck_prpr"))
        volume = parse_price(out.get("acml_vol"))
        amount = parse_price(out.get("acml_tr_pbmn"))
        change_rate = None
        try:
            change_rate = float(str(out.get("prdy_ctrt", "")).replace(",", ""))
        except Exception:
            change_rate = 0.0
        return {
            "ok": True,
            "name": n,
            "code": code,
            "price": price,
            "volume": volume,
            "amount": amount,
            "change_rate": change_rate,
            "src": f"KIS {code}",
            "checked_at": now_label(),
            "token_status": token_info.get("status", "-"),
            "token_cached": token_info.get("cached", False),
        }
    except Exception as e:
        return {"ok": False, "name": n, "code": code, "status": "요청 실패", "error": str(e)[:220]}


def render_kis_token_cache_status():
    info = kis_stable_token_info(force_new=False)
    app_key, app_secret, paper = kis_credentials()
    status = "✅ 기존 토큰 재사용" if info.get("cached") else ("⚠️ 신규 토큰 발급" if info.get("ok") else "❌ 토큰 확인 실패")
    exp = info.get("expires_at_utc", "-")
    issued = info.get("issued_at_utc", "-")
    html = (
        '<div class="db-card">'
        '<div class="db-title">🔐 V122-1 KIS 토큰 캐시 상태</div>'
        '<div class="db-sub">새로고침/탭 이동 때마다 토큰을 새로 발급하지 않고 24시간 동안 재사용합니다.</div>'
        f'<div class="db-action">판정: {status}<br>투자구분: {"모의" if paper else "실전"} · 키상태: {"인식" if app_key and app_secret else "없음"}</div>'
        '<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">토큰상태</div><div class="db-value">{info.get("status", "-")}</div></div>'
        f'<div class="db-box"><div class="db-label">캐시사용</div><div class="db-value">{"예" if info.get("cached") else "아니오"}</div></div>'
        f'<div class="db-box"><div class="db-label">발급시각(UTC)</div><div class="db-value">{issued}</div></div>'
        f'<div class="db-box"><div class="db-label">만료예정(UTC)</div><div class="db-value">{exp}</div></div>'
        '</div>'
        '<div class="db-sub">※ 이 카드 확인 후 새로고침했을 때 한국투자 알림톡이 또 오지 않으면 캐시가 정상입니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def smart_money_data_status():
    kis = kis_ready()
    return {
        "quote_volume": "한국투자/KIS 현재가·거래량 연결" if kis else "네이버 현재가/일별거래량 1차 연결",
        "trading_value": "한국투자/KIS 거래대금 연결" if kis else "현재가×거래량 추정 연결",
        "institution": "KIS 투자자 수급 연결 준비" if kis else "API 키 연결 전",
        "foreign": "KIS 투자자 수급 연결 준비" if kis else "API 키 연결 전",
        "kis_ready": kis,
        "kiwoom_ready": env_or_secret_exists("KIWOOM_APP_KEY", "KIWOOM_SECRET", "KIWOOM_TOKEN"),
    }

@st.cache_data(ttl=300, show_spinner=False)
def fetch_daily_ohlcv(name, pages=2):
    """네이버 일별시세에서 최근 일봉 OHLCV를 가져옵니다.
    반환: [{date, close, open, high, low, volume}]
    장중에는 당일 행이 포함될 수 있어 V121 스마트머니 1차 데이터로 사용합니다.
    """
    n = norm(name)
    code = code_map().get(n)
    if not code:
        return []
    rows = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for page in range(1, int(pages or 1) + 1):
        try:
            url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"
            html = requests.get(url, headers=headers, timeout=4).text
            # 한 행 안의 span 값: 날짜, 종가, 전일비, 시가, 고가, 저가, 거래량
            for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", html):
                vals = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<span[^>]*>([\s\S]*?)</span>", tr)]
                vals = [v.replace("\xa0", "").strip() for v in vals if v and v.strip()]
                if len(vals) >= 7 and re.match(r"\d{4}\.\d{2}\.\d{2}", vals[0]):
                    try:
                        rows.append({
                            "date": vals[0],
                            "close": parse_price(vals[1]) or 0,
                            "open": parse_price(vals[3]) or 0,
                            "high": parse_price(vals[4]) or 0,
                            "low": parse_price(vals[5]) or 0,
                            "volume": parse_price(vals[6]) or 0,
                        })
                    except Exception:
                        pass
        except Exception:
            pass
    # 날짜 중복 제거, 최신순 유지
    uniq = []
    seen = set()
    for r in rows:
        if r.get("date") not in seen and r.get("close", 0) > 0:
            uniq.append(r)
            seen.add(r.get("date"))
    return uniq

def avg_num(vals):
    vals = [sf(v) for v in vals if sf(v) > 0]
    return sum(vals) / len(vals) if vals else 0

def smart_money_metric(name):
    n = norm(name)
    kis_price = kis_inquire_price(n) if "kis_inquire_price" in globals() else None
    price_detail = fetch_price_detail(n)
    daily = fetch_daily_ohlcv(n, pages=2)
    latest = daily[0] if daily else {}
    prev = daily[1] if len(daily) > 1 else {}
    kis_ok = bool(kis_price and kis_price.get("ok"))
    price = sf((kis_price or {}).get("price") or price_detail.get("price") or latest.get("close") or fallback_price(n), 0)
    today_vol = sf((kis_price or {}).get("volume") or latest.get("volume") or price_detail.get("volume"), 0)
    avg5 = avg_num([x.get("volume") for x in daily[1:6]])
    avg20 = avg_num([x.get("volume") for x in daily[1:21]]) or avg5
    vol_ratio = today_vol / avg20 if avg20 else 0
    amount = sf((kis_price or {}).get("amount"), 0) or (price * today_vol if price and today_vol else 0)
    closes = [sf(x.get("close")) for x in daily[:21] if sf(x.get("close"))]
    ma5 = avg_num(closes[:5])
    ma20 = avg_num(closes[:20])
    high20 = max(closes[1:21]) if len(closes) > 1 else 0
    open_p = sf(latest.get("open"), 0)
    high_p = sf(latest.get("high"), 0)
    close_p = sf(latest.get("close") or price, 0)
    prev_close = sf(prev.get("close"), 0)
    day_change = ((close_p / prev_close - 1) * 100) if close_p and prev_close else price_detail.get("change_rate")
    upper_wick = ((high_p - max(open_p, close_p)) / close_p * 100) if high_p and close_p else 0

    # 유입점수: 거래량/거래대금/차트 중심, 수급은 API 연결 전 중립으로 둡니다.
    vol_score = 35
    if vol_ratio >= 5: vol_score = 100
    elif vol_ratio >= 3: vol_score = 88
    elif vol_ratio >= 2: vol_score = 74
    elif vol_ratio >= 1.5: vol_score = 62
    elif vol_ratio >= 1.1: vol_score = 52

    amount_eok = amount / 100000000 if amount else 0
    amount_score = 35
    if amount_eok >= 1000: amount_score = 95
    elif amount_eok >= 500: amount_score = 85
    elif amount_eok >= 200: amount_score = 75
    elif amount_eok >= 100: amount_score = 65
    elif amount_eok >= 30: amount_score = 55

    chart_score = 40
    chart_reasons = []
    if ma5 and ma20 and ma5 > ma20:
        chart_score += 18; chart_reasons.append("5일선이 20일선 위")
    if close_p and ma20 and close_p > ma20:
        chart_score += 16; chart_reasons.append("종가가 20일선 위")
    if high20 and close_p >= high20 * 0.97:
        chart_score += 18; chart_reasons.append("20일 고점 접근")
    if day_change is not None and sf(day_change) > 0:
        chart_score += 8; chart_reasons.append("당일 상승 흐름")
    chart_score = max(0, min(100, int(chart_score)))

    supply_score = 50  # V121-1에서는 기관/외국인 API 연결 전 중립
    news_bonus = 50
    inflow = int(vol_score * 0.30 + amount_score * 0.25 + chart_score * 0.30 + supply_score * 0.10 + news_bonus * 0.05)

    # 이탈점수: 거래량은 늘었는데 주가가 못 오르거나 윗꼬리/하락이면 경고
    exit_score = 20
    exit_reasons = []
    if vol_ratio >= 2:
        exit_score += 20; exit_reasons.append("거래량 급증")
    if day_change is not None and sf(day_change) <= 0:
        exit_score += 20; exit_reasons.append("거래량 대비 주가 상승 실패")
    if upper_wick >= 2:
        exit_score += 18; exit_reasons.append("윗꼬리 발생")
    if open_p and close_p and close_p < open_p:
        exit_score += 12; exit_reasons.append("음봉 마감/진행")
    if ma5 and close_p and close_p < ma5:
        exit_score += 10; exit_reasons.append("5일선 아래")
    exit_score = max(0, min(100, int(exit_score)))

    if inflow >= 80:
        inflow_label = "🟢 강한 유입"
    elif inflow >= 65:
        inflow_label = "🟡 유입 관찰"
    else:
        inflow_label = "⚪ 유입 약함"
    if exit_score >= 75:
        exit_label = "🔴 이탈 의심"
    elif exit_score >= 55:
        exit_label = "🟠 이탈 주의"
    else:
        exit_label = "🟢 이탈 낮음"

    reasons = []
    if vol_ratio:
        reasons.append(f"거래량 {vol_ratio:.1f}배")
    if amount_eok:
        reasons.append(f"거래대금 {amount_eok:.0f}억")
    reasons.extend(chart_reasons[:2])
    if not reasons:
        reasons.append("실시간 거래 데이터 확인 대기")

    return {
        "name": n, "price": price, "volume": today_vol, "avg20_volume": avg20, "vol_ratio": vol_ratio,
        "amount": amount, "amount_eok": amount_eok, "ma5": ma5, "ma20": ma20, "day_change": day_change,
        "upper_wick": upper_wick, "inflow": inflow, "inflow_label": inflow_label,
        "exit": exit_score, "exit_label": exit_label, "reasons": reasons[:4], "exit_reasons": exit_reasons[:4],
        "data_date": latest.get("date", "실시간") if not kis_ok else "실시간", "data_src": (kis_price.get("src") if kis_ok else price_detail.get("src", "네이버")),
    }

def smart_money_universe(data=None):
    names = []
    try:
        for h in (data or {}).get("holdings", []):
            n = norm(h.get("name", ""))
            if n and n not in names:
                names.append(n)
    except Exception:
        pass
    for n in ["대한전선", "한미반도체", "하나마이크론", "이수페타시스", "LS ELECTRIC", "효성중공업", "레인보우로보틱스", "두산로보틱스", "비에이치아이", "우진"]:
        if n not in names:
            names.append(n)
    return names

@st.cache_data(ttl=300, show_spinner=False)
def smart_money_scan_cached(names_tuple):
    out = []
    for n in list(names_tuple):
        try:
            out.append(smart_money_metric(n))
        except Exception:
            pass
    return out

def smart_money_scan(data=None):
    return smart_money_scan_cached(tuple(smart_money_universe(data)))

def render_smart_money_v121(data, compact=False):
    items = smart_money_scan(data)
    status = smart_money_data_status()
    inflows = sorted(items, key=lambda x: x.get("inflow", 0), reverse=True)
    exits = sorted([x for x in items if x.get("exit", 0) >= 55], key=lambda x: x.get("exit", 0), reverse=True)
    if compact:
        top = inflows[0] if inflows else None
        if not top:
            card("⚡ 스마트머니 V121-1", "실시간 거래량 데이터를 불러오는 중입니다.")
            return
        body = f'<b>{top["name"]}</b> · 유입 {top["inflow"]}점 · {top["inflow_label"]}<br>근거: {" · ".join(top.get("reasons", []))}<br>데이터: {top.get("data_date", "-")} · {top.get("data_src", "-")}'
        if exits:
            body += f'<br><br>⚠ 이탈주의: <b>{exits[0]["name"]}</b> · {exits[0]["exit"]}점 · {" · ".join(exits[0].get("exit_reasons", []))}'
        card("⚡ 스마트머니 V121-1", body)
        return

    st.markdown('<div class="brief-card"><div class="brief-title">⚡ 스마트머니 V121-1</div><div class="brief-sub">뉴스보다 먼저 움직이는 거래량·거래대금·차트 이상징후를 포착합니다. 기관/외국인 수급은 다음 단계에서 투자자매매동향 API로 확장합니다.</div></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="brief-card"><div class="brief-title">🔌 데이터 연결 상태</div>'
        f'<div class="brief-grid">'
        f'<div class="brief-box"><div class="brief-label">거래량</div><div class="brief-value">{status["quote_volume"]}</div></div>'
        f'<div class="brief-box"><div class="brief-label">거래대금</div><div class="brief-value">{status["trading_value"]}</div></div>'
        f'<div class="brief-box"><div class="brief-label">기관수급</div><div class="brief-value">{status["institution"]}</div></div>'
        f'<div class="brief-box"><div class="brief-label">외국인수급</div><div class="brief-value">{status["foreign"]}</div></div>'
        f'</div><div class="brief-reason">한국투자/KIS API 키 상태: {"연결 준비됨" if status.get("kis_ready") else "미연결"} · 키움 API 키 상태: {"연결 준비됨" if status.get("kiwoom_ready") else "미연결"}<br>※ API 키 값은 화면에 표시하지 않습니다.</div></div>',
        unsafe_allow_html=True
    )
    with st.expander("🔐 한국투자 Open API 키 설정 방법", expanded=False):
        st.markdown("""
PC 로컬에서는 프로젝트 폴더에 `.streamlit/secrets.toml` 파일을 만들고 아래 형식으로 저장하세요.

```toml
KIS_APP_KEY = "발급받은_APP_KEY"
KIS_APP_SECRET = "발급받은_APP_SECRET"
KIS_PAPER = "false"
```

Streamlit Cloud에서는 앱 Settings → Secrets에 같은 내용을 넣으면 됩니다.
키 값은 화면에 표시하지 않고, 연결 여부만 확인합니다.
""")
        if status.get("kis_ready"):
            st.success("KIS API 키가 감지되었습니다. 현재가·거래량·거래대금은 KIS 우선으로 조회합니다.")
        else:
            st.warning("아직 KIS API 키가 감지되지 않았습니다. secrets.toml 또는 Streamlit Secrets를 확인하세요.")

    st.markdown('<div class="brief-card"><div class="brief-title">🟢 스마트머니 유입 후보 TOP</div>', unsafe_allow_html=True)
    for idx, x in enumerate(inflows[:5], start=1):
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else "▫️"))
        st.markdown(
            f'<div class="brief-box"><div class="brief-label">{medal} {x["name"]} · {x["inflow_label"]}</div>'
            f'<div class="brief-value">유입점수 {x["inflow"]}점 · 이탈점수 {x["exit"]}점</div>'
            f'<div class="brief-reason">거래량 {x.get("vol_ratio",0):.1f}배 · 거래대금 {x.get("amount_eok",0):.0f}억 · 등락 {sf(x.get("day_change"),0):+.2f}%<br>근거: {" · ".join(x.get("reasons", []))}<br>데이터일자 {x.get("data_date", "-")}</div></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    if exits:
        st.markdown('<div class="brief-card"><div class="brief-title">🔴 스마트머니 이탈 의심</div>', unsafe_allow_html=True)
        for x in exits[:5]:
            st.markdown(
                f'<div class="brief-box"><div class="brief-label">{x["name"]} · {x["exit_label"]}</div>'
                f'<div class="brief-value">이탈점수 {x["exit"]}점</div>'
                f'<div class="brief-reason">근거: {" · ".join(x.get("exit_reasons", []))}<br>거래량 {x.get("vol_ratio",0):.1f}배 · 등락 {sf(x.get("day_change"),0):+.2f}%</div></div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        card("🔴 스마트머니 이탈 의심", "현재 후보군에서 강한 이탈 의심 신호는 없습니다.")


def home(data):
    # V108-2 VERIFIED: 홈은 컴파스 점수 / 오늘 행동 / 위험 레이더 / 발굴 TOP3만 먼저 보여줍니다.
    header()
    render_kis_live_quote_strip(data, title="📡 KIS 실시간 데이터 바로보기 · 홈")
    render_kis_token_cache_status()
    render_smart_money_live_v122(data, compact=True)
    render_backtest_tracker_v1231(data, compact=True)
    render_historical_data_test_v1241(data, compact=True)
    render_historical_replay_v1242(data, compact=True)
    render_loss_minimizer_v1243(data, compact=True)
    render_audit_mode_v1244(data, compact=True)
    render_bulk_historical_replay_v1245(data, compact=True)
    render_hypothesis_experiment_v1246(data, compact=True)
    render_profit_finder_v1247(data, compact=True)
    render_failure_analyzer_v1249(data, compact=True)
    render_support_analyzer_v12410(data, compact=True)
    render_fake_bottom_killer_v12411(data, compact=True)
    render_validation_lab_v12412(data, compact=True)
    render_combo_validation_lab_v12413(data, compact=True)
    render_compass_gauge(data)
    render_smart_money_v121(data, compact=True)
    render_action(data, show_detail=False)
    render_real_drop_defense(data)
    try:
        render_v106_risk_radar(data)
    except Exception:
        render_emergency_board(data)
    render_discovery_top3_cards(data)

    with st.expander("🧭 내 보유종목 자동판정 V117-1", expanded=False):
        render_portfolio_auto_judge_v1171(data, compact=True)

    with st.expander("🎯 좋은하락/나쁜하락 엔진 V117", expanded=False):
        render_v117_good_bad_summary(data, compact=True)

    with st.expander("전문가용 V114~V116 핵심 엔진 보기", expanded=False):
        render_core_engine_summary(data)

    with st.expander("고급 분석 엔진 보기", expanded=False):
        st.caption("기존 기능은 삭제하지 않았고, 결론 생성용 내부 엔진으로 유지합니다.")
        try:
            render_news_conclusion(data)
            render_supply_chain_discovery(data)
            render_rebalance_summary(data)
            render_target_price_summary(data)
            render_future_probability_summary(data)
        except Exception as e:
            st.caption(f"고급 분석 일부를 불러오지 못했습니다: {e}")

    if st.button("🔄 새로고침 / 다시 판단하기", use_container_width=True):
        st.rerun()


def find_holding(data, name):
    n = norm(name)
    for idx, h in enumerate(data.get("holdings", [])):
        if norm(h.get("name", "")) == n:
            return idx, h
    return None, None


def apply_actual_holdings_v113(data):
    """V113: 사용자 계좌 캡처 기준 실제 총 보유수량을 PC Master DB에 강제 반영합니다. 평단은 기존값을 유지합니다."""
    target_qty = {
        "에스피시스템스": 60,
        "제룡전기": 14,
        "ACE AI반도체 TOP3": 23,
        "KODEX 미국S&P500": 42,
        "LG디스플레이": 20,
    }
    default_avg = {
        "에스피시스템스": 6863,
        "제룡전기": 53469,
        "ACE AI반도체 TOP3": 64544,
        "KODEX 미국S&P500": 25616,
        "LG디스플레이": 14908,
    }
    data.setdefault("holdings", [])
    changes = []
    for name, qty in target_qty.items():
        idx, h = find_holding(data, name)
        if h:
            old_qty = sf(h.get("qty"))
            h.update({"name": name, "qty": float(qty), "avg": float(default_avg.get(name, sf(h.get("avg"), 0))), "updated_at": now_label(), "qty_input_mode": "TOTAL_HOLDING_QTY_V113_REAL_AVG"})
            changes.append(f"{name}: {old_qty:g}주 → {qty:g}주")
        else:
            data["holdings"].append({"name": name, "qty": float(qty), "avg": default_avg.get(name, 0), "updated_at": now_label(), "qty_input_mode": "TOTAL_HOLDING_QTY_V113"})
            changes.append(f"{name}: 신규 {qty:g}주")
    save_data(data)
    return changes

def render_v113_actual_holdings_fix(data):
    if not can_write_db():
        return
    st.markdown(
        '<div class="db-card"><div class="db-title">🧷 V113 실제 보유수량 강제 반영</div>'
        '<div class="db-sub">증권앱 캡처 기준 현재 총 보유수량으로 PC Master DB를 맞춥니다. 평단은 기존값을 유지합니다.</div>'
        '<div class="db-action">반영값: 에스피시스템스 60주 · 제룡전기 14주 · ACE AI반도체 TOP3 23주 · KODEX 미국S&P500 42주 · LG디스플레이 20주</div></div>',
        unsafe_allow_html=True
    )
    if st.button("🧷 실제 보유수량 5종목 바로 반영", use_container_width=True, key="apply_actual_holdings_v113"):
        changes = apply_actual_holdings_v113(data)
        st.success(" / ".join(changes))
        st.rerun()

def render_trade_panel(data):
    if not can_write_db():
        read_only_notice()
        return
    st.subheader("➕ 보유수량/매도 입력")
    st.info("V113 기준: 매수 입력은 '오늘 산 수량'이 아니라 증권앱에 보이는 '현재 총 보유수량'을 입력합니다. 예: 에스피시스템스가 총 60주면 60을 입력합니다.")

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
        st.caption("신규 종목입니다. 현재 총 보유수량과 현재 평단가를 입력하면 보유종목에 추가됩니다.")
    else:
        st.caption("새 종목은 종목명을 먼저 입력한 뒤 현재 총 보유수량과 현재 평단가를 저장하세요.")

    tab_buy, tab_sell = st.tabs(["현재 보유수량 맞추기", "매도"])

    with tab_buy:
        b1, b2 = st.columns(2)
        with b1:
            default_total_qty = float(sf(holding.get("qty"))) if holding else 0.0
            buy_qty = st.number_input("현재 총 보유수량", min_value=0.0, value=default_total_qty, step=1.0, key="buy_qty_v2")
        with b2:
            default_avg = float(sf(holding.get("avg"))) if holding else 0.0
            buy_avg = st.number_input("현재 평단가", min_value=0.0, value=default_avg, step=100.0, key="buy_avg_v2")
        if holding:
            old_qty_preview, old_avg_preview = sf(holding.get("qty")), sf(holding.get("avg"))
            st.caption(f"저장 전 확인: {norm(name)} {old_qty_preview:g}주 → {buy_qty:g}주 / 평단 {won(old_avg_preview)} → {won(buy_avg)}")
        if st.button("현재 총 보유수량 저장", use_container_width=True, key="buy_save_v2"):
            if name and buy_qty > 0 and buy_avg > 0:
                n = norm(name)
                idx, h = find_holding(data, n)
                if h:
                    old_qty, old_avg = sf(h.get("qty")), sf(h.get("avg"))
                    h.update({"name": n, "qty": buy_qty, "avg": buy_avg, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "qty_input_mode": "TOTAL_HOLDING_QTY"})
                    st.success(f"수량 맞춤 완료: {n} {old_qty:g}주 → {buy_qty:g}주")
                else:
                    data["holdings"].append({"name": n, "qty": buy_qty, "avg": buy_avg, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "qty_input_mode": "TOTAL_HOLDING_QTY"})
                    st.success(f"신규 종목 저장 완료: {n} {buy_qty:g}주")
                save_data(data)
                st.rerun()
            else:
                st.warning("종목명, 현재 총 보유수량, 현재 평단가를 확인하세요.")

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



def holding_decision_summary(n, q, a, r, weights, target):
    try:
        score, sig, reason = stock_signal(n, q, a, r, weights, target)
    except Exception:
        score, sig, reason = 50, "🟠 관망", "판단 데이터가 부족합니다."
    try:
        grade, risk_reason = risk_grade_simple(n, r)
    except Exception:
        grade, risk_reason = "🟡 주의", "위험등급 계산 데이터가 부족합니다."
    try:
        b = stock_briefing_data(n, r, None)
        conf = int(b.get("total", score))
    except Exception:
        conf = score
    return score, sig, reason, grade, risk_reason, conf


def render_holding_compact(i, data, n, q, a, r, weights, target):
    score, sig, reason, grade, risk_reason, conf = holding_decision_summary(n, q, a, r, weights, target)
    try:
        mq = move_quality_judgement(n, r, data, weights)
    except Exception:
        mq = {"label": "⚪ 흐름 확인", "action": "관망", "summary": "가격흐름 판정 데이터가 부족합니다.", "core": conf}
    cls = "profit" if r and r.get("profit", 0) >= 0 else "loss"
    profit_line = "현재가 확인중"
    if r:
        profit_line = f'현재가 {won(r["price"])} · 오늘 {r.get("change_text", "등락률 확인불가")} · 평가 {won(r["value"])} · <span class="{cls}">{r["rate"]:.2f}%</span>'

    st.markdown(
        f'<div class="hold">'
        f'<div class="hold-name">{n}</div>'
        f'<div class="meta">행동: <b>{sig}</b> · 위험도: <b>{grade}</b> · 신뢰도 {conf}점</div>'
        f'<div class="eval">{profit_line}<br><b>{mq.get("label", "⚪ 흐름 확인")}</b> · {mq.get("action", "관망")} · 신뢰도 {mq.get("confidence", conf)}%<br>{mq.get("summary", reason)}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    with st.expander(f"{n} 상세보기", expanded=False):
        st.markdown(f"**위험 판단**  \n{risk_reason}")
        try:
            gd_detail = good_bad_drop_engine(n, r, data, weights)
            render_good_bad_drop_card(gd_detail, "내 종목 하락판단")
        except Exception:
            pass
        try:
            render_stock_briefing(n, r, data, title_prefix="내 종목 최종 판단")
        except Exception:
            pass
        try:
            render_buy_timing_card_safe(safe_timing_score(n, r), "매수타이밍")
        except Exception:
            pass
        try:
            item = value_dividend_score(n, r)
            st.markdown(f'**저평가·성장성:** {item.get("score", 0)}점 · {item.get("action", "-")}')
        except Exception:
            pass
        try:
            plan = target_price_plan(n, r, data)
            if plan:
                render_target_price_card(plan, "목표가/손절가")
        except Exception:
            pass
        try:
            fp = future_probability_score(n, r, data)
            render_future_probability_card(fp, "미래확률")
        except Exception:
            pass

        with st.expander("현재 총 보유수량/평단 수정", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                new_qty = st.number_input("현재 총 보유수량", min_value=0.0, value=float(q), step=1.0, key=f"q_v106_{i}")
            with c2:
                new_avg = st.number_input("평단 수정", min_value=0.0, value=float(a), step=100.0, key=f"a_v106_{i}")
            b1, b2 = st.columns(2)
            with b1:
                st.caption(f"저장 전 확인: {n} {float(q):g}주 → {new_qty:g}주 / 평단 {won(a)} → {won(new_avg)}")
                if st.button("현재 총 보유수량 저장", use_container_width=True, key=f"u_v106_{i}"):
                    if new_qty <= 0:
                        data["holdings"].pop(i)
                    else:
                        data["holdings"][i].update({"name": n, "qty": new_qty, "avg": new_avg})
                    save_data(data)
                    st.rerun()
            with b2:
                if st.button("삭제", use_container_width=True, key=f"d_v106_{i}"):
                    data["holdings"].pop(i)
                    save_data(data)
                    st.rerun()


def holdings(data):
    header()
    card("내종목", "종목별로 행동 · 위험도 · 신뢰도만 먼저 보여줍니다. 매수/매도와 전체순위는 필요할 때만 엽니다.")
    card("DB 권한", db_role_label())
    render_v113_actual_holdings_fix(data)

    if st.checkbox("➕ 매수/매도 입력 열기", value=False, key="trade_panel_toggle_v1071"):
        render_trade_panel(data)

    if st.checkbox("📷 토스 수량 갱신 열기", value=False, key="toss_panel_toggle_v1071"):
        render_toss_portfolio_sync(data)

    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        weights, rows = {}, []
    target = target_return(data)

    if not rows:
        st.info("보유종목이 없습니다.")
        return

    st.subheader("📦 보유종목 행동 요약")
    render_portfolio_auto_judge_v1171(data)
    for i, (n, q, a, r) in enumerate(rows):
        render_holding_compact(i, data, n, q, a, r, weights, target)

    st.markdown("---")
    st.markdown("### 고급 전체순위")
    st.caption("평소에는 숨겨두고, 필요할 때만 선택해서 봅니다.")

    adv = st.selectbox(
        "볼 항목 선택",
        ["선택안함", "매수타이밍", "저평가·배당·성장성", "리밸런싱", "목표가", "미래확률", "전체 보기"],
        key="advanced_rank_select_v1071"
    )

    try:
        if adv == "매수타이밍":
            render_buy_timing_ranking(data)
        elif adv == "저평가·배당·성장성":
            render_value_dividend_ranking(data)
        elif adv == "리밸런싱":
            render_rebalance_detail(data)
        elif adv == "목표가":
            render_target_price_ranking(data)
        elif adv == "미래확률":
            render_future_probability_ranking(data)
        elif adv == "전체 보기":
            render_buy_timing_ranking(data)
            render_value_dividend_ranking(data)
            render_rebalance_detail(data)
            render_target_price_ranking(data)
            render_future_probability_ranking(data)
    except Exception as e:
        st.caption(f"고급 전체순위 일부를 불러오지 못했습니다: {e}")

@st.cache_data(ttl=900, show_spinner=False)
def rss_items():
    items = []
    sources = [
        ("연합뉴스 경제", "https://www.yna.co.kr/rss/economy.xml"),
        ("한국경제", "https://www.hankyung.com/feed/economy"),
    ]
    for source, url in sources:
        try:
            root = ET.fromstring(requests.get(url, timeout=5, headers={"User-Agent":"Mozilla/5.0"}).content)
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
    # V102_NEWS_RETURN: 뉴스 원문 목록 숨김
    render_news_conclusion(data)
    st.caption('뉴스 원문은 내부 분석에만 사용합니다.')
    return
    header()
    card("뉴스", "보유종목과 연결되는 실제 RSS 뉴스를 우선 표시하고, 제목 기준으로 긍정/부정 영향을 간단히 분류합니다.")

    shown = render_related_news_by_holding(data)

    if not shown:
        card("관련 뉴스 없음", "현재 RSS 안에서는 보유종목과 직접 연결되는 뉴스가 적습니다. 일반 경제뉴스를 표시합니다.")
        shown_count = 0
        for source, title, link in rss_items()[:10]:
            impact, _ = news_impact(title)
            card(title, f"영향: {impact}<br>출처: {source}<br><a href='{link}' target='_blank'>원문 보기</a>")
            shown_count += 1
            if shown_count >= 10:
                break



# V119: 위험원인 분석 엔진
# V118 위험레이더를 실전형으로 확장합니다.
# 정상 종목은 숨기고, 위험/주의 종목만 원인별 점수와 행동까지 표시합니다.
def risk_category_scores_v119(name, r=None, data=None, weights=None):
    n = norm(name)
    sec = sector(n)
    weights = weights or {}
    rate = 0.0
    today = None
    try:
        rate = float((r or {}).get("rate", 0) or 0)
    except Exception:
        rate = 0.0
    try:
        v = (r or {}).get("change_rate", None)
        today = None if v is None else float(v)
    except Exception:
        today = None

    # 1) 실적/체력 위험: 실제 실적 API가 붙기 전까지는 미래확률·가치점수·섹터 특성을 대리값으로 사용
    performance = 15
    performance_reasons = []
    try:
        fut = future_probability_score(n, r, data) if "future_probability_score" in globals() else {"p12": 60}
        p12 = int(fut.get("p12", 60) or 60)
        if p12 <= 50:
            performance += 35
            performance_reasons.append(f"12개월 기대확률 {p12}%로 낮음")
        elif p12 <= 58:
            performance += 20
            performance_reasons.append(f"12개월 기대확률 {p12}%로 약함")
        elif p12 >= 72:
            performance -= 8
            performance_reasons.append(f"12개월 기대확률 {p12}%로 우호적")
    except Exception:
        p12 = 60
    try:
        val = value_dividend_score(n, r) if "value_dividend_score" in globals() else {"score": 60, "growth": 60}
        vscore = int(val.get("score", 60) or 60)
        growth = int(val.get("growth", 60) or 60)
        if vscore < 50 or growth < 50:
            performance += 18
            performance_reasons.append(f"가치/성장 점수 약함({vscore}/{growth})")
        elif vscore >= 68 and growth >= 65:
            performance -= 6
            performance_reasons.append(f"가치/성장 점수 양호({vscore}/{growth})")
    except Exception:
        pass
    if sec == "디스플레이":
        performance += 14
        performance_reasons.append("업황 회복 확인이 필요한 섹터")
    if rate <= -15:
        performance += 14
        performance_reasons.append(f"보유 손익 {rate:.2f}%로 체력 확인 필요")
    performance = max(0, min(100, int(performance)))

    # 2) 수급 위험: 실제 외국인/기관 API 전까지는 비중·거래대금/거래량 대체값 사용
    supply = 10
    supply_reasons = []
    sec_w = float((weights or {}).get(sec, 0) or 0)
    if sec_w >= 60:
        supply += 34
        supply_reasons.append(f"{sec} 비중 {sec_w:.1f}%로 집중 위험")
    elif sec_w >= 45:
        supply += 18
        supply_reasons.append(f"{sec} 비중 {sec_w:.1f}%로 추가매수 신중")
    try:
        vol = (r or {}).get("volume", None)
        if vol is not None and float(vol or 0) <= 0:
            supply += 8
            supply_reasons.append("거래량 확인불가")
    except Exception:
        pass
    if today is not None and today <= -3:
        supply += 10
        supply_reasons.append(f"당일 하락 {today:+.2f}%로 매도압력 확인 필요")
    supply = max(0, min(100, int(supply)))

    # 3) 차트 위험: 현재 V115/타이밍 점수와 당일 등락률을 사용
    chart = 12
    chart_reasons = []
    try:
        timing = safe_timing_score(n, r) if "safe_timing_score" in globals() else {"score": 55, "stage": "중립"}
        tscore = int(timing.get("score", 55) or 55)
        if tscore <= 45:
            chart += 36
            chart_reasons.append(f"차트/타이밍 {tscore}점으로 약세")
        elif tscore <= 55:
            chart += 20
            chart_reasons.append(f"차트/타이밍 {tscore}점으로 보통 이하")
        elif tscore >= 70:
            chart -= 8
            chart_reasons.append(f"차트/타이밍 {tscore}점으로 양호")
    except Exception:
        tscore = 55
    if today is not None:
        if today <= -5:
            chart += 30
            chart_reasons.append(f"당일 급락 {today:+.2f}%")
        elif today <= -3:
            chart += 16
            chart_reasons.append(f"당일 하락 {today:+.2f}%")
        elif today >= 6:
            chart += 10
            chart_reasons.append(f"당일 급등 {today:+.2f}%로 단기 과열 주의")
    if rate <= -10:
        chart += 12
        chart_reasons.append(f"보유수익률 {rate:.2f}%로 하락 추세 확인 필요")
    chart = max(0, min(100, int(chart)))

    # 4) 뉴스 위험: RSS 제목 기반 부정 뉴스 탐지
    news = 8
    news_reasons = []
    try:
        all_news = rss_items() if "rss_items" in globals() else []
        keys = holding_news_keywords(n) if "holding_news_keywords" in globals() else [n]
        neg, pos = 0, 0
        neg_title = ""
        for source, title, link in all_news[:80]:
            match = news_matches(title, keys) if "news_matches" in globals() else (n.lower() in str(title).lower())
            if not match:
                continue
            impact, score = news_impact(title) if "news_impact" in globals() else ("⚪ 중립", 0)
            if "부정" in str(impact):
                neg += 1
                if not neg_title:
                    neg_title = title
            elif "긍정" in str(impact):
                pos += 1
        if neg >= 2:
            news += 42
            news_reasons.append(f"부정뉴스 {neg}건 감지")
        elif neg == 1:
            news += 22
            news_reasons.append(f"부정뉴스 1건 감지")
        if pos > neg and pos > 0:
            news -= 8
            news_reasons.append(f"긍정뉴스 {pos}건으로 일부 완충")
        if neg_title:
            news_reasons.append(neg_title[:60])
    except Exception:
        news_reasons.append("뉴스 데이터 확인 제한")
    news = max(0, min(100, int(news)))

    # 5) 테마 위험: 섹터/발굴 TOP 포함 여부와 선반영 위험
    theme = 10
    theme_reasons = []
    try:
        top_names = discovery_top_names(data, 5) if "discovery_top_names" in globals() else []
    except Exception:
        top_names = []
    if n not in top_names and sec in ["반도체", "전력/자동화"]:
        theme += 12
        theme_reasons.append("발굴 상위권 제외로 테마 추세 확인 필요")
    if sec == "디스플레이":
        theme += 18
        theme_reasons.append("테마 모멘텀보다 업황 회복 확인 필요")
    if rate >= 25:
        theme += 16
        theme_reasons.append(f"수익률 {rate:.2f}%로 선반영 위험")
    if sec == "미국지수":
        theme -= 8
        theme_reasons.append("지수형 자산은 개별 테마붕괴 위험 낮음")
    theme = max(0, min(100, int(theme)))

    total = int(performance * 0.30 + supply * 0.20 + chart * 0.20 + news * 0.20 + theme * 0.10)

    # 좋은하락/나쁜하락 엔진으로 최종 보정
    try:
        gd = good_bad_drop_engine(n, r, data, weights) if "good_bad_drop_engine" in globals() else {}
        label = str(gd.get("label", ""))
        if "좋은하락" in label:
            total = max(0, total - 12)
        elif "나쁜하락" in label:
            total = min(100, total + 18)
    except Exception:
        gd = {}

    if total >= 80:
        level = "🔴 위험"
        action = "추가매수 금지 · 비중축소/손실방어 검토"
    elif total >= 60:
        level = "🟠 경고"
        action = "관망 · 원인 해소 전 추매 금지"
    elif total >= 30:
        level = "🟡 주의"
        action = "보유 점검 · 소액 분할만 가능"
    else:
        level = "🟢 정상"
        action = "표시하지 않음"

    breakdown = [
        ("실적위험", performance, performance_reasons or ["특이 위험 낮음"]),
        ("수급위험", supply, supply_reasons or ["특이 위험 낮음"]),
        ("차트위험", chart, chart_reasons or ["특이 위험 낮음"]),
        ("뉴스위험", news, news_reasons or ["특이 위험 낮음"]),
        ("테마위험", theme, theme_reasons or ["특이 위험 낮음"]),
    ]
    top_causes = sorted(breakdown, key=lambda x: x[1], reverse=True)[:3]
    return {
        "name": n, "sector": sec, "rate": rate, "today": today,
        "total": max(0, min(100, int(total))), "level": level, "action": action,
        "breakdown": breakdown, "top_causes": top_causes, "good_bad": gd,
    }


def risk_cause_v119_items(data):
    try:
        _, _, _, _, weights, rows = metrics(data)
    except Exception:
        weights, rows = {}, []
    items = []
    for n, q, a, r in rows:
        if not r:
            continue
        item = risk_category_scores_v119(n, r, data, weights)
        if item.get("total", 0) >= 30:  # 정상은 숨김
            items.append(item)
    rank = {"🔴 위험": 0, "🟠 경고": 1, "🟡 주의": 2}
    return sorted(items, key=lambda x: (rank.get(x.get("level", ""), 9), -x.get("total", 0)))


def render_v106_risk_radar(data):
    """V119 위험원인 분석: 홈에는 위험 종목만 짧게 표시합니다."""
    items = risk_cause_v119_items(data)
    if not items:
        card("🚨 위험레이더 V119", "🟢 현재 바로 확인할 위험 종목은 없습니다.<br>정상 종목은 숨김 처리합니다.")
        return
    body = []
    for x in items[:4]:
        main_causes = " · ".join([f"{name} {score}점" for name, score, rs in x.get("top_causes", [])[:2]])
        body.append(
            f'<b>{x["level"]} {x["name"]}</b> · 위험도 {x["total"]}점<br>'
            f'핵심원인: {main_causes}<br>'
            f'행동: <b>{x["action"]}</b>'
        )
    card("🚨 위험레이더 V119", "<br><br>".join(body))


def render_risk_radar_v2_detail(data):
    """V119 상세: 위험을 실적/수급/차트/뉴스/테마로 분해해서 보여줍니다."""
    items = risk_cause_v119_items(data)
    if not items:
        card("🚨 위험레이더 V119", "🟢 현재 위험/주의 종목은 없습니다.<br>정상 종목은 숨김 처리합니다.")
        return
    st.markdown('<div class="brief-card"><div class="brief-title">🚨 위험원인 분석 V119</div><div class="brief-sub">정상 종목은 숨기고, 위험이 있는 종목만 실적·수급·차트·뉴스·테마로 분해합니다.</div></div>', unsafe_allow_html=True)
    for x in items:
        rows_html = ""
        for label, score, reasons in x.get("breakdown", []):
            reason = " / ".join([str(r) for r in reasons[:2]])
            rows_html += (
                f'<div class="brief-box"><div class="brief-label">{label}</div>'
                f'<div class="brief-value">{score}점</div>'
                f'<div class="brief-reason">{reason}</div></div>'
            )
        gd = x.get("good_bad", {}) or {}
        html = (
            f'<div class="brief-card">'
            f'<div class="brief-title">{x["level"]} {x["name"]} · 위험도 {x["total"]}점</div>'
            f'<div class="brief-sub">섹터 {x.get("sector", "-")} · 보유수익률 {x.get("rate", 0):.2f}% · 하락판정 {gd.get("label", "흐름확인")}</div>'
            f'<div class="brief-action">오늘 행동: {x["action"]}</div>'
            f'<div class="brief-grid">{rows_html}</div>'
            f'<div class="brief-reason"><b>판단 방식</b><br>실적 30% · 수급 20% · 차트 20% · 뉴스 20% · 테마 10%를 합산하고, 좋은하락/나쁜하락 엔진으로 최종 보정합니다.</div>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)


def rec(data):
    header()
    render_kis_live_quote_strip(data, title="📡 KIS 실시간 데이터 바로보기 · 추천")
    render_kis_token_cache_status()
    render_smart_money_live_v122(data, compact=False)
    render_backtest_tracker_v1231(data, compact=False)
    render_historical_data_test_v1241(data, compact=False)
    render_historical_replay_v1242(data, compact=False)
    render_loss_minimizer_v1243(data, compact=False)
    render_audit_mode_v1244(data, compact=False)
    render_bulk_historical_replay_v1245(data, compact=False)
    render_hypothesis_experiment_v1246(data, compact=False)
    render_profit_finder_v1247(data, compact=False)
    render_failure_analyzer_v1249(data, compact=False)
    render_support_analyzer_v12410(data, compact=False)
    render_fake_bottom_killer_v12411(data, compact=False)
    render_validation_lab_v12412(data, compact=False)
    render_combo_validation_lab_v12413(data, compact=False)
    if st.button("🔄 추천 다시 판단하기", use_container_width=True):
        st.rerun()
    render_compass_gauge(data, title="🚀 추천 컴파스")
    render_execution_strategy(data)
    render_portfolio_auto_judge_v1171(data)
    render_v117_good_bad_summary(data)
    render_risk_radar_v2_detail(data)
    render_smart_money_v121(data, compact=False)
    render_kis_real_test_panel(data)
    render_discovery_top3_cards(data)
    with st.expander("전문가용 V114~V116 핵심 엔진 보기", expanded=False):
        render_core_engine_summary(data)
    with st.expander("기존 추천 판단근거 보기", expanded=False):
        render_action(data, show_detail=True)
        period, period_reason = investment_period_hint(data)
        card("추천 투자기간", f"{period}<br>{period_reason}")
        hs, hg, hr, risk_reasons, risk_action = portfolio_health(data)
        card(
            "추천 판단 요약",
            f"포트폴리오 위험도 {hs}점 · {hg}<br>"
            f"{hr}<br><br>"
            f"행동 기준: {risk_action}"
        )


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

    with st.expander("⚙️ 전문가 메뉴 · DB 상태/동기화", expanded=False):
        st.caption("평소에는 볼 필요 없는 개발자용 확인 화면입니다. PC와 휴대폰 값이 다를 때만 열어 확인하세요.")
        render_github_json_sync_panel(data)
        render_db_truth_panel(data)
        render_db_structure_panel(data)
        render_db_status(data)

    st.caption("평가수익은 현재 보유종목 기준이고, 실현손익은 매도기록 기준입니다.")


# V123: SMART MONEY SCORE / 20일 평균 대비 엄격 점수화 엔진
# V122-2는 장중 기대치 기준이어서 장 초반에 점수가 관대해질 수 있었습니다.
# V123은 최근 20일 평균 거래량·거래대금을 기준으로 오늘 장중 흐름을 일간 환산하여 비교합니다.
def safe_ratio_percent(now_value, base_value):
    try:
        now_value = float(now_value or 0)
        base_value = float(base_value or 0)
        if base_value <= 0 or now_value <= 0:
            return 0.0
        return now_value / base_value * 100
    except Exception:
        return 0.0


def avg20_volume_amount_from_daily(name):
    try:
        daily = fetch_daily_ohlcv(name, pages=3)
        # 최신 행은 당일일 수 있으므로 제외하고 과거 20거래일 사용
        hist = daily[1:21] if len(daily) > 1 else daily[:20]
        vols = [sf(x.get('volume')) for x in hist if sf(x.get('volume')) > 0]
        amts = []
        for x in hist:
            c = sf(x.get('close'))
            v = sf(x.get('volume'))
            if c > 0 and v > 0:
                amts.append(c * v)
        return {
            'avg20_volume': avg_num(vols),
            'avg20_amount': avg_num(amts),
            'sample_count': len(vols),
        }
    except Exception:
        return {'avg20_volume': 0, 'avg20_amount': 0, 'sample_count': 0}


def smart_money_score_v123_item(name):
    n = norm(name)
    q = kis_direct_price_test(n) if 'kis_direct_price_test' in globals() else {'ok': False, 'error': 'KIS 함수 없음'}
    base_static = smart_money_baseline(n)
    avg20 = avg20_volume_amount_from_daily(n)
    progress, progress_label = market_progress_ratio_now()
    progress_safe = max(progress, 1/390)

    if not q.get('ok'):
        return {
            'ok': False, 'name': n, 'code': code_map().get(n, ''), 'score': 0,
            'verdict': '조회 실패', 'action': '연결 확인', 'reason': q.get('error', '조회 실패'), 'raw': q,
        }

    price = parse_float_safe(q.get('price'), 0)
    volume = parse_float_safe(q.get('volume'), 0)
    amount = parse_float_safe(q.get('amount'), 0)
    change = parse_float_safe(q.get('change_rate'), 0)
    if amount <= 0 and price > 0 and volume > 0:
        amount = price * volume

    # 20일 평균이 부족하면 기존 기준선을 보조로 사용합니다.
    avg20_vol = parse_float_safe(avg20.get('avg20_volume'), 0) or parse_float_safe(base_static.get('volume'), 1)
    avg20_amt = parse_float_safe(avg20.get('avg20_amount'), 0) or parse_float_safe(base_static.get('amount'), 1)

    projected_vol = volume / progress_safe if progress_safe else volume
    projected_amt = amount / progress_safe if progress_safe else amount

    vol_ratio = safe_ratio_percent(projected_vol, avg20_vol)
    amt_ratio = safe_ratio_percent(projected_amt, avg20_amt)
    live_vol_ratio = safe_ratio_percent(volume, avg20_vol)
    live_amt_ratio = safe_ratio_percent(amount, avg20_amt)

    # 엄격 점수: 90점 이상은 거래량·거래대금이 동시에 매우 강해야 함.
    score = 20
    reasons = []

    if vol_ratio >= 500:
        score += 30; reasons.append(f'20일평균 대비 거래량 환산 {vol_ratio:.0f}% 폭증')
    elif vol_ratio >= 300:
        score += 22; reasons.append(f'20일평균 대비 거래량 환산 {vol_ratio:.0f}% 급증')
    elif vol_ratio >= 200:
        score += 14; reasons.append(f'20일평균 대비 거래량 환산 {vol_ratio:.0f}% 증가')
    elif vol_ratio >= 130:
        score += 6; reasons.append(f'20일평균 대비 거래량 환산 {vol_ratio:.0f}% 관심')
    else:
        reasons.append(f'20일평균 대비 거래량 환산 {vol_ratio:.0f}%')

    if amt_ratio >= 500:
        score += 34; reasons.append(f'20일평균 대비 거래대금 환산 {amt_ratio:.0f}% 폭증')
    elif amt_ratio >= 300:
        score += 25; reasons.append(f'20일평균 대비 거래대금 환산 {amt_ratio:.0f}% 급증')
    elif amt_ratio >= 200:
        score += 16; reasons.append(f'20일평균 대비 거래대금 환산 {amt_ratio:.0f}% 증가')
    elif amt_ratio >= 130:
        score += 7; reasons.append(f'20일평균 대비 거래대금 환산 {amt_ratio:.0f}% 관심')
    else:
        reasons.append(f'20일평균 대비 거래대금 환산 {amt_ratio:.0f}%')

    # 가격 확인: 돈이 들어와도 가격이 못 오르면 이탈/매물 소화 가능성을 경고합니다.
    if change >= 5:
        score += 9; reasons.append(f'주가 강세 {change:+.2f}%')
    elif change >= 2:
        score += 6; reasons.append(f'주가 상승 {change:+.2f}%')
    elif change > 0:
        score += 3; reasons.append(f'주가 플러스 {change:+.2f}%')
    elif change <= -3:
        score -= 15; reasons.append(f'주가 약세 {change:+.2f}%')
    elif change < 0:
        score -= 7; reasons.append(f'주가 소폭 약세 {change:+.2f}%')
    else:
        reasons.append('등락률 보합권')

    # 거래량만 있고 거래대금이 약하면 큰돈이 아닐 수 있어 감점.
    if vol_ratio >= 250 and amt_ratio < 130:
        score -= 12; reasons.append('거래량 대비 거래대금 약함')
    if amt_ratio >= 250 and vol_ratio < 130:
        score -= 6; reasons.append('거래대금은 크지만 거래량 확산 제한')

    score = max(0, min(100, int(score)))

    exit_risk = 10
    exit_reasons = []
    if change <= -1 and vol_ratio >= 200:
        exit_risk += 30; exit_reasons.append('거래량 증가 대비 주가 하락')
    if change <= -2 and amt_ratio >= 200:
        exit_risk += 30; exit_reasons.append('거래대금 동반 하락')
    if change <= -4:
        exit_risk += 20; exit_reasons.append('당일 하락폭 확대')
    if vol_ratio >= 400 and change <= 0:
        exit_risk += 15; exit_reasons.append('대량거래에도 상승 실패')
    exit_risk = max(0, min(100, int(exit_risk)))

    if score >= 90 and exit_risk < 40:
        verdict = '🔥 매우 강한 유입'
        action = '집중 관찰'
    elif score >= 80 and exit_risk < 45:
        verdict = '🟢 강한 유입'
        action = '관심 강화'
    elif score >= 70 and exit_risk < 50:
        verdict = '🟡 유입 후보'
        action = '분할 관심'
    elif score >= 55:
        verdict = '⚪ 관심권'
        action = '관찰'
    elif exit_risk >= 65:
        verdict = '🔴 이탈 의심'
        action = '추격금지'
    elif exit_risk >= 45:
        verdict = '🟠 분산 주의'
        action = '관망'
    else:
        verdict = '⚪ 보통'
        action = '관찰'

    return {
        'ok': True, 'name': n, 'code': q.get('code', code_map().get(n, '')), 'price': price,
        'volume': volume, 'amount': amount, 'change': change,
        'avg20_volume': avg20_vol, 'avg20_amount': avg20_amt,
        'projected_volume': projected_vol, 'projected_amount': projected_amt,
        'vol_ratio': vol_ratio, 'amt_ratio': amt_ratio,
        'live_vol_ratio': live_vol_ratio, 'live_amt_ratio': live_amt_ratio,
        'sample_count': avg20.get('sample_count', 0), 'progress_label': progress_label,
        'score': score, 'exit_risk': exit_risk, 'verdict': verdict, 'action': action,
        'reasons': reasons[:6], 'exit_reasons': exit_reasons[:4],
        'checked_at': q.get('checked_at', now_label()), 'src': q.get('src', 'KIS'),
    }


def smart_money_score_v123_scan(data=None):
    items = []
    for n in smart_money_watchlist(data):
        try:
            items.append(smart_money_score_v123_item(n))
        except Exception as e:
            items.append({'ok': False, 'name': n, 'score': 0, 'verdict': '오류', 'action': '확인', 'reason': str(e)[:120]})
    return sorted(items, key=lambda x: (x.get('ok', False), x.get('score', 0), -x.get('exit_risk', 0)), reverse=True)


def render_smart_money_live_v122(data=None, compact=False):
    items = smart_money_score_v123_scan(data)
    ok_items = [x for x in items if x.get('ok')]
    top = ok_items[0] if ok_items else None
    if top:
        headline = f'{top["name"]} · {top["verdict"]}'
        score_line = f'스마트머니 {top["score"]}점 · 이탈위험 {top.get("exit_risk",0)}점'
        sub = f'20일평균 대비 거래량 환산 {top.get("vol_ratio",0):.0f}% · 거래대금 환산 {top.get("amt_ratio",0):.0f}% · 등락 {top.get("change",0):+.2f}%'
    else:
        headline = '조회 성공 종목 없음'
        score_line = 'KIS 키/토큰/종목코드 확인 필요'
        sub = 'V122-1 현재가·거래량 조회가 성공했는지 먼저 확인하세요.'

    html = (
        '<div class="db-card">'
        '<div class="db-title">🔥 V123 Smart Money Score</div>'
        '<div class="db-sub">최근 20일 평균 거래량·거래대금과 현재 장중 데이터를 비교해 일간 환산 증가율로 점수화합니다. 90점 이상은 매우 드문 강한 유입일 때만 표시되도록 기준을 엄격하게 조정했습니다.</div>'
        f'<div class="db-action">1순위: {headline}<br>{score_line}<br>{sub}</div>'
    )
    show_items = ok_items[:3] if compact else ok_items[:8]
    for idx, x in enumerate(show_items, start=1):
        medal = '🥇' if idx == 1 else ('🥈' if idx == 2 else ('🥉' if idx == 3 else '▫️'))
        reasons = ' · '.join(x.get('reasons', []))
        html += (
            '<div class="db-row">'
            f'<div class="db-name">{medal} {x.get("name")} · {x.get("code")} · {x.get("verdict")}</div>'
            f'<div class="db-meta">현재가 {won(x.get("price"))} · 등락 {x.get("change",0):+.2f}% · 행동 {x.get("action")}<br>'
            f'현재 거래량 {volume_text(x.get("volume"))} · 20일평균 {volume_text(x.get("avg20_volume"))} · 일간환산 {volume_text(x.get("projected_volume"))} · 증가율 {x.get("vol_ratio",0):.0f}%<br>'
            f'현재 거래대금 {amount_text(x.get("amount"))} · 20일평균 {amount_text(x.get("avg20_amount"))} · 일간환산 {amount_text(x.get("projected_amount"))} · 증가율 {x.get("amt_ratio",0):.0f}%<br>'
            f'실시간 누적 기준 거래량 {x.get("live_vol_ratio",0):.1f}% · 거래대금 {x.get("live_amt_ratio",0):.1f}% · 표본 {x.get("sample_count",0)}일 · {x.get("progress_label", "-")}<br>'
            f'스마트머니 {x.get("score",0)}점 · 이탈위험 {x.get("exit_risk",0)}점 · {reasons}<br>확인 {x.get("checked_at", now_label())}</div>'
            '</div>'
        )
    failed = [x for x in items if not x.get('ok')]
    if failed and not compact:
        html += '<div class="db-sub"><b>조회 실패 종목</b><br>' + '<br>'.join([f'{x.get("name")}: {x.get("reason", x.get("verdict", "실패"))}' for x in failed[:5]]) + '</div>'
    html += '<div class="db-sub">※ V123은 V122-1 토큰 캐시를 유지하면서 20일 평균 대비 일간 환산 증가율을 사용합니다. 다음 단계는 체결강도/외국인/기관 수급 연결입니다.</div></div>'
    st.markdown(html, unsafe_allow_html=True)



# V123-1: BACKTEST TRACKER / 반자동 학습을 위한 점수 역추적 기록 엔진
# 목적: 오늘 나온 스마트머니 점수와 가격을 저장하고, 1/3/5/20일 뒤 실제 수익률을 비교합니다.
# 원칙: 점수 공식은 자동으로 바꾸지 않습니다. 결과를 쌓은 뒤 가중치 변경안을 제안하고 사용자가 승인하는 반자동 학습으로 갑니다.
SCORE_HISTORY_FILE = DATA_DIR / "score_history.json"
BACKTEST_HORIZONS = [1, 3, 5, 20]


def load_score_history():
    try:
        if SCORE_HISTORY_FILE.exists():
            with open(SCORE_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_score_history(items):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(SCORE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def backtest_record_key(row):
    return f"{row.get('signal_date','')}|{norm(row.get('name',''))}"


def record_smart_money_signals_v1231(data=None, min_score=70, top_n=10):
    """오늘 스마트머니 상위 신호를 하루 1회 종목별로 저장합니다."""
    try:
        items = smart_money_score_v123_scan(data)
    except Exception:
        items = []
    ok_items = [x for x in items if x.get('ok')]
    selected = [x for x in ok_items if int(x.get('score', 0) or 0) >= min_score][:top_n]
    if not selected:
        selected = ok_items[:min(3, len(ok_items))]

    history = load_score_history()
    existing = {backtest_record_key(x) for x in history}
    today = today_key()
    added = 0
    for x in selected:
        row = {
            'signal_date': today,
            'signal_time': now_label(),
            'name': norm(x.get('name', '')),
            'code': x.get('code', code_map().get(norm(x.get('name','')), '')),
            'score': int(x.get('score', 0) or 0),
            'exit_risk': int(x.get('exit_risk', 0) or 0),
            'verdict': x.get('verdict', ''),
            'action': x.get('action', ''),
            'entry_price': float(x.get('price', 0) or 0),
            'entry_volume': float(x.get('volume', 0) or 0),
            'entry_amount': float(x.get('amount', 0) or 0),
            'vol_ratio': float(x.get('vol_ratio', 0) or 0),
            'amt_ratio': float(x.get('amt_ratio', 0) or 0),
            'change': float(x.get('change', 0) or 0),
            'reasons': x.get('reasons', [])[:6],
            'returns': {},
            'review_status': 'tracking',
            'learning_note': 'V123-1 자동 기록. 가중치 변경은 자동 적용하지 않고 추후 승인 방식으로 진행.',
        }
        key = backtest_record_key(row)
        if key not in existing and row['name'] and row['entry_price'] > 0:
            history.append(row)
            existing.add(key)
            added += 1
    if added:
        save_score_history(history)
    return added, selected, history


def days_since_signal(datestr):
    try:
        d = datetime.strptime(str(datestr), "%Y-%m-%d")
        nowd = datetime.strptime(today_key(), "%Y-%m-%d")
        return (nowd - d).days
    except Exception:
        return 0


def update_backtest_returns_v1231():
    """기록된 신호의 1/3/5/20일 후 수익률을 가능한 경우 갱신합니다."""
    history = load_score_history()
    changed = 0
    for row in history:
        try:
            name = norm(row.get('name', ''))
            entry = float(row.get('entry_price', 0) or 0)
            if not name or entry <= 0:
                continue
            elapsed = days_since_signal(row.get('signal_date'))
            if elapsed <= 0:
                continue
            due = [h for h in BACKTEST_HORIZONS if elapsed >= h and str(h) not in row.get('returns', {})]
            if not due:
                continue
            q = kis_direct_price_test(name) if 'kis_direct_price_test' in globals() else {'ok': False}
            if not q.get('ok'):
                continue
            price = parse_float_safe(q.get('price'), 0)
            if price <= 0:
                continue
            row.setdefault('returns', {})
            for h in due:
                ret = (price / entry - 1) * 100
                row['returns'][str(h)] = {
                    'days': h,
                    'checked_at': now_label(),
                    'price': price,
                    'return_pct': ret,
                    'success': ret > 0,
                }
                changed += 1
            if all(str(h) in row.get('returns', {}) for h in BACKTEST_HORIZONS):
                row['review_status'] = 'complete'
        except Exception:
            pass
    if changed:
        save_score_history(history)
    return changed, history


def backtest_summary_stats(history):
    stats = {}
    for h in BACKTEST_HORIZONS:
        vals = []
        wins = 0
        for row in history:
            r = (row.get('returns') or {}).get(str(h))
            if isinstance(r, dict):
                ret = float(r.get('return_pct', 0) or 0)
                vals.append(ret)
                if ret > 0:
                    wins += 1
        if vals:
            stats[h] = {
                'count': len(vals),
                'avg_return': sum(vals) / len(vals),
                'win_rate': wins / len(vals) * 100,
            }
        else:
            stats[h] = {'count': 0, 'avg_return': 0, 'win_rate': 0}
    return stats


def render_backtest_tracker_v1231(data=None, compact=False):
    changed, history = update_backtest_returns_v1231()
    added, selected, history = record_smart_money_signals_v1231(data, min_score=70, top_n=10)
    stats = backtest_summary_stats(history)
    tracked = len(history)
    completed_1d = stats.get(1, {}).get('count', 0)
    recent = sorted(history, key=lambda x: (x.get('signal_date',''), x.get('signal_time','')), reverse=True)[:(3 if compact else 8)]

    stat_line = []
    for h in BACKTEST_HORIZONS:
        stt = stats.get(h, {})
        if stt.get('count', 0):
            stat_line.append(f'{h}일 {stt["count"]}건 · 평균 {stt["avg_return"]:+.2f}% · 승률 {stt["win_rate"]:.0f}%')
    stat_html = '<br>'.join(stat_line) if stat_line else '아직 1일 이상 지난 기록이 없어 성과 검증 대기 중입니다.'

    html = (
        '<div class="db-card">'
        '<div class="db-title">📌 V123-1 Backtest Tracker</div>'
        '<div class="db-sub">오늘의 스마트머니 점수·현재가·근거를 저장하고 1일/3일/5일/20일 뒤 실제 수익률을 비교합니다. 완전 자동 변경이 아니라 반자동 학습용 기록입니다.</div>'
        f'<div class="db-action">오늘 신규기록 {added}건 · 수익률 갱신 {changed}건 · 누적 추적 {tracked}건<br>검증상태: {stat_html}</div>'
        '<div class="db-sub"><b>반자동 학습 원칙</b><br>점수 공식은 앱이 마음대로 바꾸지 않습니다. 기록이 쌓이면 차트/거래량/거래대금/리스크 가중치 변경안을 제안하고, 경규님 승인 후 반영합니다.</div>'
    )
    if recent:
        for row in recent:
            returns = row.get('returns') or {}
            ret_bits = []
            for h in BACKTEST_HORIZONS:
                r = returns.get(str(h))
                if isinstance(r, dict):
                    ret_bits.append(f'{h}일 {float(r.get("return_pct",0)):+.2f}%')
                else:
                    elapsed = days_since_signal(row.get('signal_date'))
                    ret_bits.append(f'{h}일 대기' if elapsed < h else f'{h}일 확인대기')
            reasons = ' · '.join([str(x) for x in row.get('reasons', [])[:3]])
            html += (
                '<div class="db-row">'
                f'<div class="db-name">{row.get("signal_date")} · {row.get("name")} · {row.get("score")}점 · {row.get("verdict")}</div>'
                f'<div class="db-meta">진입가 {won(row.get("entry_price"))} · 이탈위험 {row.get("exit_risk",0)}점 · 등락 {float(row.get("change",0)):+.2f}%<br>'
                f'거래량증가율 {float(row.get("vol_ratio",0)):.0f}% · 거래대금증가율 {float(row.get("amt_ratio",0)):.0f}%<br>'
                f'추적결과: {" · ".join(ret_bits)}<br>근거: {reasons}</div>'
                '</div>'
            )
    else:
        html += '<div class="db-row"><div class="db-meta">아직 저장된 점수 기록이 없습니다. 장중 스마트머니 신호가 나오면 자동 저장됩니다.</div></div>'
    html += '<div class="db-sub">※ score_history.json에 저장됩니다. Cloud 재배포/리부트 시 서버 저장소 특성상 장기 보존은 제한될 수 있어, 추후 GitHub JSON 동기화 또는 다운로드 기능으로 보강 예정입니다.</div></div>'
    st.markdown(html, unsafe_allow_html=True)



# V124-1: HISTORICAL DATA TEST / 과거 일봉 확보 가능 여부 검증
HISTORICAL_TEST_FILE = DATA_DIR / "historical_test.json"

def historical_target_names_v1241(data=None):
    """V124-7-1: 표본 확장을 위해 보유 5종목 + 기존 코드맵 주요 후보 전체를 테스트합니다.
    목표는 5종목 220건 수준에서 1,000건 이상으로 표본을 늘리는 것입니다.
    단, KIS 호출이 많아지므로 우선 기존 code_map에 코드가 확정된 종목만 사용합니다.
    """
    names = []

    # 1) 경규님 실제 보유종목을 항상 먼저 배치
    try:
        for h in (data or {}).get("holdings", []):
            n = norm(h.get("name", ""))
            if n and n not in names and code_map().get(n):
                names.append(n)
    except Exception:
        pass

    # 2) 1차 확장 후보: 코드가 이미 확정된 종목만 사용
    expansion = [
        "에스피시스템스", "제룡전기", "ACE AI반도체 TOP3", "KODEX 미국S&P500", "LG디스플레이",
        "TIGER 미국S&P500", "삼성전자", "SK하이닉스", "한미반도체", "대한전선",
        "하나마이크론", "ISC", "이수페타시스", "LS ELECTRIC", "효성중공업",
        "레인보우로보틱스", "두산로보틱스", "비에이치아이", "우진",
    ]
    for n in expansion:
        nn = norm(n)
        if nn and nn not in names and code_map().get(nn):
            names.append(nn)

    return names[:25]

def parse_kis_daily_rows_v1241(rows):
    out = []
    for r in rows or []:
        try:
            date = str(r.get("stck_bsop_date") or r.get("date") or "")
            if len(date) == 8:
                date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            else:
                date_fmt = date
            close = float(str(r.get("stck_clpr") or r.get("close") or 0).replace(',', '') or 0)
            open_p = float(str(r.get("stck_oprc") or r.get("open") or 0).replace(',', '') or 0)
            high = float(str(r.get("stck_hgpr") or r.get("high") or 0).replace(',', '') or 0)
            low = float(str(r.get("stck_lwpr") or r.get("low") or 0).replace(',', '') or 0)
            vol = float(str(r.get("acml_vol") or r.get("volume") or 0).replace(',', '') or 0)
            amount = float(str(r.get("acml_tr_pbmn") or r.get("amount") or 0).replace(',', '') or 0)
            if date_fmt and close > 0:
                out.append({
                    "date": date_fmt,
                    "open": open_p,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": vol,
                    "amount": amount,
                })
        except Exception:
            continue
    return sorted(out, key=lambda x: x.get("date", ""))

@st.cache_data(ttl=3600, show_spinner=False)
def kis_daily_chart_v1241_cached(name, start_date, end_date):
    n = norm(name)
    code = code_map().get(n)
    if not code:
        return {"ok": False, "name": n, "rows": [], "count": 0, "error": "종목코드 없음"}
    if not kis_ready():
        return {"ok": False, "name": n, "rows": [], "count": 0, "error": "KIS 키 없음"}
    try:
        token_info = kis_stable_token_info(force_new=False) if "kis_stable_token_info" in globals() else kis_direct_token_test()
        token = token_info.get("token", "") if isinstance(token_info, dict) else ""
        if not token:
            return {"ok": False, "name": n, "rows": [], "count": 0, "error": "토큰 없음"}
        app_key, app_secret, _ = kis_credentials()
        url = f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST03010100",
            "custtype": "P",
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        }
        r = requests.get(url, headers=headers, params=params, timeout=8)
        if r.status_code != 200:
            return {"ok": False, "name": n, "rows": [], "count": 0, "error": f"HTTP {r.status_code}", "raw": r.text[:160]}
        js = r.json()
        rt_cd = str(js.get("rt_cd", ""))
        if rt_cd not in ["0", ""]:
            return {"ok": False, "name": n, "rows": [], "count": 0, "error": str(js.get("msg1", js))[:160]}
        raw_rows = js.get("output2") or js.get("output") or []
        if isinstance(raw_rows, dict):
            raw_rows = [raw_rows]
        rows = parse_kis_daily_rows_v1241(raw_rows)
        return {"ok": len(rows) > 0, "name": n, "code": code, "rows": rows, "count": len(rows), "error": "" if rows else "일봉 데이터 없음"}
    except Exception as e:
        return {"ok": False, "name": n, "rows": [], "count": 0, "error": str(e)[:160]}

def kis_daily_chart_v1241(name, days=365):
    end = kst_now().strftime("%Y%m%d")
    start = (kst_now() - timedelta(days=int(days) + 10)).strftime("%Y%m%d")
    return kis_daily_chart_v1241_cached(norm(name), start, end)

def historical_period_status_v1241(count):
    # 영업일 기준 대략치: 30일≈20봉, 90일≈60봉, 180일≈120봉, 365일≈240봉
    targets = [(30, 20), (90, 60), (180, 120), (365, 220)]
    out = []
    for label, need in targets:
        ok = count >= need
        out.append((label, ok, need))
    return out

def save_historical_test_v1241(results):
    payload = {
        "version": "V124-1",
        "created_at_kst": now_label(),
        "purpose": "보유종목 5개 과거 일봉 확보 가능 여부 테스트",
        "results": results,
    }
    try:
        if can_write_db():
            write_db_json("historical_test", payload, backup=True)
    except Exception:
        pass
    return payload

def render_historical_data_test_v1241(data=None, compact=False):
    names = historical_target_names_v1241(data)
    results = []
    ok_count = 0
    rows_html = ""
    for n in names:
        res = kis_daily_chart_v1241(n, days=365)
        cnt = int(res.get("count", 0) or 0)
        ok = bool(res.get("ok")) and cnt >= 20
        ok_count += 1 if ok else 0
        rows = res.get("rows") or []
        first_date = rows[0].get("date", "-") if rows else "-"
        last_date = rows[-1].get("date", "-") if rows else "-"
        status_bits = []
        for label, pass_ok, need in historical_period_status_v1241(cnt):
            status_bits.append(f'{label}일 {"성공" if pass_ok else "부족"}')
        status_text = " · ".join(status_bits)
        err = res.get("error", "")
        result_label = "✅ 확보 가능" if ok else "❌ 확인 필요"
        rows_html += (
            '<div class="db-row">'
            f'<div class="db-name">{n} · {result_label}</div>'
            f'<div class="db-meta">수집 일봉 {cnt}개 · 기간 {first_date} ~ {last_date}<br>{status_text}'
            f'{("<br>오류: " + err) if err else ""}</div>'
            '</div>'
        )
        results.append({
            "name": n,
            "ok": ok,
            "count": cnt,
            "first_date": first_date,
            "last_date": last_date,
            "status": status_bits,
            "error": err,
        })
    save_historical_test_v1241(results)
    if ok_count == len(names) and names:
        verdict = "과거 일봉 확보 가능"
        next_step = "V124-2 과거 점수 재계산으로 진행 가능"
    elif ok_count > 0:
        verdict = "일부 종목 확보 가능"
        next_step = "실패 종목은 종목코드/ETF 지원 여부 확인 후 우회 데이터 검토"
    else:
        verdict = "과거 일봉 확보 실패"
        next_step = "KIS 일봉 API 파라미터 또는 대체 데이터 소스 확인 필요"
    html = (
        '<div class="db-card">'
        '<div class="db-title">📊 V124-1 Historical Data Test</div>'
        '<div class="db-sub">보유종목 5개에서 시작해 코드가 확정된 확장 후보까지 KIS 과거 일봉을 가져올 수 있는지 확인합니다. 이번 버전은 백테스트 계산이 아니라 데이터 확보 가능 여부 검증 단계입니다.</div>'
        f'<div class="db-action">판정: {verdict}<br>성공 {ok_count}/{len(names)}개 · 표본확장 대상 · 다음 단계: {next_step}</div>'
        f'{rows_html}'
        '<div class="db-sub">※ V124-7-1 기준: 5종목만 보지 않고 확장 후보까지 확인합니다. 현재 KIS 응답은 종목당 약 100봉 수준일 수 있어, 종목 수를 늘려 표본을 확보합니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# V124-2: HISTORICAL REPLAY ENGINE / 과거 일봉 기준 점수 재생·수익률 검증
# 목적: 오늘의 점수 공식을 과거 일봉에 되돌려 적용해, 점수가 실제 수익률로 이어졌는지 확인합니다.
# 원칙: 특정 과거 날짜의 점수 계산에는 그 날짜 이후 데이터는 절대 사용하지 않습니다.
HISTORICAL_REPLAY_FILE = DATA_DIR / "historical_replay.json"


def mean_safe_v1242(vals):
    vals = [float(x or 0) for x in vals if float(x or 0) > 0]
    return sum(vals) / len(vals) if vals else 0


def pct_change_v1242(a, b):
    try:
        a = float(a or 0); b = float(b or 0)
        if b <= 0:
            return 0
        return (a / b - 1) * 100
    except Exception:
        return 0


def historical_replay_score_v1242(rows, idx):
    """idx 날짜까지의 과거 데이터만 사용해 당시 점수를 계산합니다."""
    try:
        cur = rows[idx]
        prev = rows[idx - 1] if idx > 0 else cur
        close = float(cur.get('close', 0) or 0)
        high = float(cur.get('high', close) or close)
        low = float(cur.get('low', close) or close)
        volume = float(cur.get('volume', 0) or 0)
        amount = float(cur.get('amount', 0) or 0)
        past20 = rows[max(0, idx-20):idx]
        past5 = rows[max(0, idx-5):idx]
        if len(past20) < 15 or close <= 0:
            return None
        avg20_vol = mean_safe_v1242([r.get('volume', 0) for r in past20])
        avg20_amt = mean_safe_v1242([r.get('amount', 0) for r in past20])
        ma5 = mean_safe_v1242([r.get('close', 0) for r in past5]) or close
        ma20 = mean_safe_v1242([r.get('close', 0) for r in past20]) or close
        prev20 = rows[max(0, idx-21):idx-1]
        prev_ma20 = mean_safe_v1242([r.get('close', 0) for r in prev20]) or ma20
        prev_close = float(prev.get('close', close) or close)
        vol_ratio = volume / avg20_vol * 100 if avg20_vol else 0
        amt_ratio = amount / avg20_amt * 100 if avg20_amt else 0
        change = pct_change_v1242(close, prev_close)

        # 점수는 일부러 엄격하게 계산합니다. 90점 이상은 드물게 나와야 합니다.
        score = 40
        reasons = []

        # 거래량 25점
        if vol_ratio >= 500:
            score += 25; reasons.append(f'거래량 {vol_ratio:.0f}% 폭증')
        elif vol_ratio >= 300:
            score += 20; reasons.append(f'거래량 {vol_ratio:.0f}% 강한 증가')
        elif vol_ratio >= 180:
            score += 13; reasons.append(f'거래량 {vol_ratio:.0f}% 증가')
        elif vol_ratio >= 120:
            score += 6; reasons.append(f'거래량 {vol_ratio:.0f}% 관심')

        # 거래대금 20점
        if amt_ratio >= 500:
            score += 20; reasons.append(f'거래대금 {amt_ratio:.0f}% 폭증')
        elif amt_ratio >= 300:
            score += 16; reasons.append(f'거래대금 {amt_ratio:.0f}% 강한 증가')
        elif amt_ratio >= 180:
            score += 10; reasons.append(f'거래대금 {amt_ratio:.0f}% 증가')
        elif amt_ratio >= 120:
            score += 5; reasons.append(f'거래대금 {amt_ratio:.0f}% 관심')

        # 차트 30점
        chart_score = 0
        if close > ma5:
            chart_score += 5; reasons.append('5일선 위')
        if close > ma20:
            chart_score += 8; reasons.append('20일선 위')
        if ma5 > ma20:
            chart_score += 7; reasons.append('5일선이 20일선 위')
        if prev_close <= prev_ma20 and close > ma20:
            chart_score += 10; reasons.append('20일선 돌파')
        score += min(30, chart_score)

        # 리스크 감점 15점
        risk = 0
        if change < -2:
            risk += 8; reasons.append('당일 하락 감점')
        if high > low:
            upper_tail = (high - close) / (high - low) * 100
            if upper_tail >= 55 and change <= 1:
                risk += 7; reasons.append('윗꼬리 감점')
        if vol_ratio >= 300 and change <= 0:
            risk += 8; reasons.append('대량거래 상승 실패 감점')
        score -= min(15, risk)

        score = max(0, min(100, int(score)))
        if score >= 90:
            verdict = '🔥 매우 강한 과거신호'
        elif score >= 80:
            verdict = '🟢 강한 과거신호'
        elif score >= 70:
            verdict = '🟡 관심 과거신호'
        elif score >= 60:
            verdict = '⚪ 보통 과거신호'
        else:
            verdict = '관망'

        return {
            'date': cur.get('date'), 'close': close, 'volume': volume, 'amount': amount,
            'avg20_volume': avg20_vol, 'avg20_amount': avg20_amt,
            'vol_ratio': vol_ratio, 'amt_ratio': amt_ratio, 'ma5': ma5, 'ma20': ma20,
            'change': change, 'score': score, 'verdict': verdict, 'reasons': reasons[:6]
        }
    except Exception:
        return None


def historical_replay_one_stock_v1242(name, days=365, stride=5):
    res = kis_daily_chart_v1241(name, days=days)
    if not res.get('ok'):
        return {'ok': False, 'name': norm(name), 'error': res.get('error', '일봉 조회 실패'), 'signals': [], 'stats': {}}
    rows = res.get('rows') or []
    if len(rows) < 45:
        return {'ok': False, 'name': norm(name), 'error': f'일봉 부족 {len(rows)}개', 'signals': [], 'stats': {}}
    signals = []
    # 미래 20일 수익률을 보려면 마지막 20봉은 점수 계산 대상에서 제외합니다.
    for idx in range(25, max(26, len(rows)-20), max(1, int(stride))):
        sc = historical_replay_score_v1242(rows, idx)
        if not sc:
            continue
        entry = float(sc.get('close', 0) or 0)
        returns = {}
        for h in BACKTEST_HORIZONS:
            if idx + h < len(rows) and entry > 0:
                future = float(rows[idx+h].get('close', 0) or 0)
                returns[str(h)] = pct_change_v1242(future, entry)
        sc['returns'] = returns
        sc['name'] = norm(name)
        signals.append(sc)
    return {'ok': True, 'name': norm(name), 'count': len(rows), 'signals': signals, 'first_date': rows[0].get('date'), 'last_date': rows[-1].get('date')}


def historical_replay_scan_v1242(data=None):
    names = historical_target_names_v1241(data)
    results = []
    all_signals = []
    for n in names:
        r = historical_replay_one_stock_v1242(n, days=365, stride=5)
        results.append(r)
        if r.get('ok'):
            all_signals.extend(r.get('signals', []))
    return results, all_signals


def historical_replay_stats_v1242(signals):
    groups = {
        '90점 이상': [x for x in signals if x.get('score', 0) >= 90],
        '80~89점': [x for x in signals if 80 <= x.get('score', 0) < 90],
        '70~79점': [x for x in signals if 70 <= x.get('score', 0) < 80],
        '전체 70점 이상': [x for x in signals if x.get('score', 0) >= 70],
    }
    out = {}
    for gname, rows in groups.items():
        out[gname] = {}
        for h in BACKTEST_HORIZONS:
            vals = []
            for x in rows:
                v = (x.get('returns') or {}).get(str(h))
                if v is not None:
                    vals.append(float(v))
            if vals:
                wins = sum(1 for v in vals if v > 0)
                out[gname][h] = {'count': len(vals), 'avg_return': sum(vals)/len(vals), 'win_rate': wins/len(vals)*100}
    return out


def save_historical_replay_v1242(results, stats):
    payload = {'version': 'V124-2', 'created_at_kst': now_label(), 'purpose': '과거 일봉 기준 스마트머니 점수 재생 및 수익률 검증', 'results': results, 'stats': stats}
    try:
        if can_write_db():
            write_db_json('historical_replay', payload, backup=True)
    except Exception:
        pass
    return payload


def render_historical_replay_v1242(data=None, compact=False):
    try:
        results, signals = historical_replay_scan_v1242(data)
        stats = historical_replay_stats_v1242(signals)
        save_historical_replay_v1242(results, stats)
    except Exception as e:
        st.markdown(f'<div class="db-card"><div class="db-title">📈 V124-2 Historical Replay Engine</div><div class="db-action">오류: {str(e)[:160]}</div></div>', unsafe_allow_html=True)
        return

    ok_count = sum(1 for r in results if r.get('ok'))
    total_signals = len([x for x in signals if x.get('score', 0) >= 70])
    stat_lines = []
    for g in ['90점 이상', '80~89점', '70~79점', '전체 70점 이상']:
        st5 = (stats.get(g) or {}).get(5)
        st20 = (stats.get(g) or {}).get(20)
        if st5 or st20:
            s5 = f'5일 {st5["count"]}건 · 평균 {st5["avg_return"]:+.2f}% · 승률 {st5["win_rate"]:.0f}%' if st5 else '5일 데이터 없음'
            s20 = f'20일 {st20["count"]}건 · 평균 {st20["avg_return"]:+.2f}% · 승률 {st20["win_rate"]:.0f}%' if st20 else '20일 데이터 없음'
            stat_lines.append(f'<b>{g}</b><br>{s5}<br>{s20}')
    stat_html = '<br><br>'.join(stat_lines) if stat_lines else '아직 70점 이상 과거 신호가 부족합니다.'

    top_signals = sorted([x for x in signals if x.get('score',0) >= 70], key=lambda x: (x.get('score',0), (x.get('returns') or {}).get('20', -999)), reverse=True)
    rows_html = ''
    for x in top_signals[:(3 if compact else 10)]:
        ret = x.get('returns') or {}
        ret_text = ' · '.join([f'{h}일 {float(ret.get(str(h), 0)):+.2f}%' for h in BACKTEST_HORIZONS if str(h) in ret])
        reasons = ' · '.join(x.get('reasons', [])[:4])
        rows_html += (
            '<div class="db-row">'
            f'<div class="db-name">{x.get("date")} · {x.get("name")} · {x.get("score")}점 · {x.get("verdict")}</div>'
            f'<div class="db-meta">당시 종가 {won(x.get("close"))} · 거래량증가율 {x.get("vol_ratio",0):.0f}% · 거래대금증가율 {x.get("amt_ratio",0):.0f}% · 등락 {x.get("change",0):+.2f}%<br>'
            f'이후 수익률: {ret_text or "검증값 없음"}<br>근거: {reasons}</div>'
            '</div>'
        )

    fail_rows = ''
    failed = [r for r in results if not r.get('ok')]
    if failed and not compact:
        fail_rows = '<div class="db-sub"><b>조회 실패/제외</b><br>' + '<br>'.join([f'{r.get("name")}: {r.get("error")}' for r in failed]) + '</div>'

    html = (
        '<div class="db-card">'
        '<div class="db-title">📈 V124-2 Historical Replay Engine</div>'
        '<div class="db-sub">과거 일봉에 현재 스마트머니 점수 공식을 되감아 적용합니다. 점수 계산에는 해당 날짜 이후 데이터는 사용하지 않고, 이후 1/3/5/20일 수익률만 검증용으로 비교합니다.</div>'
        f'<div class="db-action">판정: 과거 점수 재생 {ok_count}/{len(results)}개 종목 · 70점 이상 과거신호 {total_signals}건<br>목표: 점수 공식이 실제 시장에서 통했는지 확인</div>'
        f'<div class="db-sub">{stat_html}</div>'
        f'{rows_html if rows_html else "<div class=\"db-row\"><div class=\"db-meta\">표시할 70점 이상 과거신호가 아직 부족합니다.</div></div>"}'
        f'{fail_rows}'
        '<div class="db-sub">※ V124-2는 검증 전용입니다. 가중치는 자동 변경하지 않습니다. 결과가 쌓이면 V125에서 변경안을 제안하고 경규님 승인 후 반영합니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# V124-3: Loss Minimizer Weight Optimizer
LOSS_MINIMIZER_PROFILES_V1243 = [
    {"name": "현재형", "chart": 30, "volume": 25, "amount": 20, "momentum": 10, "risk": 15, "desc": "V124-2에 가까운 기본형"},
    {"name": "차트중심형", "chart": 45, "volume": 20, "amount": 15, "momentum": 10, "risk": 10, "desc": "차트 돌파와 이동평균 위치를 가장 크게 봄"},
    {"name": "손실방어형", "chart": 35, "volume": 15, "amount": 15, "momentum": 10, "risk": 25, "desc": "윗꼬리·상승실패·급락 위험 감점을 강하게 반영"},
    {"name": "거래량공격형", "chart": 25, "volume": 40, "amount": 20, "momentum": 10, "risk": 5, "desc": "급격한 거래량 유입을 우선 포착"},
    {"name": "거래대금형", "chart": 30, "volume": 20, "amount": 35, "momentum": 10, "risk": 5, "desc": "실제 돈의 유입 규모를 가장 크게 봄"},
    {"name": "균형방어형", "chart": 38, "volume": 22, "amount": 18, "momentum": 7, "risk": 15, "desc": "차트와 수급을 보되 손실방어를 같이 반영"},
]

def score_components_v1243(rows, idx):
    try:
        cur = rows[idx]
        prev = rows[idx - 1] if idx > 0 else cur
        close = float(cur.get('close', 0) or 0)
        high = float(cur.get('high', close) or close)
        low = float(cur.get('low', close) or close)
        volume = float(cur.get('volume', 0) or 0)
        amount = float(cur.get('amount', 0) or 0)
        past20 = rows[max(0, idx-20):idx]
        past5 = rows[max(0, idx-5):idx]
        past60 = rows[max(0, idx-60):idx]
        if len(past20) < 15 or close <= 0:
            return None
        avg20_vol = mean_safe_v1242([r.get('volume', 0) for r in past20])
        avg20_amt = mean_safe_v1242([r.get('amount', 0) for r in past20])
        ma5 = mean_safe_v1242([r.get('close', 0) for r in past5]) or close
        ma20 = mean_safe_v1242([r.get('close', 0) for r in past20]) or close
        ma60 = mean_safe_v1242([r.get('close', 0) for r in past60]) or ma20
        prev20 = rows[max(0, idx-21):idx-1]
        prev_ma20 = mean_safe_v1242([r.get('close', 0) for r in prev20]) or ma20
        prev_close = float(prev.get('close', close) or close)
        vol_ratio = volume / avg20_vol * 100 if avg20_vol else 0
        amt_ratio = amount / avg20_amt * 100 if avg20_amt else 0
        change = pct_change_v1242(close, prev_close)

        volume_score = 0
        if vol_ratio >= 500: volume_score = 100
        elif vol_ratio >= 300: volume_score = 84
        elif vol_ratio >= 180: volume_score = 62
        elif vol_ratio >= 120: volume_score = 38
        else: volume_score = max(0, min(30, int(vol_ratio / 4)))

        amount_score = 0
        if amt_ratio >= 500: amount_score = 100
        elif amt_ratio >= 300: amount_score = 82
        elif amt_ratio >= 180: amount_score = 60
        elif amt_ratio >= 120: amount_score = 36
        else: amount_score = max(0, min(28, int(amt_ratio / 4)))

        chart_score = 0
        if close > ma5: chart_score += 18
        if close > ma20: chart_score += 25
        if ma5 > ma20: chart_score += 20
        if close > ma60: chart_score += 12
        if prev_close <= prev_ma20 and close > ma20: chart_score += 25
        chart_score = max(0, min(100, chart_score))

        momentum_score = 50
        if change >= 8: momentum_score = 65  # 상한가성 급등은 추격 위험도 있으므로 과점수 방지
        elif change >= 3: momentum_score = 78
        elif change >= 1: momentum_score = 65
        elif change >= -1: momentum_score = 50
        elif change >= -3: momentum_score = 35
        else: momentum_score = 18

        risk_penalty = 0
        risk_notes = []
        if change < -2:
            risk_penalty += 28; risk_notes.append('당일 하락')
        if high > low:
            upper_tail = (high - close) / (high - low) * 100
            if upper_tail >= 55 and change <= 1:
                risk_penalty += 30; risk_notes.append('윗꼬리')
        if vol_ratio >= 300 and change <= 0:
            risk_penalty += 35; risk_notes.append('대량거래 상승실패')
        if close < ma20:
            risk_penalty += 18; risk_notes.append('20일선 아래')
        risk_score = max(0, 100 - min(100, risk_penalty))

        return {
            'date': cur.get('date'), 'close': close, 'volume': volume, 'amount': amount,
            'vol_ratio': vol_ratio, 'amt_ratio': amt_ratio, 'change': change,
            'ma5': ma5, 'ma20': ma20, 'ma60': ma60,
            'volume_score': volume_score, 'amount_score': amount_score,
            'chart_score': chart_score, 'momentum_score': momentum_score,
            'risk_score': risk_score, 'risk_notes': risk_notes,
        }
    except Exception:
        return None

def weighted_score_v1243(comp, profile):
    try:
        score = (
            comp.get('chart_score', 0) * profile.get('chart', 0) +
            comp.get('volume_score', 0) * profile.get('volume', 0) +
            comp.get('amount_score', 0) * profile.get('amount', 0) +
            comp.get('momentum_score', 0) * profile.get('momentum', 0) +
            comp.get('risk_score', 0) * profile.get('risk', 0)
        ) / 100.0
        # 90점은 정말 드물게 나오도록 한 번 더 엄격화
        if comp.get('risk_score', 100) < 55:
            score -= 8
        if comp.get('chart_score', 0) < 45 and score >= 80:
            score -= 10
        return max(0, min(100, int(round(score))))
    except Exception:
        return 0

def profile_backtest_one_stock_v1243(name, profile, days=365, stride=5, threshold=70):
    res = kis_daily_chart_v1241(name, days=days)
    if not res.get('ok'):
        return {'ok': False, 'name': norm(name), 'error': res.get('error', '일봉 조회 실패'), 'signals': []}
    rows = res.get('rows') or []
    if len(rows) < 45:
        return {'ok': False, 'name': norm(name), 'error': f'일봉 부족 {len(rows)}개', 'signals': []}
    signals = []
    for idx in range(25, max(26, len(rows)-20), max(1, int(stride))):
        comp = score_components_v1243(rows, idx)
        if not comp:
            continue
        score = weighted_score_v1243(comp, profile)
        if score < threshold:
            continue
        entry = float(comp.get('close', 0) or 0)
        returns = {}
        for h in BACKTEST_HORIZONS:
            if idx + h < len(rows) and entry > 0:
                future = float(rows[idx+h].get('close', 0) or 0)
                returns[str(h)] = pct_change_v1242(future, entry)
        sig = dict(comp)
        sig.update({'name': norm(name), 'score': score, 'returns': returns, 'profile': profile.get('name')})
        signals.append(sig)
    return {'ok': True, 'name': norm(name), 'signals': signals, 'count': len(rows)}

def evaluate_weight_profile_v1243(profile, data=None, horizon=20):
    names = historical_target_names_v1241(data)
    all_signals, failures = [], []
    for n in names:
        r = profile_backtest_one_stock_v1243(n, profile, days=365, stride=5, threshold=70)
        if r.get('ok'):
            all_signals.extend(r.get('signals', []))
        else:
            failures.append(f'{r.get("name")}: {r.get("error")}')
    vals = []
    for x in all_signals:
        v = (x.get('returns') or {}).get(str(horizon))
        if v is not None:
            vals.append(float(v))
    if vals:
        wins = sum(1 for v in vals if v > 0)
        losses = [v for v in vals if v < 0]
        avg = sum(vals)/len(vals)
        win_rate = wins/len(vals)*100
        max_loss = min(vals)
        loss_rate = len(losses)/len(vals)*100
        avg_loss = sum(losses)/len(losses) if losses else 0
    else:
        avg = win_rate = loss_rate = avg_loss = 0
        max_loss = 0
    # 목적: 최대손실률을 줄이면서 승률/평균수익률을 보존
    # 최대손실 페널티를 강하게 둔다.
    stability_score = (
        win_rate * 0.40 +
        max(0, avg) * 3.0 -
        abs(min(0, max_loss)) * 2.0 -
        loss_rate * 0.25
    )
    if len(vals) < 8:
        stability_score -= 20  # 표본이 너무 적으면 신뢰도 감점
    return {
        'profile': profile, 'signals': all_signals, 'failures': failures,
        'count': len(vals), 'avg_return': avg, 'win_rate': win_rate,
        'max_loss': max_loss, 'loss_rate': loss_rate, 'avg_loss': avg_loss,
        'stability_score': stability_score,
    }

def run_loss_minimizer_v1243(data=None):
    results = []
    for p in LOSS_MINIMIZER_PROFILES_V1243:
        results.append(evaluate_weight_profile_v1243(p, data=data, horizon=20))
    # 1차: 안정점수, 2차: 최대손실률 작은 순, 3차: 평균수익률
    results = sorted(results, key=lambda x: (x.get('stability_score', -999), x.get('max_loss', -999), x.get('avg_return', -999)), reverse=True)
    payload = {'version': 'V124-3', 'created_at_kst': now_label(), 'purpose': '최대손실률 축소 목적의 가중치 후보 검증', 'results': [
        {k:v for k,v in r.items() if k != 'signals'} for r in results
    ]}
    try:
        if can_write_db():
            write_db_json('weight_optimizer', payload, backup=True)
    except Exception:
        pass
    return results

def render_loss_minimizer_v1243(data=None, compact=False):
    try:
        results = run_loss_minimizer_v1243(data)
    except Exception as e:
        st.markdown(f'<div class="db-card"><div class="db-title">🛡️ V124-3 Loss Minimizer Engine</div><div class="db-action">오류: {str(e)[:160]}</div></div>', unsafe_allow_html=True)
        return
    if not results:
        st.markdown('<div class="db-card"><div class="db-title">🛡️ V124-3 Loss Minimizer Engine</div><div class="db-action">검증 결과가 아직 없습니다.</div></div>', unsafe_allow_html=True)
        return
    best = results[0]
    bp = best.get('profile', {})
    rows_html = ''
    for idx, r in enumerate(results[:6], start=1):
        p = r.get('profile', {})
        medal = '🥇' if idx == 1 else ('🥈' if idx == 2 else ('🥉' if idx == 3 else '▫️'))
        rows_html += (
            '<div class="db-row">'
            f'<div class="db-name">{medal} {p.get("name")} · 안정점수 {r.get("stability_score",0):.1f}</div>'
            f'<div class="db-meta">20일 검증 {r.get("count",0)}건 · 승률 {r.get("win_rate",0):.0f}% · 평균수익률 {r.get("avg_return",0):+.2f}% · 최대손실 {r.get("max_loss",0):+.2f}% · 손실비율 {r.get("loss_rate",0):.0f}%<br>'
            f'가중치: 차트 {p.get("chart")} / 거래량 {p.get("volume")} / 거래대금 {p.get("amount")} / 등락 {p.get("momentum")} / 리스크방어 {p.get("risk")}<br>{p.get("desc")}</div>'
            '</div>'
        )
    rec = (
        f'추천 후보: {bp.get("name")}<br>'
        f'목표: 최고 수익률보다 최대손실률 축소 우선 · 최대손실 {best.get("max_loss",0):+.2f}% · 승률 {best.get("win_rate",0):.0f}%'
    )
    if compact:
        rows_html = rows_html.split('</div><div class="db-row">')[0] + '</div>' if rows_html else rows_html
    html = (
        '<div class="db-card">'
        '<div class="db-title">🛡️ V124-3 Loss Minimizer Engine</div>'
        '<div class="db-sub">여러 가중치 조합을 과거 일봉에 동시에 적용해, 평균수익률만이 아니라 <b>최대손실률을 줄이는 조합</b>을 찾습니다. 가중치는 자동 적용하지 않고 V125에서 승인형으로 넘깁니다.</div>'
        f'<div class="db-action">판정: {rec}</div>'
        f'{rows_html}'
        '<div class="db-sub">※ 표본이 적으면 신뢰도가 낮습니다. 지금은 보유종목 5개 1년 데이터 기준 1차 검증이며, 이후 종목 수를 늘리면 추천 가중치 신뢰도가 올라갑니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)



# V124-4: AUDIT MODE / 점수·승률·손실률 계산 근거 검증판
# 목적: 화면에 표시되는 승률, 평균수익률, 최대손실률이 어떤 파일과 몇 건의 데이터에서 나온 값인지 보여줍니다.
# 원칙: 학습 엔진으로 넘어가기 전, 먼저 숫자의 출처와 표본 수를 검증합니다.
AUDIT_MIN_SAMPLE_WARNING = 30
AUDIT_GOOD_SAMPLE = 100

def audit_file_snapshot_v1244(filename):
    try:
        path = DATA_DIR / filename
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        mtime = '-'
        if exists:
            mt_kst = datetime.utcfromtimestamp(path.stat().st_mtime) + timedelta(hours=9)
            mtime = mt_kst.strftime('%Y-%m-%d %H:%M:%S')
        raw = path.read_text(encoding='utf-8') if exists else ''
        return {'file': filename, 'path': str(path), 'exists': exists, 'size': size, 'mtime': mtime, 'hash': short_hash(raw, 10), 'raw': raw}
    except Exception as e:
        return {'file': filename, 'path': str(DATA_DIR / filename), 'exists': False, 'size': 0, 'mtime': '-', 'hash': 'ERR', 'raw': '', 'error': str(e)[:120]}

def audit_load_json_v1244(filename, default):
    try:
        snap = audit_file_snapshot_v1244(filename)
        if snap.get('exists') and snap.get('raw', '').strip():
            return json.loads(snap['raw'])
    except Exception:
        pass
    return default

def audit_score_history_stats_v1244():
    history = audit_load_json_v1244('score_history.json', [])
    if not isinstance(history, list):
        history = []
    total = len(history)
    returned = 0
    wins = 0
    vals20 = []
    horizon_stats = {}
    score_bins = {
        '90점 이상': [],
        '80~89점': [],
        '70~79점': [],
        '70점 미만': [],
    }
    for row in history:
        score = int(float(row.get('score', 0) or 0))
        returns = row.get('returns') or {}
        for h in BACKTEST_HORIZONS if 'BACKTEST_HORIZONS' in globals() else [1,3,5,20]:
            r = returns.get(str(h))
            if isinstance(r, dict):
                ret = float(r.get('return_pct', 0) or 0)
                horizon_stats.setdefault(h, []).append(ret)
        r20 = returns.get('20')
        if isinstance(r20, dict):
            ret20 = float(r20.get('return_pct', 0) or 0)
            vals20.append(ret20)
            returned += 1
            if ret20 > 0:
                wins += 1
            if score >= 90:
                score_bins['90점 이상'].append(ret20)
            elif score >= 80:
                score_bins['80~89점'].append(ret20)
            elif score >= 70:
                score_bins['70~79점'].append(ret20)
            else:
                score_bins['70점 미만'].append(ret20)
    def pack(vals):
        if not vals:
            return {'count':0,'win_rate':0,'avg':0,'max_loss':0,'loss_rate':0}
        losses=[v for v in vals if v < 0]
        return {
            'count': len(vals),
            'win_rate': sum(1 for v in vals if v > 0) / len(vals) * 100,
            'avg': sum(vals)/len(vals),
            'max_loss': min(vals),
            'loss_rate': len(losses)/len(vals)*100,
        }
    return {
        'history': history,
        'total': total,
        'completed20': returned,
        'win_rate20': wins/returned*100 if returned else 0,
        'avg20': sum(vals20)/len(vals20) if vals20 else 0,
        'max_loss20': min(vals20) if vals20 else 0,
        'bins': {k: pack(v) for k,v in score_bins.items()},
        'horizons': {h: pack(v) for h,v in horizon_stats.items()},
    }

def audit_weight_optimizer_stats_v1244():
    payload = audit_load_json_v1244('weight_optimizer.json', {})
    if not isinstance(payload, dict):
        payload = {}
    results = payload.get('results') or []
    if not isinstance(results, list):
        results = []
    best = results[0] if results else {}
    return {'payload': payload, 'results': results, 'best': best, 'count': len(results)}

def audit_historical_replay_stats_v1244():
    payload = audit_load_json_v1244('historical_replay.json', {})
    if not isinstance(payload, dict):
        payload = {}
    items = payload.get('items') or payload.get('signals') or payload.get('results') or []
    if not isinstance(items, list):
        items = []
    return {'payload': payload, 'items': items, 'count': len(items)}

def audit_sample_label_v1244(n):
    try:
        n = int(n or 0)
        if n >= AUDIT_GOOD_SAMPLE:
            return '🟢 충분'
        if n >= AUDIT_MIN_SAMPLE_WARNING:
            return '🟡 검증중'
        if n > 0:
            return '🟠 표본부족'
        return '🔴 데이터없음'
    except Exception:
        return '🔴 확인불가'

def render_audit_mode_v1244(data=None, compact=False):
    score_snap = audit_file_snapshot_v1244('score_history.json')
    hist_snap = audit_file_snapshot_v1244('historical_replay.json')
    opt_snap = audit_file_snapshot_v1244('weight_optimizer.json')
    sh = audit_score_history_stats_v1244()
    wo = audit_weight_optimizer_stats_v1244()
    hr = audit_historical_replay_stats_v1244()
    sample_label = audit_sample_label_v1244(sh.get('completed20', 0))
    opt_best = wo.get('best') or {}
    opt_profile = opt_best.get('profile') or {}
    if wo.get('count'):
        opt_text = f'{opt_profile.get("name", "가중치 후보")} · 20일 검증 {opt_best.get("count",0)}건 · 승률 {opt_best.get("win_rate",0):.0f}% · 평균 {opt_best.get("avg_return",0):+.2f}% · 최대손실 {opt_best.get("max_loss",0):+.2f}%'
    else:
        opt_text = 'weight_optimizer.json 결과 없음 · V124-3 실행 후 확인 필요'
    stat_line = f'누적기록 {sh.get("total",0)}건 · 20일 검증완료 {sh.get("completed20",0)}건 · 승률 {sh.get("win_rate20",0):.1f}% · 평균 {sh.get("avg20",0):+.2f}% · 최대손실 {sh.get("max_loss20",0):+.2f}%'
    if sh.get('completed20', 0) < AUDIT_MIN_SAMPLE_WARNING:
        verdict = '검증 대기 · 아직 가중치 학습 금지'
    elif sh.get('completed20', 0) < AUDIT_GOOD_SAMPLE:
        verdict = '초기 검증 · 가중치 제안은 참고만'
    else:
        verdict = '학습 검토 가능 · V125 반자동 제안 가능'
    rows_html = ''
    for label, b in sh.get('bins', {}).items():
        rows_html += (
            '<div class="db-row">'
            f'<div class="db-name">{label} · {audit_sample_label_v1244(b.get("count",0))}</div>'
            f'<div class="db-meta">20일 표본 {b.get("count",0)}건 · 승률 {b.get("win_rate",0):.1f}% · 평균수익률 {b.get("avg",0):+.2f}% · 최대손실 {b.get("max_loss",0):+.2f}% · 손실비율 {b.get("loss_rate",0):.1f}%</div>'
            '</div>'
        )
    if compact:
        rows_html = ''
    recent_rows = ''
    for row in (sh.get('history') or [])[-5:][::-1]:
        returns = row.get('returns') or {}
        r20 = returns.get('20') if isinstance(returns, dict) else None
        rtxt = f"20일 {float(r20.get('return_pct',0)):+.2f}%" if isinstance(r20, dict) else '20일 대기'
        recent_rows += (
            '<div class="db-row">'
            f'<div class="db-name">{row.get("signal_date","-")} · {row.get("name","-")} · {row.get("score",0)}점</div>'
            f'<div class="db-meta">진입가 {won(row.get("entry_price",0))} · {rtxt} · 상태 {row.get("review_status","tracking")}</div>'
            '</div>'
        )
    html = (
        '<div class="db-card">'
        '<div class="db-title">🔍 V124-4 Audit Mode</div>'
        '<div class="db-sub">화면에 표시되는 승률·평균수익률·최대손실률이 어떤 파일과 몇 건의 데이터에서 나온 값인지 검증합니다. 학습보다 감사가 먼저입니다.</div>'
        f'<div class="db-action">판정: {verdict}<br>{stat_line}<br>표본상태: {sample_label}</div>'
        '<div class="db-grid">'
        f'<div class="db-box"><div class="db-label">score_history</div><div class="db-value">{score_snap.get("size",0)} byte · {score_snap.get("hash","-")}</div></div>'
        f'<div class="db-box"><div class="db-label">historical_replay</div><div class="db-value">{hist_snap.get("size",0)} byte · {hist_snap.get("hash","-")}</div></div>'
        f'<div class="db-box"><div class="db-label">weight_optimizer</div><div class="db-value">{opt_snap.get("size",0)} byte · {opt_snap.get("hash","-")}</div></div>'
        f'<div class="db-box"><div class="db-label">Replay 표본</div><div class="db-value">{hr.get("count",0)}건</div></div>'
        '</div>'
        f'<div class="db-sub"><b>가중치 우승 후보 근거</b><br>{opt_text}</div>'
        f'{rows_html}'
        f'{recent_rows if not compact else ""}'
        '<div class="db-sub">※ 표본 30건 미만은 판단 보류, 100건 이상부터 가중치 변경 제안 신뢰도가 올라갑니다. 가중치는 자동 변경하지 않습니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# V124-5: BULK HISTORICAL REPLAY / 과거 1년 대량 검증 데이터 확보
# 목적: 실전 데이터가 쌓이기를 기다리지 않고, 보유종목 5개의 과거 1년 일봉을 매 거래일 단위로 재생해
#       점수별 승률·평균수익률·최대손실률을 볼 수 있는 표본을 빠르게 확보합니다.
# 원칙: 실제 score_history.json은 실전 추적 기록으로 보존하고, 과거 대량 재생 결과는 historical_bulk_replay.json에 별도 저장합니다.
HISTORICAL_BULK_FILE_V1245 = DATA_DIR / "historical_bulk_replay.json"
BULK_TARGET_RECORDS_V1245 = 1000


def load_bulk_historical_v1245():
    try:
        if HISTORICAL_BULK_FILE_V1245.exists():
            with open(HISTORICAL_BULK_FILE_V1245, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_bulk_historical_v1245(payload):
    """Cloud/Viewer에서도 검증 데이터는 임시 파일로 저장을 시도합니다.
    포트폴리오 DB와 달리 사용자 보유정보를 바꾸지 않는 검증 산출물이므로 별도 파일로 저장합니다.
    Streamlit Cloud에서는 영구 저장이 아닐 수 있어 다운로드 버튼도 함께 제공합니다.
    """
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(HISTORICAL_BULK_FILE_V1245, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        try:
            if can_write_db():
                write_db_json("historical_bulk_replay", payload, backup=True)
                return True
        except Exception:
            pass
    return False


def bulk_record_from_signal_v1245(sig):
    ret = sig.get("returns") or {}
    r20 = ret.get("20")
    if r20 is None:
        r20 = ret.get(20)
    try:
        r20_val = float(r20)
    except Exception:
        r20_val = None
    return {
        "name": sig.get("name", ""),
        "signal_date": sig.get("date", ""),
        "score": int(sig.get("score", 0) or 0),
        "verdict": sig.get("verdict", ""),
        "entry_price": float(sig.get("close", 0) or 0),
        "volume": float(sig.get("volume", 0) or 0),
        "amount": float(sig.get("amount", 0) or 0),
        "vol_ratio": float(sig.get("vol_ratio", 0) or 0),
        "amt_ratio": float(sig.get("amt_ratio", 0) or 0),
        "change": float(sig.get("change", 0) or 0),
        "returns": {str(k): float(v) for k, v in ret.items() if v is not None},
        "result20": r20_val,
        "success20": bool(r20_val is not None and r20_val > 0),
        "reasons": sig.get("reasons", [])[:6],
        "source": "V124-5 bulk historical replay",
    }


def bulk_stats_v1245(records, horizon=20):
    bins = {
        "90점 이상": lambda x: x >= 90,
        "80~89점": lambda x: 80 <= x < 90,
        "70~79점": lambda x: 70 <= x < 80,
        "60~69점": lambda x: 60 <= x < 70,
        "전체": lambda x: True,
    }
    out = {}
    for label, cond in bins.items():
        vals = []
        for r in records:
            try:
                score = int(r.get("score", 0) or 0)
                if not cond(score):
                    continue
                v = (r.get("returns") or {}).get(str(horizon))
                if v is not None:
                    vals.append(float(v))
            except Exception:
                pass
        if vals:
            wins = sum(1 for v in vals if v > 0)
            losses = [v for v in vals if v < 0]
            avg = sum(vals) / len(vals)
            max_loss = min(vals)
            avg_win = sum([v for v in vals if v > 0]) / wins if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            risk_reward = (avg_win / abs(avg_loss)) if avg_loss < 0 else (avg_win if avg_win else 0)
            out[label] = {
                "count": len(vals),
                "win_rate": wins / len(vals) * 100,
                "avg_return": avg,
                "max_loss": max_loss,
                "loss_rate": len(losses) / len(vals) * 100,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "risk_reward": risk_reward,
            }
        else:
            out[label] = {"count": 0, "win_rate": 0, "avg_return": 0, "max_loss": 0, "loss_rate": 0, "avg_win": 0, "avg_loss": 0, "risk_reward": 0}
    return out


def run_bulk_historical_replay_v1245(data=None, days=365):
    names = historical_target_names_v1241(data)
    all_records = []
    stock_summaries = []
    failures = []
    for n in names:
        try:
            # stride=1: 매 거래일 단위로 재생해 표본을 최대한 확보합니다.
            res = historical_replay_one_stock_v1242(n, days=days, stride=1)
            if not res.get("ok"):
                failures.append(f'{res.get("name", n)}: {res.get("error", "실패")}')
                stock_summaries.append({"name": norm(n), "ok": False, "records": 0, "error": res.get("error", "실패")})
                continue
            signals = res.get("signals") or []
            records = [bulk_record_from_signal_v1245(x) for x in signals]
            all_records.extend(records)
            stock_summaries.append({
                "name": norm(n),
                "ok": True,
                "records": len(records),
                "first_date": records[0].get("signal_date", "-") if records else "-",
                "last_date": records[-1].get("signal_date", "-") if records else "-",
            })
        except Exception as e:
            failures.append(f'{norm(n)}: {str(e)[:120]}')
            stock_summaries.append({"name": norm(n), "ok": False, "records": 0, "error": str(e)[:120]})
    all_records = sorted(all_records, key=lambda x: (x.get("signal_date", ""), x.get("name", "")))
    stats20 = bulk_stats_v1245(all_records, horizon=20)
    payload = {
        "version": "V124-5",
        "created_at_kst": now_label(),
        "purpose": "보유종목+확장 후보 과거 일봉 매 거래일 점수 재생으로 대량 검증 데이터 확보",
        "record_count": len(all_records),
        "target_records": BULK_TARGET_RECORDS_V1245,
        "stocks": stock_summaries,
        "failures": failures,
        "stats20": stats20,
        "records": all_records,
        "note": "실전 score_history와 섞지 않는 과거 재생 데이터입니다. V125 반자동 학습의 표본 후보로 사용합니다.",
    }
    save_bulk_historical_v1245(payload)
    return payload


def bulk_need_refresh_v1245(payload):
    try:
        if not payload or int(payload.get("record_count", 0) or 0) <= 0:
            return True
        created = str(payload.get("created_at_kst", ""))
        if not created:
            return True
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        return (kst_now() - dt).total_seconds() > 21600  # 6시간 이상 지나면 갱신 후보
    except Exception:
        return True


def render_bulk_historical_replay_v1245(data=None, compact=False):
    payload = load_bulk_historical_v1245()
    generated_now = False
    if bulk_need_refresh_v1245(payload):
        try:
            payload = run_bulk_historical_replay_v1245(data, days=365)
            generated_now = True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🧱 V124-5 Bulk Historical Replay</div><div class="db-action">오류: {str(e)[:160]}</div></div>', unsafe_allow_html=True)
            return

    records = payload.get("records") or []
    stats = payload.get("stats20") or {}
    record_count = int(payload.get("record_count", len(records)) or 0)
    if record_count >= BULK_TARGET_RECORDS_V1245:
        verdict = "목표 표본 확보"
        learn_status = "V125 반자동 학습 후보로 사용 가능"
    elif record_count >= 300:
        verdict = "초기 학습 표본 확보"
        learn_status = "가중치 제안은 참고 가능"
    elif record_count >= 100:
        verdict = "기초 표본 확보"
        learn_status = "추가 종목 확장 필요"
    else:
        verdict = "표본 부족"
        learn_status = "학습 금지 · 데이터 추가 필요"

    rows_html = ""
    for label in ["90점 이상", "80~89점", "70~79점", "60~69점", "전체"]:
        b = stats.get(label) or {}
        rows_html += (
            '<div class="db-row">'
            f'<div class="db-name">{label} · 20일 검증 {b.get("count",0)}건</div>'
            f'<div class="db-meta">승률 {b.get("win_rate",0):.1f}% · 평균수익률 {b.get("avg_return",0):+.2f}% · 최대손실 {b.get("max_loss",0):+.2f}% · 손실비율 {b.get("loss_rate",0):.1f}% · 위험대비수익 {b.get("risk_reward",0):.2f}</div>'
            '</div>'
        )
        if compact and label == "80~89점":
            break

    stock_rows = ""
    if not compact:
        for x in payload.get("stocks", [])[:5]:
            ok = "✅" if x.get("ok") else "❌"
            stock_rows += (
                '<div class="db-row">'
                f'<div class="db-name">{ok} {x.get("name","-")} · {x.get("records",0)}건</div>'
                f'<div class="db-meta">기간 {x.get("first_date","-")} ~ {x.get("last_date","-")} {("· 오류 " + x.get("error","")) if x.get("error") else ""}</div>'
                '</div>'
            )
    best = stats.get("90점 이상") or stats.get("80~89점") or {}
    action = f'판정: {verdict}<br>확보 {record_count:,}건 / 목표 {BULK_TARGET_RECORDS_V1245:,}건 · {learn_status}'
    if generated_now:
        action += '<br>이번 실행에서 새로 생성/갱신됨'
    html = (
        '<div class="db-card">'
        '<div class="db-title">🧱 V124-5 Bulk Historical Replay</div>'
        '<div class="db-sub">실전 데이터가 쌓이기를 기다리지 않고, 보유종목 5개의 과거 1년 일봉을 매 거래일 단위로 되감아 점수와 1/3/5/20일 후 수익률을 생성합니다. 실제 score_history와 섞지 않는 별도 검증 데이터입니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows_html}'
        f'{stock_rows}'
        '<div class="db-sub">※ 데이터가 많아진다고 승률이 자동으로 오르는 것은 아닙니다. 대신 진짜 승률·진짜 손실률·위험대비수익률을 더 정확히 알게 됩니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button(
                "📥 historical_bulk_replay.json 다운로드",
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="historical_bulk_replay.json",
                mime="application/json",
                use_container_width=True,
                key="download_historical_bulk_replay_v1245",
            )
        except Exception:
            pass



# V124-6: HYPOTHESIS EXPERIMENT ENGINE / 가설 검증 엔진
# 원칙: 경규님 의견도, AI 의견도 정답으로 보지 않고 모델별로 과거 데이터에서 직접 비교합니다.
# 목표: 현재형 / 차트강화형 / 거래량형 / 매물대형 / 바닥탐지형을 같은 표본에서 비교해
#       승률, 평균수익률, 최대손실, 위험대비수익률을 확인합니다.
EXPERIMENT_FILE_V1246 = DATA_DIR / "hypothesis_experiment.json"

EXPERIMENT_PROFILES_V1246 = [
    {"name": "현재형", "chart": 30, "volume": 25, "amount": 20, "momentum": 10, "risk": 15, "zone": 0, "bottom": 0, "desc": "현재 V124 계열 기본 가중치"},
    {"name": "차트강화형", "chart": 52, "volume": 18, "amount": 12, "momentum": 8, "risk": 10, "zone": 0, "bottom": 0, "desc": "거래량보다 20일선·5/20 정배열·돌파를 우선"},
    {"name": "거래량공격형", "chart": 25, "volume": 42, "amount": 20, "momentum": 8, "risk": 5, "zone": 0, "bottom": 0, "desc": "거래량 폭증을 가장 강하게 반영"},
    {"name": "손실방어형", "chart": 32, "volume": 15, "amount": 13, "momentum": 5, "risk": 35, "zone": 0, "bottom": 0, "desc": "윗꼬리·20일선 아래·대량거래 상승실패 감점 강화"},
    {"name": "매물대형", "chart": 25, "volume": 15, "amount": 12, "momentum": 5, "risk": 13, "zone": 30, "bottom": 0, "desc": "과거 거래가 많이 쌓인 가격대와 현재 위치를 반영"},
    {"name": "바닥탐지형", "chart": 30, "volume": 16, "amount": 10, "momentum": 4, "risk": 15, "zone": 15, "bottom": 10, "desc": "매물대 지지 + 과열 방지 + 바닥탈출 신호를 반영"},
]


def load_experiment_v1246():
    try:
        if EXPERIMENT_FILE_V1246.exists():
            with open(EXPERIMENT_FILE_V1246, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_experiment_v1246(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(EXPERIMENT_FILE_V1246, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def volume_profile_component_v1246(rows, idx, bins=24):
    """과거 데이터만 사용해 간이 매물대 점수를 만듭니다.
    정확한 호가별 매물대가 아니라, 일봉 종가/거래량 기반의 근사치입니다.
    미래 데이터는 사용하지 않습니다.
    """
    try:
        cur = rows[idx]
        close = float(cur.get('close', 0) or 0)
        if close <= 0:
            return {"zone_score": 0, "bottom_score": 0, "support_dist": None, "resistance_dist": None, "note": "현재가 없음"}
        lookback = rows[max(0, idx-120):idx]
        if len(lookback) < 40:
            return {"zone_score": 0, "bottom_score": 0, "support_dist": None, "resistance_dist": None, "note": "매물대 표본 부족"}
        prices = [float(r.get('close', 0) or 0) for r in lookback if float(r.get('close', 0) or 0) > 0]
        vols = [float(r.get('volume', 0) or 0) for r in lookback if float(r.get('close', 0) or 0) > 0]
        if not prices or not vols:
            return {"zone_score": 0, "bottom_score": 0, "support_dist": None, "resistance_dist": None, "note": "매물대 계산 불가"}
        lo, hi = min(prices), max(prices)
        if hi <= lo:
            return {"zone_score": 50, "bottom_score": 40, "support_dist": 0, "resistance_dist": 0, "note": "가격범위 좁음"}
        step = (hi - lo) / bins
        buckets = []
        for i in range(bins):
            buckets.append({"lo": lo+i*step, "hi": lo+(i+1)*step, "vol": 0.0, "mid": lo+(i+0.5)*step})
        for pr, vol in zip(prices, vols):
            bi = int((pr - lo) / step)
            bi = max(0, min(bins-1, bi))
            buckets[bi]["vol"] += vol
        significant = sorted(buckets, key=lambda x: x["vol"], reverse=True)[:max(3, bins//5)]
        supports = [b for b in significant if b["mid"] <= close]
        resistances = [b for b in significant if b["mid"] > close]
        support = max(supports, key=lambda x: x["vol"], default=None)
        resistance = max(resistances, key=lambda x: x["vol"], default=None)
        support_dist = ((close - support["mid"]) / close * 100) if support else None
        resistance_dist = ((resistance["mid"] - close) / close * 100) if resistance else None

        zone_score = 45
        note = []
        # 강한 지지 매물대 바로 위에 있으면 바닥권 가점
        if support_dist is not None:
            if 0 <= support_dist <= 5:
                zone_score += 32; note.append("지지매물대 근접")
            elif support_dist <= 10:
                zone_score += 18; note.append("지지매물대 위")
            elif support_dist >= 35:
                zone_score -= 18; note.append("지지매물대와 이격 큼")
        else:
            zone_score -= 5; note.append("하단 지지매물대 약함")
        # 머리 위 강한 저항이 너무 가까우면 감점
        if resistance_dist is not None:
            if 0 <= resistance_dist <= 5:
                zone_score -= 25; note.append("상단 매물대 저항 근접")
            elif resistance_dist <= 12:
                zone_score -= 10; note.append("상단 저항 확인")
            elif resistance_dist >= 25:
                zone_score += 8; note.append("상단 저항 여유")
        else:
            zone_score += 5; note.append("뚜렷한 상단 저항 적음")

        # 바닥탐지: 최근 60일 저점권에서 지지매물대 위로 거래량이 붙는 경우
        past60 = rows[max(0, idx-60):idx]
        lows = [float(r.get('low', r.get('close', 0)) or 0) for r in past60 if float(r.get('low', r.get('close', 0)) or 0) > 0]
        low60 = min(lows) if lows else close
        low_dist = (close - low60) / close * 100 if close else 0
        comp = score_components_v1243(rows, idx)
        vol_ratio = comp.get('vol_ratio', 0) if comp else 0
        change = comp.get('change', 0) if comp else 0
        bottom_score = 35
        if low_dist <= 12:
            bottom_score += 22
        if support_dist is not None and support_dist <= 8:
            bottom_score += 20
        if 120 <= vol_ratio <= 350 and change >= 0:
            bottom_score += 18
        if vol_ratio >= 500 or change >= 8:
            bottom_score -= 18  # 이미 너무 뜬 자리일 수 있음
        if resistance_dist is not None and resistance_dist <= 6:
            bottom_score -= 15
        return {
            "zone_score": max(0, min(100, int(zone_score))),
            "bottom_score": max(0, min(100, int(bottom_score))),
            "support_dist": support_dist,
            "resistance_dist": resistance_dist,
            "note": " · ".join(note[:4])
        }
    except Exception as e:
        return {"zone_score": 0, "bottom_score": 0, "support_dist": None, "resistance_dist": None, "note": f"오류 {str(e)[:40]}"}


def experiment_components_v1246(rows, idx):
    comp = score_components_v1243(rows, idx)
    if not comp:
        return None
    z = volume_profile_component_v1246(rows, idx)
    comp.update(z)
    return comp


def weighted_score_v1246(comp, profile):
    try:
        score = (
            comp.get('chart_score', 0) * profile.get('chart', 0) +
            comp.get('volume_score', 0) * profile.get('volume', 0) +
            comp.get('amount_score', 0) * profile.get('amount', 0) +
            comp.get('momentum_score', 0) * profile.get('momentum', 0) +
            comp.get('risk_score', 0) * profile.get('risk', 0) +
            comp.get('zone_score', 0) * profile.get('zone', 0) +
            comp.get('bottom_score', 0) * profile.get('bottom', 0)
        ) / 100.0
        # 추격매수 방지 공통 필터
        if comp.get('risk_score', 100) < 55:
            score -= 8
        if comp.get('chart_score', 0) < 40 and score >= 80:
            score -= 10
        if comp.get('zone_score', 50) < 35 and profile.get('zone', 0) > 0:
            score -= 6
        return max(0, min(100, int(round(score))))
    except Exception:
        return 0


def experiment_one_stock_v1246(name, profile, days=365, stride=1, threshold=70):
    res = kis_daily_chart_v1241(name, days=days)
    if not res.get('ok'):
        return {'ok': False, 'name': norm(name), 'error': res.get('error', '일봉 조회 실패'), 'signals': []}
    rows = res.get('rows') or []
    if len(rows) < 65:
        return {'ok': False, 'name': norm(name), 'error': f'일봉 부족 {len(rows)}개', 'signals': []}
    signals = []
    for idx in range(60, max(61, len(rows)-20), max(1, int(stride))):
        comp = experiment_components_v1246(rows, idx)
        if not comp:
            continue
        score = weighted_score_v1246(comp, profile)
        if score < threshold:
            continue
        entry = float(comp.get('close', 0) or 0)
        returns = {}
        for h in [1, 3, 5, 20]:
            if idx + h < len(rows) and entry > 0:
                future = float(rows[idx+h].get('close', 0) or 0)
                returns[str(h)] = pct_change_v1242(future, entry)
        sig = dict(comp)
        sig.update({'name': norm(name), 'score': score, 'returns': returns, 'profile': profile.get('name')})
        signals.append(sig)
    return {'ok': True, 'name': norm(name), 'signals': signals, 'count': len(rows)}


def experiment_stats_v1246(signals, horizon=20):
    vals = []
    for x in signals:
        v = (x.get('returns') or {}).get(str(horizon))
        if v is not None:
            vals.append(float(v))
    if not vals:
        return {"count": 0, "win_rate": 0, "avg_return": 0, "max_loss": 0, "loss_rate": 0, "risk_reward": 0, "fitness": -999}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    avg = sum(vals)/len(vals)
    win_rate = len(wins)/len(vals)*100
    max_loss = min(vals)
    loss_rate = len(losses)/len(vals)*100
    avg_win = sum(wins)/len(wins) if wins else 0
    avg_loss = sum(losses)/len(losses) if losses else 0
    risk_reward = (avg_win / abs(avg_loss)) if avg_loss < 0 else (avg_win if avg_win else 0)
    # 목표: 잃지 않으면서 수익 극대화. 수익/손실 균형 점수.
    fitness = (max(0, avg) * 4.0) + (win_rate * 0.35) + (risk_reward * 8.0) - (abs(min(0, max_loss)) * 1.4) - (loss_rate * 0.18)
    if len(vals) < 30:
        fitness -= 15
    return {"count": len(vals), "win_rate": win_rate, "avg_return": avg, "max_loss": max_loss, "loss_rate": loss_rate, "risk_reward": risk_reward, "avg_win": avg_win, "avg_loss": avg_loss, "fitness": fitness}


def run_hypothesis_experiment_v1246(data=None, days=365):
    names = historical_target_names_v1241(data)
    results = []
    failures = []
    for profile in EXPERIMENT_PROFILES_V1246:
        signals = []
        for n in names:
            r = experiment_one_stock_v1246(n, profile, days=days, stride=1, threshold=70)
            if r.get('ok'):
                signals.extend(r.get('signals', []))
            else:
                failures.append(f'{profile.get("name")} / {r.get("name", n)}: {r.get("error", "실패")}')
        st20 = experiment_stats_v1246(signals, horizon=20)
        st5 = experiment_stats_v1246(signals, horizon=5)
        results.append({"profile": profile, "stats20": st20, "stats5": st5, "signals": signals[:80]})
    results = sorted(results, key=lambda x: x.get('stats20', {}).get('fitness', -999), reverse=True)
    payload = {
        "version": "V124-6",
        "created_at_kst": now_label(),
        "purpose": "현재 공식·차트강화·거래량공격·손실방어·매물대·바닥탐지 가설 비교",
        "record_scope": "보유종목 5개 과거 일봉 기반",
        "results": [{k:v for k,v in r.items() if k != 'signals'} for r in results],
        "sample_signals": {r['profile']['name']: r.get('signals', [])[:10] for r in results},
        "failures": list(dict.fromkeys(failures))[:20],
        "note": "가설 실험 결과입니다. 자동 반영하지 않고 V125에서 사용자가 승인한 모델만 반영합니다.",
    }
    save_experiment_v1246(payload)
    return payload


def experiment_need_refresh_v1246(payload):
    try:
        if not payload or not payload.get('results'):
            return True
        created = str(payload.get('created_at_kst', ''))
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True


def render_hypothesis_experiment_v1246(data=None, compact=False):
    payload = load_experiment_v1246()
    generated = False
    if experiment_need_refresh_v1246(payload):
        try:
            payload = run_hypothesis_experiment_v1246(data, days=365)
            generated = True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🧪 V124-6 Hypothesis Experiment</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    results = payload.get('results') or []
    if not results:
        st.markdown('<div class="db-card"><div class="db-title">🧪 V124-6 Hypothesis Experiment</div><div class="db-action">실험 결과가 아직 없습니다.</div></div>', unsafe_allow_html=True)
        return
    best = results[0]
    bprof = best.get('profile', {})
    bst = best.get('stats20', {})
    action = f'현재 1위 가설: {bprof.get("name", "-")}<br>20일 기준 {bst.get("count",0)}건 · 승률 {bst.get("win_rate",0):.1f}% · 평균수익 {bst.get("avg_return",0):+.2f}% · 최대손실 {bst.get("max_loss",0):+.2f}% · 위험대비수익 {bst.get("risk_reward",0):.2f}'
    if generated:
        action += '<br>이번 실행에서 새로 실험함'
    rows = ''
    for r in results[:6]:
        p = r.get('profile', {})
        st20 = r.get('stats20', {})
        rows += (
            '<div class="db-row">'
            f'<div class="db-name">{p.get("name", "-")} · 적합도 {st20.get("fitness",0):.1f}</div>'
            f'<div class="db-meta">20일 {st20.get("count",0)}건 · 승률 {st20.get("win_rate",0):.1f}% · 평균 {st20.get("avg_return",0):+.2f}% · 최대손실 {st20.get("max_loss",0):+.2f}% · 손실비율 {st20.get("loss_rate",0):.1f}% · 위험대비수익 {st20.get("risk_reward",0):.2f}<br>{p.get("desc", "")}</div>'
            '</div>'
        )
        if compact and len(rows) > 0 and p.get('name') != bprof.get('name'):
            break
    html = (
        '<div class="db-card">'
        '<div class="db-title">🧪 V124-6 Hypothesis Experiment</div>'
        '<div class="db-sub">경규님 의견도 AI 의견도 정답으로 두지 않고, 현재형·차트강화형·거래량공격형·손실방어형·매물대형·바닥탐지형을 같은 과거 데이터에서 비교합니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows}'
        '<div class="db-sub">※ 매물대는 호가별 실제 매물대가 아니라 일봉 가격·거래량 기반의 근사 실험입니다. 결과가 좋을 때만 V125 반자동 학습 후보로 올립니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button(
                "📥 hypothesis_experiment.json 다운로드",
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'),
                file_name="hypothesis_experiment.json",
                mime="application/json",
                use_container_width=True,
                key="download_hypothesis_experiment_v1246",
            )
        except Exception:
            pass


# V124-7: PROFIT FINDER / 수익 플러스 모델 탐색 엔진
# 목적: 손실을 줄이는 것에만 머무르지 않고, 과거 데이터에서 평균수익률이 플러스인 후보 공식을 찾습니다.
# 원칙: 자동 반영 금지. 표본수/평균수익률/최대손실/위험대비수익률을 함께 보고 V125 후보로만 올립니다.
PROFIT_FINDER_FILE_V1247 = DATA_DIR / "profit_finder_v1247.json"

PROFIT_FINDER_PROFILES_V1247 = [
    {"name": "저점반등형", "chart": 30, "volume": 12, "amount": 8, "momentum": 5, "risk": 15, "zone": 15, "bottom": 15, "desc": "52/60일 저점권 + 지지매물대 + 약한 반등을 우선"},
    {"name": "바닥탈출형", "chart": 38, "volume": 15, "amount": 10, "momentum": 7, "risk": 12, "zone": 12, "bottom": 6, "desc": "20일선 회복·거래량 증가 시작·과열 방지를 결합"},
    {"name": "추세초입형", "chart": 48, "volume": 16, "amount": 10, "momentum": 12, "risk": 10, "zone": 4, "bottom": 0, "desc": "5/20일선 개선과 추세 전환 초기 신호 우선"},
    {"name": "균형수익형", "chart": 40, "volume": 18, "amount": 14, "momentum": 8, "risk": 15, "zone": 5, "bottom": 0, "desc": "수익과 손실을 균형 있게 반영"},
    {"name": "저항회피형", "chart": 35, "volume": 12, "amount": 10, "momentum": 8, "risk": 20, "zone": 15, "bottom": 0, "desc": "상단 매물대가 가까운 종목을 강하게 배제"},
    {"name": "고수익도전형", "chart": 35, "volume": 28, "amount": 18, "momentum": 12, "risk": 7, "zone": 0, "bottom": 0, "desc": "큰 수익 가능성은 보되 과열 감점 필터를 병행"},
]


def load_profit_finder_v1247():
    try:
        if PROFIT_FINDER_FILE_V1247.exists():
            with open(PROFIT_FINDER_FILE_V1247, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_profit_finder_v1247(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(PROFIT_FINDER_FILE_V1247, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def profit_candidate_pass_v1247(comp, score, mode):
    """후보 필터. 미래 데이터는 쓰지 않고 그 시점의 컴포넌트만 사용합니다."""
    try:
        change = float(comp.get('change', 0) or 0)
        vol_ratio = float(comp.get('vol_ratio', 0) or 0)
        risk = float(comp.get('risk_score', 0) or 0)
        chart = float(comp.get('chart_score', 0) or 0)
        zone = float(comp.get('zone_score', 50) or 50)
        bottom = float(comp.get('bottom_score', 35) or 35)
        resist = comp.get('resistance_dist')
        support = comp.get('support_dist')

        if score < mode.get('threshold', 70):
            return False
        # 공통: 너무 위험한 자리는 제외
        if risk < mode.get('min_risk', 45):
            return False
        if change >= mode.get('max_change', 12):
            return False
        if vol_ratio >= mode.get('max_vol_ratio', 900):
            return False
        if chart < mode.get('min_chart', 25):
            return False
        # 바닥/매물대형 조건
        if mode.get('need_bottom') and bottom < mode.get('min_bottom', 55):
            return False
        if mode.get('need_zone') and zone < mode.get('min_zone', 55):
            return False
        if mode.get('avoid_resistance') and resist is not None and float(resist) <= mode.get('min_resistance_dist', 5):
            return False
        if mode.get('need_support') and (support is None or float(support) > mode.get('max_support_dist', 12)):
            return False
        return True
    except Exception:
        return False


def profit_finder_one_stock_v1247(name, profile, mode, days=365):
    res = kis_daily_chart_v1241(name, days=days)
    if not res.get('ok'):
        return {'ok': False, 'name': norm(name), 'error': res.get('error', '일봉 조회 실패'), 'signals': []}
    rows = res.get('rows') or []
    if len(rows) < 65:
        return {'ok': False, 'name': norm(name), 'error': f'일봉 부족 {len(rows)}개', 'signals': []}
    signals = []
    for idx in range(60, max(61, len(rows)-20)):
        comp = experiment_components_v1246(rows, idx)
        if not comp:
            continue
        score = weighted_score_v1246(comp, profile)
        if not profit_candidate_pass_v1247(comp, score, mode):
            continue
        entry = float(comp.get('close', 0) or 0)
        returns = {}
        for h in [1, 3, 5, 20]:
            if idx + h < len(rows) and entry > 0:
                future = float(rows[idx+h].get('close', 0) or 0)
                returns[str(h)] = pct_change_v1242(future, entry)
        sig = dict(comp)
        sig.update({'name': norm(name), 'score': score, 'returns': returns, 'profile': profile.get('name'), 'mode': mode.get('name')})
        signals.append(sig)
    return {'ok': True, 'name': norm(name), 'signals': signals, 'count': len(rows)}


def profit_fitness_v1247(stats):
    # 목표: 평균수익률 플러스 + 최대손실 억제 + 표본수 신뢰도
    try:
        cnt = float(stats.get('count', 0) or 0)
        avg = float(stats.get('avg_return', 0) or 0)
        win = float(stats.get('win_rate', 0) or 0)
        loss = abs(min(0, float(stats.get('max_loss', 0) or 0)))
        rr = float(stats.get('risk_reward', 0) or 0)
        loss_rate = float(stats.get('loss_rate', 0) or 0)
        score = avg * 10 + win * 0.25 + rr * 10 - loss * 0.9 - loss_rate * 0.12
        if avg <= 0:
            score -= 25
        if cnt < 20:
            score -= 20
        elif cnt < 50:
            score -= 8
        return score
    except Exception:
        return -999


def run_profit_finder_v1247(data=None, days=365):
    names = historical_target_names_v1241(data)
    modes = [
        {"name": "기본필터", "threshold": 68, "min_risk": 45, "max_change": 12, "max_vol_ratio": 900, "min_chart": 25},
        {"name": "보수필터", "threshold": 72, "min_risk": 55, "max_change": 8, "max_vol_ratio": 500, "min_chart": 35},
        {"name": "바닥필터", "threshold": 65, "min_risk": 45, "max_change": 8, "max_vol_ratio": 450, "min_chart": 25, "need_bottom": True, "min_bottom": 58},
        {"name": "매물대필터", "threshold": 65, "min_risk": 45, "max_change": 10, "max_vol_ratio": 600, "min_chart": 25, "need_zone": True, "min_zone": 58, "avoid_resistance": True, "min_resistance_dist": 5},
        {"name": "지지선필터", "threshold": 62, "min_risk": 45, "max_change": 10, "max_vol_ratio": 600, "min_chart": 20, "need_support": True, "max_support_dist": 10},
    ]
    results = []
    failures = []
    for profile in PROFIT_FINDER_PROFILES_V1247:
        for mode in modes:
            signals = []
            for n in names:
                r = profit_finder_one_stock_v1247(n, profile, mode, days=days)
                if r.get('ok'):
                    signals.extend(r.get('signals', []))
                else:
                    failures.append(f'{profile.get("name")} / {mode.get("name")} / {r.get("name", n)}: {r.get("error", "실패")}')
            st20 = experiment_stats_v1246(signals, horizon=20)
            st5 = experiment_stats_v1246(signals, horizon=5)
            st20['profit_fitness'] = profit_fitness_v1247(st20)
            results.append({'profile': profile, 'mode': mode, 'stats20': st20, 'stats5': st5, 'signals': signals[:60]})
    results = sorted(results, key=lambda x: x.get('stats20', {}).get('profit_fitness', -999), reverse=True)
    positive = [r for r in results if r.get('stats20', {}).get('avg_return', 0) > 0 and r.get('stats20', {}).get('count', 0) >= 10]
    payload = {
        'version': 'V124-7',
        'created_at_kst': now_label(),
        'purpose': '평균수익률 플러스 모델 탐색',
        'record_scope': '보유종목 5개 과거 일봉 기반',
        'results': [{k:v for k,v in r.items() if k != 'signals'} for r in results[:20]],
        'positive_count': len(positive),
        'sample_signals': {f"{r['profile']['name']}+{r['mode']['name']}": r.get('signals', [])[:8] for r in results[:5]},
        'failures': list(dict.fromkeys(failures))[:20],
        'note': '양수 모델을 찾는 실험입니다. 표본이 적으면 V125 반영 금지입니다.',
    }
    save_profit_finder_v1247(payload)
    return payload


def profit_finder_need_refresh_v1247(payload):
    try:
        if not payload or not payload.get('results'):
            return True
        created = str(payload.get('created_at_kst', ''))
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True


def render_profit_finder_v1247(data=None, compact=False):
    payload = load_profit_finder_v1247()
    generated = False
    if profit_finder_need_refresh_v1247(payload):
        try:
            payload = run_profit_finder_v1247(data, days=365)
            generated = True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🔎 V124-7 Profit Finder</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    results = payload.get('results') or []
    if not results:
        st.markdown('<div class="db-card"><div class="db-title">🔎 V124-7 Profit Finder</div><div class="db-action">실험 결과가 아직 없습니다.</div></div>', unsafe_allow_html=True)
        return
    best = results[0]
    p = best.get('profile', {})
    m = best.get('mode', {})
    st20 = best.get('stats20', {})
    pos_count = int(payload.get('positive_count', 0) or 0)
    if pos_count > 0:
        verdict = '플러스 후보 발견'
    else:
        verdict = '아직 플러스 후보 없음 · 조건 재탐색 필요'
    action = f'판정: {verdict}<br>1위 {p.get("name", "-")} + {m.get("name", "-")} · 20일 {st20.get("count",0)}건 · 승률 {st20.get("win_rate",0):.1f}% · 평균수익 {st20.get("avg_return",0):+.2f}% · 최대손실 {st20.get("max_loss",0):+.2f}% · 위험대비수익 {st20.get("risk_reward",0):.2f}'
    if generated:
        action += '<br>이번 실행에서 새로 탐색함'
    rows = ''
    for r in results[:6]:
        p = r.get('profile', {})
        m = r.get('mode', {})
        st20 = r.get('stats20', {})
        mark = '🟢' if st20.get('avg_return',0) > 0 else '⚪'
        rows += (
            '<div class="db-row">'
            f'<div class="db-name">{mark} {p.get("name", "-")} + {m.get("name", "-")} · 적합도 {st20.get("profit_fitness",0):.1f}</div>'
            f'<div class="db-meta">20일 {st20.get("count",0)}건 · 승률 {st20.get("win_rate",0):.1f}% · 평균 {st20.get("avg_return",0):+.2f}% · 최대손실 {st20.get("max_loss",0):+.2f}% · 손실비율 {st20.get("loss_rate",0):.1f}% · 위험대비수익 {st20.get("risk_reward",0):.2f}<br>{p.get("desc", "")} / 필터: {m.get("name", "-")}</div>'
            '</div>'
        )
        if compact and len(rows) > 0 and r is not results[0]:
            break
    html = (
        '<div class="db-card">'
        '<div class="db-title">🔎 V124-7 Profit Finder</div>'
        '<div class="db-sub">평균수익률이 플러스인 첫 모델을 찾기 위해, 바닥·추세초입·매물대·저항회피 조건을 여러 필터로 조합해 비교합니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows}'
        '<div class="db-sub">※ 목표는 승률 100%가 아니라, 수익은 크게 열고 손실은 제한하는 조합을 찾는 것입니다. 표본이 적으면 자동 반영하지 않습니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button(
                '📥 profit_finder_v1247.json 다운로드',
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'),
                file_name='profit_finder_v1247.json',
                mime='application/json',
                use_container_width=True,
                key='download_profit_finder_v1247',
            )
        except Exception:
            pass



# V124-8: DATA FACTORY DEBUG / 일봉 구간 분할 + 표본 공장 진단
# 목적: 220건에서 멈춘 원인을 종목 수/수집 일봉 수/Replay 생성 건수로 분해하고,
#       KIS 일봉 100봉 제한 가능성을 날짜 구간 분할 요청으로 우회합니다.
DATA_FACTORY_FILE_V1248 = DATA_DIR / "data_factory_debug.json"
BULK_TARGET_RECORDS_V1245 = 5000

@st.cache_data(ttl=3600, show_spinner=False)
def kis_daily_chart_v1248_chunked_cached(name, days=520, chunk_days=110):
    n = norm(name)
    end_dt = kst_now()
    start_dt = end_dt - timedelta(days=int(days) + 30)
    chunks = []
    cur_end = end_dt
    # 최근 구간부터 과거로 나누어 요청합니다. KIS가 한 번에 약 100봉만 주는 경우를 우회하기 위한 구조입니다.
    while cur_end >= start_dt:
        cur_start = max(start_dt, cur_end - timedelta(days=int(chunk_days)))
        s = cur_start.strftime('%Y%m%d')
        e = cur_end.strftime('%Y%m%d')
        try:
            res = kis_daily_chart_v1241_cached(n, s, e)
        except Exception as ex:
            res = {"ok": False, "rows": [], "count": 0, "error": str(ex)[:120]}
        chunks.append({
            "start": s,
            "end": e,
            "ok": bool(res.get("ok")),
            "count": int(res.get("count", 0) or 0),
            "error": res.get("error", ""),
            "rows": res.get("rows") or [],
        })
        cur_end = cur_start - timedelta(days=1)
        if len(chunks) > 12:
            break

    merged = {}
    errors = []
    for ch in chunks:
        if ch.get("error"):
            errors.append(f'{ch.get("start")}-{ch.get("end")}: {ch.get("error")}')
        for row in ch.get("rows") or []:
            d = row.get("date")
            if d:
                merged[d] = row
    rows = sorted(merged.values(), key=lambda x: x.get("date", ""))
    code = code_map().get(n, "")
    return {
        "ok": len(rows) > 0,
        "name": n,
        "code": code,
        "rows": rows,
        "count": len(rows),
        "chunks": [{k:v for k,v in ch.items() if k != "rows"} for ch in chunks],
        "chunk_count": len(chunks),
        "raw_row_count": sum(int(ch.get("count", 0) or 0) for ch in chunks),
        "error": "" if rows else ("; ".join(errors[:3]) or "일봉 데이터 없음"),
        "errors": errors[:8],
        "source": "V124-8 chunked daily chart",
    }

def kis_daily_chart_v1248(name, days=520):
    # 365일보다 넉넉하게 520일을 기본 조회해 실제 거래일 250일 이상 확보를 노립니다.
    return kis_daily_chart_v1248_chunked_cached(norm(name), int(days), 110)

# 기존 historical_replay_one_stock_v1242가 호출하는 이름을 V124-8 분할조회 엔진으로 교체합니다.
kis_daily_chart_v1241 = kis_daily_chart_v1248

def data_factory_save_v1248(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(DATA_FACTORY_FILE_V1248, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def data_factory_load_v1248():
    try:
        if DATA_FACTORY_FILE_V1248.exists():
            with open(DATA_FACTORY_FILE_V1248, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}

def data_factory_need_refresh_v1248(payload):
    try:
        if not payload or not payload.get("stocks"):
            return True
        created = str(payload.get("created_at_kst", ""))
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True

def run_data_factory_v1248(data=None, days=520):
    names = historical_target_names_v1241(data)
    stocks = []
    total_rows = 0
    total_replay_est = 0
    failures = []
    for n in names:
        try:
            res = kis_daily_chart_v1248(n, days=days)
            rows = res.get("rows") or []
            row_count = len(rows)
            # replay 생성 가능 건수 추정: 초기 25봉 + 미래 20봉 제외
            replay_possible = max(0, row_count - 45)
            total_rows += row_count
            total_replay_est += replay_possible
            if not res.get("ok"):
                failures.append(f'{norm(n)}: {res.get("error", "실패")}')
            stocks.append({
                "name": norm(n),
                "code": code_map().get(norm(n), ""),
                "ok": bool(res.get("ok")),
                "daily_rows": row_count,
                "raw_rows": int(res.get("raw_row_count", row_count) or row_count),
                "replay_possible": replay_possible,
                "first_date": rows[0].get("date", "-") if rows else "-",
                "last_date": rows[-1].get("date", "-") if rows else "-",
                "chunks": res.get("chunks") or [],
                "chunk_count": int(res.get("chunk_count", 0) or 0),
                "error": res.get("error", ""),
            })
        except Exception as e:
            failures.append(f'{norm(n)}: {str(e)[:120]}')
            stocks.append({"name": norm(n), "ok": False, "daily_rows": 0, "replay_possible": 0, "error": str(e)[:120], "chunks": []})
    payload = {
        "version": "V124-8",
        "created_at_kst": now_label(),
        "purpose": "Data Factory Debug - 종목 수/일봉 수/Replay 가능 표본 수 분해",
        "target_records": 5000,
        "target_daily_rows_per_stock": 220,
        "stock_count": len(names),
        "ok_stock_count": sum(1 for s in stocks if s.get("ok")),
        "total_daily_rows": total_rows,
        "estimated_replay_records": total_replay_est,
        "stocks": stocks,
        "failures": failures[:30],
        "note": "이 결과는 5000건 확보 전, 어디서 표본이 줄어드는지 확인하기 위한 진단 데이터입니다.",
    }
    data_factory_save_v1248(payload)
    return payload

def render_data_factory_v1248(data=None, compact=False):
    payload = data_factory_load_v1248()
    generated = False
    if data_factory_need_refresh_v1248(payload):
        try:
            payload = run_data_factory_v1248(data, days=520)
            generated = True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🏭 V124-8 Data Factory Debug</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    stock_count = int(payload.get("stock_count", 0) or 0)
    ok_count = int(payload.get("ok_stock_count", 0) or 0)
    daily_rows = int(payload.get("total_daily_rows", 0) or 0)
    replay_est = int(payload.get("estimated_replay_records", 0) or 0)
    target = int(payload.get("target_records", 5000) or 5000)
    if replay_est >= target:
        verdict = "5000건 후보 확보 가능"
        status = "V125 학습 전 표본 조건 충족 후보"
    elif replay_est >= 1000:
        verdict = "1000건 이상 확보 가능"
        status = "초기 모델 비교 가능 · 5000건 확장 계속 필요"
    elif replay_est >= 300:
        verdict = "기초 표본 확보"
        status = "가설 참고 가능 · 학습 금지"
    else:
        verdict = "표본 부족"
        status = "종목/기간/데이터소스 확장 필요"
    rows_html = ""
    stocks = payload.get("stocks") or []
    for x in sorted(stocks, key=lambda z: z.get("replay_possible", 0), reverse=True)[:(5 if compact else 25)]:
        ok = "✅" if x.get("ok") else "❌"
        chunk_text = " / ".join([f'{c.get("count",0)}봉' for c in (x.get("chunks") or [])[:5]])
        rows_html += (
            '<div class="db-row">'
            f'<div class="db-name">{ok} {x.get("name","-")} · 일봉 {x.get("daily_rows",0)}개 · Replay가능 {x.get("replay_possible",0)}건</div>'
            f'<div class="db-meta">기간 {x.get("first_date","-")} ~ {x.get("last_date","-")} · 요청구간 {x.get("chunk_count",0)}개 · 구간별 {chunk_text or "-"}{("<br>오류: " + x.get("error", "")) if x.get("error") else ""}</div>'
            '</div>'
        )
    action = f'판정: {verdict}<br>종목 {ok_count}/{stock_count}개 성공 · 일봉 {daily_rows:,}개 · Replay 가능 추정 {replay_est:,}건 / 목표 {target:,}건<br>{status}'
    if generated:
        action += '<br>이번 실행에서 새로 진단함'
    html = (
        '<div class="db-card">'
        '<div class="db-title">🏭 V124-8 Data Factory Debug</div>'
        '<div class="db-sub">220건에서 멈춘 원인을 해부하기 위해 종목별 실제 수집 일봉 수, 날짜 구간 분할 결과, Replay 가능 건수를 표시합니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows_html}'
        '<div class="db-sub">※ 여기서 Replay 가능 건수가 5000건에 못 미치면 모델 비교보다 데이터 확보가 우선입니다. 구간 분할로도 부족하면 종목 확대 또는 대체 데이터 소스가 필요합니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button(
                '📥 data_factory_debug_v1248.json 다운로드',
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'),
                file_name='data_factory_debug_v1248.json',
                mime='application/json',
                use_container_width=True,
                key='download_data_factory_debug_v1248',
            )
        except Exception:
            pass



# V124-9: FAILURE ANALYZER / 5,000건 표본 성공·실패 해부
# 목적: 점수와 모델을 바로 믿지 않고, 실제 과거 Replay 데이터에서 왜 벌고 왜 잃었는지 먼저 확인합니다.
# 원칙: 실패 원인 분석은 가설입니다. V125에서 자동 반영하지 않고 경규님 승인 후 가중치 변경 후보로만 사용합니다.
FAILURE_ANALYZER_FILE_V1249 = DATA_DIR / "failure_analyzer_v1249.json"
FAILURE_MIN_RECORDS_V1249 = 1000


def load_failure_analyzer_v1249():
    try:
        if FAILURE_ANALYZER_FILE_V1249.exists():
            with open(FAILURE_ANALYZER_FILE_V1249, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_failure_analyzer_v1249(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(FAILURE_ANALYZER_FILE_V1249, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def ret_value_v1249(record, horizon=20):
    try:
        returns = record.get("returns") or {}
        v = returns.get(str(horizon))
        if v is None:
            v = returns.get(horizon)
        if v is None:
            v = record.get(f"ret_{horizon}")
        if v is None and horizon == 20:
            v = record.get("result20")
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def record_flags_v1249(record):
    """실패/성공 패턴 집계용 간단 플래그. 실제 호가 매물대가 아니라 일봉 기반 근사입니다."""
    flags = []
    try:
        score = int(record.get("score", 0) or 0)
        if score >= 90:
            flags.append("90점 이상 고점수")
        elif score >= 80:
            flags.append("80점대")
        elif score >= 70:
            flags.append("70점대")
    except Exception:
        score = 0
    try:
        vol = float(record.get("vol_ratio", 0) or 0)
        if vol >= 1000:
            flags.append("거래량 과열")
        elif vol >= 300:
            flags.append("거래량 급증")
        elif vol <= 80:
            flags.append("거래량 약함")
    except Exception:
        pass
    try:
        amt = float(record.get("amt_ratio", 0) or 0)
        if amt >= 1000:
            flags.append("거래대금 과열")
        elif amt >= 300:
            flags.append("거래대금 급증")
        elif amt <= 80:
            flags.append("거래대금 약함")
    except Exception:
        pass
    try:
        chg = float(record.get("change", 0) or 0)
        if chg >= 10:
            flags.append("당일 급등 추격")
        elif chg >= 5:
            flags.append("당일 강한 상승")
        elif chg <= -5:
            flags.append("당일 급락")
        elif -2 <= chg <= 2:
            flags.append("잔파도 구간")
    except Exception:
        pass
    reason_text = " ".join([str(x) for x in record.get("reasons", [])])
    if "20일선" in reason_text:
        flags.append("20일선 언급")
    if "5일선" in reason_text:
        flags.append("5일선 언급")
    if "거래량" in reason_text:
        flags.append("거래량 근거")
    if "거래대금" in reason_text:
        flags.append("거래대금 근거")
    if "위험" in reason_text or "이탈" in reason_text:
        flags.append("위험/이탈 근거")
    verdict = str(record.get("verdict", ""))
    if "유입" in verdict:
        flags.append("스마트머니 유입 판정")
    if "주의" in verdict or "위험" in verdict:
        flags.append("주의/위험 판정")
    return list(dict.fromkeys(flags))


def top_flag_counts_v1249(records, horizon=20, topn=8):
    counts = {}
    for r in records:
        for f in record_flags_v1249(r):
            counts[f] = counts.get(f, 0) + 1
    rows = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:topn]
    total = len(records) or 1
    return [{"flag": k, "count": v, "rate": v / total * 100} for k, v in rows]


def compact_record_v1249(r, horizon=20):
    ret = ret_value_v1249(r, horizon)
    return {
        "name": r.get("name", "-"),
        "date": r.get("signal_date", r.get("date", "-")),
        "score": int(r.get("score", 0) or 0),
        "return": ret,
        "entry_price": r.get("entry_price", r.get("close", 0)),
        "change": float(r.get("change", 0) or 0),
        "vol_ratio": float(r.get("vol_ratio", 0) or 0),
        "amt_ratio": float(r.get("amt_ratio", 0) or 0),
        "flags": record_flags_v1249(r)[:6],
        "reasons": r.get("reasons", [])[:4],
    }


def analyze_failure_v1249(records, horizon=20):
    valid = []
    for r in records:
        ret = ret_value_v1249(r, horizon)
        if ret is not None:
            valid.append(r)
    wins = [r for r in valid if ret_value_v1249(r, horizon) > 0]
    losses = [r for r in valid if ret_value_v1249(r, horizon) < 0]
    flat = [r for r in valid if ret_value_v1249(r, horizon) == 0]
    vals = [ret_value_v1249(r, horizon) for r in valid]
    avg = sum(vals) / len(vals) if vals else 0
    max_loss = min(vals) if vals else 0
    max_gain = max(vals) if vals else 0
    avg_win = sum([ret_value_v1249(r, horizon) for r in wins]) / len(wins) if wins else 0
    avg_loss = sum([ret_value_v1249(r, horizon) for r in losses]) / len(losses) if losses else 0
    risk_reward = (avg_win / abs(avg_loss)) if avg_loss < 0 else (avg_win if avg_win else 0)
    worst = sorted(valid, key=lambda r: ret_value_v1249(r, horizon))[:20]
    best = sorted(valid, key=lambda r: ret_value_v1249(r, horizon), reverse=True)[:20]
    high_score_losses = [r for r in losses if int(r.get("score", 0) or 0) >= 80]
    high_score_wins = [r for r in wins if int(r.get("score", 0) or 0) >= 80]
    return {
        "horizon": horizon,
        "total": len(valid),
        "wins": len(wins),
        "losses": len(losses),
        "flat": len(flat),
        "win_rate": len(wins) / len(valid) * 100 if valid else 0,
        "avg_return": avg,
        "max_loss": max_loss,
        "max_gain": max_gain,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "risk_reward": risk_reward,
        "loss_patterns": top_flag_counts_v1249(losses, horizon=horizon, topn=10),
        "win_patterns": top_flag_counts_v1249(wins, horizon=horizon, topn=10),
        "high_score_loss_patterns": top_flag_counts_v1249(high_score_losses, horizon=horizon, topn=10),
        "high_score_win_patterns": top_flag_counts_v1249(high_score_wins, horizon=horizon, topn=10),
        "worst20": [compact_record_v1249(r, horizon) for r in worst],
        "best20": [compact_record_v1249(r, horizon) for r in best],
        "high_score_loss_count": len(high_score_losses),
        "high_score_win_count": len(high_score_wins),
    }


def run_failure_analyzer_v1249(data=None):
    bulk = load_bulk_historical_v1245() if "load_bulk_historical_v1245" in globals() else {}
    records = bulk.get("records") or []
    regenerated = False
    # 1000건 미만이면 V124-8 분할조회 엔진 기준으로 Bulk Replay를 새로 생성합니다.
    if len(records) < FAILURE_MIN_RECORDS_V1249 and "run_bulk_historical_replay_v1245" in globals():
        try:
            bulk = run_bulk_historical_replay_v1245(data, days=520)
            records = bulk.get("records") or []
            regenerated = True
        except Exception:
            pass
    analysis20 = analyze_failure_v1249(records, horizon=20)
    payload = {
        "version": "V124-9",
        "created_at_kst": now_label(),
        "source_file": "historical_bulk_replay.json",
        "source_records": len(records),
        "regenerated_bulk": regenerated,
        "analysis20": analysis20,
        "note": "실패 원인 해부용입니다. 자동 매수/매도 또는 가중치 자동 변경에 사용하지 않습니다.",
    }
    save_failure_analyzer_v1249(payload)
    return payload


def failure_need_refresh_v1249(payload):
    try:
        if not payload or not payload.get("analysis20"):
            return True
        bulk = load_bulk_historical_v1245()
        if int(payload.get("source_records", 0) or 0) != int(bulk.get("record_count", len(bulk.get("records") or [])) or 0):
            return True
        created = str(payload.get("created_at_kst", ""))
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True


def render_pattern_rows_v1249(title, rows):
    html = f'<div class="db-row"><div class="db-name">{title}</div><div class="db-meta">'
    if not rows:
        html += '표본 없음'
    else:
        html += '<br>'.join([f'{i+1}. {x.get("flag")} · {x.get("count")}건 · {x.get("rate",0):.1f}%' for i, x in enumerate(rows[:6])])
    html += '</div></div>'
    return html


def render_case_rows_v1249(title, rows, limit=5):
    html = f'<div class="db-row"><div class="db-name">{title}</div><div class="db-meta">'
    if not rows:
        html += '표본 없음'
    else:
        parts = []
        for x in rows[:limit]:
            flags = ' · '.join(x.get('flags', [])[:3])
            parts.append(f'{x.get("date")} {x.get("name")} · {x.get("score")}점 · 20일 {x.get("return",0):+.2f}% · {flags}')
        html += '<br>'.join(parts)
    html += '</div></div>'
    return html


def render_failure_analyzer_v1249(data=None, compact=False):
    payload = load_failure_analyzer_v1249()
    generated = False
    if failure_need_refresh_v1249(payload):
        try:
            payload = run_failure_analyzer_v1249(data)
            generated = True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🔬 V124-9 Failure Analyzer</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    a = payload.get("analysis20") or {}
    total = int(a.get("total", 0) or 0)
    if total >= 5000:
        verdict = "해부 가능 표본 확보"
    elif total >= 1000:
        verdict = "초기 해부 가능"
    else:
        verdict = "표본 부족 · 판단 보류"
    action = (
        f'판정: {verdict}<br>'
        f'20일 검증 {total:,}건 · 승률 {a.get("win_rate",0):.1f}% · 평균수익 {a.get("avg_return",0):+.2f}% · '
        f'최대손실 {a.get("max_loss",0):+.2f}% · 최대수익 {a.get("max_gain",0):+.2f}% · 위험대비수익 {a.get("risk_reward",0):.2f}'
    )
    if generated or payload.get("regenerated_bulk"):
        action += '<br>이번 실행에서 분석/데이터를 새로 갱신함'
    rows = ''
    rows += render_pattern_rows_v1249('실패 공통 패턴 TOP', a.get('loss_patterns') or [])
    rows += render_pattern_rows_v1249('성공 공통 패턴 TOP', a.get('win_patterns') or [])
    if not compact:
        rows += render_pattern_rows_v1249('80점 이상 실패 패턴', a.get('high_score_loss_patterns') or [])
        rows += render_pattern_rows_v1249('80점 이상 성공 패턴', a.get('high_score_win_patterns') or [])
        rows += render_case_rows_v1249('최악 손실 TOP 사례', a.get('worst20') or [], limit=10)
        rows += render_case_rows_v1249('최고 수익 TOP 사례', a.get('best20') or [], limit=10)
    else:
        rows += render_case_rows_v1249('최악 손실 예시', a.get('worst20') or [], limit=3)
    html = (
        '<div class="db-card">'
        '<div class="db-title">🔬 V124-9 Failure Analyzer</div>'
        '<div class="db-sub">5993건 수준의 과거 Replay 데이터를 기준으로 성공보다 실패를 먼저 해부합니다. 가짜 바닥과 추격 실패 조건을 찾기 위한 검증 카드입니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows}'
        '<div class="db-sub">※ 이 결과는 가설 추출용입니다. V125에서 가중치 변경 후보로 제안할 수 있지만 자동 반영하지 않습니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button(
                '📥 failure_analyzer_v1249.json 다운로드',
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'),
                file_name='failure_analyzer_v1249.json',
                mime='application/json',
                use_container_width=True,
                key='download_failure_analyzer_v1249',
            )
        except Exception:
            pass



# V124-10: Support / 매물대 근사 검증 엔진
# 목적: 5일선/20일선만으로 성공·실패 구분이 약한지 확인한 뒤,
#       지지선·저점거리·매물대 근사 위치가 실제 20일 수익률을 개선하는지 검증합니다.
# 주의: 실제 호가창 매물대가 아니라 과거 일봉 종가×거래량 기반의 근사 매물대입니다.
SUPPORT_ANALYZER_FILE_V12410 = DATA_DIR / "support_analyzer_v12410.json"
SUPPORT_MIN_RECORDS_V12410 = 1000


def load_support_analyzer_v12410():
    try:
        if SUPPORT_ANALYZER_FILE_V12410.exists():
            with open(SUPPORT_ANALYZER_FILE_V12410, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_support_analyzer_v12410(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(SUPPORT_ANALYZER_FILE_V12410, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def rr_pct_v12410(future, entry):
    try:
        if entry and float(entry) > 0:
            return (float(future) - float(entry)) / float(entry) * 100
    except Exception:
        pass
    return None


def volume_profile_zone_v12410(past_rows, close, bins=18):
    """일봉 종가와 거래량으로 근사 매물대를 계산합니다."""
    try:
        prices = [float(r.get('close', 0) or 0) for r in past_rows if float(r.get('close', 0) or 0) > 0]
        if len(prices) < 40 or close <= 0:
            return {}
        lo, hi = min(prices), max(prices)
        if hi <= lo:
            return {}
        width = (hi - lo) / bins
        buckets = []
        for i in range(bins):
            buckets.append({'lo': lo + width*i, 'hi': lo + width*(i+1), 'vol': 0.0, 'mid': lo + width*(i+0.5)})
        for r in past_rows:
            p = float(r.get('close', 0) or 0)
            v = float(r.get('volume', 0) or 0)
            if p <= 0:
                continue
            idx = int((p - lo) / width)
            idx = max(0, min(bins-1, idx))
            buckets[idx]['vol'] += v
        ranked = sorted(buckets, key=lambda x: x['vol'], reverse=True)
        # 현재가 아래의 가장 강한 매물대 = 지지 매물대 근사
        below = [b for b in buckets if b['mid'] <= close and b['vol'] > 0]
        above = [b for b in buckets if b['mid'] > close and b['vol'] > 0]
        support = sorted(below, key=lambda x: (x['vol'], x['mid']), reverse=True)[0] if below else None
        resistance = sorted(above, key=lambda x: x['vol'], reverse=True)[0] if above else None
        top = ranked[0] if ranked else None
        return {
            'support_price': support['mid'] if support else None,
            'resistance_price': resistance['mid'] if resistance else None,
            'top_zone_price': top['mid'] if top else None,
            'support_dist': (close / support['mid'] - 1) * 100 if support and support['mid'] else None,
            'resistance_room': (resistance['mid'] / close - 1) * 100 if resistance and close else None,
            'top_zone_dist': (close / top['mid'] - 1) * 100 if top and top['mid'] else None,
        }
    except Exception:
        return {}


def support_features_v12410(rows, idx):
    try:
        cur = rows[idx]
        close = float(cur.get('close', 0) or 0)
        if close <= 0:
            return None
        past20 = rows[max(0, idx-20):idx]
        past60 = rows[max(0, idx-60):idx]
        past120 = rows[max(0, idx-120):idx]
        if len(past60) < 45:
            return None
        ma20 = mean_safe_v1242([r.get('close', 0) for r in past20]) or close
        low60 = min([float(r.get('low', r.get('close', 0)) or 0) for r in past60 if float(r.get('low', r.get('close', 0)) or 0) > 0] or [close])
        high60 = max([float(r.get('high', r.get('close', 0)) or 0) for r in past60 if float(r.get('high', r.get('close', 0)) or 0) > 0] or [close])
        low120 = min([float(r.get('low', r.get('close', 0)) or 0) for r in past120 if float(r.get('low', r.get('close', 0)) or 0) > 0] or [low60])
        high120 = max([float(r.get('high', r.get('close', 0)) or 0) for r in past120 if float(r.get('high', r.get('close', 0)) or 0) > 0] or [high60])
        profile = volume_profile_zone_v12410(past120 if len(past120) >= 60 else past60, close)
        dist60_low = (close / low60 - 1) * 100 if low60 else 999
        dist120_low = (close / low120 - 1) * 100 if low120 else 999
        room60_high = (high60 / close - 1) * 100 if close else 0
        room120_high = (high120 / close - 1) * 100 if close else 0
        support_dist = profile.get('support_dist')
        resist_room = profile.get('resistance_room')
        near_low = 0 <= dist60_low <= 12 or 0 <= dist120_low <= 15
        near_support = support_dist is not None and 0 <= support_dist <= 8
        enough_room = (resist_room is None or resist_room >= 8) and room60_high >= 8
        above_ma20 = close >= ma20
        flags = []
        if near_low: flags.append('저점 근처')
        if near_support: flags.append('매물대 지지 근처')
        if enough_room: flags.append('상단 여유 있음')
        if above_ma20: flags.append('20일선 위')
        else: flags.append('20일선 아래')
        if room60_high < 5: flags.append('저항 가까움')
        if support_dist is not None and support_dist > 20: flags.append('지지선과 멂')
        return {
            'date': cur.get('date'), 'close': close, 'ma20': ma20,
            'dist60_low': dist60_low, 'dist120_low': dist120_low,
            'room60_high': room60_high, 'room120_high': room120_high,
            'support_dist': support_dist, 'resistance_room': resist_room,
            'support_price': profile.get('support_price'), 'resistance_price': profile.get('resistance_price'),
            'near_low': near_low, 'near_support': near_support, 'enough_room': enough_room, 'above_ma20': above_ma20,
            'flags': flags,
        }
    except Exception:
        return None


def support_record_v12410(name, rows, idx):
    feat = support_features_v12410(rows, idx)
    if not feat:
        return None
    entry = feat['close']
    ret20 = None
    if idx + 20 < len(rows):
        ret20 = rr_pct_v12410(rows[idx+20].get('close', 0), entry)
    if ret20 is None:
        return None
    score = 0
    score += 35 if feat['near_support'] else 0
    score += 30 if feat['near_low'] else 0
    score += 20 if feat['enough_room'] else -20
    score += 15 if feat['above_ma20'] else -10
    score = max(0, min(100, int(score)))
    mode = '지지+저점+상단여유' if (feat['near_support'] and feat['near_low'] and feat['enough_room']) else ('지지선근처' if feat['near_support'] else ('저점근처' if feat['near_low'] else '지지멀음'))
    return {
        'name': norm(name), 'date': feat['date'], 'entry': entry, 'ret20': ret20, 'support_score': score, 'mode': mode,
        **feat
    }


def stats_support_v12410(records):
    vals = [float(r.get('ret20')) for r in records if r.get('ret20') is not None]
    if not vals:
        return {'count':0,'win_rate':0,'avg':0,'max_loss':0,'max_gain':0,'loss_rate':0,'risk_reward':0}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    avg_win = sum(wins)/len(wins) if wins else 0
    avg_loss = sum(losses)/len(losses) if losses else 0
    rr = (avg_win/abs(avg_loss)) if avg_loss < 0 else (avg_win if avg_win else 0)
    return {'count':len(vals),'win_rate':len(wins)/len(vals)*100,'avg':sum(vals)/len(vals),'max_loss':min(vals),'max_gain':max(vals),'loss_rate':len(losses)/len(vals)*100,'risk_reward':rr}


def run_support_analyzer_v12410(data=None, days=520):
    names = historical_target_names_v1241(data)
    all_records = []
    stock_rows = []
    failures = []
    for n in names:
        try:
            res = kis_daily_chart_v1248(n, days=days) if 'kis_daily_chart_v1248' in globals() else kis_daily_chart_v1241(n, days=days)
            rows = res.get('rows') or []
            if not res.get('ok') or len(rows) < 100:
                failures.append(f'{norm(n)}: 일봉 부족/조회실패 {len(rows)}개')
                continue
            recs = []
            for idx in range(120, len(rows)-20):
                r = support_record_v12410(n, rows, idx)
                if r:
                    recs.append(r)
            all_records.extend(recs)
            stock_rows.append({'name': norm(n), 'bars': len(rows), 'records': len(recs), 'first': rows[0].get('date'), 'last': rows[-1].get('date')})
        except Exception as e:
            failures.append(f'{norm(n)}: {str(e)[:120]}')
    groups = {
        '전체': all_records,
        '지지+저점+상단여유': [r for r in all_records if r.get('near_support') and r.get('near_low') and r.get('enough_room')],
        '매물대 지지 근처': [r for r in all_records if r.get('near_support')],
        '저점 근처': [r for r in all_records if r.get('near_low')],
        '저항 가까움': [r for r in all_records if r.get('room60_high',999) < 5],
        '지지선과 멂': [r for r in all_records if (r.get('support_dist') is not None and r.get('support_dist') > 20)],
    }
    group_stats = {k: stats_support_v12410(v) for k,v in groups.items()}
    best = sorted([(k,v) for k,v in group_stats.items() if k != '전체'], key=lambda kv: (kv[1].get('avg',-999), -abs(kv[1].get('max_loss',0))), reverse=True)
    worst = sorted(all_records, key=lambda r: r.get('ret20',0))[:20]
    best_cases = sorted(all_records, key=lambda r: r.get('ret20',0), reverse=True)[:20]
    payload = {
        'version':'V124-10', 'created_at_kst': now_label(), 'source':'KIS daily rows / approximated support-resistance volume profile',
        'record_count': len(all_records), 'stock_count': len(stock_rows), 'stocks': stock_rows, 'failures': failures[:30],
        'group_stats': group_stats, 'best_group': best[0][0] if best else '-',
        'worst20': worst, 'best20': best_cases,
        'note':'실제 호가별 매물대가 아니라 일봉 가격·거래량 기반 근사 지지/저항 검증입니다. 자동 가중치 변경 없음.'
    }
    save_support_analyzer_v12410(payload)
    return payload


def support_need_refresh_v12410(payload):
    try:
        if not payload or int(payload.get('record_count',0) or 0) <= 0:
            return True
        dt = datetime.strptime(str(payload.get('created_at_kst','')), '%Y-%m-%d %H:%M:%S')
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True


def render_support_group_rows_v12410(stats):
    rows = ''
    for label in ['지지+저점+상단여유','매물대 지지 근처','저점 근처','저항 가까움','지지선과 멂','전체']:
        s = stats.get(label) or {}
        rows += (
            '<div class="db-row">'
            f'<div class="db-name">{label} · 20일 {s.get("count",0):,}건</div>'
            f'<div class="db-meta">승률 {s.get("win_rate",0):.1f}% · 평균수익 {s.get("avg",0):+.2f}% · 최대손실 {s.get("max_loss",0):+.2f}% · 최대수익 {s.get("max_gain",0):+.2f}% · 손실비율 {s.get("loss_rate",0):.1f}% · 위험대비수익 {s.get("risk_reward",0):.2f}</div>'
            '</div>'
        )
    return rows


def render_support_cases_v12410(title, rows, limit=5):
    html = f'<div class="db-row"><div class="db-name">{title}</div><div class="db-meta">'
    if not rows:
        html += '표본 없음'
    else:
        parts=[]
        for r in rows[:limit]:
            parts.append(f'{r.get("date")} {r.get("name")} · {r.get("mode")} · 20일 {r.get("ret20",0):+.2f}% · 지지거리 {r.get("support_dist",0) if r.get("support_dist") is not None else 0:.1f}% · 저항여유 {r.get("resistance_room",0) if r.get("resistance_room") is not None else 0:.1f}%')
        html += '<br>'.join(parts)
    html += '</div></div>'
    return html


def render_support_analyzer_v12410(data=None, compact=False):
    payload = load_support_analyzer_v12410()
    generated=False
    if support_need_refresh_v12410(payload):
        try:
            payload = run_support_analyzer_v12410(data, days=520)
            generated=True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🧱 V124-10 Support Analyzer</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    stats = payload.get('group_stats') or {}
    total = int(payload.get('record_count',0) or 0)
    best = payload.get('best_group','-')
    s_best = stats.get(best) or {}
    verdict = '검증 가능 표본 확보' if total >= SUPPORT_MIN_RECORDS_V12410 else '표본 부족 · 참고만'
    action = f'판정: {verdict}<br>전체 {total:,}건 · 우세 그룹: {best} · 승률 {s_best.get("win_rate",0):.1f}% · 평균 {s_best.get("avg",0):+.2f}% · 최대손실 {s_best.get("max_loss",0):+.2f}%'
    if generated:
        action += '<br>이번 실행에서 지지/매물대 검증 데이터를 새로 생성함'
    rows = render_support_group_rows_v12410(stats)
    if not compact:
        rows += render_support_cases_v12410('최악 손실 예시', payload.get('worst20') or [], limit=8)
        rows += render_support_cases_v12410('최고 수익 예시', payload.get('best20') or [], limit=8)
    html = (
        '<div class="db-card">'
        '<div class="db-title">🧱 V124-10 Support Analyzer</div>'
        '<div class="db-sub">매물대·지지선·저점거리 가설을 검증합니다. 실제 호가별 매물대가 아니라 과거 일봉 가격·거래량 기반 근사 실험입니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows}'
        '<div class="db-sub">※ 이 결과가 좋을 때만 V125 가중치 후보로 올립니다. 자동 반영은 하지 않습니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button('📥 support_analyzer_v12410.json 다운로드', data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'), file_name='support_analyzer_v12410.json', mime='application/json', use_container_width=True, key='download_support_analyzer_v12410')
        except Exception:
            pass



# V124-11: Fake Bottom Killer
# 목적: 저점/지지선처럼 보였지만 20일 후 큰 손실이 난 "가짜 바닥" 공통 조건을 찾아냅니다.
# 원칙: 자동 매수/매도 또는 가중치 변경 없음. V125 반자동 학습 후보만 생성합니다.
FAKE_BOTTOM_FILE_V12411 = DATA_DIR / "fake_bottom_killer_v12411.json"
FAKE_BOTTOM_MIN_RECORDS_V12411 = 1000


def load_fake_bottom_v12411():
    try:
        if FAKE_BOTTOM_FILE_V12411.exists():
            with open(FAKE_BOTTOM_FILE_V12411, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_fake_bottom_v12411(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(FAKE_BOTTOM_FILE_V12411, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def safe_pct_v12411(a, b):
    try:
        if b and float(b) != 0:
            return (float(a) - float(b)) / float(b) * 100
    except Exception:
        pass
    return 0


def fake_bottom_extra_record_v12411(name, rows, idx):
    # V124-10 support_record를 확장해서 20일선 기울기, 60일 추세, 지지/저항 상태를 추가합니다.
    try:
        base = support_record_v12410(name, rows, idx)
        if not base:
            return None
        closes = [sf(x.get('close')) for x in rows]
        cur = rows[idx]
        close = sf(cur.get('close'))
        ma20_now = sum(closes[idx-19:idx+1]) / 20 if idx >= 19 else close
        ma20_prev = sum(closes[idx-24:idx-4]) / 20 if idx >= 24 else ma20_now
        ma60_now = sum(closes[idx-59:idx+1]) / 60 if idx >= 59 else ma20_now
        ma60_prev = sum(closes[idx-69:idx-9]) / 60 if idx >= 69 else ma60_now
        low20 = min(closes[max(0, idx-19):idx+1]) if idx >= 1 else close
        low60 = min(closes[max(0, idx-59):idx+1]) if idx >= 1 else close
        high20 = max(closes[max(0, idx-19):idx+1]) if idx >= 1 else close
        prev_close = closes[idx-1] if idx >= 1 else close
        ma20_slope = safe_pct_v12411(ma20_now, ma20_prev)
        ma60_slope = safe_pct_v12411(ma60_now, ma60_prev)
        day_change = safe_pct_v12411(close, prev_close)
        base.update({
            'ma20_slope': ma20_slope,
            'ma60_slope': ma60_slope,
            'dist20_low': safe_pct_v12411(close, low20),
            'dist60_low': safe_pct_v12411(close, low60),
            'room20_high': safe_pct_v12411(high20, close),
            'day_change': day_change,
        })
        base['killer_flags'] = fake_bottom_flags_v12411(base)
        return base
    except Exception:
        return None


def fake_bottom_flags_v12411(r):
    flags = []
    try:
        if not r.get('near_support'):
            flags.append('매물대 지지 없음')
        if r.get('near_low') and not r.get('near_support'):
            flags.append('저점처럼 보이나 지지 약함')
        if r.get('support_dist') is not None and sf(r.get('support_dist')) > 12:
            flags.append('지지선과 거리 멂')
        if r.get('resistance_room') is not None and sf(r.get('resistance_room')) < 5:
            flags.append('상단 저항 가까움')
        if sf(r.get('room60_high')) < 5:
            flags.append('60일 저항 가까움')
        if not r.get('above_ma20'):
            flags.append('20일선 아래')
        if sf(r.get('ma20_slope')) < -1.0:
            flags.append('20일선 하락 기울기')
        if sf(r.get('ma60_slope')) < -1.0:
            flags.append('60일선 하락 기울기')
        if sf(r.get('dist60_low')) <= 3 and sf(r.get('ma20_slope')) < 0:
            flags.append('신저가 근처+추세하락')
        if sf(r.get('day_change')) < -3:
            flags.append('당일 급락 중 진입')
        if sf(r.get('support_score')) < 55:
            flags.append('지지점수 낮음')
    except Exception:
        pass
    return list(dict.fromkeys(flags))


def flag_summary_v12411(records, base_total=None, topn=10):
    total = base_total if base_total is not None else len(records)
    total = total or 1
    counts = {}
    for r in records:
        for f in r.get('killer_flags') or fake_bottom_flags_v12411(r):
            counts[f] = counts.get(f, 0) + 1
    return [{'flag': k, 'count': v, 'rate': v / total * 100} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:topn]]


def stats_fake_bottom_v12411(records):
    vals = [sf(r.get('ret20')) for r in records if r.get('ret20') is not None]
    if not vals:
        return {'count':0,'win_rate':0,'avg':0,'max_loss':0,'max_gain':0,'loss_rate':0}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    return {
        'count': len(vals),
        'win_rate': len(wins)/len(vals)*100,
        'avg': sum(vals)/len(vals),
        'max_loss': min(vals),
        'max_gain': max(vals),
        'loss_rate': len(losses)/len(vals)*100,
    }


def compact_fake_case_v12411(r):
    return {
        'name': r.get('name'), 'date': r.get('date'), 'ret20': sf(r.get('ret20')), 'entry': r.get('entry'),
        'support_score': r.get('support_score'), 'mode': r.get('mode'),
        'support_dist': r.get('support_dist'), 'resistance_room': r.get('resistance_room'),
        'ma20_slope': r.get('ma20_slope'), 'ma60_slope': r.get('ma60_slope'),
        'flags': (r.get('killer_flags') or [])[:6]
    }


def run_fake_bottom_killer_v12411(data=None, days=520):
    names = historical_target_names_v1241(data)
    all_records, failures, stock_rows = [], [], []
    for n in names:
        try:
            res = kis_daily_chart_v1248(n, days=days) if 'kis_daily_chart_v1248' in globals() else kis_daily_chart_v1241(n, days=days)
            rows = res.get('rows') or []
            if not res.get('ok') or len(rows) < 140:
                failures.append(f'{norm(n)}: 일봉 부족/조회실패 {len(rows)}개')
                continue
            recs = []
            for idx in range(120, len(rows)-20):
                r = fake_bottom_extra_record_v12411(n, rows, idx)
                if r:
                    recs.append(r)
            all_records.extend(recs)
            stock_rows.append({'name': norm(n), 'bars': len(rows), 'records': len(recs), 'first': rows[0].get('date'), 'last': rows[-1].get('date')})
        except Exception as e:
            failures.append(f'{norm(n)}: {str(e)[:120]}')

    # 바닥 후보: 저점 근처 또는 매물대 지지 근처
    bottom_like = [r for r in all_records if r.get('near_low') or r.get('near_support')]
    fake = [r for r in bottom_like if sf(r.get('ret20')) <= -10]
    deep_fake = [r for r in bottom_like if sf(r.get('ret20')) <= -20]
    true = [r for r in bottom_like if sf(r.get('ret20')) >= 10]
    mild = [r for r in bottom_like if -10 < sf(r.get('ret20')) < 10]

    fake_flags = flag_summary_v12411(fake, base_total=len(fake), topn=12)
    true_flags = flag_summary_v12411(true, base_total=len(true), topn=12)
    # 제거 후보: 가짜 바닥에서 자주 나오고, 진짜 바닥에서는 상대적으로 덜 나오는 플래그
    true_map = {x['flag']: x['rate'] for x in true_flags}
    killer_rules = []
    for x in fake_flags:
        tr = true_map.get(x['flag'], 0)
        gap = x['rate'] - tr
        if x['count'] >= 5 and gap >= 8:
            killer_rules.append({'rule': x['flag'], 'fake_rate': x['rate'], 'true_rate': tr, 'gap': gap, 'fake_count': x['count']})
    killer_rules = sorted(killer_rules, key=lambda x: (x['gap'], x['fake_count']), reverse=True)[:8]

    worst = sorted(bottom_like, key=lambda r: sf(r.get('ret20')))[:20]
    best = sorted(bottom_like, key=lambda r: sf(r.get('ret20')), reverse=True)[:20]

    payload = {
        'version': 'V124-11', 'created_at_kst': now_label(), 'source': 'KIS daily rows / V124-10 support records extended',
        'record_count': len(all_records), 'bottom_like_count': len(bottom_like), 'stock_count': len(stock_rows),
        'stocks': stock_rows, 'failures': failures[:30],
        'overall': stats_fake_bottom_v12411(all_records),
        'bottom_like': stats_fake_bottom_v12411(bottom_like),
        'fake_bottom': stats_fake_bottom_v12411(fake),
        'deep_fake_bottom': stats_fake_bottom_v12411(deep_fake),
        'true_bottom': stats_fake_bottom_v12411(true),
        'mild_bottom': stats_fake_bottom_v12411(mild),
        'fake_flags': fake_flags,
        'true_flags': true_flags,
        'killer_rules': killer_rules,
        'worst20': [compact_fake_case_v12411(r) for r in worst],
        'best20': [compact_fake_case_v12411(r) for r in best],
        'note': '가짜 바닥 제거 후보를 찾는 실험입니다. 자동 가중치 변경 또는 자동매매에 사용하지 않습니다.'
    }
    save_fake_bottom_v12411(payload)
    return payload


def fake_bottom_need_refresh_v12411(payload):
    try:
        if not payload or int(payload.get('record_count',0) or 0) <= 0:
            return True
        dt = datetime.strptime(str(payload.get('created_at_kst','')), '%Y-%m-%d %H:%M:%S')
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True


def fake_stats_line_v12411(label, s):
    return (f'{label} · {int(s.get("count",0)):,}건 · 승률 {s.get("win_rate",0):.1f}% · '
            f'평균 {s.get("avg",0):+.2f}% · 최대손실 {s.get("max_loss",0):+.2f}% · 최대수익 {s.get("max_gain",0):+.2f}% · 손실비율 {s.get("loss_rate",0):.1f}%')


def render_rule_rows_v12411(title, rows):
    html = f'<div class="db-row"><div class="db-name">{title}</div><div class="db-meta">'
    if not rows:
        html += '뚜렷한 제거 후보 없음 · 표본 확대 후 재검증 필요'
    else:
        parts = []
        for i, x in enumerate(rows[:8], start=1):
            parts.append(f'{i}. {x.get("rule")} · 가짜바닥 {x.get("fake_rate",0):.1f}% / 진짜바닥 {x.get("true_rate",0):.1f}% · 차이 {x.get("gap",0):+.1f}%p')
        html += '<br>'.join(parts)
    html += '</div></div>'
    return html


def render_flag_rows_v12411(title, rows):
    html = f'<div class="db-row"><div class="db-name">{title}</div><div class="db-meta">'
    if not rows:
        html += '표본 없음'
    else:
        html += '<br>'.join([f'{i+1}. {x.get("flag")} · {x.get("count")}건 · {x.get("rate",0):.1f}%' for i, x in enumerate(rows[:6])])
    html += '</div></div>'
    return html


def render_fake_cases_v12411(title, rows, limit=5):
    html = f'<div class="db-row"><div class="db-name">{title}</div><div class="db-meta">'
    if not rows:
        html += '표본 없음'
    else:
        parts=[]
        for r in rows[:limit]:
            flags = ' · '.join((r.get('flags') or [])[:3])
            parts.append(f'{r.get("date")} {r.get("name")} · {r.get("mode")} · 20일 {r.get("ret20",0):+.2f}% · 지지거리 {sf(r.get("support_dist")):.1f}% · 저항여유 {sf(r.get("resistance_room")):.1f}% · {flags}')
        html += '<br>'.join(parts)
    html += '</div></div>'
    return html


def render_fake_bottom_killer_v12411(data=None, compact=False):
    payload = load_fake_bottom_v12411()
    generated = False
    if fake_bottom_need_refresh_v12411(payload):
        try:
            payload = run_fake_bottom_killer_v12411(data, days=520)
            generated = True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🧨 V124-11 Fake Bottom Killer</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    total = int(payload.get('record_count',0) or 0)
    bottom = payload.get('bottom_like') or {}
    fake = payload.get('fake_bottom') or {}
    true = payload.get('true_bottom') or {}
    verdict = '가짜 바닥 해부 가능' if total >= FAKE_BOTTOM_MIN_RECORDS_V12411 else '표본 부족 · 참고만'
    action = (
        f'판정: {verdict}<br>'
        f'전체 {total:,}건 · 바닥후보 {int(payload.get("bottom_like_count",0)):,}건<br>'
        f'{fake_stats_line_v12411("가짜바닥(-10% 이하)", fake)}<br>'
        f'{fake_stats_line_v12411("진짜바닥(+10% 이상)", true)}'
    )
    if generated:
        action += '<br>이번 실행에서 가짜 바닥 데이터를 새로 생성함'
    rows = ''
    rows += render_rule_rows_v12411('가짜 바닥 제거 후보 TOP', payload.get('killer_rules') or [])
    rows += render_flag_rows_v12411('가짜 바닥 공통 패턴', payload.get('fake_flags') or [])
    rows += render_flag_rows_v12411('진짜 바닥 공통 패턴', payload.get('true_flags') or [])
    if not compact:
        rows += render_fake_cases_v12411('최악 가짜 바닥 사례', payload.get('worst20') or [], limit=10)
        rows += render_fake_cases_v12411('최고 진짜 바닥 사례', payload.get('best20') or [], limit=10)
    html = (
        '<div class="db-card">'
        '<div class="db-title">🧨 V124-11 Fake Bottom Killer</div>'
        '<div class="db-sub">저점·지지선처럼 보였지만 20일 후 크게 깨진 가짜 바닥 조건을 찾습니다. 목표는 수익률보다 먼저 큰 손실 후보를 제거하는 것입니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows}'
        '<div class="db-sub">※ 제거 후보는 V125 반자동 학습에서 제안만 합니다. 자동 적용하지 않습니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button('📥 fake_bottom_killer_v12411.json 다운로드', data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'), file_name='fake_bottom_killer_v12411.json', mime='application/json', use_container_width=True, key='download_fake_bottom_v12411')
        except Exception:
            pass



# V124-12: RS / TREND VALIDATION LAB
# 목적: 유튜브/책/아이디어를 바로 엔진에 넣지 않고, 5,000건대 일봉 표본으로 먼저 검증합니다.
# 검증 대상: 전저점 유지, RS 강도, 30주선 상승, VCP 근사, 매물대/상단저항 조건.
VALIDATION_LAB_FILE_V12412 = DATA_DIR / "validation_lab_v12412.json"

def save_validation_lab_v12412(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(VALIDATION_LAB_FILE_V12412, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_validation_lab_v12412():
    try:
        if VALIDATION_LAB_FILE_V12412.exists():
            with open(VALIDATION_LAB_FILE_V12412, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}

def validation_need_refresh_v12412(payload):
    try:
        if not payload or not payload.get('conditions'):
            return True
        dt = datetime.strptime(str(payload.get('created_at_kst','')), "%Y-%m-%d %H:%M:%S")
        return (kst_now() - dt).total_seconds() > 21600
    except Exception:
        return True

def pct_change_v12412(a, b):
    try:
        a = float(a or 0); b = float(b or 0)
        if a <= 0: return None
        return (b / a - 1) * 100
    except Exception:
        return None

def avg_v12412(vals, default=0):
    vals = [float(x) for x in vals if x is not None]
    return sum(vals) / len(vals) if vals else default

def slope_v12412(vals):
    vals = [float(x) for x in vals if x is not None]
    if len(vals) < 2: return 0
    return vals[-1] - vals[0]

def validation_record_v12412(name, rows, idx):
    # rows: 날짜 오름차순 KIS 일봉. idx 기준으로 과거만 보고 20일 후 수익률을 검증합니다.
    try:
        r = rows[idx]
        close = float(r.get('close', 0) or 0)
        if close <= 0 or idx < 155 or idx + 20 >= len(rows):
            return None
        prev = rows[:idx+1]
        future = rows[idx+20]
        ret20 = pct_change_v12412(close, future.get('close'))
        if ret20 is None:
            return None
        closes = [float(x.get('close',0) or 0) for x in prev]
        vols = [float(x.get('volume',0) or 0) for x in prev]
        lows = [float(x.get('low', x.get('close',0)) or 0) for x in prev]
        highs = [float(x.get('high', x.get('close',0)) or 0) for x in prev]
        ma5 = avg_v12412(closes[-5:])
        ma20 = avg_v12412(closes[-20:])
        ma60 = avg_v12412(closes[-60:])
        ma150 = avg_v12412(closes[-150:])
        ma150_prev = avg_v12412(closes[-170:-20]) if len(closes) >= 170 else avg_v12412(closes[-150:-20])
        ret20_past = pct_change_v12412(closes[-21], close) if len(closes) >= 21 else 0
        ret60_past = pct_change_v12412(closes[-61], close) if len(closes) >= 61 else 0
        prev_low_20 = min(lows[-40:-20]) if len(lows) >= 40 else min(lows[:-20] or lows)
        low_20 = min(lows[-20:]) if lows[-20:] else close
        prev_low_60 = min(lows[-80:-20]) if len(lows) >= 80 else min(lows[:-20] or lows)
        # 전저점 유지: 최근 20일 저점이 이전 의미 저점 대비 -2% 이상 이탈하지 않음
        prior_low_hold = bool(prev_low_20 > 0 and low_20 >= prev_low_20 * 0.98)
        prior_low_break = bool(prev_low_20 > 0 and low_20 < prev_low_20 * 0.98)
        near_low = bool(close <= min(lows[-60:]) * 1.10 if len(lows) >= 60 else False)
        # 상단저항 여유: 최근 120일 고점까지 12% 이상 여유
        high120 = max(highs[-120:]) if len(highs) >= 120 else max(highs)
        resistance_room = bool(high120 > 0 and (high120 / close - 1) * 100 >= 12)
        # 30주선 근사: 일봉 150일선 위 + 150일선 기울기 상승
        above_30w = bool(close > ma150)
        up_30w = bool(ma150 > ma150_prev)
        down_30w = bool(ma150 <= ma150_prev)
        # VCP 근사: 변동폭 축소 + 거래량 감소. 15일 구간 3개로 나눠 high-low range가 줄어드는지 확인.
        def range_pct(seg):
            if not seg: return 0
            h=max(float(x.get('high',x.get('close',0)) or 0) for x in seg)
            l=min(float(x.get('low',x.get('close',0)) or 0) for x in seg)
            c=avg_v12412([float(x.get('close',0) or 0) for x in seg], 1)
            return (h-l)/c*100 if c else 0
        seg1=prev[-60:-40]; seg2=prev[-40:-20]; seg3=prev[-20:]
        rg1, rg2, rg3 = range_pct(seg1), range_pct(seg2), range_pct(seg3)
        vol1, vol2, vol3 = avg_v12412([x.get('volume') for x in seg1]), avg_v12412([x.get('volume') for x in seg2]), avg_v12412([x.get('volume') for x in seg3])
        vcp = bool(rg1 > rg2 > rg3 and vol1 >= vol2 >= vol3 and rg3 <= 12)
        volatility_contract = bool(rg1 > rg3 and rg3 <= 12)
        volume_dry = bool(vol3 < avg_v12412(vols[-80:-20]) * 0.85 if len(vols) >= 80 else False)
        # 돌파 근사: 현재가가 최근 20일 고점 부근, 거래량이 50일 평균 대비 150% 이상
        breakout = bool(close >= max(highs[-20:]) * 0.995 and vols[-1] >= avg_v12412(vols[-50:]) * 1.5)
        # 매물대 지지 근사: 최근 120일 가격대를 12구간으로 나누어 거래량 집중 가격대와 현재가 거리
        support_zone = False
        try:
            lo=min(lows[-120:]); hi=max(highs[-120:])
            if hi > lo:
                buckets=[0]*12
                for rr in prev[-120:]:
                    c=float(rr.get('close',0) or 0); v=float(rr.get('volume',0) or 0)
                    bi=max(0,min(11,int((c-lo)/(hi-lo)*12)))
                    buckets[bi]+=v
                bi=max(range(12), key=lambda j:buckets[j])
                level=lo+(hi-lo)*(bi+0.5)/12
                dist=(close/level-1)*100 if level>0 else 999
                support_zone=bool(-5 <= dist <= 10)
        except Exception:
            support_zone=False
        return {
            'stock': norm(name), 'date': r.get('date'), 'close': close,
            'ret20': ret20, 'ret20_past': ret20_past or 0, 'ret60_past': ret60_past or 0,
            'prior_low_hold': prior_low_hold, 'prior_low_break': prior_low_break,
            'near_low': near_low, 'resistance_room': resistance_room,
            'above_30w': above_30w, 'up_30w': up_30w, 'down_30w': down_30w,
            'vcp': vcp, 'volatility_contract': volatility_contract, 'volume_dry': volume_dry,
            'breakout': breakout, 'support_zone': support_zone,
            'ma150': ma150, 'ma150_slope': ma150 - ma150_prev, 'rg1': rg1, 'rg2': rg2, 'rg3': rg3,
        }
    except Exception:
        return None

def stats_validation_v12412(records):
    vals = [float(r.get('ret20',0) or 0) for r in records if r.get('ret20') is not None]
    if not vals:
        return {'n':0,'win_rate':0,'avg_return':0,'max_loss':0,'max_gain':0,'loss_rate':0,'adopt_score':0,'verdict':'표본없음'}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    win_rate = len(wins)/len(vals)*100
    avg_return = sum(vals)/len(vals)
    max_loss = min(vals)
    max_gain = max(vals)
    loss_rate = len(losses)/len(vals)*100
    # 채택점수: 승률 30 + 평균수익 40 + 최대손실 30. 최대손실은 -10% 이상이면 고득점, -40% 이하면 저득점.
    win_score = max(0,min(100,win_rate))
    avg_score = max(0,min(100,50 + avg_return*3))
    dd_score = max(0,min(100,100 + max_loss*2.5))
    adopt = int(win_score*0.30 + avg_score*0.40 + dd_score*0.30)
    if len(vals) < 100:
        verdict='표본부족'
    elif adopt >= 75 and avg_return > 0:
        verdict='채택후보'
    elif adopt >= 65 and avg_return > 0:
        verdict='보류후보'
    else:
        verdict='탈락/주의'
    return {'n':len(vals),'win_rate':win_rate,'avg_return':avg_return,'max_loss':max_loss,'max_gain':max_gain,'loss_rate':loss_rate,'adopt_score':adopt,'verdict':verdict}

def run_validation_lab_v12412(data=None, days=520):
    names = historical_target_names_v1241(data)
    all_records=[]
    by_date={}
    stock_rows=[]
    for n in names:
        try:
            res = kis_daily_chart_v1248(n, days=days)
            rows = res.get('rows') or []
            count=0
            for idx in range(155, max(155, len(rows)-20)):
                rec = validation_record_v12412(n, rows, idx)
                if rec:
                    all_records.append(rec); count+=1
                    by_date.setdefault(rec['date'], []).append(rec)
            stock_rows.append({'name':norm(n),'daily_rows':len(rows),'validation_records':count,'ok':bool(rows)})
        except Exception as e:
            stock_rows.append({'name':norm(n),'daily_rows':0,'validation_records':0,'ok':False,'error':str(e)[:120]})
    # RS 근사: 같은 날짜 전체 후보군 중 과거 20일 수익률 순위 상/하 20%
    for d, rows in by_date.items():
        ranked=sorted(rows, key=lambda x: x.get('ret20_past',0), reverse=True)
        m=len(ranked)
        if m <= 1: continue
        top_cut=max(1,int(m*0.2)); bot_cut=max(1,int(m*0.2))
        for i,r in enumerate(ranked):
            r['rs_rank_pct'] = (m-i)/m*100
            r['rs_top20'] = i < top_cut
            r['rs_bottom20'] = i >= m-bot_cut
    def pick(cond):
        return [r for r in all_records if cond(r)]
    conditions={
        '전저점 유지': pick(lambda r: r.get('prior_low_hold')),
        '전저점 이탈': pick(lambda r: r.get('prior_low_break')),
        'RS 상위 20%': pick(lambda r: r.get('rs_top20')),
        'RS 하위 20%': pick(lambda r: r.get('rs_bottom20')),
        '30주선 상승': pick(lambda r: r.get('above_30w') and r.get('up_30w')),
        '30주선 하락/저항': pick(lambda r: r.get('down_30w')),
        'VCP 근사': pick(lambda r: r.get('vcp')),
        '변동성 축소': pick(lambda r: r.get('volatility_contract')),
        '거래량 돌파': pick(lambda r: r.get('breakout')),
        '매물대 지지': pick(lambda r: r.get('support_zone')),
        '상단 저항 여유': pick(lambda r: r.get('resistance_room')),
        '종합 후보(전저점+30주+RS)': pick(lambda r: r.get('prior_low_hold') and r.get('above_30w') and r.get('up_30w') and r.get('rs_top20')),
        '방어 후보(전저점+매물대+저항여유)': pick(lambda r: r.get('prior_low_hold') and r.get('support_zone') and r.get('resistance_room')),
    }
    cond_stats=[]
    for name, recs in conditions.items():
        stt=stats_validation_v12412(recs)
        stt['name']=name
        cond_stats.append(stt)
    cond_stats=sorted(cond_stats, key=lambda x:(x.get('adopt_score',0), x.get('avg_return',0), x.get('n',0)), reverse=True)
    payload={
        'version':'V124-12', 'created_at_kst': now_label(),
        'purpose':'RS / 30주선 / 전저점 / VCP 가설 검증. 통과한 공식만 V125 후보로 올림.',
        'total_records': len(all_records), 'stock_count': len(names), 'stocks': stock_rows,
        'overall': stats_validation_v12412(all_records), 'conditions': cond_stats,
        'top_examples': sorted(all_records, key=lambda r:r.get('ret20',0), reverse=True)[:20],
        'worst_examples': sorted(all_records, key=lambda r:r.get('ret20',0))[:20],
        'note':'RS는 전체시장 지수 대신 동일 후보군 내 과거 20일 수익률 상대순위로 근사했습니다. V125 정식 반영 전 보조 검증값입니다.',
    }
    save_validation_lab_v12412(payload)
    return payload

def render_validation_lab_v12412(data=None, compact=False):
    payload=load_validation_lab_v12412()
    generated=False
    if validation_need_refresh_v12412(payload):
        try:
            payload=run_validation_lab_v12412(data, days=520); generated=True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🧪 V124-12 RS / Trend Validation Lab</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    overall=payload.get('overall') or {}
    conds=payload.get('conditions') or []
    top=conds[0] if conds else {}
    action=(f'검증표본 {int(payload.get("total_records",0)):,}건 · 전체 승률 {overall.get("win_rate",0):.1f}% · 평균수익 {overall.get("avg_return",0):+.2f}%<br>'
            f'현재 1위 공식: {top.get("name","-")} · 채택점수 {top.get("adopt_score",0)}점 · 승률 {top.get("win_rate",0):.1f}% · 평균수익 {top.get("avg_return",0):+.2f}% · 최대손실 {top.get("max_loss",0):+.2f}%')
    if generated:
        action += '<br>이번 실행에서 새로 검증함'
    rows=''
    for x in conds[:(5 if compact else 14)]:
        mark='✅' if x.get('verdict')=='채택후보' else ('🟡' if x.get('verdict')=='보류후보' else ('⚠️' if x.get('verdict')=='표본부족' else '❌'))
        rows += (f'<div class="db-row"><div class="db-name">{mark} {x.get("name","-")} · 표본 {x.get("n",0):,}건 · 채택점수 {x.get("adopt_score",0)}점</div>'
                 f'<div class="db-meta">승률 {x.get("win_rate",0):.1f}% · 평균수익 {x.get("avg_return",0):+.2f}% · 최대손실 {x.get("max_loss",0):+.2f}% · 최대수익 {x.get("max_gain",0):+.2f}% · 판정 {x.get("verdict","-")}</div></div>')
    html=(
        '<div class="db-card">'
        '<div class="db-title">🧪 V124-12 RS / Trend Validation Lab</div>'
        '<div class="db-sub">RS 강도, 30주선 상승, 전저점 유지, VCP/변동성축소, 거래량돌파가 실제 20일 후 수익률에 도움이 되는지 검증합니다.</div>'
        f'<div class="db-action">{action}</div>'
        f'{rows}'
        '<div class="db-sub">※ 이번 단계는 정식 추천 공식 변경이 아닙니다. 표본 100건 미만은 채택 금지, 살아남은 공식만 V125 후보로 올립니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button('📥 validation_lab_v12412.json 다운로드', data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'), file_name='validation_lab_v12412.json', mime='application/json', use_container_width=True, key='download_validation_lab_v12412')
        except Exception:
            pass



# V124-13: COMBO VALIDATION LAB
# 목적: V124-12에서 살아남은 단일 조건들을 실제 교집합으로 조합 검증합니다.
# 원칙: 표본 100건 미만은 승률이 높아도 채택 금지. 자동 가중치 변경 없음.
COMBO_VALIDATION_FILE_V12413 = DATA_DIR / "combo_validation_v12413.json"

def save_combo_validation_v12413(payload):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(COMBO_VALIDATION_FILE_V12413, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_combo_validation_v12413():
    try:
        if COMBO_VALIDATION_FILE_V12413.exists():
            with open(COMBO_VALIDATION_FILE_V12413, "r", encoding="utf-8") as f:
                d=json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}

def combo_need_refresh_v12413(payload):
    try:
        if not payload or not payload.get('combos'):
            return True
        dt=datetime.strptime(str(payload.get('created_at_kst','')), "%Y-%m-%d %H:%M:%S")
        return (kst_now()-dt).total_seconds() > 21600
    except Exception:
        return True

def combo_grade_v12413(stt):
    n=int(stt.get('n',0) or 0)
    wr=float(stt.get('win_rate',0) or 0)
    ar=float(stt.get('avg_return',0) or 0)
    ml=float(stt.get('max_loss',0) or 0)
    adopt=int(stt.get('adopt_score',0) or 0)
    if n < 30:
        return '표본극소'
    if n < 100:
        return '표본부족'
    if n >= 100 and wr >= 80 and ar > 0 and ml >= -15:
        return '80%후보'
    if n >= 100 and wr >= 75 and ar > 0 and ml >= -20:
        return '채택후보'
    if n >= 100 and adopt >= 65 and ar > 0:
        return '보류후보'
    return '탈락/주의'

def run_combo_validation_lab_v12413(data=None, days=520):
    # V124-12의 validation_record_v12412 로직을 그대로 사용해 같은 기준의 원본 레코드를 만든 뒤 조합만 새로 검증합니다.
    names = historical_target_names_v1241(data)
    all_records=[]
    by_date={}
    stock_rows=[]
    for n in names:
        try:
            res=kis_daily_chart_v1248(n, days=days)
            rows=res.get('rows') or []
            count=0
            for idx in range(155, max(155, len(rows)-20)):
                rec=validation_record_v12412(n, rows, idx)
                if rec:
                    all_records.append(rec); count+=1
                    by_date.setdefault(rec.get('date'), []).append(rec)
            stock_rows.append({'name':norm(n),'daily_rows':len(rows),'combo_records':count,'ok':bool(rows)})
        except Exception as e:
            stock_rows.append({'name':norm(n),'daily_rows':0,'combo_records':0,'ok':False,'error':str(e)[:120]})
    # RS 근사 재부여: 같은 날짜 후보군 내 과거 20일 수익률 상대순위
    for d, rows in by_date.items():
        ranked=sorted(rows, key=lambda x:x.get('ret20_past',0), reverse=True)
        m=len(ranked)
        if m <= 1:
            continue
        top_cut=max(1,int(m*0.2)); bot_cut=max(1,int(m*0.2))
        for i,r in enumerate(ranked):
            r['rs_rank_pct']=(m-i)/m*100
            r['rs_top20']=i < top_cut
            r['rs_bottom20']=i >= m-bot_cut
    def pick(cond):
        return [r for r in all_records if cond(r)]
    combo_defs=[
        ('VCP + 30주선 상승', lambda r: r.get('vcp') and r.get('above_30w') and r.get('up_30w')),
        ('VCP + 거래량 돌파', lambda r: r.get('vcp') and r.get('breakout')),
        ('VCP + RS 상위20%', lambda r: r.get('vcp') and r.get('rs_top20')),
        ('VCP + 전저점 유지', lambda r: r.get('vcp') and r.get('prior_low_hold')),
        ('VCP + 매물대 지지', lambda r: r.get('vcp') and r.get('support_zone')),
        ('VCP + 상단 저항 여유', lambda r: r.get('vcp') and r.get('resistance_room')),
        ('30주선 상승 + RS 상위20%', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('rs_top20')),
        ('30주선 상승 + 거래량 돌파', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('breakout')),
        ('30주선 상승 + 전저점 유지', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('prior_low_hold')),
        ('30주선 상승 + 매물대 지지', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('support_zone')),
        ('30주선 상승 + VCP + 거래량 돌파', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('vcp') and r.get('breakout')),
        ('30주선 상승 + VCP + RS 상위20%', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('vcp') and r.get('rs_top20')),
        ('30주선 상승 + VCP + 전저점 유지', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('vcp') and r.get('prior_low_hold')),
        ('30주선 상승 + VCP + 매물대 지지', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('vcp') and r.get('support_zone')),
        ('30주선 상승 + VCP + 저항여유', lambda r: r.get('above_30w') and r.get('up_30w') and r.get('vcp') and r.get('resistance_room')),
        ('RS + 30주선 + 전저점 + 매물대', lambda r: r.get('rs_top20') and r.get('above_30w') and r.get('up_30w') and r.get('prior_low_hold') and r.get('support_zone')),
        ('방어형: 전저점 + 매물대 + 저항여유', lambda r: r.get('prior_low_hold') and r.get('support_zone') and r.get('resistance_room')),
        ('공격형: RS + 30주선 + 거래량돌파', lambda r: r.get('rs_top20') and r.get('above_30w') and r.get('up_30w') and r.get('breakout')),
    ]
    combos=[]
    for name, cond in combo_defs:
        recs=pick(cond)
        stt=stats_validation_v12412(recs)
        stt['name']=name
        stt['combo_grade']=combo_grade_v12413(stt)
        # 표본 부족 페널티를 적용한 실전점수: 100건 미만은 아무리 좋아도 아래로 보냄
        n=stt.get('n',0)
        penalty = 0 if n >= 100 else (25 if n >= 30 else 50)
        stt['practical_score']=max(0, int(stt.get('adopt_score',0) - penalty))
        combos.append(stt)
    combos=sorted(combos, key=lambda x:(x.get('practical_score',0), x.get('n',0), x.get('avg_return',0)), reverse=True)
    valid_over_100=[x for x in combos if x.get('n',0) >= 100]
    over80=[x for x in combos if x.get('n',0) >= 100 and x.get('win_rate',0) >= 80]
    payload={
        'version':'V124-13',
        'created_at_kst':now_label(),
        'purpose':'VCP, 30주선, RS, 전저점, 매물대, 거래량 돌파의 실제 교집합 조합 검증',
        'total_records':len(all_records),
        'stock_count':len(names),
        'stocks':stock_rows,
        'overall':stats_validation_v12412(all_records),
        'combos':combos,
        'valid_over_100':valid_over_100,
        'over80_candidates':over80,
        'note':'표본 100건 미만은 승률이 높아도 채택하지 않습니다. 이번 결과는 정식 가중치 변경이 아니라 V125 후보 선별용입니다.',
    }
    save_combo_validation_v12413(payload)
    return payload

def render_combo_validation_lab_v12413(data=None, compact=False):
    payload=load_combo_validation_v12413()
    generated=False
    if combo_need_refresh_v12413(payload):
        try:
            payload=run_combo_validation_lab_v12413(data, days=520); generated=True
        except Exception as e:
            st.markdown(f'<div class="db-card"><div class="db-title">🧬 V124-13 Combo Validation Lab</div><div class="db-action">오류: {str(e)[:180]}</div></div>', unsafe_allow_html=True)
            return
    overall=payload.get('overall') or {}
    combos=payload.get('combos') or []
    over80=payload.get('over80_candidates') or []
    top=combos[0] if combos else {}
    msg=(f'조합 검증표본 {int(payload.get("total_records",0)):,}건 · 전체 승률 {overall.get("win_rate",0):.1f}% · 평균수익 {overall.get("avg_return",0):+.2f}%<br>'
         f'1위 조합: {top.get("name","-")} · 표본 {top.get("n",0):,}건 · 승률 {top.get("win_rate",0):.1f}% · 평균수익 {top.get("avg_return",0):+.2f}% · 최대손실 {top.get("max_loss",0):+.2f}% · 실전점수 {top.get("practical_score",0)}점')
    if over80:
        msg += f'<br>80% 이상 후보 {len(over80)}개 발견'
    else:
        msg += '<br>표본 100건 이상 + 승률 80% 후보는 아직 없음'
    if generated:
        msg += '<br>이번 실행에서 새로 조합 검증함'
    rows=''
    limit=5 if compact else 18
    for x in combos[:limit]:
        grade=x.get('combo_grade','-')
        if grade=='80%후보': mark='🏆'
        elif grade=='채택후보': mark='✅'
        elif grade=='보류후보': mark='🟡'
        elif '표본' in grade: mark='⚠️'
        else: mark='❌'
        rows += (f'<div class="db-row"><div class="db-name">{mark} {x.get("name","-")} · {grade} · 표본 {x.get("n",0):,}건 · 실전점수 {x.get("practical_score",0)}점</div>'
                 f'<div class="db-meta">승률 {x.get("win_rate",0):.1f}% · 평균수익 {x.get("avg_return",0):+.2f}% · 최대손실 {x.get("max_loss",0):+.2f}% · 최대수익 {x.get("max_gain",0):+.2f}% · 손실비율 {x.get("loss_rate",0):.1f}%</div></div>')
    html=(
        '<div class="db-card">'
        '<div class="db-title">🧬 V124-13 Combo Validation Lab</div>'
        '<div class="db-sub">VCP, 30주선 상승, RS 상위, 전저점 유지, 매물대 지지, 거래량 돌파를 실제 교집합으로 조합 검증합니다.</div>'
        f'<div class="db-action">{msg}</div>'
        f'{rows}'
        '<div class="db-sub">※ 자동 추천 공식 변경 없음. 표본 100건 미만은 승률이 높아도 채택 금지. 다음 단계는 표본 확장 후 재검증입니다.</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if not compact:
        try:
            st.download_button('📥 combo_validation_v12413.json 다운로드', data=json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'), file_name='combo_validation_v12413.json', mime='application/json', use_container_width=True, key='download_combo_validation_v12413')
        except Exception:
            pass


# V124-8: 기존 Bulk Replay 렌더러를 확장해서 Data Factory 진단을 먼저 보여주고, 그 다음 Bulk Replay를 실행합니다.
_original_render_bulk_historical_replay_v1245 = render_bulk_historical_replay_v1245

def render_bulk_historical_replay_v1245(data=None, compact=False):
    render_data_factory_v1248(data, compact=compact)
    _original_render_bulk_historical_replay_v1245(data, compact=compact)


def main():
    css()
    data = load_data()
    tab = current_tab()
    if tab == "search":
        search(data)
    elif tab == "news":
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
