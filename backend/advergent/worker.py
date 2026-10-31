import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL
from sqlalchemy import text
from .config import Settings
from .contracts import GoldenMetric
from .exasol import ExasolAnalytics
from .operational import OperationalStore, ROOT


def refresh(store, analytics, fixture_path=ROOT / 'fixtures/foundation-v1.json'):
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    digest = hashlib.sha256(fixture_bytes).hexdigest()
    dataset_id = str(uuid5(NAMESPACE_URL, digest))
    job_id = str(uuid4())
    # Session-level lock serializes loaders across API/worker processes. Release on crash.
    with store.engine.connect() as lock:
        if not lock.execute(text('SELECT pg_try_advisory_lock(17012026)')).scalar():
            raise RuntimeError('Refresh already running')
        lock.commit()
        try:
            with store.engine.begin() as conn:
                conn.execute(text("UPDATE refresh_jobs SET status='failed', error_code='worker_interrupted', finished_at=now() WHERE status='running'"))
                conn.execute(text("INSERT INTO refresh_jobs(id,dataset_id,dataset_version,fixture_hash,status) VALUES (:job,:dataset,:version,:hash,'running')"), dict(job=job_id, dataset=dataset_id, version=fixture['version'], hash=digest))
            try:
                analytics.probe()
                analytics.load(dataset_id, fixture)
                if analytics.metric(dataset_id) != GoldenMetric(**fixture['expected']):
                    raise ValueError('Golden metric mismatch')
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE refresh_jobs SET status='succeeded',finished_at=now() WHERE id=:job"), {'job': job_id})
                    conn.execute(text('INSERT INTO publications VALUES (1,:job) ON CONFLICT(singleton) DO UPDATE SET job_id=EXCLUDED.job_id'), {'job': job_id})
            except Exception:
                with store.engine.begin() as conn:
                    conn.execute(text("UPDATE refresh_jobs SET status='failed',error_code='analytics_refresh_failed',finished_at=now() WHERE id=:job"), {'job': job_id})
                raise RuntimeError('Refresh failed; prior publication preserved') from None
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(17012026)'))
            lock.commit()
    return dataset_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['migrate', 'refresh', 'probe', 'commerce', 'ads', 'attribution', 'finance', 'inventory', 'diagnostics'])
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    settings = Settings.from_env()
    store, analytics = OperationalStore(settings.database_url), ExasolAnalytics(settings)
    if args.command == 'migrate':
        store.migrate()
        analytics.migrate()
    elif args.command == 'probe':
        analytics.probe()
    elif args.command == 'diagnostics':
        from .diagnostics import import_diagnostics
        print(import_diagnostics(store, analytics, **({'fixture_path': args.fixture} if args.fixture else {})))
    elif args.command == 'inventory':
        from .inventory import import_inventory
        print(import_inventory(store, analytics, **({'fixture_path': args.fixture} if args.fixture else {})))
    elif args.command == 'finance':
        from .finance import import_finance
        print(import_finance(store, analytics, **({'fixture_path': args.fixture} if args.fixture else {})))
    elif args.command == 'attribution':
        from .attribution import import_attribution
        print(import_attribution(store, analytics, **({'fixture_path': args.fixture} if args.fixture else {})))
    elif args.command == 'ads':
        from .ads import import_ads
        print(import_ads(store, analytics, **({'fixture_path': args.fixture} if args.fixture else {})))
    elif args.command == 'commerce':
        from .commerce import import_commerce
        print(import_commerce(store, analytics, **({'fixture_path': args.fixture} if args.fixture else {})))
    else:
        print(refresh(store, analytics))


if __name__ == '__main__':
    main()
