"""Inventory evidence and advisory policy. No advertising write capability."""
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import text
from .commerce import SourceModel
from .attribution import Identity, resolve_mapping
from .operational import ROOT


class Observation(SourceModel):
    variant_id: str
    available: int = Field(ge=0)
    committed: int = Field(ge=0)
    merchant_reserve: int = Field(ge=0)
    stock_observed_at: AwareDatetime
    eligible_units: int = Field(ge=0)
    in_stock_seconds: int | None = Field(default=None, ge=0)
    source: str = Field(min_length=1, max_length=500)
    merchant_weight: int | None = Field(default=None, ge=0)


class Receipt(SourceModel):
    id: str
    variant_id: str
    quantity: int = Field(gt=0)
    expected_at: AwareDatetime
    observed_at: AwareDatetime
    status: Literal['confirmed', 'unconfirmed', 'cancelled']
    source: str = Field(min_length=1)


class ResourceState(Identity):
    status: Literal['active', 'paused']
    paused_by: Literal['AdVergent', 'merchant', 'unknown'] | None
    pause_evidence_id: str | None
    observed_at: AwareDatetime
    blockers: list[str]
    source: str = Field(min_length=1)


class InventoryFixture(SourceModel):
    version: str = Field(min_length=1, max_length=100)
    as_of: AwareDatetime
    window_start: AwareDatetime
    observed_at: AwareDatetime
    observations: list[Observation] = Field(min_length=1)
    warehouse_id: Literal['warehouse-1'] = 'warehouse-1'
    receipts: list[Receipt]
    resource_states: list[ResourceState]
    lead_days: dict[str, int | None]
    lead_source: str = Field(min_length=1)
    safety_days: int = Field(default=3, ge=0)
    min_units: int = Field(default=10, gt=0)
    min_exposure_days: int = Field(default=7, gt=0)
    throttle_days: int = Field(default=5, gt=0)
    recovery_days: int = Field(default=7, gt=0)
    pause_unavailable_bps: int = Field(default=6000, ge=1, le=10000)
    recovery_unavailable_bps: int = Field(default=4000, ge=0, le=10000)
    freshness_seconds: int = Field(default=900, gt=0)

    @model_validator(mode='after')
    def valid(self):
        if not self.window_start < self.as_of <= self.observed_at <= datetime.now(timezone.utc):
            raise ValueError('Invalid inventory interval')
        duration = int((self.as_of-self.window_start).total_seconds())
        for group, key in ((self.observations, lambda r:r.variant_id), (self.receipts, lambda r:r.id), (self.resource_states, lambda r:r.key)):
            if len({key(r) for r in group}) != len(group): raise ValueError('Duplicate inventory evidence')
        for r in self.observations:
            if r.stock_observed_at > self.observed_at or (r.in_stock_seconds is not None and r.in_stock_seconds > duration):
                raise ValueError('Invalid stock/exposure observation')
            if r.in_stock_seconds == 0 and r.eligible_units: raise ValueError('Demand without observed exposure')
        if any(v is not None and v < 0 for v in self.lead_days.values()): raise ValueError('Negative lead time')
        if any(r.observed_at > self.observed_at for r in self.receipts+self.resource_states): raise ValueError('Future source evidence')
        return self


def decimal(value):
    return None if value is None else str(value)


