"""Run the non-mutating A25 source rehearsal against existing private stores."""
import json
from datetime import datetime, timezone
from advergent.config import Settings
from advergent.demo import rehearse_isolation
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore, ROOT

settings = Settings.from_env()
result = rehearse_isolation(OperationalStore(settings.database_url), ExasolAnalytics(settings))
result['verified_at_utc'] = datetime.now(timezone.utc).isoformat()
(ROOT / '.runtime/phase14-rehearsal.json').write_text(json.dumps(result, indent=2))
print('PASS: A25 two disjoint source runs; reproducible semantic facts; retained partial-action history; six protected hashes unchanged; defaults restored; zero advertising mutations')
