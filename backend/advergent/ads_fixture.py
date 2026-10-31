"""Deterministic input scenarios; oracle totals live independently in tests."""
import json
from .operational import ROOT
from .ads import AdFixture


def build_fixture(corrected=True):
    accounts = [dict(platform='meta', id='meta-inr', currency='INR', timezone='Asia/Kolkata'),
                dict(platform='google', id='google-inr', currency='INR', timezone='UTC')]
    resources, budgets = [], []

    def resource(platform, id, parent, kind, campaign_type, budget=None, scope='single'):
        resources.append(dict(platform=platform, account_id=f'{platform}-inr', id=id, parent_id=parent,
                              kind=kind, campaign_type=campaign_type, name=id, status='active', budget_id=budget, product_scope=scope,
                              source_product_refs=['native-product-01', 'native-product-02'] if scope == 'multiple' else ['native-product-01'] if scope == 'single' else []))

    def budget(platform, id, owner=None, shared=False, amount=100000):
        budgets.append(dict(platform=platform, account_id=f'{platform}-inr', id=id, owner_id=owner, shared=shared, daily_paise=amount))

    resource('meta', 'm-abo', None, 'campaign', 'meta')
    resource('meta', 'm-set', 'm-abo', 'ad_set', 'meta', 'm-set-budget')
    resource('meta', 'm-ad', 'm-set', 'ad', 'meta')
    budget('meta', 'm-set-budget', 'm-set')
    resource('meta', 'm-cbo', None, 'campaign', 'meta', 'm-campaign-budget', 'multiple')
    resource('meta', 'm-mixed-set', 'm-cbo', 'ad_set', 'meta', scope='multiple')
    resource('meta', 'm-mixed-ad', 'm-mixed-set', 'ad', 'meta', scope='multiple')
    budget('meta', 'm-campaign-budget', 'm-cbo', amount=200000)
    for id in ('g-search-a', 'g-search-b'):
        resource('google', id, None, 'campaign', 'search', 'g-shared')
        resource('google', id+'-group', id, 'ad_group', 'search')
        resource('google', id+'-ad', id+'-group', 'ad', 'search')
    budget('google', 'g-shared', shared=True, amount=300000)
    resource('google', 'g-shopping', None, 'campaign', 'shopping', 'g-shopping-budget', 'multiple')
    resource('google', 'g-shopping-group', 'g-shopping', 'ad_group', 'shopping', scope='multiple')
    budget('google', 'g-shopping-budget')
    resource('google', 'g-pmax', None, 'campaign', 'pmax', 'g-pmax-budget', 'multiple')
    resource('google', 'g-assets', 'g-pmax', 'asset_group', 'pmax', scope='multiple')
    budget('google', 'g-pmax-budget', amount=400000)

    def report(platform, resource_id, start, revision, amount, reported='2026-10-29T20:00:00Z'):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day = datetime.fromisoformat(start).astimezone(ZoneInfo('Asia/Kolkata' if platform == 'meta' else 'UTC')).date().isoformat()
        return dict(platform=platform, account_id=f'{platform}-inr', resource_id=resource_id,
                    interval_start=start, source_day=day, revision=revision, reported_at=reported, currency='INR',
                    amount_rupees=amount if platform == 'meta' else None, cost_micros=amount if platform == 'google' else None)

    m1 = report('meta', 'm-ad', '2026-10-29T18:00:00Z', 1, '100.01')
    m2 = report('meta', 'm-mixed-ad', '2026-10-29T18:30:00Z', 1, '200.02')
    g1 = report('google', 'g-search-a-ad', '2026-10-29T18:00:00Z', 1, 500030000)
    g2 = report('google', 'g-search-b-ad', '2026-10-29T18:30:00Z', 1, 600040000)
    g3 = report('google', 'g-shopping-group', '2026-10-29T18:30:00Z', 1, 700050000)
    g4 = report('google', 'g-assets', '2026-10-29T18:30:00Z', 1, 800060000)
    pages = {'meta': [[m1, m2, m1]], 'google': [[g1, g2, g3, g4, g1]]}
    if corrected:
        pages['meta'].append([report('meta', 'm-ad', '2026-10-29T18:00:00Z', 2, '90.01', '2026-10-30T10:00:00Z'), m1,
                              report('meta', 'm-ad', '2026-10-29T19:00:00Z', 1, '10.07', '2026-10-30T10:00:00Z')])
        pages['google'].append([report('google', 'g-assets', '2026-10-29T18:30:00Z', 2, 0, '2026-10-30T10:00:00Z'), g4])
    return dict(version='ads-corrected-v1' if corrected else 'ads-initial-v1', seed=20261030,
                observed_at='2026-10-30T10:00:00Z' if corrected else '2026-10-29T20:00:00Z',
                scenario_clock='2026-10-30T10:00:00Z', accounts=accounts, resources=resources, budgets=budgets, pages=pages)


def main():
    for corrected in (False, True):
        source = build_fixture(corrected)
        raw = json.dumps(source, indent=2) + '\n'
        AdFixture.model_validate_json(raw)
        path = ROOT / 'fixtures' / (source['version'] + '.json')
        path.write_text(raw, encoding='utf-8')
        print(path.name)


if __name__ == '__main__':
    main()
