"""Read-only conflict policy and operational recommendation observations."""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import text
from fastapi.encoders import jsonable_encoder
from .commerce import SourceModel, canonical
from .budget import BudgetRequest
from .clearance import ClearanceRequest
from .execution import Change, ExecutionBlocked, digest, scope, validate_policy, evidence_deadline, execution_lock
from .attribution import Mapping
from .contracts import AnalyticsUnavailable


class TrackDecision(SourceModel):
    digest: str = Field(pattern='^[a-f0-9]{64}$')
    key: str = Field(min_length=1, max_length=500)
    action_id: str | None = Field(default=None,pattern='^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')


class UnifiedDecision(BaseModel):
    key: str
    platform: str
    account_id: str
    resource_id: str
    resource_kind: str
    advice: Literal['pause_review', 'throttle_review', 'recovery_review', 'budget_comparison', 'diagnostic_review', 'creative_review', 'abstain']
    products: list[str]
    members: list[str]
    blockers: list[str]
    suppressed: list[str]
    explanation: str
    evidence: dict
    change: dict | None = None
    approval_required: Literal[True] = True
    mutation_enabled: Literal[False] = False


class DecisionData(BaseModel):
    digest: str = ''
    valid_until: str | None
    decisions: list[UnifiedDecision]
    budget: dict
    context: dict
    proposal_validity: list[dict]
    tracked_validity: list[dict] = Field(default_factory=list)
    publishing_enabled: Literal[False] = False
    mutation_enabled: Literal[False] = False
    basis: str = 'Synthetic advisory decisions. Recorded action read-back is not a financial, causal or incremental-profit outcome. No recommendation grants approval.'


class DecisionSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'inputs_changed', 'analytics_unavailable']
    pins: dict[str, str] = Field(default_factory=dict)
    input_observations: dict[str, str] = Field(default_factory=dict)
    queried_at: str | None = None
    data: DecisionData | None = None


class DecisionObservation(BaseModel):
    digest: str
    resource_key: str
    snapshot: DecisionSnapshot
    recorded_at: datetime
    recorded_by: str = 'demo operator'
    linked_at: datetime | None = None
    action_id: UUID | None = None
    outcome: str
    action_steps: list[dict]
    financial_outcome_paise: None = None
    validity: Literal['unknown_until_current_query'] = 'unknown_until_current_query'
    basis: str


class DecisionHistory(BaseModel):
    observations: list[DecisionObservation]
    mutation_enabled: Literal[False] = False
    publishing_enabled: Literal[False] = False


def identity(platform, account, kind, resource):
    return canonical([platform, account, kind, resource])


def budget_identity(budget):
    # Meta budget IDs are distinct from their actual campaign/ad-set owner IDs.
    return identity(budget.platform,budget.account_id,'resource' if budget.platform=='meta' else 'budget',
                    budget.members[0] if budget.platform=='meta' and len(budget.members)==1 else budget.budget_id)


