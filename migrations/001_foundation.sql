CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash VARCHAR(64) PRIMARY KEY,
 expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS refresh_jobs (
 id UUID PRIMARY KEY,
 dataset_id UUID NOT NULL,
 dataset_version TEXT NOT NULL,
 fixture_hash VARCHAR(64) NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 finished_at TIMESTAMPTZ,
 error_code TEXT
);
CREATE TABLE IF NOT EXISTS publications (
 singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
 job_id UUID NOT NULL REFERENCES refresh_jobs(id)
);
INSERT INTO schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;
