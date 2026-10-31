"""Reproducible synthetic mapping and first-party click evidence."""
import json
from datetime import datetime, timedelta
from .operational import ROOT
from .attribution import MODEL, AttributionFixture


def build_fixture():
    commerce = json.loads((ROOT / 'fixtures/commerce-v1.json').read_text())
    orders = {r['id']: r['data'] for r in commerce['snapshot'] if r['kind'] == 'orders'}
    def identity(resource):
        platform = 'meta' if resource.startswith('m-') else 'google'
        return dict(platform=platform, account_id=platform + '-inr', resource_id=resource)
    def mapping(id, resource, products, **extra):
        return dict(id=id, **identity(resource), products=products, provenance='synthetic merchant catalog review',
                    confidence_bps=9500, valid_from='2026-01-01T00:00:00Z', valid_to='2027-01-01T00:00:00Z',
                    override=False, actor='fixture-operator', reason='Explicit reviewed product set', **extra)
    mappings = [mapping('single', 'm-ad', ['p0']), mapping('mixed', 'g-assets', ['p0', 'p1']),
                mapping('ambiguous-a', 'g-shopping-group', ['p2']), mapping('ambiguous-b', 'g-shopping-group', ['p3']),
                mapping('base', 'm-mixed-ad', ['p4'])]
    override = mapping('override', 'm-mixed-ad', ['p0', 'p1'])
    override.update(override=True, reason='Correct historical catalog set; supersedes candidate')
    mappings.append(override)
    low = mapping('low', 'g-search-b-ad', ['p9']); low['confidence_bps'] = 6000
    mappings.append(low)
    clicks = []
    def click(id, order, resource, days=1, seconds=0, kind='paid_click', identifiable=True):
        placed = datetime.fromisoformat(orders[order]['placed_at'])
        return dict(id=id, order_id=order, **identity(resource), clicked_at=(placed - timedelta(days=days, seconds=seconds)).isoformat(), kind=kind, identifiable=identifiable)
    clicks += [click('o0-old', 'o0', 'm-ad', 2), click('o0-last', 'o0', 'g-assets'), click('o0-last', 'o0', 'g-assets')]
    clicks += [click('boundary', 'o1', 'm-ad', 7), click('expired', 'o2', 'm-ad', 7, 1),
               click('view', 'o3', 'm-ad', kind='view'), click('future', 'o4', 'm-ad', -1),
               click('tie-a', 'o5', 'm-ad'), click('tie-b', 'o5', 'g-assets'),
               click('anonymous', 'o6', 'm-ad', identifiable=False), click('mixed-order', 'o10', 'g-assets'),
               click('cross-product-order', 'o35', 'g-assets')]
    claims = [dict(id='meta-claim', order_id='o0', **identity('m-ad'), reported_value_paise=100000),
              dict(id='google-claim', order_id='o0', **identity('g-assets'), reported_value_paise=100000)]
    source = dict(version='mapping-attribution-v1', model=MODEL, observed_at='2026-10-30T10:00:00Z', mappings=mappings, clicks=clicks, platform_claims=claims)
    AttributionFixture.model_validate_json(json.dumps(source))
    return source


if __name__ == '__main__':
    (ROOT / 'fixtures/attribution-v1.json').write_text(json.dumps(build_fixture(), indent=2) + '\n')
