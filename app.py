
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
def universe(limit_each=120):
    """Collect code first, then resolve each name from its own code page.
       This prevents code/name cross-binding from market-list HTML changes."""
    out=[]; seen=set()
    for sosok,market in [(0,"KOSPI"),(1,"KOSDAQ")]:
        for page in range(1,max(2,math.ceil(limit_each/50)+2)):
            try:
                html=requests.get(
                    f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}",
                    headers={"User-Agent":"Mozilla/5.0"},timeout=8
                ).text
            except: continue
            codes=re.findall(r'/item/main\.naver\?code=(\d{6})',html)
            for code in codes:
                if code in seen: continue
                seen.add(code)
                name=_name_from_code(code)
                if not name: continue
                out.append({"code":code,"name":name,"market":market})
                if sum(1 for x in out if x["market"]==market)>=limit_each: break
            if sum(1 for x in out if x["market"]==market)>=limit_each: break
    bad=("ETF","ETN","스팩","리츠","우B","우C","1우","2우","3우")
    return [x for x in out if not any(t in x["name"] for t in bad) and not x["name"].endswith("우")]

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
    """Hard gate: displayed name/code/current price must describe the same security."""
    try:
        code=stock["code"]
        official=_name_from_code(code)
        if not official:return False,"종목명 확인 실패"
        # Normalize spaces only; exact canonical name must match the collected name.
        a=re.sub(r"\s+","",str(stock.get("name","")))
        b=re.sub(r"\s+","",official)
        if a!=b:return False,f"종목명 불일치: {stock.get('name')} / {official}"
        if df is None or df.empty:return False,"가격 데이터 없음"
        chart_close=float(df.iloc[-1].close)
        if not np.isfinite(chart_close) or chart_close<=0:return False,"현재가 오류"
        return True,"정상"
    except Exception as e:
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

def analyze_one(s):
    try:
        df=daily(s["code"],900)
        if len(df)<300:return None
        ok,_identity_reason=identity_guard(s,df)
        if not ok:return None
        stc=structure(df)
        if not stc:return None
        bt=big_trend_gate(df)
        if not bt["ok"]:return None
        A,B,C,ridge=stc
        if not A or float(A.get("low",0) or 0)<=0:return None
        state,ca,cp,uw,lw,vr,rec,dng=candle_state(df,A)
        score,dist=candidate_score(df,A,B,C,ridge,state,(ca,cp,uw,lw,vr,rec,dng))
        if not np.isfinite(score) or not np.isfinite(dist):return None
        return {"stock":s,"df":df,"bigtrend":bt,"A":A,"B":B,"C":C,"ridge":ridge,"state":state,
                "score":score,"dist":dist,"close_a":ca,"cp":cp,"uw":uw,"lw":lw,"vr":vr}
    except Exception:
        return None

