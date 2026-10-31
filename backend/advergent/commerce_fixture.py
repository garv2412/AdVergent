"""Deterministic source inputs, never precomputed analytical outputs."""
import copy
import json
import random
from datetime import datetime, timedelta, timezone
from .operational import ROOT


def build_fixture(order_count=3000):
    rng = random.Random(20261030)
    clock = datetime(2026, 10, 29, 18, 0, tzinfo=timezone.utc)
    stamp = clock.isoformat()
    records = []
    def add(kind, key, data, at=stamp):
        record = dict(kind=kind, id=key, updated_at=at, deleted=False, data=data)
        records.append(record)
        return record
    for i in range(30):
        add('products', f'p{i}', dict(title='<script>untrusted catalog text</script>' if i == 0 else f'Cotton style {i:02}', status='archived' if i == 29 else 'active'))
        for j, size in enumerate(('S', 'M', 'L', 'XL', 'XXL', 'XXXL')):
            n = i * 6 + j
            cost = None if n == 0 else 32000 + i * 100
            add('variants', f'v{n}', dict(product_id=f'p{i}', sku=f'APP-{n:04}', size=size, color='indigo', price_paise=80000 + i * 1000, unit_cost_paise=cost, cost_status='missing' if cost is None else 'actual', cost_source='synthetic-merchant-cost', cost_effective_at=(clock-timedelta(days=180)).isoformat()))
            # Available already excludes commitments; the mirror preserves both.
            add('inventory', f'i{n}', dict(variant_id=f'v{n}', location_id='warehouse-1', available=0 if n < 3 else rng.randint(5, 100), committed=3, merchant_reserve=0))
    for i in range(1000):
        add('customers', f'c{i}', dict(synthetic_key=f'synthetic-customer-{i}'))
    for i in range(order_count):
        placed = (clock - timedelta(days=179 - i % 180, minutes=i % 1000)).isoformat()
        status = ('delivered', 'delivered', 'delivered', 'shipped', 'rto', 'cancelled', 'unfulfilled')[i % 7]
        cod = i % 3 == 0
        add('orders', f'o{i}', dict(customer_id=f'c{i % 1000}', currency='INR', placed_at=placed, payment_method='cod' if cod else 'prepaid', payment_status='unremitted' if cod and status == 'delivered' else 'pending' if cod else 'paid', fulfillment_status=status))
        for j in range(2 if i % 5 == 0 else 1):
            variant = (i + j) % 180
            cost = None if variant == 0 else 30000 + (variant // 6) * 100
            # Historical costs intentionally differ from today's catalog costs.
            add('lines', f'l{i}-{j}', dict(order_id=f'o{i}', variant_id=f'v{variant}', quantity=2 if i % 11 == 0 else 1, unit_price_paise=80000 + (variant // 6) * 1000, discount_paise=1000 if i % 9 == 0 else 0, tax_paise=4000, unit_cost_paise=cost, cost_status='missing' if cost is None else 'actual', cost_source='synthetic-order-cost-snapshot', cost_effective_at=placed))
        if i % 21 == 0:
            add('refunds', f'r{i}', dict(order_id=f'o{i}', line_id=f'l{i}-0', quantity=1, merchandise_paise=70000, tax_paise=3500, refunded_at=stamp, recovery=('intact', 'damaged', 'unknown')[i // 21 % 3]))
    deliveries = [dict(delivery_id=f'd{index}', record=copy.deepcopy(record)) for index, record in enumerate(records)]
    # Missed refund, stock change and catalog change are repaired by reconciliation.
    missed = {('refunds', 'r0'), ('inventory', 'i0'), ('products', 'p2')}
    deliveries = [d for d in deliveries if (d['record']['kind'], d['record']['id']) not in missed]
    old = copy.deepcopy(next(r for r in records if r['kind'] == 'inventory' and r['id'] == 'i1'))
    old['updated_at'] = (clock - timedelta(hours=1)).isoformat()
    old['data']['available'] = 999
    deliveries.append(dict(delivery_id='late-old-stock', record=old))
    deliveries.append(copy.deepcopy(deliveries[0]))
    ghost = dict(kind='products', id='deleted-product', updated_at=(clock-timedelta(hours=2)).isoformat(), deleted=False, data=dict(title='Deleted style', status='active'))
    deliveries.append(dict(delivery_id='ghost-create', record=ghost))
    tombstone = dict(kind='products', id='deleted-product', updated_at=stamp, deleted=True, data={})
    deliveries.append(dict(delivery_id='ghost-delete', record=tombstone))
    deliveries.append(dict(delivery_id='ghost-late-create', record=copy.deepcopy(ghost)))
    # A missed delete must be swept by the complete source snapshot.
    absent = copy.deepcopy(ghost)
    absent['id'] = 'missed-delete'
    deliveries.append(dict(delivery_id='missed-delete-create', record=absent))
    return dict(version='commerce-v1', seed=20261030, scenario_clock=stamp, observed_at=stamp, pages=[deliveries[i:i+500] for i in range(0, len(deliveries), 500)], snapshot=records)


if __name__ == '__main__':
    path = ROOT / 'fixtures/commerce-v1.json'
    path.write_text(json.dumps(build_fixture(), sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {path.name}: {path.stat().st_size} bytes')
