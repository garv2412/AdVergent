from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from contextlib import nullcontext
import pytest
from fastapi.testclient import TestClient
from advergent.api import create_app
from advergent.budget import allocate, BudgetRequest
from advergent.attribution import Mapping
from advergent.commerce import canonical
from advergent.contracts import AnalyticsUnavailable
from advergent.decisions import resolve, proposal_validity, DecisionService, TrackDecision
from advergent.execution import ExecutionBlocked
from test_budget import resource
from test_foundation import MemoryStore, SETTINGS, HEADERS, sign_in


def example():
    at=datetime.now(timezone.utc)
    resources=[];recs=[];ds=[];mappings=[];states=[];products=[]
    for rid in ('donor','grow'):
        resources.append(dict(platform='meta',account_id='synthetic',id=rid,parent_id=None,status='active',status_control_supported=True,
            budget_control_supported=True,affected_budget_ids=[rid],effective_budget_id=rid))
        recs.append(dict(platform='meta',account_id='synthetic',resource_id=rid,affected_products=[rid],action='none',eligibility='abstain',blockers=[]))
        ds.append(dict(platform='meta',account_id='synthetic',resource_id=rid,blockers=[],suggestions=[],destinations=[]))
        mappings.append(Mapping.model_validate_json(canonical(dict(id=rid,platform='meta',account_id='synthetic',resource_id=rid,products=[rid],
            provenance='test',confidence_bps=9500,valid_from=(at-timedelta(days=1)).isoformat(),valid_to=(at+timedelta(days=1)).isoformat(),actor='test',reason='test'))))
        states.append(dict(platform='meta',account_id='synthetic',resource_id=rid,observed_at=at.isoformat(),blockers=[]))
        products.append(dict(product_id=rid,fresh=True,pause_eligible=True,throttle_eligible=True,recovery_stock_eligible=False,risk='pause',variants=[dict(stock_observed_at=at.isoformat())]))
    ev=dict(at=at,pins={k:k for k in ('commerce','ads','attribution','finance','inventory','diagnostics')},source_deadline=at+timedelta(seconds=900),
        ads=dict(resources=resources,budgets=[dict(platform='meta',account_id='synthetic',id=r,status='active',budget_control_supported=True,shared=False,daily_paise=10000,member_ids=[r]) for r in ('donor','grow')]),
        inventory=dict(products=products,recommendations=recs,assumptions={'freshness_seconds':900}),
        diagnostics=dict(recommendations=ds,assumptions={'freshness_seconds':900}),mappings=mappings,stock_states=states)
    budget=allocate([resource('donor',1),resource('grow',5)],BudgetRequest(),{'history_complete':False})
    state=dict(resources={},stopped=False,unresolved=0)
    return ev,budget,state


def run(ev,budget,state,plans=()):return resolve(ev,budget,{'cohorts':budget.cohort_context},state,list(plans),ev['at'])


def test_unique_resource_budget_owner_conflict_freezes_both_legs_and_explanation():
    ev,b,s=example();ev['inventory']['recommendations'][1].update(action='pause',eligibility='eligible')
    d=run(ev,b,s)
    assert len(d.decisions)==len({r.key for r in d.decisions})==2
    grow=next(r for r in d.decisions if r.resource_id=='grow')
    assert grow.advice=='pause_review' and grow.change['after']=='paused'
    assert grow.evidence['budget']['allocated_paise']==11000
    assert 'inventory' in grow.explanation.lower() and grow.suppressed
    assert d.budget['allocation_withheld']
    assert d.budget['allocated_total_paise']==d.budget['total_paise']==20000
    assert all(r['allocated_paise']==r['current_paise'] for r in d.budget['allocations'])
    assert not d.context['cohorts']['history_complete'] and not d.mutation_enabled
    assert d.digest==run(ev,b,s).digest


@pytest.mark.parametrize('blocker',['stale inventory','mapping ambiguous','mixed-product scope','missing costs'])
def test_blocked_inventory_never_enables_growth_or_broad_pause(blocker):
    ev,b,s=example();ev['inventory']['recommendations'][1].update(action='pause',eligibility='advisory',blockers=[blocker])
    d=run(ev,b,s);grow=next(r for r in d.decisions if r.resource_id=='grow')
    assert grow.advice=='abstain' and grow.change is None
    assert blocker in grow.blockers and d.budget['allocation_withheld']


