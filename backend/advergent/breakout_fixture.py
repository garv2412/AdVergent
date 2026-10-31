"""Generate raw event deliveries, never dashboard results."""
import json
from datetime import datetime, timedelta, timezone
from .operational import ROOT


def fixture():
    end = datetime(2026, 10, 15, tzinfo=timezone.utc)
    events, coverage = [], []
    for pid in ('p0', 'p1', 'p3'):
        for w, offset, views in (('baseline', -14, 100), ('signal', -7, 200), ('evaluation', 0, 250)):
            coverage.append(dict(product_id=pid, window=w, tracked_days=7, ad_series='synthetic-placement-v1'))
            amounts = dict(view=views, cart=25, impression=1000, click=30) if pid != 'p0' else dict(view=3, cart=1, impression=10, click=2)
            for kind, n in amounts.items():
                for i in range(n):
                    events.append(dict(id=f'{pid}-{w}-{kind}-{i}', product_id=pid, kind=kind,
                        at=(end+timedelta(days=offset, seconds=i)).isoformat(), order_id=None))
    events.append(events[0].copy())
    return dict(version='breakout-v1', observed_at=(end+timedelta(days=7)).isoformat(),
                signal_end=end.isoformat(), events=events, coverage=coverage)


if __name__ == '__main__':
    (ROOT/'fixtures/breakout-v1.json').write_text(json.dumps(fixture(), indent=2)+'\n', encoding='utf-8')
