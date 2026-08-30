import re
import html
from pathlib import Path
import requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title='전저점 A/B/C 행동패턴 타임머신 검증', layout='wide')
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

def select_levels(cut):
    """
    A = 현재 파동의 핵심 전저점
        1차: 최근 120봉 안에서 의미 있는 큰 계곡
        2차: 없거나 너무 약하면 최근 250봉까지 확장
    C = A가 무너졌을 때 확인할 더 오래된 하단 의미전저점

    주의: '가장 깊은 저점 = A'로 고정하지 않는다.
    """
    cands=deep_valley_candidates(cut)
    if not cands:
        return None,None,cands

    n=len(cut)
    current_close=float(cut.iloc[-1].close)

    enriched=[]
    for x in cands:
        y=dict(x)
        age=max(0,n-1-int(x['i']))
        y['age']=age

        # 현재 파동 연결성:
        # - 계곡 자체의 의미(score)가 우선
        # - 최근 3~6개월 안의 계곡에만 제한된 최근성 가점
        # - 현재가와 너무 동떨어진 과거 대바닥이 A를 독식하지 않게 함
        if age<=120:
            recency=1.0-age/120.0
        elif age<=250:
            recency=0.35*(1.0-(age-120)/130.0)
        else:
            recency=0.0

        dist=max(0.0,(current_close/float(x['low'])-1.0)*100.0) if x['low'] else 999.0
        # 현재가 대비 2배/3배 아래인 오래된 저점은 현재 A보다는 C 역할에 가깝다.
        connection=max(0.0,1.0-min(dist,120.0)/120.0)

        # tiny pivot 방지: valley score가 본체, 최근성/연결성은 보조
        y['role_score']=float(x['score'])*0.72 + recency*14.0 + connection*14.0
        enriched.append(y)

    # ① 최근 120봉에서 먼저 A를 찾는다.
    recent120=[x for x in enriched if x['age']<=120 and (x['drop']>=8 or x['rebound']>=10)]
    # 너무 약한 잔계곡만 있으면 250봉까지 넓힌다.
    if recent120 and max(x['score'] for x in recent120)>=38:
        pool=recent120
        a_scope='최근120봉'
    else:
        pool=[x for x in enriched if x['age']<=250 and (x['drop']>=8 or x['rebound']>=10)]
        a_scope='최근250봉'
    if not pool:
        pool=enriched
        a_scope='전체구간(후보부족)'

    A=max(pool,key=lambda x:(x['role_score'],x['score']))
    A['scope']=a_scope

    # ② C는 A보다 '과거'이면서 '가격이 더 낮은' 다음 하단 의미계곡.
    # 가격상 A 바로 아래 방어선을 우선한다.
    lower=[x for x in enriched if x['i']<A['i'] and x['low']<A['low']*0.995]
    C=max(lower,key=lambda x:x['low']) if lower else None
    if C:
        C['scope']='A 아래 장기 방어선'

    return A,C,enriched

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


def _bar_features(row, vol_ma20=None):
    o,h,l,c=[float(row[k]) for k in ('open','high','low','close')]
    rng=max(h-l,1e-9)
    body=abs(c-o)
    upper=max(0.0,h-max(o,c))
    lower=max(0.0,min(o,c)-l)
    return {
        'bull': c>o,
        'bear': c<o,
        'close_pos': (c-l)/rng,
        'upper_pct': upper/rng,
        'lower_pct': lower/rng,
        'body_pct': body/rng,
        'vol_ratio': (float(row.get('volume',0))/vol_ma20) if vol_ma20 and vol_ma20>0 else None,
    }


