-- The account workflow does not modify reports or model tables.
CREATE TABLE IF NOT EXISTS admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(40) NOT NULL UNIQUE,
  email VARCHAR(254) NOT NULL,
  organization VARCHAR(160) NOT NULL,
  reason VARCHAR(800) NOT NULL,
  password_hash TEXT NOT NULL,
  status VARCHAR(12) NOT NULL DEFAULT 'pending'
      CHECK (status IN ('pending','approved','rejected','disabled')),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at TIMESTAMPTZ,
  reviewed_by VARCHAR(80),
  review_note VARCHAR(800)
);
CREATE INDEX IF NOT EXISTS admin_users_status_requested_idx ON admin_users(status, requested_at);
CREATE TABLE IF NOT EXISTS admin_audit_logs (
  id BIGSERIAL PRIMARY KEY,
  actor VARCHAR(80) NOT NULL,
  action VARCHAR(48) NOT NULL,
  target_username VARCHAR(40) NOT NULL,
  detail VARCHAR(800),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS admin_audit_logs_created_idx ON admin_audit_logs(created_at DESC);
