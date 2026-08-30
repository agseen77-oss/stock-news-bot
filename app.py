
import re, time, math, statistics
from io import StringIO
import requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="전저점 ABC 대량 타임머신 검증", layout="wide")

st.markdown("""
<style>
.block-container{max-width:1500px;padding-top:2.5rem;padding-bottom:3rem}
.big{font-size:28px;font-weight:900;margin-bottom:4px}
.sub{color:#9aa0a6;font-size:14px;line-height:1.55;margin-bottom:18px}
.good{background:#12351f;border:1px solid #225d35;border-radius:9px;padding:10px 12px}
.warn{background:#3b2d12;border:1px solid #6d5420;border-radius:9px;padding:10px 12px}
.bad{background:#3b1919;border:1px solid #733030;border-radius:9px;padding:10px 12px}
</style>
""", unsafe_allow_html=True)

HEADERS={"User-Agent":"Mozilla/5.0"}

def fmtp(x):
    try:return f"{int(round(float(x))):,}원"
    except:return "-"

@st.cache_data(ttl=3600, show_spinner=False)
def naver_universe(max_each_market=100):
    """네이버 시가총액 페이지에서 KOSPI/KOSDAQ 종목코드를 동적으로 수집."""
    out=[]
    for sosok, market in [(0,"KOSPI"),(1,"KOSDAQ")]:
        pages=max(1, math.ceil(max_each_market/50))
        for page in range(1,pages+1):
            url=f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            try:
                txt=requests.get(url,headers=HEADERS,timeout=8).text
            except Exception:
                continue
            # 종목명/코드
            for code,name in re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)</a>',txt):
                name=re.sub(r"\s+"," ",name).strip()
                if code and name and not any(x["code"]==code for x in out):
                    out.append({"code":code,"name":name,"market":market})
        # 다음 시장
    # ETF/ETN/우선주/스팩 노이즈를 최대한 제외
    bad_tokens=("ETF","ETN","스팩","우B","우C","1우","2우","3우","리츠")
    clean=[]
    for x in out:
        n=x["name"]
        if any(t in n for t in bad_tokens): continue
        if n.endswith("우"): continue
        clean.append(x)
    return clean

@st.cache_data(ttl=3600, show_spinner=False)
def daily_fast(code, count=1000):
    """네이버 차트 단일 호출. 실패 시 일별 페이지 방식 fallback."""
    url=f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={int(count)}&requestType=0"
    try:
        txt=requests.get(url,headers=HEADERS,timeout=8).text
        items=re.findall(r'<item data="([^"]+)"',txt)
        rows=[]
        for item in items:
            v=item.split("|")
            if len(v)>=6 and re.fullmatch(r"\d{8}",v[0]):
                # date|open|high|low|close|volume
                rows.append({
                    "date":pd.to_datetime(v[0],format="%Y%m%d"),
                    "open":float(v[1]),"high":float(v[2]),"low":float(v[3]),
                    "close":float(v[4]),"volume":float(v[5])
                })
        if len(rows)>=120:
            return pd.DataFrame(rows).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    except Exception:
        pass

    rows=[]
    pages=min(100,max(15,math.ceil(count/10)))
    for page in range(1,pages+1):
        try:
            txt=requests.get(
                f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}",
                headers=HEADERS,timeout=6).text
        except Exception:
            continue
        for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>",txt):
            vals=[re.sub(r"<[^>]+>","",x).replace("\xa0","").strip()
                  for x in re.findall(r"<span[^>]*>([\s\S]*?)</span>",tr)]
            vals=[v for v in vals if v]
            if len(vals)>=7 and re.match(r"\d{4}\.\d{2}\.\d{2}",vals[0]):
                def num(s):
                    try:return float(str(s).replace(",","").replace("+","").replace("-",""))
                    except:return np.nan
                rows.append({
                    "date":pd.to_datetime(vals[0].replace(".","-")),
                    "close":num(vals[1]),"open":num(vals[3]),"high":num(vals[4]),
                    "low":num(vals[5]),"volume":num(vals[6])
                })
    if not rows:return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates("date").sort_values("date").dropna().reset_index(drop=True)

