"""Run with an HTTP server serving project root or dist on 127.0.0.1:8000."""
import datetime as dt
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CAL=json.loads((ROOT/'data/calendar.json').read_text())
NOW=dt.datetime.now(dt.timezone.utc)
SESSIONS=[s for s in CAL['sessions'] if dt.datetime.fromisoformat(s['close']) <= NOW]
LAST=SESSIONS[-1]['date']
HISTORY=SESSIONS[-1300:]
ROWS=[{'date':s['date'],'QQQ':100+i/5,'TQQQ':30+i/20,'SOXL':20+i/30} for i,s in enumerate(HISTORY)]
LIVE={'demo':False,'adjustment':'split_only','source':'MOCK — not real API','attribution':'Test fixture only',
      'license_valid_until':'2099-12-31','updated_at':NOW.isoformat(),'last_session':LAST,
      'prices':ROWS,'indicators':{k:{'status':'ok','value':v,'date':LAST,'source':'MOCK',
      'attribution':'Fixture only','license_valid_until':'2099-12-31'} for k,v in [('vix',20),('hySpread',3.2)]}}
count=0

def check(condition,label):
    global count
    assert condition,label
    count+=1;print('PASS',label)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1200})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8000');page.wait_for_selector('#summary .card')
    check('DEMO / DATA NOT CONNECTED' in page.locator('#mode').inner_text(),'unconfigured demo explicitly labeled')
    check(page.locator('#fearScore').inner_text()=='—','no sentiment without external indicators')
    check(page.locator('#mddChart polyline').count()==3,'three ETF chart curves')
    for period in ['3','5','0','1']:page.locator(f'[data-range="{period}"]').click()
    check(page.locator('[data-range="1"]').get_attribute('class')=='active','all time ranges operate')
    page.locator('#nowPrice').fill('0')
    check('0보다' in page.locator('#calcResult').inner_text(),'zero current price rejected')
    page.locator('#nowPrice').fill('40')
    for i in range(1,5):page.locator('#p'+str(i)).fill('0');page.locator('#a'+str(i)).fill('0')
    page.locator('#p1').fill('60');page.locator('#a1').fill('600');page.locator('#p2').fill('40');page.locator('#a2').fill('400')
    check('50.00' in page.locator('#calcResult').inner_text() and '25.00%' in page.locator('#calcResult').inner_text(),'amount average and recovery rendered')
    page.locator('#calcMode').select_option('quantity');page.locator('#a1').fill('10');page.locator('#a2').fill('10')
    check('1,000.00' in page.locator('#calcResult').inner_text(),'quantity totals rendered')
    page.locator('#p1').fill('-1');check('음수' in page.locator('#calcResult').inner_text(),'negative input rejected')
    page.locator('#p1').fill('60')
    page.locator('#csv').set_input_files({'name':'local.csv','mimeType':'text/csv','buffer':b'date,QQQ,TQQQ,SOXL\n2026-11-06,100,20,10\n2026-11-09,101,21,11'})
    check('출처 미검증' in page.locator('#mode').inner_text(),'CSV kept as unverified local source')
    dialogs=[];page.on('dialog',lambda d:(dialogs.append(d.message),d.accept()))
    with page.expect_event('dialog'):
        page.locator('#csv').set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':b'date,QQQ,TQQQ,SOXL\n2026-02-30,1,2,3\n2026-03-01,2,3,4'})
    check(bool(dialogs) and 'CSV' in dialogs[-1],'malformed CSV rejected')
    page.route('**/data/market.json',lambda route:route.fulfill(json=LIVE))
    page.route('**/data/status.json',lambda route:route.fulfill(json={'state':'ok','code':'UPDATED','checked_at':NOW.isoformat()}))
    page.reload();page.wait_for_selector('#summary .card')
    check('실데이터 · 최신 종가'==page.locator('#mode').inner_text(),'mock authorized payload accepted')
    check(page.locator('#fearScore').inner_text()!='—','sentiment enabled for complete fresh mock data')
    LIVE['indicators']['hySpread']['date']='2020-01-02'
    page.reload();page.wait_for_selector('#summary .card')
    check(page.locator('#fearScore').inner_text()=='—','stale spread suppresses sentiment')
    LIVE['attribution']='<img src=x onerror="window.injected=1">'
    page.reload();page.wait_for_selector('#summary .card')
    check(page.evaluate('window.injected||null') is None and page.locator('#notice img').count()==0,'provider metadata safely escaped')
    LIVE['license_valid_until']='2000-01-01'
    page.reload();page.wait_for_selector('#summary .card')
    check('미확인' in page.locator('#mode').inner_text(),'expired license prevents confirmed status')
    page.unroute('**/data/market.json');page.route('**/data/market.json',lambda r:r.fulfill(status=503,body='Unavailable'))
    page.reload();page.wait_for_selector('#summary .card')
    check('DEMO' in page.locator('#mode').inner_text(),'fetch failure falls back to labeled demo')
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function("document.getElementById('mddChart').viewBox.baseVal.width<600")
    check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'mobile viewport has no horizontal overflow')
    check(not errors,'no browser JavaScript errors')
    screenshot=os.environ.get('SCREENSHOT_PATH')
    if screenshot:page.screenshot(path=screenshot,full_page=True)
    browser.close()
print(f'{count} browser checks passed. All connected scenarios used MOCK responses, not real market APIs.')
