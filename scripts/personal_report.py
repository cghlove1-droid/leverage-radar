"""Private morning report. Never writes personal observations to the public repo."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import html
import io
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from zoneinfo import ZoneInfo
from update import ROOT, UTC, SYMBOLS, Massive, DataError, NoRedirect, atomic, calendar, date, fetch, last_session, validate_prices

FRED_SERIES={'vix':('VIXCLS','CBOE VIX via FRED. Copyright Chicago Board Options Exchange, Inc. Reprinted with permission.'),
             'hySpread':('BAMLH0A0HYM2','ICE BofA US High Yield Index Option-Adjusted Spread via FRED. Copyright ICE Data Indices. Personal use only.')}

def fetch_csv(url):
    with build_opener(NoRedirect()).open(Request(url,headers={'User-Agent':'LeverageRadar/3.0 personal report'}),timeout=30) as response:
        data=response.read(1_000_001)
    if len(data)>1_000_000:raise DataError('fred_csv_too_large')
    return data.decode('utf-8-sig')

def fred_download(series,end,get_csv=fetch_csv):
    # Official FRED download endpoint; not HTML scraping or the CNN unofficial API.
    start=end-dt.timedelta(days=40)
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?'+urlencode({'id':series,'cosd':str(start),'coed':str(end)})
    reader=csv.DictReader(io.StringIO(get_csv(url)))
    if not reader.fieldnames or reader.fieldnames[0] not in ('observation_date','DATE') or series not in reader.fieldnames:
        raise DataError('invalid_fred_csv')
    valid=[]
    for row in reader:
        if row[series] in ('','.'):continue
        d=date(row[reader.fieldnames[0]])
        value=float(row[series])
        import math
        if d>end or value<0 or not math.isfinite(value):raise DataError('invalid_fred_csv_value')
        valid.append({'date':str(d),'value':value})
    if not valid:raise DataError('fred_observation_missing')
    return max(valid,key=lambda x:x['date'])

def fresh(observed,expected,cal,lag=0):
    if not observed or date(observed)>expected:return False
    sessions=cal.sessions_in_range(observed,str(expected))
    return sum(s.date()>date(observed) for s in sessions)<=lag

def safe_output(output,root=ROOT):
    output=Path(output).resolve();root=root.resolve()
    if output==root or root in output.parents:raise DataError('personal_output_must_be_outside_public_repo')
    output.mkdir(parents=True,exist_ok=True)
    return output

def collect(output,env=None,now=None,get=fetch,get_csv=fetch_csv):
    env=os.environ if env is None else env;now=now or dt.datetime.now(UTC)
    output=safe_output(output);cal=calendar(now);expected=last_session(now)
    report={'schema_version':1,'access':'personal_only','demo':False,'generated_at':now.isoformat(),
            'expected_session':str(expected),'adjustment':'split_only','prices':[],
            'price_status':'not_connected','price_code':'MASSIVE_API_KEY_REQUIRED','indicators':{}}
    key=env.get('MASSIVE_API_KEY','')
    cache=output/'prices.private.json'
    if key:
        try:
            # Within the Basic plan's 2-year history. No attempt to bypass entitlements.
            start=str(now.date()-dt.timedelta(days=720))
            payload=Massive(key,get).load(expected,start=start)
            report['prices']=validate_prices(payload['prices'],expected,cal)
            report['price_status']='ok';report['price_code']='CONNECTED'
            atomic(cache,{'prices':report['prices'],'source':'Massive personal API','updated_at':now.isoformat()})
        except Exception:
            report['price_status']='error';report['price_code']='MASSIVE_FETCH_OR_VALIDATION_FAILED'
    if not report['prices'] and cache.exists():
        try:
            previous=json.loads(cache.read_text());rows=previous['prices'];last=date(rows[-1]['date'])
            if last>expected:raise DataError('future_cache')
            report['prices']=validate_prices(rows,last,cal)
            report['price_status']='cached';report['cached_at']=previous['updated_at']
        except Exception:pass
    report['price_fresh']=report['price_status']=='ok' and fresh(report['prices'][-1]['date'],expected,cal)
    for name,(series,credit) in FRED_SERIES.items():
        item={'status':'unavailable','value':None,'date':None,'source':f'https://fred.stlouisfed.org/series/{series}','attribution':credit}
        try:
            value=fred_download(series,expected,get_csv)
            item.update(value);item['status']='ok' if fresh(item['date'],expected,cal,3) else 'stale'
        except Exception:item['code']='FRED_DOWNLOAD_FAILED'
        report['indicators'][name]=item
    data={'prices':report['prices'],'priceFresh':report['price_fresh'],
          'vix':report['indicators']['vix']['value'] if report['indicators']['vix']['status']=='ok' else None,
          'spread':report['indicators']['hySpread']['value'] if report['indicators']['hySpread']['status']=='ok' else None}
    result=subprocess.run(['node',str(ROOT/'scripts/report_metrics.mjs')],input=json.dumps(data),text=True,capture_output=True,check=True)
    report['metrics']=json.loads(result.stdout)
    atomic(output/'morning.private.json',report)
    (output/'morning-report.html').write_text(render(report),encoding='utf-8')
    (output/'morning-report.md').write_text(markdown(report),encoding='utf-8')
    return report

def fmt(value,suffix=''):
    return '미확인' if value is None else f'{value:,.2f}{suffix}'

def markdown(report):
    metrics=report['metrics'];date_text=dt.datetime.fromisoformat(report['generated_at']).astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M KST')
    lines=[f'# LEVERAGE RADAR 아침 보고서 · {date_text}',
           f"개인 열람 전용 · 최근 완료 미국 거래일 {report['expected_session']}",
           f"ETF 연결: {report['price_status']} ({report['price_code']})",'']
    if report['prices']:lines.append(f"ETF 관측일 {report['prices'][-1]['date']} · 제공 이력 {report['prices'][0]['date']}~{report['prices'][-1]['date']} · 분할 조정/배당 미조정")
    lines+=['','| ETF | 종가 USD | 전일 대비 | 고점 대비 | 제공 기간 MDD |','|---|---:|---:|---:|---:|']
    by_symbol={item['symbol']:item for item in metrics['etfs']}
    for symbol in SYMBOLS:
        item=by_symbol.get(symbol,{})
        lines.append(f"| {symbol} | {fmt(item.get('close'))} | {fmt(item.get('dayChange'),'%')} | {fmt(item.get('drawdown'),'%')} | {fmt(item.get('mdd'),'%')} |")
    lines+=['',f"QQQ RSI(14): {fmt(metrics['rsi'])} · SMA200: {fmt(metrics['sma200'])} · 이격도: {fmt(metrics['delta'],'%')}"]
    for key,label in [('vix','VIX'),('hySpread','하이일드 OAS (%)')]:
        item=report['indicators'][key];lines.append(f"- {label}: {fmt(item['value'])} · 관측일 {item['date'] or '없음'} · {item['status']} · 출처 {item['source']}")
    lines += ['',f"자체 심리지수: {fmt(metrics['score'])} / 100 (CNN 지수 아님)",
              'CNN 공식 지수: https://www.cnn.com/markets/fear-and-greed',
              '', '휴장·주말에는 마지막 거래일 자료입니다. 누락·지연 값을 추정하지 않습니다. 무료 ETF 요금제의 약 2년 이력에서는 3·5년/설정 이후 MDD를 계산할 수 없습니다.',
              'ETF 연결 전에는 가상 가격을 사용하지 않습니다. Massive 무료 개인용 API 키를 환경 설정에 등록하면 연결할 수 있습니다.',
              '', *[v['attribution'] for v in report['indicators'].values()]]
    return '\n'.join(lines)+'\n'

def render(report):
    escape=html.escape;metrics=report['metrics'];rows=report['prices']
    day=dt.datetime.fromisoformat(report['generated_at']).astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y.%m.%d · %H:%M KST')
    cards=[];lookup={r['symbol']:r for r in metrics['etfs']}
    for symbol in SYMBOLS:
        r=lookup.get(symbol,{})
        cards.append(f"<article><h2>{symbol}</h2><strong>{('$'+fmt(r['close'])) if r else '미연결'}</strong><p>전일 {fmt(r.get('dayChange'),'%')}<br>고점 대비 {fmt(r.get('drawdown'),'%')}<br>기간 MDD {fmt(r.get('mdd'),'%')}</p></article>")
    risk=[]
    for key,label,unit in [('vix','VIX',''),('hySpread','하이일드 OAS','%')]:
        i=report['indicators'][key]
        risk.append(f"<article><h2>{label}</h2><strong>{fmt(i['value'],unit)}</strong><p>{escape(i['date'] or '관측일 없음')} · {escape(i['status'])}<br>{escape(i['attribution'])}</p></article>")
    chart='<p>ETF API 키 미설정: 가상 가격으로 차트를 만들지 않습니다.</p>'
    if rows:
        chart='<svg viewBox="0 0 1000 240" role="img" aria-label="제공 이력 고점 대비 낙폭">'
        for index,item in enumerate(metrics['etfs']):
            series=item['series'];points=' '.join(f"{40+i/max(1,len(series)-1)*930:.2f},{20-p['value']*1.8:.2f}" for i,p in enumerate(series))
            color=['#70b7ff','#ffc16d','#ff879e'][index]
            chart+=f'<polyline points="{points}" stroke="{color}" stroke-width="2" fill="none"/><text x="{40+index*150}" y="230" fill="{color}">{item["symbol"]}</text>'
        chart+='</svg>'
    price_note=(f"종가 기준 {rows[-1]['date']} · 이력 {rows[0]['date']}~{rows[-1]['date']} · 분할 조정/배당 미조정" if rows else 'ETF 미연결 · Massive 개인용 API 키 필요')
    state='정상 연결' if report['price_fresh'] else 'ETF 미연결/미확인'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>LEVERAGE RADAR 아침 보고서</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#0b1020;color:#edf3ff;font:17px system-ui,sans-serif}}main{{max-width:1160px;margin:auto;padding:38px}}header{{display:flex;justify-content:space-between;align-items:center}}h1{{margin:8px 0;font-size:32px}}h2{{font-size:17px;margin:0 0 14px}}.eyebrow{{color:#70b7ff;font-size:13px;letter-spacing:2px}}.badge{{border:1px solid #b78d4c;border-radius:30px;color:#ffd08e;padding:10px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin:22px 0}}article,section{{background:#151d31;border:1px solid #2a3650;border-radius:16px;padding:22px}}strong{{font-size:32px}}p{{color:#a9b8cf;line-height:1.7;font-size:14px}}svg{{width:100%;max-height:270px}}.note{{border-left:3px solid #70b7ff;padding:12px 18px;background:#182b3c}}footer{{font-size:12px;color:#a9b8cf;line-height:1.7}}a{{color:#70b7ff}}@media(max-width:650px){{main{{padding:20px}}.grid{{grid-template-columns:1fr}}header{{display:block}}.badge{{display:inline-block;margin-top:12px}}}}
    </style></head><body><main><header><div><div class="eyebrow">PRIVATE MORNING BRIEF</div><h1>LEVERAGE RADAR</h1><p>{day} · 최근 완료 거래일 {report['expected_session']}</p></div><span class="badge">개인 열람 전용 · {state}</span></header>
    <div class="note">{escape(price_note)}<br>휴장일에는 마지막 거래일 자료를 사용합니다. 누락 값은 추정하지 않습니다.</div>
    <div class="grid">{''.join(cards)}</div><section><h2>제공 이력 내 누적 고점 대비 낙폭</h2>{chart}<p>무료 요금제는 약 2년 이력이며, 3·5년 또는 설정 이후 MDD가 아닙니다.</p></section>
    <div class="grid">{''.join(risk)}<article><h2>QQQ 기술지표 / 자체 심리</h2><p>RSI(14) <b>{fmt(metrics['rsi'])}</b><br>SMA200 ${fmt(metrics['sma200'])}<br>200일선 이격도 {fmt(metrics['delta'],'%')}<br>자체 심리 <b>{fmt(metrics['score'])}</b> / 100</p><p>필수 지표가 미확인이면 점수를 표시하지 않습니다.</p></article></div>
    <footer>개인 비상업용 보고서 · 시세 출처 Massive personal API / 지표 출처 FRED (CBOE·ICE). 공개 재배포용이 아닙니다.<br>캡처 시각과 지표 관측일은 다릅니다. 정보 제공용이며 투자 조언이 아닙니다.<br><a href="https://www.cnn.com/markets/fear-and-greed">CNN 공식 Fear &amp; Greed 확인</a> · 자체 지수는 CNN 지수와 무관합니다.</footer></main></body></html>'''

def screenshot(output):
    from playwright.sync_api import sync_playwright
    output=Path(output)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1200,'height':1000},device_scale_factor=1.5)
        page.goto((output/'morning-report.html').as_uri());page.evaluate('document.fonts.ready')
        page.screenshot(path=str(output/'morning-report.png'),full_page=True)
        browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--screenshot',action='store_true');args=parser.parse_args()
    try:
        report=collect(args.output)
        if args.screenshot:screenshot(args.output)
        print(json.dumps({'price_status':report['price_status'],'indicators':{k:v['status'] for k,v in report['indicators'].items()},'personal_only':True}))
    except Exception:
        print('Personal report failed; no credentials or raw error responses logged.')
        raise SystemExit(1)