def local_minima(cut, radius=6):
    a=cut.low.to_numpy(float); out=[]
    for i in range(radius,len(cut)-radius):
        if a[i] <= np.nanmin(a[i-radius:i+radius+1]):
            out.append(i)
    # 기준일 직전 20봉 신저점도 후보로 남김(미래 확인 금지)
    if len(cut)>=10:
        s=max(0,len(cut)-20)
        out.append(s+int(np.nanargmin(a[s:])))
    return sorted(set(out))

def cluster_valleys(cut, idxs, gap=18):
    if not idxs:return []
    groups=[]; cur=[idxs[0]]
    for i in idxs[1:]:
        if i-cur[-1] <= gap: cur.append(i)
        else: groups.append(cur); cur=[i]
    groups.append(cur)
    ans=[]
    for g in groups:
        s=max(0,min(g)-8); e=min(len(cut)-1,max(g)+8)
        seg=cut.iloc[s:e+1]
        j=int(seg["low"].idxmin())
        ans.append((s,e,j))
    seen=set(); out=[]
    for z in ans:
        if z[2] not in seen:
            seen.add(z[2]); out.append(z)
    return out

def deep_valleys(cut):
    n=len(cut)
    if n<160:return []
    overall_lo=float(cut.low.min()); overall_hi=float(cut.high.max())
    full=max(overall_hi-overall_lo,1)
    vals=[]
    for s,e,i in cluster_valleys(cut,local_minima(cut,6),18):
        row=cut.loc[i]; lv=float(row.low)
        pre=cut.iloc[max(0,i-100):i+1]
        post=cut.iloc[i:min(n,i+101)]   # 기준일 이전 데이터만 존재
        pre_hi=float(pre.high.max()); post_hi=float(post.high.max())
        drop=max(0,(pre_hi/lv-1)*100) if lv else 0
        rebound=max(0,(post_hi/lv-1)*100) if lv else 0
        near=cut.iloc[max(0,i-140):min(n,i+141)]
        nlo=float(near.low.min()); nhi=float(near.high.max())
        depth=1-(lv-nlo)/max(nhi-nlo,1)
        gd=1-(lv-overall_lo)/full
        left=float(cut.iloc[max(0,i-35):i].close.median()) if i else lv
        right=float(cut.iloc[i+1:min(n,i+36)].close.median()) if i+1<n else lv
        shoulder=max(0,(min(left,right)/lv-1)*100) if lv else 0
        score=(min(drop,80)/80)*20+(min(rebound,180)/180)*30+depth*20+gd*18+(min(shoulder,40)/40)*12
        if (drop>=10 or rebound>=18) and depth>=0.48:
            vals.append({"i":i,"date":row.date,"low":lv,"drop":drop,"rebound":rebound,
                         "depth":depth,"score":score})
    return vals

def select_A_C(cut):
    """현재파동 A와 그 아래 과거 C를 분리. 미래 데이터 사용 안 함."""
    cands=deep_valleys(cut)
    if not cands:return None,None,[]
    n=len(cut); cur=float(cut.iloc[-1].close)
    enriched=[]
    for x in cands:
        y=dict(x); age=n-1-int(x["i"]); y["age"]=age
        rec=1-age/120 if age<=120 else (0.35*(1-(age-120)/130) if age<=250 else 0)
        dist=max(0,(cur/y["low"]-1)*100) if y["low"] else 999
        conn=max(0,1-min(dist,120)/120)
        y["role_score"]=y["score"]*0.72+rec*14+conn*14
        enriched.append(y)
    recent=[x for x in enriched if x["age"]<=120 and (x["drop"]>=8 or x["rebound"]>=10)]
    if recent and max(x["score"] for x in recent)>=38:
        pool=recent
    else:
        pool=[x for x in enriched if x["age"]<=250 and (x["drop"]>=8 or x["rebound"]>=10)] or enriched
    A=max(pool,key=lambda x:(x["role_score"],x["score"]))
    lower=[x for x in enriched if x["i"]<A["i"] and x["low"]<A["low"]*0.995]
    C=max(lower,key=lambda x:x["low"]) if lower else None
    return A,C,enriched

