import os
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.config import Settings
from advergent.api import create_app
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.contracts import AnalyticsUnavailable
from advergent.ads import import_ads
from advergent.attribution import import_attribution
from advergent.finance import import_finance
from advergent.inventory import import_inventory
from advergent.diagnostics import import_diagnostics
from advergent.operational import ROOT

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def context():
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    p=store.finance_publication()[0]
    pins=dict(finance=str(p['id']),**{k:str(p[k+'_id']) for k in ('commerce','ads','attribution')})
    cutoff=min(datetime.fromisoformat(p['configuration']['as_of']),p['observed_at'],
        store.commerce_publication()[0]['observed_at'],store.ad_publication()[0]['observed_at'],store.attribution_publication()[0]['observed_at'])
    return s,store,a,p,pins,cutoff


def test_real_a20_sql_fractional_assignments_maturity_event_reconciliation_and_corruption():
    s,store,a,p,pins,cutoff=context()
    def audit():
        with store.engine.connect() as c:
            return tuple(c.execute(text('SELECT COUNT(*) FROM '+t)).scalar() for t in ('action_plans','action_steps','action_events','simulated_receipts'))
    before=audit()
    d=a.cohort_data(pins,cutoff,p['configuration']['period_start'])
    assert d.customers and d.buckets and not d.history_complete
    assert {w.mature for c in d.customers for w in c.windows}=={False,True}
    assert any(len(c.weights)>1 for c in d.customers)
    assert any(w.missing_events for c in d.customers for w in c.windows)
    assert len({c.customer_id for c in d.customers})==len(d.customers)
    # Independent oracle from verified finance event payload and commerce identity.
    finance=a.finance_data(pins['finance'])
    os={r.id:r.data for r in a.commerce_records(pins['commerce'],'orders',limit=None)}
    original={r.id:r.data for r in a.commerce_records(pins['commerce'],'lines',limit=None)}
    variants={r.id:r.data for r in a.commerce_records(pins['commerce'],'variants',limit=None)}
    multi=missing=mature=immature=0
    for customer in d.customers:
        eligible=[line for line in finance['lines'] if os[line['order_id']]['customer_id']==customer.customer_id]
        delivered={(line['evidence']['order']['delivered_at'],line['order_id']) for line in eligible
                   if line['evidence']['order']['delivered_at'] and datetime.fromisoformat(line['evidence']['order']['delivered_at'])<=cutoff}
        earliest=min(delivered,key=lambda t:(datetime.fromisoformat(t[0]),t[1]))
        assert customer.first_order_id==earliest[1]
        start=datetime.fromisoformat(earliest[0]);values={}
        for lid,line in original.items():
            if line['order_id']==earliest[1]:
                pid=variants[line['variant_id']]['product_id']
                values[pid]=values.get(pid,0)+line['quantity']*line['unit_price_paise']-line['discount_paise']
        assert customer.weights=={pid:str(Fraction(value,sum(values.values()))) for pid,value in values.items() if value}
        assert sum(map(Fraction,customer.weights.values()))==1
        multi+=len(customer.weights)>1
        for w in customer.windows:
            end=start+timedelta(days=w.days)
            events=[e for l in eligible for e in l['events'] if datetime.fromisoformat(e['occurred_at'])<end
                    and datetime.fromisoformat(e['occurred_at'])<=cutoff
                    and (datetime.fromisoformat(e['occurred_at'])>=start or e['order_id']==earliest[1])]
            unknown=sum(e['net_product_cost_paise'] is None or e['variable_paise'] is None for e in events)
            subtotal=sum(e['net_sales_paise']-e['net_product_cost_paise']-e['variable_paise'] for e in events if e['net_product_cost_paise'] is not None and e['variable_paise'] is not None)
            assert w.events==len(events) and w.missing_events==unknown
            assert w.covered_event_contribution_paise==subtotal
            assert w.contribution_before_ads_paise==(None if unknown else subtotal)
            if not unknown: assert sum(w.product_contribution_paise.values())==subtotal
            missing+=unknown>0;mature+=w.mature;immature+=not w.mature
    assert all((multi,missing,mature,immature))
    for days in (60,90):
        assert sum(b.known_customer_contribution_paise for b in d.buckets if b.days==days)==sum(w.contribution_before_ads_paise or 0 for c in d.customers for w in c.windows if w.days==days)
        assert sum((Fraction(b.customer_weight) for b in d.buckets if b.days==days),Fraction())==len(d.customers)
    assert a.cohort_data(pins,cutoff,p['configuration']['period_start'])==d
    # Fully verified source/typed events must fail closed and restore exactly.
    line=finance['lines'][0];eid=line['events'][0]['id'];value=line['events'][0]['net_sales_paise']
    try:
        with a.connection() as c:
            c.execute('UPDATE ADVERGENT.FIN_EVENTS SET NET_SALES_PAISE=NET_SALES_PAISE+1 WHERE DATASET_ID={fid} AND EVENT_ID={eid}',dict(fid=pins['finance'],eid=eid));c.commit()
        with pytest.raises(AnalyticsUnavailable):a.cohort_data(pins,cutoff,p['configuration']['period_start'])
    finally:
        with a.connection() as c:
            c.execute('UPDATE ADVERGENT.FIN_EVENTS SET NET_SALES_PAISE={v} WHERE DATASET_ID={fid} AND EVENT_ID={eid}',dict(v=value,fid=pins['finance'],eid=eid));c.commit()
    assert a.cohort_data(pins,cutoff,p['configuration']['period_start'])==d
    assert audit()==before


def test_real_authenticated_asof_exclusive_boundary_changed_pins_and_restore():
    s,store,a,p,pins,cutoff=context()
    token='phase11-'+str(uuid4());store.login(token)
    client=TestClient(create_app(s,store,a))
    assert client.get('/api/cohorts').status_code==401
    client.cookies.set('advergent_session',token,path='/api')
    try:
        snap=client.get('/api/cohorts').json()
        assert snap['status']=='available' and snap['dependencies_current'] and snap['pins']==pins
        chosen=next(c for c in snap['data']['customers'] if c['windows'][0]['mature'])
        boundary=datetime.fromisoformat(chosen['windows'][0]['end'])
        before=client.get('/api/cohorts',params={'as_of':(boundary-timedelta(microseconds=1)).isoformat()}).json()
        exact=client.get('/api/cohorts',params={'as_of':boundary.isoformat()}).json()
        find=lambda d:next(c for c in d['data']['customers'] if c['customer_id']==chosen['customer_id'])['windows'][0]
        assert not find(before)['mature'] and find(exact)['mature']
        assert find(exact)['contribution_before_ads_paise']==chosen['windows'][0]['contribution_before_ads_paise']
        assert client.get('/api/cohorts',params={'as_of':(cutoff+timedelta(seconds=1)).isoformat()}).status_code==422
        import_ads(store,a,ROOT/'fixtures/ads-initial-v1.json')
        changed=client.get('/api/cohorts').json()
        assert changed['status']=='inputs_changed' and changed['data'] is None
    finally:
        store.logout(token)
        import_ads(store,a);import_attribution(store,a);import_finance(store,a);import_inventory(store,a);import_diagnostics(store,a)
    assert store.finance_publication()[0]['id']==p['id']
