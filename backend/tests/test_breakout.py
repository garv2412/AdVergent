from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from advergent.breakout import FunnelSource, FunnelEvent, evaluate
from advergent.breakout_fixture import fixture
from advergent.api import create_app
from advergent.contracts import AnalyticsUnavailable
from test_foundation import SETTINGS, MemoryStore, sign_in

NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)


def inputs():
    f = fixture()
    # A signal-time query cannot observe the future holdout.
    f['observed_at'] = NOW.isoformat()
    f['events'] = [e for e in f['events'] if datetime.fromisoformat(e['at']) < NOW]
    return FunnelSource.model_validate(f)


def counts():
    return {(pid,w,k):n for pid in ('p0','p1','p2') for w in ('baseline','signal','evaluation')
            for k,n in dict(view=100 if w=='baseline' else 200,cart=25,impression=1000,click=30,purchase=0).items()}


def run(f=None, c=None, risk='clear', fresh=True, margin=3000, at=NOW, current=True):
    return evaluate(f or inputs(), c if c is not None else counts(),
        [dict(product_id='p1',risk=risk,fresh=fresh)], {'p1':margin}, at, current, 'hash', 0).ranking[0]


def test_exact_score_floor_and_a19_abstention():
    r=run()
    assert r.view_growth_bps==10000 and r.cart_rate_bps==1250 and r.ctr_bps==300
    assert r.score==14550 and r.rank==1 and r.evaluation=='pending'
    c=counts()
    for w in ('baseline','signal'):
        c['p1',w,'view']=3;c['p1',w,'cart']=1;c['p1',w,'click']=2
    r=run(c=c)
    assert r.score is None and r.rank is None and 'sparse funnel evidence' in r.blockers
    assert 'sparse ad evidence' in r.blockers


@pytest.mark.parametrize('kind,n',[('view',99),('cart',19),('impression',999),('click',19)])
def test_each_window_evidence_floor(kind,n):
    for w in ('baseline','signal'):
        c=counts();c['p1',w,kind]=n
        assert run(c=c).score is None


def test_dedup_conflict_utc_and_strict_event_money_exclusion():
    raw=fixture();f=FunnelSource.model_validate(raw)
    assert len(f.events)-len(f.unique_events())==1
    raw['events'][-1]['product_id']='p1'
    with pytest.raises(ValidationError,match='Conflicting'):FunnelSource.model_validate(raw)
    e=dict(id='x',product_id='p0',kind='view',at='2026-10-15T05:30:00+05:30')
    assert FunnelEvent(**e).at==NOW
    with pytest.raises(ValidationError):FunnelEvent(**e,revenue_paise=100)
    with pytest.raises(ValidationError):FunnelEvent(**{**e,'at':'2026-10-15'})
    with pytest.raises(ValidationError):FunnelEvent(**{**e,'kind':'purchase'})


@pytest.mark.parametrize('change', ['coverage','series','margin','negative','stock','fresh','current','stale','future','zero','inconsistent'])
def test_abstain_on_incomplete_or_unsafe_evidence(change):
    f=inputs();c=counts();args={}
    if change=='coverage':f.coverage[3].tracked_days=6
    if change=='series':f.coverage[4].ad_series='different-placement'
    if change=='margin':args['margin']=None
    if change=='negative':args['margin']=-1
    if change=='stock':args['risk']='pause'
    if change=='fresh':args['fresh']=False
    if change=='current':args['current']=False
    if change=='stale':args['at']=NOW+timedelta(seconds=901)
    if change=='future':args['at']=NOW-timedelta(seconds=1)
    if change=='zero':c['p1','baseline','view']=0
    if change=='inconsistent':c['p1','signal','cart']=201
    assert run(f,c,**args).score is None


def test_later_evaluation_never_changes_score_or_rank():
    f=FunnelSource.model_validate(fixture());c=counts()
    at=NOW+timedelta(days=7)
    r=run(f,c,at=at)
    assert r.evaluation=='sustained' and r.score is None  # old signal is never current
    c['p1','evaluation','view']=101
    assert run(f,c,at=at).evaluation=='not sustained'
    c['p1','evaluation','cart']=19
    assert run(f,c,at=at).evaluation=='insufficient'
    # Even accidental future holdout counters passed to policy do not enter the score.
    c=counts();a=run(c=c);c['p1','evaluation','view']=10000000
    assert run(c=c).score==a.score and run(c=c).rank==a.rank


def test_api_auth_unavailable_pin_change_and_no_mutations():
    pubs={k:dict(id=uuid4(),observed_at=NOW) for k in ('inventory','finance','commerce','ads','attribution')}
    for k in ('finance','commerce','ads','attribution'):pubs['inventory'][k+'_id']=pubs[k]['id']
    store=MemoryStore()
    for k in pubs:setattr(store,{'ads':'ad'}.get(k,k)+'_publication',lambda key=k:(pubs[key],None))
    class Analytics:
        fail=False
        change=False
        def breakout_data(self,pins,at,current):
            if self.fail:raise AnalyticsUnavailable('private-secret')
            if self.change:pubs['commerce']=dict(id=uuid4(),observed_at=NOW)
            return evaluate(inputs(),counts(),[dict(product_id='p1',risk='clear',fresh=True)],{'p1':3000},NOW,current,'hash',0)
    a=Analytics();client=TestClient(create_app(SETTINGS,store,a))
    assert client.get('/api/breakout').status_code==401
    sign_in(client)
    assert client.get('/api/breakout').json()['data']['ranking'][0]['rank']==1
    a.change=True
    d=client.get('/api/breakout').json()
    assert not d['dependencies_current'] and d['data']['ranking'][0]['rank'] is None
    a.fail=True
    d=client.get('/api/breakout').json()
    assert d['status']=='analytics_unavailable' and d['data'] is None and d['queried_at'] is None
    assert 'private-secret' not in str(d)
    assert client.post('/api/breakout',json={}).status_code in (403,405)


def test_source_rejects_future_observations_and_duplicate_coverage():
    raw=fixture();raw['events'][0]['at']='2026-11-01T00:00:00Z'
    with pytest.raises(ValidationError,match='future'):FunnelSource.model_validate(raw)
    raw=fixture();raw['coverage'].append(raw['coverage'][0].copy())
    with pytest.raises(ValidationError,match='Duplicate coverage'):FunnelSource.model_validate(raw)


def test_partial_evaluation_window_never_reported_as_complete():
    f=FunnelSource.model_validate(fixture())
    f.observed_at=NOW+timedelta(days=7,seconds=-1)
    assert run(f,at=NOW+timedelta(days=7)).evaluation=='pending'