def classify_A_behavior(df, base_idx, A, C, max_future=180):
    """A 재접근 뒤 나타나는 여러 행동을 한 가지 답으로 고정하지 않고 유형별로 기록한다.
    분봉 의도 추정은 하지 않는다. 일봉 OHLC/거래량으로 관측 가능한 흔적만 사용한다.
    """
    if A is None or base_idx>=len(df)-1:
        return {'status':'미래구간 없음','events':[]}
    future=df.iloc[base_idx+1:min(len(df),base_idx+1+max_future)].copy().reset_index(drop=True)
    if future.empty: return {'status':'미래구간 없음','events':[]}
    ap=float(A['low']); cp=float(C['low']) if C else None

    # A +8% 이내에 들어온 날부터 A 주변 사건 후보로 기록
    near=np.where(future.low.to_numpy(float)<=ap*1.08)[0]
    if len(near)==0:
        return {'status':'A 재접근 없음','events':[],'future_bars':len(future)}

    events=[]
    last_event=-99
    for j in near:
        j=int(j)
        if j-last_event<3:  # 같은 흔들림을 매일 중복 기록하지 않음
            continue
        row=future.iloc[j]
        hist=pd.concat([df.iloc[:base_idx+1],future.iloc[:j]],ignore_index=True)
        vma=float(hist.volume.tail(20).mean()) if 'volume' in hist.columns and len(hist)>=5 else None
        f=_bar_features(row,vma)
        low=float(row.low); close=float(row.close)
        breach=(low/ap-1)*100
        close_vs_A=(close/ap-1)*100

        # 다음 3거래일 회복 여부 / 다음 5,10,20봉의 성과는 검증 결과일 뿐 신호 생성에 쓰지 않음
        nxt=future.iloc[j+1:min(len(future),j+21)].copy()
        reclaim3=False; reclaim_date=None
        if not nxt.empty:
            r3=nxt.iloc[:3]
            hit=np.where(r3.close.to_numpy(float)>=ap)[0]
            if len(hit):
                reclaim3=True; reclaim_date=r3.iloc[int(hit[0])].date
        no_reclaim3 = (close<ap) and (not reclaim3)

        # '윗꼬리 없이 상승마감'의 일봉 대용치: 양봉 + 종가가 당일 범위 상단 80% 이상 + 윗꼬리 12% 이하
        clean_bull = f['bull'] and f['close_pos']>=0.80 and f['upper_pct']<=0.12
        strong_close = f['close_pos']>=0.72 and f['upper_pct']<=0.20
        hammer = f['lower_pct']>=0.35 and f['close_pos']>=0.65
        vol_reclaim = (f['vol_ratio'] is not None and f['vol_ratio']>=1.5 and close>=ap and strong_close)

        if low>=ap*0.995 and clean_bull:
            typ='A 정상지지 + 고가권 상승마감'
            plan='A'
        elif low<ap and close>=ap and clean_bull:
            typ='A 장중이탈 → 당일 회복(페이크 이탈 후보)'
            plan='B'
        elif low<ap and hammer and close>=ap*0.985:
            typ='A 이탈 → 긴 아랫꼬리 회복'
            plan='B'
        elif low<ap and reclaim3:
            typ='A 이탈 → 1~3일 내 재회복'
            plan='B'
        elif vol_reclaim:
            typ='거래량 동반 A 회복'
            plan='B'
        elif close<ap and f['bear'] and f['close_pos']<=0.35 and f['lower_pct']<=0.18 and no_reclaim3:
            typ='A 하향붕괴 + 저가권 마감'
            plan='C'
        elif close<ap and no_reclaim3:
            typ='A 이탈 지속 · C플랜 관찰'
            plan='C'
        else:
            typ='A 주변 애매구간 · 관찰'
            plan='OBS'

        # 이후 실제 경로 요약
        out={}
        for horizon in (5,10,20):
            seg=future.iloc[j+1:min(len(future),j+1+horizon)]
            if len(seg):
                out[f'max_up_{horizon}']=(float(seg.high.max())/close-1)*100
                out[f'max_down_{horizon}']=(float(seg.low.min())/close-1)*100
            else:
                out[f'max_up_{horizon}']=None; out[f'max_down_{horizon}']=None
        c_touch=None
        if cp and len(nxt):
            hit=np.where(nxt.low.to_numpy(float)<=cp*1.02)[0]
            if len(hit): c_touch=nxt.iloc[int(hit[0])].date

        events.append({
            'date':row.date,'type':typ,'plan':plan,'low':low,'close':close,
            'breach_pct':breach,'close_vs_A_pct':close_vs_A,'close_pos':f['close_pos']*100,
            'upper_pct':f['upper_pct']*100,'lower_pct':f['lower_pct']*100,
            'vol_ratio':f['vol_ratio'],'reclaim3':reclaim3,'reclaim_date':reclaim_date,
            'C_touch_date':c_touch,**out
        })
        last_event=j

    counts={k:sum(1 for e in events if e['plan']==k) for k in ('A','B','C','OBS')}
    return {'status':'검증완료','events':events,'counts':counts,'future_bars':len(future)}

