import json
import os
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
from uuid import uuid4,uuid5,NAMESPACE_URL
import hashlib
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from advergent.config import Settings
from advergent.operational import OperationalStore,ROOT
from advergent.exasol import ExasolAnalytics
from advergent.inventory import import_inventory
from advergent.inventory_fixture import build_fixture
from advergent.api import create_app

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def test_inventory_real_exasol_a09_a11_recovery_pinning_and_failure(tmp_path):
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    store.migrate();a.migrate();original=store.inventory_publication()[0];finance=store.finance_publication()[0]
    token='inventory-test-'+str(uuid4());base=build_fixture()
    def source(data,name):
        data=deepcopy(data);data['version']=name+'-'+str(uuid4());p=tmp_path/(name+'.json');raw=json.dumps(data).encode();p.write_bytes(raw)
        run=str(uuid5(NAMESPACE_URL,'inventory-v1:'+hashlib.sha256(raw).hexdigest()+str(finance['id'])))
        return p,run
    def query(run):return a.inventory_data(run,at=datetime.fromisoformat(base['as_of'].replace('Z','+00:00')))
    try:
        run=import_inventory(store,a);pub=store.inventory_publication()[0];data=query(run)
        ps={r['product_id']:r for r in data['products']};v=next(r for r in ps['p1']['variants'] if r['variant_id']=='v6')
        assert len(data['products'])==30 and data['variants']==180 and data['reconciled']
        assert v['sellable_units']==40 and Decimal(v['daily_velocity'])==10 and Decimal(v['days_of_cover'])==4
        assert ps['p1']['throttle_eligible'] and Decimal(ps['p0']['unavailable_weight_bps'])==6000 and ps['p0']['pause_eligible']
        for pid in ('p2','p3','p4'):assert ps[pid]['days_of_cover'] is None and not ps[pid]['recovery_stock_eligible']
        assert ps['p5']['lead_days'] is None and ps['p5']['uncertain']
        rs={r['resource_id']:r for r in data['recommendations']}
        assert rs['m-ad']['action']=='pause' and rs['m-ad']['eligibility']=='eligible'
        assert rs['m-ad']['impact']['expected_contribution_paise'] is None and rs['m-ad']['impact']['missing_lines']>0
        assert rs['g-assets']['eligibility']=='advisory' and any('mixed-product' in b for b in rs['g-assets']['blockers'])
        assert rs['g-shopping-group']['mapping']['status']=='ambiguous'
        assert import_inventory(store,a)==run
        replay=store.inventory_publication()[0]
        assert replay['observed_at']==pub['observed_at'] and replay['finished_at']==pub['finished_at']
        # Available excludes committed; reserve alone changes exact SQL stock and cover.
        changed=deepcopy(base);o=next(r for r in changed['observations'] if r['variant_id']=='v6');o.update(committed=999,merchant_reserve=5)
        next(r for r in changed['observations'] if r['variant_id']=='v7')['merchant_reserve']=999
        path,changed_run=source(changed,'stock-arithmetic');assert import_inventory(store,a,path)==changed_run
        cv=next(r for r in query(changed_run)['products'] if r['product_id']=='p1')['variants']
        cv=next(r for r in cv if r['variant_id']=='v6');assert cv['sellable_units']==35 and Decimal(cv['days_of_cover'])==Decimal('3.5')
        assert next(v for r in query(changed_run)['products'] if r['product_id']=='p1' for v in r['variants'] if v['variant_id']=='v7')['sellable_units']==0
        old_v7=next(r for r in base['observations'] if r['variant_id']=='v7')['available']
        assert query(run)['sellable_units']-query(changed_run)['sellable_units']==5+old_v7
        # Confirmed receipt at day 3 bridges four-day stockout; late/unknown evidence does not.
        receipts=deepcopy(base);receipts['receipts'][0].update(expected_at='2026-11-02T10:00:00Z',quantity=200)
        rp,rr=source(receipts,'timely-receipt');import_inventory(store,a,rp)
        rv=next(r for r in query(rr)['products'] if r['product_id']=='p1')['variants']
        assert next(v for v in rv if v['variant_id']=='v6')['replenishment_sufficient']
        mixed_data=query(rr);mp={p['product_id']:p for p in mixed_data['products']}
        assert mp['p0']['pause_eligible'] and not mp['p1']['pause_eligible'] and not mp['p1']['throttle_eligible']
        mixed_rec=next(r for r in mixed_data['recommendations'] if r['resource_id']=='g-assets')
        assert mixed_rec['eligibility']=='advisory' and any('mixed-product' in b for b in mixed_rec['blockers'])
        # Actual SQL primary key failure rolls back observations and completion marker.
        bad_path,bad_run=source(base,'sql-failure')
        class Broken(ExasolAnalytics):
            def load_inventory(self,run,fid,f):
                f.observations.append(f.observations[-1]);super().load_inventory(run,fid,f)
        with pytest.raises(RuntimeError,match='prior publication preserved'):import_inventory(store,Broken(s),bad_path)
        assert str(store.inventory_publication()[0]['id'])==rr
        with a.connection() as conn:
            for table in ('INV_OBSERVATIONS','INV_COMPLETE'):
                assert conn.execute(f'SELECT COUNT(*) FROM ADVERGENT.{table} WHERE DATASET_ID={{id}}',dict(id=bad_run)).fetchval()==0
        assert import_inventory(store,a,bad_path)==bad_run
        # A committed analytical orphan is verified/reused after a publication failure.
        orphan_path,orphan=source(base,'post-commit')
        class VerifyFailure(ExasolAnalytics):
            def verify_inventory(self,*args):raise RuntimeError('After commit')
        with pytest.raises(RuntimeError):import_inventory(store,VerifyFailure(s),orphan_path)
        assert str(store.inventory_publication()[0]['id'])==bad_run and query(orphan)['reconciled']
        assert import_inventory(store,a,orphan_path)==orphan
        client=TestClient(create_app(s,store,a));assert client.get('/api/inventory').status_code==401
        store.login(token);client.cookies.set('advergent_session',token,path='/api')
        response=client.get('/api/inventory').json()
        assert response['status']=='available' and response['freshness']=='stale' and response['dependencies_current']
        assert all(r['eligibility']!='eligible' for r in response['data']['recommendations'])
        # Real typed corruption fails closed; exact source value is restored.
        try:
            with a.connection() as conn:
                conn.execute('UPDATE ADVERGENT.INV_OBSERVATIONS SET AVAILABLE=1 WHERE DATASET_ID={id} AND VARIANT_ID={vid}',dict(id=orphan,vid='v6'));conn.commit()
            response=client.get('/api/inventory').json()
            assert response['status']=='analytics_unavailable' and response['data'] is None and response['queried_at'] is None
        finally:
            with a.connection() as conn:
                conn.execute('UPDATE ADVERGENT.INV_OBSERVATIONS SET AVAILABLE=40 WHERE DATASET_ID={id} AND VARIANT_ID={vid}',dict(id=orphan,vid='v6'));conn.commit()
        # Fresh, explicit simulated observations permit recovery only after system pause.
        recover=deepcopy(base);now=datetime.now(timezone.utc).isoformat();recover['observed_at']=now
        for o in recover['observations']:
            o['stock_observed_at']=now
            if int(o['variant_id'][1:])<6:o.update(available=40,eligible_units=28)
        for state in recover['resource_states']:
            state['observed_at']=now
            if state['resource_id']=='m-ad':state.update(status='paused',paused_by='AdVergent',pause_evidence_id='simulated-prior-approved-pause-1')
        rec_path,rec_run=source(recover,'recovery');import_inventory(store,a,rec_path)
        response=client.get('/api/inventory').json();rec=next(r for r in response['data']['recommendations'] if r['resource_id']=='m-ad')
        assert response['freshness']=='fresh' and rec['action']=='recovery' and rec['eligibility']=='eligible' and rec['approval_required']
        recover['resource_states'][2]['paused_by']='merchant'
        merchant_path,_=source(recover,'merchant-pause');import_inventory(store,a,merchant_path)
        rec=next(r for r in client.get('/api/inventory').json()['data']['recommendations'] if r['resource_id']=='m-ad')
        assert rec['eligibility']=='advisory' and 'no prior AdVergent pause evidence' in rec['blockers']
        # Changed pinned finance stays historical, blocks eligibility and blocks a new import.
        from advergent.finance import import_finance
        fc=deepcopy(finance['configuration']);fc['version']='inventory-pin-'+str(uuid4());fp=tmp_path/'finance.json';fp.write_text(json.dumps(fc))
        import_finance(store,a,fp)
        assert not client.get('/api/inventory').json()['dependencies_current']
        assert all(r['eligibility']!='eligible' for r in client.get('/api/inventory').json()['data']['recommendations'])
        # Current finance itself remains coherent; a new inventory version pins it separately.
        assert import_inventory(store,a)!=run
        with store.engine.begin() as conn:conn.execute(text('UPDATE finance_publications SET run_id=:id WHERE singleton=1'),dict(id=finance['id']))
    finally:
        store.logout(token)
        with store.engine.begin() as conn:
            conn.execute(text('UPDATE finance_publications SET run_id=:id WHERE singleton=1'),dict(id=finance['id']))
        import_inventory(store,a)
