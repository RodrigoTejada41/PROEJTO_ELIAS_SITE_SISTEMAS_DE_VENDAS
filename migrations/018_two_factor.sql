BEGIN;

ALTER TABLE identity_users ADD COLUMN totp_secret bytea;
ALTER TABLE identity_users ADD COLUMN totp_last_step bigint;
ALTER TABLE identity_sessions ADD COLUMN mfa_verified boolean NOT NULL DEFAULT false;

CREATE TABLE identity_mfa_challenges (
    user_id bigint PRIMARY KEY REFERENCES identity_users (id),
    token_hash bytea NOT NULL UNIQUE,
    password_version bytea NOT NULL,
    expires_at timestamptz NOT NULL,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5)
);

COMMIT;
