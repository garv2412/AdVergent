CREATE TABLE IF NOT EXISTS decision_observations (
 digest text NOT NULL, resource_key text NOT NULL, snapshot jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 action_id uuid REFERENCES action_plans(id),
 PRIMARY KEY(digest,resource_key)
);
ALTER TABLE decision_observations ADD COLUMN IF NOT EXISTS recorded_by text NOT NULL DEFAULT 'demo operator';
ALTER TABLE decision_observations ADD COLUMN IF NOT EXISTS linked_at timestamptz;
