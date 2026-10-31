"""Read-only inherited gates, fixed portfolio and action/state preservation audit."""
import runpy
from datetime import datetime, timezone
from pathlib import Path
from advergent.budget import BudgetRequest

state=runpy.run_path(str(Path(__file__).with_name('verify-cohorts-state.py')))
a,store,pubs=(state[k] for k in ('a','store','pubs'))
pins={k:str(pubs[k]['id']) for k in ('commerce','ads','attribution','finance','inventory','diagnostics')}
before=store.budget_state()
d=a.budget_data(pins,datetime.now(timezone.utc),BudgetRequest(),pubs,before)
assert len(d.rows)==5 and len({r.key for r in d.rows})==5
assert d.status=='abstain' and d.total_paise==d.allocated_total_paise
assert all(r.allocated_paise==r.current_paise==r.minimum_paise==r.maximum_paise for r in d.rows)
assert all(r.response.status=='abstain' for r in d.rows)
assert all(abs(r.allocated_paise-r.current_paise)*10000<=r.current_paise*1000 for r in d.rows)
assert not d.cohort_context['history_complete']
assert all(w['mature']>0 and w['immature']>0 and w['missing']>0 for w in d.cohort_context['windows'])
assert d.conservative_delta_paise is None and d.portfolio_contribution_after_ads_paise is None
assert not d.publishing_enabled and not d.mutation_enabled
assert store.budget_state()==before
print('PASS: Phase 12 real SQL default budget audit; five distinct budgets; fixed total',d.total_paise,
      'paise; all frozen; sparse response abstains; separate mature/immature/missing-cost cohort context; action state unchanged')
print('A21 attractive-stockout policy and fresh real-stockout checks are separately recorded in the Phase 12 handoff')
