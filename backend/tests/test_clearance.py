from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from advergent.clearance import ClearanceRequest, evaluate
from advergent.contracts import AnalyticsUnavailable
from advergent.api import create_app
from test_foundation import SETTINGS, HEADERS, MemoryStore, sign_in


def row(**changes):
    return dict(variant_id='v6',product_id='p1',sellable_units=40,price_paise=80000,
        unit_cost_paise=44000,cost_status='actual',stock_observed_at='2026-10-30T10:00:00Z',
        fresh=True,demand_status='sufficient',daily_velocity='1',**changes)


def test_a18_hand_calculated_revenue_gain_loses_contribution():
    d=evaluate([row()],ClearanceRequest())
    assert d.baseline.revenue_paise==80000
    assert d.baseline.expected_contribution_paise==19150
    assert d.scenario.revenue_paise==120000
    assert d.scenario.expected_contribution_paise==-50550
    assert d.revenue_delta_paise==40000 and d.contribution_delta_paise==-69700
    assert d.scenario.blockers==['contribution floor','margin floor']
    assert not d.feasible and not d.mutation_enabled and not d.publishing_enabled
    assert d.ranking[0].excess_units==10 and d.ranking[0].age_excess_score==1200


def test_bundle_stock_limit_never_clamps_or_adds_receipts():
    second=row();second.update(variant_id='v7',sellable_units=2)
    request=ClearanceRequest(components=[dict(variant_id='v6',units_per_bundle=2),dict(variant_id='v7',units_per_bundle=1)],
        scenario_bundles=3,markdown_bps=0)
    d=evaluate([row(),second],request)
    assert d.scenario.units==9 and d.scenario.revenue_paise==720000
    assert d.scenario.blockers==['stock limit: v7'] and not d.feasible
    assert d.baseline.units==3 and d.baseline.additional_spend_paise==0
    invalid_baseline=evaluate([row(),second],request.model_copy(update={'baseline_bundles':3,'scenario_bundles':1}))
    assert invalid_baseline.scenario.limits_pass and not invalid_baseline.feasible
    assert 'no-action baseline exceeds available stock' in invalid_baseline.evidence_blockers


@pytest.mark.parametrize('field',['unit_cost_paise','variable_paise_per_unit','return_loss_paise_per_unit','holding_paise_per_unit_day'])
def test_unknown_costs_propagate(field):
    r=row();args={}
    if field=='unit_cost_paise':r[field]=None;r['cost_status']='missing'
    else:args[field]=None
    d=evaluate([r],ClearanceRequest(**args))
    assert d.scenario.expected_contribution_paise is None and d.scenario.margin_bps is None
    assert d.contribution_delta_paise is None and 'incomplete cost coverage' in d.scenario.blockers
    assert d.scenario.cost_coverage_bps==(0 if field=='unit_cost_paise' else 10000)


def test_exact_margin_floor_rounding_spend_and_zero_revenue():
    r=row();r.update(price_paise=101,unit_cost_paise=50,sellable_units=10)
    args=dict(baseline_bundles=1,scenario_bundles=1,markdown_bps=3333,variable_paise_per_unit=0,
              return_loss_paise_per_unit=0,holding_paise_per_unit_day=0,min_margin_bps=2538)
    d=evaluate([r],ClearanceRequest(**args))
    assert d.scenario.revenue_paise==67 and d.scenario.expected_contribution_paise==17
    assert 'margin floor' in d.scenario.blockers  # 2537.31 bps
    assert evaluate([r],ClearanceRequest(**{**args,'min_margin_bps':2537})).scenario.limits_pass
    args.update(markdown_bps=0,min_margin_bps=0,additional_spend_paise=52)
    d=evaluate([r],ClearanceRequest(**args));assert d.scenario.expected_contribution_paise==-1
    assert d.scenario.blockers==['contribution floor','margin floor']
    args.update(markdown_bps=10000,additional_spend_paise=0)
    d=evaluate([r],ClearanceRequest(**args));assert d.scenario.margin_bps is None and not d.feasible


@pytest.mark.parametrize('status,rate',[('missing_exposure',None),('sparse','0.01'),('zero_observed_demand','0')])
def test_unknown_demand_not_promoted_to_deadstock(status,rate):
    r=row();r.update(demand_status=status,daily_velocity=rate)
    d=evaluate([r],ClearanceRequest());assert d.ranking[0].excess_units is None
    assert d.ranking[0].deadstock_candidate is None and not d.feasible


def test_age_threshold_sorting_and_evidence_fail_closed():
    r=row();r.update(fresh=False)
    second=row();second.update(variant_id='v7',sellable_units=100)
    d=evaluate([r,second],ClearanceRequest(assumed_stock_age_days=30),False)
    assert d.ranking[0].variant_id=='v7' and not d.ranking[0].deadstock_candidate
    assert d.evidence_blockers==['pinned dependencies changed','stale or future selected stock observations']
    with pytest.raises(ValueError,match='Unknown variant'):evaluate([r],ClearanceRequest(components=[dict(variant_id='<script>')]))


@pytest.mark.parametrize('bad',[dict(markdown_bps=10001),dict(markdown_bps=True),dict(additional_spend_paise=1.5),
    dict(min_contribution_paise=-1),dict(min_margin_bps=-1),dict(horizon_days=0),dict(publish=True),
    dict(components=[dict(variant_id='v6'),dict(variant_id='v6')]),dict(components=[])])
def test_invalid_terms_reject(bad):
    with pytest.raises(ValidationError):ClearanceRequest(**bad)


def test_authenticated_api_unavailable_changed_pins_and_no_actions():
    now=datetime.now(timezone.utc)
    ids={k:uuid4() for k in ('inventory','finance','commerce','ads','attribution')}
    pubs={k:dict(id=v,observed_at=now) for k,v in ids.items()}
    for k in ('finance','commerce','ads','attribution'):pubs['inventory'][k+'_id']=ids[k]
    class Store(MemoryStore):pass
    store=Store()
    for k in pubs:setattr(store,{'ads':'ad'}.get(k,k)+'_publication',lambda key=k:(pubs[key],None))
    class Analytics:
        unavailable=False
        change=False
        def clearance_data(self,i,f,c,request,at,current):
            assert (i,f,c)==tuple(str(ids[k]) for k in ('inventory','finance','commerce'))
            if self.unavailable:raise AnalyticsUnavailable('private secret')
            if self.change:pubs['commerce']=dict(id=uuid4(),observed_at=now)
            return evaluate([row()],request,current)
    a=Analytics();client=TestClient(create_app(SETTINGS,store,a))
    assert client.get('/api/clearance').status_code==401
    sign_in(client)
    assert client.post('/api/clearance/scenario',json={}).status_code==403
    d=client.get('/api/clearance').json();assert d['status']=='available' and d['dependencies_current']
    assert client.post('/api/clearance/scenario',json={'publish':True},headers=HEADERS).status_code==422
    a.change=True
    d=client.get('/api/clearance').json();assert not d['dependencies_current']
    assert 'publication changed during query' in d['data']['evidence_blockers']
    a.unavailable=True
    d=client.get('/api/clearance').json();assert d['data'] is None and d['queried_at'] is None
    assert d['pins']['commerce']==str(ids['commerce']) and 'private secret' not in str(d)