def candle_features(row, vol_ma20):
    o,h,l,c=map(float,[row.open,row.high,row.low,row.close])
    rng=max(h-l,1e-9)
    body=abs(c-o)
    upper=(h-max(o,c))/rng*100
    lower=(min(o,c)-l)/rng*100
    close_pos=(c-l)/rng*100
    ret=(c/o-1)*100 if o else 0
    vr=float(row.volume/vol_ma20) if vol_ma20 and vol_ma20>0 else np.nan
    return ret,upper,lower,close_pos,vr

def one_retest_event(df, base_idx, A, C, horizon=20):
    """
    기준일 이후 A에 처음 재접근한 1개 사건만 기록해 중복을 줄인다.
    결과는 '정답 플랜'을 억지로 붙이지 않고 원시 행동/미래결과를 저장한다.
    """
    if A is None or base_idx>=len(df)-5:return None
    future=df.iloc[base_idx+1:min(len(df),base_idx+1+80)].copy().reset_index(drop=True)
    ap=float(A["low"])
    near=np.where(future.low.to_numpy(float)<=ap*1.03)[0]
    if not len(near):return None
    j=int(near[0]); row=future.iloc[j]
    low=float(row.low); close=float(row.close)
    breach=(low/ap-1)*100
    close_vs_A=(close/ap-1)*100

    hist=df.iloc[:base_idx+1+j].copy()
    vol_ma=float(hist.volume.tail(20).mean()) if len(hist)>=5 else np.nan
    day_ret,upper,lower,close_pos,vr=candle_features(row,vol_ma)

    nxt=future.iloc[j+1:min(len(future),j+1+horizon)].copy()
    if nxt.empty:return None

    def reclaim(k):
        seg=future.iloc[j:min(len(future),j+1+k)]
        return bool((seg.close>=ap).any())
    def new_low(k):
        seg=future.iloc[j+1:min(len(future),j+1+k)]
        return bool(len(seg) and float(seg.low.min())<low)
    def mx(k):
        seg=future.iloc[j+1:min(len(future),j+1+k)]
        if seg.empty:return (np.nan,np.nan)
        up=(float(seg.high.max())/close-1)*100 if close else np.nan
        dn=(float(seg.low.min())/close-1)*100 if close else np.nan
        return up,dn

    up5,dn5=mx(5); up10,dn10=mx(10); up20,dn20=mx(20)
    c_reached=False
    if C is not None and len(nxt):
        c_reached=bool(float(nxt.low.min())<=float(C["low"])*1.02)

    # 사용자 제안의 '깔끔한 상승마감/반대 붕괴'를 별도 관측변수로 기록만 한다.
    clean_up = bool(day_ret>0 and close_pos>=75 and upper<=15)
    clean_down = bool(day_ret<0 and close_pos<=25 and lower<=15)

    return {
        "event_date":row.date,"A_date":A["date"],"A":ap,
        "C":float(C["low"]) if C else np.nan,
        "breach_pct":breach,"close_vs_A_pct":close_vs_A,
        "day_ret_pct":day_ret,"upper_wick_pct":upper,"lower_wick_pct":lower,
        "close_pos_pct":close_pos,"volume_ratio":vr,
        "clean_up":clean_up,"clean_down":clean_down,
        "reclaim1":reclaim(1),"reclaim3":reclaim(3),"reclaim5":reclaim(5),
        "newlow3":new_low(3),"newlow5":new_low(5),
        "C_reached20":c_reached,
        "up5":up5,"down5":dn5,"up10":up10,"down10":dn10,"up20":up20,"down20":dn20
    }

def sample_base_indices(df, per_stock=10):
    # 최소 300봉을 보고, 이후 미래검증 80봉 확보
    lo=300; hi=len(df)-90
    if hi<=lo:return []
    raw=np.linspace(lo,hi,per_stock).astype(int)
    return sorted(set(int(x) for x in raw))

def breach_bucket(x):
    if x>=0:return "A 위 지지"
    if x>=-2:return "0~-2%"
    if x>=-4:return "-2~-4%"
    if x>=-6:return "-4~-6%"
    if x>=-8:return "-6~-8%"
    if x>=-12:return "-8~-12%"
    return "-12% 이하"

