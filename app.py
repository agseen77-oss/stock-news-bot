
import re, math, requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Stock Compass · ONE", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0"}

st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:2.0rem}
h1{margin-bottom:.2rem}
.card{border:1px solid #343a40;border-radius:12px;padding:14px;margin:8px 0}
.good{background:#12351f;border:1px solid #275e39;border-radius:10px;padding:12px}
.warn{background:#3b2e12;border:1px solid #6d5520;border-radius:10px;padding:12px}
.bad{background:#3b1919;border:1px solid #713232;border-radius:10px;padding:12px}
.small{color:#9aa0a6;font-size:13px}
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
        return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
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
        pre=df.iloc[max(0,i-90):i+1]
        post=df.iloc[i:min(n,i+91)]
        drop=(float(pre.high.max())/lv-1)*100
        rebound=(float(post.high.max())/lv-1)*100
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
    df=daily(s["code"],900)
    if len(df)<300:return None
    stc=structure(df)
    if not stc:return None
    A,B,C,ridge=stc
    state,ca,cp,uw,lw,vr,rec,dng=candle_state(df,A)
    score,dist=candidate_score(df,A,B,C,ridge,state,(ca,cp,uw,lw,vr,rec,dng))
    return {"stock":s,"df":df,"A":A,"B":B,"C":C,"ridge":ridge,"state":state,
            "score":score,"dist":dist,"close_a":ca,"cp":cp,"uw":uw,"lw":lw,"vr":vr}

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

st.title("🎯 STOCK COMPASS · ONE")
st.caption("여러 종목을 보여주지 않습니다. 뒤에서 전부 비교하고, 기준을 통과한 가장 강한 1종목만 보여줍니다. 없으면 '오늘 후보 없음'입니다.")

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

    st.success(f"오늘의 ONE · {name} ({one['stock']['market']})")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("현재가",won(cur))
    c2.metric("핵심 A",won(A["low"]))
    c3.metric("현재 상태",one["state"])
    c4.metric("선정점수",f"{one['score']:.1f}")

    st.subheader("① 지금 행동")
    if one["state"].startswith("A"):
        action="A플랜 · A가 지켜지고 회복행동이 우세합니다. 신규 진입은 당일 고가 돌파/다음 봉 지지 확인 후, 보유자는 유지."
    elif one["state"].startswith("B"):
        action="B플랜 · A 주변 흔들림입니다. 추격매수 금지. A 재회복과 추가 신저점 여부를 확인."
    else:
        action="관찰 · 아직 돈을 넣지 않습니다."
    st.info(action)

    # 진입 트리거는 현재 봉의 고가: 돌파 전에는 '진입대기 가격'으로만 표시.
    trigger=float(df.iloc[-1].high)
    st.subheader("② 가격별 대응계획")
    rows=[
        {"구분":"진입 대기선","가격":won(trigger),"행동":"현재 회복봉 고가를 넘어설 때만 진입 검토"},
        {"구분":"A 핵심 전저점","가격":won(A["low"]),"행동":"핵심 지지선. 단순 장중 이탈만으로 즉시 손절하지 않음"},
        {"구분":"최근 방어저점","가격":won(B["low"]),"행동":"상승 후 새 저점이 높아지면 이 방어선을 계속 위로 갱신"},
    ]
    if R: rows.append({"구분":"위쪽 큰 능선","가격":won(R["high"]),"행동":"1차 매도 판단구간. 돌파·안착하면 계속 보유"})
    if C: rows.append({"구분":"하단 C","가격":won(C["low"]),"행동":"A 실제 붕괴·손절 후 다음 관찰구간"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

    st.subheader("③ A / B / C 상황별 대책")
    plans=[
        {"상황":"A · 예상대로 상승","대응":"보유. 새 의미저점이 높아질 때마다 방어선을 올림. 큰 능선 돌파·안착 시 계속 보유."},
        {"상황":"B · A 주변 흔들기","대응":"즉시 손절하지 않음. 종가 위치·꼬리·거래량·A 회복 여부 확인. 추가 신저점이 없으면 관찰보유."},
        {"상황":"C · 실제 붕괴","대응":"A 미회복 + 추가 신저점이면 일단 손절. 종목은 삭제하지 않고 하단 C 또는 그 전 새 추세전환 대기."},
        {"상황":"상승 후 구조 붕괴","대응":"고정 수익률이 아니라 직전 높아진 의미저점이 깨지고 능선 돌파도 실패하면 수익보호 매도."},
    ]
    st.dataframe(pd.DataFrame(plans),use_container_width=True,hide_index=True)

    st.subheader("④ 일반 봉차트")
    # Streamlit native chart only: external plotly/matplotlib dependency 없음.
    chart=df.tail(120).set_index("date")[["open","high","low","close"]]
    try:
        st.line_chart(chart[["close"]],height=360)
        st.caption("현재 배포환경 호환성을 우선한 종가차트입니다. 본체 결합 시 기존 일반 봉차트 모듈에 A/능선/C 표식을 연결합니다.")
    except:
        st.dataframe(chart.tail(30),use_container_width=True)

    st.subheader("⑤ 오늘 한 줄")
    if one["state"].startswith("A"):
        st.success(f"{name}: A {won(A['low'])} 지지 확인 중. {won(trigger)} 돌파 확인 시 진입 검토, 구조가 살아있는 동안 보유.")
    elif one["state"].startswith("B"):
        st.warning(f"{name}: A {won(A['low'])} 주변 B플랜. 지금은 추격보다 회복 확인이 먼저.")
    else:
        st.info(f"{name}: 아직 진입하지 않고 기다립니다.")
elif "one" in st.session_state:
    st.warning("오늘은 기준을 통과한 종목이 없습니다.")
