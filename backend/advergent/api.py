import secrets
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Request, Response, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from .config import Settings
from .contracts import AnalyticsUnavailable, Login, Snapshot, CommerceSnapshot, AdSnapshot, AttributionSnapshot, AttributionData, FinanceSnapshot, InventorySnapshot, DiagnosticsSnapshot
from .commerce import Record, KINDS, canonical
from .exasol import ExasolAnalytics
from .operational import OperationalStore, ROOT
from .security import verify_password
from .execution import Executor, Proposal, Approval, KillSwitch, ExecutionBlocked, ActionLedger, ActionPlan
from uuid import UUID
from .clearance import ClearanceRequest, ClearanceSnapshot
from .breakout import BreakoutSnapshot
from .cohorts import CohortSnapshot
from .budget import BudgetRequest, BudgetSnapshot
from .decisions import DecisionService, DecisionSnapshot, TrackDecision, DecisionHistory
from pydantic import AwareDatetime


def create_app(settings=None, store=None, analytics=None):
    settings = settings or Settings.from_env()
    store = store or OperationalStore(settings.database_url)
    analytics = analytics or ExasolAnalytics(settings)
    app = FastAPI(title='AdVergent', version='0.3.0')
    executor = Executor(store, analytics)
    decision_service = DecisionService(store, analytics, executor)

    @app.exception_handler(ExecutionBlocked)
    async def action_blocked(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={'detail': str(exc)})

    @app.exception_handler(AnalyticsUnavailable)
    async def action_analytics_failure(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={'detail': 'Exasol evidence unavailable; action blocked'})

    @app.exception_handler(SQLAlchemyError)
    async def operational_failure(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={'detail': 'Operational database unavailable'})

    @app.middleware('http')
    async def protections(request: Request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and (request.headers.get('origin') != settings.origin or request.headers.get('x-advergent-request') != '1'):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={'detail': 'Same-origin request required'})
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; frame-ancestors 'none'"
        return response

    def authenticated(request: Request):
        token = request.cookies.get('advergent_session')
        if not token or not store.session(token):
            raise HTTPException(401, 'Authentication required')
        return token

    @app.post('/api/login', status_code=204)
    def login(body: Login, response: Response):
        if not verify_password(body.password, settings.password_hash):
            raise HTTPException(401, 'Invalid password')
        token = secrets.token_urlsafe(32)
        store.login(token)
        response.set_cookie('advergent_session', token, httponly=True, secure=settings.cookie_secure, samesite='strict', max_age=3600, path='/api')

    @app.post('/api/logout', status_code=204)
    def logout(response: Response, token=Depends(authenticated)):
        store.logout(token)
        response.delete_cookie('advergent_session', path='/api')

    @app.get('/api/session')
    def session(token=Depends(authenticated)) -> dict[str, str]:
        return {'operator': 'demo operator'}

    @app.get('/api/decisions', response_model=DecisionSnapshot)
    def decisions(token=Depends(authenticated)):
        return decision_service.query()

    @app.get('/api/decisions/history', response_model=DecisionHistory)
    def decision_history(token=Depends(authenticated)):
        return decision_service.history()

    @app.post('/api/decisions/track', response_model=DecisionHistory)
    def track_decision(body: TrackDecision, token=Depends(authenticated)):
        return decision_service.track(body)

    @app.get('/api/actions', response_model=ActionLedger)
    def actions(token=Depends(authenticated)):
        return executor.list()

    @app.post('/api/actions/propose', response_model=ActionPlan)
    def propose_action(body: Proposal, token=Depends(authenticated)):
        return executor.propose(body, 'demo operator')

    @app.post('/api/actions/kill-switch', response_model=ActionLedger)
    def kill_actions(body: KillSwitch, token=Depends(authenticated)):
        return executor.kill(body.stopped, 'demo operator')

    @app.post('/api/actions/{plan_id}/approve', response_model=ActionPlan)
    def approve_action(plan_id: UUID, body: Approval, token=Depends(authenticated)):
        return executor.approve(str(plan_id), body, 'demo operator')

    @app.post('/api/actions/{plan_id}/execute', response_model=ActionPlan)
    def execute_action(plan_id: UUID, token=Depends(authenticated)):
        return executor.execute(str(plan_id))

    @app.post('/api/actions/{plan_id}/reject', response_model=ActionPlan)
    def reject_action(plan_id: UUID, token=Depends(authenticated)):
        return executor.reject(str(plan_id), 'demo operator')

    @app.get('/api/foundation', response_model=Snapshot)
    def foundation(token=Depends(authenticated)):
        published, latest = store.publication()
        if published is None:
            return Snapshot(status='not_loaded', latest_refresh_status=latest)
        evidence = dict(dataset_id=published['dataset_id'], refresh_job_id=published['id'], dataset_version=published['dataset_version'], fixture_hash=published['fixture_hash'], published_at=published['finished_at'], latest_refresh_status=latest)
        try:
            metric = analytics.metric(str(published['dataset_id']))
            return Snapshot(status='available', metric=metric, queried_at=datetime.now(timezone.utc), **evidence)
        except AnalyticsUnavailable:
            return Snapshot(status='analytics_unavailable', **evidence)

    @app.get('/api/commerce', response_model=CommerceSnapshot)
    def commerce(token=Depends(authenticated)):
        published, latest = store.commerce_publication()
        progress = dict(latest_import_status=latest['status'], next_page=latest['next_page']) if latest else {}
        if published is None:
            return CommerceSnapshot(status='not_loaded', **progress)
        now = datetime.now(timezone.utc)
        age = max(0, int((now - published['observed_at']).total_seconds()))
        evidence = dict(dataset_id=published['id'], dataset_version=published['version'], fixture_hash=published['fixture_hash'], observed_at=published['observed_at'], scenario_clock=published['scenario_clock'], published_at=published['finished_at'], age_seconds=age, repair_count=published['repair_count'], **progress)
        try:
            totals = analytics.commerce_totals(str(published['id']))
            return CommerceSnapshot(status='available', totals=totals, queried_at=now, freshness='stale' if age > 900 else 'fresh', **evidence)
        except AnalyticsUnavailable:
            return CommerceSnapshot(status='analytics_unavailable', **evidence)

    @app.get('/api/commerce/records/{kind}', response_model=list[Record])
    def commerce_records(kind: str, dataset_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), token=Depends(authenticated)):
        if kind not in KINDS:
            raise HTTPException(404, 'Unknown commerce collection')
        published, _ = store.commerce_publication()
        if not published or str(published['id']) != dataset_id:
            raise HTTPException(409, 'Commerce publication changed; query again')
        try:
            return analytics.commerce_records(dataset_id, kind, limit, offset)
        except AnalyticsUnavailable:
            raise HTTPException(503, 'Commerce analytics unavailable') from None

    @app.get('/api/ads', response_model=AdSnapshot)
    def ads(token=Depends(authenticated)):
        published, latest = store.ad_publication()
        if published is None:
            return AdSnapshot(status='not_loaded', latest_import_status=latest)
        now = datetime.now(timezone.utc)
        age = max(0, int((now - published['observed_at']).total_seconds()))
        evidence = dict(dataset_id=published['id'], dataset_version=published['version'], fixture_hash=published['fixture_hash'], observed_at=published['observed_at'], scenario_clock=published['scenario_clock'], published_at=published['finished_at'], age_seconds=age, latest_import_status=latest)
        try:
            data = analytics.ad_data(str(published['id']))
            return AdSnapshot(status='available', data=data, queried_at=now, freshness='stale' if age > 900 else 'fresh', **evidence)
        except AnalyticsUnavailable:
            return AdSnapshot(status='analytics_unavailable', **evidence)

    @app.get('/api/attribution', response_model=AttributionSnapshot)
    def attribution(token=Depends(authenticated)):
        published, latest = store.attribution_publication()
        if not published:
            return AttributionSnapshot(status='not_loaded', latest_import_status=latest)
        commerce, _ = store.commerce_publication()
        ads, _ = store.ad_publication()
        current = bool(commerce and ads and commerce['id'] == published['commerce_id'] and ads['id'] == published['ads_id'])
        now = datetime.now(timezone.utc)
        age = max(0, int((now - published['observed_at']).total_seconds()))
        evidence = dict(dataset_id=published['id'], commerce_id=published['commerce_id'], ads_id=published['ads_id'], dataset_version=published['version'], fixture_hash=published['fixture_hash'], observed_at=published['observed_at'], published_at=published['finished_at'], latest_import_status=latest, dependencies_current=current, age_seconds=age)
        evidence['mapping_as_of'] = published['configuration']['observed_at']
        try:
            data = AttributionData.model_validate_json(canonical(analytics.attribution_data(str(published['id']))))
            return AttributionSnapshot(status='available', data=data, queried_at=now, freshness='stale' if age > 900 else 'fresh', **evidence)
        except AnalyticsUnavailable:
            return AttributionSnapshot(status='analytics_unavailable', **evidence)

    @app.get('/api/finance', response_model=FinanceSnapshot)
    def finance(token=Depends(authenticated)):
        published, latest = store.finance_publication()
        if not published:
            return FinanceSnapshot(status='not_loaded', latest_import_status=latest)
        now = datetime.now(timezone.utc)
        age = max(0, int((now-published['observed_at']).total_seconds()))
        current = True
        for method, key in ((store.commerce_publication,'commerce_id'), (store.ad_publication,'ads_id'), (store.attribution_publication,'attribution_id')):
            upstream = method()[0]
            current = current and bool(upstream and upstream['id']==published[key])
        config = published['configuration']
        evidence = dict(dataset_id=published['id'], commerce_id=published['commerce_id'], ads_id=published['ads_id'], attribution_id=published['attribution_id'],
            dataset_version=published['version'], fixture_hash=published['fixture_hash'], observed_at=published['observed_at'], published_at=published['finished_at'],
            input_observations={k:published[k] for k in ('commerce_observed_at','ads_observed_at','attribution_observed_at')},
            period_start=config['period_start'], as_of=config['as_of'], reserve_assumptions={k:config[k] for k in ('reserve_window_days','return_probability_bps','recovery_bps','future_return_fee_paise','reserve_source')},
            latest_import_status=latest, dependencies_current=current, age_seconds=age)
        try:
            data = analytics.finance_data(str(published['id']), tuple(str(published[k]) for k in ('commerce_id','ads_id','attribution_id')))
            return FinanceSnapshot(status='available', data=data, queried_at=now, freshness='stale' if age>900 else 'fresh', **evidence)
        except AnalyticsUnavailable:
            return FinanceSnapshot(status='analytics_unavailable', **evidence)

    @app.get('/api/inventory', response_model=InventorySnapshot)
    def inventory(token=Depends(authenticated)):
        published,latest=store.inventory_publication()
        if not published:return InventorySnapshot(status='not_loaded',latest_import_status=latest)
        now=datetime.now(timezone.utc)
        current=True
        for method,key in ((store.finance_publication,'finance_id'),(store.commerce_publication,'commerce_id'),(store.ad_publication,'ads_id'),(store.attribution_publication,'attribution_id')):
            upstream=method()[0]
            current=current and bool(upstream and upstream['id']==published[key])
        age=max(0,int((now-published['observed_at']).total_seconds()))
        evidence=dict(dataset_id=published['id'],finance_id=published['finance_id'],commerce_id=published['commerce_id'],ads_id=published['ads_id'],attribution_id=published['attribution_id'],
            dataset_version=published['version'],fixture_hash=published['fixture_hash'],observed_at=published['observed_at'],published_at=published['finished_at'],latest_import_status=latest,dependencies_current=current,age_seconds=age)
        try:
            data=analytics.inventory_data(str(published['id']),at=now,dependencies_current=current,expected_finance=str(published['finance_id']))
            limit=published['configuration'].get('freshness_seconds',900)
            return InventorySnapshot(status='available',data=data,queried_at=now,freshness='stale' if age>limit else 'fresh',**evidence)
        except AnalyticsUnavailable:
            return InventorySnapshot(status='analytics_unavailable',**evidence)

    @app.get('/api/diagnostics', response_model=DiagnosticsSnapshot)
    def diagnostics(token=Depends(authenticated)):
        published,latest=store.diagnostics_publication()
        if not published:return DiagnosticsSnapshot(status='not_loaded',latest_import_status=latest)
        now=datetime.now(timezone.utc)
        current=True
        for method,key in ((store.inventory_publication,'inventory_id'),(store.finance_publication,'finance_id'),(store.commerce_publication,'commerce_id'),(store.ad_publication,'ads_id'),(store.attribution_publication,'attribution_id')):
            upstream=method()[0]
            current=current and bool(upstream and upstream['id']==published[key])
        age=max(0,int((now-published['observed_at']).total_seconds()))
        evidence=dict(dataset_id=published['id'],inventory_id=published['inventory_id'],finance_id=published['finance_id'],commerce_id=published['commerce_id'],ads_id=published['ads_id'],attribution_id=published['attribution_id'],
            dataset_version=published['version'],fixture_hash=published['fixture_hash'],observed_at=published['observed_at'],published_at=published['finished_at'],latest_import_status=latest,dependencies_current=current,age_seconds=age)
        try:
            data=analytics.diagnostics_data(str(published['id']),at=now,dependencies_current=current,expected_inventory=str(published['inventory_id']))
            limit=published['configuration'].get('freshness_seconds',900)
            return DiagnosticsSnapshot(status='available',data=data,queried_at=now,freshness='stale' if age>limit else 'fresh',**evidence)
        except AnalyticsUnavailable:
            return DiagnosticsSnapshot(status='analytics_unavailable',**evidence)

    def budget_query(terms):
        methods = dict(inventory=store.inventory_publication, finance=store.finance_publication,
            commerce=store.commerce_publication, ads=store.ad_publication,
            attribution=store.attribution_publication, diagnostics=store.diagnostics_publication)
        pubs = {k: method()[0] for k, method in methods.items()}
        if not all(pubs.values()): return BudgetSnapshot(status='not_loaded')
        pins = {k: str(p['id']) for k,p in pubs.items()}
        evidence = dict(pins=pins, input_observations={k:p['observed_at'].isoformat() for k,p in pubs.items()}, dependencies_current=True)
        if any(p.get(k+'_id',upstream['id']) != upstream['id'] for p in pubs.values() for k,upstream in pubs.items()):
            evidence['dependencies_current'] = False
            return BudgetSnapshot(status='inputs_changed', **evidence)
        state = store.budget_state()
        now = datetime.now(timezone.utc)
        try:
            data = analytics.budget_data(pins, now, terms, pubs, state)
            changed = any(not (p := method()[0]) or str(p['id']) != pins[k] for k,method in methods.items())
            changed = changed or store.budget_state() != state
            changed = changed or bool(data.valid_until and datetime.now(timezone.utc) >= datetime.fromisoformat(data.valid_until))
            if changed:
                evidence['dependencies_current'] = False
                return BudgetSnapshot(status='inputs_changed', **evidence)
            return BudgetSnapshot(status='available', data=data, queried_at=now.isoformat(), **evidence)
        except AnalyticsUnavailable:
            return BudgetSnapshot(status='analytics_unavailable', **evidence)

    @app.get('/api/budget', response_model=BudgetSnapshot)
    def budget(token=Depends(authenticated)):
        return budget_query(BudgetRequest())

    @app.post('/api/budget/scenario', response_model=BudgetSnapshot)
    def budget_scenario(terms: BudgetRequest, token=Depends(authenticated)):
        return budget_query(terms)

    @app.get('/api/cohorts', response_model=CohortSnapshot)
    def cohorts(as_of: AwareDatetime | None = None, token=Depends(authenticated)):
        methods = dict(finance=store.finance_publication, commerce=store.commerce_publication,
                       ads=store.ad_publication, attribution=store.attribution_publication)
        pubs = {key: method()[0] for key, method in methods.items()}
        if not all(pubs.values()): return CohortSnapshot(status='not_loaded')
        finance = pubs['finance']
        pins = dict(finance=str(finance['id']), **{k: str(finance[k+'_id']) for k in ('commerce','ads','attribution')})
        current = all(str(pubs[k]['id']) == pins[k] for k in pins)
        current = current and all(pubs['attribution'][k+'_id'] == pubs[k]['id'] for k in ('commerce','ads'))
        evidence = dict(pins=pins, dependencies_current=current,
            input_observations={k: p['observed_at'].isoformat() for k, p in pubs.items() if str(p['id']) == pins[k]})
        if not current: return CohortSnapshot(status='inputs_changed', **evidence)
        now = datetime.now(timezone.utc)
        config = finance['configuration']
        cutoff = min(now, datetime.fromisoformat(config['as_of']), *(p['observed_at'] for p in pubs.values()))
        if as_of:
            if as_of > cutoff: raise HTTPException(422, 'as_of exceeds observed source coverage')
            cutoff = as_of
        if cutoff < datetime.fromisoformat(config['period_start']):
            raise HTTPException(422, 'as_of precedes available financial history')
        try:
            data = analytics.cohort_data(pins, cutoff, config['period_start'])
            if any(not (p := method()[0]) or p['id'] != pubs[k]['id'] for k, method in methods.items()):
                evidence['dependencies_current'] = False
                return CohortSnapshot(status='inputs_changed', **evidence)
            return CohortSnapshot(status='available', data=data, queried_at=now.isoformat(), **evidence)
        except AnalyticsUnavailable:
            return CohortSnapshot(status='analytics_unavailable', **evidence)

    def breakout_query():
        methods = dict(inventory=store.inventory_publication, finance=store.finance_publication,
                       commerce=store.commerce_publication, ads=store.ad_publication,
                       attribution=store.attribution_publication)
        publications = {key: method()[0] for key, method in methods.items()}
        if not all(publications.values()):
            return BreakoutSnapshot(status='not_loaded')
        inv = publications['inventory']
        current = all(p.get(key + '_id', upstream['id']) == upstream['id']
                      for p in publications.values() for key, upstream in publications.items())
        pins = {key: str(p['id']) for key, p in publications.items()}
        # Always query the inventory's exact pinned finance/catalog, even after upstream changes.
        pins.update({key: str(inv[key + '_id']) for key in ('finance', 'commerce', 'ads', 'attribution')})
        evidence = dict(pins=pins, dependencies_current=current,
                        input_observations={key: p['observed_at'].isoformat()
                                            for key, p in publications.items() if str(p['id']) == pins[key]})
        now = datetime.now(timezone.utc)
        try:
            data = analytics.breakout_data(pins, now, current)
            # A concurrent publication cannot make a result look current after its query.
            after = {key: method()[0] for key, method in methods.items()}
            changed = any(not after[key] or after[key]['id'] != publications[key]['id'] for key in methods)
            if changed:
                for row in data.ranking:
                    row.blockers.append('publication changed during query')
                    row.score = row.rank = None
                evidence['dependencies_current'] = False
            return BreakoutSnapshot(status='available', data=data, queried_at=now.isoformat(), **evidence)
        except AnalyticsUnavailable:
            return BreakoutSnapshot(status='analytics_unavailable', **evidence)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/api/breakout', response_model=BreakoutSnapshot)
    def breakout(token=Depends(authenticated)):
        return breakout_query()

    def clearance_query(body):
        methods = dict(inventory=store.inventory_publication, finance=store.finance_publication,
                       commerce=store.commerce_publication, ads=store.ad_publication,
                       attribution=store.attribution_publication)
        publications = {key: method()[0] for key, method in methods.items()}
        if not all(publications.values()):
            return ClearanceSnapshot(status='not_loaded')
        inv = publications['inventory']
        current = all(p.get(key + '_id', upstream['id']) == upstream['id']
                      for p in publications.values() for key, upstream in publications.items())
        pins = {key: str(p['id']) for key, p in publications.items()}
        # Always query the inventory's exact pinned finance/catalog, even after upstream changes.
        pins.update({key: str(inv[key + '_id']) for key in ('finance', 'commerce', 'ads', 'attribution')})
        evidence = dict(pins=pins, observed_at=inv['observed_at'].isoformat(), dependencies_current=current,
                        input_observations={key: p['observed_at'].isoformat()
                                            for key, p in publications.items() if str(p['id']) == pins[key]})
        now = datetime.now(timezone.utc)
        try:
            data = analytics.clearance_data(pins['inventory'], pins['finance'], pins['commerce'], body, now, current)
            # A concurrent publication cannot make a result look current after its query.
            after = {key: method()[0] for key, method in methods.items()}
            changed = any(not after[key] or after[key]['id'] != publications[key]['id'] for key in methods)
            if changed:
                data.evidence_blockers.append('publication changed during query')
                data.feasible = False
                evidence['dependencies_current'] = False
            return ClearanceSnapshot(status='available', data=data, queried_at=now.isoformat(), **evidence)
        except AnalyticsUnavailable:
            return ClearanceSnapshot(status='analytics_unavailable', **evidence)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/api/clearance', response_model=ClearanceSnapshot)
    def clearance(token=Depends(authenticated)):
        return clearance_query(ClearanceRequest())

    @app.post('/api/clearance/scenario', response_model=ClearanceSnapshot)
    def clearance_scenario(body: ClearanceRequest, token=Depends(authenticated)):
        return clearance_query(body)

    dist = ROOT / 'frontend/dist'
    if dist.exists():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
