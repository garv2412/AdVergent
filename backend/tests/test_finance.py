"""Independent hand-calculated finance cases, source validation and rounding."""
import json
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from advergent.finance import FinanceFixture, normalize, allocate
from advergent.finance_fixture import build_fixture
from advergent.finance_sql import ratio
from advergent.operational import ROOT


def scenario():
    stamp='2026-10-20T00:00:00+00:00'
    f=dict(version='golden',observed_at='2026-10-29T18:00:00+00:00',period_start='2026-05-01T00:00:00+00:00',as_of='2026-10-29T18:00:00+00:00',reserve_window_days=30,return_probability_bps=1000,recovery_bps=8000,future_return_fee_paise=5000,reserve_source='synthetic assumption',orders=[dict(order_id='o',delivered_at=stamp,shipping_revenue_paise=0,forward_paise=20000,payment_fee_paise=5000,reverse_paise=0,other_paise=0,failed_loss_paise=0,cash_received_paise=420000,cash_refunded_paise=0,settled_at=stamp,status='actual',source='ledger',effective_at=stamp)],corrections=[],recoveries=[])
    def record(id,data): return SimpleNamespace(id=id,data=data)
    records=dict(orders=[record('o',dict(placed_at=stamp,fulfillment_status='delivered',payment_method='prepaid'))],lines=[record('a',dict(order_id='o',variant_id='v',quantity=2,unit_price_paise=100000,discount_paise=0,tax_paise=10000,unit_cost_paise=55000,cost_status='actual',cost_source='historic',cost_effective_at=stamp)),record('b',dict(order_id='o',variant_id='v2',quantity=1,unit_price_paise=200000,discount_paise=0,tax_paise=10000,unit_cost_paise=110000,cost_status='actual',cost_source='historic',cost_effective_at=stamp))],refunds=[])
    return f,records


def test_a01_golden_exact_paise_and_ratios():
    f,r=scenario();rows=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    assert sum(l['delivered_paise'] for l in rows)==400000
    assert sum(l['sold_cost_paise'] for l in rows)==220000
    assert sum(l['variable_paise'] for l in rows)==25000
    before=sum(l['delivered_paise']-l['sold_cost_paise']-l['variable_paise'] for l in rows)
    assert before==155000 and before-100000==55000
    # Contract's INR 500 variable-cost case.
    f['orders'][0]['forward_paise']=45000
    rows=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    before=sum(l['delivered_paise']-l['sold_cost_paise']-l['variable_paise'] for l in rows)
    assert before==130000 and before-100000==30000
    assert ratio(before,100000)=='1.3' and ratio(400000,100000)=='4'
    assert ratio(-100,100)=='-1' and ratio(100,0) is None and ratio(None,100) is None


def test_a03_effective_correction_does_not_rewrite_original_or_other_lines():
    f,r=scenario(); original=deepcopy(r)
    f['corrections']=[dict(line_id='a',unit_cost_paise=60000,effective_at='2026-10-01T00:00:00Z',source='explicit invoice correction',reason='correct historical invoice',status='actual')]
    rows=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    assert rows[0]['sold_cost_paise']==120000 and rows[1]['sold_cost_paise']==110000
    assert rows[0]['evidence']['original_line']['unit_cost_paise']==55000
    assert r['lines'][0].data==original['lines'][0].data
    f['corrections'][0]['effective_at']='2026-10-21T00:00:00Z'
    with pytest.raises(ValueError,match='not effective'): normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)


def test_a04_partial_return_recovery_and_reserve_replacement():
    f,r=scenario()
    initial=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)[0]
    # 10% * (2000 revenue - 880 recoverable cost + 100 return fee).
    assert initial['reserve_paise']==12200 and initial['exposed_units']==2
    r['refunds']=[SimpleNamespace(id='refund',data=dict(order_id='o',line_id='a',quantity=1,merchandise_paise=100000,tax_paise=5000,refunded_at='2026-10-25T00:00:00Z',recovery='intact'))]
    f['recoveries']=[dict(refund_id='refund',recovered_value_paise=55000,source='warehouse inspection',effective_at='2026-10-25T00:00:00Z')]
    f['orders'][0]['reverse_paise']=5000
    f['orders'][0]['cash_refunded_paise']=105000
    row=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)[0]
    assert row['refunded_paise']==100000 and row['recovered_paise']==55000
    assert row['reserve_paise']==6100 and row['exposed_units']==1
    assert row['variable_paise']==15000
    # Full outcome removes all reserve; refund does not infer recovery.
    r['refunds'][0].data.update(quantity=2,merchandise_paise=200000)
    f['recoveries'][0]['recovered_value_paise']=None
    row=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)[0]
    assert row['reserve_paise']==0 and row['recovered_paise'] is None


