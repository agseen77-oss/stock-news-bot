import re, math, requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Stock Compass V4 · 후보조건 선별", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0"}

st.title("🧪 Stock Compass V4 · 후보조건 선별")
st.caption("V3는 건드리지 않습니다. A/B 회복 뒤 실제 상승 지속과 재붕괴를 더 잘 가르는 조건만 검증합니다.")

@st.cache_data(ttl=3600,show_spinner=False)
def universe(limit_each=120):
    out=[]
    for sosok,market in [(0,"KOSPI"),(1,"KOSDAQ")]:
        for page in range(1,max(2,math.ceil(limit_each/50)+1)):
            try:
                txt=requests.get(f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}",headers=HEADERS,timeout=8).text
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
        txt=requests.get(f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={count}&requestType=0",headers=HEADERS,timeout=8).text
        rows=[]
        for item in re.findall(r'<item data="([^"]+)"',txt):
            v=item.split("|")
            if len(v)>=6:
                rows.append([pd.to_datetime(v[0],format="%Y%m%d"),float(v[1]),float(v[2]),float(v[3]),float(v[4]),float(v[5])])
        df=pd.DataFrame(rows,columns=["date","open","high","low","close","volume"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
        if df.empty:return df
        return df[(df.open>0)&(df.high>0)&(df.low>0)&(df.close>0)].reset_index(drop=True)
    except:return pd.DataFrame()

def pivots(a,kind="high",r=5):
    x=np.asarray(a,float); out=[]
    for i in range(r,len(x)-r):
        w=x[i-r:i+r+1]
        if (kind=="high" and x[i]>=np.max(w)) or (kind=="low" and x[i]<=np.min(w)): out.append(i)
    return out

def meaningful_A(hist):
    lows=pivots(hist.low,"low",6)
    if not lows:return None
    n=len(hist); vals=[]
    for i in lows:
        lv=float(hist.iloc[i].low)
        if lv<=0:continue
        pre=hist.iloc[max(0,i-80):i+1]; post=hist.iloc[i:min(n,i+61)]
        drop=(float(pre.high.max())/lv-1)*100
        rebound=(float(post.high.max())/lv-1)*100
        age=n-1-i
        if (drop>=8 or rebound>=15) and age<=120:
            score=min(drop,60)+min(rebound,100)*.7+(120-age)*.08
            vals.append((score,i,lv))
    if not vals:return None
    _,i,lv=max(vals)
    return i,lv

def descending_line(hist):
    """Return current projected descending resistance using last 2-4 meaningful lower highs.
       This is a TEST FEATURE only, not a proven rule."""
    hs=pivots(hist.high,"high",5)
    hs=[i for i in hs if i>=max(0,len(hist)-140)]
    if len(hs)<2:return None
    # Search recent pairs where later high is lower, favor separation and recency.
    pairs=[]
    for a in range(max(0,len(hs)-7),len(hs)-1):
        for b in range(a+1,len(hs)):
            i1,i2=hs[a],hs[b]
            h1,h2=float(hist.iloc[i1].high),float(hist.iloc[i2].high)
            if i2-i1>=8 and h2<h1*.995:
                slope=(h2-h1)/(i2-i1)
                proj=h2+slope*((len(hist)-1)-i2)
                if proj>0:
                    pairs.append((i2, i2-i1, i1,i2,h1,h2,proj,slope))
    if not pairs:return None
    _,_,i1,i2,h1,h2,proj,slope=max(pairs,key=lambda x:(x[0],x[1]))
    return {"i1":i1,"i2":i2,"h1":h1,"h2":h2,"proj":proj,"slope":slope}

def features_at(df,t):
    hist=df.iloc[:t+1].copy()
    if len(hist)<180:return None
    A=meaningful_A(hist)
    if not A:return None
    ai,av=A
    r=hist.iloc[-1]; rng=max(float(r.high-r.low),1e-9)
    cp=(float(r.close-r.low)/rng)*100
    uw=(float(r.high-max(r.open,r.close))/rng)*100
    lw=(float(min(r.open,r.close)-r.low)/rng)*100
    vr=float(r.volume/max(hist.volume.tail(21).iloc[:-1].mean(),1))
    close_a=(float(r.close/av)-1)*100
    # Same-day A/B style gate: no future information.
    recovery=(close_a>=0 and (cp>=55 or lw>=30 or r.close>=r.open))
    shake=(close_a<0 and (lw>=30 or cp>=55))
    if not (recovery or shake): return None

    tl=descending_line(hist)
    tl_dist=np.nan; tl_break=False; tl_near=False
    if tl:
        tl_dist=(float(r.close)/tl["proj"]-1)*100
        tl_break=bool(float(r.close)>tl["proj"])
        tl_near=bool(-4<=tl_dist<=2)

    ma20=hist.close.rolling(20).mean()
    ma60=hist.close.rolling(60).mean()
    ma120=hist.close.rolling(120).mean()
    ma20_up=bool(len(hist)>=25 and ma20.iloc[-1]>ma20.iloc[-6])
    ma60_up=bool(len(hist)>=65 and ma60.iloc[-1]>ma60.iloc[-6])
    above60=bool(r.close>ma60.iloc[-1]) if np.isfinite(ma60.iloc[-1]) else False
    above120=bool(r.close>ma120.iloc[-1]) if np.isfinite(ma120.iloc[-1]) else False

    # Time-efficiency proxies: recent range compression + recent rebound speed.
    h20=float(hist.high.tail(20).max()); l20=float(hist.low.tail(20).min())
    compression20=(h20/l20-1)*100 if l20>0 else np.nan
    ret5=(float(r.close/hist.iloc[-6].close)-1)*100 if len(hist)>=6 else np.nan
    ret10=(float(r.close/hist.iloc[-11].close)-1)*100 if len(hist)>=11 else np.nan

    return dict(A=av,close_a=close_a,cp=cp,uw=uw,lw=lw,vr=vr,
                tl_exists=tl is not None,tl_dist=tl_dist,tl_break=tl_break,tl_near=tl_near,
                ma20_up=ma20_up,ma60_up=ma60_up,above60=above60,above120=above120,
                compression20=compression20,ret5=ret5,ret10=ret10)

def outcome(df,t):
    if t+20>=len(df):return None
    base=float(df.iloc[t].close)
    f5=df.iloc[t+1:t+6]; f10=df.iloc[t+1:t+11]; f20=df.iloc[t+1:t+21]
    return dict(
        up10=(float(f10.high.max())/base-1)*100,
        down10=(float(f10.low.min())/base-1)*100,
        up20=(float(f20.high.max())/base-1)*100,
        down20=(float(f20.low.min())/base-1)*100,
        newlow5=bool(float(f5.low.min())<float(df.iloc[t].low)),
    )

def summarize(g):
    if len(g)==0:return None
    return {
        "표본":len(g),
        "10일 +5% 도달":(g.up10>=5).mean()*100,
        "20일 +10% 도달":(g.up20>=10).mean()*100,
        "10일 -5% 이내":(g.down10>-5).mean()*100,
        "5일 신저점":g.newlow5.mean()*100,
        "중앙 up10":g.up10.median(),
        "중앙 down10":g.down10.median(),
    }

def run(nstocks,step):
    u=universe(max(80,math.ceil(nstocks/2)))
    ks=[x for x in u if x["market"]=="KOSPI"][:math.ceil(nstocks/2)]
    kq=[x for x in u if x["market"]=="KOSDAQ"][:nstocks//2]
    pool=(ks+kq)[:nstocks]
    rows=[]; bar=st.progress(0,text="과거 시점 검증 중...")
    for k,s in enumerate(pool):
        bar.progress((k+1)/max(len(pool),1),text=f"{k+1}/{len(pool)} {s['name']}")
        df=daily(s["code"],900)
        if len(df)<300:continue
        # Multiple historical cutoffs, no future used in features.
        for t in range(max(180,len(df)-420),len(df)-21,step):
            f=features_at(df,t)
            if not f:continue
            o=outcome(df,t)
            if not o:continue
            rows.append({"code":s["code"],"name":s["name"],"market":s["market"],"date":df.iloc[t].date,**f,**o})
    return pd.DataFrame(rows)

c1,c2=st.columns(2)
n=c1.select_slider("검증 종목수",options=[40,60,100,150],value=60)
step=c2.select_slider("과거 시점 간격(거래일)",options=[5,10,15,20],value=10)

if st.button("▶ 후보조건 선별 시작",type="primary",use_container_width=True):
    df=run(n,step)
    st.session_state["v4df"]=df

df=st.session_state.get("v4df")
if isinstance(df,pd.DataFrame) and not df.empty:
    st.success(f"완료 · {df['name'].nunique()}종목 / {len(df):,}사건")

    tests = {
        "전체 A/B 회복": pd.Series(True,index=df.index),
        "하락추세선 존재": df.tl_exists,
        "추세선 4% 이내 접근": df.tl_exists & df.tl_near,
        "추세선 종가 돌파": df.tl_exists & df.tl_break,
        "돌파 + 거래량 1.3배": df.tl_exists & df.tl_break & (df.vr>=1.3),
        "고가권 종가 70%+": df.cp>=70,
        "윗꼬리 15% 이하": df.uw<=15,
        "거래량 1.5배+": df.vr>=1.5,
        "20MA 상승": df.ma20_up,
        "60MA 상승": df.ma60_up,
        "60MA 위": df.above60,
        "120MA 위": df.above120,
        "20일 변동폭 15% 이하": df.compression20<=15,
        "최근5일 +3% 이상": df.ret5>=3,
        "추세선 접근 + 고가권": df.tl_exists & df.tl_near & (df.cp>=70),
        "추세선 돌파 + 고가권": df.tl_exists & df.tl_break & (df.cp>=70),
    }
    base=summarize(df)
    out=[]
    for name,mask in tests.items():
        g=df[mask.fillna(False)]
        z=summarize(g)
        if not z:continue
        z["조건"]=name
        z["10일+5 개선"]=z["10일 +5% 도달"]-base["10일 +5% 도달"]
        z["재붕괴 개선"]=base["5일 신저점"]-z["5일 신저점"]
        out.append(z)
    res=pd.DataFrame(out)
    res["종합개선"]=res["10일+5 개선"]+res["재붕괴 개선"]
    res=res.sort_values(["종합개선","표본"],ascending=[False,False])

    st.subheader("1. 후보조건 순위")
    st.dataframe(res[["조건","표본","10일 +5% 도달","20일 +10% 도달","5일 신저점","중앙 up10","중앙 down10","10일+5 개선","재붕괴 개선","종합개선"]],
                 use_container_width=True,hide_index=True)

    # Conservative promotion rule: enough sample + improves both upside and rebreak.
    promoted=res[(res["표본"]>=40)&(res["10일+5 개선"]>2)&(res["재붕괴 개선"]>2)]
    st.subheader("2. V3 장착 후보")
    if promoted.empty:
        st.warning("현재 조건 중 V3에 바로 장착할 만큼 동시에 개선된 조건이 없습니다. V3는 그대로 유지합니다.")
    else:
        st.dataframe(promoted[["조건","표본","10일+5 개선","재붕괴 개선","종합개선"]],use_container_width=True,hide_index=True)
        st.caption("여기 나온 조건도 곧바로 핵심 매수규칙으로 확정하지 않습니다. 다음 독립구간 확인 후 액세서리/필터/핵심엔진 중 역할을 정합니다.")

    st.subheader("3. 원자료")
    st.download_button("CSV 내려받기",df.to_csv(index=False).encode("utf-8-sig"),"V4_candidate_screen_raw.csv","text/csv")
    st.dataframe(df.tail(200),use_container_width=True,hide_index=True)
else:
    st.info("검증을 실행하면 하락추세선·거래량·MA·고가권 종가·압축/속도를 같은 과거 사건에서 비교합니다.")
