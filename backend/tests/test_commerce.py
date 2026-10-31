import copy
import json
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from advergent.commerce import CommerceFixture, Record, validate_snapshot
from advergent.commerce_fixture import build_fixture


def test_fixture_is_deterministic_and_preserves_source_semantics():
    source = build_fixture(42)
    assert source == build_fixture(42)
    fixture = CommerceFixture.model_validate_json(json.dumps(source))
    groups = validate_snapshot(fixture.snapshot)
    assert len(groups['orders']) == 42
    assert len(groups['variants']) == 180
    assert groups['inventory']['i0']['available'] == 0
    assert groups['inventory']['i0']['committed'] == 3
    assert groups['lines']['l0-0']['unit_cost_paise'] is None
    assert groups['lines']['l1-0']['unit_cost_paise'] != groups['variants']['v1']['unit_cost_paise']
    assert groups['orders']['o0']['payment_status'] == 'unremitted'
    assert groups['orders']['o4']['fulfillment_status'] == 'rto'
    assert groups['refunds']['r0']['quantity'] < groups['lines']['l0-0']['quantity']
    assert {r['data']['synthetic_key'] for r in source['snapshot'] if r['kind'] == 'customers'} == {f'synthetic-customer-{i}' for i in range(1000)}


@pytest.mark.parametrize('mutation', ['float', 'currency', 'naive', 'missing', 'duplicate', 'future'])
def test_bad_source_is_rejected(mutation):
    source = build_fixture(2)
    if mutation == 'float':
        next(r for r in source['snapshot'] if r['kind'] == 'lines')['data']['unit_price_paise'] = 1.5
    elif mutation == 'currency':
        next(r for r in source['snapshot'] if r['kind'] == 'orders')['data']['currency'] = 'USD'
    elif mutation == 'naive':
        source['observed_at'] = '2026-10-29T18:00:00'
    elif mutation == 'missing':
        next(r for r in source['snapshot'] if r['kind'] == 'lines')['data']['cost_status'] = 'actual'
    elif mutation == 'duplicate':
        source['snapshot'].append(copy.deepcopy(source['snapshot'][0]))
    else:
        source['observed_at'] = source['scenario_clock'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        CommerceFixture.model_validate_json(json.dumps(source))


@pytest.mark.parametrize('mutation', ['dangling', 'refund', 'warehouse', 'inventory'])
def test_reconciliation_rejects_invalid_relationships(mutation):
    source = build_fixture(2)
    if mutation == 'dangling':
        source['snapshot'] = [r for r in source['snapshot'] if r['kind'] != 'customers']
    elif mutation == 'refund':
        next(r for r in source['snapshot'] if r['kind'] == 'refunds')['data']['quantity'] = 10
    elif mutation == 'warehouse':
        extra = copy.deepcopy(next(r for r in source['snapshot'] if r['kind'] == 'inventory'))
        extra['id'] = 'duplicate-stock'
        source['snapshot'].append(extra)
    else:
        source['snapshot'] = [r for r in source['snapshot'] if not (r['kind'] == 'inventory' and r['id'] == 'i0')]
    fixture = CommerceFixture.model_validate_json(json.dumps(source))
    with pytest.raises(ValueError):
        validate_snapshot(fixture.snapshot)
