"""Generate explicit synthetic fee, settlement and recovery evidence, not results."""
import json
from datetime import datetime
from .operational import ROOT


def build_fixture():
    commerce=json.loads((ROOT/'fixtures/commerce-v1.json').read_text())
    groups={k:{} for k in ('orders','lines','refunds')}
    for r in commerce['snapshot']:
        if r['kind'] in groups: groups[r['kind']][r['id']]=r['data']
    orders=[]
    for oid,o in groups['orders'].items():
        ls=[l for l in groups['lines'].values() if l['order_id']==oid]
        rs=[r for r in groups['refunds'].values() if r['order_id']==oid]
        gross=sum(l['quantity']*l['unit_price_paise']-l['discount_paise']+l['tax_paise'] for l in ls)
        captured=gross if o['payment_method']=='prepaid' else 0
        paid_refund=sum(r['merchandise_paise']+r['tax_paise'] for r in rs) if captured else 0
        status=o['fulfillment_status']
        orders.append(dict(order_id=oid,delivered_at=o['placed_at'] if status=='delivered' else None,
            shipping_revenue_paise=0,forward_paise=7001 if status in ('delivered','shipped','rto') else 0,
            payment_fee_paise=1500 if captured else 2000 if status=='delivered' else 0,
            reverse_paise=5000 if rs or status=='rto' else 0,other_paise=500 if status=='cancelled' else 0,
            failed_loss_paise=0,cash_received_paise=captured,cash_refunded_paise=paid_refund,
            settled_at=commerce['observed_at'] if captured else None,
            status='actual',source='synthetic-fulfillment-settlement-ledger',effective_at=commerce['observed_at']))
    recoveries=[]
    for rid,r in groups['refunds'].items():
        cost=groups['lines'][r['line_id']]['unit_cost_paise']
        value=None if r['recovery']=='unknown' or cost is None else cost*r['quantity'] if r['recovery']=='intact' else cost*r['quantity']//5 if r['recovery']=='damaged' else 0
        recoveries.append(dict(refund_id=rid,recovered_value_paise=value,source='synthetic-warehouse-assessment',effective_at=r['refunded_at']))
    ads=json.loads((ROOT/'fixtures/ads-corrected-v1.json').read_text())
    placed=[o['placed_at'] for o in groups['orders'].values()]
    return dict(version='finance-v1',observed_at=ads['observed_at'],period_start=min(placed,key=datetime.fromisoformat),as_of=ads['observed_at'],
        reserve_window_days=30,return_probability_bps=1000,recovery_bps=8000,future_return_fee_paise=5000,
        reserve_source='synthetic assumption; not calibrated',orders=orders,corrections=[],recoveries=recoveries)


if __name__=='__main__':
    path=ROOT/'fixtures/finance-v1.json'
    path.write_text(json.dumps(build_fixture(),sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    print('Wrote '+path.name)
