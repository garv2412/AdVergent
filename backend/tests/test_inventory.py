import json
from copy import deepcopy
from datetime import datetime,timedelta
from decimal import Decimal
import pytest
from pydantic import ValidationError
from advergent.inventory import InventoryFixture,assess,recommendations
from advergent.inventory_fixture import build_fixture
from advergent.attribution_fixture import build_fixture as attribution_fixture
from advergent.attribution import Mapping
from advergent.ads_fixture import build_fixture as ads_fixture
from advergent.ads import AdFixture,hierarchy
from advergent.operational import ROOT


def fixture(data=None):
    return InventoryFixture.model_validate_json(json.dumps(data or build_fixture()))


def features(f):
    result=[]
    for r in f.observations:
        d=r.model_dump(mode='json');n=int(r.variant_id[1:]);stock=max(0,r.available-r.merchant_reserve)
        velocity=Decimal(r.eligible_units)*86400/r.in_stock_seconds if r.in_stock_seconds else None
        result.append(dict(**d,product_id=f'p{n//6}',size=str(n%6),sellable_units=stock,
            daily_velocity=str(velocity) if velocity is not None else None,
            raw_days_of_cover=str(Decimal(stock)/velocity) if velocity else None))
    return result


def products(f,at=None):return assess(f,features(f),at or f.as_of)
def product(rows,id):return next(r for r in rows if r['product_id']==id)


def proposals(f,ps=None,at=None,current=True):
    ads=hierarchy(AdFixture.model_validate_json(json.dumps(ads_fixture())))
    maps=[Mapping.model_validate_json(json.dumps(m)) for m in attribution_fixture()['mappings']]
    return recommendations(f,ps or products(f),ads,maps,{'lines':[]},at or f.as_of,current)


def test_deterministic_inventory_source_and_a09_a10():
    assert json.loads((ROOT/'fixtures/inventory-v1.json').read_text())==build_fixture()
    f=fixture();ps=products(f)
    v=next(r for r in product(ps,'p1')['variants'] if r['variant_id']=='v6')
    assert v['sellable_units']==40 and v['committed']==3
    assert Decimal(v['daily_velocity'])==10 and Decimal(v['days_of_cover'])==4
    assert product(ps,'p1')['lead_days']==14 and product(ps,'p1')['throttle_eligible']
    assert product(ps,'p0')['unavailable_weight_bps']=='6000.0'
    assert product(ps,'p0')['pause_eligible']


@pytest.mark.parametrize('pid,status',[('p2','sparse'),('p3','missing_exposure'),('p4','zero_observed_demand')])
def test_uncertain_demand_never_produces_safe_cover(pid,status):
    p=product(products(fixture()),pid)
    assert p['days_of_cover'] is None and p['daily_velocity'] is None and p['uncertain']
    assert all(v['days_of_cover'] is None and v['demand_status']==status for v in p['variants'])
    assert not p['recovery_stock_eligible']


def test_unknown_lead_and_explicit_merchant_weights():
    f=fixture();assert product(products(f),'p5')['uncertain']
    for r in f.observations[:6]:r.in_stock_seconds=None;r.merchant_weight=1
    p=product(products(f),'p0')
    assert p['weight_source']=='merchant assumption' and Decimal(p['unavailable_weight_bps'])==5000
    assert p['days_of_cover'] is None


@pytest.mark.parametrize('day,quantity,status,expect',[(3,200,'confirmed',True),(5,200,'confirmed',False),(3,1,'confirmed',False),(3,200,'unconfirmed',False),(3,200,'cancelled',False)])
def test_receipts_must_bridge_depletion_and_sufficient_quantity(day,quantity,status,expect):
    f=fixture();r=f.receipts[0];r.expected_at=f.as_of+timedelta(days=day);r.quantity=quantity;r.status=status
    v=next(v for v in product(products(f),'p1')['variants'] if v['variant_id']=='v6')
    assert v['replenishment_sufficient']==expect
    assert v['sellable_units']==40


def test_stale_receipt_and_unbridged_gap_cannot_suppress_throttle():
    f=fixture();r=f.receipts[0];r.expected_at=f.as_of+timedelta(days=3);r.quantity=1000;r.observed_at=f.as_of-timedelta(seconds=901)
    assert product(products(f),'p1')['throttle_eligible']
    r.observed_at=f.as_of;r.expected_at=f.as_of+timedelta(days=5)
    assert product(products(f),'p1')['throttle_eligible']


def test_exact_freshness_boundary_and_no_replay_clock():
    f=fixture()
    assert product(products(f,f.as_of+timedelta(seconds=900)),'p0')['pause_eligible']
    p=product(products(f,f.as_of+timedelta(seconds=901)),'p0')
    assert not p['pause_eligible'] and p['risk']=='stale'
    assert all(r['eligibility']!='eligible' for r in proposals(f,at=f.as_of+timedelta(seconds=901)))


def test_a11_exact_mixed_scope_and_unsupported_budget_controls():
    f=fixture();rs={r['resource_id']:r for r in proposals(f)}
    assert rs['m-ad']['action']=='pause' and rs['m-ad']['eligibility']=='eligible'
    assert rs['g-assets']['eligibility']=='advisory' and any('mixed-product' in b for b in rs['g-assets']['blockers'])
    assert rs['m-mixed-ad']['eligibility']=='advisory'
    assert rs['g-shopping-group']['mapping']['status']=='ambiguous'
    assert rs['g-search-b-ad']['mapping']['status']=='unmapped'
    assert all(r['approval_required'] and not r['mutation_enabled'] for r in rs.values())
    assert all(r['eligibility']!='eligible' for r in proposals(f,current=False))
    assert all(r['mapping']['status']=='unmapped' for r in proposals(f,at=datetime.fromisoformat('2027-01-01T00:00:00+00:00')))


