"""Synthetic reporting application contract; no external SDK or mutation method.

Each fixture is a complete bounded report history, not an incremental live feed.
Durable adapter cursors and revision state belong to PostgreSQL, analytics to Exasol.
"""
import hashlib
import json
from datetime import timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, uuid4, uuid5
from zoneinfo import ZoneInfo
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import text
from .commerce import SourceModel, canonical
from .operational import ROOT

Platform = Literal['meta', 'google']
Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')]


class Account(SourceModel):
    platform: Platform
    id: Identifier
    currency: Literal['INR']
    timezone: Literal['Asia/Kolkata', 'UTC']


class Resource(SourceModel):
    platform: Platform
    account_id: Identifier
    id: Identifier
    parent_id: Identifier | None
    kind: Literal['campaign', 'ad_set', 'ad_group', 'ad', 'asset_group']
    campaign_type: Literal['meta', 'search', 'shopping', 'pmax']
    name: str = Field(min_length=1, max_length=200)
    status: Literal['active', 'paused']
    budget_id: Identifier | None
    product_scope: Literal['single', 'multiple', 'unknown']
    source_product_refs: list[Identifier]

    @model_validator(mode='after')
    def scope_hints(self):
        count = len(set(self.source_product_refs))
        if count != len(self.source_product_refs) or (self.product_scope == 'single' and count != 1) or (self.product_scope == 'multiple' and count < 2) or (self.product_scope == 'unknown' and count):
            raise ValueError('Product-scope source hints inconsistent')
        return self


class Budget(SourceModel):
    platform: Platform
    account_id: Identifier
    id: Identifier
    owner_id: Identifier | None
    shared: bool
    daily_paise: int = Field(ge=0, le=10**12)


class Report(SourceModel):
    platform: Platform
    account_id: Identifier
    resource_id: Identifier
    interval_start: AwareDatetime
    source_day: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    revision: int = Field(ge=1)
    reported_at: AwareDatetime
    currency: Literal['INR']
    amount_rupees: str | None = None
    cost_micros: int | None = Field(default=None, ge=0, le=10**16)

    @model_validator(mode='after')
    def amount(self):
        if self.platform == 'meta':
            if self.cost_micros is not None or self.amount_rupees is None:
                raise ValueError('Meta source requires decimal rupees only')
            import re
            if not re.fullmatch(r'\d{1,10}(\.\d{1,2})?', self.amount_rupees):
                raise ValueError('Meta rupees must be exact nonnegative paise')
        elif self.amount_rupees is not None or self.cost_micros is None or self.cost_micros % 10000:
            raise ValueError('Google source requires exact paise in micros')
        return self

    @property
    def paise(self):
        return int(Decimal(self.amount_rupees) * 100) if self.platform == 'meta' else self.cost_micros // 10000

    @property
    def key(self):
        return f'{self.platform}:{self.account_id}:{self.resource_id}:{self.interval_start.astimezone(timezone.utc).isoformat()}'

    def normalized(self):
        return dict(key=self.key, platform=self.platform, account_id=self.account_id,
                    resource_id=self.resource_id, interval_start=self.interval_start.astimezone(timezone.utc).isoformat(),
                    reporting_day=self.interval_start.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat(),
                    source_day=self.source_day, revision=self.revision,
                    reported_at=self.reported_at.astimezone(timezone.utc).isoformat(), currency=self.currency, spend_paise=self.paise)


