"""Inherited analytical gates and full read-only preservation verification."""
import hashlib
import json
import runpy
import sys
from pathlib import Path
from sqlalchemy import text
from advergent.config import Settings
from advergent.operational import OperationalStore, ROOT
from advergent.exasol import ExasolAnalytics
from advergent.execution import Executor
from advergent.decisions import DecisionService

store=OperationalStore(Settings.from_env().database_url)
tables=('action_plans','action_steps','action_events','simulated_resources','simulated_receipts','execution_control')
def action_hashes():
    with store.engine.connect() as conn:
        return {t:hashlib.sha256('\n'.join(sorted(conn.execute(text('SELECT row_to_json(t)::text FROM '+t+' t')).scalars())).encode()).hexdigest() for t in tables}


hashes=action_hashes()
private=json.loads((ROOT/'.runtime/phase12-preservation.json').read_text())
for name, expected in private.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest().upper()==expected.upper(), 'Preserved file changed'
baseline=ROOT/'.runtime/phase13-action-baseline.json'
if '--capture' in sys.argv:
    if baseline.exists(): assert json.loads(baseline.read_text())==hashes
    else: baseline.write_text(json.dumps(hashes,sort_keys=True))
    print('PASS: six full action/state/control baseline hashes captured; five original private hashes match')
else:
    assert json.loads(baseline.read_text())==hashes, 'Action/state/control history changed'
    runpy.run_path(str(ROOT/'scripts/verify-budget-state.py'))
    a=ExasolAnalytics(Settings.from_env())
    svc=DecisionService(store,a,Executor(store,a))
    snapshot=svc.query()
    assert snapshot.status=='available'
    d=snapshot.data
    assert len(d.decisions)==len({r.key for r in d.decisions})
    assert d.budget['total_paise']==d.budget['allocated_total_paise']==1100000
    assert not any(r.change for r in d.decisions)
    assert all(r.advice=='abstain' for r in d.decisions)
    assert not d.context['cohorts']['history_complete']
    assert d.context['clearance']['contribution_delta_paise']==-45400
    assert all(r['rank'] is None for r in d.context['breakout']['ranking'])
    assert all(p['validity']=='invalidated' for p in d.proposal_validity)
    history=svc.history()['observations']
    assert all(r['financial_outcome_paise'] is None for r in history)
    assert action_hashes()==hashes, 'Read-only audit changed action history/state'
    for name, expected in private.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest().upper()==expected.upper(), 'Audit changed preserved file'
    print('PASS: unified exact resources',len(d.decisions),'; all default advice abstains; fixed total and inherited contexts retained; no financial outcome inferred')
    print('PASS: six full action/state/control hashes and five original private/TLS/launcher/deployment/unrelated-file hashes unchanged')
    print('Retained recommendation observations:',len(history),'; explicit action links:',sum(r['action_id'] is not None for r in history),'; financial outcomes unknown')
