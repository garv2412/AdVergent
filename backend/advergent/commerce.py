"""Versioned synthetic Shopify-shaped source and resumable commerce ingestion.

No Shopify network access. Source revisions and observation time are distinct from
delivery time and the wall clock. Operational staging is never a dashboard source.
"""
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from sqlalchemy import text
from .operational import ROOT

KINDS = ('products', 'variants', 'customers', 'orders', 'lines', 'refunds', 'inventory')


class SourceModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Product(SourceModel):
    title: str = Field(max_length=500)
    status: Literal['active', 'archived']


class Variant(SourceModel):
    product_id: str
    sku: str
    size: str
    color: str
    price_paise: int = Field(ge=0)
    unit_cost_paise: int | None = Field(ge=0)
    cost_status: Literal['actual', 'estimated', 'missing']
    cost_source: str
    cost_effective_at: AwareDatetime

    @model_validator(mode='after')
    def cost_coverage(self):
        if (self.unit_cost_paise is None) != (self.cost_status == 'missing'):
            raise ValueError('Missing costs must remain unknown')
        return self


class Customer(SourceModel):
    synthetic_key: str


class Order(SourceModel):
    customer_id: str
    currency: Literal['INR']
    placed_at: AwareDatetime
    payment_method: Literal['prepaid', 'cod']
    payment_status: Literal['paid', 'pending', 'unremitted', 'refunded']
    fulfillment_status: Literal['unfulfilled', 'shipped', 'delivered', 'cancelled', 'rto']


class Line(SourceModel):
    order_id: str
    variant_id: str
    quantity: int = Field(gt=0)
    unit_price_paise: int = Field(ge=0)
    discount_paise: int = Field(ge=0)
    tax_paise: int = Field(ge=0)
    unit_cost_paise: int | None = Field(ge=0)
    cost_status: Literal['actual', 'estimated', 'missing']
    cost_source: str
    cost_effective_at: AwareDatetime

    @model_validator(mode='after')
    def valid_amounts(self):
        if self.discount_paise > self.quantity * self.unit_price_paise:
            raise ValueError('Discount exceeds merchandise')
        if (self.unit_cost_paise is None) != (self.cost_status == 'missing'):
            raise ValueError('Missing historical costs must remain unknown')
        return self


class Refund(SourceModel):
    order_id: str
    line_id: str
    quantity: int = Field(gt=0)
    merchandise_paise: int = Field(ge=0)
    tax_paise: int = Field(ge=0)
    refunded_at: AwareDatetime
    recovery: Literal['none', 'intact', 'damaged', 'unknown']


class Inventory(SourceModel):
    variant_id: str
    location_id: Literal['warehouse-1']
    available: int = Field(ge=0)
    committed: int = Field(ge=0)
    merchant_reserve: int = Field(ge=0)


MODELS = dict(zip(KINDS, (Product, Variant, Customer, Order, Line, Refund, Inventory), strict=True))


class Record(SourceModel):
    kind: Literal['products', 'variants', 'customers', 'orders', 'lines', 'refunds', 'inventory']
    id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    updated_at: AwareDatetime
    deleted: bool = False
    data: dict

    @model_validator(mode='after')
    def payload(self):
        if self.deleted:
            if self.data:
                raise ValueError('Tombstone must have empty data')
        else:
            # JSON validation parses only the explicitly typed timestamp fields.
            self.data = MODELS[self.kind].model_validate_json(json.dumps(self.data)).model_dump(mode='json')
        return self


class Delivery(SourceModel):
    delivery_id: str = Field(min_length=1, max_length=100)
    record: Record


