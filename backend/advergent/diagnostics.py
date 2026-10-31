"""Deterministic diagnostic evidence and advisory policy; no network or model calls."""
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import text
from .commerce import SourceModel
from .attribution import Identity, resolve_mapping
from .operational import ROOT


class Check(Identity):
    id: str = Field(min_length=1, max_length=100)
    variant_id: str
    url: str = Field(min_length=1, max_length=2000)
    observed_at: AwareDatetime
    outcome: Literal['ok','not_found','timeout','server_error','redirect','bot_block']
    redirect_to: str | None = None
    page_variant_id: str | None = None
    page_price_paise: int | None = Field(default=None, ge=0)
    advertised_price_paise: int | None = Field(default=None, ge=0)
    currency: Literal['INR'] = 'INR'
    offer_expires_at: AwareDatetime | None = None
    page_text: str = Field(default='', max_length=2000)


class Window(Identity):
    id: str
    creative_id: str
    start: AwareDatetime
    end: AwareDatetime
    audience: str
    placement: str
    objective: str
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)

    @model_validator(mode='after')
    def interval(self):
        if self.end-self.start != timedelta(days=7) or self.clicks>self.impressions:
            raise ValueError('Closed seven-day window and valid clicks required')
        return self


class DiagnosticsFixture(SourceModel):
    version: str = Field(min_length=1, max_length=100)
    observed_at: AwareDatetime
    checks: list[Check] = Field(min_length=1)
    windows: list[Window]
    min_impressions: int = Field(default=1000, gt=0)
    min_clicks: int = Field(default=20, gt=0)
    ctr_drop_bps: int = Field(default=3000, ge=1, le=10000)
    repeat_failures: int = Field(default=2, ge=2)
    retry_spacing_seconds: int = Field(default=60, ge=1)
    freshness_seconds: int = Field(default=900, gt=0)

    @model_validator(mode='after')
    def valid(self):
        if self.observed_at>datetime.now(timezone.utc):raise ValueError('Future observation')
        for group in (self.checks,self.windows):
            if len({r.id for r in group})!=len(group):raise ValueError('Duplicate diagnostic evidence')
        if any(r.observed_at>self.observed_at for r in self.checks) or any(r.end>self.observed_at for r in self.windows):raise ValueError('Future evidence')
        attempts=[(r.key,r.variant_id,r.url,r.observed_at) for r in self.checks]
        if len(set(attempts))!=len(attempts):raise ValueError('Duplicate destination observation time')
        keys=[(r.key,r.creative_id,r.start,r.end) for r in self.windows]
        if len(set(keys))!=len(keys):raise ValueError('Duplicate creative window')
        return self


def destination(f, rows, variant, product, at):
    rows=sorted(rows,key=lambda r:r.observed_at)
    latest=rows[-1]
    status={'ok':'healthy','not_found':'uncertain_not_found','timeout':'uncertain_transient','server_error':'uncertain_transient','redirect':'redirect_review','bot_block':'uncertain_bot_block'}[latest.outcome]
    trailing=[]
    for r in reversed(rows):
        if r.outcome!='not_found':break
        if not trailing or (trailing[-1].observed_at-r.observed_at).total_seconds()>=f.retry_spacing_seconds:trailing.append(r)
    fresh=lambda r:0<=(at-r.observed_at).total_seconds()<=f.freshness_seconds
    if len(trailing)>=f.repeat_failures and all(fresh(r) for r in trailing[:f.repeat_failures]):status='confirmed_not_found'
    if product['status']=='archived':status='archived_product'
    if not fresh(latest):status='stale_evidence'
    price='not_checked'
    if latest.outcome=='ok':
        if latest.offer_expires_at is not None and latest.offer_expires_at<=at:price='expired_offer'
        elif latest.page_variant_id!=latest.variant_id:price='uncertain_variant'
        elif latest.page_price_paise is None or latest.advertised_price_paise is None:price='unknown_price'
        else:price='match' if latest.page_price_paise==latest.advertised_price_paise==variant['price_paise'] else 'variant_price_mismatch'
    if not fresh(latest):price='stale_evidence'
    return dict(variant_id=latest.variant_id,product_id=variant['product_id'],url=latest.url,status=status,price_status=price,
        catalog_price_paise=variant['price_paise'],catalog_status=product['status'],evidence=[r.model_dump(mode='json') for r in rows],fresh=fresh(latest))


def fatigue(f, rows, at):
    rows=sorted(rows,key=lambda r:r.start)
    status='insufficient_windows';before=after=None
    if len(rows)==2:
        b,c=rows
        comparable=b.end==c.start and (b.audience,b.placement,b.objective)==(c.audience,c.placement,c.objective)
        enough=all(r.impressions>=f.min_impressions and r.clicks>=f.min_clicks for r in rows)
        before=Decimal(b.clicks)/b.impressions if b.impressions else None
        after=Decimal(c.clicks)/c.impressions if c.impressions else None
        status='incomparable_windows' if not comparable else 'insufficient_evidence' if not enough else 'possible_fatigue' if after<=before*(10000-f.ctr_drop_bps)/10000 else 'no_fatigue_signal'
        if not 0<=(at-c.end).total_seconds()<=f.freshness_seconds:status='stale_evidence'
    return dict(creative_id=rows[0].creative_id,status=status,prior_ctr=str(before) if before is not None else None,current_ctr=str(after) if after is not None else None,evidence=[r.model_dump(mode='json') for r in rows],interpretation='Descriptive comparable-window CTR decline only; no causal or effectiveness claim')


