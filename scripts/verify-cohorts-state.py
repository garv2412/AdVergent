"""Read-only A20 and inherited A18/A19/default/action preservation audit."""
import runpy
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

state = runpy.run_path(str(Path(__file__).with_name('verify-breakout-state.py')))
a, store, pubs = (state[k] for k in ('a', 'store', 'pubs'))
p = pubs['finance']
pins = dict(finance=str(p['id']), **{k: str(p[k+'_id']) for k in ('commerce', 'ads', 'attribution')})
cutoff = min(datetime.now(timezone.utc), datetime.fromisoformat(p['configuration']['as_of']),
             *(pubs[k]['observed_at'] for k in pins))
d = a.cohort_data(pins, cutoff, p['configuration']['period_start'])
assert not d.history_complete and not d.publishing_enabled and not d.mutation_enabled
assert {w.mature for c in d.customers for w in c.windows} == {True, False}
assert any(len(c.weights) > 1 for c in d.customers)
assert any(w.missing_events for c in d.customers for w in c.windows)
assert len({c.customer_id for c in d.customers}) == len(d.customers)
for c in d.customers:
    assert sum(map(Fraction, c.weights.values())) == 1 and not c.history_complete
    for w in c.windows:
        if w.contribution_before_ads_paise is not None:
            assert sum(w.product_contribution_paise.values()) == w.contribution_before_ads_paise
for days in (60, 90):
    assert sum((Fraction(b.customer_weight) for b in d.buckets if b.days == days), Fraction()) == len(d.customers)
    assert sum(b.known_customer_contribution_paise for b in d.buckets if b.days == days) == sum(
        w.contribution_before_ads_paise or 0 for c in d.customers for w in c.windows if w.days == days)
print('PASS: A20; assigned', len(d.customers), '; without delivery', d.customers_without_delivery,
      '; zero value unassigned', d.zero_value_unassigned, '; multi-product', sum(len(c.weights)>1 for c in d.customers))
for days in (60, 90):
    windows = [w for c in d.customers for w in c.windows if w.days == days]
    print(days, 'days: mature', sum(w.mature for w in windows), '; immature', sum(not w.mature for w in windows),
          '; missing-cost windows', sum(w.missing_events>0 for w in windows))
print('History incomplete; historical cutoff', d.cutoff, '; no publishing or mutation authority')