def candle_chart(show, markers=None):
    """외부 차트 라이브러리 없이 실제 OHLC로 그리는 증권사형 캔들차트."""
    if show.empty:
        st.warning("차트 데이터가 없습니다.")
        return

    d = show.copy().reset_index(drop=True)
    valid = (
        (d["high"] >= d[["open","close","low"]].max(axis=1)) &
        (d["low"] <= d[["open","close","high"]].min(axis=1)) &
        (d[["open","high","low","close"]] > 0).all(axis=1)
    )
    d = d.loc[valid].reset_index(drop=True)
    if d.empty:
        st.error("정상 OHLC 봉 데이터가 없습니다.")
        return

    n = len(d)
    step = 8 if n <= 140 else (6 if n <= 280 else 4)
    body_w = max(3, step - 3)
    left, right, top, bottom = 64, 20, 24, 46
    plot_h = 470
    width = max(760, left + right + n * step)
    height = top + plot_h + bottom

    lo = float(d["low"].min())
    hi = float(d["high"].max())
    span = max(hi - lo, 1.0)
    pad = span * 0.06
    ymin, ymax = lo - pad, hi + pad
    yrange = max(ymax - ymin, 1.0)

    def y(px):
        return top + (ymax - float(px)) / yrange * plot_h

    def x(i):
        return left + i * step + step / 2

    parts = [
        f'<div style="overflow-x:auto; width:100%; border:1px solid #d8dee9; border-radius:8px; background:#ffffff;">',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="display:block;">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>'
    ]

    # Horizontal grid + price labels
    for j in range(6):
        price = ymin + (ymax - ymin) * j / 5
        yy = y(price)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e6e9ef" stroke-width="1"/>')
        parts.append(f'<text x="{left-8}" y="{yy+4:.1f}" text-anchor="end" font-size="12" fill="#616b7a">{price:,.0f}</text>')

    # Candles: wick = low~high, body = open~close ONLY
    for i, row in d.iterrows():
        o, h, l, c = [float(row[k]) for k in ("open","high","low","close")]
        xx = x(i)
        col = "#d32f2f" if c >= o else "#1565c0"
        yo, yc, yh, yl = y(o), y(c), y(h), y(l)
        parts.append(f'<line x1="{xx:.1f}" y1="{yh:.1f}" x2="{xx:.1f}" y2="{yl:.1f}" stroke="{col}" stroke-width="1"/>')
        body_top = min(yo, yc)
        body_h = abs(yc - yo)
        if body_h < 1.2:
            parts.append(f'<line x1="{xx-body_w/2:.1f}" y1="{body_top:.1f}" x2="{xx+body_w/2:.1f}" y2="{body_top:.1f}" stroke="{col}" stroke-width="1.4"/>')
        else:
            parts.append(f'<rect x="{xx-body_w/2:.1f}" y="{body_top:.1f}" width="{body_w:.1f}" height="{body_h:.1f}" fill="{col}" stroke="{col}" stroke-width="0.5"/>')

    # Date labels (6~8)
    tick_count = min(8, n)
    tick_idx = sorted(set(int(round(v)) for v in np.linspace(0, n-1, tick_count)))
    for i in tick_idx:
        xx = x(i)
        label = d.iloc[i]["date"].strftime("%Y-%m-%d")
        parts.append(f'<line x1="{xx:.1f}" y1="{top+plot_h}" x2="{xx:.1f}" y2="{top+plot_h+5}" stroke="#9aa4b2"/>')
        parts.append(f'<text x="{xx:.1f}" y="{top+plot_h+22}" text-anchor="middle" font-size="11" fill="#616b7a">{label}</text>')

    # A/C marker(s)
    for m in (markers or []):
        try:
            dt = pd.Timestamp(m.get("date"))
            hits = d.index[d["date"] == dt].tolist()
            if not hits:
                continue
            i = hits[0]
            price = float(m.get("price"))
            label = html.escape(str(m.get("label","A")))
            xx, yy = x(i), y(price)
            parts.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top+plot_h}" stroke="#2e7d32" stroke-width="1.2" stroke-dasharray="5 4"/>')
            parts.append(f'<polygon points="{xx-6:.1f},{yy-16:.1f} {xx+6:.1f},{yy-16:.1f} {xx:.1f},{yy-5:.1f}" fill="#2e7d32"/>')
            parts.append(f'<rect x="{xx-54:.1f}" y="{max(2,yy-43):.1f}" width="108" height="21" rx="4" fill="#e8f5e9" stroke="#2e7d32"/>')
            parts.append(f'<text x="{xx:.1f}" y="{max(16,yy-28):.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#1b5e20">{label}</text>')
        except Exception:
            pass

    parts.append('</svg></div>')
    st.markdown("".join(parts), unsafe_allow_html=True)