class CommerceFixture(SourceModel):
    version: str = Field(min_length=1, max_length=100)
    seed: int
    scenario_clock: AwareDatetime
    observed_at: AwareDatetime
    pages: list[list[Delivery]]
    snapshot: list[Record]

    @model_validator(mode='after')
    def source_contract(self):
        if self.observed_at > datetime.now(timezone.utc):
            raise ValueError('Source observation is in the future')
        if self.scenario_clock != self.observed_at:
            raise ValueError('Fixture snapshot must match scenario clock')
        keys = [(r.kind, r.id) for r in self.snapshot]
        if len(keys) != len(set(keys)) or any(r.deleted for r in self.snapshot):
            raise ValueError('Snapshot must have unique live keys')
        for r in self.snapshot + [e.record for page in self.pages for e in page]:
            if r.updated_at > self.observed_at:
                raise ValueError('Source revision exceeds observation time')
        return self


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def validate_snapshot(records):
    """Check source relationships before analytical loading, including refunds."""
    groups = {kind: {} for kind in KINDS}
    for record in records:
        if not record.deleted:
            groups[record.kind][record.id] = record.data
    def require(kind, key):
        if key not in groups[kind]:
            raise ValueError('Dangling commerce reference')
        return groups[kind][key]
    for v in groups['variants'].values():
        require('products', v['product_id'])
    for order in groups['orders'].values():
        require('customers', order['customer_id'])
    for line in groups['lines'].values():
        require('orders', line['order_id'])
        require('variants', line['variant_id'])
    quantities, amounts = {}, {}
    for refund in groups['refunds'].values():
        line = require('lines', refund['line_id'])
        if refund['order_id'] != line['order_id']:
            raise ValueError('Refund order mismatch')
        key = refund['line_id']
        quantities[key] = quantities.get(key, 0) + refund['quantity']
        amounts[key] = amounts.get(key, 0) + refund['merchandise_paise']
        if quantities[key] > line['quantity'] or amounts[key] > line['quantity'] * line['unit_price_paise'] - line['discount_paise']:
            raise ValueError('Refund exceeds source line')
    inventory_variants = set()
    for inv in groups['inventory'].values():
        require('variants', inv['variant_id'])
        if inv['variant_id'] in inventory_variants:
            raise ValueError('Duplicate inventory at the single warehouse')
        inventory_variants.add(inv['variant_id'])
    if inventory_variants != set(groups['variants']):
        raise ValueError('Incomplete warehouse inventory snapshot')
    return groups


@contextmanager
def commerce_attempt(store, run):
    attempt = str(uuid4())
    with store.engine.begin() as conn:
        conn.execute(text("INSERT INTO commerce_attempts(id,run_id,status) VALUES (:id,:run,'running')"), dict(id=attempt, run=run))
    try:
        yield attempt
    except Exception:
        with store.engine.begin() as conn:
            conn.execute(text("UPDATE commerce_attempts SET status='failed',finished_at=now(),error_code='commerce_import_failed' WHERE id=:id"), {'id': attempt})
        raise RuntimeError('Commerce import failed; checkpoint and prior publication preserved') from None
    else:
        with store.engine.begin() as conn:
            conn.execute(text("UPDATE commerce_attempts SET status='succeeded',finished_at=now() WHERE id=:id"), {'id': attempt})