def resolve(ev, budget, context, state, plans, at):
    """No executor methods which create proposals, approvals or observations are used."""
    resources = ev['ads']['resources']
    inventory = {(r['platform'], r['account_id'], r['resource_id']): r for r in ev['inventory']['recommendations']}
    diagnostics = {(r['platform'], r['account_id'], r['resource_id']): r for r in ev['diagnostics']['recommendations']}
    globals_ = []
    if state['stopped']: globals_.append('kill switch enabled')
    if state['unresolved']: globals_.append('unresolved execution intents')
    fresh = at < ev['source_deadline'] and ev.get('sources_not_future',True)
    if not fresh: globals_.append('stale or future source evidence')
    rows = {}
    protective = set()
    limits = [datetime.fromisoformat(budget.valid_until)] if budget.valid_until else []
    # Include creative and product-context clock transitions as well as action proof.
    from datetime import timedelta
    limits.append(ev['source_deadline'])
    for rec in ev['diagnostics']['recommendations']:
        for window in rec.get('fatigue',[]):
            for obs in window['evidence']:
                limits.append(datetime.fromisoformat(obs['end'])+timedelta(seconds=min(900,ev['diagnostics']['assumptions']['freshness_seconds'])))
    breakout = context.get('breakout',{})
    for name in ('source_observed_at','signal_end'):
        if breakout.get(name): limits.append(datetime.fromisoformat(breakout[name])+timedelta(seconds=900))
    if breakout.get('evaluation_end'): limits.append(datetime.fromisoformat(breakout['evaluation_end']))
    for r in resources:
        key = (r['platform'], r['account_id'], r['id'])
        inv, diag = inventory.get(key), diagnostics.get(key)
        products = inv['affected_products'] if inv else []
        reasons = list(globals_) + (inv['blockers'] if inv else ['inventory resource evidence missing'])
        advice, change = 'abstain', None
        suppressed = []
        risk = inv and inv['action'] in ('pause', 'throttle', 'advisory')
        if risk: protective.add(key)
        if inv and inv['action'] in ('pause', 'throttle', 'recovery'):
            action = 'resume' if inv['action'] == 'recovery' else inv['action']
            c = Change(platform=r['platform'], account_id=r['account_id'], resource_id=r['id'], kind='status', after='paused' if action == 'pause' else 'active')
            if action == 'throttle':
                # There is no calibrated exact protective amount; preserve the review.
                c = Change(platform=r['platform'], account_id=r['account_id'], resource_id=r['effective_budget_id'] or r['id'], kind='budget', after=0)
            try:
                if reasons or inv['eligibility'] != 'eligible': raise ExecutionBlocked('inventory advice is not exact-resource eligible')
                sc = scope(c, ev)
                validate_policy(action, c, sc, ev)
                before = state['resources'].get(c.key)
                value = before['value'] if before else sc['initial']
                if action == 'resume':
                    # Only recorded, approved pause with unchanged read-back can recover.
                    pauses = [s for p in plans if p['approved_at'] for s in p['steps']
                        if s['resource_key'] == c.key and s['outcome'] == 'succeeded' and s['request_id'] == (before or {}).get('last_request')
                        and s['intent']['after'] == 'paused' and before['revision'] == s['intent']['before']['revision'] + 1]
                    if not pauses or value != 'paused': raise ExecutionBlocked('durable approved pause read-back missing or changed')
                if action == 'pause' and value != 'active': raise ExecutionBlocked('resource already paused')
                deadline = evidence_deadline(ev, [dict(**c.model_dump(), scope=sc)])
                limits.append(deadline)
                if at >= deadline: raise ExecutionBlocked('evidence clock boundary reached')
                advice = {'pause':'pause_review', 'throttle':'throttle_review', 'resume':'recovery_review'}[action]
                if action != 'throttle': change = dict(**c.model_dump(), key=c.key, before=before or dict(value=sc['initial'],revision=0,last_request=None), scope=sc)
            except ExecutionBlocked as exc:
                reasons.append(str(exc))
        elif diag and diag['blockers']:
            advice = 'diagnostic_review' if not reasons else 'abstain'
        elif diag and diag['suggestions'] and not reasons:
            advice = 'creative_review'
        if diag: reasons += diag['blockers']
        if risk and diag and diag['suggestions']: suppressed.append('creative review: inventory precedence')
        rowkey = identity(*key[:2], 'resource', key[2])
        rows[rowkey] = UnifiedDecision(key=rowkey, platform=key[0], account_id=key[1], resource_id=key[2], resource_kind='resource',
            advice=advice, products=products, members=[key[2]], blockers=sorted(set(reasons)), suppressed=suppressed,
            explanation='Inventory protection precedes growth and recovery; exact scope and current evidence are required.' if risk else 'Delivered module evidence determines advice; unknown or stale evidence abstains.',
            evidence=dict(inventory=inv, diagnostics=diag), change=change)
    # Expand risk through hierarchy and whole-budget membership. Withhold every leg
    # together rather than leaving an unmatched donor or recipient.
    conflict = False
    related_by_budget = {}
    for b in budget.rows:
        related = {r['id'] for r in resources if (r['platform'], r['account_id']) == (b.platform, b.account_id)
                   and (r['effective_budget_id'] == b.budget_id or r['id'] in b.members)}
        for r in resources:
            if (r['platform'], r['account_id']) != (b.platform, b.account_id): continue
            child = r
            while child['parent_id']:
                parent = next(x for x in resources if (x['platform'], x['account_id'], x['id']) == (b.platform, b.account_id, child['parent_id']))
                if r['id'] in related: related.add(parent['id'])
                child = parent
        related_by_budget[b.key] = related
        if b.allocated_paise != b.current_paise and any((b.platform,b.account_id,rid) in protective for rid in related): conflict = True
        owner = rows.get(budget_identity(b))
        if b.allocated_paise != b.current_paise and (globals_ or b.blockers or (owner and (owner.blockers or owner.advice in ('pause_review','throttle_review','recovery_review','diagnostic_review')))): conflict = True
    allocations = []
    for b in budget.rows:
        allocated = b.current_paise if conflict else b.allocated_paise
        allocations.append(dict(key=b.key, current_paise=b.current_paise, allocated_paise=allocated))
        key = budget_identity(b)
        row = rows.get(key)
        if not row:
            row = UnifiedDecision(key=key,platform=b.platform,account_id=b.account_id,resource_id=b.budget_id,resource_kind='budget',
                advice='abstain',products=b.products,members=b.members,blockers=[],suppressed=[],explanation='Whole-budget fixed-total comparison; an unsafe baseline is not endorsed.',evidence={})
            rows[key] = row
        row.products = sorted(set(row.products + b.products))
        row.members = sorted(set(row.members + b.members))
        row.evidence['budget'] = b.model_dump(mode='json')
        row.blockers = sorted(set(row.blockers + b.blockers + globals_))
        if b.allocated_paise != b.current_paise:
            if conflict or row.advice in ('pause_review','throttle_review','recovery_review','diagnostic_review') or row.blockers:
                row.suppressed.append('budget allocation: conflicting protection or evidence')
            else:
                row.advice = 'budget_comparison'
                row.change = dict(platform=b.platform,account_id=b.account_id,kind='budget',resource_id=b.budget_id,
                    currency='INR',after=allocated,key=b.key,before=b.state or dict(value=b.current_paise,revision=0,last_request=None))
    # Hierarchy protection must also suppress a child recovery/creative suggestion.
    for row in rows.values():
        overlap = any((row.platform,row.account_id,rid) in protective for b in budget.rows
            if (b.platform,b.account_id)==(row.platform,row.account_id) and (row.resource_id in related_by_budget[b.key] or row.resource_id==b.budget_id)
            for rid in related_by_budget[b.key])
        if overlap and row.advice in ('recovery_review','creative_review'):
            row.suppressed.append(row.advice+': related inventory protection')
            row.advice, row.change = 'abstain', None
    ordered = sorted(rows.values(),key=lambda r:r.key)
    valid_until = min((t for t in limits if t >= at), default=None)
    if budget.valid_until:
        inherited = datetime.fromisoformat(budget.valid_until)
        valid_until = min(valid_until,inherited) if valid_until else inherited
    proposals = [proposal_validity(p, ev['pins'],state,ordered,at) for p in plans if p['status'] in ('proposed','approved','revalidating','executing','unknown')]
    result = DecisionData(valid_until=valid_until.isoformat() if valid_until else None, decisions=ordered,
        budget=dict(total_paise=budget.total_paise, allocated_total_paise=sum(r['allocated_paise'] for r in allocations),
            allocations=allocations, allocation_withheld=conflict, change_bps=budget.terms.change_bps,
            conservative_delta_paise=None if conflict else budget.conservative_delta_paise), context=context,proposal_validity=proposals)
    result.digest = digest(dict(pins=ev['pins'],state=state,decisions=[r.model_dump(mode='json') for r in ordered],
        budget=result.budget,context=context,valid_until=result.valid_until))
    return result


