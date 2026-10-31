CREATE TABLE IF NOT EXISTS execution_control (
 singleton integer PRIMARY KEY CHECK (singleton=1), stopped boolean NOT NULL DEFAULT false,
 actor text NOT NULL DEFAULT 'initial', changed_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO execution_control(singleton) VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS simulated_resources (
 resource_key text PRIMARY KEY, value jsonb NOT NULL, revision integer NOT NULL DEFAULT 0,
 changed_at timestamptz NOT NULL DEFAULT now(), last_request text
);
CREATE TABLE IF NOT EXISTS action_plans (
 id uuid PRIMARY KEY, actor text NOT NULL, client_key text NOT NULL UNIQUE,
 request jsonb NOT NULL, plan jsonb NOT NULL, digest text NOT NULL,
 status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL,
 approved_by text, approved_at timestamptz, error_code text
);
CREATE TABLE IF NOT EXISTS action_steps (
 plan_id uuid NOT NULL REFERENCES action_plans(id), ordinal integer NOT NULL,
 resource_key text NOT NULL, request_id text NOT NULL UNIQUE, intent jsonb NOT NULL,
 outcome text NOT NULL DEFAULT 'pending', actual jsonb, error_code text,
 started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 PRIMARY KEY(plan_id,ordinal)
);
CREATE TABLE IF NOT EXISTS action_events (
 id bigserial PRIMARY KEY, plan_id uuid REFERENCES action_plans(id), actor text NOT NULL,
 event text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS simulated_receipts (
 request_id text PRIMARY KEY, resource_key text NOT NULL, before_state jsonb NOT NULL,
 after_state jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now()
);