def import_commerce(store, analytics, fixture_path=ROOT / 'fixtures/commerce-v1.json', after_page=None):
    raw = fixture_path.read_bytes()
    fixture = CommerceFixture.model_validate_json(raw)
    validate_snapshot(fixture.snapshot)
    digest = hashlib.sha256(raw).hexdigest()
    run = str(uuid5(NAMESPACE_URL, 'commerce-schema-v1:' + digest))
    with store.engine.connect() as lock, commerce_attempt(store, run) as attempt:
        if not lock.execute(text('SELECT pg_try_advisory_lock(17012028)')).scalar():
            raise RuntimeError('Commerce import already running')
        lock.commit()
        try:
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE commerce_attempts SET status='failed',finished_at=now(),error_code='worker_interrupted' WHERE status='running' AND id<>:attempt"), {'attempt': attempt})
            with store.engine.connect() as conn:
                completed = conn.execute(text("SELECT 1 FROM commerce_runs WHERE id=:run AND status='succeeded'"), {'run': run}).scalar()
            if completed:
                analytics.verify_commerce(run, fixture.snapshot)
                with store.engine.begin() as conn:
                    conn.execute(text('INSERT INTO commerce_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'), {'run': run})
                return run
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE commerce_runs SET status='failed',error_code='worker_interrupted' WHERE status='running'"))
                conn.execute(text('''INSERT INTO commerce_runs(id,fixture_hash,version,observed_at,scenario_clock,status)
                    VALUES (:id,:hash,:version,:observed,:clock,'running') ON CONFLICT(id)
                    DO UPDATE SET status='running', error_code=NULL, finished_at=NULL'''),
                    dict(id=run, hash=digest, version=fixture.version, observed=fixture.observed_at, clock=fixture.scenario_clock))
            try:
                with store.engine.connect() as conn:
                    cursor = conn.execute(text('SELECT next_page FROM commerce_runs WHERE id=:id'), {'id': run}).scalar_one()
                for index in range(cursor, len(fixture.pages)):
                    with store.engine.begin() as conn:
                        for delivery in fixture.pages[index]:
                            record = delivery.record
                            body = record.model_dump(mode='json')
                            payload_hash = hashlib.sha256(canonical(body).encode()).hexdigest()
                            prior = conn.execute(text('SELECT payload_hash FROM commerce_deliveries WHERE run_id=:run AND delivery_id=:delivery'), dict(run=run, delivery=delivery.delivery_id)).scalar()
                            if prior:
                                if prior != payload_hash:
                                    raise ValueError('Delivery ID reused with different content')
                                continue
                            conn.execute(text('INSERT INTO commerce_deliveries VALUES (:run,:delivery,:hash)'), dict(run=run, delivery=delivery.delivery_id, hash=payload_hash))
                            old = conn.execute(text('SELECT body FROM commerce_staging WHERE run_id=:run AND kind=:kind AND source_id=:id'), dict(run=run, kind=record.kind, id=record.id)).scalar()
                            if old:
                                old_record = Record.model_validate_json(json.dumps(old))
                                if old_record.updated_at == record.updated_at and old_record != record:
                                    raise ValueError('Conflicting equal source revisions')
                                if old_record.updated_at >= record.updated_at:
                                    continue
                            conn.execute(text('''INSERT INTO commerce_staging VALUES (:run,:kind,:id,CAST(:body AS jsonb))
                                ON CONFLICT(run_id,kind,source_id) DO UPDATE SET body=EXCLUDED.body'''), dict(run=run, kind=record.kind, id=record.id, body=canonical(body)))
                        conn.execute(text('UPDATE commerce_runs SET next_page=:page WHERE id=:run'), dict(page=index + 1, run=run))
                    if after_page:
                        after_page(index + 1)
                # Complete authoritative snapshot repairs missed events and removes
                # absent objects. Only a complete snapshot may perform this sweep.
                with store.engine.begin() as conn:
                    previous = conn.execute(text('SELECT kind,source_id,body FROM commerce_staging WHERE run_id=:run'), {'run': run}).mappings().all()
                    old = {(row['kind'], row['source_id']): row['body'] for row in previous if not row['body']['deleted']}
                    current = {(r.kind, r.id): r.model_dump(mode='json') for r in fixture.snapshot}
                    repairs = sum(old.get(key) != body for key, body in current.items()) + len(old.keys() - current.keys())
                    # Snapshot cannot silently regress a newer delivered revision.
                    for row in previous:
                        r = Record.model_validate_json(json.dumps(row['body']))
                        body = current.get((r.kind, r.id))
                        if body:
                            authoritative = Record.model_validate_json(json.dumps(body))
                            if r.updated_at > authoritative.updated_at or (r.updated_at == authoritative.updated_at and r != authoritative):
                                raise ValueError('Snapshot conflicts with delivered revision')
                    conn.execute(text('DELETE FROM commerce_staging WHERE run_id=:run'), {'run': run})
                    if current:
                        conn.execute(text('INSERT INTO commerce_staging VALUES (:run,:kind,:id,CAST(:body AS jsonb))'),
                            [dict(run=run, kind=r.kind, id=r.id, body=canonical(r.model_dump(mode='json'))) for r in fixture.snapshot])
                    conn.execute(text('UPDATE commerce_runs SET reconciled=true,repair_count=:repairs WHERE id=:run'), dict(run=run, repairs=repairs))
                analytics.load_commerce(run, fixture.snapshot)
                analytics.verify_commerce(run, fixture.snapshot)
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE commerce_runs SET status='succeeded',finished_at=now() WHERE id=:run"), {'run': run})
                    conn.execute(text('INSERT INTO commerce_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'), {'run': run})
            except Exception:
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE commerce_runs SET status='failed',error_code='commerce_import_failed',finished_at=now() WHERE id=:run"), {'run': run})
                raise RuntimeError('Commerce import failed; checkpoint and prior publication preserved') from None
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(17012028)'))
            lock.commit()
    return run
