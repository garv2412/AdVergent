from copy import deepcopy
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from itertools import product
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from advergent.api import create_app
from advergent.budget import BudgetRequest, baseline, allocate, observed_outcome
from advergent.contracts import AnalyticsUnavailable
from test_foundation import MemoryStore, SETTINGS, HEADERS, sign_in


def resource(key, slope, current=10000, blockers=()):
    observations = [dict(day=f'2026-01-{i*3+j+1:02}', spend_paise=x,
        contribution_paise=x*slope, orders=20, complete=True, mature=True)
        for i,x in enumerate((5000,10000,15000)) for j in range(3)]
    return dict(key=key, platform='meta', account_id='synthetic', budget_id=key, shared=False,
        members=[key],products=[key],current_paise=current,observations=observations,blockers=list(blockers))


def test_a21_attractive_stockout_inventory_precedence_fixed_total_and_exact_change():
    rows=[resource('donor',1),resource('clear',3),resource('stockout',100,blockers=['inventory p0: pause'])]
    d=allocate(rows,BudgetRequest(),{})
    by={r.key:r for r in d.rows}
    assert by['stockout'].allocated_paise==10000 and by['stockout'].response.lower_slope=='100'
    assert by['stockout'].minimum_paise==by['stockout'].maximum_paise==10000
    assert by['donor'].allocated_paise==9000 and by['clear'].allocated_paise==11000
    assert d.total_paise==d.allocated_total_paise==30000
    assert d.conservative_delta_paise==d.upper_delta_paise=='2000'
    assert not d.publishing_enabled and not d.mutation_enabled and d.approval_required
    assert d.portfolio_contribution_after_ads_paise is None


@pytest.mark.parametrize('field,value,reason',[
    ('complete',False,'coverage'),('mature',False,'immature'),('orders',19,'twenty'),
    ('contribution_paise',None,'missing'),('spend_paise',0,'nonpositive')])
def test_unsuitable_day_abstains_without_selective_dropping(field,value,reason):
    r=resource('a',2);r['observations'][0][field]=value
    b=baseline(r['observations'])
    assert b.status=='abstain' and any(reason in s for s in b.blockers)


def test_response_floors_slope_envelope_negative_and_no_extrapolation():
    obs=resource('a',2)['observations']
    assert baseline(obs[:6]).status=='abstain'
    assert baseline(obs[:-1]).status=='abstain'
    obs[0]['contribution_paise']+=1000
    b=baseline(obs)
    assert b.lower_slope=='9/5' and b.upper_slope=='2'
    obs[-1]['contribution_paise']=-100000
    assert baseline(obs).status=='abstain'
    r=resource('a',2,current=20000)
    d=allocate([r,resource('b',5)],BudgetRequest(),{})
    assert d.status=='abstain' and all(r.allocated_paise==r.current_paise for r in d.rows)


def test_order_outcomes_mature_exclusive_boundary_refund_recovery_and_missing_costs():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    events=[dict(at=(start+timedelta(days=day)).isoformat(),contribution_paise=value)
            for day,value in ((-1,-100),(1,1000),(30,-400),(59,100),(60,-9000),(70,7000))]
    assert observed_outcome(events,start,start+timedelta(days=59)) is None
    assert observed_outcome(events,start,start+timedelta(days=60))==600
    assert observed_outcome(events,start,start+timedelta(days=90))==600
    events[1]['correction_at']=(start+timedelta(days=60)).isoformat()
    assert observed_outcome(events,start,start+timedelta(days=90)) is None
    del events[1]['correction_at'];events[1]['contribution_paise']=None
    assert observed_outcome(events,start,start+timedelta(days=90)) is None


def test_daily_gaps_duplicates_and_complete_envelope_abstain():
    obs=resource('a',2)['observations']
    obs[1]['day']=obs[0]['day']
    assert 'noncontiguous or duplicate daily observations' in baseline(obs).blockers
    obs=resource('a',2)['observations'];obs[-1]['day']='2026-01-10'
    assert baseline(obs).status=='abstain'


def test_uncertain_envelopes_overlap_no_reallocation_and_unknown_totals():
    rows=[resource('a',2),resource('b',2)]
    rows[0]['observations'][0]['contribution_paise']+=100
    d=allocate(rows,BudgetRequest(),{'history_complete':False})
    assert d.status=='abstain' and d.conservative_delta_paise is None
    assert d.portfolio_contribution_after_ads_paise is None and not d.cohort_context['history_complete']


