import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.api import create_app
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.breakout import FunnelSource
from advergent.breakout_fixture import fixture
from advergent.contracts import AnalyticsUnavailable
from advergent.inventory import import_inventory
from advergent.ads import import_ads
from advergent.diagnostics import import_diagnostics

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def test_real_breakout_dedup_boundaries_purchases_corruption_api_and_preservation(tmp_path):
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    p=store.inventory_publication()[0]
    pins=dict(inventory=str(p['id']),**{k:str(p[k+'_id']) for k in ('finance','commerce','ads','attribution')})
    def audit():
        with store.engine.connect() as c:
            return tuple(c.execute(text('SELECT COUNT(*) FROM '+t)).scalar() for t in
                         ('action_plans','action_steps','action_events','simulated_receipts'))
    before=audit();now=datetime.now(timezone.utc)
    d=a.breakout_data(pins,now,True)
    sparse=next(r for r in d.ranking if r.product_id=='p0')
    assert sparse.counts['signal']['click']==2 and sparse.rank is None and sparse.score is None
    assert 'sparse funnel evidence' in sparse.blockers and d.duplicate_events==1
    assert len(d.ranking)==30 and not any(r.rank for r in d.ranking)
    assert d.added_revenue_paise==0 and not d.publishing_enabled and not d.mutation_enabled
    assert next(r for r in d.ranking if r.product_id=='p1').counts['signal']['view']==200
    assert a.breakout_data(pins,now,True)==d  # immutable replay including retained duplicate evidence
    # Typed tampering must never become current ranking; restore original analytical value.
    try:
        with a.connection() as c:
            c.execute("UPDATE ADVERGENT.BR_EVENTS SET KIND='cart' WHERE SOURCE_HASH={h} AND EVENT_ID='p1-signal-view-0'",dict(h=d.source_hash));c.commit()
        with pytest.raises(AnalyticsUnavailable):a.breakout_data(pins,now,True)
    finally:
        with a.connection() as c:
            c.execute("UPDATE ADVERGENT.BR_EVENTS SET KIND='view' WHERE SOURCE_HASH={h} AND EVENT_ID='p1-signal-view-0'",dict(h=d.source_hash));c.commit()
    raw=fixture()
    # Existing product/order references, including repeated purchase callbacks under different event IDs.
    with a.connection() as c:
        oid,pid,placed=c.execute('''SELECT l.ORDER_ID,v.PRODUCT_ID,o.PLACED_AT FROM ADVERGENT.COMMERCE_LINES l
            JOIN ADVERGENT.COMMERCE_VARIANTS v ON v.DATASET_ID=l.DATASET_ID AND v.SOURCE_ID=l.VARIANT_ID
            JOIN ADVERGENT.COMMERCE_ORDERS o ON o.DATASET_ID=l.DATASET_ID AND o.SOURCE_ID=l.ORDER_ID
            WHERE l.DATASET_ID={id} ORDER BY o.PLACED_AT LIMIT 1''',dict(id=pins['commerce'])).fetchone()
    stamp=raw['signal_end']
    for i in range(2):raw['events'].append(dict(id='callback-'+str(i),product_id=pid,kind='purchase',at=stamp,order_id=oid))
    src=FunnelSource.model_validate(raw)
    linked=a.breakout_data(pins,now,True,src)
    assert linked.linked_purchase_pairs==1 and linked.added_revenue_paise==0
    assert next(r for r in linked.ranking if r.product_id==pid).counts['evaluation']['purchase']==1
    # An exact signal-end event belongs only to the later window, and future holdout is hidden at cutoff.
    cutoff=src.signal_end
    earlier=a.breakout_data(pins,cutoff,True,src)
    assert all(r.counts['evaluation']['view']==0 and r.counts['evaluation']['purchase']==0 for r in earlier.ranking)
    assert all(r.evaluation=='pending' for r in earlier.ranking)
    bad=src.model_dump(mode='json');bad['events'][-1]['order_id']='missing'
    with pytest.raises(AnalyticsUnavailable):a.breakout_data(pins,now,True,FunnelSource.model_validate(bad))
    token='phase10-'+str(uuid4());store.login(token);client=TestClient(create_app(s,store,a))
    try:
        assert client.get('/api/breakout').status_code==401
        client.cookies.set('advergent_session',token,path='/api')
        response=client.get('/api/breakout').json()
        assert response['status']=='available' and response['dependencies_current']
        assert response['data']['source_hash']==d.source_hash and response['pins']==pins
    finally:store.logout(token)
    assert audit()==before


