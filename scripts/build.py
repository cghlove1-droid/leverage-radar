"""Create a public-only Cloudflare Pages artifact; enforce publication rights."""
import datetime as dt
import json
from pathlib import Path
import shutil
import sys
from update import ROOT, UTC, require_license, validate_prices, calendar, date, DataError

def build(root=ROOT):
    now = dt.datetime.now(UTC)
    market = json.loads((root/'data/market.json').read_text())
    if market.get('demo') is not True:
        config = json.loads((root/'config/licenses.json').read_text())
        lic = require_license(config, 'prices', now)
        if lic['provider'] != market.get('source') or market.get('adjustment') != 'split_only':
            raise DataError('publication_metadata_mismatch')
        validate_prices(market['prices'], date(market['last_session']), calendar(now))
        if date(market['license_valid_until']) < now.date(): raise DataError('published_license_expired')
        for key, value in market.get('indicators', {}).items():
            if value.get('value') is not None:
                require_license(config, key, now)
                if date(value['license_valid_until']) < now.date(): raise DataError('indicator_license_expired')
    out = root/'dist'
    if out.exists(): shutil.rmtree(out)
    out.mkdir()
    for name in ('index.html','assets','data','_headers'):
        source = root/name
        if source.is_dir(): shutil.copytree(source, out/name)
        else: shutil.copy2(source, out/name)
    print('Built dist/ (public assets only)')

if __name__ == '__main__':
    try: build()
    except Exception:
        print('Publication blocked: invalid data or missing/expired redistribution license', file=sys.stderr)
        raise SystemExit(1)