def summarize_buckets(ev):
    if ev.empty:return pd.DataFrame()
    rows=[]
    order=["A 위 지지","0~-2%","-2~-4%","-4~-6%","-6~-8%","-8~-12%","-12% 이하"]
    for b in order:
        g=ev[ev["breach_bucket"]==b]
        if g.empty:continue
        rows.append({
            "A 이탈구간":b,"사례수":len(g),
            "1일 A회복%":round(g.reclaim1.mean()*100,1),
            "3일 A회복%":round(g.reclaim3.mean()*100,1),
            "5일 A회복%":round(g.reclaim5.mean()*100,1),
            "5일내 신저점%":round(g.newlow5.mean()*100,1),
            "C접근20일%":round(g.C_reached20.mean()*100,1),
            "10일 중앙 최대상승%":round(g.up10.median(),1),
            "10일 중앙 최대하락%":round(g.down10.median(),1),
        })
    return pd.DataFrame(rows)

def condition_summary(ev):
    if ev.empty:return pd.DataFrame()
    tests=[
        ("윗꼬리 짧은 상승마감", ev.clean_up),
        ("저가권 하락마감", ev.clean_down),
        ("종가가 A 위", ev.close_vs_A_pct>=0),
        ("거래량 1.5배 이상", ev.volume_ratio>=1.5),
        ("긴 아랫꼬리(30%+)", ev.lower_wick_pct>=30),
        ("윗꼬리 짧음(15%-)", ev.upper_wick_pct<=15),
        ("고가권 마감(75%+)", ev.close_pos_pct>=75),
        ("저가권 마감(25%-)", ev.close_pos_pct<=25),
    ]
    rows=[]
    for name,mask in tests:
        g=ev[mask.fillna(False)]
        if len(g)<5:continue
        rows.append({
            "관측조건":name,"사례수":len(g),
            "3일 A회복%":round(g.reclaim3.mean()*100,1),
            "5일내 신저점%":round(g.newlow5.mean()*100,1),
            "C접근20일%":round(g.C_reached20.mean()*100,1),
            "10일 중앙 최대상승%":round(g.up10.median(),1),
            "10일 중앙 최대하락%":round(g.down10.median(),1),
        })
    return pd.DataFrame(rows).sort_values(["3일 A회복%","C접근20일%"],ascending=[False,True])

def empirical_boundary(ev):
    """A 하향 이탈 사례에서 -1~-15% 후보 경계를 실제 데이터로만 비교."""
    g=ev[ev.breach_pct<0].copy()
    if len(g)<30:return None
    candidates=[]
    for t in np.arange(-1,-15.1,-0.5):
        mild=g[g.breach_pct>=t]
        deep=g[g.breach_pct<t]
        if len(mild)<15 or len(deep)<15:continue
        # 살아남음 = 3일내 A 회복, 붕괴 위험 = 5일내 신저점 또는 C접근
        rec_gap=mild.reclaim3.mean()-deep.reclaim3.mean()
        risk_gap=(deep.newlow5.mean()+deep.C_reached20.mean())/2 - (mild.newlow5.mean()+mild.C_reached20.mean())/2
        score=rec_gap+risk_gap
        candidates.append((score,t,len(mild),len(deep),
                           mild.reclaim3.mean(),deep.reclaim3.mean(),
                           mild.newlow5.mean(),deep.newlow5.mean()))
    if not candidates:return None
    score,t,nm,nd,rm,rd,lm,ld=max(candidates,key=lambda z:z[0])
    return {
        "threshold":t,"score":score,"mild_n":nm,"deep_n":nd,
        "mild_reclaim":rm,"deep_reclaim":rd,
        "mild_newlow":lm,"deep_newlow":ld
    }

