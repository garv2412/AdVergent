"""Phase 14 preservation fence, extending the inherited full analytical audit."""
import json
import runpy
import sys
from advergent.config import Settings
from advergent.demo import protected_hashes, observation_hashes
from advergent.operational import OperationalStore, ROOT

store = OperationalStore(Settings.from_env().database_url)
baseline = ROOT / '.runtime/phase14-preservation.json'
current = dict(protected=protected_hashes(store), observations=observation_hashes(store))
if '--capture' in sys.argv:
    if baseline.exists():
        assert json.loads(baseline.read_text()) == current, 'Existing Phase 14 baseline differs'
    else:
        baseline.write_text(json.dumps(current, sort_keys=True))
    print('PASS: Phase 14 six protected hashes and all inherited observations captured')
else:
    expected = json.loads(baseline.read_text())
    assert current['protected'] == expected['protected']
    assert all(current['observations'].get(k) == v for k, v in expected['observations'].items())
    runpy.run_path(str(ROOT / 'scripts/verify-decisions-state.py'))
    assert protected_hashes(store) == expected['protected']
    after = observation_hashes(store)
    assert all(after.get(k) == v for k, v in current['observations'].items())
    print('PASS: Phase 14 inherited observations unchanged; additional observations retained; all analytical/default/history gates pass')
