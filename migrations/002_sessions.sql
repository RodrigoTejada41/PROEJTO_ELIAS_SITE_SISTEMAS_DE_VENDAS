BEGIN;

CREATE TABLE identity_sessions (
    token_hash bytea PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES identity_users (id),
    expires_at timestamptz NOT NULL
);

CREATE TABLE identity_login_limits (
    address inet PRIMARY KEY,
    attempts integer NOT NULL,
    expires_at timestamptz NOT NULL
);

COMMIT;
