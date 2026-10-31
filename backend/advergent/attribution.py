"""Versioned first-party evidence and mapping decisions; no platform actions."""
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5
from pydantic import AwareDatetime, Field, model_validator
from typing import Literal
from sqlalchemy import text
from .commerce import SourceModel, canonical
from .operational import ROOT

MODEL = 'last-paid-click-7d-no-view-v1'


class Identity(SourceModel):
    platform: Literal['meta', 'google']
    account_id: str = Field(min_length=1, max_length=80)
    resource_id: str = Field(min_length=1, max_length=80)

    @property
    def key(self):
        return self.platform, self.account_id, self.resource_id


class Mapping(Identity):
    id: str = Field(min_length=1, max_length=100)
    products: list[str] = Field(min_length=1)
    provenance: str = Field(min_length=1, max_length=500)
    confidence_bps: int = Field(ge=0, le=10000)
    valid_from: AwareDatetime
    valid_to: AwareDatetime
    override: bool = False
    actor: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def interval(self):
        if self.valid_to <= self.valid_from or len(set(self.products)) != len(self.products):
            raise ValueError('Invalid mapping interval or duplicate products')
        return self


class Click(Identity):
    id: str = Field(min_length=1, max_length=100)
    order_id: str
    clicked_at: AwareDatetime
    kind: Literal['paid_click', 'view', 'organic']
    identifiable: bool


class Claim(Identity):
    id: str = Field(min_length=1, max_length=100)
    order_id: str
    reported_value_paise: int = Field(ge=0)


class AttributionFixture(SourceModel):
    version: str = Field(min_length=1, max_length=100)
    model: Literal['last-paid-click-7d-no-view-v1']
    observed_at: AwareDatetime
    mappings: list[Mapping]
    clicks: list[Click]
    platform_claims: list[Claim]

    @model_validator(mode='after')
    def evidence(self):
        if self.observed_at > datetime.now(timezone.utc):
            raise ValueError('Future observation')
        for rows in (self.mappings, self.platform_claims):
            if len({r.id for r in rows}) != len(rows):
                raise ValueError('Duplicate evidence ID')
        deduplicate(self.clicks)
        if any(c.clicked_at > self.observed_at for c in self.clicks):
            raise ValueError('Future click')
        return self


def deduplicate(clicks):
    result = {}
    for click in clicks:
        if click.id in result and result[click.id] != click:
            raise ValueError('Conflicting click ID')
        result[click.id] = click
    return list(result.values())


def resolve_mapping(rows, key, at):
    active = [r for r in rows if r.key == key and r.valid_from <= at < r.valid_to]
    overrides = [r for r in active if r.override]
    candidates = overrides or [r for r in active if r.confidence_bps >= 9000]
    sets = {tuple(sorted(r.products)) for r in candidates}
    status = 'resolved' if len(sets) == 1 else 'ambiguous' if len(sets) > 1 else 'unmapped'
    return dict(platform=key[0], account_id=key[1], resource_id=key[2], status=status,
                products=list(next(iter(sets))) if status == 'resolved' else [],
                evidence_ids=sorted(r.id for r in active), override=bool(overrides),
                product_control_supported=False)


