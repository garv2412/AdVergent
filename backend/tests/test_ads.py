import copy
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from advergent.ads import AdFixture, hierarchy, budget_capabilities
from advergent.ads_fixture import build_fixture
from advergent.contracts import AnalyticsUnavailable


def parse(source):
    return AdFixture.model_validate_json(json.dumps(source))


def resolved(fixture):
    result = {}
    for pages in fixture.pages.values():
        for page in pages:
            for r in page:
                if r.key not in result or result[r.key].revision < r.revision:
                    result[r.key] = r
    return list(result.values())


def test_source_oracles_currency_timezones_replacements_and_capabilities():
    initial, corrected = parse(build_fixture(False)), parse(build_fixture(True))
    first, final = resolved(initial), resolved(corrected)
    # Independent literal oracles: 100.01+200.02+500.03+600.04+700.05+800.06
    assert len(first) == 6 and sum(r.paise for r in first) == 290021
    # Replace 100.01 with 90.01, replace 800.06 with zero, add delayed 10.07.
    assert len(final) == 7 and sum(r.paise for r in final) == 210022
    assert sum(r.paise for r in final if r.platform == 'meta') == 30010
    assert sum(r.paise for r in final if r.platform == 'google') == 180012
    by_day = {}
    for r in final:
        day = r.normalized()['reporting_day']
        by_day[day] = by_day.get(day, 0) + r.paise
    assert by_day == {'2026-10-29': 59004, '2026-10-30': 151018}
    google_next_day = next(r for r in final if r.resource_id == 'g-assets')
    assert google_next_day.source_day == '2026-10-29'
    assert google_next_day.normalized()['reporting_day'] == '2026-10-30'
    rows = {r['id']: r for r in hierarchy(corrected)}
    assert rows['m-ad']['budget_owner_id'] == 'm-set'
    assert rows['m-mixed-ad']['budget_owner_id'] == 'm-cbo'
    assert rows['m-abo']['effective_budget_id'] is None
    assert rows['m-abo']['affected_budget_ids'] == ['m-set-budget']
    assert rows['g-search-a-ad']['budget_members'] == ['g-search-a', 'g-search-b']
    assert rows['g-assets']['product_scope'] == 'multiple' and not rows['g-assets']['shared_budget']
    assert rows['g-shopping-group']['product_scope'] == 'multiple'
    assert len(rows['g-assets']['source_product_refs']) == 2
    assert len(rows['m-ad']['source_product_refs']) == 1
    assert all(not r['mutation_enabled'] and not r['product_control_supported'] for r in rows.values())
    assert rows['m-set']['budget_control_supported'] and not rows['m-ad']['budget_control_supported']
    b = {b['id']: b for b in budget_capabilities(corrected)}
    assert b['g-shared']['shared'] and len(b['g-shared']['member_ids']) == 2
    assert b['g-pmax-budget']['member_ids'] == ['g-pmax'] and not b['g-pmax-budget']['shared']


@pytest.mark.parametrize('case', ['currency', 'float', 'micros', 'rupees', 'parent', 'budget', 'double_owner', 'source_day', 'naive', 'offset', 'future', 'nonadditive', 'conflict', 'nonshared', 'scope'])
def test_invalid_sources_rejected(case):
    source = build_fixture()
    r = source['pages']['google'][0][0]
    if case == 'currency': source['accounts'][0]['currency'] = 'USD'
    if case == 'float': r['cost_micros'] = 1.5
    if case == 'micros': r['cost_micros'] = 10001
    if case == 'rupees': source['pages']['meta'][0][0]['amount_rupees'] = '1.001'
    if case == 'parent': source['resources'][2]['parent_id'] = 'missing'
    if case == 'budget': source['budgets'][0]['owner_id'] = 'm-ad'
    if case == 'double_owner': source['resources'][0]['budget_id'] = 'm-campaign-budget'
    if case == 'source_day': r['source_day'] = '2026-10-30'
    if case == 'naive': r['interval_start'] = '2026-10-29T18:00:00'
    if case == 'offset': r['interval_start'] = '2026-10-29T18:00:00+00:15'
    if case == 'future': r['reported_at'] = '2099-01-01T00:00:00Z'
    if case == 'nonadditive': r['resource_id'] = 'g-search-a'
    if case == 'conflict':
        r = copy.deepcopy(r)
        r['cost_micros'] = 0
        source['pages']['google'][0].append(r)
    if case == 'nonshared': source['budgets'][2]['shared'] = False
    if case == 'scope': source['resources'][0]['source_product_refs'] = []
    with pytest.raises(ValidationError): parse(source)


def test_ad_api_auth_freshness_unloaded_and_unavailability():
    from test_foundation import MemoryStore, StubAnalytics, SETTINGS, HEADERS
    from fastapi.testclient import TestClient
    from advergent.api import create_app
    store, analytics = MemoryStore(), StubAnalytics()
    store.ad_publication = lambda: (None, None)
    client = TestClient(create_app(SETTINGS, store, analytics))
    assert client.get('/api/ads').status_code == 401
    assert client.post('/api/login', json={'password': 'test-password'}, headers=HEADERS).status_code == 204
    assert client.get('/api/ads').json()['status'] == 'not_loaded'
    published = dict(id=uuid4(), version='test', fixture_hash='hash', observed_at=datetime.now(timezone.utc)-timedelta(seconds=800), scenario_clock=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc))
    store.ad_publication = lambda: (published, 'failed')
    analytics.ad_data = lambda dataset: dict(accounts=[], budgets=[], resources=[], reports=[], groups=[], report_count=0, spend_paise=0)
    result = client.get('/api/ads').json()
    assert result['freshness'] == 'fresh' and result['latest_import_status'] == 'failed'
    published['observed_at'] -= timedelta(seconds=200)
    assert client.get('/api/ads').json()['freshness'] == 'stale'
    def fail(dataset): raise AnalyticsUnavailable()
    analytics.ad_data = fail
    result = client.get('/api/ads').json()
    assert result['status'] == 'analytics_unavailable' and result['data'] is None
    assert result['freshness'] == 'unknown' and result['queried_at'] is None and result['observed_at']
