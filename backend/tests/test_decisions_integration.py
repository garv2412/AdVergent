import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from advergent.api import create_app
from advergent.decisions import DecisionService, TrackDecision
from advergent.execution import Executor
from advergent.execution_scenarios import prepare, restore
from test_budget_integration import context, audit

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def test_real_unified_default_scope_persisted_observation_and_no_action_inference():
    settings,store,a,pubs,pins=context();before=audit(store)
    token='phase13-'+str(uuid4());store.login(token)
    client=TestClient(create_app(settings,store,a));headers={'Origin':settings.origin,'X-AdVergent-Request':'1'}
    try:
        assert client.get('/api/decisions').status_code==401
        client.cookies.set('advergent_session',token,path='/api')
        s=client.get('/api/decisions').json()
        assert s['status']=='available' and s['pins']==pins and len(s['data']['decisions'])==19
        d=s['data'];assert len({r['key'] for r in d['decisions']})==19
        assert all(r['advice']=='abstain' and r['change'] is None for r in d['decisions'])
        assert d['budget']['total_paise']==d['budget']['allocated_total_paise']==1100000
        assert not d['context']['cohorts']['history_complete']
        assert all(w['mature']>0 and w['immature']>0 and w['missing']>0 for w in d['context']['cohorts']['windows'])
        assert d['context']['clearance']['contribution_delta_paise']==-45400
        assert all(r['rank'] is None for r in d['context']['breakout']['ranking'])
        body=dict(digest=d['digest'],key=d['decisions'][0]['key'])
        assert client.post('/api/decisions/track',json=body).status_code==403
        response=client.post('/api/decisions/track',json=body,headers=headers)
        assert response.status_code==200,response.text
        first=response.json()['observations']
        assert first and all(r['outcome']=='not_observed' and r['financial_outcome_paise'] is None for r in first)
        assert len(client.post('/api/decisions/track',json=body,headers=headers).json()['observations'])==len(first)
        assert client.post('/api/decisions/track',json=dict(body,digest='0'*64),headers=headers).status_code==409
        linked=dict(body,action_id=str(uuid4()))
        assert client.post('/api/decisions/track',json=linked,headers=headers).status_code==409
        assert client.get('/api/decisions/history').json()['observations']==first
    finally:store.logout(token)
    assert audit(store)==before


def test_real_fresh_inventory_protection_changed_pins_and_default_restore():
    _,store,a,_,_=context();before=audit(store)
    svc=DecisionService(store,a,Executor(store,a))
    try:
        names=prepare(store,a,mode='pause')
        s=svc.query();assert s.status=='available'
        row=next(r for r in s.data.decisions if r.resource_id==names['m-set'])
        assert row.advice=='pause_review' and row.change['after']=='paused'
        assert row.products==['p0']
        assert row.evidence['budget']['allocated_paise']==row.evidence['budget']['current_paise']
        assert row.key not in {r.key for r in s.data.decisions if r.resource_id==names['m-set-budget']}
        assert not s.data.mutation_enabled and not s.data.publishing_enabled
        saved=svc.track(TrackDecision(digest=s.data.digest,key=row.key))
        assert any(r['digest']==s.data.digest and r['resource_key']==row.key and r['outcome']=='not_observed' for r in saved['observations'])
        # Genuine coherent-pointer change midway through a query suppresses it all.
        original=a.clearance_data
        def changed(*args,**kwargs):
            result=original(*args,**kwargs)
            from advergent.ads import import_ads
            import_ads(store,a)
            return result
        a.clearance_data=changed
        changed_result=svc.query()
        assert changed_result.status=='inputs_changed' and changed_result.data is None and changed_result.queried_at is None
    finally:
        restore(store,a)
        if 'original' in locals():a.clearance_data=original
    current=svc.query()
    assert current.status=='available'
    assert any(r['digest']==s.data.digest and r['key']==row.key and r['validity']=='invalidated' for r in current.data.tracked_validity)
    assert audit(store)==before
