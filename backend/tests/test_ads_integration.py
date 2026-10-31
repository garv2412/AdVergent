"""Phase 3 gate against real PostgreSQL/Exasol; no substituted success paths."""
import hashlib
import json
import os
import secrets
from uuid import NAMESPACE_URL, uuid4, uuid5
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.ads import import_ads
from advergent.ads_fixture import build_fixture
from advergent.api import create_app
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1', reason='Dedicated real database configuration required')]


def test_real_ad_reporting_correction_replay_resume_failure_and_authenticated_queries(tmp_path):
    settings = Settings.from_env()
    store, analytics = OperationalStore(settings.database_url), ExasolAnalytics(settings)
    store.migrate()
    analytics.migrate()
    original = store.ad_publication()[0]
    token = secrets.token_urlsafe(32)

    def source_file(corrected, suffix):
        source = build_fixture(corrected)
        source['version'] += '-' + suffix + '-' + str(uuid4())
        path = tmp_path / (suffix + '.json')
        path.write_text(json.dumps(source))
        run = str(uuid5(NAMESPACE_URL, 'ads-schema-v2:' + hashlib.sha256(path.read_bytes()).hexdigest()))
        return path, run

    try:
        path, initial = source_file(False, 'initial')
        assert import_ads(store, analytics, path) == initial
        assert analytics.ad_data(initial)['spend_paise'] == 290021
        path, corrected = source_file(True, 'corrected')
        def interrupt(platform, page):
            if platform == 'google' and page == 2:
                raise SystemExit('Controlled process exit after both adapters committed pages')
        with pytest.raises(SystemExit): import_ads(store, analytics, path, after_page=interrupt)
        assert str(store.ad_publication()[0]['id']) == initial
        with store.engine.connect() as conn:
            assert sorted(conn.execute(text('SELECT next_page FROM ad_cursors WHERE run_id=:run'), {'run': corrected}).scalars()) == [2, 2]
            assert conn.execute(text('SELECT count(*) FROM ad_source_reports WHERE run_id=:run'), {'run': corrected}).scalar() == 7
        def no_replay(platform, page): pytest.fail('Committed source page replayed')
        assert import_ads(store, analytics, path, after_page=no_replay) == corrected
        publication = store.ad_publication()[0]
        assert import_ads(store, analytics, path, after_page=no_replay) == corrected
        replay = store.ad_publication()[0]
        assert replay['finished_at'] == publication['finished_at'] and replay['observed_at'] == publication['observed_at']
        data = analytics.ad_data(corrected)
        assert (data['report_count'], data['spend_paise']) == (7, 210022)
        assert sum(g['spend_paise'] for g in data['groups'] if g['reporting_day'] == '2026-10-29') == 59004
        assert sum(g['spend_paise'] for g in data['groups'] if g['reporting_day'] == '2026-10-30') == 151018
        assert sum(g['spend_paise'] for g in data['groups'] if g['budget_id'] == 'g-shared') == 110007
        assert next(r for r in data['reports'] if r['resource_id'] == 'g-assets')['spend_paise'] == 0
        broken_path, broken = source_file(True, 'rollback')
        class DuplicateAtEnd(ExasolAnalytics):
            def load_ads(self, run, fixture, reports):
                super().load_ads(run, fixture, reports + [reports[-1]])
        with pytest.raises(RuntimeError, match='prior publication preserved'):
            import_ads(store, DuplicateAtEnd(settings), broken_path)
        assert str(store.ad_publication()[0]['id']) == corrected
        assert store.ad_publication()[1] == 'failed'
        with analytics.connection() as conn:
            for table in ('AD_ENTITIES', 'AD_RESOURCES', 'AD_REPORTS', 'AD_COMPLETE'):
                assert conn.execute(f'SELECT COUNT(*) FROM ADVERGENT.{table} WHERE DATASET_ID={{id}}', {'id': broken}).fetchval() == 0
        client = TestClient(create_app(settings, store, analytics))
        assert client.get('/api/ads').status_code == 401
        store.login(token)
        client.cookies.set('advergent_session', token, path='/api')
        result = client.get('/api/ads').json()
        assert result['status'] == 'available' and result['freshness'] == 'stale'
        assert result['data']['spend_paise'] == 210022 and result['latest_import_status'] == 'failed'
        assert result['fixture_hash'] == publication['fixture_hash'] and result['queried_at']
        assert result['reporting_timezone'] == 'Asia/Kolkata' and result['currency'] == 'INR'
        assert all(not r['product_control_supported'] and not r['mutation_enabled'] for r in result['data']['resources'])
        # Resume failed SQL load from durable source state; no source-page replay.
        assert import_ads(store, analytics, broken_path, after_page=no_replay) == broken
        assert analytics.ad_data(broken)['spend_paise'] == 210022
        # Commit-then-publication failure leaves immutable orphan evidence; retry reuses it.
        orphan_path, orphan = source_file(True, 'orphan')
        class VerifyFailure(ExasolAnalytics):
            def verify_ads(self, *args): raise RuntimeError('Fault after real Exasol commit')
        with pytest.raises(RuntimeError): import_ads(store, VerifyFailure(settings), orphan_path)
        assert str(store.ad_publication()[0]['id']) == broken
        assert analytics.ad_data(orphan)['spend_paise'] == 210022
        assert import_ads(store, analytics, orphan_path, after_page=no_replay) == orphan
        assert analytics.ad_data(orphan)['report_count'] == 7
    finally:
        store.logout(token)
        with store.engine.begin() as conn:
            if original:
                conn.execute(text('INSERT INTO ad_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'), {'run': original['id']})
            else:
                conn.execute(text('DELETE FROM ad_publications WHERE singleton=1'))
