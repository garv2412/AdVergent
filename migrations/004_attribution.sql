CREATE TABLE IF NOT EXISTS attribution_runs (
 id uuid PRIMARY KEY, version text NOT NULL, fixture_hash text NOT NULL,
 commerce_id uuid NOT NULL, ads_id uuid NOT NULL, configuration jsonb NOT NULL,
 observed_at timestamptz NOT NULL, finished_at timestamptz
);
CREATE TABLE IF NOT EXISTS attribution_attempts (
 id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES attribution_runs(id),
 status text NOT NULL, started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 error_code text
);
CREATE TABLE IF NOT EXISTS attribution_publications (
 singleton integer PRIMARY KEY CHECK(singleton=1), run_id uuid NOT NULL REFERENCES attribution_runs(id)
);
