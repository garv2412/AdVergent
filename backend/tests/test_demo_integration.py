"""A25 preserving rehearsal; explicit opt-in, never executes advertising actions."""
import os
import pytest
from advergent.config import Settings
from advergent.demo import rehearse_isolation
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore

pytestmark = pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1', reason='Dedicated real stores only')


def test_real_a25_new_runs_preserve_partial_history_and_restore_defaults():
    settings = Settings.from_env()
    result = rehearse_isolation(OperationalStore(settings.database_url), ExasolAnalytics(settings))
    assert result['semantic_facts_match'] and result['retained_partial_actions'] > 0
    assert result['advertising_mutations'] == 0
