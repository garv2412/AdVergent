"""Immutable finance inputs and deterministic exact-paise allocation. No ad actions."""
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5
from typing import Literal
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import text
from .commerce import SourceModel, canonical
from .operational import ROOT


class OrderFinance(SourceModel):
    order_id: str
    delivered_at: AwareDatetime | None
    shipping_revenue_paise: int = Field(ge=0)
    forward_paise: int | None = Field(ge=0)
    payment_fee_paise: int | None = Field(ge=0)
    reverse_paise: int | None = Field(ge=0)
    other_paise: int | None = Field(ge=0)
    failed_loss_paise: int | None = Field(ge=0)
    cash_received_paise: int = Field(ge=0)
    cash_refunded_paise: int = Field(ge=0)
    settled_at: AwareDatetime | None
    status: Literal['actual', 'estimated', 'missing']
    source: str = Field(min_length=1)
    effective_at: AwareDatetime

    @model_validator(mode='after')
    def coverage(self):
        missing = any(getattr(self, k) is None for k in ('forward_paise','payment_fee_paise','reverse_paise','other_paise','failed_loss_paise'))
        if missing != (self.status == 'missing'):
            raise ValueError('Expense coverage must be explicit')
        if (self.cash_received_paise > 0 or self.cash_refunded_paise > 0) and self.settled_at is None:
            raise ValueError('Actual cash needs settlement evidence')
        return self


class Correction(SourceModel):
    line_id: str
    unit_cost_paise: int = Field(ge=0)
    effective_at: AwareDatetime
    source: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    status: Literal['actual', 'estimated']


class Recovery(SourceModel):
    refund_id: str
    recovered_value_paise: int | None = Field(ge=0)
    source: str = Field(min_length=1)
    effective_at: AwareDatetime


class FinanceFixture(SourceModel):
    version: str = Field(min_length=1, max_length=100)
    observed_at: AwareDatetime
    period_start: AwareDatetime
    as_of: AwareDatetime
    reserve_window_days: int = Field(ge=0, le=365)
    return_probability_bps: int = Field(ge=0, le=10000)
    recovery_bps: int = Field(ge=0, le=10000)
    future_return_fee_paise: int = Field(ge=0)
    reserve_source: str = Field(min_length=1)
    orders: list[OrderFinance]
    corrections: list[Correction]
    recoveries: list[Recovery]

    @model_validator(mode='after')
    def valid(self):
        if not self.period_start < self.as_of <= self.observed_at <= datetime.now(timezone.utc):
            raise ValueError('Invalid financial interval')
        for rows, key in ((self.orders,'order_id'),(self.corrections,'line_id'),(self.recoveries,'refund_id')):
            if len({getattr(r,key) for r in rows}) != len(rows):
                raise ValueError('Duplicate financial evidence')
        return self


