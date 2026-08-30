
import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="A/B 회복 후 진짜 상승 검증", layout="wide")
st.title("🧭 A/B 회복 후 진짜 상승 검증")
st.caption("A를 다시 회복했다는 사실만으로 보유하지 않습니다. 회복 뒤 실제 상승 지속과 재붕괴를 분리합니다.")

up = st.file_uploader("V11 원자료 CSV", type=["csv"])
if up is None:
    st.info("V11에서 내려받은 abc_bulk_validation.csv를 넣어주세요.")
    st.stop()

df=pd.read_csv(up)
need=["breach_pct","close_vs_A_pct","day_ret_pct","upper_wick_pct","lower_wick_pct",
      "close_pos_pct","volume_ratio","reclaim1","reclaim3","newlow5","C_reached20",
      "up5","down5","up10","down10","up20","down20"]
miss=[c for c in need if c not in df.columns]
if miss:
    st.error("필요한 열이 없습니다: "+", ".join(miss)); st.stop()

for c in ["reclaim1","reclaim3","newlow5","C_reached20"]:
    if df[c].dtype==object:
        df[c]=df[c].astype(str).str.lower().map({"true":True,"false":False}).fillna(False)

def today_plan(r):
    close_a=float(r.close_vs_A_pct); close_pos=float(r.close_pos_pct)
    upper=float(r.upper_wick_pct); lower=float(r.lower_wick_pct)
    dayret=float(r.day_ret_pct)
    vr=float(r.volume_ratio) if pd.notna(r.volume_ratio) else 1.0
    recovery=danger=0
    if close_a>=0: recovery+=3
    if close_pos>=70: recovery+=2
    if lower>=30: recovery+=1
    if dayret>0: recovery+=1
    if upper<=15: recovery+=1
    if vr>=1.5 and close_pos>=55: recovery+=1
    if close_a<0: danger+=2
    if close_pos<=30: danger+=2
    if dayret<0: danger+=1
    if lower<=12 and close_pos<=35: danger+=1
    if vr>=1.5 and close_pos<=35: danger+=1
    if close_a>=0 and recovery>=danger+2: return "A"
    if close_a<0 and close_pos<=30 and danger>=recovery+2: return "C"
    if recovery>=danger or lower>=30 or close_pos>=55: return "B"
    return "관찰"

df["plan"]=df.apply(today_plan,axis=1)
ab=df[df.plan.isin(["A","B"])].copy()

# Outcome definitions are descriptive, not fixed-profit trading targets.
# "상승 지속": 10일 MFE >= +5% and 10일 MAE > -5%
# "강한 상승": 20일 MFE >= +10%
# "재붕괴": 5일 신저점 AND 10일 MAE <= -5%
ab["상승지속"]=(ab.up10>=5) & (ab.down10>-5)
ab["강한상승"]=(ab.up20>=10)
ab["재붕괴"]=(ab.newlow5) & (ab.down10<=-5)

c1,c2,c3,c4=st.columns(4)
c1.metric("A/B 사례",len(ab))
c2.metric("10일 상승지속",f"{ab.상승지속.mean()*100:.1f}%")
c3.metric("20일 +10% 이상",f"{ab.강한상승.mean()*100:.1f}%")
c4.metric("5일 신저점+10일 -5%",f"{ab.재붕괴.mean()*100:.1f}%")

st.subheader("① A와 B를 따로 보면")
rows=[]
for p,g in ab.groupby("plan"):
    rows.append({"구분":p,"사례수":len(g),
                 "10일 상승지속%":round(g.상승지속.mean()*100,1),
                 "20일 +10%%":round(g.강한상승.mean()*100,1),
                 "재붕괴%":round(g.재붕괴.mean()*100,1),
                 "10일 중앙상승%":round(g.up10.median(),1),
                 "10일 중앙하락%":round(g.down10.median(),1)})
st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

st.subheader("② 당일 어떤 모습이 회복 후 상승을 더 잘 구분했나")
tests=[
 ("종가 A 위",ab.close_vs_A_pct>=0),
 ("고가권 마감 70%+",ab.close_pos_pct>=70),
 ("긴 아랫꼬리 30%+",ab.lower_wick_pct>=30),
 ("윗꼬리 15% 이하",ab.upper_wick_pct<=15),
 ("당일 상승마감",ab.day_ret_pct>0),
 ("거래량 1.5배+",ab.volume_ratio>=1.5),
 ("A 위+고가권", (ab.close_vs_A_pct>=0)&(ab.close_pos_pct>=70)),
 ("상승+고가권+짧은윗꼬리",(ab.day_ret_pct>0)&(ab.close_pos_pct>=70)&(ab.upper_wick_pct<=15)),
 ("긴아랫꼬리+종가A위",(ab.lower_wick_pct>=30)&(ab.close_vs_A_pct>=0)),
]
rows=[]
for name,m in tests:
    g=ab[m.fillna(False)]
    if len(g)<15: continue
    rows.append({"당일조건":name,"사례수":len(g),
                 "10일 상승지속%":round(g.상승지속.mean()*100,1),
                 "20일 +10%%":round(g.강한상승.mean()*100,1),
                 "재붕괴%":round(g.재붕괴.mean()*100,1),
                 "10일 중앙상승%":round(g.up10.median(),1),
                 "10일 중앙하락%":round(g.down10.median(),1)})
res=pd.DataFrame(rows)
if not res.empty:
    res=res.sort_values(["10일 상승지속%","재붕괴%"],ascending=[False,True])
    st.dataframe(res,use_container_width=True,hide_index=True)

st.subheader("③ 결론")
base=ab.상승지속.mean()*100
if not res.empty:
    best=res.iloc[0]
    lift=float(best["10일 상승지속%"])-base
    if best["사례수"]>=30 and lift>=10 and best["재붕괴%"]<=25:
        st.success(f"구분력 있음: '{best['당일조건']}'에서 상승지속률이 A/B 전체보다 {lift:.1f}%p 높습니다. 다음 독립검증 후보입니다.")
    else:
        st.warning("현재 당일 봉/거래량만으로는 'A 회복 후 진짜 상승'을 충분히 가르지 못합니다. 억지 조건 추가는 하지 않습니다.")
else:
    st.warning("표본이 부족합니다.")

st.subheader("④ 사례 원자료")
cols=["stock","market","base_date","A_date","A","C","event_date","plan","breach_pct","close_vs_A_pct",
      "day_ret_pct","upper_wick_pct","lower_wick_pct","close_pos_pct","volume_ratio",
      "reclaim3","newlow5","up5","down5","up10","down10","up20","down20","상승지속","강한상승","재붕괴"]
cols=[c for c in cols if c in ab.columns]
st.dataframe(ab[cols],use_container_width=True,hide_index=True,height=450)