def test_real_fresh_positive_ranking_changed_pins_and_restore(tmp_path):
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    p=store.inventory_publication()[0];config=p['configuration']
    now=datetime.now(timezone.utc);stamp=now.isoformat()
    config['version']='phase10-fresh-'+str(uuid4());config['observed_at']=stamp
    for r in config['observations']:
        r.update(stock_observed_at=stamp,available=10000,merchant_reserve=0,eligible_units=280,in_stock_seconds=28*86400)
    for r in config['resource_states']:r['observed_at']=stamp
    path=tmp_path/'fresh.json';path.write_text(json.dumps(config))
    raw=fixture();shift=now-datetime.fromisoformat(raw['signal_end'])
    raw['signal_end']=stamp;raw['observed_at']=stamp;raw['version']='phase10-fresh-source'
    for e in raw['events']:e['at']=(datetime.fromisoformat(e['at'])+shift).isoformat()
    raw['events']=[e for e in raw['events'] if datetime.fromisoformat(e['at'])<now]
    src=FunnelSource.model_validate(raw)
    try:
        import_inventory(store,a,path)
        p=store.inventory_publication()[0]
        pins=dict(inventory=str(p['id']),**{k:str(p[k+'_id']) for k in ('finance','commerce','ads','attribution')})
        d=a.breakout_data(pins,now,True,src)
        positive=[r for r in d.ranking if r.rank is not None]
        assert positive and all(r.inventory_risk=='clear' and r.score>0 for r in positive)
        assert all(r.evaluation=='pending' for r in positive)
        assert next(r for r in d.ranking if r.product_id=='p0').rank is None
        from advergent.operational import ROOT
        import_ads(store,a,ROOT/'fixtures/ads-initial-v1.json')
        blocked=a.breakout_data(pins,now,False,src)
        assert all(r.rank is None and 'pinned dependencies changed' in r.blockers for r in blocked.ranking)
        token='phase10-pin-'+str(uuid4());store.login(token)
        try:
            client=TestClient(create_app(s,store,a));client.cookies.set('advergent_session',token,path='/api')
            response=client.get('/api/breakout').json()
            assert not response['dependencies_current'] and response['pins']==pins
            assert not any(r['rank'] for r in response['data']['ranking'])
        finally:store.logout(token)
    finally:
        import_ads(store,a);import_inventory(store,a);import_diagnostics(store,a)


def test_real_funnel_sql_failure_rolls_back_and_retry_reuses_verified_source():
    import hashlib
    from advergent.commerce import canonical
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    p=store.inventory_publication()[0]
    pins=dict(inventory=str(p['id']),**{k:str(p[k+'_id']) for k in ('finance','commerce','ads','attribution')})
    raw=fixture();raw['version']='phase10-rollback-'+str(uuid4())
    class BrokenDedup(FunnelSource):
        def unique_events(self):
            unique=super().unique_events()
            return unique+[unique[0]]  # Inject a genuine final-batch Exasol primary-key failure.
    broken=BrokenDedup.model_validate(raw)
    digest=hashlib.sha256(canonical(broken.model_dump(mode='json')).encode()).hexdigest()
    with pytest.raises(AnalyticsUnavailable):a.breakout_data(pins,datetime.now(timezone.utc),True,broken)
    with a.connection() as c:
        for table in ('BR_EVENTS','BR_SOURCES'):
            assert c.execute('SELECT COUNT(*) FROM ADVERGENT.'+table+' WHERE SOURCE_HASH={h}',dict(h=digest)).fetchval()==0
    src=FunnelSource.model_validate(raw)
    good=a.breakout_data(pins,datetime.now(timezone.utc),True,src)
    assert good.source_hash==digest and good.duplicate_events==1
    assert a.breakout_data(pins,datetime.now(timezone.utc),True,src).source_hash==digest