@pytest.mark.parametrize('owner,evidence,blockers,eligible',[('AdVergent','pause-1',[],True),('merchant','pause-1',[],False),('unknown','pause-1',[],False),('AdVergent',None,[],False),('AdVergent','pause-1',['destination issue'],False)])
def test_recovery_only_prior_advergent_pause_with_cleared_conditions(owner,evidence,blockers,eligible):
    f=fixture()
    for r in f.observations[:6]:r.available=40;r.eligible_units=28
    state=next(s for s in f.resource_states if s.resource_id=='m-ad')
    state.status='paused';state.paused_by=owner;state.pause_evidence_id=evidence;state.blockers=blockers
    rs={r['resource_id']:r for r in proposals(f)}
    assert rs['m-ad']['action']==('recovery' if owner=='AdVergent' and evidence else 'advisory')
    assert (rs['m-ad']['eligibility']=='eligible')==eligible
    f.observations[0].available=0
    # 16.7% missing weight clears size threshold, but low-cover variant remains a blocker.
    assert next(r for r in proposals(f) if r['resource_id']=='m-ad')['eligibility']!='eligible'


def test_invalid_inventory_evidence_rejected():
    for mutation in ('duplicate','exposure','future','zero-exposure','lead'):
        d=deepcopy(build_fixture())
        if mutation=='duplicate':d['observations'].append(d['observations'][0])
        elif mutation=='exposure':d['observations'][0]['in_stock_seconds']=29*86400
        elif mutation=='future':d['observations'][0]['stock_observed_at']='2027-01-01T00:00:00Z'
        elif mutation=='lead':d['lead_days']['p0']=-1
        else:d['observations'][0]['in_stock_seconds']=0
        with pytest.raises(ValidationError):fixture(d)


def test_exact_resource_throttle_capabilities_and_shared_budget_abstention():
    f=fixture();ads=hierarchy(AdFixture.model_validate_json(json.dumps(ads_fixture())))
    template=attribution_fixture()['mappings'][0]
    maps=[]
    for rid,platform in (('m-set','meta'),('g-search-a','google')):
        m=deepcopy(template);m.update(id=rid,resource_id=rid,platform=platform,account_id=platform+'-inr',products=['p1'])
        maps.append(Mapping.model_validate_json(json.dumps(m)))
    rs={r['resource_id']:r for r in recommendations(f,products(f),ads,maps,{'lines':[]},f.as_of,True)}
    assert rs['m-set']['action']=='throttle' and rs['m-set']['eligibility']=='eligible'
    assert rs['g-search-a']['action']=='throttle' and rs['g-search-a']['eligibility']=='advisory'
    assert any('unshared' in b for b in rs['g-search-a']['blockers'])


def test_weight_boundary_and_partial_receipt_sequence():
    f=fixture()
    for i,r in enumerate(f.observations[:6]):r.in_stock_seconds=None;r.merchant_weight=1999 if i<3 else 2001
    p=product(products(f),'p0')
    assert Decimal(p['unavailable_weight_bps'])<6000 and not p['pause_eligible']
    f=fixture();r=f.receipts[0];r.expected_at=f.as_of+timedelta(days=3);r.quantity=20
    later=r.model_copy(update=dict(id='second',expected_at=f.as_of+timedelta(days=5),quantity=110))
    f.receipts.append(later)
    v=lambda:next(v for v in product(products(f),'p1')['variants'] if v['variant_id']=='v6')
    assert v()['replenishment_sufficient']
    later.expected_at=f.as_of+timedelta(days=7)
    assert not v()['replenishment_sufficient']


def test_overdue_receipt_is_not_assumed_received():
    f=fixture();r=f.receipts[0];r.expected_at=f.as_of+timedelta(seconds=60);r.quantity=200
    p=product(products(f,f.as_of+timedelta(seconds=120)),'p1')
    v=next(v for v in p['variants'] if v['variant_id']=='v6')
    assert not v['replenishment_sufficient'] and v['qualified_receipt_ids']==[]


@pytest.mark.parametrize('contribution,expected',[(1000,'5000'),(-1000,'-5000'),(None,None)])
def test_finance_daily_context_keeps_unknown_and_negative_contribution(contribution,expected):
    f=fixture();ads=hierarchy(AdFixture.model_validate_json(json.dumps(ads_fixture())))
    maps=[Mapping.model_validate_json(json.dumps(m)) for m in attribution_fixture()['mappings']]
    line=dict(expected_before_ads_paise=contribution,delivered_paise=10000,evidence=dict(original_line=dict(variant_id='v0',quantity=2)))
    rs=recommendations(f,products(f),ads,maps,{'lines':[line]},f.as_of,True)
    impact=next(r for r in rs if r['resource_id']=='m-ad')['impact']
    assert impact['daily_contribution_context_paise']==expected
    assert impact['expected_contribution_paise']==contribution
    assert impact['delivered_sample_units']==2