st.markdown('<div class="main-title">🕰️ 전저점 A/B/C 행동패턴 타임머신 검증</div>',unsafe_allow_html=True)
st.markdown('<div class="sub">1단계는 <b>깊은계곡 A를 정확히 고르는지</b> 확인합니다. 그 다음, 기준일 이후 미래구간은 오직 검증용으로 열어 현재 파동 A 위 지지 / A 아래 일시 이탈 후 회복 / A 붕괴 뒤 더 오래된 하단 전저점 C 접근을 구분합니다.</div>',unsafe_allow_html=True)

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
A,C,cands=select_levels(cut); hier=low_hierarchy(cut); direction=broad_direction(cut)

m1,m2,m3,m4=st.columns(4)
m1.metric('기준일',base_date.strftime('%Y-%m-%d'))
m2.metric('당시 종가',pp(cut.iloc[-1].close))
m3.metric('큰 방향',direction)
m4.metric('기준일까지 과거봉',f'{len(cut)}개')

st.markdown('### ① 전저점 역할 분리 — 현재 A / 하단 C')
if A:
    c1,c2,c3,c4=st.columns(4)
    c1.metric('현재 파동 A',pp(A['low']),A['date'].strftime('%Y-%m-%d'))
    c2.metric('A 탐색범위',A.get('scope',''))
    c3.metric('A 계곡점수',f"{A['score']:.1f}")
    c4.metric('현재연결 점수',f"{A.get('role_score',0):.1f}")
    st.success(
        f"현재 매매에서 먼저 볼 A: {A['date'].strftime('%Y-%m-%d')} · {pp(A['low'])} "
        f"({A.get('scope','')}). 가장 오래된 최저가를 무조건 A로 쓰지 않습니다."
    )
    if C:
        st.info(
            f"A가 무너지면 다음에 확인할 C(하단 장기 전저점): "
            f"{C['date'].strftime('%Y-%m-%d')} · {pp(C['low'])}"
        )
    else:
        st.info('현재 확보한 과거구간에서는 A 아래의 별도 C 방어선을 찾지 못했습니다.')
else:
    st.warning('이 기준일까지 현재 파동 A를 확정하지 못했습니다.')

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
st.caption('빨강=상승봉 · 파랑=하락봉 · 몸통=시가~종가 · 꼬리=고가~저가. 차트가 넓으면 아래 영역을 좌우로 스크롤할 수 있습니다. A/C는 실제 일중 저가(Low)에 표시합니다.')

st.markdown('### ④ A 후보 점검')
if cands:
    rows=[]
    for k,x in enumerate(sorted(cands,key=lambda z:z.get('role_score',z.get('score',0)),reverse=True)[:10],1):
        role=''
        if A and x['i']==A['i']: role='A 현재파동'
        elif C and x['i']==C['i']: role='C 하단방어'
        rows.append({'순위':k,'날짜':x['date'].strftime('%Y-%m-%d'),'실제 Low':int(x['low']),
                     '경과봉':int(x.get('age',0)),'전 하락%':round(x['drop'],1),'후 반등%':round(x['rebound'],1),
                     '계곡점수':round(x['score'],1),'현재연결':round(x.get('role_score',0),1),'역할':role})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
