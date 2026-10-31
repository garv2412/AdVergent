"""Phase 4 gate: actual local stores, SQL rollback, publication and API."""
import hashlib
import json
import os
import secrets
from uuid import NAMESPACE_URL, uuid4, uuid5
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.attribution import import_attribution
from advergent.attribution_fixture import build_fixture
from advergent.api import create_app
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1', reason='Dedicated real stores required')]


def test_real_mapping_attribution_replay_failure_reconciliation_and_authentication(tmp_path):
    settings = Settings.from_env()
    store, analytics = OperationalStore(settings.database_url), ExasolAnalytics(settings)
    store.migrate(); analytics.migrate()
    original = store.attribution_publication()[0]
    original_ads = store.ad_publication()[0]
    token = secrets.token_urlsafe(32)
    def source(suffix):
        data = build_fixture(); data['version'] += '-' + suffix + '-' + str(uuid4())
        path = tmp_path / (suffix + '.json'); path.write_text(json.dumps(data))
        commerce, ads = store.commerce_publication()[0], store.ad_publication()[0]
        run = str(uuid5(NAMESPACE_URL, 'attribution-v1:' + hashlib.sha256(path.read_bytes()).hexdigest() + str(commerce['id']) + str(ads['id'])))
        return path, run
    try:
        path, run = source('success')
        assert import_attribution(store, analytics, path) == run
        before = store.attribution_publication()[0]
        assert import_attribution(store, analytics, path) == run
        assert store.attribution_publication()[0]['finished_at'] == before['finished_at']
        assert store.attribution_publication()[0]['observed_at'] == before['observed_at']
        data = analytics.attribution_data(run)
        assert data['reconciliation'] == dict(orders=3000, lines=3600, placed_merchandise_paise=369912000, refunds=143)
        groups = {g['campaign_id']: g for g in data['groups']}
        assert groups['m-abo']['placed_merchandise_paise'] == 80000 and groups['m-abo']['orders'] == 1
        assert groups['g-pmax']['orders'] == 3
        assert groups[None]['orders'] == 2996
        assert len(data['assignments']) == len({r['order_id'] for r in data['assignments']}) == 3000
        assert len(data['platform_claims']) == 2  # both claim o0 without double assignment
        rows = {m['resource_id']: m for m in data['mappings']}
        assert rows['g-assets']['products'] == ['p0', 'p1']
        assert rows['g-shopping-group']['status'] == 'ambiguous'
        assert rows['m-mixed-ad']['override']
        assert {p['product_id'] for p in data['product_allocations'] if p['campaign_id'] == 'g-pmax'} == {'p0', 'p1', 'p5', 'p6'}
        assert all(r['campaign_id'] == next(a['campaign_id'] for a in data['assignments'] if a['order_id'] == r['order_id']) for r in data['refund_links'])
        broken_path, broken = source('rollback')
        class Broken(ExasolAnalytics):
            def load_attribution(self, run, commerce, data):
                data = dict(data, assignments=data['assignments'] + [data['assignments'][-1]])
                super().load_attribution(run, commerce, data)
        with pytest.raises(RuntimeError, match='prior publication preserved'):
            import_attribution(store, Broken(settings), broken_path)
        assert str(store.attribution_publication()[0]['id']) == run
        assert store.attribution_publication()[1] == 'failed'
        with analytics.connection() as conn:
            for table in ('ATTR_ENTITIES', 'ATTR_ORDERS', 'ATTR_COMPLETE'):
                assert conn.execute(f'SELECT COUNT(*) FROM ADVERGENT.{table} WHERE DATASET_ID={{id}}', dict(id=broken)).fetchval() == 0
        client = TestClient(create_app(settings, store, analytics))
        assert client.get('/api/attribution').status_code == 401
        store.login(token); client.cookies.set('advergent_session', token, path='/api')
        result = client.get('/api/attribution').json()
        assert result['status'] == 'available' and result['data']['reconciliation']['orders'] == 3000
        assert result['latest_import_status'] == 'failed' and result['dependencies_current']
        assert result['model'] == 'last-paid-click-7d-no-view-v1' and result['freshness'] == 'stale'
        assert result['queried_at'] and result['commerce_id'] and result['ads_id']
        with store.engine.connect() as locked:
            locked.execute(text('SELECT pg_advisory_lock(17012030)')); locked.commit()
            try:
                with pytest.raises(RuntimeError, match='Dependent import already running'):
                    import_attribution(store, analytics, path)
            finally:
                locked.execute(text('SELECT pg_advisory_unlock(17012030)')); locked.commit()
        from advergent.ads import import_ads
        from advergent.operational import ROOT
        import_ads(store, analytics, ROOT / 'fixtures/ads-initial-v1.json')
        pinned = client.get('/api/attribution').json()
        assert not pinned['dependencies_current'] and pinned['data']['reconciliation'] == result['data']['reconciliation']
        with store.engine.begin() as conn:
            conn.execute(text('UPDATE ad_publications SET run_id=:id WHERE singleton=1'), dict(id=original_ads['id']))
        assert import_attribution(store, analytics, broken_path) == broken
        orphan_path, orphan = source('orphan')
        class VerifyFailure(ExasolAnalytics):
            def verify_attribution(self, *args): raise RuntimeError('After actual commit')
        with pytest.raises(RuntimeError): import_attribution(store, VerifyFailure(settings), orphan_path)
        assert str(store.attribution_publication()[0]['id']) == broken
        assert analytics.attribution_data(orphan)['reconciliation']['orders'] == 3000
        assert import_attribution(store, analytics, orphan_path) == orphan
        assert len(analytics.attribution_data(orphan)['assignments']) == 3000
        # A corrupt published assignment is detected rather than served as reconciled.
        with analytics.connection() as conn:
            conn.execute('UPDATE ADVERGENT.ATTR_ORDERS SET CAMPAIGN_ID={campaign} WHERE DATASET_ID={id} AND ORDER_ID={order}', dict(campaign='corrupt', id=orphan, order='o0')); conn.commit()
        unavailable = client.get('/api/attribution').json()
        assert unavailable['status'] == 'analytics_unavailable' and unavailable['data'] is None and unavailable['queried_at'] is None
        assert unavailable['dataset_id'] == orphan
        with analytics.connection() as conn:
            conn.execute('UPDATE ADVERGENT.ATTR_ORDERS SET CAMPAIGN_ID={campaign} WHERE DATASET_ID={id} AND ORDER_ID={order}', dict(campaign='g-pmax', id=orphan, order='o0')); conn.commit()
        # Operational config is immutable evidence, not an analytics fallback.
        with store.engine.connect() as conn:
            assert conn.execute(text('SELECT configuration->>\'model\' FROM attribution_runs WHERE id=:id'), dict(id=run)).scalar() == result['model']
    finally:
        store.logout(token)
        with store.engine.begin() as conn:
            conn.execute(text('UPDATE ad_publications SET run_id=:id WHERE singleton=1'), dict(id=original_ads['id']))
            if original:
                conn.execute(text('INSERT INTO attribution_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'), dict(run=original['id']))
            else:
                conn.execute(text('DELETE FROM attribution_publications WHERE singleton=1'))
