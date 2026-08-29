import re
from datetime import datetime
import requests
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title='전저점 타임머신 검증', layout='wide')

st.markdown('''
<style>
.block-container{max-width:1280px;padding-top:1.2rem;padding-bottom:3rem}
.big{font-size:30px;font-weight:900}.sub{color:#555;font-size:15px;margin-bottom:12px}
.card{border:1px solid #ddd;border-radius:14px;padding:14px 16px;background:white;margin:8px 0}
.ok{font-weight:800;color:#147d35}.warn{font-weight:800;color:#b26a00}
</style>
''', unsafe_allow_html=True)

DEFAULT_CODES = {
    '후성':'093370','미래반도체':'254490','켐트로스':'220260','삼성전자':'005930','SK하이닉스':'000660',
    '제룡전기':'033100','에스피시스템스':'317830','LG디스플레이':'034220','리노공업':'058470',
    '테크윙':'089030','원익IPS':'240810','솔브레인':'357780','솔브레인홀딩스':'036830'
}

def pp(x):
    try:return f'{int(round(float(x))):,}원'
    except:return '-'

@st.cache_data(ttl=3600, show_spinner=False)
def naver_daily(code:str, pages:int=90):
    headers={'User-Agent':'Mozilla/5.0'}; rows=[]
    for page in range(1,pages+1):
        url=f'https://finance.naver.com/item/sise_day.naver?code={code}&page={page}'
        try:
            html=requests.get(url,headers=headers,timeout=5).text
        except Exception:
            continue
        for tr in re.findall(r'<tr[^>]*>([\s\S]*?)</tr>',html):
            vals=[re.sub(r'<[^>]+>','',x).replace('\xa0','').strip() for x in re.findall(r'<span[^>]*>([\s\S]*?)</span>',tr)]
            vals=[v for v in vals if v]
            if len(vals)>=7 and re.match(r'\d{4}\.\d{2}\.\d{2}',vals[0]):
                def num(s):
                    try:return float(str(s).replace(',','').replace('+','').replace('-',''))
                    except:return np.nan
                rows.append(dict(date=vals[0].replace('.','-'),close=num(vals[1]),open=num(vals[3]),high=num(vals[4]),low=num(vals[5]),volume=num(vals[6])))
    if not rows:return pd.DataFrame()
    df=pd.DataFrame(rows).drop_duplicates('date').sort_values('date')
    df['date']=pd.to_datetime(df['date'])
    for c in ['open','high','low','close','volume']:df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['low','high','close']).reset_index(drop=True)

def local_extrema(df, radius=7, kind='low'):
    vals=df['low'].to_numpy() if kind=='low' else df['high'].to_numpy()
    out=[]
    for i in range(radius,len(df)-radius):
        w=vals[i-radius:i+radius+1]
        if kind=='low':
            if vals[i] != np.nanmin(w): continue
        else:
            if vals[i] != np.nanmax(w): continue
        out.append(i)
    return out

def analyze(cut):
    n=len(cut)
    if n<140:return None
    lows=local_extrema(cut,7,'low'); highs=local_extrema(cut,7,'high')
    valley=[]
    for i in lows:
        pre=cut.iloc[max(0,i-40):i+1]
        post=cut.iloc[i:min(n,i+61)]
        lv=float(cut.iloc[i].low)
        prior_high=float(pre.high.max()) if len(pre) else lv
        future_high=float(post.high.max()) if len(post) else lv
        drop=(prior_high/lv-1)*100 if lv else 0
        rebound=(future_high/lv-1)*100 if lv else 0
        # 큰 계곡: 들어오기 전 하락폭과 이후 반등폭을 함께 본다.
        score=min(drop,80)*0.45 + min(rebound,120)*0.55
        valley.append({'i':i,'low':lv,'drop':drop,'rebound':rebound,'score':score,'date':cut.iloc[i].date})
    # 최근 250봉에서 의미 있는 큰 계곡 후보. 너무 최근은 B 후보로 남긴다.
    base=[v for v in valley if v['i'] <= n-12 and v['drop']>=8 and v['rebound']>=10]
    if not base:return {'valleys':valley,'A':None,'R':None,'B':None}
    # 최근 약 1년 안에서 점수 + 시간 균형. 단순 최저가가 아니라 큰 파동을 만든 계곡 우선.
    start=max(0,n-300)
    cand=[v for v in base if v['i']>=start] or base[-8:]
    # A 뒤에 충분한 큰 능선과 후속 눌림이 존재해야 한다.
    valid=[]
    for a in cand:
        later_highs=[h for h in highs if h>a['i']+5]
        if not later_highs:continue
        r=max(later_highs,key=lambda j: cut.iloc[j].high if j<n else 0)
        if r>=n-5:continue
        rise=(float(cut.iloc[r].high)/a['low']-1)*100
        later_vals=[v for v in valley if v['i']>r+3]
        if not later_vals:continue
        # B는 R 이후 가장 깊은 계곡 중 A를 심하게 깨지 않은 것. 최근 저점도 포함.
        valid_b=[v for v in later_vals if v['low'] >= a['low']*0.97]
        if not valid_b:continue
        b=min(valid_b,key=lambda v:v['low'])
        pull=(1-b['low']/float(cut.iloc[r].high))*100
        if rise>=20 and pull>=8:
            valid.append((a,r,b,rise,pull))
    if valid:
        # 가장 최근의 완성된 큰 파동을 우선하되, A의 의미점수도 반영
        valid.sort(key=lambda x:(x[0]['i'],x[0]['score']))
        a,r,b,rise,pull=valid[-1]
    else:
        # 구조 미완성: 가장 의미 큰 A만 보여준다.
        a=max(cand,key=lambda v:v['score']); r=None; b=None; rise=pull=None
    return {'valleys':valley,'A':a,'R':r,'B':b,'rise':rise,'pull':pull}