else:
    st.info('A 후보가 없습니다.')

st.markdown('### ⑤ A 주변 행동패턴 검증 — 한 가지 봉모양으로 단정하지 않음')
max_future=st.slider('검증할 미래 봉 수',40,240,160,20)
pat=classify_A_behavior(df,base_idx,A,C,max_future=max_future)
if pat.get('status')=='검증완료':
    cnt=pat.get('counts',{})
    c1,c2,c3,c4=st.columns(4)
    c1.metric('A 정상지지',cnt.get('A',0))
    c2.metric('B 흔들기/회복',cnt.get('B',0))
    c3.metric('C 붕괴/이탈지속',cnt.get('C',0))
    c4.metric('관찰',cnt.get('OBS',0))

    ev=pat.get('events') or []
    rows=[]
    for e in ev:
        rows.append({
            '날짜':e['date'].strftime('%Y-%m-%d'),'플랜':e['plan'],'판정':e['type'],
            'A대비 저가%':round(e['breach_pct'],2),'A대비 종가%':round(e['close_vs_A_pct'],2),
            '종가위치%':round(e['close_pos'],1),'윗꼬리%':round(e['upper_pct'],1),'아랫꼬리%':round(e['lower_pct'],1),
            '거래량배수':round(e['vol_ratio'],2) if e['vol_ratio'] is not None else None,
            '3일내 A회복':'예' if e['reclaim3'] else '아니오',
            '향후10봉 최대상승%':round(e['max_up_10'],1) if e['max_up_10'] is not None else None,
            '향후10봉 최대하락%':round(e['max_down_10'],1) if e['max_down_10'] is not None else None,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        # 이번 종목에서 B 회복과 C 붕괴가 실제로 어느 이탈폭에서 갈렸는지 요약
        b=[e['breach_pct'] for e in ev if e['plan']=='B']
        c=[e['breach_pct'] for e in ev if e['plan']=='C']
        if b:
            st.success(f"B플랜 사례의 A 최대 이탈: 평균 {np.mean(b):.2f}% · 중앙 {np.median(b):.2f}% · 최저 {min(b):.2f}%")
        if c:
            st.error(f"C플랜 사례의 A 최대 이탈: 평균 {np.mean(c):.2f}% · 중앙 {np.median(c):.2f}% · 최저 {min(c):.2f}%")
    else:
        st.info('A 주변에서 분류할 사건이 없었습니다.')
elif pat.get('status')=='A 재접근 없음':
    st.info(f"기준일 이후 {pat.get('future_bars',0)}봉 동안 A 가격대로 다시 접근하지 않았습니다.")
else:
    st.info(pat.get('status','검증 결과 없음'))

with st.expander('이번 검증에서 보는 조건'):
    st.write('• A플랜: A 위에서 지지하면서 양봉 + 종가가 고가권 + 윗꼬리가 짧은 날')
    st.write('• B플랜: A를 장중 깨고 당일 회복, 긴 아랫꼬리 회복, 또는 1~3일 안에 A를 재회복하는 경우')
    st.write('• 거래량 급증을 동반한 회복도 별도 흔적으로 기록합니다.')
    st.write('• C플랜: A 아래에서 하락마감하고 저가권 종가이며, 3일 안에도 A를 회복하지 못하는 경우')
    st.write('• 애매한 날은 억지로 성공/붕괴로 넣지 않고 관찰로 남깁니다.')
    st.write('• “세력 털기”라고 단정하지 않습니다. 관측 가능한 OHLC·거래량 행동만 분류합니다.')
    st.write('• 현재 버전은 일봉 검증입니다. 과거 분봉이 확보되는 구간은 이후 같은 분류를 분봉으로 한 번 더 확인할 수 있습니다.')

st.caption(f'전체 확보 일봉 {len(df)}개 · A 판독 사용 {len(cut)}개 · 기준일 이후 데이터는 ⑤ 검증 구역에서만 사용')
