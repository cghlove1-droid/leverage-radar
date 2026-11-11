"""Licensed end-of-day ingestion. No scraping; atomic last-good publication."""
from __future__ import annotations
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
import exchange_calendars as xcals

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = ('QQQ', 'TQQQ', 'SOXL')
UTC = dt.timezone.utc

class DataError(Exception): pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DataError('redirect_refused')

def fetch(url, token='', params=None):
    if urlparse(url).scheme != 'https' or urlparse(url).username or urlparse(url).password:
        raise DataError('https_required')
    if params: url += ('&' if '?' in url else '?') + urlencode(params)
    headers = {'Accept': 'application/json', 'User-Agent': 'LeverageRadar/3.0'}
    if token: headers['Authorization'] = 'Bearer ' + token
    for attempt in range(3):
        try:
            with build_opener(NoRedirect()).open(Request(url, headers=headers), timeout=30) as r:
                payload = r.read(12_000_001)
                if len(payload) > 12_000_000: raise DataError('response_too_large')
                return json.loads(payload)
        except HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise DataError(f'provider_http_{e.code}') from None
            time.sleep(min(10, 2 ** attempt))
        except (URLError, TimeoutError):
            if attempt == 2: raise DataError('provider_network_error') from None
            time.sleep(2 ** attempt)
    raise DataError('provider_unavailable')

def date(value):
    if not isinstance(value, str): raise DataError('invalid_date')
    try: parsed = dt.date.fromisoformat(value)
    except ValueError: raise DataError('invalid_date') from None
    if parsed.isoformat() != value: raise DataError('invalid_date')
    return parsed

def positive(v):
    if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v <= 0:
        raise DataError('invalid_price')
    return v

def calendar(now):
    return xcals.get_calendar('XNYS', start='2010-01-01', end=f'{now.year+1}-12-31')

def last_session(now):
    cal = calendar(now)
    local = now.astimezone(ZoneInfo('America/New_York')).date()
    session = cal.date_to_session(local, direction='previous')
    if cal.session_close(session).to_pydatetime() > now:
        session = cal.previous_session(session)
    return session.date()

def validate_prices(rows, expected, cal, minimum=200):
    if not isinstance(rows, list) or len(rows) < minimum: raise DataError('insufficient_history')
    result = []
    seen = set()
    for row in rows:
        d = date(row['date'])
        if d > expected or not cal.is_session(d) or d in seen: raise DataError('invalid_price_session')
        seen.add(d)
        result.append({'date': d.isoformat(), **{k: positive(row[k]) for k in SYMBOLS}})
    result.sort(key=lambda x: x['date'])
    # Internal missing sessions must not silently bias RSI/MDD or comparisons.
    sessions = {x.date().isoformat() for x in cal.sessions_in_range(result[0]['date'], result[-1]['date'])}
    if sessions != {x['date'] for x in result}: raise DataError('missing_price_sessions')
    if date(result[-1]['date']) != expected: raise DataError('latest_close_unavailable')
    return result

def approved(entry, now):
    return (isinstance(entry, dict) and entry.get('public_display') is True
            and entry.get('raw_redistribution') is True and bool(entry.get('reference'))
            and bool(entry.get('attribution')) and date(entry.get('valid_until')) >= now.date())

def require_license(config, key, now):
    if not approved(config.get(key), now): raise DataError('license_not_approved_' + key)
    return config[key]

class Massive:
    """Daily aggregate close, split adjusted, NOT dividend adjusted."""
    def __init__(self, api_key, get=fetch): self.key, self.get = api_key, get
    def load(self, end):
        if not self.key: raise DataError('missing_massive_api_key')
        by_symbol = {}
        for symbol in SYMBOLS:
            url = f'https://api.massive.com/v2/aggs/ticker/{symbol}/range/1/day/2010-03-11/{end}'
            data = self.get(url, self.key, {'adjusted':'true','sort':'asc','limit':50000})
            if data.get('status') not in ('OK', 'DELAYED') or data.get('adjusted') is not True or data.get('next_url'):
                raise DataError('invalid_massive_response')
            prices = {}
            for bar in data.get('results', []):
                d = dt.datetime.fromtimestamp(bar['t']/1000, UTC).astimezone(ZoneInfo('America/New_York')).date().isoformat()
                if d in prices: raise DataError('duplicate_massive_bar')
                prices[d] = positive(bar['c'])
            by_symbol[symbol] = prices
        common = set.intersection(*(set(p) for p in by_symbol.values()))
        # Before the common start inception differences are allowed, afterwards holes are errors.
        rows = [{'date': d, **{k: by_symbol[k][d] for k in SYMBOLS}} for d in sorted(common)]
        return {'demo':False,'adjustment':'split_only','prices':rows,'indicators':{}}

