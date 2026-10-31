"""Explicit approved execution against a durable local simulator only.

Intent, adapter receipt and read-back are separate commits. Retrying an interrupted
plan reconciles intent first and never resends an uncertain write. No live adapter.
"""
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from .commerce import SourceModel, canonical
from .contracts import AnalyticsUnavailable
from .attribution import Mapping, resolve_mapping


class ExecutionBlocked(ValueError):
    pass


class Change(SourceModel):
    platform: Literal['meta', 'google']
    account_id: str = Field(min_length=1, max_length=80)
    resource_id: str = Field(min_length=1, max_length=80)
    kind: Literal['status', 'budget']
    after: Literal['active', 'paused'] | int
    currency: Literal['INR'] = 'INR'

    @model_validator(mode='after')
    def valid(self):
        if self.kind == 'budget' and (type(self.after) is not int or not 0 <= self.after <= 10**12):
            raise ValueError('Budget requires integer paise')
        if self.kind == 'status' and self.after not in ('active', 'paused'):
            raise ValueError('Status requires active or paused')
        return self

    @property
    def key(self):
        return canonical([self.platform, self.account_id, self.kind, self.resource_id])


class Proposal(SourceModel):
    client_key: str = Field(min_length=1, max_length=100)
    action: Literal['pause', 'resume', 'throttle', 'transfer', 'recovery']
    changes: list[Change] = Field(min_length=1, max_length=2)
    recovery_of: str | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def shape(self):
        if len({c.key for c in self.changes}) != len(self.changes):
            raise ValueError('Duplicate resource')
        if self.action in ('pause', 'resume'):
            if len(self.changes) != 1 or self.changes[0].kind != 'status' or self.changes[0].after != ('paused' if self.action == 'pause' else 'active'):
                raise ValueError('Exact status change required')
        elif self.action == 'throttle':
            if len(self.changes) != 1 or self.changes[0].kind != 'budget':
                raise ValueError('One exact budget required for throttle')
        elif self.action == 'transfer':
            if len(self.changes) != 2 or any(c.kind != 'budget' for c in self.changes):
                raise ValueError('Two exact budget resources required')
        elif not self.recovery_of:
            raise ValueError('Recovery requires an actual partial action')
        return self


class Approval(SourceModel):
    digest: str = Field(pattern='^[a-f0-9]{64}$')
    approve: Literal[True]


class KillSwitch(SourceModel):
    stopped: bool


class ActionPlan(BaseModel):
    id: str
    actor: str
    client_key: str
    request: dict
    plan: dict
    digest: str
    status: Literal['proposed', 'approved', 'revalidating', 'executing', 'succeeded', 'partially_succeeded', 'failed', 'unknown', 'rejected', 'expired']
    created_at: datetime
    expires_at: datetime
    approved_by: str | None
    approved_at: datetime | None
    error_code: str | None
    steps: list[dict]
    events: list[dict]


class ActionLedger(BaseModel):
    simulated: Literal[True]
    kill_switch: bool
    plans: list[ActionPlan]


def now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@contextmanager
def execution_lock(store):
    # Same dependency locks as the importers, plus one execution lock. Conservative
    # global serialization is deliberate for this one-merchant prototype.
    with store.engine.connect() as conn:
        acquired = []
        try:
            for n in (17012028, 17012030, 17012031, 17012032, 17012033, 17012034, 17012035):
                if not conn.execute(text('SELECT pg_try_advisory_lock(:n)'), {'n': n}).scalar():
                    raise ExecutionBlocked('Execution or dependent import already running')
                acquired.append(n)
            conn.commit()
            yield
        finally:
            conn.rollback()
            for n in reversed(acquired):
                conn.execute(text('SELECT pg_advisory_unlock(:n)'), {'n': n})
            conn.commit()


