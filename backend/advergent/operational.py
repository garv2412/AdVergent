from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import create_engine, text
from .security import token_hash

ROOT = Path(__file__).resolve().parents[2]


class OperationalStore:
    def budget_state(self):
        """Read-only snapshot; never initializes or resets simulator observations."""
        with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
            control = conn.execute(text('SELECT stopped,actor,changed_at FROM execution_control WHERE singleton=1')).mappings().one()
            resources = {r['resource_key']: dict(value=r['value'], revision=r['revision'], last_request=r['last_request'])
                for r in conn.execute(text('SELECT resource_key,value,revision,last_request FROM simulated_resources')).mappings()}
            unresolved = conn.execute(text("SELECT COUNT(*) FROM action_steps s JOIN action_plans p ON p.id=s.plan_id WHERE s.outcome='unknown' OR p.status IN ('executing','revalidating')")).scalar_one()
            return dict(resources=resources, stopped=control['stopped'], unresolved=unresolved,
                control_version=dict(actor=control['actor'],changed_at=control['changed_at'].isoformat()))

    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 5})

    def migrate(self):
        with self.engine.begin() as conn:
            conn.execute(text('SELECT pg_advisory_xact_lock(17012027)'))
            for migration in sorted((ROOT / 'migrations').glob('*.sql')):
                for statement in migration.read_text().split(';'):
                    if statement.strip():
                        conn.execute(text(statement))

    def commerce_publication(self):
        with self.engine.connect() as conn:
            row = conn.execute(text('SELECT r.* FROM commerce_publications p JOIN commerce_runs r ON r.id=p.run_id WHERE p.singleton=1')).mappings().first()
            latest = conn.execute(text('SELECT a.status,r.next_page,a.error_code FROM commerce_attempts a LEFT JOIN commerce_runs r ON r.id=a.run_id ORDER BY a.started_at DESC LIMIT 1')).mappings().first()
            return (dict(row) if row else None), (dict(latest) if latest else None)

    def ad_publication(self):
        with self.engine.connect() as conn:
            row = conn.execute(text('SELECT r.* FROM ad_publications p JOIN ad_runs r ON r.id=p.run_id WHERE p.singleton=1')).mappings().first()
            latest = conn.execute(text('SELECT status FROM ad_attempts ORDER BY started_at DESC LIMIT 1')).scalar()
            return (dict(row) if row else None), latest

    def attribution_publication(self):
        with self.engine.connect() as conn:
            row = conn.execute(text('SELECT r.* FROM attribution_publications p JOIN attribution_runs r ON r.id=p.run_id WHERE p.singleton=1')).mappings().first()
            latest = conn.execute(text('SELECT status FROM attribution_attempts ORDER BY started_at DESC LIMIT 1')).scalar()
            return (dict(row) if row else None), latest

    def finance_publication(self):
        with self.engine.connect() as conn:
            row = conn.execute(text('SELECT r.*, c.observed_at AS commerce_observed_at, a.observed_at AS ads_observed_at, t.observed_at AS attribution_observed_at FROM finance_publications p JOIN finance_runs r ON r.id=p.run_id JOIN commerce_runs c ON c.id=r.commerce_id JOIN ad_runs a ON a.id=r.ads_id JOIN attribution_runs t ON t.id=r.attribution_id WHERE p.singleton=1')).mappings().first()
            latest = conn.execute(text('SELECT status FROM finance_attempts ORDER BY started_at DESC LIMIT 1')).scalar()
            return (dict(row) if row else None), latest

    def inventory_publication(self):
        with self.engine.connect() as conn:
            row=conn.execute(text('SELECT r.*,f.commerce_id,f.ads_id,f.attribution_id FROM inventory_publications p JOIN inventory_runs r ON r.id=p.run_id JOIN finance_runs f ON f.id=r.finance_id WHERE p.singleton=1')).mappings().first()
            latest=conn.execute(text('SELECT status FROM inventory_attempts ORDER BY started_at DESC LIMIT 1')).scalar()
            return (dict(row) if row else None),latest

    def diagnostics_publication(self):
        with self.engine.connect() as conn:
            row=conn.execute(text('SELECT r.*,i.finance_id,f.commerce_id,f.ads_id,f.attribution_id FROM diagnostics_publications p JOIN diagnostics_runs r ON r.id=p.run_id JOIN inventory_runs i ON i.id=r.inventory_id JOIN finance_runs f ON f.id=i.finance_id WHERE p.singleton=1')).mappings().first()
            latest=conn.execute(text('SELECT status FROM diagnostics_attempts ORDER BY started_at DESC LIMIT 1')).scalar()
            return (dict(row) if row else None),latest

    def session(self, token: str):
        with self.engine.connect() as conn:
            return bool(conn.execute(text('SELECT 1 FROM sessions WHERE token_hash=:hash AND expires_at > now()'), {'hash': token_hash(token)}).scalar())

    def login(self, token: str):
        with self.engine.begin() as conn:
            conn.execute(text('DELETE FROM sessions WHERE expires_at <= now()'))
            conn.execute(text('INSERT INTO sessions VALUES (:hash, :expiry)'), {'hash': token_hash(token), 'expiry': datetime.now(timezone.utc) + timedelta(hours=1)})

    def logout(self, token: str):
        with self.engine.begin() as conn:
            conn.execute(text('DELETE FROM sessions WHERE token_hash=:hash'), {'hash': token_hash(token)})

    def publication(self):
        with self.engine.connect() as conn:
            row = conn.execute(text('SELECT j.* FROM publications p JOIN refresh_jobs j ON j.id=p.job_id WHERE p.singleton=1')).mappings().first()
            latest = conn.execute(text('SELECT status FROM refresh_jobs ORDER BY started_at DESC LIMIT 1')).scalar()
            return (dict(row) if row else None), latest