def low_hierarchy(cut):
    out=[]
    for d in [5,10,20,60,120,250]:
        x=cut.tail(min(d,len(cut)))
        j=x['low'].idxmin(); r=cut.loc[j]
        out.append((d,r.date,float(r.low)))
    return out

def broad_direction(cut):
    x=cut.tail(min(250,len(cut))).copy()
    if len(x)<120:return '판단보류'
    q=len(x)//4
    lo1=x.iloc[:q].low.min(); lo2=x.iloc[-q:].low.min()
    hi1=x.iloc[:q].high.max(); hi2=x.iloc[-q:].high.max()
    lr=(lo2/lo1-1)*100; hr=(hi2/hi1-1)*100
    if lr>5 and hr>5:return '우상향'
    if lr<-8 and hr<-8:return '우하향'
    return '횡보/혼조'

st.markdown('<div class="big">🕰️ 전저점 타임머신 검증</div>',unsafe_allow_html=True)
st.markdown('<div class="sub">수익률 검증이 아닙니다. 과거 그 날짜까지만 보고 <b>큰 방향 → 깊은 계곡 A → 큰 능선 R → 다음 계곡 B</b>를 제대로 찾는지 확인합니다.</div>',unsafe_allow_html=True)

c1,c2,c3=st.columns([1.3,1,1])
with c1:
    name=st.selectbox('종목',list(DEFAULT_CODES.keys())+['직접입력'])
with c2:
    code=st.text_input('종목코드',DEFAULT_CODES.get(name,''),max_chars=6)
with c3:
    pages=st.number_input('조회 페이지(1페이지≈10봉)',30,120,90,10)

if not re.fullmatch(r'\d{6}',code or ''):
    st.warning('6자리 종목코드를 입력하세요.')
    st.stop()

with st.spinner('과거 일봉을 불러오는 중...'):
    df=naver_daily(code,int(pages))
if df.empty:
    st.error('일봉을 가져오지 못했습니다. 인터넷 연결 또는 종목코드를 확인하세요.')
    st.stop()

min_i=min(130,len(df)-1)
default_i=max(min_i,len(df)-21)
base_date=st.select_slider('타임머신 기준일',options=list(df['date']),value=df.iloc[default_i].date,format_func=lambda x:x.strftime('%Y-%m-%d'))
cut=df[df.date<=base_date].copy().reset_index(drop=True)
future=df[df.date>base_date].copy()

res=analyze(cut); hier=low_hierarchy(cut); direction=broad_direction(cut)
A=res.get('A') if res else None; R=res.get('R') if res else None; B=res.get('B') if res else None

m1,m2,m3,m4=st.columns(4)
m1.metric('기준일',base_date.strftime('%Y-%m-%d'))
m2.metric('당시 종가',pp(cut.iloc[-1].close))
m3.metric('큰 방향',direction)
m4.metric('사용한 과거봉',f'{len(cut)}개')

st.markdown('### ① AI가 찾은 큰 파동')
if A:
    cols=st.columns(3)
    cols[0].metric('A · 깊은 계곡',pp(A['low']),A['date'].strftime('%Y-%m-%d'))
    if R is not None:
        rr=cut.iloc[R]; cols[1].metric('R · 큰 능선',pp(rr.high),rr.date.strftime('%Y-%m-%d'))
    else: cols[1].metric('R · 큰 능선','미완성')
    if B:
        cols[2].metric('B · 다음 계곡',pp(B['low']),B['date'].strftime('%Y-%m-%d'))
    else: cols[2].metric('B · 다음 계곡','아직 없음')
else:
    st.warning('이 기준일까지는 큰 파동 A를 확정하지 못했습니다. 이것도 검증 결과입니다.')

st.markdown('### ② 5·10·20·60·120·250일 저점 계층')
hdf=pd.DataFrame([{'구간':f'{d}일','저점일':dt.strftime('%Y-%m-%d'),'저점':int(v)} for d,dt,v in hier])
st.dataframe(hdf,use_container_width=True,hide_index=True)

st.markdown('### ③ 기준일 당시 차트 — 미래 데이터 사용 안 함')
show=cut.tail(min(320,len(cut))).copy().reset_index(drop=True)