def scan(n):
    u=universe(max(80,math.ceil(n/2)))
    # 양 시장 균형
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(n/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:n//2]
    pool=(ks+kq)[:n]
    bar=st.progress(0,text="오늘의 한 종목을 찾는 중...")
    arr=[]
    for i,x in enumerate(pool):
        bar.progress((i+1)/max(len(pool),1),text=f"{i+1}/{len(pool)} {x['name']} 분석")
        z=analyze_one(x)
        if z and not z["state"].startswith("C") and z["dist"]<=35:
            arr.append(z)
    arr.sort(key=lambda z:z["score"],reverse=True)
    return arr[0] if arr else None, arr


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
st.caption("5~10초 안에 판단: 종목명 → 지금 행동 → 핵심 가격 → 차트 순서로 봅니다.")

with st.expander("선정 원칙"):
    st.write("기업 건강검진은 최종 본체 연결 시 공시/재무 데이터로 별도 게이트화합니다. 이 버전은 검증된 차트 구조와 ABC 행동을 먼저 한 화면으로 조립한 마무리 프로토타입입니다.")
    st.write("A 의미저점 → 현재 행동 A/B/C → 위쪽 능선 → 하단 C 순으로 대응합니다.")
    st.write("고정 +10/+20% 목표가는 사용하지 않습니다.")

n=st.select_slider("자동 비교 종목수",options=[60,100,150,200],value=100)
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
        one,arr=scan(n)
    st.session_state["one"]=one
    st.session_state["qualified"]=len(arr)

one=st.session_state.get("one")
if one is not None:
    # 보수적 최소점수. 낮으면 억지 추천하지 않음.
    if one["score"]<55:
        st.warning("오늘은 매수 후보 없음 — 1등도 기준점수를 넘지 못했습니다.")
        st.stop()

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

    # 진입 트리거는 현재 봉의 고가: 돌파 전에는 '진입대기 가격'으로만 표시.
    trigger=float(df.iloc[-1].high)

    if one["state"].startswith("A"):
        action_short="진입 검토 / 보유"
        action_cls="action-buy"
        action_text="A 지지 확인 중 · 당일 고가 돌파/다음 봉 지지 확인 시 진입 검토"
    elif one["state"].startswith("B"):
        action_short="관찰 보유"
        action_cls="action-wait"
        action_text="A 주변 흔들림 · 추격매수 금지 · A 재회복과 추가 신저점 여부 확인"
    else:
        action_short="대기"
        action_cls="action-wait"
        action_text="아직 돈을 넣지 않음 · 구조가 더 명확해질 때까지 대기"

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
    _pz=overhead_zones(df,cur)
    _p1=_pz[0] if len(_pz)>0 else None
    _p2=_pz[1] if len(_pz)>1 else None
    _price_summary=(f"현재가 {won(cur)} | 진입가 {won(trigger)} (0.0%) | "
                    f"지지선 {price_pct(trigger,A_price)} | "
                    f"1차 수익구간 {price_pct(trigger,_p1) if _p1 else '-'} | "
                    f"2차 수익구간 {price_pct(trigger,_p2) if _p2 else '-'}")

    st.markdown(f"""
    <div class="action {'action-buy' if decision=='진입 검토' else ('action-stop' if decision=='탈락' else 'action-wait')}">
      🎯 5초 결론: {decision} · {' · '.join(flags) if flags else '확인 신호 부족'}
    </div>
    """,unsafe_allow_html=True)

    st.markdown('<div class="section-title">① 핵심 가격만 보기</div>',unsafe_allow_html=True)
    rows=[
        {"구분":"진입 대기선","가격":won(trigger),"행동":"돌파 시 진입 검토"},
        {"구분":"A 핵심 전저점","가격":won(A_price),"행동":"핵심 지지선"},
        {"구분":"최근 방어저점","가격":won(B_price),"행동":"새 저점 상승 시 방어선 상향"},
    ]
    if R: rows.append({"구분":"상단 저항","가격":won(R["high"]),"행동":"돌파·안착 시 보유, 실패 시 매도판단"})
    if C: rows.append({"구분":"하단 C","가격":won(C_price),"행동":"손절 후 다음 관찰구간"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

    sp=sell_plan(df,cur,ls)
    st.markdown('<div class="section-title">② 수익구간 · 분할매도</div>',unsafe_allow_html=True)
    if sp["rows"]:
        if sp["upside"] is not None:
            st.markdown(f'<div class="action action-wait">현재가→표시된 매도구간 상단: +{sp["upside"]:.1f}% · 예상수익률이 아니라 차트상 매도구간</div>',unsafe_allow_html=True)
        plan_df=pd.DataFrame(sp["rows"],columns=["구간","가격","현재가 대비","행동"])
        plan_df["가격"]=plan_df["가격"].map(lambda x:f"{x:,.0f}원")
        plan_df["현재가 대비"]=plan_df["현재가 대비"].map(lambda x:f"+{x:.1f}%")
        plan_df["행동"]=plan_df["행동"].map(lambda x:"일부 매도 검토")
        st.dataframe(plan_df,use_container_width=True,hide_index=True)
    else:
        st.info("가까운 위쪽 매도구간이 뚜렷하지 않아 수익률 숫자를 표시하지 않습니다.")
    st.markdown("### 핵심 가격")
    st.info(_price_summary)
    st.info("왜 뽑혔나: "+why_buy+"  |  아직 조심할 점: "+why_wait)
    st.markdown('<div class="section-title">③ 상황별 대응</div>',unsafe_allow_html=True)
    plans=[
        {"상황":"A · 예상대로 상승","대응":"보유 · 새 의미저점이 높아지면 방어선도 올림"},
        {"상황":"B · A 주변 흔들기","대응":"즉시 손절 금지 · A 회복/추가 신저점 확인"},
        {"상황":"C · 실제 붕괴","대응":"A 미회복 + 추가 신저점이면 손절 · C 또는 새 추세전환 대기"},
        {"상황":"상승 후 구조 붕괴","대응":"직전 의미저점 붕괴 + 상단 저항 돌파 실패 시 수익보호 매도"},
    ]
    st.dataframe(pd.DataFrame(plans),use_container_width=True,hide_index=True)

    st.markdown('<div class="section-title">④ ONE 종목 차트</div>',unsafe_allow_html=True)
    _cc=df.close.astype(float)
    st.caption(f"큰 추세: {bt['state']} · MA20 {won(float(_cc.rolling(20).mean().iloc[-1]))} · MA60 {won(float(_cc.rolling(60).mean().iloc[-1]))} · MA120 {won(float(_cc.rolling(120).mean().iloc[-1]))}")

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
    st.warning("오늘은 기준을 통과한 종목이 없습니다.")

# ============================================================
# FINAL 50K ONE TIME MACHINE
# 현재 ONE 선발 핵심을 과거시점에서 그대로 재현하는 검증기
# ============================================================
def _tm_hist_analyze(stock, hist):
    try:
        if hist is None or len(hist)<300:return None
        cur=float(hist.iloc[-1].close)
        if not np.isfinite(cur) or cur<=0 or cur>50000:return None
        stc=structure(hist)
        if not stc:return None
        bt=big_trend_gate(hist)
        if not bt.get("ok",False):return None
        A,B,C,ridge=stc
        if not A or float(A.get("low",0) or 0)<=0:return None
        state,ca,cp,uw,lw,vr,rec,dng=candle_state(hist,A)
        score,dist=candidate_score(hist,A,B,C,ridge,state,(ca,cp,uw,lw,vr,rec,dng))
        if score is None or not np.isfinite(score) or not np.isfinite(dist):return None
        if state.startswith("C") or dist>35:return None
        return {"stock":stock,"score":float(score),"state":state,"dist":float(dist),"entry":cur,"A":float(A["low"])}
    except:return None

def _tm_future(full, idx, entry, A):
    fut=full.iloc[idx+1:idx+21]
    if len(fut)<20:return None
    h10=float(fut.iloc[:10].high.max()); l10=float(fut.iloc[:10].low.min())
    h20=float(fut.high.max()); l20=float(fut.low.min())
    return {
        "up10":(h10/entry-1)*100,"dn10":(l10/entry-1)*100,
        "up20":(h20/entry-1)*100,"dn20":(l20/entry-1)*100,
        "A_break20":bool(l20<A)
    }

def _tm_summary(rows):
    if not rows:return {}
    n=len(rows)
    rate=lambda f: round(100*sum(1 for r in rows if f(r))/n,1)
    return {
        "ONE 표본":n,
        "20일 +5% 도달":rate(lambda r:r["up20"]>=5),
        "20일 +10% 도달":rate(lambda r:r["up20"]>=10),
        "20일 +20% 도달":rate(lambda r:r["up20"]>=20),
        "20일 A 미이탈":rate(lambda r:not r["A_break20"]),
        "10일 중앙 최대상승":round(float(pd.Series([r["up10"] for r in rows]).median()),1),
        "20일 중앙 최대상승":round(float(pd.Series([r["up20"] for r in rows]).median()),1),
        "20일 중앙 최대하락":round(float(pd.Series([r["dn20"] for r in rows]).median()),1),
    }

def final50k_one_timemachine(scan_count=120, months=18):
    u=universe(max(80,math.ceil(scan_count/2)))
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(scan_count/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:scan_count//2]
    pool=(ks+kq)[:scan_count]
    data={}
    load=st.progress(0,text="과거 주가 불러오는 중...")
    for i,x in enumerate(pool):
        d=daily(x["code"],900)
        if d is not None and len(d)>=340:data[x["code"]]=d.reset_index(drop=True)
        load.progress((i+1)/max(len(pool),1),text=f"과거 주가 {i+1}/{len(pool)}")
    if not data:return []
    # 공통 월말 검증일: 최근 완결 18개월, 미래 20거래일 확보
    all_dates=sorted(set(dt for df in data.values() for dt in df.date.tolist()))
    latest=max(all_dates)-pd.Timedelta(days=35)
    start=latest-pd.DateOffset(months=months)
    dser=pd.Series([d for d in all_dates if d>=start and d<=latest])
    checkpoints=[]
    if len(dser):
        tmp=pd.DataFrame({"date":dser}); tmp["ym"]=tmp.date.dt.to_period("M")
        checkpoints=tmp.groupby("ym").date.max().tolist()
    rows=[]
    prog=st.progress(0,text="과거 ONE 재선발 중...")
    for ci,cpdate in enumerate(checkpoints):
        candidates=[]
        locs={}
        for x in pool:
            full=data.get(x["code"])
            if full is None:continue
            inds=full.index[full.date<=cpdate].tolist()
            if not inds:continue
            idx=inds[-1]
            if idx<299 or idx+20>=len(full):continue
            hist=full.iloc[:idx+1].copy()
            z=_tm_hist_analyze(x,hist)
            if z:
                candidates.append(z); locs[x["code"]]=(full,idx)
        if candidates:
            candidates.sort(key=lambda z:z["score"],reverse=True)
            one=candidates[0]
            full,idx=locs[one["stock"]["code"]]
            out=_tm_future(full,idx,one["entry"],one["A"])
            if out:
                rows.append({"date":str(full.iloc[idx].date.date()),"code":one["stock"]["code"],
                             "name":one["stock"]["name"],"entry":one["entry"],"score":round(one["score"],1),
                             "state":one["state"],"A":one["A"],**out})
        prog.progress((ci+1)/max(len(checkpoints),1),text=f"타임머신 {ci+1}/{len(checkpoints)} · ONE {len(rows)}건")
    return rows

st.divider()
st.subheader("🕰 FINAL 50K · ONE 타임머신")
st.caption("현재 FINAL의 5만원 이하·큰추세·A/B/C·거리·점수 조건으로 각 과거 월말마다 그 당시 ONE 1종목만 다시 뽑습니다. 미래 20거래일은 결과 측정에만 사용합니다.")
tm_scan=st.slider("타임머신 종목수",80,240,240,20,key="tm_scan_final50k")
tm_months=st.slider("검증기간(개월)",6,24,24,3,key="tm_month_final50k")
if st.button("🚀 FINAL 50K 승률 검증",key="tm_run_final50k"):
    tm_rows=final50k_one_timemachine(tm_scan,tm_months)
    st.session_state["proven_tm_rows"]=tm_rows
    sm=_tm_summary(tm_rows)
    if sm:
        a,b,c,d=st.columns(4)
        a.metric("ONE 표본",f'{sm["ONE 표본"]}건')
        b.metric("20일 +5%",f'{sm["20일 +5% 도달"]}%')
        c.metric("20일 +10%",f'{sm["20일 +10% 도달"]}%')
        d.metric("20일 +20%",f'{sm["20일 +20% 도달"]}%')
        st.write(sm)
        tdf=pd.DataFrame(tm_rows)
        st.dataframe(tdf,use_container_width=True)
        if not (sm["20일 +5% 도달"] >= sm["20일 +10% 도달"] >= sm["20일 +20% 도달"]):
            st.error("검산 오류: +5% ≥ +10% ≥ +20% 순서가 맞지 않습니다. 피보나치 검증을 진행하지 마세요.")
        else:
            st.success("검산 통과: 동일 20거래일 기준 +5% ≥ +10% ≥ +20%")
        st.download_button("타임머신 CSV 저장",tdf.to_csv(index=False).encode("utf-8-sig"),"Stock_Compass_FINAL50K_TM.csv","text/csv")
        st.info("승률은 고정 익절 규칙이 아니라 '해당 기간 안에 해당 상승폭에 도달했는가'를 보여주는 진단값입니다.")
    else:
        st.warning("검증 가능한 ONE 표본이 없습니다. 종목수나 기간을 늘려 다시 실행하세요.")


# ============================================================
# SAME-ONE STEP-LOW V3 — exact proven TM rows only
# ============================================================
def _so_apply(row):
    code=str(row["code"]).zfill(6)
    full=daily(code,900)
    if full is None or len(full)<260:return None
    full=full.sort_values("date").reset_index(drop=True)
    target=pd.Timestamp(str(row["date"])[:10])
    ids=full.index[full.date.dt.normalize()==target.normalize()].tolist()
    if not ids:return None
    idx=ids[-1]; entry=float(row["entry"])
    x=pd.to_numeric(full.iloc[:idx+1].low,errors="coerce")
    levels=(float(x.tail(60).min()),float(x.tail(120).min()),float(x.tail(250).min()))
    uniq=[]
    for days,v in zip((60,120,250),levels):
        if not np.isfinite(v) or v<=0 or v>entry:continue
        if any(abs(v-u[1])/u[1]<=0.005 for u in uniq):continue
        uniq.append((days,v))
    if not uniq:return None
    floor_days,floor=min(uniq,key=lambda u:(entry-u[1])/u[1])
    fut=full.iloc[idx+1:idx+21]
    if len(fut)<5:return None
    highs=fut.high.astype(float).to_numpy()
    lows=fut.low.astype(float).to_numpy()
    closes=fut.close.astype(float).to_numpy()
    stop=None
    for j,c in enumerate(closes):
        if c<floor:
            stop=j;break
    end=stop if stop is not None else len(fut)-1
    run_high=float(np.max(highs[:end+1]))
    run_low=float(np.min(lows[:end+1]))
    exitpx=float(closes[stop]) if stop is not None else float(closes[-1])
    return {**row,"low60":levels[0],"low120":levels[1],"low250":levels[2],
            "방어선기간":floor_days,"방어선":floor,
            "전저점손절":stop is not None,
            "손절적용수익":(exitpx/entry-1)*100,
            "손절전최대상승":(run_high/entry-1)*100,
            "손절전최대하락":(run_low/entry-1)*100,
            "손절전10%도달":run_high>=entry*1.10}

def _so_summary(rows):
    if not rows:return {}
    n=len(rows)
    return {"동일 ONE 표본":n,
            "손절 전 +10% 도달":round(100*sum(r["손절전10%도달"] for r in rows)/n,1),
            "전저점 손절 발생":round(100*sum(r["전저점손절"] for r in rows)/n,1),
            "평균 손절적용수익":round(float(np.mean([r["손절적용수익"] for r in rows])),2),
            "평균 최대하락":round(float(np.mean([r["손절전최대하락"] for r in rows])),2)}

# ============================================================
# 전저점 가짜이탈 vs 진짜이탈 LAB
# D0 = 방어선(60/120/250일 저점) 최초 이탈일
# D0 특징은 그날까지의 정보만 사용.
# 미래 5/10일은 라벨 판정에만 사용.
# ============================================================
def _bt_feature(full, i, floor):
    if i<21:return None
    r=full.iloc[i]
    prev=full.iloc[i-1]
    o,h,l,c,v=[float(r[x]) for x in ("open","high","low","close","volume")]
    pc=float(prev.close)
    rng=max(h-l,1e-9)
    body=abs(c-o)/rng*100
    lower=(min(o,c)-l)/rng*100
    upper=(h-max(o,c))/rng*100
    closepos=(c-l)/rng*100
    vol20=float(full.iloc[i-20:i].volume.astype(float).mean())
    prevv=float(prev.volume)
    return {
      "D0이탈폭%":(l/floor-1)*100,
      "D0종가vs전저점%":(c/floor-1)*100,
      "D0등락률%":(c/pc-1)*100,
      "양봉":c>=o,
      "몸통%":body,
      "아래꼬리%":lower,
      "윗꼬리%":upper,
      "종가위치%":closepos,
      "거래량20일배":v/vol20 if vol20>0 else np.nan,
      "전일거래량배":v/prevv if prevv>0 else np.nan,
    }

def _bt_label(full, i, floor):
    fut=full.iloc[i+1:i+11]
    if len(fut)<5:return None
    # Outcome only. Fake: reclaim floor quickly AND then +5% from D0 close.
    d0=float(full.iloc[i].close)
    closes=fut.close.astype(float).to_numpy()
    highs=fut.high.astype(float).to_numpy()
    lows=fut.low.astype(float).to_numpy()
    rec1=bool(closes[0]>=floor) if len(closes)>=1 else False
    rec3=bool(np.any(closes[:3]>=floor))
    rec5=bool(np.any(closes[:5]>=floor))
    newlow5=float(np.min(lows[:5])) < float(full.iloc[i].low)
    up5=(float(np.max(highs[:5]))/d0-1)*100
    up10=(float(np.max(highs))/d0-1)*100
    down5=(float(np.min(lows[:5]))/d0-1)*100

    # D0 포함, 최초 종가 회복일까지 실제 얼마나 전저점 아래로 밀렸는지
    # 미래는 결과 분석용으로만 사용.
    end = min(i+5, len(full)-1)
    reclaim_idx = None
    for k in range(i, end+1):
        if k > i and float(full.iloc[k].close) >= floor:
            reclaim_idx = k
            break
    depth_end = reclaim_idx if reclaim_idx is not None else end
    depth_low = float(full.iloc[i:depth_end+1].low.astype(float).min())
    max_floor_undercut = (depth_low/floor-1)*100
    days_to_reclaim = (reclaim_idx-i) if reclaim_idx is not None else np.nan
    # strict outcome labels; ambiguous cases kept separate
    if rec3 and up10>=5:
        lab="가짜이탈"
    elif (not rec5) and newlow5:
        lab="진짜이탈"
    else:
        lab="애매"
    return {"판정":lab,"D1회복":rec1,"3일회복":rec3,"5일회복":rec5,
            "5일신저가":newlow5,"5일최대상승%":up5,"10일최대상승%":up10,
            "5일최대하락%":down5,
            "회복전최대이탈%":max_floor_undercut,
            "회복까지거래일":days_to_reclaim}

def _bt_collect(base_rows):
    events=[]
    for bi,row in enumerate(base_rows):
        try:
            code=str(row["code"]).zfill(6)
            full=daily(code,900)
            if full is None or len(full)<280:continue
            full=full.sort_values("date").reset_index(drop=True)
            target=pd.Timestamp(str(row["date"])[:10]).normalize()
            ids=full.index[full.date.dt.normalize()==target].tolist()
            if not ids:continue
            idx=ids[-1]; entry=float(row["entry"])
            x=full.iloc[:idx+1].low.astype(float)
            levels=(float(x.tail(60).min()),float(x.tail(120).min()),float(x.tail(250).min()))
            uniq=[]
            for days,val in zip((60,120,250),levels):
                if val<=0 or val>entry:continue
                if any(abs(val-u[1])/u[1]<=0.005 for u in uniq):continue
                uniq.append((days,val))
            if not uniq:continue
            days,floor=min(uniq,key=lambda u:(entry-u[1])/u[1])

            # first breach within 20 trading days after entry
            breach=None
            for j in range(idx+1,min(idx+21,len(full)-10)):
                if float(full.iloc[j].low)<floor:
                    breach=j;break
            if breach is None:continue

            feat=_bt_feature(full,breach,floor)
            lab=_bt_label(full,breach,floor)
            if feat and lab:
                events.append({"code":code,"name":row.get("name",code),
                    "진입일":str(row["date"])[:10],
                    "D0":str(full.iloc[breach].date.date()),
                    "방어선기간":days,"방어선":floor,"진입가":entry,
                    **feat,**lab})
        except Exception:
            pass
    return events

def _bt_group_table(df):
    feats=["D0이탈폭%","D0종가vs전저점%","D0등락률%","몸통%","아래꼬리%",
           "윗꼬리%","종가위치%","거래량20일배","전일거래량배"]
    rows=[]
    for g in ("가짜이탈","진짜이탈","애매"):
        z=df[df["판정"]==g]
        if len(z)==0:continue
        r={"구분":g,"표본":len(z)}
        for f in feats:r[f]=round(float(pd.to_numeric(z[f],errors="coerce").median()),2)
        r["양봉비율%"]=round(100*float(z["양봉"].mean()),1)
        r["D1회복%"]=round(100*float(z["D1회복"].mean()),1)
        rows.append(r)
    return pd.DataFrame(rows)

def _bt_simple_rules(df):
    # Exploratory screening only: find D0 features that separate true breaks.
    z=df[df["판정"].isin(["가짜이탈","진짜이탈"])].copy()
    if len(z)<4:return pd.DataFrame()
    base=100*(z["판정"]=="진짜이탈").mean()
    tests=[]
    candidates=[
      ("종가가 전저점 아래", z["D0종가vs전저점%"]<0),
      ("종가위치 35% 이하", z["종가위치%"]<=35),
      ("음봉", ~z["양봉"]),
      ("아래꼬리 20% 이하", z["아래꼬리%"]<=20),
      ("거래량 20일평균 1.5배+", z["거래량20일배"]>=1.5),
      ("D0 -3% 이상 하락", z["D0등락률%"]<=-3),
    ]
    for name,mask in candidates:
        q=z[mask]
        if len(q):
            tests.append({"D0 특징":name,"표본":len(q),
                          "진짜이탈 비율%":round(100*(q["판정"]=="진짜이탈").mean(),1),
                          "전체대비 변화%p":round(100*(q["판정"]=="진짜이탈").mean()-base,1)})
    return pd.DataFrame(tests).sort_values(["진짜이탈 비율%","표본"],ascending=[False,False])

# ============================================================
# 성공 ONE · 피보나치 수익구간 LAB
# 목적: 전저점 방어에 성공한 ONE이 실제로 어느 확장구간까지 가는지 검증.
# A = 진입 시점의 방어 전저점(60/120/250 중 가장 가까운 하단 저점)
# B = 진입 전, A 이후 형성된 스윙 고점
# 목표 = A + (B-A) * Fib ratio
# 미래 데이터는 목표 도달/최대상승 판정에만 사용.
# ============================================================
def _fib_exit_rows(base_rows):
    out=[]
    ratios=[1.0,1.272,1.382,1.5,1.618,2.0,2.618]
    for row in base_rows:
        try:
            code=str(row["code"]).zfill(6)
            full=daily(code,900)
            if full is None or len(full)<280: continue
            full=full.sort_values("date").reset_index(drop=True)
            target=pd.Timestamp(str(row["date"])[:10]).normalize()
            ids=full.index[full.date.dt.normalize()==target].tolist()
            if not ids: continue
            idx=ids[-1]
            entry=float(row["entry"])
            if idx < 60 or idx+2 >= len(full): continue

            hist=full.iloc[:idx+1]
            lows=[]
            for days in (60,120,250):
                val=float(hist.tail(days).low.astype(float).min())
                if val<=entry:
                    if not any(abs(val-u[1])/u[1] <= .005 for u in lows):
                        lows.append((days,val))
            if not lows: continue
            floor_days,A=min(lows,key=lambda u:(entry-u[1])/u[1])

            # Locate most recent occurrence of A in available historical window.
            look=hist.tail(max(floor_days,60))
            aidx=int(look.low.astype(float).idxmin())
            if aidx>=idx: continue

            # B is the highest high from A through entry date: all known at entry.
            B=float(full.iloc[aidx:idx+1].high.astype(float).max())
            if B<=A: continue
            wave=B-A

            # Follow 60 trading days to capture the successful swing more fully.
            fut=full.iloc[idx+1:min(idx+61,len(full))]
            if len(fut)<5: continue

            # "Survived": no close below A before first +5% move.
            survived=True
            hit5=None
            for j,r in fut.iterrows():
                if float(r.close)<A:
                    survived=False
                    break
                if float(r.high)>=entry*1.05:
                    hit5=j
                    break
            if not survived or hit5 is None:
                continue

            max_high=float(fut.high.astype(float).max())
            max_up=(max_high/entry-1)*100
            rec={"date":str(row["date"])[:10],"code":code,"name":row.get("name",code),
                 "entry":entry,"방어선기간":floor_days,"A전저점":A,"B기준고점":B,
                 "AB파동%":(B/A-1)*100,"60일최대상승%":max_up}
            for rr in ratios:
                level=A+wave*rr
                rec[f"Fib {rr:g}"]=level
                rec[f"{rr:g}도달"]=bool(max_high>=level)
            out.append(rec)
        except Exception:
            pass
    return out

st.divider()
st.subheader("📐 성공 ONE · 피보나치 수익구간 검증")
st.caption("전저점이 깨지지 않고 실제 상승한 동일 ONE만 봅니다. 진입 당시 이미 알 수 있었던 A(방어 전저점)와 B(그 이후 고점)로 피보나치 확장선을 만든 뒤, 이후 어느 선까지 도달했는지 확인합니다.")
if st.button("📈 피보나치 매도구간 검증",key="fib_exit_lab"):
    _base=st.session_state.get("proven_tm_rows",[])
    if not _base:
        st.warning("먼저 위 FINAL 50K 승률 검증을 실행해주세요.")
    else:
        _fr=_fib_exit_rows(_base)
        if not _fr:
            st.warning("검증 가능한 성공 ONE을 만들지 못했습니다.")
        else:
            _fd=pd.DataFrame(_fr)
            _rat=[1.0,1.272,1.382,1.5,1.618,2.0,2.618]
            _reach=[]
            for rr in _rat:
                col=f"{rr:g}도달"
                _reach.append({"피보나치":f"{rr:g}",
                               "도달건수":int(_fd[col].sum()),
                               "도달률%":round(100*float(_fd[col].mean()),1)})
            _reachdf=pd.DataFrame(_reach)
            q1,q2,q3,q4=st.columns(4)
            _n=len(_fd)
            _sample_grade="낮음" if _n<50 else ("참고" if _n<100 else ("보통" if _n<200 else "높음"))
            q1.metric("성공 ONE",f"{_n}건")
            q2.metric("최대상승 중앙값",f"{_fd['60일최대상승%'].median():.1f}%")
            q3.metric("1.618 도달률",f"{100*_fd['1.618도달'].mean():.1f}%")
            q4.metric("2.0 도달률",f"{100*_fd['2도달'].mean():.1f}%")
            st.caption(f"현재 성공 표본 {_n}건 · 표본 신뢰도: {_sample_grade}")
            st.markdown("#### 어느 피보나치 선까지 갔나")
            st.dataframe(_reachdf,use_container_width=True)
            st.markdown("#### 성공 종목별 실제 결과")
            show=["date","code","name","entry","A전저점","B기준고점","AB파동%",
                  "60일최대상승%","1.272도달","1.382도달","1.5도달","1.618도달","2도달","2.618도달"]
            st.dataframe(_fd[show],use_container_width=True)
            st.download_button("피보나치 수익구간 CSV",
                _fd.to_csv(index=False).encode("utf-8-sig"),
                "FIB_EXIT_LAB.csv","text/csv")
            st.info("도달률이 높다고 바로 매도선으로 확정하지 않습니다. 표본과 실제 최대상승 분포를 같이 보고 FINAL 반영 여부를 결정합니다.")


# ============================================================
# LARGE SAMPLE FIB — all historical candidates, not monthly ONE only
# ============================================================
def fib_all_candidate_timemachine(scan_count=240, months=24):
    u=universe(max(80,math.ceil(scan_count/2)))
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(scan_count/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:scan_count//2]
    pool=(ks+kq)[:scan_count]
    data={}
    load=st.progress(0,text="피보나치 대규모 과거주가 불러오는 중...")
    for i,x in enumerate(pool):
        d=daily(x["code"],900)
        if d is not None and len(d)>=340:data[x["code"]]=d.reset_index(drop=True)
        load.progress((i+1)/max(len(pool),1),text=f"과거주가 {i+1}/{len(pool)}")
    if not data:return []

    all_dates=sorted(set(dt for df in data.values() for dt in df.date.tolist()))
    latest=max(all_dates)-pd.Timedelta(days=75)  # 60거래일 outcome 여유
    start=latest-pd.DateOffset(months=months)
    dser=pd.Series([d for d in all_dates if d>=start and d<=latest])
    if not len(dser):return []
    tmp=pd.DataFrame({"date":dser}); tmp["ym"]=tmp.date.dt.to_period("M")
    checkpoints=tmp.groupby("ym").date.max().tolist()

    raw=[]
    prog=st.progress(0,text="월별 전체 후보 재선발 중...")
    for ci,cpdate in enumerate(checkpoints):
        for x in pool:
            full=data.get(x["code"])
            if full is None:continue
            inds=full.index[full.date<=cpdate].tolist()
            if not inds:continue
            idx=inds[-1]
            if idx<299 or idx+60>=len(full):continue
            hist=full.iloc[:idx+1].copy()
            z=_tm_hist_analyze(x,hist)   # exact current FINAL candidate gate
            if not z:continue
            raw.append({"date":str(full.iloc[idx].date.date()),"code":x["code"],
                        "name":x["name"],"entry":z["entry"],"score":round(z["score"],1),
                        "state":z["state"],"A":z["A"]})
        prog.progress((ci+1)/max(len(checkpoints),1),text=f"전체 후보 {ci+1}/{len(checkpoints)} · {len(raw)}건")

    # de-duplicate same stock repeated in adjacent monthly checkpoints if entry date is too close
    raw=sorted(raw,key=lambda r:(r["code"],r["date"]))
    ded=[]
    last={}
    for r in raw:
        d=pd.Timestamp(r["date"])
        if r["code"] in last and (d-last[r["code"]]).days<20:continue
        ded.append(r);last[r["code"]]=d

    # Reuse the already validated Fibonacci calculation on each candidate.
    return _fib_exit_rows(ded)

st.divider()
st.subheader("📚 피보나치 대규모 표본 검증")
st.caption("월별 ONE 1종목만 보지 않고, 같은 FINAL 50K 조건을 통과한 과거 후보 전체를 검증합니다. 진입 당시 정보로 후보를 고르고 미래 60거래일은 결과 측정에만 사용합니다.")
if st.button("🚀 전체 후보 피보나치 검증",key="fib_large_all"):
    _large=fib_all_candidate_timemachine(tm_scan,tm_months)
    if not _large:
        st.warning("검증 가능한 성공 후보가 없습니다.")
    else:
        _ld=pd.DataFrame(_large)
        _rat=[1.0,1.272,1.382,1.5,1.618,2.0,2.618]
        _rr=[]
        for _x in _rat:
            _col=f"{_x:g}도달"
            _rr.append({"피보나치":f"{_x:g}","도달건수":int(_ld[_col].sum()),
                        "도달률%":round(100*float(_ld[_col].mean()),1)})
        _rdf=pd.DataFrame(_rr)
        _n=len(_ld)
        _grade="낮음" if _n<100 else ("보통" if _n<300 else "높음")
        l1,l2,l3,l4=st.columns(4)
        l1.metric("성공 후보 표본",f"{_n}건")
        l2.metric("표본 신뢰도",_grade)
        l3.metric("최대상승 중앙값",f"{_ld['60일최대상승%'].median():.1f}%")
        l4.metric("1.618 도달률",f"{100*_ld['1.618도달'].mean():.1f}%")
        st.dataframe(_rdf,use_container_width=True)
        st.markdown("#### 전체 성공 후보 결과")
        st.dataframe(_ld,use_container_width=True)
        st.download_button("대규모 피보나치 CSV",_ld.to_csv(index=False).encode("utf-8-sig"),
                           "FIB_LARGE_ALL_CANDIDATES.csv","text/csv")
        st.info("100건 이상이면 참고 신뢰도, 300건 이상이면 본격적인 매도구간 후보로 검토합니다.")


# ============================================================
# TIME EFFICIENCY LAB — how fast successful candidates reach profit targets
# A = prior-low purchase assumption.
# Candidate selection uses current FINAL historical gate only.
# Future data is used solely to measure target hit time/outcome.
# ============================================================
def _time_efficiency_all_candidates(scan_count=240, months=24):
    u=universe(max(80,math.ceil(scan_count/2)))
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(scan_count/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:scan_count//2]
    pool=(ks+kq)[:scan_count]

    data={}
    load=st.progress(0,text="시간효율 검증용 과거주가 불러오는 중...")
    for i,x in enumerate(pool):
        d=daily(x["code"],900)
        if d is not None and len(d)>=340:
            data[x["code"]]=d.reset_index(drop=True)
        load.progress((i+1)/max(len(pool),1),text=f"과거주가 {i+1}/{len(pool)}")
    if not data:return []

    all_dates=sorted(set(dt for df in data.values() for dt in df.date.tolist()))
    latest=max(all_dates)-pd.Timedelta(days=75)  # future 60 trading-day room
    start=latest-pd.DateOffset(months=months)
    dser=pd.Series([d for d in all_dates if d>=start and d<=latest])
    if not len(dser):return []
    tmp=pd.DataFrame({"date":dser}); tmp["ym"]=tmp.date.dt.to_period("M")
    checkpoints=tmp.groupby("ym").date.max().tolist()

    raw=[]
    prog=st.progress(0,text="전체 후보 시간효율 재선발 중...")
    for ci,cpdate in enumerate(checkpoints):
        for x in pool:
            full=data.get(x["code"])
            if full is None:continue
            inds=full.index[full.date<=cpdate].tolist()
            if not inds:continue
            idx=inds[-1]
            if idx<299 or idx+60>=len(full):continue
            hist=full.iloc[:idx+1].copy()
            z=_tm_hist_analyze(x,hist)
            if not z:continue

            entry=float(z["entry"])
            # A = current defense prior low from FINAL logic.
            A=float(z["A"])
            if not np.isfinite(A) or A<=0:continue

            # B = highest high from the most recent occurrence of A through entry date.
            # Entirely historical at the checkpoint.
            look=hist.tail(250)
            # find most recent row whose low is approximately A; fallback closest low
            lowvals=look.low.astype(float)
            near=(lowvals-A).abs()
            aidx=int(near.idxmin())
            if aidx>=idx:continue
            B=float(full.iloc[aidx:idx+1].high.astype(float).max())
            if B<=A:continue
            wave=B-A

            fut=full.iloc[idx+1:idx+61].copy()
            if len(fut)<5:continue

            rec={"date":str(full.iloc[idx].date.date()),"code":x["code"],"name":x["name"],
                 "A전저점":A,"entry":entry,"B기준고점":B,
                 "AB파동%":(B/A-1)*100}

            # fixed-return targets measured from A purchase assumption
            for pct in (10,15,20,25,30):
                target=A*(1+pct/100)
                hit=None
                for k,rr in enumerate(fut.itertuples(index=False),start=1):
                    if float(rr.high)>=target:
                        hit=k;break
                rec[f"+{pct}%도달"]=hit is not None
                rec[f"+{pct}%도달일"]=hit if hit is not None else np.nan

            # Fibonacci extension targets
            for fib in (1.272,1.382,1.618,2.0):
                target=A+wave*fib
                hit=None
                for k,rr in enumerate(fut.itertuples(index=False),start=1):
                    if float(rr.high)>=target:
                        hit=k;break
                rec[f"Fib{fib:g}도달"]=hit is not None
                rec[f"Fib{fib:g}도달일"]=hit if hit is not None else np.nan

            # time-efficient realized-return proxy:
            # target return divided by median hit days is computed in summary only.
            raw.append(rec)

        prog.progress((ci+1)/max(len(checkpoints),1),text=f"시간효율 {ci+1}/{len(checkpoints)} · 후보 {len(raw)}건")

    # de-duplicate adjacent monthly repeats for same stock
    raw=sorted(raw,key=lambda r:(r["code"],r["date"]))
    ded=[];last={}
    for r in raw:
        d=pd.Timestamp(r["date"])
        if r["code"] in last and (d-last[r["code"]]).days<20:continue
        ded.append(r);last[r["code"]]=d
    return ded

def _time_eff_summary(rows):
    if not rows:return pd.DataFrame()
    d=pd.DataFrame(rows)
    specs=[
        ("+10%",10,"+10%도달","+10%도달일"),
        ("+15%",15,"+15%도달","+15%도달일"),
        ("+20%",20,"+20%도달","+20%도달일"),
        ("+25%",25,"+25%도달","+25%도달일"),
        ("+30%",30,"+30%도달","+30%도달일"),
        ("Fib 1.272",None,"Fib1.272도달","Fib1.272도달일"),
        ("Fib 1.382",None,"Fib1.382도달","Fib1.382도달일"),
        ("Fib 1.618",None,"Fib1.618도달","Fib1.618도달일"),
        ("Fib 2.0",None,"Fib2도달","Fib2도달일"),
    ]
    out=[]
    for label,pct,hcol,dcol in specs:
        hit=d[d[hcol]==True]
        rate=100*len(hit)/len(d)
        med=float(pd.to_numeric(hit[dcol],errors="coerce").median()) if len(hit) else np.nan
        avg=float(pd.to_numeric(hit[dcol],errors="coerce").mean()) if len(hit) else np.nan
        if pct is not None and np.isfinite(med) and med>0:
            eff=pct/med
        else:
            eff=np.nan
        out.append({"목표":label,"도달률%":round(rate,1),
                    "평균도달일":round(avg,1) if np.isfinite(avg) else np.nan,
                    "중앙도달일":round(med,1) if np.isfinite(med) else np.nan,
                    "고정수익 목표/중앙일":round(eff,2) if np.isfinite(eff) else np.nan})
    return pd.DataFrame(out)

st.divider()
st.subheader("⏱ 수익률 × 시간효율 대규모 검증")
st.caption("전저점 A에서 매수했다고 가정하고, +10/+15/+20/+25/+30%와 피보나치 목표까지 실제 몇 거래일 걸렸는지 전체 FINAL 후보에서 비교합니다.")
if st.button("⚡ 시간효율 전체 검증",key="time_eff_large"):
    _te=_time_efficiency_all_candidates(tm_scan,tm_months)
    if not _te:
        st.warning("검증 가능한 후보가 없습니다.")
    else:
        _tedf=pd.DataFrame(_te)
        _sum=_time_eff_summary(_te)
        st.session_state["time_eff_rows"]=_te
        st.metric("시간효율 표본",f"{len(_tedf)}건")
        st.dataframe(_sum,use_container_width=True)
        st.markdown("#### 해석")
        st.caption("도달률이 높고 중앙 도달일이 짧을수록 자금회전 효율이 좋습니다. 고정수익 목표는 '목표수익률 ÷ 중앙도달일'도 함께 표시합니다.")
        st.markdown("#### 전체 개별 결과")
        st.dataframe(_tedf,use_container_width=True)
        st.download_button("시간효율 CSV",_tedf.to_csv(index=False).encode("utf-8-sig"),
                           "TIME_EFFICIENCY_ALL_CANDIDATES.csv","text/csv")


# ============================================================
# STAGE 1 — REAL ONE ENTRY × FIXED TP × PRIOR-LOW HARD STOP
# Selection: exact current FINAL historical candidate gate.
# Entry: actual ONE discovery price (z["entry"]), NOT A.
# Stop: prior-low A break => immediate exit at A (conservative threshold fill).
# Target: +10 / +15 / +20% from actual ONE entry.
# Horizon: 60 future trading days.
# If stop and target both touch in same daily candle: STOP FIRST (conservative).
# If neither: exit at day-60 close.
# ============================================================
def _stage1_real_trade(scan_count=240, months=24):
    u=universe(max(80,math.ceil(scan_count/2)))
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(scan_count/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:scan_count//2]
    pool=(ks+kq)[:scan_count]

    data={}
    p=st.progress(0,text="1차 실전검증 과거주가 불러오는 중...")
    for i,x in enumerate(pool):
        d=daily(x["code"],900)
        if d is not None and len(d)>=340:
            data[x["code"]]=d.reset_index(drop=True)
        p.progress((i+1)/max(1,len(pool)),text=f"과거주가 {i+1}/{len(pool)}")
    if not data:return []

    dates=sorted(set(dt for d in data.values() for dt in d.date.tolist()))
    latest=max(dates)-pd.Timedelta(days=75)
    start=latest-pd.DateOffset(months=months)
    ds=pd.Series([d for d in dates if start<=d<=latest])
    if not len(ds):return []
    t=pd.DataFrame({"date":ds}); t["ym"]=t.date.dt.to_period("M")
    cps=t.groupby("ym").date.max().tolist()

    rows=[]
    q=st.progress(0,text="실제 ONE 진입가 기준 매매 재현 중...")
    for ci,cp in enumerate(cps):
        for x in pool:
            full=data.get(x["code"])
            if full is None:continue
            inds=full.index[full.date<=cp].tolist()
            if not inds:continue
            idx=inds[-1]
            if idx<299 or idx+60>=len(full):continue
            hist=full.iloc[:idx+1].copy()
            z=_tm_hist_analyze(x,hist)
            if not z:continue
            entry=float(z["entry"]); A=float(z["A"])
            if not np.isfinite(entry) or not np.isfinite(A) or entry<=0 or A<=0 or A>=entry:continue
            fut=full.iloc[idx+1:idx+61].copy()
            if len(fut)<5:continue
            base={"date":str(full.iloc[idx].date.date()),"code":x["code"],"name":x["name"],
                  "ONE진입가":entry,"전저점A":A,"전저점여유%":(entry/A-1)*100}
            for tp in (10,15,20):
                target=entry*(1+tp/100)
                outcome="TIMEOUT"; days=len(fut); exitp=float(fut.iloc[-1].close)
                for k,rr in enumerate(fut.itertuples(index=False),start=1):
                    lo=float(rr.low); hi=float(rr.high)
                    # Conservative OHLC ordering: if both touched same day, stop wins.
                    if lo < A:
                        outcome="STOP"; days=k; exitp=A; break
                    if hi >= target:
                        outcome="WIN"; days=k; exitp=target; break
                ret=(exitp/entry-1)*100
                base[f"{tp}%결과"]=outcome
                base[f"{tp}%소요일"]=days
                base[f"{tp}%수익률"]=ret
            rows.append(base)
        q.progress((ci+1)/max(1,len(cps)),text=f"1차 검증 {ci+1}/{len(cps)} · {len(rows)}건")

    # remove adjacent repeated monthly selections for same stock
    rows=sorted(rows,key=lambda r:(r["code"],r["date"]))
    ded=[]; last={}
    for r in rows:
        d=pd.Timestamp(r["date"])
        if r["code"] in last and (d-last[r["code"]]).days<20:continue
        ded.append(r);last[r["code"]]=d
    return ded

def _stage1_summary(rows):
    d=pd.DataFrame(rows); out=[]
    if d.empty:return pd.DataFrame()
    for tp in (10,15,20):
        oc=d[f"{tp}%결과"]
        win=(oc=="WIN"); stop=(oc=="STOP"); timeout=(oc=="TIMEOUT")
        rr=pd.to_numeric(d[f"{tp}%수익률"],errors="coerce")
        dd=pd.to_numeric(d.loc[win,f"{tp}%소요일"],errors="coerce")
        # simple capital rotation score: arithmetic expected return per average holding day
        hold=pd.to_numeric(d[f"{tp}%소요일"],errors="coerce")
        avg_hold=float(hold.mean())
        avg_ret=float(rr.mean())
        out.append({
            "고정익절":f"+{tp}%",
            "성공률%":round(100*win.mean(),1),
            "전저점손절률%":round(100*stop.mean(),1),
            "60일미결률%":round(100*timeout.mean(),1),
            "성공시중앙소요일":round(float(dd.median()),1) if len(dd) else np.nan,
            "전체평균보유일":round(avg_hold,1),
            "1회평균수익률%":round(avg_ret,2),
            "일평균회전효율%":round(avg_ret/avg_hold,3) if avg_hold>0 else np.nan,
            "평균손절수익률%":round(float(rr[stop].mean()),2) if stop.any() else np.nan
        })
    return pd.DataFrame(out)

st.divider()
st.subheader("🎯 1차 최종검증 · 실제 ONE 진입가")
st.caption("ONE 발견가격에 매수 → +10/+15/+20% 전량익절 비교 → 전저점 A를 깨면 무조건 전량손절. 같은 날 목표와 손절이 모두 닿으면 보수적으로 손절 우선 처리합니다.")
if st.button("▶ 1차 실전전략 검증",key="stage1_real_trade"):
    _r=_stage1_real_trade(tm_scan,tm_months)
    if not _r:
        st.warning("검증 가능한 후보가 없습니다.")
    else:
        _rdf=pd.DataFrame(_r); _rs=_stage1_summary(_r)
        st.session_state["stage1_real_rows"]=_r
        st.metric("실전 매매 표본",f"{len(_rdf)}건")
        st.dataframe(_rs,use_container_width=True)
        # pick by average return/day, but expose all metrics so not silently overfit.
        if len(_rs):
            best=_rs.sort_values(["일평균회전효율%","1회평균수익률%"],ascending=False).iloc[0]
            st.success(f"현재 1차 우세: {best['고정익절']} · 성공률 {best['성공률%']}% · 평균 {best['1회평균수익률%']}%/회 · 평균보유 {best['전체평균보유일']}일")
        st.markdown("#### 개별 매매 결과")
        st.dataframe(_rdf,use_container_width=True)
        st.download_button("1차 검증 CSV",_rdf.to_csv(index=False).encode("utf-8-sig"),
                           "STAGE1_REAL_ONE_TP_STOP.csv","text/csv")


# ============================================================
# STAGE 2 — SUCCESS vs STOP SELECTOR AUDIT
# Goal: improve ONE selection, not tune TP.
# All features below are known at selection time.
# Outcome label: +15% WIN vs prior-low STOP; TIMEOUT kept separately.
# ============================================================
def _stage2_selector_audit(scan_count=240, months=24):
    u=universe(max(80,math.ceil(scan_count/2)))
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(scan_count/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:scan_count//2]
    pool=(ks+kq)[:scan_count]
    data={}
    pg=st.progress(0,text="2차 선별검증 과거주가 불러오는 중...")
    for i,x in enumerate(pool):
        d=daily(x["code"],900)
        if d is not None and len(d)>=340:data[x["code"]]=d.reset_index(drop=True)
        pg.progress((i+1)/max(1,len(pool)),text=f"과거주가 {i+1}/{len(pool)}")
    if not data:return []
    dates=sorted(set(dt for dd in data.values() for dt in dd.date.tolist()))
    latest=max(dates)-pd.Timedelta(days=75); start=latest-pd.DateOffset(months=months)
    ds=pd.Series([x for x in dates if start<=x<=latest])
    if not len(ds):return []
    tt=pd.DataFrame({"date":ds});tt["ym"]=tt.date.dt.to_period("M")
    cps=tt.groupby("ym").date.max().tolist()
    rows=[]
    pr=st.progress(0,text="성공/손절 차이 추출 중...")
    for ci,cp in enumerate(cps):
        for x in pool:
            full=data.get(x["code"])
            if full is None:continue
            ii=full.index[full.date<=cp].tolist()
            if not ii:continue
            idx=ii[-1]
            if idx<299 or idx+60>=len(full):continue
            hist=full.iloc[:idx+1].copy()
            z=_tm_hist_analyze(x,hist)
            if not z:continue
            entry=float(z["entry"]); A=float(z["A"])
            if not np.isfinite(entry) or not np.isfinite(A) or A<=0 or A>=entry:continue
            stc=structure(hist)
            if not stc:continue
            AA,BB,CC,ridge=stc
            state,ca,cpv,uw,lw,vr,rec,dng=candle_state(hist,AA)
            score,dist=candidate_score(hist,AA,BB,CC,ridge,state,(ca,cpv,uw,lw,vr,rec,dng))
            # Recent trend/volume features, all known now.
            cl=hist.close.astype(float); vol=hist.volume.astype(float)
            ma20=float(cl.tail(20).mean()); ma60=float(cl.tail(60).mean()); ma120=float(cl.tail(120).mean())
            r20=(entry/float(cl.iloc[-21])-1)*100 if len(cl)>=21 else np.nan
            r60=(entry/float(cl.iloc[-61])-1)*100 if len(cl)>=61 else np.nan
            v20=float(vol.iloc[-1]/max(vol.tail(20).mean(),1))
            fut=full.iloc[idx+1:idx+61]
            target=entry*1.15
            outcome="TIMEOUT";days=len(fut);exitp=float(fut.iloc[-1].close)
            for k,rr in enumerate(fut.itertuples(index=False),1):
                if float(rr.low)<A:
                    outcome="STOP";days=k;exitp=A;break
                if float(rr.high)>=target:
                    outcome="WIN";days=k;exitp=target;break
            rows.append({
                "date":str(full.iloc[idx].date.date()),"code":x["code"],"name":x["name"],
                "entry":entry,"A":A,"A거리%":(entry/A-1)*100,
                "score":float(score),"state":state,"dist":float(dist),
                "캔들몸통":float(ca),"종가위치":float(cpv),"윗꼬리":float(uw),"아랫꼬리":float(lw),
                "거래량비":float(vr),"최근성":float(rec),"dng":float(dng),
                "20일수익%":r20,"60일수익%":r60,"현재/20MA%":(entry/ma20-1)*100,
                "현재/60MA%":(entry/ma60-1)*100,"현재/120MA%":(entry/ma120-1)*100,
                "당일/20일거래량":v20,"15%결과":outcome,"소요일":days,
                "실현수익%":(exitp/entry-1)*100
            })
        pr.progress((ci+1)/max(1,len(cps)),text=f"2차 검증 {ci+1}/{len(cps)} · {len(rows)}건")
    rows=sorted(rows,key=lambda r:(r["code"],r["date"]))
    ded=[];last={}
    for r in rows:
        dd=pd.Timestamp(r["date"])
        if r["code"] in last and (dd-last[r["code"]]).days<20:continue
        ded.append(r);last[r["code"]]=dd
    return ded

def _stage2_feature_table(rows):
    d=pd.DataFrame(rows)
    core=d[d["15%결과"].isin(["WIN","STOP"])].copy()
    feats=["A거리%","score","dist","종가위치","윗꼬리","아랫꼬리","거래량비",
           "20일수익%","60일수익%","현재/20MA%","현재/60MA%","현재/120MA%","당일/20일거래량"]
    out=[]
    for f in feats:
        x=pd.to_numeric(core[f],errors="coerce")
        w=x[core["15%결과"]=="WIN"]; q=x[core["15%결과"]=="STOP"]
        if len(w)<10 or len(q)<10:continue
        out.append({"진입시점특징":f,"성공중앙값":round(float(w.median()),3),
                    "손절중앙값":round(float(q.median()),3),
                    "차이":round(float(w.median()-q.median()),3)})
    return pd.DataFrame(out)

st.divider()
st.subheader("🔎 2차 검증 · 오를 ONE 선별 정밀화")
st.caption("+15% 성공 종목과 전저점 손절 종목을 비교합니다. 미래정보는 결과표시에만 쓰고, 비교 특징은 모두 ONE 발견 당시 알 수 있었던 값만 사용합니다.")
if st.button("▶ 2차 ONE 선별검증",key="stage2_selector"):
    _s2=_stage2_selector_audit(tm_scan,tm_months)
    if not _s2:st.warning("검증 가능한 후보가 없습니다.")
    else:
        _d2=pd.DataFrame(_s2);_ft=_stage2_feature_table(_s2)
        st.metric("2차 표본",f"{len(_d2)}건")
        a,b,c=st.columns(3)
        a.metric("+15% 성공",f'{100*(_d2["15%결과"]=="WIN").mean():.1f}%')
        b.metric("전저점 손절",f'{100*(_d2["15%결과"]=="STOP").mean():.1f}%')
        c.metric("60일 미결",f'{100*(_d2["15%결과"]=="TIMEOUT").mean():.1f}%')
        st.markdown("#### 성공과 손절의 진입 당시 차이")
        st.dataframe(_ft,use_container_width=True)
        st.markdown("#### 개별 표본")
        st.dataframe(_d2,use_container_width=True)
        st.download_button("2차 검증 CSV",_d2.to_csv(index=False).encode("utf-8-sig"),
                           "STAGE2_ONE_SELECTOR_AUDIT.csv","text/csv")
