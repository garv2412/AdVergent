"""Reproducible synthetic warehouse counters, exposure, receipts and state evidence."""
import json
from .operational import ROOT
from .inventory import InventoryFixture


def build_fixture():
    commerce=json.loads((ROOT/'fixtures/commerce-v1.json').read_text())
    stock=[r for r in commerce['snapshot'] if r['kind']=='inventory']
    at='2026-10-30T10:00:00Z'
    observations=[]
    for r in stock:
        d=r['data'];n=int(d['variant_id'][1:])
        units=28
        if n<6:units=[56,56,56,28,28,56][n]  # 60% observed demand unavailable.
        if 6<=n<12:units=280 if n==6 else 28
        if 12<=n<18:units=2
        if 24<=n<30:units=0
        observations.append(dict(variant_id=d['variant_id'],available=40 if n==6 else d['available'],committed=d['committed'],merchant_reserve=0,
            stock_observed_at=at,eligible_units=units,in_stock_seconds=None if 18<=n<24 else 28*86400,
            source='simulated warehouse stock count and 28-day eligible fulfilled-unit/exposure counters; not inferred from current stock',merchant_weight=None))
    resources=json.loads((ROOT/'fixtures/ads-corrected-v1.json').read_text())['resources']
    states=[dict(platform=r['platform'],account_id=r['account_id'],resource_id=r['id'],status=r['status'],paused_by=None,pause_evidence_id=None,
        observed_at=at,blockers=[],source='simulated resource observation; no platform write') for r in resources]
    f=dict(version='inventory-v1',as_of=at,window_start='2026-10-02T10:00:00Z',observed_at=at,observations=observations,
        receipts=[dict(id='late-v6',variant_id='v6',quantity=100,expected_at='2026-11-05T10:00:00Z',observed_at=at,status='confirmed',source='simulated supplier confirmation; arrives after four-day stockout')],
        resource_states=states,lead_days={f'p{i}':None if i==5 else 14 for i in range(30)},lead_source='synthetic configuration assumption; not merchant-confirmed',
        safety_days=3,min_units=10,min_exposure_days=7,throttle_days=5,recovery_days=7,pause_unavailable_bps=6000,recovery_unavailable_bps=4000,freshness_seconds=900)
    return InventoryFixture.model_validate_json(json.dumps(f)).model_dump(mode='json')


if __name__=='__main__':
    (ROOT/'fixtures/inventory-v1.json').write_text(json.dumps(build_fixture(),indent=2)+'\n',encoding='utf-8')