def run_bulk(stock_n=60, per_stock=8, count=1000):
    universe=naver_universe(max_each_market=max(60,stock_n))
    # 시장 균형: KOSPI/KOSDAQ 절반씩
    k1=[x for x in universe if x["market"]=="KOSPI"][:math.ceil(stock_n/2)]
    k2=[x for x in universe if x["market"]=="KOSDAQ"][:stock_n//2]
    stocks=(k1+k2)[:stock_n]

    prog=st.progress(0,text="종목 데이터를 준비합니다.")
    all_events=[]; status=[]
    total=max(1,len(stocks))
    for si,s in enumerate(stocks):
        prog.progress(si/total,text=f"{si+1}/{total} {s['name']} 과거 시세 검증 중")
        try:
            df=daily_fast(s["code"],count)
            if len(df)<420:
                status.append({"종목":s["name"],"코드":s["code"],"상태":"데이터부족","일봉수":len(df),"사건수":0})
                continue
            seen=set(); n_ev=0
            for bi in sample_base_indices(df,per_stock):
                cut=df.iloc[:bi+1].copy().reset_index(drop=True)
                A,C,_=select_A_C(cut)
                if not A:continue
                e=one_retest_event(df,bi,A,C,20)
                if not e:continue
                # 같은 A/재접근 날짜 중복 제거
                key=(str(e["A_date"].date()),str(e["event_date"].date()))
                if key in seen:continue
                seen.add(key)
                e.update({"stock":s["name"],"code":s["code"],"market":s["market"],
                          "base_date":df.iloc[bi].date})
                all_events.append(e); n_ev+=1
            status.append({"종목":s["name"],"코드":s["code"],"상태":"정상","일봉수":len(df),"사건수":n_ev})
        except Exception as ex:
            status.append({"종목":s["name"],"코드":s["code"],"상태":f"오류:{str(ex)[:35]}","일봉수":0,"사건수":0})
    prog.progress(1.0,text="대량 타임머신 검증 완료")
    ev=pd.DataFrame(all_events)
    if not ev.empty:
        ev["breach_bucket"]=ev.breach_pct.apply(breach_bucket)
    return ev,pd.DataFrame(status)

st.markdown('<div class="big">🕰️ 전저점 ABC 대량 타임머신 검증</div>',unsafe_allow_html=True)
st.markdown(
    '<div class="sub">종목을 하나씩 골라 결과를 맞추지 않습니다. 여러 종목·여러 과거시점에서 '
    '<b>A 재접근 이후 실제 행동</b>을 자동 수집해, A 위 지지 / 소폭 이탈 후 회복 / 실제 붕괴가 '
    '어디에서 갈리는지 데이터로 찾습니다. +20% 같은 고정 목표는 합격기준으로 쓰지 않습니다.</div>',
    unsafe_allow_html=True)

with st.expander("이번 검증에서 일부러 고정하지 않은 것",expanded=False):
    st.write("• 'A를 -5% 깨면 손절' 같은 숫자를 미리 넣지 않았습니다.")
    st.write("• '세력 털기'를 사실로 단정하지 않습니다. OHLC·거래량에서 보이는 행동만 기록합니다.")
    st.write("• 윗꼬리 없는 상승마감과 반대형 하락마감은 관측조건으로 비교하지만, 처음부터 정답으로 지정하지 않습니다.")
    st.write("• 미래 데이터는 A 선정에 사용하지 않고, 기준일 이후 성과 확인에만 사용합니다.")

c1,c2,c3=st.columns(3)
with c1: stock_n=st.select_slider("자동 검증 종목수",options=[30,60,90,120],value=60)
with c2: per_stock=st.select_slider("종목당 과거 기준시점",options=[6,8,10,12],value=8)
with c3: count=st.select_slider("종목당 확보 일봉",options=[700,900,1100,1300],value=1100)

run=st.button("🚀 전체 자동검증 실행",type="primary",use_container_width=True)

if run:
    with st.spinner("여러 종목의 과거 시점으로 돌아가 A 재접근 사건을 수집합니다..."):
        ev,status=run_bulk(stock_n,per_stock,count)
    st.session_state["bulk_ev"]=ev
    st.session_state["bulk_status"]=status

ev=st.session_state.get("bulk_ev")
status=st.session_state.get("bulk_status")

if ev is not None:
    st.markdown("### ① 검증 데이터 품질")
    if ev.empty:
        st.error("검증 사건을 확보하지 못했습니다. 네이버 시세 연결 상태나 종목수를 확인하세요.")
        if status is not None: st.dataframe(status,use_container_width=True,hide_index=True)
        st.stop()

    s1,s2,s3,s4=st.columns(4)
    s1.metric("확보 사건",f"{len(ev):,}건")
    s2.metric("검증 종목",f"{ev.stock.nunique():,}개")
    s3.metric("A 아래 이탈",f"{(ev.breach_pct<0).sum():,}건")
    s4.metric("A 위 지지",f"{(ev.breach_pct>=0).sum():,}건")

    st.markdown("### ② 핵심 — A를 얼마나 깨고도 다시 살아나는가")
    buck=summarize_buckets(ev)
    st.dataframe(buck,use_container_width=True,hide_index=True)

    bd=empirical_boundary(ev)
    if bd:
        st.markdown("### ③ 데이터가 제안하는 B ↔ C 경계 후보")
        t=bd["threshold"]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("경계 후보",f"A 대비 {t:.1f}%")
        c2.metric("경계 안 3일회복",f"{bd['mild_reclaim']*100:.1f}%")
        c3.metric("경계 밖 3일회복",f"{bd['deep_reclaim']*100:.1f}%")
        c4.metric("표본",f"{bd['mild_n']} / {bd['deep_n']}")
        st.info(
            "이 값은 제가 임의로 정한 손절선이 아닙니다. -1~-15% 후보를 모두 비교해 "
            "A 회복률과 추가 신저점 위험이 가장 크게 갈린 지점을 자동으로 표시한 것입니다. "
            "아직 '최종 손절선'이 아니라 다음 검증에 사용할 경계 후보입니다."
        )
    else:
        st.warning("A 하향 이탈 표본이 아직 부족해 B/C 경계를 자동 계산하지 않았습니다.")

    st.markdown("### ④ 봉·거래량 조건이 실제로 구분력이 있는가")
    cond=condition_summary(ev)
    if not cond.empty:
        st.dataframe(cond,use_container_width=True,hide_index=True)
    else:
        st.info("조건별 최소 표본이 부족합니다.")

    st.markdown("### ⑤ 제가 자동으로 내리는 현재 판정")
    # Conservative automated verdict
    if bd and len(ev)>=120 and ev.stock.nunique()>=20:
        gap=(bd["mild_reclaim"]-bd["deep_reclaim"])*100
        if gap>=20:
            st.success(
                f"계속 진행 가치 있음: A 이탈 깊이에 따라 3일 내 회복률 차이가 {gap:.1f}%p로 나타났습니다. "
                "다음 단계는 이 경계에 종가위치·윗/아랫꼬리·거래량을 결합해 오판을 줄이는 것입니다."
            )
        else:
            st.warning(
                f"이탈폭만으로는 부족: 경계 안/밖 회복률 차이가 {gap:.1f}%p입니다. "
                "봉 모양과 거래량이 구분력을 추가하는지 ④ 표를 우선 봐야 합니다."
            )
    else:
        st.warning("아직 표본이 부족하거나 경계가 뚜렷하지 않습니다. 숫자를 억지로 확정하지 않습니다.")

    st.markdown("### ⑥ 원자료")
    cols=["stock","market","base_date","A_date","A","C","event_date","breach_pct","close_vs_A_pct",
          "day_ret_pct","upper_wick_pct","lower_wick_pct","close_pos_pct","volume_ratio",
          "clean_up","clean_down","reclaim1","reclaim3","reclaim5","newlow5","C_reached20",
          "up5","down5","up10","down10","up20","down20"]
    show=ev[cols].copy()
    for c in ["base_date","A_date","event_date"]:
        show[c]=pd.to_datetime(show[c]).dt.strftime("%Y-%m-%d")
    st.dataframe(show,use_container_width=True,hide_index=True,height=420)
    st.download_button(
        "검증 원자료 CSV 다운로드",
        data=show.to_csv(index=False).encode("utf-8-sig"),
        file_name="abc_bulk_validation.csv",
        mime="text/csv",
        use_container_width=True
    )

    with st.expander("종목별 데이터 수집 상태"):
        st.dataframe(status,use_container_width=True,hide_index=True)

st.caption("A 선정에는 기준일 이전 데이터만 사용 · 기준일 이후 데이터는 재접근/회복/붕괴 검증에만 사용")