def test_supported_budget_changes_keep_exact_total_and_bounds_without_duplicate_owner():
    ev,b,s=example();d=run(ev,b,s)
    assert len(d.decisions)==2 and all(r.advice=='budget_comparison' for r in d.decisions)
    assert sum(r.change['after'] for r in d.decisions)==20000
    assert all(abs(r.change['after']-10000)<=1000 for r in d.decisions)


@pytest.mark.parametrize('control',['stopped','unresolved'])
def test_control_blocks_protection_growth_and_recovery(control):
    ev,b,s=example();s[control]=True
    ev['inventory']['recommendations'][1].update(action='pause',eligibility='eligible')
    d=run(ev,b,s)
    assert all(r.change is None and r.advice=='abstain' for r in d.decisions)
    assert d.budget['allocation_withheld']


def test_recovery_needs_durable_approved_pause_not_imported_claim():
    ev,b,s=example();b=allocate([resource('donor',1),resource('grow',1)],BudgetRequest(),{})
    ev['inventory']['recommendations'][1].update(action='recovery',eligibility='eligible')
    ev['inventory']['products'][1].update(risk='clear',recovery_stock_eligible=True)
    ev['ads']['resources'][1]['status']='paused'
    d=run(ev,b,s);grow=next(r for r in d.decisions if r.resource_id=='grow')
    assert grow.advice=='abstain' and any('durable approved pause' in v for v in grow.blockers)


def test_throttle_amount_unspecified_no_invented_exact_change():
    ev,b,s=example();ev['inventory']['recommendations'][1].update(action='throttle',eligibility='eligible')
    d=run(ev,b,s);grow=next(r for r in d.decisions if r.resource_id=='grow')
    assert grow.advice=='throttle_review' and grow.change is None
    assert d.budget['allocation_withheld']


@pytest.mark.parametrize('change',['pin','revision','clock','switch','advice'])
def test_stale_pending_proposals_invalidated_without_rewriting_audit(change):
    ev,b,s=example();d=run(ev,b,s);c=deepcopy(d.decisions[0].change)
    c['before']=dict(value=10000,revision=0,last_request=None);s['resources'][c['key']]=deepcopy(c['before'])
    p=dict(id='plan',status='approved',expires_at=ev['at']+timedelta(minutes=30),plan=dict(evidence=deepcopy(ev['pins']),clock_valid_until=(ev['at']+timedelta(seconds=900)).isoformat(),changes=[c]))
    original=deepcopy(p)
    assert proposal_validity(p,ev['pins'],s,d.decisions,ev['at'])['validity']=='requires_phase8_revalidation'
    if change=='pin':ev['pins']['ads']='changed'
    if change=='revision':s['resources'][c['key']]['revision']=2
    if change=='clock':ev['at']+=timedelta(seconds=900)
    if change=='switch':s['stopped']=True
    if change=='advice':d.decisions=[]
    assert proposal_validity(p,ev['pins'],s,d.decisions,ev['at'])['validity']=='invalidated'
    assert p==original


def test_diagnostic_review_overrides_creative_and_unsafe_destination_blocks_pause():
    ev,b,s=example();ev['diagnostics']['recommendations'][1].update(blockers=['destination/price review required'],suggestions=[{'text':'untrusted <script>'}])
    d=run(ev,b,s);assert next(r for r in d.decisions if r.resource_id=='grow').advice=='diagnostic_review'
    ev['inventory']['recommendations'][1].update(action='pause',eligibility='eligible')
    d=run(ev,b,s);r=next(r for r in d.decisions if r.resource_id=='grow')
    assert r.advice=='abstain' and r.change is None and r.suppressed


def test_api_auth_origin_strict_terms_and_no_analytics_fallback(monkeypatch):
    client=TestClient(create_app(SETTINGS,MemoryStore(),object()))
    for path in ('decisions','decisions/history'):assert client.get('/api/'+path).status_code==401
    sign_in(client)
    assert client.post('/api/decisions/track',json={}).status_code==403
    assert client.post('/api/decisions/track',json={'digest':'x','key':'a'},headers=HEADERS).status_code==422
    assert client.post('/api/decisions/track',json={'digest':'a'*64,'key':'a','approve':True},headers=HEADERS).status_code==422


