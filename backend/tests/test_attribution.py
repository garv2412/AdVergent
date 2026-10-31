import copy
from datetime import datetime, timezone, timedelta
import json
import pytest
from advergent.attribution import AttributionFixture, derive, resolve_mapping
from advergent.attribution_fixture import build_fixture
from advergent.ads import AdFixture, hierarchy
from advergent.commerce import CommerceFixture
from advergent.operational import ROOT


def inputs(source=None):
    fixture = AttributionFixture.model_validate_json(json.dumps(source or build_fixture()))
    commerce = CommerceFixture.model_validate_json((ROOT / 'fixtures/commerce-v1.json').read_bytes())
    ads = AdFixture.model_validate_json((ROOT / 'fixtures/ads-corrected-v1.json').read_bytes())
    return fixture, [r for r in commerce.snapshot if r.kind == 'orders'], [r.id for r in commerce.snapshot if r.kind == 'products'], hierarchy(ads)


def test_mapping_sets_overrides_ambiguity_and_native_hints():
    data = derive(*inputs())
    rows = {r['resource_id']: r for r in data['mappings']}
    assert rows['g-assets']['products'] == ['p0', 'p1']
    assert rows['g-shopping-group']['status'] == 'ambiguous' and rows['g-shopping-group']['products'] == []
    assert rows['m-mixed-ad']['override'] and rows['m-mixed-ad']['products'] == ['p0', 'p1']
    assert rows['g-search-b-ad']['status'] == 'unmapped'
    assert rows['m-set']['status'] == 'unmapped'  # no inferred parent/child mapping
    assert all(not r['product_control_supported'] for r in rows.values())


def test_mapping_half_open_validity_and_conflicting_overrides_abstain():
    fixture = inputs()[0]
    m = fixture.mappings[0]
    assert resolve_mapping([m], m.key, m.valid_from)['status'] == 'resolved'
    assert resolve_mapping([m], m.key, m.valid_to)['status'] == 'unmapped'
    assert resolve_mapping([m], m.key, m.valid_from - timedelta(microseconds=1))['status'] == 'unmapped'
    a = m.model_copy(update={'override': True})
    b = m.model_copy(update={'id': 'other', 'override': True, 'products': ['p9']})
    assert resolve_mapping([a, b], m.key, m.valid_from)['status'] == 'ambiguous'


def test_last_click_window_dedup_ties_and_unattributed():
    data = derive(*inputs())
    rows = {r['order_id']: r for r in data['assignments']}
    assert len(rows) == len(data['assignments']) == 3000
    assert rows['o0']['campaign_id'] == 'g-pmax' and rows['o0']['click_ids'] == ['o0-last']
    assert rows['o1']['campaign_id'] == 'm-abo'  # exactly seven days
    for order in ('o2', 'o3', 'o4', 'o6'):
        assert rows[order]['campaign_id'] is None
    assert rows['o5']['reason'] == 'ambiguous_click'
    assert sum(r['campaign_id'] is not None for r in rows.values()) == 4
    assert len(data['platform_claims']) == 2 and all(c['order_id'] == 'o0' for c in data['platform_claims'])


@pytest.mark.parametrize('change', ['conflict', 'unknown_product', 'unknown_resource', 'unknown_order', 'invalid_interval', 'duplicate_product', 'future', 'model'])
def test_invalid_evidence_rejects(change):
    source = copy.deepcopy(build_fixture())
    if change == 'conflict': source['clicks'][2]['resource_id'] = 'm-ad'
    if change == 'unknown_product': source['mappings'][0]['products'] = ['missing']
    if change == 'unknown_resource': source['mappings'][0]['account_id'] = 'other-account'
    if change == 'unknown_order': source['clicks'][0]['order_id'] = 'missing'
    if change == 'invalid_interval': source['mappings'][0]['valid_to'] = source['mappings'][0]['valid_from']
    if change == 'duplicate_product': source['mappings'][0]['products'] = ['p0', 'p0']
    if change == 'future': source['observed_at'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    if change == 'model': source['model'] = 'unsupported'
    with pytest.raises(ValueError): derive(*inputs(source))


def test_fixture_reproducible():
    assert (ROOT / 'fixtures/attribution-v1.json').read_text() == json.dumps(build_fixture(), indent=2) + '\n'
