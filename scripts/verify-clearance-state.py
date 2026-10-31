"""Read-only default publication, analytical and retained execution audit checks."""
from datetime import datetime, timezone
from sqlalchemy import text
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.clearance import ClearanceRequest

s = Settings.from_env()
store, a = OperationalStore(s.database_url), ExasolAnalytics(s)
a.probe()
methods = dict(foundation=store.publication, commerce=store.commerce_publication,
               ads=store.ad_publication, attribution=store.attribution_publication,
               finance=store.finance_publication, inventory=store.inventory_publication,
               diagnostics=store.diagnostics_publication)
pubs = {key: method()[0] for key, method in methods.items()}
versions = dict(foundation='foundation-v1', commerce='commerce-v1', ads='ads-corrected-v1',
                attribution='mapping-attribution-v1', finance='finance-v1',
                inventory='inventory-v1', diagnostics='diagnostics-v1')
for name, p in pubs.items():
    assert p and p.get('version', p.get('dataset_version')) == versions[name], name
    for upstream in ('commerce', 'ads', 'attribution', 'finance', 'inventory'):
        if upstream + '_id' in p:
            assert p[upstream + '_id'] == pubs[upstream]['id'], (name, upstream)
inv = pubs['inventory']
iid, fid, cid = map(str, (inv['id'], inv['finance_id'], inv['commerce_id']))
d = a.clearance_data(iid, fid, cid, ClearanceRequest(), datetime.now(timezone.utc), True)
assert len(d.ranking) == 180 and sum(r.sellable_units for r in d.ranking) == 8817
assert d.revenue_delta_paise == 40500 and d.contribution_delta_paise == -45400
assert not d.feasible and not d.publishing_enabled and not d.mutation_enabled
assert 'stale or future selected stock observations' in d.evidence_blockers
diagnostics = a.diagnostics_data(str(pubs['diagnostics']['id']), expected_inventory=iid)
assert len(diagnostics['recommendations']) == 2
assert not any(r['suggestions'] for r in diagnostics['recommendations'])
assert len(diagnostics['variant_price_evidence']) == 11 and len(diagnostics['ctr_evidence']) == 4
with store.engine.connect() as c:
    audit = c.execute(text("""SELECT COUNT(*) AS receipts, COUNT(*) FILTER (
        WHERE p.approved_at IS NULL OR p.approved_by IS NULL OR p.approved_at>r.recorded_at
        OR r.before_state<>s.intent->'before' OR r.after_state->'value'<>s.intent->'after') AS invalid
        FROM simulated_receipts r JOIN action_steps s ON s.request_id=r.request_id
        JOIN action_plans p ON p.id=s.plan_id""")).mappings().one()
    assert audit['invalid'] == 0
    assert c.execute(text('SELECT COUNT(*) FROM simulated_receipts r LEFT JOIN action_steps s ON s.request_id=r.request_id WHERE s.request_id IS NULL')).scalar() == 0
    assert c.execute(text("SELECT COUNT(*) FROM action_steps WHERE outcome='unknown'")).scalar() == 0
print('PASS: all seven defaults/coherent pins; 180 variants/8817 sellable units; A18 +40500 revenue/-45400 contribution paise; historical stock stale; diagnostics 2/11/4/zero suggestions')
print('Retained execution receipts:', audit['receipts'], '; invalid/orphan receipts and unresolved intents: zero')