def evaluate(f, variants, products, resources, mappings, inventory, at, current=True):
    result=[];stock={p['product_id']:p for p in inventory['products']}
    for resource in resources:
        key=(resource['platform'],resource['account_id'],resource['id'])
        checks=[r for r in f.checks if r.key==key];windows=[r for r in f.windows if r.key==key]
        if not checks and not windows:continue
        mapping=resolve_mapping(mappings,key,at);blockers=[]
        if mapping['status']!='resolved':blockers.append('reviewed mapping '+mapping['status'])
        if not current:blockers.append('pinned upstream publication changed')
        ds=[]
        for vid,url in sorted({(r.variant_id,r.url) for r in checks}):
            v=variants[vid]
            if v['product_id'] not in mapping['products']:blockers.append('destination outside exact reviewed product scope')
            ds.append(destination(f,[r for r in checks if r.variant_id==vid and r.url==url],v,products[v['product_id']],at))
        fs=[fatigue(f,[r for r in windows if r.creative_id==cid],at) for cid in sorted({r.creative_id for r in windows})]
        for pid in mapping['products']:
            if stock[pid]['risk']!='clear':blockers.append('inventory '+pid+': '+stock[pid]['risk'])
            if products[pid]['status']=='archived':blockers.append('archived catalog product '+pid)
        if any(d['status']!='healthy' or d['price_status'] not in ('match',) for d in ds):blockers.append('destination/price review required')
        if not ds:blockers.append('destination evidence missing')
        suggestions=[]
        # Only structured catalog fields enter fixed templates. Titles/page text stay evidence.
        if not blockers and any(r['status']=='possible_fatigue' for r in fs):
            for pid in mapping['products']:
                sizes=sorted({v['size'] for v in variants.values() if v['product_id']==pid})
                colors=sorted({v['color'] for v in variants.values() if v['product_id']==pid})
                suggestions.append(dict(product_id=pid,text='Consider a new size and color presentation for review.',facts=dict(sizes=sizes,colors=colors),basis='Pinned structured catalog attributes only; no invented discounts, scarcity, materials or performance promises'))
        result.append(dict(platform=key[0],account_id=key[1],resource_id=key[2],mapping=mapping,destinations=ds,fatigue=fs,suggestions=suggestions,
            catalog_evidence=[dict(product_id=p,**products[p]) for p in mapping['products']],blockers=sorted(set(blockers)),
            capability_evidence=resource['capability_evidence'],product_control_supported=resource['product_control_supported'],
            status_control_supported=resource['status_control_supported'],budget_control_supported=resource['budget_control_supported'],
            budget_id=resource['effective_budget_id'],shared_budget=resource['shared_budget'],budget_members=resource['budget_members'],
            unsupported_reason=resource['unsupported_reason'],
            advisory=True,approval_required=True,mutation_enabled=False))
    return dict(recommendations=result,assumptions={k:v for k,v in f.model_dump(mode='json').items() if k not in ('checks','windows')},evaluated_at=at.isoformat(),basis='Synthetic destination observations and creative counters; real Exasol typed joins/CTR queries. No crawling or generated model claims.')
def import_diagnostics(store, analytics, fixture_path=ROOT/'fixtures/diagnostics-v1.json'):
    raw=fixture_path.read_bytes();f=DiagnosticsFixture.model_validate_json(raw)
    digest=hashlib.sha256(raw).hexdigest()
    with store.engine.connect() as lock:
        acquired=[]
        try:
            for n in (17012028,17012030,17012031,17012032,17012033,17012034):
                if not lock.execute(text('SELECT pg_try_advisory_lock(:n)'),dict(n=n)).scalar(): raise RuntimeError('Dependent import already running')
                acquired.append(n)
            lock.commit()
            finance=store.inventory_publication()[0]
            if not finance: raise RuntimeError('Publish inventory first')
            for method,key in ((store.finance_publication,'finance_id'),(store.commerce_publication,'commerce_id'),(store.ad_publication,'ads_id'),(store.attribution_publication,'attribution_id')):
                upstream=method()[0]
                if not upstream or upstream['id']!=finance[key]: raise RuntimeError('Inventory inputs changed; republish dependencies first')
            fid=str(finance['id']);run=str(uuid5(NAMESPACE_URL,'diagnostics-v1:'+digest+fid));attempt=str(uuid4())
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE diagnostics_attempts SET status='failed',error_code='worker_interrupted',finished_at=now() WHERE status='running'"))
                conn.execute(text('INSERT INTO diagnostics_runs(id,version,fixture_hash,inventory_id,configuration,observed_at) VALUES (:id,:version,:hash,:fid,CAST(:config AS jsonb),:observed) ON CONFLICT(id) DO NOTHING'),dict(id=run,version=f.version,hash=digest,fid=fid,config=raw.decode(),observed=f.observed_at))
                conn.execute(text("INSERT INTO diagnostics_attempts(id,run_id,status) VALUES (:id,:run,'running')"),dict(id=attempt,run=run))
            try:
                analytics.load_diagnostics(run,fid,f)
                analytics.verify_diagnostics(run,f,fid)
                with store.engine.begin() as conn:
                    conn.execute(text('UPDATE diagnostics_runs SET finished_at=COALESCE(finished_at,now()) WHERE id=:id'),dict(id=run))
                    conn.execute(text("UPDATE diagnostics_attempts SET status='succeeded',finished_at=now() WHERE id=:id"),dict(id=attempt))
                    conn.execute(text('INSERT INTO diagnostics_publications VALUES (1,:run) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id'),dict(run=run))
            except Exception:
                with store.engine.begin() as conn:conn.execute(text("UPDATE diagnostics_attempts SET status='failed',error_code='diagnostics_failed',finished_at=now() WHERE id=:id"),dict(id=attempt))
                raise RuntimeError('Diagnostics failed; prior publication preserved') from None
            return run
        finally:
            for n in reversed(acquired):lock.execute(text('SELECT pg_advisory_unlock(:n)'),dict(n=n))
            lock.commit()