@pytest.mark.parametrize('change',[0,1,333,1000])
def test_integer_bounds_zero_budget_shared_identity_and_fixed_total(change):
    rows=[resource('shared',1,current=10001),resource('recipient',5,current=10003)]
    rows[0].update(shared=True,members=['campaign-a','campaign-b'])
    d=allocate(rows,BudgetRequest(change_bps=change),{})
    assert d.total_paise==d.allocated_total_paise==20004
    for r in d.rows: assert abs(r.allocated_paise-r.current_paise)<=r.current_paise*change//10000
    wrong=allocate(rows,BudgetRequest(total_paise=20005),{})
    assert wrong.status=='infeasible' and all(r.allocated_paise==r.current_paise for r in wrong.rows)
    zero=allocate([resource('zero',2,current=0)],BudgetRequest(),{})
    assert zero.status=='abstain' and zero.total_paise==0


def test_allocator_matches_independent_exhaustive_small_integer_optimum():
    # Exhaustive feasible portfolios establish the objective and residual paise.
    for slopes in ((1,2,5),(3,3,3),(5,2,1),(1,5,3)):
        rows=[resource(str(i),s,current=20) for i,s in enumerate(slopes)]
        for r,s in zip(rows,slopes):
            r['observations']=[dict(day=f'2026-01-{i+1:02}',spend_paise=x,contribution_paise=x*s+(i%3),
                orders=20,complete=True,mature=True) for i,x in enumerate([10]*3+[20]*3+[30]*3)]
        d=allocate(rows,BudgetRequest(),{})
        bs=[baseline(r['observations']) for r in rows]
        def objective(deltas):
            return sum(Fraction(b.lower_slope if delta>0 else b.upper_slope)*delta for b,delta in zip(bs,deltas))
        optimal=max(objective(ds) for ds in product(range(-2,3),repeat=3) if sum(ds)==0)
        result=objective([r.allocated_paise-r.current_paise for r in d.rows])
        assert result==optimal
    blocked=allocate(rows,BudgetRequest(),{},['kill switch enabled'])
    assert blocked.status=='abstain'


@pytest.mark.parametrize('terms',[{'change_bps':1001},{'change_bps':True},{'change_bps':1.5},{'total_paise':'100'},{'total_paise':-1},{'curve':[]}])
def test_strict_terms(terms):
    with pytest.raises(ValidationError): BudgetRequest(**terms)


def test_api_auth_origin_terms_failure_pin_state_and_clock_changes():
    now=datetime.now(timezone.utc)
    pubs={k:dict(id=uuid4(),observed_at=now) for k in ('inventory','finance','commerce','ads','attribution','diagnostics')}
    pubs['inventory'].update({k+'_id':pubs[k]['id'] for k in ('finance','commerce','ads','attribution')})
    store=MemoryStore();state=dict(resources={},stopped=False,unresolved=0)
    for k in pubs:setattr(store,{'ads':'ad'}.get(k,k)+'_publication',lambda key=k:(pubs[key],None))
    store.budget_state=lambda:deepcopy(state)
    class Analytics:
        fail=False
        change=None
        def budget_data(self,pins,at,terms,publications,operational):
            if self.fail: raise AnalyticsUnavailable('private secret')
            d=allocate([resource('a',1),resource('b',3)],terms,{})
            if self.change=='pin':pubs['ads']['id']=uuid4()
            if self.change=='state':state['resources']['changed']={}
            if self.change=='clock':d.valid_until=(now-timedelta(seconds=1)).isoformat()
            return d
    a=Analytics();client=TestClient(create_app(SETTINGS,store,a))
    assert client.get('/api/budget').status_code==401
    sign_in(client)
    assert client.post('/api/budget/scenario',json={}).status_code==403
    assert client.post('/api/budget/scenario',json={'change_bps':1001},headers=HEADERS).status_code==422
    d=client.get('/api/budget').json()
    assert d['status']=='available' and len(d['pins'])==6 and d['data']['status']=='scenario'
    assert client.post('/api/budget/scenario',json={'total_paise':1},headers=HEADERS).json()['data']['status']=='infeasible'
    a.fail=True;d=client.get('/api/budget').json()
    assert d['status']=='analytics_unavailable' and d['data'] is None and d['queried_at'] is None and 'secret' not in str(d)
    a.fail=False
    for change in ('state','clock','pin'):
        a.change=change
        d=client.get('/api/budget').json()
        assert d['status']=='inputs_changed' and d['data'] is None and d['queried_at'] is None
