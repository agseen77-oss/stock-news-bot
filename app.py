import re, math, requests, io, zipfile, os, time, json, hashlib
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import Counter

st.set_page_config(page_title="Stock Compass · ONE", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0"}
APP_SCAN_SCHEMA="FINAL_AB_BASE_2609"
APP_VERSION="VOLUME_ZONE_ENTRY_EXIT_V6_20261001"
LIVE_ENGINE_VERSION="ONE_LIVE_1.0_FIXED"
FUTURE_AI_SCHEMA="WEBSEARCH_NO_JSON_V2"
# UI styles
st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:1.2rem;padding-bottom:2.5rem}
h1,h2,h3{letter-spacing:-0.02em}
.hero{border:1px solid #343a40;border-radius:16px;padding:18px 20px;margin:8px 0 14px 0;background:linear-gradient(135deg,#171a20,#111318)}
.hero-top{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
.hero-name{font-size:34px;font-weight:950;line-height:1.05}
.hero-code{font-size:14px;color:#9aa0a6;margin-top:5px}
.hero-badge{font-size:18px;font-weight:900;padding:9px 14px;border-radius:999px;background:#15351f;border:1px solid #2b6b3c}
.hero-line{font-size:15px;color:#d7dbe0;margin-top:12px}
.kpi-grid{display:grid;grid-template-columns:repeat(5,minmax(135px,1fr));gap:10px;margin:12px 0 18px}
.kpi{border:1px solid #343a40;border-radius:12px;padding:12px 13px;background:#15181d}
.kpi .label{font-size:12px;color:#9aa0a6;margin-bottom:5px}
.kpi .value{font-size:22px;font-weight:900}
.action{border-radius:12px;padding:14px 16px;font-size:18px;font-weight:900;margin:10px 0}
.action-buy{background:#113b23;border:1px solid #2f7b49}
.action-wait{background:#3a2f12;border:1px solid #80651f}
.action-stop{background:#401919;border:1px solid #8b3434}
.section-title{font-size:20px;font-weight:950;margin:16px 0 8px}
.quick-grid{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:9px;margin:8px 0 14px}
.quick{border:1px solid #343a40;border-radius:10px;padding:10px 12px;background:#13161a}
.quick b{display:block;font-size:12px;color:#9aa0a6;margin-bottom:4px}
.quick span{font-size:18px;font-weight:900}
.card{border:1px solid #343a40;border-radius:12px;padding:14px;margin:8px 0}
.small{color:#9aa0a6;font-size:13px}
.data-status{border:1px solid #343a40;border-radius:10px;padding:9px 12px;margin:8px 0 10px;background:#15181d;color:#cfd4da;font-size:13px}
.flow-card{border:1px solid #343a40;border-radius:12px;padding:12px 14px;margin:10px 0;background:#13161a}
.flow-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:5px 0;font-size:14px}
.flow-name{min-width:58px;font-weight:900}
.radar-card{border:1px solid #343a40;border-radius:12px;padding:12px 14px;background:#13161a;height:100%}
.radar-title{font-size:16px;font-weight:950;margin-bottom:7px}
.radar-line{padding:4px 0;font-size:13px;color:#d7dbe0}
.future-card{border:1px solid #343a40;border-radius:14px;padding:14px 16px;margin:9px 0;background:linear-gradient(135deg,#142018,#111318)}
.future-rank{font-size:20px;font-weight:950;margin-bottom:4px}
.future-theme{font-size:13px;color:#9fd3ac;margin-bottom:8px}
.future-grid{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:7px;margin-top:8px}
.future-kpi{background:#15181d;border:1px solid #30353b;border-radius:9px;padding:8px 9px}
.future-kpi b{display:block;font-size:10px;color:#9aa0a6;margin-bottom:3px}
.future-kpi span{font-size:15px;font-weight:900}
.ai-status{border:1px solid #343a40;border-radius:10px;padding:9px 12px;margin:8px 0;background:#15181d;font-size:13px}
div[data-testid="stDataFrame"]{border:1px solid #30343a;border-radius:10px;overflow:hidden}
@media(max-width:900px){
 .block-container{padding-left:.55rem!important;padding-right:.55rem!important;padding-top:.65rem!important}
 .kpi-grid{grid-template-columns:repeat(2,1fr)!important;gap:7px!important}
 .quick-grid{grid-template-columns:repeat(2,1fr)!important;gap:7px!important}
 .future-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .hero{padding:14px 13px!important;border-radius:13px!important}
 .hero-name{font-size:24px!important;line-height:1.18!important}
 .hero-code{font-size:14px!important;line-height:1.5!important}
 .hero-line{font-size:15px!important;line-height:1.55!important}
 .hero-badge{font-size:15px!important;padding:7px 10px!important}
 .small,.data-status,.radar-line,.flow-row,.future-theme,.ai-status{font-size:14px!important;line-height:1.55!important}
 .section-title{font-size:19px!important;margin-top:14px!important}
 .radar-title{font-size:17px!important}
 .future-rank{font-size:20px!important}
 .future-kpi b{font-size:12px!important}
 .future-kpi span{font-size:16px!important}
 div[data-testid="stMetricLabel"] p{font-size:14px!important}
 div[data-testid="stMetricValue"]{font-size:24px!important}
 div[data-testid="stMetricDelta"]{font-size:13px!important}
 div[data-testid="stMarkdownContainer"] p,
 div[data-testid="stCaptionContainer"] p{font-size:14px!important;line-height:1.55!important}
 div.stButton>button{min-height:46px!important;font-size:15px!important;font-weight:800!important}
 div[role="radiogroup"] label{font-size:14px!important}
}
@media(max-width:520px){
 .kpi-grid,.quick-grid,.future-grid{grid-template-columns:1fr 1fr!important}
 .hero-name{font-size:22px!important}
 .card,.flow-card,.radar-card,.future-card{padding:11px!important}
}
</style>
""",unsafe_allow_html=True)

def won(x):
    try:return f"{int(round(float(x))):,}원"
    except:return "-"

# ---------------- V2 데이터 증분 저장 ----------------
KST=ZoneInfo("Asia/Seoul")
DAILY_CACHE_DIR=Path("data")/"daily_cache"
SCAN_META_FILE=Path("data")/"scan_meta.json"

def now_kst():
    return datetime.now(KST)

def _daily_cache_path(code):
    return DAILY_CACHE_DIR/f"{str(code).zfill(6)}.csv"

def _load_daily_disk(code):
    try:
        p=_daily_cache_path(code)
        if not p.exists():return pd.DataFrame()
        d=pd.read_csv(p,parse_dates=["date"])
        for c in ["open","high","low","close","volume"]:
            d[c]=pd.to_numeric(d[c],errors="coerce")
        return d.dropna(subset=["date","open","high","low","close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    except:
        return pd.DataFrame()

def _save_daily_disk(code,df):
    try:
        if df is None or df.empty:return
        DAILY_CACHE_DIR.mkdir(parents=True,exist_ok=True)
        d=df.copy().drop_duplicates("date").sort_values("date").tail(520)
        d.to_csv(_daily_cache_path(code),index=False,date_format="%Y-%m-%d")
    except:
        pass

def _read_scan_meta():
    try:
        if SCAN_META_FILE.exists():
            d=json.loads(SCAN_META_FILE.read_text(encoding="utf-8"))
            return d if isinstance(d,dict) else {}
    except:pass
    return {}

def _write_scan_meta(data_date,stats=None):
    try:
        SCAN_META_FILE.parent.mkdir(parents=True,exist_ok=True)
        payload={
            "data_date":str(data_date or ""),
            "updated_at_kst":now_kst().strftime("%Y-%m-%d %H:%M:%S"),
            "schema":APP_SCAN_SCHEMA,
        }
        if isinstance(stats,dict):
            payload.update({k:stats.get(k) for k in ("all","master_pass","daily_ok","prefilter") if k in stats})
        SCAN_META_FILE.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    except:pass

def _update_status_html():
    meta=_read_scan_meta()
    if not meta.get("data_date"):
        return '<div class="data-status">📅 데이터 업데이트 기록 없음 · 첫 ONE 검색은 과거 일봉 저장 때문에 시간이 걸릴 수 있습니다.</div>'
    dd=str(meta.get("data_date",""))
    ua=str(meta.get("updated_at_kst",""))
    try:
        ddate=pd.to_datetime(dd).date(); now=now_kst()
        if ddate==now.date() and now.time()>=dt_time(15,40): state="✅ 장마감 확정"
        elif ddate==now.date() and now.time()>=dt_time(9,0): state="🟡 장중 데이터"
        else: state="✅ 최근 장마감 데이터"
    except:
        state="데이터 확인"
    tm=ua[11:16] if len(ua)>=16 else "-"
    return f'<div class="data-status">📅 데이터 기준일 <b>{dd}</b> · 최근 업데이트 <b>{tm}</b> · {state}</div>'

@st.cache_data(ttl=1800,show_spinner=False)
def _name_from_code(code):
    """Resolve the name from the stock's own main page. Code is the primary key."""
    try:
        html=requests.get(
            f"https://finance.naver.com/item/main.naver?code={code}",
            headers={"User-Agent":"Mozilla/5.0"},timeout=8
        ).text
        # Canonical page title/name areas. Never infer a name from a neighboring market-list cell.
        pats=[
            r'<title>\s*([^:<]+?)\s*[:\-]',
            r'<div class="wrap_company">.*?<h2[^>]*>\s*<a[^>]*>([^<]+)</a>',
            r'<div class="wrap_company">.*?<h2[^>]*>([^<]+)</h2>',
        ]
        for pat in pats:
            m=re.search(pat,html,re.S|re.I)
            if m:
                name=re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',m.group(1))).strip()
                if name:return name
    except: pass
    return None

@st.cache_data(ttl=21600,show_spinner=False)
def universe(limit_each=None):
    """KIS 공식 마스터. 메인 ONE, 저유동 급등감시, ETF 섹터레이더를 한 번에 분리한다."""
    urls={"KOSPI":"https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
          "KOSDAQ":"https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip"}
    specs={
      "KOSPI":([2,1,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9,5,5,1,1,1,2,1,1,1,2,2,2,3,1,3,12,12,8,15,21,2,7,1,1,1,1,1,9,9,9,5,9,8,9,3,1,1,1],
       ['그룹코드','시총규모','업종대','업종중','업종소','제조업','저유동성','지배구조','K200섹터','K100','K50','KRX','ETP','ELW','KRX100','자동차','반도체','바이오','은행','SPAC','에너지','철강','단기과열','미디어','건설','Non1','증권','선박','보험','운송','SRI','기준가','매매단위','시간외단위','거래정지','정리매매','관리종목','시장경고','경고예고','불성실','우회상장','락','액면변경','증자','증거금','신용','신용기간','전일거래량','액면가','상장일자','상장주수','자본금','결산월','공모가','우선주','공매도과열','이상급등','KRX300','KOSPI','매출액','영업이익','경상이익','당기순이익','ROE','기준년월','시가총액','그룹사','신용한도초과','담보대출','대주']),
      "KOSDAQ":([2,1,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9,5,5,1,1,1,2,1,1,1,2,2,2,3,1,3,12,12,8,15,21,2,7,1,1,1,1,9,9,9,5,9,8,9,3,1,1,1],
       ['그룹코드','시총규모','업종대','업종중','업종소','벤처','저유동성','KRX','ETP','KRX100','자동차','반도체','바이오','은행','SPAC','에너지','철강','단기과열','미디어','건설','투자주의환기','증권','선박','보험','운송','K150','기준가','매매단위','시간외단위','거래정지','정리매매','관리종목','시장경고','경고예고','불성실','우회상장','락','액면변경','증자','증거금','신용','신용기간','전일거래량','액면가','상장일자','상장주수','자본금','결산월','공모가','우선주','공매도과열','이상급등','KRX300','매출액','영업이익','경상이익','당기순이익','ROE','기준년월','시가총액','그룹사','신용한도초과','담보대출','대주'])}
    out=[]; low_watch=[]; etfs=[]; total=0; seen=set(); sess=requests.Session(); sess.headers.update({"User-Agent":"Mozilla/5.0"})
    sector_words=("반도체","AI","인공지능","바이오","헬스케어","2차전지","배터리","전력","원자력","원전","로봇","방산","조선","자동차","소프트웨어","인터넷","게임","미디어","우주","항공","데이터센터","신재생","태양광","수소","금융","은행","증권","화학","철강")
    reject_etf_words=("ETN","인버스","레버리지","채권","국고채","회사채","금리","머니마켓","단기통안","CD금리","선물인버스")
    for market,url in urls.items():
        try:
            r=sess.get(url,timeout=15);r.raise_for_status();z=zipfile.ZipFile(io.BytesIO(r.content));raw=z.read(z.namelist()[0]);lines=raw.decode('cp949',errors='ignore').splitlines()
        except:continue
        widths,names=specs[market]; tail_len=sum(widths)
        for line in lines:
            if len(line)<=tail_len+21:continue
            total+=1
            front=line[:-tail_len]; tail=line[-tail_len:]
            rawcode=front[0:9].strip(); name=front[21:].strip()
            m=re.match(r'^(\d{6})',rawcode)
            if not m or not name:continue
            code=m.group(1)
            vals={};p=0
            for wd,nm in zip(widths,names):vals[nm]=tail[p:p+wd].strip();p+=wd
            def nval(k):
                try:return float(str(vals.get(k,'')).replace(',','').strip() or 0)
                except:return 0.0
            price=nval('기준가'); prevvol=nval('전일거래량'); mcap=nval('시가총액'); shares=nval('상장주수')
            if code in seen:continue
            if price<5000 or price>50000:continue
            if mcap and mcap<1000:continue
            if str(vals.get('SPAC','')).strip() in ('Y','1'):continue
            if str(vals.get('우선주','')).strip() not in ('','0','N'):continue
            if str(vals.get('관리종목','')).strip() in ('Y','1'):continue
            if str(vals.get('정리매매','')).strip() in ('Y','1'):continue
            if str(vals.get('거래정지','')).strip() in ('Y','1'):continue
            up=name.upper().replace(' ','')
            if '리츠' in name or 'REIT' in up:continue
            base={'code':code,'name':name,'market':market,'snapshot_price':price,'prev_volume':prevvol,
                  'prev_trade_value':price*prevvol,'market_cap_eok':mcap,'listed_shares':shares,'source':'KIS_MASTER'}
            is_etp=str(vals.get('ETP','')).strip() not in ('','0','N')
            if is_etp:
                # ETN/레버리지/인버스는 레이더에서도 제외. 섹터 ETF만 보조 레이더에 사용.
                if not any(w.upper() in up for w in reject_etf_words) and any(w.upper() in up for w in sector_words) and prevvol>=10000:
                    etfs.append(base)
                seen.add(code);continue
            lowflag=str(vals.get('저유동성','')).strip() in ('Y','1')
            if lowflag or prevvol<50000:
                # 저유동성은 메인 ONE에서 제외하되, 최근 거래가 살아난 종목만 급등감시 후보로 남긴다.
                if prevvol>=20000 and price*prevvol>=200_000_000:
                    low_watch.append(base)
                seen.add(code);continue
            seen.add(code);out.append(base)
    low_watch=sorted(low_watch,key=lambda x:x.get('prev_trade_value',0),reverse=True)[:30]
    etfs=sorted(etfs,key=lambda x:x.get('prev_trade_value',0),reverse=True)[:24]
    return out,total,low_watch,etfs

def _prefilter_stock(stock):
    try:
        df=daily(stock["code"],260)
        if df is None or len(df)<140:return None
        cur=float(df.iloc[-1].close)
        if not np.isfinite(cur) or cur<5000 or cur>50000:return None
        v=df.volume.astype(float).tail(20)
        if len(v)<15 or float(v.median())<50000:return None
        if float((df.close.astype(float).tail(20)*v).median())<500_000_000:return None
        z=dict(stock);z['_df']=df;return z
    except:return None

def _prefilter_stock(stock):
    try:
        df=stock.get("_df")
        if df is None: df=daily(stock["code"],260)
        if df is None or len(df)<140:return None
        cur=float(df.iloc[-1].close)
        if not np.isfinite(cur) or cur<5000 or cur>50000:return None
        v=df.volume.astype(float).tail(20)
        if len(v)<15:return None
        if float(v.median())<50000:return None
        if float((df.close.astype(float).tail(20)*v).median())<500_000_000:return None
        if (v<=0).sum()>=3:return None
        z=dict(stock); z["_df"]=df
        return z
    except:return None

def _prefilter_stock(stock):
    """시장목록에서 이미 1차 필터된 종목만 통과시킨다. 추가 HTTP 호출 없음."""
    try:
        p=float(stock.get("snapshot_price",0) or 0)
        v=float(stock.get("snapshot_volume",0) or 0)
        tv=float(stock.get("snapshot_value",0) or 0)
        if p<5000 or p>50000:return None
        if v<50000 or tv<500_000_000:return None
        return stock
    except:
        return None

@st.cache_data(ttl=1800,show_spinner=False)
def _secret(*names, default=""):
    for name in names:
        try:
            v=os.environ.get(name)
            if v:return str(v).strip()
        except:pass
        try:
            if name in st.secrets and st.secrets.get(name):return str(st.secrets.get(name)).strip()
            if "kis" in st.secrets and name in st.secrets["kis"] and st.secrets["kis"].get(name):
                return str(st.secrets["kis"].get(name)).strip()
        except:pass
    return default

def kis_credentials():
    app_key=_secret("KIS_APP_KEY","KIS_APPKEY","KOREA_INVESTMENT_APP_KEY","APP_KEY")
    app_secret=_secret("KIS_APP_SECRET","KIS_APPSECRET","KOREA_INVESTMENT_APP_SECRET","APP_SECRET")
    paper=_secret("KIS_PAPER","KOREA_INVESTMENT_PAPER",default="false").lower() in ("1","true","yes","y")
    return app_key,app_secret,paper

def kis_base_url():
    _,_,paper=kis_credentials()
    return "https://openapivts.koreainvestment.com:29443" if paper else "https://openapi.koreainvestment.com:9443"

KIS_TOKEN_CACHE_FILE = Path("data") / "kis_token.json"

def _kis_cache_key(app_key, app_secret, paper):
    raw=f"{app_key}|{app_secret}|{bool(paper)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]

def _read_kis_token_cache():
    try:
        if KIS_TOKEN_CACHE_FILE.exists():
            with open(KIS_TOKEN_CACHE_FILE,"r",encoding="utf-8") as f:
                d=json.load(f)
            if isinstance(d,dict): return d
    except: pass
    return {}

def _write_kis_token_cache(data):
    try:
        KIS_TOKEN_CACHE_FILE.parent.mkdir(parents=True,exist_ok=True)
        with open(KIS_TOKEN_CACHE_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
    except: pass

def _parse_expire(v):
    try:return datetime.strptime(str(v),"%Y-%m-%d %H:%M:%S")
    except:return datetime.utcfromtimestamp(0)

@st.cache_data(ttl=60,show_spinner=False)
def kis_stable_token_info(force_new=False):
    app_key,app_secret,paper=kis_credentials()
    if not app_key or not app_secret:
        return {"ok":False,"status":"키 없음","error":"Streamlit Secrets에서 KIS APP KEY/SECRET을 찾지 못했습니다.","token":"","cached":False}

    now=datetime.utcnow()
    key=_kis_cache_key(app_key,app_secret,paper)
    cache=_read_kis_token_cache()

    if not force_new:
        token=str(cache.get("access_token","") or "")
        exp=_parse_expire(cache.get("expires_at_utc",""))
        if token and cache.get("cache_key")==key and exp > now+timedelta(minutes=10):
            return {"ok":True,"status":"재사용","error":"","token":token,"cached":True,
                    "expires_at_utc":cache.get("expires_at_utc","")}

    try:
        url=f"{kis_base_url()}/oauth2/tokenP"
        payload={"grant_type":"client_credentials","appkey":app_key,"appsecret":app_secret}
        r=requests.post(url,json=payload,timeout=10)
        try: js=r.json()
        except: js={"raw":r.text[:180]}
        token=str(js.get("access_token","") or "") if isinstance(js,dict) else ""
        if r.status_code==200 and token:
            issued=now
            expires=now+timedelta(hours=23,minutes=30)
            data={"cache_key":key,"paper":bool(paper),"access_token":token,
                  "issued_at_utc":issued.strftime("%Y-%m-%d %H:%M:%S"),
                  "expires_at_utc":expires.strftime("%Y-%m-%d %H:%M:%S")}
            _write_kis_token_cache(data)
            return {"ok":True,"status":"신규발급","error":"","token":token,"cached":False,
                    "expires_at_utc":data["expires_at_utc"]}
        msg=""
        if isinstance(js,dict):
            msg=str(js.get("msg1") or js.get("error_description") or js.get("error") or js)[:180]
        else:
            msg=str(js)[:180]
        return {"ok":False,"status":f"HTTP {r.status_code}","error":msg,"token":"","cached":False}
    except Exception as e:
        return {"ok":False,"status":"요청 실패","error":str(e)[:180],"token":"","cached":False}

def kis_access_token():
    info=kis_stable_token_info(False)
    return info.get("token","") if info.get("ok") else ""

def kis_ready():
    a,b,_=kis_credentials()
    return bool(a and b)

def kis_connection_probe():
    """실제 스캔 전에 인증과 일봉 1종목을 분리 점검."""
    if not kis_ready():
        return {"ok":False,"stage":"인증","error":"KIS APP KEY/SECRET 인식 실패","token_status":"키 없음"}
    info=kis_stable_token_info(False)
    if not info.get("ok"):
        return {"ok":False,"stage":"토큰","error":info.get("error","토큰 발급 실패"),
                "token_status":info.get("status","실패")}
    try:
        app_key,app_secret,_=kis_credentials()
        end_dt=datetime.now()
        start_dt=end_dt-timedelta(days=90)
        url=f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers={"authorization":f"Bearer {info['token']}","appkey":app_key,"appsecret":app_secret,
                 "tr_id":"FHKST03010100","custtype":"P"}
        params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":"005930",
                "FID_INPUT_DATE_1":start_dt.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2":end_dt.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE":"D","FID_ORG_ADJ_PRC":"0"}
        r=requests.get(url,headers=headers,params=params,timeout=10)
        try: js=r.json()
        except: js={}
        if r.status_code!=200:
            return {"ok":False,"stage":"일봉","error":f"HTTP {r.status_code}: {r.text[:120]}",
                    "token_status":info.get("status","정상")}
        if str(js.get("rt_cd","0")) not in ("0",""):
            return {"ok":False,"stage":"일봉","error":str(js.get("msg1") or js)[:160],
                    "token_status":info.get("status","정상")}
        rows=js.get("output2") or js.get("output") or []
        if isinstance(rows,dict): rows=[rows]
        if not rows:
            return {"ok":False,"stage":"일봉","error":"삼성전자 일봉 응답이 비어 있습니다.",
                    "token_status":info.get("status","정상")}
        return {"ok":True,"stage":"정상","error":"","token_status":info.get("status","정상"),
                "probe_rows":len(rows)}
    except Exception as e:
        return {"ok":False,"stage":"일봉","error":str(e)[:160],
                "token_status":info.get("status","정상")}

def _kis_rows_to_df(rows):
    out=[]
    for r in rows or []:
        try:
            d=str(r.get("stck_bsop_date") or "")
            op=float(str(r.get("stck_oprc") or 0).replace(",",""))
            hi=float(str(r.get("stck_hgpr") or 0).replace(",",""))
            lo=float(str(r.get("stck_lwpr") or 0).replace(",",""))
            cl=float(str(r.get("stck_clpr") or 0).replace(",",""))
            vo=float(str(r.get("acml_vol") or 0).replace(",",""))
            if len(d)==8 and cl>0:out.append({"date":pd.to_datetime(d,format="%Y%m%d"),"open":op,"high":hi,"low":lo,"close":cl,"volume":vo})
        except:continue
    return out

def _kis_fetch_window(code,start_dt,end_dt,token=None):
    if not kis_ready():return []
    token=token or kis_access_token()
    if not token:return []
    app_key,app_secret,_=kis_credentials()
    url=f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    headers={"authorization":f"Bearer {token}","appkey":app_key,"appsecret":app_secret,"tr_id":"FHKST03010100","custtype":"P"}
    params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":str(code).zfill(6),
            "FID_INPUT_DATE_1":start_dt.strftime("%Y%m%d"),"FID_INPUT_DATE_2":end_dt.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE":"D","FID_ORG_ADJ_PRC":"0"}
    for retry in range(3):
        try:
            r=requests.get(url,headers=headers,params=params,timeout=8)
            if r.status_code==200:
                js=r.json()
                if str(js.get("rt_cd","0")) in ("0",""):
                    raw=js.get("output2") or js.get("output") or []
                    if isinstance(raw,dict):raw=[raw]
                    return _kis_rows_to_df(raw)
                if "초당" in str(js.get("msg1","")) or "EGW00201" in str(js):
                    time.sleep(0.15*(retry+1));continue
        except:pass
        time.sleep(0.12*(retry+1))
    return []



def _kis_minute_bars(code, token=None):
    """KIS 주식당일분봉조회. 최종 후보에만 호출해 전체 검색속도는 유지."""
    try:
        if not kis_ready():return pd.DataFrame()
        token=token or kis_access_token()
        if not token:return pd.DataFrame()
        app_key,app_secret,_=kis_credentials()
        url=f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        headers={
            "authorization":f"Bearer {token}",
            "appkey":app_key,
            "appsecret":app_secret,
            "tr_id":"FHKST03010200",
            "custtype":"P",
        }
        now=now_kst()
        hhmmss=now.strftime("%H%M%S")
        params={
            "FID_COND_MRKT_DIV_CODE":"J",
            "FID_INPUT_ISCD":str(code).zfill(6),
            "FID_INPUT_HOUR_1":hhmmss,
            "FID_PW_DATA_INCU_YN":"Y",
            "FID_ETC_CLS_CODE":"",
        }
        r=requests.get(url,headers=headers,params=params,timeout=8)
        if r.status_code!=200:return pd.DataFrame()
        js=r.json()
        if str(js.get("rt_cd","0")) not in ("0",""):return pd.DataFrame()
        raw=js.get("output2") or []
        rows=[]
        for q in raw:
            try:
                d=str(q.get("stck_bsop_date") or now.strftime("%Y%m%d"))
                t=str(q.get("stck_cntg_hour") or q.get("cntg_hour") or "")
                if len(t)<6:continue
                rows.append({
                    "date":pd.to_datetime(d+t[:6],format="%Y%m%d%H%M%S",errors="coerce"),
                    "open":float(str(q.get("stck_oprc") or q.get("oprc") or 0).replace(",","")),
                    "high":float(str(q.get("stck_hgpr") or q.get("hgpr") or 0).replace(",","")),
                    "low":float(str(q.get("stck_lwpr") or q.get("lwpr") or 0).replace(",","")),
                    "close":float(str(q.get("stck_prpr") or q.get("prpr") or 0).replace(",","")),
                    "volume":float(str(q.get("cntg_vol") or q.get("acml_vol") or 0).replace(",","")),
                })
            except:
                pass
        df=pd.DataFrame(rows)
        if df.empty:return df
        df=df.dropna(subset=["date"]).sort_values("date").drop_duplicates("date",keep="last")
        for c in ["open","high","low","close","volume"]:
            df[c]=pd.to_numeric(df[c],errors="coerce")
        return df.dropna(subset=["open","high","low","close"]).reset_index(drop=True)
    except:
        return pd.DataFrame()

def minute_entry_timing(code, confirm_line, token=None):
    """
    일봉 후보가 나온 뒤 5분봉으로 실제 진입 순간 확인.
    전체 종목에 분봉을 호출하지 않고 최종 상위 종목에만 사용.
    """
    raw=_kis_minute_bars(code,token=token)
    if raw is None or len(raw)<10:
        return {"available":False,"ok":False,"score":0,"state":"분봉 확인불가",
                "price":None,"volume_ratio":None}

    try:
        x=raw.copy().set_index("date")
        m5=x.resample("5min").agg({
            "open":"first","high":"max","low":"min","close":"last","volume":"sum"
        }).dropna(subset=["open","high","low","close"]).reset_index()
        if len(m5)<4:
            return {"available":False,"ok":False,"score":0,"state":"분봉 자료부족",
                    "price":float(raw.iloc[-1].close),"volume_ratio":None}

        c=m5.close.astype(float)
        v=m5.volume.astype(float)
        ma3=c.rolling(3).mean()
        prev_high=float(m5.iloc[-2].high)
        vr=float(v.iloc[-1]/max(float(v.iloc[-4:-1].mean()),1.0)) if len(v)>=4 else 1.0
        price=float(c.iloc[-1])
        line=float(confirm_line)

        checks=[
            price>=line,                         # 일봉 반등확인선 위
            c.iloc[-1]>=c.iloc[-2],             # 직전 5분봉보다 상승
            c.iloc[-1]>=ma3.iloc[-1],           # 5분봉 단기평균 위
            ma3.iloc[-1]>=ma3.iloc[-2],         # 5분봉 평균 상승
            price>=prev_high or vr>=1.20,        # 직전 고점 돌파 또는 거래량 유입
        ]
        score=int(sum(bool(z) for z in checks))
        ok=bool(price>=line and score>=4)
        if ok:state="진입 시점 확인"
        elif price<line:state="반등확인선 대기"
        elif score>=3:state="분봉 반등 진행"
        else:state="분봉 대기"
        return {
            "available":True,"ok":ok,"score":score,"state":state,
            "price":price,"volume_ratio":round(vr,2),
            "last_time":str(m5.iloc[-1]["date"])[11:16],
        }
    except:
        return {"available":False,"ok":False,"score":0,"state":"분봉 확인불가",
                "price":None,"volume_ratio":None}


def _kis_multi_quote(codes, token=None, progress=None):
    """
    KIS 관심종목 멀티시세: 한 번에 최대 30종목.
    어제까지의 일봉은 디스크 캐시를 쓰고, 오늘 OHLCV만 이 API로 묶어서 갱신한다.
    """
    codes=[str(c).zfill(6) for c in codes if str(c).strip()]
    codes=list(dict.fromkeys(codes))
    if not codes or not kis_ready():
        return {}
    token=token or kis_access_token()
    if not token:
        return {}
    app_key,app_secret,_=kis_credentials()
    url=f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/intstock-multprice"
    headers={
        "authorization":f"Bearer {token}",
        "appkey":app_key,
        "appsecret":app_secret,
        "tr_id":"FHKST11300006",
        "custtype":"P",
    }
    out={}
    chunks=[codes[i:i+30] for i in range(0,len(codes),30)]
    for bi,chunk in enumerate(chunks,1):
        if progress is not None:
            try: progress.progress(bi/max(len(chunks),1), text=f"오늘 시세 묶음 업데이트 {bi}/{len(chunks)}")
            except: pass
        params={}
        for j,code in enumerate(chunk,1):
            params[f"FID_COND_MRKT_DIV_CODE_{j}"]="J"
            params[f"FID_INPUT_ISCD_{j}"]=code
        ok=False
        for retry in range(3):
            try:
                r=requests.get(url,headers=headers,params=params,timeout=8)
                js=r.json() if r.status_code==200 else {}
                if r.status_code==200 and str(js.get("rt_cd","0")) in ("0",""):
                    raw=js.get("output") or []
                    if isinstance(raw,dict): raw=[raw]
                    for q in raw:
                        try:
                            code=str(q.get("inter_shrn_iscd") or q.get("stck_shrn_iscd") or "").zfill(6)
                            if not code.strip("0"): continue
                            close=float(str(q.get("inter2_prpr") or 0).replace(",",""))
                            op=float(str(q.get("inter2_oprc") or close).replace(",",""))
                            hi=float(str(q.get("inter2_hgpr") or close).replace(",",""))
                            lo=float(str(q.get("inter2_lwpr") or close).replace(",",""))
                            vol=float(str(q.get("acml_vol") or 0).replace(",",""))
                            amt=float(str(q.get("acml_tr_pbmn") or 0).replace(",",""))
                            if close>0:
                                out[code]={"open":op or close,"high":hi or close,"low":lo or close,
                                           "close":close,"volume":vol,"amount":amt}
                        except: pass
                    ok=True
                    break
                msg=str(js.get("msg1","") or js)
                if "초당" in msg or "EGW00201" in msg or "EGW00215" in msg:
                    time.sleep(0.18*(retry+1))
                    continue
            except:
                pass
            time.sleep(0.14*(retry+1))
        # KIS 실전 REST 18TPS 이하 유지. 멀티시세는 약 30종목/호출이라 호출 수 자체가 작다.
        time.sleep(0.07)
    return out

def _merge_cached_quote(code, count=260, quote=None):
    """충분한 과거 캐시가 있으면 KIS 일봉 API를 다시 부르지 않고 오늘 멀티시세 1행만 병합."""
    code=str(code).zfill(6)
    cached=_load_daily_disk(code)
    min_cache=min(140,max(70,int(count)))
    if cached is None or len(cached)<min_cache:
        # 최초 1회만 과거 일봉 전체 수집
        return daily(code,count)

    now=now_kst()
    q=quote if isinstance(quote,dict) else None
    if q and now.weekday()<5 and now.time()>=dt_time(9,0):
        today=pd.Timestamp(now.date())
        row=pd.DataFrame([{
            "date":today,
            "open":float(q.get("open") or q.get("close") or 0),
            "high":float(q.get("high") or q.get("close") or 0),
            "low":float(q.get("low") or q.get("close") or 0),
            "close":float(q.get("close") or 0),
            "volume":float(q.get("volume") or 0),
        }])
        if float(row.iloc[0]["close"])>0:
            cached=pd.concat([cached,row],ignore_index=True)
            cached=cached.drop_duplicates("date",keep="last").sort_values("date").reset_index(drop=True)
            _save_daily_disk(code,cached)
    return cached.tail(count).reset_index(drop=True)


@st.cache_data(ttl=300,show_spinner=False)
def daily(code,count=260):
    """V2: 최초 1회 과거 일봉 저장, 이후 최근 며칠만 다시 받아 증분 병합한다."""
    code=str(code).zfill(6)
    cached=_load_daily_disk(code)
    token=kis_access_token() if kis_ready() else ""
    if not token:
        return cached.tail(count).reset_index(drop=True) if not cached.empty else pd.DataFrame()

    now=now_kst(); today=now.date()
    min_cache=min(140,max(70,int(count)))
    need_full=(cached is None or len(cached)<min_cache)
    merged=cached.copy() if cached is not None else pd.DataFrame()

    if need_full:
        allrows=[]; seen=set(); end_dt=datetime.combine(today,dt_time(23,59))
        want=max(int(count),min_cache)
        for _ in range(5):
            start_dt=end_dt-timedelta(days=190)
            rows=_kis_fetch_window(code,start_dt,end_dt,token)
            if not rows:break
            for x in rows:
                key=x["date"].strftime("%Y%m%d")
                if key not in seen:seen.add(key);allrows.append(x)
            if len(allrows)>=want:break
            earliest=min(x["date"] for x in rows)
            end_dt=earliest.to_pydatetime()-timedelta(days=1)
            time.sleep(0.04)
        if allrows:
            fresh=pd.DataFrame(allrows)
            merged=pd.concat([cached,fresh],ignore_index=True) if not cached.empty else fresh
    else:
        last=pd.to_datetime(cached.iloc[-1]["date"]).date()
        # 장 시작 전/주말에는 전 거래일 저장분을 그대로 쓴다.
        should_refresh=(today.weekday()<5 and now.time()>=dt_time(9,0))
        # 장마감 후 오늘 일봉을 이미 확정 저장했다면 같은 날 다시 KIS를 부르지 않는다.
        if should_refresh and last==today and now.time()>=dt_time(15,40):
            try:
                mt=datetime.fromtimestamp(_daily_cache_path(code).stat().st_mtime,KST)
                if mt.date()==today and mt.time()>=dt_time(15,40):should_refresh=False
            except:pass
        if should_refresh:
            # 수정주가/권리락 보정에 대비해 최근 7일만 겹쳐 다시 확인.
            start_date=min(last,today)-timedelta(days=7)
            rows=_kis_fetch_window(code,datetime.combine(start_date,dt_time.min),datetime.combine(today,dt_time.max),token)
            if rows:
                fresh=pd.DataFrame(rows)
                merged=pd.concat([cached,fresh],ignore_index=True)

    if merged is None or merged.empty:return pd.DataFrame()
    merged=merged.drop_duplicates("date",keep="last").sort_values("date").reset_index(drop=True)
    for c in ["open","high","low","close","volume"]:merged[c]=pd.to_numeric(merged[c],errors="coerce")
    merged=merged.dropna(subset=["open","high","low","close"])
    _save_daily_disk(code,merged)
    return merged.tail(count).reset_index(drop=True)

def extrema(df,r=6):
    lo=df.low.to_numpy(); hi=df.high.to_numpy()
    lows=[]; highs=[]
    for i in range(r,len(df)-r):
        if lo[i]<=np.min(lo[i-r:i+r+1]): lows.append(i)
        if hi[i]>=np.max(hi[i-r:i+r+1]): highs.append(i)
    return lows,highs

def major_valleys(df):
    lows,_=extrema(df,6); n=len(df)
    vals=[]
    if not lows:return vals
    full=max(float(df.high.max()-df.low.min()),1)
    gl=float(df.low.min())
    for i in lows:
        lv=float(df.iloc[i].low)
        if not np.isfinite(lv) or lv<=0:
            continue
        pre=df.iloc[max(0,i-90):i+1]
        post=df.iloc[i:min(n,i+91)]
        pre_hi=float(pre.high.max()) if len(pre) else lv
        post_hi=float(post.high.max()) if len(post) else lv
        if not np.isfinite(pre_hi) or pre_hi<=0: pre_hi=lv
        if not np.isfinite(post_hi) or post_hi<=0: post_hi=lv
        drop=max(0.0,(pre_hi/lv-1)*100)
        rebound=max(0.0,(post_hi/lv-1)*100)
        global_depth=1-(lv-gl)/full
        age=n-1-i
        score=min(drop,70)/70*22+min(rebound,150)/150*34+global_depth*18
        if age<=120: score+=18*(1-age/120)
        elif age<=250: score+=5*(1-(age-120)/130)
        if drop>=8 or rebound>=15:
            vals.append({"i":i,"date":df.iloc[i].date,"low":lv,"score":score,
                         "drop":drop,"rebound":rebound,"age":age})
    return vals

def structure(df):
    vals=major_valleys(df)
    if not vals:return None
    recent=[v for v in vals if v["age"]<=120 and v["score"]>=30]
    pool=recent or [v for v in vals if v["age"]<=250] or vals
    A=max(pool,key=lambda v:v["score"])
    older_lower=[v for v in vals if v["i"]<A["i"] and v["low"]<A["low"]*.995]
    C=max(older_lower,key=lambda v:v["low"]) if older_lower else None

    # A 이후 큰 능선
    post=df.iloc[A["i"]+1:]
    ridge=None
    if len(post):
        ri=int(post.high.idxmax())
        ridge={"i":ri,"date":df.loc[ri,"date"],"high":float(df.loc[ri,"high"])}

    # 최근 20봉의 현재 방어 저점 (상승 시 추적선)
    recent20=df.tail(20)
    bi=int(recent20.low.idxmin())
    B={"i":bi,"date":df.loc[bi,"date"],"low":float(df.loc[bi,"low"])}
    return A,B,C,ridge

def candle_state(df,A):
    r=df.iloc[-1]
    rng=max(float(r.high-r.low),1e-9)
    close_pos=(float(r.close-r.low)/rng)*100
    upper=(float(r.high-max(r.open,r.close))/rng)*100
    lower=(float(min(r.open,r.close)-r.low)/rng)*100
    vr=float(r.volume/df.volume.tail(21).iloc[:-1].mean()) if len(df)>=21 else 1
    close_a=(float(r.close/A["low"])-1)*100
    rec=dng=0
    if close_a>=0: rec+=3
    if close_pos>=70: rec+=2
    if lower>=30: rec+=1
    if r.close>r.open: rec+=1
    if upper<=15: rec+=1
    if vr>=1.5 and close_pos>=55: rec+=1
    if close_a<0:dng+=2
    if close_pos<=30:dng+=2
    if r.close<r.open:dng+=1
    if lower<=12 and close_pos<=35:dng+=1
    if vr>=1.5 and close_pos<=35:dng+=1
    if close_a>=0 and rec>=dng+2: state="A · 보유/진입 가능성"
    elif close_a<0 and close_pos<=30 and dng>=rec+2: state="C경고 · 손절 준비"
    elif rec>=dng or lower>=30 or close_pos>=55: state="B · 관찰/회복 확인"
    else: state="관찰 · 아직 매수 안 함"
    return state,close_a,close_pos,upper,lower,vr,rec,dng

def candidate_score(df,A,B,C,ridge,state,feat):
    cur=float(df.iloc[-1].close)
    if cur>50000:return None
    close_a,cp,up,low,vr,rec,dng=feat
    # 선택과 집중: 현재가가 A와 너무 멀면 감점. 구조/행동/큰 추세를 함께 본다.
    dist=abs(cur/A["low"]-1)*100
    score=A["score"]
    score+=max(0,24-dist*.8)
    score+=rec*4-dng*4
    if state.startswith("A"):score+=12
    elif state.startswith("B"):score+=5
    elif state.startswith("C"):score-=30
    # 장기 큰 방향: 120봉 전보다 현재 종가가 높고, 최근 60봉 저점이 120봉 저점보다 높으면 가점
    if len(df)>=140:
        if cur>float(df.iloc[-121].close):score+=8
        lo60=float(df.tail(60).low.min()); lo120=float(df.tail(120).low.min())
        if lo60>=lo120*.98:score+=7
    # 능선까지 공간
    if ridge and ridge["high"]>cur*1.08:score+=5
    return score,dist


def identity_guard(stock,df):
    """시장목록 코드/종목명과 차트 데이터가 같은 종목인지 빠르게 검증."""
    try:
        code=str(stock.get("code",""))
        name=str(stock.get("name","")).strip()
        if not re.fullmatch(r"\d{6}",code) or not name:
            return False,"종목 식별값 오류"
        if df is None or df.empty:
            return False,"가격 데이터 없음"
        chart_close=float(df.iloc[-1].close)
        if not np.isfinite(chart_close) or chart_close<=0:
            return False,"현재가 오류"

        snap=float(stock.get("snapshot_price",0) or 0)
        # 장중/장마감 시점 차이를 감안해 너무 큰 괴리만 차단.
        if snap>0:
            gap=abs(chart_close/snap-1)
            if gap>0.25:
                return False,"시장목록/차트 가격 불일치"
        return True,"정상"
    except:
        return False,"식별 검증 실패"

def big_trend_gate(df):
    try:
        c=df.tail(260).close.astype(float)
        if len(c)<140:return {"ok":False,"state":"자료부족","score":0}
        ma60=c.rolling(60).mean()
        ln,lp=float(c.iloc[-60:].min()),float(c.iloc[-120:-60].min())
        hn,hp=float(c.iloc[-60:].max()),float(c.iloc[-120:-60].max())
        score=int(sum([c.iloc[-1]>=ma60.iloc[-1],ma60.iloc[-1]>=ma60.iloc[-21],
                       ln>=lp*.97,hn>=hp*.95,c.iloc[-1]>=c.iloc[-121]*.90]))
        hard=(hn<hp*.90 and ln<lp*.95 and c.iloc[-1]<ma60.iloc[-1])
        return {"ok":bool(score>=3 and not hard),
                "state":"상승/회복" if score>=4 else ("중립" if score>=3 else "하락"),
                "score":score}
    except:return {"ok":False,"state":"확인불가","score":0}


def _resample_ohlcv(df, rule):
    try:
        x=df.copy()
        x["date"]=pd.to_datetime(x["date"],errors="coerce")
        x=x.dropna(subset=["date"]).set_index("date").sort_index()
        rr="ME" if str(rule)=="M" else rule
        try:
            y=x.resample(rr).agg({
                "open":"first","high":"max","low":"min","close":"last","volume":"sum"
            })
        except Exception:
            # pandas 구버전 호환
            rr="M" if rr=="ME" else rr
            y=x.resample(rr).agg({
                "open":"first","high":"max","low":"min","close":"last","volume":"sum"
            })
        return y.dropna(subset=["open","high","low","close"]).reset_index()
    except:
        return pd.DataFrame()

def _trend_frame_score(tf, kind="W"):
    """월/주봉의 큰 방향만 판단. 매수 타점은 일봉/분봉에서 따로 잡는다."""
    try:
        c=tf.close.astype(float)
        h=tf.high.astype(float)
        l=tf.low.astype(float)
        if kind=="M":
            if len(c)<8:return {"score":0,"state":"자료부족","ok":False}
            fast=c.rolling(3).mean()
            slow=c.rolling(6).mean()
            recent_n=3; prev_n=3
        else:
            if len(c)<24:return {"score":0,"state":"자료부족","ok":False}
            fast=c.rolling(10).mean()
            slow=c.rolling(20).mean()
            recent_n=8; prev_n=8

        rlo=float(l.iloc[-recent_n:].min())
        plo=float(l.iloc[-(recent_n+prev_n):-recent_n].min())
        rhi=float(h.iloc[-recent_n:].max())
        phi=float(h.iloc[-(recent_n+prev_n):-recent_n].max())

        checks=[
            c.iloc[-1] >= fast.iloc[-1],
            fast.iloc[-1] >= fast.iloc[-3],
            c.iloc[-1] >= slow.iloc[-1],
            slow.iloc[-1] >= slow.iloc[-3],
            rlo >= plo*0.97,
            rhi >= phi*0.95,
        ]
        score=int(sum(bool(x) for x in checks))
        if score>=5:state="강한 상승"
        elif score>=4:state="상승"
        elif score==3:state="중립"
        elif score==2:state="약한 하락"
        else:state="하락"
        return {"score":score,"state":state,"ok":score>=3}
    except:
        return {"score":0,"state":"확인불가","ok":False}

def multi_timeframe_trend(df):
    """
    월봉 → 주봉으로 큰 추세 확인.
    일봉 A→B 타점과 분봉 진입시점은 별도 단계에서 판단.
    """
    try:
        w=_resample_ohlcv(df,"W-FRI")
        mo=_resample_ohlcv(df,"M")
        ws=_trend_frame_score(w,"W")
        ms=_trend_frame_score(mo,"M")
        # 강력추천: 월/주 모두 최소 중립 이상.
        strong_ok=bool(ms["score"]>=3 and ws["score"]>=3)
        # 후보: 월/주가 모두 명백한 하락일 때만 제외.
        candidate_ok=bool(ms["score"]>=2 and ws["score"]>=2)
        return {
            "monthly":ms,"weekly":ws,
            "strong_ok":strong_ok,"candidate_ok":candidate_ok,
            "monthly_bars":len(mo),"weekly_bars":len(w),
        }
    except:
        return {
            "monthly":{"score":0,"state":"확인불가","ok":False},
            "weekly":{"score":0,"state":"확인불가","ok":False},
            "strong_ok":False,"candidate_ok":False,
            "monthly_bars":0,"weekly_bars":0,
        }


def _live_pivot_lows(df,left=3,right=3):
    vals=df["low"].astype(float).to_numpy()
    out=[]
    for i in range(left,len(vals)-right):
        v=vals[i]
        if v==np.min(vals[i-left:i+right+1]) and v<np.min(vals[i-left:i]) and v<=np.min(vals[i+1:i+right+1]):
            out.append(i)
    return out



def _window_low_point(h, window, confirmed_end=None):
    """현재 시점에서 확인 가능한 저점만 사용해 N거래일 최저점을 반환."""
    try:
        n=len(h)
        end=int(confirmed_end if confirmed_end is not None else max(0,n-3))
        if end<=0:return None
        w=min(int(window),end)
        if w<5:return None
        seg=h.iloc[end-w:end]
        if seg.empty:return None
        i=int(seg.low.astype(float).idxmin())
        return {"i":i,"date":h.loc[i,"date"],"low":float(h.loc[i,"low"]),"window":int(window)}
    except:return None


def true_bottom_anchor(df):
    """
    고정 BASE A 탐색.
    최근 60봉은 B(재조정) 확인 구간으로 남기고 A로 쓰지 않는다.
    먼저 그 이전 60봉(현재 기준 61~120봉 전)에서 가장 깊은 확정 계곡을 찾는다.
    그 구간에 확정 계곡이 없을 때만 150봉 전까지 넓힌다.
    마지막 3봉은 저점 확정 전이므로 어떤 구간에서도 제외한다.
    """
    try:
        if df is None or len(df)<125:return None
        h=df.tail(300).copy().reset_index(drop=True)
        n=len(h); confirmed_end=max(0,n-3)
        if confirmed_end<121:return None
        piv=set(_live_pivot_lows(h,3,3))
        def pick(start,end):
            # Deep valley must be locally confirmed; the lowest price wins.
            ids=[i for i in piv if start<=i<end]
            if not ids:return None
            i=min(ids,key=lambda j:float(h.loc[j,"low"]))
            return {"i":int(i),"date":h.loc[i,"date"],"low":float(h.loc[i,"low"])}
        # 61~120 trading days before the latest confirmed candle.
        end=confirmed_end-60; start=max(3,end-60)
        base=pick(start,end); expanded=False
        if base is None:
            # Only if no deep valley exists: extend the older edge to 150 days.
            base=pick(max(3,confirmed_end-150),end); expanded=True
        if base is None:return None

        ai=int(base['i']); A=float(base['low']); age=(n-1)-ai
        hierarchy=[{"window":60,"i":ai,"low":A,"date":base["date"]}]
        state="진바닥 · 60일 이전 깊은 계곡" if not expanded else "진바닥 · 150일 확장 깊은 계곡"

        return {
            "i":ai,"date":h.loc[ai,'date'],"low":A,
            "age":int(age),"fresh":False,"state":state,
            "base_window":150 if expanded else 120,"support_windows":[60],
            "expanded":expanded,"hierarchy":hierarchy,
            "audit":{
                "recent_excluded_sessions":60,
                "first_range_start":str(h.loc[start,'date'].date()),
                "first_range_end":str(h.loc[end-1,'date'].date()),
                "used_range":"150일 확장" if expanded else "60일 이전 기본구간",
            },
        }
    except:return None




def below_b_support_profile(df, b_price, lookback=120, depth_pct=5.0):
    """
    B 바로 아래쪽(B ~ B-5%)에 실제로 쌓인 거래량만 측정한다.
    B 위쪽 거래는 지지매물로 인정하지 않는다.
    신호 당일 봉은 제외하여 미래정보를 쓰지 않는다.
    """
    try:
        if df is None or len(df)<30:
            return {"state":"확인불가","below_share":0.0,"density":0.0,"touch_share":0.0}
        h=df.copy().reset_index(drop=True)
        hist=h.iloc[:-1].tail(int(lookback)).copy()
        b=float(b_price)
        if hist.empty or b<=0:
            return {"state":"확인불가","below_share":0.0,"density":0.0,"touch_share":0.0}

        zlo=b*(1-float(depth_pct)/100.0)
        zhi=b
        total=max(float(hist.volume.astype(float).clip(lower=0).sum()),1.0)

        zone_vol=0.0
        touches=0
        for _,r in hist.iterrows():
            lo=float(r.low); hi=float(r.high); vol=max(float(r.volume),0.0)
            if hi<lo: lo,hi=hi,lo
            overlap=max(0.0,min(hi,zhi)-max(lo,zlo))
            if overlap>0:
                touches+=1
                span=max(hi-lo, max(b*0.001,1e-9))
                zone_vol += vol*min(1.0,overlap/span)

        below_share=zone_vol/total*100.0
        touch_share=touches/max(len(hist),1)*100.0

        obs_lo=float(hist.low.astype(float).min())
        obs_hi=float(hist.high.astype(float).max())
        obs_span=max(obs_hi-obs_lo,b*0.01)
        expected=min(1.0,max(0.01,(zhi-zlo)/obs_span))*100.0
        density=below_share/max(expected,0.01)

        if density>=1.20 and below_share>=8.0 and touch_share>=8.0:
            state="강함"
        elif density<0.65 and below_share<5.0:
            state="약함"
        else:
            state="보통"

        return {
            "state":state,
            "below_share":round(below_share,2),
            "density":round(float(density),3),
            "touch_share":round(touch_share,2),
            "zone_low":zlo,"zone_high":zhi,
        }
    except:
        return {"state":"확인불가","below_share":0.0,"density":0.0,"touch_share":0.0}


def b_support_supply_profile(df, b_price, lookback=120, zone_down=3.0, zone_up=4.0):
    """
    B 부근/아래 매물대 = 지지력.
    신호 당일까지 이미 형성된 거래만 사용하며, 현재 봉은 제외한다.
    B의 -3% ~ +4% 가격대에 거래가 얼마나 집중되어 있는지 본다.
    """
    try:
        if df is None or len(df)<30:
            return {"state":"확인불가","zone_share":0.0,"density":0.0,"touch_share":0.0}
        h=df.copy().reset_index(drop=True)
        hist=h.iloc[:-1].tail(int(lookback)).copy()
        b=float(b_price)
        if hist.empty or b<=0:
            return {"state":"확인불가","zone_share":0.0,"density":0.0,"touch_share":0.0}

        zlo=b*(1-float(zone_down)/100.0)
        zhi=b*(1+float(zone_up)/100.0)
        total=max(float(hist.volume.astype(float).clip(lower=0).sum()),1.0)

        zone_vol=0.0
        touches=0
        for _,r in hist.iterrows():
            lo=float(r.low); hi=float(r.high); vol=max(float(r.volume),0.0)
            if hi<lo: lo,hi=hi,lo
            overlap=max(0.0,min(hi,zhi)-max(lo,zlo))
            if overlap>0:
                touches+=1
                span=max(hi-lo, max(b*0.001,1e-9))
                zone_vol += vol*min(1.0,overlap/span)

        zone_share=zone_vol/total*100.0
        touch_share=touches/max(len(hist),1)*100.0

        obs_lo=float(hist.low.astype(float).min())
        obs_hi=float(hist.high.astype(float).max())
        obs_span=max(obs_hi-obs_lo,b*0.01)
        expected=min(1.0,max(0.01,(zhi-zlo)/obs_span))*100.0
        density=zone_share/max(expected,0.01)

        # '강함'은 B 부근에 반복 거래가 쌓여 지지 역할을 할 가능성이 큰 경우.
        if (density>=1.25 and zone_share>=10.0) or (touch_share>=18.0 and density>=1.00):
            state="강함"
        elif density<0.70 and zone_share<7.0 and touch_share<9.0:
            state="약함"
        else:
            state="보통"

        return {
            "state":state,
            "zone_share":round(zone_share,1),
            "density":round(float(density),2),
            "touch_share":round(touch_share,1),
            "zone_low":zlo,"zone_high":zhi,
        }
    except:
        return {"state":"확인불가","zone_share":0.0,"density":0.0,"touch_share":0.0}


def overhead_supply_profile(df, base_price, target_pct=10.0, lookback=120, bins=18):
    """
    진바닥/A-B 판정 이후에만 보는 상단 매물대.
    과거 OHLC 범위와 거래량을 가격 구간에 분산해 base~+10% 사이의
    거래량 비중과 가장 두꺼운 가격벽을 계산한다. 미래 데이터는 사용하지 않는다.
    """
    try:
        if df is None or len(df)<30:return {"state":"확인불가","zone_share":0.0,"density":0.0,"wall_price":None,"wall_share":0.0}
        h=df.copy().reset_index(drop=True)
        # 현재 봉은 제외. 오늘 종가로 진입 판단할 때 오늘 거래량을 매물대로 소급하지 않는다.
        hist=h.iloc[:-1].tail(int(lookback)).copy()
        base=float(base_price)
        top=base*(1+float(target_pct)/100.0)
        if hist.empty or base<=0 or top<=base:
            return {"state":"확인불가","zone_share":0.0,"density":0.0,"wall_price":None,"wall_share":0.0}

        edges=np.linspace(base,top,int(bins)+1)
        alloc=np.zeros(int(bins),dtype=float)
        total=max(float(hist.volume.astype(float).clip(lower=0).sum()),1.0)
        for _,r in hist.iterrows():
            lo=float(r.low); hi=float(r.high); vol=max(float(r.volume),0.0)
            if vol<=0:continue
            if hi<lo:lo,hi=hi,lo
            if hi-lo<1e-9:
                px=float(r.close)
                j=int(np.searchsorted(edges,px,side='right')-1)
                if 0<=j<len(alloc):alloc[j]+=vol
                continue
            for j in range(len(alloc)):
                ov=max(0.0,min(hi,edges[j+1])-max(lo,edges[j]))
                if ov>0:alloc[j]+=vol*(ov/(hi-lo))

        zone_vol=float(alloc.sum())
        zone_share=zone_vol/total*100.0
        peak=float(alloc.max()) if len(alloc) else 0.0
        wall_share=peak/total*100.0
        wi=int(np.argmax(alloc)) if peak>0 else -1
        wall_price=float((edges[wi]+edges[wi+1])/2) if wi>=0 else None

        obs_lo=float(hist.low.astype(float).min()); obs_hi=float(hist.high.astype(float).max())
        obs_span=max(obs_hi-obs_lo,base*0.01)
        expected=min(1.0,max(0.01,(top-base)/obs_span))*100.0
        density=zone_share/max(expected,0.01)
        avg_bin=zone_vol/max(len(alloc),1)
        wall_ratio=peak/max(avg_bin,1.0)

        if (zone_share>=28 and density>=1.10) or (wall_share>=7.0 and wall_ratio>=2.0):
            state='두꺼움'
        elif zone_share<=12 and density<=0.90:
            state='얇음'
        else:
            state='보통'

        return {
            "state":state,
            "zone_share":round(zone_share,1),
            "density":round(float(density),2),
            "wall_price":wall_price,
            "wall_share":round(wall_share,1),
            "wall_ratio":round(float(wall_ratio),2),
            "base":base,"target":top,
        }
    except:
        return {"state":"확인불가","zone_share":0.0,"density":0.0,"wall_price":None,"wall_share":0.0}

def _live_ab_signal_core(df, use_b_support=True, use_overhead=True):
    """
    새 기본 순서:
    진바닥 A → B 지지 → B 주변 지지매물 → B+3% 재반등 → +10% 상단저항.

    진바닥 기준은 그대로 두되, 너무 엄격했던 ONE 컷은 완화한다.
    대신 완화된 신호는 B 지지매물이 실제로 받쳐주는 경우에만 살린다.
    """
    if df is None or len(df)<140:return None
    h=df.tail(300).copy().reset_index(drop=True)
    n=len(h)
    piv=_live_pivot_lows(h,3,3)
    if not piv:return None

    A0=true_bottom_anchor(h)
    if not A0:return None
    ai=int(A0["i"]); A=float(A0["low"])
    age=int(A0.get("age",999))

    # A 탐색은 60일 이전~최대 150일 확장까지가 고정 BASE 범위다.
    # 오래된 A일수록 B 지지가 강해야 한다는 안전장치만 유지한다.
    if age>150:return None

    today=h.iloc[-1]
    cur=float(today.close); op=float(today.open); hi=float(today.high); lo=float(today.low)
    rng=max(hi-lo,1e-9)
    body=abs(cur-op)/rng*100

    # 예전 53% 고정 컷을 완화. 53% 미만은 B 지지매물이 강해야만 최종 통과.
    if body<40:return None

    for bi in reversed(piv):
        # B 허용기간 35 → 55거래일, A-B 간격 120 → 150거래일
        if bi<=ai or bi>n-4 or bi<n-55:continue
        if not (8<=bi-ai<=150):continue

        B=float(h.iloc[bi].low)
        if B<A:continue

        mid=h.iloc[ai+1:bi]
        if mid.empty:continue
        peak=float(mid.high.astype(float).max())
        rebound=(peak/A-1)*100
        if rebound<5:continue

        # B가 A보다 너무 멀어진 구조는 제외하되 12% → 18%로 완화.
        bdist=(B/A-1)*100
        if bdist<0 or bdist>18:continue

        trigger=krx_ceil_price(B*1.03)
        after_b=h.iloc[bi+1:]
        if len(after_b)==0 or float(after_b.low.astype(float).min())<A:continue

        # 같은 B에서 한 번만 신호가 나오도록 첫 B+3% 회복일만 사용.
        prior=h.iloc[bi+1:n-1]
        if len(prior) and (prior.close.astype(float)>=trigger).any():continue
        if cur<trigger:continue
        if cur<=float(h.iloc[-2].close):continue

        tail=h.close.astype(float).tail(5).to_numpy()
        rises=sum(tail[j]>tail[j-1] for j in range(1,len(tail)))
        if rises<1:continue

        bsup=b_support_supply_profile(h,B,120,3.0,4.0)

        if use_b_support:
            # 사용자가 관찰한 핵심: B가 버티려면 B 부근 매물대가 받쳐줘야 한다.
            if bsup.get("state")=="약함":continue
            if age>60 and bsup.get("state")!="강함":continue
            if body<53 and bsup.get("state")!="강함":continue
            if bdist>12 and bsup.get("state")!="강함":continue

        overhead=overhead_supply_profile(h,cur,10.0,120,18)
        if use_overhead and overhead.get("state")=="두꺼움":continue

        ridx=int(mid.high.astype(float).idxmax())
        return {
            "A":{**A0},
            "B":{"i":bi,"date":h.iloc[bi].date,"low":B},
            "C":None,
            "ridge":{"i":ridx,"date":h.loc[ridx,"date"],"high":peak},
            "confirm_line":trigger,"entry":cur,
            "body_pct":body,"rebound_pct":rebound,"b_above_a_pct":bdist,
            "b_support":bsup,
            "supply":overhead,
            "true_bottom":A0,
            "state":"진바닥 A → B 지지매물 → B+3% 재반등 → 상단저항 통과"
        }
    return None


def _live_ab_signal(df):
    """
    실전 BASE는 진바닥 A → B 지지 → B+3% 재반등 그대로 유지.
    B 아래 매물대는 아직 실전 컷으로 쓰지 않고 타임머신에서만 검증한다.
    """
    return _live_ab_signal_core(df, use_b_support=False, use_overhead=False)

def krx_tick_size(price):
    """KRX 주권 가격대별 최소 호가단위."""
    p=float(price)
    if p < 2000: return 1
    if p < 5000: return 5
    if p < 20000: return 10
    if p < 50000: return 50
    if p < 200000: return 100
    if p < 500000: return 500
    return 1000

def krx_ceil_price(price):
    """조건선/목표가는 기준값 이상이 되도록 실제 주문 가능한 호가로 올림."""
    p=float(price)
    tick=krx_tick_size(p)
    q=math.ceil((p-1e-12)/tick)*tick
    # 경계 가격을 넘은 경우 새 가격대 호가단위로 한 번 더 보정
    tick2=krx_tick_size(q)
    if tick2 != tick:
        q=math.ceil((q-1e-12)/tick2)*tick2
    return float(q)


def _candidate_ab_setup(df):
    """
    후보는 항상 ONE 뒤를 따라오도록 넓게 유지한다.
    단, 후보를 매수추천으로 오해하지 않게 약한 구조는 반드시 '관망' 표시.
    """
    if df is None or len(df)<140:return None
    h=df.tail(300).copy().reset_index(drop=True)
    n=len(h); cur=float(h.iloc[-1].close)
    if not np.isfinite(cur) or cur<=0:return None

    piv=_live_pivot_lows(h,3,3)
    A0=true_bottom_anchor(h)
    if not A0:return None

    ai=int(A0["i"]); A=float(A0["low"])
    best=None

    for bi in reversed(piv):
        if bi<=ai or bi>n-4 or bi<n-100:continue
        if not (6<=bi-ai<=230):continue
        B=float(h.iloc[bi].low)
        if B<A:continue

        mid=h.iloc[ai+1:bi]
        if mid.empty:continue
        peak=float(mid.high.astype(float).max())
        rebound=(peak/A-1)*100
        if rebound<2.5:continue

        bdist=(B/A-1)*100
        if bdist<0 or bdist>40:continue

        after=h.iloc[bi+1:]
        if len(after) and float(after.low.astype(float).min())<A:continue

        desired=krx_ceil_price(B*1.03)
        stop=A
        target=krx_ceil_price(desired*1.10)
        risk=abs((stop/desired-1)*100)
        gap=(cur/desired-1)*100
        if cur>=target*1.05:continue

        bsup=b_support_supply_profile(h,B,120,3.0,4.0)
        overhead=overhead_supply_profile(h,desired,10.0,120,18)
        age=int(A0.get("age",999))
        stale=age>90

        structural_watch=bool(
            stale or risk>18 or bdist>25 or
            bsup.get("state")=="약함" or
            overhead.get("state")=="두꺼움"
        )

        if structural_watch:
            status="관망"
        elif cur<desired:
            status="반등확인"
        elif gap<=4:
            status="진입준비"
        else:
            status="후보"

        # B 지지매물이 강할수록 후보 순위를 올리고, 상단저항은 감점.
        support_bonus={"강함":-6.0,"보통":0.0,"약함":8.0}.get(bsup.get("state"),2.0)
        overhead_pen={"얇음":-2.0,"보통":1.5,"두꺼움":8.0}.get(overhead.get("state"),3.0)
        structure_penalty=abs(min(bdist,25)-5.0)*0.35 + min(risk,40)*0.60 + max(0.0,5.0-rebound)*0.70
        proximity_penalty=min(abs(gap),20.0)*0.16
        age_pen=max(0,age-60)*0.12
        rank=structure_penalty+proximity_penalty+age_pen+support_bonus+overhead_pen

        ridx=int(mid.high.astype(float).idxmax())
        item={
            "A":{**A0},
            "B":{"i":bi,"date":h.iloc[bi].date,"low":B},
            "ridge":{"i":ridx,"date":h.loc[ridx,"date"],"high":float(h.loc[ridx,"high"])},
            "desired_entry":desired,"target":target,"stop":stop,
            "stop_pct":(stop/desired-1)*100,"gap_pct":gap,
            "rebound_pct":rebound,"b_above_a_pct":bdist,
            "status":status,"rank":rank,"mode":"TRUE_BOTTOM_AB",
            "true_bottom":A0,"b_support":bsup,"supply":overhead,
            "stale_bottom":stale,
        }
        if best is None or rank<best["rank"]:best=item

    if best is not None:
        return best

    # B가 아직 완성되지 않은 경우에도 '관망 후보'는 남긴다.
    # 이것은 매수추천이 아니라 다음 B 형성 여부를 보는 감시용이다.
    confirmed_end=max(1,n-3)
    if confirmed_end-ai<5:return None
    seg=h.iloc[max(ai+1,confirmed_end-30):confirmed_end]
    if seg.empty:return None
    bi=int(seg.low.astype(float).idxmin())
    if bi<=ai:return None
    B=max(A,float(h.loc[bi,"low"]))
    desired=krx_ceil_price(B*1.03)
    target=krx_ceil_price(desired*1.10)
    risk=abs((A/desired-1)*100)
    bsup=b_support_supply_profile(h,B,120,3.0,4.0)
    overhead=overhead_supply_profile(h,desired,10.0,120,18)
    mid=h.iloc[ai+1:bi+1]
    if mid.empty:return None
    ridx=int(mid.high.astype(float).idxmax())
    return {
        "A":{**A0},"B":{"i":bi,"date":h.loc[bi,"date"],"low":B},
        "ridge":{"i":ridx,"date":h.loc[ridx,"date"],"high":float(h.loc[ridx,"high"])},
        "desired_entry":desired,"target":target,"stop":A,
        "stop_pct":(A/desired-1)*100,"gap_pct":(cur/desired-1)*100,
        "rebound_pct":max(0.0,(float(mid.high.astype(float).max())/A-1)*100),
        "b_above_a_pct":(B/A-1)*100,
        "status":"관망","rank":50.0+min(risk,40)+int(A0.get("age",0))*0.10,
        "mode":"WATCH","true_bottom":A0,"b_support":bsup,"supply":overhead,
        "stale_bottom":int(A0.get("age",999))>90,
    }

def _surge_watch_signal(stock,df):
    """저유동성 메인 제외 종목 중 거래량/거래대금이 실제로 폭증한 경우만 별도 감시."""
    try:
        if df is None or len(df)<25:return None
        d=df.tail(25).copy(); cur=d.iloc[-1]; prev=d.iloc[-2]
        base=float(d.volume.astype(float).iloc[-21:-1].median())
        if base<=0:return None
        vr=float(cur.volume)/base
        trade=float(cur.close)*float(cur.volume)
        ret=(float(cur.close)/float(prev.close)-1)*100 if float(prev.close)>0 else 0.0
        if vr<3.0 or trade<500_000_000 or float(cur.volume)<50000 or ret<2.0:return None
        return {"code":stock['code'],"name":stock['name'],"market":stock['market'],
                "volume_ratio":vr,"ret1":ret,"trade_value":trade,
                "score":vr+max(ret,0)*0.18,"date":str(cur.date)[:10]}
    except:return None

def _etf_radar_entry(stock,df):
    try:
        if df is None or len(df)<65:return None
        c=df.close.astype(float)
        cur=float(c.iloc[-1]); r5=(cur/float(c.iloc[-6])-1)*100; r20=(cur/float(c.iloc[-21])-1)*100
        ma20=c.rolling(20).mean();ma60=c.rolling(60).mean()
        trend=sum([cur>=ma20.iloc[-1],cur>=ma60.iloc[-1],ma20.iloc[-1]>=ma20.iloc[-6],ma60.iloc[-1]>=ma60.iloc[-21]])
        score=r5*0.65+r20*0.20+trend*1.2
        return {"code":stock['code'],"name":stock['name'],"r5":r5,"r20":r20,"trend":trend,"score":score,"date":str(df.iloc[-1].date)[:10]}
    except:return None

def analyze_candidate(stock):
    try:
        df=stock.get("_df")
        if df is None:
            df=daily(stock["code"],300)
        if df is None or len(df)<140:return None
        ok,_reason=identity_guard(stock,df)
        if not ok:return None
        cur=float(df.iloc[-1].close)
        if not np.isfinite(cur) or cur<5000 or cur>50000:return None

        bt=big_trend_gate(df)
        # 월봉→주봉은 후보를 없애는 하드필터가 아니라 위험도/순위에 반영한다.
        # 후보는 화면에 남기되, 방향이 약하면 '관망'으로 표시한다.
        mtf=multi_timeframe_trend(df)
        if not bt: bt={"score":0,"ok":False,"state":"중립"}

        setup=_candidate_ab_setup(df)
        if not setup:return None

        raw_status=setup["status"]
        bt_score=int(bt.get("score",0))
        ms=int(mtf.get("monthly",{}).get("score",0))
        ws=int(mtf.get("weekly",{}).get("score",0))
        # 진바닥이 오래됐거나 상단 매물대가 두꺼우면 방향이 좋아도 관망.
        if raw_status=="관망" or setup.get("stale_bottom") or setup.get("b_support",{}).get("state")=="약함" or setup.get("supply",{}).get("state")=="두꺼움":
            final_status="관망"
        elif bt_score<=2 or ms<3 or ws<3:
            final_status="관망"
        elif raw_status=="확인선 하회":
            final_status="반등확인"
        elif raw_status=="진입준비":
            final_status="진입준비"
        else:
            final_status="후보"

        base_rank=float(setup.get("rank",0.0))
        direction_penalty=max(0,5-bt_score)*1.20
        ms=int(mtf.get("monthly",{}).get("score",0))
        ws=int(mtf.get("weekly",{}).get("score",0))
        mtf_penalty=max(0,4-ms)*1.10 + max(0,4-ws)*0.80
        rank=base_rank+direction_penalty+mtf_penalty

        return {
            "stock":stock,"df":df,"bigtrend":bt,"mtf":mtf,
            "A":setup["A"],"B":setup["B"],"C":None,"ridge":setup["ridge"],
            "state":final_status,"candidate_status":final_status,
            "raw_candidate_status":raw_status,
            "desired_entry":float(setup["desired_entry"]),
            "target":float(setup["target"]),
            "stop":float(setup["stop"]),
            "stop_pct":float(setup["stop_pct"]),
            "gap_pct":float(setup["gap_pct"]),
            "rebound_pct":float(setup["rebound_pct"]),
            "b_above_a_pct":float(setup["b_above_a_pct"]),
            "candidate_rank":float(rank),
            "candidate_mode":setup.get("mode","TRUE_BOTTOM_AB"),
            "true_bottom":setup.get("true_bottom",setup.get("A")),
            "b_support":setup.get("b_support",{}),
            "supply":setup.get("supply",{}),
            "stale_bottom":bool(setup.get("stale_bottom",False)),
        }
    except:
        return None



def analyze_one(stock):
    try:
        df=stock.get("_df")
        if df is None: df=daily(stock["code"],300)
        if df is None or len(df)<140:return None
        ok,_reason=identity_guard(stock,df)
        if not ok:return None
        cur=float(df.iloc[-1].close)
        if not np.isfinite(cur) or cur<5000 or cur>50000:return None

        bt=big_trend_gate(df)
        if not bt or not bt.get("ok",False):return None

        sig=_live_ab_signal_core(df,use_b_support=False,use_overhead=False)
        if not sig:return None

        A=sig["A"]; B=sig["B"]
        stop=float(A["low"]); entry=float(sig["entry"])
        if stop<=0 or stop>=entry:return None
        stop_pct=(stop/entry-1)*100

        mtf=multi_timeframe_trend(df)
        ms=int(mtf.get("monthly",{}).get("score",0))
        ws=int(mtf.get("weekly",{}).get("score",0))
        rank=float(sig["body_pct"]) + max(0,ms-3)*0.25 + max(0,ws-3)*0.15


        return {
            "stock":stock,"df":df,"bigtrend":bt,"mtf":mtf,
            "A":A,"B":B,"C":None,"ridge":sig["ridge"],
            "state":sig["state"],"score":rank,
            "dist":(entry/stop-1)*100,
            "entry":entry,"confirm_line":float(sig["confirm_line"]),
            "body_pct":float(sig["body_pct"]),
            "rebound_pct":float(sig["rebound_pct"]),
            "b_above_a_pct":float(sig["b_above_a_pct"]),
            "stop_pct":stop_pct,"true_bottom":sig.get("true_bottom",A),
            "b_support":{},"supply":{},"base_engine":True,
        }
    except Exception:
        return None

def scan(_n=None):
    probe=kis_connection_probe()
    if not probe.get("ok"):
        return None,None,[],[],{"schema":APP_SCAN_SCHEMA,"all":0,"master_pass":0,"prefilter":0,"daily_ok":0,
                             "source_error":True,"error_stage":probe.get("stage","KIS"),
                             "error":probe.get("error",""),"token_status":probe.get("token_status","")}

    u,total,low_watch,etf_watch=universe()
    if not u:
        return None,None,[],[],{"schema":APP_SCAN_SCHEMA,"all":total,"master_pass":0,"prefilter":0,"daily_ok":0,
                             "source_error":True,"error_stage":"종목마스터",
                             "error":"KIS 종목마스터 필터 결과가 0종목입니다.",
                             "token_status":probe.get("token_status","")}

    # 핵심 속도개선:
    # 과거 일봉은 저장본 사용 + 오늘 시세는 KIS 멀티종목 API(최대 30종목/호출)로 한 번에 갱신.
    # 600종목이면 기존 약 600번 일봉 호출 → 약 20여 번 멀티시세 호출.
    all_scan_stocks=[]
    seen_codes=set()
    for x in (u+low_watch+etf_watch):
        c=str(x.get("code","")).zfill(6)
        if c and c not in seen_codes:
            seen_codes.add(c); all_scan_stocks.append(x)

    qbar=st.progress(0,text="저장된 과거 일봉 확인 중...")
    token=kis_access_token() if kis_ready() else ""
    now=now_kst()
    need_today=(now.weekday()<5 and now.time()>=dt_time(9,0))
    quotes={}
    if need_today and token:
        quotes=_kis_multi_quote([x["code"] for x in all_scan_stocks],token=token,progress=qbar)
    qbar.empty()

    pre=st.progress(0,text=f"KIS 전체 {total:,}종목 → 메인 {len(u):,}종목 분석 준비...")
    pool=[];daily_ok=0; surge=[]; data_dates=[]; full_fetch_count=0
    for i,x in enumerate(u):
        if i%10==0 or i==len(u)-1:
            pre.progress((i+1)/len(u),text=f"{i+1:,}/{len(u):,} {x['name']} 저장 일봉 분석")
        try:
            before=_load_daily_disk(x['code'])
            if before is None or len(before)<140: full_fetch_count+=1
            df=_merge_cached_quote(x['code'],260,quotes.get(str(x['code']).zfill(6)))
            if df is not None and len(df)>=140:
                daily_ok+=1; data_dates.append(str(df.iloc[-1].date)[:10])
                cur=float(df.iloc[-1].close); v=df.volume.astype(float).tail(20)
                is_liquid=(5000<=cur<=50000 and len(v)>=15 and float(v.median())>=50000 and
                           float((df.close.astype(float).tail(20)*v).median())>=500_000_000)
                if is_liquid:
                    z=dict(x);z['_df']=df;pool.append(z)
                else:
                    sw=_surge_watch_signal(x,df)
                    if sw:surge.append(sw)
        except:pass
    pre.empty()

    for x in low_watch:
        try:
            df=_merge_cached_quote(x['code'],80,quotes.get(str(x['code']).zfill(6)))
            sw=_surge_watch_signal(x,df)
            if sw:surge.append(sw)
        except:pass
    surge=sorted({z['code']:z for z in surge}.values(),key=lambda z:z['score'],reverse=True)[:3]

    etf_radar=[]
    for x in etf_watch:
        try:
            df=_merge_cached_quote(x['code'],90,quotes.get(str(x['code']).zfill(6)))
            z=_etf_radar_entry(x,df)
            if z:etf_radar.append(z)
        except:pass
    etf_radar=sorted(etf_radar,key=lambda z:z['score'],reverse=True)[:3]

    if daily_ok==0:
        return None,None,[],[],{"schema":APP_SCAN_SCHEMA,"all":total,"master_pass":len(u),"prefilter":0,"daily_ok":0,
                             "source_error":True,"error_stage":"KIS 일봉","error":"인증 테스트는 통과했지만 전체 스캔 일봉이 모두 실패했습니다.",
                             "token_status":probe.get("token_status","")}

    bar=st.progress(0,text=f"1차 통과 {len(pool):,}종목 · 저장된 일봉으로 강력추천/후보 분석...")
    strong=[];candidates=[];candidate_checked=0
    for i,x in enumerate(pool):
        if i%10==0 or i==len(pool)-1:
            bar.progress((i+1)/max(len(pool),1),text=f"{i+1:,}/{len(pool):,} {x['name']} 구조 분석")
        z=analyze_one(x)
        if z:strong.append(z)
        c=analyze_candidate(x);candidate_checked+=1
        if c and (not z or z['stock']['code']!=c['stock']['code']):candidates.append(c)
    bar.empty()

    strong.sort(key=lambda z:(z['body_pct'],-z['dist']),reverse=True)
    candidates.sort(key=lambda z:(z['candidate_rank'],abs(z['stop_pct'])))

    def flow_bonus(z):
        try:
            f=investor_flow(z['stock']['code'],z['stock'].get('listed_shares',0))
            score=0
            score += 1 if (f.get('foreign_5') or 0)>0 else (-1 if (f.get('foreign_5') or 0)<0 else 0)
            score += 1 if (f.get('inst_5') or 0)>0 else (-1 if (f.get('inst_5') or 0)<0 else 0)
            return score
        except:return 0
    for z in strong[:3]:z['flow_bonus']=flow_bonus(z)
    for z in candidates[:5]:z['flow_bonus']=flow_bonus(z)
    # Research candidates never affect production ranks.
    strong.sort(
        key=lambda z:(z['score']+0.8*z.get('flow_bonus',0),-z['dist']),
        reverse=True
    )
    candidates.sort(
        key=lambda z:(z['candidate_rank']-0.6*z.get('flow_bonus',0),abs(z['stop_pct']))
    )

    # 분봉은 최종 상위 종목만 확인: 전체 검색속도 저하 방지.
    _minute_token=token
    for z in strong[:3]:
        z["minute"]=minute_entry_timing(z["stock"]["code"],z.get("confirm_line",z.get("entry",0)),token=_minute_token)
    for z in candidates[:3]:
        z["minute"]=minute_entry_timing(z["stock"]["code"],z.get("desired_entry",0),token=_minute_token)

    # 검증된 BASE ONE은 분봉 때문에 탈락시키지 않는다. 분봉은 진입시점 참고만.
    one=strong[0] if strong else None
    candidate_top3=candidates[:3]
    candidate=candidate_top3[0] if candidate_top3 else None
    data_date=Counter(data_dates).most_common(1)[0][0] if data_dates else ""
    stats={"schema":APP_SCAN_SCHEMA,"all":total,"master_pass":len(u),"prefilter":len(pool),"daily_ok":daily_ok,
           "strong_count":len(strong),"candidate_count":len(candidates),"candidate_checked":candidate_checked,
           "source_error":False,"token_status":probe.get("token_status",""),
           "surge_watch":surge,"etf_radar":etf_radar,"data_date":data_date,
           "batch_quote_count":len(quotes),"full_fetch_count":full_fetch_count,"mtf_enabled":True,"retired_score_removed":True,"minute_top_checked":min(3,len(strong))+min(3,len(candidates))}
    _write_scan_meta(data_date,stats)
    return one,candidate,strong,candidate_top3,stats

def candle_svg(df,A=None,B=None,C=None,R=None,trigger=None,bars=120):
    d=df.tail(int(bars)).copy().reset_index(drop=True)
    if d.empty:return ""
    n=len(d); step=8 if n<=130 else 6
    left,right,top,bottom=70,28,28,45
    ph=500
    width=max(900,left+right+n*step)
    height=top+ph+bottom
    lo=float(d.low.min()); hi=float(d.high.max())
    span=max(hi-lo,1.0); pad=span*.07
    ymin,ymax=lo-pad,hi+pad; yr=max(ymax-ymin,1.0)
    def yy(v): return top+(ymax-float(v))/yr*ph
    def xx(i): return left+i*step+step/2
    body=max(3,step-3)
    out=[f'<div style="overflow-x:auto;border:1px solid #343a40;border-radius:10px;background:white;">',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="white"/>']
    for j in range(6):
        pr=ymin+(ymax-ymin)*j/5; y=yy(pr)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e8ebef"/>')
        out.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#5f6875">{pr:,.0f}</text>')
    for i,r in d.iterrows():
        o,h,l,c=[float(r[k]) for k in ("open","high","low","close")]
        x=xx(i); col="#d32f2f" if c>=o else "#1565c0"
        out.append(f'<line x1="{x:.1f}" y1="{yy(h):.1f}" x2="{x:.1f}" y2="{yy(l):.1f}" stroke="{col}" stroke-width="1"/>')
        yt=min(yy(o),yy(c)); bh=abs(yy(c)-yy(o))
        if bh<1.2:
            out.append(f'<line x1="{x-body/2:.1f}" y1="{yt:.1f}" x2="{x+body/2:.1f}" y2="{yt:.1f}" stroke="{col}" stroke-width="1.5"/>')
        else:
            out.append(f'<rect x="{x-body/2:.1f}" y="{yt:.1f}" width="{body:.1f}" height="{bh:.1f}" fill="{col}" stroke="{col}"/>')
    ticks=sorted(set(np.linspace(0,n-1,min(8,n)).astype(int)))
    for i in ticks:
        x=xx(i); lab=pd.Timestamp(d.iloc[i].date).strftime("%Y-%m-%d")
        out.append(f'<text x="{x:.1f}" y="{top+ph+25}" text-anchor="middle" font-size="11" fill="#5f6875">{lab}</text>')
    def mark_date_price(obj,label,color,price_key):
        if not obj:return
        try:
            dt=pd.Timestamp(obj["date"]); price=float(obj[price_key])
            hits=d.index[pd.to_datetime(d.date).dt.normalize()==dt.normalize()].tolist()
            if not hits:return
            i=hits[0]; x=xx(i); y=yy(price)
            out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+ph}" stroke="{color}" stroke-width="1" stroke-dasharray="5 4"/>')
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}"/>')
            out.append(f'<text x="{x+6:.1f}" y="{max(14,y-8):.1f}" font-size="11" font-weight="700" fill="{color}">{label} {price:,.0f}</text>')
        except: pass
    mark_date_price(A,"A","#2e7d32","low")
    mark_date_price(B,"방어저점","#8e24aa","low")
    mark_date_price(C,"C","#ef6c00","low")
    mark_date_price(R,"능선","#6d4c41","high")
    # horizontal entry/current
    if trigger and np.isfinite(trigger):
        y=yy(trigger); out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#00897b" stroke-width="1.2" stroke-dasharray="6 4"/>')
        out.append(f'<text x="{width-right-4}" y="{y-5:.1f}" text-anchor="end" font-size="11" fill="#00897b">반등확인선 {trigger:,.0f}</text>')
    cur=float(d.iloc[-1].close); y=yy(cur)
    out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#455a64" stroke-width="1" stroke-dasharray="3 3"/>')
    out.append(f'<text x="{width-right-4}" y="{y+14:.1f}" text-anchor="end" font-size="11" fill="#455a64">현재 {cur:,.0f}</text>')
    out.append('</svg></div>')
    return "".join(out)


def _pivot_highs(df,r=5):
    vals=df["high"].to_numpy(float); out=[]
    for i in range(r,len(vals)-r):
        if vals[i]>=np.max(vals[i-r:i+r+1]): out.append(i)
    return out

def launch_signal(df):
    """Accessory signal only. Does NOT override ABC or become a mandatory buy rule."""
    d=df.copy().reset_index(drop=True)
    if len(d)<80:return {"grade":"자료부족","score":0,"trend":"없음","volume":"보통","close":"보통","line":None}
    r=d.iloc[-1]; rng=max(float(r.high-r.low),1e-9)
    cp=(float(r.close-r.low)/rng)*100
    vr=float(r.volume/max(d.volume.tail(21).iloc[:-1].mean(),1))
    hs=[i for i in _pivot_highs(d.tail(140).reset_index(drop=True),5)]
    line=None; dist=None; crossed=False
    if len(hs)>=2:
        dd=d.tail(140).reset_index(drop=True)
        pairs=[]
        for a in range(max(0,len(hs)-7),len(hs)-1):
            for b in range(a+1,len(hs)):
                i1,i2=hs[a],hs[b]
                h1,h2=float(dd.iloc[i1].high),float(dd.iloc[i2].high)
                if i2-i1>=8 and h2<h1*.995:
                    slope=(h2-h1)/(i2-i1)
                    proj=h2+slope*((len(dd)-1)-i2)
                    if proj>0:pairs.append((i2,i2-i1,i1,i2,h1,h2,proj,slope))
        if pairs:
            _,_,i1,i2,h1,h2,proj,slope=max(pairs,key=lambda x:(x[0],x[1]))
            dist=(float(r.close)/proj-1)*100
            crossed=bool(float(r.close)>proj)
            line={"proj":proj,"dist":dist,"crossed":crossed}
    score=0
    if vr>=1.5: score+=2
    elif vr>=1.3: score+=1
    if cp>=70: score+=1
    if line and crossed and vr>=1.3: score+=2
    elif line and -4<=dist<=2: score+=1
    grade={0:"약함",1:"관찰",2:"보통",3:"양호",4:"강함",5:"강함"}.get(score,"관찰")
    return {"grade":grade,"score":score,
            "trend":("돌파" if line and crossed else ("접근" if line and -4<=dist<=2 else "미확인")),
            "volume":("강함" if vr>=1.5 else ("증가" if vr>=1.3 else "보통")),
            "close":("고가권" if cp>=70 else "보통"),
            "vr":vr,"cp":cp,"line":line}


@st.cache_data(ttl=900,show_spinner=False)
def investor_flow(code,listed_shares=0):
    # Naver 외국인/기관 표를 5거래일만 읽어 다이어트된 수급 데이터로 반환.
    out={"inst_today":None,"foreign_today":None,"inst_5":None,"foreign_5":None,
         "foreign_hold":None,"foreign_rate":None,"inst_5_pct":None,"foreign_5_pct":None}
    try:
        html=requests.get(f"https://finance.naver.com/item/frgn.naver?code={code}&page=1",headers={"User-Agent":"Mozilla/5.0"},timeout=8).text
        trs=re.findall(r"<tr[^>]*>(.*?)</tr>",html,re.S|re.I); rows=[]
        def p_int(v):
            t=re.sub(r"[^0-9+\-]","",v or "")
            return int(t) if t not in ("","+","-") else 0
        def p_float(v):
            t=re.sub(r"[^0-9+\-.]","",v or "")
            return float(t) if t not in ("","+","-",".") else None
        for tr in trs:
            cells=[re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>",tr,re.S|re.I)]
            if len(cells)>=9 and re.search(r"\d{4}\.\d{2}\.\d{2}",cells[0]):
                try:
                    rows.append({"inst":p_int(cells[5]),"foreign":p_int(cells[6]),"hold":p_int(cells[7]),"rate":p_float(cells[8])})
                except:pass
            if len(rows)>=5:break
        if not rows:return out
        out["inst_today"]=rows[0]["inst"];out["foreign_today"]=rows[0]["foreign"]
        out["inst_5"]=sum(r["inst"] for r in rows);out["foreign_5"]=sum(r["foreign"] for r in rows)
        out["foreign_hold"]=rows[0]["hold"];out["foreign_rate"]=rows[0]["rate"]
        shares=float(listed_shares or 0)
        if shares>0:
            out["inst_5_pct"]=out["inst_5"]/shares*100;out["foreign_5_pct"]=out["foreign_5"]/shares*100
        return out
    except:return out

def _signed_shares(v):
    try:return f"{int(v):+,}주"
    except:return "-"

def _flow_dir(v,pct=None):
    try:v=float(v)
    except:return ("━","0","#9aa0a6")
    if v>0:arrow="▲";color="#ff6666"
    elif v<0:arrow="▼";color="#5b8cff"
    else:arrow="━";color="#9aa0a6"
    txt=f"{pct:+.2f}%" if pct is not None else _signed_shares(v)
    return arrow,txt,color

def flow_summary_html(stock):
    f=investor_flow(stock.get('code',''),stock.get('listed_shares',0))
    fa,fp,fc=_flow_dir(f.get('foreign_5'),f.get('foreign_5_pct'))
    ia,ip,ic=_flow_dir(f.get('inst_5'),f.get('inst_5_pct'))
    fr=f"{f['foreign_rate']:.2f}%" if f.get('foreign_rate') is not None else "-"
    return f'''<div class="flow-card">
      <div class="flow-row"><span class="flow-name">외국인</span><span>보유 <b>{fr}</b></span><span>오늘 <b>{_signed_shares(f.get('foreign_today'))}</b></span><span style="color:{fc};font-weight:900">5일 {fa} {fp}</span></div>
      <div class="flow-row"><span class="flow-name">기관</span><span>오늘 <b>{_signed_shares(f.get('inst_today'))}</b></span><span style="color:{ic};font-weight:900">5일 {ia} {ip}</span></div>
    </div>'''

def company_health(code):
    """Safety screen only: explicit public warning terms -> 위험, otherwise '기본통과'.
       This is deliberately NOT a full audit/financial-quality score."""
    try:
        html=requests.get(f"https://finance.naver.com/item/main.naver?code={code}",headers={"User-Agent":"Mozilla/5.0"},timeout=8).text
        txt=re.sub(r"<[^>]+>"," ",html)
        danger_words=["관리종목","거래정지","상장폐지","자본잠식"]
        hits=[w for w in danger_words if w in txt]
        if hits:return {"status":"위험","reason":"공개화면 위험표시: "+", ".join(hits[:2])}
        caution_words=["유상증자","전환사채","신주인수권"]
        caut=[w for w in caution_words if w in txt]
        if caut:return {"status":"주의","reason":"희석/자금조달 문구 확인: "+", ".join(caut[:2])}
        return {"status":"기본통과","reason":"1차 안전검사 통과 · 상세 재무/공시는 별도 확인"}
    except:return {"status":"확인필요","reason":"기업안전 데이터 확인 실패"}


def overhead_zones(df,cur):
    d=df.tail(420).copy().reset_index(drop=True)
    hs=_pivot_highs(d,5)
    levels=[]
    for i in hs:
        h=float(d.iloc[i].high)
        if h>cur*1.025:
            # cluster near levels within 3%
            levels.append((h,i))
    if not levels:return []
    levels=sorted(levels,key=lambda x:x[0])
    clusters=[]
    for h,i in levels:
        if not clusters or abs(h/clusters[-1][0]-1)>.03:
            clusters.append([h,[i]])
        else:
            clusters[-1][1].append(i)
            clusters[-1][0]=sum(float(d.iloc[j].high) for j in clusters[-1][1])/len(clusters[-1][1])
    return [x[0] for x in clusters[:3]]

def sell_plan(df,cur,ls):
    zones=overhead_zones(df,cur)
    if not zones:return {"upside":None,"rows":[],"label":"계산불가"}
    # Only show actionable overhead zones. A very old/far high must not be presented
    # as an expected return. The 3rd zone can remain as an extension only when structure is strong.
    actionable=[z for z in zones if 1.025 < z/cur <= 1.45]
    if not actionable:return {"upside":None,"rows":[],"label":"상단구간 멂"}
    strength=ls.get("score",0)
    # First two nearby resistance clusters define the practical range.
    use=actionable[:2]
    if strength>=4 and len(actionable)>=3 and actionable[2]/cur<=1.45:
        use=actionable[:3]
    upside=(use[-1]/cur-1)*100
    if strength>=4: alloc=[20,30,50]
    elif strength>=2: alloc=[30,35,35]
    else: alloc=[40,35,25]
    rows=[]
    for k,z in enumerate(use):
        rows.append((f"{k+1}차 수익구간",z,(z/cur-1)*100,alloc[min(k,2)]))
    return {"upside":upside,"rows":rows,"label":"차트상 매도구간"}

st.markdown("""
<style>
@media(max-width:700px){
 .block-container{padding:0.7rem 0.55rem 1.5rem!important;max-width:100%!important}
 .hero{padding:12px!important;border-radius:12px!important}
 .hero-name{font-size:25px!important}
 .hero-badge{font-size:14px!important;padding:6px 9px!important}
 .hero-line{font-size:12px!important}
 .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:6px!important}
 .kpi{padding:9px!important}
 .kpi .label{font-size:10px!important}
 .kpi .value{font-size:17px!important}
 .quick-grid{grid-template-columns:1fr!important;gap:6px!important}
 .future-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .action{font-size:14px!important;padding:10px!important}
 .section-title{font-size:17px!important}
 div[data-testid="stDataFrame"]{font-size:11px!important}
 button{min-height:38px!important}
}
</style>
""",unsafe_allow_html=True)
st.markdown("## 🎯 STOCK COMPASS · ONE")
st.caption("진바닥 후보를 찾고, 최종 판단은 차트로 확인")
st.caption(f"앱 버전: {APP_VERSION} · 굴곡형 10이평 독립 검증 탑재")

with st.expander("선정 기준"):
    st.write("오늘을 제외한 전날~120거래일 전의 가장 깊은 확정 전저점 A. 오늘 저가가 A를 깨지 않고 A~A+3%에 닿은 종목만 후보로 표시합니다.")

st.markdown("**검색범위: KOSPI + KOSDAQ 전체 · KIS 종목마스터 + KIS 일봉** · **현재가 5,000~50,000원** · ETF/ETN/스팩/리츠/우선주·거래정지·관리종목 제외")
st.markdown(_update_status_html(),unsafe_allow_html=True)
n=None
def interactive_candle_chart(df,A=None,B=None,C=None,entry=None,zones=None,projection=None,initial_bars=120):
    import json
    d=df.tail(500).copy(); rows=[]
    for _,r in d.iterrows():
        try:
            rows.append({"t":str(r["date"])[:10],"o":float(r.open),"h":float(r.high),"l":float(r.low),"c":float(r.close),"v":float(r.volume)})
        except:
            pass
    if len(rows)<20:return "<div>차트 데이터 부족</div>"
    marks=[]
    for label,val in [("A 지지선",A),("B",B),("C 다음지지",C),("반등확인선",entry)]:
        try:
            if val is not None and np.isfinite(float(val)):
                marks.append({"label":label,"v":float(val)})
        except:
            pass
    for i,z in enumerate((zones or [])[:2]):
        try:marks.append({"label":f"{i+1}차 수익구간","v":float(z)})
        except:pass
    proj=[]
    for p in (projection or []):
        try:
            if isinstance(p,dict):proj.append({"label":str(p.get("label","")),"v":float(p.get("v"))})
            else:proj.append({"label":"","v":float(p)})
        except:pass
    try:init=max(30,min(int(initial_bars),len(rows)))
    except:init=min(120,len(rows))
    rid="tv_"+str(abs(hash((rows[-1]["t"],rows[-1]["c"],init))))
    return f"""<div id="{rid}" style="width:100%;height:620px;background:#fff;position:relative;border-radius:8px;overflow:hidden">
<div style="position:absolute;z-index:7;top:6px;left:6px;right:6px;display:flex;gap:5px;align-items:center;flex-wrap:wrap;background:rgba(255,255,255,.95);padding:5px 6px;border-radius:7px;border:1px solid #e4e7eb;font:700 12px sans-serif">
<button data-z="in" style="min-width:38px;height:34px;border:1px solid #d0d5dd;border-radius:6px;background:#fff;font-weight:900">＋</button>
<button data-n="30" style="min-width:42px;height:34px;border:1px solid #d0d5dd;border-radius:6px;background:#fff;font-weight:800">30</button>
<button data-n="60" style="min-width:42px;height:34px;border:1px solid #d0d5dd;border-radius:6px;background:#fff;font-weight:800">60</button>
<button data-n="120" style="min-width:48px;height:34px;border:1px solid #d0d5dd;border-radius:6px;background:#fff;font-weight:800">120</button>
<button data-n="250" style="min-width:48px;height:34px;border:1px solid #d0d5dd;border-radius:6px;background:#fff;font-weight:800">250</button>
<button data-z="out" style="min-width:38px;height:34px;border:1px solid #d0d5dd;border-radius:6px;background:#fff;font-weight:900">－</button>
<span style="color:#667085;margin-left:2px">좌우로 밀기 · 버튼 확대</span>
</div>
<canvas style="width:100%;height:100%;touch-action:pan-y"></canvas>
<div class="tip" style="display:none;position:absolute;z-index:8;top:50px;left:7px;right:7px;background:#111;color:#fff;padding:8px;border-radius:5px;font:14px sans-serif;white-space:normal"></div>
</div>
<script>(()=>{{const root=document.getElementById("{rid}"),cv=root.querySelector("canvas"),tip=root.querySelector(".tip"),D={json.dumps(rows,ensure_ascii=False)},M={json.dumps(marks,ensure_ascii=False)},P={json.dumps(proj,ensure_ascii=False)};
let n=Math.min({init},D.length),end=D.length,drag=false,lx=0,ly=0;
function clampN(v){{return Math.max(30,Math.min(D.length,Math.round(v)))}}
function ma(k,i){{if(i<k-1)return null;let q=0;for(let j=i-k+1;j<=i;j++)q+=D[j].c;return q/k}}
function draw(){{
 let r=root.getBoundingClientRect(),dpr=devicePixelRatio||1;cv.width=r.width*dpr;cv.height=r.height*dpr;let x=cv.getContext("2d");x.scale(dpr,dpr);
 let W=r.width,H=r.height,mobile=W<620,L=mobile?46:52,R=P.length?(mobile?92:145):(mobile?62:68),T=58,VH=mobile?70:80,B=mobile?30:24,PH=H-T-VH-B,st=Math.max(0,end-n),a=D.slice(st,end);if(!a.length)return;
 let lo=Math.min(...a.map(q=>q.l)),hi=Math.max(...a.map(q=>q.h));if(P.length){{lo=Math.min(lo,...P.map(p=>p.v));hi=Math.max(hi,...P.map(p=>p.v))}}let pad=(hi-lo)*.08||1;lo-=pad;hi+=pad;
 let yy=v=>T+(hi-v)/(hi-lo)*PH,xx=i=>L+(i+.5)*(W-L-R)/a.length,cw=Math.max(1,(W-L-R)/a.length*.62);
 x.fillStyle="#fff";x.fillRect(0,0,W,H);x.strokeStyle="#e8edf2";x.font=(mobile?"12px":"11px")+" sans-serif";x.fillStyle="#667085";
 for(let k=0;k<6;k++){{let y=T+k*PH/5,val=hi-k*(hi-lo)/5;x.beginPath();x.moveTo(L,y);x.lineTo(W-R,y);x.stroke();x.fillText(Math.round(val).toLocaleString(),W-R+4,y+4)}}
 let mv=Math.max(...a.map(q=>q.v),1);a.forEach((q,i)=>{{let h=q.v/mv*(VH-10);x.fillStyle=q.c>=q.o?"rgba(220,70,70,.32)":"rgba(50,105,220,.32)";x.fillRect(xx(i)-cw/2,T+PH+VH-h,cw,h)}});
 a.forEach((q,i)=>{{let X=xx(i);x.strokeStyle=x.fillStyle=q.c>=q.o?"#df4b4b":"#356fd3";x.beginPath();x.moveTo(X,yy(q.h));x.lineTo(X,yy(q.l));x.stroke();let y1=yy(Math.max(q.o,q.c)),y2=yy(Math.min(q.o,q.c));x.fillRect(X-cw/2,y1,cw,Math.max(1,y2-y1))}});
 [[20,"#f0a000"],[60,"#2b7de9"],[120,"#8a55c5"]].forEach(([k,col])=>{{x.strokeStyle=col;x.lineWidth=mobile?1.6:1.3;x.beginPath();let on=false;a.forEach((q,i)=>{{let v=ma(k,st+i);if(v==null)return;on?x.lineTo(xx(i),yy(v)):(x.moveTo(xx(i),yy(v)),on=true)}});x.stroke()}});
 let used=[];M.forEach((m,i)=>{{if(m.v<lo||m.v>hi)return;let y=yy(m.v);x.setLineDash([5,4]);x.strokeStyle=i%2?"#8b5cf6":"#159570";x.beginPath();x.moveTo(L,y);x.lineTo(W-R,y);x.stroke();x.setLineDash([]);let ty=y-4;while(used.some(u=>Math.abs(u-ty)<16))ty+=16;used.push(ty);x.fillStyle="#20242a";x.font=(mobile?"12px":"11px")+" sans-serif";x.fillText(m.label+" "+Math.round(m.v).toLocaleString(),L+3,ty)}});
 if(P.length){{let x0=xx(a.length-1),pts=[{{x:x0,y:yy(a[a.length-1].c)}}];P.forEach((p,i)=>pts.push({{x:(W-R)+(mobile?20:35)+i*(mobile?30:48),y:yy(p.v),label:p.label,v:p.v}}));x.strokeStyle="#159570";x.lineWidth=2;x.setLineDash([7,5]);x.beginPath();pts.forEach((p,i)=>i?x.lineTo(p.x,p.y):x.moveTo(p.x,p.y));x.stroke();x.setLineDash([]);pts.slice(1).forEach(p=>{{x.fillStyle="#159570";x.beginPath();x.arc(p.x,p.y,4,0,Math.PI*2);x.fill();x.font=(mobile?"11px":"10px")+" sans-serif";x.fillText((p.label||"")+" "+Math.round(p.v).toLocaleString(),Math.min(p.x+4,W-(mobile?88:105)),Math.max(T+8,p.y-6))}})}}
 let step=Math.max(1,Math.floor(a.length/(mobile?4:6)));x.fillStyle="#667085";x.font=(mobile?"12px":"11px")+" sans-serif";for(let i=0;i<a.length;i+=step)x.fillText(a[i].t.slice(2),Math.max(2,xx(i)-22),H-7);root.g={{a,L,R,W,st}}}}
root.querySelectorAll("button[data-n]").forEach(b=>b.addEventListener("click",()=>{{n=clampN(+b.dataset.n);end=D.length;draw()}}));
root.querySelectorAll("button[data-z]").forEach(b=>b.addEventListener("click",()=>{{n=clampN(n+(b.dataset.z==="in"?-20:20));draw()}}));
cv.addEventListener("wheel",e=>{{e.preventDefault();n=clampN(n+(e.deltaY>0?15:-15));draw()}},{{passive:false}});
cv.addEventListener("pointerdown",e=>{{drag=true;lx=e.clientX;ly=e.clientY;try{{cv.setPointerCapture(e.pointerId)}}catch(_e){{}}}});
cv.addEventListener("pointerup",()=>drag=false);cv.addEventListener("pointercancel",()=>drag=false);
cv.addEventListener("pointermove",e=>{{if(drag){{let dx=e.clientX-lx,dy=e.clientY-ly;if(Math.abs(dx)>12&&Math.abs(dx)>Math.abs(dy)){{end=Math.max(n,Math.min(D.length,end-(dx>0?3:-3)));lx=e.clientX;ly=e.clientY;draw()}}return}}
 let g=root.g,r=cv.getBoundingClientRect(),i=Math.floor((e.clientX-r.left-g.L)/(g.W-g.L-g.R)*g.a.length);i=Math.max(0,Math.min(g.a.length-1,i));let q=g.a[i];tip.style.display="block";tip.textContent=`${{q.t}}  시 ${{q.o.toLocaleString()}}  고 ${{q.h.toLocaleString()}}  저 ${{q.l.toLocaleString()}}  종 ${{q.c.toLocaleString()}}  거래량 ${{Math.round(q.v).toLocaleString()}}`; }});
cv.addEventListener("mouseleave",()=>tip.style.display="none");
cv.addEventListener("dblclick",()=>{{n=Math.min(120,D.length);end=D.length;draw()}});
addEventListener("resize",draw);draw();}})();</script>"""

def trend_gauge_7(df):
    """20/60/120일선과 각 방향을 동일가중치로 판단하는 7단계 방향 게이지.
    매수선정 규칙을 바꾸지 않고 화면 요약에만 사용한다.
    """
    try:
        c=df.close.astype(float).dropna()
        if len(c)<125:
            return {"level":3,"label":"중립","score":0,"checks":[]}
        ma20=c.rolling(20).mean()
        ma60=c.rolling(60).mean()
        ma120=c.rolling(120).mean()
        checks=[
            ("현재가 > 20일선", c.iloc[-1] >= ma20.iloc[-1]),
            ("현재가 > 60일선", c.iloc[-1] >= ma60.iloc[-1]),
            ("현재가 > 120일선", c.iloc[-1] >= ma120.iloc[-1]),
            ("20일선 상승", ma20.iloc[-1] >= ma20.iloc[-6]),
            ("60일선 상승", ma60.iloc[-1] >= ma60.iloc[-21]),
            ("120일선 상승", ma120.iloc[-1] >= ma120.iloc[-21]),
        ]
        # 각 조건은 상승이면 +1, 하락이면 -1. 총점 -6~+6.
        score=sum(1 if ok else -1 for _,ok in checks)
        if score>=5: level=6
        elif score>=3: level=5
        elif score>=1: level=4
        elif score==0: level=3
        elif score>=-2: level=2
        elif score>=-4: level=1
        else: level=0
        labels=["강한 하락","하락","약한 하락","중립","약한 상승","상승","강한 상승"]
        return {"level":level,"label":labels[level],"score":score,"checks":checks}
    except:
        return {"level":3,"label":"중립","score":0,"checks":[]}

def gauge_svg_7(info):
    labels=["강한 하락","하락","약한 하락","중립","약한 상승","상승","강한 상승"]
    colors=["#c62828","#e53935","#fb8c00","#8d939b","#8bc34a","#43a047","#1b7f3a"]
    level=int(max(0,min(6,info.get("level",3))))
    cx,cy=350,255
    r1,r2=150,215
    def pt(r,deg):
        a=math.radians(deg)
        return cx+r*math.cos(a), cy-r*math.sin(a)
    segs=[]
    # 180° -> 0°, 7 equal annular wedges.
    for i in range(7):
        a1=180-i*(180/7)
        a2=180-(i+1)*(180/7)
        x1,y1=pt(r2,a1); x2,y2=pt(r2,a2)
        x3,y3=pt(r1,a2); x4,y4=pt(r1,a1)
        path=(f"M {x1:.1f},{y1:.1f} "
              f"A {r2},{r2} 0 0 1 {x2:.1f},{y2:.1f} "
              f"L {x3:.1f},{y3:.1f} "
              f"A {r1},{r1} 0 0 0 {x4:.1f},{y4:.1f} Z")
        opacity="1" if i==level else ".62"
        segs.append(f'<path d="{path}" fill="{colors[i]}" opacity="{opacity}"/>')
        mid=(a1+a2)/2
        tx,ty=pt(238,mid)
        segs.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="11" fill="#dfe3e8">{labels[i]}</text>')
    # needle points at segment center
    deg=180-(level+.5)*(180/7)
    nx,ny=pt(125,deg)
    score=info.get("score",0)
    return f"""
    <div style="border:1px solid #343a40;border-radius:14px;padding:8px 10px 4px;margin:8px 0 12px;background:#111318;">
      <div style="text-align:center;font-size:14px;font-weight:800;color:#dfe3e8;margin-top:3px;">방향 게이지</div>
      <svg viewBox="0 0 700 315" width="100%" style="max-height:270px;display:block;margin:auto;">
        {''.join(segs)}
        <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#ffffff" stroke-width="7" stroke-linecap="round"/>
        <circle cx="{cx}" cy="{cy}" r="14" fill="#ffffff"/>
        <text x="{cx}" y="292" text-anchor="middle" font-size="25" font-weight="900" fill="{colors[level]}">{info.get('label','중립')}</text>
        <text x="{cx}" y="312" text-anchor="middle" font-size="12" fill="#9aa0a6">20·60·120일선 실제 방향 · 점수 {score:+d}</text>
      </svg>
    </div>
    """

def candidate_price_path(cur,stop,confirm,target,status,action=None):
    vals=[float(stop),float(confirm),float(cur),float(target)]
    lo=min(vals); hi=max(vals); span=max(hi-lo,1.0)
    def pos(v):
        return 6 + (float(v)-lo)/span*88
    ps,pe,pc,pt=[pos(v) for v in (stop,confirm,cur,target)]
    if action and action.get("label")=="추격매수 금지":
        badge="🔴 추격매수 금지"
    elif status=="진입준비":
        badge="🟡 진입준비"
    elif status=="반등확인":
        badge="🟠 반등확인"
    elif status=="관망":
        badge="👀 후보 · 관망"
    else:
        badge="👀 후보"
    return f"""
    <div style="border:1px solid #343a40;border-radius:14px;padding:14px 16px;margin:10px 0;background:#15181d;">
      <div style="font-size:21px;font-weight:900;margin-bottom:4px;">{badge}</div>
      <div style="font-size:13px;color:#aab0b7;margin-bottom:15px;">{(action or {}).get('reason','지금 매수 아님 · 반등확인선을 통과하는지 보는 종목')}</div>
      <div style="position:relative;height:92px;margin:0 8px;">
        <div style="position:absolute;left:5%;right:5%;top:39px;border-top:3px dashed #6f7782;"></div>
        <div style="position:absolute;left:{ps:.1f}%;top:22px;height:38px;border-left:3px solid #e53935;"></div>
        <div style="position:absolute;left:{pe:.1f}%;top:19px;height:44px;border-left:4px dashed #f6c344;"></div>
        <div style="position:absolute;left:{pc:.1f}%;top:27px;width:18px;height:18px;border-radius:50%;background:#ffffff;transform:translateX(-9px);box-shadow:0 0 0 4px #455a64;"></div>
        <div style="position:absolute;left:{pt:.1f}%;top:22px;height:38px;border-left:3px dashed #43a047;"></div>
        <div style="position:absolute;left:{ps:.1f}%;top:64px;transform:translateX(-50%);font-size:11px;color:#ef9a9a;">손절<br>{stop:,.0f}</div>
        <div style="position:absolute;left:{pe:.1f}%;top:0px;transform:translateX(-50%);font-size:11px;color:#ffd54f;font-weight:800;">반등확인선<br>{confirm:,.0f}</div>
        <div style="position:absolute;left:{pc:.1f}%;top:64px;transform:translateX(-50%);font-size:11px;color:#fff;font-weight:800;">현재<br>{cur:,.0f}</div>
        <div style="position:absolute;left:{pt:.1f}%;top:0px;transform:translateX(-50%);font-size:11px;color:#81c784;font-weight:800;">계획 목표 (+10%)<br>{target:,.0f}</div>
      </div>
    </div>
    """

def pct_from(base,val):
    try:return (float(val)/float(base)-1)*100
    except:return np.nan

def price_pct(base,val):
    try:return f"{won(val)} ({pct_from(base,val):+.1f}%)"
    except:return "-"

def validation_status_html(df):
    """Evidence card: makes rejected research unable to masquerade as live proof."""
    as_of=str(df.iloc[-1].get("date","-"))[:10] if df is not None and len(df) else "-"
    return f"""
    <div class="card" style="border-color:#4f5d70;">
      <b>🔒 실전 신뢰도 상태</b><br>
      <span class="small">기준일 <b>{as_of}</b> · 실전 BASE: A→B 지지 · 신호 종가 확인 후 다음 거래일 시가 · A 이탈 손절 · 실제 진입가 +10% · 최대 15거래일</span><br>
      <span class="small" style="color:#ffb4a9;">제외: V7 홀드아웃 실패 필터 · V8 파생 5년 점수 (실전 순위 반영 0)</span><br>
      <span class="small" style="color:#b8d7ff;">미검증 연구 규칙·점수는 이 실전판의 ONE·TOP3·오늘 행동에 사용하지 않음</span>
    </div>
    """

def live_entry_action(current, planned_entry, stop, target):
    """Show the action at *today's* price without changing the validated BASE scan.

    The BASE entry/stop/target remain frozen.  This only prevents a plan made at
    one price from being displayed as a buy after price has already moved away.
    """
    cur, entry, sl, tp = map(float, (current, planned_entry, stop, target))
    remaining_up = (tp / cur - 1.0) * 100.0
    remaining_down = (sl / cur - 1.0) * 100.0
    plan_gap = (cur / entry - 1.0) * 100.0
    rr = remaining_up / abs(remaining_down) if remaining_down < 0 else np.nan
    # This does not change the scanner.  It only refuses a fresh order when,
    # at today's price, the remaining target is smaller than the loss to A.
    if cur > entry and np.isfinite(rr) and rr < 1.0:
        return {"label":"추격매수 금지", "cls":"action-stop",
                "reason":"계획 진입가를 이미 넘어 현재가 기준 남은 수익보다 A 손절 위험이 큽니다. 재조정 후 다시 확인합니다.",
                "up":remaining_up, "down":remaining_down, "gap":plan_gap, "rr":rr}
    if cur < entry:
        return {"label":"관망 · 확인선 대기", "cls":"action-wait",
                "reason":"반등확인선 아래입니다. B 지지와 다음 거래일 시가 진입 조건을 기다립니다.",
                "up":remaining_up, "down":remaining_down, "gap":plan_gap, "rr":rr}
    return {"label":"조건 확인 후 진입 검토", "cls":"action-wait",
            "reason":"계획 진입가 부근입니다. 종가 확인 뒤 다음 거래일 시가 조건만 검토합니다.",
            "up":remaining_up, "down":remaining_down, "gap":plan_gap, "rr":rr}

# ---------------------------------------------------------------------------
# Live deep-valley discovery.  This is intentionally separate from the older
# ONE/A→B engine: it finds every chart the user should inspect, and never
# turns a candidate into an automatic buy recommendation.
DEEP_VALLEY_LIVE_DIR=Path("data")/"deep_valley_live"
DEEP_VALLEY_LIVE_STATE=DEEP_VALLEY_LIVE_DIR/"state.json"
DEEP_VALLEY_LIVE_RESULT=DEEP_VALLEY_LIVE_DIR/"candidates.json"
DEEP_VALLEY_LIVE_VERSION="DEEP_VALLEY_CANDIDATES_V1_20260908"

def _deep_valley_state_write(path,obj):
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    except: pass

def _deep_valley_state_read(path):
    try:
        if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
    except: pass
    return {}

def _deep_valley_anchor_current(h):
    """Frozen A rule: find the deepest confirmed A from yesterday back 120 sessions."""
    try:
        h=h.reset_index(drop=True)
        n=len(h); confirmed_end=max(0,n-3)
        if n<125 or confirmed_end<4:return None
        piv=set(_live_pivot_lows(h,3,3))
        # Today is not an anchor.  The pivot's right-side confirmation needs
        # three completed candles, so the very latest three days cannot yet be A.
        start=max(3,confirmed_end-120); end=confirmed_end
        ids=[i for i in piv if start<=i<end]
        if not ids:return None
        ai=min(ids,key=lambda i:float(h.loc[i,"low"]))
        A=float(h.loc[ai,"low"])
        rebound=float(h.iloc[ai+1:-1].high.astype(float).max()/A-1)*100
        if rebound<5.0:return None
        return {"i":int(ai),"date":str(pd.Timestamp(h.loc[ai,"date"]).date()),
                "low":A,"age":int(n-1-ai),"rebound_pct":round(rebound,2),
                "range":"전날~120거래일 전"}
    except Exception:return None

def _independent_a_revisits(hist,A):
    """Count separate returns to A, not consecutive days parked at A."""
    try:
        away=True; count=0
        for low in hist.low.astype(float).tail(60):
            if low>A*1.05: away=True
            elif A<=low<=A*1.03 and away:
                count+=1; away=False
        return count
    except:return 0

def _deep_valley_candidate(stock,h):
    try:
        if h is None or len(h)<155:return None
        ok,_=identity_guard(stock,h)
        if not ok:return None
        row=h.iloc[-1]; Ainfo=_deep_valley_anchor_current(h)
        if not Ainfo:return None
        A=float(Ainfo["low"]); low=float(row.low); close=float(row.close)
        cap=float(krx_ceil_price(A*1.03))
        # The low itself is the hard truth: a single intraday break invalidates.
        if low<A or low>cap or close<=0:return None
        hist=h.iloc[:-1].copy()
        typ=(hist.high.astype(float)+hist.low.astype(float)+hist.close.astype(float))/3
        vol=hist.volume.astype(float).clip(lower=0).tail(120)
        typ=typ.tail(120); total=max(float(vol.sum()),1.0)
        support=float(vol[(typ>=A*.97)&(typ<=A*1.03)].sum()/total)
        return {"code":str(stock["code"]).zfill(6),"name":stock.get("name",""),
                "market":stock.get("market",""),"listed_shares":float(stock.get("listed_shares",0) or 0),
                "date":str(pd.Timestamp(row.date).date()),"current":close,"day_low":low,
                "A":A,"A_date":Ainfo["date"],"A_age":Ainfo["age"],
                "A_range":Ainfo["range"],"A_rebound_pct":Ainfo["rebound_pct"],"entry_cap":cap,
                "distance_pct":round((close/A-1)*100,3),"low_distance_pct":round((low/A-1)*100,3),
                "support_volume_share":round(support*100,2),
                "independent_revisits":_independent_a_revisits(hist,A)}
    except Exception:return None

def _deep_valley_live_worker():
    state={"phase":"SCANNING","done":0,"total":0,"version":DEEP_VALLEY_LIVE_VERSION,"error":""}; _deep_valley_state_write(DEEP_VALLEY_LIVE_STATE,state)
    try:
        u,total,_,_=universe()
        token=kis_access_token() if kis_ready() else ""
        state.update({"total":len(u)}); _deep_valley_state_write(DEEP_VALLEY_LIVE_STATE,state)
        quotes={}
        now=now_kst()
        if token and now.weekday()<5 and now.time()>=dt_time(9,0):
            quotes=_kis_multi_quote([x["code"] for x in u],token=token)
        found=[]
        for i,stock in enumerate(u,1):
            # Stored KIS history is used first.  A missing history is reported by
            # omission rather than silently downloading an endless full universe.
            h=_merge_cached_quote(stock["code"],300,quotes.get(str(stock["code"]).zfill(6)))
            z=_deep_valley_candidate(stock,h)
            if z:found.append(z)
            if i%5==0 or i==len(u):
                state.update({"done":i,"last":stock.get("name",stock["code"]),"heartbeat":now_kst().strftime("%H:%M:%S")}); _deep_valley_state_write(DEEP_VALLEY_LIVE_STATE,state)
        # Only candidates call the external flow page; this keeps the full scan
        # bounded and makes the displayed flow data specific to the final list.
        for z in found:
            f=investor_flow(z["code"],z.get("listed_shares",0))
            for k,v in f.items():z[k]=v
        found.sort(key=lambda z:(z["distance_pct"],z["code"]))
        DEEP_VALLEY_LIVE_DIR.mkdir(parents=True,exist_ok=True)
        _deep_valley_state_write(DEEP_VALLEY_LIVE_RESULT,{"version":DEEP_VALLEY_LIVE_VERSION,"as_of":now_kst().isoformat(),"candidates":found})
        state.update({"phase":"DONE","found":len(found)}); _deep_valley_state_write(DEEP_VALLEY_LIVE_STATE,state)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _deep_valley_state_write(DEEP_VALLEY_LIVE_STATE,state)

def _render_deep_valley_candidates():
    import threading
    st.subheader("🕳️ 전략 1 · 전저점 지지 매수")
    st.caption("전날~120거래일 전의 가장 깊은 확정 전저점 A를 찾고, 오늘 저가가 A를 깨지 않으면서 A~A+3%에 닿은 종목만 표시합니다. 최종 매수 전 차트·공시·시장 상황을 확인하세요.")
    state=_deep_valley_state_read(DEEP_VALLEY_LIVE_STATE) or {"phase":"미실행"}; phase=state.get("phase","미실행")
    st.write(f"상태: **{phase}** · {state.get('done',0)} / {state.get('total',0)}" + (f" · {state.get('last')}" if state.get('last') else ""))
    if phase in ("미실행","DONE","ERROR") and st.button("🕳️ 진바닥 후보 전체 찾기",type="primary",key="deep_valley_live_start"):
        if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
        else:
            threading.Thread(target=_deep_valley_live_worker,daemon=True).start()
            st.success("한 번만 누르시면 됩니다. 전체 종목을 확인한 뒤 후보와 수급을 자동으로 표시합니다.")
            st.rerun()
    if phase=="SCANNING":
        st.info("백그라운드에서 전체 종목을 확인 중입니다. 이 화면은 10초마다 자동 갱신됩니다.")
        st.markdown('<meta http-equiv="refresh" content="10">',unsafe_allow_html=True)
        return
    result=_deep_valley_state_read(DEEP_VALLEY_LIVE_RESULT) if DEEP_VALLEY_LIVE_RESULT.exists() else {}
    rows=result.get("candidates",[]) if isinstance(result,dict) else []
    if phase=="ERROR": st.error(f"후보 검색 오류: {state.get('error','원인 미확인')}")
    if not rows:return
    st.success(f"{len(rows)}개 후보입니다. 가까운 A 순서이며, 어느 것도 자동 매수 대상이 아닙니다.")
    view=[]
    for z in rows:
        view.append({"종목":f"{z['name']} ({z['code']})","현재가":won(z["current"]),"전저점 A":won(z["A"]),
                     "현재/A":f"{z['distance_pct']:+.2f}%","오늘저가/A":f"{z['low_distance_pct']:+.2f}%",
                     "A일자":z["A_date"],"A경과":f"{z['A_age']}일","외국인 보유율":("-" if z.get("foreign_rate") is None else f"{z['foreign_rate']:.2f}%"),
                     "외국인 5일":_signed_shares(z.get("foreign_5")),"기관 5일":_signed_shares(z.get("inst_5"))})
    st.dataframe(pd.DataFrame(view),use_container_width=True,hide_index=True)
    st.caption("외국인 보유수량·보유율, 외국인/기관 당일·5일 순매수는 현재 화면용 참고 데이터입니다. 기관 전체 보유율은 제공 데이터가 없어 표기하지 않습니다.")
    for z in rows:
        with st.expander(f"{z['name']} · A {won(z['A'])} · 현재/A {z['distance_pct']:+.2f}%",expanded=False):
            a,b,c=st.columns(3); a.metric("전저점 A",won(z["A"]),f"{z['A_date']} · {z['A_age']}일 전"); b.metric("오늘 저가",won(z["day_low"]),f"A 대비 {z['low_distance_pct']:+.2f}%"); c.metric("추격 상한",won(z["entry_cap"]),"A+3%")
            st.caption(f"A 탐색 {z['A_range']} · A 이후 반등 {z['A_rebound_pct']:.1f}% · A 부근 거래량 근사 {z['support_volume_share']:.1f}% · 독립 재접근 {z['independent_revisits']}회")
            st.markdown(flow_summary_html(z),unsafe_allow_html=True)
            h=daily(z["code"],300)
            if h is not None and len(h):
                st.markdown(interactive_candle_chart(h,A=z["A"],initial_bars=250),unsafe_allow_html=True)
            st.info("최종 판단: 차트에서 A가 실제 지지인지, 거래량·공시·시장 상황을 직접 확인한 뒤 결정하세요.")

# The older A→B/ONE engine is a failed research path.  Keep its code isolated
# for audit only; it must never render a button, result, or recommendation.
for _legacy_key in ("one","candidate","candidate_top3","qualified","scan_stats"):
    st.session_state.pop(_legacy_key,None)
if False and st.button("🔎 ONE 검색",type="primary",use_container_width=True,key="one_search_v2_main"):
    with st.spinner("선택과 집중 분석 중..."):
        one,candidate,arr,candidate_top3,scan_stats=scan(n)
    st.session_state["one"]=one
    st.session_state["candidate"]=candidate
    st.session_state["candidate_top3"]=candidate_top3
    st.session_state["qualified"]=len(arr)
    st.session_state["scan_stats"]=scan_stats
    st.rerun()

_old_stats=st.session_state.get("scan_stats")
if isinstance(_old_stats,dict) and _old_stats.get("schema")!=APP_SCAN_SCHEMA:
    st.session_state.pop("one",None)
    st.session_state.pop("candidate",None)
    st.session_state.pop("candidate_top3",None)
    st.session_state.pop("qualified",None)
    st.session_state.pop("scan_stats",None)
    st.info("후보 엔진이 업데이트되었습니다. 'ONE 검색'을 다시 눌러 새 기준으로 검색해주세요.")

one=st.session_state.get("one")
candidate=st.session_state.get("candidate")

# 코드 업데이트 전 세션에 남아 있던 옛 ONE 결과는 새 엔진 필드가 없어 오류가 납니다.
# 새 A→B 엔진 결과가 아니면 자동 폐기하고 다시 스캔하게 합니다.
if one is not None:
    _required=("entry","body_pct","confirm_line","A","B","state")
    if not isinstance(one,dict) or any(k not in one for k in _required):
        st.session_state.pop("one",None)
        st.session_state.pop("qualified",None)
        st.session_state.pop("scan_stats",None)
        st.session_state.pop("candidate",None)
        st.session_state.pop("candidate_top3",None)
        one=None
        candidate=None
        st.info("엔진이 업데이트되었습니다. 'ONE 검색'을 다시 눌러주세요.")

if one is not None:

    df=one["df"]; A=one["A"]; B=one["B"]; C=one["C"]; R=one["ridge"]
    cur=float(df.iloc[-1].close)

    def _level(v):
        if isinstance(v,dict):
            for k in ("low","price","value"):
                if k in v:
                    try:return float(v[k])
                    except: pass
        try:return float(v)
        except:return np.nan

    A_price=_level(A); B_price=_level(B); C_price=_level(C)
    name=one["stock"]["name"]

    # 실제 ONE 발견 시점 현재가를 실전 진입 추천가로 사용.
    entry_price=float(one.get("entry",df.iloc[-1].close))
    confirm_line=float(one.get("confirm_line",entry_price))
    trigger=entry_price

    _mtf=one.get("mtf",multi_timeframe_trend(df))
    _min=one.get("minute",{"available":False,"ok":False,"state":"분봉 확인불가","score":0})
    _minute_ok=bool(_min.get("ok",False))
    action_short="진입 추천"
    action_cls="action-buy"
    action_text=(f"진바닥 A→B BASE 통과 · 월봉 {_mtf['monthly']['state']} · 주봉 {_mtf['weekly']['state']} · 분봉 {_min.get('state','참고')}")
    _hero_tail="오늘의 ONE · 분봉은 타이밍 참고"

    st.markdown(f"""
    <div class="hero">
      <div class="hero-top">
        <div>
          <div class="hero-name">🏆 {name}</div>
          <div class="hero-code">{one['stock']['market']} · 종목코드 {one['stock']['code']} · 코드/종목명 검증 통과 · {_hero_tail}</div>
        </div>
        <div class="hero-badge">{action_short}</div>
      </div>
      <div class="hero-line">현재 상태: {one['state']}</div>
      <div class="small">기준일 {str(df.iloc[-1]["date"])[:10]} · 현재가 {won(cur)}</div>
    </div>
    """,unsafe_allow_html=True)
    st.markdown(validation_status_html(df),unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card">
      <b>🧭 다중시간대 판단</b><br>
      <span class="small">
        월봉 <b>{_mtf['monthly']['state']}</b> ({_mtf['monthly']['score']}/6)
        → 주봉 <b>{_mtf['weekly']['state']}</b> ({_mtf['weekly']['score']}/6)
        → 일봉 <b>진바닥 A→B 통과</b>
        → 분봉 <b>{_min.get('state','확인불가')}</b> ({_min.get('score',0)}/5)
      </span>
    </div>
    """,unsafe_allow_html=True)

    _gauge=trend_gauge_7(df)
    st.markdown(gauge_svg_7(_gauge),unsafe_allow_html=True)

    _tb=one.get("true_bottom",A if isinstance(A,dict) else {}) or {}
    _sup=one.get("supply",{}) or {}
    _sw=",".join(str(x) for x in _tb.get("support_windows",[])) or str(_tb.get("base_window","-"))
    _wall=(won(_sup.get("wall_price")) if _sup.get("wall_price") else "-")
    st.markdown(f"""
    <div class="card">
      <b>🕳️ 진바닥 → 📦 상단 매물대</b><br>
      <span class="small">진바닥 A <b>{won(A_price)}</b> · {_tb.get('state','확인')} · 경과 {_tb.get('age','-')}거래일 · 저점계층 {_sw}일<br>
      +10% 구간 매물 <b>{_sup.get('state','확인불가')}</b> · 누적 {_sup.get('zone_share',0):.1f}% · 가장 두꺼운 벽 {_wall}</span>
    </div>
    """,unsafe_allow_html=True)

    c_price=won(cur); a_price=won(A_price); trig=won(trigger)
    r_price=won(R["high"]) if R else "-"
    c_price2=won(C_price) if C else "-"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi"><div class="label">현재가</div><div class="value">{c_price}</div></div>
      <div class="kpi"><div class="label">반등확인선</div><div class="value">{won(confirm_line)}</div></div>
      <div class="kpi"><div class="label">진바닥 A</div><div class="value">{a_price}</div></div>
      <div class="kpi"><div class="label">상단 저항</div><div class="value">{r_price}</div></div>
      <div class="kpi"><div class="label">하단 C</div><div class="value">{c_price2}</div></div>
    </div>
    <div class="action {action_cls}">👉 지금 행동: {action_text}</div>
    """,unsafe_allow_html=True)

    ls=launch_signal(df)
    st.markdown(f"""
    <div class="card">
      <b>🚀 상승출발 보조신호 · {ls['grade']}</b><br>
      <span class="small">거래량 {ls['volume']} · 종가 {ls['close']} · 하락추세선 {ls['trend']} · 점수 {ls['score']}/5</span>
    </div>
    """,unsafe_allow_html=True)

    health=company_health(one["stock"]["code"])
    st.markdown(f"""
    <div class="quick-grid">
      <div class="quick"><b>기업 안전</b><span>{health['status']}</span><div class="small">{health['reason']}</div></div>
    </div>
    """,unsafe_allow_html=True)
    st.markdown(flow_summary_html(one["stock"]),unsafe_allow_html=True)

    # 5-second synthesis: descriptive, not a fake probability.
    flags=[]
    if one["state"].startswith("A"): flags.append("진바닥 A지지")
    if ls["score"]>=3: flags.append("출발신호 양호")
    _flow=investor_flow(one["stock"]["code"],one["stock"].get("listed_shares",0))
    if (_flow.get("inst_5") or 0)>0 and (_flow.get("foreign_5") or 0)>0: flags.append("수급 동반")
    bt=one.get("bigtrend",big_trend_gate(df))
    buy_reasons=(["큰 추세 회복"] if bt["state"]=="상승/회복" else [])
    wait_reasons=([] if bt["state"]=="상승/회복" else ["큰 추세 중립"])
    if one["state"].startswith("A"): buy_reasons.append("진바닥 A 지지")
    else: wait_reasons.append("저점 재확인")
    if ls["score"]>=3: buy_reasons.append("출발신호 양호")
    else: wait_reasons.append("출발신호 부족")
    why_buy=" + ".join(buy_reasons[:3]) if buy_reasons else "확실한 매수근거 부족"
    why_wait=" · ".join(wait_reasons[:3]) if wait_reasons else "치명적 탈락사유 없음"
    core_ok = (
        bt.get("ok",False)
        and one["state"].startswith(("A","B"))
        and health["status"] not in ("위험","확인필요")
    )
    if health["status"]=="위험": decision="탈락"
    elif health["status"] in ("주의","확인필요"): decision="대기/확인"
    elif core_ok and one["state"].startswith("A") and ls["score"]>=3 and _minute_ok: decision="진입 검토"
    elif core_ok and one["state"].startswith("A") and not _minute_ok: decision="분봉 대기"
    elif one["state"].startswith(("A","B")): decision="대기/관찰"
    else: decision="대기"

    _target=krx_ceil_price(trigger*1.10)
    _stop_pct=(A_price/trigger-1)*100
    st.markdown('<div class="section-title">추천 가격</div>',unsafe_allow_html=True)
    _c1,_c2,_c3=st.columns(3)
    _c1.metric("진입 추천",won(trigger))
    _c2.metric("익절 추천",won(_target),"+10.0%")
    _c3.metric("손절",won(A_price),f"{_stop_pct:.1f}%")
    st.caption(f"진입 {won(trigger)} → 익절 {won(_target)} (+10.0%) / 손절 {won(A_price)} ({_stop_pct:.1f}%)")

    st.markdown('<div class="section-title">차트</div>',unsafe_allow_html=True)
    _cc=df.close.astype(float)

    bars=st.radio("차트 기간",options=[60,120,250],index=1,horizontal=True,key="one_bars")
    _zones_chart=overhead_zones(df,cur)
    _idf=df.tail(max(250,bars)).copy()
    st.components.v1.html(
        interactive_candle_chart(
            _idf,
            A=A_price if A else None,
            B=B_price if B else None,
            C=C_price if C else None,
            entry=confirm_line,
            zones=_zones_chart[:2],
            initial_bars=bars,
        ),
        height=640,
        scrolling=False,
    )
    st.caption("📱 모바일: 차트 위 30/60/120/250 또는 ＋/－로 확대·축소 · 차트를 좌우로 밀어 과거 이동 · PC는 휠 확대 가능")
    with st.expander("기존 고정 차트 보기"):
        svg=candle_svg(df,A=A,B=B,C=C,R=R,trigger=confirm_line,bars=bars)
        if svg:
            st.markdown(svg,unsafe_allow_html=True)

    st.markdown('<div class="section-title">⑤ 오늘 한 줄</div>',unsafe_allow_html=True)
    if one["state"].startswith("A"):
        st.success(f"{name}: 진바닥 A→B BASE 통과. 현재가 {won(trigger)} 기준 진입 검토 · 진바닥 A {won(A_price)} 이탈 시 손절 · 분봉은 타이밍 참고.")
    elif one["state"].startswith("B"):
        st.warning(f"{name}: A {won(A_price)} 주변 B플랜. 지금은 추격보다 회복 확인이 먼저.")
    else:
        st.info(f"{name}: 아직 진입하지 않고 기다립니다.")
elif candidate is not None:
    df=candidate["df"]
    A=candidate["A"]; B=candidate["B"]; R=candidate["ridge"]
    cur=float(df.iloc[-1].close)
    name=candidate["stock"]["name"]
    desired=float(candidate["desired_entry"])  # 내부 변수명 유지, 화면에서는 반등확인선
    target=float(candidate["target"])
    stop=float(candidate["stop"])
    status=candidate.get("candidate_status","후보")
    raw_status=candidate.get("raw_candidate_status","후보")
    gap=float(candidate.get("gap_pct",0))
    mode=candidate.get("candidate_mode","AB")
    live_action=live_entry_action(cur,desired,stop,target)
    display_status=live_action["label"] if live_action["label"]=="추격매수 금지" else status
    if display_status=="추격매수 금지":
        badge="🔴 추격매수 금지"
    elif status=="진입준비":
        badge="🟡 진입준비"
    elif status=="반등확인":
        badge="🟠 반등확인"
    elif status=="관망":
        badge="👀 후보 · 관망"
    else:
        badge="👀 후보"

    st.markdown(f"""
    <div class="hero">
      <div class="hero-top">
        <div>
          <div class="hero-name">{badge} · {name}</div>
          <div class="hero-code">{candidate['stock']['market']} · 종목코드 {candidate['stock']['code']} · 오늘의 최우선 후보</div>
        </div>
        <div class="hero-badge">{display_status}</div>
      </div>
      <div class="hero-line">{live_action['reason']}{(" · 관망용 저점 후보" if mode=="WATCH" else "")}</div>
      <div class="small">현재가 {won(cur)} · 반등확인선 {won(desired)} · 확인선 대비 {gap:+.1f}%</div>
    </div>
    """,unsafe_allow_html=True)
    st.markdown(validation_status_html(df),unsafe_allow_html=True)

    _cmtf=candidate.get("mtf",multi_timeframe_trend(df))
    _cmin=candidate.get("minute",{"state":"분봉 확인불가","score":0})
    st.markdown(f"""
    <div class="card">
      <b>🧭 다중시간대 판단</b><br>
      <span class="small">
        월봉 <b>{_cmtf['monthly']['state']}</b> ({_cmtf['monthly']['score']}/6)
        → 주봉 <b>{_cmtf['weekly']['state']}</b> ({_cmtf['weekly']['score']}/6)
        → 일봉 <b>{status}</b>
        → 분봉 <b>{_cmin.get('state','확인불가')}</b> ({_cmin.get('score',0)}/5)
      </span>
    </div>
    """,unsafe_allow_html=True)

    _tb=candidate.get("true_bottom",A) or {}
    _bs=candidate.get("b_support",{}) or {}
    _sup=candidate.get("supply",{}) or {}
    _sw=",".join(str(x) for x in _tb.get("support_windows",[])) or str(_tb.get("base_window","-"))
    _wall=(won(_sup.get("wall_price")) if _sup.get("wall_price") else "-")
    _audit=_tb.get("audit",{}) or {}
    _adate=str(_tb.get("date","-"))[:10]
    _bdate=str((candidate.get("B") or {}).get("date","-"))[:10]
    st.markdown(f"""
    <div class="card">
      <b>🕳️ 진바닥 → B 지지매물 → 상단저항</b><br>
      <span class="small">
      A <b>{won(stop)}</b> · {_tb.get('state','확인')} · A일자 {_adate} · 경과 {_tb.get('age','-')}거래일<br>
      A 검수: 최근 {_audit.get('recent_excluded_sessions','-')}봉 제외 · {_audit.get('used_range','확인불가')} ({_audit.get('first_range_start','-')} ~ {_audit.get('first_range_end','-')}) · B일자 {_bdate}<br>
      B 지지매물 <b>{_bs.get('state','확인불가')}</b> · B주변 거래비중 {_bs.get('zone_share',0):.1f}% · 접촉 {_bs.get('touch_share',0):.1f}%<br>
      +10% 상단저항 <b>{_sup.get('state','확인불가')}</b> · 누적 {_sup.get('zone_share',0):.1f}% · 최대벽 {_wall}
      </span>
    </div>
    """,unsafe_allow_html=True)

    _gauge=trend_gauge_7(df)
    st.markdown(gauge_svg_7(_gauge),unsafe_allow_html=True)
    st.markdown(candidate_price_path(cur,stop,desired,target,status,live_action),unsafe_allow_html=True)
    st.markdown(flow_summary_html(candidate["stock"]),unsafe_allow_html=True)

    st.markdown('<div class="section-title">후보 가격</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("현재가",won(cur))
    c2.metric("반등확인선",won(desired),f"{(desired/cur-1)*100:+.1f}%")
    c3.metric("손절 (현재가 기준)",won(stop),f"{live_action['down']:.1f}%")
    c4.metric("목표 (현재가 기준)",won(target),f"{live_action['up']:+.1f}%")
    rr_text=f"{live_action['rr']:.2f} : 1" if np.isfinite(live_action['rr']) else "계산불가"
    st.markdown(f'<div class="action {live_action["cls"]}">👉 오늘 행동: <b>{live_action["label"]}</b><br><span class="small">현재가 기준 손익비 {rr_text} · 계획 진입가 대비 {live_action["gap"]:+.1f}%</span></div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">후보 차트</div>',unsafe_allow_html=True)
    bars=st.radio("차트 기간",options=[60,120,250],index=1,horizontal=True,key="candidate_bars")
    st.components.v1.html(
        interactive_candle_chart(
            df.tail(max(250,bars)).copy(),
            A=float(A["low"]),
            B=float(B["low"]),
            C=None,
            entry=desired,
            zones=overhead_zones(df,desired)[:2],
            projection=None,
            initial_bars=bars,
        ),
        height=640,
        scrolling=False,
    )
    st.caption("📱 모바일 차트는 위 버튼으로 확대·축소 · 반등확인선 통과 후 최종 조건 충족 시 강력추천 승격 · 실제 익절가는 실제 진입가 기준 +10%")

    if live_action["label"]=="추격매수 금지":
        st.error(f"{name}: 계획 진입가 {won(desired)}를 지나 현재가에서의 남은 목표는 {live_action['up']:+.1f}%, 손절까지는 {live_action['down']:.1f}%입니다. 지금 매수하지 않고 재조정을 기다립니다.")
    elif status=="진입준비":
        st.warning(f"{name}: 반등확인선 {won(desired)} 부근입니다. 방향과 최종 반등 조건까지 통과하면 강력추천으로 승격합니다.")
    elif status=="반등확인":
        st.warning(f"{name}: 반등확인선 아래입니다. 바로 매수하지 않고 A {won(stop)}를 지키며 {won(desired)}를 회복하는지 확인합니다.")
    elif status=="관망":
        _why=[]
        if candidate.get("stale_bottom"): _why.append("진바닥이 오래됨")
        if candidate.get("b_support",{}).get("state")=="약함": _why.append("B 지지매물대가 약함")
        if candidate.get("supply",{}).get("state")=="두꺼움": _why.append("+10% 구간 상단저항이 두꺼움")
        if not _why: _why.append("큰 방향이 아직 약함")
        st.info(f"{name}: " + " · ".join(_why) + ". 지금은 관망합니다.")
    else:
        st.info(f"{name}: 오늘의 후보입니다. 현재는 추격하지 않고 반등확인선 {won(desired)}을 기다립니다.")

elif "one" in st.session_state:
    _ss=st.session_state.get("scan_stats",{})
    if _ss.get("source_error"):
        _stage=_ss.get("error_stage","KIS")
        _err=_ss.get("error","확인 필요")
        _tok=_ss.get("token_status","")
        st.error(f"KIS {_stage} 실패 · {_err}" + (f" · 토큰 {_tok}" if _tok else ""))
    elif _ss:
        st.warning(f"오늘 강력추천/후보 없음 · 전체 {_ss.get('all',0):,} / 마스터 {_ss.get('master_pass',0):,} / KIS일봉 {_ss.get('daily_ok',0):,} / 1차 {_ss.get('prefilter',0):,} / 후보검사 {_ss.get('candidate_checked',0):,} / 후보 {_ss.get('candidate_count',0):,}")
    else:
        st.warning("오늘 ONE 없음")



# ---------------- V3 AI 미래발굴 엔진 ----------------
FUTURE_CACHE_FILE=Path("data")/"future_discovery_web_v2.json"

def _future_cache_read():
    try:
        if FUTURE_CACHE_FILE.exists():
            d=json.loads(FUTURE_CACHE_FILE.read_text(encoding="utf-8"))
            return d if isinstance(d,dict) else {}
    except:pass
    return {}

def _future_cache_write(d):
    try:
        FUTURE_CACHE_FILE.parent.mkdir(parents=True,exist_ok=True)
        FUTURE_CACHE_FILE.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    except:pass

def _future_ai_config():
    key=_secret("OPENAI_API_KEY","OPENAI_KEY")
    model=_secret("OPENAI_MODEL",default="gpt-5.6-sol") or "gpt-5.6-sol"
    return key,model

def _responses_output_text(js):
    try:
        if isinstance(js.get("output_text"),str) and js.get("output_text").strip():
            return js["output_text"].strip()
        parts=[]
        for item in js.get("output",[]) or []:
            if not isinstance(item,dict) or item.get("type")!="message":continue
            for c in item.get("content",[]) or []:
                if isinstance(c,dict) and c.get("type") in ("output_text","text") and c.get("text"):
                    parts.append(str(c.get("text")))
        return "\n".join(parts).strip()
    except:return ""

def _responses_sources(js):
    out=[];seen=set()
    try:
        for item in js.get("output",[]) or []:
            if not isinstance(item,dict):continue
            if item.get("type") in ("web_search_call","web_search"):
                action=item.get("action") or {}
                for z in action.get("sources",[]) or []:
                    if not isinstance(z,dict):continue
                    url=str(z.get("url") or z.get("link") or "").strip()
                    title=str(z.get("title") or z.get("name") or url).strip()
                    if url and url not in seen:
                        seen.add(url);out.append({"title":title[:120],"url":url})
            if item.get("type")=="message":
                for c in item.get("content",[]) or []:
                    for a in (c.get("annotations",[]) if isinstance(c,dict) else []):
                        if not isinstance(a,dict):continue
                        url=str(a.get("url") or (a.get("url_citation") or {}).get("url") or "").strip()
                        title=str(a.get("title") or (a.get("url_citation") or {}).get("title") or url).strip()
                        if url and url not in seen:
                            seen.add(url);out.append({"title":title[:120],"url":url})
    except:pass
    return out[:12]

def _json_object_from_text(txt):
    t=(txt or "").strip()
    t=re.sub(r"^```(?:json)?\s*","",t,flags=re.I)
    t=re.sub(r"\s*```$","",t)
    a=t.find("{");b=t.rfind("}")
    if a<0 or b<=a:return None
    try:return json.loads(t[a:b+1])
    except:return None

def _ai_web_future_research():
    key,model=_future_ai_config()
    if not key:
        return {"ok":False,"error":"OPENAI_API_KEY 없음","model":model}
    today=now_kst().strftime("%Y-%m-%d")
    prompt=f"""
오늘은 {today}, 한국 시간이다.
너는 STOCK COMPASS의 'AI 미래발굴 참모'다. 반드시 웹 검색을 사용해 최신 자료를 확인한다.

목표:
- 최근 7일 뉴스와 최근 30일의 흐름을 함께 보고 한국 증시에서 앞으로 관심이 커질 가능성이 있는 산업/기술/정책/수주/설비투자 흐름을 발굴한다.
- 이미 단기 급등한 테마를 뒤쫓는 것이 아니라, 수요·투자·정책·수주가 이제 커지기 시작하는 2차/3차 수혜 연결고리를 우선한다.
- 루머, 단순 정치 테마, 근거 없는 종목 연결은 제외한다.
- 후보 회사는 KOSPI/KOSDAQ의 일반 상장사만 적고 ETF/ETN/스팩/리츠/우선주는 제외한다.
- 회사명을 자신 있게 연결할 근거가 없으면 억지로 회사명을 쓰지 않는다.
- 매수 추천을 하지 않는다. '미래발굴 → 차트/재무 검증 → ONE 승격 대기'를 위한 선행 발굴이다.

최종 답변은 반드시 JSON 객체 하나만 출력한다. 설명문/마크다운/코드펜스는 절대 출력하지 않는다.
형식:
{{
  "market_flow":"최근 시장/산업 흐름을 2문장 이내",
  "themes":[
    {{
      "theme":"테마명",
      "stage":"초기|확산|성숙",
      "confidence":0,
      "why_now":"왜 지금 중요한지 1문장",
      "catalysts":["근거1","근거2"],
      "companies":["정확한 한국 상장사명"]
    }}
  ],
  "avoid":["과열 또는 주의할 흐름"]
}}
themes는 최대 5개, companies는 테마당 최대 5개, confidence는 0~100 정수.
"""
    payload={
        "model":model,
        "reasoning":{"effort":"low"},
        "tools":[{"type":"web_search_preview","search_context_size":"medium"}],
        "tool_choice":"auto",
        "include":["web_search_call.action.sources"],
        "input":[{"role":"user","content":[{"type":"input_text","text":prompt}]}],
        "max_output_tokens":3200,
        "store":False,
    }
    try:
        r=requests.post("https://api.openai.com/v1/responses",
                        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                        json=payload,timeout=75)
        try:js=r.json()
        except:js={}
        if r.status_code!=200:
            msg=(js.get("error") or {}).get("message") if isinstance(js,dict) else ""
            return {"ok":False,"error":f"OpenAI HTTP {r.status_code} · {str(msg or r.text[:180])[:180]}","model":model}
        txt=_responses_output_text(js)
        obj=_json_object_from_text(txt)
        if not isinstance(obj,dict):
            return {"ok":False,"error":"AI 응답 JSON 해석 실패","model":model}
        themes=obj.get("themes") or []
        if not isinstance(themes,list):themes=[]
        clean=[]
        for th in themes[:5]:
            if not isinstance(th,dict):continue
            name=str(th.get("theme","")).strip()
            if not name:continue
            try:conf=max(0,min(100,int(float(th.get("confidence",0) or 0))))
            except:conf=0
            companies=[str(x).strip() for x in (th.get("companies") or []) if str(x).strip()][:5]
            clean.append({
                "theme":name[:50],
                "stage":str(th.get("stage","초기"))[:10],
                "confidence":conf,
                "why_now":str(th.get("why_now","")).strip()[:220],
                "catalysts":[str(x).strip()[:140] for x in (th.get("catalysts") or []) if str(x).strip()][:3],
                "companies":companies,
            })
        return {"ok":True,"model":model,"market_flow":str(obj.get("market_flow","")).strip()[:500],
                "themes":clean,"avoid":[str(x).strip()[:140] for x in (obj.get("avoid") or []) if str(x).strip()][:4],
                "sources":_responses_sources(js)}
    except Exception as e:
        return {"ok":False,"error":f"AI 요청 실패 · {str(e)[:160]}","model":model}

def _norm_company_name(name):
    return re.sub(r"[^0-9A-Za-z가-힣]","",str(name or "")).upper()

def _future_technical(stock,theme,confidence,why_now):
    try:
        df=daily(stock["code"],260)
        if df is None or len(df)<140:return None
        c=df.close.astype(float);v=df.volume.astype(float)
        cur=float(c.iloc[-1])
        if not (5000<=cur<=50000):return None
        r5=(cur/float(c.iloc[-6])-1)*100 if len(c)>=6 else 0
        r20=(cur/float(c.iloc[-21])-1)*100 if len(c)>=21 else 0
        r60=(cur/float(c.iloc[-61])-1)*100 if len(c)>=61 else 0
        low120=float(df.tail(120).low.astype(float).min())
        low_dist=(cur/low120-1)*100 if low120>0 else 999
        base_vol=float(v.iloc[-25:-5].mean()) if len(v)>=25 else float(v.tail(20).mean())
        recent_vol=float(v.tail(5).mean())
        vr=recent_vol/max(base_vol,1.0)
        bt=big_trend_gate(df)
        bt_score=int(bt.get("score",0))
        overheat=bool(r5>=15 or r20>=30)

        tech=0.0
        if low_dist<=12:tech+=18
        elif low_dist<=20:tech+=15
        elif low_dist<=35:tech+=9
        elif low_dist<=50:tech+=4
        tech+=max(0,min(20,bt_score*4))
        if 1.15<=vr<=3.5:tech+=min(12,(vr-1)*8)
        elif vr>3.5:tech+=5
        if -8<=r20<=18:tech+=8
        elif 18<r20<30:tech+=4
        if -12<=r60<=30:tech+=5
        if overheat:tech-=22

        total=max(0,min(100,float(confidence)*0.52+tech))
        if overheat:stage="과열 제외"
        elif bt_score>=4 and vr>=1.15:stage="추적 강화"
        elif bt_score>=3:stage="추적"
        else:stage="초기 관심"

        z=dict(stock);z["_df"]=df
        one_now=analyze_one(z)
        cand_now=None if one_now else analyze_candidate(z)
        if one_now:one_stage="🔥 ONE 조건"
        elif cand_now:one_stage={"진입준비":"🟡 진입준비","반등확인":"🟠 반등확인","관망":"👀 관망"}.get(cand_now.get("candidate_status"),"👀 후보")
        else:one_stage="🌱 미래발굴"

        return {"code":stock["code"],"name":stock["name"],"market":stock["market"],
                "theme":theme,"why_now":why_now,"ai_confidence":int(confidence),
                "score":round(total,1),"stage":stage,"one_stage":one_stage,
                "current":cur,"r5":round(r5,1),"r20":round(r20,1),"r60":round(r60,1),
                "low120_dist":round(low_dist,1),"volume_ratio":round(vr,2),
                "bigtrend_score":bt_score,"overheat":overheat,
                "date":str(df.iloc[-1].date)[:10]}
    except:return None

def run_future_discovery():
    today=now_kst().strftime("%Y-%m-%d")
    old=_future_cache_read()
    # 비용 통제: "성공한 동일 엔진 결과"만 하루 1회 잠금.
    # 이전 버전의 실패 캐시/JSON-mode 오류 캐시는 잠금에 사용하지 않는다.
    if (old.get("date")==today and old.get("attempted") and old.get("ok")
        and old.get("ai_schema")==FUTURE_AI_SCHEMA):
        old["daily_locked"]=True
        return old

    ai=_ai_web_future_research()
    if not ai.get("ok"):
        # API 오류는 비용성공으로 보지 않는다. 수정 후 같은 날 다시 시도할 수 있게 잠그지 않음.
        fail={"ok":False,"date":today,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M:%S"),
              "version":"V4_MTF_AI_CACHEFIX1","ai_schema":FUTURE_AI_SCHEMA,
              "attempted":False,"daily_locked":False,
              "error":ai.get("error","AI 분석 실패"),"model":ai.get("model","")}
        _future_cache_write(fail)
        return fail

    main,total,low_watch,etfs=universe()
    # exact/normalized KIS master match only: AI가 만든 존재하지 않는 종목명은 자동 폐기
    pool=main + low_watch
    exact={str(x.get("name","")).strip():x for x in pool}
    norm={}
    for x in pool:
        k=_norm_company_name(x.get("name",""))
        if k and k not in norm:norm[k]=x

    found=[]
    for th in ai.get("themes",[])[:5]:
        theme=th.get("theme","")
        conf=int(th.get("confidence",0) or 0)
        why=th.get("why_now","")
        for nm in th.get("companies",[])[:5]:
            stock=exact.get(nm) or norm.get(_norm_company_name(nm))
            if not stock:continue
            z=_future_technical(stock,theme,conf,why)
            if z:found.append(z)

    # 같은 종목이 여러 테마에 걸리면 가장 높은 점수만 유지
    uniq={}
    for z in found:
        k=z["code"]
        if k not in uniq or z["score"]>uniq[k]["score"]:uniq[k]=z
    ranked=sorted(uniq.values(),key=lambda z:(z["overheat"],-z["score"],z["low120_dist"]))

    # 기업 안전은 최종 상위 후보에만 확인해 속도/호출량 절약
    top=[]
    excluded=[]
    for z in ranked:
        if z.get("overheat"):
            excluded.append(z);continue
        h=company_health(z["code"])
        z["health_status"]=h.get("status","확인필요")
        z["health_reason"]=h.get("reason","")
        if z["health_status"]=="위험":
            excluded.append(z);continue
        top.append(z)
        if len(top)>=3:break

    result={"ok":True,"date":today,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M:%S"),
            "version":"V4_MTF_AI_CACHEFIX1","ai_schema":FUTURE_AI_SCHEMA,
            "attempted":True,"daily_locked":True,
            "model":ai.get("model",""),"market_flow":ai.get("market_flow",""),
            "themes":ai.get("themes",[]),"candidates":top,
            "excluded_count":len(excluded),"sources":ai.get("sources",[])[:8],"avoid":ai.get("avoid",[])}
    _future_cache_write(result)
    return result

def _future_status_html():
    key,model=_future_ai_config()
    cached=_future_cache_read()
    today=now_kst().strftime("%Y-%m-%d")
    if not key:
        return f'<div class="ai-status">🤖 AI 미래발굴 <b>미연결</b> · Streamlit Secrets에 <b>OPENAI_API_KEY</b>가 필요합니다. · 기본 모델 {model}</div>'
    if (cached.get("date")==today and cached.get("attempted") and cached.get("ok")
        and cached.get("ai_schema")==FUTURE_AI_SCHEMA):
        t=str(cached.get("updated_at",""))
        return f'<div class="ai-status">🔒 오늘 AI 미래발굴 1회 사용 완료 · {model} · <b>{t[:16] or "-"}</b> · 내일 다시 사용 가능</div>'
    return f'<div class="ai-status">🤖 AI 연결됨 · {model} · 오늘 1회 분석 가능</div>'

def _future_optional_error_message(error):
    """선택 기능의 결제/할당량 문제를 핵심 ONE 엔진 오류와 분리한다."""
    msg=str(error or "AI 미래발굴 실패")
    low=msg.lower()
    quota=any(x in low for x in ["no credits", "insufficient_quota", "billing", "http 429"])
    if quota:
        return "AI 미래발굴만 일시중지 · API 잔액을 충전하면 다시 사용할 수 있습니다. ONE 검색과 KIS 검증은 정상 작동합니다.", True
    return msg, False

def _render_future_discovery():
    st.markdown('<div class="section-title">🌱 AI 미래발굴</div>',unsafe_allow_html=True)
    st.caption("뉴스·산업·정책 흐름을 AI가 먼저 찾고 KIS로 재검증합니다. · 하루 1회 실행 · 같은 날 재실행 차단")
    st.markdown(_future_status_html(),unsafe_allow_html=True)

    key,_model=_future_ai_config()
    today=now_kst().strftime("%Y-%m-%d")
    cached_today=_future_cache_read()
    used_today=bool(
        cached_today.get("date")==today and cached_today.get("attempted")
        and cached_today.get("ok") and cached_today.get("ai_schema")==FUTURE_AI_SCHEMA
    )
    run=st.button(
        "🔒 오늘 분석 완료" if used_today else "🌱 AI 미래발굴 분석",
        use_container_width=True,
        key="future_ai_v3_run",
        disabled=(not bool(key)) or used_today
    )
    if run:
        with st.spinner("최신 뉴스·산업 흐름 검색 → AI 분석 → KIS 차트 검증 중..."):
            res=run_future_discovery()
        st.session_state["future_discovery"]=res
        st.rerun()

    res=st.session_state.get("future_discovery")
    if isinstance(res,dict) and res.get("ai_schema")!=FUTURE_AI_SCHEMA:
        st.session_state.pop("future_discovery",None)
        res=None
    if not res:
        res=_future_cache_read()
    if isinstance(res,dict) and res.get("ai_schema")!=FUTURE_AI_SCHEMA:
        res={}
    if not key:
        st.info("KIS만으로는 뉴스의 의미를 해석할 수 없어 AI 미래발굴만 별도 API 연결이 필요합니다.")
        return
    if not res:return
    if not res.get("ok"):
        msg,optional_pause=_future_optional_error_message(res.get("error","AI 미래발굴 실패"))
        if optional_pause:
            st.info(msg)
        else:
            st.warning(f"선택 기능 오류 · {msg}")
        return

    if res.get("market_flow"):
        st.markdown(f'<div class="card"><b>오늘의 큰 흐름</b><br><span class="small">{res["market_flow"]}</span></div>',unsafe_allow_html=True)

    cands=res.get("candidates") or []
    if not cands:
        st.warning("AI가 흐름은 찾았지만 KIS 종목/차트/기업안전 검증까지 통과한 미래발굴주는 없습니다.")
    for i,z in enumerate(cands,1):
        health=z.get("health_status","확인필요")
        htxt=f'{health}' + (f' · {z.get("health_reason","")}' if z.get("health_reason") else "")
        st.markdown(f"""
        <div class="future-card">
          <div class="future-rank">🌱 미래발굴 {i}위 · {z["name"]}</div>
          <div class="future-theme">{z["theme"]} · AI 흐름확신 {z["ai_confidence"]}% · 종합 {z["score"]:.1f}점</div>
          <div style="font-size:13px;margin-bottom:6px;">{z["why_now"]}</div>
          <div class="future-grid">
            <div class="future-kpi"><b>현재 단계</b><span>{z["stage"]}</span></div>
            <div class="future-kpi"><b>ONE 연결</b><span>{z["one_stage"]}</span></div>
            <div class="future-kpi"><b>120일 저점 대비</b><span>{z["low120_dist"]:+.1f}%</span></div>
            <div class="future-kpi"><b>최근 거래량</b><span>{z["volume_ratio"]:.2f}배</span></div>
          </div>
          <div class="small" style="margin-top:8px;">현재 {z["current"]:,.0f}원 · 5일 {z["r5"]:+.1f}% · 20일 {z["r20"]:+.1f}% · 기업안전 {htxt}</div>
          <div style="font-size:12px;color:#ffd54f;margin-top:7px;font-weight:800;">아직 매수 추천 아님 → 기존 후보/진입준비/🔥 ONE 조건으로 승격할 때까지 추적</div>
        </div>
        """,unsafe_allow_html=True)

    themes=res.get("themes") or []
    if themes:
        with st.expander("AI가 본 미래 테마"):
            for th in themes:
                st.markdown(f"**{th.get('theme','')}** · {th.get('stage','')} · 확신 {th.get('confidence',0)}%  \n{th.get('why_now','')}")
    sources=res.get("sources") or []
    if sources:
        with st.expander("AI 웹검색 근거"):
            for z in sources[:8]:
                title=str(z.get("title") or z.get("url") or "출처").replace("[","").replace("]","")
                url=str(z.get("url") or "")
                if url.startswith("http"):
                    st.markdown(f"- [{title}]({url})")
    st.caption(f"최근 분석 {str(res.get('updated_at',''))[:16]} · 모델 {res.get('model','')} · AI는 발굴 담당, 실제 진입 판단은 기존 ONE 엔진 담당")




# Existing KIS/cache adapters retained; retired experiment engines removed.
TM_V4_DAILY_DIR=Path("data")/"tm_v4_v2_daily"
AUTO5Y_STATE_FILE=Path("data")/"auto5y_state_v1.json"
AUTO5Y_BATCH=20
AUTO5Y_MIN_ROWS=300
AUTO5Y_WARMUP_DAYS=450
AUTO5Y_MAX_WINDOWS_PER_STOCK=20

def _tm_full_universe():
    """현재 KIS 마스터의 메인 적격 종목 전체."""
    main,_,_,_=universe()
    rows=[{"code":str(z["code"]).zfill(6),"name":z["name"],"market":z.get("market","")} for z in main]
    return sorted(rows,key=lambda z:(z.get("market",""),z.get("code","")))


def _tm_daily_cache_path(code):
    TM_V4_DAILY_DIR.mkdir(parents=True,exist_ok=True)
    return TM_V4_DAILY_DIR/f"{str(code).zfill(6)}.csv"


def _vg_write(path,obj):
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    except:pass


def _vg_read(path):
    try:
        if path.exists():return json.loads(path.read_text(encoding="utf-8"))
    except:pass
    return {}


def _ad5_dates():
    end=pd.Timestamp(now_kst().date())-pd.Timedelta(days=1)
    start=end-pd.DateOffset(years=5)
    warm=start-pd.Timedelta(days=AUTO5Y_WARMUP_DAYS)
    return pd.Timestamp(start),pd.Timestamp(end),pd.Timestamp(warm)


def _ad5_state():
    q=_vg_read(AUTO5Y_STATE_FILE)
    return q if isinstance(q,dict) else {}


def _ad5_save_state(q):
    _vg_write(AUTO5Y_STATE_FILE,q)


def _ad5_cache_info(stock,warm_start,end_dt):
    code=str(stock["code"]).zfill(6)
    p=_tm_daily_cache_path(code)
    state=_ad5_state().get(code,{})
    try:
        if not p.exists():
            return {"ready":False,"rows":0,"reason":"파일없음","full":False}
        q=pd.read_csv(p,usecols=["date"])
        d=pd.to_datetime(q["date"],errors="coerce").dropna().sort_values()
        if d.empty:
            return {"ready":False,"rows":0,"reason":"날짜없음","full":False}
        rows=len(d); first=d.iloc[0]; last=d.iloc[-1]
        recent=bool(last>=pd.Timestamp(end_dt)-pd.Timedelta(days=10))
        full=bool(first<=pd.Timestamp(warm_start)+pd.Timedelta(days=45))
        exhausted=bool(state.get("exhausted",False))
        if rows>=AUTO5Y_MIN_ROWS and recent and (full or exhausted):
            return {
                "ready":True,"rows":rows,"reason":"FULL" if full else "PARTIAL",
                "full":full,"first":str(first.date()),"last":str(last.date())
            }
        return {
            "ready":False,"rows":rows,
            "reason":"최근자료부족" if not recent else "과거확장필요",
            "full":full,"first":str(first.date()),"last":str(last.date())
        }
    except:
        return {"ready":False,"rows":0,"reason":"캐시읽기실패","full":False}


def _ad5_status(stocks,warm_start,end_dt):
    ready=[];pending=[];skipped=[]
    state=_ad5_state()
    for x in stocks:
        code=str(x["code"]).zfill(6)
        if state.get(code,{}).get("skip"):
            z=dict(x);z["_reason"]=state[code].get("reason","제외");skipped.append(z);continue
        info=_ad5_cache_info(x,warm_start,end_dt)
        z=dict(x);z["_info"]=info
        (ready if info.get("ready") else pending).append(z)
    return ready,pending,skipped


def _ad5_write_cache(code,df):
    try:
        p=_tm_daily_cache_path(code)
        p.parent.mkdir(parents=True,exist_ok=True)
        q=df.copy()
        q["date"]=pd.to_datetime(q["date"],errors="coerce")
        for c in ["open","high","low","close","volume"]:
            q[c]=pd.to_numeric(q[c],errors="coerce")
        q=q.dropna(subset=["date","open","high","low","close"]).drop_duplicates("date").sort_values("date")
        q.to_csv(p,index=False,date_format="%Y-%m-%d")
    except:
        pass


def _ad5_extend_one(stock,warm_start,end_dt,token):
    code=str(stock["code"]).zfill(6)
    p=_tm_daily_cache_path(code)
    state=_ad5_state()
    oldstate=state.get(code,{})
    try:
        if p.exists():
            q=pd.read_csv(p,parse_dates=["date"]).sort_values("date").drop_duplicates("date")
        else:
            q=pd.DataFrame(columns=["date","open","high","low","close","volume"])
    except:
        q=pd.DataFrame(columns=["date","open","high","low","close","volume"])

    # 최근자료 보정
    if q.empty or pd.Timestamp(q["date"].max())<pd.Timestamp(end_dt)-pd.Timedelta(days=10):
        recent_start=max(pd.Timestamp(end_dt)-pd.Timedelta(days=180),pd.Timestamp(warm_start))
        batch=_kis_fetch_window(code,recent_start.to_pydatetime(),pd.Timestamp(end_dt).to_pydatetime(),token)
        if batch:
            q=pd.concat([q,pd.DataFrame(batch)],ignore_index=True)

    exhausted=False
    prev_earliest=None
    for _ in range(AUTO5Y_MAX_WINDOWS_PER_STOCK):
        if not q.empty:
            q["date"]=pd.to_datetime(q["date"],errors="coerce")
            q=q.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
            earliest=pd.Timestamp(q["date"].min())
            if earliest<=pd.Timestamp(warm_start)+pd.Timedelta(days=30):
                break
            cur_end=earliest-pd.Timedelta(days=1)
        else:
            earliest=None
            cur_end=pd.Timestamp(end_dt)

        batch=_kis_fetch_window(code,pd.Timestamp(warm_start).to_pydatetime(),cur_end.to_pydatetime(),token)
        if not batch:
            exhausted=True
            break

        bdf=pd.DataFrame(batch)
        if bdf.empty:
            exhausted=True
            break
        q=pd.concat([q,bdf],ignore_index=True)
        q["date"]=pd.to_datetime(q["date"],errors="coerce")
        q=q.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
        new_earliest=pd.Timestamp(q["date"].min())

        if prev_earliest is not None and new_earliest>=prev_earliest:
            exhausted=True
            break
        if earliest is not None and new_earliest>=earliest:
            exhausted=True
            break
        prev_earliest=new_earliest
        time.sleep(0.06)

    _ad5_write_cache(code,q)

    rows=len(q)
    recent=bool(rows and pd.Timestamp(q["date"].max())>=pd.Timestamp(end_dt)-pd.Timedelta(days=10))
    full=bool(rows and pd.Timestamp(q["date"].min())<=pd.Timestamp(warm_start)+pd.Timedelta(days=45))

    if exhausted and rows<AUTO5Y_MIN_ROWS:
        state[code]={"skip":True,"reason":f"상장이력부족 {rows}봉","exhausted":True}
    else:
        state[code]={
            "skip":False,
            "exhausted":bool(exhausted),
            "rows":rows,
            "full":full,
            "updated":now_kst().strftime("%Y-%m-%d %H:%M:%S")
        }
    _ad5_save_state(state)
    return {"rows":rows,"full":full,"exhausted":exhausted,"recent":recent}


def _ad5_prepare_batch(stocks,warm_start,end_dt,batch=AUTO5Y_BATCH):
    token=kis_access_token() if kis_ready() else ""
    if not token:return {"ok":False,"error":"KIS 인증 필요"}
    ready,pending,skipped=_ad5_status(stocks,warm_start,end_dt)
    todo=pending[:int(batch)]
    if not todo:
        return {"ok":True,"done":True,"ready":len(ready),"skipped":len(skipped),"pending":0}
    p=st.progress(0,text=f"5년자료 확장 · 이번 회차 {len(todo)}종목...")
    notes=[]
    for i,x in enumerate(todo,1):
        p.progress(i/max(len(todo),1),text=f"{i}/{len(todo)} · {x['name']} · 과거이력 확장")
        r=_ad5_extend_one(x,warm_start,end_dt,token)
        notes.append(f'{x["name"]}:{r.get("rows",0)}봉')
    p.empty()
    r2,p2,s2=_ad5_status(stocks,warm_start,end_dt)
    return {
        "ok":True,"done":len(p2)==0,
        "ready":len(r2),"skipped":len(s2),"pending":len(p2),
        "notes":notes[:20]
    }


def _render_candidate_top3():
    arr=st.session_state.get("candidate_top3") or []
    if not arr:return
    st.markdown('<div class="section-title">👀 ONE 뒤를 따라오는 후보 TOP3</div>',unsafe_allow_html=True)
    st.caption("강력추천이 있어도 후보는 계속 표시 · 후보는 지금 매수 신호가 아닙니다.")
    rows=[]
    for i,z in enumerate(arr[:3],1):
        try:
            cur=float(z["df"].iloc[-1].close)
            rows.append({"순위":i,"종목":z["stock"]["name"],"상태":z.get("candidate_status","관망"),
                         "현재가":won(cur),"반등확인선":won(z.get("desired_entry",0)),
                         "확인선 거리":f'{float(z.get("gap_pct",0)):+.1f}%',"진바닥 A":won(z.get("stop",0))})
        except:pass
    if rows: st.dataframe(rows,use_container_width=True,hide_index=True)

def _render_aux_radars(stats):
    if not isinstance(stats,dict) or stats.get("source_error"):return
    surge=stats.get("surge_watch") or []; etfs=stats.get("etf_radar") or []
    st.markdown('<div class="section-title">보조 레이더</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        lines=''.join(f'<div class="radar-line"><b>{z["name"]}</b> · 거래량 {z["volume_ratio"]:.1f}배 · {z["ret1"]:+.1f}%</div>' for z in surge[:3]) or '<div class="small">현재 급등감시 없음</div>'
        st.markdown(f'<div class="radar-card"><div class="radar-title">⚡ 급등감시</div><div class="small">저유동성 메인 제외 · 거래량이 갑자기 살아난 종목만</div>{lines}</div>',unsafe_allow_html=True)
    with c2:
        lines=''.join(f'<div class="radar-line"><b>{z["name"]}</b> · 5일 {z["r5"]:+.1f}% · {"▲" if z["r5"]>0 else "▼" if z["r5"]<0 else "━"}</div>' for z in etfs[:3]) or '<div class="small">ETF 섹터 신호 없음</div>'
        st.markdown(f'<div class="radar-card"><div class="radar-title">📡 ETF 레이더</div><div class="small">섹터 방향 확인용 · 메인 ONE과 분리</div>{lines}</div>',unsafe_allow_html=True)

# FINAL 실전판에서는 대체 후보 TOP3와 연구 설명을 표시하지 않는다.
# ---- embedded paired validator: disabled in FINAL runtime ----
_PAIRED_VALIDATOR_NOTE = "Paired, frozen, price-only ONE research. Never changes live selection."
from pathlib import Path
import gzip
import hashlib
import io
import json
import math
import zipfile

import numpy as np
import pandas as pd

SCHEMA = "ONE_PAIRED_V9_1"
CONFIG = {
    "schema": SCHEMA, "hypothesis": "base_score_minus_0.5_stop_risk_pct",
    "risk_weight": 0.5, "history_bars": 260, "holding_sessions": 60,
    "target_pct": 10.0, "round_trip_cost_pct": 0.35,
    "cost_stress_pct": 0.70, "bootstrap_draws": 2000, "seed": 2608,
    "min_pairs": 60, "min_changed_pairs": 30, "min_months": 12,
    "scope": "price_only_current_survivors_retrospective_not_live",
}
ROOT = Path("data/one_paired_v9")


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def clean_prices(df, end):
    cols = ["date", "open", "high", "low", "close", "volume"]
    q = df[cols].copy()
    q["date"] = pd.to_datetime(q.date, errors="raise").dt.normalize()
    q = q[q.date <= pd.Timestamp(end)].sort_values("date").reset_index(drop=True)
    if q.date.duplicated().any():
        raise ValueError("중복 거래일: 자동으로 덮어쓰지 않습니다")
    for c in cols[1:]:
        q[c] = pd.to_numeric(q[c], errors="raise")
    if not np.isfinite(q[cols[1:]].to_numpy()).all():
        raise ValueError("비정상 가격/거래량")
    if ((q[cols[1:5]] <= 0).any(axis=1) | (q.volume < 0) |
        (q.high < q[["open", "close", "low"]].max(axis=1)) |
        (q.low > q[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("OHLC 관계 오류 또는 0원 봉")
    return q


def choose(events, weight=0.0):
    """Uses signal-date fields only; symbol deterministically resolves final ties."""
    if not events:
        return None
    return min(events, key=lambda e: (-(e["score"] - weight * e["risk_pct"]),
                                      e["dist"], e["code"]))


def simulate(df, signal_date, stop, ceil_price, config=CONFIG):
    """D+1 open, strict A break, stop-first ambiguous bar; no incomplete winners."""
    future = df[df.date > pd.Timestamp(signal_date)].head(config["holding_sessions"])
    # Require the SAME full observation window regardless of early outcome.
    if len(future) < config["holding_sessions"]:
        return {"status": "INCOMPLETE"}
    entry = float(future.iloc[0].open)
    if entry <= stop:
        return {"status": "GAP_INVALID"}  # selected first; never pick runner-up
    target = float(ceil_price(entry * (1 + config["target_pct"] / 100)))
    outcome, exit_price, exit_date = "TIMEOUT", float(future.iloc[-1].close), future.iloc[-1].date
    ambiguous = False
    for _, bar in future.iterrows():
        o, h, l = float(bar.open), float(bar.high), float(bar.low)
        if o < stop:
            outcome, exit_price, exit_date = "STOP", o, bar.date
            break
        if o >= target:
            outcome, exit_price, exit_date = "TARGET", target, bar.date
            break
        if l < stop:
            ambiguous = h >= target
            outcome, exit_price, exit_date = "STOP", stop, bar.date
            break
        if h >= target:
            outcome, exit_price, exit_date = "TARGET", target, bar.date
            break
    gross = (exit_price / entry - 1) * 100
    return {"status": "COMPLETE", "outcome": outcome, "entry": entry,
            "exit": exit_price, "exit_date": str(pd.Timestamp(exit_date).date()),
            "gross_pct": gross, "net_pct": gross - config["round_trip_cost_pct"],
            "ambiguous": ambiguous}


def metrics(trades):
    if not trades:
        return {"n": 0, "target_rate_pct": None, "profitable_rate_pct": None,
                "stop_rate_pct": None, "mean_net_pct": None, "worst_trade_pct": None}
    return {"n": len(trades),
            "target_rate_pct": 100 * np.mean([t["outcome"] == "TARGET" for t in trades]),
            "profitable_rate_pct": 100 * np.mean([t["net_pct"] > 0 for t in trades]),
            "stop_rate_pct": 100 * np.mean([t["outcome"] == "STOP" for t in trades]),
            "mean_net_pct": float(np.mean([t["net_pct"] for t in trades])),
            "worst_trade_pct": min(t["net_pct"] for t in trades)}


def paired_ci(pairs, config=CONFIG):
    """Resample whole signal-month blocks, preserve paired same-day outcomes."""
    groups = {}
    for p in pairs:
        groups.setdefault(p["date"][:7], []).append(p)
    blocks = []
    for values in groups.values():
        blocks.append([len(values),
                       sum(p["candidate"]["net_pct"] - p["base"]["net_pct"] for p in values),
                       sum(int(p["candidate"]["outcome"] == "TARGET") -
                           int(p["base"]["outcome"] == "TARGET") for p in values)])
    if len(blocks) < 2:
        return {"months": len(blocks), "net_ci95": None, "target_ci95_pp": None}
    a = np.array(blocks, dtype=float)
    rng = np.random.default_rng(config["seed"])
    sums = a[rng.integers(0, len(a), (config["bootstrap_draws"], len(a)))].sum(axis=1)
    return {"months": len(blocks),
            "net_ci95": np.quantile(sums[:, 1] / sums[:, 0], [.025, .975]).tolist(),
            "target_ci95_pp": np.quantile(100 * sums[:, 2] / sums[:, 0], [.025, .975]).tolist()}


def report(pairs, exclusions, coverage, config=CONFIG):
    base, candidate = metrics([p["base"] for p in pairs]), metrics([p["candidate"] for p in pairs])
    ci = paired_ci(pairs, config)
    changed = sum(p["base_code"] != p["candidate_code"] for p in pairs)
    enough = len(pairs) >= config["min_pairs"] and changed >= config["min_changed_pairs"] and ci["months"] >= config["min_months"]
    status, reason = "HOLD", "표본·변경일 또는 불확실성 기준 미충족"
    if enough and ci["net_ci95"]:
        if ci["net_ci95"][1] < 0 or ci["target_ci95_pp"][1] < 0:
            status, reason = "REJECT", "순수익 또는 목표도달률의 차이 신뢰구간 전체가 음수"
        elif (coverage["excluded_stocks"] == 0 and not exclusions and
              ci["net_ci95"][0] > 0 and ci["target_ci95_pp"][0] > 0 and
              candidate["stop_rate_pct"] <= base["stop_rate_pct"] and
              candidate["worst_trade_pct"] >= base["worst_trade_pct"] and
              candidate["mean_net_pct"] > config["cost_stress_pct"] - config["round_trip_cost_pct"]):
            status, reason = "RESEARCH_PASS", "가격기반 후향 비교 기준 통과. 실전 개선 인증 아님"
    # Annual and recent-period deterioration override aggregate success.
    yearly = []
    for year in sorted({p["date"][:4] for p in pairs}):
        subset = [p for p in pairs if p["date"].startswith(year)]
        b, c = metrics([p["base"] for p in subset]), metrics([p["candidate"] for p in subset])
        yearly.append({"year": year, "n": len(subset), "base_mean_net_pct": b["mean_net_pct"],
                       "candidate_mean_net_pct": c["mean_net_pct"],
                       "delta_net_pp": c["mean_net_pct"] - b["mean_net_pct"]})
    recent = pairs[int(len(pairs) * .7):]
    rb, rc = metrics([p["base"] for p in recent]), metrics([p["candidate"] for p in recent])
    if status == "RESEARCH_PASS" and (any(y["delta_net_pp"] < 0 for y in yearly if y["n"] >= 20) or
            len(recent) < 20 or rc["mean_net_pct"] <= rb["mean_net_pct"] or
            rc["target_rate_pct"] < rb["target_rate_pct"]):
        status, reason = "HOLD", "연도별 또는 최근 30%에서 개선 일관성 부족"
    return {"status": status, "reason": reason, "base": base, "candidate": candidate,
            "changed_pairs": changed, "ci": ci, "yearly": yearly,
            "recent_30pct": {"base": rb, "candidate": rc},
            "coverage": coverage, "excluded_days": exclusions,
            "paired_days": len(pairs), "production_adoption": False,
            "live_accuracy": "UNKNOWN", "pairs": pairs}


def collect(df, stock, api, start, end):
    events = []
    # No outcomes, flows from today, or future candles enter this loop.
    # Current scanner supplies 260 daily bars; preserve that information set exactly.
    for i in range(config_history_bars() - 1, len(df)):
        day = df.iloc[i].date
        if not (pd.Timestamp(start) <= day <= pd.Timestamp(end)):
            continue
        h = df.iloc[max(0, i - 259):i + 1].reset_index(drop=True)
        cur = float(h.iloc[-1].close)
        bar = h.iloc[-1]
        if abs(float(bar.close) - float(bar.open)) / max(float(bar.high) - float(bar.low), 1e-9) * 100 < 40:
            continue
        if not 5000 <= cur <= 50000 or h.volume.tail(20).median() < 50000 or (h.close * h.volume).tail(20).median() < 500_000_000:
            continue
        bt = api["big_trend_gate"](h)
        if not bt or not bt.get("ok"):
            continue
        sig = api["_live_ab_signal_core"](h, use_b_support=False, use_overhead=False)
        if not sig:
            continue
        stop, entry = float(sig["A"]["low"]), float(sig["entry"])
        if not 0 < stop < entry:
            continue
        mtf = api["multi_timeframe_trend"](h)
        score = float(sig["body_pct"]) + max(0, int(mtf["monthly"]["score"]) - 3) * .25 + max(0, int(mtf["weekly"]["score"]) - 3) * .15
        events.append({"date": str(day.date()), "code": stock["code"], "score": score,
                       "stop": stop, "risk_pct": (1 - stop / entry) * 100,
                       "dist": (entry / stop - 1) * 100})
    return events


def config_history_bars():
    return int(CONFIG["history_bars"])


def source_hash(api):
    import inspect
    # Whole production source plus module changes invalidate continuation.
    path = Path(inspect.getsourcefile(api["_live_ab_signal_core"]))
    return hashlib.sha256(path.read_bytes() + Path(__file__).read_bytes()).hexdigest()


def step(api, root=ROOT):
    manifest = read(root / "manifest.json")
    if not manifest:
        stocks = api["_tm_full_universe"]()
        if not stocks:
            raise ValueError("KIS 종목목록 없음: 검증을 시작하지 않았습니다")
        if any(not str(s["code"]).isdigit() or len(str(s["code"])) != 6 for s in stocks):
            raise ValueError("종목코드 형식 오류")
        stocks = list({s["code"]: s for s in stocks}.values())
        start, end, warm = api["_ad5_dates"]()
        # Exclude common trailing 90 calendar days BEFORE examining any outcomes.
        signal_end = pd.Timestamp(end) - pd.Timedelta(days=120)
        manifest = {"config": CONFIG, "source_hash": source_hash(api), "stocks": stocks,
                    "start": str(start.date()), "end": str(end.date()), "warm": str(warm.date()),
                    "signal_end": str(signal_end.date()), "phase": "PREPARE", "files": {},
                    "done": [], "event_hashes": {}, "excluded": [], "stalls": 0}
        write(root / "manifest.json", manifest)
    if manifest["source_hash"] != source_hash(api) or manifest["config"] != CONFIG:
        raise ValueError("잠금 이후 코드/설정 변경. 기존 결과를 이어 계산하지 않습니다")
    stocks, warm, end = manifest["stocks"], manifest["warm"], manifest["end"]
    if manifest["phase"] == "PREPARE":
        ready, pending, skipped = api["_ad5_status"](stocks, warm, end)
        if pending:
            result = api["_ad5_prepare_batch"](stocks, warm, end, batch=3)
            if not result.get("ok"):
                raise ValueError(result.get("error", "KIS 자료 준비 실패"))
            after = api["_ad5_status"](stocks, warm, end)[1]
            manifest["stalls"] = manifest["stalls"] + 1 if len(after) >= len(pending) else 0
            write(root / "manifest.json", manifest)
            if manifest["stalls"] >= 3:
                raise ValueError("3회 연속 자료 준비 진전 없음. API/자료 오류를 확인한 뒤 재개하세요")
            return "KIS 자료 준비", len(stocks) - len(after), len(stocks)
        # Snapshot separately from event collection. Freeze ALL inputs first.
        manifest["eligible"] = [s for s in ready]
        manifest["excluded"] = [{"code": s["code"], "reason": s.get("_reason", "자료 제외")} for s in skipped]
        manifest["phase"] = "FREEZE"
        write(root / "manifest.json", manifest)
    if manifest["phase"] == "FREEZE":
        todo = [s for s in manifest["eligible"] if s["code"] not in manifest["files"]]
        for stock in todo[:10]:
            code = stock["code"]
            q = clean_prices(pd.read_csv(api["_tm_daily_cache_path"](code)), end)
            raw = q.to_csv(index=False, date_format="%Y-%m-%d").encode()
            target = root / "snapshots" / (code + ".csv.gz")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(gzip.compress(raw, mtime=0))
            manifest["files"][code] = hashlib.sha256(raw).hexdigest()
            if not stock.get("_info", {}).get("full", False):
                manifest["excluded"].append({"code": code, "reason": "부분 이력 / API 빈 응답과 상장일 미분리"})
        if len(todo) <= 10:
            manifest["input_hash"] = digest({"files": manifest["files"], "stocks": stocks,
                                             "start": manifest["start"], "end": end, "config": CONFIG})
            manifest["phase"] = "EVENTS"
        write(root / "manifest.json", manifest)
        return "입력 스냅샷 고정", len(manifest["files"]), len(manifest["eligible"])
    if manifest["phase"] == "EVENTS":
        todo = [s for s in manifest["eligible"] if s["code"] not in manifest["done"]]
        for stock in todo[:2]:
            q = load_snapshot(root, manifest, stock["code"])
            events = collect(q, stock, api, manifest["start"], manifest["signal_end"])
            write(root / "events" / (stock["code"] + ".json"), events)
            manifest["event_hashes"][stock["code"]] = digest(events)
            manifest["done"].append(stock["code"])
            write(root / "manifest.json", manifest)
        if not todo:
            manifest["phase"] = "COMPARE"
            write(root / "manifest.json", manifest)
        return "과거 시점 신호 계산", len(manifest["done"]), len(manifest["eligible"])
    if manifest["phase"] == "COMPARE":
        by_day = {}
        for code in manifest["done"]:
            events = read(root / "events" / (code + ".json"), [])
            if digest(events) != manifest["event_hashes"][code]:
                raise ValueError(f"{code} 신호 기록 해시 불일치")
            for e in events:
                by_day.setdefault(e["date"], []).append(e)
        # Freeze choices BEFORE loading future data.
        choices = [{"date": day, "base": choose(events), "candidate": choose(events, CONFIG["risk_weight"])}
                   for day, events in sorted(by_day.items())]
        write(root / "choices.json", choices)
        pairs, excluded = [], []
        from functools import lru_cache
        @lru_cache(maxsize=16)
        def prices(code):
            return load_snapshot(root, manifest, code)
        for choice in choices:
            b, c = choice["base"], choice["candidate"]
            rb = simulate(prices(b["code"]), choice["date"], b["stop"], api["krx_ceil_price"])
            rc = simulate(prices(c["code"]), choice["date"], c["stop"], api["krx_ceil_price"])
            if rb["status"] != "COMPLETE" or rc["status"] != "COMPLETE":
                excluded.append({"date": choice["date"], "base_code": b["code"], "candidate_code": c["code"],
                                 "base_status": rb["status"], "candidate_status": rc["status"]})
            else:
                pairs.append({"date": choice["date"], "base_code": b["code"], "candidate_code": c["code"], "base": rb, "candidate": rc})
        coverage = {"frozen_stocks": len(stocks), "processed_stocks": len(manifest["done"]),
                    "excluded_stocks": len({s["code"] for s in manifest["excluded"]}),
                    "stock_issues": manifest["excluded"], "selected_days": len(choices)}
        result = report(pairs, excluded, coverage)
        result.update({"input_hash": manifest["input_hash"], "source_hash": manifest["source_hash"], "config": CONFIG,
                       "start": manifest["start"], "signal_end": manifest["signal_end"]})
        months = max(1, len(pd.period_range(manifest["start"], manifest["signal_end"], freq="M")))
        result["frequency"] = {"selected_days_per_month": len(choices) / months,
                               "paired_days_per_month": len(pairs) / months,
                               "calendar_months": months}
        write(root / "result.json", result)
        write(root / "experiment_ledger.json", {"experiment": CONFIG["hypothesis"], "result_hash": digest(result),
              "status": result["status"], "reason": result["reason"], "input_hash": manifest["input_hash"],
              "production_adoption": False, "repeat_locked": True})
        manifest["phase"] = "DONE"
        write(root / "manifest.json", manifest)
        return "비교 완료", len(pairs), len(pairs)
    return "완료 · 같은 실험 재실행 잠금", 1, 1


def load_snapshot(root, manifest, code):
    raw = gzip.decompress((root / "snapshots" / (code + ".csv.gz")).read_bytes())
    if hashlib.sha256(raw).hexdigest() != manifest["files"][code]:
        raise ValueError(f"{code} 입력 해시 불일치")
    return clean_prices(pd.read_csv(io.BytesIO(raw)), manifest["end"])


def backup(root):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix != ".tmp":
                z.write(p, str(p.relative_to(root)))
    return output.getvalue()


def restore(payload, api, root=ROOT):
    """Restore only to an unused run folder; whitelist paths, never extractall."""
    import re
    if root.exists() and any(root.iterdir()):
        raise ValueError("현재 진행 기록이 있으므로 덮어쓰지 않습니다")
    allowed = re.compile(r"(?:manifest|choices|result|experiment_ledger)\.json|(?:snapshots/[0-9]{6}\.csv\.gz)|(?:events/[0-9]{6}\.json)")
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        infos = z.infolist()
        if sum(i.file_size for i in infos) > 512 * 1024 * 1024 or len(infos) > 15000:
            raise ValueError("체크포인트 크기 제한 초과")
        if len({i.filename for i in infos}) != len(infos) or any(not allowed.fullmatch(i.filename) for i in infos):
            raise ValueError("허용하지 않은 경로 또는 중복 파일")
        files = {i.filename: z.read(i) for i in infos}
    m = json.loads(files["manifest.json"])
    if m["source_hash"] != source_hash(api) or m["config"] != CONFIG:
        raise ValueError("다른 코드/설정의 체크포인트")
    # Structural checks and bounded decompression before writing anything.
    for code, expected in m["files"].items():
        if not re.fullmatch(r"[0-9]{6}", code):
            raise ValueError("잘못된 종목코드")
        with gzip.GzipFile(fileobj=io.BytesIO(files[f"snapshots/{code}.csv.gz"])) as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("스냅샷 크기/해시 오류")
    for code in m["done"]:
        if digest(json.loads(files[f"events/{code}.json"])) != m["event_hashes"][code]:
            raise ValueError("신호 해시 오류")
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def render(api):
    st = api["st"]
    st.subheader("ONE 전후 비교 · 타임머신 V9")
    st.caption("현재 ONE은 유지합니다. 비교 후보: BASE 점수 − A손절거리(%) × 0.5. 고정 가설 1개이며 성적을 보고 계수를 바꾸지 않습니다.")
    st.warning("가격기반 연구용 비교입니다. 과거 수급·당시 상장종목 전체·실제 체결을 복원하지 못하므로 실전 ONE의 정확도나 수익 보장이 아닙니다.")
    st.caption("D+1 시가 · +10% 목표 · A 저가 이탈 · 최대 60거래일 · 왕복비용 가정 0.35% / 스트레스 0.70%. 거래별 평가이며 중복 보유를 반영한 계좌 수익률/MDD는 아닙니다.")
    try:
        result = read(ROOT / "result.json")
        manifest = read(ROOT / "manifest.json", {})
        frozen_code_changed = bool(manifest and manifest["source_hash"] != source_hash(api))
        frozen_config_changed = bool(manifest and manifest["config"] != CONFIG)
        if (frozen_code_changed or frozen_config_changed) and not result:
            raise ValueError("잠금 이후 코드/설정 변경: 기존 검증을 이어 계산하지 않았습니다")
        if result:
            ledger = read(ROOT / "experiment_ledger.json", {})
            if digest(result) != ledger.get("result_hash") or result["input_hash"] != manifest.get("input_hash"):
                raise ValueError("결과/실험 기록 해시 불일치")
    except Exception as exc:
        st.error(str(exc))
        return
    if result:
        if frozen_code_changed or frozen_config_changed:
            st.warning("이 표는 이전에 고정·완료된 결과의 읽기 전용 표시입니다. 현재 코드/설정으로 이어 계산하거나 실전 반영하지 않습니다.")
        labels = {"HOLD": "판단 보류", "REJECT": "개선 실패", "RESEARCH_PASS": "후향 가격검증 통과 · 실전 신뢰도 미판정"}
        st.info(labels[result["status"]] + " · " + result["reason"])
        table = []
        for label, key in [("기존 ONE 가격기반 재현", "base"), ("미채택 개선 후보", "candidate")]:
            m = result[key]
            table.append({"방식": label, "동일일 비교 건수": m["n"], "+10% 도달률(%)": m["target_rate_pct"],
                          "비용 후 수익 거래(%)": m["profitable_rate_pct"], "A손절률(%)": m["stop_rate_pct"],
                          "평균 순수익(%)": m["mean_net_pct"], "최악 거래(%)": m["worst_trade_pct"]})
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        st.write(f"선택 종목이 달라진 비교일: {result['changed_pairs']}일 · 비교 불가: {len(result['excluded_days'])}일")
        st.write(f"월평균 선택 {result['frequency']['selected_days_per_month']:.1f}일 · 실제 짝비교 {result['frequency']['paired_days_per_month']:.1f}일")
        st.write("평균 순수익 차이 95% 구간 (%p):", result["ci"]["net_ci95"])
        st.write("목표도달률 차이 95% 구간 (%p):", result["ci"]["target_ci95_pp"])
        st.caption("월 단위 묶음 재표본 추정입니다. 60일 중복보유의 월간 의존성까지 모두 해소하지는 못합니다. 95% 구간은 실전 성공확률이 아닙니다.")
        st.dataframe(pd.DataFrame(result["yearly"]), use_container_width=True, hide_index=True)
        st.caption(f"기간 {result['start']} ~ {result['signal_end']} · 고정 {result['coverage']['frozen_stocks']}종목 · 자료 누락/부분 이력 {result['coverage']['excluded_stocks']}종목 · 실전 자동 적용 없음")
        with st.expander("최근 30% / 자료 누락 / 체결 제외 내역"):
            st.json({"recent_30pct": result["recent_30pct"], "coverage": result["coverage"], "excluded_days": result["excluded_days"]})
        st.download_button("비교 결과 JSON", json.dumps(result, ensure_ascii=False, indent=2), "one_v9_result.json", "application/json")
        st.session_state["v9_running"] = False
    else:
        st.caption("5년 자료를 기존 KIS 연결로 준비하고 입력을 고정한 뒤 이어 계산합니다. 시작 시점의 종목목록/기간/설정은 바뀌지 않습니다.")
        if st.button("검증 시작 / 이어서 진행", key="v9_start"):
            st.session_state["v9_running"] = True
        if st.button("일시 정지", key="v9_pause"):
            st.session_state["v9_running"] = False
        st.write("현재 단계:", manifest.get("phase", "미실행"))
        if not manifest:
            with st.expander("이전 체크포인트 복원"):
                upload = st.file_uploader("이 검증기가 저장한 ZIP만 사용", type="zip", key="v9_restore_file")
                if upload is not None and st.button("체크포인트 복원", key="v9_restore"):
                    try:
                        restore(upload.getvalue(), api)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"복원하지 못했습니다: {exc}")
    if manifest:
        if st.button("재현용 백업 준비", key="v9_backup"):
            st.session_state["v9_backup_bytes"] = backup(ROOT)
        if st.session_state.get("v9_backup_bytes"):
            st.download_button("현재 체크포인트 ZIP 저장", st.session_state["v9_backup_bytes"], "one_v9_checkpoint.zip", "application/zip")
        st.caption("서버 로컬 저장이 초기화되면 진행 기록도 사라질 수 있습니다. 체크포인트 ZIP에는 가격 스냅샷과 실험 기록이 포함되며 API 키는 포함하지 않습니다.")
    if st.session_state.get("v9_running") and not result:
        try:
            with st.spinner("타임머신 검증 진행 중 · 종목 단위로 체크포인트 저장"):
                label, done, total = step(api)
            st.progress(min(done / max(total, 1), 1.0), text=f"{label}: {done}/{total}")
            st.rerun()
        except Exception as exc:
            st.session_state["v9_running"] = False
            st.error(f"검증 중단 · 결과를 성공으로 처리하지 않았습니다: {type(exc).__name__}: {exc}")


# FINAL 실전판: 연구 엔진(V7/V8/V9), 미래발굴, 보조 레이더를 실행하지 않는다.
# 실전 화면은 위의 A→B BASE 결과와 오늘 행동만 사용한다.

# Research-only exit validator.  It reads the KIS time-machine cache and cannot
# alter ONE selection, entry, stop, or the live +10% rule.
def _fib_exit_research_rows():
    rows=[]
    for p in sorted(TM_V4_DAILY_DIR.glob("*.csv")):
        try:
            d=pd.read_csv(p,parse_dates=["date"]).sort_values("date").reset_index(drop=True)
            for i in range(260,len(d)-15):
                # Do not recreate a similar signal.  This is the exact live BASE
                # signal function, evaluated with candles available on that day only.
                h=d.iloc[i-259:i+1].reset_index(drop=True)
                sig=_live_ab_signal(h)
                if not sig: continue
                A=float(sig["A"]["low"]); B=float(sig["ridge"]["high"])
                f=d.iloc[i+1:i+16]; entry=float(f.open.iloc[0])
                if entry<=A: continue
                fixed=krx_ceil_price(entry*1.10); ext=krx_ceil_price(A+(B-A)*1.272)
                bp,bo=float(f.close.iloc[-1]),"TIMEOUT"; fp,fo=bp,"TIMEOUT"; half=False; base_done=False; highc=entry
                for _,r in f.iterrows():
                    o,hi,lo,c=map(float,(r.open,r.high,r.low,r.close))
                    if lo<A or o<A:
                        x=o if o<A else A
                        if not base_done: bp,bo=x,"STOP"; base_done=True
                        fp,fo=(fixed-entry)*.5+(x-entry)*.5,("HALF_STOP" if half else "STOP"); break
                    if not base_done and (o>=fixed or hi>=fixed): bp,bo=fixed,"TARGET"; base_done=True
                    if not half and (o>=fixed or hi>=fixed): half=True
                    if half:
                        highc=max(highc,c)
                        if o>=ext or hi>=ext: fp,fo=(fixed-entry)*.5+(ext-entry)*.5,"FIB_1272"; break
                        if c<highc*.97: fp,fo=(fixed-entry)*.5+(c-entry)*.5,"TRAIL"; break
                else:
                    if half: fp,fo=(fixed-entry)*.5+(float(f.close.iloc[-1])-entry)*.5,"HALF_TIMEOUT"
                rows.append({"날짜":str(h.date.iloc[-1].date()),"종목코드":p.stem,"A":A,"B":B,"BASE 순수익%":(bp/entry-1)*100-.35,"피보 순수익%":fp/entry*100-.35,"BASE 매도":bo,"피보 매도":fo,"피보 1.272":ext})
        except Exception: continue
    return pd.DataFrame(rows)

def _render_fib_exit_validator():
    st.divider(); st.subheader("📐 피보나치 매도 검증 · 연구 전용")
    st.caption("ONE 선정·진입·손절은 바꾸지 않습니다. 동일한 과거 BASE 신호에서 매도 방식만 비교합니다.")
    if st.button("KIS 과거 일봉 20종목 준비",key="fib_exit_validate"):
        # One bounded batch only.  Never force st.rerun(): it locks the page.
        stocks=_tm_full_universe()[:120]
        ws,we,ww=_ad5_dates()
        if not kis_ready():
            st.error("KIS APP KEY/SECRET이 연결되지 않아 과거 일봉을 준비할 수 없습니다.")
            return
        r=_ad5_prepare_batch(stocks,ww,we,batch=20)
        if not r.get("ok"):
            st.error(r.get("error","KIS 과거 일봉 준비 실패")); return
        st.success(f"이번 준비 완료 · 누적 {r.get('ready',0)} / 120종목 · 필요하면 같은 버튼을 다시 누르세요.")
    if st.button("준비된 KIS 일봉으로 결과 계산",key="fib_exit_calculate"):
        st.session_state["fib_calculate"]=True
    if st.session_state.pop("fib_calculate",False):
        with st.spinner("KIS 타임머신 저장 일봉의 동일 신호를 비교 중입니다..."):
            q=_fib_exit_research_rows()
        if q.empty: st.error("검증할 KIS 5년 일봉 또는 완결 신호가 없습니다. 결과를 성공으로 처리하지 않습니다."); return
        # A duplicated signal indicates broken point-in-time signal replay.
        q=q.drop_duplicates(["종목코드","날짜"])
        if len(q)>3000:
            st.error("신호 수가 비정상적으로 많아 결과를 무효 처리했습니다."); return
        delta=float((q["피보 순수익%"]-q["BASE 순수익%"]).mean())
        verdict="보류/폐기" if len(q)<80 or delta<=0 or q["피보 순수익%"].min()<q["BASE 순수익%"].min() else "추가 독립검증 후보"
        a,b,c,d=st.columns(4); a.metric("동일 신호",f"{len(q)}건"); b.metric("BASE 평균",f"{q['BASE 순수익%'].mean():.2f}%"); c.metric("피보 평균",f"{q['피보 순수익%'].mean():.2f}%"); d.metric("차이",f"{delta:+.2f}%p")
        st.info(verdict+" · 통과해도 실전 매도 규칙은 자동 변경되지 않습니다.")
        st.download_button("검증 결과 CSV",q.to_csv(index=False).encode("utf-8-sig"),"fib_exit_paired_results.csv","text/csv")

# Deliberately not rendered in the live app.  Historical KIS collection is a
# long-running research job and must never block the user's live ONE screen.

# BASE scorecard: reads only already-cached KIS daily bars.  No network calls,
# no reruns, and no effect on live ONE selection.
BASE_SCORECARD_FILE=Path("data")/"base_scorecard.json"
def _base_scorecard_rows():
    rows=[]
    for p in sorted(DAILY_CACHE_DIR.glob("*.csv"))[:120]:
        try:
            d=_load_daily_disk(p.stem)
            if d is None or len(d)<275: continue
            for i in range(259,len(d)-15):
                h=d.iloc[i-259:i+1].reset_index(drop=True); sig=_live_ab_signal(h)
                if not sig: continue
                fut=d.iloc[i+1:i+16].reset_index(drop=True); entry=float(fut.open.iloc[0]); stop=float(sig["A"]["low"])
                if entry<=stop: continue
                target=krx_ceil_price(entry*1.10); outcome="TIMEOUT"; exit_px=float(fut.close.iloc[-1]); days=15
                for j,r in fut.iterrows():
                    op,hi,cl=map(float,(r.open,r.high,r.close))
                    if op>=target: outcome="TARGET"; exit_px=target; days=j+1; break
                    if op<stop: outcome="GAP_STOP"; exit_px=op; days=j+1; break
                    if hi>=target: outcome="TARGET"; exit_px=target; days=j+1; break
                    if cl<stop: outcome="CLOSE_STOP"; exit_px=cl; days=j+1; break
                rows.append({"code":p.stem,"date":str(h.date.iloc[-1].date()),"outcome":outcome,"days":days,"net_pct":(exit_px/entry-1)*100-.35})
        except: continue
    return pd.DataFrame(rows).drop_duplicates(["code","date"]) if rows else pd.DataFrame()

def _render_base_scorecard():
    st.divider(); st.subheader("🔒 고정 BASE 성적표 · 연구 전용")
    st.caption("저장된 KIS 일봉만 읽습니다. 인터넷 재호출·자동 반복·실전 추천 변경은 없습니다.")
    if st.button("저장된 KIS 일봉으로 BASE 성적 계산",key="base_scorecard_run"):
        with st.spinner("저장된 일봉에서 고정 BASE 신호를 계산 중입니다..."):
            q=_base_scorecard_rows()
        if q.empty:
            st.error("검증 가능한 저장 일봉·완결 신호가 없습니다. 결과를 성공으로 처리하지 않습니다."); return
        result={"status":"HOLD","scope":"저장 일봉 한정 · TOP ONE 정확도 아님","signals":int(len(q)),
                "target_rate_pct":round(float((q.outcome=="TARGET").mean()*100),2),
                "stop_rate_pct":round(float(q.outcome.isin(["GAP_STOP","CLOSE_STOP"]).mean()*100),2),
                "mean_net_pct":round(float(q.net_pct.mean()),3),"worst_net_pct":round(float(q.net_pct.min()),3)}
        BASE_SCORECARD_FILE.parent.mkdir(parents=True,exist_ok=True); BASE_SCORECARD_FILE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        st.session_state["base_scorecard"]=result
    result=st.session_state.get("base_scorecard")
    if result is None:
        try: result=json.loads(BASE_SCORECARD_FILE.read_text(encoding="utf-8")) if BASE_SCORECARD_FILE.exists() else None
        except: result=None
    if result:
        a,b,c,d=st.columns(4); a.metric("완결 신호",f"{result['signals']}건"); b.metric("+10% 도달률",f"{result['target_rate_pct']:.2f}%"); c.metric("A 손절률",f"{result['stop_rate_pct']:.2f}%"); d.metric("평균 순수익",f"{result['mean_net_pct']:+.3f}%")
        st.info("현재 상태: HOLD · 저장 일봉 범위의 BASE 성적표입니다. 충분한 KIS 5년·TOP ONE 짝비교 전 실전 기준은 변경하지 않습니다.")

# Old A→B scorecard is intentionally not rendered.  Its research result is not
# part of the current deep-valley candidate workflow.

# True historical ONE replay.  Long KIS work is isolated in a daemon thread;
# the live screen never calls it automatically and never waits for it.
BASE_TM_DIR=Path("data")/"base_true_timemachine"
BASE_TM_STATE=BASE_TM_DIR/"state.json"
BASE_TM_RESULT=BASE_TM_DIR/"result.json"
BASE_TM_TRADES=BASE_TM_DIR/"trades.csv"
def _base_tm_collect_worker(stocks,warm,end,token):
    state={"phase":"COLLECTING","done":0,"total":len(stocks),"error":""}; _vg_write(BASE_TM_STATE,state)
    try:
        for i,x in enumerate(stocks,1):
            _ad5_extend_one(x,warm,end,token)
            state.update({"done":i,"last":x.get("name",x["code"])}); _vg_write(BASE_TM_STATE,state)
        state.update({"phase":"READY"}); _vg_write(BASE_TM_STATE,state)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(BASE_TM_STATE,state)

def _base_tm_replay_worker(stocks):
    state={"phase":"REPLAY","done":0,"total":len(stocks),"error":""}; _vg_write(BASE_TM_STATE,state)
    picks={}
    try:
        for n,x in enumerate(stocks,1):
            p=_tm_daily_cache_path(x["code"])
            if not p.exists(): continue
            d=pd.read_csv(p,parse_dates=["date"]).sort_values("date").reset_index(drop=True)
            for i in range(259,len(d)-15):
                h=d.iloc[i-259:i+1].reset_index(drop=True)
                z=analyze_one({"code":str(x["code"]).zfill(6),"name":x.get("name",x["code"]),"_df":h})
                if not z: continue
                day=str(h.date.iloc[-1].date()); picks.setdefault(day,[]).append(z)
            state.update({"done":n,"last":x.get("name",x["code"])}); _vg_write(BASE_TM_STATE,state)
        trades=[]
        for day,arr in picks.items():
            z=sorted(arr,key=lambda q:(q["body_pct"],-q["dist"],q["stock"]["code"]),reverse=True)[0]
            d=z["df"]; # source window ends on signal day; reload exact future by code
            full=pd.read_csv(_tm_daily_cache_path(z["stock"]["code"]),parse_dates=["date"]).sort_values("date").reset_index(drop=True)
            k=full.index[full.date.dt.normalize()==pd.Timestamp(day)].tolist()
            if not k or k[-1]+15>=len(full): continue
            f=full.iloc[k[-1]+1:k[-1]+16].reset_index(drop=True); entry=float(f.open.iloc[0]); stop=float(z["A"]["low"]); target=krx_ceil_price(entry*1.10); out="TIMEOUT"; ex=float(f.close.iloc[-1])
            for _,r in f.iterrows():
                op,hi,cl=map(float,(r.open,r.high,r.close))
                if op>=target or hi>=target: out="TARGET"; ex=target; break
                if op<stop: out="GAP_STOP"; ex=op; break
                if cl<stop: out="CLOSE_STOP"; ex=cl; break
            b_age=len(z["df"])-1-int(z["B"]["i"])
            signal_close=float(z["entry"]); hist=z["df"]
            vol_base=float(hist.volume.astype(float).iloc[-21:-1].median()) if len(hist)>=21 else 0.0
            vol_ratio=float(hist.volume.iloc[-1])/vol_base if vol_base>0 else 0.0
            trades.append({"date":day,"code":z["stock"]["code"],"entry":entry,"stop":stop,"outcome":out,"net_pct":(ex/entry-1)*100-.35,"a_age":int(z["A"].get("age",0)),"b_age":b_age,"body_pct":float(z.get("body_pct",0)),"volume_ratio":vol_ratio,"next_open_gap_pct":(entry/signal_close-1)*100})
        q=pd.DataFrame(trades)
        result={"status":"HOLD","scope":"현재 KIS 종목풀 후향 재현 · 과거 상장폐지 종목 미포함","signals":len(q),"target_rate_pct":round(float((q.outcome=="TARGET").mean()*100),2) if len(q) else None,"stop_rate_pct":round(float(q.outcome.isin(["GAP_STOP","CLOSE_STOP"]).mean()*100),2) if len(q) else None,"mean_net_pct":round(float(q.net_pct.mean()),3) if len(q) else None,"worst_net_pct":round(float(q.net_pct.min()),3) if len(q) else None}
        BASE_TM_DIR.mkdir(parents=True,exist_ok=True)
        if not q.empty: q.to_csv(BASE_TM_TRADES,index=False,encoding="utf-8-sig")
        _vg_write(BASE_TM_RESULT,result); state.update({"phase":"DONE"}); _vg_write(BASE_TM_STATE,state)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(BASE_TM_STATE,state)

def _render_true_timemachine():
    import threading
    st.divider(); st.subheader("🧪 고정 BASE · 과거 ONE 재현")
    st.caption("실전 화면과 분리 · KIS 수집/재현은 백그라운드 · 자동 반복 없음 · 결과는 연구용 HOLD")
    state=_vg_read(BASE_TM_STATE) or {"phase":"미실행"}; phase=state.get("phase","미실행")
    st.write(f"상태: **{phase}** · {state.get('done',0)} / {state.get('total',0)}" + (f" · {state.get('last')}" if state.get('last') else ""))
    if phase in ("미실행","ERROR") and st.button("KIS 5년 일봉 수집 시작",key="base_tm_collect"):
        if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
        else:
            stocks=_tm_full_universe()[:120]; start,end,warm=_ad5_dates(); token=kis_access_token()
            threading.Thread(target=_base_tm_collect_worker,args=(stocks,warm,end,token),daemon=True).start(); st.success("백그라운드 수집을 시작했습니다. 화면은 계속 사용할 수 있습니다.")
    if phase=="READY" and st.button("과거 날짜별 ONE 재현 시작",key="base_tm_replay"):
        limit=600 if int(state.get("total",0))>=600 else (300 if int(state.get("total",0))>=300 else 120)
        stocks=_tm_full_universe()[:limit]; threading.Thread(target=_base_tm_replay_worker,args=(stocks,),daemon=True).start(); st.success("백그라운드 재현을 시작했습니다. 상태 새로고침으로 확인하세요.")
    if phase=="DONE" and st.button("표본을 300종목으로 확장",key="base_tm_expand_300"):
        if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
        else:
            stocks=_tm_full_universe()[:300]; start,end,warm=_ad5_dates(); token=kis_access_token()
            threading.Thread(target=_base_tm_collect_worker,args=(stocks,warm,end,token),daemon=True).start(); st.success("300종목 확장을 시작했습니다. 완료 후 과거 ONE 재현을 다시 실행하세요.")
    if phase=="DONE" and int(state.get("total",0))>=300 and st.button("재검증 표본을 600종목으로 확장",key="base_tm_expand_600"):
        if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
        else:
            stocks=_tm_full_universe()[:600]; start,end,warm=_ad5_dates(); token=kis_access_token()
            threading.Thread(target=_base_tm_collect_worker,args=(stocks,warm,end,token),daemon=True).start(); st.success("추가 300종목 수집을 시작했습니다. 완료 후 과거 ONE 재현을 다시 실행하세요.")
    if st.button("상태 새로고침",key="base_tm_refresh"): st.rerun()
    result=_vg_read(BASE_TM_RESULT) if BASE_TM_RESULT.exists() else {}
    if phase=="DONE" and result:
        a,b,c,d=st.columns(4); a.metric("날짜별 ONE",f"{result['signals']}건"); b.metric("+10% 도달",f"{result['target_rate_pct']}%"); c.metric("A 손절",f"{result['stop_rate_pct']}%"); d.metric("평균 순수익",f"{result['mean_net_pct']}%")
        st.info("결과는 현재 KIS 종목풀의 후향 재현입니다. 표본·과거 종목풀 한계가 있어 실전 반영은 자동으로 하지 않습니다.")
        if BASE_TM_TRADES.exists():
            q=pd.read_csv(BASE_TM_TRADES)
            st.markdown("#### 307건 해부")
            c1,c2,c3=st.columns(3); c1.metric("시간종료",f"{int((q.outcome=='TIMEOUT').sum())}건"); c2.metric("목표도달",f"{int((q.outcome=='TARGET').sum())}건"); c3.metric("A 손절",f"{int(q.outcome.isin(['GAP_STOP','CLOSE_STOP']).sum())}건")
            q["A 경과구간"]=pd.cut(q.a_age,bins=[0,90,120,153],labels=["60~90일","91~120일","121~150일"],include_lowest=True)
            st.dataframe(q.groupby("A 경과구간",observed=False).agg(건수=("net_pct","size"),평균순수익=("net_pct","mean"),목표도달률=("outcome",lambda x:100*(x=="TARGET").mean()),손절률=("outcome",lambda x:100*x.isin(["GAP_STOP","CLOSE_STOP"]).mean())).reset_index().round(2),use_container_width=True,hide_index=True)
            if {"b_age","body_pct","volume_ratio","next_open_gap_pct"}.issubset(q.columns):
                st.markdown("#### 시간종료 원인 후보 · 아직 규칙 반영 금지")
                q["B 경과구간"]=pd.cut(q.b_age,bins=[0,10,25,56],labels=["10일 이내","11~25일","26~55일"],include_lowest=True)
                q["확인봉 구간"]=pd.cut(q.body_pct,bins=[0,53,70,101],labels=["40~53%","54~70%","71% 이상"],include_lowest=True)
                q["다음날 갭"]=pd.cut(q.next_open_gap_pct,bins=[-100,0,2,100],labels=["하락/동일","0~2%","2% 초과"],include_lowest=True)
                def _cut(col): return q.groupby(col,observed=False).agg(건수=("net_pct","size"),평균순수익=("net_pct","mean"),목표도달률=("outcome",lambda x:100*(x=="TARGET").mean()),시간종료률=("outcome",lambda x:100*(x=="TIMEOUT").mean())).reset_index().round(2)
                x,y,z=st.columns(3)
                with x: st.caption("B 형성 뒤 경과일"); st.dataframe(_cut("B 경과구간"),hide_index=True,use_container_width=True)
                with y: st.caption("확인봉 몸통"); st.dataframe(_cut("확인봉 구간"),hide_index=True,use_container_width=True)
                with z: st.caption("다음날 시가 갭"); st.dataframe(_cut("다음날 갭"),hide_index=True,use_container_width=True)
                st.markdown("#### B 11~25일 가설 · 시간순 독립 비교")
                qq=q.sort_values("date").reset_index(drop=True); n=len(qq); cuts=[(0,int(n*.6),"TRAIN"),(int(n*.6),int(n*.8),"VALID"),(int(n*.8),n,"BLIND")]
                rows=[]
                for lo,hi,label in cuts:
                    base=qq.iloc[lo:hi]; cand=base[(base.b_age>=11)&(base.b_age<=25)]
                    for name,zv in [("기존 BASE",base),("B 11~25일만",cand)]:
                        rows.append({"구간":label,"방식":name,"거래수":len(zv),"평균순수익":round(float(zv.net_pct.mean()),2) if len(zv) else None,"목표도달률":round(float((zv.outcome=='TARGET').mean()*100),2) if len(zv) else None,"손절률":round(float(zv.outcome.isin(['GAP_STOP','CLOSE_STOP']).mean()*100),2) if len(zv) else None})
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
                st.caption("이는 ‘현재 ONE이 B 11~25일일 때만 거래하고 나머지는 관망’하는 단일 가설입니다. BLIND에서도 개선·표본충분·손절악화 없음이 모두 확인되기 전에는 BASE에 반영하지 않습니다.")
                st.markdown("#### B 11~25일 고정 · 워크포워드")
                wf=[]; test_n=max(30,n//5)
                for end in range(max(120,n-3*test_n),n,test_n):
                    test=qq.iloc[end:min(end+test_n,n)]; cand=test[(test.b_age>=11)&(test.b_age<=25)]
                    if len(test)<20: continue
                    wf.append({"검증구간":f"{test.date.iloc[0]} ~ {test.date.iloc[-1]}","BASE건수":len(test),"BASE평균":round(float(test.net_pct.mean()),2),"B11~25건수":len(cand),"B11~25평균":round(float(cand.net_pct.mean()),2) if len(cand) else None,"B11~25목표도달률":round(float((cand.outcome=='TARGET').mean()*100),2) if len(cand) else None})
                st.dataframe(pd.DataFrame(wf),use_container_width=True,hide_index=True)
                st.caption("각 검증구간은 그 이전 날짜의 자료 뒤에 이어집니다. 다만 B 11~25일 가설 자체는 이번 전체 해부에서 발견했으므로, 이 표도 연구용 HOLD이며 새 기간 재검증 전 채택하지 않습니다.")
        if st.button("상세 해부용 과거 ONE 재현 다시 실행",key="base_tm_replay_again"):
            stocks=_tm_full_universe()[:120]; threading.Thread(target=_base_tm_replay_worker,args=(stocks,),daemon=True).start(); st.success("기존 KIS 저장본으로 상세 해부를 다시 만들고 있습니다.")

# New frozen BASE: deep-valley support touch.  This intentionally does not use
# the earlier A→B / B+3% engine or its results.
SUPPORT_TM_DIR=Path("data")/"support_touch_timemachine"
SUPPORT_TM_STATE=SUPPORT_TM_DIR/"state.json"
SUPPORT_TM_RESULT=SUPPORT_TM_DIR/"result.json"
SUPPORT_TM_TRADES=SUPPORT_TM_DIR/"trades.csv"
SUPPORT_TM_VERSION="DEEP_VALLEY_TOUCH_V2_PREV1_TO_120_20260908"

def _support_touch_anchor(h):
    """Point-in-time A: deepest confirmed pivot from yesterday back 120 sessions."""
    try:
        h=h.reset_index(drop=True)
        n=len(h)
        if n<125:return None
        end=n-3                          # keep three completed candles for pivot confirmation
        start=max(3,end-120)             # yesterday back to 120 sessions; today is never A
        piv=[i for i in _live_pivot_lows(h,3,3) if start<=i<end]
        if not piv:return None
        # The deepest confirmed valley wins; no recent shallow low may replace it.
        ai=min(piv,key=lambda i:float(h.loc[i,"low"]))
        a=float(h.loc[ai,"low"])
        # It must have produced a meaningful rebound before today's retest.
        rebound=float(h.iloc[ai+1:-1].high.astype(float).max()/a-1)*100
        if rebound<5.0:return None
        return {"i":int(ai),"date":str(pd.Timestamp(h.loc[ai,"date"]).date()),
                "low":a,"age":int(n-1-ai),"rebound_pct":round(rebound,2)}
    except Exception:return None

def _support_touch_signal(h, stock):
    """A~A+3% only.  Any intraday break of A rejects the setup."""
    try:
        if h is None or len(h)<125:return None
        a=_support_touch_anchor(h)
        if not a:return None
        row=h.iloc[-1]
        A=float(a["low"]); low=float(row.low); op=float(row.open); close=float(row.close)
        cap=krx_ceil_price(A*1.03)
        # A single tick below A invalidates the entire day.  A gap below A too.
        if low<A or op<A:return None
        # The day must actually visit the permitted buy zone; no chasing above it.
        if low>cap:return None
        # Limit-order execution: open inside the zone fills at open; otherwise at cap.
        entry=op if A<=op<=cap else cap
        if entry<A or entry>cap:return None
        hist=h.iloc[:-1]
        vbase=float(hist.volume.astype(float).tail(20).median()) if len(hist)>=20 else 0.0
        typ=(hist.high.astype(float)+hist.low.astype(float)+hist.close.astype(float))/3
        vol=hist.volume.astype(float).clip(lower=0)
        total=max(float(vol.tail(120).sum()),1.0)
        support_share=float(vol.tail(120)[(typ.tail(120)>=A*.97)&(typ.tail(120)<=A*1.03)].sum()/total)
        overhead_share=float(vol.tail(120)[(typ.tail(120)>=entry)&(typ.tail(120)<=entry*1.10)].sum()/total)
        retests=int(((hist.low.astype(float).tail(60)>=A)&(hist.low.astype(float).tail(60)<=A*1.03)).sum())
        return {"stock":stock,"A":a,"signal_date":str(pd.Timestamp(row.date).date()),
                "entry":float(entry),"entry_cap":float(cap),
                "entry_premium_pct":round((entry/A-1)*100,3),
                "volume_ratio":round(float(row.volume)/vbase,3) if vbase>0 else 0.0,
                "support_share":round(support_share,4),"overhead_share":round(overhead_share,4),"retests":retests}
    except Exception:return None

def _support_touch_sim(full, signal_index, setup):
    """No same-day target assumption: daily OHLC cannot order low then high safely."""
    try:
        A=float(setup["A"]["low"]); entry=float(setup["entry"]); target=krx_ceil_price(entry*1.10)
        fut=full.iloc[signal_index+1:signal_index+16].reset_index(drop=True)
        if len(fut)<15:return None
        exit_px=float(fut.close.iloc[-1]); outcome="TIMEOUT"; exit_date=str(pd.Timestamp(fut.date.iloc[-1]).date()); days=15
        for j,r in fut.iterrows():
            op,hi,lo=map(float,(r.open,r.high,r.low))
            d=str(pd.Timestamp(r.date).date())
            # The user's rule is intraday invalidation.  Gaps are exited at open.
            if op<A:
                outcome="GAP_STOP"; exit_px=op; exit_date=d; days=j+1; break
            if lo<A:
                outcome="INTRADAY_STOP"; exit_px=A; exit_date=d; days=j+1; break
            if op>=target or hi>=target:
                outcome="TARGET"; exit_px=target; exit_date=d; days=j+1; break
        return {"outcome":outcome,"exit":exit_px,"exit_date":exit_date,"days":days,
                "net_pct":round((exit_px/entry-1)*100-0.35,3)}
    except Exception:return None

def _support_touch_replay_worker(stocks):
    state={"phase":"REPLAY","done":0,"total":len(stocks),"error":"","version":SUPPORT_TM_VERSION}; _vg_write(SUPPORT_TM_STATE,state)
    choices={}
    try:
        for n,x in enumerate(stocks,1):
            p=_tm_daily_cache_path(x["code"])
            if p.exists():
                d=pd.read_csv(p,parse_dates=["date"]).sort_values("date").reset_index(drop=True)
                for i in range(124,len(d)-15):
                    z=_support_touch_signal(d.iloc[i-124:i+1].reset_index(drop=True),x)
                    if z: choices.setdefault(z["signal_date"],[]).append(z)
            state.update({"done":n,"last":x.get("name",x["code"])}); _vg_write(SUPPORT_TM_STATE,state)
        trades=[]; occupied_until=None; skipped_while_held=0
        for day in sorted(choices):
            # One account, one position: later signals while holding are not counted.
            if occupied_until and pd.Timestamp(day)<=pd.Timestamp(occupied_until):
                skipped_while_held+=len(choices[day]); continue
            z=sorted(choices[day],key=lambda q:(q["entry_premium_pct"],-q["volume_ratio"],q["stock"]["code"]))[0]
            full=pd.read_csv(_tm_daily_cache_path(z["stock"]["code"]),parse_dates=["date"]).sort_values("date").reset_index(drop=True)
            k=full.index[full.date.dt.normalize()==pd.Timestamp(day)].tolist()
            if not k:continue
            sim=_support_touch_sim(full,k[-1],z)
            if not sim:continue
            occupied_until=sim["exit_date"]
            trades.append({"date":day,"code":str(z["stock"]["code"]).zfill(6),"name":z["stock"].get("name",""),
                           "A_date":z["A"]["date"],"A":z["A"]["low"],"A_age":z["A"]["age"],
                           "entry":z["entry"],"entry_cap":z["entry_cap"],"entry_premium_pct":z["entry_premium_pct"],
                           "support_share":z["support_share"],"overhead_share":z["overhead_share"],"retests":z["retests"],
                           "outcome":sim["outcome"],"exit":sim["exit"],"exit_date":sim["exit_date"],"days":sim["days"],"net_pct":sim["net_pct"]})
        q=pd.DataFrame(trades)
        result={"status":"HOLD","version":SUPPORT_TM_VERSION,
                "scope":"현재 KIS 종목풀 후향 재현 · 단일 보유 · 과거 상장폐지 종목 미포함",
                "signals":len(q),"raw_signal_days":len(choices),"skipped_while_held":skipped_while_held,
                "target_rate_pct":round(float((q.outcome=="TARGET").mean()*100),2) if len(q) else None,
                "stop_rate_pct":round(float(q.outcome.isin(["GAP_STOP","INTRADAY_STOP"]).mean()*100),2) if len(q) else None,
                "mean_net_pct":round(float(q.net_pct.mean()),3) if len(q) else None,
                "worst_net_pct":round(float(q.net_pct.min()),3) if len(q) else None}
        SUPPORT_TM_DIR.mkdir(parents=True,exist_ok=True)
        if not q.empty:q.to_csv(SUPPORT_TM_TRADES,index=False,encoding="utf-8-sig")
        _vg_write(SUPPORT_TM_RESULT,result); state.update({"phase":"DONE"}); _vg_write(SUPPORT_TM_STATE,state)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(SUPPORT_TM_STATE,state)

def _support_touch_collect_worker(stocks,warm,end,token):
    state={"phase":"COLLECTING","done":0,"total":len(stocks),"error":"","version":SUPPORT_TM_VERSION}; _vg_write(SUPPORT_TM_STATE,state)
    try:
        for n,x in enumerate(stocks,1):
            _ad5_extend_one(x,warm,end,token)
            state.update({"done":n,"last":x.get("name",x["code"])}); _vg_write(SUPPORT_TM_STATE,state)
        state.update({"phase":"READY"}); _vg_write(SUPPORT_TM_STATE,state)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(SUPPORT_TM_STATE,state)

def _support_touch_full_worker(stocks,warm,end,token):
    """One click: finish collection first, then replay without another action."""
    import threading
    state={"phase":"COLLECTING","done":0,"total":len(stocks),"error":"","version":SUPPORT_TM_VERSION}; _vg_write(SUPPORT_TM_STATE,state)
    try:
        for n,x in enumerate(stocks,1):
            # KIS may occasionally stop responding for one code.  Do not let one
            # request leave the entire 600-stock job looking like infinite loading.
            box={}
            def _one():
                try: box["result"]=_ad5_extend_one(x,warm,end,token)
                except Exception as exc: box["error"]=type(exc).__name__
            t=threading.Thread(target=_one,daemon=True); t.start()
            waited=0
            while t.is_alive() and waited<90:
                t.join(5); waited+=5
                state.update({"done":n-1,"last":x.get("name",x["code"]),"waiting_seconds":waited,
                              "heartbeat":now_kst().strftime("%H:%M:%S")}); _vg_write(SUPPORT_TM_STATE,state)
            if t.is_alive():
                state.setdefault("skipped",[]).append(str(x["code"]).zfill(6))
            elif box.get("error"):
                state.setdefault("skipped",[]).append(str(x["code"]).zfill(6))
            state.update({"done":n,"last":x.get("name",x["code"]),"waiting_seconds":0,
                          "heartbeat":now_kst().strftime("%H:%M:%S")}); _vg_write(SUPPORT_TM_STATE,state)
        _support_touch_replay_worker(stocks)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(SUPPORT_TM_STATE,state)

def _render_support_touch_timemachine():
    import threading
    st.divider(); st.subheader("🧪 새 BASE · 깊은 계곡 전저점 지지 검증")
    st.caption("A~A+3%에서만 매수 · 장중 A 이탈 즉시 손절 · +10% 매도 · 15거래일 · 단일 보유. 이전 A→B 결과와 섞지 않습니다.")
    state=_vg_read(SUPPORT_TM_STATE) or {"phase":"미실행"}; phase=state.get("phase","미실행")
    st.write(f"상태: **{phase}** · {state.get('done',0)} / {state.get('total',0)}" + (f" · {state.get('last')}" if state.get('last') else ""))
    if state.get("waiting_seconds"):
        st.caption(f"현재 종목 응답 대기 {state['waiting_seconds']}초 · 90초가 지나면 자동으로 건너뛰고 계속합니다.")
    if phase in ("미실행","ERROR","DONE") and st.button("한 번에 수집·새 BASE 검증 시작",key="support_touch_full"):
        if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
        else:
            stocks=_tm_full_universe()[:600]; start,end,warm=_ad5_dates(); token=kis_access_token()
            threading.Thread(target=_support_touch_full_worker,args=(stocks,warm,end,token),daemon=True).start(); st.success("수집이 끝나면 자동으로 재현까지 이어서 실행합니다. 기다리기만 하시면 됩니다.")
    if phase in ("COLLECTING","REPLAY"):
        st.info("백그라운드에서 진행 중입니다. 응답이 멈춘 종목은 최대 90초 뒤 자동으로 건너뜁니다.")
        st.markdown('<meta http-equiv="refresh" content="10">',unsafe_allow_html=True)
    result=_vg_read(SUPPORT_TM_RESULT) if SUPPORT_TM_RESULT.exists() else {}
    if result and result.get("version")!=SUPPORT_TM_VERSION:
        st.warning("전저점 A 기준이 ‘전날~120거래일 전’으로 바뀌었습니다. 이전 성적은 새 기준 결과가 아니므로 보류합니다. 검증을 다시 시작하세요.")
        result={}
    if phase=="DONE" and result:
        a,b,c,d=st.columns(4); a.metric("단일 보유 거래",f"{result['signals']}건"); b.metric("+10% 도달",f"{result['target_rate_pct']}%"); c.metric("장중 A 이탈 손절",f"{result['stop_rate_pct']}%"); d.metric("평균 순수익",f"{result['mean_net_pct']}%")
        st.info(f"원시 신호일 {result['raw_signal_days']}일 · 보유 중 건너뜀 {result['skipped_while_held']}건 · 결과는 연구용 HOLD입니다.")
        if SUPPORT_TM_TRADES.exists():
            q=pd.read_csv(SUPPORT_TM_TRADES)
            if {"support_share","overhead_share","retests"}.issubset(q.columns):
                st.markdown("#### 추가 조건 해부 · 아직 규칙 반영 금지")
                q["A매물대"]=pd.qcut(q.support_share,3,duplicates="drop")
                q["상단매물대"]=pd.qcut(q.overhead_share,3,duplicates="drop")
                q["A재접근"]=pd.cut(q.retests,[-1,1,2,99],labels=["1회","2회","3회 이상"])
                rows=[]
                for col in ["A매물대","상단매물대","A재접근"]:
                    for label,g in q.groupby(col,observed=False):
                        rows.append({"조건":col,"구간":str(label),"거래":len(g),"평균순수익":round(float(g.net_pct.mean()),2),"목표도달률":round(float((g.outcome=='TARGET').mean()*100),2),"손절률":round(float(g.outcome.isin(['GAP_STOP','INTRADAY_STOP']).mean()*100),2)})
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
                st.caption("일봉 거래량을 가격대에 배분한 근사치입니다. 공시·수급·시장충격은 공식 과거 데이터가 연결되기 전까지 이 표에 넣지 않습니다.")
            st.dataframe(q.tail(100),use_container_width=True,hide_index=True)
            st.download_button("새 BASE 거래별 결과 CSV",q.to_csv(index=False).encode("utf-8-sig"),"deep_valley_support_touch_trades.csv","text/csv")

# Rebuilt ONE: it does not add every indicator as a hard gate.  The frozen
# deep-valley setup remains the entry rule; trend and volume structure only
# decide which one candidate deserves the day's single position.
ONE_REBUILD_DIR=Path("data")/"one_rebuild_validation"
ONE_REBUILD_STATE=ONE_REBUILD_DIR/"state.json"
ONE_REBUILD_RESULT=ONE_REBUILD_DIR/"result.json"
ONE_REBUILD_TRADES=ONE_REBUILD_DIR/"trades.csv"
ONE_REBUILD_VERSION="ONE_DEEP_SUPPORT_TREND_RANK_V1_20260920"

def _one_rebuild_features(h, setup):
    """Point-in-time features only; the signal day's future close is never used."""
    try:
        q=h.copy().sort_values("date").reset_index(drop=True)
        q["date"]=pd.to_datetime(q.date); q["close"]=pd.to_numeric(q.close,errors="coerce")
        c=q.close
        if len(q)<260: return None
        ma60=c.rolling(60).mean(); close=float(c.iat[-1])
        above_rising_60=bool(close>=float(ma60.iat[-1]) and float(ma60.iat[-1])>=float(ma60.iat[-21]))
        # Exclude the signal day: Friday intraday entries must not borrow that
        # evening's weekly close.
        prior=q.iloc[:-1].set_index("date")["close"].resample("W-FRI").last().dropna()
        if len(prior)<34: return None
        ma30=prior.rolling(30).mean()
        above_rising_30=bool(close>=float(ma30.iat[-1]) and float(ma30.iat[-1])>=float(ma30.iat[-5]))
        trend_points=int(above_rising_60)+int(above_rising_30)
        # Ranking, not an after-the-fact threshold: candidates close to A with
        # more traded support below and less overhead supply rank first.
        score=(trend_points*1000 + float(setup["support_share"])*100
               - float(setup["overhead_share"])*100 - float(setup["entry_premium_pct"])*10)
        return {"trend_points":trend_points,"above_rising_60":above_rising_60,
                "above_rising_30":above_rising_30,"one_score":round(score,5)}
    except Exception:
        return None

def _one_rebuild_replay_worker(stocks):
    state={"phase":"REPLAY","done":0,"total":len(stocks),"error":"","version":ONE_REBUILD_VERSION}; _vg_write(ONE_REBUILD_STATE,state)
    choices={}
    try:
        for n,x in enumerate(stocks,1):
            p=_tm_daily_cache_path(x["code"])
            if p.exists():
                d=pd.read_csv(p,parse_dates=["date"]).sort_values("date").reset_index(drop=True)
                for i in range(259,len(d)-15):
                    h=d.iloc[i-259:i+1].reset_index(drop=True)
                    z=_support_touch_signal(h,x)
                    if not z: continue
                    f=_one_rebuild_features(h,z)
                    if f is None: continue
                    z.update(f); choices.setdefault(z["signal_date"],[]).append(z)
            state.update({"done":n,"last":x.get("name",x["code"])}); _vg_write(ONE_REBUILD_STATE,state)
        trades=[]; occupied_until=None; skipped=0
        for day in sorted(choices):
            if occupied_until and pd.Timestamp(day)<=pd.Timestamp(occupied_until):
                skipped+=len(choices[day]); continue
            # A down/sideways candidate is never allowed to outrank a clearly
            # rising one, but the signal set itself is not shrunk by arbitrary
            # post-hoc thresholds.
            z=sorted(choices[day],key=lambda q:(q["one_score"],q["support_share"],-q["overhead_share"],-q["entry_premium_pct"],q["stock"]["code"]),reverse=True)[0]
            full=pd.read_csv(_tm_daily_cache_path(z["stock"]["code"]),parse_dates=["date"]).sort_values("date").reset_index(drop=True)
            k=full.index[full.date.dt.normalize()==pd.Timestamp(day)].tolist()
            if not k: continue
            sim=_support_touch_sim(full,k[-1],z)
            if not sim: continue
            occupied_until=sim["exit_date"]
            trades.append({"date":day,"code":str(z["stock"]["code"]).zfill(6),"name":z["stock"].get("name",""),
                "A":z["A"]["low"],"entry":z["entry"],"support_share":z["support_share"],"overhead_share":z["overhead_share"],
                "trend_points":z["trend_points"],"60일선상승":z["above_rising_60"],"30주선상승":z["above_rising_30"],
                "outcome":sim["outcome"],"days":sim["days"],"net_pct":sim["net_pct"],"exit_date":sim["exit_date"]})
        q=pd.DataFrame(trades); ONE_REBUILD_DIR.mkdir(parents=True,exist_ok=True)
        if not q.empty: q.to_csv(ONE_REBUILD_TRADES,index=False,encoding="utf-8-sig")
        result={"status":"HOLD","version":ONE_REBUILD_VERSION,"scope":"현재 KIS 종목풀 후향 재현 · 하루 ONE · 단일 보유 · 과거 상장폐지 종목 미포함",
            "signals":int(len(q)),"raw_signal_days":int(len(choices)),"skipped_while_held":int(skipped),
            "target_rate_pct":round(float((q.outcome=="TARGET").mean()*100),2) if len(q) else None,
            "stop_rate_pct":round(float(q.outcome.isin(["GAP_STOP","INTRADAY_STOP"]).mean()*100),2) if len(q) else None,
            "mean_net_pct":round(float(q.net_pct.mean()),3) if len(q) else None,
            "mean_days":round(float(q.days.mean()),2) if len(q) else None,
            "trend2_rate_pct":round(float((q.trend_points==2).mean()*100),2) if len(q) else None}
        _vg_write(ONE_REBUILD_RESULT,result); state.update({"phase":"DONE"}) ; _vg_write(ONE_REBUILD_STATE,state)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(ONE_REBUILD_STATE,state)

def _one_rebuild_full_worker(stocks,warm,end,token):
    import threading
    state={"phase":"COLLECTING","done":0,"total":len(stocks),"error":"","version":ONE_REBUILD_VERSION}; _vg_write(ONE_REBUILD_STATE,state)
    try:
        for n,x in enumerate(stocks,1):
            box={}
            def _one():
                try: box["ok"]=_ad5_extend_one(x,warm,end,token)
                except Exception as exc: box["error"]=type(exc).__name__
            t=threading.Thread(target=_one,daemon=True); t.start(); waited=0
            while t.is_alive() and waited<90:
                t.join(5); waited+=5
                state.update({"done":n-1,"last":x.get("name",x["code"]),"waiting_seconds":waited,"heartbeat":now_kst().strftime("%H:%M:%S")}); _vg_write(ONE_REBUILD_STATE,state)
            if t.is_alive() or box.get("error"): state.setdefault("skipped",[]).append(str(x["code"]).zfill(6))
            state.update({"done":n,"last":x.get("name",x["code"]),"waiting_seconds":0,"heartbeat":now_kst().strftime("%H:%M:%S")}); _vg_write(ONE_REBUILD_STATE,state)
        _one_rebuild_replay_worker(stocks)
    except Exception as e:
        state.update({"phase":"ERROR","error":type(e).__name__}); _vg_write(ONE_REBUILD_STATE,state)

def _render_one_rebuild_lab():
    import threading
    st.divider(); st.subheader("🧭 ONE 재건 · 깊은 지지 + 추세 우선순위")
    st.caption("전저점 A 지지는 고정합니다. 60일선·30주선의 상승 여부와 A 부근/상단 매물 구조로 같은 날 후보 중 ONE만 고릅니다. 실패한 10일선·피보나치·반등확인 규칙은 넣지 않습니다.")
    state=_vg_read(ONE_REBUILD_STATE) or {"phase":"미실행"}; phase=state.get("phase","미실행")
    st.write(f"상태: **{phase}** · {state.get('done',0)} / {state.get('total',0)}" + (f" · {state.get('last')}" if state.get('last') else ""))
    if phase in ("미실행","ERROR","DONE") and st.button("ONE 재건 검증 시작",type="primary",key="one_rebuild_start"):
        if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
        else:
            stocks=_tm_full_universe()[:600]; start,end,warm=_ad5_dates(); token=kis_access_token()
            threading.Thread(target=_one_rebuild_full_worker,args=(stocks,warm,end,token),daemon=True).start()
            st.success("수집 후 검증까지 자동으로 이어집니다. 한 번만 누르고 기다리시면 됩니다.")
    if phase in ("COLLECTING","REPLAY"):
        st.info("백그라운드 검증 중입니다. 응답이 멈춘 종목은 90초 뒤 건너뜁니다.")
        st.markdown('<meta http-equiv="refresh" content="10">',unsafe_allow_html=True)
    result=_vg_read(ONE_REBUILD_RESULT) if ONE_REBUILD_RESULT.exists() else {}
    if phase=="ERROR": st.error(f"검증 오류: {state.get('error','원인 미확인')}")
    if phase=="DONE" and result.get("version")==ONE_REBUILD_VERSION:
        a,b,c,d=st.columns(4); a.metric("단일 보유 거래",f"{result.get('signals',0)}건"); b.metric("+10% 도달",f"{result.get('target_rate_pct')}%"); c.metric("A 손절",f"{result.get('stop_rate_pct')}%"); d.metric("평균 순수익",f"{result.get('mean_net_pct')}%")
        st.info(f"상승 추세 2점 비중 {result.get('trend2_rate_pct')}% · 평균 보유 {result.get('mean_days')}일 · 결과는 검증 통과 전 연구용 HOLD입니다.")
        base=_vg_read(SUPPORT_TM_RESULT) if SUPPORT_TM_RESULT.exists() else {}
        if base.get("version")==SUPPORT_TM_VERSION:
            st.markdown("#### 고정 BASE와 비교")
            st.dataframe(pd.DataFrame([
                {"조건":"고정 BASE","거래":base.get("signals"),"+10%도달률":base.get("target_rate_pct"),"손절률":base.get("stop_rate_pct"),"평균순수익":base.get("mean_net_pct")},
                {"조건":"ONE 재건","거래":result.get("signals"),"+10%도달률":result.get("target_rate_pct"),"손절률":result.get("stop_rate_pct"),"평균순수익":result.get("mean_net_pct")},
            ]),use_container_width=True,hide_index=True)
        if ONE_REBUILD_TRADES.exists():
            q=pd.read_csv(ONE_REBUILD_TRADES)
            st.dataframe(q.tail(100),use_container_width=True,hide_index=True)
            st.download_button("ONE 재건 거래별 CSV",q.to_csv(index=False).encode("utf-8-sig"),"one_rebuild_trades.csv","text/csv")

MA10_CANDIDATE_DIR=Path("data")/"ma10_close_touch_candidates"
MA10_CANDIDATE_RESULT=MA10_CANDIDATE_DIR/"result.json"
MA10_CANDIDATE_CSV=MA10_CANDIDATE_DIR/"candidates.csv"
MA10_CANDIDATE_VERSION="MONTHLY_WEEKLY_DAILY_MA10_STAGE_CANDIDATES_V3_20260910"
TREND_LOOKBACK=150
MEANINGFUL_BREAK_PCT=3.0

def _close_hull(points, upper=True):
    """Keep only the outer closing-price peaks (upper) or troughs (lower)."""
    hull=[]
    for p in points:
        while len(hull)>=2:
            a,b=hull[-2],hull[-1]
            cross=(b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0])
            if (upper and cross>=0) or ((not upper) and cross<=0): hull.pop()
            else: break
        hull.append(p)
    return hull

def _line_at_last_bar(hull, bar_index):
    if len(hull)<2: return None,None
    a,b=hull[-2],hull[-1]
    slope=(b[1]-a[1])/(b[0]-a[0])
    return b[1]+slope*(bar_index-b[0]),slope

def _close_trend_state(closes):
    """Classify today's state from yesterday's 150-day close-only trendlines."""
    past=np.asarray(closes[-(TREND_LOOKBACK+1):-1],dtype=float)
    if len(past)!=TREND_LOOKBACK or not np.isfinite(past).all(): return None,None,None
    points=[(i,float(v)) for i,v in enumerate(past)]
    today=float(closes[-1]); today_x=TREND_LOOKBACK
    resistance,res_slope=_line_at_last_bar(_close_hull(points,upper=True),today_x)
    support,sup_slope=_line_at_last_bar(_close_hull(points,upper=False),today_x)
    # A downtrend becomes a transition only after a meaningful close, not a tiny touch.
    if resistance is not None and res_slope<0 and today>=resistance*(1+MEANINGFUL_BREAK_PCT/100):
        return "추세전환",resistance,(today/resistance-1)*100
    # An uptrend is retained while its close-based rising support is not broken.
    if support is not None and sup_slope>0 and today>=support:
        return "상승장",support,(today/support-1)*100
    return None,None,None

def _last_completed_months(h):
    """Exclude the still-forming current month; use only confirmed monthly closes."""
    month_now=pd.Period(now_kst().date(),freq="M")
    d=h.loc[h.date.dt.to_period("M")<month_now,["date","close"]].copy()
    if d.empty: return pd.Series(dtype=float)
    return d.set_index("date")["close"].resample("ME").last().dropna()

def _ma10_close_touch_candidates():
    """Only clear multi-timeframe uptrends may use the daily MA10 entry touch."""
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}
    try:
        names={str(z["code"]).zfill(6):z.get("name","") for z in _tm_full_universe()}
    except Exception:
        names={}
    rows=[]; final_rows=[]
    def _rising_touch(series, lookback, min_ma_rise):
        if len(series)<10+lookback: return None
        close=float(series.iat[-1]); prior=float(series.iat[-2]); ma=float(series.rolling(10).mean().iat[-1]); prior_ma=float(series.rolling(10).mean().iat[-2])
        gap=(ma/close-1)*100 if close>0 else 999
        ma_rise=(ma/float(series.rolling(10).mean().iat[-1-lookback])-1)*100
        # A pullback may be red, but the 10-line itself must be clearly rising.
        if 0<=gap<=1.0 and ma_rise>=min_ma_rise and ma>=prior_ma: return close,ma,gap,ma_rise
        return None
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"]).sort_values("date").reset_index(drop=True)
            h["close"]=pd.to_numeric(h["close"],errors="coerce")
            h=h.dropna(subset=["close"])
            if len(h)<260: continue
            monthly=_last_completed_months(h)
            weekly=h.loc[h.date.dt.to_period("W-FRI")<pd.Period(now_kst().date(),freq="W-FRI")].set_index("date")["close"].resample("W-FRI").last().dropna()
            daily=h.set_index("date")["close"]
            current=float(daily.iat[-1])
            if not 5000<=current<=50000: continue
            month_hit=_rising_touch(monthly,3,1.5)
            week_hit=_rising_touch(weekly,4,1.0)
            day_hit=_rising_touch(daily,10,1.0)
            for stage,hit,series in (("1단계 · 월봉 상승 후보",month_hit,monthly),("2단계 · 주봉 상승 후보",week_hit,weekly),("3단계 · 일봉 상승 후보",day_hit,daily)):
                if hit is None: continue
                close,ma,gap,ma_rise=hit
                rows.append({"단계":stage,"종목코드":str(code).zfill(6),"종목명":names.get(str(code).zfill(6),""),"기준 종가":int(round(close)),"10선":round(ma,1),"10선까지 차이(%)":round(gap,2),"10선 기울기(%)":round(ma_rise,2),"기준일":str(series.index[-1].date())})
            # The sequence is not three unrelated lists: the same stock must
            # pass monthly and weekly direction before a daily entry appears.
            if not (month_hit and week_hit and day_hit): continue
            close,ma,gap,ma_rise=day_hit
            final_rows.append({"단계":"3단계 · 일봉 최종 진입 후보","종목코드":str(code).zfill(6),"종목명":names.get(str(code).zfill(6),""),
                         "기준 종가":int(round(close)),"일봉 10일선":round(ma,1),"일봉 차이(%)":round(gap,2),
                         "월봉 10선 기울기(3개월%)":round(month_hit[3],2),"주봉 10선 기울기(4주%)":round(week_hit[3],2),"일봉 10선 기울기(10일%)":round(ma_rise,2),"기준일":str(daily.index[-1].date())})
        except Exception:
            pass
    q=pd.DataFrame(rows)
    if not q.empty:
        q=q.sort_values(["단계","10선까지 차이(%)","종목코드"])
    MA10_CANDIDATE_DIR.mkdir(parents=True,exist_ok=True)
    result={"version":MA10_CANDIDATE_VERSION,"count":int(len(q)),"final_count":int(len(final_rows)),"final_candidates":final_rows,"scanned":len(paths),
            "scope":"횡보·하락 제외 · 같은 종목이 월봉 10선 3개월 +1.5% 이상, 주봉 10선 4주 +1.0% 이상, 일봉 10선 10일 +1.0% 이상 상승하며 각 종가가 10선 아래 1% 이내일 때만 일봉 최종 진입 후보 · 종가 5,000~50,000원"}
    _vg_write(MA10_CANDIDATE_RESULT,result)
    if q.empty:
        # Do not display candidates from an older, looser scan.
        MA10_CANDIDATE_CSV.unlink(missing_ok=True)
    else:
        q.to_csv(MA10_CANDIDATE_CSV,index=False,encoding="utf-8-sig")
    return result,q

def _render_ma10_touch_candidates():
    st.subheader("📈 전략 2 · 10선 추세전환 매수·매도")
    st.caption("횡보·하락은 제외합니다. 월봉→주봉→일봉 후보를 단계별로 보여주며, 같은 종목이 세 단계를 모두 통과할 때만 ‘일봉 최종 진입 후보’가 됩니다.")
    if st.button("월·주·일 10선 순차 후보 찾기",key="ma10_candidate_start"):
        with st.spinner("저장된 일봉으로 월·주·일 10선 후보를 찾는 중입니다..."):
            _ma10_close_touch_candidates()
        st.rerun()
    result=_vg_read(MA10_CANDIDATE_RESULT) if MA10_CANDIDATE_RESULT.exists() else {}
    if not result or result.get("version")!=MA10_CANDIDATE_VERSION: return
    st.info(f"{result.get('scope','')} · {result.get('scanned',0)}개 종목 중 단계 후보 {result.get('count',0)}개 · 최종 진입 {result.get('final_count',0)}개")
    if result.get("count",0)==0:
        st.warning("현재 기준에서는 횡보를 제외한 10선 후보가 없습니다.")
        return
    if not MA10_CANDIDATE_CSV.exists(): return
    q=pd.read_csv(MA10_CANDIDATE_CSV)
    if q.empty:
        st.warning("현재 저장 일봉 기준 조건에 맞는 종목이 없습니다.")
        return
    st.dataframe(q,use_container_width=True,hide_index=True)
    finals=pd.DataFrame(result.get("final_candidates",[]))
    st.markdown("#### 최종 진입 후보")
    if finals.empty:
        st.info("세 단계를 같은 종목으로 모두 통과한 최종 진입 후보는 아직 없습니다. 위 단계 후보를 순서대로 추적합니다.")
    else:
        st.dataframe(finals,use_container_width=True,hide_index=True)
    st.download_button("월·주·일 10선 순차 후보 CSV",q.to_csv(index=False).encode("utf-8-sig"),"ma10_sequence_candidates.csv","text/csv")

PRIORLOW_LAB_DIR=Path("data")/"prior_low_rejudge_validation"
PRIORLOW_LAB_RESULT=PRIORLOW_LAB_DIR/"result.json"
PRIORLOW_LAB_TRADES=PRIORLOW_LAB_DIR/"trades.csv"
PRIORLOW_LAB_VERSION="PRIORLOW_REJUDGE_120DAY_LIMIT_1TO3_TARGET10_V5_20260909"
PRIORLOW_FIB_RESULT=PRIORLOW_LAB_DIR/"fibonacci_result.json"
PRIORLOW_FIB_TRADES=PRIORLOW_LAB_DIR/"fibonacci_trades.csv"
PRIORLOW_FIB_VERSION="PRIORLOW_FIB_RETRACE_382_500_618_V2_TIME_SPLIT_20260909"
PRIORLOW_CONFIRM_RESULT=PRIORLOW_LAB_DIR/"confirmation_result.json"
PRIORLOW_CONFIRM_VERSION="PRIORLOW_CONFIRM_REBOUND_1_2_3_V1_20260909"
PRIORLOW_ALIGNMENT_RESULT=PRIORLOW_LAB_DIR/"full_alignment_result.json"
PRIORLOW_ALIGNMENT_VERSION="PRIORLOW_FULL_BULLISH_ALIGNMENT_V1_20260916"
BREAKOUT_LAB_RESULT=PRIORLOW_LAB_DIR/"trend_breakout_result.json"
BREAKOUT_LAB_VERSION="TREND_30W_BASE_VOLUME_BREAKOUT_V1_20260916"
PULLBACK_LAB_RESULT=PRIORLOW_LAB_DIR/"trend_pullback_result.json"
PULLBACK_LAB_VERSION="TREND_30W_MA10_PULLBACK_V1_20260916"
WEEK30_LAB_RESULT=PRIORLOW_LAB_DIR/"week30_trend_result.json"
WEEK30_LAB_VERSION="WEEK30_CROSS_EXIT_V1_20260916"
WEEK30_FILTER_RESULT=PRIORLOW_LAB_DIR/"priorlow_week30_filter_result.json"
WEEK30_FILTER_VERSION="PRIORLOW_A1_WEEK30_RISING_FILTER_V1_20260920"

# Results must never be improved by choosing exclusions after seeing them.
# These dates are registered before the run as market-wide abnormal-event days.
MARKET_SHOCK_DATES={"2024-12-04"}  # emergency-martial-law market shock
def _parse_excluded_dates(text):
    found=re.findall(r"\b\d{4}-\d{2}-\d{2}\b",str(text or ""))
    out=[]
    for day in found:
        try:
            if pd.Timestamp(day).strftime("%Y-%m-%d")==day and day not in out: out.append(day)
        except Exception: pass
    return set(out)

def _surviving_prior_low(h, i):
    """Newest unbroken trough; if it broke, automatically fall back to an older trough."""
    lows=h.low.to_numpy(dtype=float); highs=h.high.to_numpy(dtype=float)
    # First use the agreed prior-day~120-trading-day window.  Only if every
    # candidate there has already broken do we extend back to find B/C support.
    for span in (120,360):
        start=max(4,i-span); anchors=[]
        for j in range(start,i-3):
            if lows[j]<=np.min(lows[j-3:j]) and lows[j]<=np.min(lows[j+1:j+4]):
                anchors.append(j)
        for j in reversed(anchors):
            a=float(lows[j])
            if np.min(lows[j+1:i]) < a: continue
            if np.max(highs[j+1:i]) <= a: continue  # any rebound is enough; no strength test
            return j,a
    return None,None

def _priorlow_events(d, code, excluded_dates=None):
    try:
        h=d.copy().sort_values("date").reset_index(drop=True)
        for col in ("open","high","low","close"): h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["open","high","low","close"]).reset_index(drop=True)
        code=str(code).zfill(6); excluded_dates=excluded_dates or set()
        rows=[]; i=125; n=len(h)
        while i<n-16:
            signal_date=str(pd.Timestamp(h.date.iat[i]).date())
            if signal_date in excluded_dates:
                i+=1; continue
            a_idx,a=_surviving_prior_low(h,i)
            if a is None or float(h.low.iat[i])<a or float(h.low.iat[i])>a*1.03 or not float(h.close.iat[i])>float(h.open.iat[i]):
                i+=1; continue
            limit=a*1.01; cap=a*1.03; op,hi=float(h.open.iat[i]),float(h.high.iat[i])
            if op>cap: i+=1; continue
            if float(h.low.iat[i])<=limit<=hi: entry=limit
            elif limit<=op<=cap: entry=op
            else: i+=1; continue
            exit_i=None; outcome="TIMEOUT"; exit_px=float(h.close.iat[min(i+15,n-1)])
            for j in range(i+1,min(i+16,n)):
                o,hh,ll,c=map(float,(h.open.iat[j],h.high.iat[j],h.low.iat[j],h.close.iat[j]))
                if o<a or ll<a:
                    exit_i=j; outcome="INTRADAY_STOP"; exit_px=o if o<a else a; break
                if hh>=entry*1.10:
                    exit_i=j; outcome="TARGET"; exit_px=entry*1.10; break
            if exit_i is None: exit_i=min(i+15,n-1)
            gross=(exit_px/entry-1)*100; held=h.iloc[i:exit_i+1]
            rows.append({"signal_date":signal_date,"code":code,
                         "A_date":str(pd.Timestamp(h.date.iat[a_idx]).date()),"A":round(a,2),"entry":round(entry,2),
                         "entry_premium_pct":round((entry/a-1)*100,2),"outcome":outcome,
                         "exit_date":str(pd.Timestamp(h.date.iat[exit_i]).date()),"exit":round(exit_px,2),
                         "days":int(exit_i-i),"net_pct":round(gross-0.35,3),
                         "max_runup_pct":round((float(held.high.max())/entry-1)*100,3),
                         "max_drawdown_pct":round((float(held.low.min())/entry-1)*100,3)})
            i=exit_i+1
        return rows
    except Exception:
        return []

def _run_priorlow_lab(excluded_dates=None):
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES); rows=[]
    for code,p in sorted(paths.items()):
        try: rows.extend(_priorlow_events(pd.read_csv(p,parse_dates=["date"]),code,excluded_dates))
        except Exception: pass
    q=pd.DataFrame(rows)
    PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    result={"version":PRIORLOW_LAB_VERSION,"stocks":len(paths),"trades":int(len(q)),
            "scope":"전날~120거래일의 살아남은 전저점 · A 이탈 시 최대 360거래일로 확장해 더 과거 전저점 재판정 · A+1% 지정가, A+3% 초과 추격 제외 · 장중 A 이탈 손절 · +10% 목표, 최대 15거래일 · 시장 충격일 제외" ,
            "market_shock_dates":sorted(excluded_dates)}
    if not q.empty:
        result["summary"]={"+10%도달률":round(float((q.outcome=='TARGET').mean()*100),2),"손절률":round(float((q.outcome=='INTRADAY_STOP').mean()*100),2),"평균순수익":round(float(q.net_pct.mean()),2),"평균보유일":round(float(q.days.mean()),1)}
        q.to_csv(PRIORLOW_LAB_TRADES,index=False,encoding="utf-8-sig")
    _vg_write(PRIORLOW_LAB_RESULT,result)

def _fib_retrace_at_a(h, a_date, a, entry):
    """A must sit at a 38.2/50/61.8% retracement of the prior rising swing."""
    try:
        h=h.copy().sort_values("date").reset_index(drop=True)
        h["date"]=pd.to_datetime(h["date"])
        a_idx=int(h.index[h.date.eq(pd.Timestamp(a_date))][0])
        if a_idx<25: return None
        lo=pd.to_numeric(h.low,errors="coerce").to_numpy(float)
        hi=pd.to_numeric(h.high,errors="coerce").to_numpy(float)
        start=max(3,a_idx-120); peaks=[]
        for j in range(start+3,a_idx-3):
            if hi[j]>=np.max(hi[j-3:j]) and hi[j]>=np.max(hi[j+1:j+4]): peaks.append(j)
        # Use the nearest prior meaningful peak, not a future high or a chosen
        # peak that makes the result look best.
        for peak in reversed(peaks):
            low_idx=start+int(np.argmin(lo[start:peak+1])); low=float(lo[low_idx]); high=float(hi[peak])
            if low<=0 or high/low<1.15: continue
            levels={"38.2%":high-(high-low)*.382,"50.0%":high-(high-low)*.5,"61.8%":high-(high-low)*.618}
            level,gap=min(levels.items(),key=lambda x:abs(float(a)/x[1]-1))
            if abs(float(a)/gap-1)<=.02 and high>=float(entry)*1.10:
                return {"fib_level":level,"fib_low":round(low,2),"fib_high":round(high,2),"fib_gap_pct":round((float(a)/gap-1)*100,2)}
        return None
    except Exception:
        return None

def _priorlow_summary(q):
    if q.empty: return {"거래":0}
    return {"거래":int(len(q)),"+10%도달률":round(float((q.outcome=="TARGET").mean()*100),2),
            "손절률":round(float((q.outcome=="INTRADAY_STOP").mean()*100),2),
            "평균순수익":round(float(q.net_pct.mean()),2),"평균보유일":round(float(q.days.mean()),1)}

def _priorlow_time_split(base, fib):
    """Three chronological blocks; cut points come from the full base sample only."""
    if base.empty: return [],"표본 없음"
    b=base.copy(); b["signal_date"]=pd.to_datetime(b.signal_date)
    f=fib.copy(); f["signal_date"]=pd.to_datetime(f.signal_date) if not f.empty else pd.Series(dtype="datetime64[ns]")
    c1,c2=b.signal_date.quantile([1/3,2/3]).tolist()
    blocks=[("앞 구간",None,c1),("중간 구간",c1,c2),("최근 구간",c2,None)]
    rows=[]; passed=True
    for label,left,right in blocks:
        mask=pd.Series(True,index=b.index)
        if left is not None: mask &= b.signal_date>left
        if right is not None: mask &= b.signal_date<=right
        base_part=b[mask]
        fmask=pd.Series(True,index=f.index)
        if left is not None: fmask &= f.signal_date>left
        if right is not None: fmask &= f.signal_date<=right
        fib_part=f[fmask]
        bs=_priorlow_summary(base_part); fs=_priorlow_summary(fib_part)
        good=(fs.get("거래",0)>=100 and fs.get("평균순수익",-999)>=bs.get("평균순수익",999) and fs.get("손절률",999)<=bs.get("손절률",-999))
        passed &= good
        rows.append({"구간":label,"기준 거래":bs.get("거래",0),"피보 거래":fs.get("거래",0),
                     "기준 평균순수익":bs.get("평균순수익",0),"피보 평균순수익":fs.get("평균순수익",0),
                     "기준 손절률":bs.get("손절률",0),"피보 손절률":fs.get("손절률",0),
                     "판정":"통과" if good else "보류"})
    return rows,"3구간 모두 표본 100건 이상·평균순수익 개선·손절률 악화 없음" if passed else "아직 3구간 동시 통과 아님"

def _full_bullish_alignment(h, signal_date):
    """Close-only complete bullish alignment at the actual signal date, no future bars."""
    try:
        q=h.copy().sort_values("date").reset_index(drop=True)
        q["date"]=pd.to_datetime(q["date"]); q["close"]=pd.to_numeric(q["close"],errors="coerce")
        i=int(q.index[q.date.eq(pd.Timestamp(signal_date))][0])
        if i<199: return False
        c=q.close.iloc[:i+1]
        ma=[float(c.rolling(n).mean().iat[-1]) for n in (5,20,60,120,200)]
        return bool(float(c.iat[-1])>ma[0]>ma[1]>ma[2]>ma[3]>ma[4])
    except Exception:
        return False

def _run_priorlow_alignment_lab(excluded_dates=None):
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES)
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}
    base=[]; aligned=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"])
            events=_priorlow_events(h,code,excluded_dates)
            base.extend(events)
            aligned.extend(row for row in events if _full_bullish_alignment(h,row["signal_date"]))
        except Exception: pass
    q_base=pd.DataFrame(base); q_aligned=pd.DataFrame(aligned)
    comparison=[dict({"조건":"기존 전저점"},**_priorlow_summary(q_base)),dict({"조건":"+ 완전 정배열"},**_priorlow_summary(q_aligned))]
    time_split,verdict=_priorlow_time_split(q_base,q_aligned)
    PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    _vg_write(PRIORLOW_ALIGNMENT_RESULT,{"version":PRIORLOW_ALIGNMENT_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),"comparison":comparison,"time_split":time_split,"time_split_verdict":verdict,"definition":"전저점 신호 당일 종가가 5일선 > 20일선 > 60일선 > 120일선 > 200일선 위에 있는 완전 정배열일 때만 통과합니다. 이 정배열 필터만 추가하고 진입·손절·목표·보유기간은 기존 전저점 검증과 동일하게 유지합니다."})

def _breakout_records(h, code, excluded_dates=None):
    """Independent trend strategy: rising 30-week MA, tight base, volume-backed close breakout."""
    try:
        h=h.copy().sort_values("date").reset_index(drop=True)
        for col in ("high","low","close","volume"): h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["high","low","close","volume"]).reset_index(drop=True)
        rows=[]; excluded_dates=excluded_dates or set(); i=155; n=len(h)
        while i<n-16:
            day=str(pd.Timestamp(h.date.iat[i]).date())
            if day in excluded_dates or not 5000<=float(h.close.iat[i])<=50000:
                i+=1; continue
            past=h.iloc[:i+1].set_index("date")["close"].resample("W-FRI").last().dropna()
            if len(past)<34: i+=1; continue
            ma30=float(past.rolling(30).mean().iat[-1]); ma30_old=float(past.rolling(30).mean().iat[-5])
            base=h.iloc[i-20:i]; recent=h.iloc[i-10:i]; early=h.iloc[i-20:i-10]
            base_low=float(base.low.min()); base_high=float(base.high.max())
            base_range=base_high/base_low-1; recent_range=float(recent.high.max()/recent.low.min()-1); early_range=float(early.high.max()/early.low.min()-1)
            entry=float(h.close.iat[i]); volume_ratio=float(h.volume.iat[i]/h.volume.iloc[i-50:i].mean()) if h.volume.iloc[i-50:i].mean()>0 else 0
            if not (entry>ma30 and ma30>ma30_old and base_range<=.15 and recent_range<=early_range and entry>base_high and volume_ratio>=1.5 and (entry/base_low-1)<=.07):
                i+=1; continue
            future=h.iloc[i+1:i+16]
            if len(future)<15: break
            rows.append({"signal_date":day,"code":str(code).zfill(6),"entry":round(entry,2),"base_low":round(base_low,2),"risk_to_base_pct":round((entry/base_low-1)*100,2),"volume_ratio":round(volume_ratio,2),"ret15_pct":round((float(future.close.iat[-1])/entry-1)*100-.35,3),"max_runup_pct":round((float(future.high.max())/entry-1)*100,3),"max_drawdown_pct":round((float(future.low.min())/entry-1)*100,3),"base_break_pct":round((float(future.low.min())/base_low-1)*100,3)})
            i+=16
        return rows
    except Exception: return []

def _breakout_summary(q):
    if q.empty: return {"거래":0}
    return {"거래":int(len(q)),"15일 평균수익":round(float(q.ret15_pct.mean()),2),"+10%도달률":round(float((q.max_runup_pct>=10).mean()*100),2),"+20%도달률":round(float((q.max_runup_pct>=20).mean()*100),2),"+30%도달률":round(float((q.max_runup_pct>=30).mean()*100),2),"-5%도달률":round(float((q.max_drawdown_pct<=-5).mean()*100),2),"-7%도달률":round(float((q.max_drawdown_pct<=-7).mean()*100),2),"베이스이탈률":round(float((q.base_break_pct<0).mean()*100),2)}

def _breakout_time_split(q):
    if q.empty: return []
    z=q.copy(); z["signal_date"]=pd.to_datetime(z.signal_date); c1,c2=z.signal_date.quantile([1/3,2/3]).tolist(); rows=[]
    for label,left,right in (("앞 구간",None,c1),("중간 구간",c1,c2),("최근 구간",c2,None)):
        mask=pd.Series(True,index=z.index)
        if left is not None: mask &= z.signal_date>left
        if right is not None: mask &= z.signal_date<=right
        rows.append(dict({"구간":label},**_breakout_summary(z[mask])))
    return rows

def _run_breakout_lab(excluded_dates=None):
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES); paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}; rows=[]
    for code,p in sorted(paths.items()):
        try: rows.extend(_breakout_records(pd.read_csv(p,parse_dates=["date"]),code,excluded_dates))
        except Exception: pass
    q=pd.DataFrame(rows); PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    _vg_write(BREAKOUT_LAB_RESULT,{"version":BREAKOUT_LAB_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),"summary":_breakout_summary(q),"time_split":_breakout_time_split(q),"definition":"별도 추세추종 전략: 종가 1만~5만원 · 주가가 상승 30주선 위 · 직전 20일 베이스 폭 15% 이하이며 최근 10일 변동폭 축소 · 베이스 고점 종가 돌파 · 돌파일 거래량이 이전 50일 평균의 150% 이상 · 베이스 저점까지 위험 7% 이내. 돌파 당일 종가 진입 후 15일 성과·상승폭·하락폭을 측정합니다."})

def _trend_pullback_records(h, code, excluded_dates=None):
    """Trend pullback, not a base-breakout: rising 30-week trend plus daily MA10 recovery."""
    try:
        h=h.copy().sort_values("date").reset_index(drop=True)
        for col in ("open","high","low","close","volume"): h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["open","high","low","close","volume"]).reset_index(drop=True)
        excluded_dates=excluded_dates or set(); rows=[]; i=170; n=len(h)
        while i<n-16:
            day=str(pd.Timestamp(h.date.iat[i]).date())
            if day in excluded_dates or not 5000<=float(h.close.iat[i])<=50000: i+=1; continue
            close=h.close.iloc[:i+1]; ma10=float(close.rolling(10).mean().iat[-1])
            weekly=pd.Series(close.to_numpy(),index=pd.to_datetime(h.date.iloc[:i+1])).resample("W-FRI").last().dropna()
            if len(weekly)<34: i+=1; continue
            ma30=float(weekly.rolling(30).mean().iat[-1]); ma30_old=float(weekly.rolling(30).mean().iat[-5])
            impulse=h.iloc[i-30:i-10]; pullback=h.iloc[i-5:i]; support=float(pullback.low.min())
            impulse_gain=float(impulse.close.max()/impulse.close.min()-1)
            quiet=float(pullback.volume.mean()/h.volume.iloc[i-25:i-5].mean()) if h.volume.iloc[i-25:i-5].mean()>0 else 9
            entry=float(h.close.iat[i])
            # A real rising trend, then a lighter-volume pullback and an MA10 recovery.
            if not (entry>ma30 and ma30>=ma30_old and impulse_gain>=.08 and quiet<=1.0 and float(h.close.iat[i-1])<=float(close.rolling(10).mean().iat[-2]) and float(h.low.iat[i])<=ma10*1.01 and entry>ma10 and entry>float(h.open.iat[i]) and (entry/support-1)<=.07):
                i+=1; continue
            future=h.iloc[i+1:i+16]
            if len(future)<15: break
            outcome="TIMEOUT"; exit_px=float(future.close.iat[-1]); exit_i=i+15
            for j in range(i+1,i+16):
                o,hi,lo=map(float,(h.open.iat[j],h.high.iat[j],h.low.iat[j]))
                if o<support or lo<support: outcome="INTRADAY_STOP"; exit_px=o if o<support else support; exit_i=j; break
                if hi>=entry*1.10: outcome="TARGET"; exit_px=entry*1.10; exit_i=j; break
            held=h.iloc[i:exit_i+1]
            rows.append({"signal_date":day,"code":str(code).zfill(6),"entry":round(entry,2),"support":round(support,2),"outcome":outcome,"days":int(exit_i-i),"net_pct":round((exit_px/entry-1)*100-.35,3),"ret15_pct":round((float(future.close.iat[-1])/entry-1)*100-.35,3),"max_runup_pct":round((float(held.high.max())/entry-1)*100,3),"max_drawdown_pct":round((float(held.low.min())/entry-1)*100,3)})
            i=exit_i+1
        return rows
    except Exception: return []

def _run_trend_pullback_lab(excluded_dates=None):
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES); paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}; rows=[]
    for code,p in sorted(paths.items()):
        try: rows.extend(_trend_pullback_records(pd.read_csv(p,parse_dates=["date"]),code,excluded_dates))
        except Exception: pass
    q=pd.DataFrame(rows); PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    _vg_write(PULLBACK_LAB_RESULT,{"version":PULLBACK_LAB_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),"summary":_priorlow_summary(q),"risk_summary":_breakout_summary(q),"time_split":_breakout_time_split(q),"definition":"별도 상승 추세 눌림목 전략: 종가 1만~5만원 · 상승/평탄 30주선 위 · 직전 20거래일 중 최소 8% 상승 이력 · 최근 5거래일 거래량이 그 이전 20거래일 평균 이하로 감소 · 10일선까지 눌린 뒤 종가가 10일선 위로 회복한 양봉 · 최근 5일 저점까지 위험 7% 이내. 회복 당일 종가 진입, 최근 5일 저점 이탈 손절, +10% 목표·최대 15거래일입니다."})

def _week30_records(h, code, excluded_dates=None):
    """Pure 30-week trend rule: enter on upward cross, exit on weekly close below MA30."""
    try:
        h=h.copy().sort_values("date").reset_index(drop=True)
        for col in ("high","low","close"): h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["high","low","close"]).set_index("date")
        w=h.resample("W-FRI").agg({"close":"last","high":"max","low":"min"}).dropna().reset_index()
        w["ma30"]=w.close.rolling(30).mean(); excluded_dates=excluded_dates or set(); rows=[]; i=34
        while i<len(w)-1:
            date=str(pd.Timestamp(w.date.iat[i]).date()); entry=float(w.close.iat[i]); prev=float(w.close.iat[i-1]); ma=float(w.ma30.iat[i]); prev_ma=float(w.ma30.iat[i-1]); old_ma=float(w.ma30.iat[i-4])
            if date in excluded_dates or not 5000<=entry<=50000 or not (prev<=prev_ma and entry>ma and ma>old_ma):
                i+=1; continue
            exit_i=None
            for j in range(i+1,len(w)):
                if float(w.close.iat[j])<float(w.ma30.iat[j]): exit_i=j; break
            if exit_i is None: break  # still open: no future return is claimed
            held=w.iloc[i:exit_i+1]; exit_px=float(w.close.iat[exit_i])
            rows.append({"signal_date":date,"code":str(code).zfill(6),"entry":round(entry,2),"exit_date":str(pd.Timestamp(w.date.iat[exit_i]).date()),"exit":round(exit_px,2),"weeks":int(exit_i-i),"net_pct":round((exit_px/entry-1)*100-.35,3),"max_runup_pct":round((float(held.high.max())/entry-1)*100,3),"max_drawdown_pct":round((float(held.low.min())/entry-1)*100,3)})
            i=exit_i+1
        return rows
    except Exception: return []

def _week30_summary(q):
    if q.empty: return {"거래":0}
    return {"거래":int(len(q)),"승률":round(float((q.net_pct>0).mean()*100),2),"평균순수익":round(float(q.net_pct.mean()),2),"중앙순수익":round(float(q.net_pct.median()),2),"평균보유주":round(float(q.weeks.mean()),1),"+10%도달률":round(float((q.max_runup_pct>=10).mean()*100),2),"평균최대하락":round(float(q.max_drawdown_pct.mean()),2)}

def _week30_time_split(q):
    if q.empty: return []
    z=q.copy(); z["signal_date"]=pd.to_datetime(z.signal_date); c1,c2=z.signal_date.quantile([1/3,2/3]).tolist(); out=[]
    for label,left,right in (("앞 구간",None,c1),("중간 구간",c1,c2),("최근 구간",c2,None)):
        mask=pd.Series(True,index=z.index)
        if left is not None: mask &= z.signal_date>left
        if right is not None: mask &= z.signal_date<=right
        out.append(dict({"구간":label},**_week30_summary(z[mask])))
    return out

def _run_week30_lab(excluded_dates=None):
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES); paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}; rows=[]
    for code,p in sorted(paths.items()):
        try: rows.extend(_week30_records(pd.read_csv(p,parse_dates=["date"]),code,excluded_dates))
        except Exception: pass
    q=pd.DataFrame(rows); PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    _vg_write(WEEK30_LAB_RESULT,{"version":WEEK30_LAB_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),"summary":_week30_summary(q),"time_split":_week30_time_split(q),"definition":"독립 30주선 전략: 주봉 종가가 30주선 아래에서 위로 돌파하고, 30주선이 4주 전보다 상승했을 때 그 주 종가에 진입합니다. 이후 주봉 종가가 30주선 아래로 내려간 첫 주에 청산합니다. 전저점·10일선·거래량·정배열 조건은 사용하지 않습니다. 아직 청산 신호가 없는 보유 거래는 결과에 넣지 않습니다."})

def _week30_rising_regime_at_signal(h, signal_date, close_price):
    """Use only the latest completed Friday, never the rest of the signal week."""
    try:
        q=h.copy().sort_values("date").reset_index(drop=True)
        q["date"]=pd.to_datetime(q["date"])
        q["close"]=pd.to_numeric(q["close"],errors="coerce")
        day=pd.Timestamp(signal_date).normalize()
        # The entry can occur intraday, including Friday.  Exclude the signal
        # day itself so the weekly regime never sees a later Friday close.
        completed=q[q.date < day]
        completed=completed[completed.date.dt.weekday==4]  # completed weekly closes only
        if len(completed)<34: return False
        w=completed.set_index("date")["close"].resample("W-FRI").last().dropna()
        if len(w)<34: return False
        ma30=w.rolling(30).mean()
        ma_now=float(ma30.iat[-1]); ma_4w=float(ma30.iat[-5])
        return bool(float(close_price)>ma_now and ma_now>ma_4w)
    except Exception:
        return False

def _priorlow_week30_summary(q):
    summary=_priorlow_summary(q)
    if not q.empty:
        summary["평균최대하락"]=round(float(q.max_drawdown_pct.mean()),2)
    return summary

def _priorlow_week30_time_split(base, filtered):
    if base.empty: return [],"기준 표본 없음"
    b=base.copy(); b["signal_date"]=pd.to_datetime(b.signal_date)
    f=filtered.copy(); f["signal_date"]=pd.to_datetime(f.signal_date) if not f.empty else pd.Series(dtype="datetime64[ns]")
    c1,c2=b.signal_date.quantile([1/3,2/3]).tolist(); rows=[]; passed=True
    for label,left,right in (("앞 구간",None,c1),("중간 구간",c1,c2),("최근 구간",c2,None)):
        bm=pd.Series(True,index=b.index); fm=pd.Series(True,index=f.index)
        if left is not None: bm &= b.signal_date>left; fm &= f.signal_date>left
        if right is not None: bm &= b.signal_date<=right; fm &= f.signal_date<=right
        bs=_priorlow_week30_summary(b[bm]); fs=_priorlow_week30_summary(f[fm])
        good=(fs.get("거래",0)>=100 and fs.get("평균순수익",-999)>=bs.get("평균순수익",999)
              and fs.get("손절률",999)<=bs.get("손절률",-999)
              and fs.get("평균최대하락",999)<=bs.get("평균최대하락",-999))
        passed &= good
        rows.append({"구간":label,"기준 거래":bs.get("거래",0),"30주선 거래":fs.get("거래",0),
                     "기준 평균순수익":bs.get("평균순수익",0),"30주선 평균순수익":fs.get("평균순수익",0),
                     "기준 손절률":bs.get("손절률",0),"30주선 손절률":fs.get("손절률",0),
                     "기준 평균최대하락":bs.get("평균최대하락",0),"30주선 평균최대하락":fs.get("평균최대하락",0),
                     "판정":"통과" if good else "보류"})
    verdict="3구간 모두 표본 100건 이상·평균순수익 개선·손절률과 최대하락 악화 없음" if passed else "3구간 동시 통과 아님"
    return rows,verdict

def _run_priorlow_week30_filter_lab(excluded_dates=None):
    """One-factor experiment: rising 30-week regime filter on the same prior-low trade."""
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES)
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}
    base=[]; filtered=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"])
            # The price universe stays identical in both rows.  30-week status is the sole test factor.
            events=[r for r in _priorlow_events(h,code,excluded_dates) if 5000<=float(r["entry"])<=50000]
            base.extend(events)
            filtered.extend(r for r in events if _week30_rising_regime_at_signal(h,r["signal_date"],r["entry"]))
        except Exception: pass
    q_base=pd.DataFrame(base); q_filtered=pd.DataFrame(filtered); PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    split,verdict=_priorlow_week30_time_split(q_base,q_filtered)
    _vg_write(WEEK30_FILTER_RESULT,{"version":WEEK30_FILTER_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),
        "comparison":[dict({"조건":"기준 전저점 (1만~5만원)"},**_priorlow_week30_summary(q_base)),dict({"조건":"+ 상승 30주선 필터"},**_priorlow_week30_summary(q_filtered))],
        "time_split":split,"time_split_verdict":verdict,
        "definition":"비교 두 조건 모두 전저점 A+1% 진입, A 장중 이탈 손절, +10% 목표, 최대 15거래일과 신호 당일 진입가 1만~5만원을 동일하게 적용합니다. 추가된 조건은 하나뿐입니다: 신호일 직전 완료 주봉 기준 종가가 30주선 위이고 30주선이 4주 전보다 상승 중이어야 합니다. 신호 주의 미완성 주봉은 사용하지 않습니다."})

def _priorlow_confirmation_events(d, code, rebound_pct, excluded_dates=None):
    """Support closes first; entry only on a later +1/+2/+3% rebound within five sessions."""
    try:
        h=d.copy().sort_values("date").reset_index(drop=True)
        for col in ("open","high","low","close"): h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["open","high","low","close"]).reset_index(drop=True)
        excluded_dates=excluded_dates or set(); rows=[]; i=125; n=len(h); code=str(code).zfill(6)
        while i<n-22:
            signal_date=str(pd.Timestamp(h.date.iat[i]).date()); a_idx,a=_surviving_prior_low(h,i)
            if signal_date in excluded_dates or a is None or h.low.iat[i]<a or h.low.iat[i]>a*1.03 or h.close.iat[i]<=h.open.iat[i]:
                i+=1; continue
            entry=float(a)*(1+rebound_pct/100); entry_i=None; cancelled=False
            for j in range(i+1,min(i+6,n)):
                if float(h.open.iat[j])<a or float(h.low.iat[j])<a: cancelled=True; break
                if float(h.open.iat[j])<=entry<=float(h.high.iat[j]): entry_i=j; break
                if entry<=float(h.open.iat[j])<=a*1.03: entry_i=j; entry=float(h.open.iat[j]); break
            if cancelled or entry_i is None: i+=1; continue
            exit_i=None; outcome="TIMEOUT"; exit_px=float(h.close.iat[min(entry_i+15,n-1)])
            for j in range(entry_i+1,min(entry_i+16,n)):
                o,hh,ll=map(float,(h.open.iat[j],h.high.iat[j],h.low.iat[j]))
                if o<a or ll<a: exit_i=j; outcome="INTRADAY_STOP"; exit_px=o if o<a else a; break
                if hh>=entry*1.10: exit_i=j; outcome="TARGET"; exit_px=entry*1.10; break
            if exit_i is None: exit_i=min(entry_i+15,n-1)
            held=h.iloc[entry_i:exit_i+1]
            rows.append({"signal_date":signal_date,"entry_date":str(pd.Timestamp(h.date.iat[entry_i]).date()),"code":code,"A":round(float(a),2),"rebound_pct":rebound_pct,"entry":round(entry,2),"outcome":outcome,"days":int(exit_i-entry_i),"net_pct":round((exit_px/entry-1)*100-.35,3),"max_drawdown_pct":round((float(held.low.min())/entry-1)*100,3)})
            i=exit_i+1
        return rows
    except Exception: return []

def _run_priorlow_confirmation_lab(excluded_dates=None):
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES); paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}; rows=[]
    for pct in (1,2,3):
        q=[]
        for code,p in sorted(paths.items()):
            try: q.extend(_priorlow_confirmation_events(pd.read_csv(p,parse_dates=["date"]),code,pct,excluded_dates))
            except Exception: pass
        rows.append(dict({"조건":f"종가 지지 후 +{pct}% 확인 진입"},**_priorlow_summary(pd.DataFrame(q))))
    PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    _vg_write(PRIORLOW_CONFIRM_RESULT,{"version":PRIORLOW_CONFIRM_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),"comparison":rows,"definition":"전저점 A 위에서 양봉 종가로 지지를 확인한 뒤, 다음 5거래일 안에 A 대비 +1%·+2%·+3% 반등가에 도달할 때만 진입합니다. A 장중 이탈 시 취소·손절, +10% 목표·최대 15거래일은 기존과 동일합니다."})

def _run_priorlow_fib_lab(excluded_dates=None):
    excluded_dates=set(excluded_dates or MARKET_SHOCK_DATES)
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}
    base=[]; fib=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"])
            for row in _priorlow_events(h,code,excluded_dates):
                base.append(row)
                detail=_fib_retrace_at_a(h,row["A_date"],row["A"],row["entry"])
                if detail:
                    fib.append(dict(row,**detail))
        except Exception: pass
    q_base=pd.DataFrame(base); q_fib=pd.DataFrame(fib)
    PRIORLOW_LAB_DIR.mkdir(parents=True,exist_ok=True)
    comparison=[dict({"조건":"기존 전저점"},**_priorlow_summary(q_base)),
                dict({"조건":"+ 피보나치 되돌림"},**_priorlow_summary(q_fib))]
    time_split,time_split_verdict=_priorlow_time_split(q_base,q_fib)
    if not q_fib.empty: q_fib.to_csv(PRIORLOW_FIB_TRADES,index=False,encoding="utf-8-sig")
    _vg_write(PRIORLOW_FIB_RESULT,{"version":PRIORLOW_FIB_VERSION,"stocks":len(paths),"excluded_dates":sorted(excluded_dates),"comparison":comparison,
        "time_split":time_split,"time_split_verdict":time_split_verdict,
        "definition":"A가 직전 120거래일 내 상승파동(저점→고점 +15% 이상)의 38.2%·50.0%·61.8% 되돌림값 ±2%에 있고, 직전 고점까지 진입가 기준 최소 10% 여력이 있을 때만 통과"})

def _render_priorlow_lab():
    st.divider(); st.subheader("🧪 전저점 재판정 검증 · 연구용")
    st.caption("A를 깨면 더 과거 전저점으로 다시 잡습니다. A 위 1% 지정가 진입, +3% 초과 추격 제외, 장중 A 이탈 손절, +10% 목표·최대 15거래일 기준입니다. 시장 전체 이슈 날짜만 제외합니다.")
    dates_text=st.text_input("검증 제외 날짜 (쉼표 또는 줄바꿈 구분)",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="priorlow_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("전저점 재판정 검증 시작",key="priorlow_lab_start"):
        with st.spinner("저장된 일봉으로 전저점 재판정 거래를 검증 중입니다..."):
            _run_priorlow_lab(excluded_dates)
        st.rerun()
    result=_vg_read(PRIORLOW_LAB_RESULT) if PRIORLOW_LAB_RESULT.exists() else {}
    if not result or result.get("version")!=PRIORLOW_LAB_VERSION: return
    st.info(f"{result.get('scope','')} · {result.get('stocks',0)}개 종목, {result.get('trades',0)}건")
    market_days=", ".join(result.get("market_shock_dates",[])) or "없음"
    st.caption(f"시장 전체 이슈 제외일: {market_days}")
    summary=result.get("summary",{})
    if summary: st.dataframe(pd.DataFrame([summary]),use_container_width=True,hide_index=True)
    if PRIORLOW_LAB_TRADES.exists():
        q=pd.read_csv(PRIORLOW_LAB_TRADES)
        st.download_button("전저점 재판정 검증 CSV",q.to_csv(index=False).encode("utf-8-sig"),"prior_low_rejudge_trades.csv","text/csv")

def _render_priorlow_fib_lab():
    st.subheader("🧪 피보나치 되돌림 + 전저점 · 연구용")
    st.caption("A가 직전 상승파동의 38.2%·50.0%·61.8% 되돌림값 ±2%에 있고, 직전 고점까지 진입가 기준 최소 10% 여력이 있을 때만 기존 전저점 거래를 통과시킵니다. 미래 고점은 사용하지 않습니다.")
    dates_text=st.text_input("피보나치 검증 제외 날짜 (쉼표 또는 줄바꿈 구분)",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="priorlow_fib_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("피보나치 전저점 검증 시작",key="priorlow_fib_start"):
        with st.spinner("저장된 일봉으로 피보나치 되돌림을 검증 중입니다..."):
            _run_priorlow_fib_lab(excluded_dates)
        st.rerun()
    result=_vg_read(PRIORLOW_FIB_RESULT) if PRIORLOW_FIB_RESULT.exists() else {}
    if not result or result.get("version")!=PRIORLOW_FIB_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    st.dataframe(pd.DataFrame(result.get("comparison",[])),use_container_width=True,hide_index=True)
    if result.get("time_split"):
        st.markdown("#### 시간순 3구간 비교")
        st.caption("같은 규칙을 앞·중간·최근 구간으로 나눠 기준 전저점과 비교합니다. 각 구간에서 피보나치 표본 100건 이상, 평균순수익은 기준 이상, 손절률은 기준 이하일 때만 통과입니다.")
        st.dataframe(pd.DataFrame(result["time_split"]),use_container_width=True,hide_index=True)
        st.caption(f"판정: {result.get('time_split_verdict','')}")
    st.caption(result.get("definition",""))
    if PRIORLOW_FIB_TRADES.exists():
        q=pd.read_csv(PRIORLOW_FIB_TRADES)
        st.download_button("피보나치 전저점 검증 CSV",q.to_csv(index=False).encode("utf-8-sig"),"prior_low_fibonacci_trades.csv","text/csv")

def _render_priorlow_confirmation_lab():
    st.subheader("🧪 전저점 종가 지지 후 반등 진입 · 연구용")
    st.caption("전저점 A를 장중 깨지 않고 양봉 종가로 지지를 확인한 뒤, 다음 5거래일 안의 반등에서만 진입합니다. +1%·+2%·+3%를 같은 손절·목표·보유기간으로 비교합니다.")
    dates_text=st.text_input("확인형 진입 검증 제외 날짜 (쉼표 또는 줄바꿈 구분)",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="priorlow_confirm_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("종가 지지 후 반등 진입 검증 시작",key="priorlow_confirm_start"):
        with st.spinner("저장된 일봉으로 확인형 진입을 검증 중입니다..."):
            _run_priorlow_confirmation_lab(excluded_dates)
        st.rerun()
    result=_vg_read(PRIORLOW_CONFIRM_RESULT) if PRIORLOW_CONFIRM_RESULT.exists() else {}
    if not result or result.get("version")!=PRIORLOW_CONFIRM_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    st.dataframe(pd.DataFrame(result.get("comparison",[])),use_container_width=True,hide_index=True)
    st.caption(result.get("definition",""))

def _render_priorlow_alignment_lab():
    st.divider(); st.subheader("🧪 완전 정배열 + 기본 진입 검증")
    st.caption("영상의 ‘정배열은 좋고 역배열은 나쁘다’를 하나의 필터로만 시험합니다. 신호 당일 종가가 5일선·20일선·60일선·120일선·200일선 모두 위에 있는 경우입니다.")
    dates_text=st.text_input("정배열 검증 제외 날짜",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="priorlow_alignment_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("완전 정배열 결합 검증 시작",key="priorlow_alignment_start"):
        with st.spinner("기본 전저점과 완전 정배열 결합을 비교 중입니다..."):
            _run_priorlow_alignment_lab(excluded_dates)
        st.rerun()
    result=_vg_read(PRIORLOW_ALIGNMENT_RESULT) if PRIORLOW_ALIGNMENT_RESULT.exists() else {}
    if not result or result.get("version")!=PRIORLOW_ALIGNMENT_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    st.dataframe(pd.DataFrame(result.get("comparison",[])),use_container_width=True,hide_index=True)
    if result.get("time_split"):
        st.markdown("#### 시간순 3구간 비교")
        st.dataframe(pd.DataFrame(result["time_split"]),use_container_width=True,hide_index=True)
        st.caption(f"판정: {result.get('time_split_verdict','')}")
    st.caption(result.get("definition",""))

def _render_breakout_lab():
    st.divider(); st.subheader("🧪 30주선 베이스 돌파 · 별도 전략 검증")
    st.caption("전저점과 섞지 않는 추세추종 전략입니다. 상승 30주선 위에서 변동폭이 줄어든 베이스를 거래량과 함께 종가 돌파할 때만 기록합니다.")
    dates_text=st.text_input("돌파 전략 검증 제외 날짜",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="breakout_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("30주선 베이스 돌파 검증 시작",key="breakout_lab_start"):
        with st.spinner("저장된 일봉으로 30주선 베이스 돌파를 검증 중입니다..."):
            _run_breakout_lab(excluded_dates)
        st.rerun()
    result=_vg_read(BREAKOUT_LAB_RESULT) if BREAKOUT_LAB_RESULT.exists() else {}
    if not result or result.get("version")!=BREAKOUT_LAB_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    summary=result.get("summary",{})
    if summary: st.dataframe(pd.DataFrame([summary]),use_container_width=True,hide_index=True)
    if result.get("time_split"):
        st.markdown("#### 시간순 3구간")
        st.dataframe(pd.DataFrame(result["time_split"]),use_container_width=True,hide_index=True)
    st.caption(result.get("definition",""))

def _render_trend_pullback_lab():
    st.divider(); st.subheader("🧪 상승 추세 눌림목 · 별도 전략 검증")
    st.caption("저점매수와 섞지 않는 전략입니다. 상승 30주선 위에서 거래량이 줄며 10일선까지 눌린 뒤, 양봉 종가로 10일선을 회복할 때만 진입합니다.")
    dates_text=st.text_input("눌림목 전략 검증 제외 날짜",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="pullback_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("상승 추세 눌림목 검증 시작",key="pullback_lab_start"):
        with st.spinner("저장된 일봉으로 상승 추세 눌림목을 검증 중입니다..."):
            _run_trend_pullback_lab(excluded_dates)
        st.rerun()
    result=_vg_read(PULLBACK_LAB_RESULT) if PULLBACK_LAB_RESULT.exists() else {}
    if not result or result.get("version")!=PULLBACK_LAB_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    st.dataframe(pd.DataFrame([result.get("summary",{})]),use_container_width=True,hide_index=True)
    if result.get("time_split"):
        st.markdown("#### 시간순 3구간")
        st.dataframe(pd.DataFrame(result["time_split"]),use_container_width=True,hide_index=True)
    st.caption(result.get("definition",""))

def _render_week30_lab():
    st.divider(); st.subheader("🧪 30주선 추세 돌파·이탈 검증")
    st.caption("30주선만 사용하는 독립 전략입니다. 주봉 종가가 상승 30주선을 위로 돌파하면 진입하고, 주봉 종가가 30주선 아래로 내려가면 청산합니다.")
    dates_text=st.text_input("30주선 검증 제외 날짜",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="week30_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("30주선 추세 검증 시작",key="week30_lab_start"):
        with st.spinner("저장된 일봉을 주봉으로 재구성해 30주선을 검증 중입니다..."):
            _run_week30_lab(excluded_dates)
        st.rerun()
    result=_vg_read(WEEK30_LAB_RESULT) if WEEK30_LAB_RESULT.exists() else {}
    if not result or result.get("version")!=WEEK30_LAB_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    st.dataframe(pd.DataFrame([result.get("summary",{})]),use_container_width=True,hide_index=True)
    if result.get("time_split"):
        st.markdown("#### 시간순 3구간")
        st.dataframe(pd.DataFrame(result["time_split"]),use_container_width=True,hide_index=True)
    st.caption(result.get("definition",""))

def _render_priorlow_week30_filter_lab():
    st.divider(); st.subheader("🧪 전저점 + 상승 30주선 필터 검증")
    st.caption("30주선을 매수·매도선으로 쓰지 않습니다. 같은 전저점 매매에서 하락장만 제외하는 필터로 효과가 있는지 비교합니다.")
    dates_text=st.text_input("검증 제외 날짜",value=", ".join(sorted(MARKET_SHOCK_DATES)),key="priorlow_week30_filter_excluded_dates")
    excluded_dates=_parse_excluded_dates(dates_text)
    if st.button("전저점 + 상승 30주선 검증 시작",key="priorlow_week30_filter_start"):
        with st.spinner("같은 전저점 거래에 상승 30주선 조건만 추가해 비교 중입니다..."):
            _run_priorlow_week30_filter_lab(excluded_dates)
        st.rerun()
    result=_vg_read(WEEK30_FILTER_RESULT) if WEEK30_FILTER_RESULT.exists() else {}
    if not result or result.get("version")!=WEEK30_FILTER_VERSION: return
    st.info(f"{result.get('stocks',0)}개 종목 · 제외일: {', '.join(result.get('excluded_dates',[])) or '없음'}")
    st.dataframe(pd.DataFrame(result.get("comparison",[])),use_container_width=True,hide_index=True)
    if result.get("time_split"):
        st.markdown("#### 시간순 3구간")
        st.dataframe(pd.DataFrame(result["time_split"]),use_container_width=True,hide_index=True)
    st.caption(f"판정: {result.get('time_split_verdict','')}")
    st.caption(result.get("definition",""))

def _render_research_ledger():
    st.divider(); st.subheader("📌 검증 이력 고정표")
    st.caption("상태가 채택·폐기·보류가 된 항목은 같은 형태로 다시 검증하지 않습니다. 다음 시도는 미검증 항목에서 하나만 고릅니다.")
    fib_result=_vg_read(PRIORLOW_FIB_RESULT) if PRIORLOW_FIB_RESULT.exists() else {}
    fib_summary={}
    if fib_result.get("version")==PRIORLOW_FIB_VERSION:
        comparison=fib_result.get("comparison",[])
        fib_summary=comparison[-1] if len(comparison)>1 else {}
    confirm_result=_vg_read(PRIORLOW_CONFIRM_RESULT) if PRIORLOW_CONFIRM_RESULT.exists() else {}
    confirm_summary=confirm_result.get("comparison",[]) if confirm_result.get("version")==PRIORLOW_CONFIRM_VERSION else []
    rows=[
        {"항목":"전저점 재판정 A+1%·+10%","상태":"보류","근거":"2,090건 · 목표 39.57% · 손절 54.45% · 평균 +2.83%","다음 행동":"추천 엔진 미반영"},
        {"항목":"가격 1만~5만원·20일 거래대금 10억","상태":"보류","근거":"708건 · 평균 +3.14%로 기준 대비 개선, 단일 표본","다음 행동":"분할검증 전까지 채택 금지"},
        {"항목":"주봉·월봉 상승을 추가","상태":"폐기","근거":"86건 · 목표 32.56% · 손절 63.95% · 평균 +1.63%","다음 행동":"같은 정의로 재시도 금지"},
        {"항목":"반등일 거래량 증가","상태":"보류","근거":"28건으로 표본 100건 미만","다음 행동":"단독 규칙으로 승격 금지"},
        {"항목":"일봉 거래량 단순 매물대","상태":"폐기","근거":"163건 · 평균 +2.51%, 가격·유동성 기준보다 악화","다음 행동":"단순 비중식 재시도 금지"},
        {"항목":"10일선 종가 교차 보유매매","상태":"폐기","근거":"일·주·월봉 결과가 추천 기준에 미달","다음 행동":"현재 BASE에 결합 금지"},
        {"항목":"2608 지지클러스터(전저점·매물대·주지지선)","상태":"보류","근거":"기존 로직은 확인됨, 최종 수치 결과 파일은 현재 작업본에 없음","다음 행동":"결과 원본 확인 전 재검증 금지"},
        {"항목":"실제 기관·외국인 과거 수급","상태":"미검증","근거":"현재 저장 일봉에 과거 투자자별 수급 원천자료 없음","다음 행동":"원천자료 확보 후 단독 검증"},
        {"항목":"피보나치 되돌림과 전저점 결합","상태":"폐기","근거":"669건 · 시간순 중간 구간에서 평균수익 2.65%로 기준 2.73% 미달, 손절 57.6%로 기준 54.61% 초과","다음 행동":"같은 정의로 재시도 금지"},
        {"항목":"MACD·상승눌림A 결합","상태":"폐기","근거":"30종목 확장검증에서 평균수익·중앙값 개선 실패","다음 행동":"매수 필수조건으로 재사용 금지"},
        {"항목":"결합형+거래량 1.0·1.2·1.5배","상태":"폐기","근거":"거래량 기준 강화 시 평균수익 -1.14%→-4.84%로 악화","다음 행동":"단순 거래량 배수 필터 재시도 금지"},
        {"항목":"시장 대비 상대강도 RS20·RS60","상태":"보조만","근거":"RS20≥3·RS60≥5 전체 평균은 개선됐으나 기간 안정성·최대손실·종목 쏠림 감사 탈락","다음 행동":"하드필터 금지 · 동률 후보 순위 보조만"},
        {"항목":"전저점 종가 지지 후 반등 진입","상태":"보류" if confirm_summary else "미검증","근거":"+1%·+2%·+3% 확인 진입을 같은 손절·목표로 비교" if not confirm_summary else "단일 실행 결과는 시간분할 전 채택 금지","다음 행동":"단독 검증 1회" if not confirm_summary else "시간분할 전 채택 금지"},
    ]
    q=pd.DataFrame(rows)
    st.dataframe(q,use_container_width=True,hide_index=True)
    st.info("2608 지지클러스터는 기존 결과 원본을 확인하기 전까지 건드리지 않습니다.")

# Recommendation campaign: recommendations are frozen first, then judged by
# their actual subsequent path.  No result is backfilled or silently replaced.
CAMPAIGN_DIR=Path("data")/"recommendation_campaign"
CAMPAIGN_FILE=CAMPAIGN_DIR/"campaign.json"
CAMPAIGN_VERSION="RECOMMEND_TOP5_DYNAMIC_EXIT_V3_FORWARD_20260928"

def _campaign_read():
    base={"version":CAMPAIGN_VERSION,"candidates":[],"active":[],"closed":[],"last_update":""}
    try:
        if CAMPAIGN_FILE.exists():
            saved=json.loads(CAMPAIGN_FILE.read_text(encoding="utf-8"))
            if isinstance(saved,dict):
                base.update(saved);base["candidates"]=base.get("candidates",[])[:5];base["version"]=CAMPAIGN_VERSION
    except Exception: pass
    return base

def _campaign_write(state):
    try:
        CAMPAIGN_DIR.mkdir(parents=True,exist_ok=True)
        state["version"]=CAMPAIGN_VERSION
        CAMPAIGN_FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    except Exception: pass

def _campaign_source_candidates():
    result=_deep_valley_state_read(DEEP_VALLEY_LIVE_RESULT) if DEEP_VALLEY_LIVE_RESULT.exists() else {}
    rows=result.get("candidates",[]) if isinstance(result,dict) else []
    out=[]
    for z in rows:
        try:
            price=float(z.get("current",0))
            if not 5000<=price<=50000: continue
            out.append({"code":str(z["code"]).zfill(6),"name":z.get("name",""),"captured_at":str(z.get("date",now_kst().date())),
                "price":price,"A":float(z.get("A",0)),"entry_cap":float(z.get("entry_cap",0)),
                "distance_pct":float(z.get("distance_pct",0)),"support_volume_share":float(z.get("support_volume_share",0)),
                "foreign_5":z.get("foreign_5"),"inst_5":z.get("inst_5")})
        except Exception: pass
    return sorted(out,key=lambda z:(z["distance_pct"],-z["support_volume_share"],z["code"]))

def _campaign_fill_candidates(state):
    known={str(x.get("code")).zfill(6) for x in state.get("candidates",[])+state.get("active",[])+state.get("closed",[])}
    added=0
    for row in _campaign_source_candidates():
        if row["code"] in known: continue
        row.update({"history":[],"held_days":0,"last_price":row["price"],"last_return_pct":0.0,
                    "status":"추천 고정 · 추적 시작","action":"관찰","review":"추적 중","selected":False})
        state.setdefault("candidates",[]).append(row); known.add(row["code"]); added+=1
        if len(state["candidates"])>=5: break
    state["candidates"]=state.get("candidates",[])[:5]
    return added

def _campaign_history(code, quotes=None):
    try:
        return _merge_cached_quote(str(code).zfill(6),300,(quotes or {}).get(str(code).zfill(6)))
    except Exception:
        return None

def _campaign_dynamic_exit(h,start,entry,stop):
    """Walk forward only: let winners run, exit after profit when trend deterioration is confirmed."""
    x=h.copy().sort_values("date").reset_index(drop=True)
    for c in ("high","low","close","volume"):x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna(subset=["date","high","low","close"]).reset_index(drop=True)
    x["ma10"]=x.close.rolling(10).mean()
    ema12=x.close.ewm(span=12,adjust=False,min_periods=12).mean();ema26=x.close.ewm(span=26,adjust=False,min_periods=26).mean()
    x["hist"]=(ema12-ema26)-(ema12-ema26).ewm(span=9,adjust=False,min_periods=9).mean()
    prev=x.close.shift(1);tr=pd.concat([(x.high-x.low),(x.high-prev).abs(),(x.low-prev).abs()],axis=1).max(axis=1)
    x["atr14"]=tr.rolling(14).mean()
    idx=x.index[pd.to_datetime(x.date).dt.normalize()>=pd.Timestamp(start).normalize()].tolist()
    if not idx:return {"exit":False}
    peak=float(entry);peak_high=float(entry);last={}
    for j in idx:
        r=x.iloc[j];close=float(r.close);low=float(r.low);peak=max(peak,close);peak_high=max(peak_high,float(r.high))
        a_break=bool(stop>0 and low<float(stop))
        profit_active=peak_high>=float(entry)*1.01
        cross=bool(j>=1 and np.isfinite(x.ma10.iat[j]) and np.isfinite(x.ma10.iat[j-1]) and float(x.close.iat[j-1])>=float(x.ma10.iat[j-1]) and close<float(x.ma10.iat[j]))
        macd_weak=bool(j>=2 and np.isfinite(x["hist"].iat[j]) and np.isfinite(x["hist"].iat[j-1]) and np.isfinite(x["hist"].iat[j-2]) and float(x["hist"].iat[j])<float(x["hist"].iat[j-1])<float(x["hist"].iat[j-2]))
        atr=float(x.atr14.iat[j]) if np.isfinite(x.atr14.iat[j]) else close*.02
        trail=peak-max(2*atr,peak*.04);trail_break=bool(profit_active and close<trail)
        trend_exit=bool(profit_active and ((cross and macd_weak) or trail_break))
        reason="A 장중 이탈" if a_break else ("고점 변동성 추적선 이탈" if trail_break else ("10일선 하향이탈+MACD 약화" if trend_exit else ""))
        last={"date":str(pd.Timestamp(r.date).date()),"close":close,"peak":peak_high,"ma10_cross":cross,"macd_weak":macd_weak,"trail":trail,"trail_break":trail_break,"profit_active":profit_active}
        if a_break or trend_exit:
            return {**last,"exit":True,"reason":reason,"exit_price":close,"return_pct":round((close/float(entry)-1)*100,2)}
    return {**last,"exit":False,"reason":"상승 추세 유지"}

def _campaign_update_one(pos, quotes=None):
    h=_campaign_history(pos["code"],quotes)
    if h is None or h.empty: return pos
    try:
        h=h.copy().sort_values("date").reset_index(drop=True)
        for col in ("high","low","close"): h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["high","low","close"])
        row=h.iloc[-1]; asof=str(pd.Timestamp(row.date).date())
        entry=float(pos["entry"]); stop=float(pos["stop"]); target1=float(pos["target1"]); target2=float(pos["target2"])
        entered=pd.Timestamp(pos["bought_at"]).normalize()
        period=h[pd.to_datetime(h.date).dt.normalize()>=entered]
        held=int(len(period)-1)
        high=float(row.high); low=float(row.low); close=float(row.close)
        # The labels state current path only; they never claim a future win probability.
        broke=bool(not period.empty and float(period.low.min())<stop)
        peak=float(period.high.max()) if not period.empty else high
        if broke: status="작전실패 · 매도 확인"; action="손절 기준 이탈"
        elif peak>=target2: status="목표2 도달"; action="익절 또는 보유 판단"
        elif peak>=target1: status="목표1 도달"; action="손익 보호 구간"
        elif close>=entry: status="상승 시나리오 유지"; action="보유"
        else: status="A 위 경계"; action="추가매수 금지·관찰"
        obs={"date":asof,"close":round(close,2),"high":round(high,2),"low":round(low,2),
             "held_days":max(0,held),"return_pct":round((close/entry-1)*100,2),"status":status,"action":action}
        history=[x for x in pos.get("history",[]) if x.get("date")!=asof]; history.append(obs)
        pos.update({"last_date":asof,"last_price":round(close,2),"last_return_pct":obs["return_pct"],"held_days":obs["held_days"],
                    "status":status,"action":action,"history":history[-25:]})
        if held>=20: pos["review"]="20일 추적 완료"
        elif held>=10: pos["review"]="10일 중간 평가"
        else: pos["review"]="추적 중"
    except Exception: pass
    return pos

def _campaign_update_candidate(pos,quotes=None):
    """추천가·A를 고정하고, 기간 제한 없이 동적 매도 신호까지 전진 추적한다."""
    if pos.get("exit_date"):return pos
    h=_campaign_history(pos["code"],quotes)
    if h is None or h.empty:return pos
    try:
        h=h.copy().sort_values("date").reset_index(drop=True)
        for col in ("high","low","close"):h[col]=pd.to_numeric(h[col],errors="coerce")
        h=h.dropna(subset=["date","high","low","close"])
        start=pd.Timestamp(pos.get("captured_at",now_kst().date())).normalize()
        period=h[pd.to_datetime(h.date).dt.normalize()>=start]
        if period.empty:return pos
        row=period.iloc[-1]; entry=float(pos["price"]); stop=float(pos["A"]); held=max(0,len(period)-1)
        peak=float(period.high.max()); trough=float(period.low.min()); close=float(row.close)
        hit10=peak>=entry*1.10; hit20=peak>=entry*1.20
        dyn=_campaign_dynamic_exit(h,start,entry,stop);broke=bool(dyn.get("exit") and dyn.get("reason")=="A 장중 이탈")
        if dyn.get("exit"):
            close=float(dyn.get("exit_price",close));status=f"매도 신호 · {dyn.get('reason','')}";action="결과 고정"
            held=max(0,len(period[pd.to_datetime(period.date).dt.normalize()<=pd.Timestamp(dyn.get("date")).normalize()])-1)
        elif hit20:status="+20% 이상 상승 중";action="추세 보유"
        elif hit10:status="+10% 이상 상승 중";action="추세 보유"
        elif close>=entry:status="상승 중";action="추세 보유"
        else:status="A 위 조정 중";action="추적 계속"
        obs={"date":str(pd.Timestamp(row.date).date()),"close":round(close,2),"return_pct":round((close/entry-1)*100,2),
             "held_days":held,"peak_pct":round((peak/entry-1)*100,2),"trough_pct":round((trough/entry-1)*100,2),"A_broken":broke,"hit10":hit10,"hit20":hit20}
        history=[x for x in pos.get("history",[]) if x.get("date")!=obs["date"]];history.append(obs)
        pos.update({"last_date":obs["date"],"last_price":round(close,2),"last_return_pct":obs["return_pct"],"held_days":held,
                    "peak_pct":obs["peak_pct"],"trough_pct":obs["trough_pct"],"A_broken":broke,"hit10":hit10,"hit20":hit20,
                    "status":status,"action":action,"review":"매도 신호 확정" if dyn.get("exit") else "기간 제한 없이 추적 중","history":history[-60:]})
        if dyn.get("exit"):pos.update({"exit_date":dyn.get("date"),"exit_price":round(close,2),"exit_reason":dyn.get("reason"),"realized_return_pct":obs["return_pct"]})
    except Exception:pass
    return pos

def _campaign_refresh(state):
    active=state.get("active",[])
    candidates=state.get("candidates",[])
    quotes={}
    try:
        now=now_kst()
        if (active or candidates) and kis_ready() and now.weekday()<5 and now.time()>=dt_time(9,0):
            codes=list(dict.fromkeys([x["code"] for x in active+candidates]))
            quotes=_kis_multi_quote(codes,token=kis_access_token())
    except Exception: quotes={}
    state["active"]=[_campaign_update_one(dict(pos),quotes) for pos in active]
    state["candidates"]=[_campaign_update_candidate(dict(pos),quotes) for pos in candidates]
    state["last_update"]=now_kst().strftime("%Y-%m-%d %H:%M")
    return state

def _campaign_active_rows(state):
    rows=[]
    for p in state.get("active",[]):
        rows.append({"종목":f"{p.get('name','')} ({p.get('code','')})","매수가":won(p.get("entry",0)),"현재가":won(p.get("last_price",p.get("entry",0))),
            "수익률":f"{float(p.get('last_return_pct',0)):+.2f}%","손절":won(p.get("stop",0)),"목표1":won(p.get("target1",0)),"목표2":won(p.get("target2",0)),
            "보유일":p.get("held_days",0),"상태":p.get("status","가격 갱신 필요"),"오늘 행동":p.get("action","갱신")})
    return rows

def _campaign_candidate_rows(state):
    rows=[]
    for x in state.get("candidates",[]):
        rows.append({"종목":f"{x.get('name','')} ({x.get('code','')})","추천일":x.get("captured_at","-"),"고정가":won(x.get("price",0)),
            "현재가":won(x.get("last_price",x.get("price",0))),"현재수익":f"{float(x.get('last_return_pct',0)):+.2f}%",
            "최대상승":f"{float(x.get('peak_pct',0)):+.2f}%","최대하락":f"{float(x.get('trough_pct',0)):+.2f}%","A":won(x.get("A",0)),
            "추적일":x.get("held_days",0),"상태":x.get("status","갱신 필요"),"매수선택":"선택" if x.get("selected") else "-"})
    return rows

# 경규님 실제 보유자산. ETF는 장기 핵심, 개별주는 신규 우위 후보가
# 있을 때만 교체하는 자산으로 분리한다. 점수는 성공확률이 아니라
# 보유 종목끼리 비교하기 위한 동일 척도다.
PORTFOLIO_CAPITAL=11755564
PORTFOLIO_HOLDINGS=[
    {"code":"006660","name":"삼성공조","kind":"개별주","buy_date":"2026-09-10","qty":77,"avg":12950},
    {"code":"317830","name":"에스피시스템스","kind":"개별주","buy_date":"2026-06-01","qty":60,"avg":6863},
    {"code":"033100","name":"제룡전기","kind":"개별주","buy_date":"2026-06-10","qty":64,"avg":47917},
    {"code":"469150","name":"ACE AI반도체TOP3+","kind":"ETF","buy_date":"2026-03-18","qty":74,"avg":62391},
    {"code":"379800","name":"KODEX 미국S&P500","kind":"ETF","buy_date":"2026-06-04","qty":94,"avg":25158},
    {"code":"034220","name":"LG디스플레이","kind":"개별주","buy_date":"2026-06-02","qty":20,"avg":14908},
]

def _portfolio_one(h,quotes=None):
    out=dict(h);out["principal"]=int(h["qty"]*h["avg"])
    d=_campaign_history(h["code"],quotes)
    if d is None or d.empty:
        out.update({"current":None,"value":None,"pnl":None,"pnl_pct":None,"strength":None,"A":None,"action":"가격 갱신 필요","reason":"저장 일봉 없음"});return out
    try:
        d=d.copy().sort_values("date").reset_index(drop=True)
        for c in ("open","high","low","close","volume"):d[c]=pd.to_numeric(d[c],errors="coerce")
        d=d.dropna(subset=["date","high","low","close"])
        close=float(d.close.iloc[-1]);low=float(d.low.iloc[-1]);ma20=float(d.close.rolling(20).mean().iloc[-1]);ma60=float(d.close.rolling(60).mean().iloc[-1]);ma120=float(d.close.rolling(120).mean().iloc[-1])
        ma60_prev=float(d.close.rolling(60).mean().iloc[-6]);ret20=(close/float(d.close.iloc[-21])-1)*100 if len(d)>=21 else 0
        x=_mtf_context(d);a_idx,a=_surviving_prior_low(x,len(x)-1);a=float(a) if a is not None and np.isfinite(a) else None
        # 고정 실전점수: 차트 60 + 실제 최근 수급 20. 실적 15와 뉴스 5는
        # 신뢰 가능한 자동 원천이 연결되기 전까지 점수에 넣어 추정하지 않는다.
        chart_score=(10 if close>=ma20 else 0)+(12 if close>=ma60 else 0)+(10 if close>=ma120 else 0)+(10 if ma60>=ma60_prev else 0)+(8 if ret20>=0 else 0)+(10 if a is not None and low>=a else 0)
        flow=investor_flow(h["code"],0)
        flow_available=any(flow.get(k) is not None for k in ("foreign_5","inst_5"))
        flow_score=((10 if float(flow.get("foreign_5") or 0)>0 else 0)+(10 if float(flow.get("inst_5") or 0)>0 else 0)) if flow_available else None
        # 비교점수는 누락 수급 때문에 종목을 자동 탈락시키지 않도록 차트점수를
        # 80점 척도로 환산한다. 수급이 있으면 실제 20점을 그대로 사용한다.
        score=int(round(chart_score+(flow_score if flow_available else chart_score/3)))
        score=max(0,min(80,score))
        if h["kind"]=="ETF":
            action="장기유지" if close>=ma120 else "ETF 비중점검";reason="장기 핵심자산 · 120일선 기준"
        elif a is not None and low<a:
            action="매도우선";reason=f"A {won(a)} 장중 이탈"
        elif close<ma60 and ma60<ma60_prev:
            action="경계";reason="60일선 아래·60일선 하락"
        elif score<45:
            action="교체검토";reason="보유 상대강도 최하위권"
        else:
            action="유지";reason="A·중기추세 유지"
        value=int(round(close*h["qty"]));principal=int(h["qty"]*h["avg"])
        out.update({"current":close,"value":value,"pnl":value-principal,"pnl_pct":round((close/h["avg"]-1)*100,2),"strength":score,"chart_score":chart_score,"flow_score":flow_score,"flow_available":flow_available,"foreign_5":flow.get("foreign_5"),"inst_5":flow.get("inst_5"),"A":a,"action":action,"reason":reason,"ret20":round(ret20,2)})
    except Exception as e:out.update({"current":None,"value":None,"pnl":None,"pnl_pct":None,"strength":None,"A":None,"action":"계산 확인","reason":str(e)[:60]})
    return out

def _portfolio_rows(items):
    return [{"구분":z["kind"],"종목":z["name"],"수량":z["qty"],"평단":won(z["avg"]),"현재가":won(z["current"]) if z.get("current") else "-",
             "평가금액":won(z["value"]) if z.get("value") is not None else "-","손익":won(z["pnl"]) if z.get("pnl") is not None else "-",
             "수익률":f"{z['pnl_pct']:+.2f}%" if z.get("pnl_pct") is not None else "-","A":won(z["A"]) if z.get("A") else "-",
             "차트/60":z.get("chart_score","-"),"수급/20":z.get("flow_score") if z.get("flow_score") is not None else "미수집",
             "실전점수/80":z.get("strength") if z.get("strength") is not None else "-","오늘 행동":z["action"],"이유":z["reason"]} for z in items]

def _render_live_engine_status(items):
    """5초 판단용 고정 엔진 상태. 확률처럼 보이는 허위 숫자를 만들지 않는다."""
    valid=[x for x in items if x.get("strength") is not None]
    if not valid:return
    weakest=min([x for x in valid if x.get("kind")=="개별주"] or valid,key=lambda x:x["strength"])
    strongest=max(valid,key=lambda x:x["strength"])
    broken=[x for x in valid if x.get("action")=="매도우선"]
    watch=[x for x in valid if x.get("action") in ("경계","교체검토")]
    st.markdown("#### 오늘 5초 행동판")
    a,b,c,d=st.columns(4)
    a.metric("엔진",LIVE_ENGINE_VERSION)
    b.metric("최강 보유",f"{strongest['name']} {strongest['strength']}/80")
    c.metric("최약 개별주",f"{weakest['name']} {weakest['strength']}/80")
    d.metric("구조 이탈",f"{len(broken)}종목")
    if broken:
        st.error("우선 확인: "+", ".join(f"{x['name']}({x['reason']})" for x in broken))
    elif watch:
        st.warning("교체 대기: "+", ".join(x["name"] for x in watch)+" · 더 강한 최종후보가 나올 때만 실행")
    else:
        st.success("오늘 즉시 매도 신호 없음 · 보유 유지")
    st.caption("점수 구성: 차트 60 + 실제 외국인·기관 5일 수급 20. 실적 15·뉴스 5는 자동 원천 연결 전까지 점수에서 제외하고 위험 차단용으로만 사용합니다.")

def _render_portfolio_projection(selected,timeframe="일봉"):
    """Actual OHLC is candlestick; dotted scenarios adapt to daily/weekly/monthly bars."""
    h=next((x for x in PORTFOLIO_HOLDINGS if x["code"]==selected.get("code")),None)
    if not h:return
    d=_campaign_history(h["code"])
    if d is None or len(d)<65:
        st.info("예상 경로를 그릴 일봉 자료가 부족합니다.");return
    d=d.copy().sort_values("date").reset_index(drop=True)
    d["date"]=pd.to_datetime(d.date)
    for col in ("open","high","low","close"):d[col]=pd.to_numeric(d[col],errors="coerce")
    d=d.dropna(subset=["date","open","high","low","close"])
    cfg={"일봉":{"freq":None,"hist":120,"future":20,"fit":60,"cap":.012,"unit":"20거래일","labels":["10일선","20일선","60일선"]},
         "주봉":{"freq":"W-FRI","hist":104,"future":12,"fit":40,"cap":.04,"unit":"12주","labels":["10주선","20주선","60주선"]},
         "월봉":{"freq":"ME","hist":72,"future":6,"fit":36,"cap":.10,"unit":"6개월","labels":["10개월선","20개월선","60개월선"]}}[timeframe]
    if cfg["freq"]:
        d=d.set_index("date").resample(cfg["freq"]).agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index()
    if len(d)<12:st.info(f"{timeframe} 차트를 그릴 자료가 부족합니다.");return
    d["ma10"]=d.close.rolling(10).mean();d["ma20"]=d.close.rolling(20).mean();d["ma60"]=d.close.rolling(60).mean()
    fit=d.tail(min(cfg["fit"],len(d)));y=np.log(fit.close.to_numpy(dtype=float));x=np.arange(len(y),dtype=float)
    slope=float(np.polyfit(x,y,1)[0]);slope=max(-cfg["cap"],min(cfg["cap"],slope))*0.60
    returns=np.diff(y);vol=float(np.nanstd(returns[-40:])) if len(returns) else 0.0
    last=float(d.close.iloc[-1]);last_date=pd.Timestamp(d.date.iloc[-1])
    if timeframe=="일봉":future=pd.bdate_range(last_date+pd.Timedelta(days=1),periods=cfg["future"])
    elif timeframe=="주봉":future=pd.date_range(last_date+pd.Timedelta(days=7),periods=cfg["future"],freq="W-FRI")
    else:future=pd.date_range(last_date+pd.offsets.MonthEnd(1),periods=cfg["future"],freq="ME")
    hist=d.tail(cfg["hist"]);candles=[];ma_rows=[];forecast_rows=[];ma_labels=cfg["labels"]
    for _,r in hist.iterrows():
        day=str(pd.Timestamp(r.date).date())
        candles.append({"date":day,"open":float(r.open),"high":float(r.high),"low":float(r.low),"close":float(r.close),"direction":"상승" if float(r.close)>=float(r.open) else "하락"})
        if pd.notna(r.ma10):ma_rows.append({"date":day,"value":float(r.ma10),"series":ma_labels[0]})
        if pd.notna(r.ma20):ma_rows.append({"date":day,"value":float(r.ma20),"series":ma_labels[1]})
        if pd.notna(r.ma60):ma_rows.append({"date":day,"value":float(r.ma60),"series":ma_labels[2]})
    forecast_rows.extend([
        {"date":str(last_date.date()),"value":last,"series":"기준 경로"},
        {"date":str(last_date.date()),"value":last,"series":"상승 경로"},
        {"date":str(last_date.date()),"value":last,"series":"하락 경로"}])
    base=upper=lower=last
    for i,day in enumerate(future,1):
        base=last*math.exp(slope*i);spread=min(0.28,vol*math.sqrt(i)*0.75)
        upper=base*math.exp(spread);lower=base*math.exp(-spread)
        ds=str(day.date());forecast_rows.extend([
            {"date":ds,"value":round(base,2),"series":"기준 경로"},
            {"date":ds,"value":round(upper,2),"series":"상승 경로"},
            {"date":ds,"value":round(lower,2),"series":"하락 경로"}])
    avg=float(h["avg"]);a=float(selected.get("A") or 0)
    if go is None:
        fallback=hist.set_index("date")[["close","ma10","ma20","ma60"]].rename(columns={"close":"종가","ma10":ma_labels[0],"ma20":ma_labels[1],"ma60":ma_labels[2]})
        st.warning("확대형 봉차트 모듈이 아직 설치되지 않아 기본 차트로 표시합니다. 배포 저장소의 requirements.txt에 plotly>=5.18,<7을 추가하면 봉차트가 자동 복구됩니다.")
        st.line_chart(fallback,use_container_width=True,height=460)
        return
    fig=go.Figure()
    fig.add_trace(go.Candlestick(x=hist["date"],open=hist["open"],high=hist["high"],low=hist["low"],close=hist["close"],
        name="봉",increasing_line_color="#ef5350",increasing_fillcolor="#ef5350",decreasing_line_color="#3f8cff",decreasing_fillcolor="#3f8cff"))
    ma_colors={ma_labels[0]:"#ffd84d",ma_labels[1]:"#4ea1ff",ma_labels[2]:"#b06cff"}
    ma_df=pd.DataFrame(ma_rows)
    for label,color in ma_colors.items():
        q=ma_df[ma_df["series"]==label] if not ma_df.empty else pd.DataFrame()
        if not q.empty:fig.add_trace(go.Scatter(x=q["date"],y=q["value"],mode="lines",name=label,line=dict(color=color,width=1.6)))
    forecast_colors={"기준 경로":"#62d26f","상승 경로":"#40c9a2","하락 경로":"#ef6461"}
    forecast_df=pd.DataFrame(forecast_rows)
    for label,color in forecast_colors.items():
        q=forecast_df[forecast_df["series"]==label]
        fig.add_trace(go.Scatter(x=q["date"],y=q["value"],mode="lines",name=label,line=dict(color=color,width=2.2,dash="dash")))
    fig.add_hline(y=avg,line_dash="dot",line_color="#f6c344",annotation_text="평단",annotation_position="top left")
    if a>0:fig.add_hline(y=a,line_dash="dot",line_color="#ef6461",annotation_text="A 지지",annotation_position="bottom left")
    fig.update_layout(height=520,margin=dict(l=8,r=8,t=18,b=8),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6e9ed"),hovermode="x unified",dragmode="pan",legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="left",x=0),
        xaxis=dict(title=None,gridcolor="#30343b",rangeslider=dict(visible=True,thickness=.09),rangeselector=dict(buttons=[
            dict(count=1,label="1개월",step="month",stepmode="backward"),dict(count=3,label="3개월",step="month",stepmode="backward"),
            dict(count=6,label="6개월",step="month",stepmode="backward"),dict(step="all",label="전체")],bgcolor="#1b1f25",activecolor="#48515e")),
        yaxis=dict(title="가격(원)",gridcolor="#30343b",fixedrange=False),uirevision=f"{h['code']}-{timeframe}")
    st.plotly_chart(fig,use_container_width=True,config={"scrollZoom":True,"displaylogo":False,"responsive":True,"modeBarButtonsToRemove":["select2d","lasso2d"]})
    base_ret=(base/last-1)*100;upper_ret=(upper/last-1)*100;lower_ret=(lower/last-1)*100;recovery=(avg/last-1)*100
    c1,c2,c3,c4=st.columns(4);c1.metric(f"{cfg['unit']} 기준경로",f"{base_ret:+.1f}%");c2.metric("상승 시나리오",f"{upper_ret:+.1f}%");c3.metric("하락 시나리오",f"{lower_ret:+.1f}%");c4.metric("평단 회복 필요",f"{recovery:+.1f}%")
    if base>=avg:st.success(f"기준 경로상 {cfg['unit']} 내 평단 {won(avg)} 회복 구간에 도달합니다.")
    elif upper>=avg:st.warning(f"기준 경로는 평단 미달, 상승 시나리오에서만 평단 {won(avg)} 회복 가능 구간입니다.")
    else:st.error(f"현재 {cfg['unit']} 시나리오 범위로는 평단 {won(avg)} 회복 여력이 부족합니다.")
    st.caption(f"휠로 확대·축소, 드래그로 좌우 이동, 아래 범위막대로 기간을 조절할 수 있습니다. 빨간 봉은 상승, 파란 봉은 하락이며 노란선은 {ma_labels[0]}입니다. 미래 점선은 통계적 시나리오이며 보장된 목표가가 아닙니다.")

def _render_portfolio_adviser():
    st.divider();st.subheader("🧭 내 자금 운용 참모 · 보유→매도→교체")
    st.caption("총 운용원금 안에서만 교체합니다. 신규 후보가 최약체 개별주보다 명확히 강할 때만 매도대금 범위로 매수수량을 계산합니다.")
    state=_campaign_read();quotes={}
    if st.button("보유 6종목 오늘 판단 갱신",type="primary",key="portfolio_refresh"):
        try:
            if kis_ready():quotes=_kis_multi_quote([x["code"] for x in PORTFOLIO_HOLDINGS],token=kis_access_token())
        except:quotes={}
        items=[_portfolio_one(x,quotes) for x in PORTFOLIO_HOLDINGS]
        _vg_write(CAMPAIGN_DIR/"portfolio_today.json",{"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"items":items})
        st.rerun()
    saved=_vg_read(CAMPAIGN_DIR/"portfolio_today.json");items=saved.get("items",[])
    if not items:
        st.info("보유 6종목 오늘 판단 갱신을 눌러 첫 판단을 만드세요.");return
    total_value=sum(float(z.get("value") or 0) for z in items);total_pnl=total_value-PORTFOLIO_CAPITAL
    cash=max(0,PORTFOLIO_CAPITAL-total_value) if total_value<PORTFOLIO_CAPITAL else 0
    k1,k2,k3,k4=st.columns(4);k1.metric("고정 운용원금",won(PORTFOLIO_CAPITAL));k2.metric("현재 평가액",won(total_value));k3.metric("평가손익",won(total_pnl));k4.metric("신규 투입금",won(0))
    st.caption(f"최근 판단 {saved.get('updated_at','')} · 실전점수는 종목간 비교용이며 상승확률이 아닙니다.")
    _render_live_engine_status(items)
    st.dataframe(pd.DataFrame(_portfolio_rows(items)),use_container_width=True,hide_index=True)
    st.markdown("#### 보유종목 회복·상승 예상 차트")
    chart_name=st.selectbox("차트를 볼 종목",[z["name"] for z in items],key="portfolio_chart_name")
    chart_tf=st.radio("차트 기간",["일봉","주봉","월봉"],horizontal=True,key="portfolio_chart_tf")
    chart_item=next(z for z in items if z["name"]==chart_name)
    _render_portfolio_projection(chart_item,chart_tf)
    stocks=[z for z in items if z.get("kind")=="개별주" and z.get("strength") is not None]
    weakest=min(stocks,key=lambda z:(z.get("strength",999),z.get("pnl_pct",0))) if stocks else None
    candidates=[z for z in state.get("candidates",[]) if not z.get("A_broken") and z.get("status") not in ("A 이탈 · 후보 실패",)]
    if weakest:
        st.markdown("#### 오늘의 교체 판단")
        if weakest.get("action")=="매도우선":
            st.error(f"먼저 확인: {weakest['name']} {weakest['qty']}주 · {weakest['reason']} · 예상 확보 {won(weakest.get('value',0))}")
        elif weakest.get("action") in ("경계","교체검토"):
            st.warning(f"최약체: {weakest['name']} · {weakest['action']} · {weakest['reason']}")
        else:st.success(f"현재 최약체 {weakest['name']}도 즉시 매도 신호 없음 · 신규 후보가 명확히 우위일 때만 교체")
        # 교체 후보는 고정 엔진이 개발구간뿐 아니라 독립 확인구간까지
        # 통과한 경우에만 사용한다. 과거 10일선 후보나 관찰 순위는 금지한다.
        live=_vg_read(RANK_ENGINE_RESULT) if RANK_ENGINE_RESULT.exists() else {}
        final_candidates=live.get("candidates",[]) if isinstance(live,dict) and live.get("version")==RANK_ENGINE_VERSION and live.get("verdict")=="독립 확인 통과 후보" else []
        if not final_candidates:
            st.info("오늘 최종 진입 후보 0개 → 기존 보유 유지 또는 매도 후 현금. 억지 교체 없음.")
        else:
            c=final_candidates[0]
            candidate_h={"code":str(c.get("종목코드",c.get("code",""))).zfill(6),"name":c.get("종목명",c.get("name","")),"kind":"개별주","buy_date":"","qty":1,"avg":float(c.get("현재가",c.get("기준 종가",0)) or 1)}
            candidate=_portfolio_one(candidate_h)
            gap=(candidate.get("strength") or 0)-(weakest.get("strength") or 0)
            price=float(candidate.get("current") or c.get("현재가",c.get("기준 종가",0)) or 0);proceeds=float(weakest.get("value",0) or 0);qty=int(proceeds//price) if price>0 else 0
            if candidate.get("strength") is None:
                st.info("최종 후보의 현재 일봉이 아직 준비되지 않아 교체 판단을 보류합니다.")
            elif gap<15:
                st.info(f"교체 보류: {candidate_h['name']} 상태점수 {candidate['strength']}점 · {weakest['name']} 대비 +{gap}점. 명확한 우위 기준 +15점 미달입니다.")
            elif weakest.get("action")=="유지":
                st.info(f"후보 {candidate_h['name']}은 +{gap}점 우위지만, 현재 보유주에 매도 신호가 없어 교체를 보류합니다.")
            else:
                st.warning(f"교체 검토: {weakest['name']} {weakest['qty']}주 전량매도 예상금 {won(proceeds)} → {candidate_h['name']} 최대 {qty}주 · 상태점수 +{gap}점 우위 · 실제 주문은 사용자 확인 후")

def _render_campaign_manager():
    st.divider(); st.subheader("📋 정밀 후보 5종목 · 동적 매도 전진검증")
    st.caption("추천 당시 가격과 A를 고정하고 5개 이하만 추적합니다. 15일에 강제 매도하지 않고, A 이탈 또는 수익구간의 추세 약화 신호가 나올 때까지 추적합니다.")
    state=_campaign_read()
    c1,c2=st.columns(2)
    with c1:
        if st.button("현재 정밀 후보 최대 5개 고정",key="campaign_fill"):
            added=_campaign_fill_candidates(state); _campaign_write(state)
            st.success(f"{added}개 후보를 추가했습니다."); st.rerun()
    with c2:
        if st.button("후보·보유 오늘 상태 갱신",key="campaign_refresh"):
            with st.spinner("후보 10개와 보유 종목의 실제 가격 경로를 갱신 중입니다..."):
                state=_campaign_refresh(state); _campaign_write(state)
            st.rerun()
    done10=sum(int(x.get("held_days",0))>=10 for x in state.get("candidates",[]));done20=sum(int(x.get("held_days",0))>=20 for x in state.get("candidates",[]))
    hit10=sum(bool(x.get("hit10")) for x in state.get("candidates",[]));failed=sum(bool(x.get("A_broken")) for x in state.get("candidates",[]))
    st.caption(f"최근 갱신: {state.get('last_update') or '아직 없음'} · 후보 {len(state.get('candidates',[]))}/5 · 보유 {len(state.get('active',[]))}/2")
    if state.get("candidates"):
        k1,k2,k3,k4=st.columns(4);k1.metric("10일 이상 추적",done10);k2.metric("20일 이상 추적",done20);k3.metric("+10% 도달",hit10);k4.metric("A 이탈",failed)
    active_rows=_campaign_active_rows(state)
    if active_rows:
        st.markdown("#### 현재 보유 · 오늘 행동")
        st.dataframe(pd.DataFrame(active_rows),use_container_width=True,hide_index=True)
    else:
        st.info("현재 매수 등록 종목이 없습니다. 후보에서 1~2개만 선택해 매수 등록하세요.")
    candidates=state.get("candidates",[])
    if candidates:
        st.markdown("#### 고정 후보 전진검증")
        st.dataframe(pd.DataFrame(_campaign_candidate_rows(state)),use_container_width=True,hide_index=True)
    available=[x for x in candidates if not x.get("selected") and x["code"] not in {p["code"] for p in state.get("active",[])}]
    if len(state.get("active",[]))<2 and available:
        labels={f"{x['name']} ({x['code']}) · {won(x['price'])}":x for x in available}
        choice=st.selectbox("매수 등록 종목",list(labels),key="campaign_buy_choice")
        x=labels[choice]
        a,b,c=st.columns(3)
        with a: entry=st.number_input("실제 매수가",min_value=1.0,value=float(x["price"]),step=10.0,key="campaign_entry")
        with b: stop=st.number_input("손절가",min_value=1.0,value=float(x["A"]),step=10.0,key="campaign_stop")
        with c: target2=st.number_input("2차 목표가",min_value=1.0,value=round(float(entry)*1.20,2),step=10.0,key="campaign_target2")
        if st.button("이 종목 매수 등록",type="primary",key="campaign_buy"):
            if stop>=entry: st.error("손절가는 실제 매수가보다 낮아야 합니다.")
            else:
                state["active"].append({"id":f"{x['code']}-{now_kst().strftime('%Y%m%d%H%M%S')}","code":x["code"],"name":x["name"],"bought_at":str(now_kst().date()),"entry":float(entry),"stop":float(stop),"target1":round(float(entry)*1.10,2),"target2":float(target2),"history":[],"status":"매수 등록 · 가격 갱신 필요","action":"오늘 상태 갱신"})
                for z in state["candidates"]:
                    if z["code"]==x["code"]:z["selected"]=True;z["selected_at"]=str(now_kst().date())
                _campaign_write(state); st.rerun()
    if state.get("active"):
        st.markdown("#### 매도 완료")
        labels={f"{x['name']} ({x['code']})":x for x in state["active"]}
        sold_key=st.selectbox("매도 종목",list(labels),key="campaign_sell_choice"); p=labels[sold_key]
        sale=st.number_input("실제 매도가",min_value=1.0,value=float(p.get("last_price",p["entry"])),step=10.0,key="campaign_sale_price")
        if st.button("매도 완료 · 다음 후보 자리 열기",key="campaign_sell"):
            p=dict(p); p.update({"sold_at":str(now_kst().date()),"sale_price":float(sale),"sale_return_pct":round((float(sale)/float(p["entry"])-1)*100,2)})
            state["closed"].append(p); state["active"]=[x for x in state["active"] if x["id"]!=p["id"]]
            _campaign_fill_candidates(state);_campaign_write(state);st.rerun()
    if state.get("closed"):
        st.markdown("#### 완료된 추천 성적")
        hist=pd.DataFrame([{ "종목":f"{x['name']} ({x['code']})","매수일":x.get("bought_at"),"매수가":won(x["entry"]),"매도일":x.get("sold_at"),"매도가":won(x.get("sale_price",0)),"실현수익률":f"{x.get('sale_return_pct',0):+.2f}%"} for x in state["closed"]])
        st.dataframe(hist,use_container_width=True,hide_index=True)

# 월봉→주봉→일봉 10선 왕복전략 검증기. 신호는 고가/저가가 아니라
# 각 봉의 확정 종가만 사용한다. 월봉은 월말, 주봉은 금요일 확정값을
# 다음 거래일부터 사용해 미래 데이터를 미리 보는 오류를 막는다.
MTF10_RESULT=Path("data")/"mtf10_relative_strength_backtest.json"
MTF10_PREP_STATUS=Path("data")/"mtf10_prepare_status.json"
MTF10_INDEX_STATUS=Path("data")/"mtf10_index_prepare_status.json"
MTF10_VERSION="MTF10_CLOSE_ONLY_V13_RS_WALK_FORWARD_20260928"
MTF10_MIN_ROWS=900
MTF10_QUICK_CODES="005930, 000660, 005380, 035420, 035720"
MTF10_EXPANDED_CODES=("005930, 000660, 005380, 035420, 035720, 051910, 006400, 012330, 000270, 105560, "
                      "055550, 086790, 316140, 034020, 010140, 009540, 042660, 028260, 003550, 017670, "
                      "030200, 066570, 011200, 096770, 047050, 032830, 018260, 090430, 004020, 010950")

def _mtf_bars(d,rule):
    x=d.set_index("date").sort_index()
    return x.resample(rule).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum")).dropna(subset=["close"])

def _mtf_index_cache_path(market):
    p=Path("data")/"mtf10_index"
    p.mkdir(parents=True,exist_ok=True)
    return p/f"{market}.csv"

def _mtf_index_rows(rows):
    out=[]
    for r in rows or []:
        try:
            day=str(r.get("stck_bsop_date") or "")
            close=float(str(r.get("bstp_nmix_prpr") or 0).replace(",",""))
            if len(day)==8 and close>0:
                out.append({"date":pd.to_datetime(day,format="%Y%m%d"),"close":close})
        except:pass
    return out

def _mtf_fetch_index_window(market,start_dt,end_dt,token):
    app_key,app_secret,_=kis_credentials()
    url=f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice"
    headers={"authorization":f"Bearer {token}","appkey":app_key,"appsecret":app_secret,"tr_id":"FHKUP03500100","custtype":"P"}
    params={"FID_COND_MRKT_DIV_CODE":"U","FID_INPUT_ISCD":"0001" if market=="KOSPI" else "1001",
            "FID_INPUT_DATE_1":pd.Timestamp(start_dt).strftime("%Y%m%d"),"FID_INPUT_DATE_2":pd.Timestamp(end_dt).strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE":"D"}
    for retry in range(3):
        try:
            r=requests.get(url,headers=headers,params=params,timeout=10)
            if r.status_code==200:
                js=r.json()
                if str(js.get("rt_cd","0")) in ("0",""):
                    raw=js.get("output2") or js.get("output") or []
                    if isinstance(raw,dict):raw=[raw]
                    return _mtf_index_rows(raw)
        except:pass
        time.sleep(0.2*(retry+1))
    return []

def _mtf_prepare_indexes(token):
    end_dt=pd.Timestamp(now_kst().date())-pd.Timedelta(days=1)
    start_dt=end_dt-pd.DateOffset(years=6)
    rows=[]
    for market in ("KOSPI","KOSDAQ"):
        path=_mtf_index_cache_path(market)
        try:q=pd.read_csv(path,parse_dates=["date"]) if path.exists() else pd.DataFrame(columns=["date","close"])
        except:q=pd.DataFrame(columns=["date","close"])
        for _ in range(24):
            cur_end=end_dt if q.empty else pd.Timestamp(q.date.min())-pd.Timedelta(days=1)
            if not q.empty and pd.Timestamp(q.date.min())<=start_dt+pd.Timedelta(days=30):break
            batch=_mtf_fetch_index_window(market,start_dt,cur_end,token)
            if not batch:break
            old_min=pd.Timestamp(q.date.min()) if not q.empty else None
            q=pd.concat([q,pd.DataFrame(batch)],ignore_index=True).drop_duplicates("date").sort_values("date")
            if old_min is not None and pd.Timestamp(q.date.min())>=old_min:break
            time.sleep(0.08)
        if not q.empty:q.to_csv(path,index=False,date_format="%Y-%m-%d")
        rows.append({"시장지수":market,"저장봉":len(q),"시작일":str(pd.Timestamp(q.date.min()).date()) if not q.empty else "-","종료일":str(pd.Timestamp(q.date.max()).date()) if not q.empty else "-","상태":"준비완료" if len(q)>=MTF10_MIN_ROWS else "자료부족"})
    status={"ok":all(z["저장봉"]>=MTF10_MIN_ROWS for z in rows),"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"rows":rows}
    _vg_write(MTF10_INDEX_STATUS,status)
    return status

def _mtf_load_index(market):
    try:
        q=pd.read_csv(_mtf_index_cache_path(market),parse_dates=["date"])
        q["close"]=pd.to_numeric(q.close,errors="coerce")
        return q.dropna(subset=["date","close"]).drop_duplicates("date").sort_values("date")
    except:return pd.DataFrame()

def _mtf_market_map(targets):
    known={}
    try:
        main,_,low,_=universe()
        known={str(z.get("code","")).zfill(6):z.get("market","") for z in main+low}
    except:pass
    # 현재 기본 30종목은 모두 유가증권시장 종목이다. 사용자 입력 종목은
    # KIS 마스터 결과를 우선 사용하고, 확인되지 않은 코드는 계산에서 제외한다.
    return {code:known.get(code, "KOSPI" if code in set(MTF10_EXPANDED_CODES.replace(" ","").split(",")) else "") for code in targets}

def _mtf_context(d,benchmark=None):
    x=d.copy().sort_values("date").set_index("date")
    x["d10"]=x.close.rolling(10).mean()
    x["d20"]=x.close.rolling(20).mean()
    x["d60"]=x.close.rolling(60).mean(); x["d60_up"]=(x.close>=x.d60)&(x.d60>x.d60.shift(5))
    x["d120"]=x.close.rolling(120).mean()
    # 진입 당일을 제외한 직전 20거래일 평균과 비교해 미래참조와
    # 당일 거래량의 자기포함 왜곡을 피한다.
    x["vol20_prev"]=x.volume.shift(1).rolling(20).mean()
    x["volume_ratio"]=x.volume/x.vol20_prev.replace(0,np.nan)
    # 표준 MACD(12, 26, 9). 필수형과 가점형 모두 신호 당일까지의
    # 확정 종가만 사용하므로 미래 자료가 섞이지 않는다.
    ema12=x.close.ewm(span=12,adjust=False,min_periods=12).mean()
    ema26=x.close.ewm(span=26,adjust=False,min_periods=26).mean()
    x["macd"]=ema12-ema26
    x["macd_signal"]=x.macd.ewm(span=9,adjust=False,min_periods=9).mean()
    x["macd_hist"]=x.macd-x.macd_signal
    x["macd_hist_rising2"]=(x.macd_hist>x.macd_hist.shift(1))&(x.macd_hist.shift(1)>x.macd_hist.shift(2))
    # 서로 독립된 세 항목으로 평가한다. MACD>신호선과 히스토그램>0은
    # 같은 식이므로 중복 점수로 세지 않는다.
    x["macd_above_zero"]=(x.macd>0)
    x["macd_score"]=(x.macd_hist>0).astype(int)+x.macd_hist_rising2.astype(int)+x.macd_above_zero.astype(int)
    x["rs20"]=np.nan; x["rs60"]=np.nan
    if benchmark is not None and not benchmark.empty:
        b=benchmark[["date","close"]].copy().sort_values("date").rename(columns={"close":"index_close"})
        b["index_ret20"]=b.index_close.pct_change(20)*100
        b["index_ret60"]=b.index_close.pct_change(60)*100
        x=x.reset_index().sort_values("date")
        x=pd.merge_asof(x,b[["date","index_ret20","index_ret60"]],on="date",direction="backward")
        x=x.set_index("date")
        x["rs20"]=x.close.pct_change(20)*100-x.index_ret20
        x["rs60"]=x.close.pct_change(60)*100-x.index_ret60
    w=_mtf_bars(d,"W-FRI"); w["w10"]=w.close.rolling(10).mean(); w["w_up"]=(w.close>=w.w10)&(w.w10>w.w10.shift(1))
    w["w30"]=w.close.rolling(30).mean(); w["w30_up"]=(w.close>=w.w30)&(w.w30>w.w30.shift(1))
    m=_mtf_bars(d,"ME"); m["m10"]=m.close.rolling(10).mean(); m["m_up"]=(m.close>=m.m10)&(m.m10>m.m10.shift(1))
    # 주봉은 금요일 종가, 월봉은 월말 종가가 확정된 시각부터 유효하다.
    # resample의 라벨 자체가 금요일/월말이므로 추가 shift를 하면 신호가
    # 한 주/한 달 더 늦어지는 오류가 생긴다. 확정 라벨을 그대로 일봉에 전달한다.
    x["w_up"]=w.w_up.reindex(x.index,method="ffill").fillna(False)
    x["w30_up"]=w.w30_up.reindex(x.index,method="ffill").fillna(False)
    x["m_up"]=m.m_up.reindex(x.index,method="ffill").fillna(False)
    x["buy_cross"]=(x.close.shift(1)<x.d10.shift(1))&(x.close>=x.d10)
    x["sell_cross"]=(x.close.shift(1)>x.d10.shift(1))&(x.close<=x.d10)
    return x.reset_index()

def _mtf_trades(d,mode,x=None):
    x=_mtf_context(d) if x is None else x; trades=[]; pos=None
    for i,r in x.iterrows():
        if i<12 or not np.isfinite(r.d10): continue
        if pos is None:
            allow=bool(r.buy_cross) and (mode=="일봉 단독" or (bool(r.w_up) and bool(r.m_up)))
            if allow: pos={"entry_date":r.date,"entry_i":i,"entry":float(r.close),"peak":float(r.close),"trough":float(r.close)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high)); pos["trough"]=min(pos["trough"],float(r.low))
        exit_now=False
        if mode in ("일봉 단독","월주일·즉시매도"): exit_now=bool(r.sell_cross)
        else:
            # 월·주가 모두 상승이면 일봉 하락터치는 단기조정으로 보유.
            exit_now=bool(r.sell_cross) and not (bool(r.w_up) and bool(r.m_up))
        if exit_now:
            ret=(float(r.close)/pos["entry"]-1)*100
            trades.append({"진입일":str(pd.Timestamp(pos["entry_date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"수익률":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["entry_i"],"청산사유":"10일선 매도" if mode!="월주 상승·조정보유" else "상위추세 종료"})
            pos=None
    return trades

def _is_uptrend_pullback_a(x,a_idx):
    """A가 하락장 바닥이 아니라 상승 추세 안의 눌림목 저점인지 확인한다."""
    if a_idx<125:return False
    a=x.iloc[a_idx]
    needed=(a.d20,a.d60,a.d120,x.d60.iloc[a_idx-20])
    if not all(np.isfinite(v) for v in needed):return False
    # A 당시 20>60>120 정배열, 60일선은 20거래일 전보다 상승.
    if not (float(a.d20)>float(a.d60)>float(a.d120) and float(a.d60)>float(x.d60.iloc[a_idx-20])):return False
    # 최근 고점에서 최소 5% 조정이 있어야 눌림목이며, 종가는 60일선의
    # 5% 아래보다 깊게 무너지지 않아 상승 추세가 유지된 자리만 인정한다.
    prev_high=float(x.high.iloc[max(0,a_idx-20):a_idx].max())
    a_low=float(a.low); a_close=float(a.close)
    return bool(prev_high>=a_low*1.05 and a_close>=float(a.d60)*0.95)

def _mtf_a15_trades(d,x=None,max_a_distance=None,trend_filter=False,macd_mode=None,pullback_a=False,min_volume_ratio=None,rs20_min=None,rs60_min=None):
    """월·주 상승 중 일봉 10선 돌파 진입, A 이탈 손절 또는 15거래일 종가 청산."""
    x=_mtf_context(d) if x is None else x; trades=[]; i=125; n=len(x)
    while i<n-15:
        r=x.iloc[i]
        if not (bool(r.buy_cross) and bool(r.w_up) and bool(r.m_up)):
            i+=1; continue
        if trend_filter and not (bool(r.d60_up) and bool(r.w30_up)):
            i+=1; continue
        if macd_mode=="positive" and not (np.isfinite(r.macd_hist) and float(r.macd_hist)>0):
            i+=1; continue
        if macd_mode=="score2" and not (np.isfinite(r.macd_score) and int(r.macd_score)>=2):
            i+=1; continue
        if macd_mode=="strong3" and not (np.isfinite(r.macd_score) and int(r.macd_score)==3):
            i+=1; continue
        if min_volume_ratio is not None and not (np.isfinite(r.volume_ratio) and float(r.volume_ratio)>=float(min_volume_ratio)):
            i+=1; continue
        if rs20_min is not None and not (np.isfinite(r.rs20) and float(r.rs20)>=float(rs20_min)):
            i+=1; continue
        if rs60_min is not None and not (np.isfinite(r.rs60) and float(r.rs60)>=float(rs60_min)):
            i+=1; continue
        a_idx,a=_surviving_prior_low(x,i); entry=float(r.close)
        if a is None or not np.isfinite(a) or a>=entry or float(r.low)<a:
            i+=1; continue
        if pullback_a and not _is_uptrend_pullback_a(x,a_idx):
            i+=1; continue
        a_distance=(entry/float(a)-1)*100
        if max_a_distance is not None and a_distance>float(max_a_distance):
            i+=1; continue
        peak=entry; trough=entry; exit_i=i+15; exit_px=float(x.close.iat[exit_i]); reason="15일 청산"
        hit10=hit20=hit30=False
        for j in range(i+1,i+16):
            o=float(x.open.iat[j]); hi=float(x.high.iat[j]); lo=float(x.low.iat[j])
            if o<a or lo<a:
                # 같은 봉에서 목표가와 A가 모두 닿으면 선후를 알 수 없으므로
                # 목표 도달로 과대평가하지 않고 손절을 먼저 적용한다.
                trough=min(trough,o if o<a else float(a))
                exit_i=j; exit_px=o if o<a else float(a); reason="A 손절"; break
            peak=max(peak,hi); trough=min(trough,lo)
            hit10=hit10 or hi>=entry*1.10; hit20=hit20 or hi>=entry*1.20; hit30=hit30 or hi>=entry*1.30
        trades.append({"진입일":str(pd.Timestamp(r.date).date()),"청산일":str(pd.Timestamp(x.date.iat[exit_i]).date()),"A":float(a),"A일자":str(pd.Timestamp(x.date.iat[a_idx]).date()),"A거리":a_distance,"진입가":entry,"청산가":exit_px,"RS20":round(float(r.rs20),2) if np.isfinite(r.rs20) else None,"RS60":round(float(r.rs60),2) if np.isfinite(r.rs60) else None,"수익률":(exit_px/entry-1)*100,"최대상승":(peak/entry-1)*100,"최대하락":(trough/entry-1)*100,"+10%":hit10,"+20%":hit20,"+30%":hit30,"보유일":exit_i-i,"청산사유":reason})
        i=exit_i+1
    return trades

def _mtf_summary(rows,label):
    if not rows:return {"전략":label,"거래":0,"승률":"-","평균수익":"-","중앙값":"-","+10%도달":"-","+20%도달":"-","+30%도달":"-","A손절":"-","최대손실":"-","평균보유일":"-"}
    q=pd.DataFrame(rows)
    reach=lambda pct:f"{(q['최대상승']>=pct).mean()*100:.1f}%"
    stop=f"{(q['청산사유']=='A 손절').mean()*100:.1f}%" if "A" in q.columns else "-"
    return {"전략":label,"거래":len(q),"승률":f"{(q['수익률']>0).mean()*100:.1f}%","평균수익":f"{q['수익률'].mean():+.2f}%","중앙값":f"{q['수익률'].median():+.2f}%","+10%도달":reach(10),"+20%도달":reach(20),"+30%도달":reach(30),"A손절":stop,"최대손실":f"{q['수익률'].min():+.2f}%","평균보유일":f"{q['보유일'].mean():.1f}일"}

def _mtf_numeric_summary(rows):
    if not rows:return {"거래":0,"승률":None,"평균수익":None,"중앙값":None,"+10%도달":None,"A손절":None,"최대손실":None}
    q=pd.DataFrame(rows)
    return {"거래":len(q),"승률":round((q["수익률"]>0).mean()*100,1),"평균수익":round(q["수익률"].mean(),2),
            "중앙값":round(q["수익률"].median(),2),"+10%도달":round((q["최대상승"]>=10).mean()*100,1),
            "A손절":round((q["청산사유"]=="A 손절").mean()*100,1),"최대손실":round(q["수익률"].min(),2)}

def _mtf_rs_audit(allrows):
    """선택한 RS 조건을 시간순 구간과 종목 쏠림으로 감사한다. 임계값은 여기서 다시 조정하지 않는다."""
    base=allrows.get("기준·60일·30주",[]); cand=allrows.get("기준+RS20≥3·RS60≥5",[])
    periods=(("개발구간·2020~2022","2020-01-01","2022-12-31"),("검증구간·2023~2024","2023-01-01","2024-12-31"),("후행구간·2025~현재","2025-01-01","2099-12-31"))
    period_rows=[]
    for label,start,end in periods:
        for strategy,rows in (("기준",base),("RS20≥3·RS60≥5",cand)):
            picked=[z for z in rows if start<=str(z.get("진입일",""))<=end]
            m=_mtf_numeric_summary(picked); m.update({"기간":label,"전략":strategy}); period_rows.append(m)
    annual=[]
    years=sorted({str(z.get("진입일",""))[:4] for z in cand if str(z.get("진입일",""))[:4].isdigit()})
    for year in years:
        picked=[z for z in cand if str(z.get("진입일",""))[:4]==year]
        m=_mtf_numeric_summary(picked); m["연도"]=year; annual.append(m)
    concentration=[]; top_share=None
    if cand:
        q=pd.DataFrame(cand); g=q.groupby("종목코드").agg(거래=("수익률","size"),합산수익=("수익률","sum"),평균수익=("수익률","mean")).reset_index()
        g=g.sort_values("합산수익",ascending=False)
        positive_total=max(0,float(g.loc[g.합산수익>0,"합산수익"].sum()))
        top_share=(max(0,float(g.iloc[0].합산수익))/positive_total*100) if positive_total>0 and not g.empty else None
        concentration=[{"종목코드":str(r.종목코드),"거래":int(r.거래),"평균수익":round(float(r.평균수익),2),"합산수익":round(float(r.합산수익),2)} for _,r in g.head(10).iterrows()]
    later=[z for z in period_rows if z["전략"]=="RS20≥3·RS60≥5" and z["기간"]!="개발구간·2020~2022"]
    base_later={z["기간"]:z for z in period_rows if z["전략"]=="기준"}
    enough=all((z["거래"]>=30) for z in later)
    improved=all(z["평균수익"] is not None and base_later[z["기간"]]["평균수익"] is not None and z["평균수익"]>base_later[z["기간"]]["평균수익"] for z in later)
    risk_ok=all(z["최대손실"] is not None and base_later[z["기간"]]["최대손실"] is not None and z["최대손실"]>=base_later[z["기간"]]["최대손실"] for z in later)
    concentration_ok=top_share is None or top_share<=20
    verdict="기간분할 통과 후보" if enough and improved and risk_ok and concentration_ok else "최종 채택 보류"
    reasons=[]
    if not enough:reasons.append("후행 구간 표본 30건 미만")
    if not improved:reasons.append("검증·후행 구간 모두에서 기준 평균수익을 넘지 못함")
    if not risk_ok:reasons.append("검증 또는 후행 구간 최대손실 악화")
    if not concentration_ok:reasons.append("최상위 종목의 양의 수익 기여 20% 초과")
    return {"periods":period_rows,"annual":annual,"concentration":concentration,"top_positive_share":round(top_share,1) if top_share is not None else None,"verdict":verdict,"reasons":reasons}

@st.cache_data(show_spinner=False,max_entries=64)
def _mtf_code_results(code,data_signature,index_signature,_daily,_benchmark):
    """확정 기준전략과 시장 대비 상대강도 단계만 같은 진입·청산 조건으로 비교한다."""
    x=_mtf_context(_daily,_benchmark)
    out={}
    out["기준·60일·30주"]=_mtf_a15_trades(_daily,x=x,trend_filter=True)
    out["기준+RS20≥0"]=_mtf_a15_trades(_daily,x=x,trend_filter=True,rs20_min=0)
    out["기준+RS60≥0"]=_mtf_a15_trades(_daily,x=x,trend_filter=True,rs60_min=0)
    out["기준+RS20·60≥0"]=_mtf_a15_trades(_daily,x=x,trend_filter=True,rs20_min=0,rs60_min=0)
    out["기준+RS20≥3·RS60≥5"]=_mtf_a15_trades(_daily,x=x,trend_filter=True,rs20_min=3,rs60_min=5)
    out["기준+RS20≥5·RS60≥10"]=_mtf_a15_trades(_daily,x=x,trend_filter=True,rs20_min=5,rs60_min=10)
    return out

def _mtf_data_signature(d):
    return {"rows":int(len(d)),"last_date":str(pd.Timestamp(d.date.max())),"last_close":round(float(d.close.iloc[-1]),4),"last_volume":round(float(d.volume.iloc[-1]),4)}

def _mtf_cached(code):
    a=_load_daily_disk(code); b=pd.DataFrame()
    try:
        p=_tm_daily_cache_path(code)
        if p.exists(): b=pd.read_csv(p,parse_dates=["date"])
    except: pass
    q=pd.concat([a,b],ignore_index=True) if not a.empty or not b.empty else pd.DataFrame()
    if q.empty:return q
    for c in ("open","high","low","close","volume"):q[c]=pd.to_numeric(q[c],errors="coerce")
    q["date"]=pd.to_datetime(q.date); return q.dropna(subset=["date","close"]).drop_duplicates("date",keep="last").sort_values("date")

def _mtf_prepare_codes(targets):
    """입력한 모든 종목을 6년 범위로 개별 수집하고 실제 저장행수를 검증한다."""
    token=kis_access_token() if kis_ready() else ""
    if not token:return {"ok":False,"error":"KIS 인증 필요","rows":[]}
    end_dt=pd.Timestamp(now_kst().date())-pd.Timedelta(days=1)
    warm_start=end_dt-pd.DateOffset(years=6)
    bar=st.progress(0,text="장기 일봉 준비 중")
    rows=[]
    for j,code in enumerate(targets,1):
        bar.progress((j-1)/max(1,len(targets)),text=f"{j}/{len(targets)} · {code} 장기자료 수집")
        last_error=""
        # 일시적인 호출 실패는 종목별 최대 3회 재시도한다.
        for attempt in range(3):
            try:
                _ad5_extend_one({"code":code,"name":code,"market":""},warm_start,end_dt,token)
                q=_mtf_cached(code)
                if len(q)>=MTF10_MIN_ROWS:break
                last_error=f"저장 {len(q)}봉"
            except Exception as e:
                last_error=str(e)[:80]
            time.sleep(0.35*(attempt+1))
        q=_mtf_cached(code)
        rows.append({"종목코드":code,"저장봉":len(q),"시작일":str(pd.Timestamp(q.date.min()).date()) if not q.empty else "-","종료일":str(pd.Timestamp(q.date.max()).date()) if not q.empty else "-","상태":"준비완료" if len(q)>=MTF10_MIN_ROWS else f"자료부족 · {last_error}"})
        time.sleep(0.18)
    bar.progress(1.0,text="종목별 저장자료 확인 완료"); bar.empty()
    result={"ok":all(x["저장봉"]>=MTF10_MIN_ROWS for x in rows),"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"rows":rows}
    _vg_write(MTF10_PREP_STATUS,result)
    return result

def _render_mtf10_lab():
    st.divider(); st.subheader("📈 시장 대비 상대강도 검증")
    st.caption("확정 기준=월·주 상승 + 일봉 10선 회복 + 60일선·30주선 상승 + A 장중 이탈 손절 + 최대 15거래일 보유")
    st.caption("RS20·RS60 = 종목의 20·60거래일 수익률 − 같은 기간 코스피/코스닥 지수 수익률(%p)")
    st.caption("MACD·거래량·상승눌림A 실패 조합은 제외하고, 진입 당일까지 확정된 상대강도만 단계별로 비교합니다.")
    scale=st.radio("검증 규모",("빠른 5종목","확장 30종목"),horizontal=True,index=1,key="mtf10_scale")
    default_codes=MTF10_EXPANDED_CODES if scale=="확장 30종목" else MTF10_QUICK_CODES
    codes=st.text_input("검증 종목코드",value=default_codes,help="쉼표로 구분 · 저장자료가 없으면 KIS 연결 후 먼저 수집합니다.",key=f"mtf10_codes_{scale}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("KIS 일봉 준비",key="mtf10_prepare"):
            if not kis_ready(): st.error("KIS APP KEY/SECRET 연결이 필요합니다.")
            else:
                targets=[z.strip().zfill(6) for z in codes.split(",") if z.strip()]
                prep=_mtf_prepare_codes(targets)
                index_prep=_mtf_prepare_indexes(kis_access_token())
                if prep.get("ok") and index_prep.get("ok"):st.success(f"{len(targets)}개 종목과 코스피·코스닥 지수 장기자료 준비 완료")
                else:st.error("일부 종목 또는 시장지수 자료가 부족합니다. 아래 상태를 확인한 뒤 KIS 일봉 준비를 다시 누르세요.")
    with c2:
        run=st.button("상대강도 6가지 비교",type="primary",key="mtf10_run")
    prep=_vg_read(MTF10_PREP_STATUS)
    if prep.get("rows"):
        st.markdown("#### 종목별 자료 준비 상태")
        st.dataframe(pd.DataFrame(prep["rows"]),use_container_width=True,hide_index=True)
    index_prep=_vg_read(MTF10_INDEX_STATUS)
    if index_prep.get("rows"):
        st.markdown("#### 시장지수 자료 준비 상태")
        st.dataframe(pd.DataFrame(index_prep["rows"]),use_container_width=True,hide_index=True)
    if run:
        targets=[z.strip().zfill(6) for z in codes.split(",") if z.strip()]
        missing=[code for code in targets if len(_mtf_cached(code))<MTF10_MIN_ROWS]
        if missing:
            st.error("비교를 중단했습니다. 자료부족 종목: "+", ".join(missing)+" · 모든 종목이 준비된 뒤 다시 실행하세요.")
            return
        benchmarks={m:_mtf_load_index(m) for m in ("KOSPI","KOSDAQ")}
        missing_index=[m for m,q in benchmarks.items() if len(q)<MTF10_MIN_ROWS]
        if missing_index:
            st.error("비교를 중단했습니다. 시장지수 자료부족: "+", ".join(missing_index)+" · KIS 일봉 준비를 먼저 누르세요.")
            return
        markets=_mtf_market_map(targets)
        unknown=[code for code in targets if not markets.get(code)]
        if unknown:
            st.error("시장구분을 확인하지 못한 종목: "+", ".join(unknown)+" · KIS 종목마스터에서 확인 가능한 종목만 입력하세요.")
            return
        daily_by_code={code:_mtf_cached(code) for code in targets}
        signatures={code:_mtf_data_signature(daily_by_code[code]) for code in targets}
        index_signatures={m:_mtf_data_signature(q.assign(volume=0)) for m,q in benchmarks.items()}
        old=_vg_read(MTF10_RESULT)
        if old.get("version")==MTF10_VERSION and old.get("codes")==targets and old.get("data_signatures")==signatures and old.get("index_signatures")==index_signatures and old.get("markets")==markets:
            st.success("일봉 자료가 바뀌지 않아 저장된 검증결과를 즉시 불러왔습니다.")
        else:
            allrows={k:[] for k in ("기준·60일·30주","기준+RS20≥0","기준+RS60≥0","기준+RS20·60≥0","기준+RS20≥3·RS60≥5","기준+RS20≥5·RS60≥10")}; used=[]
            calc_bar=st.progress(0,text="전략 검증 준비 중")
            for idx,code in enumerate(targets,1):
                calc_bar.progress((idx-1)/max(1,len(targets)),text=f"{idx}/{len(targets)} · {code} 검증 중")
                d=daily_by_code[code]; used.append(code); sig=signatures[code]; market=markets[code]; bench=benchmarks[market]
                code_rows=_mtf_code_results(code,sig,index_signatures[market],d,bench)
                for mode in allrows:
                    for trade in code_rows[mode]:
                        trade=dict(trade); trade["종목코드"]=code; trade["시장"]=market; allrows[mode].append(trade)
            calc_bar.progress(1.0,text="검증 완료"); calc_bar.empty()
            result={"version":MTF10_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"codes":used,"markets":markets,"data_signatures":signatures,"index_signatures":index_signatures,"summary":[_mtf_summary(allrows[k],k) for k in allrows],"trades":allrows,"rs_audit":_mtf_rs_audit(allrows)}
            _vg_write(MTF10_RESULT,result)
    result=_vg_read(MTF10_RESULT)
    if result.get("version")==MTF10_VERSION:
        st.info(f"검증 종목 {len(result.get('codes',[]))}개 · 최근 계산 {result.get('updated_at','')}")
        st.dataframe(pd.DataFrame(result.get("summary",[])),use_container_width=True,hide_index=True)
        selected_n=len(result.get("trades",{}).get("기준+RS20≥3·RS60≥5",[]))
        if selected_n>=100:st.success(f"선택 상대강도형 표본 {selected_n}건 · 기간분할 판단을 위한 최소 100건을 확보했습니다.")
        else:st.warning(f"선택 상대강도형 표본 {selected_n}건 · 최소 100건 전이므로 성적이 좋아도 아직 확정하지 않습니다.")
        audit=result.get("rs_audit",{})
        if audit:
            st.markdown("#### RS20≥3 · RS60≥5 기간분할·워크포워드 감사")
            st.caption("임계값을 다시 맞추지 않고 2020~2022 개발, 2023~2024 검증, 2025~현재 후행 구간으로 고정 비교합니다.")
            if audit.get("verdict")=="기간분할 통과 후보":st.success(audit["verdict"]+" · 독립 종목군 재검증 전까지 실전 하드필터로 자동 적용하지 않습니다.")
            else:st.warning(audit.get("verdict","최종 채택 보류")+" · "+(" · ".join(audit.get("reasons",[])) or "추가 확인 필요"))
            st.dataframe(pd.DataFrame(audit.get("periods",[])),use_container_width=True,hide_index=True)
            st.markdown("##### 연도별 RS 후보 성적")
            st.dataframe(pd.DataFrame(audit.get("annual",[])),use_container_width=True,hide_index=True)
            share=audit.get("top_positive_share")
            st.markdown("##### 종목별 수익 쏠림")
            st.caption(f"최상위 종목의 양의 합산수익 기여율: {share:.1f}%" if share is not None else "양의 수익 기여율 계산 불가")
            st.dataframe(pd.DataFrame(audit.get("concentration",[])),use_container_width=True,hide_index=True)
        with st.expander("거래별 결과 보기"):
            mode=st.selectbox("전략",[x["전략"] for x in result.get("summary",[])],key="mtf10_detail")
            st.dataframe(pd.DataFrame(result.get("trades",{}).get(mode,[])),use_container_width=True,hide_index=True)
        st.warning("결과는 과거 검증이며 다음 달·다음 주 상승을 보장하지 않습니다. 상장폐지 종목이 빠진 현재 종목풀은 후향편향이 있습니다.")

PRIORLOW_COMBO_RESULT=Path("data")/"priorlow_combo_compare"/"result.json"
PRIORLOW_COMBO_VERSION="PRIORLOW_OLD_VS_BREAKOUT_CONFIRM_4EXITS_WF_V1_20260928"

def _pl_combo_exit(h,ei,entry,stop,mode):
    peak=entry;peak_close=entry
    for j in range(ei+1,len(h)):
        o,hi,lo,c=map(float,(h.open.iat[j],h.high.iat[j],h.low.iat[j],h.close.iat[j]));peak=max(peak,hi);peak_close=max(peak_close,c)
        if o<stop or lo<stop:return j,(o if o<stop else stop),"손절"
        gain=peak>=entry*1.01;fib23=peak-.236*(peak-stop);fib38=peak-.382*(peak-stop)
        ma10=float(h.ma10.iat[j]);pma=float(h.ma10.iat[j-1])
        hist=h.macd_hist
        tech=bool(gain and np.isfinite(ma10) and c<=ma10 and float(h.close.iat[j-1])>pma and j>=2 and hist.iat[j]<hist.iat[j-1]<hist.iat[j-2])
        atr=float(h.atr14.iat[j]);atr_break=bool(gain and np.isfinite(atr) and c<peak_close-max(2*atr,peak_close*.04))
        fire=(gain and c<=fib23) if mode=="FIB23.6" else ((gain and c<=fib38) if mode=="FIB38.2" else (tech if mode=="10선+MACD" else (gain and (c<=fib38 or tech or atr_break))))
        if fire:return j,c,mode
    return None

def _pl_combo_trades(h,entry_mode,exit_mode):
    h=h.copy().sort_values("date").reset_index(drop=True)
    for c in ("open","high","low","close"):h[c]=pd.to_numeric(h[c],errors="coerce")
    h=h.dropna(subset=["date","open","high","low","close"]).reset_index(drop=True)
    h["ma10"]=h.close.rolling(10).mean();ema12=h.close.ewm(span=12,adjust=False).mean();ema26=h.close.ewm(span=26,adjust=False).mean();macd=ema12-ema26;h["macd_hist"]=macd-macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([(h.high-h.low),(h.high-h.close.shift(1)).abs(),(h.low-h.close.shift(1)).abs()],axis=1).max(axis=1);h["atr14"]=tr.rolling(14).mean();out=[];i=155
    while i<len(h)-2:
        aidx,a=_surviving_prior_low(h,i);ei=None;entry=stop=None
        if a is None:i+=1;continue
        if entry_mode=="기존 A부근":
            if float(h.low.iat[i])>=a and float(h.low.iat[i])<=a*1.03 and float(h.close.iat[i])>float(h.open.iat[i]):ei=i;entry=float(h.close.iat[i]);stop=float(a)
        else:
            state,_,_=_close_trend_state(h.close.iloc[:i+1].to_numpy())
            if state=="추세전환" and float(h.close.iat[i])>float(h.open.iat[i]) and float(h.low.iat[i])>=a:
                j=i+1
                if float(h.close.iat[j])>float(h.close.iat[i]) and float(h.close.iat[j])>float(h.open.iat[j]) and float(h.low.iat[j])>=float(h.low.iat[i]):ei=j;entry=float(h.close.iat[j]);stop=float(h.low.iat[i])
        if ei is None or not 5000<=entry<=50000:i+=1;continue
        ex=_pl_combo_exit(h,ei,entry,stop,exit_mode)
        if ex is None:break
        xi,xp,reason=ex;held=h.iloc[ei:xi+1]
        out.append({"진입방식":entry_mode,"매도방식":exit_mode,"진입일":str(pd.Timestamp(h.date.iat[ei]).date()),"청산일":str(pd.Timestamp(h.date.iat[xi]).date()),"순수익":(xp/entry-1)*100-.35,"최대상승":(float(held.high.max())/entry-1)*100,"최대하락":(float(held.low.min())/entry-1)*100,"보유일":xi-ei,"청산사유":reason});i=xi+1
    return out

def _pl_combo_summary(rows,label,period):
    q=pd.DataFrame(rows)
    if not q.empty:q=q[(pd.to_datetime(q["진입일"]).dt.year<=2023) if period=="개발 2020~2023" else (pd.to_datetime(q["진입일"]).dt.year>=2024)]
    if q.empty:return {"조합":label,"구간":period,"거래":0,"승률":None,"평균순수익":None,"중앙값":None,"최대손실":None,"평균보유일":None}
    return {"조합":label,"구간":period,"거래":len(q),"승률":round((q["순수익"]>0).mean()*100,1),"평균순수익":round(q["순수익"].mean(),2),"중앙값":round(q["순수익"].median(),2),"최대손실":round(q["순수익"].min(),2),"평균보유일":round(q["보유일"].mean(),1)}

def _run_priorlow_combo():
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))};modes=["기존 A부근","추세돌파+다음날확인"];exits=["FIB23.6","FIB38.2","10선+MACD","복합"] ;allrows={f"{a} · {b}":[] for a in modes for b in exits};used=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"])
            if len(h)<300:continue
            for a in modes:
                for b in exits:
                    for z in _pl_combo_trades(h,a,b):z["종목코드"]=str(code).zfill(6);allrows[f"{a} · {b}"].append(z)
            used.append(code)
        except Exception:pass
    summary=[_pl_combo_summary(v,k,p) for k,v in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x["거래"]>=30 and x["평균순수익"] is not None and x["최대손실"]>-25];winner=max(dev,key=lambda x:(x["중앙값"],x["평균순수익"],x["승률"]),default=None)
    confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None);verdict="확정 보류"
    if winner and confirm and confirm["거래"]>=30 and confirm["평균순수익"]>0 and confirm["중앙값"]>0 and confirm["최대손실"]>-25:verdict="독립 확인 통과 후보"
    result={"version":PRIORLOW_COMBO_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":verdict,"trades":allrows};_vg_write(PRIORLOW_COMBO_RESULT,result);return result

def _render_priorlow_combo():
    with st.expander("🧪 전저점 기존형 vs 추세돌파형 최적 조합 검증",expanded=False):
        st.caption("개발구간에서 조합을 선정하고 2024년 이후 확인구간으로 다시 판정합니다.")
        if st.button("전저점 8개 조합 비교 시작",key="priorlow_combo_start"):
            with st.spinner("기존·추세돌파 진입과 4개 매도법을 비교 중입니다..."):_run_priorlow_combo()
            st.rerun()
        r=_vg_read(PRIORLOW_COMBO_RESULT)
        if r.get("version")==PRIORLOW_COMBO_VERSION:
            st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}")
            st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
            if r.get("development_winner"):
                msg=f"개발구간 1위: {r['development_winner']['조합']}"
                if r.get("verdict")=="독립 확인 통과 후보":st.success(msg+" · 최근 확인구간 통과 후보")
                else:st.warning(msg+" · 최근 확인구간 실패, 실전 채택 금지")
            if r.get("confirmation"):st.write("**최근 확인구간 결과**",r["confirmation"])
            st.caption("거래 30건 미만 또는 최대손실 -25% 이하인 조합은 채택 대상에서 제외합니다. 통과 결과도 실전 자동 적용 전 전진검증이 필요합니다.")

PRIORLOW_FILTER_RESULT=Path("data")/"priorlow_filter_tournament"/"result.json"
PRIORLOW_FILTER_VERSION="PRIORLOW_BREAKOUT_CONFIRM_FILTER_TOURNAMENT_WF_V1_20260928"

def _pl_filter_pass(h,i,mode):
    if mode=="새 진입 단독":return True
    vol_ok=False
    if "volume" in h.columns and i>=20:
        base=pd.to_numeric(h.volume.iloc[i-20:i],errors="coerce").median();cur=float(pd.to_numeric(pd.Series([h.volume.iat[i]]),errors="coerce").iat[0])
        vol_ok=bool(np.isfinite(base) and base>0 and cur>=base*1.3)
    macd_ok=bool(i>=2 and h.macd_hist.iat[i]>0 and h.macd_hist.iat[i]>h.macd_hist.iat[i-1]>h.macd_hist.iat[i-2])
    mtf_ok=bool(i>=220 and np.isfinite(h.ma50.iat[i]) and np.isfinite(h.ma200.iat[i]) and h.close.iat[i]>h.ma50.iat[i]>h.ma200.iat[i] and h.ma50.iat[i]>h.ma50.iat[i-5] and h.ma200.iat[i]>h.ma200.iat[i-20])
    checks={"+거래량":vol_ok,"+MACD":macd_ok,"+월·주 추세":mtf_ok,"+추세+거래량":mtf_ok and vol_ok,"+추세+MACD":mtf_ok and macd_ok,"+추세+거래량+MACD":mtf_ok and vol_ok and macd_ok}
    return checks.get(mode,False)

def _pl_filtered_trades(h,filter_mode):
    h=h.copy().sort_values("date").reset_index(drop=True)
    for c in ("open","high","low","close","volume"):
        if c in h.columns:h[c]=pd.to_numeric(h[c],errors="coerce")
    h=h.dropna(subset=["date","open","high","low","close"]).reset_index(drop=True)
    h["ma10"]=h.close.rolling(10).mean();h["ma50"]=h.close.rolling(50).mean();h["ma200"]=h.close.rolling(200).mean()
    ema12=h.close.ewm(span=12,adjust=False).mean();ema26=h.close.ewm(span=26,adjust=False).mean();macd=ema12-ema26;h["macd_hist"]=macd-macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([(h.high-h.low),(h.high-h.close.shift(1)).abs(),(h.low-h.close.shift(1)).abs()],axis=1).max(axis=1);h["atr14"]=tr.rolling(14).mean()
    out=[];i=220
    while i<len(h)-2:
        _,a=_surviving_prior_low(h,i)
        if a is None:i+=1;continue
        state,_,_=_close_trend_state(h.close.iloc[:i+1].to_numpy())
        if state!="추세전환" or float(h.close.iat[i])<=float(h.open.iat[i]) or float(h.low.iat[i])<a:i+=1;continue
        j=i+1
        if not(float(h.close.iat[j])>float(h.close.iat[i]) and float(h.close.iat[j])>float(h.open.iat[j]) and float(h.low.iat[j])>=float(h.low.iat[i])):i+=1;continue
        entry=float(h.close.iat[j]);stop=float(h.low.iat[i])
        if not 5000<=entry<=50000 or not _pl_filter_pass(h,j,filter_mode):i+=1;continue
        ex=_pl_combo_exit(h,j,entry,stop,"복합")
        if ex is None:break
        xi,xp,reason=ex;held=h.iloc[j:xi+1]
        out.append({"필터":filter_mode,"진입일":str(pd.Timestamp(h.date.iat[j]).date()),"청산일":str(pd.Timestamp(h.date.iat[xi]).date()),"순수익":(xp/entry-1)*100-.35,"최대상승":(float(held.high.max())/entry-1)*100,"최대하락":(float(held.low.min())/entry-1)*100,"보유일":xi-j,"청산사유":reason});i=xi+1
    return out

def _run_priorlow_filter_tournament():
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))}
    modes=["새 진입 단독","+거래량","+MACD","+월·주 추세","+추세+거래량","+추세+MACD","+추세+거래량+MACD"]
    allrows={m:[] for m in modes};used=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"])
            if len(h)<300:continue
            for m in modes:
                for z in _pl_filtered_trades(h,m):z["종목코드"]=str(code).zfill(6);allrows[m].append(z)
            used.append(code)
        except Exception:pass
    summary=[_pl_combo_summary(v,k,p) for k,v in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x["거래"]>=30 and x["평균순수익"]>0 and x["중앙값"]>0 and x["최대손실"]>-15]
    winner=max(dev,key=lambda x:(x["중앙값"],x["평균순수익"],x["승률"],x["최대손실"]),default=None)
    confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None)
    passed=bool(confirm and confirm["거래"]>=30 and confirm["평균순수익"]>0 and confirm["중앙값"]>0 and confirm["최대손실"]>-15)
    result={"version":PRIORLOW_FILTER_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":"독립 확인 통과 후보" if passed else "확정 보류","trades":allrows};_vg_write(PRIORLOW_FILTER_RESULT,result);return result

def _render_priorlow_filter_tournament():
    with st.expander("🔬 다음 검증 · 추세·거래량·MACD 필터 조합",expanded=False):
        st.caption("새 진입법의 매도법은 고정하고, 진입 필터 7단계를 개발구간과 최근 확인구간으로 나눠 검증합니다.")
        if st.button("전저점 필터 7단계 검증 시작",key="priorlow_filter_start"):
            with st.spinner("월·주 추세, 거래량, MACD 조합을 검증 중입니다..."):_run_priorlow_filter_tournament()
            st.rerun()
        r=_vg_read(PRIORLOW_FILTER_RESULT)
        if r.get("version")!=PRIORLOW_FILTER_VERSION:return
        st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}")
        st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
        w=r.get("development_winner")
        if not w:st.error("개발구간부터 기준을 만족한 조합이 없습니다. 전저점 새 진입법은 채택하지 않습니다.")
        elif r.get("verdict")=="독립 확인 통과 후보":st.success(f"{w['조합']} · 최근 확인구간까지 통과한 후보입니다.")
        else:st.warning(f"개발구간 1위 {w['조합']} · 최근 확인구간 실패로 채택하지 않습니다.")
        if r.get("confirmation"):st.write("**최근 확인구간 결과**",r["confirmation"])
        st.caption("최소 30거래, 평균·중앙 수익 양수, 최대손실 -15% 초과를 개발/확인구간에서 모두 요구합니다.")

MA10_BODY_COMPARE_RESULT=Path("data")/"ma10_body_compare"/"result.json"
MA10_BODY_COMPARE_VERSION="MA10_CLOSE_CROSS_VS_BODY_TOUCH_MTF_DYNAMIC_EXIT_V1_20260928"

MA10_CURVE_RESULT=Path("data")/"ma10_curve_turn"/"result.json"
MA10_CURVE_VERSION="MA10_CURVE_BODY_TURN_NO_SIDEWAYS_WF_V1_20260930"

def _ma10_curve_trades(h,label,curve_pct,away_pct,max_crosses,entry_kind):
    """Independent MA10 strategy: enough amplitude, no line-hugging, body touch and close confirmation."""
    z=h[["date","open","high","low","close"]].copy().sort_values("date").drop_duplicates("date")
    for c in ("open","high","low","close"):z[c]=pd.to_numeric(z[c],errors="coerce")
    z=z.dropna().reset_index(drop=True);z["date"]=pd.to_datetime(z.date)
    z["ma10"]=z.close.rolling(10).mean();z["curve20"]=(z.high.rolling(20).max()/z.low.rolling(20).min()-1)*100
    z["dist"]=(z.close/z.ma10-1)*100;z["max_above20"]=z.dist.shift(1).rolling(20).max();z["max_below20"]=(-z.dist.shift(1)).rolling(20).max()
    side=np.sign(z.close-z.ma10);z["cross10"]=(side.ne(side.shift(1))&side.ne(0)&side.shift(1).ne(0)).rolling(10).sum()
    z["slope3"]=(z.ma10/z.ma10.shift(3)-1)*100
    body_lo=z[["open","close"]].min(axis=1);body_hi=z[["open","close"]].max(axis=1)
    body_touch=(body_lo<=z.ma10)&(body_hi>=z.ma10);bull=(z.close>z.open)&(z.close>=z.ma10)
    from_below=(z.close.shift(1)<z.ma10.shift(1))&(z.max_below20>=away_pct)
    pullback=(z.close.shift(1)>=z.ma10.shift(1))&(z.max_above20>=away_pct)
    origin=from_below if entry_kind=="추세전환" else pullback
    z["entry_signal"]=(z.close.between(5000,50000)&(z.curve20>=curve_pct)&(z.cross10<=max_crosses)&(z.slope3>0)&body_touch&bull&origin)
    sell_lo=z[["open","close"]].min(axis=1);sell_hi=z[["open","close"]].max(axis=1)
    z["exit_signal"]=(sell_lo<=z.ma10)&(sell_hi>=z.ma10)&(z.close<=z.ma10)&(z.close<z.open)
    rows=[];pos=None
    for i,r in z.iterrows():
        if pos is None:
            if bool(r.entry_signal):pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low))
        if bool(r.exit_signal):
            ret=(float(r.close)/pos["entry"]-1)*100-.35
            rows.append({"조합":label,"진입유형":entry_kind,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"순수익":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"]});pos=None
    return rows

def _ma10_curve_period_summary(rows,label,period):
    q=pd.DataFrame(rows)
    if not q.empty:
        years=pd.to_datetime(q["진입일"]).dt.year;q=q[years<=2023] if period.startswith("개발") else q[years>=2024]
    if q.empty:return {"조합":label,"구간":period,"거래":0,"승률":None,"평균순수익":None,"중앙순수익":None,"상위1제외":None,"상위3제외":None,"손익비":None,"10%도달":None,"최대손실":None,"평균보유일":None}
    ordered=q.순수익.sort_values(ascending=False);wins=q.loc[q.순수익>0,"순수익"];losses=q.loc[q.순수익<=0,"순수익"]
    trim1=ordered.iloc[1:].mean() if len(ordered)>1 else None;trim3=ordered.iloc[3:].mean() if len(ordered)>3 else None
    payoff=(wins.mean()/abs(losses.mean())) if len(wins) and len(losses) and losses.mean()!=0 else None
    return {"조합":label,"구간":period,"거래":len(q),"승률":round((q.순수익>0).mean()*100,1),"평균순수익":round(q.순수익.mean(),2),"중앙순수익":round(q.순수익.median(),2),"상위1제외":round(trim1,2) if pd.notna(trim1) else None,"상위3제외":round(trim3,2) if pd.notna(trim3) else None,"손익비":round(payoff,2) if pd.notna(payoff) else None,"10%도달":round((q.최대상승>=10).mean()*100,1),"최대손실":round(q.순수익.min(),2),"평균보유일":round(q.보유일.mean(),1)}

def _run_ma10_curve_lab():
    variants=[("완화형",10,5,2),("균형형",15,8,2),("엄격형",20,10,1)]
    allrows={f"{name}·{kind}":[] for name,_,_,_ in variants for kind in ("추세전환","눌림목")}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[]
    progress=st.progress(0,text=f"굴곡형 자료 준비 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<180:continue
            for name,curve,away,crosses in variants:
                for kind in ("추세전환","눌림목"):
                    key=f"{name}·{kind}"
                    for row in _ma10_curve_trades(h,key,curve,away,crosses,kind):row["종목코드"]=str(code).zfill(6);allrows[key].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"굴곡형 자료 준비 {n}/{len(codes)}")
    progress.empty();summary=[_ma10_curve_period_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x["거래"]>=30 and x["평균순수익"] is not None and x["평균순수익"]>0 and x["중앙순수익"]>0 and x["최대손실"]>-15]
    winner=max(dev,key=lambda x:(x["평균순수익"],x["승률"])) if dev else None
    confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None)
    passed=bool(confirm and confirm["거래"]>=30 and confirm["평균순수익"]>0 and confirm["중앙순수익"]>0 and confirm["최대손실"]>-15)
    result={"version":MA10_CURVE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":"독립 확인 통과 후보" if passed else "확정 보류","trades":allrows,"definition":"전저점과 분리한 굴곡형 10이평 전략. 최근 20봉 고저폭과 과거 10이평 최대 이격을 동시에 요구하고, 최근 10봉 교차가 많으면 횡보로 제외합니다. 상승하는 10이평에 양봉 몸통이 닿고 종가가 선 위에서 확정될 때 진입하며, 반대 음봉 몸통 접촉·종가 하향 확정 때 청산합니다. 15일 강제청산 없이 비용 0.35%를 차감합니다."}
    _vg_write(MA10_CURVE_RESULT,result);return result

def _render_ma10_curve_lab():
    st.subheader("〽️ 굴곡형 10이평 추세전환 · 독립 검증")
    st.caption("단순 교차가 아니라 충분히 벌어졌다 돌아오는 큰 굴곡만 봅니다. 횡보 중 10이평을 물고 가는 구간은 교차 횟수로 제외합니다.")
    if st.button("굴곡형 10이평 6조합 검증 시작",key="ma10_curve_start"):
        with st.spinner("굴곡 크기와 진입 형태를 개발·확인구간으로 나눠 검증 중입니다..."):_run_ma10_curve_lab()
        st.rerun()
    r=_vg_read(MA10_CURVE_RESULT)
    if r.get("version")!=MA10_CURVE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}")
    st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    if r.get("development_winner"):st.write("**개발구간 1위**",r["development_winner"])
    if r.get("confirmation"):st.write("**최근 독립 확인**",r["confirmation"])
    st.caption(r.get("definition",""))

# 전저점이라는 검증된 구조를 중심에 두고, 성격이 다른 추세 확인 두 개만
# 사전에 고정해 조합한다. 확인구간 결과를 본 뒤 조건을 더 붙이지 않는다.
RETAINED_COMBO_RESULT=Path("data")/"retained_combo_one_shot"/"result.json"
RETAINED_COMBO_VERSION="PRIORLOW_ABC_OVERHEAD_VOLUME_ZONE_V6_20261001"

def _overhead_volume_zone(h,end_i,trigger,atr):
    """신호일까지의 자료만으로, 바로 위에 있는 평균 이상 거래량 가격대를 찾는다."""
    try:
        q=h.iloc[:end_i+1];price=((q.high+q.low+q.close)/3).to_numpy(float)
        volume=pd.to_numeric(q.get("volume",pd.Series(1,index=q.index)),errors="coerce").fillna(0).to_numpy(float)
        if len(price)<60 or not np.isfinite(volume).any() or volume.sum()<=0:return None
        edges=np.histogram_bin_edges(price,bins="fd")
        if len(edges)<6:edges=np.linspace(float(np.nanmin(price)),float(np.nanmax(price)),11)
        if len(edges)>61:edges=np.linspace(float(np.nanmin(price)),float(np.nanmax(price)),61)
        weights,_=np.histogram(price,bins=edges,weights=volume);mean=float(np.mean(weights))
        zones=[]
        for n,v in enumerate(weights):
            lo,hi=float(edges[n]),float(edges[n+1])
            if hi>trigger and v>=mean:zones.append((max(lo,trigger),hi,float(v)))
        if not zones:return None
        lo,hi,v=min(zones,key=lambda x:x[0])
        return {"하단":lo,"상단":hi,"강도":v/mean} if lo-trigger<=2*atr else None
    except Exception:return None

def _volume_zone_entry(h,start_i,stop,trigger,zone):
    """매물대가 가까우면 상단 종가돌파 뒤 다음 날 재지지를 기다린다."""
    if zone is None:return None
    upper=float(zone["상단"])
    for k in range(start_i,len(h)-1):
        if float(h.low.iat[k])<stop:return None
        if float(h.close.iat[k])<=upper:continue
        r=k+1
        if float(h.low.iat[r])<stop:return None
        if float(h.low.iat[r])<=upper and float(h.close.iat[r])>=upper:
            op=float(h.open.iat[r]);entry=op if op>=upper else upper
            if entry>upper*1.03:return None
            return r,entry
    return None

def _retained_exit(h,ei,entry,stop,use_volume_zone=False):
    """기존 추세청산에 두꺼운 매물대의 반복 거절을 추가한다."""
    zone=None;rejects=0
    if use_volume_zone:
        atr=float(h.atr14.iat[ei]) if pd.notna(h.atr14.iat[ei]) else 0
        zone=_overhead_volume_zone(h,ei,entry,atr) if atr>0 else None
    peak=entry;peak_close=entry
    for j in range(ei+1,len(h)):
        o,hi,lo,c=map(float,(h.open.iat[j],h.high.iat[j],h.low.iat[j],h.close.iat[j]));peak=max(peak,hi);peak_close=max(peak_close,c)
        if o<stop or lo<stop:return j,(o if o<stop else stop),"C저점 손절"
        if zone and hi>=float(zone["하단"]):
            upper_wick=hi-max(o,c);body=abs(c-o)
            if c<float(zone["하단"]) and upper_wick>body:rejects+=1
            elif c>float(zone["상단"]):rejects=0
            if rejects>=2:return j,c,"매물대 2회 거절"
        gain=peak>=entry*1.01;fib23=peak-.236*(peak-stop);fib38=peak-.382*(peak-stop)
        ma10=float(h.ma10.iat[j]);pma=float(h.ma10.iat[j-1]);hist=h.macd_hist
        tech=bool(gain and np.isfinite(ma10) and c<=ma10 and float(h.close.iat[j-1])>pma and j>=2 and hist.iat[j]<hist.iat[j-1]<hist.iat[j-2])
        atr=float(h.atr14.iat[j]);atr_break=bool(gain and np.isfinite(atr) and c<peak_close-max(2*atr,peak_close*.04))
        if gain and (c<=fib38 or tech or atr_break):return j,c,"복합 추세매도"
    return None

def _retained_combo_all_trades(h):
    """한 번의 차트 순회로 네 조합의 공통 진입후보를 만든다."""
    labels=("전저점 터치매수","전저점+20일선 상승","전저점+매물대 대응","전저점+20일선+매물대 대응")
    h=h.copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for c in ("open","high","low","close","volume"):
        if c in h.columns:h[c]=pd.to_numeric(h[c],errors="coerce")
    h=h.dropna(subset=["date","open","high","low","close"]).reset_index(drop=True);h["date"]=pd.to_datetime(h.date)
    h["ma10"]=h.close.rolling(10).mean();h["ma20"]=h.close.rolling(20).mean();h["ma20_up"]=h.ma20>h.ma20.shift(5)
    ema12=h.close.ewm(span=12,adjust=False).mean();ema26=h.close.ewm(span=26,adjust=False).mean();macd=ema12-ema26;h["macd_hist"]=macd-macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([(h.high-h.low),(h.high-h.close.shift(1)).abs(),(h.low-h.close.shift(1)).abs()],axis=1).max(axis=1);h["atr14"]=tr.rolling(14).mean()
    w=h.set_index("date").resample("W-FRI",label="right",closed="right").agg(close=("close","last")).dropna().reset_index();w["wma10"]=w.close.rolling(10).mean();w["up"]=w.wma10>w.wma10.shift(1);w["first_up"]=w.up&~w.up.shift(1,fill_value=False)
    h=pd.merge_asof(h.sort_values("date"),w[["date","first_up"]],on="date",direction="backward");h["first_up"]=h.first_up.fillna(False).astype(bool)
    candidates=[];lows=h.low.to_numpy(float);highs=h.high.to_numpy(float)
    for i in range(220,len(h)-2):
        # C는 재조정의 실제 저점이면서 양봉이어야 한다. 단순한 매일의 작은 저점은 제외한다.
        if float(h.close.iat[i])<=float(h.open.iat[i]) or lows[i]>np.min(lows[i-3:i+1]):continue
        atr_c=float(h.atr14.iat[i])
        if not np.isfinite(atr_c) or atr_c<=0:continue
        chosen=None
        # A는 C보다 앞선 120거래일 안의 국소 저점이다. 가장 최근 A부터 검사하되
        # A→B 반등과 B→C 재조정이 실제 순서로 완성된 경우만 사용한다.
        anchors=[]
        for aidx in range(max(3,i-120),i-7):
            if lows[aidx]<=np.min(lows[aidx-3:aidx]) and lows[aidx]<=np.min(lows[aidx+1:aidx+4]):anchors.append(aidx)
        for aidx in reversed(anchors):
            a=float(lows[aidx])
            if np.min(lows[aidx+1:i+1])<a:continue
            mid_start=aidx+3;mid_end=i-2
            if mid_end<=mid_start:continue
            bidx=mid_start+int(np.argmax(highs[mid_start:mid_end+1]));b=float(highs[bidx])
            atr_ref=float(pd.to_numeric(h.atr14.iloc[aidx:bidx+1],errors="coerce").median())
            if not np.isfinite(atr_ref) or b-a<2*atr_ref:continue
            # C는 반등고점 B 뒤에 형성되고, A에서 한 ATR 이내로 돌아오되 A는 깨지 않는다.
            if bidx>=i-1 or lows[i]>a+atr_c or lows[i]>np.min(lows[bidx+1:i+1]) or b-lows[i]<atr_c:continue
            chosen=(aidx,a,bidx,b);break
        if chosen is None:continue
        # C 종가가 C고가(돌파 매수가)에 1ATR 안으로 가까울 때만 관심 등록한다.
        # 다음 날 실제로 C고가를 터치하면 C고가에 체결, 갭 상승은 +3%까지만 시가 체결한다.
        trigger=float(h.high.iat[i]);watch_close=float(h.close.iat[i]);stop=float(h.low.iat[i])
        if watch_close>trigger or trigger-watch_close>atr_c:continue
        j=i+1;op=float(h.open.iat[j]);hi=float(h.high.iat[j]);lo=float(h.low.iat[j]);entry=None
        if lo>=stop:
            if trigger<=op<=trigger*1.03:entry=op
            elif op<trigger and hi>=trigger:entry=trigger
        if entry is not None and not 5000<=entry<=50000:entry=None
        zone=_overhead_volume_zone(h,i,trigger,atr_c)
        vp=_volume_zone_entry(h,j,stop,trigger,zone) if zone else ((j,entry) if entry is not None else None)
        if entry is None and vp is None:continue
        candidates.append((j,entry,stop,chosen[0],chosen[1],chosen[2],chosen[3],i,trigger,watch_close,zone,vp))
    out={k:[] for k in labels}
    for label in labels:
        last_exit=-1;need20=label in (labels[1],labels[3]);need_vp=label in (labels[2],labels[3])
        for base_j,base_entry,stop,aidx,a,bidx,b,cidx,trigger,watch_close,zone,vp in candidates:
            if need_vp:
                if vp is None:continue
                j,entry=vp
            else:
                if base_entry is None:continue
                j,entry=base_j,base_entry
            if j<=last_exit or (need20 and not bool(h.ma20_up.iat[j])):continue
            ex=_retained_exit(h,j,entry,stop,use_volume_zone=need_vp)
            if ex is None:break
            xi,xp,reason=ex;held=h.iloc[j:xi+1]
            out[label].append({"조합":label,"A저점일":str(pd.Timestamp(h.date.iat[aidx]).date()),"A":round(a,2),"B고점일":str(pd.Timestamp(h.date.iat[bidx]).date()),"B":round(b,2),"관심등록일":str(pd.Timestamp(h.date.iat[cidx]).date()),"C저점":round(stop,2),"관심종가":round(watch_close,2),"터치매수가":round(trigger,2),"매물대상단":round(float(zone["상단"]),2) if zone else None,"매물대강도":round(float(zone["강도"]),2) if zone else None,"실제진입가":round(entry,2),"진입일":str(pd.Timestamp(h.date.iat[j]).date()),"청산일":str(pd.Timestamp(h.date.iat[xi]).date()),"순수익":float((xp/entry-1)*100-.35),"최대상승":float((held.high.max()/entry-1)*100),"최대하락":float((held.low.min()/entry-1)*100),"보유일":int(xi-j),"청산사유":reason});last_exit=xi
    return out

def _retained_combo_trades(h,label):
    h=h.copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for c in ("open","high","low","close","volume"):
        if c in h.columns:h[c]=pd.to_numeric(h[c],errors="coerce")
    h=h.dropna(subset=["date","open","high","low","close"]).reset_index(drop=True)
    h["date"]=pd.to_datetime(h.date);h["ma10"]=h.close.rolling(10).mean();h["ma20"]=h.close.rolling(20).mean()
    h["ma20_up"]=h.ma20>h.ma20.shift(5)
    ema12=h.close.ewm(span=12,adjust=False).mean();ema26=h.close.ewm(span=26,adjust=False).mean();macd=ema12-ema26
    h["macd_hist"]=macd-macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([(h.high-h.low),(h.high-h.close.shift(1)).abs(),(h.low-h.close.shift(1)).abs()],axis=1).max(axis=1);h["atr14"]=tr.rolling(14).mean()
    w=h.set_index("date").resample("W-FRI",label="right",closed="right").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).dropna().reset_index()
    w["wma10"]=w.close.rolling(10).mean();w["wma_up"]=w.wma10>w.wma10.shift(1);w["first_up"]=w.wma_up&~w.wma_up.shift(1,fill_value=False)
    h=pd.merge_asof(h.sort_values("date"),w[["date","first_up"]].sort_values("date"),on="date",direction="backward")
    h["first_up"]=h.first_up.fillna(False).astype(bool)
    need20=label in ("전저점+20일선 상승","전저점+20일선+주봉전환")
    needw=label in ("전저점+주봉 첫전환","전저점+20일선+주봉전환")
    out=[];i=220
    while i<len(h)-2:
        _,a=_surviving_prior_low(h,i)
        if a is None:i+=1;continue
        state,_,_=_close_trend_state(h.close.iloc[:i+1].to_numpy())
        if state!="추세전환" or float(h.close.iat[i])<=float(h.open.iat[i]) or float(h.low.iat[i])<a:i+=1;continue
        j=i+1
        confirmed=float(h.close.iat[j])>float(h.close.iat[i]) and float(h.close.iat[j])>float(h.open.iat[j]) and float(h.low.iat[j])>=float(h.low.iat[i])
        if not confirmed:i+=1;continue
        if need20 and not bool(h.ma20_up.iat[j]):i+=1;continue
        if needw and not bool(h.first_up.iat[j]):i+=1;continue
        entry=float(h.close.iat[j]);stop=float(h.low.iat[i])
        if not 5000<=entry<=50000:i+=1;continue
        ex=_pl_combo_exit(h,j,entry,stop,"복합")
        if ex is None:break
        xi,xp,reason=ex;held=h.iloc[j:xi+1]
        out.append({"조합":label,"진입일":str(pd.Timestamp(h.date.iat[j]).date()),"청산일":str(pd.Timestamp(h.date.iat[xi]).date()),"순수익":float((xp/entry-1)*100-.35),"최대상승":float((held.high.max()/entry-1)*100),"최대하락":float((held.low.min()/entry-1)*100),"보유일":int(xi-j),"청산사유":reason})
        i=xi+1
    return out

def _retained_combo_summary(rows,label,period):
    q=pd.DataFrame(rows)
    if not q.empty:
        years=pd.to_datetime(q["진입일"]).dt.year;q=q[years<=2023] if period.startswith("개발") else q[years>=2024]
    if q.empty:return {"조합":label,"구간":period,"거래":0,"승률":None,"평균순수익":None,"중앙값":None,"손익비":None,"수익/최대손실":None,"평균수익보존":None,"최대손실":None,"평균보유일":None}
    wins=q[q.순수익>0];losses=q[q.순수익<=0]
    profit_factor=float(wins.순수익.sum()/abs(losses.순수익.sum())) if len(losses) and losses.순수익.sum()!=0 else None
    worst=abs(float(q.순수익.min()));risk_return=float(q.순수익.mean()/worst) if worst>0 else None
    # 실제 청산수익이 보유 중 최대상승분 가운데 얼마나 남았는지 본다.
    capturable=q[(q.최대상승>0)&(q.순수익>0)].copy()
    capture=float((capturable.순수익/capturable.최대상승).clip(upper=1).mean()*100) if len(capturable) else None
    return {"조합":label,"구간":period,"거래":int(len(q)),"승률":round(float((q.순수익>0).mean()*100),1),"평균순수익":round(float(q.순수익.mean()),2),"중앙값":round(float(q.순수익.median()),2),"손익비":round(profit_factor,2) if profit_factor is not None else None,"수익/최대손실":round(risk_return,3) if risk_return is not None else None,"평균수익보존":round(capture,1) if capture is not None else None,"최대손실":round(float(q.순수익.min()),2),"평균보유일":round(float(q.보유일.mean()),1)}

def _run_retained_combo_lab():
    labels=("전저점 터치매수","전저점+20일선 상승","전저점+매물대 대응","전저점+20일선+매물대 대응")
    allrows={k:[] for k in labels};codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[]
    progress=st.progress(0,text=f"남길 조합 검증 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<300:continue
            stock_rows=_retained_combo_all_trades(h)
            for label in labels:
                for row in stock_rows[label]:row["종목코드"]=str(code).zfill(6);allrows[label].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"남길 조합 검증 {n}/{len(codes)}")
    progress.empty();summary=[_retained_combo_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x.get("거래",0)>=30 and (x.get("평균순수익") or -999)>0]
    # 승률보다 손익비와 평균수익/최악손실을 우선한다. 승률은 동률 보조 기준이다.
    winner=max(dev,key=lambda x:(x.get("손익비") or -999,x.get("수익/최대손실") or -999,x.get("평균순수익") or -999,x.get("승률") or -999))["조합"] if dev else None
    confirm=next((x for x in summary if x["구간"].startswith("확인") and x["조합"]==winner),None);base=next((x for x in summary if x["구간"].startswith("확인") and x["조합"]==labels[0]),None)
    adopted=bool(winner and winner!=labels[0] and confirm and base and confirm["평균순수익"]>0 and (confirm.get("손익비") or 0)>1 and (confirm.get("손익비") or 0)>(base.get("손익비") or 0) and (confirm.get("수익/최대손실") or -999)>(base.get("수익/최대손실") or -999) and confirm["최대손실"]>=base["최대손실"])
    result={"version":RETAINED_COMBO_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"baseline_confirmation":base,"verdict":f"채택 후보: {winner}" if adopted else "채택 없음 · 조건 추가 중단","trades":allrows,"rules":["A: 최근 120거래일 안의 국소 전저점","B: A 이후 종목 고유 변동성(ATR)보다 충분히 큰 실제 반등고점","C: B 이후 A를 장중에도 깨지 않고 A에서 1ATR 안으로 재조정된 양봉 저점","관심등록: C 종가가 C봉 고가에서 1ATR 이내로 가까울 때","기본매수: 가까운 두꺼운 매물대가 없으면 다음 거래일 C봉 고가 터치가격에 체결","매물대매수: 가까운 두꺼운 매물대가 있으면 첫 터치는 관망하고, 매물대 상단 종가돌파 후 다음 날 상단 재지지 때 체결","추격금지: 체결가격이 기준가보다 3%를 넘으면 매수 취소","후보취소·손절: 대기 중 또는 매수 후 C봉 저점 이탈","매물대매도: 두꺼운 매물대에서 긴 윗꼬리 거절이 2회 발생하면 매도","기본익절: 피보나치 되돌림·10일선+MACD 약화·ATR 추적 중 먼저 발생한 신호","매물대는 각 과거 시점까지 누적된 거래량만 사용해 미래정보를 보지 않음","비교 조합은 전저점 단독·20일선 상승·매물대 대응·20일선+매물대 대응","개발구간 거래 30건 미만 조합은 1위 선정 제외","2020~2023에서 손익비→수익/최대손실→평균수익 순으로 하나만 선택","2024~현재에서 손익비 1 초과·기준보다 손익비와 위험대비수익 개선·최대손실 비악화일 때만 채택"]}
    _vg_write(RETAINED_COMBO_RESULT,result);return result

def _render_retained_combo_lab():
    st.subheader("🧩 남길 조건 조합 · 진입·청산·손실·수익 검증")
    st.caption("가까운 두꺼운 매물대가 없으면 C고가 터치매수, 있으면 상단 종가돌파 후 재지지 매수합니다. 매물대 반복거절은 매도에 반영합니다.")
    if st.button("남길 4개 조합 검증",key="retained_combo_one_shot"):
        with st.spinner("사전 고정한 네 조합을 개발·최근 구간으로 분리 검증 중입니다..."):_run_retained_combo_lab()
        st.rerun()
    r=_vg_read(RETAINED_COMBO_RESULT)
    if r.get("version")!=RETAINED_COMBO_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    if r.get("development_winner"):st.write("**개발구간 손익비 1위**",r.get("development_winner"))
    if r.get("confirmation"):st.write("**최근 독립 확인**",r.get("confirmation"))
    with st.expander("조합·합격 규칙 공개",expanded=False):st.write(r.get("rules",[]))

EXIT_ONLY_RESULT=Path("data")/"fixed_entry_exit_one_shot"/"result.json"
EXIT_ONLY_VERSION="ABC_MA20_TOUCH_FIXED_ENTRY_3EXITS_V1_20261001"

def _fixed_entry_exit(h,entry_i,entry,stop,mode):
    peak=float(entry);trough=float(entry);peak_close=float(entry)
    for j in range(entry_i+1,len(h)):
        o,hi,lo,c=map(float,(h.open.iat[j],h.high.iat[j],h.low.iat[j],h.close.iat[j]));peak=max(peak,hi);trough=min(trough,lo);peak_close=max(peak_close,c)
        if o<stop or lo<stop:return j,(o if o<stop else stop),"C저점 손절",peak,trough
        atr=float(h.atr14.iat[j]) if pd.notna(h.atr14.iat[j]) else np.nan
        if mode=="현재 복합매도":
            gain=peak>entry;fib38=peak-.382*(peak-stop);hist=h.macd_hist
            tech=bool(j>=2 and c<=float(h.ma10.iat[j]) and float(h.close.iat[j-1])>float(h.ma10.iat[j-1]) and hist.iat[j]<hist.iat[j-1]<hist.iat[j-2])
            trail=bool(np.isfinite(atr) and c<peak_close-max(2*atr,peak_close*.04))
            if gain and (c<=fib38 or tech or trail):return j,c,"현재 복합매도",peak,trough
        elif mode=="ATR 고점추적":
            if np.isfinite(atr) and c<peak_close-2*atr:return j,c,"ATR 고점추적",peak,trough
        else:
            hist=h.macd_hist;ma20=float(h.ma20.iat[j]) if pd.notna(h.ma20.iat[j]) else np.nan
            weakening=bool(j>=2 and hist.iat[j]<hist.iat[j-1]<hist.iat[j-2])
            if np.isfinite(ma20) and c<ma20 and weakening:return j,c,"20일선+MACD",peak,trough
    return None

def _run_exit_only_lab():
    modes=("현재 복합매도","ATR 고점추적","20일선+MACD 추세매도");allrows={m:[] for m in modes}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"고정매수·매도비교 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code);prepared=h.copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
            for c in ("open","high","low","close","volume"):
                if c in prepared.columns:prepared[c]=pd.to_numeric(prepared[c],errors="coerce")
            prepared=prepared.dropna(subset=["date","open","high","low","close"]).reset_index(drop=True);prepared["date"]=pd.to_datetime(prepared.date)
            prepared["ma10"]=prepared.close.rolling(10).mean();prepared["ma20"]=prepared.close.rolling(20).mean();ema12=prepared.close.ewm(span=12,adjust=False).mean();ema26=prepared.close.ewm(span=26,adjust=False).mean();macd=ema12-ema26;prepared["macd_hist"]=macd-macd.ewm(span=9,adjust=False).mean();tr=pd.concat([(prepared.high-prepared.low),(prepared.high-prepared.close.shift(1)).abs(),(prepared.low-prepared.close.shift(1)).abs()],axis=1).max(axis=1);prepared["atr14"]=tr.rolling(14).mean()
            base=_retained_combo_all_trades(h).get("전저점+20일선 상승",[])
            for signal in base:
                hits=prepared.index[prepared.date.eq(pd.Timestamp(signal["진입일"]))]
                if not len(hits):continue
                ei=int(hits[0]);entry=float(signal["실제진입가"]);stop=float(signal["C저점"])
                for mode in modes:
                    ex=_fixed_entry_exit(prepared,ei,entry,stop,mode)
                    if ex is None:continue
                    xi,xp,reason,peak,trough=ex
                    allrows[mode].append({"조합":mode,"종목코드":str(code).zfill(6),"진입일":signal["진입일"],"청산일":str(pd.Timestamp(prepared.date.iat[xi]).date()),"진입가":entry,"C저점":stop,"순수익":float((xp/entry-1)*100-.35),"최대상승":float((peak/entry-1)*100),"최대하락":float((trough/entry-1)*100),"보유일":int(xi-ei),"청산사유":reason})
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"고정매수·매도비교 {n}/{len(codes)}")
    progress.empty();summary=[_retained_combo_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x.get("거래",0)>=30 and (x.get("평균순수익") or -999)>0]
    winner=max(dev,key=lambda x:(x.get("손익비") or -999,x.get("평균수익보존") or -999,x.get("수익/최대손실") or -999))["조합"] if dev else None
    confirm=next((x for x in summary if winner and x["조합"]==winner and x["구간"].startswith("확인")),None);base=next((x for x in summary if x["조합"]==modes[0] and x["구간"].startswith("확인")),None)
    passed=bool(winner and confirm and base and confirm["평균순수익"]>0 and (confirm.get("손익비") or 0)>1 and (confirm.get("손익비") or 0)>=(base.get("손익비") or 0) and (confirm.get("평균수익보존") or 0)>(base.get("평균수익보존") or 0) and confirm["최대손실"]>=base["최대손실"])
    result={"version":EXIT_ONLY_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"baseline_confirmation":base,"verdict":f"채택 후보: {winner}" if passed else "채택 없음 · 매도 튜닝 종료","trades":allrows,"rules":["매수종목·매수일·매수가·C저점은 세 매도법 모두 동일","매수는 ABC 전저점+20일선 상승+다음 날 C고가 터치","C저점 이탈 손절은 세 매도법 공통","2020~2023 손익비 1위 한 개만 선택","2024~현재에서 손익비·수익보존율 개선과 최대손실 비악화를 한 번 확인","실패하면 새로운 매도조건을 추가하지 않음"]};_vg_write(EXIT_ONLY_RESULT,result);return result

def _render_exit_only_lab():
    st.subheader("✂️ 고정 매수 · 매도법 3가지 최종 비교")
    st.caption("같은 종목·같은 매수일로 매도법만 비교합니다. 이번 한 번으로 매도 튜닝을 종료합니다.")
    if st.button("고정매수 매도법 3가지 비교",key="fixed_entry_exit_test"):
        with st.spinner("같은 매수 건에 세 가지 매도법을 적용 중입니다..."):_run_exit_only_lab()
        st.rerun()
    r=_vg_read(EXIT_ONLY_RESULT)
    if r.get("version")!=EXIT_ONLY_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    if r.get("development_winner"):st.write("**개발구간 손익비 1위**",r.get("development_winner"))
    if r.get("confirmation"):st.write("**최근 독립 확인**",r.get("confirmation"))
    with st.expander("고정 규칙 공개",expanded=False):st.write(r.get("rules",[]))

LOSS_GUARD_RESULT=Path("data")/"loss_guard_one_by_one"/"result.json"
LOSS_GUARD_VERSION="ABC_FIXED_ENTRY_LOSS_GUARD_ATR2_V1_20261001"

def _loss_guard_summary(rows,label,period):
    base=_retained_combo_summary(rows,label,period);q=pd.DataFrame(rows)
    if not q.empty:
        years=pd.to_datetime(q["진입일"]).dt.year;q=q[years.le(2023) if period.startswith("개발") else years.ge(2024)]
    base["-5%이하"]=int((q["순수익"]<=-5).sum()) if not q.empty else 0;base["-10%이하"]=int((q["순수익"]<=-10).sum()) if not q.empty else 0;base["손절거래"]=int(q["청산사유"].astype(str).str.contains("손절").sum()) if not q.empty else 0
    return base

def _run_loss_guard_lab():
    modes=("기존 C저점 손절","C저점·ATR2 중 가까운 손절");allrows={m:[] for m in modes};codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"손실 1단계 검증 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code);prepared=h.copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
            for c in ("open","high","low","close","volume"):
                if c in prepared.columns:prepared[c]=pd.to_numeric(prepared[c],errors="coerce")
            prepared=prepared.dropna(subset=["date","open","high","low","close"]).reset_index(drop=True);prepared["date"]=pd.to_datetime(prepared.date);prepared["ma10"]=prepared.close.rolling(10).mean();prepared["ma20"]=prepared.close.rolling(20).mean();ema12=prepared.close.ewm(span=12,adjust=False).mean();ema26=prepared.close.ewm(span=26,adjust=False).mean();macd=ema12-ema26;prepared["macd_hist"]=macd-macd.ewm(span=9,adjust=False).mean();tr=pd.concat([(prepared.high-prepared.low),(prepared.high-prepared.close.shift(1)).abs(),(prepared.low-prepared.close.shift(1)).abs()],axis=1).max(axis=1);prepared["atr14"]=tr.rolling(14).mean()
            for signal in _retained_combo_all_trades(h).get("전저점+20일선 상승",[]):
                hits=prepared.index[prepared.date.eq(pd.Timestamp(signal["진입일"]))]
                if not len(hits):continue
                ei=int(hits[0]);entry=float(signal["실제진입가"]);c_stop=float(signal["C저점"]);atr=float(prepared.atr14.iat[ei]) if pd.notna(prepared.atr14.iat[ei]) else np.nan;stops={modes[0]:c_stop,modes[1]:max(c_stop,entry-2*atr) if np.isfinite(atr) and atr>0 else c_stop}
                for mode,stop in stops.items():
                    ex=_fixed_entry_exit(prepared,ei,entry,stop,"현재 복합매도")
                    if ex is None:continue
                    xi,xp,reason,peak,trough=ex;allrows[mode].append({"조합":mode,"종목코드":str(code).zfill(6),"진입일":signal["진입일"],"청산일":str(pd.Timestamp(prepared.date.iat[xi]).date()),"진입가":entry,"C저점":c_stop,"적용손절":float(stop),"초기위험%":float((entry-stop)/entry*100),"순수익":float((xp/entry-1)*100-.35),"최대상승":float((peak/entry-1)*100),"최대하락":float((trough/entry-1)*100),"보유일":int(xi-ei),"청산사유":reason})
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"손실 1단계 검증 {n}/{len(codes)}")
    progress.empty();summary=[_loss_guard_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")];dev_base=next((x for x in summary if x["조합"]==modes[0] and x["구간"].startswith("개발")),None);dev_guard=next((x for x in summary if x["조합"]==modes[1] and x["구간"].startswith("개발")),None);cf_base=next((x for x in summary if x["조합"]==modes[0] and x["구간"].startswith("확인")),None);cf_guard=next((x for x in summary if x["조합"]==modes[1] and x["구간"].startswith("확인")),None)
    passed=bool(dev_base and dev_guard and cf_base and cf_guard and dev_guard["-10%이하"]<dev_base["-10%이하"] and cf_guard["-10%이하"]<cf_base["-10%이하"] and (dev_guard.get("평균순수익") or -999)>=dev_base["평균순수익"] and (cf_guard.get("평균순수익") or -999)>=cf_base["평균순수익"] and (cf_guard.get("손익비") or 0)>=cf_base.get("손익비",0))
    result={"version":LOSS_GUARD_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"verdict":"1단계 채택 · ATR2 손실상한" if passed else "1단계 미채택 · 기존 C저점 유지","trades":allrows,"rules":["매수 종목·매수일·매수가와 복합매도는 동일","변경은 최초 손절선 하나뿐","기존은 C봉 저점 이탈 손절","시험안은 C저점과 매수가-2ATR 중 매수가에 가까운 가격을 손절선으로 사용","ATR은 진입일까지 확정된 14일 값만 사용","개발·확인 구간 모두 -10% 손실 건수가 감소해야 함","두 구간 평균수익 비악화 및 확인구간 손익비 비악화일 때만 채택","실패하면 ATR 배수를 바꾸며 반복하지 않음"]};_vg_write(LOSS_GUARD_RESULT,result);return result

def _render_loss_guard_lab():
    st.subheader("🛡️ 손실 줄이기 1단계 · 큰 손절 제한");st.caption("다른 조건은 고정하고 C저점 손절이 너무 먼 경우에만 진입 당시 2ATR로 위험을 제한합니다.")
    if st.button("손실 1단계 검증",key="loss_guard_step1"):
        with st.spinner("같은 매수·같은 매도에서 큰 손실만 줄일 수 있는지 비교 중입니다..."):_run_loss_guard_lab()
        st.rerun()
    r=_vg_read(LOSS_GUARD_RESULT)
    if r.get("version")!=LOSS_GUARD_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    with st.expander("최근 -10% 이하 손실 거래",expanded=False):
        rows=[]
        for mode,trades in r.get("trades",{}).items():rows.extend([dict(x,조합=mode) for x in trades if str(x.get("진입일",""))[:4]>="2024" and float(x.get("순수익",0))<=-10])
        st.dataframe(pd.DataFrame(rows).sort_values("순수익") if rows else pd.DataFrame(),use_container_width=True,hide_index=True)
    with st.expander("채택 기준",expanded=False):st.write(r.get("rules",[]))

def _ma10_compare_bars(h,freq=None):
    z=h[["date","open","high","low","close"]].copy().sort_values("date")
    for c in ("open","high","low","close"):z[c]=pd.to_numeric(z[c],errors="coerce")
    z=z.dropna();z["date"]=pd.to_datetime(z.date)
    if freq:z=z.set_index("date").resample(freq).agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index()
    z["ma10"]=z.close.rolling(10).mean();z["range20"]=(z.high.rolling(20).max()/z.low.rolling(20).min()-1)*100
    prev_close=z.close.shift(1);prev_ma=z.ma10.shift(1);lo=z[["open","close"]].min(axis=1);hi=z[["open","close"]].max(axis=1)
    z["buy_cross"]=(prev_close<prev_ma)&(z.close>=z.ma10)
    z["sell_cross"]=(prev_close>prev_ma)&(z.close<=z.ma10)
    z["buy_body"]=(z.range20>=8)&(prev_close<prev_ma)&(lo<=z.ma10)&(hi>=z.ma10)&(z.close>=z.ma10)&(z.close>z.open)
    z["sell_body"]=(z.range20>=8)&(prev_close>prev_ma)&(lo<=z.ma10)&(hi>=z.ma10)&(z.close<=z.ma10)&(z.close<z.open)
    state=0;states=[]
    for b,s in zip(z.buy_body.fillna(False),z.sell_body.fillna(False)):
        if b:state=1
        elif s:state=-1
        states.append(state)
    z["body_state"]=states;return z

def _ma10_compare_trades(h,mode):
    d=_ma10_compare_bars(h);w=_ma10_compare_bars(h,"W-FRI");m=_ma10_compare_bars(h,"ME")
    wx=w[["date","close","ma10","body_state"]].rename(columns={"close":"wclose","ma10":"wma","body_state":"wstate"})
    mx=m[["date","close","ma10","body_state"]].rename(columns={"close":"mclose","ma10":"mma","body_state":"mstate"})
    x=pd.merge_asof(d.sort_values("date"),wx.sort_values("date"),on="date",direction="backward")
    x=pd.merge_asof(x.sort_values("date"),mx.sort_values("date"),on="date",direction="backward")
    trades=[];pos=None
    for i,r in x.iterrows():
        if pos is None:
            if mode=="기존 종가교차":entry=bool(r.buy_cross and r.wclose>=r.wma and r.mclose>=r.mma)
            else:entry=bool(r.buy_body and r.wstate==1 and r.mstate==1)
            if entry:pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low))
        exit_now=bool(r.sell_cross) if mode=="기존 종가교차" else bool(r.sell_body)
        if exit_now:
            ret=(float(r.close)/pos["entry"]-1)*100-.35
            trades.append({"전략":mode,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"진입가":pos["entry"],"청산가":float(r.close),"순수익":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"]});pos=None
    return trades

def _ma10_compare_summary(rows,label):
    if not rows:return {"전략":label,"거래":0,"승률":"-","평균순수익":"-","중앙값":"-","+10%도달":"-","최대손실":"-","평균보유일":"-"}
    q=pd.DataFrame(rows)
    return {"전략":label,"거래":len(q),"승률":f"{(q['순수익']>0).mean()*100:.1f}%","평균순수익":f"{q['순수익'].mean():+.2f}%","중앙값":f"{q['순수익'].median():+.2f}%","+10%도달":f"{(q['최대상승']>=10).mean()*100:.1f}%","최대손실":f"{q['순수익'].min():+.2f}%","평균보유일":f"{q['보유일'].mean():.1f}일"}

def _run_ma10_body_compare():
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))};allrows={"기존 종가교차":[],"신규 몸통접촉":[]};used=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"]).sort_values("date").drop_duplicates("date")
            if len(h)<300:continue
            for mode in allrows:
                for z in _ma10_compare_trades(h,mode):z["종목코드"]=str(code).zfill(6);allrows[mode].append(z)
            used.append(str(code).zfill(6))
        except Exception:pass
    result={"version":MA10_BODY_COMPARE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":[_ma10_compare_summary(allrows[k],k) for k in allrows],"trades":allrows,"definition":"동일 종목·기간. 기존=종가 단순교차, 신규=횟보(20봉 폭 8% 미만) 제외+꾸리 무시+몸통 10선 접촉+월→주→일 확정. 둘 다 15일 제한 없이 반대 일봉 신호 종가 청산, 비용 0.35% 차감."}
    _vg_write(MA10_BODY_COMPARE_RESULT,result);return result

def _render_ma10_body_compare():
    with st.expander("🧪 기존 10선 vs 몸통 접촉 추세전환 검증",expanded=False):
        st.caption("전저점 전략과 섞지 않고 10선 전략만 별도 비교합니다. 미래 종가를 미리 보지 않습니다.")
        if st.button("10선 두 조건 동일 비교 시작",key="ma10_body_compare_start"):
            with st.spinner("저장 일봉으로 기존형과 신규형을 같은 기간에서 비교 중입니다..."):_run_ma10_body_compare()
            st.rerun()
        r=_vg_read(MA10_BODY_COMPARE_RESULT)
        if r.get("version")==MA10_BODY_COMPARE_VERSION:
            st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('definition','')}")
            st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)

MA10_SAFE_RESULT=Path("data")/"ma10_safe_engine"/"result.json"
MA10_SAFE_VERSION="MA10_CLOSE_CROSS_PRIORLOW_RISK_EXIT_WF_V1_20260928"

def _ma10_safe_trades(h,mode):
    d=_ma10_compare_bars(h);w=_ma10_compare_bars(h,"W-FRI");m=_ma10_compare_bars(h,"ME")
    wx=w[["date","close","ma10"]].rename(columns={"close":"wclose","ma10":"wma"});mx=m[["date","close","ma10"]].rename(columns={"close":"mclose","ma10":"mma"})
    x=pd.merge_asof(d.sort_values("date"),wx.sort_values("date"),on="date",direction="backward");x=pd.merge_asof(x.sort_values("date"),mx.sort_values("date"),on="date",direction="backward").reset_index(drop=True)
    tr=pd.concat([(x.high-x.low),(x.high-x.close.shift(1)).abs(),(x.low-x.close.shift(1)).abs()],axis=1).max(axis=1);x["atr14"]=tr.rolling(14).mean()
    trades=[];pos=None
    for i,r in x.iterrows():
        if pos is None:
            entry_signal=bool(r.buy_cross and r.wclose>=r.wma and r.mclose>=r.mma and 5000<=float(r.close)<=50000)
            if not entry_signal:continue
            _,a=_surviving_prior_low(x,i)
            if mode in ("전저점 손절","통합 안전형") and a is None:continue
            base_stop=float(r.close)*.93 if mode=="7% 방어" else None
            if mode=="전저점 손절":base_stop=float(a)
            if mode=="통합 안전형":base_stop=max(float(a),float(r.close)*.93)
            pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low),"stop":base_stop,"a":a}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low));exit_price=None;reason=None
        stop=pos["stop"]
        if mode=="통합 안전형" and pos["peak"]>=pos["entry"]*1.05 and np.isfinite(r.atr14):stop=max(stop,pos["peak"]-2*float(r.atr14));pos["stop"]=stop
        if stop is not None and (float(r.open)<stop or float(r.low)<stop):exit_price=float(r.open) if float(r.open)<stop else float(stop);reason="위험손절"
        elif bool(r.sell_cross):exit_price=float(r.close);reason="10선 매도"
        if exit_price is not None:
            trades.append({"전략":mode,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"진입가":pos["entry"],"청산가":exit_price,"전저점":pos["a"],"순수익":(exit_price/pos["entry"]-1)*100-.35,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"],"청산사유":reason});pos=None
    return trades

def _run_ma10_safe_engine():
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))};modes=["기존 10선","7% 방어","전저점 손절","통합 안전형"];allrows={m:[] for m in modes};used=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"]).sort_values("date").drop_duplicates("date")
            if len(h)<300:continue
            for mode in modes:
                for z in _ma10_safe_trades(h,mode):z["종목코드"]=str(code).zfill(6);allrows[mode].append(z)
            used.append(str(code).zfill(6))
        except Exception:pass
    summary=[_pl_combo_summary(v,k,p) for k,v in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x["거래"]>=30 and x["평균순수익"]>0 and x["중앙값"]>0 and x["최대손실"]>-15]
    winner=max(dev,key=lambda x:(x["중앙값"],x["평균순수익"],x["승률"],x["최대손실"]),default=None)
    confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None)
    passed=bool(confirm and confirm["거래"]>=30 and confirm["평균순수익"]>0 and confirm["중앙값"]>0 and confirm["최대손실"]>-15)
    result={"version":MA10_SAFE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":"독립 확인 통과 후보" if passed else "확정 보류","trades":allrows};_vg_write(MA10_SAFE_RESULT,result);return result

def _render_ma10_safe_engine():
    with st.expander("🛡️ 10일선 본체 + 전저점 안전장치 검증",expanded=False):
        st.caption("15일 강제매도 없이 기존 10일선 진입을 유지하고, 전저점은 진입이 아닌 손실 방어에만 사용합니다.")
        if st.button("10일선 안전형 4가지 비교 시작",key="ma10_safe_start"):
            with st.spinner("기존 10선과 세 가지 손실 방어형을 개발·확인구간으로 검증 중입니다..."):_run_ma10_safe_engine()
            st.rerun()
        r=_vg_read(MA10_SAFE_RESULT)
        if r.get("version")!=MA10_SAFE_VERSION:return
        st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}")
        st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
        w=r.get("development_winner")
        if not w:st.error("개발구간 기준을 만족한 안전형이 없습니다. 실전 채택하지 않습니다.")
        elif r.get("verdict")=="독립 확인 통과 후보":st.success(f"{w['조합']} · 최근 확인구간까지 통과한 최종 후보입니다.")
        else:st.warning(f"개발구간 1위 {w['조합']} · 최근 확인구간 실패로 확정하지 않습니다.")
        if r.get("confirmation"):st.write("**최근 확인구간 결과**",r["confirmation"])
        st.caption("최소 30거래, 평균·중앙 수익 양수, 최대손실 -15% 초과를 개발/확인구간에서 모두 요구합니다.")

BREAKOUT_PULLBACK_RESULT=Path("data")/"breakout_pullback_wf"/"result.json"
BREAKOUT_PULLBACK_VERSION="PRICE_VOLUME_BREAKOUT_FIRST_PULLBACK_WF_V1_20260929"

def _bp_prepare(h):
    z=h[[c for c in ("date","open","high","low","close","volume") if c in h.columns]].copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for c in ("open","high","low","close","volume"):
        if c in z.columns:z[c]=pd.to_numeric(z[c],errors="coerce")
    z=z.dropna(subset=["date","open","high","low","close","volume"]).reset_index(drop=True);z["date"]=pd.to_datetime(z.date)
    z["ma60"]=z.close.rolling(60).mean();z["ma120"]=z.close.rolling(120).mean();z["high60"]=z.high.rolling(60).max().shift(1);z["vol20"]=z.volume.rolling(20).median().shift(1)
    tr=pd.concat([(z.high-z.low),(z.high-z.close.shift(1)).abs(),(z.low-z.close.shift(1)).abs()],axis=1).max(axis=1);z["atr14"]=tr.rolling(14).mean();return z

def _bp_entry(z,i,mode):
    r=z.iloc[i];trend=bool(i>=130 and r.close>r.ma60>r.ma120 and z.ma60.iat[i]>z.ma60.iat[i-10]);brk=bool(trend and r.close>r.high60 and r.volume>=r.vol20*1.5 and r.close>r.open and 5000<=r.close<=50000)
    if not brk:return None
    level=float(r.high60);bvol=float(r.volume)
    if mode=="고점돌파 즉시":return i,float(r.close),max(level*.97,float(r.close)*.93),level
    pull=None
    for j in range(i+2,min(i+11,len(z)-1)):
        q=z.iloc[j]
        held=bool(q.low>=level*.97 and q.close>=level and q.close<=float(r.close)*1.03)
        turn=bool(q.close>q.open and q.close>z.close.iat[j-1])
        if held and turn:
            pull=j;break
    if pull is None:return None
    q=z.iloc[pull]
    if mode=="첫 눌림 확인":return pull,float(q.close),max(level*.97,float(q.close)*.93),level
    if mode=="거래량 감소 눌림":
        if float(q.volume)>bvol*.70:return None
        return pull,float(q.close),max(level*.97,float(q.close)*.93),level
    for j in range(pull+1,min(pull+6,len(z))):
        if float(z.close.iat[j])>float(z.high.iloc[max(pull-2,0):j].max()) and float(z.close.iat[j])<=float(r.close)*1.06:
            return j,float(z.close.iat[j]),max(float(z.low.iloc[pull:j+1].min()),level*.97,float(z.close.iat[j])*.93),level
    return None

def _bp_trades(h,mode):
    z=_bp_prepare(h);out=[];i=130
    while i<len(z)-2:
        e=_bp_entry(z,i,mode)
        if e is None:i+=1;continue
        ei,entry,stop,level=e;peak=float(z.high.iat[ei]);peak_close=float(z.close.iat[ei]);done=False
        for j in range(ei+1,len(z)):
            r=z.iloc[j];peak=max(peak,float(r.high));peak_close=max(peak_close,float(r.close))
            active_stop=stop
            if peak>=entry*1.05 and np.isfinite(r.atr14):active_stop=max(active_stop,peak_close-max(2*float(r.atr14),peak_close*.06))
            if float(r.open)<active_stop or float(r.low)<active_stop:
                xp=float(r.open) if float(r.open)<active_stop else float(active_stop);reason="구조손절" if peak<entry*1.05 else "추적매도"
                held=z.iloc[ei:j+1];out.append({"전략":mode,"진입일":str(z.date.iat[ei].date()),"청산일":str(z.date.iat[j].date()),"진입가":entry,"청산가":xp,"돌파선":level,"순수익":(xp/entry-1)*100-.35,"최대상승":(float(held.high.max())/entry-1)*100,"최대하락":(float(held.low.min())/entry-1)*100,"보유일":j-ei,"청산사유":reason});i=j+1;done=True;break
        if not done:
            j=len(z)-1;xp=float(z.close.iat[j]);held=z.iloc[ei:j+1];out.append({"전략":mode,"진입일":str(z.date.iat[ei].date()),"청산일":str(z.date.iat[j].date()),"진입가":entry,"청산가":xp,"돌파선":level,"순수익":(xp/entry-1)*100-.35,"최대상승":(float(held.high.max())/entry-1)*100,"최대하락":(float(held.low.min())/entry-1)*100,"보유일":j-ei,"청산사유":"기간말 평가"});break
    return out

def _run_breakout_pullback_wf():
    paths={p.stem:p for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))};modes=["고점돌파 즉시","첫 눌림 확인","거래량 감소 눌림","눌림후 재돌파"];allrows={m:[] for m in modes};used=[]
    for code,p in sorted(paths.items()):
        try:
            h=pd.read_csv(p,parse_dates=["date"])
            if len(h)<300 or "volume" not in h.columns:continue
            for mode in modes:
                for q in _bp_trades(h,mode):q["종목코드"]=str(code).zfill(6);allrows[mode].append(q)
            used.append(str(code).zfill(6))
        except Exception:pass
    summary=[_pl_combo_summary(v,k,p) for k,v in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x["거래"]>=30 and x["평균순수익"]>0 and x["중앙값"]>0 and x["최대손실"]>-15]
    winner=max(dev,key=lambda x:(x["중앙값"],x["평균순수익"],x["승률"],x["최대손실"]),default=None);confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None)
    passed=bool(confirm and confirm["거래"]>=30 and confirm["평균순수익"]>0 and confirm["중앙값"]>0 and confirm["최대손실"]>-15)
    result={"version":BREAKOUT_PULLBACK_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":"독립 확인 통과 후보" if passed else "확정 보류","trades":allrows};_vg_write(BREAKOUT_PULLBACK_RESULT,result);return result

def _render_breakout_pullback_wf():
    st.caption("10일선을 사용하지 않습니다. 가격 구조·거래량·60/120일 상승 방향만으로 돌파 후 첫 눌림을 검증합니다.")
    if st.button("돌파·첫 눌림 4가지 검증 시작",key="breakout_pullback_start"):
        with st.spinner("가격·거래량 돌파와 첫 눌림 조건을 개발·확인구간으로 검증 중입니다..."):_run_breakout_pullback_wf()
        st.rerun()
    r=_vg_read(BREAKOUT_PULLBACK_RESULT)
    if r.get("version")!=BREAKOUT_PULLBACK_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}")
    st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    w=r.get("development_winner")
    if not w:st.error("개발구간부터 기준을 만족한 조합이 없습니다. 이 접근도 채택하지 않습니다.")
    elif r.get("verdict")=="독립 확인 통과 후보":st.success(f"{w['조합']} · 최근 확인구간까지 통과한 후보입니다.")
    else:st.warning(f"개발구간 1위 {w['조합']} · 최근 확인구간 실패로 채택하지 않습니다.")
    if r.get("confirmation"):st.write("**최근 확인구간 결과**",r["confirmation"])
    st.caption("최소 30거래, 평균·중앙 수익 양수, 최대손실 -15% 초과를 개발/확인구간에서 모두 요구합니다.")

RANK_ENGINE_RESULT=Path("data")/"cross_section_rank"/"result.json"
RANK_ENGINE_VERSION="PRIOR_LOW_MA20_TURN_V16_20260929"
RANK_ROUND_TRIP_COST=0.35
RANK_RUN_LEGACY_OUTCOMES=False

def _rank_support_events(z):
    """차트를 한 번만 훑어 확인일별 (확인일, 의미저점)을 만든다."""
    events=[];swing=np.flatnonzero(z.swing7.to_numpy())
    for b in range(110,len(z)-2):
        # 눌림봉 뒤 3거래일 안의 양봉 고점돌파를 확인한다.
        confirm_i=None
        for c in range(b+1,min(b+4,len(z))):
            ma_turn=(c>=5 and pd.notna(z.at[c,"ma20"]) and pd.notna(z.at[c-5,"ma20"]) and float(z.at[c,"close"])>float(z.at[c,"ma20"]) and float(z.at[c,"ma20"])>float(z.at[c-5,"ma20"]))
            if ma_turn and float(z.at[c,"close"])>float(z.at[c,"open"]) and float(z.at[c,"close"])>float(z.at[b,"high"]):
                confirm_i=c;break
        if confirm_i is None:continue
        recent=swing[(swing>=b-100)&(swing<=b-10)]
        support=None
        for a in recent[::-1]:
            lo=float(z.at[a,"low"])
            if lo<=0 or float(z.at[b,"low"])<lo or float(z.at[b,"low"])>lo*1.05:continue
            if float(z.high.iloc[a+1:b].max())<lo*1.08:continue
            if float(z.low.iloc[a+1:confirm_i+1].min())<lo:continue
            support=lo;break
        if support is not None:events.append((confirm_i,support))
    return events

def _rank_support_outcome(z,i,events):
    """이번 주에 확정된 전저점 신호를 다음 거래일 시가로 검증한다."""
    if i<125 or i+1>=len(z):return None
    recent=[x for x in events if i-4<=x[0]<=i]
    if not recent:return None
    confirm_i,support=recent[-1]
    # 같은 주의 확인 종가를 본 뒤 다음 거래일 시가로 진입한다.
    e=i+1;entry=float(z.at[e,"open"])
    if entry<=0 or entry>float(z.at[confirm_i,"close"])*1.03:return None
    end=min(e+39,len(z)-1);peak=entry;worst=0.0;exit_i=end;support_broken=False
    for j in range(e,end+1):
        peak=max(peak,float(z.at[j,"close"]));worst=min(worst,(float(z.at[j,"low"])/entry-1)*100)
        support_broken=float(z.at[j,"low"])<support
        below20=(j>=e+1 and pd.notna(z.at[j,"ma20"]) and pd.notna(z.at[j-1,"ma20"]) and float(z.at[j,"close"])<float(z.at[j,"ma20"]) and float(z.at[j-1,"close"])<float(z.at[j-1,"ma20"]))
        trail=(peak/entry>=1.10 and float(z.at[j,"close"])/peak-1<=-0.06)
        if support_broken or below20 or trail:exit_i=j;break
    exit_price=min(float(z.at[exit_i,"open"]),support) if support_broken else float(z.at[exit_i,"close"])
    return {"ret":(exit_price/entry-1)*100,"dd":worst,"days":exit_i-e+1,"level":support,"entry_date":str(pd.Timestamp(z.at[e,"date"]).date())}

def _rank_feature_frame(h,code,name):
    z=h[[c for c in ("date","open","close","high","low","volume") if c in h.columns]].copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for c in ("open","close","high","low","volume"):z[c]=pd.to_numeric(z[c],errors="coerce")
    z=z.dropna().reset_index(drop=True);z["date"]=pd.to_datetime(z.date);z["code"]=str(code).zfill(6);z["name"]=name
    z["mom20"]=(z.close/z.close.shift(20)-1)*100;z["mom60"]=(z.close/z.close.shift(60)-1)*100;z["mom120"]=(z.close/z.close.shift(120)-1)*100
    z["ma20"]=z.close.rolling(20).mean();z["ma60"]=z.close.rolling(60).mean();z["ma120"]=z.close.rolling(120).mean();z["near_high"]=(z.close/z.high.rolling(60).max()-1)*100;z["vol_ratio"]=z.volume/z.volume.rolling(20).median()
    z["swing7"]=z.low.eq(z.low.rolling(7,center=True).min())
    tr=pd.concat([(z.high-z.low),(z.high-z.close.shift(1)).abs(),(z.low-z.close.shift(1)).abs()],axis=1).max(axis=1);z["risk"]=tr.rolling(14).mean()/z.close*100
    z["trend"]=(z.close>z.ma60).astype(int)+(z.ma60>z.ma120).astype(int)+(z.ma60>z.ma60.shift(10)).astype(int)
    for n in (10,20):
        z[f"ret{n}"]=(z.close.shift(-n)/z.close-1)*100
        z[f"dd{n}"]=(z.low.shift(-1)[::-1].rolling(n,min_periods=n).min()[::-1]/z.close-1)*100
    z["week"]=z.date.dt.to_period("W-FRI")
    weekly_idx=z.groupby("week",as_index=False).tail(1).index
    z["trend_ret"]=np.nan;z["trend_dd"]=np.nan;z["trend_days"]=np.nan;z["open_trend_ret"]=np.nan;z["open_trend_dd"]=np.nan;z["open_trend_days"]=np.nan
    z["limit1_trend_ret"]=np.nan;z["limit1_trend_dd"]=np.nan;z["limit1_trend_days"]=np.nan;z["limit1_filled"]=0
    z["support_ret"]=np.nan;z["support_dd"]=np.nan;z["support_days"]=np.nan;z["support_level"]=np.nan;z["support_entry_date"]=None
    support_events=_rank_support_events(z)
    for i in weekly_idx:
        if i+3>=len(z):continue
        if not RANK_RUN_LEGACY_OUTCOMES:
            out=_rank_support_outcome(z,i,support_events)
            if out:
                z.at[i,"support_ret"]=out["ret"];z.at[i,"support_dd"]=out["dd"];z.at[i,"support_days"]=out["days"]
                z.at[i,"support_level"]=out["level"];z.at[i,"support_entry_date"]=out["entry_date"]
            continue
        end=min(i+40,len(z)-1);entry=float(z.at[i,"close"]);peak=entry;worst=0.0;exit_i=end
        for j in range(i+1,end+1):
            peak=max(peak,float(z.at[j,"close"]));worst=min(worst,(float(z.at[j,"low"])/entry-1)*100)
            below20=(j>=i+3 and pd.notna(z.at[j,"ma20"]) and pd.notna(z.at[j-1,"ma20"]) and float(z.at[j,"close"])<float(z.at[j,"ma20"]) and float(z.at[j-1,"close"])<float(z.at[j-1,"ma20"]))
            trail=(peak/entry>=1.10 and float(z.at[j,"close"])/peak-1<=-0.06)
            if below20 or trail:exit_i=j;break
        z.at[i,"trend_ret"]=(float(z.at[exit_i,"close"])/entry-1)*100
        z.at[i,"trend_dd"]=worst;z.at[i,"trend_days"]=exit_i-i
        entry_i=i+1;end2=min(entry_i+39,len(z)-1);entry2=float(z.at[entry_i,"open"]);peak2=entry2;worst2=0.0;exit2=end2
        if entry2>0:
            for j in range(entry_i,end2+1):
                peak2=max(peak2,float(z.at[j,"close"]));worst2=min(worst2,(float(z.at[j,"low"])/entry2-1)*100)
                below20=(j>=entry_i+1 and pd.notna(z.at[j,"ma20"]) and pd.notna(z.at[j-1,"ma20"]) and float(z.at[j,"close"])<float(z.at[j,"ma20"]) and float(z.at[j-1,"close"])<float(z.at[j-1,"ma20"]))
                trail=(peak2/entry2>=1.10 and float(z.at[j,"close"])/peak2-1<=-0.06)
                if below20 or trail:exit2=j;break
            z.at[i,"open_trend_ret"]=(float(z.at[exit2,"close"])/entry2-1)*100
            z.at[i,"open_trend_dd"]=worst2;z.at[i,"open_trend_days"]=exit2-entry_i+1
        # 실전 지정가: 신호일 종가보다 1% 넘게 추격하지 않는다.
        # 다음 거래일 시가가 상한 이하이면 시가, 아니면 장중 저가가 상한에
        # 닿았을 때만 상한가로 체결된 것으로 보며 닿지 않으면 매수를 건너뛴다.
        limit1=entry*1.01
        next_open=float(z.at[entry_i,"open"]);next_low=float(z.at[entry_i,"low"])
        entry3=(next_open if next_open<=limit1 else limit1 if next_low<=limit1 else np.nan)
        if np.isfinite(entry3) and entry3>0:
            z.at[i,"limit1_filled"]=1;end3=min(entry_i+39,len(z)-1);peak3=entry3;worst3=0.0;exit3=end3
            for j in range(entry_i,end3+1):
                peak3=max(peak3,float(z.at[j,"close"]));worst3=min(worst3,(float(z.at[j,"low"])/entry3-1)*100)
                below20=(j>=entry_i+1 and pd.notna(z.at[j,"ma20"]) and pd.notna(z.at[j-1,"ma20"]) and float(z.at[j,"close"])<float(z.at[j,"ma20"]) and float(z.at[j-1,"close"])<float(z.at[j-1,"ma20"]))
                trail=(peak3/entry3>=1.10 and float(z.at[j,"close"])/peak3-1<=-0.06)
                if below20 or trail:exit3=j;break
            z.at[i,"limit1_trend_ret"]=(float(z.at[exit3,"close"])/entry3-1)*100
            z.at[i,"limit1_trend_dd"]=worst3;z.at[i,"limit1_trend_days"]=exit3-entry_i+1
        # 순위 선정 뒤 최대 10거래일 동안, 선정 당시 이미 알 수 있었던
        # 120일 전저점(최근 10일 제외)의 재지지와 반등 돌파만 기다린다.
        if i>=120:
            prior=z.iloc[i-120:i-9]
            if not prior.empty:
                support=float(prior.low.min());test_i=None;confirm_i=None
                for t in range(i+1,min(i+11,len(z)-2)):
                    if float(z.at[t,"low"])<support:break
                    touched=float(z.at[t,"low"])<=support*1.03
                    rebound=float(z.at[t,"close"])>float(z.at[t,"open"])
                    if touched and rebound:
                        c=t+1
                        if float(z.at[c,"low"])<support:break
                        if float(z.at[c,"close"])>float(z.at[t,"high"]) and float(z.at[c,"close"])>float(z.at[c,"open"]):
                            test_i=t;confirm_i=c;break
                if confirm_i is not None and confirm_i+1<len(z):
                    e=confirm_i+1;entry4=float(z.at[e,"open"])
                    if entry4>0 and entry4<=float(z.at[confirm_i,"close"])*1.03:
                        end4=min(e+39,len(z)-1);peak4=entry4;worst4=0.0;exit4=end4
                        for j in range(e,end4+1):
                            peak4=max(peak4,float(z.at[j,"close"]));worst4=min(worst4,(float(z.at[j,"low"])/entry4-1)*100)
                            support_stop=float(z.at[j,"low"])<support
                            below20=(j>=e+1 and pd.notna(z.at[j,"ma20"]) and pd.notna(z.at[j-1,"ma20"]) and float(z.at[j,"close"])<float(z.at[j,"ma20"]) and float(z.at[j-1,"close"])<float(z.at[j-1,"ma20"]))
                            trail=(peak4/entry4>=1.10 and float(z.at[j,"close"])/peak4-1<=-0.06)
                            if support_stop or below20 or trail:exit4=j;break
                        exit_price=(min(float(z.at[exit4,"open"]),support) if float(z.at[exit4,"low"])<support else float(z.at[exit4,"close"]))
                        z.at[i,"support_ret"]=(exit_price/entry4-1)*100;z.at[i,"support_dd"]=worst4;z.at[i,"support_days"]=exit4-e+1
                        z.at[i,"support_level"]=support;z.at[i,"support_entry_date"]=str(pd.Timestamp(z.at[e,"date"]).date())
    z=z.loc[weekly_idx].copy()
    return z[(z.close>=5000)&(z.close<=50000)&z.mom120.notna()].copy()

def _rank_score_panel(panel):
    if panel.empty:return panel
    # 종목별 휴장·누락일 때문에 같은 주의 마지막 날짜가 다를 수 있으므로
    # 정확한 날짜가 아니라 W-FRI 주차로 단면 순위를 계산한다.
    g=panel.groupby("week")
    panel["r20"]=g.mom20.rank(pct=True);panel["r60"]=g.mom60.rank(pct=True);panel["r120"]=g.mom120.rank(pct=True);panel["rhigh"]=g.near_high.rank(pct=True);panel["rvol"]=g.vol_ratio.rank(pct=True);panel["rrisk"]=g.risk.rank(pct=True,ascending=False)
    panel["score"]=25*panel.r20+25*panel.r60+15*panel.r120+15*panel.rhigh+10*panel.rvol+5*(panel.trend/3)+5*panel.rrisk
    # 순위 신호는 그대로 두고, 큰 손실을 줄이기 위한 사전 위험조건만 별도로 검증한다.
    panel["risk_pct"]=g.risk.rank(pct=True)
    panel["breadth"]=g.trend.transform(lambda s:float((s>=2).mean()))
    panel["defensive50"]=(panel.risk_pct<=0.50)&(panel.trend>=2)
    panel["defensive70"]=(panel.risk_pct<=0.70)&(panel.trend>=2)
    panel["market_ok"]=panel.breadth>=0.50
    return panel

def _rank_period_summary(rows,label,period):
    q=pd.DataFrame(rows)
    if not q.empty:q=q[(pd.to_datetime(q["기준일"]).dt.year<=2023) if period.startswith("개발") else (pd.to_datetime(q["기준일"]).dt.year>=2024)]
    if q.empty:return {"조합":label,"구간":period,"평가주":0,"평균체결률":None,"순승률":None,"평균순수익":None,"중앙순수익":None,"최악순수익":None,"평균최대하락":None,"평균보유일":None}
    fill=round(q.체결률.mean(),1) if "체결률" in q.columns else None
    return {"조합":label,"구간":period,"평가주":len(q),"평균체결률":fill,"순승률":round((q.순수익>0).mean()*100,1),"평균순수익":round(q.순수익.mean(),2),"중앙순수익":round(q.순수익.median(),2),"최악순수익":round(q.순수익.min(),2),"평균최대하락":round(q.최대하락.mean(),2),"평균보유일":round(q.보유일.mean(),1)}

def _run_rank_engine():
    # 같은 종목의 장기 타임머신 파일과 짧은 최신 캐시가 함께 있으면
    # 하나를 덮어쓰지 말고 날짜 기준으로 합쳐 완전한 이력을 만든다.
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))})
    try:names={str(x["code"]).zfill(6):x.get("name","") for x in _tm_full_universe()}
    except Exception:names={}
    frames=[];progress=st.progress(0,text=f"종목 자료 준비 0/{len(codes)}")
    for n_code,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)>=180 and "volume" in h.columns:frames.append(_rank_feature_frame(h,code,names.get(str(code).zfill(6),"")))
        except Exception:pass
        if n_code==len(codes) or n_code%5==0:progress.progress(n_code/len(codes),text=f"종목 자료 준비 {n_code}/{len(codes)}")
    progress.empty()
    if not frames:return {}
    panel=_rank_score_panel(pd.concat(frames,ignore_index=True));complete=panel.dropna(subset=["ret10","dd10"]);rows={}
    # 이전 순위 단독 전략은 탈락했으므로 더 이상 계산하거나 표시하지 않는다.
    modes=()
    for mode,screen in modes:
        for n in (3,5):
            label=f"{mode} · 상위{n} · 10일";pick=[]
            for week,q in complete.groupby("week"):
                if len(q)<30:continue
                top=screen(q).nlargest(n,"score")
                if len(top)<n:continue
                detail=[]
                for _,x in top.iterrows():
                    detail.append({"종목코드":str(x.code),"종목명":str(x["name"]),"10일수익":round(float(x.ret10),2),"최대하락":round(float(x.dd10),2),"위험도":round(float(x.risk),2),"점수":round(float(x.score),1)})
                gross=float(top.ret10.mean());pick.append({"기준일":str(pd.Timestamp(top.date.max()).date()),"비교종목수":int(len(q)),"수익률":gross,"순수익":gross-RANK_ROUND_TRIP_COST,"최대하락":float(top.dd10.mean()),"보유일":10.0,"종목":", ".join(top.code.tolist()),"상세":detail})
            rows[label]=pick
    trend=[]
    for week,q in ([] if not RANK_RUN_LEGACY_OUTCOMES else complete.groupby("week")):
        if len(q)<30:continue
        top=q[q.defensive50&q.trend_ret.notna()].nlargest(5,"score")
        if len(top)<5:continue
        detail=[]
        for _,x in top.iterrows():detail.append({"종목코드":str(x.code),"종목명":str(x["name"]),"10일수익":round(float(x.trend_ret),2),"최대하락":round(float(x.trend_dd),2),"위험도":round(float(x.risk),2),"점수":round(float(x.score),1)})
        gross=float(top.trend_ret.mean());trend.append({"기준일":str(pd.Timestamp(top.date.max()).date()),"비교종목수":int(len(q)),"수익률":gross,"순수익":gross-RANK_ROUND_TRIP_COST,"최대하락":float(top.trend_dd.mean()),"보유일":float(top.trend_days.mean()),"종목":", ".join(top.code.tolist()),"상세":detail})
    rows["방어50 · 상위5 · 추세보유"]=trend
    market_trend=[]
    for week,q in ([] if not RANK_RUN_LEGACY_OUTCOMES else complete.groupby("week")):
        if len(q)<30:continue
        top=q[q.defensive50&q.market_ok&q.trend_ret.notna()].nlargest(5,"score")
        if len(top)<5:continue
        detail=[]
        for _,x in top.iterrows():detail.append({"종목코드":str(x.code),"종목명":str(x["name"]),"10일수익":round(float(x.trend_ret),2),"최대하락":round(float(x.trend_dd),2),"위험도":round(float(x.risk),2),"점수":round(float(x.score),1)})
        gross=float(top.trend_ret.mean());market_trend.append({"기준일":str(pd.Timestamp(top.date.max()).date()),"비교종목수":int(len(q)),"수익률":gross,"순수익":gross-RANK_ROUND_TRIP_COST,"최대하락":float(top.trend_dd.mean()),"보유일":float(top.trend_days.mean()),"종목":", ".join(top.code.tolist()),"상세":detail})
    rows["방어50+시장 · 상위5 · 추세보유"]=market_trend
    next_open=[]
    for week,q in ([] if not RANK_RUN_LEGACY_OUTCOMES else complete.groupby("week")):
        if len(q)<30:continue
        top=q[q.defensive50&q.market_ok&q.open_trend_ret.notna()].nlargest(5,"score")
        if len(top)<5:continue
        detail=[]
        for _,x in top.iterrows():detail.append({"종목코드":str(x.code),"종목명":str(x["name"]),"10일수익":round(float(x.open_trend_ret),2),"최대하락":round(float(x.open_trend_dd),2),"위험도":round(float(x.risk),2),"점수":round(float(x.score),1)})
        gross=float(top.open_trend_ret.mean());next_open.append({"기준일":str(pd.Timestamp(top.date.max()).date()),"비교종목수":int(len(q)),"수익률":gross,"순수익":gross-RANK_ROUND_TRIP_COST,"최대하락":float(top.open_trend_dd.mean()),"보유일":float(top.open_trend_days.mean()),"종목":", ".join(top.code.tolist()),"상세":detail})
    rows["방어50+시장 · 상위5 · 다음시가+추세"]=next_open
    for pick_n in (() if not RANK_RUN_LEGACY_OUTCOMES else (1,2,5)):
        limit1=[]
        for week,q in complete.groupby("week"):
            if len(q)<30:continue
            # 순위 종목을 먼저 확정한 뒤 체결된 종목만 평가한다. 미체결을
            # 차순위 종목으로 바꾸지 않아 사후 종목선택 편향을 막는다.
            selected=q[q.defensive50&q.market_ok].nlargest(pick_n,"score")
            if len(selected)<pick_n:continue
            top=selected[(selected.limit1_filled==1)&selected.limit1_trend_ret.notna()]
            if top.empty:continue
            detail=[]
            for _,x in top.iterrows():detail.append({"종목코드":str(x.code),"종목명":str(x["name"]),"10일수익":round(float(x.limit1_trend_ret),2),"최대하락":round(float(x.limit1_trend_dd),2),"위험도":round(float(x.risk),2),"점수":round(float(x.score),1)})
            gross=float(top.limit1_trend_ret.mean());limit1.append({"기준일":str(pd.Timestamp(selected.date.max()).date()),"비교종목수":int(len(q)),"선정수":pick_n,"체결수":int(len(top)),"체결률":float(len(top)/pick_n*100),"수익률":gross,"순수익":gross-RANK_ROUND_TRIP_COST,"최대하락":float(top.limit1_trend_dd.mean()),"보유일":float(top.limit1_trend_days.mean()),"종목":", ".join(top.code.tolist()),"상세":detail})
        rows[f"방어50+시장 · 상위{pick_n} · +1%지정가+추세"]=limit1
    support_combo=[];support_gate=[]
    for week,q in complete.groupby("week"):
        if len(q)<30:continue
        # 전저점 구조를 먼저 찾고, 그 후보 안에서만 점수 상위 2개를 고른다.
        signals=q[q.market_ok&q.support_ret.notna()]
        triggered=signals.nlargest(2,"score")
        signal_date=str(pd.Timestamp(q.date.max()).date())
        support_gate.append({"기준일":signal_date,"감시수":int(len(q)),"발생수":int(len(signals)),"진입수":int(len(triggered))})
        if triggered.empty:continue
        detail=[]
        for _,x in triggered.iterrows():
            detail.append({"종목코드":str(x.code),"종목명":str(x["name"]),"진입일":x.support_entry_date,"전저점":round(float(x.support_level),0),"수익":round(float(x.support_ret),2),"최대하락":round(float(x.support_dd),2),"점수":round(float(x.score),1)})
        gross=float(triggered.support_ret.mean());support_combo.append({"기준일":signal_date,"비교종목수":int(len(q)),"신호종목수":int(len(signals)),"진입수":int(len(triggered)),"체결률":float(len(triggered)/len(q)*100),"수익률":gross,"순수익":gross-RANK_ROUND_TRIP_COST,"최대하락":float(triggered.support_dd.mean()),"보유일":float(triggered.support_days.mean()),"종목":", ".join(triggered.code.tolist()),"상세":detail})
    support_label="전저점지지+20일선전환→순위 · 최대2"
    rows[support_label]=support_combo
    summary=[_rank_period_summary(v,k,p) for k,v in rows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    # 전저점 전략의 비율은 신호가 없었던 주도 분모에 넣어 과장하지 않는다.
    gate_df=pd.DataFrame(support_gate)
    for item in summary:
        if item["조합"]!=support_label or gate_df.empty:continue
        years=pd.to_datetime(gate_df["기준일"]).dt.year
        g=gate_df[years<=2023] if item["구간"].startswith("개발") else gate_df[years>=2024]
        item["평균체결률"]=round(g.진입수.sum()/g.감시수.sum()*100,1) if not g.empty and g.감시수.sum() else None
    dev=[x for x in summary if x["조합"]==support_label and x["구간"].startswith("개발") and x["평가주"]>=30 and x["순승률"]>=55 and x["평균순수익"]>0 and x["중앙순수익"]>0 and x["최악순수익"]>-15]
    winner=dev[0] if dev else None;confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None)
    passed=bool(confirm and confirm["평가주"]>=30 and confirm["순승률"]>=55 and confirm["평균순수익"]>0 and confirm["중앙순수익"]>0 and confirm["최악순수익"]>-15)
    last=panel.week.max();latest_pool=panel[(panel.week==last)&panel.defensive70&panel.market_ok];latest=latest_pool.nlargest(3,"score");candidates=[]
    for _,r in latest.iterrows():candidates.append({"순위":len(candidates)+1,"종목코드":r.code,"종목명":r["name"],"현재가":int(round(r.close)),"종합점수":round(r.score,1),"20일추세":round(r.mom20,1),"60일추세":round(r.mom60,1),"120일추세":round(r.mom120,1),"거래량배수":round(r.vol_ratio,2),"위험도":round(r.risk,2),"기준일":str(pd.Timestamp(r.date).date())})
    result={"version":RANK_ENGINE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(frames),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":"독립 확인 통과 후보" if passed else "확정 보류","candidates":candidates,"weekly":rows,"support_gate":support_gate};_vg_write(RANK_ENGINE_RESULT,result);return result

def _render_rank_engine():
    st.caption("전저점 지지 구조를 고정하고, 확인봉 종가가 20일선 위이며 20일선도 5거래일 전보다 상승한 경우만 최대 2개 진입합니다.")
    if st.button("전체 종목 순위·전진검증 시작",key="rank_engine_start"):
        with st.spinner("전체 종목 순위에 비용과 추세매도까지 적용해 계산 중입니다..."):_run_rank_engine()
        st.rerun()
    r=_vg_read(RANK_ENGINE_RESULT)
    if r.get("version")!=RANK_ENGINE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}")
    summary_df=pd.DataFrame(r.get("summary",[]))
    focus_names={"전저점지지+20일선전환→순위 · 최대2"}
    focus=summary_df[summary_df["조합"].isin(focus_names)] if not summary_df.empty and "조합" in summary_df.columns else pd.DataFrame()
    st.subheader("핵심 결과 · 전저점 지지 + 20일선 전환")
    if not focus.empty:st.dataframe(focus,use_container_width=True,hide_index=True)
    else:st.info("검증 버튼을 누르면 10일 고정매도와 추세보유 결과가 여기에 표시됩니다.")
    with st.expander("검증 상세 보기",expanded=False):
        st.dataframe(focus,use_container_width=True,hide_index=True)
    w=r.get("development_winner")
    if not w:st.error("개발구간 기준을 통과한 순위 조합이 없습니다. 현재 후보는 관찰용으로만 사용합니다.")
    elif r.get("verdict")=="독립 확인 통과 후보":st.success(f"{w['조합']} · 최근 확인구간까지 통과했습니다.")
    else:st.warning(f"개발구간 1위 {w['조합']} · 최근 확인구간 실패로 매수에 사용하지 않습니다.")
    if w and r.get("weekly",{}).get(w["조합"]):
        recent=[x for x in r["weekly"][w["조합"]] if pd.Timestamp(x["기준일"]).year>=2024]
        worst=sorted(recent,key=lambda x:x.get("수익률",999))[:5]
        audit=[]
        for event in worst:
            for d in event.get("상세",[]):
                audit.append({"기준일":event["기준일"],"비교종목수":event.get("비교종목수",0),"주간평균":round(float(event["수익률"]),2),**d,"이상치의심":"확인필요" if d.get("10일수익",0)<=-30 or d.get("최대하락",0)<=-35 else "-"})
        if audit:
            with st.expander("🔍 최근 최악 손실 5회 · 원인 종목 확인",expanded=True):
                st.dataframe(pd.DataFrame(audit),use_container_width=True,hide_index=True)
                st.caption("표의 개별 수익은 고정형은 10일, 추세보유형은 실제 청산일까지입니다. -30% 이하 또는 최대하락 -35% 이하는 데이터 이상 가능성도 확인합니다.")
    st.subheader("오늘의 순위 관찰 후보 · 매수신호 아님")
    st.dataframe(pd.DataFrame(r.get("candidates",[])),use_container_width=True,hide_index=True)
    st.caption("이 표는 전저점 신호를 기다릴 관찰 후보일 뿐입니다. 전저점 미이탈·반등·고점돌파가 모두 확인되기 전에는 매수하지 않습니다. 시장상승 조건을 통과하지 않으면 표시하지 않습니다.")

MA10_CURVE_VERSION="MA10_MONTH_WEEK_DAY_HIERARCHY_BODY_V2_20260930"

def _ma10_hierarchy_bars(h,freq,curve_pct,away_pct):
    z=h[["date","open","high","low","close"]].copy().sort_values("date").drop_duplicates("date")
    for c in ("open","high","low","close"):z[c]=pd.to_numeric(z[c],errors="coerce")
    z=z.dropna();z["date"]=pd.to_datetime(z.date)
    if freq:z=z.set_index("date").resample(freq).agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index()
    z=z.reset_index(drop=True);z["ma10"]=z.close.rolling(10).mean();z["curve20"]=(z.high.rolling(20).max()/z.low.rolling(20).min()-1)*100
    z["dist"]=(z.close/z.ma10-1)*100;z["max_above"]=z.dist.shift(1).rolling(20).max();z["max_below"]=(-z.dist.shift(1)).rolling(20).max()
    side=np.sign(z.close-z.ma10);z["crosses"]=(side.ne(side.shift(1))&side.ne(0)&side.shift(1).ne(0)).rolling(10).sum();z["slope3"]=(z.ma10/z.ma10.shift(3)-1)*100
    lo=z[["open","close"]].min(axis=1);hi=z[["open","close"]].max(axis=1);touch=(lo<=z.ma10)&(hi>=z.ma10)
    enough=(z.curve20>=curve_pct)&(z.crosses<=2);from_below=(z.close.shift(1)<z.ma10.shift(1))&(z.max_below>=away_pct);pullback=(z.close.shift(1)>=z.ma10.shift(1))&(z.max_above>=away_pct)
    z["buy"]=(enough&(z.slope3>0)&touch&(z.close>z.open)&(z.close>=z.ma10)&(from_below|pullback)).fillna(False)
    body_sell=(touch&(z.close<z.open)&(z.close<=z.ma10));gap_sell=(z.close.shift(1)>=z.ma10.shift(1))&(z.close<z.ma10)
    z["sell"]=(body_sell|gap_sell).fillna(False)
    state=0;states=[]
    for buy,sell in zip(z.buy,z.sell):
        if bool(buy):state=1
        elif bool(sell):state=-1
        states.append(state)
    z["state"]=states
    return z

def _ma10_hierarchy_trades(h,label,level):
    # 같은 원천 일봉을 각각 월봉·주봉·일봉으로 재구성한다. 미래 월말/금요일 값은 사용하지 않는다.
    settings={"완화형":((18,6),(12,5),(8,3)),"균형형":((25,8),(18,7),(10,4)),"엄격형":((35,12),(25,10),(15,6))}
    (mc,ma),(wc,wa),(dc,da)=settings[level]
    d=_ma10_hierarchy_bars(h,None,dc,da);w=_ma10_hierarchy_bars(h,"W-FRI",wc,wa);m=_ma10_hierarchy_bars(h,"ME",mc,ma)
    wx=w[["date","buy","sell","state"]].rename(columns={"buy":"wbuy","sell":"wsell","state":"wstate"});mx=m[["date","buy","sell","state"]].rename(columns={"buy":"mbuy","sell":"msell","state":"mstate"})
    x=pd.merge_asof(d.sort_values("date"),wx.sort_values("date"),on="date",direction="backward");x=pd.merge_asof(x.sort_values("date"),mx.sort_values("date"),on="date",direction="backward")
    for c in ("wbuy","wsell","mbuy","msell"):x[c]=x[c].fillna(False).astype(bool)
    for c in ("wstate","mstate"):x[c]=x[c].fillna(0).astype(int)
    rows=[];pos=None
    for i,r in x.iterrows():
        if pos is None:
            # 월봉 상승 확정 → 주봉 상승 확정 → 일봉 몸통 접촉 종가 확정의 순서다.
            if r.mstate==1 and r.wstate==1 and bool(r.buy) and 10000<=float(r.close)<=50000:
                pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low))
        # 월·주 상승 중 일봉의 일시 이탈은 보유한다. 완성된 주봉 또는 월봉 반대 신호만 청산한다.
        if bool(r.wsell) or bool(r.msell):
            ret=(float(r.close)/pos["entry"]-1)*100-.35;reason="월봉 10개월선 반대신호" if bool(r.msell) else "주봉 10주선 반대신호"
            rows.append({"조합":label,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"순수익":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"],"청산사유":reason});pos=None
    return rows

def _run_ma10_curve_lab():
    levels=("완화형","균형형","엄격형");allrows={f"월→주→일·{level}":[] for level in levels}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"월·주·일 자료 준비 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<700:continue
            for level in levels:
                key=f"월→주→일·{level}"
                for row in _ma10_hierarchy_trades(h,key,level):row["종목코드"]=str(code).zfill(6);allrows[key].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"월·주·일 자료 준비 {n}/{len(codes)}")
    progress.empty();summary=[_ma10_curve_period_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x["거래"]>=30 and x["평균순수익"] is not None and x["평균순수익"]>0 and x["중앙순수익"]>0 and x["최대손실"]>-15]
    winner=max(dev,key=lambda x:(x["평균순수익"],x["승률"])) if dev else None;confirm=next((x for x in summary if winner and x["조합"]==winner["조합"] and x["구간"].startswith("확인")),None)
    passed=bool(confirm and confirm["거래"]>=30 and confirm["평균순수익"]>0 and confirm["중앙순수익"]>0 and confirm["최대손실"]>-15)
    result={"version":MA10_CURVE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"verdict":"독립 확인 통과 후보" if passed else "확정 보류","trades":allrows,"fixed_rules":["월봉은 10개월선·월말 종가 확정","주봉은 10주선·금요일 종가 확정","일봉은 10일선·당일 종가 확정","꼬리 제외·봉 몸통 접촉","월봉→주봉→일봉 순서","월·주 상승 중 일봉 단독 이탈은 보유","15일 강제청산 없음"],"test_only_rules":["굴곡 최소폭 완화/균형/엄격 수치는 미확정 비교값","최근 10봉 교차 2회 이하는 횡보 제외용 시험값"],"definition":"경규님 원안: 월봉 10개월선으로 큰 흐름을 먼저 확정하고, 주봉 10주선으로 중기 상승을 확인한 뒤, 일봉 10일선에 양봉 몸통이 닿고 종가가 위에서 확정될 때 진입합니다. 꼬리는 제외합니다. 월·주 상승 중 일봉만 이탈하면 보유하고, 금요일 주봉 또는 월말 월봉의 반대 몸통/갭 종가 신호에서 청산합니다. 15일 강제청산은 없습니다."};_vg_write(MA10_CURVE_RESULT,result);return result

def _render_ma10_curve_lab():
    st.subheader("〽️ 월봉→주봉→일봉 10이평 굴곡형 · 원안 검증")
    st.caption("월봉=10개월선, 주봉=10주선, 일봉=10일선입니다. 이전 일봉 전용 굴곡형 결과는 폐기되었습니다.")
    st.warning("할루시네이션 방지: 굴곡 퍼센트와 횡보 교차 횟수는 경규님이 수치로 확정하지 않았으므로 채택 조건이 아니라 비교 실험값입니다.")
    if st.button("경규님 원안 월·주·일 검증 시작",key="ma10_curve_mtf_start"):
        with st.spinner("월말·금요일·당일 종가 순서로 미래값 없이 검증 중입니다..."):_run_ma10_curve_lab()
        st.rerun()
    r=_vg_read(MA10_CURVE_RESULT)
    if r.get("version")!=MA10_CURVE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · 판정: {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    if r.get("development_winner"):st.write("**개발구간 1위**",r["development_winner"])
    if r.get("confirmation"):st.write("**최근 독립 확인**",r["confirmation"])
    with st.expander("실제 적용 조건 공개",expanded=False):
        st.write("**경규님 확정 규칙**",r.get("fixed_rules",[]));st.write("**미확정·비교용 수치**",r.get("test_only_rules",[]))
    st.caption(r.get("definition",""))

MA10_CURVE_VERSION="MA10_FAIR_EVENT_COMPARE_V6_20260930"

def _ma10_immediate_trades(h,rise_pct):
    cols=["date","open","high","low","close"]+(["volume"] if "volume" in h.columns else [])
    d=h[cols].copy().sort_values("date").drop_duplicates("date")
    if "volume" not in d:d["volume"]=1.0
    for c in ("open","high","low","close","volume"):d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna().reset_index(drop=True);d["date"]=pd.to_datetime(d.date);d["ma10"]=d.close.rolling(10).mean()
    # 진입일을 포함하지 않은 과거 120거래일 저점 대비 상승폭.
    # 미래 최고가를 사용하지 않으며, '큰 상승' 문턱만 20/30/40%로 비교한다.
    d["prior_low120"]=d.low.shift(1).rolling(120).min()
    d["prior_rise_pct"]=(d.close.shift(1)/d.prior_low120-1)*100
    d["rise_now"]=(d.close/d.prior_low120-1)*100
    d["prior_high60"]=d.high.shift(1).rolling(60).max()
    d["vol20"]=d.volume.shift(1).rolling(20).mean()
    # 최근 120거래일 안에 고점 대비 20% 이상 하락한 굴곡이 실제로 있었는지 확인한다.
    d["drawdown"]=d.close/d.high.rolling(60,min_periods=20).max()-1
    d["major_fall_recent"]=d.drawdown.shift(1).rolling(120).min()<=-0.20
    def trend_frame(freq,prefix):
        z=d.set_index("date").resample(freq).agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index()
        z["ma10"]=z.close.rolling(10).mean();z[f"{prefix}trend"]=(z.close>=z.ma10)&(z.ma10>z.ma10.shift(1))
        return z[["date",f"{prefix}trend"]]
    w=trend_frame("W-FRI","w");m=trend_frame("ME","m")
    x=pd.merge_asof(d.sort_values("date"),w.sort_values("date"),on="date",direction="backward");x=pd.merge_asof(x.sort_values("date"),m.sort_values("date"),on="date",direction="backward")
    x[["wtrend","mtrend"]]=x[["wtrend","mtrend"]].fillna(False).astype(bool)
    body_lo=x[["open","close"]].min(axis=1);body_hi=x[["open","close"]].max(axis=1)
    # 상승률 도달일과 돌파일을 억지로 일치시키지 않는다. 동일 돌파 사건을 모든 문턱에서 공유한다.
    x["structure_breakout"]=(x.major_fall_recent&x.mtrend&x.wtrend&(x.close>x.prior_high60)&(x.volume>=x.vol20*1.5)).fillna(False)
    x["pullback_touch"]=(x.mtrend&x.wtrend&(x.close.shift(1)>=x.ma10.shift(1))&(body_lo<=x.ma10)&(body_hi>=x.ma10)&(x.close>=x.ma10)&x.close.between(10000,50000)).fillna(False)
    # 연속 돌파는 하나의 사건으로 묶고, 30거래일 안의 재돌파도 같은 파동으로 본다.
    starts=list(x.index[x.structure_breakout & ~x.structure_breakout.shift(1,fill_value=False)])
    events=[];last=-999
    for i in starts:
        if i-last>30:events.append(i);last=i
    rows=[]
    for i in events:
        impulse=x.loc[i]
        if pd.isna(impulse.rise_now) or float(impulse.rise_now)<float(rise_pct):continue
        entry_i=None
        for j in range(i+1,min(len(x),i+31)):
            r=x.loc[j]
            if not bool(r.mtrend and r.wtrend):break
            if bool(r.pullback_touch):entry_i=j;break
        if entry_i is None:continue
        entry=x.loc[entry_i];exit_i=None
        peak=float(entry.high);trough=float(entry.low)
        for k in range(entry_i+1,len(x)):
            r=x.loc[k];peak=max(peak,float(r.high));trough=min(trough,float(r.low))
            if pd.notna(r.ma10) and float(r.close)<float(r.ma10):exit_i=k;break
        if exit_i is None:continue
        out=x.loc[exit_i];exit_price=float(out.close);ret=(exit_price/float(entry.close)-1)*100-.35
        rows.append({"조합":f"동일돌파·첫눌림 {rise_pct}%+","돌파일":str(pd.Timestamp(impulse.date).date()),"돌파상승폭":float(impulse.rise_now),"진입일":str(pd.Timestamp(entry.date).date()),"청산일":str(pd.Timestamp(out.date).date()),"진입가":float(entry.close),"청산가":exit_price,"순수익":ret,"최대상승":(peak/float(entry.close)-1)*100,"최대하락":(trough/float(entry.close)-1)*100,"보유일":exit_i-entry_i,"청산사유":"10일선 종가 이탈"})
    return rows

def _run_ma10_curve_lab():
    levels=(20,30,40);allrows={f"동일돌파·첫눌림 {v}%+":[] for v in levels}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"큰 상승 종목 검증 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<300:continue
            for level in levels:
                key=f"동일돌파·첫눌림 {level}%+"
                for row in _ma10_immediate_trades(h,level):row["종목코드"]=str(code).zfill(6);allrows[key].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"큰 상승 종목 검증 {n}/{len(codes)}")
    progress.empty();summary=[_ma10_curve_period_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    result={"version":MA10_CURVE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"verdict":"동일 돌파사건으로 20%·30%·40% 누적 비교","trades":allrows,"fixed_rules":["최근 120거래일 안에 고점 대비 20% 이상 하락한 큰 굴곡 존재","월봉 10개월선과 주봉 10주선이 모두 상승 방향","60거래일 전고점 돌파와 20일 평균 대비 거래량 1.5배 이상 동반","상승률 도달일과 돌파일을 같은 날로 강제하지 않음","같은 돌파사건을 상승폭 20%·30%·40% 이상으로 누적 비교","연속 돌파와 30거래일 내 재돌파는 하나의 파동으로 처리","돌파 후 30거래일 안의 첫 10일선 몸통 눌림만 종가 매수","종가가 10일선 아래면 매도·15일 강제청산 없음","상위 1건·3건 제외 평균과 손익비를 함께 표시"],"test_only_rules":["큰 하락 20%","거래량 1.5배","60거래일 전고점","돌파사건 간격·눌림 대기 30거래일","상승폭 20%·30%·40%는 아직 미확정 시험값"],"definition":"모든 비교는 동일한 거래량 동반 60일 전고점 돌파 사건에서 시작합니다. 돌파 당시 저점 대비 상승폭이 20%·30%·40% 이상인지 누적 분류한 뒤, 30거래일 안의 첫 10일선 눌림에서 매수하고 종가 이탈에서 매도합니다. 따라서 정상이라면 거래 수는 20% 이상이 가장 많고 40% 이상이 가장 적어야 합니다."};_vg_write(MA10_CURVE_RESULT,result);return result

def _render_ma10_curve_lab():
    st.subheader("〽️ 동일 돌파사건 · 큰 상승 첫 10일선 눌림")
    st.caption("하나의 돌파사건을 20%·30%·40%에 공통 적용해 공정하게 비교합니다. 거래 수는 20%≥30%≥40%가 정상입니다.")
    st.warning("20%·30%·40%, 하락 20%, 거래량 1.5배, 30일은 확정 조건이 아니라 경계를 찾기 위한 비교값입니다.")
    if st.button("동일 돌파사건으로 다시 검증",key="ma10_fair_event_retest"):
        with st.spinner("동일한 돌파사건을 기준으로 20%·30%·40% 누적 비교 중입니다..."):_run_ma10_curve_lab()
        st.rerun()
    r=_vg_read(MA10_CURVE_RESULT)
    if r.get("version")!=MA10_CURVE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    with st.expander("실제 적용 조건 공개",expanded=False):
        st.write("**검증 구조**",r.get("fixed_rules",[]));st.write("**미확정 시험값**",r.get("test_only_rules",[]))
    st.caption(r.get("definition",""))

# 경규님 원본 차트 재현: 임의 퍼센트·기간·거래량 문턱 없이 봉과 10이평선의 기하만 사용
MA10_CURVE_VERSION="MA10_ORIGINAL_CHART_GEOMETRY_V7_20260930"

def _ma10_original_bars(h,timeframe):
    d=h[["date","open","high","low","close"]].copy().sort_values("date").drop_duplicates("date")
    for c in ("open","high","low","close"):d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna().reset_index(drop=True);d["date"]=pd.to_datetime(d.date)
    if timeframe in ("주봉","월봉"):
        freq="W-FRI" if timeframe=="주봉" else "M";period=d.date.dt.to_period(freq)
        z=d.assign(_period=period).groupby("_period",as_index=False).agg(date=("date","last"),open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"))
        # 아직 끝나지 않은 현재 주·월 봉은 신호에 사용하지 않는다.
        if len(z) and d.date.max().date()<z._period.iloc[-1].end_time.date():z=z.iloc[:-1]
        d=z.drop(columns="_period").reset_index(drop=True)
    d["ma10"]=d.close.rolling(10).mean();d["ma_up"]=d.ma10>d.ma10.shift(1);d["ma_down"]=d.ma10<d.ma10.shift(1)
    lo=d[["open","close"]].min(axis=1);hi=d[["open","close"]].max(axis=1);touch=(lo<=d.ma10)&(hi>=d.ma10)
    # 꼬리는 제외한다. 봉 몸통이 아래→위로 통과하고 10이평이 상승하면 매수,
    # 위→아래로 통과하고 10이평이 하락하면 매도한다. 하락 갭은 안전상 이탈로 처리한다.
    d["buy"]=(d.close.shift(1)<d.ma10.shift(1))&touch&(d.close>=d.ma10)&d.ma_up
    d["sell"]=(d.close.shift(1)>d.ma10.shift(1))&(d.close<d.ma10)&d.ma_down&(touch|(hi<d.ma10))
    d["regime"]=(d.close>=d.ma10)&d.ma_up
    return d

def _ma10_original_trades(h,label,timeframe):
    z=_ma10_original_bars(h,timeframe);rows=[];pos=None
    for i,r in z.iterrows():
        if pos is None:
            if bool(r.buy):pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low))
        if bool(r.sell):
            ret=(float(r.close)/pos["entry"]-1)*100-.35
            rows.append({"조합":label,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"진입가":pos["entry"],"청산가":float(r.close),"순수익":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"]})
            pos=None
    return rows

def _ma10_original_hierarchy(h):
    d=_ma10_original_bars(h,"일봉");w=_ma10_original_bars(h,"주봉")[["date","regime"]].rename(columns={"regime":"wreg"});m=_ma10_original_bars(h,"월봉")[["date","regime"]].rename(columns={"regime":"mreg"})
    if d.empty or w.empty or m.empty:return []
    z=pd.merge_asof(d.sort_values("date"),w.sort_values("date"),on="date",direction="backward");z=pd.merge_asof(z.sort_values("date"),m.sort_values("date"),on="date",direction="backward")
    z[["wreg","mreg"]]=z[["wreg","mreg"]].fillna(False).astype(bool);rows=[];pos=None
    for i,r in z.iterrows():
        if pos is None:
            if bool(r.mreg and r.wreg and r.buy):pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low))
        if bool(r.sell or not r.wreg or not r.mreg):
            ret=(float(r.close)/pos["entry"]-1)*100-.35
            rows.append({"조합":"월→주→일 순서","진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"진입가":pos["entry"],"청산가":float(r.close),"순수익":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"]});pos=None
    return rows

def _run_ma10_curve_lab():
    labels=("월봉 10개월선","주봉 10주선","일봉 10일선","월→주→일 순서");allrows={k:[] for k in labels}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"원본 차트 규칙 검증 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<300:continue
            for label,tf in ((labels[0],"월봉"),(labels[1],"주봉"),(labels[2],"일봉")):
                for row in _ma10_original_trades(h,label,tf):row["종목코드"]=str(code).zfill(6);allrows[label].append(row)
            for row in _ma10_original_hierarchy(h):row["종목코드"]=str(code).zfill(6);allrows[labels[3]].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"원본 차트 규칙 검증 {n}/{len(codes)}")
    progress.empty();summary=[_ma10_curve_period_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    result={"version":MA10_CURVE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"verdict":"임의 숫자 제거 · 원본 차트 몸통/10이평 기하 검증","trades":allrows,"fixed_rules":["월봉은 10개월선·주봉은 10주선·일봉은 10일선","꼬리는 제외하고 시가와 종가 사이의 봉 몸통만 판정","10이평이 상승하면서 봉 몸통이 아래에서 위로 통과한 종가 매수","10이평이 하락하면서 봉 몸통이 위에서 아래로 통과한 종가 매도","하락 갭으로 몸통 전체가 10이평 아래면 안전상 매도","월봉·주봉·일봉 단독과 월→주→일 순서를 같은 자료에서 비교","현재 진행 중인 미완성 주봉·월봉은 신호에서 제외","15일 강제청산 없음"],"removed_rules":["상승폭 20%·30%·40%","고점 대비 하락 20%","거래량 1.5배","60일 전고점","돌파 후 30일 제한"],"definition":"경규님이 보여준 월봉·주봉·일봉 차트의 노란 10이평과 봉 몸통 관계만 코드로 옮겼습니다. 임의 상승률·거래량·전고점 기간은 쓰지 않습니다. 월·주·일 각각의 신호와 월→주→일 순서 신호를 분리해 어느 해석이 실제 그림과 맞는지 비교합니다."};_vg_write(MA10_CURVE_RESULT,result);return result

def _render_ma10_curve_lab():
    st.subheader("〽️ 경규님 원본 차트 · 숫자 없는 10이평 검증")
    st.caption("20%·1.5배·60일·30일을 모두 제거했습니다. 봉 몸통과 월10·주10·일10선의 방향만 검증합니다.")
    if st.button("원본 차트 규칙 그대로 검증",key="ma10_original_geometry_retest"):
        with st.spinner("월봉·주봉·일봉의 몸통과 10이평 접촉만 검증 중입니다..."):_run_ma10_curve_lab()
        st.rerun()
    r=_vg_read(MA10_CURVE_RESULT)
    if r.get("version")!=MA10_CURVE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    with st.expander("실제 적용 조건 공개",expanded=False):
        st.write("**경규님 차트에서 옮긴 규칙**",r.get("fixed_rules",[]));st.write("**이번에 삭제한 임의 조건**",r.get("removed_rules",[]))
    st.caption(r.get("definition",""))

# 주봉 매수는 고정하고, 경규님이 말한 '위에서 몸통 최초 접촉' 매도만 비교한다.
MA10_CURVE_VERSION="MA10_WEEKLY_CONFIRMED_CLOSE_V8_20261001"

def _ma10_first_down_touch(z):
    lo=z[["open","close"]].min(axis=1);hi=z[["open","close"]].max(axis=1);touch=(lo<=z.ma10)&(hi>=z.ma10)
    # 이평선의 기울기는 기다리지 않는다. 위에 있던 봉이 몸통으로 닿거나 하락 갭으로 아래 마감하면 즉시 매도한다.
    return ((z.close.shift(1)>z.ma10.shift(1))&(z.close<=z.ma10)&(touch|(hi<z.ma10))).fillna(False)

def _weekly_entry_exit_compare(h,exit_mode):
    w=_ma10_original_bars(h,"주봉").copy();d=_ma10_original_bars(h,"일봉").copy()
    if w.empty or d.empty:return []
    w["fast_sell"]=_ma10_first_down_touch(w);d["fast_sell"]=_ma10_first_down_touch(d)
    rows=[];pos=None
    for i,r in w.iterrows():
        if pos is None:
            if bool(r.buy):pos={"wi":i,"date":r.date,"entry":float(r.close)}
            continue
        if exit_mode=="주봉 첫 접촉" and bool(r.fast_sell):
            segment=d[(d.date>=pos["date"])&(d.date<=r.date)];peak=float(segment.high.max()) if len(segment) else float(r.high);trough=float(segment.low.min()) if len(segment) else float(r.low)
            ret=(float(r.close)/pos["entry"]-1)*100-.35
            rows.append({"조합":exit_mode,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"진입가":pos["entry"],"청산가":float(r.close),"순수익":ret,"최대상승":(peak/pos["entry"]-1)*100,"최대하락":(trough/pos["entry"]-1)*100,"보유일":len(segment)});pos=None
        elif exit_mode=="일봉 첫 접촉":
            exits=d[(d.date>pos["date"])&(d.fast_sell)]
            if len(exits):
                out=exits.iloc[0]
                # 아직 도달하지 않은 미래 일봉이면 다음 주봉 반복에서 기다린다.
                if out.date<=r.date:
                    segment=d[(d.date>=pos["date"])&(d.date<=out.date)];peak=float(segment.high.max());trough=float(segment.low.min());ret=(float(out.close)/pos["entry"]-1)*100-.35
                    rows.append({"조합":exit_mode,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(out.date).date()),"진입가":pos["entry"],"청산가":float(out.close),"순수익":ret,"최대상승":(peak/pos["entry"]-1)*100,"최대하락":(trough/pos["entry"]-1)*100,"보유일":len(segment)});pos=None
    return rows

def _run_ma10_curve_lab():
    labels=("주봉 금요일 확정매도",);allrows={k:[] for k in labels}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"주봉 진입·매도 비교 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<300:continue
            for row in _weekly_entry_exit_compare(h,"주봉 첫 접촉"):
                row["조합"]="주봉 금요일 확정매도";row["종목코드"]=str(code).zfill(6);allrows[labels[0]].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"주봉 진입·매도 비교 {n}/{len(codes)}")
    progress.empty();summary=[_ma10_curve_period_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    result={"version":MA10_CURVE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"verdict":"주중 흔들림 무시 · 금요일 주봉 몸통만 확정 판정","trades":allrows,"fixed_rules":["매수는 주봉 10주선이 상승하면서 봉 몸통이 아래에서 위로 통과한 금요일 종가","주중 10주선 이탈은 미확정이므로 매도하지 않음","금요일 종가에 회복하면 밑꼬리로 보고 계속 보유","금요일 확정 주봉 몸통이 위에서 10주선에 닿거나 아래 마감할 때 매도","꼬리는 접촉 판정에서 제외","매도할 때 10주선이 하락할 때까지 기다리지 않음","일봉 신호를 주봉 포지션의 매도에 섞지 않음","15일 강제청산 없음"],"removed_rules":["주봉 매수 후 일봉 첫 접촉 매도","매도 시 10이평선 하락 기울기 조건","상승폭·거래량·전고점·대기기간 조건"],"definition":"주봉 전략은 금요일 종가로 완성된 주봉만 판정합니다. 주중에 10주선 아래로 내려가도 금요일에 말아 올리면 밑꼬리이므로 보유합니다. 금요일 종가 기준 봉 몸통이 10주선에 닿거나 아래에서 끝났을 때만 매도합니다."};_vg_write(MA10_CURVE_RESULT,result);return result

def _render_ma10_curve_lab():
    st.subheader("〽️ 주봉 10주선 · 금요일 종가 확정 검증")
    st.caption("주중 하락은 신호가 아닙니다. 금요일에 완성된 주봉 몸통만 매수·매도 판정합니다.")
    if st.button("금요일 확정 주봉전략 검증",key="ma10_weekly_confirmed_close"):
        with st.spinner("주중 밑꼬리를 무시하고 금요일 확정 주봉만 검증 중입니다..."):_run_ma10_curve_lab()
        st.rerun()
    r=_vg_read(MA10_CURVE_RESULT)
    if r.get("version")!=MA10_CURVE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    with st.expander("실제 적용 조건 공개",expanded=False):
        st.write("**고정·비교 규칙**",r.get("fixed_rules",[]));st.write("**제거한 잘못된 조건**",r.get("removed_rules",[]))
    st.caption(r.get("definition",""))

# 승률 개선은 사전 고정한 네 후보만 1회 비교한다. 확인구간을 보고 재튜닝하지 않는다.
MA10_CURVE_VERSION="MA10_WINRATE_ONE_SHOT_V9_20261001"

def _weekly_variant_trades(h,label):
    w=_ma10_original_bars(h,"주봉").copy();m=_ma10_original_bars(h,"월봉")[["date","regime"]].rename(columns={"regime":"mreg"})
    if w.empty:return []
    w["fast_sell"]=_ma10_first_down_touch(w);w["bull_body"]=w.close>w.open;w["first_turn"]=w.ma_up&~w.ma_up.shift(1,fill_value=False)
    if len(m):w=pd.merge_asof(w.sort_values("date"),m.sort_values("date"),on="date",direction="backward")
    else:w["mreg"]=False
    w["mreg"]=w.mreg.fillna(False).astype(bool)
    if label=="기존 주봉":buy=w.buy
    elif label=="상승 몸통":buy=w.buy&w.bull_body
    elif label=="첫 상승전환":buy=w.buy&w.first_turn
    else:buy=w.buy&w.bull_body&w.mreg
    rows=[];pos=None
    for i,r in w.iterrows():
        if pos is None:
            if bool(buy.loc[i]):pos={"i":i,"date":r.date,"entry":float(r.close),"peak":float(r.high),"trough":float(r.low)}
            continue
        pos["peak"]=max(pos["peak"],float(r.high));pos["trough"]=min(pos["trough"],float(r.low))
        if bool(r.fast_sell):
            ret=(float(r.close)/pos["entry"]-1)*100-.35
            rows.append({"조합":label,"진입일":str(pd.Timestamp(pos["date"]).date()),"청산일":str(pd.Timestamp(r.date).date()),"진입가":pos["entry"],"청산가":float(r.close),"순수익":ret,"최대상승":(pos["peak"]/pos["entry"]-1)*100,"최대하락":(pos["trough"]/pos["entry"]-1)*100,"보유일":i-pos["i"]});pos=None
    return rows

def _run_ma10_curve_lab():
    labels=("기존 주봉","상승 몸통","첫 상승전환","월봉상승+상승몸통");allrows={k:[] for k in labels}
    codes=sorted({p.stem for p in list(TM_V4_DAILY_DIR.glob("*.csv"))+list(DAILY_CACHE_DIR.glob("*.csv"))});used=[];progress=st.progress(0,text=f"승률 개선 1회 검증 0/{len(codes)}")
    for n,code in enumerate(codes,1):
        try:
            h=_mtf_cached(code)
            if len(h)<300:continue
            for label in labels:
                for row in _weekly_variant_trades(h,label):row["종목코드"]=str(code).zfill(6);allrows[label].append(row)
            used.append(str(code).zfill(6))
        except Exception:pass
        if n==len(codes) or n%5==0:progress.progress(n/max(1,len(codes)),text=f"승률 개선 1회 검증 {n}/{len(codes)}")
    progress.empty();summary=[_ma10_curve_period_summary(rows,key,p) for key,rows in allrows.items() for p in ("개발 2020~2023","확인 2024~현재")]
    dev=[x for x in summary if x["구간"].startswith("개발") and x.get("거래",0)>0];winner=max(dev,key=lambda x:(x.get("승률") or -999,x.get("평균순수익") or -999))["조합"] if dev else None
    confirm=next((x for x in summary if x["구간"].startswith("확인") and x["조합"]==winner),None);base=next((x for x in summary if x["구간"].startswith("확인") and x["조합"]=="기존 주봉"),None)
    adopted=bool(winner and winner!="기존 주봉" and confirm and base and confirm["승률"]>base["승률"] and confirm["평균순수익"]>0 and confirm["중앙순수익"]>=base["중앙순수익"] and confirm["최대손실"]>=base["최대손실"])
    verdict=(f"채택 후보: {winner}" if adopted else "채택 없음 · 10주선 승률 튜닝 종료")
    result={"version":MA10_CURVE_VERSION,"updated_at":now_kst().strftime("%Y-%m-%d %H:%M"),"stocks":len(used),"summary":summary,"development_winner":winner,"confirmation":confirm,"baseline_confirmation":base,"verdict":verdict,"trades":allrows,"fixed_rules":["매수·매도는 금요일 종가로 완성된 주봉 몸통만 사용","매도는 위에서 10주선에 몸통이 최초 접촉하면 확정","개발구간 2020~2023에서 승률 1위 하나만 선택","확인구간 2024~현재는 선택 후 단 한 번만 평가","확인구간에서 기존보다 승률 상승·평균수익 양수·중앙수익과 최대손실 비악화 시에만 채택","통과하지 못하면 새로운 조건을 더 붙이지 않고 10주선 승률 튜닝 종료"],"candidates":{"기존 주봉":"현재 원안 기준","상승 몸통":"매수 주봉의 종가가 시가보다 높은 경우","첫 상승전환":"10주선이 하락·평탄에서 처음 상승한 주","월봉상승+상승몸통":"10개월선 상승 상태이면서 상승 주봉 몸통"},"definition":"무한 반복을 막기 위해 후보와 합격 규칙을 결과 확인 전에 고정했습니다. 개발구간 승률만으로 1위를 선택하고 확인구간은 수정 없이 한 번 평가합니다. 실패하면 추가 튜닝하지 않습니다."};_vg_write(MA10_CURVE_RESULT,result);return result

def _render_ma10_curve_lab():
    st.subheader("🎯 주봉 10주선 승률 개선 · 1회 최종검증")
    st.caption("네 후보를 미리 고정했습니다. 개발구간 1위를 확인구간에서 딱 한 번 평가하고 실패하면 추가 튜닝을 중단합니다.")
    if st.button("승률 개선 최종 1회 검증",key="ma10_winrate_one_shot"):
        with st.spinner("사전 고정한 네 후보를 개발·확인구간으로 분리 검증 중입니다..."):_run_ma10_curve_lab()
        st.rerun()
    r=_vg_read(MA10_CURVE_RESULT)
    if r.get("version")!=MA10_CURVE_VERSION:return
    st.info(f"검증 종목 {r.get('stocks',0)}개 · {r.get('updated_at','')} · {r.get('verdict','')}");st.dataframe(pd.DataFrame(r.get("summary",[])),use_container_width=True,hide_index=True)
    if r.get("development_winner"):st.write("**개발구간 승률 1위**",r.get("development_winner"))
    if r.get("confirmation"):st.write("**1위의 독립 확인 결과**",r.get("confirmation"))
    with st.expander("후보와 합격 규칙 공개",expanded=False):
        st.write("**사전 고정 후보**",r.get("candidates",{}));st.write("**무한반복 방지 규칙**",r.get("fixed_rules",[]))
    st.caption(r.get("definition",""))

# 실전 화면에는 추천·보유·추적만 노출하고, 백테스트는 요청할 때만 열어
# 모바일에서 5~10초 안에 행동을 결정할 수 있게 한다.
st.header("🏆 전체 종목 순위·지속 추적")
_render_rank_engine()
_render_portfolio_adviser()
_render_campaign_manager()
st.divider()
with st.expander("🧪 연구용 검증실 · 필요할 때만 열기",expanded=False):
    st.caption("남길 조건 조합과 굴곡형 10이평 검증만 바로 실행할 수 있습니다. 나머지 과거 연구는 숨겼습니다.")
    _render_retained_combo_lab()
    st.divider()
    _render_exit_only_lab()
    st.divider()
    _render_loss_guard_lab()
    st.divider()
    _render_ma10_curve_lab()
    if st.toggle("고급 백테스트·상대강도 검증 표시",value=False,key="show_research_labs"):
        _render_one_rebuild_lab()
        _render_mtf10_lab()
