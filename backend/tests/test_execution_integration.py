import os
from uuid import uuid4
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.execution import Executor, Simulator, Proposal, Approval, ExecutionBlocked, execution_lock
from advergent.execution_scenarios import prepare, restore
from advergent.api import create_app

pytestmark = pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1', reason='Dedicated real stores only')


def test_real_a12_a17_durable_approved_execution(tmp_path):
    settings = Settings.from_env();store = OperationalStore(settings.database_url);analytics = ExasolAnalytics(settings)
    store.migrate();ex = Executor(store, analytics)
    def request(action, changes, **kw):
        return Proposal(client_key=str(uuid4()), action=action, changes=changes, reason='Explicit synthetic acceptance test', **kw)
    def change(resource, kind='status', after='paused'):
        return dict(platform='meta', account_id='meta-inr', resource_id=resource, kind=kind, after=after)
    def approved(req, executor=ex):
        p = executor.propose(req, 'test operator')
        assert not p['approved_at'] and p['status'] == 'proposed'
        assert executor.execute(p['id'])['status'] == 'proposed'
        p = executor.approve(p['id'], Approval(digest=p['digest'], approve=True), 'test operator')
        assert p['status'] == 'approved'
        return p
    def edit(c, value):
        # Inject a later merchant-side edit; never an AdVergent approved write.
        from advergent.execution import Change
        from advergent.commerce import canonical
        with store.engine.begin() as conn:
            conn.execute(text('UPDATE simulated_resources SET value=CAST(:v AS jsonb),revision=revision+1,last_request=NULL WHERE resource_key=:k'), dict(v=canonical(value), k=Change(**c).key))
    try:
        names = prepare(store, analytics, 'pause')
        req = request('pause', [change(names['m-ad'])]);p = approved(req)
        assert ex.propose(req, 'test operator')['id'] == p['id']
        with pytest.raises(ExecutionBlocked):ex.propose(req.model_copy(update={'reason': 'changed'}), 'test operator')
        with pytest.raises(ExecutionBlocked):ex.approve(p['id'], Approval(digest='0' * 64, approve=True), 'test operator')
        result = ex.execute(p['id']);assert result['status'] == 'succeeded'
        assert result['steps'][0]['actual']['value'] == 'paused'
        assert ex.execute(p['id'])['steps'] == result['steps']
        assert ex.approve(p['id'], Approval(digest=p['digest'], approve=True), 'test operator')['status'] == 'succeeded'
        with store.engine.connect() as conn:
            assert conn.execute(text('SELECT COUNT(*) FROM simulated_receipts WHERE request_id=:r'), {'r': str(p['id']) + ':0'}).scalar() == 1
        # Persistent lock behavior across a second independent connection.
        with execution_lock(store):
            with ThreadPoolExecutor(1) as pool:
                with pytest.raises(ExecutionBlocked):pool.submit(ex.execute, p['id']).result()
        # Resume is not granted by imported provenance and cannot precede recovery.
        with pytest.raises(ExecutionBlocked):ex.propose(request('resume', [change(names['m-ad'], after='active')]), 'test operator')
        names = prepare(store, analytics, 'clear', tag=names['m-ad'].split('m-ad-')[1])
        p = approved(request('resume', [change(names['m-ad'], after='active')]))
        assert ex.execute(p['id'])['status'] == 'succeeded'
        # A12 second cycle used for expiry, kill and stale evidence checks.
        names = prepare(store, analytics, 'pause', tag=names['m-ad'].split('m-ad-')[1])
        p = approved(request('pause', [change(names['m-ad'])]))
        with store.engine.begin() as conn:conn.execute(text("UPDATE action_plans SET expires_at=now()-interval '1 second' WHERE id=:p"), {'p': p['id']})
        assert ex.execute(p['id'])['status'] == 'expired'
        expired = ex.propose(request('pause', [change(names['m-ad'])]), 'test operator')
        with store.engine.begin() as conn:conn.execute(text("UPDATE action_plans SET expires_at=now()-interval '1 second' WHERE id=:p"), {'p': expired['id']})
        expired = ex.approve(expired['id'], Approval(digest=expired['digest'], approve=True), 'test operator')
        assert expired['status'] == 'expired' and expired['approved_at'] is None
        p = approved(request('pause', [change(names['m-ad'])]));ex.kill(True, 'test operator')
        assert ex.execute(p['id'])['status'] == 'rejected';ex.kill(False, 'test operator')
        p = approved(request('pause', [change(names['m-ad'])]))
        names = prepare(store, analytics, 'pause', tag=names['m-ad'].split('m-ad-')[1])
        assert ex.execute(p['id'])['status'] == 'rejected'
        # A13 exact revision binding, including a later edit restored to same value.
        p = approved(request('pause', [change(names['m-ad'])]));edit(change(names['m-ad']), 'active')
        assert ex.execute(p['id'])['status'] == 'rejected'
        # Actual analytics availability checked at execute, not just proposal.
        p = approved(request('pause', [change(names['m-ad'])]))
        class Unavailable(ExasolAnalytics):
            def inventory_data(self, *args, **kw):
                from advergent.contracts import AnalyticsUnavailable
                raise AnalyticsUnavailable('injected adapter outage')
        assert Executor(store, Unavailable(settings)).execute(p['id'])['status'] == 'rejected'
        # A14 precise unequal-percentage transfer with successful donor and failed recipient.
        names = prepare(store, analytics, 'clear', tag=names['m-ad'].split('m-ad-')[1])
        budgets = {b['id']: b['daily_paise'] for b in analytics.ad_data(str(store.ad_publication()[0]['id']))['budgets']}
        donor, recipient = names['m-set-budget'], names['m-campaign-budget']
        transfer = request('transfer', [change(donor, 'budget', budgets[donor] - 12345), change(recipient, 'budget', budgets[recipient] + 12345)])
        stale = approved(transfer)
        edit(change(donor, 'budget', 0), budgets[donor] + 1)
        assert ex.execute(stale['id'])['status'] == 'rejected'
        edit(change(donor, 'budget', 0), budgets[donor])
        transfer = transfer.model_copy(update={'client_key': str(uuid4())})
        class RecipientFailure(Simulator):
            def apply(self, rid, intent):
                if rid.endswith(':1'):raise RuntimeError('synthetic recipient rejection')
                super().apply(rid, intent)
        partial_ex = Executor(store, analytics, RecipientFailure(store))
        p = approved(transfer, partial_ex);partial = partial_ex.execute(p['id'])
        assert partial['status'] == 'partially_succeeded'
        assert [s['actual']['value'] for s in partial['steps']] == [budgets[donor] - 12345, budgets[recipient]]
        # New explicit recovery approval; original partial execution grants none.
        recovery = approved(request('recovery', [change(donor, 'budget', budgets[donor])], recovery_of=p['id']))
        assert ex.execute(recovery['id'])['status'] == 'succeeded'
        class KillAfterDonor(Simulator):
            def apply(self, rid, intent):
                super().apply(rid, intent)
                ex.kill(True, 'test mid-transfer kill')
        killed_ex = Executor(store, analytics, KillAfterDonor(store))
        killed = approved(transfer.model_copy(update={'client_key': str(uuid4())}), killed_ex)
        assert killed_ex.execute(killed['id'])['status'] == 'partially_succeeded'
        ex.kill(False, 'test operator')
        recovery = approved(request('recovery', [change(donor, 'budget', budgets[donor])], recovery_of=killed['id']))
        assert ex.execute(recovery['id'])['status'] == 'succeeded'
        # A15 accepted write followed by timeout is resolved once by read-back.
        class Timeout(Simulator):
            def apply(self, rid, intent):
                super().apply(rid, intent);raise TimeoutError('response lost')
        timeout_ex = Executor(store, analytics, Timeout(store))
        p = approved(transfer.model_copy(update={'client_key': str(uuid4())}), timeout_ex)
        assert timeout_ex.execute(p['id'])['status'] == 'succeeded'
        assert len(timeout_ex.execute(p['id'])['steps']) == 2
        # Unknown read-back stays unknown, reserves resources and later reconciles.
        class Unknown(Simulator):
            lost = False
            def apply(self, rid, intent):
                super().apply(rid, intent);self.lost = True;raise TimeoutError()
            def inspect(self, key):
                if self.lost:raise TimeoutError('read-back unavailable')
                return super().inspect(key)
        unknown_sim = Unknown(store);unknown_ex = Executor(store, analytics, unknown_sim)
        reverse = request('transfer', [change(recipient, 'budget', budgets[recipient]), change(donor, 'budget', budgets[donor])])
        p = approved(reverse, unknown_ex);unknown = unknown_ex.execute(p['id']);assert unknown['status'] == 'unknown'
        unknown_sim.lost = False
        # New plan cannot write the unresolved donor, even with a new approval.
        blocked = approved(request('transfer', [change(recipient, 'budget', budgets[recipient] - 100), change(donor, 'budget', budgets[donor] - 12345 + 100)]))
        assert ex.execute(blocked['id'])['status'] == 'rejected'
        assert Executor(OperationalStore(settings.database_url), ExasolAnalytics(settings)).execute(p['id'])['status'] == 'partially_succeeded'
        # Reconciliation never increases the unattempted recipient. Explicit inverse.
        recovery = approved(request('recovery', [change(recipient, 'budget', budgets[recipient] + 12345)], recovery_of=p['id']))
        edit(change(recipient, 'budget', 0), budgets[recipient] + 12345)
        assert ex.execute(recovery['id'])['status'] == 'rejected'
        # Imported/merchant pause cannot replace approved execution history.
        edit(change(names['m-ad']), 'paused')
        with pytest.raises(ExecutionBlocked, match='approved AdVergent pause'):
            ex.propose(request('resume', [change(names['m-ad'], after='active')]), 'test operator')
        names = prepare(store, analytics, 'throttle', tag=names['m-ad'].split('m-ad-')[1])
        from advergent.execution import Change
        before = ex.sim.inspect(Change(**change(donor, 'budget', 0)).key)['value']
        throttle = approved(request('throttle', [change(donor, 'budget', before - 100)]))
        assert ex.execute(throttle['id'])['status'] == 'succeeded'
        # API authentication / origin / digest checks use durable actual ledger.
        token = 'execution-' + str(uuid4());store.login(token)
        try:
            client = TestClient(create_app(settings, store, analytics))
            assert client.get('/api/actions').status_code == 401
            client.cookies.set('advergent_session', token, path='/api')
            assert client.get('/api/actions').json()['simulated']
            assert client.post('/api/actions/kill-switch', json={'stopped': True}).status_code == 403
        finally:store.logout(token)
    finally:
        ex.kill(False, 'test cleanup')
        restore(store, analytics)


