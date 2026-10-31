from datetime import datetime, timedelta, timezone
from fractions import Fraction
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from advergent.api import create_app
from advergent.cohorts import evaluate
from advergent.contracts import AnalyticsUnavailable
from test_foundation import MemoryStore, SETTINGS, sign_in

START = datetime(2026, 5, 1, tzinfo=timezone.utc)


def inputs():
    def order(oid, customer, day):
        return dict(order_id=oid, customer_id=customer, delivered_at=(START+timedelta(days=day)).isoformat() if day is not None else None, campaign=[None,None,None])
    orders=[order('first','repeat',0),order('later','repeat',40),order('new','new',50),order('failed','none',None)]
    lines=[dict(order_id='first',product_id='p1',merchandise_paise=100),dict(order_id='first',product_id='p2',merchandise_paise=300),dict(order_id='new',product_id='p1',merchandise_paise=200)]
    def event(oid, customer, day, value):
        return dict(order_id=oid,customer_id=customer,at=(START+timedelta(days=day)).isoformat(),contribution_paise=value,estimated=False)
    events=[event('first','repeat',-1,-100),event('first','repeat',0,1000),event('later','repeat',40,500),event('first','repeat',60,-300),event('first','repeat',90,900000),event('new','new',50,200)]
    return orders,lines,events


def run(day=70, args=None):
    return evaluate(*(args or inputs()),START+timedelta(days=day),START.isoformat())


def test_a20_exact_weights_repeat_buyers_mature_partial_and_no_future_leakage():
    d=run();repeat=next(c for c in d.customers if c.customer_id=='repeat')
    assert repeat.weights=={'p1':'1/4','p2':'3/4'}
    assert sum(map(Fraction,repeat.weights.values()))==1
    assert repeat.windows[0].mature and not repeat.windows[1].mature
    assert repeat.windows[0].contribution_before_ads_paise==1400
    assert repeat.windows[0].product_contribution_paise=={'p1':350,'p2':1050}
    assert repeat.windows[1].contribution_before_ads_paise==1100
    assert len(d.customers)==2 and d.customers_without_delivery==1 and not d.history_complete
    assert all(not c.history_complete for c in d.customers)
    assert len({b.mature for b in d.buckets if b.days==60})==2
    # Arbitrarily huge post-window refunds/sales cannot alter the mature window.
    args=inputs();args[2][-2]['contribution_paise']=-9999999
    later=run(100,args).customers[-1]
    assert later.windows[0].contribution_before_ads_paise==1400
    assert later.windows[1].contribution_before_ads_paise==1100
    assert sum(b.known_customer_contribution_paise for b in d.buckets if b.days==60)==1600


@pytest.mark.parametrize('day,mature60,mature90',[(59,False,False),(60,True,False),(89,True,False),(90,True,True)])
def test_exact_maturity_and_exclusive_end(day,mature60,mature90):
    c=run(day).customers[-1]
    assert [w.mature for w in c.windows]==[mature60,mature90]
    if mature90: assert c.windows[1].contribution_before_ads_paise==1100


def test_missing_cost_is_unknown_with_covered_subtotal_and_future_unknown_does_not_leak():
    args=inputs();args[2][2]['contribution_paise']=None
    c=run(args=args).customers[-1]
    assert c.windows[0].contribution_before_ads_paise is None
    assert c.windows[0].covered_event_contribution_paise==900
    assert c.windows[0].missing_events==1
    assert all(v is None for v in c.windows[0].product_contribution_paise.values())
    assert all(b.contribution_before_ads_paise is None for b in run(args=args).buckets if b.mature)
    args=inputs();args[2][-2]['contribution_paise']=None
    assert run(100,args).customers[-1].windows[1].contribution_before_ads_paise==1100


def test_first_delivery_not_placement_future_delivery_ties_and_same_product_variants():
    args=inputs();args[0][0]['delivered_at']=(START+timedelta(days=45)).isoformat()
    args[1].append(dict(order_id='later',product_id='actual-first',merchandise_paise=500))
    c=run(args=args).customers[-1]
    assert c.first_order_id=='later' and c.weights=={'actual-first':'1'}
    args=inputs();args[0][1]['delivered_at']=START.isoformat()
    args[1].append(dict(order_id='first',product_id='p1',merchandise_paise=200))
    c=run(args=args).customers[-1]
    assert c.first_order_id=='first' and c.weights=={'p1':'1/2','p2':'1/2'}
    assert len(run(-1).customers)==0


def test_zero_merchandise_abstains_and_negative_paise_allocation_reconciles():
    args=inputs()
    for l in args[1]:l['merchandise_paise']=0
    assert run(args=args).zero_value_unassigned==2 and not run(args=args).customers
    args=inputs();args[2][1]['contribution_paise']=-401
    c=run(args=args).customers[-1]
    assert c.windows[0].contribution_before_ads_paise==-1
    assert sum(c.windows[0].product_contribution_paise.values())==-1