@pytest.mark.parametrize('status,method,cash', [('rto','cod',0),('shipped','prepaid',420000),('cancelled','prepaid',420000)])
def test_a05_undelivered_and_rto_no_sales_or_sold_cogs(status,method,cash):
    f,r=scenario();r['orders'][0].data.update(fulfillment_status=status,payment_method=method)
    f['orders'][0].update(delivered_at=None,cash_received_paise=cash,failed_loss_paise=3000,reverse_paise=5000)
    rows=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    assert sum(l['delivered_paise'] for l in rows)==sum(l['sold_cost_paise'] for l in rows)==0
    assert sum(l['failed_loss_paise'] for l in rows)==3000
    assert sum(l['variable_paise'] for l in rows)==30000
    assert sum(l['cash_paise'] for l in rows)==cash


def test_a06_cod_delivered_separate_cash_and_a08_missing_cost():
    f,r=scenario();r['orders'][0].data['payment_method']='cod'
    f['orders'][0].update(cash_received_paise=0,settled_at=None)
    r['lines'][0].data.update(unit_cost_paise=None,cost_status='missing')
    rows=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    assert sum(l['delivered_paise'] for l in rows)==400000
    assert sum(l['unsettled_cod_paise'] for l in rows)==420000
    assert rows[0]['sold_cost_paise'] is None and rows[0]['reserve_paise'] is None
    assert sum(l['cash_paise'] for l in rows)==0
    f['as_of']='2026-11-25T00:00:00Z';f['observed_at']=f['as_of']
    # Exercise maturity without future-source validation by copying the validated model.
    f0,r0=scenario();model=FinanceFixture.model_validate_json(json.dumps(f0)).model_copy(update={'as_of':datetime(2026,11,25,tzinfo=timezone.utc)})
    assert all(l['reserve_paise']==0 for l in normalize(model,r0))


def test_rounding_zero_weights_and_unknown_expense():
    assert allocate(1,{'b':1,'a':1})=={'b':0,'a':1}
    assert allocate(3,{'b':0,'a':0})=={'b':1,'a':2}
    assert sum(allocate(-3,{'b':1,'a':1}).values())==-3
    assert allocate(None,{'a':1})=={'a':None}
    f,r=scenario();f['orders'][0].update(forward_paise=None,status='missing')
    assert all(l['variable_paise'] is None for l in normalize(FinanceFixture.model_validate_json(json.dumps(f)),r))


def test_source_integrity_and_deterministic_generator():
    assert json.loads((ROOT/'fixtures/finance-v1.json').read_text())==build_fixture()
    f,r=scenario();f['orders'].append(f['orders'][0])
    with pytest.raises(ValueError,match='Duplicate'): FinanceFixture.model_validate_json(json.dumps(f))
    f,r=scenario();f['orders']=[]
    with pytest.raises(ValueError,match='Incomplete'):normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)


def test_estimated_provenance_and_invalid_recovery_or_expense_dates():
    f,r=scenario();f['orders'][0]['status']='estimated';r['lines'][0].data['cost_status']='estimated'
    rows=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    assert rows[0]['cost_status']=='estimated' and rows[0]['expense_status']=='estimated'
    assert rows[0]['evidence']['original_line']['cost_source']=='historic'
    f['orders'][0]['effective_at']='2026-04-01T00:00:00Z'
    with pytest.raises(ValueError,match='outside interval'):normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    f,r=scenario();r['orders'][0].data['fulfillment_status']='shipped';f['orders'][0]['delivered_at']=None
    r['refunds']=[SimpleNamespace(id='refund',data=dict(order_id='o',line_id='a',quantity=1,merchandise_paise=100000,tax_paise=5000,refunded_at='2026-10-25T00:00:00Z',recovery='intact'))]
    f['recoveries']=[dict(refund_id='refund',recovered_value_paise=55000,source='warehouse',effective_at='2026-10-25T00:00:00Z')]
    # An undelivered payment refund changes cash, never recognized sales/COGS.
    f['orders'][0]['cash_refunded_paise']=105000
    undelivered=normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
    assert sum(l['refunded_paise'] for l in undelivered)==0
    assert sum(l['recovered_paise'] for l in undelivered)==0
    assert sum(l['cash_paise'] for l in undelivered)==315000
    r['orders'][0].data['fulfillment_status']='delivered';f['orders'][0]['delivered_at']='2026-10-20T00:00:00Z'
    f['recoveries'][0]['recovered_value_paise']=55001
    with pytest.raises(ValueError,match='exceeds historical'):normalize(FinanceFixture.model_validate_json(json.dumps(f)),r)