class AdFixture(SourceModel):
    version: str = Field(min_length=1, max_length=100)
    seed: int
    observed_at: AwareDatetime
    scenario_clock: AwareDatetime
    accounts: list[Account]
    resources: list[Resource]
    budgets: list[Budget]
    pages: dict[Platform, list[list[Report]]]

    @model_validator(mode='after')
    def relationships(self):
        from datetime import datetime
        if self.observed_at > datetime.now(timezone.utc) or self.observed_at > self.scenario_clock:
            raise ValueError('Invalid source observation')
        accounts = {(a.platform, a.id): a for a in self.accounts}
        resources = {(r.platform, r.account_id, r.id): r for r in self.resources}
        budgets = {(b.platform, b.account_id, b.id): b for b in self.budgets}
        if len(accounts) != len(self.accounts) or len(resources) != len(self.resources) or len(budgets) != len(self.budgets):
            raise ValueError('Duplicate hierarchy identity')
        if set(self.pages) != {'meta', 'google'} or set(a.platform for a in self.accounts) != {'meta', 'google'}:
            raise ValueError('Both synthetic adapters required')
        for r in self.resources:
            if (r.platform, r.account_id) not in accounts:
                raise ValueError('Unknown account')
            allowed = {'campaign': None, 'ad_set': 'campaign', 'ad_group': 'campaign', 'ad': 'ad_set' if r.platform == 'meta' else 'ad_group', 'asset_group': 'campaign'}
            if r.kind not in ({'campaign', 'ad_set', 'ad'} if r.platform == 'meta' else {'campaign', 'ad_group', 'ad', 'asset_group'}):
                raise ValueError('Platform hierarchy mismatch')
            if (r.platform == 'meta') != (r.campaign_type == 'meta'):
                raise ValueError('Campaign type mismatch')
            if r.kind == 'campaign':
                if r.parent_id is not None:
                    raise ValueError('Campaign cannot have parent')
            else:
                parent = resources.get((r.platform, r.account_id, r.parent_id))
                if not parent or parent.kind != allowed[r.kind] or parent.campaign_type != r.campaign_type:
                    raise ValueError('Invalid parent')
                if (r.kind == 'asset_group') != (r.campaign_type == 'pmax'):
                    raise ValueError('PMax uses asset groups in this contract')
            if r.budget_id and (r.platform, r.account_id, r.budget_id) not in budgets:
                raise ValueError('Unknown budget')
        for b in self.budgets:
            if (b.platform, b.account_id) not in accounts:
                raise ValueError('Unknown budget account')
            members = [r for r in self.resources if (r.platform, r.account_id, r.budget_id) == (b.platform, b.account_id, b.id)]
            if b.platform == 'meta':
                if b.shared or len(members) != 1 or members[0].id != b.owner_id or members[0].kind not in ('campaign', 'ad_set'):
                    raise ValueError('Meta budget must belong to campaign or ad set')
            elif b.owner_id is not None or not members or any(r.kind != 'campaign' for r in members) or (not b.shared and len(members) != 1):
                raise ValueError('Google budget membership invalid')
        for r in self.resources:
            chain = ancestry(r, resources)
            owners = sum(x.budget_id is not None for x in chain)
            if owners > 1 or (owners == 0 and not (r.platform == 'meta' and r.kind == 'campaign' and any(x.parent_id == r.id for x in self.resources if x.platform == r.platform and x.account_id == r.account_id))):
                raise ValueError('Each resource must resolve exactly one budget owner')
        grains = {}
        for platform, pages in self.pages.items():
            for page in pages:
                for report in page:
                    account = accounts.get((platform, report.account_id))
                    resource = resources.get((platform, report.account_id, report.resource_id))
                    if report.platform != platform or not account or not resource:
                        raise ValueError('Report identity mismatch')
                    # One additive grain only: Meta ads; Google Search ads,
                    # Shopping ad groups, PMax asset groups. Never mix parent totals.
                    leaf_kind = 'ad' if resource.campaign_type in ('meta', 'search') else 'asset_group' if resource.campaign_type == 'pmax' else 'ad_group'
                    if resource.kind != leaf_kind:
                        raise ValueError('Non-additive report grain')
                    start = report.interval_start
                    if start.second or start.microsecond or start.astimezone(timezone.utc).minute not in (0, 30) or report.reported_at < start + timedelta(minutes=30) or report.reported_at > self.observed_at:
                        raise ValueError('Invalid closed half-hour report interval')
                    if report.source_day != start.astimezone(ZoneInfo(account.timezone)).date().isoformat():
                        raise ValueError('Source timezone/day mismatch')
                    # Reject conflicting equal revisions even if a newer one arrived first.
                    key = (report.key, report.revision)
                    body = canonical(report.model_dump(mode='json'))
                    if key in grains and grains[key] != body:
                        raise ValueError('Conflicting report revision')
                    grains[key] = body
        return self


def ancestry(resource, resources):
    chain = [resource]
    while chain[-1].parent_id is not None:
        chain.append(resources[(resource.platform, resource.account_id, chain[-1].parent_id)])
    return chain


def hierarchy(fixture):
    resources = {(r.platform, r.account_id, r.id): r for r in fixture.resources}
    budgets = {(b.platform, b.account_id, b.id): b for b in fixture.budgets}
    result = []
    for r in fixture.resources:
        chain = ancestry(r, resources)
        owner = next((x for x in chain if x.budget_id), None)
        b = budgets[(r.platform, r.account_id, owner.budget_id)] if owner else None
        members = sorted(x.id for x in fixture.resources if b and (x.platform, x.account_id, x.budget_id) == (b.platform, b.account_id, b.id))
        affected = sorted({x.budget_id for x in fixture.resources if x.budget_id and (x.platform, x.account_id) == (r.platform, r.account_id) and r in ancestry(x, resources)})
        if b:
            affected = [b.id]
        result.append(dict(**r.model_dump(), campaign_id=chain[-1].id, effective_budget_id=b.id if b else None,
                           budget_owner_id=(b.owner_id or b.id) if b else None, shared_budget=b.shared if b else False, budget_members=members, affected_budget_ids=affected,
                           status_control_supported=True, budget_control_supported=bool(r.platform == 'meta' and owner and r.id == owner.id),
                           product_control_supported=False, mutation_enabled=False,
                           capability_evidence='synthetic contract only; live compatibility unverified',
                           unsupported_reason='Product-level controls unsupported; advisory only. Shared budget changes affect all member campaigns.' if b and b.shared else 'Product-level controls unsupported; advisory only. Budget control belongs to the resolved owner.'))
    return result


