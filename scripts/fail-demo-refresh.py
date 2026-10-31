"""A26: real duplicate-key failure after the first INSERT; keep prior version."""
import hashlib
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore, ROOT
from advergent.worker import refresh

settings = Settings.from_env()
store, analytics = OperationalStore(settings.database_url), ExasolAnalytics(settings)
original = store.publication()[0]
assert original is not None
expected = analytics.metric(str(original['dataset_id']))
fixture = json.loads((ROOT / 'fixtures/foundation-v1.json').read_text())
fixture['version'] = 'phase14-failed-' + uuid4().hex
fixture['lines'][1]['id'] = fixture['lines'][0]['id']
with TemporaryDirectory() as directory:
    path = Path(directory) / 'duplicate.json'
    path.write_text(json.dumps(fixture))
    failed = str(uuid5(NAMESPACE_URL, hashlib.sha256(path.read_bytes()).hexdigest()))
    try:
        refresh(store, analytics, path)
    except RuntimeError as error:
        assert str(error) == 'Refresh failed; prior publication preserved'
    else:
        raise AssertionError('Duplicate-key refresh unexpectedly succeeded')
assert analytics.metric(failed).line_count == 0
assert store.publication()[0] == original and store.publication()[1] == 'failed'
assert analytics.metric(str(original['dataset_id'])) == expected
print('PASS: A26 actual SQL failure rolled back; exact prior publication and metric retained')