@pytest.mark.parametrize('status',['succeeded','partially_succeeded','failed','unknown','approved'])
def test_outcomes_are_explicit_linked_readback_no_financial_benefit(status):
    svc=DecisionService(None,None,None)
    svc.records=lambda:[dict(digest='a'*64,resource_key='r',action_id='plan',snapshot={},recorded_at=datetime.now(timezone.utc))]
    class Executor:
        def get(self,pid):return dict(status=status,steps=[dict(outcome='unknown')])
    svc.executor=Executor()
    result=svc.history()['observations'][0]
    assert result['outcome']==status and result['financial_outcome_paise'] is None
    svc.records=lambda:[dict(digest='a'*64,resource_key='r',action_id=None,snapshot={},recorded_at=datetime.now(timezone.utc))]
    assert svc.history()['observations'][0]['outcome']=='not_observed'


def test_tracking_rejects_stale_digest_unknown_resource_and_past_actions(monkeypatch):
    from advergent.decisions import DecisionSnapshot
    ev,b,s=example();d=run(ev,b,s);snapshot=DecisionSnapshot(status='available',data=d,pins=ev['pins'])
    svc=DecisionService(None,None,None);svc.query=lambda:snapshot;svc.records=lambda:[]
    with pytest.raises(ExecutionBlocked):svc._track(TrackDecision(digest='a'*64,key=d.decisions[0].key))
    with pytest.raises(ExecutionBlocked):svc._track(TrackDecision(digest=d.digest,key='unknown'))
    with pytest.raises(ExecutionBlocked):svc._track(TrackDecision.model_validate_json(canonical(dict(digest=d.digest,key=d.decisions[0].key,action_id=str(uuid4())))))


@pytest.mark.parametrize('transition',['none','pin','state','ledger','clock','failure','missing','incoherent'])
def test_query_coherence_races_clock_and_analytics_failure(transition):
    from types import SimpleNamespace
    ev,b,state=example();store=MemoryStore();plans=[]
    pubs={k:dict(id=k,observed_at=ev['at'],configuration={'resource_states':ev['stock_states']}) for k in ev['pins']}
    for k in pubs:setattr(store,('ad' if k=='ads' else k)+'_publication',lambda key=k:(pubs[key],None))
    store.budget_state=lambda:deepcopy(state)
    if transition=='missing':pubs['ads']=None
    if transition=='incoherent':pubs['inventory']['finance_id']='changed'
    class Analytics:
        def budget_data(self,*args):
            if transition=='failure':raise AnalyticsUnavailable('private error')
            return b
        def ad_data(self,*args):return ev['ads']
        def inventory_data(self,*args,**kwargs):return ev['inventory']
        def diagnostics_data(self,*args,**kwargs):return ev['diagnostics']
        def attribution_data(self,*args):return {'mapping_evidence':[m.model_dump(mode='json') for m in ev['mappings']]}
        def breakout_data(self,*args):return SimpleNamespace(model_dump=lambda **kwargs:{})
        def clearance_data(self,*args):
            if transition=='pin':pubs['ads']['id']='changed'
            if transition=='state':state['control_version']='changed'
            if transition=='ledger':plans.append(dict(status='failed'))
            if transition=='clock':b.valid_until=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            return SimpleNamespace(model_dump=lambda **kwargs:{})
    svc=DecisionService(store,Analytics(),None);svc.plans=lambda:deepcopy(plans);svc.records=lambda:[]
    result=svc.query()
    expected={'none':'available','failure':'analytics_unavailable','missing':'not_loaded'}.get(transition,'inputs_changed')
    assert result.status==expected
    if transition!='none':assert result.data is None and result.queried_at is None and 'private error' not in str(result)


def test_meta_distinct_budget_id_collapses_into_actual_owner():
    ev,b,s=example();b.rows[0].budget_id='distinct-budget-id'
    d=run(ev,b,s)
    assert len(d.decisions)==2 and len({r.key for r in d.decisions})==2
    owner=next(r for r in d.decisions if r.resource_id=='donor')
    assert owner.evidence['budget']['budget_id']=='distinct-budget-id'


