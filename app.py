
import re, math, requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Stock Compass · ONE", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0"}

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
div[data-testid="stDataFrame"]{border:1px solid #30343a;border-radius:10px;overflow:hidden}
@media(max-width:900px){
 .kpi-grid{grid-template-columns:repeat(2,1fr)}
 .quick-grid{grid-template-columns:repeat(2,1fr)}
 .hero-name{font-size:28px}
}
</style>
""",unsafe_allow_html=True)

def won(x):
    try:return f"{int(round(float(x))):,}원"
    except:return "-"

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

@st.cache_data(ttl=3600,show_spinner=False)
@st.cache_data(ttl=1800,show_spinner=False)
def universe(limit_each=None):
    """KOSPI/KOSDAQ 전체검색용 1차 후보 수집.
    JSON 시장목록을 우선 사용하고, 실패 시 HTML의 href/code와 텍스트를 보수적으로 복구한다.
    종목별 상세페이지 호출은 하지 않는다.
    """
    bad_tokens=("ETF","ETN","스팩","SPAC","리츠","인버스","레버리지",
                "선물","채권","우B","우C","1우","2우","3우")
    out=[]; seen=set()
    sess=requests.Session(); sess.headers.update({
        "User-Agent":"Mozilla/5.0",
        "Referer":"https://finance.naver.com/"
    })

    def accept(code,name,market,price,volume):
        try:
            code=str(code).zfill(6); name=str(name).strip()
            price=float(price); volume=float(volume)
            if not re.fullmatch(r"\d{6}",code) or not name:return
            if code in seen:return
            if any(t in name for t in bad_tokens) or name.endswith("우"):return
            if price<1000 or price>50000:return
            if volume<50000:return
            tv=price*volume
            if tv<500_000_000:return
            seen.add(code)
            out.append({"code":code,"name":name,"market":market,
                        "snapshot_price":price,"snapshot_volume":volume,
                        "snapshot_value":tv})
        except:
            return

    # Naver mobile stock API. Paging until an empty page.
    for market_type,market in [("KOSPI","KOSPI"),("KOSDAQ","KOSDAQ")]:
        api_ok=False
        for page in range(1,80):
            urls=[
                f"https://m.stock.naver.com/api/stocks/marketValue/{market_type}?page={page}&pageSize=50",
                f"https://m.stock.naver.com/api/stocks/marketValue/{market_type}?page={page}&pageSize=100",
            ]
            data=None
            for url in urls:
                try:
                    r=sess.get(url,timeout=6)
                    if r.ok and "application/json" in r.headers.get("content-type",""):
                        data=r.json(); break
                except:
                    pass
            if data is None:
                break

            items=[]
            if isinstance(data,list):items=data
            elif isinstance(data,dict):
                for k in ("stocks","items","result","data"):
                    v=data.get(k)
                    if isinstance(v,list):items=v; break
                    if isinstance(v,dict):
                        for kk in ("stocks","items"):
                            if isinstance(v.get(kk),list):
                                items=v[kk]; break
                        if items:break
            if not items:break
            api_ok=True

            for it in items:
                if not isinstance(it,dict):continue
                code=it.get("itemCode") or it.get("code") or it.get("stockCode")
                name=it.get("stockName") or it.get("name") or it.get("itemName")
                price=(it.get("closePrice") or it.get("currentPrice") or
                       it.get("now") or it.get("price"))
                volume=(it.get("accumulatedTradingVolume") or it.get("tradeVolume") or
                        it.get("volume") or it.get("accTradeVolume"))
                def n(v):
                    if v is None:return 0
                    return float(re.sub(r"[^0-9.+-]","",str(v).replace(",","")) or 0)
                accept(code,name,market,n(price),n(volume))

            if len(items)<45:break

        # Fallback only if API produced no usable candidates for this market.
        if not any(x["market"]==market for x in out):
            empty=0
            for page in range(1,80):
                try:
                    html=sess.get(
                        f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={0 if market=='KOSPI' else 1}&page={page}",
                        timeout=6).text
                except:
                    empty+=1
                    if empty>=2:break
                    continue
                rows=re.findall(r"<tr[^>]*>(.*?)</tr>",html,re.S|re.I)
                found=0
                for row in rows:
                    m=re.search(r'code=(\d{6})[^>]*>(.*?)</a>',row,re.S|re.I)
                    if not m:continue
                    found+=1
                    code=m.group(1)
                    name=re.sub(r"<.*?>","",m.group(2)).strip()
                    # number cells in actual market summary table
                    nums=[]
                    for td in re.findall(r'<td[^>]*class=["\'][^"\']*number[^"\']*["\'][^>]*>(.*?)</td>',row,re.S|re.I):
                        txt=re.sub(r"<[^>]+>","",td).replace(",","").replace("%","").strip()
                        x=re.sub(r"[^0-9.+-]","",txt)
                        if x:
                            try:nums.append(float(x))
                            except:pass
                    if len(nums)>=8:
                        accept(code,name,market,nums[0],nums[7])
                if found==0:
                    empty+=1
                    if empty>=2:break
                else:empty=0
    return out

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
def daily(code,count=900):
    try:
        txt=requests.get(
            f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={count}&requestType=0",
            headers=HEADERS,timeout=8).text
        rows=[]
        for item in re.findall(r'<item data="([^"]+)"',txt):
            v=item.split("|")
            if len(v)>=6:
                rows.append({"date":pd.to_datetime(v[0],format="%Y%m%d"),
                             "open":float(v[1]),"high":float(v[2]),"low":float(v[3]),
                             "close":float(v[4]),"volume":float(v[5])})
        df=pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        if df.empty:return df
        for c in ["open","high","low","close","volume"]:
            df[c]=pd.to_numeric(df[c],errors="coerce")
        df=df.dropna(subset=["open","high","low","close"])
        df=df[(df["open"]>0)&(df["high"]>0)&(df["low"]>0)&(df["close"]>0)]
        df=df[(df["high"]>=df[["open","close","low"]].max(axis=1)) &
              (df["low"]<=df[["open","close","high"]].min(axis=1))]
        return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    except:return pd.DataFrame()

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


def _live_pivot_lows(df,left=3,right=3):
    vals=df["low"].astype(float).to_numpy()
    out=[]
    for i in range(left,len(vals)-right):
        v=vals[i]
        if v==np.min(vals[i-left:i+right+1]) and v<np.min(vals[i-left:i]) and v<=np.min(vals[i+1:i+right+1]):
            out.append(i)
    return out

def _live_ab_signal(df):
    """
    LIVE rule:
    A prior low -> rebound >=5% -> B retest that does not break A
    -> TODAY confirms B+3% -> strong candle body >=53%.
    Uses only information available through today's candle.
    """
    if df is None or len(df)<140:return None
    h=df.tail(250).copy().reset_index(drop=True)
    n=len(h)
    piv=_live_pivot_lows(h,3,3)
    if len(piv)<2:return None

    today=h.iloc[-1]
    cur=float(today.close); op=float(today.open); hi=float(today.high); lo=float(today.low)
    rng=max(hi-lo,1e-9)
    body=abs(cur-op)/rng*100

    # The adopted R1 filter.
    if body < 53:return None

    for bi in reversed(piv):
        # B must be confirmed and recent.
        if bi>n-4 or bi<n-30:continue
        B=float(h.iloc[bi].low)
        acands=[ai for ai in piv if 10<=bi-ai<=120 and float(h.iloc[ai].low)<=B]
        if not acands:continue
        ai=acands[-1]
        A=float(h.iloc[ai].low)
        if A<=0:continue

        # A -> first rebound must be meaningful.
        mid=h.iloc[ai+1:bi]
        if mid.empty:continue
        peak=float(mid.high.astype(float).max())
        rebound=(peak/A-1)*100
        if rebound<5:continue

        # B holds A and remains in the same support area.
        bdist=(B/A-1)*100
        if bdist<0 or bdist>12:continue

        trigger=B*1.03

        # A must remain intact after B.
        after_b=h.iloc[bi+1:]
        if len(after_b)==0 or float(after_b.low.astype(float).min()) < A:continue

        # Today must be the first confirmed B+3% close.
        # This prevents stale signals from being shown as a new ONE.
        prior=h.iloc[bi+1:n-1]
        if len(prior) and (prior.close.astype(float)>=trigger).any():continue
        if cur < trigger:continue

        # Renewed upturn, not just a wick touch.
        if cur <= float(h.iloc[-2].close):continue
        tail=h.close.astype(float).tail(5).to_numpy()
        rises=sum(tail[j]>tail[j-1] for j in range(1,len(tail)))
        if rises<2:continue

        Aobj={"i":ai,"date":h.iloc[ai].date,"low":A}
        Bobj={"i":bi,"date":h.iloc[bi].date,"low":B}
        ridge={"i":int(mid.high.astype(float).idxmax()),"date":mid.loc[mid.high.astype(float).idxmax(),"date"],"high":peak}
        return {
            "A":Aobj,"B":Bobj,"C":None,"ridge":ridge,
            "confirm_line":trigger,"entry":cur,
            "body_pct":body,"rebound_pct":rebound,"b_above_a_pct":bdist,
            "state":"A→B 지지 · B+3% 재반등 · 몸통≥53%"
        }
    return None

def analyze_one(stock):
    try:
        df=daily(stock["code"],900)
        if df is None or len(df)<300:return None
        ok,_reason=identity_guard(stock,df)
        if not ok:return None
        cur=float(df.iloc[-1].close)
        if not np.isfinite(cur) or cur<=0 or cur>50000:return None
        bt=big_trend_gate(df)
        if not bt or not bt.get("ok",False):return None

        sig=_live_ab_signal(df)
        if not sig:return None

        A=sig["A"]; B=sig["B"]
        stop=float(A["low"])
        entry=float(sig["entry"])
        if stop<=0 or stop>=entry:return None
        stop_pct=(stop/entry-1)*100

        # ONE ranking uses the adopted R1 strength first.
        # No legacy A/B/C state score is used.
        rank=float(sig["body_pct"])

        return {
            "stock":stock,"df":df,"bigtrend":bt,
            "A":A,"B":B,"C":None,"ridge":sig["ridge"],
            "state":sig["state"],"score":rank,
            "dist":(entry/stop-1)*100,
            "entry":entry,"confirm_line":float(sig["confirm_line"]),
            "body_pct":float(sig["body_pct"]),
            "rebound_pct":float(sig["rebound_pct"]),
            "b_above_a_pct":float(sig["b_above_a_pct"]),
            "stop_pct":stop_pct
        }
    except Exception:
        return None

def scan(_n=None):
    # 1단계: 시장목록 페이지만 읽어 전체시장 1차 압축
    pool=universe()
    if not pool:
        return None,[],{"all":"전체","prefilter":0,"source_error":True}

    # 2단계: 압축된 종목만 900일 차트 1회 호출 + A→B 정밀검사
    bar=st.progress(0,text=f"전체시장 1차 통과 {len(pool):,}종목 정밀분석 중...")
    arr=[]
    for i,x in enumerate(pool):
        if i%3==0 or i==len(pool)-1:
            bar.progress(
                (i+1)/max(len(pool),1),
                text=f"{i+1:,}/{len(pool):,} {x['name']} A→B 분석"
            )
        z=analyze_one(x)
        if z:arr.append(z)

    arr.sort(key=lambda z:(z["body_pct"],-z["dist"]),reverse=True)
    return (arr[0] if arr else None),arr,{"all":"전체","prefilter":len(pool),"source_error":False}
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
        out.append(f'<text x="{width-right-4}" y="{y-5:.1f}" text-anchor="end" font-size="11" fill="#00897b">진입대기 {trigger:,.0f}</text>')
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


@st.cache_data(ttl=1800,show_spinner=False)
def investor_flow(code):
    try:
        url=f"https://finance.naver.com/item/frgn.naver?code={code}&page=1"
        html=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=8).text
        # Rows often contain date, close, change, ..., institution, foreigner.
        rows=re.findall(r'<tr[^>]*>(.*?)</tr>',html,re.S)
        inst=[]; foreign=[]
        for row in rows:
            nums=[re.sub(r"[^0-9+-]","",x) for x in re.findall(r'<td[^>]*class="num"[^>]*>(.*?)</td>',row,re.S)]
            nums=[re.sub(r"<.*?>","",x).strip() for x in nums]
            nums=[x for x in nums if x not in ("","+","-")]
            if len(nums)>=7:
                try:
                    inst.append(int(nums[-2].replace(",","")))
                    foreign.append(int(nums[-1].replace(",","")))
                except: pass
            if len(inst)>=5: break
        if not inst:return {"inst":None,"foreign":None,"status":"자료없음"}
        si=sum(inst[:5]); sf=sum(foreign[:5])
        if si>0 and sf>0: status="기관·외국인 동반유입"
        elif si>0 or sf>0: status="한쪽 유입"
        else: status="수급 약함"
        return {"inst":si,"foreign":sf,"status":status}
    except:return {"inst":None,"foreign":None,"status":"자료없음"}

@st.cache_data(ttl=3600,show_spinner=False)

@st.cache_data(ttl=900,show_spinner=False)
def investor_detail(code):
    out={"foreign_hold":None,"foreign_rate":None,"foreign_today":None,"inst_today":None}
    try:
        html=requests.get(f"https://finance.naver.com/item/frgn.naver?code={code}",headers={"User-Agent":"Mozilla/5.0"},timeout=8).text
        trs=re.findall(r"<tr[^>]*>(.*?)</tr>",html,re.S|re.I)
        for tr in trs:
            cells=[re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>",tr,re.S|re.I)]
            if cells and re.search(r"\d{4}\.\d{2}\.\d{2}",cells[0]):
                nums=[]
                for c in cells[1:]:
                    try: nums.append(float(c.replace(",","").replace("%","")))
                    except: pass
                if len(nums)>=6:
                    out["foreign_today"]=nums[2];out["inst_today"]=nums[3];out["foreign_hold"]=int(nums[4]);out["foreign_rate"]=float(nums[5])
                break
    except: pass
    return out

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

st.markdown("**검색범위: KOSPI + KOSDAQ 전체**  ·  **현재가 50,000원 이하**  ·  ETF/ETN/스팩/리츠/우선주 제외  ·  저유동성 제외")
n=None
def interactive_candle_chart(df,A=None,B=None,C=None,entry=None,zones=None):
    import json
    d=df.tail(500).copy(); rows=[]
    for _,r in d.iterrows():
        try: rows.append({"t":str(r["date"])[:10],"o":float(r.open),"h":float(r.high),"l":float(r.low),"c":float(r.close),"v":float(r.volume)})
        except: pass
    if len(rows)<20:return "<div>차트 데이터 부족</div>"
    marks=[]
    for label,val in [("A 지지선",A),("B",B),("C 다음지지",C),("진입 확인선",entry)]:
        try:
            if val is not None and np.isfinite(float(val)):marks.append({"label":label,"v":float(val)})
        except: pass
    for i,z in enumerate((zones or [])[:2]):
        try: marks.append({"label":f"{i+1}차 수익구간","v":float(z)})
        except: pass
    rid="tv_"+str(abs(hash((rows[-1]["t"],rows[-1]["c"]))))
    return f"""<div id="{rid}" style="width:100%;height:570px;background:#fff;position:relative;border-radius:6px;overflow:hidden">
<canvas style="width:100%;height:100%;touch-action:none"></canvas><div class="tip" style="display:none;position:absolute;top:6px;left:6px;background:#111;color:white;padding:6px;border-radius:4px;font:12px sans-serif"></div></div>
<script>(()=>{{const root=document.getElementById("{rid}"),cv=root.querySelector("canvas"),tip=root.querySelector(".tip"),D={json.dumps(rows,ensure_ascii=False)},M={json.dumps(marks,ensure_ascii=False)};
let n=Math.min(120,D.length),end=D.length,drag=false,lx=0;
function ma(k,i){{if(i<k-1)return null;let q=0;for(let j=i-k+1;j<=i;j++)q+=D[j].c;return q/k}}
function draw(){{let r=root.getBoundingClientRect(),dpr=devicePixelRatio||1;cv.width=r.width*dpr;cv.height=r.height*dpr;let x=cv.getContext("2d");x.scale(dpr,dpr);
let W=r.width,H=r.height,L=52,R=68,T=18,VH=80,B=24,PH=H-T-VH-B,st=Math.max(0,end-n),a=D.slice(st,end);if(!a.length)return;
let lo=Math.min(...a.map(q=>q.l)),hi=Math.max(...a.map(q=>q.h)),pad=(hi-lo)*.08||1;lo-=pad;hi+=pad;
let yy=v=>T+(hi-v)/(hi-lo)*PH,xx=i=>L+(i+.5)*(W-L-R)/a.length,cw=Math.max(1,(W-L-R)/a.length*.62);
x.fillStyle="#fff";x.fillRect(0,0,W,H);x.strokeStyle="#e8edf2";x.font="11px sans-serif";x.fillStyle="#667085";
for(let k=0;k<6;k++){{let y=T+k*PH/5,val=hi-k*(hi-lo)/5;x.beginPath();x.moveTo(L,y);x.lineTo(W-R,y);x.stroke();x.fillText(Math.round(val).toLocaleString(),W-R+4,y+4)}}
let mv=Math.max(...a.map(q=>q.v),1);a.forEach((q,i)=>{{let h=q.v/mv*(VH-10);x.fillStyle=q.c>=q.o?"rgba(220,70,70,.32)":"rgba(50,105,220,.32)";x.fillRect(xx(i)-cw/2,T+PH+VH-h,cw,h)}});
a.forEach((q,i)=>{{let X=xx(i);x.strokeStyle=x.fillStyle=q.c>=q.o?"#df4b4b":"#356fd3";x.beginPath();x.moveTo(X,yy(q.h));x.lineTo(X,yy(q.l));x.stroke();let y1=yy(Math.max(q.o,q.c)),y2=yy(Math.min(q.o,q.c));x.fillRect(X-cw/2,y1,cw,Math.max(1,y2-y1))}});
[[20,"#f0a000"],[60,"#2b7de9"],[120,"#8a55c5"]].forEach(([k,col])=>{{x.strokeStyle=col;x.lineWidth=1.3;x.beginPath();let on=false;a.forEach((q,i)=>{{let v=ma(k,st+i);if(v==null)return;on?(x.lineTo(xx(i),yy(v))):(x.moveTo(xx(i),yy(v)),on=true)}});x.stroke()}});
M.forEach((m,i)=>{{if(m.v<lo||m.v>hi)return;let y=yy(m.v);x.setLineDash([5,4]);x.strokeStyle=i%2?"#8b5cf6":"#159570";x.beginPath();x.moveTo(L,y);x.lineTo(W-R,y);x.stroke();x.setLineDash([]);x.fillStyle="#222";x.fillText(m.label+" "+Math.round(m.v).toLocaleString(),L+4,y-3)}});
let step=Math.max(1,Math.floor(a.length/6));x.fillStyle="#667085";for(let i=0;i<a.length;i+=step)x.fillText(a[i].t.slice(2),xx(i)-22,H-5);root.g={{a,L,R,W,st}}}}
cv.addEventListener("wheel",e=>{{e.preventDefault();n=Math.max(30,Math.min(D.length,n+(e.deltaY>0?15:-15)));draw()}},{{passive:false}});
cv.addEventListener("pointerdown",e=>{{drag=true;lx=e.clientX;cv.setPointerCapture(e.pointerId)}});cv.addEventListener("pointerup",()=>drag=false);
cv.addEventListener("pointermove",e=>{{if(drag){{let dx=e.clientX-lx;if(Math.abs(dx)>10){{end=Math.max(n,Math.min(D.length,end-(dx>0?3:-3)));lx=e.clientX;draw()}}return}}
let g=root.g,r=cv.getBoundingClientRect(),i=Math.floor((e.clientX-r.left-g.L)/(g.W-g.L-g.R)*g.a.length);i=Math.max(0,Math.min(g.a.length-1,i));let q=g.a[i];tip.style.display="block";tip.textContent=`${{q.t}} 시 ${{q.o.toLocaleString()}} 고 ${{q.h.toLocaleString()}} 저 ${{q.l.toLocaleString()}} 종 ${{q.c.toLocaleString()}} 거래량 ${{Math.round(q.v).toLocaleString()}}`;}});
cv.addEventListener("mouseleave",()=>tip.style.display="none");addEventListener("resize",draw);draw();}})();</script>"""

def pct_from(base,val):
    try:return (float(val)/float(base)-1)*100
    except:return np.nan

def price_pct(base,val):
    try:return f"{won(val)} ({pct_from(base,val):+.1f}%)"
    except:return "-"

if st.button("🔎 오늘의 ONE 찾기",type="primary",use_container_width=True):
    with st.spinner("선택과 집중 분석 중..."):
        one,arr,scan_stats=scan(n)
    st.session_state["one"]=one
    st.session_state["qualified"]=len(arr)
    st.session_state["scan_stats"]=scan_stats

one=st.session_state.get("one")

# 코드 업데이트 전 세션에 남아 있던 옛 ONE 결과는 새 엔진 필드가 없어 오류가 납니다.
# 새 A→B 엔진 결과가 아니면 자동 폐기하고 다시 스캔하게 합니다.
if one is not None:
    _required=("entry","body_pct","confirm_line","A","B","state")
    if not isinstance(one,dict) or any(k not in one for k in _required):
        st.session_state.pop("one",None)
        st.session_state.pop("qualified",None)
        st.session_state.pop("scan_stats",None)
        one=None
        st.info("엔진이 업데이트되었습니다. '오늘의 ONE 찾기'를 다시 눌러주세요.")

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
    trigger=float(one.get("entry",df.iloc[-1].close))

    action_short="진입 추천"
    action_cls="action-buy"
    action_text=f"A→B 지지 확인 · B+3% 재반등 · 몸통 {one['body_pct']:.1f}%"

    st.markdown(f"""
    <div class="hero">
      <div class="hero-top">
        <div>
          <div class="hero-name">🏆 {name}</div>
          <div class="hero-code">{one['stock']['market']} · 종목코드 {one['stock']['code']} · 코드/종목명 검증 통과 · 오늘의 ONE</div>
        </div>
        <div class="hero-badge">{action_short}</div>
      </div>
      <div class="hero-line">현재 상태: {one['state']}</div>
      <div class="small">기준일 {str(df.iloc[-1]["date"])[:10]} · 현재가 {won(cur)}</div>
    </div>
    """,unsafe_allow_html=True)

    c_price=won(cur); a_price=won(A_price); trig=won(trigger)
    r_price=won(R["high"]) if R else "-"
    c_price2=won(C_price) if C else "-"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi"><div class="label">현재가</div><div class="value">{c_price}</div></div>
      <div class="kpi"><div class="label">진입 대기선</div><div class="value">{trig}</div></div>
      <div class="kpi"><div class="label">핵심 A</div><div class="value">{a_price}</div></div>
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

    flow=investor_flow(one["stock"]["code"])
    idet=investor_detail(one["stock"]["code"])
    _tv=float(df.iloc[-1].volume) if len(df) else 0
    _fp=(idet["foreign_today"]/_tv*100) if idet.get("foreign_today") is not None and _tv>0 else None
    _ip=(idet["inst_today"]/_tv*100) if idet.get("inst_today") is not None and _tv>0 else None

    health=company_health(one["stock"]["code"])
    st.markdown(f"""
    <div class="quick-grid">
      <div class="quick"><b>기업 안전</b><span>{health['status']}</span><div class="small">{health['reason']}</div></div>
      <div class="quick"><b>최근 5일 수급</b><span>{flow['status']}</span><div class="small">기관 {flow['inst'] if flow['inst'] is not None else '-'} · 외국인 {flow['foreign'] if flow['foreign'] is not None else '-'}</div></div>
    </div>
    """,unsafe_allow_html=True)

    _fh=f"{idet['foreign_hold']:,}주" if idet.get("foreign_hold") is not None else "자료없음"
    _fr=f"{idet['foreign_rate']:.2f}%" if idet.get("foreign_rate") is not None else "자료없음"
    _ft=(f"{int(idet['foreign_today']):+,}주 ·  {_fp:+.2f}%" if _fp is not None else "자료없음")
    _it=(f"{int(idet['inst_today']):+,}주 ·  {_ip:+.2f}%" if _ip is not None else "자료없음")
    st.markdown(f"""
    <div class="quick-grid">
      <div class="quick"><b>외국인 보유</b><span>{_fh}</span><div class="small">보유율 {_fr}</div></div>
      <div class="quick"><b>오늘 외국인</b><span>{_ft}</span><div class="small">순매수/순매도 수량</div></div>
      <div class="quick"><b>오늘 기관</b><span>{_it}</span><div class="small">순매수/순매도 수량</div></div>
    </div>
    """,unsafe_allow_html=True)

    # 5-second synthesis: descriptive, not a fake probability.
    flags=[]
    if one["state"].startswith("A"): flags.append("A지지")
    if ls["score"]>=3: flags.append("출발신호 양호")
    if flow["status"]=="기관·외국인 동반유입": flags.append("수급 동반")
    bt=one.get("bigtrend",big_trend_gate(df))
    buy_reasons=(["큰 추세 회복"] if bt["state"]=="상승/회복" else [])
    wait_reasons=([] if bt["state"]=="상승/회복" else ["큰 추세 중립"])
    if one["state"].startswith("A"): buy_reasons.append("A 저점 지지")
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
    elif core_ok and one["state"].startswith("A") and ls["score"]>=3: decision="진입 검토"
    elif one["state"].startswith(("A","B")): decision="대기/관찰"
    else: decision="대기"

    _target=trigger*1.10
    _stop_pct=(A_price/trigger-1)*100
    st.markdown('<div class="section-title">추천 가격</div>',unsafe_allow_html=True)
    _c1,_c2,_c3=st.columns(3)
    _c1.metric("진입 추천",won(trigger))
    _c2.metric("익절 추천",won(_target),"+10.0%")
    _c3.metric("손절",won(A_price),f"{_stop_pct:.1f}%")
    st.caption(f"진입 {won(trigger)} → 익절 {won(_target)} (+10.0%) / 손절 {won(A_price)} ({_stop_pct:.1f}%)")

    st.markdown('<div class="section-title">차트</div>',unsafe_allow_html=True)
    _cc=df.close.astype(float)

    bars=st.radio("차트 기간",options=[60,120,250,500],index=1,horizontal=True,key="one_bars")
    _zones_chart=overhead_zones(df,cur)
    _idf=df.tail(max(250,bars)).copy()
    st.components.v1.html(
        interactive_candle_chart(
            _idf,
            A=A_price if A else None,
            B=B_price if B else None,
            C=C_price if C else None,
            entry=trigger,
            zones=_zones_chart[:2],
        ),
        height=590,
        scrolling=False,
    )
    st.caption("휠 확대·축소 · 드래그 좌우 이동 · 마우스 OHLC/거래량 · MA20/60/120 · A/B/C/진입선/수익구간")
    with st.expander("기존 고정 차트 보기"):
        svg=candle_svg(df,A=A,B=B,C=C,R=R,trigger=trigger,bars=bars)
        if svg:
            st.markdown(svg,unsafe_allow_html=True)

    st.markdown('<div class="section-title">⑤ 오늘 한 줄</div>',unsafe_allow_html=True)
    if one["state"].startswith("A"):
        st.success(f"{name}: A {won(A_price)} 지지 확인 중. {won(trigger)} 돌파 확인 시 진입 검토, 구조가 살아있는 동안 보유.")
    elif one["state"].startswith("B"):
        st.warning(f"{name}: A {won(A_price)} 주변 B플랜. 지금은 추격보다 회복 확인이 먼저.")
    else:
        st.info(f"{name}: 아직 진입하지 않고 기다립니다.")
elif "one" in st.session_state:
    _ss=st.session_state.get("scan_stats",{})
    if _ss.get("source_error"):
        st.error("전체시장 종목 데이터를 가져오지 못했습니다. 매수 후보 0개로 판정하지 않고 데이터 오류로 처리합니다.")
    elif _ss:
        st.warning(f"오늘 ONE 없음 · KOSPI+KOSDAQ 전체검색 / 1차 통과 {_ss.get('prefilter',0):,}종목 정밀분석")
    else:
        st.warning("오늘 ONE 없음")
