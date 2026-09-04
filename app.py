
import re, math, requests, io, zipfile, os, time, json, hashlib
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import Counter

st.set_page_config(page_title="Stock Compass · ONE", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0"}
APP_SCAN_SCHEMA="V4_BASE_WHOLE_MARKET1"
APP_VERSION="V4_ENTRY_SAME_EVENT_FIX1"
FUTURE_AI_SCHEMA="WEBSEARCH_NO_JSON_V2"

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
            if price<1000 or price>50000:continue
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
        if not np.isfinite(cur) or cur<1000 or cur>50000:return None
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
        if not np.isfinite(cur) or cur<1000 or cur>50000:return None
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
        if p<1000 or p>50000:return None
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
    진바닥을 먼저 정한 뒤 B를 찾는다.
    - 5/10/20/60/120일 저점을 서로 비교한다.
    - 최근 얕은 5/10/20일 저점을 A로 승격하지 않는다.
    - 기본 A는 120일의 깊은 저점.
    - 120일 저점이 창의 왼쪽에 너무 가까우면(90거래일 이상 경과),
      250일까지 확장해 3% 이상 더 깊은 오래된 저점이 있는지 확인한다.
    - 마지막 3봉은 pivot 확인 전이므로 A 탐색에서 제외한다.
    """
    try:
        if df is None or len(df)<80:return None
        h=df.tail(300).copy().reset_index(drop=True)
        n=len(h); confirmed_end=max(0,n-3)
        if confirmed_end<60:return None

        windows=[5,10,20,60,120]
        if confirmed_end>=180:windows.append(250)
        pts={w:_window_low_point(h,w,confirmed_end) for w in windows}
        pts={w:p for w,p in pts.items() if p}
        if not pts:return None

        # 기본 진바닥: 120일. 자료가 짧으면 60일.
        base_w=120 if 120 in pts else 60
        base=dict(pts[base_w])
        base_age=(n-1)-int(base['i'])
        expanded=False

        # 120일 끝자락 저점은 잘린 큰 파도일 수 있으므로 250일까지 자동 확장.
        if 250 in pts and base_w==120 and base_age>=90:
            longp=pts[250]
            if float(longp['low']) <= float(base['low'])*0.97:
                base=dict(longp); base_w=250; expanded=True

        ai=int(base['i']); A=float(base['low']); age=(n-1)-ai
        support=[]
        for w,p in pts.items():
            if abs(int(p['i'])-ai)<=3:
                support.append(int(w))
        support=sorted(support)

        # A가 60일 범위 안에도 실제 최저점이면 현재 매매에 쓸 수 있는 '신선한 진바닥'.
        fresh=bool(age<=60 and any(w in support for w in (20,60,120)))
        if fresh:
            state='진바닥 · 신선'
        elif age<=120:
            state='진바닥 · 오래됨'
        else:
            state='장기 진바닥 · 관망'

        # 화면 설명용 최근 저점 계층.
        hierarchy=[]
        for w in (5,10,20,60,120,250):
            p=pts.get(w)
            if p:
                hierarchy.append({"window":w,"i":int(p['i']),"low":float(p['low']),"date":p['date']})

        return {
            "i":ai,"date":h.loc[ai,'date'],"low":A,
            "age":int(age),"fresh":fresh,"state":state,
            "base_window":int(base_w),"support_windows":support,
            "expanded":expanded,"hierarchy":hierarchy,
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

    # 60일만 고집하지 않고 90일까지 허용하되,
    # 60일을 넘긴 진바닥은 강한 B 지지매물이 있어야 최종 ONE으로 승격된다.
    if age>90:return None

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
        if not np.isfinite(cur) or cur<1000 or cur>50000:return None

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
            "stale_bottom":bool(setup.get("stale_bottom",False))
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
        if not np.isfinite(cur) or cur<=0 or cur>50000:return None

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
                is_liquid=(1000<=cur<=50000 and len(v)>=15 and float(v.median())>=50000 and
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
    strong.sort(key=lambda z:(z['score']+0.8*z.get('flow_bonus',0),-z['dist']),reverse=True)
    candidates.sort(key=lambda z:(z['candidate_rank']-0.6*z.get('flow_bonus',0),abs(z['stop_pct'])))

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
           "batch_quote_count":len(quotes),"full_fetch_count":full_fetch_count,"mtf_enabled":True,"minute_top_checked":min(3,len(strong))+min(3,len(candidates))}
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
st.caption("진입 · 익절 · 손절만 확인")

with st.expander("선정 기준"):
    st.write("A 전저점 → B 지지 → 재반등 확인. +10% 익절 / A 이탈 손절.")

st.markdown("**검색범위: KOSPI + KOSDAQ 전체 · KIS 종목마스터 + KIS 일봉** · **현재가 50,000원 이하** · 메인 ONE은 ETF/ETN/스팩/리츠/우선주·저유동성 제외 · 저유동 급등/ETF는 별도 레이더")
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

def candidate_price_path(cur,stop,confirm,target,status):
    vals=[float(stop),float(confirm),float(cur),float(target)]
    lo=min(vals); hi=max(vals); span=max(hi-lo,1.0)
    def pos(v):
        return 6 + (float(v)-lo)/span*88
    ps,pe,pc,pt=[pos(v) for v in (stop,confirm,cur,target)]
    if status=="진입준비":
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
      <div style="font-size:13px;color:#aab0b7;margin-bottom:15px;">지금 매수 아님 · 반등확인선을 통과하는지 보는 종목</div>
      <div style="position:relative;height:92px;margin:0 8px;">
        <div style="position:absolute;left:5%;right:5%;top:39px;border-top:3px dashed #6f7782;"></div>
        <div style="position:absolute;left:{ps:.1f}%;top:22px;height:38px;border-left:3px solid #e53935;"></div>
        <div style="position:absolute;left:{pe:.1f}%;top:19px;height:44px;border-left:4px dashed #f6c344;"></div>
        <div style="position:absolute;left:{pc:.1f}%;top:27px;width:18px;height:18px;border-radius:50%;background:#ffffff;transform:translateX(-9px);box-shadow:0 0 0 4px #455a64;"></div>
        <div style="position:absolute;left:{pt:.1f}%;top:22px;height:38px;border-left:3px dashed #43a047;"></div>
        <div style="position:absolute;left:{ps:.1f}%;top:64px;transform:translateX(-50%);font-size:11px;color:#ef9a9a;">손절<br>{stop:,.0f}</div>
        <div style="position:absolute;left:{pe:.1f}%;top:0px;transform:translateX(-50%);font-size:11px;color:#ffd54f;font-weight:800;">반등확인선<br>{confirm:,.0f}</div>
        <div style="position:absolute;left:{pc:.1f}%;top:64px;transform:translateX(-50%);font-size:11px;color:#fff;font-weight:800;">현재<br>{cur:,.0f}</div>
        <div style="position:absolute;left:{pt:.1f}%;top:0px;transform:translateX(-50%);font-size:11px;color:#81c784;font-weight:800;">예상 +10%<br>{target:,.0f}</div>
      </div>
    </div>
    """

def pct_from(base,val):
    try:return (float(val)/float(base)-1)*100
    except:return np.nan

def price_pct(base,val):
    try:return f"{won(val)} ({pct_from(base,val):+.1f}%)"
    except:return "-"

if st.button("🔎 ONE 검색",type="primary",use_container_width=True,key="one_search_v2_main"):
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
    if status=="진입준비":
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
        <div class="hero-badge">{status}</div>
      </div>
      <div class="hero-line">{("가격은 왔지만 방향이 약해 관망합니다." if status=="관망" else ("반등확인선 아래라 재상승 확인이 먼저입니다." if status=="반등확인" else ("반등확인선에 근접했습니다. 최종 반등 조건을 기다립니다." if status=="진입준비" else "지금 매수 아님 · 반등확인선을 기다립니다.")))}{(" · 관망용 저점 후보" if mode=="WATCH" else "")}</div>
      <div class="small">현재가 {won(cur)} · 반등확인선 {won(desired)} · 확인선 대비 {gap:+.1f}%</div>
    </div>
    """,unsafe_allow_html=True)

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
    st.markdown(f"""
    <div class="card">
      <b>🕳️ 진바닥 → B 지지매물 → 상단저항</b><br>
      <span class="small">
      A <b>{won(stop)}</b> · {_tb.get('state','확인')} · 경과 {_tb.get('age','-')}거래일 · 저점계층 {_sw}일<br>
      B 지지매물 <b>{_bs.get('state','확인불가')}</b> · B주변 거래비중 {_bs.get('zone_share',0):.1f}% · 접촉 {_bs.get('touch_share',0):.1f}%<br>
      +10% 상단저항 <b>{_sup.get('state','확인불가')}</b> · 누적 {_sup.get('zone_share',0):.1f}% · 최대벽 {_wall}
      </span>
    </div>
    """,unsafe_allow_html=True)

    _gauge=trend_gauge_7(df)
    st.markdown(gauge_svg_7(_gauge),unsafe_allow_html=True)
    st.markdown(candidate_price_path(cur,stop,desired,target,status),unsafe_allow_html=True)
    st.markdown(flow_summary_html(candidate["stock"]),unsafe_allow_html=True)

    st.markdown('<div class="section-title">후보 가격</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("현재가",won(cur))
    c2.metric("반등확인선",won(desired),f"{(desired/cur-1)*100:+.1f}%")
    c3.metric("손절 진바닥 A",won(stop),f"{(stop/desired-1)*100:.1f}%")
    c4.metric("예상 목표(+10%)",won(target),"확인선 기준")

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
            projection=[{"label":"확인","v":desired},{"label":"+10%","v":target}],
            initial_bars=bars,
        ),
        height=640,
        scrolling=False,
    )
    st.caption("📱 모바일 차트는 위 버튼으로 확대·축소 · 반등확인선 통과 후 최종 조건 충족 시 강력추천 승격 · 실제 익절가는 실제 진입가 기준 +10%")

    if status=="진입준비":
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
        if not (1000<=cur<=50000):return None
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
        st.error(res.get("error","AI 미래발굴 실패"));return

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




# ---------------- V4 TIME MACHINE · CURRENT ENGINE DISCOVERY ----------------
TM_V4_SCHEMA="V4_ENTRY_SAME_EVENT_TM1"
TM_V4_RESULT_FILE=Path("data")/"v4_mtf_time_machine_v2_result.json"
TM_V4_UNIVERSE_FILE=Path("data")/"v4_mtf_time_machine_v2_universe.json"
TM_V4_DAILY_DIR=Path("data")/"tm_v4_v2_daily"
TM_V4_MIN_DIR=Path("data")/"tm_v4_v2_minute"

def _tm_json_write(path,obj):
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    except:pass

def _tm_json_read(path):
    try:
        if path.exists():
            x=json.loads(path.read_text(encoding="utf-8"))
            return x if isinstance(x,dict) else {}
    except:pass
    return {}


def _tm_full_universe():
    """현재 KIS 마스터의 메인 적격 종목 전체."""
    main,_,_,_=universe()
    rows=[{"code":str(z["code"]).zfill(6),"name":z["name"],"market":z.get("market","")} for z in main]
    return sorted(rows,key=lambda z:(z.get("market",""),z.get("code","")))

def _tm_fixed_universe(n=300):
    """현재 메인 유니버스에서 해시순 300종목을 최초 1회 고정. 이후 동일 종목 재사용."""
    try:
        old=_tm_json_read(TM_V4_UNIVERSE_FILE)
        rows=old.get("stocks") or []
        if old.get("schema")==TM_V4_SCHEMA and len(rows)==n:
            return rows
    except:pass
    main,_,_,_=universe()
    import hashlib as _hh
    rows=sorted(main,key=lambda z:_hh.sha256(str(z.get("code","")).encode()).hexdigest())[:n]
    keep=[{"code":str(z["code"]).zfill(6),"name":z["name"],"market":z.get("market","")} for z in rows]
    _tm_json_write(TM_V4_UNIVERSE_FILE,{"schema":TM_V4_SCHEMA,"n":n,"stocks":keep})
    return keep

def _tm_daily_cache_path(code):
    TM_V4_DAILY_DIR.mkdir(parents=True,exist_ok=True)
    return TM_V4_DAILY_DIR/f"{str(code).zfill(6)}.csv"

def _tm_fetch_history(code, start_dt, end_dt, token=None):
    """테스트 시작 전 충분한 이력 + 테스트 종료까지 KIS 일봉. 종목별 저장 후 재사용."""
    code=str(code).zfill(6)
    p=_tm_daily_cache_path(code)
    try:
        if p.exists():
            q=pd.read_csv(p,parse_dates=["date"]).sort_values("date")
            if (len(q)>=320 and pd.to_datetime(q["date"]).min()<=pd.Timestamp(start_dt)+pd.Timedelta(days=30)
                and pd.to_datetime(q["date"]).max()>=pd.Timestamp(end_dt)-pd.Timedelta(days=7)):
                return q.reset_index(drop=True)
    except:pass

    token=token or kis_access_token()
    if not token:return pd.DataFrame()
    rows=[];seen=set();cur_end=pd.Timestamp(end_dt).to_pydatetime()
    for _ in range(12):
        batch=_kis_fetch_window(code,pd.Timestamp(start_dt).to_pydatetime(),cur_end,token)
        if not batch:break
        for x in batch:
            try:
                dd=pd.Timestamp(x["date"]);k=dd.strftime("%Y%m%d")
                if k not in seen:
                    seen.add(k);rows.append(x)
            except:pass
        earliest=min(pd.Timestamp(x["date"]) for x in batch)
        if earliest<=pd.Timestamp(start_dt):break
        cur_end=(earliest-pd.Timedelta(days=1)).to_pydatetime()
        time.sleep(0.07)
    if not rows:return pd.DataFrame()
    q=pd.DataFrame(rows)
    q["date"]=pd.to_datetime(q["date"],errors="coerce")
    for c in ["open","high","low","close","volume"]:
        q[c]=pd.to_numeric(q[c],errors="coerce")
    q=q.dropna(subset=["date","open","high","low","close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    try:q.to_csv(p,index=False,encoding="utf-8-sig")
    except:pass
    return q

def _tm_minute_cache_path(code,date):
    TM_V4_MIN_DIR.mkdir(parents=True,exist_ok=True)
    return TM_V4_MIN_DIR/f"{str(code).zfill(6)}_{pd.Timestamp(date).strftime('%Y%m%d')}.csv"

def _tm_historical_minute(code, target_date, token=None):
    """KIS 주식일별분봉조회 [국내주식-213], TR FHKST03010230."""
    p=_tm_minute_cache_path(code,target_date)
    try:
        if p.exists():
            q=pd.read_csv(p,parse_dates=["date"])
            if len(q)>=20:return q.sort_values("date").reset_index(drop=True)
    except:pass
    try:
        token=token or kis_access_token()
        if not token:return pd.DataFrame()
        app_key,app_secret,_=kis_credentials()
        url=f"{kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
        headers={"authorization":f"Bearer {token}","appkey":app_key,"appsecret":app_secret,
                 "tr_id":"FHKST03010230","custtype":"P"}
        ds=pd.Timestamp(target_date).strftime("%Y%m%d")
        params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":str(code).zfill(6),
                "FID_INPUT_HOUR_1":"153000","FID_INPUT_DATE_1":ds,
                "FID_PW_DATA_INCU_YN":"Y","FID_FAKE_TICK_INCU_YN":""}
        r=requests.get(url,headers=headers,params=params,timeout=9)
        if r.status_code!=200:return pd.DataFrame()
        js=r.json()
        if str(js.get("rt_cd","0")) not in ("0",""):return pd.DataFrame()
        raw=js.get("output2") or []
        rows=[]
        for q in raw:
            try:
                t=str(q.get("stck_cntg_hour") or "")
                if len(t)<6:continue
                dt=pd.to_datetime(ds+t[:6],format="%Y%m%d%H%M%S",errors="coerce")
                if pd.isna(dt):continue
                rows.append({"date":dt,
                    "open":float(str(q.get("stck_oprc") or 0).replace(",","")),
                    "high":float(str(q.get("stck_hgpr") or 0).replace(",","")),
                    "low":float(str(q.get("stck_lwpr") or 0).replace(",","")),
                    "close":float(str(q.get("stck_prpr") or 0).replace(",","")),
                    "volume":float(str(q.get("cntg_vol") or 0).replace(",",""))})
            except:pass
        x=pd.DataFrame(rows)
        if x.empty:return x
        x=x.drop_duplicates("date",keep="last").sort_values("date").reset_index(drop=True)
        try:x.to_csv(p,index=False,encoding="utf-8-sig")
        except:pass
        return x
    except:return pd.DataFrame()

def _tm_liquid_at_date(hist):
    try:
        cur=float(hist.iloc[-1].close)
        if not (1000<=cur<=50000):return False
        v=hist.volume.astype(float).tail(20)
        if len(v)<15:return False
        return bool(float(v.median())>=50000 and float((hist.close.astype(float).tail(20)*v).median())>=500_000_000)
    except:return False

def _tm_next_row(df, signal_date):
    ds=pd.to_datetime(df["date"]).dt.normalize()
    d=pd.Timestamp(signal_date).normalize()
    z=df[ds>d]
    return None if z.empty else z.iloc[0]

def _tm_daily_sim(df, signal_date, stop, max_days=60):
    """D일 종가 신호 → D+1 시가 진입. 같은 날 손절/목표 동시 터치 시 손절 우선."""
    z=_tm_next_row(df,signal_date)
    if z is None:return None
    entry=float(z.open);stop=float(stop)
    if entry<=0 or stop<=0:return None
    target=krx_ceil_price(entry*1.10)
    ds=pd.to_datetime(df["date"]).dt.normalize()
    td=pd.Timestamp(z["date"]).normalize()
    fut=df[ds>=td].head(max_days)
    last=entry
    for k,(_,r) in enumerate(fut.iterrows()):
        last=float(r.close)
        if k==0 and entry<=stop:
            return {"outcome":"STOP","days":0,"return_pct":(entry/entry-1)*100,"entry":entry}
        if float(r.low)<stop:
            return {"outcome":"STOP","days":k,"return_pct":(stop/entry-1)*100,"entry":entry}
        if float(r.high)>=target:
            return {"outcome":"WIN","days":k,"return_pct":10.0,"entry":entry}
    return {"outcome":"TIMEOUT","days":len(fut),"return_pct":(last/entry-1)*100,"entry":entry}

def _tm_minute_entry(raw, confirm_line):
    if raw is None or len(raw)<12:return None
    try:
        x=raw.copy().set_index("date")
        m5=x.resample("5min").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna(subset=["close"]).reset_index()
        if len(m5)<5:return None
        c=m5.close.astype(float);v=m5.volume.astype(float);ma3=c.rolling(3).mean()
        for i in range(3,len(m5)):
            price=float(c.iloc[i]); vr=float(v.iloc[i]/max(float(v.iloc[max(0,i-3):i].mean()),1.0))
            checks=[price>=float(confirm_line),price>=float(c.iloc[i-1]),price>=float(ma3.iloc[i]),
                    float(ma3.iloc[i])>=float(ma3.iloc[i-1]),
                    price>=float(m5.iloc[i-1].high) or vr>=1.20]
            score=sum(bool(q) for q in checks)
            if price>=float(confirm_line) and score>=4:
                return {"time":pd.Timestamp(m5.iloc[i]["date"]),"price":price,"score":score,"volume_ratio":vr}
    except:pass
    return None

def _tm_minute_sim(df, raw, entry_obj, stop, max_days=60):
    if not entry_obj:return None
    entry=float(entry_obj["price"]);stop=float(stop);target=krx_ceil_price(entry*1.10)
    et=pd.Timestamp(entry_obj["time"])
    try:
        rem=raw[pd.to_datetime(raw["date"])>et]
        for _,r in rem.iterrows():
            if float(r.low)<stop:return {"outcome":"STOP","days":0,"return_pct":(stop/entry-1)*100,"entry":entry}
            if float(r.high)>=target:return {"outcome":"WIN","days":0,"return_pct":10.0,"entry":entry}
    except:pass
    ds=pd.to_datetime(df["date"]).dt.normalize();td=et.normalize()
    fut=df[ds>td].head(max_days);last=entry
    for k,(_,r) in enumerate(fut.iterrows(),1):
        last=float(r.close)
        if float(r.low)<stop:return {"outcome":"STOP","days":k,"return_pct":(stop/entry-1)*100,"entry":entry}
        if float(r.high)>=target:return {"outcome":"WIN","days":k,"return_pct":10.0,"entry":entry}
    return {"outcome":"TIMEOUT","days":len(fut),"return_pct":(last/entry-1)*100,"entry":entry}

def _tm_summary(records):
    n=len(records);vc=Counter(x["outcome"] for x in records)
    return {"n":n,"win":vc.get("WIN",0),"stop":vc.get("STOP",0),"timeout":vc.get("TIMEOUT",0),
            "win_rate":round(vc.get("WIN",0)/n*100,1) if n else 0,
            "stop_rate":round(vc.get("STOP",0)/n*100,1) if n else 0,
            "timeout_rate":round(vc.get("TIMEOUT",0)/n*100,1) if n else 0,
            "avg_return":round(sum(float(x["return_pct"]) for x in records)/n,2) if n else 0,
            "avg_days":round(sum(int(x["days"]) for x in records)/n,1) if n else 0}


NEW_ANGLE_SCHEMA="SPACE_EFF_FRESH_BLIND1"
NEW_ANGLE_RESULT_FILE=Path("data")/"v4_new_angle_lab_result.json"

def _new_angle_features(hist, sig):
    """
    모두 '신호 당일 종가까지'의 데이터만 사용한다.
    1) space_score: 현재가~+10% 사이 과거 매물 혼잡도가 낮을수록 높음.
    2) rebound_eff: B 이후 가격이 얼마나 직선적으로 올라왔는지.
    3) freshness_days: B 형성 후 신호까지 걸린 거래일 수.
    """
    try:
        h=hist.tail(250).copy().reset_index(drop=True)
        cur=float(h.iloc[-1].close)
        if cur<=0:return None

        # --- 1. 상단 매물공간 ---
        # 현재 봉은 제외. 과거 120거래일에서 현재가~+10% 구간의 거래량/가격접촉 밀도를 본다.
        look=h.iloc[:-1].tail(120).copy()
        lo=cur*1.01
        hi=cur*1.10
        if len(look)<40:return None
        typ=(look.high.astype(float)+look.low.astype(float)+look.close.astype(float))/3.0
        vol=look.volume.astype(float).clip(lower=0)
        total_vol=max(float(vol.sum()),1.0)
        vol_share=float(vol[(typ>=lo)&(typ<=hi)].sum()/total_vol)
        touch=((look.high.astype(float)>=lo)&(look.low.astype(float)<=hi))
        touch_share=float(touch.mean()) if len(touch) else 0.0
        congestion=max(0.0,min(1.0,0.70*vol_share+0.30*touch_share))
        _supply=overhead_supply_profile(h,cur,10.0,120,18)
        # 신규 검증실도 생산 엔진과 같은 상단 매물 계산을 우선 사용.
        space_score=max(0.0,100.0-float(_supply.get("zone_share",0))*2.2) if _supply.get("state")!="확인불가" else (1.0-congestion)*100.0

        # 현재가 위 첫 의미있는 과거 고점까지의 거리도 참고값으로 저장
        ph=[]
        highs=look.high.astype(float).to_numpy()
        for j in range(2,len(highs)-2):
            if highs[j]>=max(highs[j-2:j+3]) and highs[j]>cur:
                ph.append(highs[j])
        nearest_res=min(ph) if ph else cur*1.12
        resistance_gap=max(0.0,(nearest_res/cur-1)*100)

        # --- 2. 반등 효율 ---
        bdate=pd.Timestamp(sig.get("B",{}).get("date")).normalize()
        hd=pd.to_datetime(h["date"]).dt.normalize()
        hits=h.index[hd==bdate].tolist()
        if not hits:return None
        bi=int(hits[-1])
        if bi<0 or bi>=len(h)-1:return None
        seg=h.iloc[bi:].close.astype(float).to_numpy()
        if len(seg)<3:return None
        path=float(np.abs(np.diff(seg)).sum())
        net=max(0.0,float(seg[-1]-seg[0]))
        rebound_eff=0.0 if path<=1e-9 else max(0.0,min(1.0,net/path))

        # --- 3. 신호 신선도 ---
        freshness_days=int((len(h)-1)-bi)

        return {
            "space_score":round(space_score,3),
            "overhead_congestion":round(congestion,5),
            "resistance_gap_pct":round(resistance_gap,3),
            "rebound_eff":round(rebound_eff,5),
            "freshness_days":freshness_days,
        }
    except:
        return None

def _lab_summary(rows):
    n=len(rows)
    vc=Counter(str(x.get("outcome","")) for x in rows)
    if not n:
        return {"n":0,"win_rate":0.0,"stop_rate":0.0,"timeout_rate":0.0,
                "avg_return":0.0,"avg_days":0.0}
    return {
        "n":n,
        "win_rate":round(vc.get("WIN",0)/n*100,1),
        "stop_rate":round(vc.get("STOP",0)/n*100,1),
        "timeout_rate":round(vc.get("TIMEOUT",0)/n*100,1),
        "avg_return":round(sum(float(x.get("return_pct",0)) for x in rows)/n,2),
        "avg_days":round(sum(int(x.get("days",0)) for x in rows)/n,1),
    }

def _lab_apply(rows, rule):
    out=[]
    for x in rows:
        if "space_min" in rule and float(x["space_score"])<float(rule["space_min"]):continue
        if "eff_min" in rule and float(x["rebound_eff"])<float(rule["eff_min"]):continue
        if "fresh_max" in rule and int(x["freshness_days"])>int(rule["fresh_max"]):continue
        out.append(x)
    return out

def _uniq_vals(vals, ndigits=4):
    z=[]
    for v in vals:
        try:
            q=round(float(v),ndigits)
            if q not in z:z.append(q)
        except:pass
    return z

def _new_angle_select_rules(train_rows, blind_rows):
    """
    임계값은 TRAIN 70%에서만 고른다.
    마지막 30% BLIND 성적은 선택 과정에서 보지 않는다.
    너무 적은 신호를 골라 승률만 높이는 것을 막기 위해 표본 유지율 >=45% 강제.
    """
    if len(train_rows)<20:
        return {"ok":False,"error":"TRAIN 표본 부족"}

    import numpy as _np
    base_train=_lab_summary(train_rows)
    base_blind=_lab_summary(blind_rows)
    min_n=max(12,int(len(train_rows)*0.45))

    space=[float(x["space_score"]) for x in train_rows]
    eff=[float(x["rebound_eff"]) for x in train_rows]
    fresh=[float(x["freshness_days"]) for x in train_rows]

    # 엄격도 후보는 TRAIN 분포의 분위수만 사용
    qset=[0.30,0.40,0.50,0.60,0.70]
    space_thr=_uniq_vals([_np.quantile(space,q) for q in qset],3)
    eff_thr=_uniq_vals([_np.quantile(eff,q) for q in qset],4)
    fresh_thr=sorted(set(int(round(_np.quantile(fresh,q))) for q in qset))

    candidates=[]
    def add_rule(label,rule):
        tr=_lab_apply(train_rows,rule)
        if len(tr)<min_n:return
        sm=_lab_summary(tr)
        retain=len(tr)/len(train_rows)*100
        # 승률 + 손절감소가 중심. 표본 축소는 작은 페널티.
        objective=(sm["win_rate"]-base_train["win_rate"])*1.0 + \
                  (base_train["stop_rate"]-sm["stop_rate"])*0.45 - \
                  max(0,60-retain)*0.05
        candidates.append({"label":label,"rule":rule,"train":sm,
                           "train_retain":round(retain,1),"objective":round(objective,3)})

    for a in space_thr:add_rule("상단공간",{"space_min":a})
    for b in eff_thr:add_rule("반등효율",{"eff_min":b})
    for c in fresh_thr:add_rule("신선도",{"fresh_max":c})

    # 2개 조합
    for a in space_thr:
        for b in eff_thr:add_rule("상단공간+반등효율",{"space_min":a,"eff_min":b})
    for a in space_thr:
        for c in fresh_thr:add_rule("상단공간+신선도",{"space_min":a,"fresh_max":c})
    for b in eff_thr:
        for c in fresh_thr:add_rule("반등효율+신선도",{"eff_min":b,"fresh_max":c})

    # 3개 조합
    for a in space_thr:
        for b in eff_thr:
            for c in fresh_thr:
                add_rule("3종 결합",{"space_min":a,"eff_min":b,"fresh_max":c})

    if not candidates:
        return {"ok":False,"error":"유효 규칙 없음"}

    candidates.sort(key=lambda x:(x["objective"],x["train"]["win_rate"],x["train_retain"]),reverse=True)

    # 각 단일개념의 최고 TRAIN 규칙 + 전체 최고 조합
    picked=[]
    for prefix in ["상단공간","반등효율","신선도"]:
        arr=[x for x in candidates if x["label"]==prefix]
        if arr:picked.append(arr[0])
    best=candidates[0]

    def attach_blind(x):
        z=dict(x)
        br=_lab_apply(blind_rows,x["rule"])
        z["blind"]=_lab_summary(br)
        z["blind_retain"]=round(len(br)/len(blind_rows)*100,1) if blind_rows else 0
        return z

    return {
        "ok":True,
        "base_train":base_train,
        "base_blind":base_blind,
        "single_best":[attach_blind(x) for x in picked],
        "best_combo":attach_blind(best),
        "min_train_n":min_n,
    }

def _rule_text(rule):
    bits=[]
    if "space_min" in rule:bits.append(f'상단공간≥{float(rule["space_min"]):.1f}')
    if "eff_min" in rule:bits.append(f'반등효율≥{float(rule["eff_min"]):.2f}')
    if "fresh_max" in rule:bits.append(f'B후≤{int(rule["fresh_max"])}일')
    return " · ".join(bits) if bits else "기준없음"

def run_new_angle_lab(nstocks=300):
    token=kis_access_token() if kis_ready() else ""
    if not token:return {"ok":False,"error":"KIS 인증 필요"}

    today=pd.Timestamp(now_kst().date())
    test_end=today-pd.Timedelta(days=1)
    test_start=test_end-pd.Timedelta(days=330)
    history_start=test_start-pd.Timedelta(days=430)

    stocks=_tm_fixed_universe(nstocks)
    records=[]
    p=st.progress(0,text="신규 관점 검증 · 상단공간/반등효율/신선도 계산 중...")

    for si,stock in enumerate(stocks,1):
        p.progress(si/max(len(stocks),1),text=f"{si}/{len(stocks)} · {stock['name']} · 과거 V4 신호 재생")
        df=_tm_fetch_history(stock["code"],history_start,test_end,token)
        if df is None or len(df)<180:continue
        dates=pd.to_datetime(df["date"]).dt.normalize()
        idxs=[i for i,d in enumerate(dates) if d>=test_start and d<=test_end and i>=160 and i<len(df)-1]

        for i in idxs:
            hist=df.iloc[:i+1].copy().reset_index(drop=True)
            if not _tm_liquid_at_date(hist):continue
            bt=big_trend_gate(hist)
            if not bt.get("ok",False):continue
            sig=_live_ab_signal(hist)
            if not sig:continue
            mtf=multi_timeframe_trend(hist)
            if not mtf.get("strong_ok",False):continue

            signal_date=pd.Timestamp(hist.iloc[-1]["date"]).normalize()
            feat=_new_angle_features(hist,sig)
            if not feat:continue
            sim=_tm_daily_sim(df,signal_date,float(sig["A"]["low"]),60)
            if not sim:continue

            records.append({
                "code":stock["code"],"name":stock["name"],
                "signal_date":str(signal_date.date()),
                "outcome":sim["outcome"],"return_pct":sim["return_pct"],"days":sim["days"],
                "space_score":feat["space_score"],
                "overhead_congestion":feat["overhead_congestion"],
                "resistance_gap_pct":feat["resistance_gap_pct"],
                "rebound_eff":feat["rebound_eff"],
                "freshness_days":feat["freshness_days"],
                "month":mtf["monthly"]["state"],"week":mtf["weekly"]["state"],
            })
    p.empty()

    records=sorted(records,key=lambda x:(x["signal_date"],x["code"]))
    if len(records)<25:
        result={"ok":False,"error":f"MTF 신호 표본 부족 · {len(records)}건","records":records}
        _tm_json_write(NEW_ANGLE_RESULT_FILE,result)
        return result

    # 날짜 순서 70/30. 같은 날짜가 양쪽으로 쪼개지지 않도록 split date 사용.
    dates_sorted=sorted(set(x["signal_date"] for x in records))
    cut_idx=max(1,min(len(dates_sorted)-1,int(len(dates_sorted)*0.70)))
    cut_date=dates_sorted[cut_idx]
    train=[x for x in records if x["signal_date"]<cut_date]
    blind=[x for x in records if x["signal_date"]>=cut_date]
    sel=_new_angle_select_rules(train,blind)

    result={
        "ok":bool(sel.get("ok")),
        "schema":NEW_ANGLE_SCHEMA,
        "created_at":now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks":len(stocks),
        "test_start":str(test_start.date()),"test_end":str(test_end.date()),
        "split_date":cut_date,
        "all":_lab_summary(records),
        "train_n":len(train),"blind_n":len(blind),
        "selection":sel,
        "records":records,
        "note":"생산 ONE 로직에는 아직 미적용. TRAIN 70%에서 임계값 선택 후 마지막 30% BLIND로 확인.",
    }
    _tm_json_write(NEW_ANGLE_RESULT_FILE,result)
    return result

def _render_new_angle_lab():
    st.markdown('<div class="section-title">🧪 신규 관점 검증실</div>',unsafe_allow_html=True)
    st.caption("상단 매물공간 · 반등 효율 · 신호 신선도 · 생산 ONE에는 아직 미적용 · 시간순 70% TRAIN / 30% BLIND")
    res=_tm_json_read(NEW_ANGLE_RESULT_FILE)

    if res.get("ok") and res.get("schema")==NEW_ANGLE_SCHEMA:
        sel=res.get("selection",{})
        base_tr=sel.get("base_train",{})
        base_bl=sel.get("base_blind",{})
        st.markdown(f"**검증기간 {res.get('test_start')} ~ {res.get('test_end')} · MTF 신호 {res.get('all',{}).get('n',0)}건 · BLIND 시작 {res.get('split_date')}**")

        rows=[{
            "규칙":"기존 월/주봉 기준",
            "조건":"추가필터 없음",
            "TRAIN 건수":base_tr.get("n",0),
            "TRAIN +10%":f'{base_tr.get("win_rate",0):.1f}%',
            "BLIND 건수":base_bl.get("n",0),
            "BLIND +10%":f'{base_bl.get("win_rate",0):.1f}%',
            "BLIND A손절":f'{base_bl.get("stop_rate",0):.1f}%',
            "BLIND 평균":f'{base_bl.get("avg_return",0):+.2f}%',
        }]
        for x in sel.get("single_best",[]):
            b=x.get("blind",{})
            rows.append({
                "규칙":x.get("label",""),
                "조건":_rule_text(x.get("rule",{})),
                "TRAIN 건수":x.get("train",{}).get("n",0),
                "TRAIN +10%":f'{x.get("train",{}).get("win_rate",0):.1f}%',
                "BLIND 건수":b.get("n",0),
                "BLIND +10%":f'{b.get("win_rate",0):.1f}%',
                "BLIND A손절":f'{b.get("stop_rate",0):.1f}%',
                "BLIND 평균":f'{b.get("avg_return",0):+.2f}%',
            })
        best=sel.get("best_combo",{})
        if best:
            b=best.get("blind",{})
            rows.append({
                "규칙":"🏆 TRAIN 선택 최우수",
                "조건":_rule_text(best.get("rule",{})),
                "TRAIN 건수":best.get("train",{}).get("n",0),
                "TRAIN +10%":f'{best.get("train",{}).get("win_rate",0):.1f}%',
                "BLIND 건수":b.get("n",0),
                "BLIND +10%":f'{b.get("win_rate",0):.1f}%',
                "BLIND A손절":f'{b.get("stop_rate",0):.1f}%',
                "BLIND 평균":f'{b.get("avg_return",0):+.2f}%',
            })
        st.dataframe(rows,use_container_width=True,hide_index=True)

        if best:
            b=best.get("blind",{})
            delta=float(b.get("win_rate",0))-float(base_bl.get("win_rate",0))
            retain=float(best.get("blind_retain",0))
            if b.get("n",0)>=8 and delta>=3 and retain>=40:
                st.success(f"BLIND 개선 확인 · 기존 {base_bl.get('win_rate',0):.1f}% → {b.get('win_rate',0):.1f}% ({delta:+.1f}%p) · 표본유지 {retain:.1f}%")
            elif b.get("n",0)<8:
                st.warning("BLIND 표본이 너무 작습니다. 승률이 높아도 채택하지 않습니다.")
            else:
                st.info(f"최우수 조합 BLIND 변화 {delta:+.1f}%p · 아직 생산엔진 채택 보류")

        with st.expander("신호별 특징 상세"):
            st.dataframe(res.get("records",[]),use_container_width=True,hide_index=True)

    elif res:
        st.warning(res.get("error","아직 유효한 결과가 없습니다."))

    if st.button("🧪 신규 관점 타임머신 실행",use_container_width=True,key="new_angle_lab_run"):
        with st.spinner("300종목 과거 신호에서 상단공간·반등효율·신선도를 계산하고 BLIND 검증 중..."):
            rr=run_new_angle_lab(300)
        if rr.get("ok"):
            best=rr.get("selection",{}).get("best_combo",{})
            bb=best.get("blind",{}) if best else {}
            st.success(f"완료 · BLIND {bb.get('n',0)}건 · +10% {bb.get('win_rate',0):.1f}% · A손절 {bb.get('stop_rate',0):.1f}%")
            st.rerun()
        else:
            st.error(rr.get("error","신규 관점 검증 실패"))



def _tm_monthly_rate(n, start_date, end_date):
    try:
        a=pd.Timestamp(start_date); b=pd.Timestamp(end_date)
        months=max(1,(b.year-a.year)*12+(b.month-a.month)+1)
        return round(float(n)/months,1)
    except:return 0.0


def _tm_monthly_rate(n, start_date, end_date):
    try:
        a=pd.Timestamp(start_date); b=pd.Timestamp(end_date)
        months=max(1,(b.year-a.year)*12+(b.month-a.month)+1)
        return round(float(n)/months,2)
    except:return 0.0

def _tm_filter_below_b(rows, metric, threshold):
    return [x for x in rows if float(x.get(metric,0))>=float(threshold)]

def _tm_pick_train_threshold(train_rows, blind_rows, metric, label):
    if len(train_rows)<15:
        return {"label":label,"ok":False,"error":"TRAIN 표본 부족"}
    vals=sorted(float(x.get(metric,0)) for x in train_rows)
    if not vals:
        return {"label":label,"ok":False,"error":"값 없음"}

    qset=[0.20,0.30,0.40,0.50,0.60]
    thrs=[]
    for q in qset:
        j=min(len(vals)-1,max(0,int(round((len(vals)-1)*q))))
        v=vals[j]
        if v not in thrs: thrs.append(v)

    base=_tm_summary(train_rows)
    min_n=max(10,int(len(train_rows)*0.55))
    cand=[]
    for t in thrs:
        rr=_tm_filter_below_b(train_rows,metric,t)
        if len(rr)<min_n: continue
        sm=_tm_summary(rr)
        retain=len(rr)/len(train_rows)*100.0
        objective=(sm.get("win_rate",0)-base.get("win_rate",0)) + \
                  (base.get("stop_rate",0)-sm.get("stop_rate",0))*0.5 - \
                  max(0,70-retain)*0.04
        cand.append((objective,t,sm,retain))

    if not cand:
        return {"label":label,"ok":False,"error":"유효 임계값 없음"}

    cand.sort(key=lambda x:(x[0],x[2].get("win_rate",0),x[3]),reverse=True)
    _,t,tr,retain=cand[0]
    br=_tm_filter_below_b(blind_rows,metric,t)
    return {
        "label":label,"ok":True,"metric":metric,"threshold":round(float(t),4),
        "train":tr,"blind":_tm_summary(br),
        "train_retain":round(retain,1),
        "blind_retain":round(len(br)/len(blind_rows)*100,1) if blind_rows else 0.0,
    }


def _tm_monthly_rate(n, start_date, end_date):
    try:
        a=pd.Timestamp(start_date); b=pd.Timestamp(end_date)
        months=max(1,(b.year-a.year)*12+(b.month-a.month)+1)
        return round(float(n)/months,2)
    except:return 0.0


def _speed_features(hist, sig):
    """
    신호 당일 종가까지의 정보만 사용한다.
    - b_days: B 저점 이후 신호까지 거래일 수 (짧을수록 좋음)
    - velocity: B 저점 → 신호 종가까지 하루 평균 상승률
    - efficiency: 실제 가격 경로가 얼마나 직선적으로 상승했는지 0~1
    - value_accel: 최근 3일 거래대금 / 직전 20일 거래대금
    """
    try:
        h=hist.tail(300).copy().reset_index(drop=True)
        n=len(h)
        bi=int(sig.get("B",{}).get("i",-1))
        if bi<0 or bi>=n-1:return None

        B=float(sig["B"]["low"])
        cur=float(h.iloc[-1].close)
        b_days=max(1,(n-1)-bi)
        velocity=((cur/B)-1.0)*100.0/b_days

        closes=h.iloc[bi:].close.astype(float).to_numpy()
        if len(closes)<2:return None
        path=abs(float(closes[0])-B)
        if len(closes)>1:
            path += float(np.abs(np.diff(closes)).sum())
        net=max(0.0,cur-B)
        efficiency=0.0 if path<=1e-9 else max(0.0,min(1.0,net/path))

        values=(h.close.astype(float)*h.volume.astype(float)).clip(lower=0)
        recent=values.tail(3)
        prior=values.iloc[max(0,n-23):max(0,n-3)]
        if len(prior)<10:
            prior=values.iloc[:-3]
        recent_med=float(recent.median()) if len(recent) else 0.0
        prior_med=float(prior.median()) if len(prior) else 0.0
        value_accel=recent_med/max(prior_med,1.0)

        return {
            "b_days":int(b_days),
            "velocity":round(float(velocity),5),
            "efficiency":round(float(efficiency),5),
            "value_accel":round(float(value_accel),5),
        }
    except:
        return None

def _speed_summary(rows, horizon="15"):
    n=len(rows)
    if not n:
        return {"n":0,"win_rate":0.0,"stop_rate":0.0,"timeout_rate":0.0,
                "avg_return":0.0,"avg_days":0.0}
    ok=f"outcome{horizon}"
    rk=f"return{horizon}"
    dk=f"days{horizon}"
    vc=Counter(str(x.get(ok,"")) for x in rows)
    return {
        "n":n,
        "win_rate":round(vc.get("WIN",0)/n*100,1),
        "stop_rate":round(vc.get("STOP",0)/n*100,1),
        "timeout_rate":round(vc.get("TIMEOUT",0)/n*100,1),
        "avg_return":round(sum(float(x.get(rk,0)) for x in rows)/n,2),
        "avg_days":round(sum(int(x.get(dk,0)) for x in rows)/n,1),
    }

def _speed_percentile(ref, value, higher_better=True):
    try:
        vals=sorted(float(v) for v in ref)
        if not vals:return 50.0
        import bisect
        p=bisect.bisect_right(vals,float(value))/len(vals)*100.0
        return p if higher_better else 100.0-p
    except:
        return 50.0

def _speed_build_scores(train_rows, rows):
    """
    점수 가중치는 미리 고정한다. BLIND 결과를 보고 조정하지 않는다.
    35% B 신선도 + 30% 상승속도 + 20% 직선성 + 15% 거래대금 가속.
    """
    refs={
        "b_days":[x["b_days"] for x in train_rows],
        "velocity":[x["velocity"] for x in train_rows],
        "efficiency":[x["efficiency"] for x in train_rows],
        "value_accel":[x["value_accel"] for x in train_rows],
    }
    for x in rows:
        fresh=_speed_percentile(refs["b_days"],x["b_days"],False)
        vel=_speed_percentile(refs["velocity"],x["velocity"],True)
        eff=_speed_percentile(refs["efficiency"],x["efficiency"],True)
        val=_speed_percentile(refs["value_accel"],x["value_accel"],True)
        score=0.35*fresh+0.30*vel+0.20*eff+0.15*val
        x["speed_score"]=round(float(score),2)
        x["fresh_score"]=round(float(fresh),1)
        x["velocity_score"]=round(float(vel),1)
        x["efficiency_score"]=round(float(eff),1)
        x["value_score"]=round(float(val),1)
    return rows

def _speed_filter(rows, threshold):
    return [x for x in rows if float(x.get("speed_score",0))>=float(threshold)]

def _speed_monthly_rate(rows, start_date, end_date):
    try:
        a=pd.Timestamp(start_date); b=pd.Timestamp(end_date)
        months=max(1,(b.year-a.year)*12+(b.month-a.month)+1)
        return round(len(rows)/months,2)
    except:return 0.0

def _speed_select_threshold(train_rows, blind_rows):
    """
    TRAIN에서만 속도점수 컷을 고른다.
    전체 BASE 월 6.1건 수준을 고려해 TRAIN 표본 65% 이상 유지.
    목표함수는 15거래일 내 +10% 성공률을 최우선으로 한다.
    """
    if len(train_rows)<25:
        return {"ok":False,"error":"TRAIN 표본 부족"}

    vals=sorted(float(x["speed_score"]) for x in train_rows)
    base15=_speed_summary(train_rows,"15")
    base60=_speed_summary(train_rows,"60")
    min_n=max(15,int(len(train_rows)*0.65))

    # 낮은 15~35%만 제거 → 신호 수를 지나치게 줄이지 않는다.
    qset=[0.15,0.20,0.25,0.30,0.35]
    candidates=[]
    for q in qset:
        j=min(len(vals)-1,max(0,int(round((len(vals)-1)*q))))
        t=vals[j]
        tr=_speed_filter(train_rows,t)
        if len(tr)<min_n:continue
        sm15=_speed_summary(tr,"15")
        sm60=_speed_summary(tr,"60")
        retain=len(tr)/len(train_rows)*100.0
        # 15일 성공률 + A손절 감소 + 15일 평균수익을 함께 본다.
        objective=(
            (sm15["win_rate"]-base15["win_rate"])*1.0 +
            (base15["stop_rate"]-sm15["stop_rate"])*0.45 +
            (sm15["avg_return"]-base15["avg_return"])*0.35 -
            max(0.0,70.0-retain)*0.08
        )
        candidates.append({
            "threshold":round(float(t),2),
            "train15":sm15,"train60":sm60,
            "train_retain":round(retain,1),
            "objective":round(float(objective),3)
        })

    if not candidates:
        return {"ok":False,"error":"유효한 속도점수 기준 없음"}

    candidates.sort(
        key=lambda x:(x["objective"],x["train15"]["win_rate"],x["train15"]["avg_return"],x["train_retain"]),
        reverse=True
    )
    best=candidates[0]
    blind_sel=_speed_filter(blind_rows,best["threshold"])
    best["blind15"]=_speed_summary(blind_sel,"15")
    best["blind60"]=_speed_summary(blind_sel,"60")
    best["blind_retain"]=round(len(blind_sel)/len(blind_rows)*100,1) if blind_rows else 0.0
    return {"ok":True,"best":best,"candidates":candidates}





def _event_common_candle_ok(h, j):
    """
    BASE의 신호 캔들 품질만 공통으로 유지.
    진입선(T3/T5/T7/BRK) 외 조건은 모든 규칙에서 동일하다.
    """
    try:
        if j<=0:return False
        cur=float(h.iloc[j].close)
        op=float(h.iloc[j].open)
        hi=float(h.iloc[j].high)
        lo=float(h.iloc[j].low)
        rng=max(hi-lo,1e-9)
        body=abs(cur-op)/rng*100.0
        if body<40.0:return False
        if cur<=float(h.iloc[j-1].close):return False
        tail=h.close.astype(float).iloc[max(0,j-4):j+1].to_numpy()
        rises=sum(tail[k]>tail[k-1] for k in range(1,len(tail)))
        return rises>=1
    except:
        return False

def _find_new_ab_event(hist):
    """
    '오늘' 새로 확인된 B 피벗만 사건으로 만든다.
    right=3이므로 오늘 인덱스 n-1에서 새로 확정되는 B는 n-4 하나뿐이다.
    이때 A와 B를 고정하여 이후 T3/T5/T7/BRK 모두 같은 사건을 추적한다.
    """
    try:
        h=hist.tail(300).copy().reset_index(drop=True)
        n=len(h)
        if n<140:return None

        A0=true_bottom_anchor(h)
        if not A0:return None
        ai=int(A0["i"]); A=float(A0["low"])
        if int(A0.get("age",999))>90:return None

        bi=n-4
        if bi<=ai:return None

        piv=_live_pivot_lows(h,3,3)
        if bi not in piv:return None

        if not (8<=bi-ai<=150):return None
        B=float(h.iloc[bi].low)
        if B<A:return None

        mid=h.iloc[ai+1:bi]
        if mid.empty:return None
        peak=float(mid.high.astype(float).max())
        rebound=(peak/A-1.0)*100.0
        if rebound<5.0:return None

        bdist=(B/A-1.0)*100.0
        if bdist<0.0 or bdist>18.0:return None

        # B 확인일까지 A가 깨지지 않았어야 한다.
        after_b=h.iloc[bi+1:]
        if len(after_b) and float(after_b.low.astype(float).min())<A:return None

        # 큰 방향은 사건 생성 시점에서 한 번만 고정한다.
        bt=big_trend_gate(h)
        if not bt.get("ok",False):return None

        return {
            "A":{**A0},
            "B":{"i":bi,"date":h.iloc[bi].date,"low":B},
            "event_date":h.iloc[-1].date,
            "rebound_pct":rebound,
            "b_above_a_pct":bdist,
            "bigtrend_state":bt.get("state",""),
            "bigtrend_score":bt.get("score",0),
        }
    except:
        return None

def _event_rule_first_hits(df, event):
    """
    동일한 A/B 사건 하나를 앞으로 한 번만 추적한다.

    T3/T5/T7:
      B 확인 이후 처음 해당 가격을 종가로 넘는 날.
    BRK:
      B 확인 이후 처음 직전 5거래일 고가를 종가로 돌파하는 날.

    A가 먼저 깨지면 그 이후 규칙은 진입 없음.
    A는 사건 생성 당시의 동일 A를 끝까지 사용한다.
    """
    try:
        ds=pd.to_datetime(df["date"]).dt.normalize()
        event_date=pd.Timestamp(event["event_date"]).normalize()
        b_date=pd.Timestamp(event["B"]["date"]).normalize()
        a_date=pd.Timestamp(event["A"]["date"]).normalize()

        ei_list=df.index[ds==event_date].tolist()
        bi_list=df.index[ds==b_date].tolist()
        ai_list=df.index[ds==a_date].tolist()
        if not ei_list or not bi_list or not ai_list:return None

        ei=int(ei_list[-1]); bi=int(bi_list[-1]); ai=int(ai_list[-1])
        A=float(event["A"]["low"]); B=float(event["B"]["low"])

        thresholds={
            "T3":krx_ceil_price(B*1.03),
            "T5":krx_ceil_price(B*1.05),
            "T7":krx_ceil_price(B*1.07),
        }
        result={
            "T3":{"hit":False,"reason":"미도달"},
            "T5":{"hit":False,"reason":"미도달"},
            "T7":{"hit":False,"reason":"미도달"},
            "BRK":{"hit":False,"reason":"미도달"},
        }

        # "첫 돌파"를 정확히 보려면 각 규칙별로 최초 가격도달 여부를 따로 기억.
        crossed={"T3":False,"T5":False,"T7":False,"BRK":False}

        # 현재 BASE의 유효기간을 그대로 유지:
        # A는 최대 90일, B는 최대 55일 안에서 진입 신호를 기다린다.
        last=min(len(df)-2, bi+55, ai+90)  # D+1 시가가 필요하므로 len-2
        if last<ei:return result

        for j in range(ei,last+1):
            # 진입 신호보다 A 이탈이 먼저면 사건 종료.
            if float(df.iloc[j].low)<A:
                for key in result:
                    if not result[key]["hit"] and not crossed[key]:
                        result[key]["reason"]="A선이탈"
                break

            close=float(df.iloc[j].close)

            # T3/T5/T7 최초 종가 도달
            for key in ("T3","T5","T7"):
                if crossed[key]:continue
                if close>=float(thresholds[key]):
                    crossed[key]=True
                    if _event_common_candle_ok(df,j):
                        result[key]={
                            "hit":True,"reason":"첫돌파",
                            "signal_index":j,
                            "signal_date":df.iloc[j]["date"],
                            "signal_close":close,
                            "line":float(thresholds[key]),
                        }
                    else:
                        # '첫 종가 돌파'가 BASE 공통 캔들조건을 못 만족하면
                        # 뒤늦은 재돌파를 새 신호로 만들지 않는다.
                        result[key]["reason"]="첫돌파_캔들미달"

            # BRK: 오늘 이전 5거래일의 고가 최대를 종가로 최초 돌파
            if not crossed["BRK"] and j>=max(ei,5):
                prev5=df.iloc[j-5:j]
                if len(prev5)==5:
                    line=float(prev5.high.astype(float).max())
                    if close>line:
                        crossed["BRK"]=True
                        if _event_common_candle_ok(df,j):
                            result["BRK"]={
                                "hit":True,"reason":"첫돌파",
                                "signal_index":j,
                                "signal_date":df.iloc[j]["date"],
                                "signal_close":close,
                                "line":line,
                            }
                        else:
                            result["BRK"]["reason"]="첫돌파_캔들미달"

        return result
    except:
        return None

def _same_event_next_open(df, signal_index, signal_close, max_gap_pct=3.0):
    try:
        j=int(signal_index)
        if j+1>=len(df):return None
        row=df.iloc[j+1]
        entry=float(row.open)
        if entry<=0:return None
        gap=(entry/float(signal_close)-1.0)*100.0
        return {
            "skip":bool(gap>=float(max_gap_pct)),
            "gap_pct":gap,
            "entry":entry,
            "entry_date":row["date"],
        }
    except:
        return None

def _same_event_sim(df, entry_date, entry, stop_a, max_days=15):
    """
    실제 진입가 +10% / 동일 A 손절 / 최대 15거래일.
    같은 날 목표와 A가 모두 터치되면 손절 우선.
    """
    try:
        ds=pd.to_datetime(df["date"]).dt.normalize()
        ed=pd.Timestamp(entry_date).normalize()
        hits=df.index[ds==ed].tolist()
        if not hits:return None
        i0=int(hits[-1])

        entry=float(entry); stop=float(stop_a)
        if entry<=0 or stop<=0:return None
        if entry<=stop:
            return {"outcome":"STOP","return_pct":0.0,"days":0,
                    "entry":entry,"target":entry*1.10,"stop":stop}

        target=entry*1.10
        end=min(len(df),i0+int(max_days))
        last=entry

        for k,i in enumerate(range(i0,end),1):
            r=df.iloc[i]
            lo=float(r.low); hi=float(r.high); last=float(r.close)
            hit_stop=lo<=stop
            hit_win=hi>=target
            if hit_stop and hit_win:
                return {"outcome":"STOP","return_pct":(stop/entry-1)*100.0,
                        "days":k,"entry":entry,"target":target,"stop":stop}
            if hit_stop:
                return {"outcome":"STOP","return_pct":(stop/entry-1)*100.0,
                        "days":k,"entry":entry,"target":target,"stop":stop}
            if hit_win:
                return {"outcome":"WIN","return_pct":10.0,
                        "days":k,"entry":entry,"target":target,"stop":stop}

        return {"outcome":"TIMEOUT","return_pct":(last/entry-1)*100.0,
                "days":max(1,end-i0),"entry":entry,"target":target,"stop":stop}
    except:
        return None

def _same_event_summary(rows):
    n=len(rows)
    if not n:
        return {"n":0,"win_rate":0.0,"stop_rate":0.0,
                "timeout_rate":0.0,"avg_return":0.0,"avg_days":0.0}
    vc=Counter(str(x.get("outcome","")) for x in rows)
    return {
        "n":n,
        "win_rate":round(vc.get("WIN",0)/n*100.0,1),
        "stop_rate":round(vc.get("STOP",0)/n*100.0,1),
        "timeout_rate":round(vc.get("TIMEOUT",0)/n*100.0,1),
        "avg_return":round(sum(float(x.get("return_pct",0)) for x in rows)/n,2),
        "avg_days":round(sum(int(x.get("days",0)) for x in rows)/n,1),
    }

def _same_event_monthly_rate(rows,start_date,end_date):
    try:
        a=pd.Timestamp(start_date); b=pd.Timestamp(end_date)
        months=max(1,(b.year-a.year)*12+(b.month-a.month)+1)
        return round(len(rows)/months,2)
    except:return 0.0



def run_v4_time_machine(nstocks=None):
    token=kis_access_token() if kis_ready() else ""
    if not token:return {"ok":False,"error":"KIS 인증 필요"}

    today=pd.Timestamp(now_kst().date())
    test_end=today-pd.Timedelta(days=1)
    test_start=test_end-pd.Timedelta(days=330)
    history_start=test_start-pd.Timedelta(days=430)

    stocks=_tm_full_universe()

    events=[]
    buckets={"T3":[],"T5":[],"T7":[],"BRK":[]}
    reached={"T3":0,"T5":0,"T7":0,"BRK":0}
    gap_skips={"T3":0,"T5":0,"T7":0,"BRK":0}
    candle_miss={"T3":0,"T5":0,"T7":0,"BRK":0}
    a_break_before={"T3":0,"T5":0,"T7":0,"BRK":0}

    p=st.progress(0,text=f"전체 적격 {len(stocks):,}종목 · 동일 A/B 사건 고정 검증 중...")

    for si,stock in enumerate(stocks,1):
        p.progress(si/max(len(stocks),1),
                   text=f"{si:,}/{len(stocks):,} · {stock['name']} · A/B 사건 생성 → 4개 진입선 추적")

        df=_tm_fetch_history(stock["code"],history_start,test_end,token)
        if df is None or len(df)<180:continue

        dates=pd.to_datetime(df["date"]).dt.normalize()
        idxs=[i for i,d in enumerate(dates)
              if d>=test_start and d<=test_end and i>=160 and i<len(df)-2]

        seen=set()

        # 사건 생성: B가 right=3으로 '처음 확정되는 날' 딱 한 번만 생성
        for i in idxs:
            hist=df.iloc[:i+1].copy().reset_index(drop=True)
            if not _tm_liquid_at_date(hist):continue

            ev=_find_new_ab_event(hist)
            if not ev:continue

            a_date=str(pd.Timestamp(ev["A"]["date"]).date())
            b_date=str(pd.Timestamp(ev["B"]["date"]).date())
            event_id=f'{stock["code"]}|{a_date}|{b_date}'
            if event_id in seen:continue
            seen.add(event_id)

            ev_full={
                "event_id":event_id,
                "code":stock["code"],"name":stock["name"],"market":stock.get("market",""),
                "event_date":str(pd.Timestamp(ev["event_date"]).date()),
                "A_date":a_date,"A":round(float(ev["A"]["low"]),2),
                "B_date":b_date,"B":round(float(ev["B"]["low"]),2),
                "rebound_pct":round(float(ev.get("rebound_pct",0)),2),
                "b_above_a_pct":round(float(ev.get("b_above_a_pct",0)),2),
                "bigtrend_state":ev.get("bigtrend_state",""),
                "bigtrend_score":ev.get("bigtrend_score",0),
            }

            hits=_event_rule_first_hits(df,ev)
            if not hits:continue

            ev_full["rules"]={}
            for key in ("T3","T5","T7","BRK"):
                h=hits.get(key,{})
                ev_full["rules"][key]=h.get("reason","미도달")

                if h.get("hit"):
                    reached[key]+=1
                    ent=_same_event_next_open(
                        df,h["signal_index"],h["signal_close"],3.0
                    )
                    if not ent:continue
                    if ent.get("skip"):
                        gap_skips[key]+=1
                        continue

                    sim=_same_event_sim(
                        df,ent["entry_date"],float(ent["entry"]),
                        float(ev["A"]["low"]),15
                    )
                    if not sim:continue

                    buckets[key].append({
                        "event_id":event_id,
                        "code":stock["code"],"name":stock["name"],
                        "event_date":ev_full["event_date"],
                        "A":ev_full["A"],"B":ev_full["B"],
                        "signal_date":str(pd.Timestamp(h["signal_date"]).date()),
                        "line":round(float(h.get("line",0)),2),
                        "signal_close":round(float(h.get("signal_close",0)),2),
                        "entry_date":str(pd.Timestamp(ent["entry_date"]).date()),
                        "entry":round(float(ent["entry"]),2),
                        "gap_pct":round(float(ent.get("gap_pct",0)),2),
                        "outcome":sim["outcome"],
                        "return_pct":sim["return_pct"],
                        "days":sim["days"],
                    })
                else:
                    reason=h.get("reason","")
                    if reason=="첫돌파_캔들미달":
                        candle_miss[key]+=1
                    elif reason=="A선이탈":
                        a_break_before[key]+=1

            events.append(ev_full)

    p.empty()

    events=sorted(events,key=lambda x:(x["event_date"],x["code"],x["B_date"]))
    if len(events)<20:
        result={"ok":False,"error":f"동일 A/B 사건 표본 부족 · {len(events)}건","events":events}
        _tm_json_write(TM_V4_RESULT_FILE,result)
        return result

    # 모든 규칙이 정확히 같은 사건 시계열로 TRAIN/BLIND를 나눈다.
    event_dates=sorted(set(x["event_date"] for x in events))
    cut_i=max(1,min(len(event_dates)-1,int(len(event_dates)*0.70)))
    cut_date=event_dates[cut_i]

    result_rules={}
    labels={"T3":"B+3%","T5":"B+5%","T7":"B+7%","BRK":"5일고점 돌파"}

    for key in ("T3","T5","T7","BRK"):
        rows=sorted(buckets[key],key=lambda x:(x["event_date"],x["code"]))
        tr=[x for x in rows if x["event_date"]<cut_date]
        bl=[x for x in rows if x["event_date"]>=cut_date]
        result_rules[key]={
            "label":labels[key],
            "reached":int(reached[key]),
            "entered":len(rows),
            "all":_same_event_summary(rows),
            "train":_same_event_summary(tr),
            "blind":_same_event_summary(bl),
            "monthly_rate":_same_event_monthly_rate(rows,test_start,test_end),
            "event_retain":round(reached[key]/len(events)*100.0,1),
            "entry_retain":round(len(rows)/len(events)*100.0,1),
            "gap_skips":int(gap_skips[key]),
            "candle_miss":int(candle_miss[key]),
            "a_break_before":int(a_break_before[key]),
            "rows":rows[-1200:],
        }

    monotonic=bool(
        reached["T3"]>=reached["T5"]>=reached["T7"]
    )

    result={
        "ok":True,"schema":TM_V4_SCHEMA,
        "created_at":now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks":len(stocks),
        "test_start":str(test_start.date()),"test_end":str(test_end.date()),
        "split_date":cut_date,
        "event_count":len(events),
        "monotonic_t357":monotonic,
        "rules":result_rules,
        "events":events[-1200:],
        "method":"B 피벗이 right=3으로 처음 확정되는 날 A/B 사건을 1회 생성하고 A/B를 고정. 같은 사건을 앞으로 추적해 T3/T5/T7/직전5일고점 최초 종가돌파를 기록. A가 먼저 깨지면 이후 진입 없음. 종가 신호→D+1 시가, +3% 이상 갭상승 추격 제외, 실제진입가 +10%, 동일 A 손절, 15거래일, 동시터치 손절우선. TRAIN/BLIND도 동일 사건 날짜로 공통 분할.",
    }
    _tm_json_write(TM_V4_RESULT_FILE,result)
    return result


def _render_v4_time_machine():
    st.markdown('<div class="section-title">🎯 동일 A/B 사건 · 진입시점 4종 재검증</div>',unsafe_allow_html=True)
    st.caption("이번에는 A/B를 매일 다시 잡지 않습니다 · 사건 1개를 고정한 뒤 T3/T5/T7/5일고점을 앞으로 추적합니다.")
    res=_tm_json_read(TM_V4_RESULT_FILE)

    if res.get("ok") and res.get("schema")==TM_V4_SCHEMA:
        st.markdown(
            f"**검증기간 {res.get('test_start','')} ~ {res.get('test_end','')} · "
            f"적격 전체 {res.get('stocks',0):,}종목 · 고정 A/B 사건 {res.get('event_count',0)}건 · "
            f"BLIND 시작 {res.get('split_date','')}**"
        )

        if res.get("monotonic_t357"):
            st.success("동일 사건 검증 정상 · T3 도달 ≥ T5 도달 ≥ T7 도달")
        else:
            st.error("검증 구조 이상 · T3/T5/T7 도달건수 단조관계 확인 필요")

        rows=[]
        for key in ("T3","T5","T7","BRK"):
            x=res.get("rules",{}).get(key,{})
            a=x.get("all",{}); b=x.get("blind",{})
            rows.append({
                "진입법":x.get("label",key),
                "도달사건":x.get("reached",0),
                "실제진입":x.get("entered",0),
                "사건유지":f'{x.get("event_retain",0):.1f}%',
                "전체 15일 +10%":f'{a.get("win_rate",0):.1f}%',
                "전체 A손절":f'{a.get("stop_rate",0):.1f}%',
                "BLIND 건수":b.get("n",0),
                "BLIND +10%":f'{b.get("win_rate",0):.1f}%',
                "BLIND A손절":f'{b.get("stop_rate",0):.1f}%',
                "월평균":f'{x.get("monthly_rate",0):.1f}건',
            })
        st.dataframe(rows,use_container_width=True,hide_index=True)

        st.markdown("**진입하지 않은 이유**")
        why=[]
        for key in ("T3","T5","T7","BRK"):
            x=res.get("rules",{}).get(key,{})
            why.append({
                "진입법":x.get("label",key),
                "A 먼저 이탈":x.get("a_break_before",0),
                "첫돌파 캔들미달":x.get("candle_miss",0),
                "+3% 갭추격 제외":x.get("gap_skips",0),
            })
        st.dataframe(why,use_container_width=True,hide_index=True)

        # 동일 사건 비교에서 사전 채택조건 자동 판정
        t3=res.get("rules",{}).get("T3",{})
        t3b=t3.get("blind",{})
        event_n=max(1,int(res.get("event_count",0)))

        choices=[]
        for key in ("T5","T7","BRK"):
            x=res.get("rules",{}).get(key,{})
            b=x.get("blind",{})
            delta=float(b.get("win_rate",0))-float(t3b.get("win_rate",0))
            retain=float(x.get("event_retain",0))
            monthly=float(x.get("monthly_rate",0))
            passed=(
                b.get("n",0)>=10 and
                float(b.get("win_rate",0))>=50.0 and
                delta>=5.0 and
                float(b.get("stop_rate",100))<=15.0 and
                4.0<=monthly<=8.0 and
                retain>=60.0
            )
            choices.append((passed,delta,b.get("win_rate",0),-b.get("stop_rate",100),retain,key,x))

        choices.sort(reverse=True)
        if choices and choices[0][0]:
            _,delta,_,_,retain,key,x=choices[0]
            b=x.get("blind",{})
            st.success(
                f"채택 후보 · {x.get('label')} · BLIND +10% {b.get('win_rate',0):.1f}% "
                f"({delta:+.1f}%p vs T3) · A손절 {b.get('stop_rate',0):.1f}% · "
                f"월 {x.get('monthly_rate',0):.1f}건 · 사건유지 {retain:.1f}%"
            )
        else:
            st.warning("사전 채택조건을 모두 만족한 진입법 없음 · 결과 확인 전 T3 BASE 유지")

        with st.expander("고정 A/B 사건 상세"):
            view=[]
            for e in res.get("events",[]):
                rr=e.get("rules",{})
                view.append({
                    "사건ID":e.get("event_id",""),
                    "종목":e.get("name",""),
                    "사건일":e.get("event_date",""),
                    "A":e.get("A",0),"B":e.get("B",0),
                    "T3":rr.get("T3",""),
                    "T5":rr.get("T5",""),
                    "T7":rr.get("T7",""),
                    "5일고점":rr.get("BRK",""),
                })
            st.dataframe(view,use_container_width=True,hide_index=True)

        with st.expander("실제 진입 상세"):
            for key in ("T3","T5","T7","BRK"):
                x=res.get("rules",{}).get(key,{})
                st.markdown(f"**{x.get('label',key)}**")
                st.dataframe(x.get("rows",[]),use_container_width=True,hide_index=True)

        st.caption(f"결과 저장 {res.get('created_at','')}")

    elif res:
        st.warning(res.get("error","아직 동일 사건 검증 결과가 없습니다."))

    if st.button("🎯 동일 A/B 사건으로 4종 재검증",use_container_width=True,key="tm_same_ab_event"):
        with st.spinner("A/B 사건을 먼저 고정한 뒤 T3/T5/T7/5일고점을 같은 사건에서 추적 중..."):
            rr=run_v4_time_machine()
        if rr.get("ok"):
            txt=[]
            for key in ("T3","T5","T7","BRK"):
                x=rr.get("rules",{}).get(key,{})
                b=x.get("blind",{})
                txt.append(f"{x.get('label',key)} {b.get('win_rate',0):.1f}%")
            st.success(
                f"완료 · 고정사건 {rr.get('event_count',0)}건 · "
                + " / ".join(txt)
            )
            st.rerun()
        else:
            st.error(rr.get("error","동일 사건 검증 실패"))

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

_render_candidate_top3()
_render_v4_time_machine()

_render_aux_radars(st.session_state.get("scan_stats",{}))
_render_future_discovery()
