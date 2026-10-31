"""Read-only Phase 10 gate and inherited default/action preservation verification."""
import runpy
from datetime import datetime, timezone
from pathlib import Path

state = runpy.run_path(str(Path(__file__).with_name('verify-clearance-state.py')))
a, store, pubs = (state[k] for k in ('a', 'store', 'pubs'))
p = pubs['inventory']
pins = dict(inventory=str(p['id']), **{k:str(p[k+'_id']) for k in ('finance','commerce','ads','attribution')})
d = a.breakout_data(pins, datetime.now(timezone.utc), True)
assert len(d.ranking) == 30 and not any(r.rank is not None for r in d.ranking)
sparse = next(r for r in d.ranking if r.product_id == 'p0')
assert sparse.counts['signal']['view'] == 3 and sparse.counts['signal']['cart'] == 1 and sparse.counts['signal']['click'] == 2
assert 'sparse funnel evidence' in sparse.blockers and sparse.score is None
assert d.duplicate_events == 1 and d.added_revenue_paise == 0
assert not d.publishing_enabled and not d.mutation_enabled
assert next(r for r in d.ranking if r.product_id == 'p1').historical_margin_bps is None
assert next(r for r in d.ranking if r.product_id == 'p3').evaluation == 'sustained'
print('PASS: A19; 30 products/zero current ranks; one duplicate delivery removed; no added revenue or action authority; historical source remains stale')