def evidence(store, analytics):
    """Only real analytics may supply capabilities, mappings and stock features."""
    methods = dict(commerce=store.commerce_publication, ads=store.ad_publication,
                   attribution=store.attribution_publication, finance=store.finance_publication,
                   inventory=store.inventory_publication, diagnostics=store.diagnostics_publication)
    pubs = {k: m()[0] for k, m in methods.items()}
    if not all(pubs.values()):
        raise ExecutionBlocked('Missing evidence publication')
    for name, pub in pubs.items():
        for upstream in pubs:
            key = upstream + '_id'
            if key in pub and pub[key] != pubs[upstream]['id']:
                raise ExecutionBlocked('Pinned dependencies changed')
    at = now()
    for name in ('ads', 'inventory', 'diagnostics'):
        if not 0 <= (at - pubs[name]['observed_at']).total_seconds() <= 900:
            raise ExecutionBlocked('Stale ' + name + ' evidence')
    pins = {k: str(v['id']) for k, v in pubs.items()}
    ads = analytics.ad_data(pins['ads'])
    inventory = analytics.inventory_data(pins['inventory'], at=at, expected_finance=pins['finance'])
    diagnostics = analytics.diagnostics_data(pins['diagnostics'], at=at, expected_inventory=pins['inventory'])
    # ad_data/inventory_data/diagnostics_data verify retained typed source cores.
    mappings = [Mapping.model_validate_json(canonical(r)) for r in analytics.attribution_data(pins['attribution'])['mapping_evidence']]
    return dict(pins=pins, ads=ads, inventory=inventory, diagnostics=diagnostics,
                mappings=mappings, at=at, stock_states=pubs['inventory']['configuration']['resource_states'],
                source_deadline=min(pubs[k]['observed_at'] + timedelta(seconds=900) for k in ('ads', 'inventory', 'diagnostics')))


def evidence_deadline(ev, changes):
    """Bind the next clock boundary; queries and queueing cannot renew proof."""
    limits = [ev['source_deadline']]
    def timestamp(value):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    for c in changes:
        sc = c['scope'];identity = (c['platform'], c['account_id'])
        for p in ev['inventory']['products']:
            if p['product_id'] in sc['products']:
                limits.extend(timestamp(v['stock_observed_at']) + timedelta(seconds=min(900, ev['inventory']['assumptions']['freshness_seconds'])) for v in p['variants'])
        for s in ev['stock_states']:
            if (s['platform'], s['account_id']) == identity and s['resource_id'] in sc['members']:
                limits.append(timestamp(s['observed_at']) + timedelta(seconds=900))
        for m in ev['mappings']:
            if m.key[:2] == identity and m.resource_id in sc['members']:
                limits.extend(t for t in (m.valid_from, m.valid_to) if t > ev['at'])
        for r in ev['diagnostics']['recommendations']:
            if (r['platform'], r['account_id']) == identity and r['resource_id'] in sc['members']:
                for d in r['destinations']:
                    latest = max(d['evidence'], key=lambda x: timestamp(x['observed_at']))
                    limits.append(timestamp(latest['observed_at']) + timedelta(seconds=min(900, ev['diagnostics']['assumptions']['freshness_seconds'])))
                    if latest.get('offer_expires_at'):
                        limits.append(timestamp(latest['offer_expires_at']))
    return min(limits)


def scope(change, ev):
    key = (change.platform, change.account_id, change.resource_id)
    resources = ev['ads']['resources']
    shared = False
    if change.kind == 'status':
        rows = [r for r in resources if (r['platform'], r['account_id'], r['id']) == key]
        if not rows or not rows[0]['status_control_supported']:
            raise ExecutionBlocked('Exact status control unsupported')
        initial = rows[0]['status']
        affected = rows
    else:
        budgets = [b for b in ev['ads']['budgets'] if (b['platform'], b['account_id'], b['id']) == key]
        if not budgets or not budgets[0]['budget_control_supported']:
            raise ExecutionBlocked('Exact budget control unsupported')
        b = budgets[0]
        shared = b['shared']
        # Google budget is separate; Meta mutation must address its actual owner.
        affected = [r for r in resources if (r['platform'], r['account_id']) == key[:2] and r['id'] in b['member_ids']]
        initial = b['daily_paise']
    resolved = [resolve_mapping(ev['mappings'], (r['platform'], r['account_id'], r['id']), ev['at']) for r in affected]
    if not resolved or any(m['status'] != 'resolved' for m in resolved):
        raise ExecutionBlocked('Exact reviewed mapping unavailable for every member')
    products = sorted({p for m in resolved for p in m['products']})
    lock_keys = {canonical([change.platform, change.account_id, 'resource', r['id']]) for r in affected}
    budget_ids = {change.resource_id} if change.kind == 'budget' else {b for r in affected for b in r['affected_budget_ids']}
    lock_keys.update(canonical([change.platform, change.account_id, 'budget', b]) for b in budget_ids)
    return dict(initial=initial, products=products, mappings=resolved, shared=shared,
                members=sorted(r['id'] for r in affected), capability=affected, lock_keys=sorted(lock_keys))


