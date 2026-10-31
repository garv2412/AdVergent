from copy import deepcopy
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from advergent.execution import Change, Proposal, Approval, ExecutionBlocked, validate_policy, scope, Executor, digest
from advergent.attribution import Mapping
from advergent.commerce import canonical


def test_exact_typed_terms_and_explicit_approval():
    for amount in (1.5, True, -1, '100.50', 10**12 + 1):
        with pytest.raises(ValidationError):
            Change(platform='meta', account_id='a', resource_id='b', kind='budget', after=amount)
    with pytest.raises(ValidationError):
        Approval(digest='a' * 64, approve=False)
    with pytest.raises(ValidationError):
        Proposal(client_key='k', action='resume', changes=[Change(platform='meta', account_id='a', resource_id='b', kind='status', after='paused')], reason='test')
    assert digest({'paise': 100}) != digest({'paise': 101})
    for field in ('resource', 'currency', 'evidence', 'revision'):
        assert digest({field: 'a'}) != digest({field: 'b'})


def ev():
    return dict(at=datetime.now(timezone.utc), stock_states=[], inventory={'products': [dict(product_id='p', fresh=True, pause_eligible=True, recovery_stock_eligible=False, risk='pause')]}, diagnostics={'recommendations': []})


@pytest.mark.parametrize('risk,fresh', [('clear', True), ('pause', False), ('uncertain', True), ('stale', False)])
def test_pause_never_broadens_to_unaffected_or_stale_product(risk, fresh):
    e = ev();e['inventory']['products'].append(dict(product_id='q', risk=risk, fresh=fresh, pause_eligible=False))
    with pytest.raises(ExecutionBlocked):
        validate_policy('pause', None, {'products': ['p', 'q'], 'members': []}, e)


def test_growth_and_resume_require_clear_fresh_diagnostics():
    c = Change(platform='meta', account_id='a', resource_id='r', kind='status', after='active')
    e = ev();sc = {'products': ['p'], 'members': ['r']}
    e['stock_states'] = [dict(platform='meta', account_id='a', resource_id='r', observed_at=e['at'].isoformat(), blockers=[])]
    with pytest.raises(ExecutionBlocked):validate_policy('resume', c, sc, e)


    e['inventory']['products'][0].update(risk='clear', recovery_stock_eligible=True)
    with pytest.raises(ExecutionBlocked, match='Diagnostic'):validate_policy('resume', c, sc, e)
    e['diagnostics']['recommendations'] = [dict(platform='meta', account_id='a', resource_id='r', blockers=[])]
    validate_policy('resume', c, sc, e)
    e['diagnostics']['recommendations'][0]['blockers'] = ['variant_price_mismatch']
    with pytest.raises(ExecutionBlocked):validate_policy('resume', c, sc, e)


def test_throttle_requires_unshared_whole_scope_condition():
    e = ev();e['inventory']['products'][0].update(risk='throttle', throttle_eligible=True)
    c = Change(platform='meta', account_id='a', resource_id='b', kind='budget', after=100)
    sc = {'products': ['p'], 'members': [], 'shared': False}
    validate_policy('throttle', c, sc, e)
    with pytest.raises(ExecutionBlocked):validate_policy('throttle', c, dict(sc, shared=True), e)


def test_protective_pause_still_obeys_destination_and_resource_blockers():
    e = ev();c = Change(platform='meta', account_id='a', resource_id='r', kind='status', after='paused')
    sc = {'products': ['p'], 'members': ['r']}
    e['stock_states'] = [dict(platform='meta', account_id='a', resource_id='r', observed_at=e['at'].isoformat(), blockers=[])]
    d = dict(platform='meta', account_id='a', resource_id='r', blockers=['inventory p: pause'])
    e['diagnostics']['recommendations'] = [d]
    validate_policy('pause', c, sc, e)
    d['blockers'].append('destination/price review required')
    with pytest.raises(ExecutionBlocked, match='Diagnostic'):validate_policy('pause', c, sc, e)
    d['blockers'] = ['inventory p: pause'];e['stock_states'][0]['blockers'] = ['merchant restriction']
    with pytest.raises(ExecutionBlocked, match='blocked'):validate_policy('pause', c, sc, e)


