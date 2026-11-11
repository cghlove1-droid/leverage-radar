import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update as u
from build import build

NOW=dt.datetime(2026,11,10,23,15,tzinfo=u.UTC)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'data').mkdir();(self.root/'config').mkdir()
        self.end=u.last_session(NOW)
        self.cal=u.calendar(NOW)
        self.rows=[{'date':str(s.date()),'QQQ':100+i,'TQQQ':20+i,'SOXL':10+i}
                   for i,s in enumerate(self.cal.sessions_in_range('2025-01-02',str(self.end)))]
        self.payload={'demo':False,'adjustment':'split_only','prices':self.rows,'indicators':{}}
        self.lic={key:{'provider':'licensed_json','public_display':True,'raw_redistribution':True,
                      'reference':'test permission','attribution':'Test provider','valid_until':'2099-12-31'}
                  for key in ['prices','vix','hySpread']}
        self.save_lic()
        (self.root/'data/market.json').write_text('{"demo":true,"prices":[]}')
        self.env={'DATA_PROVIDER':'licensed_json','MARKET_DATA_URL':'https://example.com/data'}
    def save_lic(self): (self.root/'config/licenses.json').write_text(json.dumps(self.lic))
    def run_update(self,payload=None,now=NOW):
        return u.run(self.root,self.env,now,lambda *a,**k:copy.deepcopy(self.payload if payload is None else payload))
    def test_sort_and_validation(self):
        self.assertEqual(u.validate_prices(list(reversed(self.rows)),self.end,self.cal),self.rows)
        for mutate in [lambda r:r.append(r[0]),lambda r:r.pop(50),lambda r:r[0].update(QQQ=float('nan')),
                       lambda r:r[0].update(QQQ=True),lambda r:r[0].update(date='2025-02-30'),lambda r:r[0].update(SOXL=0)]:
            rows=copy.deepcopy(self.rows);mutate(rows)
            with self.assertRaises(u.DataError):u.validate_prices(rows,self.end,self.cal)
    def test_market_calendar_holidays_dst_early_close(self):
        cases=[('2026-11-26T23:15:00+00:00','2026-11-25'),
               ('2026-11-27T17:59:00+00:00','2026-11-25'),
               ('2026-11-27T18:01:00+00:00','2026-11-27'),
               ('2026-07-06T19:59:00+00:00','2026-07-02'),
               ('2026-07-06T20:01:00+00:00','2026-07-06'),
               ('2026-11-10T20:59:00+00:00','2026-11-09')]
        for now,expected in cases:self.assertEqual(str(u.last_session(dt.datetime.fromisoformat(now))),expected)
    def test_no_configuration(self):
        before=(self.root/'data/market.json').read_bytes()
        self.assertEqual(u.run(self.root,{},NOW),0)
        self.assertEqual(before,(self.root/'data/market.json').read_bytes())
    def test_license_gate_and_last_good(self):
        for mutation in [{'public_display':False},{'raw_redistribution':False},{'valid_until':'2000-01-01'},{'reference':''}]:
            lic=copy.deepcopy(self.lic);self.lic['prices'].update(mutation);self.save_lic()
            before=(self.root/'data/market.json').read_bytes()
            self.assertEqual(self.run_update(),1)
            self.assertEqual(before,(self.root/'data/market.json').read_bytes())
            self.lic=lic
    def test_success_and_unchanged_holiday(self):
        for key in ['vix','hySpread']:self.payload['indicators'][key]={'value':20,'date':str(self.end)}
        self.assertEqual(self.run_update(),0)
        data=json.loads((self.root/'data/market.json').read_text());self.assertFalse(data['demo'])
        self.assertEqual(data['indicators']['vix']['value'],20)
        before=(self.root/'data/market.json').read_bytes()
        self.assertEqual(self.run_update(now=NOW+dt.timedelta(minutes=1)),0)
        self.assertEqual(before,(self.root/'data/market.json').read_bytes())
    def test_actual_us_holiday_preserves_snapshot(self):
        wednesday=dt.datetime(2026,11,25,23,15,tzinfo=u.UTC)
        thursday=wednesday+dt.timedelta(days=1)
        end=u.last_session(wednesday)
        self.payload['prices']=[{'date':str(session.date()),'QQQ':100+i,'TQQQ':20+i,'SOXL':10+i}
            for i,session in enumerate(self.cal.sessions_in_range('2025-01-02',str(end)))]
        self.assertEqual(self.run_update(now=wednesday),0)
        before=(self.root/'data/market.json').read_bytes()
        self.assertEqual(self.run_update(now=thursday),0)
        self.assertEqual(before,(self.root/'data/market.json').read_bytes())
    def test_end_to_end_mock_update_build(self):
        self.assertEqual(self.run_update(),0)
        (self.root/'assets').mkdir();(self.root/'assets/app.mjs').write_text('// fixture')
        (self.root/'index.html').write_text('<html>Fixture</html>')
        (self.root/'_headers').write_text('/*')
        build(self.root)
        public=json.loads((self.root/'dist/data/market.json').read_text())
        self.assertFalse(public['demo'])
        self.assertEqual(public['last_session'],str(self.end))
        self.assertFalse((self.root/'dist/config').exists())
        self.assertFalse((self.root/'dist/scripts').exists())
    def test_partial_indicators_no_invented_values(self):
        self.assertEqual(self.run_update(),0)
        data=json.loads((self.root/'data/market.json').read_text())
        self.assertIsNone(data['indicators']['vix']['value'])
        self.assertEqual(json.loads((self.root/'data/status.json').read_text())['state'],'partial')
    def test_stale_prices_failure_and_secret_redaction(self):
        self.assertEqual(self.run_update(),0);before=(self.root/'data/market.json').read_bytes()
        payload=copy.deepcopy(self.payload);payload['prices'].pop()
        self.assertEqual(self.run_update(payload),1)
        self.assertEqual(before,(self.root/'data/market.json').read_bytes())
        def error(*a,**k):raise ValueError('SECRET_API_KEY')
        self.assertEqual(u.run(self.root,self.env,NOW,error),1)
        self.assertNotIn('SECRET_API_KEY',(self.root/'data/status.json').read_text())
    def test_wrong_adjustment_and_demo_refused(self):
        for patch in [{'adjustment':'total_return'},{'demo':True}]:
            with self.assertRaises(u.DataError):u.LicensedJSON('https://example.com',get=lambda *a,**k:{**self.payload,**patch}).load(self.end)
    def test_massive_adapter(self):
        calls=[]
        def get(url,token,params):
            calls.append((url,token,params))
            return {'status':'OK','adjusted':True,'results':[
                {'t':int(dt.datetime(2026,11,10,5,tzinfo=u.UTC).timestamp()*1000),'c':10}]}
        data=u.Massive('fake-key',get).load(self.end)
        self.assertEqual(data['prices'],[{'date':'2026-11-10','QQQ':10,'TQQQ':10,'SOXL':10}])
        self.assertEqual(len(calls),3);self.assertEqual(calls[0][2]['adjusted'],'true')
        with self.assertRaises(u.DataError):u.Massive('',get).load(self.end)
    def test_massive_rejects_unadjusted_pagination(self):
        for response in [{'status':'OK','adjusted':False},{'status':'OK','adjusted':True,'next_url':'x'}]:
            with self.assertRaises(u.DataError):u.Massive('fake',lambda *a,**k:response).load(self.end)
    def test_fred_missing_and_invalid(self):
        payload={'observations':[{'date':'2026-11-10','value':'.'},{'date':'2026-11-09','value':'3.2'}]}
        self.assertEqual(u.fred('BAMLH0A0HYM2','fake',self.end,lambda *a,**k:payload)['value'],3.2)
        with self.assertRaises(u.DataError):u.fred('VIXCLS','',self.end)
        with self.assertRaises(u.DataError):u.normalize_indicator({'value':float('inf'),'date':str(self.end)},self.end,'x','x')
    def test_history_truncation(self):
        self.assertEqual(self.run_update(),0)
        shorter=copy.deepcopy(self.payload);shorter['prices']=shorter['prices'][1:]
        self.assertEqual(self.run_update(shorter),1)
    def test_build_blocks_without_permission(self):
        self.assertEqual(self.run_update(),0)
        self.lic['prices']['public_display']=False;self.save_lic()
        with self.assertRaises(u.DataError):build(self.root)
    def test_http_url_rejected(self):
        with self.assertRaises(u.DataError):u.fetch('http://example.com')

if __name__=='__main__':unittest.main()
