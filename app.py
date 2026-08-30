import re
import html
from pathlib import Path
import requests
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates

st.set_page_config(page_title='전저점 A + 지지/이탈 타임머신 검증', layout='wide')
st.markdown('''
<style>
html,body,[class*="css"]{font-family:Arial,"Malgun Gothic",sans-serif}
.block-container{max-width:1450px;padding-top:4.5rem;padding-bottom:3rem}
h1,h2,h3{line-height:1.35!important;margin-top:.45rem!important}
.main-title{font-size:30px;font-weight:900;line-height:1.45;margin:8px 0 10px 0;padding-top:4px;overflow:visible}
.sub{color:#9aa0a6;font-size:14px;line-height:1.55;margin-bottom:14px}
.note{border:1px solid #3a3f47;border-radius:12px;padding:12px 14px;margin:8px 0;line-height:1.55}
.good{background:#12351f;border:1px solid #225d35;border-radius:10px;padding:10px 12px}
.warn{background:#3b2d12;border:1px solid #6d5420;border-radius:10px;padding:10px 12px}
.bad{background:#3b1919;border:1px solid #733030;border-radius:10px;padding:10px 12px}
</style>
''', unsafe_allow_html=True)

DEFAULT_CODES={
 '후성':'093370','미래반도체':'254490','켐트로스':'220260','삼성전자':'005930','SK하이닉스':'000660',
 '제룡전기':'033100','에스피시스템스':'317830','LG디스플레이':'034220','리노공업':'058470',
 '테크윙':'089030','원익IPS':'240810','솔브레인':'357780','솔브레인홀딩스':'036830'
}

def pp(x):
    try:return f'{int(round(float(x))):,}원'
    except:return '-'

def pct(x):
    try:return f'{float(x):.1f}%'
    except:return '-'

@st.cache_data(ttl=3600, show_spinner=False)
def naver_daily(code:str,pages:int=100):
    headers={'User-Agent':'Mozilla/5.0'}; rows=[]
    for page in range(1,pages+1):
        url=f'https://finance.naver.com/item/sise_day.naver?code={code}&page={page}'
        try:
            txt=requests.get(url,headers=headers,timeout=5).text
        except Exception:
            continue
        for tr in re.findall(r'<tr[^>]*>([\s\S]*?)</tr>',txt):
            vals=[re.sub(r'<[^>]+>','',x).replace('\xa0','').strip() for x in re.findall(r'<span[^>]*>([\s\S]*?)</span>',tr)]
            vals=[v for v in vals if v]
            if len(vals)>=7 and re.match(r'\d{4}\.\d{2}\.\d{2}',vals[0]):
                def num(s):
                    try:return float(str(s).replace(',','').replace('+','').replace('-',''))
                    except:return np.nan
                rows.append({'date':vals[0].replace('.','-'),'close':num(vals[1]),'open':num(vals[3]),'high':num(vals[4]),'low':num(vals[5]),'volume':num(vals[6])})
    if not rows:return pd.DataFrame()
    df=pd.DataFrame(rows).drop_duplicates('date').sort_values('date')
    df['date']=pd.to_datetime(df['date'])
    for c in ['open','high','low','close','volume']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['open','high','low','close']).reset_index(drop=True)

def low_hierarchy(cut):
    out=[]
    for d in [5,10,20,60,120,250,500]:
        x=cut.tail(min(d,len(cut)))
        j=x['low'].idxmin(); r=cut.loc[j]
        out.append({'days':d,'date':r.date,'low':float(r.low)})
    return out

def local_minima(cut, radius=6):
    a=cut.low.to_numpy(float); out=[]
    for i in range(radius, len(cut)-radius):
        if np.isfinite(a[i]) and a[i] <= np.nanmin(a[i-radius:i+radius+1]):
            out.append(i)
    # 최근 신저점은 미래 봉 확인을 기다리지 않고 후보군에는 포함
    if len(cut)>=8:
        s=max(0,len(cut)-20); j=s+int(np.nanargmin(a[s:]))
        out.append(j)
    return sorted(set(out))

