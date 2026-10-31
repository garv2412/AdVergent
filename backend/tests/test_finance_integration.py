"""Phase 5 actual PostgreSQL/Exasol finance gate; no mocked analytical results."""
import hashlib
import json
import os
import secrets
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid4, uuid5
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.finance import import_finance
from advergent.finance_fixture import build_fixture
from advergent.api import create_app
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore, ROOT

pytestmark=[pytest.mark.integration,pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Dedicated real stores required')]


def test_real_finance_a01_a08_reconciliation_corrections_reserves_replay_and_failure(tmp_path):
    s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
    store.migrate();a.migrate()
    original=store.finance_publication()[0]
    original_ads=store.ad_publication()[0]
    tid=str(store.attribution_publication()[0]['id'])
    token=secrets.token_urlsafe(32)
    def source(data,label):
        data=deepcopy(data);data['version']=label+'-'+str(uuid4())
        path=tmp_path/(label+'.json');path.write_text(json.dumps(data))
        run=str(uuid5(NAMESPACE_URL,'finance-v3:'+hashlib.sha256(path.read_bytes()).hexdigest()+tid))
        return path,run
    try:
        base=build_fixture();path,run=source(base,'baseline')
        assert import_finance(store,a,path)==run
        first=store.finance_publication()[0]
        assert import_finance(store,a,path)==run
        assert store.finance_publication()[0]['finished_at']==first['finished_at']
        assert store.finance_publication()[0]['observed_at']==first['observed_at']
        data=a.finance_data(run);t=data['totals'];ls={r['line_id']:r for r in data['lines']}
        # Independent full-store financial golden values, never foundation totals.
        assert (t['orders'],t['lines'],t['placed_paise'],t['delivered_paise'],t['refunded_paise'],t['net_sales_paise'])==(3000,3600,369912000,158757000,10010000,148747000)
        assert t['spend_paise']==210022 and t['missing_lines']==54 and t['cost_coverage_bps']==9850
        assert t['contribution_before_ads_paise'] is None and t['contribution_after_ads_paise'] is None and t['poas'] is None
        assert t['covered_contribution_paise']==76063310
        assert (t['cash_paise'],t['unsettled_cod_paise'])==(256575000,44531500)
        assert ls['l1-0']['contribution_before_ads_paise']==41499 and ls['l1-0']['cash_paise']==84000
        assert ls['l18-0']['contribution_before_ads_paise']==-12001 and ls['l18-0']['net_sales_paise']==0 and ls['l18-0']['sold_cost_paise']==0
        assert ls['l0-0']['net_product_cost_paise'] is None and ls['l0-0']['cash_paise']==0 and ls['l0-0']['unsettled_cod_paise']>0
        assert sum(g['totals']['net_sales_paise'] for g in data['allocations'])==t['net_sales_paise']
        assert len(data['lines'])==len({r['line_id'] for r in data['lines']})==3600
        assert sum(g['totals']['orders'] for g in data['allocations'])==3000
        assert next(g for g in data['allocations'] if g['campaign_id'] is None)['totals']['orders']==2996
        assert a.attribution_data(tid)['platform_claims'][0]['order_id']=='o0'
        assert len(a.attribution_data(tid)['platform_claims'])==2
        assert ls['l0-0']['campaign_id']=='g-pmax'
        assert sum(d['net_sales_paise'] for d in data['transaction_days'])==sum(d['net_sales_paise'] for d in data['acquisition_days'])==t['net_sales_paise']
        assert next(d for d in data['transaction_days'] if d['day']=='2026-10-29')['net_sales_paise']<0
        changed=deepcopy(base)
        changed['corrections']=[dict(line_id='l0-0',unit_cost_paise=25000,effective_at='2026-05-01T00:00:00Z',source='explicit historical invoice',reason='correct purchase invoice',status='actual')]
        next(r for r in changed['recoveries'] if r['refund_id']=='r0')['recovered_value_paise']=20000
        # Old acquisition, recent delivery, partial actual return: only one of two units remains exposed.
        next(r for r in changed['orders'] if r['order_id']=='o0')['delivered_at']='2026-10-29T17:00:00Z'
        correction_path,correction_run=source(changed,'corrected')
        import_finance(store,a,correction_path)
        corrected=a.finance_data(correction_run);cl={r['line_id']:r for r in corrected['lines']}
        assert cl['l0-0']['contribution_before_ads_paise']==51999 and cl['l0-1']['contribution_before_ads_paise']==92000
        assert cl['l0-0']['sold_cost_paise']==50000 and cl['l0-0']['recovered_paise']==20000
        assert cl['l0-0']['reserve_paise']==6450 and cl['l0-0']['exposed_units']==1
        assert cl['l0-0']['evidence']['original_line']['unit_cost_paise'] is None
        assert cl['l1-0']==ls['l1-0']
        assert a.finance_data(run)['totals']==t  # Historical publication unchanged.
        # A fully covered fixture verifies complete totals and POAS through real SQL.
        complete=deepcopy(base)
        commerce={r.id:r.data for r in a.commerce_records(str(first['commerce_id']),'lines',limit=None)}
        complete['corrections']=[dict(line_id=k,unit_cost_paise=30000,effective_at=l['cost_effective_at'],source='explicit missing invoice',reason='supplied historical invoice',status='actual') for k,l in commerce.items() if l['unit_cost_paise'] is None]
        for r in complete['recoveries']:
            if r['recovered_value_paise'] is None:r['recovered_value_paise']=0
        cp,cr=source(complete,'complete');import_finance(store,a,cp);cd=a.finance_data(cr)
        assert cd['totals']['missing_lines']==0 and cd['totals']['cost_coverage_bps']==10000
        # Independent oracle from actual source: sales less historic cost plus explicit recovery, fees and loss.
        orders={r.id:r.data for r in a.commerce_records(str(first['commerce_id']),'orders',limit=None)}
        costs=sum((l['unit_cost_paise'] if l['unit_cost_paise'] is not None else 30000)*l['quantity'] for l in commerce.values() if orders[l['order_id']]['fulfillment_status']=='delivered')
        recovery=sum(r['recovered_value_paise'] for r in complete['recoveries'])
        fees=sum(o['forward_paise']+o['payment_fee_paise']+o['reverse_paise']+o['other_paise']+o['failed_loss_paise'] for o in complete['orders'])
        expected=148747000-costs+recovery-fees
        assert cd['totals']['contribution_before_ads_paise']==expected
        assert cd['totals']['contribution_after_ads_paise']==expected-210022
        assert cd['totals']['poas'] is not None
        assert sum(g['totals']['contribution_before_ads_paise'] for g in cd['allocations'])==expected
        # Genuine SQL duplicate key aborts the whole load, including event rows and marker.
        bad_path,bad_run=source(base,'sql-failure')
        class Broken(ExasolAnalytics):
            def load_finance(self,run,cid,aid,tid,rows):
                super().load_finance(run,cid,aid,tid,rows+[rows[-1]])
        with pytest.raises(RuntimeError,match='prior publication preserved'):import_finance(store,Broken(s),bad_path)
        assert str(store.finance_publication()[0]['id'])==cr
        with a.connection() as conn:
            for table in ('FIN_LINES','FIN_EVENTS','FIN_COMPLETE'):
                assert conn.execute(f'SELECT COUNT(*) FROM ADVERGENT.{table} WHERE DATASET_ID={{id}}',dict(id=bad_run)).fetchval()==0
        client=TestClient(create_app(s,store,a));assert client.get('/api/finance').status_code==401
        store.login(token);client.cookies.set('advergent_session',token,path='/api')
        response=client.get('/api/finance').json()
        assert response['status']=='available' and response['latest_import_status']=='failed' and response['data']['reconciled']
        assert response['dependencies_current'] and response['queried_at'] and response['freshness']=='stale'
        from advergent.ads import import_ads
        import_ads(store,a,ROOT/'fixtures/ads-initial-v1.json')
        response=client.get('/api/finance').json();assert not response['dependencies_current'] and response['data']['totals']==cd['totals']
        with pytest.raises(RuntimeError,match='inputs changed'):import_finance(store,a,path)
        with store.engine.begin() as conn:conn.execute(text('UPDATE ad_publications SET run_id=:id WHERE singleton=1'),dict(id=original_ads['id']))
        assert import_finance(store,a,bad_path)==bad_run
        orphan_path,orphan=source(base,'orphan')
        class VerifyFailure(ExasolAnalytics):
            def verify_finance(self,*args):raise RuntimeError('After actual commit')
        with pytest.raises(RuntimeError):import_finance(store,VerifyFailure(s),orphan_path)
        assert str(store.finance_publication()[0]['id'])==bad_run
        assert a.finance_data(orphan)['totals']==t
        assert import_finance(store,a,orphan_path)==orphan
        # Typed financial corruption fails closed; restore exact value afterward.
        with a.connection() as conn:
            conn.execute('UPDATE ADVERGENT.FIN_LINES SET DELIVERED_PAISE=1 WHERE DATASET_ID={id} AND LINE_ID={lid}',dict(id=orphan,lid='l1-0'));conn.commit()
        response=client.get('/api/finance').json()
        assert response['status']=='analytics_unavailable' and response['data'] is None and response['queried_at'] is None
        with a.connection() as conn:
            conn.execute('UPDATE ADVERGENT.FIN_LINES SET DELIVERED_PAISE=80000 WHERE DATASET_ID={id} AND LINE_ID={lid}',dict(id=orphan,lid='l1-0'));conn.commit()
        # Both connected platforms at zero spend: ratios undefined through actual SQL/API.
        zero=json.loads((ROOT/'fixtures/ads-corrected-v1.json').read_text());zero['version']='zero-'+str(uuid4())
        for platform,pages in zero['pages'].items():
            for page in pages:
                for report in page:
                    if platform=='meta':report['amount_rupees']='0.00'
                    else:report['cost_micros']=0
        zp=tmp_path/'zero-ads.json';zp.write_text(json.dumps(zero));import_ads(store,a,zp)
        from advergent.attribution import import_attribution
        import_attribution(store,a)
        import_finance(store,a,cp)
        z=client.get('/api/finance').json()['data']['totals']
        assert z['spend_paise']==0 and z['poas'] is None and z['mer'] is None
        assert z['contribution_before_ads_paise']==z['contribution_after_ads_paise']==expected
    finally:
        store.logout(token)
        with store.engine.begin() as conn:
            conn.execute(text('UPDATE ad_publications SET run_id=:id WHERE singleton=1'),dict(id=original_ads['id']))
            conn.execute(text('UPDATE attribution_publications SET run_id=:id WHERE singleton=1'),dict(id=tid))
            if original:conn.execute(text('INSERT INTO finance_publications VALUES (1,:id) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'),dict(id=original['id']))
            else:conn.execute(text('DELETE FROM finance_publications WHERE singleton=1'))
