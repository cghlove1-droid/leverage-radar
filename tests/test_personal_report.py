import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import personal_report as p
from update import UTC, DataError, calendar
NOW=dt.datetime(2026,11,11,0,0,tzinfo=UTC)

class PersonalReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.output=Path(self.tmp.name)
        self.cal=calendar(NOW);self.rows=[{'date':str(d.date()),'QQQ':100+i,'TQQQ':20+i,'SOXL':10+i}
            for i,d in enumerate(self.cal.sessions_in_range('2025-01-02','2026-11-10'))]
    @staticmethod
    def csv(url):
        series='BAMLH0A0HYM2' if 'BAMLH0A0HYM2' in url else 'VIXCLS'
        return f'observation_date,{series}\n2026-11-09,20\n2026-11-10,21\n'
    def test_no_key_has_real_indicators_but_no_demo_etfs(self):
        report=p.collect(self.output,{},NOW,get_csv=self.csv)
        self.assertEqual(report['price_status'],'not_connected');self.assertEqual(report['prices'],[])
        self.assertEqual(report['indicators']['vix']['value'],21)
        self.assertIsNone(report['metrics']['score'])
        self.assertIn('미연결',(self.output/'morning-report.html').read_text())
    def test_personal_output_cannot_enter_public_repository(self):
        with self.assertRaises(DataError):p.safe_output(p.ROOT/'reports')
    def test_download_selects_latest_and_skips_missing(self):
        text='observation_date,VIXCLS\n2026-11-10,.\n2026-11-09,20\n2026-11-06,25\n'
        self.assertEqual(p.fred_download('VIXCLS',dt.date(2026,11,10),lambda u:text)['date'],'2026-11-09')
        for value in ['-1','NaN','Infinity']:
            with self.assertRaises(DataError):p.fred_download('VIXCLS',dt.date(2026,11,10),lambda u:f'observation_date,VIXCLS\n2026-11-10,{value}\n')
    def test_missing_download_keeps_unavailable(self):
        def failed(url):raise RuntimeError('fake-secret-token')
        report=p.collect(self.output,{},NOW,get_csv=failed)
        self.assertEqual(report['indicators']['vix']['status'],'unavailable')
        self.assertNotIn('fake-secret-token',(self.output/'morning.private.json').read_text())
    def test_complete_private_mock_report(self):
        with patch.object(p.Massive,'load',return_value={'prices':self.rows}) as load:
            report=p.collect(self.output,{'MASSIVE_API_KEY':'fake-secret'},NOW,get_csv=self.csv)
        self.assertEqual(report['price_status'],'ok');self.assertIsNotNone(report['metrics']['score'])
        self.assertEqual(load.call_args.kwargs['start'],'2024-11-21')
        self.assertNotIn('fake-secret',(self.output/'morning.private.json').read_text())
        self.assertEqual(len(report['metrics']['etfs']),3)
    def test_cache_is_private_and_labeled(self):
        with patch.object(p.Massive,'load',return_value={'prices':self.rows}):
            p.collect(self.output,{'MASSIVE_API_KEY':'fake'},NOW,get_csv=self.csv)
        report=p.collect(self.output,{},NOW,get_csv=self.csv)
        self.assertEqual(report['price_status'],'cached');self.assertFalse(report['price_fresh'])
        self.assertIsNone(report['metrics']['score'])
    def test_stale_spread_suppresses_score(self):
        def get(url):
            if 'BAMLH0A0HYM2' in url:return 'observation_date,BAMLH0A0HYM2\n2026-10-01,3.2\n'
            return self.csv(url)
        with patch.object(p.Massive,'load',return_value={'prices':self.rows}):
            report=p.collect(self.output,{'MASSIVE_API_KEY':'fake'},NOW,get_csv=get)
        self.assertEqual(report['indicators']['hySpread']['status'],'stale');self.assertIsNone(report['metrics']['score'])
    def test_html_escapes_observation_metadata(self):
        report=p.collect(self.output,{},NOW,get_csv=self.csv)
        report['indicators']['vix']['attribution']='<script>window.injected=1</script>'
        self.assertNotIn('<script>',p.render(report))

if __name__=='__main__':unittest.main()