def proposal_validity(plan, pins, state, decisions, at):
    reasons = []
    body = plan['plan']
    if body['evidence'] != pins: reasons.append('publication pins changed')
    if at >= plan['expires_at']: reasons.append('approval/proposal expired')
    if not body.get('clock_valid_until') or at >= datetime.fromisoformat(body['clock_valid_until']): reasons.append('proof clock expired or absent')
    if state['stopped']: reasons.append('kill switch enabled')
    if state['unresolved']: reasons.append('unresolved execution intents')
    for c in body['changes']:
        if state['resources'].get(c['key']) != c['before']: reasons.append('durable state or revision changed')
        if not any(r.change and r.change['key'] == c['key'] and r.change['after'] == c['after'] for r in decisions): reasons.append('current unified advice does not support exact change')
    return dict(action_id=str(plan['id']),recorded_status=plan['status'],validity='invalidated' if reasons else 'requires_phase8_revalidation',reasons=sorted(set(reasons)))


class DecisionService:
    def __init__(self, store, analytics, executor):
        self.store, self.analytics, self.executor = store, analytics, executor

    def plans(self):
        with self.store.engine.connect() as conn:
            ids = conn.execute(text('SELECT id FROM action_plans ORDER BY created_at,id')).scalars().all()
        return [self.executor.get(str(pid)) for pid in ids]

    def query(self):
        methods = {k:getattr(self.store, ('ad' if k=='ads' else k)+'_publication') for k in ('commerce','ads','attribution','finance','inventory','diagnostics')}
        pubs = {k:m()[0] for k,m in methods.items()}
        if not all(pubs.values()): return DecisionSnapshot(status='not_loaded')
        pins = {k:str(p['id']) for k,p in pubs.items()}
        evidence = dict(pins=pins,input_observations={k:p['observed_at'].isoformat() for k,p in pubs.items()})
        if any(p.get(k+'_id',u['id']) != u['id'] for p in pubs.values() for k,u in pubs.items()): return DecisionSnapshot(status='inputs_changed',**evidence)
        state, plans = self.store.budget_state(), self.plans()
        ledger_hash = digest(jsonable_encoder(plans))
        at = datetime.now(timezone.utc)
        try:
            a = self.analytics
            budget = a.budget_data(pins,at,BudgetRequest(),pubs,state)
            ads = a.ad_data(pins['ads'])
            inv = a.inventory_data(pins['inventory'],at=at,expected_finance=pins['finance'])
            diag = a.diagnostics_data(pins['diagnostics'],at=at,expected_inventory=pins['inventory'])
            from datetime import timedelta
            ev = dict(pins=pins,ads=ads,inventory=inv,diagnostics=diag,at=at,
                mappings=[Mapping.model_validate_json(canonical(m)) for m in a.attribution_data(pins['attribution'])['mapping_evidence']],
                stock_states=pubs['inventory']['configuration']['resource_states'],
                source_deadline=min(pubs[k]['observed_at']+timedelta(seconds=900) for k in ('ads','inventory','diagnostics')))
            ev['sources_not_future'] = all(pubs[k]['observed_at']<=at for k in ('ads','inventory','diagnostics'))
            breakout = a.breakout_data(pins,at,True).model_dump(mode='json')
            clearance = a.clearance_data(pins['inventory'],pins['finance'],pins['commerce'],ClearanceRequest(),at,True).model_dump(mode='json')
            context = dict(cohorts=budget.cohort_context,breakout=breakout,clearance=clearance)
            data = resolve(ev,budget,context,state,plans,at)
            changed = any(not (p:=m()[0]) or str(p['id']) != pins[k] for k,m in methods.items())
            changed = changed or state != self.store.budget_state() or ledger_hash != digest(jsonable_encoder(self.plans()))
            changed = changed or bool(data.valid_until and datetime.now(timezone.utc)>=datetime.fromisoformat(data.valid_until))
            if changed: return DecisionSnapshot(status='inputs_changed',**evidence)
            data.tracked_validity = [dict(digest=r['digest'],key=r['resource_key'],validity='current' if r['digest']==data.digest else 'invalidated') for r in self.records()]
            return DecisionSnapshot(status='available',data=data,queried_at=at.isoformat(),**evidence)
        except AnalyticsUnavailable:
            return DecisionSnapshot(status='analytics_unavailable',**evidence)

    def records(self):
        with self.store.engine.connect() as conn:
            return [dict(r) for r in conn.execute(text('SELECT * FROM decision_observations ORDER BY recorded_at,digest,resource_key')).mappings()]

    def track(self, request):
        with execution_lock(self.store):
            return self._track(request)

    def _track(self, request):
        previous = next((r for r in self.records() if r['digest']==request.digest and r['resource_key']==request.key),None)
        if request.action_id:
            if not previous: raise ExecutionBlocked('Retained recommendation observation required before linking an action')
            snapshot = DecisionSnapshot.model_validate(previous['snapshot'])
        else:
            snapshot = self.query()
            if snapshot.status != 'available' or snapshot.data.digest != request.digest: raise ExecutionBlocked('Decision changed or unavailable; query again')
        row = next((r for r in snapshot.data.decisions if r.key==request.key),None)
        if row is None: raise ExecutionBlocked('Unknown decision resource')
        action = self.executor.get(str(request.action_id)) if request.action_id else None
        if action:
            # A new action must follow this observation. Linking past action history
            # to a newly computed scenario would fabricate adoption.
            if not previous or action['created_at'] < previous['recorded_at'] or not row.change:
                raise ExecutionBlocked('Action must follow a retained exact recommendation observation')
            supported = [r.change for r in snapshot.data.decisions if r.change]
            if action['plan']['evidence'] != snapshot.pins or not any(c['key']==row.change['key'] and c['after']==row.change['after'] and c['before']==row.change['before'] for c in action['plan']['changes']):
                raise ExecutionBlocked('Action does not match exact recommendation')
            if not all(any(c['key']==r['key'] and c['after']==r['after'] and c['before']==r['before'] for r in supported) for c in action['plan']['changes']):
                raise ExecutionBlocked('Every action leg must match the retained unified recommendation')
            if snapshot.data.valid_until and action['created_at']>=datetime.fromisoformat(snapshot.data.valid_until):
                raise ExecutionBlocked('Action was proposed after recommendation evidence expired')
        if not action and snapshot.data.valid_until and datetime.now(timezone.utc)>=datetime.fromisoformat(snapshot.data.valid_until):
            raise ExecutionBlocked('Evidence clock expired before recording')
        with self.store.engine.begin() as conn:
            # Operational history only; never writes action/simulator/control tables.
            if not request.action_id:
                saved = conn.execute(text('''INSERT INTO decision_observations(digest,resource_key,snapshot)
                    SELECT :d,:k,CAST(:s AS jsonb) WHERE CAST(:deadline AS timestamptz) IS NULL OR clock_timestamp()<CAST(:deadline AS timestamptz)
                    ON CONFLICT(digest,resource_key) DO UPDATE SET digest=EXCLUDED.digest RETURNING digest'''),
                    dict(d=request.digest,k=request.key,s=canonical(snapshot.model_dump(mode='json')),deadline=snapshot.data.valid_until)).scalar_one_or_none()
                if saved is None: raise ExecutionBlocked('Evidence expired before observation commit')
            if request.action_id:
                existing = conn.execute(text('SELECT action_id FROM decision_observations WHERE digest=:d AND resource_key=:k FOR UPDATE'),dict(d=request.digest,k=request.key)).scalar()
                if existing and str(existing)!=str(request.action_id): raise ExecutionBlocked('Existing action linkage is immutable')
                conn.execute(text('UPDATE decision_observations SET action_id=:a,linked_at=clock_timestamp() WHERE digest=:d AND resource_key=:k AND action_id IS NULL'),dict(a=str(request.action_id),d=request.digest,k=request.key))
        return self.history()

    def history(self):
        result = []
        for r in self.records():
            action = self.executor.get(str(r['action_id'])) if r['action_id'] else None
            result.append(dict(**r,outcome=action['status'] if action else 'not_observed',
                action_steps=action['steps'] if action else [],financial_outcome_paise=None,
                validity='unknown_until_current_query',basis='Explicitly linked durable action read-back only; financial effect and causal benefit unknown'))
        return dict(observations=result,mutation_enabled=False,publishing_enabled=False)