def assess(f, variants, at, aggregate_features=None):
    """SQL supplies exact stock/demand/cover inputs; Python applies vendor-neutral policy."""
    products = []
    for pid in sorted({v['product_id'] for v in variants}):
        rows = [dict(v) for v in variants if v['product_id'] == pid]
        lead = f.lead_days[pid]
        for r in rows:
            velocity = Decimal(r['daily_velocity']) if r['daily_velocity'] is not None else None
            reliable = bool(velocity is not None and r['eligible_units'] >= f.min_units and r['in_stock_seconds'] >= f.min_exposure_days*86400)
            r['demand_status'] = 'sufficient' if reliable else 'missing_exposure' if r['in_stock_seconds'] is None else 'zero_observed_demand' if not r['eligible_units'] else 'sparse'
            r['days_of_cover'] = r['raw_days_of_cover'] if reliable and velocity > 0 else None
            r['fresh'] = 0 <= (at-datetime.fromisoformat(r['stock_observed_at'])).total_seconds() <= f.freshness_seconds
            receipts = [x for x in f.receipts if x.variant_id == r['variant_id']]
            r['receipts'] = [x.model_dump(mode='json') for x in receipts]
            # Walk receipts in time; late/uncertain receipts never bridge an earlier gap.
            horizon = Decimal(r['days_of_cover']) if r['days_of_cover'] is not None else None
            used=[]
            if horizon is not None:
                for x in sorted(receipts, key=lambda x:x.expected_at):
                    days=Decimal(str((x.expected_at-datetime.fromisoformat(r['stock_observed_at'])).total_seconds()))/86400
                    if x.status == 'confirmed' and x.expected_at >= at and x.expected_at > datetime.fromisoformat(r['stock_observed_at']) and 0 <= (at-x.observed_at).total_seconds() <= f.freshness_seconds and days <= horizon:
                        horizon += Decimal(x.quantity)/velocity
                        used.append(x.id)
            r['no_gap_cover_with_receipts'] = decimal(horizon)
            r['qualified_receipt_ids'] = used
            r['replenishment_sufficient'] = bool(lead is not None and horizon is not None and horizon >= lead+f.safety_days)
        known = all(r['demand_status']=='sufficient' for r in rows)
        fallback = all(r['merchant_weight'] is not None for r in rows) and sum(r['merchant_weight'] for r in rows)>0
        weights = [Decimal(r['daily_velocity']) for r in rows] if known else [Decimal(r['merchant_weight']) for r in rows] if fallback else None
        total_weight = sum(weights) if weights else 0
        available_weight = sum(w for r,w in zip(rows,weights,strict=True) if r['sellable_units']>0) if weights else None
        unavailable = (Decimal(1)-available_weight/total_weight)*10000 if total_weight else None
        # Compare exact decimals, round only display. Never round a 59.999% risk up to a pause.
        velocity = sum(Decimal(r['daily_velocity']) for r in rows) if known else None
        stock = sum(r['sellable_units'] for r in rows)
        cover = Decimal(stock)/velocity if velocity and velocity>0 else None
        if aggregate_features is not None:
            sql=aggregate_features[pid]
            stock=sql['sellable_units']
            velocity=sql['daily_velocity']
            cover=sql['days_of_cover']
            unavailable=sql['unavailable_weight_bps']
        fresh=all(r['fresh'] for r in rows)
        pause = stock==0 or (unavailable is not None and unavailable >= f.pause_unavailable_bps)
        throttle = any(r['days_of_cover'] is not None and Decimal(r['days_of_cover'])<f.throttle_days and not r['replenishment_sufficient'] for r in rows)
        warning = lead is not None and any(r['days_of_cover'] is not None and Decimal(r['days_of_cover'])<lead+f.safety_days for r in rows)
        uncertain = not known or lead is None or unavailable is None
        recovery = bool(fresh and not uncertain and not pause and not throttle and cover is not None and cover>=f.recovery_days and unavailable<f.recovery_unavailable_bps)
        products.append(dict(product_id=pid, sellable_units=stock, daily_velocity=decimal(velocity), days_of_cover=decimal(cover),
            lead_days=lead, lead_source=f.lead_source, warning=warning, stockout=stock==0,
            unavailable_weight_bps=decimal(unavailable), weight_source='observed in-stock demand rates' if known else 'merchant assumption' if fallback else 'unknown',
            pause_eligible=pause and fresh, throttle_eligible=throttle and fresh and not pause, recovery_stock_eligible=recovery,
            risk='stale' if not fresh else 'pause' if pause else 'throttle' if throttle else 'uncertain' if uncertain else 'warning' if warning else 'clear',
            suggested_action='pause' if pause else 'throttle' if throttle else 'inspect' if uncertain or warning else 'none',
            approval_required=True, affected_scope=[pid],
            uncertain=uncertain, fresh=fresh, variants=rows))
    return products