def validate_policy(action, change, sc, ev):
    ps = [p for p in ev['inventory']['products'] if p['product_id'] in sc['products']]
    if len(ps) != len(sc['products']) or any(not p['fresh'] for p in ps):
        raise ExecutionBlocked('Missing or stale inventory')
    for member in sc['members']:
        states = [s for s in ev['stock_states'] if (s['platform'], s['account_id'], s['resource_id']) == (change.platform, change.account_id, member)]
        if not states or any(s['blockers'] or not 0 <= (ev['at'] - datetime.fromisoformat(s['observed_at'].replace('Z', '+00:00'))).total_seconds() <= 900 for s in states):
            raise ExecutionBlocked('Missing, blocked or stale simulated resource observation')
        ds = [r for r in ev['diagnostics']['recommendations'] if
              (r['platform'], r['account_id'], r['resource_id']) == (change.platform, change.account_id, member)]
        # Only the inventory condition supporting this protective reduction may
        # pass. Missing destinations and all other diagnostic/catalog blockers veto.
        supporting = {f'inventory {p}: {action}' for p in sc['products']} if action in ('pause', 'throttle') else set()
        if not ds or any(b not in supporting for r in ds for b in r['blockers']):
            raise ExecutionBlocked('Diagnostic or catalog blockers for exact member')
    if action == 'pause':
        if not all(p['pause_eligible'] for p in ps):
            raise ExecutionBlocked('Mixed or non-pause inventory scope; narrow control unsupported')
        return
    if action == 'throttle':
        if sc['shared'] or not all(p['throttle_eligible'] for p in ps):
            raise ExecutionBlocked('Exact unshared all-product throttle required')
        return
    if action == 'resume' and not all(p['recovery_stock_eligible'] and p['risk'] == 'clear' for p in ps):
        raise ExecutionBlocked('Inventory recovery blockers')
    if any(p['risk'] != 'clear' for p in ps):
        raise ExecutionBlocked('Inventory blockers')