def derive(fixture, orders, products, resources):
    resource_index = {(r['platform'], r['account_id'], r['id']): r for r in resources}
    order_index = {r.id: r for r in orders}
    for m in fixture.mappings:
        if m.key not in resource_index or not set(m.products) <= set(products):
            raise ValueError('Unknown mapping resource/product')
    clicks = deduplicate(fixture.clicks)
    for event in clicks + fixture.platform_claims:
        if event.key not in resource_index or event.order_id not in order_index:
            raise ValueError('Unknown attribution identity')
    assignments = []
    for order in orders:
        placed = datetime.fromisoformat(order.data['placed_at'])
        eligible = [c for c in clicks if c.order_id == order.id and c.kind == 'paid_click' and c.identifiable
                    and placed - timedelta(days=7) <= c.clicked_at <= placed]
        latest = max((c.clicked_at for c in eligible), default=None)
        winners = [c for c in eligible if c.clicked_at == latest]
        campaigns = {(c.platform, c.account_id, resource_index[c.key]['campaign_id']) for c in winners}
        campaign = next(iter(campaigns)) if len(campaigns) == 1 else (None, None, None)
        assignments.append(dict(order_id=order.id, platform=campaign[0], account_id=campaign[1], campaign_id=campaign[2],
                                reason='paid_click' if len(campaigns) == 1 else 'ambiguous_click' if campaigns else 'no_eligible_click',
                                click_ids=sorted(c.id for c in winners)))
    mappings = [resolve_mapping(fixture.mappings, key, fixture.observed_at) for key in sorted(resource_index)]
    return dict(assignments=assignments, mappings=mappings,
                mapping_evidence=[r.model_dump(mode='json') for r in fixture.mappings],
                platform_claims=[r.model_dump(mode='json') for r in fixture.platform_claims],
                clicks=[c.model_dump(mode='json') for c in clicks])


def import_attribution(store, analytics, fixture_path=ROOT / 'fixtures/attribution-v1.json'):
    raw = fixture_path.read_bytes()
    fixture = AttributionFixture.model_validate_json(raw)
    digest = hashlib.sha256(raw).hexdigest()
    with store.engine.connect() as lock:
        acquired = []
        try:
            # Same locks as the upstream loaders pin both inputs through publication.
            for number in (17012028, 17012030, 17012031):
                if not lock.execute(text('SELECT pg_try_advisory_lock(:number)'), dict(number=number)).scalar():
                    raise RuntimeError('Dependent import already running')
                acquired.append(number)
            lock.commit()
            commerce = store.commerce_publication()[0]
            ads = store.ad_publication()[0]
            if not commerce or not ads:
                raise RuntimeError('Commerce and ads must be published first')
            commerce_id, ads_id = str(commerce['id']), str(ads['id'])
            run = str(uuid5(NAMESPACE_URL, 'attribution-v1:' + digest + commerce_id + ads_id))
            attempt = str(uuid4())
            observed = min(fixture.observed_at, commerce['observed_at'], ads['observed_at'])
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE attribution_attempts SET status='failed',error_code='worker_interrupted',finished_at=now() WHERE status='running'"))
                conn.execute(text('INSERT INTO attribution_runs(id,version,fixture_hash,commerce_id,ads_id,configuration,observed_at) VALUES (:id,:version,:hash,:commerce,:ads,CAST(:config AS jsonb),:observed) ON CONFLICT(id) DO NOTHING'), dict(id=run, version=fixture.version, hash=digest, commerce=commerce_id, ads=ads_id, config=raw.decode(), observed=observed))
                conn.execute(text("INSERT INTO attribution_attempts(id,run_id,status) VALUES (:id,:run,'running')"), dict(id=attempt, run=run))
            try:
                orders = analytics.commerce_records(commerce_id, 'orders', limit=None)
                products = [r.id for r in analytics.commerce_records(commerce_id, 'products', limit=None)]
                resources = analytics.ad_data(ads_id)['resources']
                data = derive(fixture, orders, products, resources)
                analytics.load_attribution(run, commerce_id, data)
                analytics.verify_attribution(run, commerce_id, data)
                with store.engine.begin() as conn:
                    conn.execute(text('UPDATE attribution_runs SET finished_at=COALESCE(finished_at,now()) WHERE id=:run'), dict(run=run))
                    conn.execute(text("UPDATE attribution_attempts SET status='succeeded',finished_at=now() WHERE id=:id"), dict(id=attempt))
                    conn.execute(text('INSERT INTO attribution_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'), dict(run=run))
            except Exception:
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE attribution_attempts SET status='failed',error_code='attribution_failed',finished_at=now() WHERE id=:id"), dict(id=attempt))
                raise RuntimeError('Attribution failed; prior publication preserved') from None
            return run
        finally:
            for number in reversed(acquired):
                lock.execute(text('SELECT pg_advisory_unlock(:number)'), dict(number=number))
            lock.commit()
