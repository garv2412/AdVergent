CREATE TABLE IF NOT EXISTS commerce_runs (
 id UUID PRIMARY KEY,
 fixture_hash VARCHAR(64) NOT NULL,
 version TEXT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL,
 scenario_clock TIMESTAMPTZ NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('running','failed','succeeded')),
 next_page INTEGER NOT NULL DEFAULT 0,
 reconciled BOOLEAN NOT NULL DEFAULT false,
 repair_count INTEGER NOT NULL DEFAULT 0,
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 finished_at TIMESTAMPTZ,
 error_code TEXT
);
CREATE TABLE IF NOT EXISTS commerce_staging (
 run_id UUID NOT NULL REFERENCES commerce_runs(id),
 kind TEXT NOT NULL,
 source_id TEXT NOT NULL,
 body JSONB NOT NULL,
 PRIMARY KEY(run_id,kind,source_id)
);
CREATE TABLE IF NOT EXISTS commerce_deliveries (
 run_id UUID NOT NULL REFERENCES commerce_runs(id),
 delivery_id TEXT NOT NULL,
 payload_hash VARCHAR(64) NOT NULL,
 PRIMARY KEY(run_id,delivery_id)
);
CREATE TABLE IF NOT EXISTS commerce_publications (
 singleton INTEGER PRIMARY KEY CHECK (singleton=1),
 run_id UUID NOT NULL REFERENCES commerce_runs(id)
);
CREATE TABLE IF NOT EXISTS commerce_attempts (
 id UUID PRIMARY KEY,
 run_id UUID NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('running','failed','succeeded')),
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 finished_at TIMESTAMPTZ,
 error_code TEXT
);
INSERT INTO schema_migrations(version) VALUES (2) ON CONFLICT DO NOTHING;