def recommendations(f, products, resources, mappings, finance, at, dependencies_current):
    byproduct={p['product_id']:p for p in products}
    states={r.key:r for r in f.resource_states}
    result=[]
    for resource in resources:
        key=(resource['platform'],resource['account_id'],resource['id'])
        mapping=resolve_mapping(mappings,key,at)
        ps=[byproduct[p] for p in mapping['products']]
        state=states.get(key)
        blockers=[]
        if not dependencies_current: blockers.append('pinned upstream publication changed')
        if mapping['status']!='resolved': blockers.append('mapping '+mapping['status'])
        if ps and any(not p['fresh'] for p in ps): blockers.append('stale inventory')
        state_fresh=bool(state and 0 <= (at-state.observed_at).total_seconds() <= f.freshness_seconds)
        if not state_fresh: blockers.append('missing or stale simulated resource observation')
        if state: blockers.extend(state.blockers)
        action='none'
        risky=[p for p in ps if p['risk'] in ('pause','throttle')]
        if risky:
            action='pause' if any(p['pause_eligible'] for p in risky) else 'throttle'
            if (action=='pause' and not all(p['pause_eligible'] for p in ps)) or (action=='throttle' and not all(p['throttle_eligible'] for p in ps)):
                blockers.append('mixed-product scope includes unaffected products; narrow product controls unavailable')
            if action=='pause' and not resource['status_control_supported']: blockers.append('exact status control unsupported')
            if action=='throttle' and (not resource['budget_control_supported'] or resource['shared_budget']): blockers.append('exact unshared resource budget control unsupported')
            if state and state.status!='active': blockers.append('resource already paused')
        elif ps and state and state.status=='paused':
            action='recovery'
            if state.paused_by!='AdVergent' or not state.pause_evidence_id:
                action='advisory'
                blockers.append('no prior AdVergent pause evidence')
            if not all(p['recovery_stock_eligible'] for p in ps): blockers.append('inventory recovery conditions not cleared')
            if not resource['status_control_supported']: blockers.append('exact status control unsupported')
        elif ps and any(p['risk'] not in ('clear',) for p in ps):
            action='advisory'
            blockers.append('inventory warning or uncertainty; no eligible mutation')
        # Pinned finance is historical impact context, never causal lift or avoided profit.
        impact=[r for r in finance['lines'] if r['evidence']['original_line']['variant_id'] in {v['variant_id'] for p in ps for v in p['variants']}]
        unknown=any(r['expected_before_ads_paise'] is None for r in impact)
        subtotal=sum(r['expected_before_ads_paise'] or 0 for r in impact)
        impact_units=sum(r['evidence']['original_line']['quantity'] for r in impact if r['delivered_paise']>0)
        # A transparent scenario estimate, not a response/causal model. Preserve each product's missing costs.
        daily_context=Decimal(0)
        daily_known=bool(ps)
        for p in ps:
            ids={v['variant_id'] for v in p['variants']}
            lines=[r for r in impact if r['evidence']['original_line']['variant_id'] in ids]
            units=sum(r['evidence']['original_line']['quantity'] for r in lines if r['delivered_paise']>0)
            if not units or p['daily_velocity'] is None or any(r['expected_before_ads_paise'] is None for r in lines):
                daily_known=False
            else:
                daily_context+=Decimal(sum(r['expected_before_ads_paise'] for r in lines))*Decimal(p['daily_velocity'])/units
        result.append(dict(platform=key[0],account_id=key[1],resource_id=key[2],campaign_id=resource['campaign_id'],
            affected_products=mapping['products'], mapping=mapping, action=action,
            eligibility='eligible' if action in ('pause','throttle','recovery') and not blockers else 'advisory' if action!='none' else 'abstain',
            blockers=blockers,approval_required=True,mutation_enabled=False,
            capability_evidence=resource['capability_evidence'], budget_id=resource['effective_budget_id'], budget_members=resource['budget_members'],
            state=state.model_dump(mode='json') if state else None,
            impact=dict(basis='pinned historical purchased-product contribution before ads, expected after reserve, across first-party assigned and unattributed orders; not incremental profit or a forecast',
                delivered_sample_units=impact_units, daily_contribution_context_paise=decimal(daily_context) if daily_known else None,
                scenario_assumption='historical product expected contribution per delivered unit times observed warehouse daily rate; includes historical failed-order costs; uncalibrated, differing cutoffs, not incremental profit or guaranteed loss',
                lines=len(impact), missing_lines=sum(r['expected_before_ads_paise'] is None for r in impact),
                expected_contribution_paise=None if unknown or not impact else subtotal,covered_subtotal_paise=subtotal),
            evidence_products=mapping['products']))
    return result


