
import json, re
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st
import requests
import xml.etree.ElementTree as ET

APP_TITLE = "🧭 스톡 컴퍼스 V104-1"
APP_SUBTITLE = "경규님 전용 개인용 AI 투자비서 · 공급망 발굴 DB 1차"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
HISTORY_FILE = DATA_DIR / "history.json"
SELL_FILE = DATA_DIR / "sell_records.json"

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

st.set_page_config(page_title="스톡 컴퍼스 V104-1", page_icon="🧭", layout="centered")

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
        "제룡전기": "033100",
        "에스피시스템스": "317830",
        "LG디스플레이": "034220",
        "ACE AI반도체 TOP3": "469150",
        "KODEX 미국S&P500": "379800",
        "TIGER 미국S&P500": "360750",
        "삼성전자": "005930",
        "SK하이닉스": "000660",
        "한미반도체": "042700",
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
    }.get(norm(name))

def parse_price(s):
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None

def fetch_price(name):
    name = norm(name)
    code = code_map().get(name)
    if not code:
        return fallback_price(name), "기본값"
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4).text
        for pat in [
            r'<p class="no_today">[\s\S]*?<span class="blind">([\d,]+)</span>',
            r'<div class="today">[\s\S]*?<span class="blind">([\d,]+)</span>',
        ]:
            m = re.search(pat, html)
            if m:
                p = parse_price(m.group(1))
                if p:
                    return p, f"네이버 {code}"
    except Exception:
        pass
    return fallback_price(name), "기본값"

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
    price, src = fetch_price(name)
    qty = sf(qty)
    avg = sf(avg)
    if not price or qty <= 0 or avg <= 0:
        return None
    buy = qty * avg
    value = qty * price
    profit = value - buy
    rate = profit / buy * 100 if buy else 0
    return {"price": price, "src": src, "buy": buy, "value": value, "profit": profit, "rate": rate}

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

    </style>
    """, unsafe_allow_html=True)

def header():
    st.markdown(f'<div class="hero"><h1>{APP_TITLE}</h1><p>{APP_SUBTITLE}</p></div>', unsafe_allow_html=True)

def card(title, body):
    st.markdown(f'<div class="card"><div class="title">{title}</div><div class="body">{body}</div></div>', unsafe_allow_html=True)

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
    st.markdown(
        '<div class="toss-card"><div class="toss-title">📷 토스 포트 자동갱신</div><div class="toss-sub">토스 보유화면의 종목명·수량을 붙여넣으면 기존 보유수량을 자동 갱신합니다. 평단은 기존 값을 보존합니다.</div><div class="toss-action">1차 버전: 캡처 이미지는 참고용으로 올리고, 텍스트는 직접 붙여넣기 방식입니다.</div></div>',
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

    if st.button("토스 수량으로 보유종목 갱신", use_container_width=True, key="apply_toss_sync_v103"):
        changes = apply_toss_sync(data, parsed)
        if changes:
            st.success(f"{len(changes)}개 종목 수량을 갱신했습니다. 평단은 기존 값을 유지했습니다.")
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


def home(data):
    header()
    render_asset_top(data)
    render_ai_boss_opinion(data)
    render_news_conclusion(data)
    render_supply_chain_discovery(data)
    render_investment_allocation(data)
    render_home_best_briefing(data)
    render_emergency_board(data)
    render_investment_thermometer(data)
    render_buy_timing_summary(data)
    render_value_dividend_summary(data)
    render_rebalance_summary(data)
    render_target_price_summary(data)
    render_future_probability_summary(data)
    if st.button("🔄 새로고침 / 다시 판단하기", use_container_width=True):
        st.rerun()
    render_action(data, show_detail=False)
    hs, hg, hr, risk_reasons, risk_action = portfolio_health(data)
    reason_html = "<br>".join([f"① {r}" for r in risk_reasons]) if risk_reasons else "현재 큰 위험요인은 보이지 않습니다."
    card(
        "🛡️ 포트폴리오 위험도",
        f"{hs}점 · {hg}<br><br>"
        f"{hr}<br><br>"
        f"<b>위험요인</b><br>{reason_html}<br><br>"
        f"<b>오늘 행동</b><br>{risk_action}"
    )
    total_buy, total_value, profit, rate, weights, rows = metrics(data)
    s = asset_summary(data)
    card("포트폴리오 요약", f"총 매입원금 {won(s['buy_principal'])}<br>현재 평가금액 {won(s['stock_value'])}<br>평가수익금 {won(s['profit'])} · 평가수익률 {s['rate']:.2f}%")
    if weights:
        card("비중 요약", "<br>".join([f"{k} {v:.1f}%" for k, v in weights.items()]))


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


def holdings(data):
    header()
    card("내종목 자동평가", "현재가, 수익률, 종목점수, 행동 시그널을 함께 표시합니다.")
    render_trade_panel(data)
    render_toss_portfolio_sync(data)
    st.subheader("📋 보유종목 현황")
    render_holdings_briefing_accordion(data)
    render_buy_timing_ranking(data)
    render_value_dividend_ranking(data)
    render_rebalance_detail(data)
    render_target_price_ranking(data)
    render_future_probability_ranking(data)
    _, _, _, _, weights, rows = metrics(data)
    target = target_return(data)
    for i, (n, q, a, r) in enumerate(rows):
        st.markdown(f'<div class="hold"><div class="hold-name">{n}</div><div class="meta">수량 {q:g}주 · 평단 {won(a)} · 매입 {won(q*a)}</div></div>', unsafe_allow_html=True)
        if r:
            cls = "profit" if r["profit"] >= 0 else "loss"
            st.markdown(f'<div class="eval">현재가 {won(r["price"])} · {r["src"]}<br>평가금액 {won(r["value"])}<br>수익금 <span class="{cls}">{won(r["profit"])}</span> · 수익률 <span class="{cls}">{r["rate"]:.2f}%</span></div>', unsafe_allow_html=True)
            grade, risk_reason = risk_grade_simple(n, r)
            st.markdown(f'<div class="scorebox"><b>위험등급 {grade}</b><br>{risk_reason}</div>', unsafe_allow_html=True)
            score, sig, reason = stock_signal(n, q, a, r, weights, target)
            st.markdown(f'<div class="scorebox"><b>종목점수 {score}점 · {sig}</b><br>{reason}</div>', unsafe_allow_html=True)
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


def rec(data):
    header()
    if st.button("🔄 추천 다시 판단하기", use_container_width=True):
        st.rerun()
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