@pytest.mark.parametrize('correction_day',[60,61])
def test_correction_effective_after_window_unknown_and_refund_does_not_change_weights(correction_day):
    args=inputs();args[2][1]['correction_at']=(START+timedelta(days=correction_day)).isoformat()
    args[2][1]['estimated']=True
    c=run(args=args).customers[-1]
    assert c.windows[0].contribution_before_ads_paise is None
    assert c.windows[0].estimated_events==1
    assert c.windows[1].contribution_before_ads_paise==1100
    assert c.weights=={'p1':'1/4','p2':'3/4'}


def test_ist_month_and_pre_acquisition_expenses_not_repeated():
    args=inputs();args[0][0]['delivered_at']='2026-04-30T20:00:00+00:00'
    args[2].append(dict(order_id='old-failed',customer_id='repeat',at='2026-04-29T00:00:00Z',contribution_paise=-9999,estimated=False))
    c=run(args=args).customers[-1]
    assert c.acquisition_month=='2026-05' and c.windows[0].excluded_before_acquisition==1
    assert c.windows[0].contribution_before_ads_paise==1400


def test_partial_acquisition_month_keeps_mature_and_immature_customers_separate():
    args=inputs();args[0][2]['delivered_at']=(START+timedelta(days=20)).isoformat()
    args[2][-1]['at']=args[0][2]['delivered_at']
    d=run(args=args)
    may=[b for b in d.buckets if b.acquisition_month=='2026-05' and b.product_id=='p1' and b.days==60]
    assert {(b.mature,b.customer_weight,b.contribution_before_ads_paise) for b in may}=={(True,'1/4',350),(False,'1',200)}
    assert sum((Fraction(b.customer_weight) for b in may),Fraction())==Fraction(5,4)


def test_later_refund_and_recovery_keep_actual_dates_without_reserve_double_count():
    args=inputs()
    args[2].append(dict(order_id='first',customer_id='repeat',at=(START+timedelta(days=65)).isoformat(),contribution_paise=120,estimated=False))
    c=run(args=args).customers[-1]
    assert c.windows[0].contribution_before_ads_paise==1400
    assert c.windows[1].contribution_before_ads_paise==1220
    # Recovery not yet assessed cannot enter an earlier query.
    earlier=run(64,args).customers[-1]
    assert earlier.windows[1].contribution_before_ads_paise==1100
    assert c.weights==earlier.weights


def test_api_auth_source_cutoff_stale_history_pin_changes_and_sanitized_failure():
    pubs={k:dict(id=uuid4(),observed_at=START+timedelta(days=70)) for k in ('finance','commerce','ads','attribution')}
    pubs['finance'].update({k+'_id':pubs[k]['id'] for k in ('commerce','ads','attribution')})
    pubs['attribution'].update({k+'_id':pubs[k]['id'] for k in ('commerce','ads')})
    pubs['finance']['configuration']=dict(as_of=(START+timedelta(days=80)).isoformat(),period_start=START.isoformat())
    store=MemoryStore()
    for k in pubs:setattr(store,{'ads':'ad'}.get(k,k)+'_publication',lambda key=k:(pubs[key],None))
    class Analytics:
        fail=False
        change=False
        def cohort_data(self,pins,cutoff,history):
            if self.fail:raise AnalyticsUnavailable('private-secret')
            if self.change:pubs['commerce']=dict(id=uuid4(),observed_at=START)
            return evaluate(*inputs(),cutoff,history)
    a=Analytics();client=TestClient(create_app(SETTINGS,store,a))
    assert client.get('/api/cohorts').status_code==401
    sign_in(client)
    d=client.get('/api/cohorts').json()
    assert d['status']=='available' and d['data']['cutoff']==(START+timedelta(days=70)).isoformat()
    for stamp in ('2026-05-01','2026-10-31T00:00:00Z','2026-04-30T00:00:00Z'):
        assert client.get('/api/cohorts',params={'as_of':stamp}).status_code==422
    assert client.get('/api/cohorts',params={'as_of':START.isoformat()}).json()['data']['customers'][0]['windows'][0]['mature'] is False
    a.fail=True;d=client.get('/api/cohorts').json()
    assert d['status']=='analytics_unavailable' and d['data'] is None and d['queried_at'] is None
    assert 'private-secret' not in str(d)
    a.fail=False;a.change=True
    assert client.get('/api/cohorts').json()['status']=='inputs_changed'
    assert client.get('/api/cohorts').json()['data'] is None
    assert client.post('/api/cohorts',json={}).status_code in (403,405)
