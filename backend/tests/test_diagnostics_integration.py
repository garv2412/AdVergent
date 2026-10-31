import json,os,hashlib
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from uuid import uuid4,uuid5,NAMESPACE_URL
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.diagnostics import import_diagnostics
from advergent.diagnostics_fixture import build_fixture
from advergent.api import create_app

pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores only')


def test_diagnostics_real_a22_a24_failure_replay_corruption_and_pinning(tmp_path):
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s);store.migrate();a.migrate()
    inv=store.inventory_publication()[0];base=build_fixture();token='diagnostics-test-'+str(uuid4())
    def source(data,name):
        data=deepcopy(data);data['version']=name+'-'+str(uuid4());p=tmp_path/(name+'.json');raw=json.dumps(data).encode();p.write_bytes(raw)
        return p,str(uuid5(NAMESPACE_URL,'diagnostics-v1:'+hashlib.sha256(raw).hexdigest()+str(inv['id'])))
    def query(run):return a.diagnostics_data(run,at=datetime.fromisoformat(base['observed_at']))
    try:
        run=import_diagnostics(store,a);published=store.diagnostics_publication()[0];data=query(run)
        rs={r['resource_id']:r for r in data['recommendations']};assert set(rs)=={'m-ad','g-search-b-ad'}
        ds={d['url'].rsplit('/',1)[-1]:d for d in rs['m-ad']['destinations']}
        assert ds['transient']['status']=='uncertain_transient' and ds['repeated']['status']=='confirmed_not_found'
        assert ds['variant']['price_status']=='uncertain_variant' and ds['mismatch']['price_status']=='variant_price_mismatch'
        assert ds['expired']['price_status']=='expired_offer' and ds['archived']['status']=='archived_product'
        assert ds['bot']['status']=='uncertain_bot_block' and ds['redirect']['status']=='redirect_review'
        assert '<script>' in json.dumps(rs['m-ad']['catalog_evidence'])
        assert all(r['approval_required'] and r['advisory'] and not r['mutation_enabled'] for r in rs.values())
        assert rs['g-search-b-ad']['fatigue'][0]['status']=='possible_fatigue'
        assert len(data['variant_price_evidence'])==11 and len(data['ctr_evidence'])==4
        assert import_diagnostics(store,a)==run and store.diagnostics_publication()[0]['finished_at']==published['finished_at']
        # Actual SQL duplicate-key failure rolls back both observations and marker.
        bp,br=source(base,'sql-failure')
        class Broken(ExasolAnalytics):
            def load_diagnostics(self,run,iid,f):
                f.checks.append(f.checks[-1]);super().load_diagnostics(run,iid,f)
        with pytest.raises(RuntimeError,match='prior publication preserved'):import_diagnostics(store,Broken(s),bp)
        assert str(store.diagnostics_publication()[0]['id'])==run
        with a.connection() as conn:
            for table in ('DIAG_CHECKS','DIAG_WINDOWS','DIAG_COMPLETE'):
                assert conn.execute('SELECT COUNT(*) FROM ADVERGENT.'+table+' WHERE DATASET_ID={id}',dict(id=br)).fetchval()==0
        assert import_diagnostics(store,a,bp)==br
        op,orphan=source(base,'post-commit')
        class VerifyFailure(ExasolAnalytics):
            def verify_diagnostics(self,*args):raise RuntimeError('after analytical commit')
        with pytest.raises(RuntimeError):import_diagnostics(store,VerifyFailure(s),op)
        assert str(store.diagnostics_publication()[0]['id'])==br and query(orphan)['recommendations']
        assert import_diagnostics(store,a,op)==orphan
        client=TestClient(create_app(s,store,a));assert client.get('/api/diagnostics').status_code==401
        store.login(token);client.cookies.set('advergent_session',token,path='/api')
        snap=client.get('/api/diagnostics').json();assert snap['status']=='available' and snap['freshness']=='stale' and snap['dependencies_current']
        assert not any(r['suggestions'] for r in snap['data']['recommendations'])
        try:
            with a.connection() as conn:
                conn.execute('UPDATE ADVERGENT.DIAG_CHECKS SET PAGE_PRICE_PAISE=1 WHERE DATASET_ID={id} AND "ID"={check}',dict(id=orphan,check='healthy-1'));conn.commit()
            snap=client.get('/api/diagnostics').json();assert snap['status']=='analytics_unavailable' and snap['data'] is None and snap['queried_at'] is None
        finally:
            with a.connection() as conn:
                conn.execute('UPDATE ADVERGENT.DIAG_CHECKS SET PAGE_PRICE_PAISE=80000 WHERE DATASET_ID={id} AND "ID"={check}',dict(id=orphan,check='healthy-1'));conn.commit()
        # A fresh independent warehouse observation and coherent fresh diagnostics permit a grounded review suggestion.
        from advergent.inventory import import_inventory
        fresh=deepcopy(inv['configuration']);now=datetime.now(timezone.utc);stamp=now.isoformat();fresh['version']='diagnostics-inventory-'+str(uuid4());fresh['observed_at']=stamp
        for o in fresh['observations']:
            o['stock_observed_at']=stamp
            if int(o['variant_id'][1:])<6:o.update(available=100,eligible_units=28)
        for r in fresh['resource_states']:r['observed_at']=stamp
        ip=tmp_path/'inventory.json';ip.write_text(json.dumps(fresh));import_inventory(store,a,ip)
        assert not client.get('/api/diagnostics').json()['dependencies_current']
        assert not any(r['suggestions'] for r in client.get('/api/diagnostics').json()['data']['recommendations'])
        f=deepcopy(base);f['checks']=[c for c in f['checks'] if c['id'] in ('healthy-1','creative-destination')];delta=now-datetime.fromisoformat(base['observed_at']);f['observed_at']=stamp
        for c in f['checks']:
            c['observed_at']=(datetime.fromisoformat(c['observed_at'].replace('Z','+00:00'))+delta).isoformat()
        for w in f['windows']:
            for k in ('start','end'):w[k]=(datetime.fromisoformat(w[k].replace('Z','+00:00'))+delta).isoformat()
        fp,_=source(f,'fresh');fresh_run=import_diagnostics(store,a,fp)
        snap=client.get('/api/diagnostics').json();assert snap['freshness']=='fresh' and snap['dependencies_current']
        r=next(r for r in snap['data']['recommendations'] if r['resource_id']=='m-ad')
        assert len(r['suggestions'])==1 and r['suggestions'][0]['facts']['colors']==['indigo']
        assert r['approval_required'] and not r['mutation_enabled']
        assert not any(r['suggestions'] for r in a.diagnostics_data(fresh_run,dependencies_current=False)['recommendations'])
    finally:
        store.logout(token)
        with store.engine.begin() as conn:conn.execute(text('UPDATE inventory_publications SET run_id=:id WHERE singleton=1'),dict(id=inv['id']))
        import_diagnostics(store,a)


