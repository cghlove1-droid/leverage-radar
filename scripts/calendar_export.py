"""Export market close instants for browser freshness; rerun after calendar updates."""
import datetime as dt
import exchange_calendars as xcals
from update import ROOT, atomic
cal = xcals.get_calendar('XNYS', start='2020-01-01', end='2031-12-31')
atomic(ROOT/'data/calendar.json', {'source':'exchange_calendars XNYS 4.11.2',
    'coverage_end':'2031-12-31','sessions':[
        {'date':str(s.date()),'close':cal.session_close(s).isoformat()} for s in cal.sessions]})