def cluster_valleys(cut, idxs, gap=18):
    """가까운 저점들을 한 계곡 구간으로 묶고 그 구간의 실제 최저 Low를 대표 A 후보로 사용."""
    if not idxs:return []
    groups=[]; cur=[idxs[0]]
    for i in idxs[1:]:
        if i-cur[-1] <= gap: cur.append(i)
        else: groups.append(cur); cur=[i]
    groups.append(cur)
    vals=[]
    for g in groups:
        s=max(0,min(g)-8); e=min(len(cut)-1,max(g)+8)
        seg=cut.iloc[s:e+1]
        j=int(seg.low.idxmin())
        vals.append((s,e,j))
    # 중복 대표 제거
    seen=set(); out=[]
    for x in vals:
        if x[2] not in seen:
            seen.add(x[2]); out.append(x)
    return out

def deep_valley_candidates(cut):
    n=len(cut)
    if n<120:return []
    overall_lo=float(cut.low.min()); overall_hi=float(cut.high.max()); full=max(overall_hi-overall_lo,1)
    clusters=cluster_valleys(cut, local_minima(cut,6), gap=18)
    vals=[]
    for s,e,i in clusters:
        row=cut.loc[i]; lv=float(row.low)
        pre=cut.iloc[max(0,i-100):i+1]
        post=cut.iloc[i:min(n,i+101)]
        pre_hi=float(pre.high.max()); post_hi=float(post.high.max())
        drop=max(0,(pre_hi/lv-1)*100) if lv else 0
        rebound=max(0,(post_hi/lv-1)*100) if lv else 0
        near=cut.iloc[max(0,i-140):min(n,i+141)]
        near_lo=float(near.low.min()); near_hi=float(near.high.max())
        depth=1-(lv-near_lo)/max(near_hi-near_lo,1)
        global_depth=1-(lv-overall_lo)/full
        # 계곡 주변에서 좌우 가격대보다 얼마나 낮은지
        left_med=float(cut.iloc[max(0,i-35):i].close.median()) if i>0 else lv
        right_med=float(cut.iloc[i+1:min(n,i+36)].close.median()) if i+1<n else lv
        shoulder=max(0, ((min(left_med,right_med)/lv)-1)*100) if lv else 0
        score=(min(drop,80)/80)*20 + (min(rebound,180)/180)*30 + depth*20 + global_depth*18 + (min(shoulder,40)/40)*12
        if (drop>=10 or rebound>=18) and depth>=0.48:
            vals.append({'i':i,'date':row.date,'low':lv,'drop':drop,'rebound':rebound,'depth':depth,
                         'global_depth':global_depth,'shoulder':shoulder,'score':score,'zone_start':s,'zone_end':e})
    return sorted(vals,key=lambda x:x['score'],reverse=True)

def select_A(cut):
    cands=deep_valley_candidates(cut)
    if not cands:return None,cands
    # 점수가 비슷하면 더 깊은 실제 저가를 우선. 최근성 자체는 가점하지 않음.
    best=cands[0]['score']
    pool=[x for x in cands if x['score']>=best-8]
    A=min(pool,key=lambda x:(x['low'],-x['score']))
    return A,cands

def previous_lower_valley(cut,A,cands):
    if not A:return None
    older=[x for x in cands if x['i']<A['i'] and x['low']<A['low']*0.995]
    if not older:return None
    # A 바로 아래 가격의 의미계곡을 다음 방어선으로 봄
    return max(older,key=lambda x:x['low'])

