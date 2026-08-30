
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

@st.cache_data(ttl=3600,show_spinner=False)
def universe(limit_each=150):
    out=[]
    for sosok,market in [(0,"KOSPI"),(1,"KOSDAQ")]:
        pages=max(1,math.ceil(limit_each/50))
        for page in range(1,pages+1):
            try:
                txt=requests.get(
                    f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}",
                    headers=HEADERS,timeout=8).text
            except: continue
            for code,name in re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)</a>',txt):
                name=re.sub(r"\s+"," ",name).strip()
                if not any(x["code"]==code for x in out):
                    out.append({"code":code,"name":name,"market":market})
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

def analyze_one(s):
    try:
        df=daily(s["code"],900)
        if len(df)<300:return None
        stc=structure(df)
        if not stc:return None
        A,B,C,ridge=stc
        if not A or float(A.get("low",0) or 0)<=0:return None
        state,ca,cp,uw,lw,vr,rec,dng=candle_state(df,A)
        score,dist=candidate_score(df,A,B,C,ridge,state,(ca,cp,uw,lw,vr,rec,dng))
        if not np.isfinite(score) or not np.isfinite(dist):return None
        return {"stock":s,"df":df,"A":A,"B":B,"C":C,"ridge":ridge,"state":state,
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
def company_health(code):
    """Conservative public-page gate. If reliable fields are unavailable, say '확인필요' rather than invent."""
    try:
        html=requests.get(f"https://finance.naver.com/item/main.naver?code={code}",headers={"User-Agent":"Mozilla/5.0"},timeout=8).text
        txt=re.sub(r"<[^>]+>"," ",html)
        danger_words=["관리종목","거래정지","상장폐지","자본잠식"]
        hits=[w for w in danger_words if w in txt]
        if hits:return {"status":"위험","reason":", ".join(hits[:2])}
        # Only claim normal when no explicit warning; finances still need deeper review.
        return {"status":"확인필요","reason":"명시적 위험표시는 미검출 · 재무/공시는 심화확인 필요"}
    except:return {"status":"확인필요","reason":"데이터 확인 실패"}


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
    if not zones:return {"upside":None,"rows":[]}
    last=zones[-1]; upside=(last/cur-1)*100
    strength=ls.get("score",0)
    rows=[]
    # Dynamic but deterministic allocation: stronger launch -> sell less early.
    if strength>=4: alloc=[20,25,55]
    elif strength>=2: alloc=[30,30,40]
    else: alloc=[40,35,25]
    for k,z in enumerate(zones[:3]):
        rows.append((f"{k+1}차 수익구간",z,(z/cur-1)*100,alloc[min(k,2)]))
    return {"upside":upside,"rows":rows}

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
          <div class="hero-code">{one['stock']['market']} · {one['stock']['code']} · 오늘의 ONE</div>
        </div>
        <div class="hero-badge">{action_short}</div>
      </div>
      <div class="hero-line">선정점수 {one['score']:.1f} · 현재 상태: {one['state']}</div>
    </div>
    """,unsafe_allow_html=True)

    c_price=won(cur); a_price=won(A["low"]); trig=won(trigger)
    r_price=won(R["high"]) if R else "-"
    c_price2=won(C["low"]) if C else "-"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi"><div class="label">현재가</div><div class="value">{c_price}</div></div>
      <div class="kpi"><div class="label">진입 대기선</div><div class="value">{trig}</div></div>
      <div class="kpi"><div class="label">핵심 A</div><div class="value">{a_price}</div></div>
      <div class="kpi"><div class="label">위쪽 큰 능선</div><div class="value">{r_price}</div></div>
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
    health=company_health(one["stock"]["code"])
    st.markdown(f"""
    <div class="quick-grid">
      <div class="quick"><b>기업 안전</b><span>{health['status']}</span><div class="small">{health['reason']}</div></div>
      <div class="quick"><b>최근 수급</b><span>{flow['status']}</span><div class="small">기관 {flow['inst'] if flow['inst'] is not None else '-'} · 외국인 {flow['foreign'] if flow['foreign'] is not None else '-'}</div></div>
    </div>
    """,unsafe_allow_html=True)

    # 5-second synthesis: descriptive, not a fake probability.
    flags=[]
    if one["state"].startswith("A"): flags.append("A지지")
    if ls["score"]>=3: flags.append("출발신호 양호")
    if flow["status"]=="기관·외국인 동반유입": flags.append("수급 동반")
    if health["status"]=="위험": decision="탈락"
    elif one["state"].startswith("A") and ls["score"]>=3: decision="진입 검토"
    elif one["state"].startswith(("A","B")): decision="대기/관찰"
    else: decision="대기"
    st.markdown(f"""
    <div class="action {'action-buy' if decision=='진입 검토' else ('action-stop' if decision=='탈락' else 'action-wait')}">
      🎯 5초 결론: {decision} · {' · '.join(flags) if flags else '확인 신호 부족'}
    </div>
    """,unsafe_allow_html=True)

    st.markdown('<div class="section-title">① 핵심 가격만 보기</div>',unsafe_allow_html=True)
    rows=[
        {"구분":"진입 대기선","가격":won(trigger),"행동":"돌파 시 진입 검토"},
        {"구분":"A 핵심 전저점","가격":won(A["low"]),"행동":"핵심 지지선"},
        {"구분":"최근 방어저점","가격":won(B["low"]),"행동":"새 저점 상승 시 방어선 상향"},
    ]
    if R: rows.append({"구분":"위쪽 큰 능선","가격":won(R["high"]),"행동":"돌파·안착 시 보유, 실패 시 매도판단"})
    if C: rows.append({"구분":"하단 C","가격":won(C["low"]),"행동":"손절 후 다음 관찰구간"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

    sp=sell_plan(df,cur,ls)
    st.markdown('<div class="section-title">② 구조상 상승여력 · 수익구간</div>',unsafe_allow_html=True)
    if sp["rows"]:
        if sp["upside"] is not None:
            st.markdown(f'<div class="action action-wait">구조상 상단 여력: 약 +{sp["upside"]:.1f}% · 확정수익률이 아니라 차트상 저항구간 기준</div>',unsafe_allow_html=True)
        plan_df=pd.DataFrame(sp["rows"],columns=["구간","가격","현재가 대비","권장 매도비중"])
        plan_df["가격"]=plan_df["가격"].map(lambda x:f"{x:,.0f}원")
        plan_df["현재가 대비"]=plan_df["현재가 대비"].map(lambda x:f"+{x:.1f}%")
        plan_df["권장 매도비중"]=plan_df["권장 매도비중"].map(lambda x:f"{x}%")
        st.dataframe(plan_df,use_container_width=True,hide_index=True)
    else:
        st.info("현재 차트에서는 위쪽 수익구간을 안정적으로 계산하기 어렵습니다.")

    st.markdown('<div class="section-title">③ 상황별 대응</div>',unsafe_allow_html=True)
    plans=[
        {"상황":"A · 예상대로 상승","대응":"보유 · 새 의미저점이 높아지면 방어선도 올림"},
        {"상황":"B · A 주변 흔들기","대응":"즉시 손절 금지 · A 회복/추가 신저점 확인"},
        {"상황":"C · 실제 붕괴","대응":"A 미회복 + 추가 신저점이면 손절 · C 또는 새 추세전환 대기"},
        {"상황":"상승 후 구조 붕괴","대응":"직전 의미저점 붕괴 + 능선 돌파 실패 시 수익보호 매도"},
    ]
    st.dataframe(pd.DataFrame(plans),use_container_width=True,hide_index=True)

    st.markdown('<div class="section-title">④ ONE 종목 차트</div>',unsafe_allow_html=True)
    bars=st.radio("차트 기간",options=[60,120,250],index=1,horizontal=True,key="one_bars")
    svg=candle_svg(df,A=A,B=B,C=C,R=R,trigger=trigger,bars=bars)
    if svg:
        st.markdown(svg,unsafe_allow_html=True)
        st.caption("상승봉 빨강 · 하락봉 파랑 · A/최근방어저점/C/큰능선/진입대기선을 한 차트에 표시")
    else:
        st.warning("차트를 표시할 데이터가 없습니다.")

    st.markdown('<div class="section-title">⑤ 오늘 한 줄</div>',unsafe_allow_html=True)
    if one["state"].startswith("A"):
        st.success(f"{name}: A {won(A['low'])} 지지 확인 중. {won(trigger)} 돌파 확인 시 진입 검토, 구조가 살아있는 동안 보유.")
    elif one["state"].startswith("B"):
        st.warning(f"{name}: A {won(A['low'])} 주변 B플랜. 지금은 추격보다 회복 확인이 먼저.")
    else:
        st.info(f"{name}: 아직 진입하지 않고 기다립니다.")
elif "one" in st.session_state:
    st.warning("오늘은 기준을 통과한 종목이 없습니다.")