def test_real_same_product_variant_prices_do_not_create_global_mismatch(tmp_path):
    from advergent.commerce import import_commerce
    from advergent.attribution import import_attribution
    from advergent.finance import import_finance
    from advergent.inventory import import_inventory
    from advergent.operational import ROOT
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    try:
        commerce=json.loads((ROOT/'fixtures/commerce-v1.json').read_text());commerce['version']='diagnostic-variant-prices-'+str(uuid4())
        for r in commerce['snapshot']:
            if r['kind']=='variants' and r['id']=='v1':r['data']['price_paise']=85000
        for page in commerce['pages']:
            for d in page:
                r=d['record']
                if r['kind']=='variants' and r['id']=='v1':r['data']['price_paise']=85000
        path=tmp_path/'variant-commerce.json';path.write_text(json.dumps(commerce));import_commerce(store,a,path)
        import_attribution(store,a);import_finance(store,a);import_inventory(store,a)
        f=build_fixture();f['version']='same-product-variants-'+str(uuid4());healthy=next(c for c in f['checks'] if c['id']=='healthy-1')
        other=dict(healthy,id='selected-v1',variant_id='v1',page_variant_id='v1',page_price_paise=85000,advertised_price_paise=85000,url='https://fixture.invalid/selected-v1')
        f['checks']=[healthy,other];path=tmp_path/'variant-diagnostics.json';path.write_text(json.dumps(f));run=import_diagnostics(store,a,path)
        data=a.diagnostics_data(run,at=datetime.fromisoformat(f['observed_at']))
        ds=next(r for r in data['recommendations'] if r['resource_id']=='m-ad')['destinations']
        assert {d['variant_id']:d['catalog_price_paise'] for d in ds}=={'v0':80000,'v1':85000}
        assert all(d['product_id']=='p0' and d['price_status']=='match' for d in ds)
        assert {r['catalog_price_paise'] for r in data['variant_price_evidence']}=={80000,85000}
    finally:
        import_commerce(store,a);import_attribution(store,a);import_finance(store,a);import_inventory(store,a);import_diagnostics(store,a)