def import_inventory(store, analytics, fixture_path=ROOT/'fixtures/inventory-v1.json'):
    raw=fixture_path.read_bytes();f=InventoryFixture.model_validate_json(raw)
    digest=hashlib.sha256(raw).hexdigest()
    with store.engine.connect() as lock:
        acquired=[]
        try:
            for n in (17012028,17012030,17012031,17012032,17012033):
                if not lock.execute(text('SELECT pg_try_advisory_lock(:n)'),dict(n=n)).scalar(): raise RuntimeError('Dependent import already running')
                acquired.append(n)
            lock.commit()
            finance=store.finance_publication()[0]
            if not finance: raise RuntimeError('Publish finance first')
            for method,key in ((store.commerce_publication,'commerce_id'),(store.ad_publication,'ads_id'),(store.attribution_publication,'attribution_id')):
                upstream=method()[0]
                if not upstream or upstream['id']!=finance[key]: raise RuntimeError('Finance inputs changed; republish dependencies first')
            fid=str(finance['id']);run=str(uuid5(NAMESPACE_URL,'inventory-v1:'+digest+fid));attempt=str(uuid4())
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE inventory_attempts SET status='failed',error_code='worker_interrupted',finished_at=now() WHERE status='running'"))
                conn.execute(text('INSERT INTO inventory_runs(id,version,fixture_hash,finance_id,configuration,observed_at) VALUES (:id,:version,:hash,:fid,CAST(:config AS jsonb),:observed) ON CONFLICT(id) DO NOTHING'),dict(id=run,version=f.version,hash=digest,fid=fid,config=raw.decode(),observed=min(r.stock_observed_at for r in f.observations)))
                conn.execute(text("INSERT INTO inventory_attempts(id,run_id,status) VALUES (:id,:run,'running')"),dict(id=attempt,run=run))
            try:
                analytics.load_inventory(run,fid,f)
                analytics.verify_inventory(run,f,fid)
                with store.engine.begin() as conn:
                    conn.execute(text('UPDATE inventory_runs SET finished_at=COALESCE(finished_at,now()) WHERE id=:id'),dict(id=run))
                    conn.execute(text("UPDATE inventory_attempts SET status='succeeded',finished_at=now() WHERE id=:id"),dict(id=attempt))
                    conn.execute(text('INSERT INTO inventory_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'),dict(run=run))
            except Exception:
                with store.engine.begin() as conn:conn.execute(text("UPDATE inventory_attempts SET status='failed',error_code='inventory_failed',finished_at=now() WHERE id=:id"),dict(id=attempt))
                raise RuntimeError('Inventory failed; prior publication preserved') from None
            return run
        finally:
            for n in reversed(acquired):lock.execute(text('SELECT pg_advisory_unlock(:n)'),dict(n=n))
            lock.commit()