class Simulator:
    def __init__(self, store):
        self.store = store

    def inspect(self, key):
        with self.store.engine.connect() as conn:
            r = conn.execute(text('SELECT value,revision,last_request FROM simulated_resources WHERE resource_key=:k'), {'k': key}).mappings().first()
            if not r:
                raise ExecutionBlocked('Simulated state missing')
            return dict(r)

    def apply(self, request_id, change):
        # Durable external-state stand-in. Never accepts a write without executor
        # approval/expiry/kill checks in the same transaction as its receipt.
        with self.store.engine.begin() as conn:
            if conn.execute(text('SELECT stopped FROM execution_control WHERE singleton=1 FOR UPDATE')).scalar():
                raise ExecutionBlocked('Kill switch enabled')
            step = conn.execute(text('SELECT s.*,p.approved_at,p.expires_at,p.status,p.approved_by,p.plan AS approved_plan,p.digest AS approved_digest FROM action_steps s JOIN action_plans p ON p.id=s.plan_id WHERE request_id=:r FOR UPDATE'), {'r': request_id}).mappings().one()
            if not step['approved_at'] or not step['approved_by'] or step['status'] != 'executing' or step['expires_at'] <= now():
                raise ExecutionBlocked('Explicit current approval required')
            if step['intent'] != change:
                raise ExecutionBlocked('Approved intent mismatch')
            if digest(step['approved_plan']) != step['approved_digest'] or 'clock_valid_until' not in step['approved_plan']:
                raise ExecutionBlocked('Approved evidence deadline required')
            proof_deadline = datetime.fromisoformat(step['approved_plan']['clock_valid_until'])
            old_receipt = conn.execute(text('SELECT 1 FROM simulated_receipts WHERE request_id=:r'), {'r': request_id}).scalar()
            if old_receipt:
                return
            # Keep the verified donor unchanged through the recipient's atomic
            # write, including a merchant edit made after the earlier read-back.
            prior = conn.execute(text('SELECT resource_key,intent,request_id,outcome FROM action_steps WHERE plan_id=:p AND ordinal<:n ORDER BY ordinal'), dict(p=step['plan_id'], n=step['ordinal'])).mappings().all()
            for previous in prior:
                observed = conn.execute(text('SELECT value,revision,last_request FROM simulated_resources WHERE resource_key=:k FOR UPDATE'), {'k': previous['resource_key']}).mappings().one()
                expected = dict(value=previous['intent']['after'], revision=previous['intent']['before']['revision'] + 1, last_request=previous['request_id'])
                if previous['outcome'] != 'succeeded' or dict(observed) != expected:
                    raise ExecutionBlocked('Previously verified transfer resource changed')
            current = conn.execute(text('SELECT value,revision,last_request FROM simulated_resources WHERE resource_key=:k FOR UPDATE'), {'k': step['resource_key']}).mappings().one()
            if dict(current) != change['before']:
                raise ExecutionBlocked('Intervening simulated edit')
            after = dict(value=change['after'], revision=current['revision'] + 1, last_request=request_id)
            updated = conn.execute(text('UPDATE simulated_resources SET value=CAST(:v AS jsonb),revision=:n,last_request=:r,changed_at=now() WHERE resource_key=:k AND clock_timestamp()<:proof AND clock_timestamp()<:expiry'), dict(v=canonical(after['value']), n=after['revision'], r=request_id, k=step['resource_key'], proof=proof_deadline, expiry=step['expires_at'])).rowcount
            if not updated:
                raise ExecutionBlocked('Evidence or approval expired before atomic mutation')
            conn.execute(text('INSERT INTO simulated_receipts(request_id,resource_key,before_state,after_state) VALUES (:r,:k,CAST(:b AS jsonb),CAST(:a AS jsonb))'), dict(r=request_id, k=step['resource_key'], b=canonical(dict(current)), a=canonical(after)))