def broad_direction(cut):
    x=cut.tail(min(500,len(cut)))
    if len(x)<160:return '판단보류'
    q=max(50,len(x)//3)
    a=x.iloc[:q]; b=x.iloc[-q:]
    lo1=float(a.low.quantile(.1)); lo2=float(b.low.quantile(.1)); hi1=float(a.high.quantile(.9)); hi2=float(b.high.quantile(.9))
    if lo2>lo1*1.06 and hi2>hi1*1.06:return '우상향'
    if lo2<lo1*0.94 and hi2<hi1*0.94:return '우하향'
    return '횡보/혼조'

def reversal_confirm(seg, low_pos, a_price):
    """저점 이후 '단순 하루 반등'이 아닌 구조적 회복 확인: 3봉 이상 지나고 이전 5봉 고점 돌파."""
    if low_pos is None:return None
    for j in range(low_pos+3, len(seg)):
        prev=seg.iloc[max(low_pos,j-5):j]
        if len(prev)<2:continue
        trigger=float(prev.high.max())
        if float(seg.iloc[j].close)>trigger and float(seg.iloc[j].close)>float(seg.iloc[j].open):
            return j
    return None

def analyze_future_retest(df, base_idx, A, C, max_future=180):
    if A is None or base_idx>=len(df)-1:return {'status':'미래구간 없음'}
    future=df.iloc[base_idx+1:min(len(df),base_idx+1+max_future)].copy().reset_index(drop=True)
    if future.empty:return {'status':'미래구간 없음'}
    ap=float(A['low'])
    # A의 +8% 이내에 처음 접근한 날부터 관찰. 이 수치는 진입조건이 아니라 관찰 시작선.
    approach=np.where(future.low.to_numpy(float)<=ap*1.08)[0]
    if len(approach)==0:
        return {'status':'A 재접근 없음','future_bars':len(future)}
    s=int(approach[0]); obs=future.iloc[s:].copy().reset_index(drop=True)
    minpos=int(np.argmin(obs.low.to_numpy(float))); minrow=obs.iloc[minpos]
    minlow=float(minrow.low); undershoot=(minlow/ap-1)*100
    c_price=float(C['low']) if C else None
    c_touch=None
    if c_price:
        hit=np.where(obs.low.to_numpy(float)<=c_price*1.02)[0]
        if len(hit):c_touch=int(hit[0])
    rev=reversal_confirm(obs,minpos,ap)
    # 결과 분류: 회복은 A 재돌파 + 구조적 반전 확인까지 요구
    recovered=False
    rec_date=None; rec_close=None
    if rev is not None:
        after=obs.iloc[rev:]
        above=np.where(after.close.to_numpy(float)>=ap)[0]
        if len(above):
            k=rev+int(above[0]); recovered=True; rec_date=obs.iloc[k].date; rec_close=float(obs.iloc[k].close)
    if minlow>=ap:
        kind='A 위 지지 후 전환' if rev is not None else 'A 위 지지 · 전환 미확인'
    elif recovered and (c_touch is None or rev<c_touch):
        kind='A 소폭/일시 이탈 후 추세전환'
    elif c_touch is not None and (rev is None or c_touch<=rev):
        kind='A 붕괴 → 다음 전저점 C 접근'
    else:
        kind='A 이탈 · 아직 방향 미확정'
    return {
        'status':'검증완료','kind':kind,'approach_date':obs.iloc[0].date,'min_date':minrow.date,'min_low':minlow,
        'undershoot_pct':undershoot,'reversal_date':obs.iloc[rev].date if rev is not None else None,
        'recovered_above_A':recovered,'recovery_date':rec_date,'recovery_close':rec_close,
        'C_touch_date':obs.iloc[c_touch].date if c_touch is not None else None,
        'future_bars':len(future)
    }

def candle_chart(show, markers=None):
    """일반 증권사 형태의 OHLC 캔들차트. 시가~종가 몸통, 고가~저가 꼬리를 실제 값 그대로 표시."""
    if show.empty:
        st.warning("차트 데이터가 없습니다.")
        return

    d = show.copy().reset_index(drop=True)
    # OHLC 데이터 자체가 비정상인 봉은 제거한다.
    valid = (
        (d["high"] >= d[["open","close","low"]].max(axis=1)) &
        (d["low"] <= d[["open","close","high"]].min(axis=1)) &
        (d[["open","high","low","close"]] > 0).all(axis=1)
    )
    d = d.loc[valid].reset_index(drop=True)
    if d.empty:
        st.error("정상 OHLC 봉 데이터가 없습니다.")
        return

    fig_w = max(12, min(22, len(d) / 8))
    fig, ax = plt.subplots(figsize=(fig_w, 7))
    x = np.arange(len(d), dtype=float)
    body_w = 0.62

    for i, row in d.iterrows():
        o, h, l, c = map(float, [row["open"], row["high"], row["low"], row["close"]])
        color = "#d32f2f" if c >= o else "#1565c0"  # 한국식: 상승 빨강 / 하락 파랑
        ax.vlines(i, l, h, color=color, linewidth=0.9, zorder=2)
        bottom = min(o, c)
        height = abs(c-o)
        if height == 0:
            ax.hlines(c, i-body_w/2, i+body_w/2, color=color, linewidth=1.3, zorder=3)
        else:
            ax.add_patch(Rectangle((i-body_w/2, bottom), body_w, height,
                                   facecolor=color, edgecolor=color, linewidth=0.7, zorder=3))

    # A 등 구조 마커
    for m in (markers or []):
        try:
            dt = pd.Timestamp(m.get("date"))
            hits = d.index[d["date"] == dt].tolist()
            if not hits:
                continue
            i = hits[0]
            price = float(m.get("price"))
            label = str(m.get("label","A"))
            ax.scatter([i], [price], marker="v", s=90, zorder=5)
            ax.annotate(f"{label}\n{price:,.0f}원", (i, price),
                        xytext=(0, 24), textcoords="offset points",
                        ha="center", va="bottom", fontsize=10, fontweight="bold",
                        arrowprops=dict(arrowstyle="-", linewidth=0.8))
        except Exception:
            pass

    # 날짜축은 읽을 수 있게 6~8개만
    nt = min(8, len(d))
    tick_idx = np.unique(np.linspace(0, len(d)-1, nt).astype(int))
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([d.iloc[i]["date"].strftime("%Y-%m-%d") for i in tick_idx],
                       rotation=0, fontsize=9)
    ax.yaxis.set_major_formatter(lambda v, pos: f"{v:,.0f}")
    ax.grid(axis="y", alpha=0.18)
    ax.set_xlim(-1, len(d))
    ymin, ymax = float(d["low"].min()), float(d["high"].max())
    pad = max((ymax-ymin)*0.07, 1)
    ax.set_ylim(ymin-pad, ymax+pad)
    ax.set_ylabel("가격(원)")
    ax.set_title("기준일 당시 OHLC 봉차트", pad=14, fontsize=13, fontweight="bold")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

st.markdown('<div class="main-title">🕰️ 전저점 A + 지지/이탈 타임머신 검증</div>',unsafe_allow_html=True)
st.markdown('<div class="sub">1단계는 <b>깊은계곡 A를 정확히 고르는지</b> 확인합니다. 그 다음, 기준일 이후 미래구간은 오직 검증용으로 열어 A 위 지지 / A 아래 일시 이탈 후 회복 / 다음 전저점 C까지 붕괴를 구분합니다.</div>',unsafe_allow_html=True)

c1,c2,c3=st.columns([1.3,1,1])
with c1:name=st.selectbox('종목',list(DEFAULT_CODES.keys())+['직접입력'])
with c2:code=st.text_input('종목코드',DEFAULT_CODES.get(name,''),max_chars=6)
with c3:pages=st.number_input('조회 페이지 (1페이지≈10봉)',50,120,100,10)
if not re.fullmatch(r'\d{6}',code or ''):
    st.warning('6자리 종목코드를 입력하세요.'); st.stop()
with st.spinner('과거 일봉을 불러오는 중...'):
    df=naver_daily(code,int(pages))
if df.empty:
    st.error('일봉을 가져오지 못했습니다.'); st.stop()

min_i=min(180,len(df)-1)
default_i=max(min_i,len(df)-121)
base_date=st.select_slider('타임머신 기준일',options=list(df.date),value=df.iloc[default_i].date,format_func=lambda x:x.strftime('%Y-%m-%d'))
base_idx=int(df.index[df.date==base_date][0])
cut=df.iloc[:base_idx+1].copy().reset_index(drop=True)
A,cands=select_A(cut); C=previous_lower_valley(cut,A,cands); hier=low_hierarchy(cut); direction=broad_direction(cut)

m1,m2,m3,m4=st.columns(4)
m1.metric('기준일',base_date.strftime('%Y-%m-%d'))
m2.metric('당시 종가',pp(cut.iloc[-1].close))
m3.metric('큰 방향',direction)
m4.metric('기준일까지 과거봉',f'{len(cut)}개')

st.markdown('### ① A · 깊은계곡부터 확정')
if A:
    c1,c2,c3,c4=st.columns(4)
    c1.metric('A 실제 바닥 Low',pp(A['low']),A['date'].strftime('%Y-%m-%d'))
    c2.metric('A 전 하락폭',pct(A['drop']))
    c3.metric('A 후 반등폭',pct(A['rebound']))
    c4.metric('A 계곡 점수',f"{A['score']:.1f}")
    if C:
        st.info(f"A가 무너지면 과거의 다음 하단 전저점 C 후보: {C['date'].strftime('%Y-%m-%d')} · {pp(C['low'])}")
    else:
        st.info('현재 확보한 과거구간에서는 A보다 아래의 의미 있는 전저점 C가 없습니다.')
else:
    st.warning('이 기준일까지 깊은계곡 A를 확정하지 못했습니다.')

st.markdown('### ② 저점 계층 — 5·10·20·60·120·250·500일')
hdf=pd.DataFrame([{'구간':f"{x['days']}일",'저점일':x['date'].strftime('%Y-%m-%d'),'실제 Low':int(x['low'])} for x in hier])
st.dataframe(hdf,use_container_width=True,hide_index=True)

st.markdown('### ③ 일반 봉차트 — 기준일 이전만 표시')
view_n=st.radio('차트 범위',options=[60,120,250,500],index=1,horizontal=True,format_func=lambda x:f'최근 {x}봉')
show=cut.tail(min(view_n,len(cut))).copy().reset_index(drop=True)
markers=[]
if A:markers.append({'date':A['date'],'price':A['low'],'label':f"A {int(A['low']):,}",'shape':'up'})
if C:markers.append({'date':C['date'],'price':C['low'],'label':f"C {int(C['low']):,}",'shape':'up'})
candle_chart(show,markers)
st.caption('빨강=상승봉 · 파랑=하락봉 · 몸통=시가~종가 · 꼬리=고가~저가. 봉이 많으면 차트를 좌우로 움직여 보세요. A/C는 실제 일중 저가(Low)에 표시합니다.')

st.markdown('### ④ A 후보 점검')
if cands:
    rows=[]
    for k,x in enumerate(cands[:10],1):
        rows.append({'순위':k,'날짜':x['date'].strftime('%Y-%m-%d'),'실제 Low':int(x['low']),'전 하락%':round(x['drop'],1),'후 반등%':round(x['rebound'],1),'계곡깊이':round(x['depth'],2),'어깨깊이%':round(x['shoulder'],1),'점수':round(x['score'],1),'A':'●' if A and x['i']==A['i'] else ''})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
else:
    st.info('A 후보가 없습니다.')

st.markdown('### ⑤ 기준일 이후 실제 결과로 A 지지/이탈 검증')
max_future=st.slider('검증할 미래 봉 수',40,240,160,20)
res=analyze_future_retest(df,base_idx,A,C,max_future=max_future)
if res.get('status')=='검증완료':
    kind=res['kind']; cls='good' if ('지지 후 전환' in kind or '일시 이탈 후 추세전환' in kind) else ('bad' if '붕괴' in kind else 'warn')
    st.markdown(f'<div class="{cls}"><b>결과: {html.escape(kind)}</b></div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    c1.metric('A 첫 재접근',res['approach_date'].strftime('%Y-%m-%d'))
    c2.metric('재접근 후 최저가',pp(res['min_low']),res['min_date'].strftime('%Y-%m-%d'))
    c3.metric('A 대비 최대 이탈',f"{res['undershoot_pct']:.2f}%")
    c4.metric('A 재회복', '예' if res['recovered_above_A'] else '아니오')
    if res.get('reversal_date') is not None:
        st.write(f"• 구조적 추세전환 확인일: **{res['reversal_date'].strftime('%Y-%m-%d')}**")
    if res.get('recovery_date') is not None:
        st.write(f"• A 가격대 재회복일: **{res['recovery_date'].strftime('%Y-%m-%d')} · {pp(res['recovery_close'])}**")
    if res.get('C_touch_date') is not None:
        st.write(f"• 다음 전저점 C 접근일: **{res['C_touch_date'].strftime('%Y-%m-%d')}**")
    # 미래 결과 차트는 검증용임을 명확히 분리
    fs=df.iloc[base_idx+1:min(len(df),base_idx+1+max_future)].copy()
    combined=pd.concat([cut.tail(80),fs],ignore_index=True)
    fmarkers=[]
    if A:fmarkers.append({'date':A['date'],'price':A['low'],'label':'A','shape':'up'})
    if res.get('min_date') is not None:fmarkers.append({'date':res['min_date'],'price':res['min_low'],'label':f"최저 {int(res['min_low']):,}",'shape':'up'})
    if res.get('reversal_date') is not None:
        rr=df[df.date==res['reversal_date']]
        if not rr.empty:fmarkers.append({'date':res['reversal_date'],'price':float(rr.iloc[0].high),'label':'추세전환 확인','shape':'down'})
    st.markdown('#### 검증용 미래 포함 차트')
    candle_chart(combined.reset_index(drop=True),fmarkers)
    st.caption('이 아래 차트만 미래 데이터를 사용합니다. A 선정에는 사용하지 않고, A가 실제로 지지됐는지/얼마나 깨고 돌았는지 검증하는 용도입니다.')
elif res.get('status')=='A 재접근 없음':
    st.info(f"기준일 이후 {res.get('future_bars',0)}봉 동안 A 가격대로 다시 내려오지 않았습니다.")
else:
    st.info(res.get('status','검증 결과 없음'))

with st.expander('이번 버전에서 고친 핵심'):
    st.write('• A 후보가 모여 있는 계곡 구간을 먼저 찾고, 그 구간 안의 실제 최저가(Low)를 A 가격으로 확정합니다.')
    st.write('• 봉 간격을 넓힌 일반 증권사식 캔들차트로 다시 만들었습니다. 빨강=상승, 파랑=하락, 몸통=시가~종가, 꼬리=고가~저가입니다.')
    st.write('• 기준일 이전 차트와 미래 검증 차트를 완전히 분리했습니다.')
    st.write('• A를 깨더라도 곧바로 실패 처리하지 않습니다. A 아래 최대 이탈률을 실제로 계산하고, 다음 전저점 C에 닿기 전에 구조적 추세전환과 A 재회복이 나오는지 확인합니다.')
    st.write('• 따라서 나중에 여러 종목을 모으면 “좋은 반전은 A를 평균 몇 %까지 깨고 돌아서는가”를 실제 분포로 만들 수 있습니다.')

st.caption(f'전체 확보 일봉 {len(df)}개 · A 판독 사용 {len(cut)}개 · 기준일 이후 데이터는 ⑤ 검증 구역에서만 사용')