def budget_capabilities(fixture):
    return [dict(**b.model_dump(), budget_control_supported=True, mutation_enabled=False,
                 approval_required=True, capability_evidence='synthetic contract only; live compatibility unverified',
                 member_ids=sorted(r.id for r in fixture.resources if (r.platform, r.account_id, r.budget_id) == (b.platform, b.account_id, b.id))) for b in fixture.budgets]


class SyntheticReportingAdapter:
    """Read-only source simulation with PostgreSQL-persisted fetch cursor/state."""
    def __init__(self, platform):
        self.platform = platform

    def ingest(self, store, run, pages, after_page=None):
        with store.engine.begin() as conn:
            conn.execute(text('INSERT INTO ad_cursors(run_id,platform) VALUES (:run,:platform) ON CONFLICT DO NOTHING'), dict(run=run, platform=self.platform))
        with store.engine.connect() as conn:
            cursor = conn.execute(text('SELECT next_page FROM ad_cursors WHERE run_id=:run AND platform=:platform'), dict(run=run, platform=self.platform)).scalar_one()
        for index in range(cursor, len(pages)):
            with store.engine.begin() as conn:
                for report in pages[index]:
                    body = report.model_dump(mode='json')
                    existing = conn.execute(text('SELECT revision,body FROM ad_source_reports WHERE run_id=:run AND report_key=:key'), dict(run=run, key=report.key)).mappings().first()
                    if existing and existing['revision'] == report.revision and existing['body'] != body:
                        raise ValueError('Conflicting source revision')
                    conn.execute(text('''INSERT INTO ad_source_reports VALUES (:run,:key,:revision,CAST(:body AS JSONB))
                        ON CONFLICT(run_id,report_key) DO UPDATE SET revision=EXCLUDED.revision,body=EXCLUDED.body
                        WHERE ad_source_reports.revision < EXCLUDED.revision'''), dict(run=run, key=report.key, revision=report.revision, body=canonical(body)))
                conn.execute(text('UPDATE ad_cursors SET next_page=:next WHERE run_id=:run AND platform=:platform'), dict(next=index+1, run=run, platform=self.platform))
            if after_page:
                after_page(self.platform, index+1)


class MetaReportingAdapter(SyntheticReportingAdapter):
    def __init__(self):
        super().__init__('meta')


class GoogleReportingAdapter(SyntheticReportingAdapter):
    def __init__(self):
        super().__init__('google')


def import_ads(store, analytics, fixture_path=ROOT / 'fixtures/ads-corrected-v1.json', after_page=None):
    raw = fixture_path.read_bytes()
    fixture = AdFixture.model_validate_json(raw)
    digest = hashlib.sha256(raw).hexdigest()
    run = str(uuid5(NAMESPACE_URL, 'ads-schema-v2:' + digest))
    attempt = str(uuid4())
    with store.engine.connect() as lock:
        if not lock.execute(text('SELECT pg_try_advisory_lock(17012030)')).scalar():
            raise RuntimeError('Advertising import already running')
        lock.commit()
        try:
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE ad_attempts SET status='failed',error_code='worker_interrupted',finished_at=now() WHERE status='running'"))
                conn.execute(text('INSERT INTO ad_runs(id,version,fixture_hash,observed_at,scenario_clock) VALUES (:run,:version,:hash,:observed,:clock) ON CONFLICT DO NOTHING'), dict(run=run, version=fixture.version, hash=digest, observed=fixture.observed_at, clock=fixture.scenario_clock))
                conn.execute(text("INSERT INTO ad_attempts(id,run_id,status) VALUES (:id,:run,'running')"), dict(id=attempt, run=run))
            try:
                for adapter in (MetaReportingAdapter(), GoogleReportingAdapter()):
                    adapter.ingest(store, run, fixture.pages[adapter.platform], after_page)
                with store.engine.connect() as conn:
                    reports = [Report.model_validate_json(json.dumps(row)) for row in conn.execute(text('SELECT body FROM ad_source_reports WHERE run_id=:run ORDER BY report_key'), {'run': run}).scalars()]
                # Independent reconstruction verifies persisted revision state before load.
                expected = {}
                for pages in fixture.pages.values():
                    for page in pages:
                        for report in page:
                            if report.key not in expected or expected[report.key].revision < report.revision:
                                expected[report.key] = report
                if {r.key: r for r in reports} != expected:
                    raise ValueError('Source reconciliation failed')
                analytics.load_ads(run, fixture, reports)
                analytics.verify_ads(run, fixture, reports)
                with store.engine.begin() as conn:
                    conn.execute(text('UPDATE ad_runs SET finished_at=COALESCE(finished_at,now()) WHERE id=:run'), {'run': run})
                    conn.execute(text("UPDATE ad_attempts SET status='succeeded',finished_at=now() WHERE id=:id"), {'id': attempt})
                    conn.execute(text('INSERT INTO ad_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'), {'run': run})
            except Exception:
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE ad_attempts SET status='failed',error_code='ad_import_failed',finished_at=now() WHERE id=:id"), {'id': attempt})
                raise RuntimeError('Ad import failed; prior publication preserved') from None
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(17012030)'))
            lock.commit()
    return run
