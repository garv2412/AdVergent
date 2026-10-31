import os
import json
from datetime import datetime,timezone
from uuid import uuid4
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from advergent.api import create_app
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore
from advergent.clearance import ClearanceRequest
from advergent.contracts import AnalyticsUnavailable
from advergent.inventory import import_inventory
from advergent.diagnostics import import_diagnostics
from advergent.ads import import_ads

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def test_clearance_real_a18_costs_bundle_limits_corruption_and_read_only():
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    p=store.inventory_publication()[0];iid,fid,cid=map(str,(p['id'],p['finance_id'],p['commerce_id']))
    def audit():
        with store.engine.connect() as c:
            return tuple(c.execute(text('SELECT COUNT(*) FROM '+table)).scalar() for table in ('action_plans','action_steps','simulated_receipts','action_events'))
    before=audit()
    def query(**args):return a.clearance_data(iid,fid,cid,ClearanceRequest(**args),datetime.now(timezone.utc),True)
    d=query()
    assert len(d.ranking)==180 and sum(r.sellable_units for r in d.ranking)==8817
    assert d.baseline.revenue_paise==81000 and d.baseline.expected_contribution_paise==32050
    assert d.scenario.revenue_paise==121500 and d.scenario.expected_contribution_paise==-13350
    assert d.revenue_delta_paise==40500 and d.contribution_delta_paise==-45400
    assert d.scenario.blockers==['contribution floor','margin floor'] and not d.feasible
    assert 'stale or future selected stock observations' in d.evidence_blockers
    assert query(scenario_bundles=41).scenario.units==41
    assert 'stock limit: v6' in query(scenario_bundles=41).scenario.blockers
    mixed=query(components=[dict(variant_id='v6',units_per_bundle=2),dict(variant_id='v7',units_per_bundle=1)],scenario_bundles=2,markdown_bps=1000,additional_spend_paise=12345)
    assert mixed.scenario.units==6 and mixed.scenario.additional_spend_paise==12345
    unknown=query(variable_paise_per_unit=None)
    assert unknown.scenario.expected_contribution_paise is None and unknown.contribution_delta_paise is None
    assert 'incomplete cost coverage' in unknown.scenario.blockers and not unknown.scenario.limits_pass
    # Actual Exasol typed/source mismatch; restore the exact old value without changing publications.
    with a.connection() as c:
        old=c.execute('SELECT PRICE_PAISE FROM ADVERGENT.COMMERCE_VARIANTS WHERE DATASET_ID={id} AND SOURCE_ID=\'v6\'',dict(id=cid)).fetchval()
    try:
        with a.connection() as c:
            c.execute('UPDATE ADVERGENT.COMMERCE_VARIANTS SET PRICE_PAISE=1 WHERE DATASET_ID={id} AND SOURCE_ID=\'v6\'',dict(id=cid));c.commit()
        with pytest.raises(AnalyticsUnavailable):query()
    finally:
        with a.connection() as c:
            c.execute('UPDATE ADVERGENT.COMMERCE_VARIANTS SET PRICE_PAISE={price} WHERE DATASET_ID={id} AND SOURCE_ID=\'v6\'',dict(id=cid,price=old));c.commit()
    client=TestClient(create_app(s,store,a));token='clearance-'+str(uuid4());store.login(token)
    try:
        assert client.get('/api/clearance').status_code==401
        client.cookies.set('advergent_session',token,path='/api')
        response=client.get('/api/clearance');assert response.status_code==200
        assert response.json()['data']['scenario']['expected_contribution_paise']==-13350
        assert response.json()['dependencies_current'] and response.json()['input_observations']['commerce']
        assert client.post('/api/clearance/scenario',json={'components':[{'variant_id':'unknown'}]},headers={'Origin':s.origin,'X-AdVergent-Request':'1'}).status_code==422
        assert query().scenario.expected_contribution_paise==-13350
    finally:store.logout(token)
    assert audit()==before
    assert str(store.inventory_publication()[0]['id'])==iid


def test_clearance_fresh_synthetic_stock_and_changed_real_pins(tmp_path):
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    f=store.inventory_publication()[0]['configuration']
    f['version']='phase9-fresh-stock-'+str(uuid4())
    stamp=datetime.now(timezone.utc).isoformat();f['observed_at']=stamp
    for r in f['observations']:r['stock_observed_at']=stamp
    for r in f['resource_states']:r['observed_at']=stamp
    path=tmp_path/'fresh.json';path.write_text(json.dumps(f))
    token='clearance-fresh-'+str(uuid4());client=TestClient(create_app(s,store,a));store.login(token)
    client.cookies.set('advergent_session',token,path='/api')
    headers={'Origin':s.origin,'X-AdVergent-Request':'1'}
    try:
        import_inventory(store,a,path)
        body=dict(scenario_bundles=2,markdown_bps=0)
        d=client.post('/api/clearance/scenario',json=body,headers=headers).json()
        assert d['dependencies_current'] and d['data']['feasible']
        assert d['data']['scenario']['limits_pass'] and not d['data']['evidence_blockers']
        pins=d['pins']
        from advergent.operational import ROOT
        import_ads(store,a,ROOT/'fixtures/ads-initial-v1.json')
        changed=client.post('/api/clearance/scenario',json=body,headers=headers).json()
        assert changed['pins']==pins and not changed['dependencies_current'] and not changed['data']['feasible']
        assert 'pinned dependencies changed' in changed['data']['evidence_blockers']
    finally:
        import_ads(store,a)
        import_inventory(store,a)
        import_diagnostics(store,a)
        store.logout(token)
