"""Real local stores only; no analytical success substitutes."""
import copy
import hashlib
import json
import os
import secrets
from uuid import NAMESPACE_URL, uuid4, uuid5
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.api import create_app
from advergent.commerce import CommerceFixture, import_commerce
from advergent.commerce_fixture import build_fixture
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore, ROOT

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1', reason='Dedicated real database configuration required')]


def test_real_commerce_resume_reconcile_replay_failure_and_api(tmp_path):
    settings = Settings.from_env()
    store, analytics = OperationalStore(settings.database_url), ExasolAnalytics(settings)
    store.migrate()
    analytics.migrate()
    source = build_fixture(42)
    source['version'] = f'commerce-integration-{uuid4()}'
    path = tmp_path / 'source.json'
    path.write_text(json.dumps(source))
    fixture = CommerceFixture.model_validate_json(path.read_bytes())
    run = str(uuid5(NAMESPACE_URL, 'commerce-schema-v1:' + hashlib.sha256(path.read_bytes()).hexdigest()))
    # Isolate this deterministic test's staging while preserving the actual demo pointer.
    with store.engine.begin() as conn:
        original = conn.execute(text('SELECT run_id FROM commerce_publications WHERE singleton=1')).scalar()
        conn.execute(text('DELETE FROM commerce_publications WHERE run_id=:run'), {'run': run})
        conn.execute(text('DELETE FROM commerce_deliveries WHERE run_id=:run'), {'run': run})
        conn.execute(text('DELETE FROM commerce_staging WHERE run_id=:run'), {'run': run})
        conn.execute(text('DELETE FROM commerce_runs WHERE id=:run'), {'run': run})
    try:
        def interrupted(page):
            if page == len(fixture.pages):
                raise SystemExit('Simulated process exit after durable page commit')
        with pytest.raises(SystemExit):
            import_commerce(store, analytics, path, after_page=interrupted)
        with store.engine.connect() as conn:
            assert conn.execute(text('SELECT next_page FROM commerce_runs WHERE id=:run'), {'run': run}).scalar() == len(fixture.pages)
            def staged(kind, key):
                return conn.execute(text('SELECT body FROM commerce_staging WHERE run_id=:run AND kind=:kind AND source_id=:key'), dict(run=run, kind=kind, key=key)).scalar()
            assert staged('inventory', 'i1')['data']['available'] == 0  # newer stock wins
            assert staged('products', 'deleted-product')['deleted'] is True  # no resurrection
            assert staged('refunds', 'r0') is None  # missed event not yet repaired
            assert conn.execute(text("SELECT COUNT(*) FROM commerce_deliveries WHERE run_id=:run AND delivery_id='d0'"), {'run': run}).scalar() == 1
        def no_replay(page):
            pytest.fail('A committed page was replayed')
        assert import_commerce(store, analytics, path, after_page=no_replay) == run
        assert import_commerce(store, analytics, path) == run
        analytics.verify_commerce(run, fixture.snapshot)
        totals = analytics.commerce_totals(run)
        assert (totals.products, totals.variants, totals.orders, totals.lines, totals.refunds) == (30, 180, 42, 51, 2)
        data = {kind: [r.data for r in fixture.snapshot if r.kind == kind] for kind in ('lines', 'inventory', 'refunds')}
        assert totals.placed_merchandise_paise == sum(r['quantity'] * r['unit_price_paise'] - r['discount_paise'] for r in data['lines'])
        assert totals.sellable_units == sum(max(0, r['available']-r['merchant_reserve']) for r in data['inventory'])
        assert totals.refund_merchandise_paise == 140000
        assert store.commerce_publication()[0]['repair_count'] == 4
        # Fail inside the real analytical transaction after successful INSERTs.
        broken = copy.deepcopy(source)
        broken['version'] = source['version'] + '-rollback'
        broken_path = tmp_path / 'broken.json'
        broken_path.write_text(json.dumps(broken))
        failed_run = str(uuid5(NAMESPACE_URL, 'commerce-schema-v1:' + hashlib.sha256(broken_path.read_bytes()).hexdigest()))
        class DuplicateAtEnd(ExasolAnalytics):
            def load_commerce(self, dataset_id, records):
                super().load_commerce(dataset_id, records + [records[-1]])
        with pytest.raises(RuntimeError, match='prior publication preserved'):
            import_commerce(store, DuplicateAtEnd(settings), broken_path)
        assert store.commerce_publication()[0]['id'].__str__() == run
        assert store.commerce_publication()[1]['status'] == 'failed'
        failed_totals = analytics.commerce_totals(failed_run)
        assert all(getattr(failed_totals, kind) == 0 for kind in ('products', 'variants', 'customers', 'orders', 'lines', 'refunds', 'inventory'))
        with analytics.connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM ADVERGENT.COMMERCE_COMPLETE WHERE DATASET_ID={id}', {'id': failed_run}).fetchval() == 0
        # Resume from the completed source checkpoint after correcting loader failure.
        assert import_commerce(store, analytics, broken_path, after_page=no_replay) == failed_run
        analytics.verify_commerce(failed_run, fixture.snapshot)
        client = TestClient(create_app(settings, store, analytics))
        assert client.get('/api/commerce').status_code == 401
        assert client.get('/api/commerce/records/orders', params={'dataset_id': failed_run}).status_code == 401
        token = secrets.token_urlsafe(32)
        store.login(token)
        client.cookies.set('advergent_session', token, path='/api')
        result = client.get('/api/commerce').json()
        assert result['status'] == 'available' and result['freshness'] == 'stale'
        assert result['totals']['orders'] == 42 and result['queried_at']
        assert client.get('/api/commerce/records/orders', params={'dataset_id': failed_run, 'limit': 2}).json()[0]['data']['currency'] == 'INR'
        assert client.get('/api/commerce/records/orders', params={'dataset_id': run}).status_code == 409
        assert client.get('/api/commerce/records/orders', params={'dataset_id': failed_run, 'limit': 101}).status_code == 422
        store.logout(token)
        # Conflicting revisions fail their page atomically; neither cursor nor
        # delivery receipt can advance past an uncommitted source change.
        conflict = copy.deepcopy(source)
        conflict['version'] = source['version'] + '-conflict'
        delivery = copy.deepcopy(conflict['pages'][0][0])
        delivery['delivery_id'] = 'equal-revision-conflict'
        delivery['record']['data']['title'] = 'Conflicting title'
        conflict['pages'][0].append(delivery)
        conflict_path = tmp_path / 'conflict.json'
        conflict_path.write_text(json.dumps(conflict))
        conflict_run = str(uuid5(NAMESPACE_URL, 'commerce-schema-v1:' + hashlib.sha256(conflict_path.read_bytes()).hexdigest()))
        with pytest.raises(RuntimeError, match='prior publication preserved'):
            import_commerce(store, analytics, conflict_path)
        with store.engine.connect() as conn:
            assert conn.execute(text('SELECT next_page FROM commerce_runs WHERE id=:run'), {'run': conflict_run}).scalar() == 0
            assert conn.execute(text('SELECT COUNT(*) FROM commerce_deliveries WHERE run_id=:run'), {'run': conflict_run}).scalar() == 0
        assert str(store.commerce_publication()[0]['id']) == failed_run
    finally:
        if original:
            with store.engine.begin() as conn:
                conn.execute(text('UPDATE commerce_publications SET run_id=:run WHERE singleton=1'), {'run': original})