class Executor:
    def __init__(self, store, analytics, simulator=None):
        self.store, self.analytics = store, analytics
        self.sim = simulator or Simulator(store)

    def event(self, conn, pid, actor, event, detail=None):
        conn.execute(text('INSERT INTO action_events(plan_id,actor,event,detail) VALUES (:p,:a,:e,CAST(:d AS jsonb))'), dict(p=pid, a=actor, e=event, d=canonical(detail or {})))

    def get(self, pid):
        with self.store.engine.connect() as conn:
            r = conn.execute(text('SELECT * FROM action_plans WHERE id=:p'), {'p': pid}).mappings().first()
            if not r:
                raise ExecutionBlocked('Unknown plan')
            data = dict(r)
            data['id'] = str(data['id'])
            data['steps'] = [dict(s) for s in conn.execute(text('SELECT * FROM action_steps WHERE plan_id=:p ORDER BY ordinal'), {'p': pid}).mappings()]
            data['events'] = [dict(s) for s in conn.execute(text('SELECT actor,event,detail,recorded_at FROM action_events WHERE plan_id=:p ORDER BY id'), {'p': pid}).mappings()]
            return data

    def list(self):
        with self.store.engine.connect() as conn:
            ids = conn.execute(text('SELECT id FROM action_plans ORDER BY created_at DESC LIMIT 50')).scalars().all()
            stopped = conn.execute(text('SELECT stopped FROM execution_control WHERE singleton=1')).scalar()
        return dict(simulated=True, kill_switch=stopped, plans=[self.get(p) for p in ids])

    def kill(self, stopped, actor):
        with self.store.engine.begin() as conn:
            conn.execute(text('UPDATE execution_control SET stopped=:s,actor=:a,changed_at=now() WHERE singleton=1'), dict(s=stopped, a=actor))
            self.event(conn, None, actor, 'kill_switch', {'stopped': stopped})
        return self.list()

    def propose(self, request, actor):
        with execution_lock(self.store):
            with self.store.engine.connect() as conn:
                old = conn.execute(text('SELECT id,request FROM action_plans WHERE client_key=:k'), {'k': request.client_key}).mappings().first()
            if old:
                if old['request'] != request.model_dump(mode='json'):
                    raise ExecutionBlocked('Idempotency key reused with different terms')
                return self.get(old['id'])
            ev = evidence(self.store, self.analytics)
            changes = []
            for c in request.changes:
                sc = scope(c, ev)
                validate_policy(request.action, c, sc, ev)
                with self.store.engine.begin() as conn:
                    conn.execute(text('INSERT INTO simulated_resources(resource_key,value) VALUES (:k,CAST(:v AS jsonb)) ON CONFLICT DO NOTHING'), {'k': c.key, 'v': canonical(sc['initial'])})
                before = self.sim.inspect(c.key)
                if before['value'] == c.after:
                    raise ExecutionBlocked('No change requested')
                if request.action == 'throttle' and c.after >= before['value']:
                    raise ExecutionBlocked('Throttle must reduce the exact unshared budget')
                if request.action == 'resume':
                    self.require_pause(before, c.key)
                changes.append(dict(**c.model_dump(), key=c.key, before=before, scope=sc))
            if request.action == 'transfer':
                deltas = [c['after'] - c['before']['value'] for c in changes]
                if not deltas[0] < 0 < deltas[1] or sum(deltas) != 0:
                    raise ExecutionBlocked('Reduce donor first then increase recipient by equal integer INR paise')
            if request.action == 'recovery':
                self.require_recovery(request.recovery_of, changes)
            plan = dict(action=request.action, changes=changes, evidence=ev['pins'], reason=request.reason,
                        currency='INR', simulated=True, recovery_of=request.recovery_of,
                        clock_valid_until=evidence_deadline(ev, changes).isoformat())
            pid = str(uuid4())
            with self.store.engine.begin() as conn:
                conn.execute(text("INSERT INTO action_plans(id,actor,client_key,request,plan,digest,status,expires_at) VALUES (:p,:a,:k,CAST(:r AS jsonb),CAST(:v AS jsonb),:d,'proposed',:x)"), dict(p=pid, a=actor, k=request.client_key, r=canonical(request.model_dump(mode='json')), v=canonical(plan), d=digest(plan), x=now() + timedelta(minutes=30)))
                self.event(conn, pid, actor, 'proposed')
            return self.get(pid)

    def require_pause(self, before, key):
        with self.store.engine.connect() as conn:
            r = conn.execute(text("SELECT s.intent FROM action_steps s JOIN action_plans p ON p.id=s.plan_id WHERE s.request_id=:r AND s.resource_key=:k AND s.outcome='succeeded' AND p.approved_at IS NOT NULL"), dict(r=before['last_request'], k=key)).scalar()
        if before['value'] != 'paused' or not r or r['after'] != 'paused' or before['revision'] != r['before']['revision'] + 1:
            raise ExecutionBlocked('Resume requires a read-back-confirmed approved AdVergent pause with unchanged revision')

    def require_recovery(self, original, changes):
        try:
            UUID(original)
        except (ValueError, TypeError):
            raise ExecutionBlocked('Invalid original plan') from None
        old = self.get(original)
        successful = [s for s in old['steps'] if s['outcome'] == 'succeeded']
        if old['status'] != 'partially_succeeded' or old['plan']['action'] != 'transfer' or len(changes) != len(successful):
            raise ExecutionBlocked('Recovery requires exact successful portion of a partial plan')
        for c, s in zip(changes, successful, strict=True):
            expected = dict(value=s['intent']['after'], revision=s['intent']['before']['revision'] + 1, last_request=s['request_id'])
            if c['key'] != s['resource_key'] or c['before'] != expected or c['after'] != s['intent']['before']['value']:
                raise ExecutionBlocked('Recovery cannot overwrite a subsequent edit or change its approved inverse')

    def approve(self, pid, approval, actor):
        with self.store.engine.begin() as conn:
            row = conn.execute(text('SELECT * FROM action_plans WHERE id=:p FOR UPDATE'), {'p': pid}).mappings().first()
            if not row:
                raise ExecutionBlocked('Unknown plan')
            if row['digest'] != approval.digest or digest(row['plan']) != approval.digest:
                raise ExecutionBlocked('Exact displayed plan digest required')
            if row['status'] == 'proposed':
                status = 'expired' if row['expires_at'] <= now() else 'approved'
                conn.execute(text('UPDATE action_plans SET status=:s,approved_at=CASE WHEN :s=\'approved\' THEN now() ELSE NULL END,approved_by=:a WHERE id=:p'), dict(s=status, a=actor, p=pid))
                self.event(conn, pid, actor, status, {'digest': approval.digest})
        return self.get(pid)

    def finish(self, pid, status, error=None):
        with self.store.engine.begin() as conn:
            conn.execute(text('UPDATE action_plans SET status=:s,error_code=:e WHERE id=:p'), dict(s=status, e=error, p=pid))
            self.event(conn, pid, 'executor', status, {'error_code': error})
        return self.get(pid)

    def reject(self, pid, actor):
        with execution_lock(self.store):
            self.get(pid)
            with self.store.engine.begin() as conn:
                updated = conn.execute(text("UPDATE action_plans SET status='rejected',error_code='operator_rejected' WHERE id=:p AND status IN ('proposed','approved')"), {'p': pid}).rowcount
                if updated:
                    self.event(conn, pid, actor, 'operator_rejected')
        return self.get(pid)

    def reconcile(self, pid):
        """Read-back only. May run while killed, expired or analytics unavailable."""
        p = self.get(pid)
        for s in p['steps']:
            if s['outcome'] != 'unknown':
                continue
            try:
                actual = self.sim.inspect(s['resource_key'])
            except Exception:
                continue
            expected = dict(value=s['intent']['after'], revision=s['intent']['before']['revision'] + 1, last_request=s['request_id'])
            outcome = 'succeeded' if actual == expected else 'failed' if actual == s['intent']['before'] else 'unknown'
            with self.store.engine.begin() as conn:
                conn.execute(text('UPDATE action_steps SET outcome=:o,actual=CAST(:a AS jsonb),finished_at=now() WHERE plan_id=:p AND ordinal=:n'), dict(o=outcome, a=canonical(actual), p=pid, n=s['ordinal']))
                self.event(conn, pid, 'executor', 'read_back', {'request_id': s['request_id'], 'outcome': outcome, 'actual': actual})
        return self.get(pid)

    def execute(self, pid):
        with execution_lock(self.store):
            p = self.get(pid)
            if p['status'] in ('revalidating', 'executing', 'unknown'):
                # A crash/unknown retry reconciles only; new remaining mutations
                # need a new approval. No recovery silently spends stale consent.
                p = self.reconcile(pid)
                return self.finish(pid, self.result(p), 'reconciled_without_retry')
            if p['status'] != 'approved':
                return p
            if p['expires_at'] <= now():
                return self.finish(pid, 'expired')
            with self.store.engine.begin() as conn:
                conn.execute(text("UPDATE action_plans SET status='revalidating' WHERE id=:p"), {'p': pid})
                self.event(conn, pid, 'executor', 'revalidating')
            try:
                with self.store.engine.connect() as conn:
                    if conn.execute(text('SELECT stopped FROM execution_control WHERE singleton=1')).scalar():
                        raise ExecutionBlocked('Kill switch enabled')
                    # Unknown intents reserve their resources across process exit.
                    unresolved = conn.execute(text("SELECT s.resource_key,s.ordinal,p.plan FROM action_steps s JOIN action_plans p ON p.id=s.plan_id WHERE s.outcome='unknown' AND s.plan_id<>:p"), {'p': pid}).mappings().all()
                busy = {key for s in unresolved for key in s['plan']['changes'][s['ordinal']]['scope'].get('lock_keys', [s['resource_key']])}
                if any(set(c['scope']['lock_keys']) & busy for c in p['plan']['changes']):
                    raise ExecutionBlocked('Resource reserved by unresolved action')
                ev = evidence(self.store, self.analytics)
                if ev['pins'] != p['plan']['evidence']:
                    raise ExecutionBlocked('Evidence version changed; updated proposal required')
                for c in p['plan']['changes']:
                    model = Change.model_validate({k: c[k] for k in Change.model_fields})
                    sc = scope(model, ev)
                    if sc != c['scope']:
                        raise ExecutionBlocked('Mapping or capabilities changed')
                    validate_policy(p['plan']['action'], model, sc, ev)
                    if self.sim.inspect(c['key']) != c['before']:
                        raise ExecutionBlocked('Simulated state edited after proposal')
                    if p['plan']['action'] == 'resume':
                        self.require_pause(c['before'], c['key'])
                if p['plan']['action'] == 'recovery':
                    self.require_recovery(p['plan']['recovery_of'], p['plan']['changes'])
                if 'clock_valid_until' not in p['plan'] or now() >= datetime.fromisoformat(p['plan']['clock_valid_until']):
                    raise ExecutionBlocked('Evidence deadline passed during revalidation')
            except (ExecutionBlocked, AnalyticsUnavailable):
                return self.finish(pid, 'rejected', 'revalidation_failed')
            with self.store.engine.begin() as conn:
                conn.execute(text("UPDATE action_plans SET status='executing' WHERE id=:p"), {'p': pid})
                self.event(conn, pid, 'executor', 'revalidated', {'evidence': ev['pins']})
            for n, c in enumerate(p['plan']['changes']):
                # Re-evaluate wall clock and health before each mutation, including
                # recipient increase after donor read-back. All imports locked.
                try:
                    current = evidence(self.store, self.analytics)
                    model = Change.model_validate({k: c[k] for k in Change.model_fields})
                    validate_policy(p['plan']['action'], model, scope(model, current), current)
                    if p['expires_at'] <= now():
                        raise ExecutionBlocked('Approval expired')
                except (ExecutionBlocked, AnalyticsUnavailable):
                    return self.finish(pid, 'partially_succeeded' if n else 'rejected', 'step_revalidation_failed')
                rid = str(pid) + ':' + str(n)
                intent = dict(before=c['before'], after=c['after'])
                with self.store.engine.begin() as conn:
                    conn.execute(text("INSERT INTO action_steps(plan_id,ordinal,resource_key,request_id,intent,outcome) VALUES (:p,:n,:k,:r,CAST(:i AS jsonb),'unknown')"), dict(p=pid, n=n, k=c['key'], r=rid, i=canonical(intent)))
                    self.event(conn, pid, 'executor', 'intent', {'request_id': rid, 'before': c['before'], 'after': c['after']})
                try:
                    self.sim.apply(rid, intent)
                except Exception:
                    with self.store.engine.begin() as conn:
                        conn.execute(text("UPDATE action_steps SET error_code='adapter_response_error' WHERE request_id=:r"), {'r': rid})
                p = self.reconcile(pid)
                if p['steps'][-1]['outcome'] != 'succeeded':
                    break
            return self.finish(pid, self.result(self.get(pid)))

    @staticmethod
    def result(p):
        outcomes = [s['outcome'] for s in p['steps']]
        if 'unknown' in outcomes:
            return 'unknown'
        if len(outcomes) == len(p['plan']['changes']) and all(o == 'succeeded' for o in outcomes):
            return 'succeeded'
        return 'partially_succeeded' if 'succeeded' in outcomes else 'failed'