def allocate(amount, weights):
    """Largest-remainder allocation; lexical line IDs break equal remainders."""
    if amount is None:
        return {k: None for k in weights}
    if not weights or any(v < 0 for v in weights.values()):
        raise ValueError('Invalid allocation weights')
    weights = weights if sum(weights.values()) else {k: 1 for k in weights}
    total = sum(weights.values())
    result = {k: amount*v//total for k,v in weights.items()}
    for k in sorted(weights, key=lambda k: (-(amount*weights[k] % total), k))[:amount-sum(result.values())]:
        result[k] += 1
    return result


def normalize(f, records):
    groups = {k: {r.id:r.data for r in rows} for k,rows in records.items()}
    orders, lines, refunds = (groups[k] for k in ('orders','lines','refunds'))
    evidence = {r.order_id:r for r in f.orders}
    corrections = {r.line_id:r for r in f.corrections}
    recovery = {r.refund_id:r for r in f.recoveries}
    if set(evidence) != set(orders) or not set(corrections) <= set(lines) or set(recovery) != set(refunds):
        raise ValueError('Incomplete or unknown financial evidence')
    def dt(v): return datetime.fromisoformat(v)
    def inside(v): return f.period_start <= v <= f.as_of
    by_order = {k: {} for k in orders}
    for key,l in lines.items(): by_order[l['order_id']][key] = l['quantity']*l['unit_price_paise']-l['discount_paise']
    result = []
    for oid, order in orders.items():
        e = evidence[oid]
        placed = dt(order['placed_at'])
        if placed < f.period_start or placed > f.as_of:
            raise ValueError('Finance snapshot must include complete order history for this interval')
        if not inside(e.effective_at) or (e.settled_at and not inside(e.settled_at)):
            raise ValueError('Financial evidence outside interval')
        delivered = order['fulfillment_status'] == 'delivered'
        if delivered != (e.delivered_at is not None): raise ValueError('Delivery evidence mismatch')
        if e.delivered_at and not placed <= e.delivered_at <= f.as_of: raise ValueError('Invalid delivery time')
        weights = by_order[oid]
        if not weights: raise ValueError('Order has no financial lines')
        expenses = None if e.status == 'missing' else e.forward_paise+e.payment_fee_paise+e.reverse_paise+e.other_paise
        alloc = {k:allocate(v,weights) for k,v in dict(shipping=e.shipping_revenue_paise, variable=expenses, loss=e.failed_loss_paise, cash=e.cash_received_paise-e.cash_refunded_paise).items()}
        # Collection receivable is gross of explicit tax; never equated with revenue.
        gross_due = sum(weights.values()) + sum(l['tax_paise'] for l in lines.values() if l['order_id']==oid) + e.shipping_revenue_paise
        refund_gross = sum(r['merchandise_paise']+r['tax_paise'] for r in refunds.values() if r['order_id']==oid and dt(r['refunded_at']) <= f.as_of)
        due = max(0, gross_due-refund_gross-e.cash_received_paise+e.cash_refunded_paise) if delivered and order['payment_method']=='cod' else 0
        unsettled = allocate(due, weights)
        for lid, placed_value in sorted(weights.items()):
            l = lines[lid]
            cost, status = l['unit_cost_paise'], l['cost_status']
            correction = corrections.get(lid)
            if correction:
                if correction.effective_at > placed: raise ValueError('Historical correction not effective for line')
                cost, status = correction.unit_cost_paise, correction.status
            rs = [(rid,r) for rid,r in refunds.items() if r['line_id']==lid and dt(r['refunded_at']) <= f.as_of]
            if delivered and any(dt(r['refunded_at']) < e.delivered_at for _,r in rs):
                raise ValueError('Refund cannot reverse unrecognized merchandise')
            recovered = 0
            for rid,r in rs:
                ev = recovery[rid]
                if ev.effective_at < dt(r['refunded_at']) or ev.effective_at > f.as_of: raise ValueError('Invalid recovery date')
                if not delivered:
                    # Payment reversal of an unrecognized sale cannot create COGS recovery.
                    continue
                if ev.recovered_value_paise is None or cost is None:
                    recovered = None
                elif ev.recovered_value_paise > cost*r['quantity']:
                    raise ValueError('Recovery exceeds historical product cost')
                elif recovered is not None: recovered += ev.recovered_value_paise
            remaining = l['quantity']-sum(r['quantity'] for _,r in rs)
            exposed = remaining if delivered and f.as_of < e.delivered_at+timedelta(days=f.reserve_window_days) else 0
            # Reserve replaces only returned units; remaining units retain exposure.
            if not exposed or not f.return_probability_bps:
                reserve = 0
            elif cost is None:
                reserve = None
            else:
                remaining_sales = allocate(placed_value, {'exposed':exposed,'other':l['quantity']-exposed})['exposed']
                loss = max(0, remaining_sales - cost*exposed*f.recovery_bps//10000 + f.future_return_fee_paise*exposed)
                reserve = (loss*f.return_probability_bps+5000)//10000
            events=[]
            def event(key, at, sales=0, product=0, variable=0, cash=0):
                from zoneinfo import ZoneInfo
                events.append(dict(id=lid+':'+key, line_id=lid, order_id=oid,
                    occurred_at=at.isoformat(), transaction_day=at.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat(),
                    acquisition_day=placed.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat(),
                    net_sales_paise=sales, net_product_cost_paise=product, variable_paise=variable, cash_paise=cash))
            if delivered: event('delivery', e.delivered_at, sales=placed_value, product=None if cost is None else cost*l['quantity'])
            event('expense',e.effective_at,sales=alloc['shipping'][lid],product=alloc['loss'][lid],variable=alloc['variable'][lid])
            if e.settled_at: event('cash',e.settled_at,cash=alloc['cash'][lid])
            for rid,r in rs:
                value=recovery[rid].recovered_value_paise
                event('refund:'+rid,dt(r['refunded_at']),sales=-r['merchandise_paise'] if delivered else 0)
                event('recovery:'+rid,recovery[rid].effective_at,product=(None if value is None or cost is None else -value) if delivered else 0)
            result.append(dict(events=events,line_id=lid, order_id=oid, placed_paise=placed_value,
                delivered_paise=placed_value if delivered else 0, refunded_paise=sum(r['merchandise_paise'] for _,r in rs) if delivered else 0,
                shipping_paise=alloc['shipping'][lid], sold_cost_paise=(None if cost is None else cost*l['quantity']) if delivered else 0,
                recovered_paise=recovered, failed_loss_paise=alloc['loss'][lid], variable_paise=alloc['variable'][lid],
                reserve_paise=reserve, cash_paise=alloc['cash'][lid], unsettled_cod_paise=unsettled[lid],
                cost_status=status if delivered else 'actual', expense_status=e.status, exposed_units=exposed,
                evidence=dict(original_line=l, correction=correction.model_dump(mode='json') if correction else None,
                    order=e.model_dump(mode='json'), refunds=[dict(id=rid, **r, recovery_evidence=recovery[rid].model_dump(mode='json')) for rid,r in rs])))
    return result


def import_finance(store, analytics, fixture_path=ROOT / 'fixtures/finance-v1.json'):
    raw = fixture_path.read_bytes()
    f = FinanceFixture.model_validate_json(raw)
    digest = hashlib.sha256(raw).hexdigest()
    with store.engine.connect() as lock:
        acquired=[]
        try:
            for number in (17012028,17012030,17012031,17012032):
                if not lock.execute(text('SELECT pg_try_advisory_lock(:n)'),dict(n=number)).scalar():
                    raise RuntimeError('Dependent import already running')
                acquired.append(number)
            lock.commit()
            attr = store.attribution_publication()[0]
            if not attr: raise RuntimeError('Publish attribution first')
            commerce, ads = store.commerce_publication()[0],store.ad_publication()[0]
            if not commerce or not ads or commerce['id'] != attr['commerce_id'] or ads['id'] != attr['ads_id']:
                raise RuntimeError('Attribution inputs changed; republish attribution first')
            cid, aid, tid = str(attr['commerce_id']),str(attr['ads_id']),str(attr['id'])
            run=str(uuid5(NAMESPACE_URL,'finance-v3:'+digest+tid))
            attempt=str(uuid4())
            observed=min(f.observed_at,attr['observed_at'])
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE finance_attempts SET status='failed',error_code='worker_interrupted',finished_at=now() WHERE status='running'"))
                conn.execute(text('INSERT INTO finance_runs(id,version,fixture_hash,commerce_id,ads_id,attribution_id,configuration,observed_at) VALUES (:id,:version,:hash,:cid,:aid,:tid,CAST(:config AS jsonb),:observed) ON CONFLICT(id) DO NOTHING'),dict(id=run,version=f.version,hash=digest,cid=cid,aid=aid,tid=tid,config=raw.decode(),observed=observed))
                conn.execute(text("INSERT INTO finance_attempts(id,run_id,status) VALUES (:id,:run,'running')"),dict(id=attempt,run=run))
            try:
                records={k:analytics.commerce_records(cid,k,limit=None) for k in ('orders','lines','refunds')}
                rows=normalize(f,records)
                if any(not f.period_start <= datetime.fromisoformat(r['interval_start']) + timedelta(minutes=30) <= f.as_of for r in analytics.ad_data(aid)['reports']):
                    raise ValueError('Spend outside financial interval')
                analytics.load_finance(run,cid,aid,tid,rows)
                analytics.verify_finance(run,rows)
                with store.engine.begin() as conn:
                    conn.execute(text('UPDATE finance_runs SET finished_at=COALESCE(finished_at,now()) WHERE id=:id'),dict(id=run))
                    conn.execute(text("UPDATE finance_attempts SET status='succeeded',finished_at=now() WHERE id=:id"),dict(id=attempt))
                    conn.execute(text('INSERT INTO finance_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'),dict(run=run))
            except Exception:
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE finance_attempts SET status='failed',error_code='finance_failed',finished_at=now() WHERE id=:id"),dict(id=attempt))
                raise RuntimeError('Finance failed; prior publication preserved') from None
            return run
        finally:
            for number in reversed(acquired): lock.execute(text('SELECT pg_advisory_unlock(:n)'),dict(n=number))
            lock.commit()