def test_shared_budget_member_protection_never_emits_unmatched_transfer():
    ev,b,s=example()
    for r in ev['ads']['resources']:r['platform']='google'
    for group in ('inventory','diagnostics'):
        for r in ev[group]['recommendations']:r['platform']='google'
    for r in b.rows:r.platform='google'
    b.rows[1].shared=True;b.rows[1].members=['grow','donor']
    ev['inventory']['recommendations'][0].update(action='advisory',blockers=['mixed-product scope'])
    d=run(ev,b,s)
    assert d.budget['allocation_withheld']
    assert all(r['allocated_paise']==r['current_paise'] for r in d.budget['allocations'])
    assert all(r.advice!='budget_comparison' for r in d.decisions)


@pytest.mark.parametrize('case',['exact','past','mismatch','other_leg','expired_proof','relink'])
def test_durable_tracking_exact_link_and_rejections(case):
    from types import SimpleNamespace
    from advergent.decisions import DecisionSnapshot
    ev,b,state=example();d=run(ev,b,state);row=d.decisions[0]
    snap=DecisionSnapshot(status='available',pins=ev['pins'],data=d)
    recorded=ev['at']-timedelta(seconds=2)
    record=dict(digest=d.digest,resource_key=row.key,snapshot=snap.model_dump(mode='json'),action_id=None,recorded_at=recorded)
    action=dict(id=str(uuid4()),created_at=ev['at']-timedelta(seconds=1),status='partially_succeeded',steps=[dict(outcome='succeeded',actual={'value':9000})],
        plan=dict(evidence=ev['pins'],changes=[deepcopy(r.change) for r in d.decisions]))
    if case=='past':action['created_at']=recorded-timedelta(seconds=1)
    if case=='mismatch':action['plan']['changes'][0]['after']+=1
    if case=='other_leg':action['plan']['changes'][1]['after']+=1
    if case=='expired_proof':record['snapshot']['data']['valid_until']=(action['created_at']-timedelta(seconds=1)).isoformat()
    if case=='relink':record['action_id']=str(uuid4())
    class Conn:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params):
            query=str(sql)
            if query.startswith('SELECT'):return SimpleNamespace(scalar=lambda:record['action_id'])
            if query.startswith('UPDATE'):record['action_id']=params['a']
    svc=DecisionService(SimpleNamespace(engine=SimpleNamespace(begin=lambda:Conn())),None,SimpleNamespace(get=lambda pid:action))
    svc.records=lambda:[record]
    request=TrackDecision(digest=d.digest,key=row.key,action_id=action['id'])
    if case=='exact':
        result=svc._track(request)['observations'][0]
        assert result['outcome']=='partially_succeeded' and result['action_steps']==action['steps']
        assert result['financial_outcome_paise'] is None
    else:
        with pytest.raises(ExecutionBlocked):svc._track(request)


def test_related_hierarchy_protection_suppresses_creative_and_future_source_abstains():
    ev,b,s=example()
    ev['ads']['resources'][1]['parent_id']='donor'
    ev['inventory']['recommendations'][0].update(action='advisory',blockers=['inventory uncertainty'])
    ev['diagnostics']['recommendations'][1]['suggestions']=[{'text':'Structured catalog facts'}]
    d=run(ev,b,s)
    grow=next(r for r in d.decisions if r.resource_id=='grow')
    assert grow.advice=='abstain' and any('related inventory' in v for v in grow.suppressed)
    ev['sources_not_future']=False
    d=run(ev,b,s)
    assert not any(r.change for r in d.decisions)


def test_durable_unchanged_approved_pause_can_support_recovery_review():
    ev,b,s=example();b=allocate([resource('donor',1),resource('grow',1)],BudgetRequest(),{})
    ev['inventory']['recommendations'][1].update(action='recovery',eligibility='eligible')
    ev['inventory']['products'][1].update(risk='clear',recovery_stock_eligible=True)
    ev['ads']['resources'][1]['status']='paused'
    key=canonical(['meta','synthetic','status','grow'])
    s['resources'][key]=dict(value='paused',revision=1,last_request='approved-pause')
    plan=dict(status='succeeded',approved_at=ev['at'],steps=[dict(resource_key=key,outcome='succeeded',request_id='approved-pause',intent=dict(after='paused',before={'revision':0}))])
    d=run(ev,b,s,[plan]);grow=next(r for r in d.decisions if r.resource_id=='grow')
    assert grow.advice=='recovery_review' and grow.change['after']=='active'
    s['resources'][key]['revision']=3
    d=run(ev,b,s,[plan]);assert next(r for r in d.decisions if r.resource_id=='grow').change is None
