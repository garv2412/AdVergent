CREATE TABLE IF NOT EXISTS ad_runs (
    id UUID PRIMARY KEY, version TEXT NOT NULL, fixture_hash TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL, scenario_clock TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS ad_attempts (
    id UUID PRIMARY KEY, run_id UUID NOT NULL REFERENCES ad_runs(id),
    status TEXT NOT NULL, started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ, error_code TEXT
);
CREATE TABLE IF NOT EXISTS ad_cursors (
    run_id UUID REFERENCES ad_runs(id), platform TEXT NOT NULL,
    next_page INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(run_id,platform)
);
CREATE TABLE IF NOT EXISTS ad_source_reports (
    run_id UUID REFERENCES ad_runs(id), report_key TEXT NOT NULL,
    revision INTEGER NOT NULL, body JSONB NOT NULL, PRIMARY KEY(run_id,report_key)
);
CREATE TABLE IF NOT EXISTS ad_publications (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1), run_id UUID NOT NULL REFERENCES ad_runs(id)
);