def test_shared_budget_requires_every_exact_member_mapping():
    c = Change(platform='google', account_id='a', resource_id='shared', kind='budget', after=100)
    e = ev();e.update(ads=dict(resources=[dict(platform='google', account_id='a', id=r, status='active', status_control_supported=True, affected_budget_ids=['shared']) for r in ('x', 'y')], budgets=[dict(platform='google', account_id='a', id='shared', budget_control_supported=True, shared=True, daily_paise=200, member_ids=['x', 'y'])]), mappings=[])
    m = dict(platform='google', account_id='a', resource_id='x', id='mapping', products=['p'], provenance='test', confidence_bps=9500, valid_from='2026-01-01T00:00:00Z', valid_to='2027-01-01T00:00:00Z', actor='test', reason='test')
    e['mappings'] = [Mapping.model_validate_json(canonical(m))]
    with pytest.raises(ExecutionBlocked, match='every member'):scope(c, e)
    e['mappings'].append(Mapping.model_validate_json(canonical(dict(m, id='second', resource_id='y'))))
    assert scope(c, e)['members'] == ['x', 'y']
    status = Change(platform='google', account_id='a', resource_id='x', kind='status', after='paused')
    assert set(scope(status, e)['lock_keys']) <= set(scope(c, e)['lock_keys'])


@pytest.mark.parametrize('outcomes,status', [(['succeeded'], 'partially_succeeded'), (['succeeded', 'failed'], 'partially_succeeded'), (['succeeded', 'unknown'], 'unknown'), (['failed'], 'failed'), (['succeeded', 'succeeded'], 'succeeded')])
def test_partial_and_unknown_never_report_success(outcomes, status):
    assert Executor.result(dict(steps=[dict(outcome=o) for o in outcomes], plan={'changes': [1, 2]})) == status


@pytest.mark.parametrize('source', ['ads', 'inventory', 'diagnostics'])
@pytest.mark.parametrize('age,allowed', [(900, True), (901, False), (-1, False)])
def test_actual_clock_freshness_boundary(monkeypatch, source, age, allowed):
    import advergent.execution as module
    at = datetime.now(timezone.utc);monkeypatch.setattr(module, 'now', lambda: at)
    class Store:
        pass
    store = Store()
    for name in ('commerce', 'ads', 'attribution', 'finance', 'inventory', 'diagnostics'):
        row = dict(id=name, observed_at=at - timedelta(seconds=age if name == source else 0), configuration={'resource_states': []})
        setattr(store, 'ad_publication' if name == 'ads' else name + '_publication', lambda r=row: (r, None))
    class Analytics:
        def ad_data(self, *a):return {}
        def inventory_data(self, *a, **k):return {}
        def diagnostics_data(self, *a, **k):return {}
        def attribution_data(self, *a):return {'mapping_evidence': []}
    if allowed:assert module.evidence(store, Analytics())['pins']['ads'] == 'ads'
    else:
        with pytest.raises(ExecutionBlocked, match='Stale'):module.evidence(store, Analytics())


def test_evidence_deadline_binds_next_mapping_offer_and_stock_boundary():
    from advergent.execution import evidence_deadline
    e = ev();at = e['at'];e['source_deadline'] = at + timedelta(seconds=900)
    e['inventory']['assumptions'] = {'freshness_seconds': 600}
    e['inventory']['products'][0]['variants'] = [{'stock_observed_at': at.isoformat()}]
    latest = dict(observed_at=at.isoformat(), offer_expires_at=(at + timedelta(seconds=20)).isoformat())
    e['diagnostics'] = dict(assumptions={'freshness_seconds': 900}, recommendations=[dict(platform='meta', account_id='a', resource_id='r', destinations=[{'evidence': [latest]}])])
    m = Mapping.model_validate_json(canonical(dict(platform='meta', account_id='a', resource_id='r', id='next', products=['p'], provenance='test', confidence_bps=9500, valid_from=(at + timedelta(seconds=10)).isoformat(), valid_to=(at + timedelta(seconds=1000)).isoformat(), actor='test', reason='test')))
    e['mappings'] = [m];changes = [dict(platform='meta', account_id='a', scope={'products': ['p'], 'members': ['r']})]
    assert evidence_deadline(e, changes) == at + timedelta(seconds=10)
    e['mappings'] = [];assert evidence_deadline(e, changes) == at + timedelta(seconds=20)
    latest['offer_expires_at'] = None;assert evidence_deadline(e, changes) == at + timedelta(seconds=600)
