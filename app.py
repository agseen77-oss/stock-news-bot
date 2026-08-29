import re
import html
import zipfile
from pathlib import Path
import requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title='A 전저점 타임머신 검증', layout='wide')
st.markdown('''
<style>
.block-container{max-width:1280px;padding-top:1.2rem;padding-bottom:3rem}
.big{font-size:30px;font-weight:900}.sub{color:#777;font-size:15px;margin-bottom:12px}
.card{border:1px solid #333;border-radius:14px;padding:14px 16px;margin:8px 0}
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

@st.cache_data(ttl=3600, show_spinner=False)
def naver_daily(code:str,pages:int=100):
    headers={'User-Agent':'Mozilla/5.0'}; rows=[]
    for page in range(1,pages+1):
        url=f'https://finance.naver.com/item/sise_day.naver?code={code}&page={page}'
        try: txt=requests.get(url,headers=headers,timeout=5).text
        except Exception: continue
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
    for c in ['open','high','low','close','volume']:df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['open','high','low','close']).reset_index(drop=True)

def low_hierarchy(cut):
    out=[]
    for d in [5,10,20,60,120,250,500]:
        x=cut.tail(min(d,len(cut)))
        j=x['low'].idxmin(); r=cut.loc[j]
        out.append({'days':d,'date':r.date,'low':float(r.low)})
    return out

def local_lows(cut,radius=5):
    a=cut['low'].to_numpy(float); out=[]
    for i in range(radius,len(cut)-radius):
        w=a[i-radius:i+radius+1]
        if a[i] <= np.nanmin(w): out.append(i)
    # 기준일에 매우 가까운 신저점은 오른쪽 봉 확인을 기다리지 않고 후보에 포함
    tail_start=max(0,len(cut)-20)
    if len(cut)>tail_start:
        j=tail_start+int(np.nanargmin(a[tail_start:]))
        if j not in out: out.append(j)
    return sorted(set(out))

def deep_valley_candidates(cut):
    n=len(cut)
    if n<120:return []
    idxs=local_lows(cut,5)
    overall_lo=float(cut['low'].min()); overall_hi=float(cut['high'].max())
    full_range=max(overall_hi-overall_lo,1.0)
    vals=[]
    for i in idxs:
        lv=float(cut.iloc[i].low)
        pre=cut.iloc[max(0,i-80):i+1]
        post=cut.iloc[i:min(n,i+81)]
        pre_hi=float(pre.high.max()) if len(pre) else lv
        post_hi=float(post.high.max()) if len(post) else lv
        drop=max(0,(pre_hi/lv-1)*100) if lv else 0
        rebound=max(0,(post_hi/lv-1)*100) if lv else 0
        # 주변 120봉에서 얼마나 바닥에 가까운지. 1.0에 가까울수록 깊은 계곡.
        near=cut.iloc[max(0,i-120):min(n,i+121)]
        near_lo=float(near.low.min()); near_hi=float(near.high.max())
        depth=1.0-(lv-near_lo)/max(near_hi-near_lo,1.0)
        # 전체 확보구간에서 가격 자체가 얼마나 낮은 축인지.
        global_depth=1.0-(lv-overall_lo)/full_range
        # 저점 이후 실제로 큰 상승파를 만들었는지 강하게 반영.
        score=(min(drop,80)/80)*22 + (min(rebound,160)/160)*34 + depth*24 + global_depth*20
        # 깊은 계곡은 최소한 하락 또는 반등 중 하나가 충분히 커야 함.
        if (drop>=12 or rebound>=20) and depth>=0.55:
            vals.append({'i':i,'date':cut.iloc[i].date,'low':lv,'drop':drop,'rebound':rebound,'depth':depth,'global_depth':global_depth,'score':score})
    return sorted(vals,key=lambda x:x['score'],reverse=True)

def select_A(cut):
    cands=deep_valley_candidates(cut)
    if not cands:return None,cands
    # 가장 점수가 높은 '대전저점'을 A로 선택. 최근이라는 이유로 우선하지 않는다.
    # 점수가 비슷하면 더 낮은 가격의 계곡을 우선한다.
    best_score=cands[0]['score']
    near=[x for x in cands if x['score']>=best_score-6]
    A=min(near,key=lambda x:(x['low'],-x['score']))
    return A,cands

def broad_direction(cut):
    x=cut.tail(min(500,len(cut)))
    if len(x)<160:return '판단보류'
    # 큰 저점/큰 고점의 앞 절반과 뒤 절반을 비교해 방향만 참고로 표시
    h=len(x)//2; a=x.iloc[:h]; b=x.iloc[h:]
    lo1=float(a.low.min()); lo2=float(b.low.min()); hi1=float(a.high.max()); hi2=float(b.high.max())
    if lo2>lo1*1.05 and hi2>hi1*1.05:return '우상향'
    if lo2<lo1*0.92 and hi2<hi1*0.92:return '우하향'
    return '횡보/혼조'

def candle_svg(show,A=None):
    W,H=1250,610; L,R,T,B=75,28,25,58
    if show.empty:return '<div>차트 데이터 없음</div>'
    ymin=float(show.low.min()); ymax=float(show.high.max()); pad=max((ymax-ymin)*0.05,1)
    ymin-=pad; ymax+=pad
    def X(i): return L+(W-L-R)*(i/max(1,len(show)-1))
    def Y(v): return T+(H-T-B)*(ymax-float(v))/max(ymax-ymin,1e-9)
    parts=[f'<svg viewBox="0 0 {W} {H}" width="100%" style="background:white;border-radius:12px;border:1px solid #bbb">']
    for k in range(6):
        val=ymax-(ymax-ymin)*k/5; y=Y(val)
        parts.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#ececec"/>')
        parts.append(f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#666">{int(val):,}</text>')
    # 봉 간격에 맞춰 몸통 폭 결정
    bw=max(1.2,min(5.0,(W-L-R)/max(len(show),1)*0.62))
    for i,row in show.iterrows():
        x=X(i); yo=Y(row.open); yc=Y(row.close); yh=Y(row.high); yl=Y(row.low)
        up=row.close>=row.open
        color='#d62728' if up else '#2468d8'
        parts.append(f'<line x1="{x:.1f}" y1="{yh:.1f}" x2="{x:.1f}" y2="{yl:.1f}" stroke="{color}" stroke-width="1"/>')
        top=min(yo,yc); height=max(abs(yc-yo),1.2)
        parts.append(f'<rect x="{x-bw/2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{height:.1f}" fill="{color}"/>')
    # A 표시
    if A:
        dates={pd.Timestamp(d):i for i,d in enumerate(show.date)}
        dt=pd.Timestamp(A['date'])
        if dt in dates:
            i=dates[dt]; x=X(i); y=Y(A['low'])
            parts.append(f'<polygon points="{x:.1f},{y-14:.1f} {x-10:.1f},{y+6:.1f} {x+10:.1f},{y+6:.1f}" fill="#19a34a" stroke="#111"/>')
            parts.append(f'<text x="{x:.1f}" y="{max(18,y-22):.1f}" text-anchor="middle" font-size="15" font-weight="800" fill="#111">A 대전저점 {int(A["low"]):,}</text>')
    for pos in [0,len(show)//2,len(show)-1]:
        row=show.iloc[pos]; parts.append(f'<text x="{X(pos):.1f}" y="{H-20}" text-anchor="middle" font-size="12" fill="#666">{row.date.strftime("%Y-%m-%d")}</text>')
    parts.append('</svg>')
    return ''.join(parts)

st.markdown('<div class="big">🕰️ A 전저점 타임머신 검증</div>',unsafe_allow_html=True)
st.markdown('<div class="sub">이번 검증은 <b>A 깊은계곡 하나만</b> 확인합니다. R·B·진입·매도는 A가 맞을 때까지 계산하지 않습니다. 기준일 이후 데이터는 사용하지 않습니다.</div>',unsafe_allow_html=True)

c1,c2,c3=st.columns([1.3,1,1])
with c1:name=st.selectbox('종목',list(DEFAULT_CODES.keys())+['직접입력'])
with c2:code=st.text_input('종목코드',DEFAULT_CODES.get(name,''),max_chars=6)
with c3:pages=st.number_input('조회 페이지(1페이지≈10봉)',40,120,100,10)
if not re.fullmatch(r'\d{6}',code or ''):
    st.warning('6자리 종목코드를 입력하세요.'); st.stop()
with st.spinner('과거 일봉을 불러오는 중...'):df=naver_daily(code,int(pages))
if df.empty:
    st.error('일봉을 가져오지 못했습니다.'); st.stop()
min_i=min(140,len(df)-1); default_i=max(min_i,len(df)-21)
base_date=st.select_slider('타임머신 기준일',options=list(df.date),value=df.iloc[default_i].date,format_func=lambda x:x.strftime('%Y-%m-%d'))
cut=df[df.date<=base_date].copy().reset_index(drop=True); future=df[df.date>base_date].copy()
A,cands=select_A(cut); hier=low_hierarchy(cut); direction=broad_direction(cut)

m1,m2,m3,m4=st.columns(4)
m1.metric('기준일',base_date.strftime('%Y-%m-%d')); m2.metric('당시 종가',pp(cut.iloc[-1].close)); m3.metric('큰 방향',direction); m4.metric('사용한 과거봉',f'{len(cut)}개')

st.markdown('### ① A · 깊은계곡 판독')
if A:
    c1,c2,c3,c4=st.columns(4)
    c1.metric('A 대전저점',pp(A['low']),A['date'].strftime('%Y-%m-%d'))
    c2.metric('A 전 하락폭',f"{A['drop']:.1f}%")
    c3.metric('A 후 반등폭',f"{A['rebound']:.1f}%")
    c4.metric('계곡 점수',f"{A['score']:.1f}")
else:st.warning('이 기준일까지 대전저점 A를 확정하지 못했습니다.')

st.markdown('### ② 5·10·20·60·120·250·500일 저점 계층')
hdf=pd.DataFrame([{'구간':f"{x['days']}일",'저점일':x['date'].strftime('%Y-%m-%d'),'저점':int(x['low'])} for x in hier])
st.dataframe(hdf,use_container_width=True,hide_index=True)

st.markdown('### ③ 기준일 당시 봉차트 — 미래 데이터 사용 안 함')
show=cut.tail(min(500,len(cut))).copy().reset_index(drop=True)
st.markdown(candle_svg(show,A),unsafe_allow_html=True)
st.caption('빨강봉=상승 · 파랑봉=하락 · 초록표시=A 대전저점. 기준일 이후 봉은 차트와 판독에서 모두 제외됩니다.')

st.markdown('### ④ A 후보 점검')
if cands:
    rows=[]
    for k,x in enumerate(cands[:8],1):
        rows.append({'순위':k,'날짜':x['date'].strftime('%Y-%m-%d'),'저점':int(x['low']),'전 하락%':round(x['drop'],1),'후 반등%':round(x['rebound'],1),'깊이':round(x['depth'],2),'점수':round(x['score'],1),'A선정':'●' if A and x['i']==A['i'] else ''})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
else:st.info('대전저점 후보가 없습니다.')

with st.expander('이번 수정에서 바꾼 점'):
    st.write('• 선차트를 봉차트로 변경했습니다.')
    st.write('• A가 맞기 전에 R/B를 만들던 로직을 제거했습니다.')
    st.write('• 최근 저점 우선이 아니라, 가격 깊이·진입 전 하락·저점 후 반등·장기 구간 위치를 합쳐 대전저점을 고릅니다.')
    st.write('• 5·10일의 새로운 신저점도 즉시 저점 계층에 들어옵니다.')
    st.write('• 250일보다 긴 구조 확인을 위해 500일 저점도 같이 표시합니다.')
    st.write('• A 후보 상위 8개를 같이 보여줘 왜 A가 선택됐는지 눈으로 검증할 수 있습니다.')

st.caption(f'전체 확보 일봉 {len(df)}개 · 기준일 이후 {len(future)}개 봉은 판독에서 차단')
