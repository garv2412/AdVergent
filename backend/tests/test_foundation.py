import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from advergent.api import create_app
from advergent.config import Settings
from advergent.contracts import AnalyticsUnavailable, GoldenMetric, CommerceTotals
from advergent.exasol import ExasolAnalytics
from advergent.operational import ROOT
from advergent.security import hash_password, token_hash

FIXTURE = json.loads((ROOT / 'fixtures/foundation-v1.json').read_text())
SETTINGS = Settings('unused', hash_password('test-password'), '127.0.0.1:1', 'unused', 'unused', 'http://testserver', False)
HEADERS = {'Origin': 'http://testserver', 'X-AdVergent-Request': '1'}


class MemoryStore:
    def __init__(self):
        self.tokens = set()
        self.published = None
        self.latest = None

    def session(self, token): return token_hash(token) in self.tokens
    def login(self, token): self.tokens.add(token_hash(token))
    def logout(self, token): self.tokens.discard(token_hash(token))
    def publication(self): return self.published, self.latest


class StubAnalytics:
    unavailable = False
    calls = 0

    def metric(self, dataset_id):
        self.calls += 1
        if self.unavailable:
            raise AnalyticsUnavailable()
        return GoldenMetric(**FIXTURE['expected'])


@pytest.fixture
def context():
    store, analytics = MemoryStore(), StubAnalytics()
    client = TestClient(create_app(SETTINGS, store, analytics))
    return client, store, analytics


def sign_in(client):
    response = client.post('/api/login', json={'password': 'test-password'}, headers=HEADERS)
    assert response.status_code == 204
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']


def test_authentication_csrf_and_logout(context):
    client, store, analytics = context
    assert client.get('/api/foundation').status_code == 401
    assert analytics.calls == 0
    assert client.post('/api/login', json={'password': 'test-password'}).status_code == 403
    assert client.post('/api/login', json={'password': 'wrong'}, headers=HEADERS).status_code == 401
    sign_in(client)
    assert client.get('/api/session').status_code == 200
    client.post('/api/logout', headers=HEADERS)
    assert client.get('/api/foundation').status_code == 401
    assert not store.tokens


def test_unloaded_and_failed_analytics_do_not_invent_metrics(context):
    client, store, analytics = context
    sign_in(client)
    assert client.get('/api/foundation').json()['status'] == 'not_loaded'
    store.published = dict(id=uuid4(), dataset_id=uuid4(), dataset_version='foundation-v1', fixture_hash='abc', finished_at=datetime.now(timezone.utc))
    store.latest = 'succeeded'
    result = client.get('/api/foundation').json()
    assert result['metric']['contribution_after_ads_paise'] == 30000
    assert result['queried_at'] is not None
    analytics.unavailable = True
    store.latest = 'failed'
    result = client.get('/api/foundation').json()
    assert result['status'] == 'analytics_unavailable'
    assert result['metric'] is None
    assert result['queried_at'] is None
    assert result['latest_refresh_status'] == 'failed'


def test_operational_failure_is_sanitized(context):
    client, store, _ = context
    sign_in(client)
    def fail(): raise OperationalError('secret DSN', {}, Exception('secret'))
    store.publication = fail
    response = client.get('/api/foundation')
    assert response.status_code == 503
    assert 'secret' not in response.text


def test_exasol_unreachable_is_sanitized():
    with pytest.raises(AnalyticsUnavailable, match='Exasol operation failed'):
        ExasolAnalytics(SETTINGS).probe()


def test_fixture_matches_independent_hand_calculation():
    # Golden oracle uses paise; fixture inputs aren't computed from the outputs.
    assert sum(line['net_sales_paise'] for line in FIXTURE['lines']) == 400000
    assert sum(line['product_cost_paise'] for line in FIXTURE['lines']) == 220000
    assert sum(line['variable_cost_paise'] for line in FIXTURE['lines']) == 50000
    assert sum(spend['spend_paise'] for spend in FIXTURE['spend']) == 100000
    assert 400000 - 220000 - 50000 - 100000 == FIXTURE['expected']['contribution_after_ads_paise']


def test_commerce_freshness_uses_source_clock_and_outage_hides_totals(context):
    from datetime import timedelta
    client, store, analytics = context
    sign_in(client)
    store.commerce_publication = lambda: (None, None)
    assert client.get('/api/commerce').json()['status'] == 'not_loaded'
    published = dict(id=uuid4(), version='test', fixture_hash='hash', observed_at=datetime.now(timezone.utc)-timedelta(seconds=800), scenario_clock=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), repair_count=4)
    store.commerce_publication = lambda: (published, {'status': 'failed', 'next_page': 2})
    analytics.commerce_totals = lambda dataset: CommerceTotals(**dict.fromkeys(CommerceTotals.model_fields, 0))
    result = client.get('/api/commerce').json()
    assert result['freshness'] == 'fresh'
    assert result['latest_import_status'] == 'failed' and result['next_page'] == 2
    published['observed_at'] -= timedelta(seconds=200)
    assert client.get('/api/commerce').json()['freshness'] == 'stale'
    def fail(dataset):
        raise AnalyticsUnavailable()
    analytics.commerce_totals = fail
    result = client.get('/api/commerce').json()
    assert result['status'] == 'analytics_unavailable' and result['freshness'] == 'unknown'
    assert result['totals'] is None and result['queried_at'] is None
    assert result['observed_at'] is not None