class LicensedJSON:
    """Contracted endpoint returning full history in the documented schema."""
    def __init__(self, url, token='', get=fetch): self.url, self.token, self.get = url, token, get
    def load(self, end):
        data = self.get(self.url, self.token)
        if data.get('demo') is not False or data.get('adjustment') != 'split_only':
            raise DataError('invalid_endpoint_metadata')
        return data

def fred(series, key, end, get=fetch):
    if not key: raise DataError('missing_fred_api_key')
    payload = get('https://api.stlouisfed.org/fred/series/observations', params={
        'api_key':key,'file_type':'json','series_id':series,'sort_order':'desc',
        'observation_end':str(end),'limit':20})
    for item in payload.get('observations', []):
        if item['value'] == '.': continue
        d = date(item['date'])
        v = float(item['value'])
        if not math.isfinite(v) or v < 0 or d > end: raise DataError('invalid_indicator')
        return {'value':v,'date':str(d)}
    raise DataError('indicator_missing')

def normalize_indicator(item, end, source, attribution):
    if not isinstance(item, dict): raise DataError('indicator_missing')
    v = item.get('value')
    if isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) or v < 0:
        raise DataError('invalid_indicator')
    d = date(item.get('date'))
    if d > end: raise DataError('future_indicator')
    return {'value':v,'date':str(d),'source':source,'attribution':attribution,'status':'ok'}

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
            name = f.name
            json.dump(data, f, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and Path(name).exists(): Path(name).unlink()

def run(root=ROOT, env=None, now=None, get=fetch):
    env = os.environ if env is None else env
    now = now or dt.datetime.now(UTC)
    status_path, market_path = root/'data/status.json', root/'data/market.json'
    base = {'checked_at': now.isoformat()}
    try:
        expected = last_session(now)
        base['expected_session'] = str(expected)
        if not env.get('DATA_PROVIDER'):
            atomic(status_path, {**base,'state':'not_configured','code':'DATA_NOT_CONNECTED'})
            return 0
        config = json.loads((root/'config/licenses.json').read_text())
        license = require_license(config, 'prices', now)
        provider = env['DATA_PROVIDER']
        if provider not in ('massive','licensed_json') or license.get('provider') != provider:
            raise DataError('provider_license_mismatch')
        adapter = Massive(env.get('MASSIVE_API_KEY',''), get) if provider == 'massive' else LicensedJSON(env.get('MARKET_DATA_URL',''), env.get('MARKET_DATA_TOKEN',''), get)
        payload = adapter.load(expected)
        rows = validate_prices(payload.get('prices'), expected, calendar(now))
        if market_path.exists():
            old = json.loads(market_path.read_text())
            if old.get('demo') is False and old.get('prices'):
                if rows[0]['date'] > old['prices'][0]['date']: raise DataError('history_truncated')
                if rows[-1]['date'] < old['prices'][-1]['date']: raise DataError('history_regression')
        indicators = {}
        for key, series in [('vix','VIXCLS'), ('hySpread','BAMLH0A0HYM2')]:
            try:
                lic = require_license(config, key, now)
                source = lic.get('provider')
                if source == 'fred': item = fred(series, env.get('FRED_API_KEY',''), expected, get)
                elif source == 'licensed_json' and provider == 'licensed_json': item = payload.get('indicators',{}).get(key)
                else: raise DataError('indicator_provider_mismatch')
                indicators[key] = normalize_indicator(item, expected, f'{source}: {series}', lic['attribution'])
                indicators[key]['license_valid_until'] = lic['valid_until']
            except (DataError, KeyError, TypeError, ValueError):
                indicators[key] = {'status':'unavailable','value':None,'date':None,'source':series}
        output = {'schema_version':1,'demo':False,'adjustment':'split_only',
                  'source':provider,'attribution':license['attribution'],
                  'updated_at':now.isoformat(),'last_session':str(expected),
                  'license_valid_until':license['valid_until'],'prices':rows,'indicators':indicators}
        # Same content on a holiday: retain the complete last-good snapshot and its timestamp.
        unchanged = market_path.exists() and all(old.get(k) == output.get(k) for k in output if k != 'updated_at')
        if not unchanged: atomic(market_path, output)
        partial = any(v['status'] != 'ok' for v in indicators.values())
        atomic(status_path, {**base,'state':'partial' if partial else 'ok','code':'INDICATORS_UNAVAILABLE' if partial else ('NO_CHANGE' if unchanged else 'UPDATED')})
        return 0
    except Exception as exc:
        # Never serialize exception messages/URLs/API response bodies, which can contain keys.
        code = str(exc) if isinstance(exc, DataError) else 'invalid_provider_payload_or_config'
        atomic(status_path, {**base,'state':'error','code':code})
        print('Update failed:', code, file=sys.stderr)
        return 1

if __name__ == '__main__': raise SystemExit(run())