def test_real_operator_withdrawal_and_atomic_evidence_deadline(monkeypatch):
    settings = Settings.from_env();store = OperationalStore(settings.database_url);a = ExasolAnalytics(settings)
    token = 'withdrawal-' + str(uuid4());headers = {'Origin': settings.origin, 'X-AdVergent-Request': '1'}
    try:
        names = prepare(store, a, 'pause')
        client = TestClient(create_app(settings, store, a))
        assert client.post('/api/actions/' + str(uuid4()) + '/reject', json={}, headers=headers).status_code == 401
        store.login(token);client.cookies.set('advergent_session', token, path='/api')
        response = client.post('/api/actions/propose', json=dict(client_key=str(uuid4()), action='pause', reason='Explicit withdrawal acceptance', changes=[dict(platform='meta', account_id='meta-inr', resource_id=names['m-ad'], kind='status', after='paused')]), headers=headers)
        assert response.status_code == 200;plan = response.json();pid = plan['id']
        response = client.post(f'/api/actions/{pid}/approve', json={'digest': plan['digest'], 'approve': True}, headers=headers)
        assert response.json()['status'] == 'approved'
        response = client.post(f'/api/actions/{pid}/reject', json={}, headers=headers)
        assert response.json()['status'] == 'rejected' and response.json()['approved_at']
        # A newly constructed executor sees withdrawal and performs no writes.
        result = Executor(OperationalStore(settings.database_url), ExasolAnalytics(settings)).execute(pid)
        assert result['status'] == 'rejected' and result['steps'] == []
        with store.engine.connect() as conn:
            assert conn.execute(text('SELECT COUNT(*) FROM simulated_receipts WHERE request_id=:r'), {'r': pid + ':0'}).scalar() == 0
        assert any(e['event'] == 'operator_rejected' for e in result['events'])
        # A deliberately short, explicitly approved proof crosses its deadline
        # inside the adapter after revalidation. Actual SQL must perform no write.
        import advergent.execution as module
        import time
        from datetime import timedelta
        verified = module.evidence(store, a);real_deadline = module.evidence_deadline
        monkeypatch.setattr(module, 'evidence', lambda *_: verified)
        monkeypatch.setattr(module, 'evidence_deadline', lambda *_: module.now() + timedelta(seconds=1))
        class Delayed(Simulator):
            def apply(self, rid, intent):
                time.sleep(2);super().apply(rid, intent)
        ex = Executor(store, a, Delayed(store))
        req = Proposal(client_key=str(uuid4()), action='pause', reason='Explicit short-proof expiry acceptance', changes=[dict(platform='meta', account_id='meta-inr', resource_id=names['m-ad'], kind='status', after='paused')])
        p = ex.propose(req, 'test operator');ex.approve(p['id'], Approval(digest=p['digest'], approve=True), 'test operator')
        failed = ex.execute(p['id']);assert failed['status'] == 'failed'
        assert failed['steps'][0]['actual']['value'] == 'active' and failed['steps'][0]['actual']['revision'] == 0
        with store.engine.connect() as conn:
            assert conn.execute(text('SELECT COUNT(*) FROM simulated_receipts WHERE request_id=:r'), {'r': p['id'] + ':0'}).scalar() == 0
        # Normal clock-bound proof permits exactly one approved mutation.
        monkeypatch.setattr(module, 'evidence_deadline', real_deadline)
        normal = Executor(store, a);p = normal.propose(req.model_copy(update={'client_key': str(uuid4())}), 'test operator')
        normal.approve(p['id'], Approval(digest=p['digest'], approve=True), 'test operator')
        assert normal.execute(p['id'])['status'] == 'succeeded'
        # Recipient application must also lock/check the previously verified
        # donor, including a merchant edit after donor read-back.
        monkeypatch.undo()
        names = prepare(store, a, 'clear', tag=names['m-ad'].split('m-ad-')[1])
        donor, recipient = names['m-set-budget'], names['m-campaign-budget']
        budgets = {b['id']: b['daily_paise'] for b in a.ad_data(str(store.ad_publication()[0]['id']))['budgets']}
        from advergent.execution import Change
        from advergent.commerce import canonical
        def transfer(executor, delta):
            req = Proposal(client_key=str(uuid4()), action='transfer', reason='Explicit donor revalidation acceptance', changes=[dict(platform='meta', account_id='meta-inr', resource_id=donor, kind='budget', after=budgets[donor]-delta), dict(platform='meta', account_id='meta-inr', resource_id=recipient, kind='budget', after=budgets[recipient]+delta)])
            p = executor.propose(req, 'test operator');executor.approve(p['id'], Approval(digest=p['digest'], approve=True), 'test operator')
            return executor.execute(p['id'])
        assert transfer(Executor(store, a), 100)['status'] == 'succeeded'
        donor_key = Change(platform='meta', account_id='meta-inr', resource_id=donor, kind='budget', after=0).key
        class LateMerchantEdit(Simulator):
            def apply(self, rid, intent):
                if rid.endswith(':1'):
                    current = self.inspect(donor_key)
                    # External merchant-side fixture edit, not an AdVergent write.
                    with store.engine.begin() as conn:
                        conn.execute(text('UPDATE simulated_resources SET value=CAST(:v AS jsonb),revision=revision+1,last_request=NULL WHERE resource_key=:k'), dict(v=canonical(current['value']+1), k=donor_key))
                super().apply(rid, intent)
        partial = transfer(Executor(store, a, LateMerchantEdit(store)), 200)
        assert partial['status'] == 'partially_succeeded'
        assert partial['steps'][1]['actual']['value'] == budgets[recipient]+100
        assert partial['steps'][1]['outcome'] == 'failed'
    finally:
        store.logout(token)
        restore(store, a)
