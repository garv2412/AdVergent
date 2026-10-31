"""Explicit opt-in. Uses a dedicated test database/schema; no runtime substitutes."""
import json
import os
import hashlib
import secrets
from dataclasses import replace
from uuid import uuid5, NAMESPACE_URL
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from advergent.api import create_app
from advergent.config import Settings
from advergent.contracts import AnalyticsUnavailable
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore, ROOT
from advergent.worker import refresh
from advergent.security import token_hash

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1', reason='Set RUN_INTEGRATION=1 with dedicated real database configuration')]


def test_real_foundation_replay_and_failure(tmp_path):
    settings = Settings.from_env()
    store, analytics = OperationalStore(settings.database_url), ExasolAnalytics(settings)
    store.migrate()
    analytics.migrate()
    analytics.probe()
    host, port = settings.exasol_dsn.rsplit(':', 1)
    if '/' in host:
        bad_fingerprint = host.split('/')[0] + '/' + '0' * 64 + ':' + port
        with pytest.raises(AnalyticsUnavailable):
            ExasolAnalytics(replace(settings, exasol_dsn=bad_fingerprint)).probe()
    first_id = refresh(store, analytics)
    first = analytics.metric(first_id)
    assert first.model_dump() == json.loads((ROOT / 'fixtures/foundation-v1.json').read_text())['expected']
    assert refresh(store, analytics) == first_id
    assert analytics.metric(first_id) == first
    original, _ = store.publication()
    class FailedAnalytics:
        def probe(self): raise AnalyticsUnavailable()
    with pytest.raises(RuntimeError, match='prior publication preserved'):
        refresh(store, FailedAnalytics())
    preserved, latest = store.publication()
    assert preserved['id'] == original['id']
    assert latest == 'failed'
    # Force an actual database error after one successful INSERT, before COMMIT.
    fixture = json.loads((ROOT / 'fixtures/foundation-v1.json').read_text())
    fixture['lines'][1]['id'] = fixture['lines'][0]['id']
    broken = tmp_path / 'duplicate-primary-key.json'
    broken.write_text(json.dumps(fixture))
    failed_dataset = str(uuid5(NAMESPACE_URL, hashlib.sha256(broken.read_bytes()).hexdigest()))
    with pytest.raises(RuntimeError, match='prior publication preserved'):
        refresh(store, analytics, broken)
    assert analytics.metric(failed_dataset).line_count == 0
    assert store.publication()[0]['id'] == original['id']
    with store.engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM refresh_jobs WHERE status='running'")).scalar() == 0
    # DB queries above are real; controlled failure below only verifies API reporting.
    client = TestClient(create_app(settings, store, analytics))
    assert client.get('/api/foundation').status_code == 401
    token = secrets.token_urlsafe(32)
    store.login(token)
    client.cookies.set('advergent_session', token, path='/api')
    response = client.get('/api/foundation')
    assert response.status_code == 200
    assert response.json()['metric']['contribution_after_ads_paise'] == 30000
    with store.engine.begin() as conn:
        conn.execute(text("UPDATE sessions SET expires_at=now()-interval '1 second' WHERE token_hash=:hash"), {'hash': token_hash(token)})
    assert client.get('/api/foundation').status_code == 401
    store.logout(token)