def svg_price_chart(show, A=None, R=None, B=None, cut=None):
    # 외부 차트 라이브러리 없이 Streamlit Cloud에서 바로 동작하는 SVG 차트
    W,H=1200,520; L,Rm,T,Bm=65,25,28,50
    if show.empty:return '<div>차트 데이터 없음</div>'
    ymin=float(show['low'].min()); ymax=float(show['high'].max())
    pad=max((ymax-ymin)*0.06,1); ymin-=pad; ymax+=pad
    def X(i): return L + (W-L-Rm)*(i/max(1,len(show)-1))
    def Y(v): return T + (H-T-Bm)*(ymax-float(v))/max(1e-9,ymax-ymin)
    parts=[f'<svg viewBox="0 0 {W} {H}" width="100%" style="background:#fff;border:1px solid #ddd;border-radius:12px">']
    # horizontal guides + prices
    for k in range(6):
        val=ymax-(ymax-ymin)*k/5; yy=Y(val)
        parts.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{W-Rm}" y2="{yy:.1f}" stroke="#ececec" stroke-width="1"/>')
        parts.append(f'<text x="{L-8}" y="{yy+4:.1f}" text-anchor="end" font-size="12" fill="#666">{int(val):,}</text>')
    # high-low bars and close line
    pts=[]
    step=max(1,len(show)//180)
    for i,row in show.iterrows():
        x=X(i)
        if i%step==0:
            parts.append(f'<line x1="{x:.1f}" y1="{Y(row.high):.1f}" x2="{x:.1f}" y2="{Y(row.low):.1f}" stroke="#b8b8b8" stroke-width="1"/>')
        pts.append(f'{x:.1f},{Y(row.close):.1f}')
    parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#2468d8" stroke-width="2"/>')
    date_to_i={pd.Timestamp(d):i for i,d in enumerate(show.date)}
    def marker(dt,price,label,fill,shape='circle'):
        dt=pd.Timestamp(dt)
        if dt not in date_to_i:return
        x=X(date_to_i[dt]); y=Y(price)
        if shape=='triangle_up':
            parts.append(f'<polygon points="{x:.1f},{y-11:.1f} {x-9:.1f},{y+7:.1f} {x+9:.1f},{y+7:.1f}" fill="{fill}" stroke="#222"/>')
        elif shape=='triangle_down':
            parts.append(f'<polygon points="{x:.1f},{y+11:.1f} {x-9:.1f},{y-7:.1f} {x+9:.1f},{y-7:.1f}" fill="{fill}" stroke="#222"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{fill}" stroke="#222"/>')
        ty=max(18,y-16)
        parts.append(f'<text x="{x:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="#111">{label}</text>')
    if A: marker(A['date'],A['low'],'A 깊은계곡','#2ca02c','triangle_up')
    if R is not None and cut is not None:
        rr=cut.iloc[R]; marker(rr.date,rr.high,'R 큰능선','#d62728','triangle_down')
    if B: marker(B['date'],B['low'],'B 다음계곡','#ffbf00','circle')
    # date labels
    for pos in [0,len(show)//2,len(show)-1]:
        row=show.iloc[pos]; x=X(pos)
        parts.append(f'<text x="{x:.1f}" y="{H-18}" text-anchor="middle" font-size="12" fill="#666">{row.date.strftime("%Y-%m-%d")}</text>')
    parts.append('</svg>')
    return ''.join(parts)

st.markdown(svg_price_chart(show,A,R,B,cut), unsafe_allow_html=True)
st.caption('파란선=종가 · 회색선=일중 고저 · A/R/B는 기준일까지 확인 가능한 데이터로만 계산')

st.markdown('### ④ 판독 확인')
if A and B:
    relation=(B['low']/A['low']-1)*100
    st.success(f"A {pp(A['low'])} → B {pp(B['low'])} · B는 A 대비 {relation:+.1f}%입니다. 차트를 보고 이 A/R/B가 실제 큰 능선·깊은 계곡과 맞는지만 확인하세요.")
elif A:
    st.info('A는 찾았지만 A 이후의 완성된 R→B 구조는 아직 잡히지 않았습니다. 기준일을 이동하며 확인하세요.')

with st.expander('검증 원칙'):
    st.write('• 기준일 이후 가격은 A/R/B 판독에 사용하지 않습니다.')
    st.write('• 5·10일 저점도 더 낮으면 저점 계층에 즉시 반영합니다.')
    st.write('• A는 단순 최저가가 아니라, 진입 전 하락폭과 이후 반등폭이 큰 계곡을 우선합니다.')
    st.write('• 6개월~1년의 큰 방향을 함께 봅니다. 이동평균선 하나로 우상향을 판정하지 않습니다.')
    st.write('• 이 앱은 전저점 판독 검증 전용입니다. 진입가·매도가·수익률은 아직 넣지 않았습니다.')

st.caption(f'전체 확보 일봉 {len(df)}개 · 기준일 이후 데이터 {len(future)}개는 판독에서 차단됨')
