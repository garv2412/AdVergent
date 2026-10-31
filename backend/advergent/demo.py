"""Preserving local demo rehearsal. No proposal, approval or simulator writes."""
import hashlib
from uuid import uuid4

from sqlalchemy import text

from .decisions import DecisionService
from .execution import Executor
from .execution_scenarios import prepare, restore


PROTECTED_TABLES = ('action_plans', 'action_steps', 'action_events',
                    'simulated_resources', 'simulated_receipts', 'execution_control')


def protected_hashes(store):
    with store.engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
        return {table: hashlib.sha256('\n'.join(sorted(conn.execute(
            text('SELECT row_to_json(t)::text FROM ' + table + ' t')
        ).scalars())).encode()).hexdigest() for table in PROTECTED_TABLES}


def observation_hashes(store):
    with store.engine.connect() as conn:
        return dict(conn.execute(text(
            "SELECT digest || ':' || resource_key, md5(row_to_json(t)::text) FROM decision_observations t"
        )).all())


def rehearse_isolation(store, analytics):
    """A25: two new source namespaces after retained partial actions, no reset.

    Fresh timestamps and UUIDs intentionally differ. Compare the same semantic
    stockout advice and exact monetary facts, rather than pretending the new
    source observations are byte-identical historical evidence.
    """
    before = protected_hashes(store)
    observations = observation_hashes(store)
    with store.engine.connect() as conn:
        partials = conn.execute(text(
            "SELECT COUNT(*) FROM action_plans WHERE status='partially_succeeded'"
        )).scalar_one()
    if not partials:
        raise RuntimeError('A25 requires retained partial-action history; do not manufacture an action')
    service = DecisionService(store, analytics, Executor(store, analytics))
    runs, facts, keys = [], [], []
    try:
        for _ in range(2):
            tag = 'demo14-' + uuid4().hex[:12]
            names = prepare(store, analytics, mode='pause', tag=tag)
            snapshot = service.query()
            assert snapshot.status == 'available'
            data = snapshot.data
            row = next(r for r in data.decisions if r.resource_id == names['m-set'])
            assert row.advice == 'pause_review' and row.change['after'] == 'paused'
            assert row.products == ['p0']
            assert not data.mutation_enabled and not data.publishing_enabled
            assert data.budget['total_paise'] == data.budget['allocated_total_paise'] == 1100000
            current = {r.key for r in data.decisions}
            assert not current.intersection(store.budget_state()['resources'])
            if keys:
                assert current.isdisjoint(keys[0])
            keys.append(current)
            facts.append((row.advice, row.products, row.change['after'],
                          data.budget['total_paise'], data.budget['allocated_total_paise']))
            runs.append(dict(tag=tag, digest=data.digest, pins=snapshot.pins))
            assert protected_hashes(store) == before
        assert facts[0] == facts[1]
        assert runs[0]['pins'] != runs[1]['pins']
        return dict(runs=runs, retained_partial_actions=partials,
                    semantic_facts_match=True, advertising_mutations=0)
    finally:
        # Also restores coherent defaults after a failed assertion/import/query.
        restore(store, analytics)
        assert protected_hashes(store) == before
        after = observation_hashes(store)
        assert all(after.get(key) == value for key, value in observations.items())
