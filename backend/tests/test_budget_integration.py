import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.api import create_app
from advergent.budget import BudgetRequest
from advergent.config import Settings
from advergent.operational import OperationalStore, ROOT
from advergent.exasol import ExasolAnalytics
from advergent.contracts import AnalyticsUnavailable
from advergent.ads import import_ads
from advergent.attribution import import_attribution
from advergent.finance import import_finance
from advergent.inventory import import_inventory
from advergent.diagnostics import import_diagnostics

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def context():
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    pubs={k:getattr(store,{'ads':'ad'}.get(k,k)+'_publication')()[0] for k in ('inventory','finance','commerce','ads','attribution','diagnostics')}
    pins={k:str(p['id']) for k,p in pubs.items()}
    return s,store,a,pubs,pins


def audit(store):
    with store.engine.connect() as c:
        return tuple(c.execute(text('SELECT COUNT(*) FROM '+t)).scalar() for t in ('action_plans','action_steps','action_events','simulated_receipts')),store.budget_state()


def test_real_budget_sql_sparse_abstention_exact_portfolio_inventory_costs_cohorts_corruption():
    s,store,a,pubs,pins=context();before=audit(store)
    def query():return a.budget_data(pins,datetime.now(timezone.utc),BudgetRequest(),pubs,store.budget_state())
    d=query()
    ads=a.ad_data(pins['ads'])
    assert d.status=='abstain' and len(d.rows)==len(ads['budgets'])==5
    assert d.total_paise==d.allocated_total_paise==sum(b['daily_paise'] for b in ads['budgets'])
    assert len({r.key for r in d.rows})==5
    assert all(r.current_paise==r.allocated_paise==r.minimum_paise==r.maximum_paise for r in d.rows)
    assert all(r.response.status=='abstain' for r in d.rows)
    assert all('stale or future inventory source' in r.blockers for r in d.rows)
    assert any('missing historical product costs or history' in r.blockers and r.historical_contribution_paise is None for r in d.rows)
    assert any(r.shared and len(r.members)==2 for r in d.rows)
    assert not d.cohort_context['history_complete']
    assert all(w['mature']>0 and w['immature']>0 and w['missing']>0 for w in d.cohort_context['windows'])
    assert d.portfolio_contribution_after_ads_paise is None and not d.mutation_enabled and not d.publishing_enabled
    assert sum(o['spend_paise'] for r in d.rows for o in r.response.observations)==ads['spend_paise']
    assert all(not o['complete'] and not o['mature'] and o['contribution_paise'] is None for r in d.rows for o in r.response.observations)
    assert query()==d
    # Genuine source/core mismatch must fail closed, then restore the exact grain.
    report=ads['reports'][0]
    try:
        with a.connection() as c:
            c.execute('UPDATE ADVERGENT.AD_REPORTS SET SPEND_PAISE=SPEND_PAISE+1 WHERE DATASET_ID={id} AND REPORT_KEY={key}',dict(id=pins['ads'],key=report['key']));c.commit()
        with pytest.raises(AnalyticsUnavailable):query()
    finally:
        with a.connection() as c:
            c.execute('UPDATE ADVERGENT.AD_REPORTS SET SPEND_PAISE={v} WHERE DATASET_ID={id} AND REPORT_KEY={key}',dict(v=report['spend_paise'],id=pins['ads'],key=report['key']));c.commit()
    assert query()==d
    assert audit(store)==before


def test_real_authenticated_budget_terms_changed_publication_and_default_restoration():
    s,store,a,pubs,pins=context();before=audit(store)
    token='phase12-'+str(uuid4());store.login(token)
    client=TestClient(create_app(s,store,a))
    assert client.get('/api/budget').status_code==401
    client.cookies.set('advergent_session',token,path='/api')
    headers={'Origin':s.origin,'X-AdVergent-Request':'1'}
    try:
        d=client.get('/api/budget').json()
        assert d['status']=='available' and d['pins']==pins and d['dependencies_current']
        assert client.post('/api/budget/scenario',json={}).status_code==403
        invalid=client.post('/api/budget/scenario',json={'total_paise':d['data']['total_paise']+1},headers=headers)
        assert invalid.status_code==200 and invalid.json()['data']['status']=='infeasible'
        assert client.post('/api/budget/scenario',json={'change_bps':1001},headers=headers).status_code==422
        import_ads(store,a,ROOT/'fixtures/ads-initial-v1.json')
        changed=client.get('/api/budget').json()
        assert changed['status']=='inputs_changed' and changed['data'] is None and changed['queried_at'] is None
    finally:
        import_ads(store,a)
        import_attribution(store,a)
        import_finance(store,a)
        import_inventory(store,a)
        import_diagnostics(store,a)
        store.logout(token)
    assert audit(store)==before


def test_real_fresh_stockout_whole_budget_mapping_blocks_growth_without_action_writes():
    from advergent.execution_scenarios import prepare, restore
    s,store,a,pubs,pins=context();before=audit(store)
    try:
        names=prepare(store,a,mode='pause')  # New synthetic observations only, no consent or writes.
        _,_,_,pubs,pins=context()
        d=a.budget_data(pins,datetime.now(timezone.utc),BudgetRequest(),pubs,store.budget_state())
        row=next(r for r in d.rows if r.budget_id==names['m-set-budget'])
        assert row.products==['p0'] and row.members==[names['m-set']]
        assert 'inventory p0: pause' in row.blockers
        assert row.current_paise==row.allocated_paise==row.minimum_paise==row.maximum_paise
        assert d.total_paise==d.allocated_total_paise
        assert all(abs(r.allocated_paise-r.current_paise)*10000<=r.current_paise*1000 for r in d.rows)
        assert not d.publishing_enabled and not d.mutation_enabled
        # Direct analytical boundary check cannot change the API's actual UTC clock.
        boundary=min(pubs[k]['observed_at'] for k in ('ads','inventory','diagnostics'))+timedelta(seconds=900)
        exact=a.budget_data(pins,boundary,BudgetRequest(),pubs,store.budget_state())
        assert exact.valid_until==boundary.isoformat()
    finally:
        restore(store,a)
    assert audit(store)==before
